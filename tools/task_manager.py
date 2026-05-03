"""任务管理器 — 读取、解析和更新 docs/tasks.md"""

from __future__ import annotations

import re
from pathlib import Path


def load_tasks_file(path: str | Path) -> str:
    """读取 docs/tasks.md 内容。"""
    return Path(path).read_text(encoding="utf-8")


def save_tasks_file(path: str | Path, content: str) -> None:
    """保存 docs/tasks.md 内容。"""
    Path(path).write_text(content, encoding="utf-8")


def parse_tasks(content: str) -> list[dict]:
    """解析 tasks.md 中的任务块。

    每个任务块以 '## T<编号>' 开头，到下一个同级标题或文件末尾结束。
    """
    # 按任务标题分割
    pattern = re.compile(r"^## (T\d+)\s+(.+)$", re.MULTILINE)
    matches = list(pattern.finditer(content))

    tasks: list[dict] = []
    for i, match in enumerate(matches):
        task_id = match.group(1)
        title = match.group(2).strip()

        # 任务正文：从标题下一行到下一个任务标题之前
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        raw = content[start:end].strip()

        # 提取各字段
        status = _extract_field(raw, "状态")
        role = _extract_field(raw, "角色")
        goal = _extract_field(raw, "目标")

        tasks.append({
            "id": task_id,
            "title": title,
            "status": status,
            "role": role,
            "goal": goal,
            "raw": raw,
        })

    return tasks


def find_next_pending_task(tasks: list[dict]) -> dict | None:
    """找到第一个状态为 pending 的任务。"""
    for task in tasks:
        if task["status"] == "pending":
            return task
    return None


def find_current_in_progress_task(tasks: list[dict]) -> dict | None:
    """找到当前第一个状态为 in_progress 的任务。"""
    for task in tasks:
        if task["status"] == "in_progress":
            return task
    return None


def update_task_status(content: str, task_id: str, new_status: str) -> str:
    """更新指定任务的状态。

    找到 ## T<task_id> 对应的任务块，将其中的"状态：xxx"改为新状态。
    如果找不到任务，抛出 ValueError。
    """
    # 匹配任务标题行及其后紧跟的"状态"行
    pattern = re.compile(
        rf"(^## {re.escape(task_id)}\s[^\n]*\n+状态[：:]\s*)(\S+)",
        re.MULTILINE,
    )
    match = pattern.search(content)
    if not match:
        raise ValueError(f"未找到任务：{task_id}")

    return content[: match.start(2)] + new_status + content[match.end(2) :]


def _extract_field(text: str, field_name: str) -> str:
    """从任务正文中提取指定字段的值。"""
    pattern = re.compile(rf"^{re.escape(field_name)}[：:]\s*(.+)$", re.MULTILINE)
    match = pattern.search(text)
    return match.group(1).strip() if match else ""
