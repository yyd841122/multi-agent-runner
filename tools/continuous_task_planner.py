"""Continuous Task Planner — 连续任务自动推进计划生成与 loop dry-run。

严格遵循 docs/continuous-task-auto-advance-design.md 协议。
T059 实现 dry-run 计划生成，T060 实现 loop dry-run 模拟推进。
T065 实现 execute mode safety gate（确认协议、前置检查、execute 硬限制）。
不执行任务，不调用 Claude Code。
"""

from __future__ import annotations

import re
import subprocess
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

EXECUTE_HARD_LIMIT = 3
EXECUTE_CONFIRM_PHRASE = "EXECUTE_PROJECT_LOOP"

REAL_CALL_CONFIRM_PHRASE = "EXECUTE_REAL_TASK_ONCE"


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


# ---------------------------------------------------------------------------
# T065: Execute Mode Safety Gate
# ---------------------------------------------------------------------------

@dataclass
class ExecuteLoopSafetyResult:
    """Execute mode safety gate 检查结果。

    不执行任何真实任务，只做前置校验。
    """

    project: str
    run_id: str
    execute_requested: bool
    confirm_status: str               # "accepted" / "missing" / "rejected"
    confirm_phrase: str | None        # 用户传入的 confirm 值
    max_tasks: int
    execute_hard_limit: int           # EXECUTE_HARD_LIMIT = 3
    planned_tasks: list[str]          # 计划执行的任务 ID 列表
    workspace_status: str             # "clean" / "dirty"
    preflight_status: str             # "passed" / "failed"
    execute_allowed: bool             # 全部检查通过才为 True
    task_execution_performed: bool    # 始终 False（safety gate 不执行任务）
    claude_code_called: bool          # 始终 False
    business_code_changed: bool       # 始终 False
    human_review_required: bool       # safety gate 不修改此值
    stop_reason: str | None           # 拒绝原因
    next_action: str                  # 建议下一步
    message: str                      # 详细消息


def _check_workspace_clean(project_root: Path) -> bool:
    """检查工作区是否 clean。"""
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True,
            text=True,
            cwd=str(project_root),
        )
        return result.stdout.strip() == ""
    except Exception:
        return False


def _check_no_in_progress_tasks(project_root: Path) -> bool:
    """检查是否有 in_progress 任务。"""
    tasks_file = project_root / "docs" / "tasks.md"
    if not tasks_file.exists():
        return True
    content = load_tasks_file(tasks_file)
    tasks = parse_tasks(content)
    return all(t["status"] != "in_progress" for t in tasks)


def _check_no_pending_rework(project_root: Path) -> bool:
    """检查是否有待处理的 rework prompt。"""
    reports_dir = project_root / "reports"
    if not reports_dir.exists():
        return True
    for f in reports_dir.rglob("*rework*prompt*"):
        return False
    return True


def validate_execute_loop_safety(
    project_root: str | Path,
    max_tasks: int,
    confirm: str | None,
) -> ExecuteLoopSafetyResult:
    """Execute mode safety gate 校验。

    检查确认短语、max_tasks、工作区、planned_tasks 等。
    不执行任何任务，不调用 Claude Code，不修改业务代码。

    Args:
        project_root: 项目根目录
        max_tasks: 用户请求的 max_tasks
        confirm: 用户传入的 --confirm 值

    Returns:
        ExecuteLoopSafetyResult
    """
    project_root = Path(project_root)
    run_id = _generate_run_id()

    # --- 1. 确认短语检查 ---
    if confirm is None:
        return ExecuteLoopSafetyResult(
            project=str(project_root),
            run_id=run_id,
            execute_requested=True,
            confirm_status="missing",
            confirm_phrase=None,
            max_tasks=max_tasks,
            execute_hard_limit=EXECUTE_HARD_LIMIT,
            planned_tasks=[],
            workspace_status="unknown",
            preflight_status="failed",
            execute_allowed=False,
            task_execution_performed=False,
            claude_code_called=False,
            business_code_changed=False,
            human_review_required=False,
            stop_reason="confirm_missing",
            next_action="provide_confirm_phrase",
            message=(
                "错误：缺少 --confirm 参数。"
                f"必须使用 --confirm {EXECUTE_CONFIRM_PHRASE}"
            ),
        )

    if confirm != EXECUTE_CONFIRM_PHRASE:
        return ExecuteLoopSafetyResult(
            project=str(project_root),
            run_id=run_id,
            execute_requested=True,
            confirm_status="rejected",
            confirm_phrase=confirm,
            max_tasks=max_tasks,
            execute_hard_limit=EXECUTE_HARD_LIMIT,
            planned_tasks=[],
            workspace_status="unknown",
            preflight_status="failed",
            execute_allowed=False,
            task_execution_performed=False,
            claude_code_called=False,
            business_code_changed=False,
            human_review_required=False,
            stop_reason="confirm_rejected",
            next_action="provide_correct_confirm_phrase",
            message=(
                f"错误：确认短语 '{confirm}' 不合法。"
                f"必须精确使用 --confirm {EXECUTE_CONFIRM_PHRASE}"
            ),
        )

    # --- 2. max_tasks 检查（execute mode 独立限制） ---
    if max_tasks < 1:
        return ExecuteLoopSafetyResult(
            project=str(project_root),
            run_id=run_id,
            execute_requested=True,
            confirm_status="accepted",
            confirm_phrase=confirm,
            max_tasks=max_tasks,
            execute_hard_limit=EXECUTE_HARD_LIMIT,
            planned_tasks=[],
            workspace_status="unknown",
            preflight_status="failed",
            execute_allowed=False,
            task_execution_performed=False,
            claude_code_called=False,
            business_code_changed=False,
            human_review_required=False,
            stop_reason="invalid_max_tasks",
            next_action="fix_max_tasks",
            message=(
                f"错误：max_tasks={max_tasks} 无效，execute mode 要求 1 <= max_tasks <= {EXECUTE_HARD_LIMIT}。"
            ),
        )

    if max_tasks > EXECUTE_HARD_LIMIT:
        return ExecuteLoopSafetyResult(
            project=str(project_root),
            run_id=run_id,
            execute_requested=True,
            confirm_status="accepted",
            confirm_phrase=confirm,
            max_tasks=max_tasks,
            execute_hard_limit=EXECUTE_HARD_LIMIT,
            planned_tasks=[],
            workspace_status="unknown",
            preflight_status="failed",
            execute_allowed=False,
            task_execution_performed=False,
            claude_code_called=False,
            business_code_changed=False,
            human_review_required=False,
            stop_reason="execute_max_tasks_exceeded",
            next_action="reduce_max_tasks",
            message=(
                f"错误：max_tasks={max_tasks} 超过 execute mode 硬限制 {EXECUTE_HARD_LIMIT}。"
                f"execute mode 最大允许 {EXECUTE_HARD_LIMIT} 个任务。"
            ),
        )

    # --- 3. 工作区检查 ---
    workspace_clean = _check_workspace_clean(project_root)
    workspace_status = "clean" if workspace_clean else "dirty"

    if not workspace_clean:
        return ExecuteLoopSafetyResult(
            project=str(project_root),
            run_id=run_id,
            execute_requested=True,
            confirm_status="accepted",
            confirm_phrase=confirm,
            max_tasks=max_tasks,
            execute_hard_limit=EXECUTE_HARD_LIMIT,
            planned_tasks=[],
            workspace_status="dirty",
            preflight_status="failed",
            execute_allowed=False,
            task_execution_performed=False,
            claude_code_called=False,
            business_code_changed=False,
            human_review_required=False,
            stop_reason="initial_worktree_dirty",
            next_action="commit_or_stash_changes",
            message="错误：工作区不 clean，请先提交或 stash 变更。",
        )

    # --- 4. 检查无 in_progress 任务 ---
    no_in_progress = _check_no_in_progress_tasks(project_root)
    if not no_in_progress:
        return ExecuteLoopSafetyResult(
            project=str(project_root),
            run_id=run_id,
            execute_requested=True,
            confirm_status="accepted",
            confirm_phrase=confirm,
            max_tasks=max_tasks,
            execute_hard_limit=EXECUTE_HARD_LIMIT,
            planned_tasks=[],
            workspace_status="clean",
            preflight_status="failed",
            execute_allowed=False,
            task_execution_performed=False,
            claude_code_called=False,
            business_code_changed=False,
            human_review_required=False,
            stop_reason="existing_in_progress",
            next_action="resolve_in_progress_task",
            message="错误：存在 in_progress 任务，请先处理后再执行 execute mode。",
        )

    # --- 5. 检查无 pending rework ---
    no_rework = _check_no_pending_rework(project_root)
    if not no_rework:
        return ExecuteLoopSafetyResult(
            project=str(project_root),
            run_id=run_id,
            execute_requested=True,
            confirm_status="accepted",
            confirm_phrase=confirm,
            max_tasks=max_tasks,
            execute_hard_limit=EXECUTE_HARD_LIMIT,
            planned_tasks=[],
            workspace_status="clean",
            preflight_status="failed",
            execute_allowed=False,
            task_execution_performed=False,
            claude_code_called=False,
            business_code_changed=False,
            human_review_required=False,
            stop_reason="pending_rework_exists",
            next_action="resolve_rework_first",
            message="错误：存在待处理的 rework prompt，请先处理返工。",
        )

    # --- 6. 生成计划并检查 planned_tasks ---
    plan = build_continuous_task_plan(
        project_root=project_root,
        max_tasks=max_tasks,
        dry_run=True,
    )

    if plan.plan_status != "planned" or not plan.planned_tasks:
        return ExecuteLoopSafetyResult(
            project=str(project_root),
            run_id=run_id,
            execute_requested=True,
            confirm_status="accepted",
            confirm_phrase=confirm,
            max_tasks=max_tasks,
            execute_hard_limit=EXECUTE_HARD_LIMIT,
            planned_tasks=[],
            workspace_status="clean",
            preflight_status="failed",
            execute_allowed=False,
            task_execution_performed=False,
            claude_code_called=False,
            business_code_changed=False,
            human_review_required=False,
            stop_reason="no_pending_tasks",
            next_action="check_tasks_or_add_new",
            message="错误：没有可执行的 pending 任务。",
        )

    planned_ids = [t.task_id for t in plan.planned_tasks]

    # --- 全部检查通过 ---
    return ExecuteLoopSafetyResult(
        project=str(project_root),
        run_id=run_id,
        execute_requested=True,
        confirm_status="accepted",
        confirm_phrase=confirm,
        max_tasks=max_tasks,
        execute_hard_limit=EXECUTE_HARD_LIMIT,
        planned_tasks=planned_ids,
        workspace_status="clean",
        preflight_status="passed",
        execute_allowed=True,
        task_execution_performed=False,
        claude_code_called=False,
        business_code_changed=False,
        human_review_required=False,
        stop_reason=None,
        next_action="ready_for_T066_execute_stub",
        message=(
            f"safety gate 通过：确认短语正确，max_tasks={max_tasks}，"
            f"工作区 clean，{len(planned_ids)} 个 pending 任务可执行。"
            f"TASK_EXECUTION_PERFORMED=false（safety gate 不执行任务）。"
        ),
    )


