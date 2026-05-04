"""
Main Agent 决策协议 MVP

规则版 Main Agent，根据任务状态、执行结果和完成证据决定下一步动作。
第一版不接入真实模型，只做规则判断。

T031 新增综合决策能力：读取 Developer / Tester / Reviewer 三方报告，生成 CombinedDecision。
"""

import re
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


# ---------------------------------------------------------------------------
# T031: 综合决策（Developer / Tester / Reviewer 三方）
# ---------------------------------------------------------------------------

@dataclass
class CombinedDecision:
    """综合决策结果。"""
    task_id: str
    developer_report_exists: bool
    tester_status: str | None
    tester_result: str | None
    reviewer_status: str | None
    reviewer_decision: str | None
    decision: str  # COMPLETE / REQUEST_CHANGES / RETRY / BLOCKED
    reason: str
    next_action: str
    blocked: bool = False


def parse_tester_report(content: str) -> dict:
    """解析 Tester 报告中的 Status 和 Result。

    Args:
        content: 测试报告 markdown 内容

    Returns:
        {"status": str | None, "result": str | None}
    """
    data = {"status": None, "result": None}

    # 解析 ## Status 后的非空行
    status_match = re.search(
        r"^##\s+Status\s*\n+\s*(PASS|FAIL|RETRY|BLOCKED|INFO)",
        content, re.MULTILINE,
    )
    if status_match:
        data["status"] = status_match.group(1)

    # 解析 ## Result 后的非空行
    result_match = re.search(
        r"^##\s+Result\s*\n+\s*(PASS|FAIL)",
        content, re.MULTILINE,
    )
    if result_match:
        data["result"] = result_match.group(1)

    return data


def parse_reviewer_report(content: str) -> dict:
    """解析 Reviewer 报告中的 status 和 decision。

    优先解析 ## Parsed Result 段落。
    如果 Parsed Result 缺失，回退到 ## Machine Readable Result 的 JSON 块。

    Args:
        content: 审查报告 markdown 内容

    Returns:
        {"status": str | None, "decision": str | None}
    """
    data = {"status": None, "decision": None}

    # 优先：解析 ## Parsed Result 段
    parsed_section = re.search(
        r"^##\s+Parsed\s+Result\s*\n(.*?)(?=\n##\s|\Z)",
        content, re.MULTILINE | re.DOTALL,
    )
    if parsed_section:
        section_text = parsed_section.group(1)

        status_match = re.search(r"status:\s*(PASS|FAIL|RETRY|BLOCKED|INFO)", section_text)
        if status_match:
            data["status"] = status_match.group(1)

        decision_match = re.search(r"decision:\s*(APPROVE|REQUEST_CHANGES|RETRY|BLOCKED)", section_text)
        if decision_match:
            data["decision"] = decision_match.group(1)

        if data["status"] and data["decision"]:
            return data

    # 回退：解析 ## Machine Readable Result 中的 JSON
    json_block = re.search(
        r"```json\s*\n(.*?)```",
        content, re.DOTALL,
    )
    if json_block:
        try:
            import json
            parsed = json.loads(json_block.group(1))
            data["status"] = parsed.get("status")
            data["decision"] = parsed.get("decision")
        except (json.JSONDecodeError, ValueError):
            pass

    return data


