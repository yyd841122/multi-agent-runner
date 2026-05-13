"""External Request → Task Proposal Dry-run Bridge.

统一桥接层：将 local_inbox 和 github_issue 两类外部请求
统一经过 safety gate 后生成 TaskProposal dry-run。

不修改 docs/tasks.md，不执行 runner，不调用模型，不执行 Git。
不访问 GitHub API，不调用 gh CLI，不创建 workflow。

T192 实现。
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# 从现有工具导入（保守兼容方式）
# ---------------------------------------------------------------------------

# tools 目录在项目根下，需要将 tools 目录加入 import 路径
_TOOLS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TOOLS_DIR.parent

if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

# 尝试从包导入，失败则直接 import 模块名
try:
    from tools.external_request_inbox import (
        ExternalRequest as InboxExternalRequest,
        ExternalRequestSafetyResult as InboxSafetyResult,
        TaskProposal as InboxTaskProposal,
        parse_markdown_request,
        run_safety_gate as inbox_run_safety_gate,
        build_task_proposal as inbox_build_task_proposal,
    )
except ImportError:
    from external_request_inbox import (
        ExternalRequest as InboxExternalRequest,
        ExternalRequestSafetyResult as InboxSafetyResult,
        TaskProposal as InboxTaskProposal,
        parse_markdown_request,
        run_safety_gate as inbox_run_safety_gate,
        build_task_proposal as inbox_build_task_proposal,
    )

try:
    from tools.github_issue_entry import (
        GitHubIssueRequest,
        parse_github_issue_fixture,
        github_issue_to_external_request,
        validate_github_issue,
        ExternalRequest as IssueExternalRequest,
        ExternalRequestSafetyResult as IssueSafetyResult,
        TaskProposal as IssueTaskProposal,
        run_safety_gate as issue_run_safety_gate,
        build_task_proposal as issue_build_task_proposal,
    )
except ImportError:
    from github_issue_entry import (
        GitHubIssueRequest,
        parse_github_issue_fixture,
        github_issue_to_external_request,
        validate_github_issue,
        ExternalRequest as IssueExternalRequest,
        ExternalRequestSafetyResult as IssueSafetyResult,
        TaskProposal as IssueTaskProposal,
        run_safety_gate as issue_run_safety_gate,
        build_task_proposal as issue_build_task_proposal,
    )


# ---------------------------------------------------------------------------
# 统一数据结构
# ---------------------------------------------------------------------------

@dataclass
class UnifiedTaskProposalResult:
    """统一 TaskProposal dry-run 结果。"""

    result: str  # pass / fail
    source_type: str  # local_inbox / github_issue
    request_id: str
    issue_id: str  # 仅 github_issue 有值
    safety_ok: bool
    risk_level: str
    prompt_injection_risk: str
    allowed_to_plan: bool
    allowed_to_execute: bool
    requires_user_approval: bool
    task_proposal_created: bool
    blocked_reasons: list[str]
    warnings: list[str]
    proposed_tasks: list[str]
    proposal_id: str
    proposal_title: str
    proposal_next_action: str
    report_path: str
    fail_reason: str


# ---------------------------------------------------------------------------
# 统一报告生成
# ---------------------------------------------------------------------------

def ensure_directory(path: Path) -> None:
    """确保目录存在。"""
    path.mkdir(parents=True, exist_ok=True)


def build_unified_report(
    result: UnifiedTaskProposalResult,
    output_dir: Path,
) -> Path:
    """生成统一 TaskProposal dry-run 报告。"""
    ensure_directory(output_dir)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"PROPOSAL-{result.source_type}-{result.request_id}-{timestamp}-report.md"
    report_path = output_dir / filename

    lines: list[str] = []
    lines.append(f"# Task Proposal Dry-run Report")
    lines.append("")
    lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}")
    lines.append(f"阶段：Stage 11 — External Request → Task Proposal Dry-run")
    lines.append(f"来源类型：{result.source_type}")
    lines.append(f"请求 ID：{result.request_id}")
    lines.append("")

    # Section 1: Safety Gate Result
    lines.append("## 1. Safety Gate Result")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|-------|-------|")
    lines.append(f"| SAFETY_STATUS | {'pass' if result.safety_ok else 'fail'} |")
    lines.append(f"| RISK_LEVEL | {result.risk_level} |")
    lines.append(f"| PROMPT_INJECTION_RISK | {result.prompt_injection_risk} |")
    lines.append(f"| ALLOWED_TO_PLAN | {'yes' if result.allowed_to_plan else 'no'} |")
    lines.append(f"| ALLOWED_TO_EXECUTE | {'yes' if result.allowed_to_execute else 'no'} |")
    lines.append(f"| REQUIRES_USER_APPROVAL | {'yes' if result.requires_user_approval else 'no'} |")
    lines.append("")

    if result.blocked_reasons:
        lines.append("### Blocked Reasons")
        lines.append("")
        for r in result.blocked_reasons:
            lines.append(f"- `{r}`")
        lines.append("")

    if result.warnings:
        lines.append("### Warnings")
        lines.append("")
        for w in result.warnings:
            lines.append(f"- `{w}`")
        lines.append("")

    # Section 2: Task Proposal
    lines.append("## 2. Task Proposal")
    lines.append("")
    if result.task_proposal_created:
        lines.append("| Field | Value |")
        lines.append("|-------|-------|")
        lines.append(f"| PROPOSAL_ID | {result.proposal_id} |")
        lines.append(f"| TITLE | {result.proposal_title} |")
        lines.append(f"| NEXT_ACTION | {result.proposal_next_action} |")
        lines.append("")
        if result.proposed_tasks:
            lines.append("### Proposed Tasks")
            lines.append("")
            for i, t in enumerate(result.proposed_tasks, 1):
                lines.append(f"{i}. {t}")
            lines.append("")
    else:
        lines.append("No task proposal generated (safety gate blocked or not allowed to plan).")
        lines.append("")

    # Section 3: Safety Guarantees
    lines.append("## 3. Safety Guarantees")
    lines.append("")
    lines.append("- DOCS_TASKS_MODIFIED=no")
    lines.append("- RUNNER_EXECUTED=no")
    lines.append("- GIT_ADD_EXECUTED=no")
    lines.append("- GIT_COMMIT_EXECUTED=no")
    lines.append("- GIT_PUSH_EXECUTED=no")
    lines.append("- GITHUB_API_ACCESSED=no")
    lines.append("- GH_CLI_CALLED=no")
    lines.append("- GITHUB_WORKFLOW_CREATED=no")
    lines.append("- USER_APPROVAL_REQUIRED=yes")
    lines.append("- DRY_RUN=yes")
    lines.append("")

    # 结构化状态行
    lines.append("---")
    lines.append("")
    lines.append("```")
    lines.append(f"TASK_PROPOSAL_DRY_RUN_RESULT={'pass' if result.result == 'pass' else 'fail'}")
    lines.append(f"SOURCE_TYPE={result.source_type}")
    lines.append(f"REQUEST_ID={result.request_id}")
    if result.issue_id:
        lines.append(f"ISSUE_ID={result.issue_id}")
    else:
        lines.append("ISSUE_ID=")
    lines.append(f"SAFETY_STATUS={'pass' if result.safety_ok else 'fail'}")
    lines.append(f"PROMPT_INJECTION_RISK={result.prompt_injection_risk}")
    lines.append(f"ALLOWED_TO_PLAN={'yes' if result.allowed_to_plan else 'no'}")
    lines.append("ALLOWED_TO_EXECUTE=no")
    lines.append(f"TASK_PROPOSAL_CREATED={'yes' if result.task_proposal_created else 'no'}")
    lines.append("DOCS_TASKS_MODIFIED=no")
    lines.append("RUNNER_EXECUTED=no")
    lines.append("GIT_ADD_EXECUTED=no")
    lines.append("GIT_COMMIT_EXECUTED=no")
    lines.append("GIT_PUSH_EXECUTED=no")
    lines.append("GITHUB_API_ACCESSED=no")
    lines.append("GH_CLI_CALLED=no")
    lines.append("GITHUB_WORKFLOW_CREATED=no")
    lines.append("USER_APPROVAL_REQUIRED=yes")
    lines.append(f"CHECK_RESULT={'pass' if result.result == 'pass' else 'fail'}")
    lines.append("```")
    lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


# ---------------------------------------------------------------------------
# Local Inbox 处理
# ---------------------------------------------------------------------------

def process_local_inbox(
    request_file: Path,
    output_dir: Path,
) -> UnifiedTaskProposalResult:
    """处理 local_inbox 请求，返回统一结果。"""
    # 1. 解析请求
    external_request = parse_markdown_request(request_file)

    # 2. 运行 safety gate
    safety = inbox_run_safety_gate(external_request)

    # 3. 生成 TaskProposal（仅在 allowed_to_plan 时）
    proposal = None
    if safety.allowed_to_plan:
        proposal = inbox_build_task_proposal(external_request, safety)

    # 4. 构建统一结果
    task_proposal_created = proposal is not None and safety.allowed_to_plan

    proposed_tasks: list[str] = []
    proposal_id = ""
    proposal_title = ""
    proposal_next_action = ""
    if proposal:
        proposed_tasks = proposal.proposed_tasks
        proposal_id = proposal.proposal_id
        proposal_title = proposal.title
        proposal_next_action = proposal.next_action

    # 5. 生成报告
    result_str = "pass" if safety.ok else "fail"
    fail_reason = "; ".join(safety.blocked_reasons) if safety.blocked_reasons else ""

    result = UnifiedTaskProposalResult(
        result=result_str,
        source_type="local_inbox",
        request_id=external_request.request_id,
        issue_id="",
        safety_ok=safety.ok,
        risk_level=safety.risk_level,
        prompt_injection_risk=safety.prompt_injection_risk,
        allowed_to_plan=safety.allowed_to_plan,
        allowed_to_execute=safety.allowed_to_execute,
        requires_user_approval=safety.requires_user_approval,
        task_proposal_created=task_proposal_created,
        blocked_reasons=safety.blocked_reasons,
        warnings=safety.warnings,
        proposed_tasks=proposed_tasks,
        proposal_id=proposal_id,
        proposal_title=proposal_title,
        proposal_next_action=proposal_next_action,
        report_path="",
        fail_reason=fail_reason,
    )

    report_path = build_unified_report(result, output_dir)
    result.report_path = str(report_path)
    return result


# ---------------------------------------------------------------------------
# GitHub Issue 处理
# ---------------------------------------------------------------------------

def process_github_issue(
    fixture_file: Path,
    output_dir: Path,
) -> UnifiedTaskProposalResult:
    """处理 github_issue fixture，返回统一结果。"""
    # 1. 解析 fixture
    issue = parse_github_issue_fixture(fixture_file)

    # 2. GitHub Issue 专用预检查
    issue_blocked = validate_github_issue(issue)
    if issue_blocked:
        repo_slug = issue.repository.replace("/", "-") if issue.repository else "unknown"
        request_id = f"GH-ISSUE-{repo_slug}-{issue.issue_number or '0'}"
        result = UnifiedTaskProposalResult(
            result="fail",
            source_type="github_issue",
            request_id=request_id,
            issue_id=issue.issue_id,
            safety_ok=False,
            risk_level="high",
            prompt_injection_risk="high",
            allowed_to_plan=False,
            allowed_to_execute=False,
            requires_user_approval=True,
            task_proposal_created=False,
            blocked_reasons=issue_blocked,
            warnings=[],
            proposed_tasks=[],
            proposal_id="",
            proposal_title="",
            proposal_next_action="stop",
            report_path="",
            fail_reason="; ".join(issue_blocked),
        )
        report_path = build_unified_report(result, output_dir)
        result.report_path = str(report_path)
        return result

    # 3. 映射到 ExternalRequest
    external_request = github_issue_to_external_request(issue)

    # 4. 运行 safety gate（使用 github_issue_entry 的版本）
    safety = issue_run_safety_gate(external_request)

    # 5. 生成 TaskProposal（仅在 allowed_to_plan 时）
    proposal = None
    if safety.allowed_to_plan:
        proposal = issue_build_task_proposal(external_request, safety)

    # 6. 构建统一结果
    task_proposal_created = proposal is not None and safety.allowed_to_plan

    proposed_tasks: list[str] = []
    proposal_id = ""
    proposal_title = ""
    proposal_next_action = ""
    if proposal:
        proposed_tasks = proposal.proposed_tasks
        proposal_id = proposal.proposal_id
        proposal_title = proposal.title
        proposal_next_action = proposal.next_action

    result_str = "pass" if safety.ok else "fail"
    fail_reason = "; ".join(safety.blocked_reasons) if safety.blocked_reasons else ""

    result = UnifiedTaskProposalResult(
        result=result_str,
        source_type="github_issue",
        request_id=external_request.request_id,
        issue_id=issue.issue_id,
        safety_ok=safety.ok,
        risk_level=safety.risk_level,
        prompt_injection_risk=safety.prompt_injection_risk,
        allowed_to_plan=safety.allowed_to_plan,
        allowed_to_execute=safety.allowed_to_execute,
        requires_user_approval=safety.requires_user_approval,
        task_proposal_created=task_proposal_created,
        blocked_reasons=safety.blocked_reasons,
        warnings=safety.warnings,
        proposed_tasks=proposed_tasks,
        proposal_id=proposal_id,
        proposal_title=proposal_title,
        proposal_next_action=proposal_next_action,
        report_path="",
        fail_reason=fail_reason,
    )

    report_path = build_unified_report(result, output_dir)
    result.report_path = str(report_path)
    return result


# ---------------------------------------------------------------------------
# CLI 输出
# ---------------------------------------------------------------------------

def print_unified_summary(
    result: UnifiedTaskProposalResult,
    print_proposal: bool = False,
) -> None:
    """打印统一 CLI 摘要。"""
    print(f"EXTERNAL_REQUEST_TASK_PROPOSAL_RESULT={result.result}")
    print(f"SOURCE_TYPE={result.source_type}")
    print(f"REQUEST_ID={result.request_id}")
    if result.issue_id:
        print(f"ISSUE_ID={result.issue_id}")
    print(f"SAFETY_STATUS={'pass' if result.safety_ok else 'fail'}")
    print(f"PROMPT_INJECTION_RISK={result.prompt_injection_risk}")
    print(f"ALLOWED_TO_PLAN={'yes' if result.allowed_to_plan else 'no'}")
    print("ALLOWED_TO_EXECUTE=no")
    print(f"TASK_PROPOSAL_CREATED={'yes' if result.task_proposal_created else 'no'}")
    print("DOCS_TASKS_MODIFIED=no")
    print("RUNNER_EXECUTED=no")
    print("GIT_ADD_EXECUTED=no")
    print("GIT_COMMIT_EXECUTED=no")
    print("GIT_PUSH_EXECUTED=no")
    print("GITHUB_API_ACCESSED=no")
    print("GH_CLI_CALLED=no")
    print("GITHUB_WORKFLOW_CREATED=no")
    print(f"REPORT_PATH={result.report_path}")
    print(f"CHECK_RESULT={result.result}")

    if result.blocked_reasons:
        print(f"BLOCKED_REASONS={result.blocked_reasons}")
    if result.warnings:
        print(f"WARNINGS={result.warnings}")
    if result.fail_reason:
        print(f"FAIL_REASON={result.fail_reason}")

    if print_proposal and result.task_proposal_created:
        print()
        print(f"PROPOSAL_ID={result.proposal_id}")
        print(f"PROPOSAL_TITLE={result.proposal_title}")
        print(f"PROPOSED_TASKS={result.proposed_tasks}")
        print(f"PROPOSAL_NEXT_ACTION={result.proposal_next_action}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    """CLI dry-run 入口。"""
    import argparse

    parser = argparse.ArgumentParser(
        description="External Request → Task Proposal Dry-run Bridge",
    )
    parser.add_argument(
        "--source-type", required=True,
        choices=["local_inbox", "github_issue"],
        help="Source type: local_inbox or github_issue",
    )
    parser.add_argument(
        "--request-file",
        help="Path to local inbox request file (for local_inbox source)",
    )
    parser.add_argument(
        "--fixture-file",
        help="Path to GitHub Issue fixture file (for github_issue source)",
    )
    parser.add_argument(
        "--output-dir", default="reports/task-proposals",
        help="Output directory for reports (default: reports/task-proposals)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", default=True,
        help="Dry-run mode (always True, Stage 11)",
    )
    parser.add_argument(
        "--print-proposal", action="store_true", default=False,
        help="Print TaskProposal details",
    )

    args = parser.parse_args()

    # 确定输出目录（相对于项目根目录）
    output_dir = _REPO_ROOT / args.output_dir

    # 根据来源类型处理
    if args.source_type == "local_inbox":
        if not args.request_file:
            print("ERROR: --request-file is required for local_inbox source type")
            return 1
        request_file = Path(args.request_file)
        if not request_file.exists():
            print(f"ERROR: Request file not found: {request_file}")
            return 1
        result = process_local_inbox(request_file, output_dir)
    elif args.source_type == "github_issue":
        if not args.fixture_file:
            print("ERROR: --fixture-file is required for github_issue source type")
            return 1
        fixture_file = Path(args.fixture_file)
        if not fixture_file.exists():
            print(f"ERROR: Fixture file not found: {fixture_file}")
            return 1
        result = process_github_issue(fixture_file, output_dir)
    else:
        print(f"ERROR: Unknown source type: {args.source_type}")
        return 1

    # 打印摘要
    print_unified_summary(result, print_proposal=args.print_proposal)

    # 返回退出码
    return 0 if result.result == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
