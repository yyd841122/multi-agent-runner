"""
Reviewer Agent 自动审查 MVP

对子项目任务执行审查：读取任务要求、开发报告、项目文件，
通过 model_adapter 调用 reviewer 模型，生成审查报告。
当前默认使用 mock provider。
"""

from pathlib import Path

from tools.model_adapter import ModelRequest, call_model


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

请严格按照以下格式输出：

# Reviewer Agent Output

## Agent

Reviewer Agent

## Task

任务编号：{task_id}
任务名称：（从任务块中提取）

## Status

PASS / FAIL / RETRY / BLOCKED / INFO

## Review Scope

审查范围：（说明审查了哪些内容）

## Requirement Match

是否符合任务目标：（是 / 否 / 部分满足，附说明）

## Acceptance Check

| 验收标准 | 是否满足 | 证据 |
|----------|----------|------|

## Issues

- （发现的问题，如无问题写"无"）

## Decision

APPROVE / REQUEST_CHANGES / RETRY / BLOCKED

## Evidence

- projects/down-100-floors-game/reports/review/{task_id}-review-report.md

## Next Action

建议下一步：

## 审查原则

1. 只审查当前任务，不审查其他任务
2. 以验收标准为判断依据
3. 不要求超出任务范围的实现
4. 不要求复杂游戏逻辑（当前是 MVP）
5. Decision 只能是 APPROVE / REQUEST_CHANGES / RETRY / BLOCKED 之一

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

请根据以上内容，审查 {task_id} 是否完成，并输出审查结论。
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
            system_prompt="你是 Reviewer Agent，负责审查任务完成情况。输出必须严格遵循指定的 markdown 格式。",
        )
    )
    print(f"模型调用完成：provider={response.provider}, model={response.model}, success={response.success}")

    # 6. 构造审查报告
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
        output_lines.extend(["", f"## Error", "", response.error])

    output_lines.extend([
        "",
        "## Reviewer Output",
        "",
        response.content,
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

    # 7. 保存审查报告
    output_path = game_project_dir / "reports" / "review" / f"{task_id}-review-report.md"
    save_review_output("\n".join(output_lines), output_path)
    print(f"审查报告已保存：{output_path}")

    return output_path