def decide_from_dev_test_review(
    task_id: str,
    dev_report_exists: bool,
    tester_data: dict,
    reviewer_data: dict,
) -> CombinedDecision:
    """综合 Developer / Tester / Reviewer 三方结果生成 Main Decision。

    Args:
        task_id: 任务编号
        dev_report_exists: 开发报告是否存在
        tester_data: parse_tester_report 返回值
        reviewer_data: parse_reviewer_report 返回值

    Returns:
        CombinedDecision 综合决策结果
    """
    # 规则 1：开发报告不存在
    if not dev_report_exists:
        return CombinedDecision(
            task_id=task_id,
            developer_report_exists=False,
            tester_status=tester_data.get("status"),
            tester_result=tester_data.get("result"),
            reviewer_status=reviewer_data.get("status"),
            reviewer_decision=reviewer_data.get("decision"),
            decision="BLOCKED",
            reason="缺少开发报告",
            next_action="返回 Developer Agent 重新生成开发报告",
            blocked=True,
        )

    # 规则 5：Tester 报告解析失败
    if tester_data.get("result") is None and tester_data.get("status") is None:
        return CombinedDecision(
            task_id=task_id,
            developer_report_exists=True,
            tester_status=None,
            tester_result=None,
            reviewer_status=reviewer_data.get("status"),
            reviewer_decision=reviewer_data.get("decision"),
            decision="BLOCKED",
            reason="Tester 报告解析失败",
            next_action="检查测试报告格式或重新生成测试报告",
            blocked=True,
        )

    # 规则 5：Reviewer 报告解析失败
    if reviewer_data.get("status") is None and reviewer_data.get("decision") is None:
        return CombinedDecision(
            task_id=task_id,
            developer_report_exists=True,
            tester_status=tester_data.get("status"),
            tester_result=tester_data.get("result"),
            reviewer_status=None,
            reviewer_decision=None,
            decision="BLOCKED",
            reason="Reviewer 报告解析失败",
            next_action="检查审查报告格式或重新生成审查报告",
            blocked=True,
        )

    # 规则 2：Tester 失败
    if tester_data.get("result") != "PASS":
        return CombinedDecision(
            task_id=task_id,
            developer_report_exists=True,
            tester_status=tester_data.get("status"),
            tester_result=tester_data.get("result"),
            reviewer_status=reviewer_data.get("status"),
            reviewer_decision=reviewer_data.get("decision"),
            decision="REQUEST_CHANGES",
            reason="Tester 测试未通过",
            next_action="返回 Developer Agent 修复测试失败项",
        )

    # 规则 3：Reviewer 不批准
    if reviewer_data.get("decision") != "APPROVE":
        return CombinedDecision(
            task_id=task_id,
            developer_report_exists=True,
            tester_status=tester_data.get("status"),
            tester_result=tester_data.get("result"),
            reviewer_status=reviewer_data.get("status"),
            reviewer_decision=reviewer_data.get("decision"),
            decision="REQUEST_CHANGES",
            reason="Reviewer 审查未批准",
            next_action="根据 Reviewer Issues 返回 Developer Agent 修复",
        )

    # 规则 4：三方都通过
    return CombinedDecision(
        task_id=task_id,
        developer_report_exists=True,
        tester_status=tester_data.get("status"),
        tester_result=tester_data.get("result"),
        reviewer_status=reviewer_data.get("status"),
        reviewer_decision=reviewer_data.get("decision"),
        decision="COMPLETE",
        reason="Developer / Tester / Reviewer 三方证据均通过",
        next_action="可以进入下一个任务",
    )


def save_combined_decision(decision: CombinedDecision, output_path: str | Path) -> Path:
    """保存综合决策报告。"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Evidence Inputs 段
    dev_text = "exists" if decision.developer_report_exists else "missing"
    tester_text = decision.tester_result or "missing"
    reviewer_text = decision.reviewer_decision or "missing"

    # Parsed Results 段
    dev_parsed = "true" if decision.developer_report_exists else "false"
    tester_status_text = decision.tester_status or "N/A"
    tester_result_text = decision.tester_result or "N/A"
    reviewer_status_text = decision.reviewer_status or "N/A"
    reviewer_decision_text = decision.reviewer_decision or "N/A"

    report = f"""# {decision.task_id} Main Decision Report

## Agent

Main Agent

## Task

任务编号：{decision.task_id}

## Evidence Inputs

- Developer Report: {dev_text}
- Tester Report: {tester_text}
- Reviewer Report: {reviewer_text}

## Parsed Results

### Developer

developer_report_exists: {dev_parsed}

### Tester

status: {tester_status_text}
result: {tester_result_text}

### Reviewer

status: {reviewer_status_text}
decision: {reviewer_decision_text}

## Main Decision

{decision.decision}

## Reason

{decision.reason}

## Next Action

{decision.next_action}

## Notes

