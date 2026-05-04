"""通用 Project Runner — 执行指定子项目中的第一个 pending 任务"""

from __future__ import annotations

import re
from pathlib import Path

from tools.task_manager import (
    load_tasks_file,
    save_tasks_file,
)
from tools.claude_code_runner import run_claude_code
from tools.report_manager import (
    save_execution_report,
    append_run_log,
    analyze_claude_output,
)


# ---------------------------------------------------------------------------
# 项目路径校验
# ---------------------------------------------------------------------------

def validate_project_root(project_path: str | Path) -> Path:
    """校验项目路径是否存在，并返回绝对 Path。"""
    p = Path(project_path)
    if not p.is_absolute():
        p = Path.cwd() / p
    p = p.resolve()
    if not p.exists():
        raise FileNotFoundError(f"项目路径不存在：{project_path}")
    if not p.is_dir():
        raise NotADirectoryError(f"项目路径不是目录：{project_path}")
    return p


# ---------------------------------------------------------------------------
# 项目任务文件路径
# ---------------------------------------------------------------------------

def get_project_tasks_file(project_root: Path) -> Path:
    """返回子项目 docs/tasks.md 路径。"""
    return project_root / "docs" / "tasks.md"


# ---------------------------------------------------------------------------
# 项目报告路径
# ---------------------------------------------------------------------------

def get_project_dev_report_path(project_root: Path, task_id: str) -> Path:
    """返回子项目开发报告路径。"""
    return project_root / "reports" / "dev" / f"{task_id}-dev-report.md"


# ---------------------------------------------------------------------------
# 通用任务解析（支持任意前缀）
# ---------------------------------------------------------------------------

def parse_project_tasks(content: str) -> list[dict]:
    """解析子项目 tasks.md，自动识别任务编号前缀（如 G、T、P 等）。

    匹配格式：## <前缀><数字> <标题>
    例如：## G003 实现玩家角色显示
    """
    pattern = re.compile(r"^## ([A-Z]+\d+)\s+(.+)$", re.MULTILINE)
    matches = list(pattern.finditer(content))

    tasks: list[dict] = []
    for i, match in enumerate(matches):
        task_id = match.group(1)
        title = match.group(2).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        raw = content[start:end].strip()

        status = _extract_project_field(raw, "状态")
        role = _extract_project_field(raw, "角色")
        goal = _extract_project_field(raw, "目标")

        tasks.append({
            "id": task_id,
            "title": title,
            "status": status,
            "role": role,
            "goal": goal,
            "raw": raw,
        })
    return tasks


def _extract_project_field(text: str, field_name: str) -> str:
    """从子项目任务正文中提取字段值。"""
    pattern = re.compile(rf"^{re.escape(field_name)}[：:]\s*(.+)$", re.MULTILINE)
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def find_next_pending_project_task(tasks: list[dict]) -> dict | None:
    """找到子项目中第一个 pending 任务。"""
    for task in tasks:
        if task["status"] == "pending":
            return task
    return None


def update_project_task_status(content: str, task_id: str, new_status: str) -> str:
    """更新子项目任务状态。"""
    pattern = re.compile(
        rf"(^## {re.escape(task_id)}\s[^\n]*\n+状态[：:]\s*)(\S+)",
        re.MULTILINE,
    )
    match = pattern.search(content)
    if not match:
        raise ValueError(f"未找到子项目任务：{task_id}")
    return content[: match.start(2)] + new_status + content[match.end(2):]


# ---------------------------------------------------------------------------
# Prompt 生成
# ---------------------------------------------------------------------------

def build_project_task_prompt(project_root: Path, task: dict) -> str:
    """根据子项目任务生成 Claude Code 执行 prompt。"""
    task_id = task.get("id", "")
    title = task.get("title", "")
    goal = task.get("goal", "")
    role = task.get("role", "Developer")
    raw = task.get("raw", "")

    # 项目目录下的关键文件（自动检测）
    project_name = project_root.name
    evidence_path = get_project_dev_report_path(project_root, task_id)

    return f"""# {task_id}：{title}

你现在是 {role} Agent。

## 当前项目

当前项目是 `{project_name}`。
项目路径：`{project_root}`

## 当前任务

{task_id}：{title}

## 任务目标

{goal}

## 任务原始内容

{raw}

## 允许修改的文件

- `{project_root}/index.html`
- `{project_root}/style.css`
- `{project_root}/script.js`
- `{project_root}/docs/`
- `{project_root}/reports/`
- `{project_root}/memory/`

## 禁止修改的文件

- `{project_root}/requirement.md`
- multi-agent-runner 主框架代码
- runner.py
- tools/*.py
- config.yaml

## 限制要求

- 必须直接修改文件，不要只输出建议代码
- 不允许扩大任务范围
- 不允许修改主框架代码
- 所有文档使用简体中文
- 文件名、路径、命令保持英文

## 完成证据

完成后必须生成开发报告：
`{evidence_path}`

报告内容包含：
- 任务编号
- 修改文件列表
- 完成内容
- 验收标准自查
- 是否完成

请直接修改文件，不要只输出建议代码。

请开始执行 {task_id}。"""


