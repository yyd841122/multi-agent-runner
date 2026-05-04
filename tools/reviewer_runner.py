"""
Reviewer Agent 自动审查 MVP

对子项目任务执行审查：读取任务要求、开发报告、项目文件，
通过 model_adapter 调用 reviewer 模型，生成审查报告。
当前默认使用 mock provider。

T027 新增：Reviewer 输出结构化解析能力。
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.model_adapter import ModelRequest, call_model


# ---------------------------------------------------------------------------
# T027：Reviewer 输出结构化解析
# ---------------------------------------------------------------------------

VALID_STATUSES = {"PASS", "FAIL", "RETRY", "BLOCKED", "INFO"}
VALID_DECISIONS = {"APPROVE", "REQUEST_CHANGES", "RETRY", "BLOCKED"}


@dataclass
class ReviewParseResult:
    """Reviewer 输出解析结果。"""
    success: bool
    status: str | None = None
    decision: str | None = None
    issues: list[str] | None = None
    summary: str | None = None
    next_action: str | None = None
    error: str | None = None
    raw: Any | None = None


def extract_machine_readable_json(content: str) -> str | None:
    """从 Reviewer 输出中提取 Machine Readable Result 的 JSON 字符串。

    支持三种格式：
    1. Markdown fenced json（```json ... ```）
    2. 无语言标记的 fenced block（``` ... ```）
    3. 整段内容就是 JSON
    """
    # 策略 1：在 "Machine Readable Result" 标题后查找 fenced json block
    mr_pattern = re.compile(
        r"##\s*Machine\s+Readable\s+Result\s*\n(.*?)(?=\n##\s|\Z)",
        re.DOTALL | re.IGNORECASE,
    )
    mr_match = mr_pattern.search(content)
    if mr_match:
        block = mr_match.group(1).strip()
        # 提取 fenced code block 中的内容
        fenced = re.search(r"```(?:json)?\s*\n(.*?)```", block, re.DOTALL)
        if fenced:
            return fenced.group(1).strip()
        # 没有 fenced block，可能直接是 JSON
        if block.startswith("{"):
            return block

    # 策略 2：全文查找 ```json ... ``` 中包含 status/decision 的块
    json_blocks = re.findall(r"```json\s*\n(.*?)```", content, re.DOTALL)
    for jb in json_blocks:
        jb_stripped = jb.strip()
        if '"status"' in jb_stripped and '"decision"' in jb_stripped:
            return jb_stripped

    # 策略 3：全文查找无标记 fenced block 中包含 status/decision 的块
    plain_blocks = re.findall(r"```\s*\n(.*?)```", content, re.DOTALL)
    for pb in plain_blocks:
        pb_stripped = pb.strip()
        if pb_stripped.startswith("{") and '"status"' in pb_stripped and '"decision"' in pb_stripped:
            return pb_stripped

    # 策略 4：整段内容就是 JSON
    stripped = content.strip()
    if stripped.startswith("{") and '"status"' in stripped and '"decision"' in stripped:
        return stripped

    return None


def parse_reviewer_output(content: str) -> ReviewParseResult:
    """解析 Reviewer 输出中的结构化结果。

    Args:
        content: Reviewer 完整输出文本

    Returns:
        ReviewParseResult 解析结果
    """
    # 1. 提取 JSON 字符串
    json_str = extract_machine_readable_json(content)
    if json_str is None:
        return ReviewParseResult(
            success=False,
            error="未找到 Machine Readable Result JSON 块",
        )

    # 2. 解析 JSON
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        return ReviewParseResult(
            success=False,
            error=f"JSON 解析失败: {e}",
            raw=json_str,
        )

    if not isinstance(data, dict):
        return ReviewParseResult(
            success=False,
            error=f"JSON 顶层不是对象，而是 {type(data).__name__}",
            raw=data,
        )

    # 3. 校验 status
    status = data.get("status")
    if status is None:
        return ReviewParseResult(
            success=False,
            error="缺少 status 字段",
            raw=data,
        )
    if status not in VALID_STATUSES:
        return ReviewParseResult(
            success=False,
            error=f"status 值不合法: {status}，可选: {', '.join(sorted(VALID_STATUSES))}",
            raw=data,
        )

    # 4. 校验 decision
    decision = data.get("decision")
    if decision is None:
        return ReviewParseResult(
            success=False,
            error="缺少 decision 字段",
            raw=data,
        )
    if decision not in VALID_DECISIONS:
        return ReviewParseResult(
            success=False,
            error=f"decision 值不合法: {decision}，可选: {', '.join(sorted(VALID_DECISIONS))}",
            raw=data,
        )

    # 5. 提取可选字段
    issues = data.get("issues", [])
    if not isinstance(issues, list):
        issues = [str(issues)]

    summary = data.get("summary", "")
    next_action = data.get("next_action", "")

    return ReviewParseResult(
        success=True,
        status=status,
        decision=decision,
        issues=issues,
        summary=str(summary),
        next_action=str(next_action),
        raw=data,
    )


def load_text_file(path: str | Path) -> str:
    """读取文本文件。"""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")
    return path.read_text(encoding="utf-8")


def extract_task_block(tasks_content: str, task_id: str) -> str:
    """从子项目 docs/tasks.md 中提取指定任务块。"""
    import re
    pattern = re.compile(
        rf"(^## {re.escape(task_id)}\s.+?$)(.*?)(?=^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(tasks_content)
    if not match:
        return f"(未找到任务 {task_id})"
    return match.group(0).strip()


def build_reviewer_prompt(
    task_id: str,
    task_block: str,
    dev_report: str,
    file_snapshots: dict[str, str],
) -> str:
    """构造 Reviewer Agent 审查 prompt。"""

    snapshots_section = ""
    for filename, content in file_snapshots.items():
        snapshots_section += f"\n### {filename}\n\n```\n{content}\n```\n"

    return f"""你是 Reviewer Agent。