# ---------------------------------------------------------------------------
# T066: Execute Stub（max_tasks=1）
# ---------------------------------------------------------------------------

@dataclass
class ExecuteLoopStubResult:
    """Execute stub 结果（max_tasks=1 stub only）。

    safety gate 通过后，只模拟识别第一个 planned task，
    不调用 run-project-task-full，不调用 Claude Code，不修改业务代码。
    """

    project: str
    run_id: str
    execute_mode: str                       # "execute"
    execute_allowed: bool                   # safety gate 是否通过
    execute_stub_started: bool              # stub 是否启动
    max_tasks: int
    planned_tasks: list[str]                # safety gate 通过时的 planned task ID 列表
    stub_task: str | None                   # 第一个 planned task（stub 模拟目标）
    completed_tasks: list[str]              # stub 模拟完成的任务（不等于真实完成）
    failed_tasks: list[str]                 # 始终空
    skipped_tasks: list[str]               # 始终空
    task_execution_performed: bool          # 始终 False
    claude_code_called: bool                # 始终 False
    business_code_changed: bool             # 始终 False
    loop_status: str                        # execute_stub_completed / safety_gate_failed / max_tasks_gt_1_not_supported
    stop_reason: str | None                 # 停止原因
    human_review_required: bool             # 始终 False
    next_action: str                        # 建议下一步
    message: str                            # 详细消息


def run_project_loop_execute_stub(
    project_root: str | Path,
    max_tasks: int = 1,
    confirm: str | None = None,
) -> ExecuteLoopStubResult:
    """Execute stub：safety gate 通过后模拟 max_tasks=1 的 execute。

    只识别 planned_tasks 中的第一个任务作为 stub_task，
    不调用 run-project-task-full，不调用 Claude Code，不修改业务代码。

    Args:
        project_root: 项目根目录
        max_tasks: 用户请求的 max_tasks（stub 只支持 1）
        confirm: 用户传入的 --confirm 值

    Returns:
        ExecuteLoopStubResult
    """
    project_root = Path(project_root)
    run_id = _generate_run_id()

    # 1. 调用 safety gate
    safety = validate_execute_loop_safety(
        project_root=project_root,
        max_tasks=max_tasks,
        confirm=confirm,
    )

    # 2. safety gate 不通过 → 返回 stub 结果，标记未启动
    if not safety.execute_allowed:
        return ExecuteLoopStubResult(
            project=str(project_root),
            run_id=run_id,
            execute_mode="execute",
            execute_allowed=False,
            execute_stub_started=False,
            max_tasks=max_tasks,
            planned_tasks=[],
            stub_task=None,
            completed_tasks=[],
            failed_tasks=[],
            skipped_tasks=[],
            task_execution_performed=False,
            claude_code_called=False,
            business_code_changed=False,
            loop_status="safety_gate_failed",
            stop_reason=safety.stop_reason,
            human_review_required=False,
            next_action=safety.next_action,
            message=f"execute stub 未启动：safety gate 拒绝（{safety.stop_reason}）。",
        )

    # 3. safety gate 通过但 max_tasks != 1 → 拒绝（T066 只支持 max_tasks=1）
    if max_tasks != 1:
        return ExecuteLoopStubResult(
            project=str(project_root),
            run_id=run_id,
            execute_mode="execute",
            execute_allowed=True,
            execute_stub_started=False,
            max_tasks=max_tasks,
            planned_tasks=safety.planned_tasks,
            stub_task=None,
            completed_tasks=[],
            failed_tasks=[],
            skipped_tasks=[],
            task_execution_performed=False,
            claude_code_called=False,
            business_code_changed=False,
            loop_status="max_tasks_gt_1_not_supported",
            stop_reason="max_tasks_gt_1_not_supported_in_stub",
            human_review_required=False,
            next_action="use_max_tasks_1_for_stub",
            message=(
                f"execute stub 当前只支持 max_tasks=1，"
                f"请求的 max_tasks={max_tasks}。"
                f"请使用 --max-tasks 1。"
            ),
        )

    # 4. safety gate 通过且 max_tasks=1 → 启动 stub
    stub_task = safety.planned_tasks[0] if safety.planned_tasks else None

    return ExecuteLoopStubResult(
        project=str(project_root),
        run_id=run_id,
        execute_mode="execute",
        execute_allowed=True,
        execute_stub_started=True,
        max_tasks=1,
        planned_tasks=safety.planned_tasks,
        stub_task=stub_task,
        completed_tasks=[stub_task] if stub_task else [],  # 模拟完成
        failed_tasks=[],
        skipped_tasks=[],
        task_execution_performed=False,        # 不执行真实任务
        claude_code_called=False,              # 不调用 Claude Code
        business_code_changed=False,           # 不修改业务代码
        loop_status="execute_stub_completed",
        stop_reason="execute_stub_only",
        human_review_required=False,
        next_action="ready_for_T067_validation",
        message=(
            f"execute stub 完成：模拟执行 {stub_task}，"
            f"未调用 run-project-task-full，未调用 Claude Code，未修改业务代码。"
            f"TASK_EXECUTION_PERFORMED=false。"
        ),
    )


# ---------------------------------------------------------------------------
# T071: Task Execution Adapter Dry-Run
# ---------------------------------------------------------------------------

@dataclass
class TaskExecutionResult:
    """单任务执行 adapter 结果（dry-run）。

    构造未来调用 run-project-task-full 的命令信息，
    不执行命令，不调用 Claude Code，不修改业务代码。
    """

    task_id: str
    command: str                           # 未来要执行的命令描述
    adapter_mode: str                      # "dry_run" / "real"
    execution_started: bool                # dry-run 下始终 False
    execution_finished: bool               # dry-run 下始终 False
    exit_code: str | None                  # dry-run 下为 None
    check_result: str                      # "pass" / "fail"
    task_status: str                       # "adapter_dry_run_ready" 等
    report_paths: list[str]                # dry-run 下为空
    workspace_status: str                  # "not_checked"
    business_code_changed: bool            # 始终 False
    rework_required: bool                  # 始终 False
    human_review_required: bool            # 始终 True（dry-run 需人工确认）
    next_action: str                       # 建议下一步
    message: str                           # 详细消息


@dataclass
class ProjectLoopExecutionResult:
    """run-project-loop task execution adapter dry-run 总结果。

    不执行任何真实任务，不调用 run-project-task-full，
    不调用 Claude Code，不修改业务代码。
    """

    run_id: str
    project: str
    execution_mode: str                    # "task_execution_adapter_dry_run"
    max_tasks: int
    started_task: str | None               # adapter 锁定的任务 ID
    completed_tasks: list[str]             # 始终空
    failed_tasks: list[str]                # 始终空
    stopped_task: str | None               # 停止的任务
    task_results: list[TaskExecutionResult]  # adapter dry-run 结果
    loop_status: str                       # adapter_dry_run_completed / safety_gate_failed / ...
    stop_reason: str | None                # 停止原因
    workspace_status: str                  # "not_checked"
    git_backup_required: bool              # 始终 False
    human_review_required: bool            # 始终 True
    task_execution_performed: bool         # 始终 False
    run_project_task_full_called: bool     # 始终 False
    claude_code_called: str                # "no"
    business_code_changed: str             # "no"
    next_action: str                       # 建议下一步
    message: str                           # 详细消息


def prepare_run_project_task_full_adapter_dry_run(
    project_path: str | Path,
    task_id: str,
) -> TaskExecutionResult:
    """构造未来调用 run-project-task-full 的 adapter dry-run。

    不执行命令，不调用 Claude Code，不修改业务代码。
    只构造未来调用信息。

    Args:
        project_path: 子项目路径
        task_id: 任务 ID

    Returns:
        TaskExecutionResult（dry-run）
    """
    project_path = Path(project_path)

    command = (
        f"run_project_task_full("
        f"project_path='{project_path}', "
        f"task_id='{task_id}')"
    )
    cli_command = (
        f"python runner.py run-project-task-full "
        f"--project {project_path} --task {task_id}"
    )

    return TaskExecutionResult(
        task_id=task_id,
        command=command,
        adapter_mode="dry_run",
        execution_started=False,
        execution_finished=False,
        exit_code=None,
        check_result="pass",
        task_status="adapter_dry_run_ready",
        report_paths=[],
        workspace_status="not_checked",
        business_code_changed=False,
        rework_required=False,
        human_review_required=True,
        next_action="ready_for_T072_adapter_validation",
        message=(
            f"[adapter dry-run] 已构造未来调用：{cli_command}。"
            f"未调用 run-project-task-full，未调用 Claude Code，未修改业务代码。"
            f"TASK_EXECUTION_PERFORMED=false。"
        ),
    )


