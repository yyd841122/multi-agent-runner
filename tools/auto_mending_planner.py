"""Auto Mending Planner — verifier 失败后自动生成返工决策和计划（dry-run）。

遵循 docs/stage10-auto-mending-planner-design.md 设计。
只生成决策和计划，不执行返工，不修改文件，不调用模型，不执行 Git。
所有不确定情况 fail closed。

T178 实现。
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime


# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

MAX_REWORK_ROUNDS = 3

# 允许自动返工的 failure_type 列表
AUTO_REWORKABLE_TYPES: list[str] = [
    "report_missing",
    "check_result_failed",
    "tests_failed",
    "syntax_failed",
]

# 始终禁止的操作
FORBIDDEN_OPERATIONS_ALWAYS: list[str] = [
    "modify_runner",
    "modify_tools",
    "git_add",
    "git_commit",
    "git_push",
    "add_dependency",
    "expand_scope",
    "modify_business_code_outside_scope",
]

# failure_type → allowed_operations 映射
FAILURE_TYPE_OPERATIONS: dict[str, list[str]] = {
    "syntax_failed": ["fix_syntax"],
    "tests_failed": ["fix_tests"],
    "report_missing": ["generate_report"],
    "check_result_failed": ["fix_check_result", "regenerate_report"],
    "verifier_failed": ["fix_verifier_issues"],
}

# failure_type → proposed_steps 映射
FAILURE_TYPE_STEPS: dict[str, list[str]] = {
    "syntax_failed": [
        "1. 定位语法错误文件",
        "2. 修复语法",
        "3. py_compile 验证",
    ],
    "tests_failed": [
        "1. 定位失败测试",
        "2. 分析失败原因",
        "3. 修复相关代码",
        "4. 重新运行测试",
    ],
    "report_missing": [
        "1. 确认报告路径",
        "2. 生成缺失报告",
        "3. 验证报告格式",
    ],
    "check_result_failed": [
        "1. 定位 CHECK_RESULT=fail 原因",
        "2. 修复问题",
        "3. 重新生成报告",
    ],
    "verifier_failed": [
        "1. 分析 verifier fail_reason",
        "2. 针对性修复",
        "3. 重新运行 verifier",
    ],
}

# failure_type → verification_steps 映射
FAILURE_TYPE_VERIFICATION: list[str] = [
    "1. 重新运行 continuous_verifier",
    "2. 确认 CHECK_RESULT=pass",
    "3. 确认报告完整",
]


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class FailureClassification:
    """失败分类结果。"""

    failure_type: str
    severity: str           # P0 / P1 / P2 / P3 / P4 / P5
    is_reworkable: bool
    requires_user_approval: bool
    default_next_action: str
    reason: str


@dataclass
class ReworkDecision:
    """返工决策 — 由 auto_mending_planner.py 生成。"""

    # 基础信息
    ok: bool
    task_id: str
    verify_status: str                  # pass / fail
    check_result: str                   # pass / fail

    # 失败分类
    failure_type: str | None
    failure_summary: str | None

    # 返工判断
    rework_allowed: bool
    auto_rework_allowed: bool
    user_approval_required: bool

    # 返工范围
    target_files: list[str]
    forbidden_files: list[str]
    unclassified_files: list[str]
    risk_level: str                     # low / medium / high / critical

    # 返工轮次控制
    current_rework_round: int
    max_rework_rounds: int

    # 结果
    next_action: str
    fail_reason: str | None


@dataclass
class ReworkPlan:
    """返工计划 — 由 auto_mending_planner.py 生成。"""

    # 基础信息
    task_id: str
    plan_id: str                        # Txxx-R{n}-plan
    rework_round: int                   # 1-based

    # 返工范围
    target_files: list[str]
    allowed_operations: list[str]
    forbidden_operations: list[str]

    # 计划内容
    proposed_steps: list[str]
    verification_steps: list[str]
    rollback_notes: list[str]

    # 报告要求
    required_reports: list[str]

    # 决策
    approval_required: bool
    next_action: str


# ---------------------------------------------------------------------------
# 基础工具函数
# ---------------------------------------------------------------------------

def normalize_list(values: list[str] | None) -> list[str]:
    """规范化字符串列表：None → []，去除空字符串和空白。"""
    if not values:
        return []
    return [v.strip() for v in values if v and v.strip()]


def _involves_restricted_files(files: list[str]) -> bool:
    """检查文件列表是否涉及 runner.py 或 tools/ 目录。"""
    for f in files:
        if f == "runner.py" or f.startswith("tools/"):
            return True
    return False


# ---------------------------------------------------------------------------
# failure_type 分类规则（11 种）
# ---------------------------------------------------------------------------

# failure_type → FailureClassification 映射表
_CLASSIFICATION_TABLE: dict[str, FailureClassification] = {
    "rate_limit_or_api_429": FailureClassification(
        failure_type="rate_limit_or_api_429",
        severity="P0",
        is_reworkable=False,
        requires_user_approval=True,
        default_next_action="wait_for_rate_limit_recovery",
        reason="API 429 rate limit 或调用限制，不自动返工",
    ),
    "forbidden_file_changed": FailureClassification(
        failure_type="forbidden_file_changed",
        severity="P1",
        is_reworkable=False,
        requires_user_approval=True,
        default_next_action="stop",
        reason="修改了 forbidden 级别文件，必须人工介入",
    ),
    "unclassified_changes": FailureClassification(
        failure_type="unclassified_changes",
        severity="P1",
        is_reworkable=False,
        requires_user_approval=True,
        default_next_action="stop",
        reason="存在未分类文件变更，必须先人工分类",
    ),
    "max_tasks_violation": FailureClassification(
        failure_type="max_tasks_violation",
        severity="P1",
        is_reworkable=False,
        requires_user_approval=True,
        default_next_action="stop",
        reason="max_tasks != 1，违反受控执行原则",
    ),
    "dirty_workspace": FailureClassification(
        failure_type="dirty_workspace",
        severity="P2",
        is_reworkable=False,
        requires_user_approval=True,
        default_next_action="stop",
        reason="工作区有未分类变更，fail closed",
    ),
    "report_missing": FailureClassification(
        failure_type="report_missing",
        severity="P3",
        is_reworkable=True,
        requires_user_approval=False,
        default_next_action="auto_rework_dry_run",
        reason="报告缺失，可自动返工 dry-run",
    ),
    "syntax_failed": FailureClassification(
        failure_type="syntax_failed",
        severity="P3",
        is_reworkable=True,
        requires_user_approval=False,
        default_next_action="auto_rework_dry_run",
        reason="语法检查失败，可自动返工 dry-run",
    ),
    "tests_failed": FailureClassification(
        failure_type="tests_failed",
        severity="P3",
        is_reworkable=True,
        requires_user_approval=False,
        default_next_action="auto_rework_dry_run",
        reason="测试失败，可自动返工 dry-run",
    ),
    "check_result_failed": FailureClassification(
        failure_type="check_result_failed",
        severity="P4",
        is_reworkable=True,
        requires_user_approval=False,
        default_next_action="auto_rework_dry_run",
        reason="CHECK_RESULT 失败，可自动返工 dry-run",
    ),
    "verifier_failed": FailureClassification(
        failure_type="verifier_failed",
        severity="P4",
        is_reworkable=True,
        requires_user_approval=True,
        default_next_action="manual_rework",
        reason="verifier 失败，需要人工确认后返工",
    ),
    "unknown_failure": FailureClassification(
        failure_type="unknown_failure",
        severity="P5",
        is_reworkable=False,
        requires_user_approval=True,
        default_next_action="stop",
        reason="无法匹配已知失败类型，fail closed",
    ),
}


def classify_failure(failure_type: str) -> FailureClassification:
    """根据 failure_type 返回分类结果。

    如果 failure_type 为空或不在已知列表中，返回 unknown_failure。
    """
    if not failure_type or not failure_type.strip():
        return _CLASSIFICATION_TABLE["unknown_failure"]
    ft = failure_type.strip()
    if ft in _CLASSIFICATION_TABLE:
        return _CLASSIFICATION_TABLE[ft]
    return _CLASSIFICATION_TABLE["unknown_failure"]


# ---------------------------------------------------------------------------
# target_files 验证
# ---------------------------------------------------------------------------

def validate_target_files(
    target_files: list[str],
    forbidden_files: list[str],
    unclassified_files: list[str],
) -> tuple[bool, str]:
    """验证 target_files 是否允许返工。

    返回 (is_valid, reason)。
    """
    if not target_files:
        return False, "target_files 为空，无法确定返工范围"
    for f in target_files:
        if f in forbidden_files:
            return False, f"target_file '{f}' 在 forbidden_files 中"
        if f in unclassified_files:
            return False, f"target_file '{f}' 在 unclassified_files 中"
    return True, ""


# ---------------------------------------------------------------------------
# risk_level 判定
# ---------------------------------------------------------------------------

def _determine_risk_level(
    failure_type: str,
    target_files: list[str],
) -> str:
    """根据 failure_type 和 target_files 判定 risk_level。"""
    # 涉及 runner.py 或 tools/ → critical
    if _involves_restricted_files(target_files):
        return "critical"
    # P1 类型 → high
    if failure_type in ("forbidden_file_changed", "unclassified_changes",
                        "dirty_workspace", "max_tasks_violation"):
        return "high"
    # P4 类型 → medium
    if failure_type in ("verifier_failed", "check_result_failed"):
        return "medium"
    # P3 类型 → low
    if failure_type in ("syntax_failed", "tests_failed", "report_missing"):
        return "low"
    # 默认 → medium
    return "medium"


# ---------------------------------------------------------------------------
# build_rework_decision
# ---------------------------------------------------------------------------

def build_rework_decision(
    task_id: str,
    verify_status: str,
    check_result: str,
    failure_type: str,
    failure_summary: str | None,
    target_files: list[str],
    forbidden_files: list[str],
    unclassified_files: list[str],
    current_rework_round: int,
    max_rework_rounds: int,
    source_report_path: str,
    rework_policy: str,
) -> ReworkDecision:
    """根据输入生成返工决策。

    严格按安全门顺序检查，任何不确定情况 fail closed。
    """
    # --- 规则 1: check_result=pass 且 verify_status=pass → 无需返工 ---
    if check_result == "pass" and verify_status == "pass":
        return ReworkDecision(
            ok=True,
            task_id=task_id,
            verify_status=verify_status,
            check_result=check_result,
            failure_type=None,
            failure_summary=failure_summary,
            rework_allowed=False,
            auto_rework_allowed=False,
            user_approval_required=False,
            target_files=[],
            forbidden_files=normalize_list(forbidden_files),
            unclassified_files=normalize_list(unclassified_files),
            risk_level="low",
            current_rework_round=current_rework_round,
            max_rework_rounds=max_rework_rounds,
            next_action="no_rework_needed",
            fail_reason=None,
        )

    # --- 规则 2: failure_type 为空 → fail closed ---
    if not failure_type or not failure_type.strip():
        return ReworkDecision(
            ok=False,
            task_id=task_id,
            verify_status=verify_status,
            check_result=check_result,
            failure_type=None,
            failure_summary=failure_summary,
            rework_allowed=False,
            auto_rework_allowed=False,
            user_approval_required=True,
            target_files=normalize_list(target_files),
            forbidden_files=normalize_list(forbidden_files),
            unclassified_files=normalize_list(unclassified_files),
            risk_level="high",
            current_rework_round=current_rework_round,
            max_rework_rounds=max_rework_rounds,
            next_action="stop",
            fail_reason="missing_failure_type",
        )

    # 获取分类
    classification = classify_failure(failure_type)
    norm_target = normalize_list(target_files)
    norm_forbidden = normalize_list(forbidden_files)
    norm_unclassified = normalize_list(unclassified_files)

    # --- 规则 3: forbidden_files 非空 → fail closed ---
    if norm_forbidden:
        return ReworkDecision(
            ok=False,
            task_id=task_id,
            verify_status=verify_status,
            check_result=check_result,
            failure_type=classification.failure_type,
            failure_summary=failure_summary,
            rework_allowed=False,
            auto_rework_allowed=False,
            user_approval_required=True,
            target_files=norm_target,
            forbidden_files=norm_forbidden,
            unclassified_files=norm_unclassified,
            risk_level="high",
            current_rework_round=current_rework_round,
            max_rework_rounds=max_rework_rounds,
            next_action="stop",
            fail_reason="forbidden_files_present",
        )

    # --- 规则 4: unclassified_files 非空 → fail closed ---
    if norm_unclassified:
        return ReworkDecision(
            ok=False,
            task_id=task_id,
            verify_status=verify_status,
            check_result=check_result,
            failure_type=classification.failure_type,
            failure_summary=failure_summary,
            rework_allowed=False,
            auto_rework_allowed=False,
            user_approval_required=True,
            target_files=norm_target,
            forbidden_files=norm_forbidden,
            unclassified_files=norm_unclassified,
            risk_level="high",
            current_rework_round=current_rework_round,
            max_rework_rounds=max_rework_rounds,
            next_action="stop",
            fail_reason="unclassified_files_present",
        )

    # --- 规则 5: current_rework_round >= max_rework_rounds → fail closed ---
    if current_rework_round >= max_rework_rounds:
        return ReworkDecision(
            ok=False,
            task_id=task_id,
            verify_status=verify_status,
            check_result=check_result,
            failure_type=classification.failure_type,
            failure_summary=failure_summary,
            rework_allowed=False,
            auto_rework_allowed=False,
            user_approval_required=True,
            target_files=norm_target,
            forbidden_files=norm_forbidden,
            unclassified_files=norm_unclassified,
            risk_level="high",
            current_rework_round=current_rework_round,
            max_rework_rounds=max_rework_rounds,
            next_action="stop",
            fail_reason="max_rework_rounds_exceeded",
        )

    # --- 规则 6: source_report_path 为空 → fail closed ---
    if not source_report_path or not source_report_path.strip():
        return ReworkDecision(
            ok=False,
            task_id=task_id,
            verify_status=verify_status,
            check_result=check_result,
            failure_type=classification.failure_type,
            failure_summary=failure_summary,
            rework_allowed=False,
            auto_rework_allowed=False,
            user_approval_required=True,
            target_files=norm_target,
            forbidden_files=norm_forbidden,
            unclassified_files=norm_unclassified,
            risk_level="medium",
            current_rework_round=current_rework_round,
            max_rework_rounds=max_rework_rounds,
            next_action="stop",
            fail_reason="missing_source_report",
        )

    # --- 规则 7: rate_limit_or_api_429 → 等待恢复 ---
    if classification.failure_type == "rate_limit_or_api_429":
        return ReworkDecision(
            ok=True,
            task_id=task_id,
            verify_status=verify_status,
            check_result=check_result,
            failure_type=classification.failure_type,
            failure_summary=failure_summary,
            rework_allowed=False,
            auto_rework_allowed=False,
            user_approval_required=True,
            target_files=norm_target,
            forbidden_files=norm_forbidden,
            unclassified_files=norm_unclassified,
            risk_level="medium",
            current_rework_round=current_rework_round,
            max_rework_rounds=max_rework_rounds,
            next_action="wait_for_rate_limit_recovery",
            fail_reason=None,
        )

    # --- 规则 8-10: fail-closed 类型（forbidden/unclassified/dirty/max_tasks/unknown）---
    fail_closed_types = {
        "forbidden_file_changed",
        "unclassified_changes",
        "dirty_workspace",
        "max_tasks_violation",
        "unknown_failure",
    }
    if classification.failure_type in fail_closed_types:
        return ReworkDecision(
            ok=False,
            task_id=task_id,
            verify_status=verify_status,
            check_result=check_result,
            failure_type=classification.failure_type,
            failure_summary=failure_summary,
            rework_allowed=False,
            auto_rework_allowed=False,
            user_approval_required=True,
            target_files=norm_target,
            forbidden_files=norm_forbidden,
            unclassified_files=norm_unclassified,
            risk_level=_determine_risk_level(classification.failure_type, norm_target),
            current_rework_round=current_rework_round,
            max_rework_rounds=max_rework_rounds,
            next_action="stop",
            fail_reason=f"failure_type={classification.failure_type} requires manual intervention",
        )

    # --- 规则 11-14: 可返工类型（syntax/tests/report/check_result/verifier）---
    # 检查 target_files 是否为空
    if not norm_target:
        return ReworkDecision(
            ok=False,
            task_id=task_id,
            verify_status=verify_status,
            check_result=check_result,
            failure_type=classification.failure_type,
            failure_summary=failure_summary,
            rework_allowed=False,
            auto_rework_allowed=False,
            user_approval_required=True,
            target_files=norm_target,
            forbidden_files=norm_forbidden,
            unclassified_files=norm_unclassified,
            risk_level=_determine_risk_level(classification.failure_type, norm_target),
            current_rework_round=current_rework_round,
            max_rework_rounds=max_rework_rounds,
            next_action="stop",
            fail_reason="target_files 为空，无法确定返工范围",
        )

    # 判断 risk_level
    risk_level = _determine_risk_level(classification.failure_type, norm_target)

    # 判断是否涉及 runner.py / tools/
    involves_restricted = _involves_restricted_files(norm_target)
    user_approval = involves_restricted or classification.requires_user_approval

    # 判断 auto_rework_allowed（10 个条件全部满足）
    auto_rework = (
        classification.failure_type in AUTO_REWORKABLE_TYPES
        and len(norm_target) > 0
        and not _involves_restricted_files(norm_target)
        and risk_level != "critical"
        and current_rework_round < max_rework_rounds
        and len(norm_forbidden) == 0
        and len(norm_unclassified) == 0
        and source_report_path.strip() != ""
        and rework_policy != "disabled"
    )

    # 判断 next_action
    if auto_rework:
        next_action = "auto_rework_dry_run"
    elif classification.is_reworkable and user_approval:
        next_action = "manual_rework"
    elif classification.is_reworkable:
        next_action = "auto_rework_dry_run"
    else:
        next_action = "stop"

    rework_allowed = classification.is_reworkable and len(norm_target) > 0

    return ReworkDecision(
        ok=True,
        task_id=task_id,
        verify_status=verify_status,
        check_result=check_result,
        failure_type=classification.failure_type,
        failure_summary=failure_summary,
        rework_allowed=rework_allowed,
        auto_rework_allowed=auto_rework,
        user_approval_required=user_approval,
        target_files=norm_target,
        forbidden_files=norm_forbidden,
        unclassified_files=norm_unclassified,
        risk_level=risk_level,
        current_rework_round=current_rework_round,
        max_rework_rounds=max_rework_rounds,
        next_action=next_action,
        fail_reason=None,
    )


# ---------------------------------------------------------------------------
# build_rework_plan_dry_run
# ---------------------------------------------------------------------------

def build_rework_plan_dry_run(decision: ReworkDecision) -> ReworkPlan | None:
    """根据 ReworkDecision 生成 dry-run 返工计划。

    只在 rework_allowed=True 时生成计划。
    """
    if not decision.rework_allowed:
        return None

    failure_type = decision.failure_type or "unknown_failure"
    rework_round = decision.current_rework_round + 1
    plan_id = f"{decision.task_id}-R{rework_round}-plan"

    # 获取 allowed_operations
    allowed_ops = list(FAILURE_TYPE_OPERATIONS.get(failure_type, []))

    # 获取 proposed_steps
    proposed_steps = list(FAILURE_TYPE_STEPS.get(failure_type, []))

    # 如果涉及 runner.py / tools/，添加额外警告步骤
    if _involves_restricted_files(decision.target_files):
        proposed_steps.insert(0, "WARNING: target_files 涉及 runner.py 或 tools/，必须人工确认")

    return ReworkPlan(
        task_id=decision.task_id,
        plan_id=plan_id,
        rework_round=rework_round,
        target_files=list(decision.target_files),
        allowed_operations=allowed_ops,
        forbidden_operations=list(FORBIDDEN_OPERATIONS_ALWAYS),
        proposed_steps=proposed_steps,
        verification_steps=list(FAILURE_TYPE_VERIFICATION),
        rollback_notes=["git checkout -- <target_file>", "恢复到返工前状态"],
        required_reports=[
            f"reports/dev/{decision.task_id}-dev-report.md",
        ],
        approval_required=decision.user_approval_required,
        next_action="execute_dry_run" if not decision.user_approval_required else "wait_for_approval",
    )


# ---------------------------------------------------------------------------
# 输出函数
# ---------------------------------------------------------------------------

def print_decision(decision: ReworkDecision) -> None:
    """打印 ReworkDecision 结构化输出。"""
    print("=== ReworkDecision ===")
    print(f"ok={decision.ok}")
    print(f"task_id={decision.task_id}")
    print(f"verify_status={decision.verify_status}")
    print(f"check_result={decision.check_result}")
    print(f"failure_type={decision.failure_type}")
    print(f"failure_summary={decision.failure_summary}")
    print(f"rework_allowed={decision.rework_allowed}")
    print(f"auto_rework_allowed={decision.auto_rework_allowed}")
    print(f"user_approval_required={decision.user_approval_required}")
    print(f"target_files={decision.target_files}")
    print(f"forbidden_files={decision.forbidden_files}")
    print(f"unclassified_files={decision.unclassified_files}")
    print(f"risk_level={decision.risk_level}")
    print(f"current_rework_round={decision.current_rework_round}")
    print(f"max_rework_rounds={decision.max_rework_rounds}")
    print(f"next_action={decision.next_action}")
    print(f"fail_reason={decision.fail_reason}")
    print()

    # 结构化状态行
    result_str = "pass" if decision.ok else "fail"
    rework_allowed_str = "yes" if decision.rework_allowed else "no"
    auto_rework_str = "yes" if decision.auto_rework_allowed else "no"
    approval_str = "yes" if decision.user_approval_required else "no"

    print(f"AUTO_MENDING_PLANNER_RESULT={result_str}")
    print(f"TASK={decision.task_id}")
    print(f"FAILURE_TYPE={decision.failure_type}")
    print(f"REWORK_ALLOWED={rework_allowed_str}")
    print(f"AUTO_REWORK_ALLOWED={auto_rework_str}")
    print(f"USER_APPROVAL_REQUIRED={approval_str}")
    print(f"NEXT_ACTION={decision.next_action}")
    print(f"FAIL_REASON={decision.fail_reason}")
    print("REAL_REWORK_EXECUTED=no")
    print("GIT_ADD_EXECUTED=no")
    print("GIT_COMMIT_EXECUTED=no")
    print("GIT_PUSH_EXECUTED=no")


def print_plan(plan: ReworkPlan) -> None:
    """打印 ReworkPlan 结构化输出。"""
    print()
    print("=== ReworkPlan ===")
    print(f"task_id={plan.task_id}")
    print(f"plan_id={plan.plan_id}")
    print(f"rework_round={plan.rework_round}")
    print(f"target_files={plan.target_files}")
    print(f"allowed_operations={plan.allowed_operations}")
    print(f"forbidden_operations={plan.forbidden_operations}")
    print(f"proposed_steps={plan.proposed_steps}")
    print(f"verification_steps={plan.verification_steps}")
    print(f"rollback_notes={plan.rollback_notes}")
    print(f"required_reports={plan.required_reports}")
    print(f"approval_required={plan.approval_required}")
    print(f"next_action={plan.next_action}")
    print()

    # 结构化状态行
    print("REWORK_PLAN_CREATED=yes")
    print(f"REWORK_PLAN_NEXT_ACTION={plan.next_action}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    """CLI dry-run 入口。"""
    parser = argparse.ArgumentParser(
        description="Auto Mending Planner — dry-run 返工决策和计划生成",
    )
    parser.add_argument("--task", required=True, help="当前任务编号（如 T178）")
    parser.add_argument("--verify-status", required=True, help="verifier 结果：pass / fail")
    parser.add_argument("--check-result", required=True, help="CHECK_RESULT：pass / fail")
    parser.add_argument("--failure-type", default="", help="失败类型")
    parser.add_argument("--failure-summary", default="", help="失败原因摘要")
    parser.add_argument("--target-file", action="append", default=[], help="目标文件（可重复）")
    parser.add_argument("--forbidden-file", action="append", default=[], help="禁止文件（可重复）")
    parser.add_argument("--unclassified-file", action="append", default=[], help="未分类文件（可重复）")
    parser.add_argument("--current-rework-round", type=int, default=0, help="当前返工轮次")
    parser.add_argument("--max-rework-rounds", type=int, default=MAX_REWORK_ROUNDS, help="最大返工轮次")
    parser.add_argument("--source-report", default="", help="来源报告路径")
    parser.add_argument("--rework-policy", default="auto_dry_run", help="返工策略")
    parser.add_argument("--print-plan", action="store_true", default=False, help="是否输出 ReworkPlan")

    args = parser.parse_args()

    # 生成决策
    decision = build_rework_decision(
        task_id=args.task,
        verify_status=args.verify_status,
        check_result=args.check_result,
        failure_type=args.failure_type,
        failure_summary=args.failure_summary if args.failure_summary else None,
        target_files=args.target_file,
        forbidden_files=args.forbidden_file,
        unclassified_files=args.unclassified_file,
        current_rework_round=args.current_rework_round,
        max_rework_rounds=args.max_rework_rounds,
        source_report_path=args.source_report,
        rework_policy=args.rework_policy,
    )

    # 打印决策
    print_decision(decision)

    # 如果要求打印计划且 rework_allowed
    if args.print_plan:
        plan = build_rework_plan_dry_run(decision)
        if plan:
            print_plan(plan)
        else:
            print()
            print("REWORK_PLAN_CREATED=no")
            print("REWORK_PLAN_NEXT_ACTION=N/A")

    return 0


if __name__ == "__main__":
    sys.exit(main())