你的任务是审查 {task_id} 的开发完成情况，判断是否符合任务验收标准。

## 输出格式要求

请严格按照以下格式输出。

自然语言审查报告可以保留，但**必须**在最后包含 `## Machine Readable Result` 段落。

### 自然语言报告格式

# Reviewer Agent Output

## Agent

Reviewer Agent

## Task

任务编号：{task_id}
任务名称：（从任务块中提取）

## Review Scope

审查范围：（说明审查了哪些内容）

## Requirement Match

是否符合任务目标：（是 / 否 / 部分满足，附说明）

## Acceptance Check

| 验收标准 | 是否满足 | 证据 |
|----------|----------|------|

## Issues

- （发现的问题，如无问题写"无"）

### Machine Readable Result（必须包含）

在自然语言报告之后，必须输出以下段落：

## Machine Readable Result

```json
{{
  "status": "PASS 或 FAIL 或 RETRY 或 BLOCKED 或 INFO",
  "decision": "APPROVE 或 REQUEST_CHANGES 或 RETRY 或 BLOCKED",
  "issues": ["问题描述1", "问题描述2"],
  "summary": "简短中文结论",
  "next_action": "中文建议下一步"
}}
```

**字段规则：**
- status 可选：PASS / FAIL / RETRY / BLOCKED / INFO
- decision 可选：APPROVE / REQUEST_CHANGES / RETRY / BLOCKED
- issues 必须是字符串数组，无问题为 []
- summary 必须是简短中文结论
- next_action 必须是中文建议

**判断规则：**
- 如果所有验收标准满足，输出 status=PASS，decision=APPROVE
- 如果有问题，输出 status=FAIL，decision=REQUEST_CHANGES
- 如果缺少文件或无法判断，输出 status=BLOCKED，decision=BLOCKED

## 审查原则

1. 只审查当前任务，不审查其他任务
2. 以验收标准为判断依据
3. 不要求超出任务范围的实现
4. 不要求复杂游戏逻辑（当前是 MVP）
5. 必须包含 Machine Readable Result

---

## 任务要求

{task_block}

---

## 开发报告

{dev_report}

---

## 项目文件快照

{snapshots_section}

---