def run_project_loop_task_execution_adapter_dry_run(
    project_root: str | Path,
    max_tasks: int = 1,
    confirm: str | None = None,
) -> ProjectLoopExecutionResult:
    """Task execution adapter dry-run。

    复用 safety gate 验证确认和前置条件，
    构造未来调用 run-project-task-full 的 adapter 信息。
    不执行任何真实任务。

    Args:
        project_root: 项目根目录
        max_tasks: 用户请求的 max_tasks（adapter 只支持 1）
        confirm: 用户传入的 --confirm 值

    Returns:
        ProjectLoopExecutionResult（adapter dry-run）
    """
    project_root = Path(project_root)
    run_id = _generate_run_id()

    # 1. 调用 safety gate
    safety = validate_execute_loop_safety(
        project_root=project_root,
        max_tasks=max_tasks,
        confirm=confirm,
    )

    # 2. safety gate 不通过 → 返回失败结果
    if not safety.execute_allowed:
        return ProjectLoopExecutionResult(
            run_id=run_id,
            project=str(project_root),
            execution_mode="task_execution_adapter_dry_run",
            max_tasks=max_tasks,
            started_task=None,
            completed_tasks=[],
            failed_tasks=[],
            stopped_task=None,
            task_results=[],
            loop_status="safety_gate_failed",
            stop_reason=safety.stop_reason,
            workspace_status="not_checked",
            git_backup_required=False,
            human_review_required=True,
            task_execution_performed=False,
            run_project_task_full_called=False,
            claude_code_called="no",
            business_code_changed="no",
            next_action="fix_adapter_preconditions",
            message=(
                f"adapter dry-run 未通过：safety gate 拒绝（{safety.stop_reason}）。"
                f"TASK_EXECUTION_PERFORMED=false。"
            ),
        )

    # 3. safety gate 通过但 max_tasks != 1 → 拒绝
    if max_tasks != 1:
        return ProjectLoopExecutionResult(
            run_id=run_id,
            project=str(project_root),
            execution_mode="task_execution_adapter_dry_run",
            max_tasks=max_tasks,
            started_task=None,
            completed_tasks=[],
            failed_tasks=[],
            stopped_task=None,
            task_results=[],
            loop_status="max_tasks_gt_1_not_supported",
            stop_reason="max_tasks_gt_1_not_supported_in_adapter",
            workspace_status="not_checked",
            git_backup_required=False,
            human_review_required=True,
            task_execution_performed=False,
            run_project_task_full_called=False,
            claude_code_called="no",
            business_code_changed="no",
            next_action="use_max_tasks_1_for_adapter",
            message=(
                f"adapter dry-run 当前只支持 max_tasks=1，"
                f"请求的 max_tasks={max_tasks}。"
                f"请使用 --max-tasks 1。"
            ),
        )

    # 4. safety gate 通过且 max_tasks=1 → 构造 adapter dry-run
    task_id = safety.planned_tasks[0] if safety.planned_tasks else None

    if task_id is None:
        return ProjectLoopExecutionResult(
            run_id=run_id,
            project=str(project_root),
            execution_mode="task_execution_adapter_dry_run",
            max_tasks=max_tasks,
            started_task=None,
            completed_tasks=[],
            failed_tasks=[],
            stopped_task=None,
            task_results=[],
            loop_status="safety_gate_failed",
            stop_reason="no_planned_task",
            workspace_status="not_checked",
            git_backup_required=False,
            human_review_required=True,
            task_execution_performed=False,
            run_project_task_full_called=False,
            claude_code_called="no",
            business_code_changed="no",
            next_action="check_tasks_or_add_new",
            message="adapter dry-run：safety gate 通过但 planned_tasks 为空。",
        )

    # 5. 确定 project_path（子项目路径）
    #    当前项目结构：project_root 下有 projects/<subproject>
    #    从 tasks.md 的任务 ID 前缀判断子项目
    subproject_path = _resolve_subproject_path(project_root, task_id)

    # 6. 构造 adapter dry-run
    task_result = prepare_run_project_task_full_adapter_dry_run(
        project_path=subproject_path,
        task_id=task_id,
    )

    return ProjectLoopExecutionResult(
        run_id=run_id,
        project=str(project_root),
        execution_mode="task_execution_adapter_dry_run",
        max_tasks=1,
        started_task=task_id,
        completed_tasks=[],
        failed_tasks=[],
        stopped_task=task_id,
        task_results=[task_result],
        loop_status="adapter_dry_run_completed",
        stop_reason="adapter_dry_run_only",
        workspace_status="not_checked",
        git_backup_required=False,
        human_review_required=True,
        task_execution_performed=False,
        run_project_task_full_called=False,
        claude_code_called="no",
        business_code_changed="no",
        next_action="ready_for_T072_adapter_validation",
        message=(
            f"adapter dry-run 完成：已构造未来调用 run-project-task-full "
            f"执行 {task_id}。"
            f"TASK_EXECUTION_PERFORMED=false，"
            f"RUN_PROJECT_TASK_FULL_CALLED=false。"
        ),
    )


# ---------------------------------------------------------------------------
# T073: Real-Call Stub（max_tasks=1）
# ---------------------------------------------------------------------------

@dataclass
class RealCallStubResult:
    """Real-call stub 结果（max_tasks=1 stub only）。

    通过 execute safety gate，解析 planned first task，
    构造 run-project-task-full 调用信息，但不真实执行。
    不调用 run-project-task-full，不调用 Claude Code，不修改业务代码。
    """

    project: str
    run_id: str
    execution_mode: str                       # "real_call_stub"
    real_call_requested: bool                 # 始终 True（--real-call-stub 触发）
    real_call_stub_started: bool              # stub 是否启动
    max_tasks: int
    planned_tasks: list[str]                  # safety gate 通过时的 planned task ID 列表
    task_id: str | None                       # 第一个 planned task（stub 目标）
    command: str                              # 未来要执行的命令描述
    preflight_status: str                     # "passed" / "failed"
    task_execution_performed: bool            # 始终 False
    run_project_task_full_called: bool        # 始终 False
    claude_code_called: str                   # "no"
    business_code_changed: str                # "no"
    exit_code: str                            # "not_executed"
    check_result: str                         # "pass" / "fail"
    task_status: str                          # "real_call_stub_ready" 等
    loop_status: str                          # real_call_stub_completed / safety_gate_failed / ...
    stop_reason: str | None                   # 停止原因
    human_review_required: bool               # 始终 True
    next_action: str                          # 建议下一步
    message: str                              # 详细消息


def run_project_loop_real_call_stub(
    project_root: str | Path,
    max_tasks: int = 1,
    confirm: str | None = None,
) -> RealCallStubResult:
    """Real-call stub：safety gate 通过后构造真实调用信息，但不执行。

    复用 safety gate 验证确认和前置条件，
    只允许 max_tasks=1，
    解析 planned first task，
    构造 run-project-task-full 调用信息。
    不执行该调用，不调用 Claude Code，不修改业务代码。

    Args:
        project_root: 项目根目录
        max_tasks: 用户请求的 max_tasks（stub 只支持 1）
        confirm: 用户传入的 --confirm 值

    Returns:
        RealCallStubResult
    """
    project_root = Path(project_root)
    run_id = _generate_run_id()

    # 默认失败结果
    def _fail_result(
        preflight: str = "failed",
        loop_status: str = "safety_gate_failed",
        stop_reason: str | None = None,
        next_action: str = "fix_real_call_preconditions",
        message: str = "",
    ) -> RealCallStubResult:
        return RealCallStubResult(
            project=str(project_root),
            run_id=run_id,
            execution_mode="real_call_stub",
            real_call_requested=True,
            real_call_stub_started=False,
            max_tasks=max_tasks,
            planned_tasks=[],
            task_id=None,
            command="",
            preflight_status=preflight,
            task_execution_performed=False,
            run_project_task_full_called=False,
            claude_code_called="no",
            business_code_changed="no",
            exit_code="not_executed",
            check_result="fail",
            task_status="real_call_stub_not_started",
            loop_status=loop_status,
            stop_reason=stop_reason,
            human_review_required=True,
            next_action=next_action,
            message=message,
        )

    # 1. 调用 safety gate
    safety = validate_execute_loop_safety(
        project_root=project_root,
        max_tasks=max_tasks,
        confirm=confirm,
    )

    # 2. safety gate 不通过 → 返回失败结果
    if not safety.execute_allowed:
        return _fail_result(
            loop_status="safety_gate_failed",
            stop_reason=safety.stop_reason,
            next_action="fix_real_call_preconditions",
            message=(
                f"real-call stub 未启动：safety gate 拒绝（{safety.stop_reason}）。"
                f"TASK_EXECUTION_PERFORMED=false。"
            ),
        )

    # 3. safety gate 通过但 max_tasks != 1 → 拒绝
    if max_tasks != 1:
        return _fail_result(
            preflight="passed",
            loop_status="max_tasks_gt_1_not_supported",
            stop_reason="max_tasks_gt_1_not_supported_in_real_call_stub",
            next_action="use_max_tasks_1_for_real_call_stub",
            message=(
                f"real-call stub 当前只支持 max_tasks=1，"
                f"请求的 max_tasks={max_tasks}。"
                f"请使用 --max-tasks 1。"
            ),
        )

    # 4. safety gate 通过且 max_tasks=1 → 构造 real-call stub
    task_id = safety.planned_tasks[0] if safety.planned_tasks else None

    if task_id is None:
        return _fail_result(
            preflight="passed",
            loop_status="safety_gate_failed",
            stop_reason="no_planned_task",
            next_action="check_tasks_or_add_new",
            message="real-call stub：safety gate 通过但 planned_tasks 为空。",
        )

    # 5. 确定 subproject path
    subproject_path = _resolve_subproject_path(project_root, task_id)

    # 6. 构造未来调用命令
    command = (
        f"run_project_task_full("
        f"project_path='{subproject_path}', "
        f"task_id='{task_id}')"
    )

    return RealCallStubResult(
        project=str(project_root),
        run_id=run_id,
        execution_mode="real_call_stub",
        real_call_requested=True,
        real_call_stub_started=True,
        max_tasks=1,
        planned_tasks=safety.planned_tasks,
        task_id=task_id,
        command=command,
        preflight_status="passed",
        task_execution_performed=False,
        run_project_task_full_called=False,
        claude_code_called="no",
        business_code_changed="no",
        exit_code="not_executed",
        check_result="pass",
        task_status="real_call_stub_ready",
        loop_status="real_call_stub_completed",
        stop_reason="real_call_stub_only",
        human_review_required=True,
        next_action="ready_for_T074_check_result_pass_validation",
        message=(
            f"real-call stub 完成：已构造未来调用 run-project-task-full "
            f"执行 {task_id}，command={command}。"
            f"TASK_EXECUTION_PERFORMED=false，"
            f"RUN_PROJECT_TASK_FULL_CALLED=false。"
        ),
    )


# ---------------------------------------------------------------------------
# T079: Real-Call Dry-Run Executor（max_tasks=1）
# ---------------------------------------------------------------------------

