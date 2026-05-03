"""
Main Agent 决策协议 MVP

规则版 Main Agent，根据任务状态、执行结果和完成证据决定下一步动作。
第一版不接入真实模型，只做规则判断。
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class MainDecision:
    """Main Agent 决策结果。"""
    decision: str
    reason: str
    task_id: str | None = None
    task_title: str | None = None
    assigned_agent: str | None = None
    next_command: str | None = None
    evidence_required: str | None = None
    blocked: bool = False


def decide_next_action(
    tasks: list[dict],
    latest_result: dict | None = None,
    evidence_exists: bool | None = None,
) -> MainDecision:
    """根据任务状态、最近执行结果和完成证据决定下一步动作。

    Args:
        tasks: 解析后的任务列表
        latest_result: analyze_claude_output 的返回结果（可选）
        evidence_exists: 当前 in_progress 任务的完成证据是否存在（可选）

    Returns:
        MainDecision 决策结果
    """
    in_progress_task = None
    has_pending = False

    for task in tasks:
        if task["status"] == "in_progress" and in_progress_task is None:
            in_progress_task = task
        if task["status"] == "pending":
            has_pending = True

    # 规则 1：存在 in_progress 任务
    if in_progress_task:
        task_id = in_progress_task["id"]
        task_title = in_progress_task["title"]

        # 检查是否被 429 限额
        if latest_result and latest_result.get("is_rate_limited"):
            return MainDecision(
                decision="BLOCKED",
                reason="API 限额（429），暂停执行，等待额度恢复。",
                task_id=task_id,
                task_title=task_title,
                blocked=True,
            )

        # 未执行过
        if latest_result is None:
            return MainDecision(
                decision="RETRY",
                reason=f"当前任务 {task_id}（{task_title}）标记为 in_progress 但未执行过，需要重新执行。",
                task_id=task_id,
                task_title=task_title,
                assigned_agent=in_progress_task.get("role", "Developer"),
                next_command="python runner.py retry-current",
            )

        # 执行失败
        if not latest_result.get("success", False):
            return MainDecision(
                decision="RETRY",
                reason=f"当前任务 {task_id}（{task_title}）执行失败（退出码 {latest_result.get('returncode', 'unknown')}），需要重新执行。",
                task_id=task_id,
                task_title=task_title,
                assigned_agent=in_progress_task.get("role", "Developer"),
                next_command="python runner.py retry-current",
            )

        # 执行成功但缺少完成证据
        if not evidence_exists:
            evidence_file = f"reports/dev/{task_id}-dev-report.md"
            return MainDecision(
                decision="RETRY",
                reason=f"当前任务 {task_id}（{task_title}）执行成功但缺少完成证据（{evidence_file}），需要重新执行。",
                task_id=task_id,
                task_title=task_title,
                assigned_agent=in_progress_task.get("role", "Developer"),
                next_command="python runner.py retry-current",
                evidence_required=evidence_file,
            )

        # 执行成功且有完成证据
        return MainDecision(
            decision="COMPLETE",
            reason=f"当前任务 {task_id}（{task_title}）执行成功且有完成证据，可以标记为 done。",
            task_id=task_id,
            task_title=task_title,
            assigned_agent=in_progress_task.get("role", "Developer"),
            next_command="python runner.py auto-complete-success",
        )

    # 规则 2：有 pending 任务
    if has_pending:
        return MainDecision(
            decision="DEVELOP",
            reason="当前没有 in_progress 任务，但有 pending 任务，建议执行下一个任务。",
            next_command="python runner.py run-next",
        )

    # 规则 3：没有 pending，也没有 in_progress
    return MainDecision(
        decision="STOP",
        reason="所有任务已完成或当前没有可执行任务。",
    )


def save_main_decision(
    decision: MainDecision,
    output_dir: str | Path = "reports/main",
) -> Path:
    """保存 Main Agent 决策报告。

    Args:
        decision: 决策结果
        output_dir: 输出目录

    Returns:
        保存的文件路径
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    task_suffix = decision.task_id or "general"
    filename = f"{task_suffix}-main-decision.md"
    output_file = output_dir / filename

    lines = [
        "# Main Agent Decision",
        "",
        f"## Decision",
        "",
        f"{decision.decision}",
        "",
        f"## Reason",
        "",
        f"{decision.reason}",
        "",
        f"## Details",
        "",
    ]

    if decision.task_id:
        lines.append(f"- 任务编号：{decision.task_id}")
    if decision.task_title:
        lines.append(f"- 任务名称：{decision.task_title}")
    if decision.assigned_agent:
        lines.append(f"- 分配 Agent：{decision.assigned_agent}")
    if decision.next_command:
        lines.append(f"- 建议命令：`{decision.next_command}`")
    if decision.evidence_required:
        lines.append(f"- 需要证据：{decision.evidence_required}")
    if decision.blocked:
        lines.append(f"- **被阻塞**：是")

    lines.extend([
        "",
        f"## Timestamp",
        "",
        f"{datetime.now().isoformat()}",
        "",
    ])

    output_file.write_text("\n".join(lines), encoding="utf-8")
    return output_file
