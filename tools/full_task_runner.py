"""Full Task Loop Runner — 单任务完整闭环自动化。

将 Developer / Tester / Reviewer / Main Agent 串成完整闭环。
协议详见 docs/full-task-loop-protocol.md。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from tools.project_runner import (
    validate_project_root,
    load_project_runner_config,
    parse_project_tasks,
    find_next_pending_project_task,
    get_project_dev_report_path,
    run_project_next,
)
from tools.task_manager import load_tasks_file
from tools.tester_runner import run_tester_for_game_task
from tools.tester_runner import run_collision_tester_for_game_task
from tools.reviewer_runner import run_reviewer_for_game_task
from tools.main_agent import run_combined_decision_for_game_task


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class FullTaskStepResult:
    """单个阶段结果。"""
    name: str
    status: str  # PASS / FAIL / BLOCKED / SKIPPED / APPROVE / REQUEST_CHANGES / COMPLETE
    success: bool
    report_path: str | None = None
    message: str = ""


@dataclass
class FullTaskLoopResult:
    """完整闭环结果。"""
    project_path: str
    task_id: str
    final_status: str  # COMPLETE / REQUEST_CHANGES / BLOCKED / FAILED
    steps: list[FullTaskStepResult] = field(default_factory=list)
    full_loop_report_path: str | None = None
    next_action: str = ""


# ---------------------------------------------------------------------------
# Specialized Tester 映射（预留）
# ---------------------------------------------------------------------------

SPECIAL_TESTER_MAP = {
    "G004": "behavior",
    "G006": "gravity",
    "G007": "collision",
}


def maybe_run_specialized_tester(
    project_path: Path, task_id: str,
) -> FullTaskStepResult | None:
    """根据任务类型选择专项 Tester。"""
    tester_type = SPECIAL_TESTER_MAP.get(task_id)
    if tester_type is None:
        return None

    # G007: Collision Tester
    if tester_type == "collision":
        try:
            report_path, result = run_collision_tester_for_game_task(task_id)
            return FullTaskStepResult(
                name="Collision Tester",
                status=result.status,
                success=result.result == "PASS",
                report_path=str(report_path),
                message=(
                    f"Status: {result.status}, "
                    f"Passed: {result.passed_count}, "
                    f"Failed: {result.failed_count}"
                ),
            )
        except Exception as e:
            return FullTaskStepResult(
                name="Collision Tester",
                status="BLOCKED",
                success=False,
                message=f"Collision Tester 执行异常：{e}",
            )

    # 其他专项 Tester 尚未集成，跳过
    return FullTaskStepResult(
        name=f"Specialized Tester ({tester_type})",
        status="SKIPPED",
        success=True,
        message=f"{tester_type} tester 尚未集成，跳过。",
    )


# ---------------------------------------------------------------------------
# Developer 阶段
# ---------------------------------------------------------------------------

def run_developer_step(
    project_path: Path, task_id: str,
    claude_permission_mode: str = "acceptEdits",
) -> FullTaskStepResult:
    """执行 Developer 阶段。"""
    # 1. 读取子项目任务
    project_root = validate_project_root(project_path)
    config = load_project_runner_config(project_root)
    content = load_tasks_file(config.tasks_file)
    tasks = parse_project_tasks(content)

    # 2. 查找目标任务
    target_task = None
    for t in tasks:
        if t["id"] == task_id:
            target_task = t
            break

    if target_task is None:
        return FullTaskStepResult(
            name="Developer",
            status="BLOCKED",
            success=False,
            message=f"未找到任务：{task_id}",
        )

    task_status = target_task["status"]
    dev_report_path = get_project_dev_report_path(project_root, task_id)

    # 3. 如果任务已 done 且开发报告存在，跳过
    if task_status == "done" and dev_report_path.exists():
        return FullTaskStepResult(
            name="Developer",
            status="SKIPPED",
            success=True,
            report_path=str(dev_report_path),
            message=f"任务 {task_id} 已完成且报告存在，跳过 Developer。",
        )

    # 4. 如果任务是 in_progress
    if task_status == "in_progress":
        if dev_report_path.exists():
            return FullTaskStepResult(
                name="Developer",
                status="PASS",
                success=True,
                report_path=str(dev_report_path),
                message=f"任务 {task_id} 状态为 in_progress，但开发报告已存在，继续后续阶段。",
            )
        return FullTaskStepResult(
            name="Developer",
            status="BLOCKED",
            success=False,
            message=f"任务 {task_id} 状态为 in_progress 且无开发报告，需要人工确认。",
        )

    # 5. 如果任务是 pending，检查是否是当前第一个 pending
    if task_status == "pending":
        pending_task = find_next_pending_project_task(tasks)
        if pending_task and pending_task["id"] != task_id:
            return FullTaskStepResult(
                name="Developer",
                status="BLOCKED",
                success=False,
                message=(
                    f"当前第一个 pending 任务是 {pending_task['id']}，"
                    f"不是 {task_id}。请按顺序执行。"
                ),
            )

        # 执行 Developer
        result = run_project_next(str(project_root), claude_permission_mode=claude_permission_mode)

        # 超时
        if result.get("timed_out"):
            return FullTaskStepResult(
                name="Developer",
                status="BLOCKED",
                success=False,
                message=(
                    f"Claude Code 超时："
                    f"{result.get('timeout_seconds', 600)} 秒"
                ),
            )

        # completed_with_model_error
        if result.get("completed_with_model_error"):
            return FullTaskStepResult(
                name="Developer",
                status="PASS",
                success=True,
                report_path=str(dev_report_path),
                message=(
                    f"Developer 完成（模型返回错误但完成证据存在）："
                    f"{result.get('message', '')}"
                ),
            )

        # 执行失败
        if not result["success"]:
            return FullTaskStepResult(
                name="Developer",
                status="FAILED",
                success=False,
                message=result.get("message", "Developer 执行失败"),
            )

        # 成功但缺证据
        if not result["evidence_found"]:
            return FullTaskStepResult(
                name="Developer",
                status="FAILED",
                success=False,
                message="Claude Code 成功，但缺少完成证据。",
            )

        # 成功
        return FullTaskStepResult(
            name="Developer",
            status="PASS",
            success=True,
            report_path=str(dev_report_path),
            message="Developer 执行成功。",
        )

    # 其他状态
    return FullTaskStepResult(
        name="Developer",
        status="BLOCKED",
        success=False,
        message=f"任务 {task_id} 状态为 {task_status}，无法执行 Developer。",
    )


# ---------------------------------------------------------------------------
# Basic Tester 阶段
# ---------------------------------------------------------------------------

def run_basic_tester_step(task_id: str) -> FullTaskStepResult:
    """执行 Basic Tester 阶段。"""
    try:
        report_path, result = run_tester_for_game_task(task_id)
        return FullTaskStepResult(
            name="Basic Tester",
            status=result.status,
            success=result.result == "PASS",
            report_path=str(report_path),
            message=(
                f"Status: {result.status}, "
                f"Passed: {result.passed_count}, "
                f"Failed: {result.failed_count}"
            ),
        )
    except Exception as e:
        return FullTaskStepResult(
            name="Basic Tester",
            status="BLOCKED",
            success=False,
            message=f"Tester 执行异常：{e}",
        )


# ---------------------------------------------------------------------------
# Reviewer 阶段
# ---------------------------------------------------------------------------

def run_reviewer_step(task_id: str) -> FullTaskStepResult:
    """执行 Reviewer 阶段。"""
    try:
        report_path, parsed = run_reviewer_for_game_task(task_id)

        if parsed is None or not parsed.success:
            error_msg = parsed.error if parsed else "模型调用失败"
            return FullTaskStepResult(
                name="Reviewer",
                status="BLOCKED",
                success=False,
                report_path=str(report_path),
                message=f"Reviewer 解析失败：{error_msg}",
            )

        decision = parsed.decision or "UNKNOWN"
        status = parsed.status or "UNKNOWN"
        success = decision == "APPROVE"

        return FullTaskStepResult(
            name="Reviewer",
            status=decision,
            success=success,
            report_path=str(report_path),
            message=f"Status: {status}, Decision: {decision}",
        )
    except Exception as e:
        return FullTaskStepResult(
            name="Reviewer",
            status="BLOCKED",
            success=False,
            message=f"Reviewer 执行异常：{e}",
        )


# ---------------------------------------------------------------------------
# Main Decision 阶段
# ---------------------------------------------------------------------------

def run_main_decision_step(task_id: str) -> FullTaskStepResult:
    """执行 Main Decision 阶段。"""
    try:
        report_path, decision = run_combined_decision_for_game_task(task_id)

        success = decision.decision == "COMPLETE"

        return FullTaskStepResult(
            name="Main Decision",
            status=decision.decision,
            success=success,
            report_path=str(report_path),
            message=f"Decision: {decision.decision}, Reason: {decision.reason}",
        )
    except Exception as e:
        return FullTaskStepResult(
            name="Main Decision",
            status="BLOCKED",
            success=False,
            message=f"Main Decision 执行异常：{e}",
        )


# ---------------------------------------------------------------------------
# Full Loop Report 生成
# ---------------------------------------------------------------------------

def save_full_loop_report(result: FullTaskLoopResult) -> Path:
    """保存完整闭环报告。"""
    project_root = Path(result.project_path)
    report_dir = project_root / "reports" / "final"
    report_dir.mkdir(parents=True, exist_ok=True)

    report_path = report_dir / f"{result.task_id}-full-loop-report.md"

    # Steps 表格
    steps_rows = []
    for step in result.steps:
        success_text = "是" if step.success else "否"
        report_text = step.report_path or "N/A"
        steps_rows.append(
            f"| {step.name} | {step.status} | {success_text} "
            f"| {report_text} | {step.message} |"
        )

    steps_table = "\n".join(steps_rows)

    report = f"""# {result.task_id} Full Task Loop Report