@dataclass
class RealCallDryRunExecutorResult:
    """Real-call dry-run executor 结果（max_tasks=1）。

    通过 execute safety gate + real-call double-confirm safety gate 后，
    解析当前 planned task，构造未来真实调用 run-project-task-full 的
    execution plan，但不执行。
    不调用 run-project-task-full，不调用 Claude Code，不修改业务代码。
    """

    project: str
    run_id: str
    execution_mode: str                       # "real_call_dry_run_executor"
    real_call_allowed: bool                   # real-call safety gate 是否通过
    dry_run_executor_started: bool            # executor 是否启动
    max_tasks: int
    task_id: str | None                       # 当前 NEXT_PENDING
    command: str                              # 未来要执行的 CLI 命令
    function_call: str                        # 未来要执行的函数调用描述
    child_result_mode: str                    # "not_executed"
    simulated_exit_code: str                  # "not_executed"
    simulated_check_result: str               # "not_executed"
    simulated_task_status: str                # "dry_run_only"
    task_execution_performed: bool            # 始终 False
    run_project_task_full_called: bool        # 始终 False
    claude_code_called: str                   # "no"
    business_code_changed: str                # "no"（注意是 str 不是 bool）
    auto_continue_to_next_task: bool          # 始终 False
    auto_git_backup: bool                     # 始终 False
    human_review_required: bool               # 始终 True
    check_result: str                         # "pass" / "fail"
    stop_reason: str | None                   # 停止原因
    next_action: str                          # 建议下一步
    message: str                              # 详细消息


def run_project_loop_real_call_dry_run_executor(
    project_root: str | Path,
    max_tasks: int = 1,
    confirm: str | None = None,
    real_confirm: str | None = None,
) -> RealCallDryRunExecutorResult:
    """Real-call dry-run executor：safety gate 通过后构造 execution plan，但不执行。

    调用 validate_real_call_safety() 做双重确认校验。
    如果通过，解析 planned task，构造未来调用的 command 和 function_call，
    但不执行 command，不调用函数，不调用 Claude Code，不修改业务代码。

    Args:
        project_root: 项目根目录
        max_tasks: 用户请求的 max_tasks（dry-run executor 只支持 1）
        confirm: 第一重确认短语
        real_confirm: 第二重确认短语

    Returns:
        RealCallDryRunExecutorResult
    """
    project_root = Path(project_root)
    run_id = _generate_run_id()

    # --- 默认失败结果 ---
    def _fail(
        stop_reason: str | None = None,
        next_action: str = "fix_real_call_dry_run_preconditions",
        message: str = "",
    ) -> RealCallDryRunExecutorResult:
        return RealCallDryRunExecutorResult(
            project=str(project_root),
            run_id=run_id,
            execution_mode="real_call_dry_run_executor",
            real_call_allowed=False,
            dry_run_executor_started=False,
            max_tasks=max_tasks,
            task_id=None,
            command="",
            function_call="",
            child_result_mode="not_executed",
            simulated_exit_code="not_executed",
            simulated_check_result="not_executed",
            simulated_task_status="dry_run_not_started",
            task_execution_performed=False,
            run_project_task_full_called=False,
            claude_code_called="no",
            business_code_changed="no",
            auto_continue_to_next_task=False,
            auto_git_backup=False,
            human_review_required=True,
            check_result="fail",
            stop_reason=stop_reason,
            next_action=next_action,
            message=message,
        )

    # 1. 调用 real-call double-confirm safety gate
    safety = validate_real_call_safety(
        project_root=project_root,
        max_tasks=max_tasks,
        execute_requested=True,
        confirm=confirm,
        real_call_requested=True,
        real_confirm=real_confirm,
        adapter_dry_run=False,
        real_call_stub=False,
    )

    # 2. safety gate 不通过 → 返回失败结果
    if not safety.real_call_allowed:
        return _fail(
            stop_reason=safety.stop_reason,
            next_action=safety.next_action,
            message=(
                f"real-call dry-run executor 未启动：safety gate 拒绝"
                f"（{safety.stop_reason}）。"
                f"TASK_EXECUTION_PERFORMED=false。"
            ),
        )

    # 3. safety gate 通过 → 解析 planned task
    task_id = safety.task_id
    if task_id is None:
        return _fail(
            stop_reason="no_task_id",
            next_action="check_tasks_or_add_new",
            message="real-call dry-run executor：safety gate 通过但 task_id 为空。",
        )

    # 4. 解析 subproject path
    subproject_path = _resolve_subproject_path(project_root, task_id)

    # 5. 构造未来调用的 command 和 function_call（不执行）
    command = (
        f"python runner.py run-project-task-full "
        f"--project {subproject_path} --task {task_id}"
    )
    function_call = (
        f"run_project_task_full("
        f"project_path='{subproject_path}', "
        f"task_id='{task_id}')"
    )

    # 6. 返回 dry-run executor 结果
    return RealCallDryRunExecutorResult(
        project=str(project_root),
        run_id=run_id,
        execution_mode="real_call_dry_run_executor",
        real_call_allowed=True,
        dry_run_executor_started=True,
        max_tasks=1,
        task_id=task_id,
        command=command,
        function_call=function_call,
        child_result_mode="not_executed",
        simulated_exit_code="not_executed",
        simulated_check_result="not_executed",
        simulated_task_status="dry_run_only",
        task_execution_performed=False,
        run_project_task_full_called=False,
        claude_code_called="no",
        business_code_changed="no",
        auto_continue_to_next_task=False,
        auto_git_backup=False,
        human_review_required=True,
        check_result="pass",
        stop_reason="real_call_dry_run_only",
        next_action="ready_for_T080_real_confirm_rejection_validation",
        message=(
            f"real-call dry-run executor 完成：已构造未来调用 "
            f"run-project-task-full 执行 {task_id}，"
            f"command={command}。"
            f"TASK_EXECUTION_PERFORMED=false，"
            f"RUN_PROJECT_TASK_FULL_CALLED=false。"
        ),
    )


# ---------------------------------------------------------------------------
# T085: Real-Call Run-Once Safety Shell（max_tasks=1）
# ---------------------------------------------------------------------------

@dataclass
class RealCallRunOnceResult:
    """Real-call run-once safety shell 结果（max_tasks=1）。

    通过 execute safety gate + real-call double-confirm safety gate 后，
    解析当前 planned task，构造未来真实调用 run-project-task-full 的
    command / function_call，但不执行。
    不调用 run-project-task-full，不调用 Claude Code，不修改业务代码。
    """

    project: str
    run_id: str
    task_id: str | None                       # 当前 NEXT_PENDING
    execution_mode: str                       # "real_call_run_once_safety_shell"
    real_call_allowed: bool                   # real-call safety gate 是否通过
    run_once_requested: bool                  # 始终 True（--real-call-run-once 触发）
    run_once_safety_shell_started: bool       # safety shell 是否启动
    command: str                              # 未来要执行的 CLI 命令
    function_call: str                        # 未来要执行的函数调用描述
    preflight_status: str                     # "passed" / "failed"
    real_task_execution: str                  # "no"（safety shell 不执行）
    run_project_task_full_called: str         # "no"
    claude_code_called: str                   # "no"
    business_code_changed: str                # "no"
    child_exit_code: str                      # "not_executed"
    child_check_result: str                   # "not_executed"
    child_task_status: str                    # "not_executed"
    auto_continue_to_next_task: str           # "false"
    auto_git_backup: str                      # "false"
    human_review_required: str                # "true"
    check_result: str                         # "pass" / "fail"
    stop_reason: str | None                   # 停止原因
    next_action: str                          # 建议下一步
    message: str                              # 详细消息


