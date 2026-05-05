"""Continuous Task Planner — 连续任务自动推进计划生成与 loop dry-run。

严格遵循 docs/continuous-task-auto-advance-design.md 协议。
T059 实现 dry-run 计划生成，T060 实现 loop dry-run 模拟推进。
不执行任务，不调用 Claude Code。
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
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


# ---------------------------------------------------------------------------
# T060: Loop Dry-Run 数据结构
# ---------------------------------------------------------------------------

@dataclass
class TaskRunResult:
    """单个任务在 loop dry-run 中的模拟结果。"""
    task_id: str
    title: str
    dry_run: bool                       # 始终 True
    execution_performed: bool           # 始终 False
    check_result: str                   # 始终 pass
    task_status: str                    # dry_run_planned
    stop_reason: str | None             # None 或 max_tasks_reached
    next_action: str                    # continue_to_next / stop / review_loop_summary
    message: str


@dataclass
class ContinuousLoopRunResult:
    """连续任务 loop dry-run 总结果。"""
    project: str
    run_id: str                         # 时间戳 + 短 UUID
    dry_run: bool                       # 始终 True
    max_tasks: int
    planned_tasks: list[str]            # task_id 列表
    completed_tasks: list[str]          # dry-run 中模拟为全部 planned
    failed_tasks: list[str]             # 始终空
    skipped_tasks: list[str]            # 始终空
    current_task: str | None            # 最后一个 planned task
    next_task: str | None               # 下一个未 planned 的 pending task
    loop_status: str                    # dry_run_completed / stopped_on_max_tasks / no_pending_task / invalid_max_tasks
    stop_reason: str | None
    human_review_required: bool
    task_results: list[TaskRunResult]
    next_action: str
    message: str


# ---------------------------------------------------------------------------
# T060: Loop Dry-Run 核心函数
# ---------------------------------------------------------------------------

def _generate_run_id() -> str:
    """生成唯一 run_id：loop-YYYYMMDD-HHMMSS-<短UUID>。"""
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    short = uuid.uuid4().hex[:6]
    return f"loop-{ts}-{short}"


def run_project_loop_dry_run(
    project_root: str | Path,
    max_tasks: int = MAX_TASKS_DEFAULT,
) -> ContinuousLoopRunResult:
    """模拟连续任务推进（dry-run）。

    复用 build_continuous_task_plan() 读取任务列表和生成计划。
    为每个 planned task 生成模拟 TaskRunResult。
    不执行任何任务，不调用 Claude Code，不修改业务代码。

    Args:
        project_root: 项目根目录（包含 docs/tasks.md）
        max_tasks: 一次最多推进任务数

    Returns:
        ContinuousLoopRunResult
    """
    project_root = Path(project_root)
    run_id = _generate_run_id()

    # 1. 调用 planner 获取计划
    plan = build_continuous_task_plan(
        project_root=project_root,
        max_tasks=max_tasks,
        dry_run=True,
    )

    # 2. 如果 plan_status 不是 planned，返回停止状态
    if plan.plan_status != "planned":
        return ContinuousLoopRunResult(
            project=str(project_root),
            run_id=run_id,
            dry_run=True,
            max_tasks=plan.max_tasks,
            planned_tasks=[],
            completed_tasks=[],
            failed_tasks=[],
            skipped_tasks=[],
            current_task=None,
            next_task=None,
            loop_status=plan.plan_status,
            stop_reason=plan.stop_reason,
            human_review_required=False,
            task_results=[],
            next_action="fix_parameters_or_check_tasks",
            message=plan.message,
        )

    # 3. 遍历 planned_tasks，为每个生成 TaskRunResult
    task_results: list[TaskRunResult] = []
    completed_ids: list[str] = []
    total_planned = len(plan.planned_tasks)

    for i, pt in enumerate(plan.planned_tasks, 1):
        is_last = (i == total_planned)

        # 判断 stop_reason 和 next_action
        if is_last and total_planned >= plan.max_tasks:
            # 达到 max_tasks 上限
            task_stop = "max_tasks_reached"
            task_next = "review_loop_summary"
        elif is_last:
            # 最后一个但没到上限（所有 pending 都 planned 了）
            task_stop = None
            task_next = "review_loop_summary"
        else:
            task_stop = None
            task_next = "continue_to_next_planned_task"

        result = TaskRunResult(
            task_id=pt.task_id,
            title=pt.title,
            dry_run=True,
            execution_performed=False,
            check_result="pass",
            task_status="dry_run_planned",
            stop_reason=task_stop,
            next_action=task_next,
            message=f"[dry-run] 模拟执行 {pt.task_id}（{pt.title}），"
                    f"顺序 {pt.order}/{total_planned}",
        )
        task_results.append(result)
        completed_ids.append(pt.task_id)

    # 4. 确定 loop 级别的 stop_reason 和 next_action
    last_result = task_results[-1]
    last_task_id = plan.planned_tasks[-1].task_id
    next_task_id = last_result.task_id  # 默认无 next

    # 检查是否还有更多 pending task（不在 planned 中的）
    tasks_file = project_root / "docs" / "tasks.md"
    content = load_tasks_file(tasks_file)
    tasks = parse_tasks(content)
    pending_ids = [t["id"] for t in tasks if t["status"] == "pending"]
    unplanned_pending = [tid for tid in pending_ids if tid not in completed_ids]
    next_task_id = unplanned_pending[0] if unplanned_pending else None

    if last_result.stop_reason == "max_tasks_reached":
        loop_status = "stopped_on_max_tasks"
        stop_reason = "max_tasks_reached"
        next_action = "review_loop_summary"
    elif next_task_id is None:
        loop_status = "dry_run_completed"
        stop_reason = "all_planned_tasks_simulated"
        next_action = "review_loop_summary"
    else:
        loop_status = "dry_run_completed"
        stop_reason = None
        next_action = "review_loop_summary"

    return ContinuousLoopRunResult(
        project=str(project_root),
        run_id=run_id,
        dry_run=True,
        max_tasks=plan.max_tasks,
        planned_tasks=completed_ids,
        completed_tasks=completed_ids,
        failed_tasks=[],
        skipped_tasks=[],
        current_task=last_task_id,
        next_task=next_task_id,
        loop_status=loop_status,
        stop_reason=stop_reason,
        human_review_required=False,
        task_results=task_results,
        next_action=next_action,
        message=(
            f"[dry-run] 模拟推进 {len(completed_ids)} 个任务，"
            f"未执行任何真实任务。"
        ),
    )