## Task

任务编号：{result.task_id}

## Project

{result.project_path}

## Final Status

{result.final_status}

## Steps

| 阶段 | 状态 | 成功 | 报告路径 | 说明 |
|---|---|---|---|---|
{steps_table}

## Next Action

{result.next_action or '无'}

## Notes

本报告由 run-project-task-full 自动生成。
"""

    report_path.write_text(report, encoding="utf-8")
    return report_path


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def _stop_and_report(
    project_path: Path,
    task_id: str,
    steps: list[FullTaskStepResult],
    final_status: str,
    next_action: str,
) -> FullTaskLoopResult:
    """停止闭环并生成报告。"""
    loop_result = FullTaskLoopResult(
        project_path=str(project_path),
        task_id=task_id,
        final_status=final_status,
        steps=steps,
        next_action=next_action,
    )
    report_path = save_full_loop_report(loop_result)
    loop_result.full_loop_report_path = str(report_path)
    return loop_result


def run_project_task_full(
    project_path: str | Path,
    task_id: str,
    claude_permission_mode: str = "acceptEdits",
) -> FullTaskLoopResult:
    """执行单个子项目任务的完整闭环 MVP。

    Args:
        project_path: 子项目路径。
        task_id: 任务编号。
        claude_permission_mode: 传递给 Developer 阶段的权限模式。
    """

    project_path = Path(project_path)
    steps: list[FullTaskStepResult] = []

    # ── 阶段 1: Developer ──
    print(f"\n[1/5] Developer 阶段...")
    dev_result = run_developer_step(project_path, task_id, claude_permission_mode=claude_permission_mode)
    steps.append(dev_result)
    print(f"  → {dev_result.status}: {dev_result.message}")

    if not dev_result.success:
        final_status = "BLOCKED" if dev_result.status == "BLOCKED" else "FAILED"
        next_action = "Developer 阶段失败，请检查报告和执行日志。"
        return _stop_and_report(project_path, task_id, steps, final_status, next_action)

    # ── 阶段 2: Basic Tester ──
    print(f"\n[2/5] Basic Tester 阶段...")
    tester_result = run_basic_tester_step(task_id)
    steps.append(tester_result)
    print(f"  → {tester_result.status}: {tester_result.message}")

    if not tester_result.success:
        next_action = "Basic Tester 失败。建议生成 rework prompt，但本 MVP 不自动执行。"
        return _stop_and_report(project_path, task_id, steps, "REQUEST_CHANGES", next_action)

    # ── 阶段 3: Specialized Tester（预留） ──
    print(f"\n[3/5] Specialized Tester 阶段...")
    spec_result = maybe_run_specialized_tester(project_path, task_id)
    if spec_result is not None:
        steps.append(spec_result)
        print(f"  → {spec_result.status}: {spec_result.message}")

        if not spec_result.success:
            next_action = "专项 Tester 失败。建议生成 rework prompt，但本 MVP 不自动执行。"
            return _stop_and_report(
                project_path, task_id, steps, "REQUEST_CHANGES", next_action,
            )
    else:
        print(f"  → SKIPPED: 无对应专项 Tester")

    # ── 阶段 4: Reviewer ──
    print(f"\n[4/5] Reviewer 阶段...")
    reviewer_result = run_reviewer_step(task_id)
    steps.append(reviewer_result)
    print(f"  → {reviewer_result.status}: {reviewer_result.message}")

    if not reviewer_result.success:
        if reviewer_result.status == "BLOCKED":
            next_action = "Reviewer 被阻塞（API 429 或调用失败），需要人工处理。"
            return _stop_and_report(project_path, task_id, steps, "BLOCKED", next_action)
        next_action = "Reviewer 未批准。建议生成 rework prompt，但本 MVP 不自动执行。"
        return _stop_and_report(project_path, task_id, steps, "REQUEST_CHANGES", next_action)

    # ── 阶段 5: Main Decision ──
    print(f"\n[5/5] Main Decision 阶段...")
    decision_result = run_main_decision_step(task_id)
    steps.append(decision_result)
    print(f"  → {decision_result.status}: {decision_result.message}")

    if not decision_result.success:
        if decision_result.status == "BLOCKED":
            next_action = "Main Decision 被阻塞，需要人工检查报告。"
            return _stop_and_report(project_path, task_id, steps, "BLOCKED", next_action)
        next_action = "Main Decision 结果为 REQUEST_CHANGES。建议生成 rework prompt。"
        return _stop_and_report(project_path, task_id, steps, "REQUEST_CHANGES", next_action)

    # ── 全部通过 ──
    return _stop_and_report(
        project_path, task_id, steps, "COMPLETE",
        "任务完整闭环通过。可以进入下一个任务。",
    )