def run_project_loop_real_call_run_once_safety_shell(
    project_root: str | Path,
    max_tasks: int = 1,
    confirm: str | None = None,
    real_confirm: str | None = None,
    real_call_dry_run: bool = False,
    adapter_dry_run: bool = False,
    real_call_stub: bool = False,
    dry_run_flag: bool = False,
) -> RealCallRunOnceResult:
    """Real-call run-once safety shell：构造未来真实调用信息，但不执行。

    调用 validate_real_call_safety() 做双重确认校验。
    如果通过，解析 planned task，构造未来调用的 command 和 function_call，
    但不执行 command，不调用函数，不调用 Claude Code，不修改业务代码。

    Args:
        project_root: 项目根目录
        max_tasks: 用户请求的 max_tasks（safety shell 只支持 1）
        confirm: 第一重确认短语
        real_confirm: 第二重确认短语
        real_call_dry_run: 是否同时传入了 --real-call-dry-run
        adapter_dry_run: 是否同时传入了 --adapter-dry-run
        real_call_stub: 是否同时传入了 --real-call-stub
        dry_run_flag: 是否同时传入了 --dry-run

    Returns:
        RealCallRunOnceResult
    """
    project_root = Path(project_root)
    run_id = _generate_run_id()

    # --- 默认失败结果 ---
    def _fail(
        stop_reason: str | None = None,
        next_action: str = "fix_real_call_run_once_preconditions",
        message: str = "",
    ) -> RealCallRunOnceResult:
        return RealCallRunOnceResult(
            project=str(project_root),
            run_id=run_id,
            task_id=None,
            execution_mode="real_call_run_once_safety_shell",
            real_call_allowed=False,
            run_once_requested=True,
            run_once_safety_shell_started=False,
            command="",
            function_call="",
            preflight_status="failed",
            real_task_execution="no",
            run_project_task_full_called="no",
            claude_code_called="no",
            business_code_changed="no",
            child_exit_code="not_executed",
            child_check_result="not_executed",
            child_task_status="not_executed",
            auto_continue_to_next_task="false",
            auto_git_backup="false",
            human_review_required="true",
            check_result="fail",
            stop_reason=stop_reason,
            next_action=next_action,
            message=message,
        )

    # --- 1. 模式互斥检查（在 safety gate 之前，更清晰的错误提示） ---
    if real_call_dry_run:
        return _fail(
            stop_reason="mode_conflict_real_call_dry_run",
            next_action="remove_real_call_dry_run",
            message=(
                "错误：--real-call-run-once 和 --real-call-dry-run 互斥，"
                "不能同时使用。"
            ),
        )

    if adapter_dry_run:
        return _fail(
            stop_reason="mode_conflict_adapter_dry_run",
            next_action="remove_adapter_dry_run",
            message=(
                "错误：--real-call-run-once 和 --adapter-dry-run 互斥，"
                "不能同时使用。"
            ),
        )

    if real_call_stub:
        return _fail(
            stop_reason="mode_conflict_real_call_stub",
            next_action="remove_real_call_stub",
            message=(
                "错误：--real-call-run-once 和 --real-call-stub 互斥，"
                "不能同时使用。"
            ),
        )

    if dry_run_flag:
        return _fail(
            stop_reason="mode_conflict_dry_run",
            next_action="remove_dry_run",
            message=(
                "错误：--real-call-run-once 和 --dry-run 互斥，"
                "不能同时使用。"
            ),
        )

    # --- 2. 调用 real-call double-confirm safety gate ---
    safety = validate_real_call_safety(
        project_root=project_root,
        max_tasks=max_tasks,
        execute_requested=True,
        confirm=confirm,
        real_call_requested=True,
        real_confirm=real_confirm,
        adapter_dry_run=False,
        real_call_stub=False,
    )

    # --- 3. safety gate 不通过 → 返回失败结果 ---
    if not safety.real_call_allowed:
        return _fail(
            stop_reason=safety.stop_reason,
            next_action=safety.next_action,
            message=(
                f"real-call run-once safety shell 未启动：safety gate 拒绝"
                f"（{safety.stop_reason}）。"
                f"REAL_TASK_EXECUTION=no。"
            ),
        )

    # --- 4. safety gate 通过 → 解析 planned task ---
    task_id = safety.task_id
    if task_id is None:
        return _fail(
            stop_reason="no_task_id",
            next_action="check_tasks_or_add_new",
            message="real-call run-once safety shell：safety gate 通过但 task_id 为空。",
        )

    # --- 5. 解析 subproject path ---
    subproject_path = _resolve_subproject_path(project_root, task_id)

    # --- 6. 构造未来调用的 command 和 function_call（不执行） ---
    command = (
        f"python runner.py run-project-task-full "
        f"--project {subproject_path} --task {task_id}"
    )
    function_call = (
        f"run_project_task_full("
        f"project_path='{subproject_path}', "
        f"task_id='{task_id}')"
    )

    # --- 7. 返回 safety shell 通过结果 ---
    return RealCallRunOnceResult(
        project=str(project_root),
        run_id=run_id,
        task_id=task_id,
        execution_mode="real_call_run_once_safety_shell",
        real_call_allowed=True,
        run_once_requested=True,
        run_once_safety_shell_started=True,
        command=command,
        function_call=function_call,
        preflight_status="passed",
        real_task_execution="no",
        run_project_task_full_called="no",
        claude_code_called="no",
        business_code_changed="no",
        child_exit_code="not_executed",
        child_check_result="not_executed",
        child_task_status="not_executed",
        auto_continue_to_next_task="false",
        auto_git_backup="false",
        human_review_required="true",
        check_result="pass",
        stop_reason="run_once_safety_shell_only",
        next_action="ready_for_T086_child_command_parser_dry_run",
        message=(
            f"real-call run-once safety shell 完成：已构造未来调用 "
            f"run-project-task-full 执行 {task_id}，"
            f"command={command}。"
            f"REAL_TASK_EXECUTION=no，"
            f"RUN_PROJECT_TASK_FULL_CALLED=no。"
        ),
    )


# ---------------------------------------------------------------------------
# T086: Workspace Helpers + Child Command Output Parser
# ---------------------------------------------------------------------------


def _snapshot_workspace(project_root: Path) -> set[str]:
    """快照当前 workspace 状态（git status --short 输出行集合）。

    Args:
        project_root: 项目根目录

    Returns:
        git status --short 输出行集合（每行一个文件状态）
    """
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True,
            text=True,
            cwd=str(project_root),
        )
        if result.stdout.strip():
            return set(result.stdout.strip().splitlines())
        return set()
    except Exception:
        return set()


def _classify_workspace_changes(
    before: set[str], after: set[str],
) -> tuple[str, list[str]]:
    """比较 workspace 前后快照，分类变更。

    Args:
        before: 执行前 git status --short 行集合
        after: 执行后 git status --short 行集合

    Returns:
        (classification, changed_files)
        classification: "clean" / "dirty_expected" / "dirty_unexpected" / "dirty_business_code"
    """
    new_files = after - before
    if not new_files:
        return "clean", []

    changed = sorted(new_files)

    # 剥离 git status 前缀（格式：XY filename，前 3 字符为状态标记）
    def _strip_git_prefix(f: str) -> str:
        return f[3:] if len(f) > 3 else f

    # 预期变更前缀
    expected_prefixes = ("reports/", "docs/tasks.md")
    unexpected = [
        f for f in changed
        if not any(_strip_git_prefix(f).startswith(p) for p in expected_prefixes)
    ]

    # 检查是否有业务代码变更
    business_extensions = (".html", ".css", ".js", ".py", ".yaml", ".json")
    business_files = [
        f for f in changed
        if any(_strip_git_prefix(f).endswith(ext) for ext in business_extensions)
        and not _strip_git_prefix(f).startswith(("reports/", "docs/"))
    ]

    if business_files:
        return "dirty_business_code", changed

    if unexpected:
        return "dirty_unexpected", changed

    return "dirty_expected", changed


def _infer_claude_code_called(
    steps: list[dict] | None,
    workspace_status: str,
) -> str:
    """推断 Claude Code 是否被调用。

    基于 steps 中是否有 Developer step 且 success，以及 workspace 变化推断。

    Args:
        steps: FullTaskStepResult 的字典列表（或 None）
        workspace_status: workspace 分类结果

    Returns:
        "yes" / "no" / "unknown"
    """
    if not steps:
        return "no"

    # 有 Developer step 且 success → 已调用
    for step in steps:
        name = step.get("name", "") if isinstance(step, dict) else getattr(step, "name", "")
        success = step.get("success", False) if isinstance(step, dict) else getattr(step, "success", False)
        if name == "Developer" and success:
            return "yes"

    # workspace 有变化 → unknown
    if workspace_status != "clean":
        return "unknown"

    return "unknown"


def _infer_business_code_changed(
    workspace_status: str,
    changed_files: list[str],
) -> str:
    """推断业务代码是否变更。

    Args:
        workspace_status: workspace 分类结果
        changed_files: 变更文件列表

    Returns:
        "yes" / "no" / "unknown"
    """
    if workspace_status == "clean":
        return "no"

    business_extensions = (".html", ".css", ".js", ".py", ".yaml", ".json")
    business_files = [
        f for f in changed_files
        if any(f.strip().endswith(ext) for ext in business_extensions)
        and not f.strip().startswith(("reports/", "docs/"))
    ]

    if business_files:
        return "yes"

    return "unknown"


# ---------------------------------------------------------------------------
# T086: Child Command Output Parser
# ---------------------------------------------------------------------------

# 需要解析的 KEY 列表
_PARSER_KNOWN_KEYS = frozenset({
    "TASK_ID",
    "CHECK_RESULT",
    "TASK_STATUS",
    "NEXT_PENDING",
    "REAL_TASK_EXECUTION",
    "CLAUDE_CODE_CALLED",
    "BUSINESS_CODE_CHANGED",
    "WORKTREE_STATUS",
    "REPORT_PATHS",
    "FINAL_STATUS",
    "FULL_LOOP_REPORT",
})

# 必需字段（缺失时 parse_check_result=fail）
_PARSER_REQUIRED_KEYS = frozenset({
    "CHECK_RESULT",
})


@dataclass
class ChildCommandParseResult:
    """子命令输出解析结果。

    解析 KEY=value 格式的 stdout，
    缺失字段按安全规则降级。
    不执行任何命令，不修改任何文件。
    """

    raw_stdout_present: bool               # stdout 是否非空
    raw_stderr_present: bool               # stderr 是否非空
    exit_code: int                         # 子命令退出码
    task_id: str                           # 解析的 task_id
    check_result: str                      # 解析的 CHECK_RESULT（pass/fail）
    task_status: str                       # 解析的 TASK_STATUS
    next_pending: str                      # 解析的 NEXT_PENDING
    real_task_execution: str               # 解析的 REAL_TASK_EXECUTION
    claude_code_called: str                # 解析的 CLAUDE_CODE_CALLED
    business_code_changed: str             # 解析的 BUSINESS_CODE_CHANGED
    worktree_status: str                   # 解析的 WORKTREE_STATUS
    report_paths: list[str]                # 解析的 REPORT_PATHS（逗号分隔 → list）
    missing_required_fields: list[str]     # 缺失的必需字段
    unknown_fields: list[str]              # 值为 unknown 的字段名列表
    parse_status: str                      # "parsed" / "parsed_with_missing_fields" / "parse_failed"
    parse_check_result: str                # "pass" / "fail"
    stop_reason: str | None                # 停止原因
    human_review_required: bool            # 是否需要人工审查
    message: str                           # 详细消息


