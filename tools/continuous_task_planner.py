"""Continuous Task Planner — 连续任务自动推进计划生成与 loop dry-run。

严格遵循 docs/continuous-task-auto-advance-design.md 协议。
T059 实现 dry-run 计划生成，T060 实现 loop dry-run 模拟推进。
T065 实现 execute mode safety gate（确认协议、前置检查、execute 硬限制）。
T117 实现 no-tool-use proposal parser dry-run。
T118 实现 no-tool-use allowed scope validator dry-run。
T119 实现 no-tool-use controlled patch apply dry-run。
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

REAL_EXECUTE_CONFIRM_PHRASE = "EXECUTE_REAL_RUN_ONCE"


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


# ---------------------------------------------------------------------------
# T096: First Real-Run Execute-Once Safety Gate
# ---------------------------------------------------------------------------

@dataclass
class FirstRealRunExecuteOnceSafetyResult:
    """首次真实执行 execute-once safety gate 检查结果。

    接收 --real-execute-once 和 --real-execute-confirm，
    复用已有 execute / real-call / run-once safety gate 逻辑，
    新增第三重确认 EXECUTE_REAL_RUN_ONCE 检查。
    不调用 run-project-task-full，不调用 Claude Code，不修改业务代码。
    """

    project: str
    run_id: str
    task_id: str | None                       # 当前 NEXT_PENDING
    execution_mode: str                       # "first_real_run_execute_once_safety_gate"
    execute_confirm_status: str               # "accepted" / "missing" / "rejected"
    real_confirm_status: str                  # "accepted" / "missing" / "rejected"
    real_execute_confirm_status: str          # "accepted" / "missing" / "rejected"
    real_execute_once_requested: bool         # --real-execute-once 是否传入
    real_execute_allowed: bool                # 全部检查通过才为 True
    real_task_execution: str                  # "no"（safety gate 不执行）
    run_project_task_full_called: str         # "no"
    claude_code_called: str                   # "no"
    business_code_changed: str                # "no"
    workspace_status_before: str              # "clean" / "dirty"
    preflight_status: str                     # "passed" / "failed"
    max_tasks: int
    planned_tasks: list[str]                  # 计划执行的任务 ID 列表
    auto_continue_to_next_task: str           # "false"
    auto_git_backup: str                      # "false"
    human_review_required: str                # "true"
    check_result: str                         # "pass" / "fail"
    stop_reason: str | None                   # 停止原因
    next_action: str                          # 建议下一步
    message: str                              # 详细消息


def validate_first_real_run_execute_once_safety(
    project_path: str | Path,
    max_tasks: int = 1,
    confirm: str | None = None,
    real_confirm: str | None = None,
    real_execute_once: bool = False,
    real_execute_confirm: str | None = None,
    real_call_dry_run: bool = False,
    adapter_dry_run: bool = False,
    real_call_stub: bool = False,
    dry_run_flag: bool = False,
) -> FirstRealRunExecuteOnceSafetyResult:
    """首次真实执行 execute-once safety gate。

    复用已有 validate_real_call_safety() 做双重确认前置检查。
    新增第三重确认 EXECUTE_REAL_RUN_ONCE 检查。
    检查 max_tasks=1、planned task 非空、workspace clean。
    不调用 run-project-task-full，不调用 Claude Code，不修改业务代码。

    Args:
        project_path: 项目根目录
        max_tasks: 用户请求的 max_tasks（必须为 1）
        confirm: 第一重确认短语
        real_confirm: 第二重确认短语
        real_execute_once: 是否传入 --real-execute-once
        real_execute_confirm: 第三重确认短语
        real_call_dry_run: 是否同时传入了 --real-call-dry-run
        adapter_dry_run: 是否同时传入了 --adapter-dry-run
        real_call_stub: 是否同时传入了 --real-call-stub
        dry_run_flag: 是否同时传入了 --dry-run

    Returns:
        FirstRealRunExecuteOnceSafetyResult
    """
    project_path = Path(project_path)
    run_id = _generate_run_id()

    # --- 默认失败结果 ---
    def _fail(
        real_execute_confirm_status: str = "missing",
        stop_reason: str | None = None,
        next_action: str = "fix_execute_once_preflight_or_confirm",
        message: str = "",
        real_confirm_status: str = "missing",
        execute_confirm_status: str = "missing",
        preflight_status: str = "failed",
        task_id: str | None = None,
        planned_tasks: list[str] | None = None,
        workspace_status_before: str = "unknown",
    ) -> FirstRealRunExecuteOnceSafetyResult:
        return FirstRealRunExecuteOnceSafetyResult(
            project=str(project_path),
            run_id=run_id,
            task_id=task_id,
            execution_mode="first_real_run_execute_once_safety_gate",
            execute_confirm_status=execute_confirm_status,
            real_confirm_status=real_confirm_status,
            real_execute_confirm_status=real_execute_confirm_status,
            real_execute_once_requested=real_execute_once,
            real_execute_allowed=False,
            real_task_execution="no",
            run_project_task_full_called="no",
            claude_code_called="no",
            business_code_changed="no",
            workspace_status_before=workspace_status_before,
            preflight_status=preflight_status,
            max_tasks=max_tasks,
            planned_tasks=planned_tasks or [],
            auto_continue_to_next_task="false",
            auto_git_backup="false",
            human_review_required="true",
            check_result="fail",
            stop_reason=stop_reason,
            next_action=next_action,
            message=message,
        )

    # --- 1. 如果没有 --real-execute-once，不进入此 gate ---
    if not real_execute_once:
        return _fail(
            real_execute_confirm_status="missing",
            stop_reason="real_execute_once_not_requested",
            next_action="use_run_once_safety_shell",
            message=(
                "execute-once safety gate：未收到 --real-execute-once 请求。"
                "如果只需要 safety shell，请使用 --real-call-run-once。"
            ),
        )

    # --- 2. 模式互斥检查 ---
    if real_call_dry_run:
        return _fail(
            stop_reason="mode_conflict_real_call_dry_run",
            next_action="remove_real_call_dry_run",
            message=(
                "错误：--real-execute-once 和 --real-call-dry-run 互斥，"
                "不能同时使用。"
            ),
        )

    if adapter_dry_run:
        return _fail(
            stop_reason="mode_conflict_adapter_dry_run",
            next_action="remove_adapter_dry_run",
            message=(
                "错误：--real-execute-once 和 --adapter-dry-run 互斥，"
                "不能同时使用。"
            ),
        )

    if real_call_stub:
        return _fail(
            stop_reason="mode_conflict_real_call_stub",
            next_action="remove_real_call_stub",
            message=(
                "错误：--real-execute-once 和 --real-call-stub 互斥，"
                "不能同时使用。"
            ),
        )

    if dry_run_flag:
        return _fail(
            stop_reason="mode_conflict_dry_run",
            next_action="remove_dry_run",
            message=(
                "错误：--real-execute-once 和 --dry-run 互斥，"
                "不能同时使用。"
            ),
        )

    # --- 3. 复用 validate_real_call_safety() 做双重确认前置检查 ---
    safety = validate_real_call_safety(
        project_root=project_path,
        max_tasks=max_tasks,
        execute_requested=True,
        confirm=confirm,
        real_call_requested=True,
        real_confirm=real_confirm,
        adapter_dry_run=False,
        real_call_stub=False,
    )

    # 映射第一重和第二重确认状态
    execute_confirm_status = "accepted" if safety.execute_allowed else (
        "missing" if not safety.execute_allowed and confirm is None else "rejected"
    )
    real_confirm_status = safety.real_confirm_status

    # --- 4. 双重确认不通过 → 返回失败 ---
    if not safety.real_call_allowed:
        return _fail(
            real_execute_confirm_status="missing",
            execute_confirm_status=execute_confirm_status,
            real_confirm_status=real_confirm_status,
            stop_reason=safety.stop_reason,
            next_action=safety.next_action,
            message=(
                f"execute-once safety gate：双重确认前置检查未通过"
                f"（{safety.stop_reason}）。"
                f"REAL_TASK_EXECUTION=no。"
            ),
            task_id=safety.task_id,
            planned_tasks=safety.planned_tasks,
            workspace_status_before=safety.workspace_status,
        )

    # --- 5. 第三重确认检查 ---
    if real_execute_confirm is None:
        return _fail(
            real_execute_confirm_status="missing",
            execute_confirm_status="accepted",
            real_confirm_status="accepted",
            stop_reason="real_execute_confirm_missing",
            next_action="provide_real_execute_confirm_phrase",
            message=(
                f"错误：缺少 --real-execute-confirm 参数。"
                f"必须使用 --real-execute-confirm {REAL_EXECUTE_CONFIRM_PHRASE}"
            ),
            task_id=safety.task_id,
            planned_tasks=safety.planned_tasks,
            workspace_status_before=safety.workspace_status,
            preflight_status="passed",
        )

    if real_execute_confirm != REAL_EXECUTE_CONFIRM_PHRASE:
        return _fail(
            real_execute_confirm_status="rejected",
            execute_confirm_status="accepted",
            real_confirm_status="accepted",
            stop_reason="real_execute_confirm_rejected",
            next_action="provide_correct_real_execute_confirm_phrase",
            message=(
                f"错误：第三重确认短语 '{real_execute_confirm}' 不合法。"
                f"必须精确使用 --real-execute-confirm {REAL_EXECUTE_CONFIRM_PHRASE}"
            ),
            task_id=safety.task_id,
            planned_tasks=safety.planned_tasks,
            workspace_status_before=safety.workspace_status,
            preflight_status="passed",
        )

    # --- 6. max_tasks 必须为 1 ---
    if max_tasks != 1:
        return _fail(
            real_execute_confirm_status="accepted",
            execute_confirm_status="accepted",
            real_confirm_status="accepted",
            stop_reason="max_tasks_not_one",
            next_action="use_max_tasks_1_for_execute_once",
            message=(
                f"错误：--real-execute-once 当前只支持 max_tasks=1，"
                f"请求的 max_tasks={max_tasks}。"
                f"请使用 --max-tasks 1。"
            ),
            task_id=safety.task_id,
            planned_tasks=safety.planned_tasks,
            workspace_status_before=safety.workspace_status,
            preflight_status="passed",
        )

    # --- 7. planned task 非空 ---
    if not safety.planned_tasks:
        return _fail(
            real_execute_confirm_status="accepted",
            execute_confirm_status="accepted",
            real_confirm_status="accepted",
            stop_reason="no_planned_tasks",
            next_action="check_tasks_or_add_new",
            message="错误：没有可执行的 pending 任务。",
            task_id=safety.task_id,
            workspace_status_before=safety.workspace_status,
            preflight_status="passed",
        )

    task_id = safety.task_id

    # --- 8. workspace clean（safety gate 已检查，但再次确认） ---
    workspace_clean = _check_workspace_clean(project_path)
    workspace_status_before = "clean" if workspace_clean else "dirty"

    if not workspace_clean:
        return FirstRealRunExecuteOnceSafetyResult(
            project=str(project_path),
            run_id=run_id,
            task_id=task_id,
            execution_mode="first_real_run_execute_once_safety_gate",
            execute_confirm_status="accepted",
            real_confirm_status="accepted",
            real_execute_confirm_status="accepted",
            real_execute_once_requested=True,
            real_execute_allowed=False,
            real_task_execution="no",
            run_project_task_full_called="no",
            claude_code_called="no",
            business_code_changed="no",
            workspace_status_before="dirty",
            preflight_status="failed",
            max_tasks=max_tasks,
            planned_tasks=safety.planned_tasks,
            auto_continue_to_next_task="false",
            auto_git_backup="false",
            human_review_required="true",
            check_result="fail",
            stop_reason="workspace_not_clean",
            next_action="commit_or_stash_changes",
            message="错误：工作区不 clean，请先提交或 stash 变更。",
        )

    # --- 全部检查通过 ---
    return FirstRealRunExecuteOnceSafetyResult(
        project=str(project_path),
        run_id=run_id,
        task_id=task_id,
        execution_mode="first_real_run_execute_once_safety_gate",
        execute_confirm_status="accepted",
        real_confirm_status="accepted",
        real_execute_confirm_status="accepted",
        real_execute_once_requested=True,
        real_execute_allowed=True,
        real_task_execution="no",
        run_project_task_full_called="no",
        claude_code_called="no",
        business_code_changed="no",
        workspace_status_before="clean",
        preflight_status="passed",
        max_tasks=1,
        planned_tasks=safety.planned_tasks,
        auto_continue_to_next_task="false",
        auto_git_backup="false",
        human_review_required="true",
        check_result="pass",
        stop_reason="execute_once_safety_gate_only",
        next_action="ready_for_T098_simulated_child_call",
        message=(
            f"execute-once safety gate 通过：三重确认正确，max_tasks=1，"
            f"工作区 clean，任务 {task_id} 可执行。"
            f"REAL_TASK_EXECUTION=no，"
            f"RUN_PROJECT_TASK_FULL_CALLED=no（safety gate 不执行任务）。"
        ),
    )


# ---------------------------------------------------------------------------
# T098: First Real-Run Executor Simulated Child Call
# ---------------------------------------------------------------------------

# 支持 6 种内置 child sample
_SIMULATED_CHILD_SAMPLES: dict[str, dict] = {
    "pass": {
        "description": "child CHECK_RESULT=pass, task done, clean workspace",
        "stdout": (
            "TASK_ID={task_id}\n"
            "CHECK_RESULT=pass\n"
            "TASK_STATUS=done\n"
            "NEXT_PENDING=\n"
            "REAL_TASK_EXECUTION=no\n"
            "CLAUDE_CODE_CALLED=no\n"
            "BUSINESS_CODE_CHANGED=no\n"
            "WORKTREE_STATUS=clean\n"
            "REPORT_PATHS=reports/dev/{task_id}-dev-report.md,reports/checks/{task_id}-check.md\n"
            "FINAL_STATUS=COMPLETE\n"
        ),
        "workspace_after": "clean",
        "workspace_classification": "clean",
        "claude_code_called": "no",
        "business_code_changed": "no",
        "child_check_result": "pass",
        "child_task_status": "done",
        "expected_acceptance_status": "ready_for_human_review",
    },
    "fail": {
        "description": "child CHECK_RESULT=fail, task failed",
        "stdout": (
            "TASK_ID={task_id}\n"
            "CHECK_RESULT=fail\n"
            "TASK_STATUS=failed\n"
            "NEXT_PENDING=\n"
            "REAL_TASK_EXECUTION=no\n"
            "CLAUDE_CODE_CALLED=no\n"
            "BUSINESS_CODE_CHANGED=no\n"
            "WORKTREE_STATUS=clean\n"
            "REPORT_PATHS=reports/dev/{task_id}-dev-report.md\n"
            "FINAL_STATUS=FAILED\n"
        ),
        "workspace_after": "clean",
        "workspace_classification": "clean",
        "claude_code_called": "no",
        "business_code_changed": "no",
        "child_check_result": "fail",
        "child_task_status": "failed",
        "expected_acceptance_status": "blocked",
    },
    "missing-check-result": {
        "description": "缺少 CHECK_RESULT, 解析失败",
        "stdout": (
            "TASK_ID={task_id}\n"
            "TASK_STATUS=done\n"
            "REAL_TASK_EXECUTION=no\n"
            "CLAUDE_CODE_CALLED=no\n"
            "BUSINESS_CODE_CHANGED=no\n"
            "WORKTREE_STATUS=clean\n"
        ),
        "workspace_after": "clean",
        "workspace_classification": "clean",
        "claude_code_called": "no",
        "business_code_changed": "no",
        "child_check_result": "unknown",
        "child_task_status": "done",
        "expected_acceptance_status": "failed_to_parse",
    },
    "dirty-unexpected": {
        "description": "workspace dirty_unexpected, 非预期变更",
        "stdout": (
            "TASK_ID={task_id}\n"
            "CHECK_RESULT=pass\n"
            "TASK_STATUS=done\n"
            "REAL_TASK_EXECUTION=no\n"
            "CLAUDE_CODE_CALLED=unknown\n"
            "BUSINESS_CODE_CHANGED=unknown\n"
            "WORKTREE_STATUS=dirty_unexpected\n"
            "REPORT_PATHS=reports/dev/{task_id}-dev-report.md\n"
        ),
        "workspace_after": "dirty_unexpected",
        "workspace_classification": "dirty_unexpected",
        "claude_code_called": "unknown",
        "business_code_changed": "unknown",
        "child_check_result": "pass",
        "child_task_status": "done",
        "expected_acceptance_status": "blocked",
    },
    "unsafe-unknown": {
        "description": "workspace dirty_unknown, 不安全",
        "stdout": (
            "TASK_ID={task_id}\n"
            "CHECK_RESULT=pass\n"
            "TASK_STATUS=done\n"
            "REAL_TASK_EXECUTION=no\n"
            "CLAUDE_CODE_CALLED=unknown\n"
            "BUSINESS_CODE_CHANGED=unknown\n"
            "WORKTREE_STATUS=dirty_unknown\n"
            "REPORT_PATHS=reports/dev/{task_id}-dev-report.md\n"
        ),
        "workspace_after": "dirty_unknown",
        "workspace_classification": "dirty_unknown",
        "claude_code_called": "unknown",
        "business_code_changed": "unknown",
        "child_check_result": "pass",
        "child_task_status": "done",
        "expected_acceptance_status": "unsafe_to_continue",
    },
    "missing-report-paths": {
        "description": "report_paths 缺失, 阻塞",
        "stdout": (
            "TASK_ID={task_id}\n"
            "CHECK_RESULT=pass\n"
            "TASK_STATUS=done\n"
            "REAL_TASK_EXECUTION=no\n"
            "CLAUDE_CODE_CALLED=no\n"
            "BUSINESS_CODE_CHANGED=no\n"
            "WORKTREE_STATUS=clean\n"
        ),
        "workspace_after": "clean",
        "workspace_classification": "clean",
        "claude_code_called": "no",
        "business_code_changed": "no",
        "child_check_result": "pass",
        "child_task_status": "done",
        "expected_acceptance_status": "blocked",
    },
}


@dataclass
class FirstRealRunExecutorSimulatedResult:
    """首次真实执行器模拟 child call 结果。

    通过三重确认 safety gate 后，构造 simulated child stdout，
    调用 parse_child_command_output() 和 evaluate_first_real_run_acceptance()，
    输出完整模拟执行结果。
    不真实调用 run-project-task-full，不调用 Claude Code，不修改业务代码。
    """

    project: str
    run_id: str
    task_id: str | None                       # 当前 NEXT_PENDING
    execution_mode: str                       # "first_real_run_executor_simulated_child_call"
    safety_gate_status: str                   # "passed" / "failed"
    real_execute_allowed: bool                # safety gate 是否通过
    simulated_child_call: bool                # 是否执行了 simulated child call
    child_sample: str                         # 使用的 sample 名称
    child_stdout_present: bool                # child stdout 是否非空
    child_stderr_present: bool                # child stderr 是否非空
    child_exit_code: int                      # child exit code（模拟为 0）
    child_check_result: str                   # "pass" / "fail" / "missing"
    child_task_status: str                    # "done" / "failed" / "unknown"
    parse_check_result: str                   # parser 的 parse_check_result
    acceptance_status: str                    # ready_for_human_review / blocked / failed_to_parse / unsafe_to_continue
    workspace_status_before: str              # "clean" / "dirty"
    workspace_status_after: str               # simulated workspace after
    workspace_change_classification: str      # simulated workspace classification
    real_task_execution: str                  # "no"
    run_project_task_full_called: str         # "no"
    claude_code_called: str                   # "no"
    business_code_changed: str                # "no"
    auto_continue_to_next_task: str           # "false"
    auto_git_backup: str                      # "false"
    human_review_required: str                # "true"
    check_result: str                         # "pass" / "fail"
    stop_reason: str | None                   # 停止原因
    next_action: str                          # 建议下一步
    message: str                              # 详细消息


def run_first_real_run_executor_simulated_child_call(
    project_path: str | Path,
    max_tasks: int = 1,
    confirm: str | None = None,
    real_confirm: str | None = None,
    real_execute_once: bool = False,
    real_execute_confirm: str | None = None,
    sample: str = "pass",
    real_call_dry_run: bool = False,
    adapter_dry_run: bool = False,
    real_call_stub: bool = False,
    dry_run_flag: bool = False,
) -> FirstRealRunExecutorSimulatedResult:
    """首次真实执行器模拟 child call。

    通过三重确认 safety gate 后，根据 sample 构造 child stdout，
    调用 parse_child_command_output() 和 evaluate_first_real_run_acceptance()。
    不执行任何真实命令，不调用 run-project-task-full，不调用 Claude Code。

    Args:
        project_path: 项目根目录
        max_tasks: max_tasks（必须为 1）
        confirm: 第一重确认短语
        real_confirm: 第二重确认短语
        real_execute_once: 是否传入 --real-execute-once
        real_execute_confirm: 第三重确认短语
        sample: child sample 名称
        real_call_dry_run: 是否同时传入了 --real-call-dry-run
        adapter_dry_run: 是否同时传入了 --adapter-dry-run
        real_call_stub: 是否同时传入了 --real-call-stub
        dry_run_flag: 是否同时传入了 --dry-run

    Returns:
        FirstRealRunExecutorSimulatedResult

    Raises:
        ValueError: sample 不存在时
    """
    project_path = Path(project_path)
    run_id = _generate_run_id()

    # --- 默认失败结果 ---
    def _fail(
        stop_reason: str | None = None,
        next_action: str = "fix_simulated_executor_preconditions",
        message: str = "",
        safety_gate_status: str = "failed",
    ) -> FirstRealRunExecutorSimulatedResult:
        return FirstRealRunExecutorSimulatedResult(
            project=str(project_path),
            run_id=run_id,
            task_id=None,
            execution_mode="first_real_run_executor_simulated_child_call",
            safety_gate_status=safety_gate_status,
            real_execute_allowed=False,
            simulated_child_call=False,
            child_sample=sample,
            child_stdout_present=False,
            child_stderr_present=False,
            child_exit_code=0,
            child_check_result="unknown",
            child_task_status="unknown",
            parse_check_result="fail",
            acceptance_status="blocked",
            workspace_status_before="unknown",
            workspace_status_after="unknown",
            workspace_change_classification="unknown",
            real_task_execution="no",
            run_project_task_full_called="no",
            claude_code_called="no",
            business_code_changed="no",
            auto_continue_to_next_task="false",
            auto_git_backup="false",
            human_review_required="true",
            check_result="fail",
            stop_reason=stop_reason,
            next_action=next_action,
            message=message,
        )

    # --- 1. 调用三重确认 safety gate ---
    safety = validate_first_real_run_execute_once_safety(
        project_path=project_path,
        max_tasks=max_tasks,
        confirm=confirm,
        real_confirm=real_confirm,
        real_execute_once=real_execute_once,
        real_execute_confirm=real_execute_confirm,
        real_call_dry_run=real_call_dry_run,
        adapter_dry_run=adapter_dry_run,
        real_call_stub=real_call_stub,
        dry_run_flag=dry_run_flag,
    )

    # --- 2. safety gate 不通过 → 直接返回失败 ---
    if not safety.real_execute_allowed:
        return _fail(
            stop_reason=safety.stop_reason,
            next_action=safety.next_action,
            message=(
                f"simulated child call 未启动：execute-once safety gate 拒绝"
                f"（{safety.stop_reason}）。"
                f"REAL_TASK_EXECUTION=no，RUN_PROJECT_TASK_FULL_CALLED=no。"
            ),
        )

    task_id = safety.task_id

    # --- 3. 验证 sample ---
    if sample not in _SIMULATED_CHILD_SAMPLES:
        available = ", ".join(sorted(_SIMULATED_CHILD_SAMPLES.keys()))
        return _fail(
            stop_reason=f"unknown_child_sample:{sample}",
            next_action="use_valid_child_sample",
            message=(
                f"错误：未知的 child sample '{sample}'。"
                f"可用样本：{available}。"
            ),
            safety_gate_status="passed",
        )

    sample_data = _SIMULATED_CHILD_SAMPLES[sample]

    # --- 4. 构造 simulated child stdout（不执行任何真实命令） ---
    child_stdout = sample_data["stdout"].format(task_id=task_id or "UNKNOWN")

    # --- 5. 调用 parse_child_command_output() ---
    child_parse = parse_child_command_output(
        stdout_text=child_stdout,
        stderr_text="",
        exit_code=0,
    )

    # --- 6. 调用 evaluate_first_real_run_acceptance() ---
    acceptance = evaluate_first_real_run_acceptance(
        project_path=project_path,
        task_id=task_id,
        child_parse_result=child_parse,
        workspace_status_before="clean",
        workspace_status_after=sample_data["workspace_after"],
        workspace_change_classification=sample_data["workspace_classification"],
        run_project_task_full_called="no",
        claude_code_called="no",
        business_code_changed="no",
    )

    # --- 7. 构造完整 simulated executor result ---
    check_result = "pass" if acceptance.check_result == "pass" else "fail"

    if acceptance.check_result == "pass":
        next_action = "ready_for_human_review"
    elif acceptance.acceptance_status == "failed_to_parse":
        next_action = "review_parse_failure"
    elif acceptance.acceptance_status == "unsafe_to_continue":
        next_action = "manual_review_required"
    else:
        next_action = "review_failure_before_continue"

    return FirstRealRunExecutorSimulatedResult(
        project=str(project_path),
        run_id=run_id,
        task_id=task_id,
        execution_mode="first_real_run_executor_simulated_child_call",
        safety_gate_status="passed",
        real_execute_allowed=True,
        simulated_child_call=True,
        child_sample=sample,
        child_stdout_present=child_parse.raw_stdout_present,
        child_stderr_present=child_parse.raw_stderr_present,
        child_exit_code=child_parse.exit_code,
        child_check_result=child_parse.check_result,
        child_task_status=child_parse.task_status,
        parse_check_result=child_parse.parse_check_result,
        acceptance_status=acceptance.acceptance_status,
        workspace_status_before=safety.workspace_status_before,
        workspace_status_after=sample_data["workspace_after"],
        workspace_change_classification=sample_data["workspace_classification"],
        real_task_execution="no",
        run_project_task_full_called="no",
        claude_code_called="no",
        business_code_changed="no",
        auto_continue_to_next_task="false",
        auto_git_backup="false",
        human_review_required="true",
        check_result=check_result,
        stop_reason=acceptance.stop_reason,
        next_action=next_action,
        message=(
            f"simulated child call 完成：sample={sample}，task_id={task_id}，"
            f"CHILD_CHECK_RESULT={child_parse.check_result}，"
            f"CHILD_TASK_STATUS={child_parse.task_status}，"
            f"ACCEPTANCE_STATUS={acceptance.acceptance_status}。"
            f"REAL_TASK_EXECUTION=no，RUN_PROJECT_TASK_FULL_CALLED=no。"
        ),
    )


# ---------------------------------------------------------------------------
# T117: No-Tool-Use Proposal Parser Dry-Run
# ---------------------------------------------------------------------------

# T116 schema 定义的 required fields
_PROPOSAL_REQUIRED_FIELDS = [
    "proposal_version",
    "execution_mode",
    "task",
    "intent",
    "scope",
    "changes",
    "safety",
    "validation",
    "next_action",
]

_PROPOSAL_REQUIRED_TASK_FIELDS = ["id", "title"]
_PROPOSAL_REQUIRED_SAFETY_FIELDS = [
    "real_task_execution",
    "run_project_task_full_called",
    "claude_code_tool_use_used",
    "auto_continue_to_next_task",
    "auto_git_backup",
    "bypass_permissions_used",
    "human_review_required",
]

_VALID_EXECUTION_MODE = "no_tool_use_single_task_proposal"
_VALID_PROPOSAL_TYPES = {
    "doc_only", "report_only", "patch_proposal",
    "command_only", "mixed_safe_proposal",
}


@dataclass
class NoToolUseProposalParseResult:
    """No-tool-use proposal 解析结果。

    只负责解析结构，不做 scope 校验、patch 校验或 command 执行。
    """
    # 核心字段
    proposal_version: str | None
    execution_mode: str | None
    task_id: str | None
    task_title: str | None
    change_type: str | None
    target_files: list[str]
    proposed_commands: list[str]
    expected_reports: list[str]

    # Safety 字段（parser 只读取，不校验）
    safety_declarations_present: bool
    human_review_required: str | None
    auto_continue_to_next_task: str | None
    auto_git_backup: str | None

    # 解析元信息
    next_action: str | None
    required_fields_missing: list[str]
    yaml_parse_error: str | None
    parse_status: str  # parsed / failed_to_parse / missing_required_fields / invalid_execution_mode
    check_result: str  # pass / fail
    message: str


def _extract_yaml_from_text(text: str) -> str | None:
    """从 Markdown 文本中提取 YAML proposal 块。

    支持 ```proposal 和 ```yaml 两种 fenced block。
    如果没有 fenced block，假设整段文本就是 YAML。
    """
    # 优先匹配 ```proposal
    pattern = r"```proposal\s*\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # 其次匹配 ```yaml
    pattern = r"```yaml\s*\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # 最后假设整段文本是 YAML（去除可能的 markdown 标题行）
    lines = text.strip().split("\n")
    yaml_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#") and not stripped.startswith("# "):
            # 可能是 YAML 注释，保留
            yaml_lines.append(line)
        elif stripped.startswith("# "):
            # Markdown 标题，跳过
            continue
        else:
            yaml_lines.append(line)
    result = "\n".join(yaml_lines).strip()
    return result if result else None


def parse_no_tool_use_execution_proposal(proposal_text: str) -> NoToolUseProposalParseResult:
    """解析 no-tool-use execution proposal 文本。

    职责：
    1. 从 Markdown fenced block 中提取 YAML
    2. 解析 YAML
    3. 提取 T116 schema 中的关键字段
    4. 检查 required fields 是否存在
    5. 检查 execution_mode 是否正确
    6. 返回 NoToolUseProposalParseResult

    不做 allowed scope 校验、patch 校验或 command 执行。
    """
    import yaml

    # --- 1. 提取 YAML ---
    yaml_text = _extract_yaml_from_text(proposal_text)
    if yaml_text is None:
        return NoToolUseProposalParseResult(
            proposal_version=None,
            execution_mode=None,
            task_id=None,
            task_title=None,
            change_type=None,
            target_files=[],
            proposed_commands=[],
            expected_reports=[],
            safety_declarations_present=False,
            human_review_required=None,
            auto_continue_to_next_task=None,
            auto_git_backup=None,
            next_action=None,
            required_fields_missing=[],
            yaml_parse_error="No YAML content found in proposal text",
            parse_status="failed_to_parse",
            check_result="fail",
            message="无法从文本中提取 YAML proposal 内容",
        )

    # --- 2. 解析 YAML ---
    try:
        data = yaml.safe_load(yaml_text)
    except yaml.YAMLError as e:
        return NoToolUseProposalParseResult(
            proposal_version=None,
            execution_mode=None,
            task_id=None,
            task_title=None,
            change_type=None,
            target_files=[],
            proposed_commands=[],
            expected_reports=[],
            safety_declarations_present=False,
            human_review_required=None,
            auto_continue_to_next_task=None,
            auto_git_backup=None,
            next_action=None,
            required_fields_missing=[],
            yaml_parse_error=str(e),
            parse_status="failed_to_parse",
            check_result="fail",
            message=f"YAML 解析失败：{e}",
        )

    if not isinstance(data, dict):
        return NoToolUseProposalParseResult(
            proposal_version=None,
            execution_mode=None,
            task_id=None,
            task_title=None,
            change_type=None,
            target_files=[],
            proposed_commands=[],
            expected_reports=[],
            safety_declarations_present=False,
            human_review_required=None,
            auto_continue_to_next_task=None,
            auto_git_backup=None,
            next_action=None,
            required_fields_missing=[],
            yaml_parse_error="YAML content is not a mapping",
            parse_status="failed_to_parse",
            check_result="fail",
            message="YAML 内容不是键值映射结构",
        )

    # --- 3. 检查 required fields ---
    missing: list[str] = []
    for f in _PROPOSAL_REQUIRED_FIELDS:
        if f not in data:
            missing.append(f)

    # 检查 task 子字段
    task_data = data.get("task")
    if isinstance(task_data, dict):
        for f in _PROPOSAL_REQUIRED_TASK_FIELDS:
            if f not in task_data:
                missing.append(f"task.{f}")
    elif "task" not in missing:
        # task 存在但不是 dict
        missing.append("task.id")
        missing.append("task.title")

    # 检查 safety 子字段
    safety_data = data.get("safety")
    safety_present = isinstance(safety_data, dict)
    missing_safety: list[str] = []
    if safety_present:
        for f in _PROPOSAL_REQUIRED_SAFETY_FIELDS:
            if f not in safety_data:
                missing_safety.append(f"safety.{f}")
                missing.append(f"safety.{f}")
    elif "safety" not in missing:
        # safety 存在但不是 dict
        for f in _PROPOSAL_REQUIRED_SAFETY_FIELDS:
            missing.append(f"safety.{f}")

    if missing:
        return NoToolUseProposalParseResult(
            proposal_version=data.get("proposal_version"),
            execution_mode=data.get("execution_mode"),
            task_id=task_data.get("id") if isinstance(task_data, dict) else None,
            task_title=task_data.get("title") if isinstance(task_data, dict) else None,
            change_type=data.get("changes", {}).get("type") if isinstance(data.get("changes"), dict) else None,
            target_files=_extract_target_files(data),
            proposed_commands=_extract_commands(data),
            expected_reports=_extract_reports(data),
            safety_declarations_present=safety_present and len(missing_safety) == 0,
            human_review_required=safety_data.get("human_review_required") if safety_present else None,
            auto_continue_to_next_task=safety_data.get("auto_continue_to_next_task") if safety_present else None,
            auto_git_backup=safety_data.get("auto_git_backup") if safety_present else None,
            next_action=data.get("next_action", {}).get("recommendation") if isinstance(data.get("next_action"), dict) else None,
            required_fields_missing=missing,
            yaml_parse_error=None,
            parse_status="missing_required_fields",
            check_result="fail",
            message=f"缺少必需字段：{', '.join(missing)}",
        )

    # --- 4. 检查 execution_mode ---
    execution_mode = data.get("execution_mode", "")
    if execution_mode != _VALID_EXECUTION_MODE:
        return NoToolUseProposalParseResult(
            proposal_version=data.get("proposal_version"),
            execution_mode=execution_mode,
            task_id=task_data.get("id") if isinstance(task_data, dict) else None,
            task_title=task_data.get("title") if isinstance(task_data, dict) else None,
            change_type=data.get("changes", {}).get("type") if isinstance(data.get("changes"), dict) else None,
            target_files=_extract_target_files(data),
            proposed_commands=_extract_commands(data),
            expected_reports=_extract_reports(data),
            safety_declarations_present=True,
            human_review_required=safety_data.get("human_review_required") if safety_present else None,
            auto_continue_to_next_task=safety_data.get("auto_continue_to_next_task") if safety_present else None,
            auto_git_backup=safety_data.get("auto_git_backup") if safety_present else None,
            next_action=data.get("next_action", {}).get("recommendation") if isinstance(data.get("next_action"), dict) else None,
            required_fields_missing=[],
            yaml_parse_error=None,
            parse_status="invalid_execution_mode",
            check_result="fail",
            message=f"execution_mode 不正确：期望 '{_VALID_EXECUTION_MODE}'，实际 '{execution_mode}'",
        )

    # --- 5. 全部通过，构造 parsed result ---
    return NoToolUseProposalParseResult(
        proposal_version=data.get("proposal_version"),
        execution_mode=execution_mode,
        task_id=task_data.get("id") if isinstance(task_data, dict) else None,
        task_title=task_data.get("title") if isinstance(task_data, dict) else None,
        change_type=data.get("changes", {}).get("type") if isinstance(data.get("changes"), dict) else None,
        target_files=_extract_target_files(data),
        proposed_commands=_extract_commands(data),
        expected_reports=_extract_reports(data),
        safety_declarations_present=True,
        human_review_required=safety_data.get("human_review_required"),
        auto_continue_to_next_task=safety_data.get("auto_continue_to_next_task"),
        auto_git_backup=safety_data.get("auto_git_backup"),
        next_action=data.get("next_action", {}).get("recommendation") if isinstance(data.get("next_action"), dict) else None,
        required_fields_missing=[],
        yaml_parse_error=None,
        parse_status="parsed",
        check_result="pass",
        message="Proposal 解析成功",
    )


def _extract_target_files(data: dict) -> list[str]:
    """从 parsed data 中提取 target_files 路径列表。"""
    changes = data.get("changes")
    if not isinstance(changes, dict):
        return []
    target_files = changes.get("target_files")
    if not isinstance(target_files, list):
        return []
    result: list[str] = []
    for item in target_files:
        if isinstance(item, dict) and "path" in item:
            result.append(item["path"])
        elif isinstance(item, str):
            result.append(item)
    return result


def _extract_commands(data: dict) -> list[str]:
    """从 parsed data 中提取 proposed commands 列表。"""
    commands = data.get("commands")
    if not isinstance(commands, dict):
        return []
    proposed = commands.get("proposed")
    if not isinstance(proposed, list):
        return []
    result: list[str] = []
    for item in proposed:
        if isinstance(item, dict) and "command" in item:
            result.append(item["command"])
        elif isinstance(item, str):
            result.append(item)
    return result


def _extract_reports(data: dict) -> list[str]:
    """从 parsed data 中提取 expected reports 路径列表。"""
    reports = data.get("reports")
    if not isinstance(reports, dict):
        return []
    expected = reports.get("expected")
    if not isinstance(expected, list):
        return []
    result: list[str] = []
    for item in expected:
        if isinstance(item, dict) and "path" in item:
            result.append(item["path"])
        elif isinstance(item, str):
            result.append(item)
    return result


# ---------------------------------------------------------------------------
# T117: 内置 sample proposals
# ---------------------------------------------------------------------------

_SAMPLE_PASS_PROPOSAL = """\
```yaml
proposal_version: "1.0"
execution_mode: "no_tool_use_single_task_proposal"

task:
  id: "T116"
  title: "Design no-tool-use execution proposal schema"
  source: "docs/tasks.md"

intent:
  summary: "Create the proposal schema document for no-tool-use execution mode"
  expected_outcome: "docs/no-tool-use-execution-proposal-schema.md created with complete schema definition"

scope:
  allowed_files:
    - "docs/no-tool-use-execution-proposal-schema.md"
    - "reports/dev/T116-dev-report.md"
  forbidden_files:
    - "runner.py"
    - "tools/*.py"
    - "projects/**"
  business_code_change: "no"
  framework_code_change: "no"

changes:
  type: "doc_only"
  target_files:
    - path: "docs/no-tool-use-execution-proposal-schema.md"
      change_type: "create"
      reason: "New schema design document"

safety:
  real_task_execution: "no"
  run_project_task_full_called: "no"
  claude_code_tool_use_used: "no"
  auto_continue_to_next_task: "no"
  auto_git_backup: "no"
  bypass_permissions_used: "no"
  human_review_required: "yes"

validation:
  expected_check_result: "pass"
  success_criteria:
    - "Schema document exists at docs/no-tool-use-execution-proposal-schema.md"
    - "Schema contains all required field definitions"

next_action:
  recommendation: "human_review"
```
"""

_SAMPLE_MISSING_REQUIRED_FIELD = """\
```yaml
proposal_version: "1.0"
execution_mode: "no_tool_use_single_task_proposal"

task:
  id: "T116"
  title: "Design no-tool-use execution proposal schema"

intent:
  summary: "Create the proposal schema document"
  expected_outcome: "Schema document created"

# scope is missing entirely

changes:
  type: "doc_only"
  target_files:
    - path: "docs/some-file.md"
      change_type: "create"
      reason: "New document"

safety:
  real_task_execution: "no"
  run_project_task_full_called: "no"
  claude_code_tool_use_used: "no"
  auto_continue_to_next_task: "no"
  auto_git_backup: "no"
  bypass_permissions_used: "no"
  human_review_required: "yes"

validation:
  expected_check_result: "pass"

next_action:
  recommendation: "human_review"
```
"""

_SAMPLE_INVALID_YAML = """\
```yaml
proposal_version: "1.0"
execution_mode: no_tool_use_single_task_proposal
task:
  id: "T116"
  title: Test proposal
  this is not valid yaml: [
    unclosed bracket
```
"""

_SAMPLE_INVALID_EXECUTION_MODE = """\
```yaml
proposal_version: "1.0"
execution_mode: "direct_tool_use_execution"

task:
  id: "T116"
  title: "Design schema"
  source: "docs/tasks.md"

intent:
  summary: "Do something"
  expected_outcome: "Result"

scope:
  allowed_files:
    - "docs/test.md"
  forbidden_files:
    - "runner.py"
  business_code_change: "no"
  framework_code_change: "no"

changes:
  type: "doc_only"
  target_files:
    - path: "docs/test.md"
      change_type: "create"
      reason: "Test"

safety:
  real_task_execution: "no"
  run_project_task_full_called: "no"
  claude_code_tool_use_used: "no"
  auto_continue_to_next_task: "no"
  auto_git_backup: "no"
  bypass_permissions_used: "no"
  human_review_required: "yes"

validation:
  expected_check_result: "pass"

next_action:
  recommendation: "human_review"
```
"""

_SAMPLE_MISSING_SAFETY = """\
```yaml
proposal_version: "1.0"
execution_mode: "no_tool_use_single_task_proposal"

task:
  id: "T116"
  title: "Design schema"
  source: "docs/tasks.md"

intent:
  summary: "Do something"
  expected_outcome: "Result"

scope:
  allowed_files:
    - "docs/test.md"
  forbidden_files:
    - "runner.py"
  business_code_change: "no"
  framework_code_change: "no"

changes:
  type: "doc_only"
  target_files:
    - path: "docs/test.md"
      change_type: "create"
      reason: "Test"

# safety is missing entirely

validation:
  expected_check_result: "pass"

next_action:
  recommendation: "human_review"
```
"""

_SAMPLE_AUTO_CONTINUE_REQUESTED = """\
```yaml
proposal_version: "1.0"
execution_mode: "no_tool_use_single_task_proposal"

task:
  id: "T116"
  title: "Design schema"
  source: "docs/tasks.md"

intent:
  summary: "Do something"
  expected_outcome: "Result"

scope:
  allowed_files:
    - "docs/test.md"
  forbidden_files:
    - "runner.py"
  business_code_change: "no"
  framework_code_change: "no"

changes:
  type: "doc_only"
  target_files:
    - path: "docs/test.md"
      change_type: "create"
      reason: "Test"

safety:
  real_task_execution: "no"
  run_project_task_full_called: "no"
  claude_code_tool_use_used: "no"
  auto_continue_to_next_task: "yes"
  auto_git_backup: "no"
  bypass_permissions_used: "no"
  human_review_required: "yes"

validation:
  expected_check_result: "pass"

next_action:
  recommendation: "human_review"
```
"""

_SAMPLE_AUTO_GIT_BACKUP_REQUESTED = """\
```yaml
proposal_version: "1.0"
execution_mode: "no_tool_use_single_task_proposal"

task:
  id: "T116"
  title: "Design schema"
  source: "docs/tasks.md"

intent:
  summary: "Do something"
  expected_outcome: "Result"

scope:
  allowed_files:
    - "docs/test.md"
  forbidden_files:
    - "runner.py"
  business_code_change: "no"
  framework_code_change: "no"

changes:
  type: "doc_only"
  target_files:
    - path: "docs/test.md"
      change_type: "create"
      reason: "Test"

safety:
  real_task_execution: "no"
  run_project_task_full_called: "no"
  claude_code_tool_use_used: "no"
  auto_continue_to_next_task: "no"
  auto_git_backup: "yes"
  bypass_permissions_used: "no"
  human_review_required: "yes"

validation:
  expected_check_result: "pass"

next_action:
  recommendation: "human_review"
```
"""

_PARSER_SAMPLES: dict[str, str] = {
    "pass": _SAMPLE_PASS_PROPOSAL,
    "missing-required-field": _SAMPLE_MISSING_REQUIRED_FIELD,
    "invalid-yaml": _SAMPLE_INVALID_YAML,
    "invalid-execution-mode": _SAMPLE_INVALID_EXECUTION_MODE,
    "missing-safety": _SAMPLE_MISSING_SAFETY,
    "auto-continue-requested": _SAMPLE_AUTO_CONTINUE_REQUESTED,
    "auto-git-backup-requested": _SAMPLE_AUTO_GIT_BACKUP_REQUESTED,
}


def run_no_tool_use_proposal_parser_dry_run(sample: str = "pass") -> NoToolUseProposalParseResult:
    """运行 proposal parser dry-run。

    使用内置 sample 文本作为 parser 输入，不读取任何外部文件。
    不执行命令、不应用 patch、不修改任何文件。

    Args:
        sample: 样本类型名称，必须在 _PARSER_SAMPLES 中存在。
    """
    if sample not in _PARSER_SAMPLES:
        available = ", ".join(sorted(_PARSER_SAMPLES.keys()))
        return NoToolUseProposalParseResult(
            proposal_version=None,
            execution_mode=None,
            task_id=None,
            task_title=None,
            change_type=None,
            target_files=[],
            proposed_commands=[],
            expected_reports=[],
            safety_declarations_present=False,
            human_review_required=None,
            auto_continue_to_next_task=None,
            auto_git_backup=None,
            next_action=None,
            required_fields_missing=[],
            yaml_parse_error=f"Unknown sample: {sample}",
            parse_status="failed_to_parse",
            check_result="fail",
            message=f"未知 sample '{sample}'。可用样本：{available}",
        )

    text = _PARSER_SAMPLES[sample]
    result = parse_no_tool_use_execution_proposal(text)

    # auto-continue 和 auto-git-backup 样本在 parser 层面可以解析成功
    # 但这些字段值违反安全约束，parser 只读取字段值，validator 负责拒绝
    # 为保持 dry-run 场景覆盖，将 check_result 标记为 fail
    if sample == "auto-continue-requested" and result.parse_status == "parsed":
        return NoToolUseProposalParseResult(
            proposal_version=result.proposal_version,
            execution_mode=result.execution_mode,
            task_id=result.task_id,
            task_title=result.task_title,
            change_type=result.change_type,
            target_files=result.target_files,
            proposed_commands=result.proposed_commands,
            expected_reports=result.expected_reports,
            safety_declarations_present=result.safety_declarations_present,
            human_review_required=result.human_review_required,
            auto_continue_to_next_task=result.auto_continue_to_next_task,
            auto_git_backup=result.auto_git_backup,
            next_action=result.next_action,
            required_fields_missing=result.required_fields_missing,
            yaml_parse_error=result.yaml_parse_error,
            parse_status="parsed",
            check_result="fail",
            message=f"Proposal 解析成功，但 auto_continue_to_next_task={result.auto_continue_to_next_task} 违反安全约束",
        )

    if sample == "auto-git-backup-requested" and result.parse_status == "parsed":
        return NoToolUseProposalParseResult(
            proposal_version=result.proposal_version,
            execution_mode=result.execution_mode,
            task_id=result.task_id,
            task_title=result.task_title,
            change_type=result.change_type,
            target_files=result.target_files,
            proposed_commands=result.proposed_commands,
            expected_reports=result.expected_reports,
            safety_declarations_present=result.safety_declarations_present,
            human_review_required=result.human_review_required,
            auto_continue_to_next_task=result.auto_continue_to_next_task,
            auto_git_backup=result.auto_git_backup,
            next_action=result.next_action,
            required_fields_missing=result.required_fields_missing,
            yaml_parse_error=result.yaml_parse_error,
            parse_status="parsed",
            check_result="fail",
            message=f"Proposal 解析成功，但 auto_git_backup={result.auto_git_backup} 违反安全约束",
        )

    return result


# ---------------------------------------------------------------------------
# T118: No-Tool-Use Allowed Scope Validator Dry-Run
# ---------------------------------------------------------------------------

def _has_path_traversal(file_path: str) -> bool:
    """检查文件路径是否包含路径逃逸 (..)。"""
    parts = file_path.replace("\\", "/").split("/")
    return ".." in parts


def _is_absolute_path(file_path: str) -> bool:
    """检查文件路径是否是绝对路径。"""
    if file_path.startswith("/"):
        return True
    if len(file_path) >= 2 and file_path[1] == ":":
        return True
    return False


def _path_matches_pattern(file_path: str, pattern: str) -> bool:
    """检查文件路径是否匹配指定模式。

    支持：
    - 精确匹配：pattern == file_path
    - 递归通配："projects/**" 匹配 "projects/a/b/c"
    - 单层通配："tools/*.py" 匹配 "tools/test.py"
    """
    import fnmatch

    if pattern == file_path:
        return True

    if pattern.endswith("/**"):
        prefix = pattern[:-3]
        if file_path.startswith(prefix + "/") or file_path == prefix:
            return True
        return False

    if "*" in pattern:
        return fnmatch.fnmatch(file_path, pattern)

    return False


def _is_path_in_scope(file_path: str, allowed_patterns: list[str]) -> bool:
    """检查文件路径是否在 allowed scope 内。保守原则：空列表则 fail。"""
    if not allowed_patterns:
        return False
    return any(_path_matches_pattern(file_path, p) for p in allowed_patterns)


def _is_path_forbidden(file_path: str, forbidden_patterns: list[str]) -> bool:
    """检查文件路径是否命中 forbidden scope。"""
    if not forbidden_patterns:
        return False
    return any(_path_matches_pattern(file_path, p) for p in forbidden_patterns)


@dataclass
class NoToolUseAllowedScopeValidationResult:
    """No-tool-use allowed scope validation result。

    只做 scope 和 safety 校验，不应用 patch，不执行 command。
    """
    # Parse 状态
    parse_status: str
    parse_check_result: str
    validation_status: str  # validated / failed_parse / failed_scope / failed_safety

    # Proposal 基本信息
    proposal_version: str | None
    execution_mode: str | None
    task_id: str | None
    change_type: str | None

    # Scope 信息
    allowed_files: list[str]
    forbidden_files: list[str]
    target_files: list[str]
    proposed_commands: list[str]
    expected_reports: list[str]

    # Scope 校验结果
    allowed_scope_pass: bool
    forbidden_scope_pass: bool

    # Safety 校验结果
    safety_declarations_pass: bool
    human_review_required_pass: bool
    auto_continue_pass: bool
    auto_git_backup_pass: bool

    # 安全保证（dry-run 硬编码）
    command_execution_blocked: bool   # 始终 True
    patch_apply_blocked: bool         # 始终 True
    real_task_execution: str          # 始终 "no"
    run_project_task_full_called: str # 始终 "no"
    claude_code_called: str           # 始终 "no"
    business_code_changed: str        # 始终 "no"
    framework_code_changed: str       # 始终 "no"

    # 违规列表
    violations: list[str]

    # 最终结果
    check_result: str  # pass / fail
    message: str


def validate_no_tool_use_allowed_scope_dry_run(
    proposal_text: str,
) -> NoToolUseAllowedScopeValidationResult:
    """验证 no-tool-use proposal 的 allowed scope。

    职责：
    1. 调用 parse_no_tool_use_execution_proposal() 解析 proposal
    2. 如果 parse fail，返回 failed_parse
    3. 从原始 YAML 中提取 scope.allowed_files 和 scope.forbidden_files
    4. 校验 target_files 是否被 allowed_files 覆盖
    5. 校验 target_files 是否命中 forbidden_files
    6. 校验路径安全（无 ../ 逃逸，无绝对路径）
    7. 校验 safety declarations
    8. 返回 validation result

    不应用 patch，不执行 command。
    """
    import yaml

    # Step 1: 解析 proposal
    parse_result = parse_no_tool_use_execution_proposal(proposal_text)

    # Step 2: Parse 失败 → 返回 failed_parse
    if parse_result.parse_status != "parsed":
        return NoToolUseAllowedScopeValidationResult(
            parse_status=parse_result.parse_status,
            parse_check_result=parse_result.check_result,
            validation_status="failed_parse",
            proposal_version=parse_result.proposal_version,
            execution_mode=parse_result.execution_mode,
            task_id=parse_result.task_id,
            change_type=parse_result.change_type,
            allowed_files=[],
            forbidden_files=[],
            target_files=parse_result.target_files,
            proposed_commands=parse_result.proposed_commands,
            expected_reports=parse_result.expected_reports,
            allowed_scope_pass=False,
            forbidden_scope_pass=False,
            safety_declarations_pass=False,
            human_review_required_pass=False,
            auto_continue_pass=False,
            auto_git_backup_pass=False,
            command_execution_blocked=True,
            patch_apply_blocked=True,
            real_task_execution="no",
            run_project_task_full_called="no",
            claude_code_called="no",
            business_code_changed="no",
            framework_code_changed="no",
            violations=[f"Proposal parse failed: {parse_result.message}"],
            check_result="fail",
            message=f"Proposal 解析失败，无法进行 scope 校验：{parse_result.message}",
        )

    # Step 3: 从原始 YAML 提取 scope 数据
    yaml_text = _extract_yaml_from_text(proposal_text)
    data = yaml.safe_load(yaml_text)

    scope_data = data.get("scope", {})
    if not isinstance(scope_data, dict):
        scope_data = {}
    allowed_files = scope_data.get("allowed_files", [])
    forbidden_files = scope_data.get("forbidden_files", [])
    if not isinstance(allowed_files, list):
        allowed_files = []
    if not isinstance(forbidden_files, list):
        forbidden_files = []

    # Step 4: 校验 target_files
    violations: list[str] = []
    allowed_scope_pass = True
    forbidden_scope_pass = True

    for tf in parse_result.target_files:
        # 路径逃逸检查
        if _has_path_traversal(tf):
            violations.append(f"Path traversal detected: {tf}")
            allowed_scope_pass = False
            continue

        # 绝对路径检查
        if _is_absolute_path(tf):
            violations.append(f"Absolute path detected: {tf}")
            allowed_scope_pass = False
            continue

        # allowed_files 覆盖检查
        if not _is_path_in_scope(tf, allowed_files):
            violations.append(f"Target file not in allowed scope: {tf}")
            allowed_scope_pass = False

        # forbidden_files 命中检查
        if _is_path_forbidden(tf, forbidden_files):
            violations.append(f"Target file in forbidden scope: {tf}")
            forbidden_scope_pass = False

    # Step 5: 校验 safety declarations
    safety_data = data.get("safety", {})
    if not isinstance(safety_data, dict):
        safety_data = {}

    safety_violations: list[str] = []

    if safety_data.get("human_review_required") != "yes":
        safety_violations.append("human_review_required must be 'yes'")
    human_review_required_pass = safety_data.get("human_review_required") == "yes"

    if safety_data.get("auto_continue_to_next_task") != "no":
        safety_violations.append("auto_continue_to_next_task must be 'no'")
    auto_continue_pass = safety_data.get("auto_continue_to_next_task") == "no"

    if safety_data.get("auto_git_backup") != "no":
        safety_violations.append("auto_git_backup must be 'no'")
    auto_git_backup_pass = safety_data.get("auto_git_backup") == "no"

    if safety_data.get("real_task_execution") != "no":
        safety_violations.append("real_task_execution must be 'no'")
    if safety_data.get("run_project_task_full_called") != "no":
        safety_violations.append("run_project_task_full_called must be 'no'")
    if safety_data.get("claude_code_tool_use_used") != "no":
        safety_violations.append("claude_code_tool_use_used must be 'no'")

    safety_declarations_pass = (
        human_review_required_pass
        and auto_continue_pass
        and auto_git_backup_pass
        and safety_data.get("real_task_execution") == "no"
        and safety_data.get("run_project_task_full_called") == "no"
        and safety_data.get("claude_code_tool_use_used") == "no"
    )

    violations.extend(safety_violations)

    # Step 6: 确定 validation_status 和 check_result
    if not allowed_scope_pass or not forbidden_scope_pass:
        validation_status = "failed_scope"
    elif not safety_declarations_pass:
        validation_status = "failed_safety"
    else:
        validation_status = "validated"

    check_result = "pass" if (
        allowed_scope_pass
        and forbidden_scope_pass
        and safety_declarations_pass
    ) else "fail"

    message = (
        "Scope validation passed" if check_result == "pass"
        else f"Scope validation failed: {'; '.join(violations)}"
    )

    return NoToolUseAllowedScopeValidationResult(
        parse_status=parse_result.parse_status,
        parse_check_result=parse_result.check_result,
        validation_status=validation_status,
        proposal_version=parse_result.proposal_version,
        execution_mode=parse_result.execution_mode,
        task_id=parse_result.task_id,
        change_type=parse_result.change_type,
        allowed_files=allowed_files,
        forbidden_files=forbidden_files,
        target_files=parse_result.target_files,
        proposed_commands=parse_result.proposed_commands,
        expected_reports=parse_result.expected_reports,
        allowed_scope_pass=allowed_scope_pass,
        forbidden_scope_pass=forbidden_scope_pass,
        safety_declarations_pass=safety_declarations_pass,
        human_review_required_pass=human_review_required_pass,
        auto_continue_pass=auto_continue_pass,
        auto_git_backup_pass=auto_git_backup_pass,
        command_execution_blocked=True,
        patch_apply_blocked=True,
        real_task_execution="no",
        run_project_task_full_called="no",
        claude_code_called="no",
        business_code_changed="no",
        framework_code_changed="no",
        violations=violations,
        check_result=check_result,
        message=message,
    )


# ---------------------------------------------------------------------------
# T118: 内置 validator dry-run samples
# ---------------------------------------------------------------------------

_VALIDATOR_SAMPLE_PASS = """\
```yaml
proposal_version: "1.0"
execution_mode: "no_tool_use_single_task_proposal"

task:
  id: "T118"
  title: "Implement allowed scope validator dry-run"
  source: "docs/tasks.md"

intent:
  summary: "Implement scope validator for no-tool-use proposals"
  expected_outcome: "Validator checks allowed_files, forbidden_files, path safety, and safety declarations"

scope:
  allowed_files:
    - "tools/continuous_task_planner.py"
    - "runner.py"
    - "reports/dev/T118-dev-report.md"
    - "reports/checks/T118-validator-dry-run-check.md"
  forbidden_files:
    - "projects/**"
    - "tools/rework_manager.py"
  business_code_change: "no"
  framework_code_change: "yes"

changes:
  type: "mixed_safe_proposal"
  target_files:
    - path: "tools/continuous_task_planner.py"
      change_type: "modify"
      reason: "Add validator dataclass and function"
    - path: "runner.py"
      change_type: "modify"
      reason: "Add validator dry-run CLI command"
    - path: "reports/dev/T118-dev-report.md"
      change_type: "create"
      reason: "Development report"

safety:
  real_task_execution: "no"
  run_project_task_full_called: "no"
  claude_code_tool_use_used: "no"
  auto_continue_to_next_task: "no"
  auto_git_backup: "no"
  bypass_permissions_used: "no"
  human_review_required: "yes"

validation:
  expected_check_result: "pass"
  success_criteria:
    - "Validator checks 9 scenarios pass/fail"

next_action:
  recommendation: "human_review"
```
"""

_VALIDATOR_SAMPLE_TARGET_OUTSIDE_ALLOWED = """\
```yaml
proposal_version: "1.0"
execution_mode: "no_tool_use_single_task_proposal"

task:
  id: "T118"
  title: "Test target outside allowed scope"
  source: "docs/tasks.md"

intent:
  summary: "Test that target files must be in allowed scope"
  expected_outcome: "Validator should reject target outside allowed_files"

scope:
  allowed_files:
    - "docs/**"
  forbidden_files:
    - "runner.py"
  business_code_change: "no"
  framework_code_change: "no"

changes:
  type: "doc_only"
  target_files:
    - path: "reports/checks/T118-check.md"
      change_type: "create"
      reason: "This file is NOT in allowed_files (only docs/** allowed)"

safety:
  real_task_execution: "no"
  run_project_task_full_called: "no"
  claude_code_tool_use_used: "no"
  auto_continue_to_next_task: "no"
  auto_git_backup: "no"
  bypass_permissions_used: "no"
  human_review_required: "yes"

validation:
  expected_check_result: "fail"

next_action:
  recommendation: "human_review"
```
"""

_VALIDATOR_SAMPLE_FORBIDDEN_FILE = """\
```yaml
proposal_version: "1.0"
execution_mode: "no_tool_use_single_task_proposal"

task:
  id: "T118"
  title: "Test forbidden file detection"
  source: "docs/tasks.md"

intent:
  summary: "Test that target files must not match forbidden_files"
  expected_outcome: "Validator should reject forbidden target file"

scope:
  allowed_files:
    - "runner.py"
    - "tools/**"
  forbidden_files:
    - "runner.py"
    - "projects/**"
  business_code_change: "no"
  framework_code_change: "yes"

changes:
  type: "patch_proposal"
  target_files:
    - path: "runner.py"
      change_type: "modify"
      reason: "This file is in both allowed and forbidden lists"

safety:
  real_task_execution: "no"
  run_project_task_full_called: "no"
  claude_code_tool_use_used: "no"
  auto_continue_to_next_task: "no"
  auto_git_backup: "no"
  bypass_permissions_used: "no"
  human_review_required: "yes"

validation:
  expected_check_result: "fail"

next_action:
  recommendation: "human_review"
```
"""

_VALIDATOR_SAMPLE_PATH_TRAVERSAL = """\
```yaml
proposal_version: "1.0"
execution_mode: "no_tool_use_single_task_proposal"

task:
  id: "T118"
  title: "Test path traversal detection"
  source: "docs/tasks.md"

intent:
  summary: "Test that path traversal (..) is detected and blocked"
  expected_outcome: "Validator should reject path traversal"

scope:
  allowed_files:
    - "../../etc/**"
    - "docs/**"
  forbidden_files:
    - "projects/**"
  business_code_change: "no"
  framework_code_change: "no"

changes:
  type: "doc_only"
  target_files:
    - path: "../../etc/passwd"
      change_type: "read"
      reason: "Path traversal attempt"

safety:
  real_task_execution: "no"
  run_project_task_full_called: "no"
  claude_code_tool_use_used: "no"
  auto_continue_to_next_task: "no"
  auto_git_backup: "no"
  bypass_permissions_used: "no"
  human_review_required: "yes"

validation:
  expected_check_result: "fail"

next_action:
  recommendation: "human_review"
```
"""

_VALIDATOR_SAMPLE_ABSOLUTE_PATH = """\
```yaml
proposal_version: "1.0"
execution_mode: "no_tool_use_single_task_proposal"

task:
  id: "T118"
  title: "Test absolute path detection"
  source: "docs/tasks.md"

intent:
  summary: "Test that absolute paths are detected and blocked"
  expected_outcome: "Validator should reject absolute path"

scope:
  allowed_files:
    - "/etc/**"
    - "docs/**"
  forbidden_files:
    - "projects/**"
  business_code_change: "no"
  framework_code_change: "no"

changes:
  type: "doc_only"
  target_files:
    - path: "/etc/passwd"
      change_type: "read"
      reason: "Absolute path attempt"

safety:
  real_task_execution: "no"
  run_project_task_full_called: "no"
  claude_code_tool_use_used: "no"
  auto_continue_to_next_task: "no"
  auto_git_backup: "no"
  bypass_permissions_used: "no"
  human_review_required: "yes"

validation:
  expected_check_result: "fail"

next_action:
  recommendation: "human_review"
```
"""

_VALIDATOR_SAMPLE_MISSING_HUMAN_REVIEW = """\
```yaml
proposal_version: "1.0"
execution_mode: "no_tool_use_single_task_proposal"

task:
  id: "T118"
  title: "Test missing human review detection"
  source: "docs/tasks.md"

intent:
  summary: "Test that human_review_required must be yes"
  expected_outcome: "Validator should reject when human_review_required is not yes"

scope:
  allowed_files:
    - "docs/**"
  forbidden_files:
    - "projects/**"
  business_code_change: "no"
  framework_code_change: "no"

changes:
  type: "doc_only"
  target_files:
    - path: "docs/test.md"
      change_type: "create"
      reason: "Test file"

safety:
  real_task_execution: "no"
  run_project_task_full_called: "no"
  claude_code_tool_use_used: "no"
  auto_continue_to_next_task: "no"
  auto_git_backup: "no"
  bypass_permissions_used: "no"
  human_review_required: "no"

validation:
  expected_check_result: "fail"

next_action:
  recommendation: "human_review"
```
"""

_VALIDATOR_SAMPLE_AUTO_CONTINUE_REQUESTED = """\
```yaml
proposal_version: "1.0"
execution_mode: "no_tool_use_single_task_proposal"

task:
  id: "T118"
  title: "Test auto-continue detection"
  source: "docs/tasks.md"

intent:
  summary: "Test that auto_continue_to_next_task must be no"
  expected_outcome: "Validator should reject when auto_continue is yes"

scope:
  allowed_files:
    - "docs/**"
  forbidden_files:
    - "projects/**"
  business_code_change: "no"
  framework_code_change: "no"

changes:
  type: "doc_only"
  target_files:
    - path: "docs/test.md"
      change_type: "create"
      reason: "Test file"

safety:
  real_task_execution: "no"
  run_project_task_full_called: "no"
  claude_code_tool_use_used: "no"
  auto_continue_to_next_task: "yes"
  auto_git_backup: "no"
  bypass_permissions_used: "no"
  human_review_required: "yes"

validation:
  expected_check_result: "fail"

next_action:
  recommendation: "human_review"
```
"""

_VALIDATOR_SAMPLE_AUTO_GIT_BACKUP_REQUESTED = """\
```yaml
proposal_version: "1.0"
execution_mode: "no_tool_use_single_task_proposal"

task:
  id: "T118"
  title: "Test auto-git-backup detection"
  source: "docs/tasks.md"

intent:
  summary: "Test that auto_git_backup must be no"
  expected_outcome: "Validator should reject when auto_git_backup is yes"

scope:
  allowed_files:
    - "docs/**"
  forbidden_files:
    - "projects/**"
  business_code_change: "no"
  framework_code_change: "no"

changes:
  type: "doc_only"
  target_files:
    - path: "docs/test.md"
      change_type: "create"
      reason: "Test file"

safety:
  real_task_execution: "no"
  run_project_task_full_called: "no"
  claude_code_tool_use_used: "no"
  auto_continue_to_next_task: "no"
  auto_git_backup: "yes"
  bypass_permissions_used: "no"
  human_review_required: "yes"

validation:
  expected_check_result: "fail"

next_action:
  recommendation: "human_review"
```
"""

_VALIDATOR_SAMPLE_PARSE_FAIL = """\
```yaml
proposal_version: "1.0"
execution_mode: no_tool_use_single_task_proposal
task:
  id: "T118"
  title: Test parse failure
  this is not valid yaml: [
    unclosed bracket
```
"""

_VALIDATOR_SAMPLES: dict[str, str] = {
    "pass": _VALIDATOR_SAMPLE_PASS,
    "target-outside-allowed": _VALIDATOR_SAMPLE_TARGET_OUTSIDE_ALLOWED,
    "forbidden-file": _VALIDATOR_SAMPLE_FORBIDDEN_FILE,
    "path-traversal": _VALIDATOR_SAMPLE_PATH_TRAVERSAL,
    "absolute-path": _VALIDATOR_SAMPLE_ABSOLUTE_PATH,
    "missing-human-review": _VALIDATOR_SAMPLE_MISSING_HUMAN_REVIEW,
    "auto-continue-requested": _VALIDATOR_SAMPLE_AUTO_CONTINUE_REQUESTED,
    "auto-git-backup-requested": _VALIDATOR_SAMPLE_AUTO_GIT_BACKUP_REQUESTED,
    "parse-fail": _VALIDATOR_SAMPLE_PARSE_FAIL,
}


def run_no_tool_use_allowed_scope_validator_dry_run(
    sample: str = "pass",
) -> NoToolUseAllowedScopeValidationResult:
    """运行 allowed scope validator dry-run。

    使用内置 sample 文本作为 validator 输入，不读取任何外部文件。
    不执行命令、不应用 patch、不修改任何文件。

    Args:
        sample: 样本类型名称，必须在 _VALIDATOR_SAMPLES 中存在。
    """
    if sample not in _VALIDATOR_SAMPLES:
        available = ", ".join(sorted(_VALIDATOR_SAMPLES.keys()))
        return NoToolUseAllowedScopeValidationResult(
            parse_status="failed_to_parse",
            parse_check_result="fail",
            validation_status="failed_parse",
            proposal_version=None,
            execution_mode=None,
            task_id=None,
            change_type=None,
            allowed_files=[],
            forbidden_files=[],
            target_files=[],
            proposed_commands=[],
            expected_reports=[],
            allowed_scope_pass=False,
            forbidden_scope_pass=False,
            safety_declarations_pass=False,
            human_review_required_pass=False,
            auto_continue_pass=False,
            auto_git_backup_pass=False,
            command_execution_blocked=True,
            patch_apply_blocked=True,
            real_task_execution="no",
            run_project_task_full_called="no",
            claude_code_called="no",
            business_code_changed="no",
            framework_code_changed="no",
            violations=[f"Unknown validator sample: {sample}"],
            check_result="fail",
            message=f"未知 validator sample '{sample}'。可用样本：{available}",
        )

    text = _VALIDATOR_SAMPLES[sample]
    return validate_no_tool_use_allowed_scope_dry_run(text)


# ---------------------------------------------------------------------------
# T119: No-Tool-Use Controlled Patch Apply Dry-Run
# ---------------------------------------------------------------------------

def _extract_diff_file(diff_text: str) -> str | None:
    """从 unified diff 文本中提取目标文件路径。"""
    # Try +++ b/<file> pattern
    match = re.search(r"^\+\+\+ b/(.+)$", diff_text, re.MULTILINE)
    if match:
        return match.group(1).strip()
    # Try diff --git a/<file> b/<file> pattern
    match = re.search(r"^diff --git a/.+ b/(.+)$", diff_text, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


def _is_patch_empty(diff_text: str) -> bool:
    """检查 patch 是否为空（无实际变更行）。"""
    for line in diff_text.split("\n"):
        if line.startswith("+") and not line.startswith("+++"):
            return False
        if line.startswith("-") and not line.startswith("---"):
            return False
    return True


def _is_valid_unified_diff(diff_text: str) -> bool:
    """检查文本是否是有效的 unified diff 格式。"""
    has_minus = bool(re.search(r"^--- ", diff_text, re.MULTILINE))
    has_plus = bool(re.search(r"^\+\+\+ ", diff_text, re.MULTILINE))
    has_hunk = bool(re.search(r"^@@ ", diff_text, re.MULTILINE))
    return has_minus and has_plus and has_hunk


@dataclass
class NoToolUseControlledPatchApplyDryRunResult:
    """No-tool-use controlled patch apply dry-run result。

    只解析、分类和预览 patch，不真实应用。
    """
    # Parse + Validation 状态
    parse_status: str
    parse_check_result: str
    validation_status: str
    validation_check_result: str
    patch_dry_run_status: str  # ready_for_future_apply / failed_parse / failed_validation / no_patch / unsafe_patch

    # Proposal 基本信息
    proposal_version: str | None
    execution_mode: str | None
    task_id: str | None
    change_type: str | None

    # 文件信息
    target_files: list[str]
    patch_files: list[str]       # patches[].file 声明的文件
    patch_count: int             # patches 数量
    empty_patch: bool            # 是否有空 patch

    # Scope 校验（patch 层面）
    allowed_scope_pass: bool
    forbidden_scope_pass: bool

    # Patch 解析
    patch_parse_pass: bool       # unified diff 格式是否正确
    patch_file_consistency_pass: bool  # patch file 是否与 target_files 一致

    # 安全保证（dry-run 硬编码）
    patch_apply_blocked: bool    # 始终 True
    command_execution_blocked: bool  # 始终 True
    real_patch_applied: str      # 始终 "no"
    real_task_execution: str     # 始终 "no"
    run_project_task_full_called: str
    claude_code_called: str
    business_code_changed: str
    framework_code_changed: str

    # 人工审查
    human_review_required: str   # 始终 "yes"

    # 是否准备就绪进入 future controlled apply
    ready_for_future_controlled_apply: bool

    # 违规列表
    violations: list[str]

    # 最终结果
    check_result: str  # pass / fail
    message: str


def run_no_tool_use_controlled_patch_apply_dry_run(
    proposal_text: str,
) -> NoToolUseControlledPatchApplyDryRunResult:
    """模拟 controlled patch apply dry-run。

    职责：
    1. 复用 T118 validator 校验 parse 和 scope
    2. 如果 parse fail 或 validation fail，立即返回
    3. 读取 patches 列表
    4. 检查 patch 是否存在（patch_proposal / mixed_safe_proposal 类型需要）
    5. 检查每个 patch 的格式、文件一致性和 scope
    6. 输出 ready_for_future_controlled_apply
    7. 不真实 apply patch，不执行 command

    不修改任何文件。
    """
    import yaml

    # Step 1: 复用 T118 validator
    validation = validate_no_tool_use_allowed_scope_dry_run(proposal_text)

    # Step 2: Parse 失败
    if validation.parse_status != "parsed":
        return NoToolUseControlledPatchApplyDryRunResult(
            parse_status=validation.parse_status,
            parse_check_result=validation.parse_check_result,
            validation_status=validation.validation_status,
            validation_check_result=validation.check_result,
            patch_dry_run_status="failed_parse",
            proposal_version=validation.proposal_version,
            execution_mode=validation.execution_mode,
            task_id=validation.task_id,
            change_type=validation.change_type,
            target_files=validation.target_files,
            patch_files=[],
            patch_count=0,
            empty_patch=False,
            allowed_scope_pass=False,
            forbidden_scope_pass=False,
            patch_parse_pass=False,
            patch_file_consistency_pass=False,
            patch_apply_blocked=True,
            command_execution_blocked=True,
            real_patch_applied="no",
            real_task_execution="no",
            run_project_task_full_called="no",
            claude_code_called="no",
            business_code_changed="no",
            framework_code_changed="no",
            human_review_required="yes",
            ready_for_future_controlled_apply=False,
            violations=[f"Proposal parse failed: {validation.message}"],
            check_result="fail",
            message=f"Proposal 解析失败，无法进行 patch apply dry-run：{validation.message}",
        )

    # Step 3: Validation 失败
    if validation.check_result != "pass":
        return NoToolUseControlledPatchApplyDryRunResult(
            parse_status=validation.parse_status,
            parse_check_result=validation.parse_check_result,
            validation_status=validation.validation_status,
            validation_check_result=validation.check_result,
            patch_dry_run_status="failed_validation",
            proposal_version=validation.proposal_version,
            execution_mode=validation.execution_mode,
            task_id=validation.task_id,
            change_type=validation.change_type,
            target_files=validation.target_files,
            patch_files=[],
            patch_count=0,
            empty_patch=False,
            allowed_scope_pass=False,
            forbidden_scope_pass=False,
            patch_parse_pass=False,
            patch_file_consistency_pass=False,
            patch_apply_blocked=True,
            command_execution_blocked=True,
            real_patch_applied="no",
            real_task_execution="no",
            run_project_task_full_called="no",
            claude_code_called="no",
            business_code_changed="no",
            framework_code_changed="no",
            human_review_required="yes",
            ready_for_future_controlled_apply=False,
            violations=[f"Scope validation failed: {validation.message}"],
            check_result="fail",
            message=f"Scope 校验失败，无法进行 patch apply dry-run：{validation.message}",
        )

    # Step 4: 从原始 YAML 提取 patches
    yaml_text = _extract_yaml_from_text(proposal_text)
    data = yaml.safe_load(yaml_text)

    patches_data = data.get("patches")
    change_type = validation.change_type or ""
    requires_patches = change_type in ("patch_proposal", "mixed_safe_proposal")

    # Step 5: 检查 patches 是否存在
    if not isinstance(patches_data, list) or len(patches_data) == 0:
        if requires_patches:
            return NoToolUseControlledPatchApplyDryRunResult(
                parse_status=validation.parse_status,
                parse_check_result=validation.parse_check_result,
                validation_status=validation.validation_status,
                validation_check_result=validation.check_result,
                patch_dry_run_status="no_patch",
                proposal_version=validation.proposal_version,
                execution_mode=validation.execution_mode,
                task_id=validation.task_id,
                change_type=validation.change_type,
                target_files=validation.target_files,
                patch_files=[],
                patch_count=0,
                empty_patch=False,
                allowed_scope_pass=True,
                forbidden_scope_pass=True,
                patch_parse_pass=True,
                patch_file_consistency_pass=True,
                patch_apply_blocked=True,
                command_execution_blocked=True,
                real_patch_applied="no",
                real_task_execution="no",
                run_project_task_full_called="no",
                claude_code_called="no",
                business_code_changed="no",
                framework_code_changed="no",
                human_review_required="yes",
                ready_for_future_controlled_apply=False,
                violations=[f"Proposal type '{change_type}' requires patches but none found"],
                check_result="fail",
                message=f"Proposal 类型 '{change_type}' 需要 patches 但未提供",
            )
        else:
            # doc_only, report_only, command_only — no patches needed
            return NoToolUseControlledPatchApplyDryRunResult(
                parse_status=validation.parse_status,
                parse_check_result=validation.parse_check_result,
                validation_status=validation.validation_status,
                validation_check_result=validation.check_result,
                patch_dry_run_status="ready_for_future_apply",
                proposal_version=validation.proposal_version,
                execution_mode=validation.execution_mode,
                task_id=validation.task_id,
                change_type=validation.change_type,
                target_files=validation.target_files,
                patch_files=[],
                patch_count=0,
                empty_patch=False,
                allowed_scope_pass=True,
                forbidden_scope_pass=True,
                patch_parse_pass=True,
                patch_file_consistency_pass=True,
                patch_apply_blocked=True,
                command_execution_blocked=True,
                real_patch_applied="no",
                real_task_execution="no",
                run_project_task_full_called="no",
                claude_code_called="no",
                business_code_changed="no",
                framework_code_changed="no",
                human_review_required="yes",
                ready_for_future_controlled_apply=True,
                violations=[],
                check_result="pass",
                message=f"Proposal 类型 '{change_type}' 不需要 patches，scope 校验通过，可进入 future controlled apply",
            )

    # Step 6: 逐个检查 patches
    violations: list[str] = []
    patch_files: list[str] = []
    has_empty = False
    all_valid_format = True
    all_consistent = True
    all_in_allowed = True
    all_not_forbidden = True

    allowed_files = validation.allowed_files
    forbidden_files = validation.forbidden_files
    target_files = validation.target_files

    for i, patch_entry in enumerate(patches_data):
        if not isinstance(patch_entry, dict):
            violations.append(f"Patch entry {i}: not a valid mapping")
            all_valid_format = False
            continue

        patch_file = patch_entry.get("file", "")
        patch_content = patch_entry.get("content", "")
        patch_format = patch_entry.get("format", "")

        if not patch_file:
            violations.append(f"Patch entry {i}: missing 'file' field")
            all_valid_format = False
            continue

        patch_files.append(patch_file)

        # 检查 format
        if patch_format != "unified_diff":
            violations.append(f"Patch '{patch_file}': unsupported format '{patch_format}', expected 'unified_diff'")
            all_valid_format = False
            continue

        # 检查空 patch
        if not patch_content or not patch_content.strip():
            violations.append(f"Patch '{patch_file}': empty patch content")
            has_empty = True
            continue

        # 检查 unified diff 格式
        if not _is_valid_unified_diff(patch_content):
            violations.append(f"Patch '{patch_file}': invalid unified diff format")
            all_valid_format = False
            continue

        # 检查空变更
        if _is_patch_empty(patch_content):
            violations.append(f"Patch '{patch_file}': patch has no actual changes")
            has_empty = True
            continue

        # 检查 patch file 与 target_files 一致性
        if patch_file not in target_files:
            violations.append(f"Patch '{patch_file}': not in target_files list")
            all_consistent = False

        # 检查 patch file 是否在 allowed scope
        if not _is_path_in_scope(patch_file, allowed_files):
            violations.append(f"Patch '{patch_file}': not in allowed scope")
            all_in_allowed = False

        # 检查 patch file 是否 forbidden
        if _is_path_forbidden(patch_file, forbidden_files):
            violations.append(f"Patch '{patch_file}': in forbidden scope")
            all_not_forbidden = False

    # Step 7: 确定 patch_dry_run_status
    if has_empty or not all_valid_format or not all_consistent or not all_in_allowed or not all_not_forbidden:
        patch_dry_run_status = "unsafe_patch"
    else:
        patch_dry_run_status = "ready_for_future_apply"

    ready = (
        patch_dry_run_status == "ready_for_future_apply"
        and not has_empty
        and all_valid_format
        and all_consistent
        and all_in_allowed
        and all_not_forbidden
    )

    check_result = "pass" if ready else "fail"

    message = (
        "Patch apply dry-run passed, ready for future controlled apply" if ready
        else f"Patch apply dry-run failed: {'; '.join(violations)}"
    )

    return NoToolUseControlledPatchApplyDryRunResult(
        parse_status=validation.parse_status,
        parse_check_result=validation.parse_check_result,
        validation_status=validation.validation_status,
        validation_check_result=validation.check_result,
        patch_dry_run_status=patch_dry_run_status,
        proposal_version=validation.proposal_version,
        execution_mode=validation.execution_mode,
        task_id=validation.task_id,
        change_type=validation.change_type,
        target_files=validation.target_files,
        patch_files=patch_files,
        patch_count=len(patches_data),
        empty_patch=has_empty,
        allowed_scope_pass=all_in_allowed,
        forbidden_scope_pass=all_not_forbidden,
        patch_parse_pass=all_valid_format,
        patch_file_consistency_pass=all_consistent,
        patch_apply_blocked=True,
        command_execution_blocked=True,
        real_patch_applied="no",
        real_task_execution="no",
        run_project_task_full_called="no",
        claude_code_called="no",
        business_code_changed="no",
        framework_code_changed="no",
        human_review_required="yes",
        ready_for_future_controlled_apply=ready,
        violations=violations,
        check_result=check_result,
        message=message,
    )


# ---------------------------------------------------------------------------
# T119: 内置 patch apply dry-run samples
# ---------------------------------------------------------------------------

_PATCH_SAMPLE_PASS = """\
```yaml
proposal_version: "1.0"
execution_mode: "no_tool_use_single_task_proposal"

task:
  id: "T119"
  title: "Implement controlled patch apply dry-run"
  source: "docs/tasks.md"

intent:
  summary: "Implement patch apply dry-run for no-tool-use proposals"
  expected_outcome: "Dry-run parses patch, checks consistency, blocks real apply"

scope:
  allowed_files:
    - "docs/test.md"
    - "reports/checks/T119-check.md"
  forbidden_files:
    - "runner.py"
    - "tools/rework_manager.py"
    - "projects/**"
  business_code_change: "no"
  framework_code_change: "no"

changes:
  type: "patch_proposal"
  target_files:
    - path: "docs/test.md"
      change_type: "modify"
      reason: "Test patch target"

patches:
  - file: "docs/test.md"
    format: "unified_diff"
    content: |
      --- a/docs/test.md
      +++ b/docs/test.md
      @@ -1,3 +1,4 @@
       line 1
       line 2
      +new line added by patch
       line 3

safety:
  real_task_execution: "no"
  run_project_task_full_called: "no"
  claude_code_tool_use_used: "no"
  auto_continue_to_next_task: "no"
  auto_git_backup: "no"
  bypass_permissions_used: "no"
  human_review_required: "yes"

validation:
  expected_check_result: "pass"

next_action:
  recommendation: "human_review"
```
"""

_PATCH_SAMPLE_NO_PATCH = """\
```yaml
proposal_version: "1.0"
execution_mode: "no_tool_use_single_task_proposal"

task:
  id: "T119"
  title: "Test no patch provided"
  source: "docs/tasks.md"

intent:
  summary: "Test patch_proposal without patches section"
  expected_outcome: "Should fail - patches required"

scope:
  allowed_files:
    - "docs/test.md"
  forbidden_files:
    - "runner.py"
    - "projects/**"
  business_code_change: "no"
  framework_code_change: "no"

changes:
  type: "patch_proposal"
  target_files:
    - path: "docs/test.md"
      change_type: "modify"
      reason: "Test"

# patches section is missing

safety:
  real_task_execution: "no"
  run_project_task_full_called: "no"
  claude_code_tool_use_used: "no"
  auto_continue_to_next_task: "no"
  auto_git_backup: "no"
  bypass_permissions_used: "no"
  human_review_required: "yes"

validation:
  expected_check_result: "fail"

next_action:
  recommendation: "human_review"
```
"""

_PATCH_SAMPLE_EMPTY_PATCH = """\
```yaml
proposal_version: "1.0"
execution_mode: "no_tool_use_single_task_proposal"

task:
  id: "T119"
  title: "Test empty patch content"
  source: "docs/tasks.md"

intent:
  summary: "Test that empty patch content is rejected"
  expected_outcome: "Should fail - patch content is empty"

scope:
  allowed_files:
    - "docs/test.md"
  forbidden_files:
    - "runner.py"
    - "projects/**"
  business_code_change: "no"
  framework_code_change: "no"

changes:
  type: "patch_proposal"
  target_files:
    - path: "docs/test.md"
      change_type: "modify"
      reason: "Test"

patches:
  - file: "docs/test.md"
    format: "unified_diff"
    content: ""

safety:
  real_task_execution: "no"
  run_project_task_full_called: "no"
  claude_code_tool_use_used: "no"
  auto_continue_to_next_task: "no"
  auto_git_backup: "no"
  bypass_permissions_used: "no"
  human_review_required: "yes"

validation:
  expected_check_result: "fail"

next_action:
  recommendation: "human_review"
```
"""

_PATCH_SAMPLE_FILE_MISMATCH = """\
```yaml
proposal_version: "1.0"
execution_mode: "no_tool_use_single_task_proposal"

task:
  id: "T119"
  title: "Test patch file mismatch"
  source: "docs/tasks.md"

intent:
  summary: "Test that patch file must match target_files"
  expected_outcome: "Should fail - patch file differs from target"

scope:
  allowed_files:
    - "docs/test.md"
    - "docs/other.md"
  forbidden_files:
    - "runner.py"
    - "projects/**"
  business_code_change: "no"
  framework_code_change: "no"

changes:
  type: "patch_proposal"
  target_files:
    - path: "docs/test.md"
      change_type: "modify"
      reason: "Target file"

patches:
  - file: "docs/other.md"
    format: "unified_diff"
    content: |
      --- a/docs/other.md
      +++ b/docs/other.md
      @@ -1,2 +1,3 @@
       line 1
      +added line
       line 2

safety:
  real_task_execution: "no"
  run_project_task_full_called: "no"
  claude_code_tool_use_used: "no"
  auto_continue_to_next_task: "no"
  auto_git_backup: "no"
  bypass_permissions_used: "no"
  human_review_required: "yes"

validation:
  expected_check_result: "fail"

next_action:
  recommendation: "human_review"
```
"""

_PATCH_SAMPLE_OUTSIDE_ALLOWED = """\
```yaml
proposal_version: "1.0"
execution_mode: "no_tool_use_single_task_proposal"

task:
  id: "T119"
  title: "Test patch outside allowed scope"
  source: "docs/tasks.md"

intent:
  summary: "Test that patch file must be in allowed scope"
  expected_outcome: "Should fail - patch file outside allowed_files"

scope:
  allowed_files:
    - "docs/test.md"
  forbidden_files:
    - "runner.py"
    - "projects/**"
  business_code_change: "no"
  framework_code_change: "no"

changes:
  type: "patch_proposal"
  target_files:
    - path: "docs/test.md"
      change_type: "modify"
      reason: "Target"
    - path: "reports/other.md"
      change_type: "create"
      reason: "Additional target outside allowed"

patches:
  - file: "reports/other.md"
    format: "unified_diff"
    content: |
      --- /dev/null
      +++ b/reports/other.md
      @@ -0,0 +1,2 @@
      +# Test
      +content

safety:
  real_task_execution: "no"
  run_project_task_full_called: "no"
  claude_code_tool_use_used: "no"
  auto_continue_to_next_task: "no"
  auto_git_backup: "no"
  bypass_permissions_used: "no"
  human_review_required: "yes"

validation:
  expected_check_result: "fail"

next_action:
  recommendation: "human_review"
```
"""

_PATCH_SAMPLE_FORBIDDEN_FILE = """\
```yaml
proposal_version: "1.0"
execution_mode: "no_tool_use_single_task_proposal"

task:
  id: "T119"
  title: "Test patch targets forbidden file"
  source: "docs/tasks.md"

intent:
  summary: "Test that patch file must not be forbidden"
  expected_outcome: "Should fail - patch file is forbidden"

scope:
  allowed_files:
    - "docs/test.md"
    - "runner.py"
  forbidden_files:
    - "runner.py"
    - "projects/**"
  business_code_change: "no"
  framework_code_change: "no"

changes:
  type: "patch_proposal"
  target_files:
    - path: "runner.py"
      change_type: "modify"
      reason: "Target is forbidden"

patches:
  - file: "runner.py"
    format: "unified_diff"
    content: |
      --- a/runner.py
      +++ b/runner.py
      @@ -1,3 +1,4 @@
       line 1
      +# injected
       line 2

safety:
  real_task_execution: "no"
  run_project_task_full_called: "no"
  claude_code_tool_use_used: "no"
  auto_continue_to_next_task: "no"
  auto_git_backup: "no"
  bypass_permissions_used: "no"
  human_review_required: "yes"

validation:
  expected_check_result: "fail"

next_action:
  recommendation: "human_review"
```
"""

_PATCH_SAMPLE_INVALID_FORMAT = """\
```yaml
proposal_version: "1.0"
execution_mode: "no_tool_use_single_task_proposal"

task:
  id: "T119"
  title: "Test invalid patch format"
  source: "docs/tasks.md"

intent:
  summary: "Test that patch must be valid unified diff"
  expected_outcome: "Should fail - invalid diff format"

scope:
  allowed_files:
    - "docs/test.md"
  forbidden_files:
    - "runner.py"
    - "projects/**"
  business_code_change: "no"
  framework_code_change: "no"

changes:
  type: "patch_proposal"
  target_files:
    - path: "docs/test.md"
      change_type: "modify"
      reason: "Test"

patches:
  - file: "docs/test.md"
    format: "unified_diff"
    content: |
      This is not a valid unified diff.
      Just some random text.
      No --- or +++ or @@ markers.

safety:
  real_task_execution: "no"
  run_project_task_full_called: "no"
  claude_code_tool_use_used: "no"
  auto_continue_to_next_task: "no"
  auto_git_backup: "no"
  bypass_permissions_used: "no"
  human_review_required: "yes"

validation:
  expected_check_result: "fail"

next_action:
  recommendation: "human_review"
```
"""

_PATCH_SAMPLE_VALIDATION_FAIL = """\
```yaml
proposal_version: "1.0"
execution_mode: "no_tool_use_single_task_proposal"

task:
  id: "T119"
  title: "Test validation failure before patch check"
  source: "docs/tasks.md"

intent:
  summary: "Test that validation failure blocks patch dry-run"
  expected_outcome: "Should fail validation first"

scope:
  allowed_files:
    - "docs/**"
  forbidden_files:
    - "runner.py"
    - "projects/**"
  business_code_change: "no"
  framework_code_change: "no"

changes:
  type: "patch_proposal"
  target_files:
    - path: "reports/other.md"
      change_type: "create"
      reason: "Not in allowed scope"

safety:
  real_task_execution: "no"
  run_project_task_full_called: "no"
  claude_code_tool_use_used: "no"
  auto_continue_to_next_task: "yes"
  auto_git_backup: "no"
  bypass_permissions_used: "no"
  human_review_required: "yes"

validation:
  expected_check_result: "fail"

next_action:
  recommendation: "human_review"
```
"""

_PATCH_SAMPLE_PARSE_FAIL = """\
```yaml
proposal_version: "1.0"
execution_mode: no_tool_use_single_task_proposal
task:
  id: "T119"
  title: Test parse failure
  this is not valid yaml: [
    unclosed bracket
```
"""

_PATCH_APPLY_SAMPLES: dict[str, str] = {
    "pass": _PATCH_SAMPLE_PASS,
    "no-patch": _PATCH_SAMPLE_NO_PATCH,
    "empty-patch": _PATCH_SAMPLE_EMPTY_PATCH,
    "patch-file-mismatch": _PATCH_SAMPLE_FILE_MISMATCH,
    "patch-outside-allowed": _PATCH_SAMPLE_OUTSIDE_ALLOWED,
    "patch-forbidden-file": _PATCH_SAMPLE_FORBIDDEN_FILE,
    "invalid-patch-format": _PATCH_SAMPLE_INVALID_FORMAT,
    "validation-fail": _PATCH_SAMPLE_VALIDATION_FAIL,
    "parse-fail": _PATCH_SAMPLE_PARSE_FAIL,
}


def run_no_tool_use_controlled_patch_apply_sample_dry_run(
    sample: str = "pass",
) -> NoToolUseControlledPatchApplyDryRunResult:
    """运行 controlled patch apply dry-run 样本。

    使用内置 sample 文本作为输入，不读取任何外部文件。
    不应用 patch、不执行命令、不修改任何文件。

    Args:
        sample: 样本类型名称，必须在 _PATCH_APPLY_SAMPLES 中存在。
    """
    if sample not in _PATCH_APPLY_SAMPLES:
        available = ", ".join(sorted(_PATCH_APPLY_SAMPLES.keys()))
        return NoToolUseControlledPatchApplyDryRunResult(
            parse_status="failed_to_parse",
            parse_check_result="fail",
            validation_status="failed_parse",
            validation_check_result="fail",
            patch_dry_run_status="failed_parse",
            proposal_version=None,
            execution_mode=None,
            task_id=None,
            change_type=None,
            target_files=[],
            patch_files=[],
            patch_count=0,
            empty_patch=False,
            allowed_scope_pass=False,
            forbidden_scope_pass=False,
            patch_parse_pass=False,
            patch_file_consistency_pass=False,
            patch_apply_blocked=True,
            command_execution_blocked=True,
            real_patch_applied="no",
            real_task_execution="no",
            run_project_task_full_called="no",
            claude_code_called="no",
            business_code_changed="no",
            framework_code_changed="no",
            human_review_required="yes",
            ready_for_future_controlled_apply=False,
            violations=[f"Unknown patch apply sample: {sample}"],
            check_result="fail",
            message=f"未知 patch apply sample '{sample}'。可用样本：{available}",
        )

    text = _PATCH_APPLY_SAMPLES[sample]
    return run_no_tool_use_controlled_patch_apply_dry_run(text)


# ---------------------------------------------------------------------------
# T120: First No-Tool-Use Real Single-Task Dry-Run
# ---------------------------------------------------------------------------

@dataclass
class FirstNoToolUseSingleTaskDryRunResult:
    """First no-tool-use single-task dry-run result。

    串联 parser → validator → patch apply dry-run 的完整 pipeline。
    不真实 apply patch，不执行 command，不调用 Claude Code。
    """

    # Execution mode
    execution_mode: str  # first_no_tool_use_real_single_task_dry_run

    # Task info
    task_id: str | None
    task_title: str | None
    proposal_source: str  # sample / file / model_output

    # Pipeline stage results
    parse_status: str
    parse_check_result: str
    validation_status: str
    validation_check_result: str
    patch_dry_run_status: str
    patch_dry_run_check_result: str

    # Pipeline summary
    pipeline_status: str  # ready_for_human_review / failed_parse / failed_validation / failed_patch_dry_run

    # File / patch info
    target_files: list[str]
    patch_files: list[str]
    proposed_commands: list[str]
    expected_reports: list[str]

    # Safety guarantees (hardcoded)
    real_patch_applied: str       # always "no"
    command_execution_performed: str  # always "no"
    real_task_execution: str      # always "no"
    run_project_task_full_called: str  # always "no"
    claude_code_called: str       # always "no"
    business_code_changed: str    # always "no"
    framework_code_changed: str   # always "no"
    auto_continue_to_next_task: str   # always "no"
    auto_git_backup: str          # always "no"
    bypass_permissions_used: str  # always "no"
    human_review_required: str    # always "yes"
    ready_for_human_review: bool
    ready_for_real_execution: str  # always "no"

    # Failure detail
    stop_reason: str | None
    violations: list[str]

    # Final result
    check_result: str  # pass / fail
    message: str


def run_first_no_tool_use_single_task_dry_run(
    proposal_text: str,
) -> FirstNoToolUseSingleTaskDryRunResult:
    """串联 parser → validator → patch apply dry-run 的完整 pipeline。

    依次调用：
    1. parse_no_tool_use_execution_proposal() — T117 parser
    2. validate_no_tool_use_allowed_scope_dry_run() — T118 validator
    3. run_no_tool_use_controlled_patch_apply_dry_run() — T119 patch apply

    不修改任何文件。不调用 Claude Code。不执行任何命令。
    """
    # Safety defaults
    _safe = dict(
        real_patch_applied="no",
        command_execution_performed="no",
        real_task_execution="no",
        run_project_task_full_called="no",
        claude_code_called="no",
        business_code_changed="no",
        framework_code_changed="no",
        auto_continue_to_next_task="no",
        auto_git_backup="no",
        bypass_permissions_used="no",
        human_review_required="yes",
        ready_for_real_execution="no",
    )

    # Step 1: Parse — T117
    parse = parse_no_tool_use_execution_proposal(proposal_text)

    if parse.parse_status != "parsed":
        return FirstNoToolUseSingleTaskDryRunResult(
            execution_mode="first_no_tool_use_real_single_task_dry_run",
            task_id=parse.task_id,
            task_title=None,
            proposal_source="sample",
            parse_status=parse.parse_status,
            parse_check_result=parse.check_result,
            validation_status="failed_parse",
            validation_check_result="fail",
            patch_dry_run_status="failed_parse",
            patch_dry_run_check_result="fail",
            pipeline_status="failed_parse",
            target_files=[],
            patch_files=[],
            proposed_commands=[],
            expected_reports=[],
            ready_for_human_review=False,
            stop_reason="parse_failed",
            violations=[f"Parse failed: {parse.message}"],
            check_result="fail",
            message=f"Pipeline 在 parse 阶段失败：{parse.message}",
            **_safe,
        )

    # Step 2: Validate — T118
    validation = validate_no_tool_use_allowed_scope_dry_run(proposal_text)

    if validation.check_result != "pass":
        return FirstNoToolUseSingleTaskDryRunResult(
            execution_mode="first_no_tool_use_real_single_task_dry_run",
            task_id=parse.task_id,
            task_title=None,
            proposal_source="sample",
            parse_status=parse.parse_status,
            parse_check_result=parse.check_result,
            validation_status=validation.validation_status,
            validation_check_result=validation.check_result,
            patch_dry_run_status="failed_validation",
            patch_dry_run_check_result="fail",
            pipeline_status="failed_validation",
            target_files=parse.target_files,
            patch_files=[],
            proposed_commands=parse.proposed_commands,
            expected_reports=parse.expected_reports,
            ready_for_human_review=False,
            stop_reason="validation_failed",
            violations=validation.violations if hasattr(validation, "violations") else [validation.message],
            check_result="fail",
            message=f"Pipeline 在 validation 阶段失败：{validation.message}",
            **_safe,
        )

    # Step 3: Patch Apply Dry-Run — T119
    patch_result = run_no_tool_use_controlled_patch_apply_dry_run(proposal_text)

    if patch_result.check_result != "pass":
        return FirstNoToolUseSingleTaskDryRunResult(
            execution_mode="first_no_tool_use_real_single_task_dry_run",
            task_id=parse.task_id,
            task_title=None,
            proposal_source="sample",
            parse_status=parse.parse_status,
            parse_check_result=parse.check_result,
            validation_status=validation.validation_status,
            validation_check_result=validation.check_result,
            patch_dry_run_status=patch_result.patch_dry_run_status,
            patch_dry_run_check_result=patch_result.check_result,
            pipeline_status="failed_patch_dry_run",
            target_files=parse.target_files,
            patch_files=patch_result.patch_files,
            proposed_commands=parse.proposed_commands,
            expected_reports=parse.expected_reports,
            ready_for_human_review=False,
            stop_reason="patch_dry_run_failed",
            violations=patch_result.violations,
            check_result="fail",
            message=f"Pipeline 在 patch dry-run 阶段失败：{patch_result.message}",
            **_safe,
        )

    # All stages passed — ready for human review
    return FirstNoToolUseSingleTaskDryRunResult(
        execution_mode="first_no_tool_use_real_single_task_dry_run",
        task_id=parse.task_id,
        task_title=None,
        proposal_source="sample",
        parse_status=parse.parse_status,
        parse_check_result=parse.check_result,
        validation_status=validation.validation_status,
        validation_check_result=validation.check_result,
        patch_dry_run_status=patch_result.patch_dry_run_status,
        patch_dry_run_check_result=patch_result.check_result,
        pipeline_status="ready_for_human_review",
        target_files=parse.target_files,
        patch_files=patch_result.patch_files,
        proposed_commands=parse.proposed_commands,
        expected_reports=parse.expected_reports,
        ready_for_human_review=True,
        stop_reason=None,
        violations=[],
        check_result="pass",
        message="Pipeline 全部通过：parse → validate → patch dry-run。"
                 "等待人工审查后决定是否进入真实执行。",
        **_safe,
    )


# --- T120 样本 ---

_SINGLE_TASK_SAMPLE_PASS = """\
```proposal
proposal_version: "1.0"
execution_mode: "no_tool_use_single_task_proposal"

task:
  id: "T120"
  title: "执行 first no-tool-use real single-task dry-run"
  source: "docs/tasks.md"

intent:
  summary: "模拟一次完整的 no-tool-use 单任务执行链路"
  expected_outcome: "Pipeline 全部通过，等待人工审查"

scope:
  allowed_files:
    - "docs/test.md"
    - "reports/dev/T120-dev-report.md"
  forbidden_files:
    - "runner.py"
    - "tools/*.py"
    - "projects/**"
  business_code_change: "no"
  framework_code_change: "no"

changes:
  type: "patch_proposal"
  target_files:
    - path: "docs/test.md"
      change_type: "create"
      reason: "Test file for dry-run validation"

patches:
  - file: "docs/test.md"
    format: "unified_diff"
    content: |
      --- a/docs/test.md
      +++ b/docs/test.md
      @@ -0,0 +1,3 @@
      +# Test
      +
      +Test content for dry-run validation.

safety:
  real_task_execution: "no"
  run_project_task_full_called: "no"
  claude_code_tool_use_used: "no"
  auto_continue_to_next_task: "no"
  auto_git_backup: "no"
  bypass_permissions_used: "no"
  human_review_required: "yes"

validation:
  expected_check_result: "pass"
  success_criteria:
    - "Pipeline parse → validate → patch dry-run all pass"

next_action:
  recommendation: "human_review"
```
"""

_SINGLE_TASK_SAMPLE_PARSE_FAIL = """\
```yaml
this is not valid yaml: [
```
"""

_SINGLE_TASK_SAMPLE_VALIDATION_FAIL = """\
```proposal
proposal_version: "1.0"
execution_mode: "no_tool_use_single_task_proposal"

task:
  id: "T120"
  title: "Validation fail sample"
  source: "docs/tasks.md"

intent:
  summary: "Test validation failure"
  expected_outcome: "Should fail validation"

scope:
  allowed_files:
    - "docs/test.md"
  forbidden_files:
    - "runner.py"
  business_code_change: "no"
  framework_code_change: "no"

changes:
  type: "doc_only"
  target_files:
    - path: "docs/test.md"
      change_type: "create"
      reason: "Test"

safety:
  real_task_execution: "no"
  run_project_task_full_called: "no"
  claude_code_tool_use_used: "no"
  auto_continue_to_next_task: "yes"
  auto_git_backup: "no"
  bypass_permissions_used: "no"
  human_review_required: "yes"

validation:
  expected_check_result: "pass"
  success_criteria:
    - "Should fail due to auto_continue"

next_action:
  recommendation: "human_review"
```
"""

_SINGLE_TASK_SAMPLE_PATCH_DRY_RUN_FAIL = """\
```proposal
proposal_version: "1.0"
execution_mode: "no_tool_use_single_task_proposal"

task:
  id: "T120"
  title: "Patch dry-run fail sample"
  source: "docs/tasks.md"

intent:
  summary: "Test patch dry-run failure with empty patch"
  expected_outcome: "Should fail patch dry-run"

scope:
  allowed_files:
    - "docs/test.md"
  forbidden_files:
    - "runner.py"
  business_code_change: "no"
  framework_code_change: "no"

changes:
  type: "patch_proposal"
  target_files:
    - path: "docs/test.md"
      change_type: "modify"
      reason: "Test patch with empty content"

patches:
  - file: "docs/test.md"
    format: "unified_diff"
    content: ""

safety:
  real_task_execution: "no"
  run_project_task_full_called: "no"
  claude_code_tool_use_used: "no"
  auto_continue_to_next_task: "no"
  auto_git_backup: "no"
  bypass_permissions_used: "no"
  human_review_required: "yes"

validation:
  expected_check_result: "pass"
  success_criteria:
    - "Should fail due to empty patch"

next_action:
  recommendation: "human_review"
```
"""

_SINGLE_TASK_SAMPLE_NO_PATCH = """\
```proposal
proposal_version: "1.0"
execution_mode: "no_tool_use_single_task_proposal"

task:
  id: "T120"
  title: "No patch sample"
  source: "docs/tasks.md"

intent:
  summary: "Test missing patches for patch_proposal type"
  expected_outcome: "Should fail because patches are required but missing"

scope:
  allowed_files:
    - "docs/test.md"
  forbidden_files:
    - "runner.py"
  business_code_change: "no"
  framework_code_change: "no"

changes:
  type: "patch_proposal"
  target_files:
    - path: "docs/test.md"
      change_type: "create"
      reason: "Test no patches"

safety:
  real_task_execution: "no"
  run_project_task_full_called: "no"
  claude_code_tool_use_used: "no"
  auto_continue_to_next_task: "no"
  auto_git_backup: "no"
  bypass_permissions_used: "no"
  human_review_required: "yes"

validation:
  expected_check_result: "pass"
  success_criteria:
    - "Should fail due to missing patches"

next_action:
  recommendation: "human_review"
```
"""

_SINGLE_TASK_SAMPLE_UNSAFE_COMMAND = """\
```proposal
proposal_version: "1.0"
execution_mode: "no_tool_use_single_task_proposal"

task:
  id: "T120"
  title: "Unsafe command sample"
  source: "docs/tasks.md"

intent:
  summary: "Test unsafe proposal with forbidden file target and dangerous command"
  expected_outcome: "Should fail validation due to forbidden file target"

scope:
  allowed_files:
    - "docs/test.md"
  forbidden_files:
    - "runner.py"
  business_code_change: "no"
  framework_code_change: "no"

changes:
  type: "command_only"
  target_files:
    - path: "runner.py"
      change_type: "modify"
      reason: "Forbidden target file with unsafe command"

commands:
  proposed:
    - command: "rm -rf /"
      purpose: "Dangerous command"
      required: true
      allowlist_category: "test"

safety:
  real_task_execution: "no"
  run_project_task_full_called: "no"
  claude_code_tool_use_used: "no"
  auto_continue_to_next_task: "no"
  auto_git_backup: "no"
  bypass_permissions_used: "no"
  human_review_required: "yes"

validation:
  expected_check_result: "fail"
  success_criteria:
    - "Should fail due to forbidden file target"

next_action:
  recommendation: "block"
```
"""

_SINGLE_TASK_SAMPLE_AUTO_CONTINUE_REQUESTED = """\
```proposal
proposal_version: "1.0"
execution_mode: "no_tool_use_single_task_proposal"

task:
  id: "T120"
  title: "Auto-continue requested sample"
  source: "docs/tasks.md"

intent:
  summary: "Test auto-continue requested"
  expected_outcome: "Should fail validation"

scope:
  allowed_files:
    - "docs/test.md"
  forbidden_files:
    - "runner.py"
  business_code_change: "no"
  framework_code_change: "no"

changes:
  type: "doc_only"
  target_files:
    - path: "docs/test.md"
      change_type: "create"
      reason: "Test"

safety:
  real_task_execution: "no"
  run_project_task_full_called: "no"
  claude_code_tool_use_used: "no"
  auto_continue_to_next_task: "yes"
  auto_git_backup: "no"
  bypass_permissions_used: "no"
  human_review_required: "yes"

validation:
  expected_check_result: "pass"
  success_criteria:
    - "Should fail due to auto_continue=yes"

next_action:
  recommendation: "human_review"
```
"""

_SINGLE_TASK_SAMPLE_AUTO_GIT_BACKUP_REQUESTED = """\
```proposal
proposal_version: "1.0"
execution_mode: "no_tool_use_single_task_proposal"

task:
  id: "T120"
  title: "Auto-git-backup requested sample"
  source: "docs/tasks.md"

intent:
  summary: "Test auto-git-backup requested"
  expected_outcome: "Should fail validation"

scope:
  allowed_files:
    - "docs/test.md"
  forbidden_files:
    - "runner.py"
  business_code_change: "no"
  framework_code_change: "no"

changes:
  type: "doc_only"
  target_files:
    - path: "docs/test.md"
      change_type: "create"
      reason: "Test"

safety:
  real_task_execution: "no"
  run_project_task_full_called: "no"
  claude_code_tool_use_used: "no"
  auto_continue_to_next_task: "no"
  auto_git_backup: "yes"
  bypass_permissions_used: "no"
  human_review_required: "yes"

validation:
  expected_check_result: "pass"
  success_criteria:
    - "Should fail due to auto_git_backup=yes"

next_action:
  recommendation: "human_review"
```
"""

_SINGLE_TASK_SAMPLES: dict[str, str] = {
    "pass": _SINGLE_TASK_SAMPLE_PASS,
    "parse-fail": _SINGLE_TASK_SAMPLE_PARSE_FAIL,
    "validation-fail": _SINGLE_TASK_SAMPLE_VALIDATION_FAIL,
    "patch-dry-run-fail": _SINGLE_TASK_SAMPLE_PATCH_DRY_RUN_FAIL,
    "no-patch": _SINGLE_TASK_SAMPLE_NO_PATCH,
    "unsafe-command": _SINGLE_TASK_SAMPLE_UNSAFE_COMMAND,
    "auto-continue-requested": _SINGLE_TASK_SAMPLE_AUTO_CONTINUE_REQUESTED,
    "auto-git-backup-requested": _SINGLE_TASK_SAMPLE_AUTO_GIT_BACKUP_REQUESTED,
}


def run_first_no_tool_use_single_task_sample_dry_run(
    sample: str = "pass",
) -> FirstNoToolUseSingleTaskDryRunResult:
    """运行 first no-tool-use single-task dry-run 样本。

    使用内置 sample 文本作为输入，不读取任何外部文件。
    不应用 patch、不执行命令、不修改任何文件、不调用 Claude Code。

    Args:
        sample: 样本类型名称，必须在 _SINGLE_TASK_SAMPLES 中存在。
    """
    if sample not in _SINGLE_TASK_SAMPLES:
        available = ", ".join(sorted(_SINGLE_TASK_SAMPLES.keys()))
        return FirstNoToolUseSingleTaskDryRunResult(
            execution_mode="first_no_tool_use_real_single_task_dry_run",
            task_id=None,
            task_title=None,
            proposal_source="sample",
            parse_status="failed_to_parse",
            parse_check_result="fail",
            validation_status="failed_parse",
            validation_check_result="fail",
            patch_dry_run_status="failed_parse",
            patch_dry_run_check_result="fail",
            pipeline_status="failed_parse",
            target_files=[],
            patch_files=[],
            proposed_commands=[],
            expected_reports=[],
            real_patch_applied="no",
            command_execution_performed="no",
            real_task_execution="no",
            run_project_task_full_called="no",
            claude_code_called="no",
            business_code_changed="no",
            framework_code_changed="no",
            auto_continue_to_next_task="no",
            auto_git_backup="no",
            bypass_permissions_used="no",
            human_review_required="yes",
            ready_for_human_review=False,
            ready_for_real_execution="no",
            stop_reason="unknown_sample",
            violations=[f"Unknown single-task sample: {sample}"],
            check_result="fail",
            message=f"未知 single-task sample '{sample}'。可用样本：{available}",
        )

    text = _SINGLE_TASK_SAMPLES[sample]
    return run_first_no_tool_use_single_task_dry_run(text)


# ---------------------------------------------------------------------------
# T124: Controlled Apply Approval Model Dry-Run
# ---------------------------------------------------------------------------

APPROVAL_TOKEN_EXPECTED = "APPROVE_CONTROLLED_APPLY_DRY_RUN"


@dataclass
class ControlledApplyApprovalDryRunResult:
    """Controlled apply approval model dry-run 结果。"""

    # 模式标识
    approval_mode: str                           # controlled_apply_approval_model_dry_run

    # Token 检查
    approval_token_expected: str                 # APPROVE_CONTROLLED_APPLY_DRY_RUN
    approval_token_provided: str                 # 实际提供的 token 或 ""
    approval_token_present: str                  # yes / no
    approval_token_valid: str                    # yes / no / not_applicable

    # 前置条件检查
    worktree_status: str                         # 输入的 worktree status
    worktree_clean_required: str                 # yes（始终要求 clean）
    worktree_clean_pass: str                     # yes / no

    previous_pipeline_status: str                # 输入的 pipeline status
    previous_pipeline_check_result: str          # 输入的 pipeline check result
    previous_pipeline_pass: str                  # yes / no

    human_review_required: str                   # 输入值
    human_review_required_pass: str              # yes / no

    ready_for_real_apply: str                    # 输入值
    ready_for_real_apply_pass: str               # yes（必须为 no） / no

    auto_continue_to_next_task: str              # 输入值
    auto_continue_pass: str                      # yes / no

    auto_git_backup: str                         # 输入值
    auto_git_backup_pass: str                    # yes / no

    # 安全保证字段（始终为安全值）
    real_patch_applied: str                      # no
    command_execution_performed: str             # no
    real_task_execution: str                     # no
    run_project_task_full_called: str            # no
    claude_code_called: str                      # no
    business_code_changed: str                   # no
    framework_code_changed: str                  # no

    # Gate 结果
    ready_for_controlled_apply_dry_run: str      # yes / no
    ready_for_real_apply_after_approval: str     # no（始终）
    rejection_reasons: list[str]
    check_result: str                            # pass / fail
    message: str


def run_controlled_apply_approval_model_dry_run(
    approval_token: str | None = None,
    worktree_status: str = "clean",
    previous_pipeline_status: str = "ready_for_human_review",
    previous_pipeline_check_result: str = "pass",
    human_review_required: str = "yes",
    ready_for_real_apply: str = "no",
    auto_continue_to_next_task: str = "no",
    auto_git_backup: str = "no",
) -> ControlledApplyApprovalDryRunResult:
    """执行 controlled apply approval model dry-run。

    只做 approval token 和前置条件检查，不真实 apply patch，不执行 command。
    函数只根据传入参数 dry-run，不检查真实 git status。

    Args:
        approval_token: 用户提供的 approval token，None 表示未提供。
        worktree_status: 工作区状态，应为 "clean" 或 "dirty"。
        previous_pipeline_status: 前一步 pipeline 状态。
        previous_pipeline_check_result: 前一步 pipeline check result。
        human_review_required: 是否需要人工审查。
        ready_for_real_apply: 是否准备好真实 apply（应为 no）。
        auto_continue_to_next_task: 是否自动继续下一任务（应为 no）。
        auto_git_backup: 是否自动 Git 备份（应为 no）。

    Returns:
        ControlledApplyApprovalDryRunResult
    """
    rejection_reasons: list[str] = []

    # Token 检查
    token_provided = approval_token or ""
    token_present = "yes" if approval_token is not None and approval_token != "" else "no"
    token_valid = "not_applicable"
    if token_present == "yes":
        token_valid = "yes" if token_provided == APPROVAL_TOKEN_EXPECTED else "no"

    if token_present == "no":
        rejection_reasons.append("missing_approval_token")
    elif token_valid == "no":
        rejection_reasons.append("invalid_approval_token")

    # Worktree 检查
    worktree_clean_pass = "yes" if worktree_status == "clean" else "no"
    if worktree_clean_pass == "no":
        rejection_reasons.append("dirty_worktree")

    # Previous pipeline 检查
    pipeline_pass = "yes" if (
        previous_pipeline_status == "ready_for_human_review"
        and previous_pipeline_check_result == "pass"
    ) else "no"
    if previous_pipeline_status != "ready_for_human_review":
        rejection_reasons.append("previous_pipeline_not_ready_for_human_review")
    if previous_pipeline_check_result != "pass":
        rejection_reasons.append("previous_pipeline_check_failed")

    # Human review 检查
    hr_pass = "yes" if human_review_required == "yes" else "no"
    if hr_pass == "no":
        rejection_reasons.append("human_review_not_required")

    # Ready for real apply 必须为 no
    rra_pass = "yes" if ready_for_real_apply == "no" else "no"
    if rra_pass == "no":
        rejection_reasons.append("ready_for_real_apply_unexpected")

    # Auto continue 检查
    ac_pass = "yes" if auto_continue_to_next_task == "no" else "no"
    if ac_pass == "no":
        rejection_reasons.append("auto_continue_requested")

    # Auto git backup 检查
    agb_pass = "yes" if auto_git_backup == "no" else "no"
    if agb_pass == "no":
        rejection_reasons.append("auto_git_backup_requested")

    # 综合判断
    all_pass = (
        token_present == "yes"
        and token_valid == "yes"
        and worktree_clean_pass == "yes"
        and pipeline_pass == "yes"
        and hr_pass == "yes"
        and rra_pass == "yes"
        and ac_pass == "yes"
        and agb_pass == "yes"
    )

    check_result = "pass" if all_pass else "fail"
    ready = "yes" if all_pass else "no"

    if all_pass:
        msg = "Controlled apply approval model dry-run: all preconditions passed. Ready for controlled apply dry-run."
    else:
        reasons_str = ", ".join(rejection_reasons)
        msg = f"Controlled apply approval model dry-run: rejected. Reasons: {reasons_str}"

    return ControlledApplyApprovalDryRunResult(
        approval_mode="controlled_apply_approval_model_dry_run",
        approval_token_expected=APPROVAL_TOKEN_EXPECTED,
        approval_token_provided=token_provided,
        approval_token_present=token_present,
        approval_token_valid=token_valid,
        worktree_status=worktree_status,
        worktree_clean_required="yes",
        worktree_clean_pass=worktree_clean_pass,
        previous_pipeline_status=previous_pipeline_status,
        previous_pipeline_check_result=previous_pipeline_check_result,
        previous_pipeline_pass=pipeline_pass,
        human_review_required=human_review_required,
        human_review_required_pass=hr_pass,
        ready_for_real_apply=ready_for_real_apply,
        ready_for_real_apply_pass=rra_pass,
        auto_continue_to_next_task=auto_continue_to_next_task,
        auto_continue_pass=ac_pass,
        auto_git_backup=auto_git_backup,
        auto_git_backup_pass=agb_pass,
        real_patch_applied="no",
        command_execution_performed="no",
        real_task_execution="no",
        run_project_task_full_called="no",
        claude_code_called="no",
        business_code_changed="no",
        framework_code_changed="no",
        ready_for_controlled_apply_dry_run=ready,
        ready_for_real_apply_after_approval="no",
        rejection_reasons=rejection_reasons,
        check_result=check_result,
        message=msg,
    )


def run_controlled_apply_approval_model_sample_dry_run(
    sample: str = "pass",
) -> ControlledApplyApprovalDryRunResult:
    """运行 controlled apply approval model dry-run 样本。

    使用内置参数，不读取外部文件，不检查真实 git status。
    不应用 patch、不执行命令、不修改任何文件、不调用 Claude Code。

    Args:
        sample: 样本类型名称。

    Returns:
        ControlledApplyApprovalDryRunResult
    """
    _APPROVAL_SAMPLES: dict[str, dict] = {
        "pass": {
            "approval_token": APPROVAL_TOKEN_EXPECTED,
            "worktree_status": "clean",
            "previous_pipeline_status": "ready_for_human_review",
            "previous_pipeline_check_result": "pass",
            "human_review_required": "yes",
            "ready_for_real_apply": "no",
            "auto_continue_to_next_task": "no",
            "auto_git_backup": "no",
        },
        "missing-token": {
            "approval_token": None,
            "worktree_status": "clean",
            "previous_pipeline_status": "ready_for_human_review",
            "previous_pipeline_check_result": "pass",
            "human_review_required": "yes",
            "ready_for_real_apply": "no",
            "auto_continue_to_next_task": "no",
            "auto_git_backup": "no",
        },
        "wrong-token": {
            "approval_token": "WRONG_TOKEN",
            "worktree_status": "clean",
            "previous_pipeline_status": "ready_for_human_review",
            "previous_pipeline_check_result": "pass",
            "human_review_required": "yes",
            "ready_for_real_apply": "no",
            "auto_continue_to_next_task": "no",
            "auto_git_backup": "no",
        },
        "dirty-worktree": {
            "approval_token": APPROVAL_TOKEN_EXPECTED,
            "worktree_status": "dirty",
            "previous_pipeline_status": "ready_for_human_review",
            "previous_pipeline_check_result": "pass",
            "human_review_required": "yes",
            "ready_for_real_apply": "no",
            "auto_continue_to_next_task": "no",
            "auto_git_backup": "no",
        },
        "pipeline-not-ready": {
            "approval_token": APPROVAL_TOKEN_EXPECTED,
            "worktree_status": "clean",
            "previous_pipeline_status": "failed_validation",
            "previous_pipeline_check_result": "pass",
            "human_review_required": "yes",
            "ready_for_real_apply": "no",
            "auto_continue_to_next_task": "no",
            "auto_git_backup": "no",
        },
        "pipeline-failed": {
            "approval_token": APPROVAL_TOKEN_EXPECTED,
            "worktree_status": "clean",
            "previous_pipeline_status": "ready_for_human_review",
            "previous_pipeline_check_result": "fail",
            "human_review_required": "yes",
            "ready_for_real_apply": "no",
            "auto_continue_to_next_task": "no",
            "auto_git_backup": "no",
        },
        "human-review-missing": {
            "approval_token": APPROVAL_TOKEN_EXPECTED,
            "worktree_status": "clean",
            "previous_pipeline_status": "ready_for_human_review",
            "previous_pipeline_check_result": "pass",
            "human_review_required": "no",
            "ready_for_real_apply": "no",
            "auto_continue_to_next_task": "no",
            "auto_git_backup": "no",
        },
        "ready-for-real-apply-unexpected": {
            "approval_token": APPROVAL_TOKEN_EXPECTED,
            "worktree_status": "clean",
            "previous_pipeline_status": "ready_for_human_review",
            "previous_pipeline_check_result": "pass",
            "human_review_required": "yes",
            "ready_for_real_apply": "yes",
            "auto_continue_to_next_task": "no",
            "auto_git_backup": "no",
        },
        "auto-continue-requested": {
            "approval_token": APPROVAL_TOKEN_EXPECTED,
            "worktree_status": "clean",
            "previous_pipeline_status": "ready_for_human_review",
            "previous_pipeline_check_result": "pass",
            "human_review_required": "yes",
            "ready_for_real_apply": "no",
            "auto_continue_to_next_task": "yes",
            "auto_git_backup": "no",
        },
        "auto-git-backup-requested": {
            "approval_token": APPROVAL_TOKEN_EXPECTED,
            "worktree_status": "clean",
            "previous_pipeline_status": "ready_for_human_review",
            "previous_pipeline_check_result": "pass",
            "human_review_required": "yes",
            "ready_for_real_apply": "no",
            "auto_continue_to_next_task": "no",
            "auto_git_backup": "yes",
        },
    }

    if sample not in _APPROVAL_SAMPLES:
        available = ", ".join(sorted(_APPROVAL_SAMPLES.keys()))
        return ControlledApplyApprovalDryRunResult(
            approval_mode="controlled_apply_approval_model_dry_run",
            approval_token_expected=APPROVAL_TOKEN_EXPECTED,
            approval_token_provided="",
            approval_token_present="no",
            approval_token_valid="not_applicable",
            worktree_status="unknown",
            worktree_clean_required="yes",
            worktree_clean_pass="no",
            previous_pipeline_status="unknown",
            previous_pipeline_check_result="unknown",
            previous_pipeline_pass="no",
            human_review_required="yes",
            human_review_required_pass="no",
            ready_for_real_apply="no",
            ready_for_real_apply_pass="no",
            auto_continue_to_next_task="no",
            auto_continue_pass="no",
            auto_git_backup="no",
            auto_git_backup_pass="no",
            real_patch_applied="no",
            command_execution_performed="no",
            real_task_execution="no",
            run_project_task_full_called="no",
            claude_code_called="no",
            business_code_changed="no",
            framework_code_changed="no",
            ready_for_controlled_apply_dry_run="no",
            ready_for_real_apply_after_approval="no",
            rejection_reasons=[f"unknown_sample:{sample}"],
            check_result="fail",
            message=f"未知 approval sample '{sample}'。可用样本：{available}",
        )

    params = _APPROVAL_SAMPLES[sample]
    return run_controlled_apply_approval_model_dry_run(**params)


# ---------------------------------------------------------------------------
# T125: Command Allowlist Validation Dry-Run
# ---------------------------------------------------------------------------

# 允许的命令类别及其模式
COMMAND_ALLOWLIST_CATEGORIES: dict[str, list[str]] = {
    "status": [
        "git status",
        "git log",
        "git diff",
        "git branch",
        "git remote",
        "git tag",
    ],
    "validation": [
        "python runner.py",
        "uv run python runner.py",
        "python -c",
        "uv run python -c",
    ],
    "test": [
        "pytest",
        "uv run pytest",
        "python -m pytest",
        "uv run python -m pytest",
    ],
}

# 禁止的命令模式（字符串包含即拒绝）
FORBIDDEN_COMMAND_PATTERNS: list[str] = [
    # Git 写操作
    "git add",
    "git commit",
    "git push",
    "git reset",
    "git checkout .",
    "git checkout --",
    "git clean",
    "git stash",
    "git merge",
    "git rebase",
    "git cherry-pick",
    "git revert",
    # 文件破坏操作
    "rm ",
    "rm -",
    "del ",
    "rmdir ",
    "Remove-Item",
    # Shell 链接
    " && ",
    " ; ",
    " | ",
    " > ",
    " >> ",
    # 网络执行
    "curl | bash",
    "irm ",
    "iex",
    "powershell -ExecutionPolicy Bypass",
    # 危险操作
    "chmod +x",
    "move /Y",
    "copy /Y",
    # 框架调用
    "run-project-task-full",
    "run_project_task_full",
    # Claude Code tool-use
    "claude --permission-mode acceptEdits",
    "claude --permission-mode bypassPermissions",
    # 绝对路径写入
    ":/>",
    "://>",
]


@dataclass
class CommandAllowlistValidationDryRunResult:
    """T125 command allowlist validation dry-run 结果。"""

    # 模式标识
    validation_mode: str                        # command_allowlist_validation_dry_run

    # 输入
    command_sample: str                         # sample 名称或 "custom"
    commands: list[str]                         # 待校验命令列表

    # 统计
    commands_total: int                         # 总命令数
    commands_allowed: int                       # 允许命令数
    commands_rejected: int                      # 拒绝命令数

    # 分类
    allowed_commands: list[str]                 # 允许的命令列表
    rejected_commands: list[str]                # 拒绝的命令列表
    rejection_reasons: list[str]                # 拒绝原因列表

    # Allowlist 类别
    allowlist_categories: list[str]             # 命中到的允许类别
    forbidden_patterns_detected: list[str]      # 检测到的禁止模式

    # 安全保证字段（始终为安全值）
    command_execution_blocked: str              # yes
    real_patch_applied: str                     # no
    real_task_execution: str                    # no
    run_project_task_full_called: str           # no
    claude_code_called: str                     # no
    business_code_changed: str                  # no
    framework_code_changed: str                 # no
    auto_continue_to_next_task: str             # no
    auto_git_backup: str                        # no
    bypass_permissions_used: str                # no
    human_review_required: str                  # yes

    # Gate 结果
    ready_for_command_execution: str            # no
    ready_for_controlled_apply_dry_run: str     # yes / no
    check_result: str                           # pass / fail
    message: str


def _classify_command(command: str) -> tuple[str, str | None, str | None]:
    """分类单个命令。

    Returns:
        (status, allowlist_category, forbidden_pattern)
        status: "allowed" / "forbidden" / "unknown"
    """
    cmd_lower = command.strip().lower()
    cmd_stripped = command.strip()

    if not cmd_stripped:
        return "forbidden", None, "empty_command"

    # 先检查禁止模式（优先于允许检查）
    for pattern in FORBIDDEN_COMMAND_PATTERNS:
        if pattern.lower() in cmd_lower:
            return "forbidden", None, pattern.strip()

    # 检查允许类别
    for category, patterns in COMMAND_ALLOWLIST_CATEGORIES.items():
        for pattern in patterns:
            if cmd_lower.startswith(pattern.lower()):
                return "allowed", category, None

    # 未知命令（保守原则：不确定就拒绝）
    return "unknown", None, "unknown_command"


def run_command_allowlist_validation_dry_run(
    commands: list[str] | None = None,
    sample: str = "pass-status",
) -> CommandAllowlistValidationDryRunResult:
    """执行 command allowlist validation dry-run。

    只做字符串级别 dry-run 判断，不执行任何命令，不调用 shell，不应用 patch。

    Args:
        commands: 自定义命令列表。None 时使用内置 sample。
        sample: 内置 sample 名称。

    Returns:
        CommandAllowlistValidationDryRunResult
    """
    # 如果提供了自定义 commands，使用自定义命令
    if commands is not None:
        cmd_list = commands
        sample_name = "custom"
    else:
        # 使用内置 sample
        sample_name = sample
        cmd_list = _get_command_sample(sample)

    # 分类每个命令
    allowed_commands: list[str] = []
    rejected_commands: list[str] = []
    rejection_reasons: list[str] = []
    allowlist_categories: list[str] = []
    forbidden_patterns_detected: list[str] = []

    for cmd in cmd_list:
        status, category, forbidden = _classify_command(cmd)
        if status == "allowed":
            allowed_commands.append(cmd)
            if category and category not in allowlist_categories:
                allowlist_categories.append(category)
        else:
            rejected_commands.append(cmd)
            if forbidden:
                reason = f"{cmd}: {forbidden}"
                rejection_reasons.append(reason)
                if forbidden not in forbidden_patterns_detected:
                    forbidden_patterns_detected.append(forbidden)

    # 综合判断
    all_allowed = len(rejected_commands) == 0 and len(cmd_list) > 0
    check_result = "pass" if all_allowed else "fail"
    ready_for_controlled = "yes" if all_allowed else "no"

    if all_allowed:
        msg = f"Command allowlist validation dry-run: all {len(cmd_list)} commands allowed."
    else:
        msg = (
            f"Command allowlist validation dry-run: "
            f"{len(rejected_commands)}/{len(cmd_list)} commands rejected. "
            f"Reasons: {'; '.join(rejection_reasons)}"
        )

    return CommandAllowlistValidationDryRunResult(
        validation_mode="command_allowlist_validation_dry_run",
        command_sample=sample_name,
        commands=cmd_list,
        commands_total=len(cmd_list),
        commands_allowed=len(allowed_commands),
        commands_rejected=len(rejected_commands),
        allowed_commands=allowed_commands,
        rejected_commands=rejected_commands,
        rejection_reasons=rejection_reasons,
        allowlist_categories=allowlist_categories,
        forbidden_patterns_detected=forbidden_patterns_detected,
        command_execution_blocked="yes",
        real_patch_applied="no",
        real_task_execution="no",
        run_project_task_full_called="no",
        claude_code_called="no",
        business_code_changed="no",
        framework_code_changed="no",
        auto_continue_to_next_task="no",
        auto_git_backup="no",
        bypass_permissions_used="no",
        human_review_required="yes",
        ready_for_command_execution="no",
        ready_for_controlled_apply_dry_run=ready_for_controlled,
        check_result=check_result,
        message=msg,
    )


def _get_command_sample(sample: str) -> list[str]:
    """获取内置 command sample。

    Args:
        sample: sample 名称。

    Returns:
        命令列表。
    """
    _COMMAND_SAMPLES: dict[str, list[str]] = {
        "pass-status": [
            "git status --short",
            "git log --oneline -5",
            "git diff --stat",
        ],
        "pass-validation": [
            "python runner.py --help",
            "python runner.py no-tool-use-parse-proposal --sample pass",
        ],
        "pass-test": [
            "pytest",
            "uv run pytest",
        ],
        "empty-command": [
            "",
        ],
        "git-add": [
            "git add .",
        ],
        "git-commit": [
            "git commit -m 'test'",
        ],
        "git-push": [
            "git push origin main",
        ],
        "git-reset": [
            "git reset --hard HEAD~1",
        ],
        "rm-command": [
            "rm -rf /tmp/test",
        ],
        "pipe-command": [
            "git status | grep modified",
        ],
        "redirect-command": [
            "echo hello > output.txt",
        ],
        "run-project-task-full": [
            "python runner.py run-project-task-full --project projects/test",
        ],
        "claude-acceptedits": [
            "claude --permission-mode acceptEdits --print 'test'",
        ],
        "unknown-command": [
            "npm install lodash",
        ],
        "mixed-safe-unsafe": [
            "git status --short",
            "git add .",
            "pytest",
            "rm -rf /tmp/test",
        ],
    }

    if sample not in _COMMAND_SAMPLES:
        # 未知 sample 返回空列表（将导致 fail）
        return []
    return _COMMAND_SAMPLES[sample]