本报告只做综合决策，不自动返工，不自动修改任务状态。
"""

    output_path.write_text(report, encoding="utf-8")
    return output_path


def run_combined_decision_for_game_task(task_id: str = "G003") -> Path:
    """对 down-100-floors-game 的指定任务生成综合决策报告。

    Args:
        task_id: 游戏任务编号，默认 G003

    Returns:
        (报告路径, CombinedDecision)
    """
    runner_root = Path(__file__).parent.parent
    game_project = runner_root / "projects" / "down-100-floors-game"

    # 1. 检查 Developer 报告
    dev_report_path = game_project / "reports" / "dev" / f"{task_id}-dev-report.md"
    dev_report_exists = dev_report_path.exists()

    # 2. 读取并解析 Tester 报告
    tester_report_path = game_project / "reports" / "test" / f"{task_id}-test-report.md"
    tester_data = {"status": None, "result": None}
    if tester_report_path.exists():
        tester_content = tester_report_path.read_text(encoding="utf-8")
        tester_data = parse_tester_report(tester_content)

    # 3. 读取并解析 Reviewer 报告
    reviewer_report_path = game_project / "reports" / "review" / f"{task_id}-review-report.md"
    reviewer_data = {"status": None, "decision": None}
    if reviewer_report_path.exists():
        reviewer_content = reviewer_report_path.read_text(encoding="utf-8")
        reviewer_data = parse_reviewer_report(reviewer_content)

    # 4. 综合决策
    decision = decide_from_dev_test_review(
        task_id=task_id,
        dev_report_exists=dev_report_exists,
        tester_data=tester_data,
        reviewer_data=reviewer_data,
    )

    # 5. 保存报告
    report_path = game_project / "reports" / "final" / f"{task_id}-main-decision.md"
    save_combined_decision(decision, report_path)

    return report_path, decision


# ---------------------------------------------------------------------------
# T037: 增强综合决策（Developer / Tester / Behavior Tester / Reviewer 四方）
# ---------------------------------------------------------------------------

@dataclass
class EnhancedCombinedDecision:
    """增强综合决策结果（含行为测试）。"""
    task_id: str
    developer_report_exists: bool
    basic_tester_status: str | None
    basic_tester_result: str | None
    behavior_tester_status: str | None
    behavior_tester_result: str | None
    behavior_report_exists: bool
    reviewer_status: str | None
    reviewer_decision: str | None
    decision: str  # COMPLETE / REQUEST_CHANGES / RETRY / BLOCKED
    reason: str
    next_action: str
    blocked: bool = False


def decide_from_dev_test_behavior_review(
    task_id: str,
    dev_report_exists: bool,
    basic_tester_data: dict,
    behavior_tester_data: dict | None,
    reviewer_data: dict,
) -> EnhancedCombinedDecision:
    """综合 Developer / Tester / Behavior Tester / Reviewer 四方结果生成 Main Decision。

    Args:
        task_id: 任务编号
        dev_report_exists: 开发报告是否存在
        basic_tester_data: 基础 Tester 报告解析结果
        behavior_tester_data: 行为 Tester 报告解析结果（None 表示报告不存在）
        reviewer_data: Reviewer 报告解析结果

    Returns:
        EnhancedCombinedDecision 增强综合决策结果
    """
    behavior_exists = behavior_tester_data is not None
    b_status = behavior_tester_data.get("status") if behavior_tester_data else None
    b_result = behavior_tester_data.get("result") if behavior_tester_data else None

    # 规则 1：开发报告不存在
    if not dev_report_exists:
        return EnhancedCombinedDecision(
            task_id=task_id,
            developer_report_exists=False,
            basic_tester_status=basic_tester_data.get("status"),
            basic_tester_result=basic_tester_data.get("result"),
            behavior_tester_status=b_status,
            behavior_tester_result=b_result,
            behavior_report_exists=behavior_exists,
            reviewer_status=reviewer_data.get("status"),
            reviewer_decision=reviewer_data.get("decision"),
            decision="BLOCKED",
            reason="缺少开发报告",
            next_action="返回 Developer Agent 重新生成开发报告",
            blocked=True,
        )

    # 规则 2：基础 Tester 失败
    if basic_tester_data.get("result") != "PASS":
        return EnhancedCombinedDecision(
            task_id=task_id,
            developer_report_exists=True,
            basic_tester_status=basic_tester_data.get("status"),
            basic_tester_result=basic_tester_data.get("result"),
            behavior_tester_status=b_status,
            behavior_tester_result=b_result,
            behavior_report_exists=behavior_exists,
            reviewer_status=reviewer_data.get("status"),
            reviewer_decision=reviewer_data.get("decision"),
            decision="REQUEST_CHANGES",
            reason="基础 Tester 测试未通过",
            next_action="返回 Developer Agent 修复测试失败项",
        )

    # 规则 3：行为 Tester 报告存在但失败
    if behavior_exists and b_result != "PASS":
        return EnhancedCombinedDecision(
            task_id=task_id,
            developer_report_exists=True,
            basic_tester_status=basic_tester_data.get("status"),
            basic_tester_result=basic_tester_data.get("result"),
            behavior_tester_status=b_status,
            behavior_tester_result=b_result,
            behavior_report_exists=behavior_exists,
            reviewer_status=reviewer_data.get("status"),
            reviewer_decision=reviewer_data.get("decision"),
            decision="REQUEST_CHANGES",
            reason="行为 Tester 测试未通过",
            next_action="返回 Developer Agent 修复行为逻辑问题",
        )

    # 规则 4：Reviewer 不批准
    if reviewer_data.get("decision") != "APPROVE":
        return EnhancedCombinedDecision(
            task_id=task_id,
            developer_report_exists=True,
            basic_tester_status=basic_tester_data.get("status"),
            basic_tester_result=basic_tester_data.get("result"),
            behavior_tester_status=b_status,
            behavior_tester_result=b_result,
            behavior_report_exists=behavior_exists,
            reviewer_status=reviewer_data.get("status"),
            reviewer_decision=reviewer_data.get("decision"),
            decision="REQUEST_CHANGES",
            reason="Reviewer 审查未批准",
            next_action="根据 Reviewer Issues 返回 Developer Agent 修复",
        )

    # 规则 5：全部通过
    if behavior_exists:
        reason = "Developer / Tester / Behavior Tester / Reviewer 证据均通过"
    else:
        reason = "Developer / Tester / Reviewer 证据均通过（无行为测试报告）"

    return EnhancedCombinedDecision(
        task_id=task_id,
        developer_report_exists=True,
        basic_tester_status=basic_tester_data.get("status"),
        basic_tester_result=basic_tester_data.get("result"),
        behavior_tester_status=b_status,
        behavior_tester_result=b_result,
        behavior_report_exists=behavior_exists,
        reviewer_status=reviewer_data.get("status"),
        reviewer_decision=reviewer_data.get("decision"),
        decision="COMPLETE",
        reason=reason,
        next_action="可以进入下一个任务",
    )


def save_enhanced_combined_decision(
    decision: EnhancedCombinedDecision, output_path: str | Path,
) -> Path:
    """保存增强综合决策报告。"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    dev_text = "exists" if decision.developer_report_exists else "missing"
    basic_text = decision.basic_tester_result or "missing"
    behavior_text = decision.behavior_tester_result if decision.behavior_report_exists else "missing"
    reviewer_text = decision.reviewer_decision or "missing"

    report = f"""# {decision.task_id} Main Decision Report V2

## Agent

Main Agent

## Task

任务编号：{decision.task_id}

## Evidence Inputs

- Developer Report: {dev_text}
- Basic Tester Report: {basic_text}
- Behavior Tester Report: {behavior_text}
- Reviewer Report: {reviewer_text}

## Parsed Results

### Developer

developer_report_exists: {'true' if decision.developer_report_exists else 'false'}

### Basic Tester

status: {decision.basic_tester_status or 'N/A'}
result: {decision.basic_tester_result or 'N/A'}

### Behavior Tester

status: {decision.behavior_tester_status or 'N/A'}
result: {decision.behavior_tester_result or 'N/A'}
report_exists: {'true' if decision.behavior_report_exists else 'false'}

### Reviewer

status: {decision.reviewer_status or 'N/A'}
decision: {decision.reviewer_decision or 'N/A'}

## Main Decision

{decision.decision}

## Reason

{decision.reason}

## Next Action

{decision.next_action}

## Notes

本报告为增强综合决策（含行为测试），不自动返工，不自动修改任务状态。
"""

    output_path.write_text(report, encoding="utf-8")
    return output_path