def parse_child_command_output(
    stdout_text: str,
    stderr_text: str = "",
    exit_code: int = 0,
) -> ChildCommandParseResult:
    """解析子命令 KEY=value 格式输出。

    支持：
    - 多行 stdout
    - 忽略非 KEY=value 的普通日志行
    - 大小写保持的 key
    - REPORT_PATHS 逗号分隔为 list
    - 缺失字段按安全规则降级

    不执行任何命令，不修改任何文件。

    Args:
        stdout_text: 子命令 stdout 文本
        stderr_text: 子命令 stderr 文本
        exit_code: 子命令退出码

    Returns:
        ChildCommandParseResult
    """
    raw_stdout_present = bool(stdout_text and stdout_text.strip())
    raw_stderr_present = bool(stderr_text and stderr_text.strip())

    # --- 空 stdout 处理 ---
    if not raw_stdout_present:
        return ChildCommandParseResult(
            raw_stdout_present=False,
            raw_stderr_present=raw_stderr_present,
            exit_code=exit_code,
            task_id="",
            check_result="",
            task_status="unknown",
            next_pending="",
            real_task_execution="unknown",
            claude_code_called="unknown",
            business_code_changed="unknown",
            worktree_status="unknown",
            report_paths=[],
            missing_required_fields=["CHECK_RESULT"],
            unknown_fields=["TASK_STATUS", "CLAUDE_CODE_CALLED", "BUSINESS_CODE_CHANGED", "WORKTREE_STATUS"],
            parse_status="parse_failed",
            parse_check_result="fail",
            stop_reason="empty_stdout",
            human_review_required=True,
            message="解析失败：stdout 为空，无法解析任何字段。",
        )

    # --- 解析 KEY=value ---
    parsed: dict[str, str] = {}
    for line in stdout_text.strip().splitlines():
        line = line.strip()
        if "=" not in line:
            continue
        # 分割第一个 =
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if key and value and key in _PARSER_KNOWN_KEYS:
            parsed[key] = value

    # --- 收集缺失字段 ---
    missing_required: list[str] = []
    for req_key in _PARSER_REQUIRED_KEYS:
        if req_key not in parsed:
            missing_required.append(req_key)

    unknown_fields: list[str] = []
    for key in ("TASK_STATUS", "CLAUDE_CODE_CALLED", "BUSINESS_CODE_CHANGED", "WORKTREE_STATUS"):
        if key not in parsed:
            unknown_fields.append(key)

    # --- 确定 parse_status ---
    if missing_required:
        parse_status = "parse_failed"
        parse_check_result = "fail"
        stop_reason = f"missing_{missing_required[0].lower()}"
    elif unknown_fields:
        parse_status = "parsed_with_missing_fields"
        parse_check_result = "pass"
        stop_reason = None
    else:
        parse_status = "parsed"
        parse_check_result = "pass"
        stop_reason = None

    # --- 构建 check_result ---
    check_result = parsed.get("CHECK_RESULT", "")
    if not check_result and not missing_required:
        # CHECK_RESULT 在 parsed 中但值为空
        parse_check_result = "fail"
        stop_reason = "empty_check_result"

    # --- REPORT_PATHS 解析 ---
    report_paths_str = parsed.get("REPORT_PATHS", "")
    report_paths: list[str] = []
    if report_paths_str:
        report_paths = [p.strip() for p in report_paths_str.split(",") if p.strip()]

    # --- 组装消息 ---
    parts = []
    if parse_status == "parsed":
        parts.append("解析完成：所有必需字段和可选字段均已解析。")
    elif parse_status == "parsed_with_missing_fields":
        parts.append(f"解析完成（有缺失可选字段）：{', '.join(unknown_fields)}。")
    else:
        parts.append(f"解析失败：缺失必需字段 {', '.join(missing_required)}。")
    if exit_code != 0:
        parts.append(f"注意：exit_code={exit_code} 非 0，需要后续执行层处理。")
    parts.append(f"共解析 {len(parsed)} 个字段。")

    message = " ".join(parts)

    # --- 构建 check_result 语义 ---
    child_check_result = check_result if check_result else "unknown"

    return ChildCommandParseResult(
        raw_stdout_present=True,
        raw_stderr_present=raw_stderr_present,
        exit_code=exit_code,
        task_id=parsed.get("TASK_ID", ""),
        check_result=child_check_result,
        task_status=parsed.get("TASK_STATUS", "unknown"),
        next_pending=parsed.get("NEXT_PENDING", ""),
        real_task_execution=parsed.get("REAL_TASK_EXECUTION", "unknown"),
        claude_code_called=parsed.get("CLAUDE_CODE_CALLED", "unknown"),
        business_code_changed=parsed.get("BUSINESS_CODE_CHANGED", "unknown"),
        worktree_status=parsed.get("WORKTREE_STATUS", "unknown"),
        report_paths=report_paths,
        missing_required_fields=missing_required,
        unknown_fields=unknown_fields,
        parse_status=parse_status,
        parse_check_result=parse_check_result,
        stop_reason=stop_reason,
        human_review_required=bool(missing_required or unknown_fields),
        message=message,
    )


def _resolve_subproject_path(project_root: Path, task_id: str) -> Path:
    """根据任务 ID 前缀解析子项目路径。

    G 前缀 → projects/down-100-floors-game
    其他 → projects/（默认，后续可扩展）
    """
    if task_id.startswith("G"):
        return project_root / "projects" / "down-100-floors-game"
    return project_root / "projects"


# ---------------------------------------------------------------------------
# T078: Real-Call Double-Confirm Safety Gate
# ---------------------------------------------------------------------------

@dataclass
class RealCallSafetyResult:
    """Real-call double-confirm safety gate 检查结果。

    不执行任何真实任务，只做前置校验。
    """

    project: str
    run_id: str
    real_call_requested: bool                # 始终 True（--real-call 触发）
    real_confirm_status: str                 # "accepted" / "missing" / "rejected"
    real_confirm_phrase: str | None          # 用户传入的 --real-confirm 值
    execute_allowed: bool                    # 第一重 execute safety gate 是否通过
    real_call_allowed: bool                  # 全部检查通过才为 True
    max_tasks: int
    planned_tasks: list[str]                 # 计划执行的任务 ID 列表
    task_id: str | None                      # 第一个 planned task
    workspace_status: str                    # "clean" / "dirty"
    preflight_status: str                    # "passed" / "failed"
    real_task_execution: bool                # 始终 False（safety gate 不执行任务）
    run_project_task_full_called: bool       # 始终 False
    claude_code_called: str                  # "no"
    business_code_changed: str               # "no"
    check_result: str                        # "pass" / "fail"
    stop_reason: str | None                  # 拒绝原因
    human_review_required: bool              # 始终 True
    next_action: str                         # 建议下一步
    message: str                             # 详细消息


def validate_real_call_safety(
    project_root: str | Path,
    max_tasks: int,
    execute_requested: bool,
    confirm: str | None,
    real_call_requested: bool,
    real_confirm: str | None,
    adapter_dry_run: bool = False,
    real_call_stub: bool = False,
) -> RealCallSafetyResult:
    """Real-call double-confirm safety gate 校验。

    检查顺序：
    1. 第一重 execute safety gate
    2. real_call_requested
    3. real_confirm 短语精确匹配
    4. max_tasks == 1
    5. adapter / stub 互斥
    6. planned_task 存在
    7. workspace clean

    不执行任何任务，不调用 Claude Code，不修改业务代码。

    Args:
        project_root: 项目根目录
        max_tasks: 用户请求的 max_tasks
        execute_requested: 是否传入 --execute
        confirm: 第一重确认短语
        real_call_requested: 是否传入 --real-call
        real_confirm: 第二重确认短语
        adapter_dry_run: 是否同时传入 --adapter-dry-run
        real_call_stub: 是否同时传入 --real-call-stub

    Returns:
        RealCallSafetyResult
    """
    project_root = Path(project_root)
    run_id = _generate_run_id()

    # --- 默认失败结果 ---
    def _fail(
        real_confirm_status: str = "missing",
        stop_reason: str | None = None,
        next_action: str = "fix_real_call_preconditions",
        message: str = "",
        execute_allowed: bool = False,
    ) -> RealCallSafetyResult:
        return RealCallSafetyResult(
            project=str(project_root),
            run_id=run_id,
            real_call_requested=True,
            real_confirm_status=real_confirm_status,
            real_confirm_phrase=real_confirm,
            execute_allowed=execute_allowed,
            real_call_allowed=False,
            max_tasks=max_tasks,
            planned_tasks=[],
            task_id=None,
            workspace_status="unknown",
            preflight_status="failed",
            real_task_execution=False,
            run_project_task_full_called=False,
            claude_code_called="no",
            business_code_changed="no",
            check_result="fail",
            stop_reason=stop_reason,
            human_review_required=True,
            next_action=next_action,
            message=message,
        )

    # --- 1. 必须传入 --execute ---
    if not execute_requested:
        return _fail(
            real_confirm_status="missing",
            stop_reason="execute_not_requested",
            next_action="use_execute_with_real_call",
            message=(
                "错误：--real-call 必须配合 --execute 使用。"
                "请使用 --execute --confirm EXECUTE_PROJECT_LOOP。"
            ),
        )

    # --- 2. 第一重 execute safety gate ---
    safety = validate_execute_loop_safety(
        project_root=project_root,
        max_tasks=max_tasks,
        confirm=confirm,
    )

    if not safety.execute_allowed:
        return _fail(
            real_confirm_status="missing",
            stop_reason=f"execute_safety_gate_failed:{safety.stop_reason}",
            next_action=safety.next_action,
            message=(
                f"real-call safety gate 拒绝：第一重 execute safety gate 未通过"
                f"（{safety.stop_reason}）。"
                f"REAL_TASK_EXECUTION=no。"
            ),
            execute_allowed=False,
        )

    # --- 3. 第二重 real_confirm 检查 ---
    if real_confirm is None:
        return _fail(
            real_confirm_status="missing",
            stop_reason="real_confirm_missing",
            next_action="provide_real_confirm_phrase",
            message=(
                f"错误：缺少 --real-confirm 参数。"
                f"必须使用 --real-confirm {REAL_CALL_CONFIRM_PHRASE}"
            ),
            execute_allowed=True,
        )

    if real_confirm != REAL_CALL_CONFIRM_PHRASE:
        return _fail(
            real_confirm_status="rejected",
            stop_reason="real_confirm_rejected",
            next_action="provide_correct_real_confirm_phrase",
            message=(
                f"错误：第二重确认短语 '{real_confirm}' 不合法。"
                f"必须精确使用 --real-confirm {REAL_CALL_CONFIRM_PHRASE}"
            ),
            execute_allowed=True,
        )

    # --- 4. max_tasks 必须为 1 ---
    if max_tasks != 1:
        return _fail(
            real_confirm_status="accepted",
            stop_reason="max_tasks_not_one",
            next_action="use_max_tasks_1_for_real_call",
            message=(
                f"错误：--real-call 当前只支持 max_tasks=1，"
                f"请求的 max_tasks={max_tasks}。"
                f"请使用 --max-tasks 1。"
            ),
            execute_allowed=True,
        )

    # --- 5. 模式互斥检查 ---
    if adapter_dry_run:
        return _fail(
            real_confirm_status="accepted",
            stop_reason="mode_conflict_adapter_dry_run",
            next_action="remove_adapter_dry_run",
            message=(
                "错误：--real-call 和 --adapter-dry-run 互斥，"
                "不能同时使用。"
            ),
            execute_allowed=True,
        )

    if real_call_stub:
        return _fail(
            real_confirm_status="accepted",
            stop_reason="mode_conflict_real_call_stub",
            next_action="remove_real_call_stub",
            message=(
                "错误：--real-call 和 --real-call-stub 互斥，"
                "不能同时使用。"
            ),
            execute_allowed=True,
        )

    # --- 6. planned_tasks 非空（从 execute safety gate 结果获取） ---
    if not safety.planned_tasks:
        return _fail(
            real_confirm_status="accepted",
            stop_reason="no_planned_tasks",
            next_action="check_tasks_or_add_new",
            message="错误：没有可执行的 pending 任务。",
            execute_allowed=True,
        )

    task_id = safety.planned_tasks[0]

    # --- 7. workspace clean（safety gate 已检查，但双重确认） ---
    workspace_clean = _check_workspace_clean(project_root)
    workspace_status = "clean" if workspace_clean else "dirty"

    if not workspace_clean:
        return RealCallSafetyResult(
            project=str(project_root),
            run_id=run_id,
            real_call_requested=True,
            real_confirm_status="accepted",
            real_confirm_phrase=real_confirm,
            execute_allowed=True,
            real_call_allowed=False,
            max_tasks=max_tasks,
            planned_tasks=safety.planned_tasks,
            task_id=task_id,
            workspace_status="dirty",
            preflight_status="failed",
            real_task_execution=False,
            run_project_task_full_called=False,
            claude_code_called="no",
            business_code_changed="no",
            check_result="fail",
            stop_reason="workspace_not_clean",
            human_review_required=True,
            next_action="commit_or_stash_changes",
            message="错误：工作区不 clean，请先提交或 stash 变更。",
        )

    # --- 全部检查通过 ---
    return RealCallSafetyResult(
        project=str(project_root),
        run_id=run_id,
        real_call_requested=True,
        real_confirm_status="accepted",
        real_confirm_phrase=real_confirm,
        execute_allowed=True,
        real_call_allowed=True,
        max_tasks=1,
        planned_tasks=safety.planned_tasks,
        task_id=task_id,
        workspace_status="clean",
        preflight_status="passed",
        real_task_execution=False,
        run_project_task_full_called=False,
        claude_code_called="no",
        business_code_changed="no",
        check_result="pass",
        stop_reason=None,
        human_review_required=True,
        next_action="ready_for_T079_real_call_dry_run_executor",
        message=(
            f"real-call safety gate 通过：双重确认正确，max_tasks=1，"
            f"工作区 clean，任务 {task_id} 可执行。"
            f"REAL_TASK_EXECUTION=no（safety gate 不执行任务）。"
        ),
    )


