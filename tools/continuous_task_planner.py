"""Continuous Task Planner — 连续任务自动推进计划生成。

严格遵循 docs/continuous-task-auto-advance-design.md 协议。
T059 只实现 dry-run 计划生成，不执行任务，不调用 Claude Code。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from tools.task_manager import load_tasks_file, parse_tasks


# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

MAX_TASKS_DEFAULT = 3
MAX_TASKS_HARD_LIMIT = 10


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class PlannedTask:
    """计划中的单个任务。"""
    task_id: str
    title: str
    status: str
    order: int          # 在计划中的顺序（1-based）
    reason: str          # 为什么选这个任务


@dataclass
class ContinuousTaskPlan:
    """连续任务推进计划。"""
    project: str                        # 项目路径
    source_file: str                    # tasks.md 路径
    next_pending: str | None            # 第一个 pending 任务编号
    planned_tasks: list[PlannedTask]    # 计划执行的任务列表
    max_tasks: int                      # 用户请求的 max_tasks
    hard_limit: int                     # 硬上限
    dry_run: bool                       # 是否 dry-run（T059 始终 True）
    plan_status: str                    # planned / no_pending_task / invalid_max_tasks
    stop_reason: str | None             # 停止原因
    human_review_required: bool         # 是否需要人工审查
    next_action: str                    # 建议下一步
    message: str                        # 详细消息


# ---------------------------------------------------------------------------
# 核心函数
# ---------------------------------------------------------------------------

def _validate_max_tasks(max_tasks: int) -> tuple[int, str]:
    """校验并修正 max_tasks。

    Returns:
        (adjusted_max_tasks, message)
    """
    if max_tasks < 1:
        return 0, f"max_tasks={max_tasks} 无效，必须 >= 1"
    if max_tasks > MAX_TASKS_HARD_LIMIT:
        adjusted = MAX_TASKS_HARD_LIMIT
        return adjusted, (
            f"max_tasks={max_tasks} 超过硬上限 {MAX_TASKS_HARD_LIMIT}，"
            f"已自动修正为 {adjusted}"
        )
    return max_tasks, ""


def build_continuous_task_plan(
    project_root: str | Path,
    max_tasks: int = MAX_TASKS_DEFAULT,
    dry_run: bool = True,
) -> ContinuousTaskPlan:
    """生成连续任务推进计划（dry-run）。

    从 docs/tasks.md 读取任务列表，识别 pending 任务，
    根据 max_tasks 生成执行计划。

    不执行任何任务，不调用 Claude Code。

    Args:
        project_root: 项目根目录（包含 docs/tasks.md）
        max_tasks: 一次最多推进任务数
        dry_run: 是否 dry-run（T059 始终 True）

    Returns:
        ContinuousTaskPlan
    """
    project_root = Path(project_root)
    tasks_file = project_root / "docs" / "tasks.md"

    # 1. 校验 max_tasks
    adjusted_max, adjust_msg = _validate_max_tasks(max_tasks)
    if adjusted_max < 1:
        return ContinuousTaskPlan(
            project=str(project_root),
            source_file=str(tasks_file),
            next_pending=None,
            planned_tasks=[],
            max_tasks=max_tasks,
            hard_limit=MAX_TASKS_HARD_LIMIT,
            dry_run=dry_run,
            plan_status="invalid_max_tasks",
            stop_reason=f"max_tasks={max_tasks} 无效",
            human_review_required=False,
            next_action="fix_max_tasks",
            message=adjust_msg,
        )

    # 2. 读取任务文件
    if not tasks_file.exists():
        return ContinuousTaskPlan(
            project=str(project_root),
            source_file=str(tasks_file),
            next_pending=None,
            planned_tasks=[],
            max_tasks=adjusted_max,
            hard_limit=MAX_TASKS_HARD_LIMIT,
            dry_run=dry_run,
            plan_status="no_pending_task",
            stop_reason="tasks.md 不存在",
            human_review_required=False,
            next_action="check_project_path",
            message=f"任务文件不存在：{tasks_file}",
        )

    content = load_tasks_file(tasks_file)
    tasks = parse_tasks(content)

    # 3. 收集所有 pending 任务
    pending_tasks = [t for t in tasks if t["status"] == "pending"]

    if not pending_tasks:
        return ContinuousTaskPlan(
            project=str(project_root),
            source_file=str(tasks_file),
            next_pending=None,
            planned_tasks=[],
            max_tasks=adjusted_max,
            hard_limit=MAX_TASKS_HARD_LIMIT,
            dry_run=dry_run,
            plan_status="no_pending_task",
            stop_reason="没有 pending 任务",
            human_review_required=False,
            next_action="all_tasks_done_or_add_new_tasks",
            message="当前没有 pending 任务，无法生成执行计划。",
        )

    # 4. 取前 adjusted_max 个 pending 任务生成计划
    planned = pending_tasks[:adjusted_max]
    planned_tasks = []
    for i, t in enumerate(planned, 1):
        planned_tasks.append(PlannedTask(
            task_id=t["id"],
            title=t["title"],
            status=t["status"],
            order=i,
            reason=f"第 {i} 个 pending 任务（共 {len(pending_tasks)} 个 pending）",
        ))

    next_pending = planned_tasks[0].task_id if planned_tasks else None
    total_pending = len(pending_tasks)
    selected = len(planned_tasks)

    # 5. 生成消息
    parts = []
    if adjust_msg:
        parts.append(adjust_msg)
    parts.append(
        f"共 {total_pending} 个 pending 任务，计划执行前 {selected} 个。"
    )
    if total_pending > adjusted_max:
        parts.append(
            f"剩余 {total_pending - adjusted_max} 个任务需要后续推进。"
        )

    return ContinuousTaskPlan(
        project=str(project_root),
        source_file=str(tasks_file),
        next_pending=next_pending,
        planned_tasks=planned_tasks,
        max_tasks=adjusted_max,
        hard_limit=MAX_TASKS_HARD_LIMIT,
        dry_run=dry_run,
        plan_status="planned",
        stop_reason=None,
        human_review_required=False,
        next_action="ready_for_run_project_loop",
        message=" ".join(parts),
    )