# ---------------------------------------------------------------------------
# 主执行函数
# ---------------------------------------------------------------------------

def run_project_next(project_path: str | Path) -> dict:
    """执行指定子项目中的第一个 pending 任务。

    Returns:
        {
            "success": bool,          # 整体是否成功
            "project_path": str,      # 项目路径
            "task_id": str | None,    # 任务编号
            "task_title": str | None, # 任务名称
            "task_status": str,       # 最终任务状态
            "evidence_found": bool,   # 完成证据是否存在
            "message": str,           # 结果描述
        }
    """
    # 1. 校验项目路径
    try:
        project_root = validate_project_root(project_path)
    except (FileNotFoundError, NotADirectoryError) as e:
        return {
            "success": False,
            "project_path": str(project_path),
            "task_id": None,
            "task_title": None,
            "task_status": "N/A",
            "evidence_found": False,
            "message": str(e),
        }

    # 2. 读取子项目任务文件
    tasks_file = get_project_tasks_file(project_root)
    if not tasks_file.exists():
        return {
            "success": False,
            "project_path": str(project_root),
            "task_id": None,
            "task_title": None,
            "task_status": "N/A",
            "evidence_found": False,
            "message": f"子项目任务文件不存在：{tasks_file}",
        }

    content = load_tasks_file(tasks_file)
    tasks = parse_project_tasks(content)

    # 3. 找到第一个 pending 任务
    task = find_next_pending_project_task(tasks)
    if not task:
        return {
            "success": True,
            "project_path": str(project_root),
            "task_id": None,
            "task_title": None,
            "task_status": "N/A",
            "evidence_found": False,
            "message": "当前项目没有 pending 任务。",
        }

    task_id = task["id"]
    task_title = task["title"]
    print(f"找到子项目 pending 任务：{task_id} {task_title}")

    # 4. 标记为 in_progress
    print(f"正在将 {task_id} 标记为 in_progress...")
    content = update_project_task_status(content, task_id, "in_progress")
    save_tasks_file(tasks_file, content)

    # 5. 生成 prompt
    print("正在生成提示词...")
    prompt = build_project_task_prompt(project_root, task)

    # 保存 prompt 到子项目目录
    prompts_dir = project_root / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    (prompts_dir / "current_prompt.md").write_text(prompt, encoding="utf-8")

    # 6. 调用 Claude Code
    print("正在调用 Claude Code...")
    print()
    result = run_claude_code(prompt)

    # 7. 保存执行结果到主项目
    # 保存最新输出（复用 runner.py 的路径约定）
    from runner import save_latest_output as _save_latest

    _save_latest_output = _save_latest
    _save_latest_output(result)

    # 保存历史报告
    from pathlib import Path as _P
    _claude_history_dir = _P("reports/claude/history")
    _claude_output_file = _P("reports/claude/latest-output.md")
    _run_log_file = _P("reports/run-log.md")

    history_path = save_execution_report(result, _claude_history_dir, task)
    append_run_log(_run_log_file, task, result, history_path)

    # 8. 检查完成证据
    evidence_path = get_project_dev_report_path(project_root, task_id)
    evidence_found = evidence_path.exists()

    # 9. 判断结果
    # 分析执行结果（检查 429 等）
    analysis = analyze_claude_output(
        _claude_output_file.read_text(encoding="utf-8")
    )

    if not analysis["success"]:
        return {
            "success": False,
            "project_path": str(project_root),
            "task_id": task_id,
            "task_title": task_title,
            "task_status": "in_progress",
            "evidence_found": False,
            "message": f"执行失败（退出码 {analysis['returncode']}）",
        }

    if not evidence_found:
        return {
            "success": True,
            "project_path": str(project_root),
            "task_id": task_id,
            "task_title": task_title,
            "task_status": "in_progress",
            "evidence_found": False,
            "message": f"Claude Code 成功，但缺少完成证据：{evidence_path}",
        }

    # 有完成证据，标记 done
    content = load_tasks_file(tasks_file)
    content = update_project_task_status(content, task_id, "done")
    save_tasks_file(tasks_file, content)

    return {
        "success": True,
        "project_path": str(project_root),
        "task_id": task_id,
        "task_title": task_title,
        "task_status": "done",
        "evidence_found": True,
        "message": f"执行成功，完成证据存在",
    }