请根据以上内容，审查 {task_id} 是否完成，并输出审查结论。务必在最后包含 Machine Readable Result JSON 块。
"""


def save_review_output(content: str, output_path: str | Path) -> Path:
    """保存 Reviewer Agent 审查报告。"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return output_path


def run_reviewer_for_game_task(
    task_id: str = "G002",
    game_project_dir: str | Path | None = None,
) -> Path:
    """对 down-100-floors-game 的指定任务执行审查。

    Args:
        task_id: 任务编号，默认 G002
        game_project_dir: 游戏项目目录，默认自动推断

    Returns:
        审查报告文件路径
    """
    if game_project_dir is None:
        game_project_dir = Path(__file__).parent.parent / "projects" / "down-100-floors-game"
    game_project_dir = Path(game_project_dir)

    # 1. 读取任务要求
    tasks_path = game_project_dir / "docs" / "tasks.md"
    tasks_content = load_text_file(tasks_path)
    task_block = extract_task_block(tasks_content, task_id)
    print(f"已读取任务要求：{task_id}")

    # 2. 读取开发报告
    dev_report_path = game_project_dir / "reports" / "dev" / f"{task_id}-dev-report.md"
    dev_report = load_text_file(dev_report_path)
    print(f"已读取开发报告：{dev_report_path.name}")

    # 3. 读取项目文件快照
    file_snapshots = {}
    for filename in ["index.html", "style.css", "script.js"]:
        filepath = game_project_dir / filename
        if filepath.exists():
            file_snapshots[filename] = load_text_file(filepath)
    print(f"已读取项目文件：{', '.join(file_snapshots.keys())}")

    # 4. 构造 Reviewer prompt
    reviewer_prompt = build_reviewer_prompt(
        task_id=task_id,
        task_block=task_block,
        dev_report=dev_report,
        file_snapshots=file_snapshots,
    )
    print("已构造 Reviewer prompt")

    # 5. 调用模型
    response = call_model(
        ModelRequest(
            agent="reviewer",
            prompt=reviewer_prompt,
            system_prompt="你是 Reviewer Agent，负责严格审查任务完成情况。输出必须包含自然语言审查报告和 Machine Readable Result JSON 块。",
        )
    )
    print(f"模型调用完成：provider={response.provider}, model={response.model}, success={response.success}")

    # 6. 解析结构化输出
    parsed = None
    if response.success and response.content:
        parsed = parse_reviewer_output(response.content)
        if parsed.success:
            print(f"结构化解析成功：status={parsed.status}, decision={parsed.decision}")
        else:
            print(f"结构化解析失败：{parsed.error}")

    # 7. 构造审查报告
    output_lines = [
        f"# {task_id} Review Report",
        "",
        "## Model Result",
        "",
        f"- provider: {response.provider}",
        f"- model: {response.model}",
        f"- success: {response.success}",
    ]

    if response.error:
        output_lines.extend(["", "## Error", "", response.error])

    # 解析结果段
    output_lines.extend(["", "## Parsed Result", ""])
    if parsed and parsed.success:
        output_lines.extend([
            f"- status: {parsed.status}",
            f"- decision: {parsed.decision}",
            f"- issues: {json.dumps(parsed.issues, ensure_ascii=False)}",
            f"- summary: {parsed.summary}",
            f"- next_action: {parsed.next_action}",
        ])
    elif parsed:
        output_lines.extend([
            f"- success: False",
            f"- error: {parsed.error}",
        ])
    else:
        output_lines.extend([
            "- success: False",
            "- error: 模型调用失败，无法解析",
        ])

    output_lines.extend([
        "",
        "## Reviewer Output",
        "",
        response.content if response.content else "(无输出)",
        "",
        "## Source Files Reviewed",
        "",
    ])
    for filename in file_snapshots:
        output_lines.append(f"- {filename}")
    output_lines.extend([
        f"- {task_id}-dev-report.md",
        "- docs/tasks.md",
        "",
    ])

    # 8. 保存审查报告
    output_path = game_project_dir / "reports" / "review" / f"{task_id}-review-report.md"
    save_review_output("\n".join(output_lines), output_path)
    print(f"审查报告已保存：{output_path}")

    return output_path, parsed