def run_enhanced_combined_decision_for_game_task(
    task_id: str = "G004",
) -> tuple[Path, EnhancedCombinedDecision]:
    """对 down-100-floors-game 的指定任务生成增强综合决策报告。

    读取 Developer / Basic Tester / Behavior Tester / Reviewer 四方报告，
    生成增强版综合决策。

    Args:
        task_id: 游戏任务编号，默认 G004

    Returns:
        (报告路径, EnhancedCombinedDecision)
    """
    runner_root = Path(__file__).parent.parent
    game_project = runner_root / "projects" / "down-100-floors-game"

    # 1. 检查 Developer 报告
    dev_report_path = game_project / "reports" / "dev" / f"{task_id}-dev-report.md"
    dev_report_exists = dev_report_path.exists()

    # 2. 读取并解析基础 Tester 报告
    basic_tester_path = game_project / "reports" / "test" / f"{task_id}-test-report.md"
    basic_tester_data = {"status": None, "result": None}
    if basic_tester_path.exists():
        basic_tester_data = parse_tester_report(
            basic_tester_path.read_text(encoding="utf-8")
        )

    # 3. 读取并解析行为 Tester 报告（可选）
    behavior_tester_path = game_project / "reports" / "test" / f"{task_id}-behavior-test-report.md"
    behavior_tester_data = None
    if behavior_tester_path.exists():
        behavior_tester_data = parse_tester_report(
            behavior_tester_path.read_text(encoding="utf-8")
        )

    # 4. 读取并解析 Reviewer 报告
    reviewer_path = game_project / "reports" / "review" / f"{task_id}-review-report.md"
    reviewer_data = {"status": None, "decision": None}
    if reviewer_path.exists():
        reviewer_data = parse_reviewer_report(
            reviewer_path.read_text(encoding="utf-8")
        )

    # 5. 增强综合决策
    decision = decide_from_dev_test_behavior_review(
        task_id=task_id,
        dev_report_exists=dev_report_exists,
        basic_tester_data=basic_tester_data,
        behavior_tester_data=behavior_tester_data,
        reviewer_data=reviewer_data,
    )

    # 6. 保存报告为 v2
    report_path = game_project / "reports" / "final" / f"{task_id}-main-decision-v2.md"
    save_enhanced_combined_decision(decision, report_path)

    return report_path, decision