# ---------------------------------------------------------------------------
# T092: First Real-Run Acceptance Result Model
# ---------------------------------------------------------------------------

_VALID_ACCEPTANCE_STATUSES = frozenset({
    "ready_for_human_review",
    "blocked",
    "failed_to_parse",
    "unsafe_to_continue",
})

_VALID_WORKSPACE_CLASSIFICATIONS = frozenset({
    "clean",
    "dirty_reports_only",
    "dirty_business_code",
    "dirty_expected",
    "dirty_unexpected",
    "dirty_unknown",
})


@dataclass
class FirstRealRunAcceptanceResult:
    """首次真实调用 run-project-task-full 后的验收结果。

    接收 ChildCommandParseResult，根据 T091 协议判断验收状态。
    不执行任何命令，不修改任何文件。
    """

    # 标识
    run_id: str                              # loop-YYYYMMDD-HHMMSS-<6hex>
    project: str                             # 项目路径
    task_id: str | None                      # 执行的任务编号
    execution_mode: str                      # "first_real_run_acceptance"

    # 执行状态
    real_task_execution: str                 # "yes"
    run_project_task_full_called: str        # "yes" / "attempted" / "no"

    # 子调用结果
    child_exit_code: str                     # "not_applicable"
    child_check_result: str                  # "pass" / "fail" / "missing"
    child_task_status: str                   # "done" / "failed" / "unknown"

    # 解析状态
    parsed_stdout_status: str                # "not_applicable"
    parsed_stderr_status: str                # "not_applicable"

    # 推断字段
    claude_code_called: str                  # "yes" / "no" / "unknown"
    business_code_changed: str               # "yes" / "no" / "unknown"

    # Workspace
    workspace_status_before: str             # "clean"
    workspace_status_after: str
    workspace_change_classification: str

    # 报告
    report_paths: list[str]

    # 验收决策
    human_review_required: bool              # 始终 True
    auto_continue_to_next_task: bool         # 始终 False
    auto_git_backup: bool                    # 始终 False
    acceptance_status: str                   # ready_for_human_review / blocked / failed_to_parse / unsafe_to_continue
    acceptance_required_reason: str          # "first_real_execution_requires_review"
    stop_reason: str
    next_action: str
    check_result: str                        # "pass" / "fail"

    # 消息
    message: str


def evaluate_first_real_run_acceptance(
    project_path: str | Path,
    task_id: str | None,
    child_parse_result: ChildCommandParseResult,
    workspace_status_before: str = "clean",
    workspace_status_after: str = "unknown",
    workspace_change_classification: str = "dirty_unknown",
    run_project_task_full_called: str = "attempted",
    claude_code_called: str = "unknown",
    business_code_changed: str = "unknown",
) -> FirstRealRunAcceptanceResult:
    """基于 child parse result 构造首次真实调用验收结果。

    根据 T091 协议判断验收状态：
    - failed_to_parse：parse 失败或缺少 CHECK_RESULT
    - blocked：check_result=fail / task_status=failed / dirty_unexpected / report_paths 缺失
    - unsafe_to_continue：dirty_unknown / business_code_changed=unknown / claude_code_called=unknown
    - ready_for_human_review：所有条件满足

    优先级：failed_to_parse > blocked > unsafe_to_continue > ready_for_human_review

    不执行任何命令，不修改任何文件。

    Args:
        project_path: 项目路径
        task_id: 任务 ID
        child_parse_result: 子命令输出解析结果
        workspace_status_before: 执行前 workspace 状态（应 clean）
        workspace_status_after: 执行后 workspace 状态
        workspace_change_classification: workspace 变更分类
        run_project_task_full_called: 是否真实调用
        claude_code_called: Claude Code 调用推断结果
        business_code_changed: 业务代码变更推断结果

    Returns:
        FirstRealRunAcceptanceResult
    """
    project_path = Path(project_path)
    run_id = _generate_run_id()

    report_paths = list(child_parse_result.report_paths)
    child_check_result = child_parse_result.check_result
    child_task_status = child_parse_result.task_status

    # --- 优先级 1：failed_to_parse ---
    if child_parse_result.parse_check_result == "fail":
        # 解析失败时，child_check_result 可能是空或 "unknown"（parser 降级值）
        effective_check = child_check_result if child_check_result and child_check_result not in ("unknown", "") else "missing"
        return FirstRealRunAcceptanceResult(
            run_id=run_id,
            project=str(project_path),
            task_id=task_id,
            execution_mode="first_real_run_acceptance",
            real_task_execution="yes",
            run_project_task_full_called=run_project_task_full_called,
            child_exit_code="not_applicable",
            child_check_result=effective_check,
            child_task_status=child_task_status,
            parsed_stdout_status="not_applicable",
            parsed_stderr_status="not_applicable",
            claude_code_called=claude_code_called,
            business_code_changed=business_code_changed,
            workspace_status_before=workspace_status_before,
            workspace_status_after=workspace_status_after,
            workspace_change_classification=workspace_change_classification,
            report_paths=report_paths,
            human_review_required=True,
            auto_continue_to_next_task=False,
            auto_git_backup=False,
            acceptance_status="failed_to_parse",
            acceptance_required_reason="first_real_execution_requires_review",
            stop_reason=child_parse_result.stop_reason or "parse_failed",
            next_action="review_parse_failure",
            check_result="fail",
            message=(
                f"验收失败：子命令输出解析失败"
                f"（{child_parse_result.stop_reason or 'parse_failed'}），"
                f"无法确认执行结果。"
            ),
        )

    # --- 优先级 2：blocked ---
    blocked_reason = None
    if child_check_result == "fail":
        blocked_reason = "child_check_result_failed"
    elif child_task_status == "failed":
        blocked_reason = "child_task_status_failed"
    elif workspace_change_classification == "dirty_unexpected":
        blocked_reason = "dirty_unexpected"
    elif not report_paths:
        blocked_reason = "missing_report_paths"

    if blocked_reason:
        next_action = "review_failure_before_continue"
        if blocked_reason == "dirty_unexpected":
            next_action = "review_unexpected_changes"
        elif blocked_reason == "missing_report_paths":
            next_action = "check_report_generation"

        return FirstRealRunAcceptanceResult(
            run_id=run_id,
            project=str(project_path),
            task_id=task_id,
            execution_mode="first_real_run_acceptance",
            real_task_execution="yes",
            run_project_task_full_called=run_project_task_full_called,
            child_exit_code="not_applicable",
            child_check_result=child_check_result,
            child_task_status=child_task_status,
            parsed_stdout_status="not_applicable",
            parsed_stderr_status="not_applicable",
            claude_code_called=claude_code_called,
            business_code_changed=business_code_changed,
            workspace_status_before=workspace_status_before,
            workspace_status_after=workspace_status_after,
            workspace_change_classification=workspace_change_classification,
            report_paths=report_paths,
            human_review_required=True,
            auto_continue_to_next_task=False,
            auto_git_backup=False,
            acceptance_status="blocked",
            acceptance_required_reason="first_real_execution_requires_review",
            stop_reason=blocked_reason,
            next_action=next_action,
            check_result="fail",
            message=(
                f"验收阻塞：{blocked_reason}。"
                f"需要人工审查并处理后再继续。"
            ),
        )

    # --- 优先级 3：unsafe_to_continue ---
    if workspace_change_classification == "dirty_unknown":
        return FirstRealRunAcceptanceResult(
            run_id=run_id,
            project=str(project_path),
            task_id=task_id,
            execution_mode="first_real_run_acceptance",
            real_task_execution="yes",
            run_project_task_full_called=run_project_task_full_called,
            child_exit_code="not_applicable",
            child_check_result=child_check_result,
            child_task_status=child_task_status,
            parsed_stdout_status="not_applicable",
            parsed_stderr_status="not_applicable",
            claude_code_called=claude_code_called,
            business_code_changed=business_code_changed,
            workspace_status_before=workspace_status_before,
            workspace_status_after=workspace_status_after,
            workspace_change_classification=workspace_change_classification,
            report_paths=report_paths,
            human_review_required=True,
            auto_continue_to_next_task=False,
            auto_git_backup=False,
            acceptance_status="unsafe_to_continue",
            acceptance_required_reason="first_real_execution_requires_review",
            stop_reason="dirty_unknown",
            next_action="manual_review_required",
            check_result="fail",
            message=(
                "验收不安全：workspace 变更无法分类（dirty_unknown），"
                "需要人工审查所有变更后再决定是否继续。"
            ),
        )

    # --- 优先级 4：ready_for_human_review ---
    # child_check_result=pass + task_status=done + workspace 可识别 + report_paths 非空
    return FirstRealRunAcceptanceResult(
        run_id=run_id,
        project=str(project_path),
        task_id=task_id,
        execution_mode="first_real_run_acceptance",
        real_task_execution="yes",
        run_project_task_full_called=run_project_task_full_called,
        child_exit_code="not_applicable",
        child_check_result=child_check_result,
        child_task_status=child_task_status,
        parsed_stdout_status="not_applicable",
        parsed_stderr_status="not_applicable",
        claude_code_called=claude_code_called,
        business_code_changed=business_code_changed,
        workspace_status_before=workspace_status_before,
        workspace_status_after=workspace_status_after,
        workspace_change_classification=workspace_change_classification,
        report_paths=report_paths,
        human_review_required=True,
        auto_continue_to_next_task=False,
        auto_git_backup=False,
        acceptance_status="ready_for_human_review",
        acceptance_required_reason="first_real_execution_requires_review",
        stop_reason="first_real_execution_requires_review",
        next_action="review_real_task_execution_result",
        check_result="pass",
        message=(
            f"首次真实执行完成：{task_id or 'unknown'}，"
            f"CHECK_RESULT=pass，等待人工验收。"
            f"HUMAN_REVIEW_REQUIRED=true，"
            f"AUTO_CONTINUE_TO_NEXT_TASK=false。"
        ),
    )


# ---------------------------------------------------------------------------
# T093: Simulated First Real-Run Acceptance Parser
# ---------------------------------------------------------------------------

_SIMULATED_ACCEPTANCE_SAMPLES: dict[str, dict] = {
    "pass": {
        "description": "正常成功，workspace clean，有报告",
        "stdout": (
            "TASK_ID=T093\n"
            "CHECK_RESULT=pass\n"
            "TASK_STATUS=done\n"
            "NEXT_PENDING=T094\n"
            "REAL_TASK_EXECUTION=yes\n"
            "CLAUDE_CODE_CALLED=yes\n"
            "BUSINESS_CODE_CHANGED=no\n"
            "WORKTREE_STATUS=clean\n"
            "REPORT_PATHS=reports/dev/T093-dev-report.md,reports/checks/T093-simulated-acceptance-check.md\n"
            "FINAL_STATUS=COMPLETE\n"
            "FULL_LOOP_REPORT=reports/T093-full-loop-report.md\n"
        ),
        "workspace_after": "clean",
        "workspace_classification": "clean",
        "claude_code_called": "yes",
        "business_code_changed": "no",
        "expected_acceptance_status": "ready_for_human_review",
    },
    "fail": {
        "description": "任务失败，check_result=fail",
        "stdout": (
            "TASK_ID=T093\n"
            "CHECK_RESULT=fail\n"
            "TASK_STATUS=failed\n"
            "NEXT_PENDING=\n"
            "REAL_TASK_EXECUTION=yes\n"
            "CLAUDE_CODE_CALLED=yes\n"
            "BUSINESS_CODE_CHANGED=no\n"
            "WORKTREE_STATUS=clean\n"
            "REPORT_PATHS=reports/dev/T093-dev-report.md\n"
            "FINAL_STATUS=FAILED\n"
            "FULL_LOOP_REPORT=reports/T093-full-loop-report.md\n"
        ),
        "workspace_after": "clean",
        "workspace_classification": "clean",
        "claude_code_called": "yes",
        "business_code_changed": "no",
        "expected_acceptance_status": "blocked",
    },
    "missing-check-result": {
        "description": "缺少 CHECK_RESULT，解析失败",
        "stdout": (
            "TASK_ID=T093\n"
            "TASK_STATUS=done\n"
            "REAL_TASK_EXECUTION=yes\n"
            "CLAUDE_CODE_CALLED=yes\n"
            "BUSINESS_CODE_CHANGED=no\n"
            "WORKTREE_STATUS=clean\n"
        ),
        "workspace_after": "clean",
        "workspace_classification": "clean",
        "claude_code_called": "yes",
        "business_code_changed": "no",
        "expected_acceptance_status": "failed_to_parse",
    },
    "unsafe-unknown": {
        "description": "workspace dirty_unknown，不安全",
        "stdout": (
            "TASK_ID=T093\n"
            "CHECK_RESULT=pass\n"
            "TASK_STATUS=done\n"
            "REAL_TASK_EXECUTION=yes\n"
            "CLAUDE_CODE_CALLED=unknown\n"
            "BUSINESS_CODE_CHANGED=unknown\n"
            "WORKTREE_STATUS=dirty_unknown\n"
            "REPORT_PATHS=reports/dev/T093-dev-report.md\n"
        ),
        "workspace_after": "dirty_unknown",
        "workspace_classification": "dirty_unknown",
        "claude_code_called": "unknown",
        "business_code_changed": "unknown",
        "expected_acceptance_status": "unsafe_to_continue",
    },
    "dirty-unexpected": {
        "description": "workspace dirty_unexpected，非预期变更",
        "stdout": (
            "TASK_ID=T093\n"
            "CHECK_RESULT=pass\n"
            "TASK_STATUS=done\n"
            "REAL_TASK_EXECUTION=yes\n"
            "CLAUDE_CODE_CALLED=yes\n"
            "BUSINESS_CODE_CHANGED=yes\n"
            "WORKTREE_STATUS=dirty_unexpected\n"
            "REPORT_PATHS=reports/dev/T093-dev-report.md\n"
        ),
        "workspace_after": "dirty_unexpected",
        "workspace_classification": "dirty_unexpected",
        "claude_code_called": "yes",
        "business_code_changed": "yes",
        "expected_acceptance_status": "blocked",
    },
    "missing-report-paths": {
        "description": "report_paths 缺失，阻塞",
        "stdout": (
            "TASK_ID=T093\n"
            "CHECK_RESULT=pass\n"
            "TASK_STATUS=done\n"
            "REAL_TASK_EXECUTION=yes\n"
            "CLAUDE_CODE_CALLED=yes\n"
            "BUSINESS_CODE_CHANGED=no\n"
            "WORKTREE_STATUS=clean\n"
        ),
        "workspace_after": "clean",
        "workspace_classification": "clean",
        "claude_code_called": "yes",
        "business_code_changed": "no",
        "expected_acceptance_status": "blocked",
    },
    "pass-dirty-reports": {
        "description": "成功，只有报告变更",
        "stdout": (
            "TASK_ID=T093\n"
            "CHECK_RESULT=pass\n"
            "TASK_STATUS=done\n"
            "NEXT_PENDING=T094\n"
            "REAL_TASK_EXECUTION=yes\n"
            "CLAUDE_CODE_CALLED=yes\n"
            "BUSINESS_CODE_CHANGED=no\n"
            "WORKTREE_STATUS=dirty_reports_only\n"
            "REPORT_PATHS=reports/dev/T093-dev-report.md,reports/checks/T093-simulated-acceptance-check.md\n"
            "FINAL_STATUS=COMPLETE\n"
        ),
        "workspace_after": "dirty_reports_only",
        "workspace_classification": "dirty_reports_only",
        "claude_code_called": "yes",
        "business_code_changed": "no",
        "expected_acceptance_status": "ready_for_human_review",
    },
    "task-status-failed": {
        "description": "task_status=failed，阻塞",
        "stdout": (
            "TASK_ID=T093\n"
            "CHECK_RESULT=pass\n"
            "TASK_STATUS=failed\n"
            "REAL_TASK_EXECUTION=yes\n"
            "CLAUDE_CODE_CALLED=yes\n"
            "BUSINESS_CODE_CHANGED=no\n"
            "WORKTREE_STATUS=clean\n"
            "REPORT_PATHS=reports/dev/T093-dev-report.md\n"
        ),
        "workspace_after": "clean",
        "workspace_classification": "clean",
        "claude_code_called": "yes",
        "business_code_changed": "no",
        "expected_acceptance_status": "blocked",
    },
}


def run_simulated_first_real_run_acceptance_parser(
    project_path: str | Path,
    task_id: str | None = None,
    sample: str = "pass",
) -> FirstRealRunAcceptanceResult:
    """使用内置 sample stdout 模拟首次真实调用后的验收流程。

    链式调用：
    1. 从 _SIMULATED_ACCEPTANCE_SAMPLES 获取 sample 数据
    2. parse_child_command_output() 解析 stdout
    3. evaluate_first_real_run_acceptance() 评估验收状态
    4. 返回 FirstRealRunAcceptanceResult

    不执行任何命令，不调用 run_project_task_full，不调用 Claude Code。

    Args:
        project_path: 项目路径
        task_id: 任务 ID（覆盖 sample 中的 task_id）
        sample: sample 名称，默认 "pass"

    Returns:
        FirstRealRunAcceptanceResult

    Raises:
        ValueError: sample 不存在时
    """
    if sample not in _SIMULATED_ACCEPTANCE_SAMPLES:
        available = ", ".join(sorted(_SIMULATED_ACCEPTANCE_SAMPLES.keys()))
        raise ValueError(
            f"unknown sample: {sample}. Available: {available}"
        )

    sample_data = _SIMULATED_ACCEPTANCE_SAMPLES[sample]

    # Step 1: parse child command output
    child_result = parse_child_command_output(
        stdout_text=sample_data["stdout"],
        stderr_text="",
        exit_code=0,
    )

    # Step 2: evaluate acceptance
    acceptance = evaluate_first_real_run_acceptance(
        project_path=project_path,
        task_id=task_id or child_result.task_id or None,
        child_parse_result=child_result,
        workspace_status_before="clean",
        workspace_status_after=sample_data["workspace_after"],
        workspace_change_classification=sample_data["workspace_classification"],
        run_project_task_full_called="yes",
        claude_code_called=sample_data["claude_code_called"],
        business_code_changed=sample_data["business_code_changed"],
    )

    return acceptance
