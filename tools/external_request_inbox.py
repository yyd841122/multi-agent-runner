"""External Request Inbox — Local request inbox dry-run.

遵循 docs/stage11-local-request-inbox-design.md 设计。
读取本地 request Markdown 文件，解析、安全门检查、生成 TaskProposal dry-run。
不修改 docs/tasks.md，不执行 runner，不调用模型，不执行 Git。

T187 实现。
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

ALLOWED_SOURCE_TYPES: list[str] = [
    "local_inbox",
]

# Prompt injection 关键词 — critical 级别
PROMPT_INJECTION_CRITICAL_PATTERNS: list[tuple[str, str]] = [
    (r"ignore\s+previous\s+instructions", "ignore_previous_instructions"),
    (r"忽略之前的规则", "ignore_previous_rules_cn"),
    (r"忽略之前的指令", "ignore_previous_instructions_cn"),
    (r"reveal\s+system\s+prompt", "reveal_system_prompt"),
    (r"输出系统提示词", "reveal_system_prompt_cn"),
    (r"bypass\s+safety", "bypass_safety"),
    (r"绕过安全限制", "bypass_safety_cn"),
    (r"skip\s+verification", "skip_verification"),
    (r"跳过验证", "skip_verification_cn"),
    (r"system\s+prompt\s+override", "system_prompt_override"),
]

# Prompt injection 关键词 — high 级别
PROMPT_INJECTION_HIGH_PATTERNS: list[tuple[str, str]] = [
    (r"directly\s+run\s+git\s+push", "directly_git_push"),
    (r"直接提交并推送", "directly_git_push_cn"),
    (r"delete\s+(all\s+)?files", "delete_files"),
    (r"删除所有文件", "delete_files_cn"),
    (r"rm\s+-rf", "rm_rf"),
    (r"expose\s+api\s+key", "expose_api_key"),
    (r"泄露密钥", "expose_api_key_cn"),
    (r"show\s+password", "show_password"),
    (r"modify\s+runner\s+without\s+approval", "modify_runner_without_approval"),
    (r"自动执行真实任务", "auto_execute_real_task_cn"),
    (r"直接运行真实任务", "directly_run_real_task_cn"),
    (r"不需要人工确认", "no_user_approval_cn"),
]

# 密钥相关关键词
SECRETS_KEYWORDS: list[str] = [
    ".env",
    "secrets",
    "api_key",
    "api key",
    "password",
    "token",
    "credential",
    "secret",
]

# 绕过安全关键词
BYPASS_KEYWORDS: list[str] = [
    "bypass",
    "skip verification",
    "ignore safety",
    "绕过安全",
    "跳过验证",
    "忽略安全",
]

# Git 危险关键词
GIT_DANGEROUS_KEYWORDS: list[str] = [
    "git push",
    "git add .",
    "git add -A",
    "git add --all",
    "git commit",
]

# 框架文件关键词
FRAMEWORK_FILE_KEYWORDS: list[str] = [
    "runner.py",
    "tools/",
    "agents/",
]

# 删除文件关键词
DELETE_KEYWORDS: list[str] = [
    "rm ",
    "rm -rf",
    "delete ",
    "remove file",
    "删除",
]

# 网络调用关键词
NETWORK_KEYWORDS: list[str] = [
    "curl ",
    "wget ",
    "http request",
    "fetch(",
    "requests.get",
    "requests.post",
]

# 真实执行关键词
REAL_EXECUTION_KEYWORDS: list[str] = [
    "run-project-loop --real-execution",
    "execute real task",
    "real execution",
    "真实执行",
    "真实任务",
    "真实返工",
    "execute real rework",
    "auto rework without",
]

# 中等风险关键词
MEDIUM_RISK_PATTERNS: list[tuple[str, str]] = [
    (r"&&", "compound_command_and"),
    (r";", "compound_command_semicolon"),
    (r"\|", "pipe_command"),
]


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class ExternalRequest:
    """外部请求数据结构，用于标准化来自不同来源的用户需求。"""

    # 基础标识
    request_id: str
    source_type: str
    source_ref: str
    title: str

    # 内容
    raw_content: str
    normalized_summary: str

    # 请求者信息
    requester: str
    created_at: str

    # 优先级与范围
    priority: str
    requested_stage: str
    requested_files: list[str]

    # 安全评估
    suspected_intent: str
    safety_risk_level: str
    prompt_injection_risk: str

    # 审批状态
    requires_user_approval: bool
    allowed_to_plan: bool
    allowed_to_execute: bool
    fail_reason: str


@dataclass
class ExternalRequestSafetyResult:
    """外部请求安全门检查结果。"""

    ok: bool
    request_id: str
    risk_level: str
    prompt_injection_risk: str
    blocked_reasons: list[str]
    warnings: list[str]
    allowed_to_plan: bool
    allowed_to_execute: bool
    requires_user_approval: bool
    next_action: str


@dataclass
class TaskProposal:
    """外部请求生成的任务提案。"""

    proposal_id: str
    request_id: str
    title: str
    normalized_summary: str
    proposed_tasks: list[str]
    proposed_files: list[str]
    forbidden_files: list[str]
    required_agents: list[str]
    risk_level: str
    requires_user_approval: bool
    allowed_to_write_tasks: bool
    allowed_to_execute: bool
    next_action: str


@dataclass
class RequestInboxRecord:
    """请求收件箱处理记录。"""

    request_path: str
    request_id: str
    parse_status: str
    safety_status: str
    proposal_status: str
    report_path: str
    processed_at: str
    dry_run: bool
    moved_to_processed: bool
    moved_to_rejected: bool
    fail_reason: str


# ---------------------------------------------------------------------------
# 基础工具函数
# ---------------------------------------------------------------------------

def normalize_list(values: list[str] | None) -> list[str]:
    """规范化字符串列表：None -> []，去除空字符串和空白。"""
    if not values:
        return []
    return [v.strip() for v in values if v and v.strip()]


def read_text_file(path: Path) -> str:
    """读取文本文件内容，不存在则返回空字符串。"""
    if path.exists() and path.is_file():
        return path.read_text(encoding="utf-8")
    return ""


# ---------------------------------------------------------------------------
# Markdown 解析
# ---------------------------------------------------------------------------

def parse_markdown_request(path: Path) -> ExternalRequest:
    """解析 Markdown request 文件，构建 ExternalRequest。

    支持可选的 YAML front matter（--- 包裹）。
    缺少字段时使用默认值。
    解析失败时 fail_reason 记录原因。
    """
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    # 读取文件
    raw_text = read_text_file(path)
    if not raw_text or not raw_text.strip():
        return ExternalRequest(
            request_id=f"REQ-{timestamp}",
            source_type="local_inbox",
            source_ref=str(path),
            title="",
            raw_content="",
            normalized_summary="",
            requester="user",
            created_at=timestamp,
            priority="normal",
            requested_stage="auto",
            requested_files=[],
            suspected_intent="unknown",
            safety_risk_level="high",
            prompt_injection_risk="high",
            requires_user_approval=True,
            allowed_to_plan=False,
            allowed_to_execute=False,
            fail_reason="empty_file",
        )

    # 尝试解析 YAML front matter
    metadata: dict[str, str] = {}
    content = raw_text

    front_matter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)", raw_text, re.DOTALL)
    if front_matter_match:
        front_matter_text = front_matter_match.group(1)
        content = front_matter_match.group(2)

        # 简单 YAML 解析（key: value 格式，不引入第三方库）
        for line in front_matter_text.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            colon_idx = line.find(":")
            if colon_idx > 0:
                key = line[:colon_idx].strip()
                value = line[colon_idx + 1:].strip()
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                metadata[key] = value

    # 提取标题
    title = metadata.get("title", "")
    if not title:
        # 从正文第一行提取
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("# "):
                title = line[2:].strip()
                break
            elif line and not line.startswith("#"):
                title = line[:100]
                break

    raw_content = content.strip()

    return ExternalRequest(
        request_id=metadata.get("request_id", f"REQ-{timestamp}"),
        source_type=metadata.get("source_type", "local_inbox"),
        source_ref=metadata.get("source_ref", str(path)),
        title=title,
        raw_content=raw_content,
        normalized_summary="",
        requester=metadata.get("requester", "user"),
        created_at=metadata.get("created_at", timestamp),
        priority=metadata.get("priority", "normal"),
        requested_stage=metadata.get("requested_stage", "auto"),
        requested_files=[],
        suspected_intent="unknown",
        safety_risk_level="high",
        prompt_injection_risk="high",
        requires_user_approval=True,
        allowed_to_plan=False,
        allowed_to_execute=False,
        fail_reason="",
    )


# ---------------------------------------------------------------------------
# Prompt Injection 检测
# ---------------------------------------------------------------------------

def detect_prompt_injection(raw_content: str) -> tuple[str, list[str]]:
    """检测 prompt injection 风险。

    Returns:
        (risk_level, detected_patterns)
        risk_level: none / low / medium / high / critical
    """
    if not raw_content:
        return "none", []

    content_lower = raw_content.lower()
    detected: list[str] = []
    has_critical = False
    has_high = False
    has_medium = False

    # Critical 级别检测
    for pattern, name in PROMPT_INJECTION_CRITICAL_PATTERNS:
        if re.search(pattern, content_lower):
            detected.append(f"critical:{name}")
            has_critical = True

    # 密钥/绕过/直接执行关键词检测 → critical/high
    for kw in SECRETS_KEYWORDS:
        if kw.lower() in content_lower:
            detected.append(f"high:secrets_keyword({kw})")
            has_high = True

    for kw in BYPASS_KEYWORDS:
        if kw.lower() in content_lower:
            detected.append(f"critical:bypass_keyword({kw})")
            has_critical = True

    for kw in GIT_DANGEROUS_KEYWORDS:
        if kw.lower() in content_lower:
            detected.append(f"high:git_dangerous({kw})")
            has_high = True

    for kw in REAL_EXECUTION_KEYWORDS:
        if kw.lower() in content_lower:
            detected.append(f"high:real_execution({kw})")
            has_high = True

    # High 级别检测
    for pattern, name in PROMPT_INJECTION_HIGH_PATTERNS:
        if re.search(pattern, content_lower):
            detected.append(f"high:{name}")
            has_high = True

    # 删除文件关键词
    for kw in DELETE_KEYWORDS:
        if kw.lower() in content_lower:
            detected.append(f"high:delete_keyword({kw})")
            has_high = True

    # Medium 级别检测（复合命令）
    for pattern, name in MEDIUM_RISK_PATTERNS:
        if re.search(pattern, content_lower):
            detected.append(f"medium:{name}")
            has_medium = True

    # 框架文件关键词
    for kw in FRAMEWORK_FILE_KEYWORDS:
        if kw.lower() in content_lower:
            detected.append(f"medium:framework_file({kw})")
            has_medium = True

    # 判定风险等级
    if has_critical:
        return "critical", detected
    if has_high:
        return "high", detected
    if has_medium:
        return "medium", detected

    return "low", detected


# ---------------------------------------------------------------------------
# Safety Gate
# ---------------------------------------------------------------------------

def run_safety_gate(request: ExternalRequest) -> ExternalRequestSafetyResult:
    """执行外部请求安全门检查。

    17 条规则按顺序检查，任何不确定情况 fail closed。
    """
    blocked_reasons: list[str] = []
    warnings: list[str] = []
    requires_user_approval = True
    allowed_to_plan = False
    # allowed_to_execute 永远为 False（Stage 11 强制）
    allowed_to_execute = False

    # 规则 1：空请求 fail closed
    if not request.raw_content or not request.raw_content.strip():
        return ExternalRequestSafetyResult(
            ok=False,
            request_id=request.request_id,
            risk_level="high",
            prompt_injection_risk="high",
            blocked_reasons=["empty_request"],
            warnings=[],
            allowed_to_plan=False,
            allowed_to_execute=False,
            requires_user_approval=True,
            next_action="stop",
        )

    # 规则 2：文件不存在 fail closed（fail_reason 包含 empty_file 时）
    if request.fail_reason == "empty_file":
        return ExternalRequestSafetyResult(
            ok=False,
            request_id=request.request_id,
            risk_level="high",
            prompt_injection_risk="high",
            blocked_reasons=["file_empty_or_not_found"],
            warnings=[],
            allowed_to_plan=False,
            allowed_to_execute=False,
            requires_user_approval=True,
            next_action="stop",
        )

    # 规则 3：解析失败 fail closed
    if request.fail_reason and request.fail_reason not in ("", "empty_file"):
        return ExternalRequestSafetyResult(
            ok=False,
            request_id=request.request_id,
            risk_level="high",
            prompt_injection_risk="high",
            blocked_reasons=[f"parse_failed:{request.fail_reason}"],
            warnings=[],
            allowed_to_plan=False,
            allowed_to_execute=False,
            requires_user_approval=True,
            next_action="stop",
        )

    # 规则 4：来源不明 fail closed
    if request.source_type not in ALLOWED_SOURCE_TYPES:
        blocked_reasons.append(f"unknown_source_type:{request.source_type}")

    # 规则 5-9：内容安全检查
    content_lower = request.raw_content.lower()

    # 规则 5：请求要求泄露密钥 fail closed
    for kw in SECRETS_KEYWORDS:
        if kw.lower() in content_lower and ("read" in content_lower or "读取" in content_lower or "show" in content_lower or "expose" in content_lower or "泄露" in content_lower or "输出" in content_lower):
            blocked_reasons.append(f"secrets_disclosure_requested:{kw}")
            break
    # 直接检测 .env 读取
    if ".env" in content_lower and ("read" in content_lower or "读取" in content_lower or "load" in content_lower):
        blocked_reasons.append("read_env_requested")

    # 规则 6：请求要求读取 .env fail closed（二次检查，确保捕获）
    if ".env" in content_lower and any(w in content_lower for w in ["read", "读取", "load", "open", "cat "]):
        if "read_env_requested" not in str(blocked_reasons):
            blocked_reasons.append("read_env_requested")

    # 规则 7：请求要求绕过系统限制 fail closed
    for kw in BYPASS_KEYWORDS:
        if kw.lower() in content_lower:
            blocked_reasons.append(f"bypass_safety_requested:{kw}")
            break

    # 规则 8：请求要求直接 git add / commit / push fail closed
    for kw in GIT_DANGEROUS_KEYWORDS:
        if kw.lower() in content_lower:
            blocked_reasons.append(f"git_operation_requested:{kw}")

    # 规则 9：请求要求直接执行真实 run-project-loop fail closed
    for kw in REAL_EXECUTION_KEYWORDS:
        if kw.lower() in content_lower:
            blocked_reasons.append(f"real_execution_requested:{kw}")
            break

    # 规则 10：请求要求直接执行真实返工 fail closed
    rework_keywords = ["execute real rework", "auto rework without", "真实返工", "自动返工"]
    for kw in rework_keywords:
        if kw in content_lower:
            blocked_reasons.append(f"real_rework_requested:{kw}")
            break

    # 规则 11：请求要求修改 runner.py / tools/ / agents/ 必须 user approval
    for kw in FRAMEWORK_FILE_KEYWORDS:
        if kw.lower() in content_lower:
            warnings.append(f"framework_file_mentioned:{kw}")
            requires_user_approval = True

    # 规则 12：请求包含删除文件要求必须 user approval
    for kw in DELETE_KEYWORDS:
        if kw.lower() in content_lower:
            warnings.append(f"delete_keyword_detected:{kw}")
            requires_user_approval = True

    # 规则 13：请求包含网络调用要求必须 user approval
    for kw in NETWORK_KEYWORDS:
        if kw.lower() in content_lower:
            warnings.append(f"network_keyword_detected:{kw}")
            requires_user_approval = True

    # 规则 14：Prompt injection 检测
    injection_risk, injection_patterns = detect_prompt_injection(request.raw_content)

    # 更新 injection 风险到 warnings 或 blocked
    if injection_risk == "critical":
        for p in injection_patterns:
            blocked_reasons.append(f"prompt_injection:{p}")
    elif injection_risk == "high":
        for p in injection_patterns:
            blocked_reasons.append(f"prompt_injection:{p}")
    elif injection_risk == "medium":
        for p in injection_patterns:
            warnings.append(f"prompt_injection:{p}")
    elif injection_risk == "low":
        for p in injection_patterns:
            warnings.append(f"prompt_injection:{p}")

    # 规则 15：allowed_to_execute 永远为 False（Stage 11 强制）
    # 已在初始化时设置

    # 规则 16：allowed_to_plan 只有低风险且未被阻断时才可 True
    final_risk = "high"
    if not blocked_reasons:
        if injection_risk in ("none", "low"):
            final_risk = "low"
        elif injection_risk == "medium":
            final_risk = "medium"
        else:
            final_risk = "high"
    else:
        final_risk = "high"

    # 规则 17：所有不确定情况 fail closed
    ok = len(blocked_reasons) == 0
    if ok and final_risk in ("low", "medium"):
        allowed_to_plan = True

    next_action = "stop"
    if blocked_reasons:
        next_action = "stop"
    elif allowed_to_plan:
        next_action = "generate_proposal"
    else:
        next_action = "stop"

    return ExternalRequestSafetyResult(
        ok=ok,
        request_id=request.request_id,
        risk_level=final_risk,
        prompt_injection_risk=injection_risk if injection_risk != "none" else "low",
        blocked_reasons=blocked_reasons,
        warnings=warnings,
        allowed_to_plan=allowed_to_plan,
        allowed_to_execute=allowed_to_execute,
        requires_user_approval=requires_user_approval,
        next_action=next_action,
    )


# ---------------------------------------------------------------------------
# Task Proposal 生成
# ---------------------------------------------------------------------------

def build_task_proposal(
    request: ExternalRequest,
    safety: ExternalRequestSafetyResult,
) -> TaskProposal:
    """根据 ExternalRequest 和 SafetyResult 生成 TaskProposal dry-run。

    只在 safety.allowed_to_plan=True 时生成有效提案。
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    proposal_id = f"PROP-{timestamp}"

    if not safety.allowed_to_plan:
        return TaskProposal(
            proposal_id=proposal_id,
            request_id=request.request_id,
            title="",
            normalized_summary="",
            proposed_tasks=[],
            proposed_files=[],
            forbidden_files=[],
            required_agents=[],
            risk_level=safety.risk_level,
            requires_user_approval=True,
            allowed_to_write_tasks=False,
            allowed_to_execute=False,
            next_action="stop",
        )

    # 简单意图推断
    content_lower = request.raw_content.lower()
    intent = "unknown"
    if any(w in content_lower for w in ["bug", "修复", "fix"]):
        intent = "bug_fix"
    elif any(w in content_lower for w in ["refactor", "重构", "重写"]):
        intent = "refactor"
    elif any(w in content_lower for w in ["test", "测试"]):
        intent = "test"
    elif any(w in content_lower for w in ["doc", "文档", "文档改进", "readme"]):
        intent = "documentation"
    elif any(w in content_lower for w in ["add", "新增", "增加", "create", "新建"]):
        intent = "new_feature"

    # 简单任务拆解
    proposed_tasks: list[str] = []
    proposed_files: list[str] = []

    if intent == "bug_fix":
        proposed_tasks.append(f"分析并修复 {request.title}")
        proposed_tasks.append("验证修复结果")
        proposed_tasks.append("更新相关文档")
    elif intent == "documentation":
        proposed_tasks.append(f"撰写文档：{request.title}")
        proposed_tasks.append("审查文档内容")
    elif intent == "new_feature":
        proposed_tasks.append(f"设计 {request.title} 方案")
        proposed_tasks.append("实现功能代码")
        proposed_tasks.append("编写测试")
        proposed_tasks.append("更新文档")
    elif intent == "test":
        proposed_tasks.append(f"编写测试：{request.title}")
        proposed_tasks.append("运行并验证测试")
    elif intent == "refactor":
        proposed_tasks.append(f"分析重构范围：{request.title}")
        proposed_tasks.append("实施重构")
        proposed_tasks.append("验证重构后功能")
    else:
        proposed_tasks.append(f"分析需求：{request.title}")
        proposed_tasks.append("设计方案")
        proposed_tasks.append("等待人工确认")

    # 判断需要哪些 Agent
    required_agents: list[str] = []
    if intent in ("bug_fix", "new_feature", "refactor"):
        required_agents.extend(["Developer", "Tester"])
    elif intent == "test":
        required_agents.append("Tester")
    elif intent == "documentation":
        required_agents.append("Developer")
    else:
        required_agents.extend(["Planner", "Developer"])

    # 禁止文件
    forbidden_files = [".env", "secrets/", "runner.py", ".git/"]

    # 生成摘要
    summary = request.raw_content[:200] if request.raw_content else ""

    return TaskProposal(
        proposal_id=proposal_id,
        request_id=request.request_id,
        title=request.title,
        normalized_summary=summary,
        proposed_tasks=proposed_tasks,
        proposed_files=proposed_files,
        forbidden_files=forbidden_files,
        required_agents=required_agents,
        risk_level=safety.risk_level,
        requires_user_approval=True,
        allowed_to_write_tasks=False,  # Stage 11 始终 False
        allowed_to_execute=False,      # Stage 11 始终 False
        next_action="wait_for_approval",
    )


# ---------------------------------------------------------------------------
# 报告生成
# ---------------------------------------------------------------------------

def ensure_directory(path: Path) -> None:
    """确保目录存在。"""
    path.mkdir(parents=True, exist_ok=True)


def write_external_request_report(
    request: ExternalRequest,
    safety: ExternalRequestSafetyResult,
    proposal: TaskProposal | None,
    output_dir: Path,
) -> Path:
    """写入 external request 处理报告。

    路径：{output_dir}/{request_id}-report.md
    """
    ensure_directory(output_dir)

    report_path = output_dir / f"{request.request_id}-report.md"

    lines: list[str] = []
    lines.append(f"# {request.request_id} External Request Report")
    lines.append("")
    lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}")
    lines.append(f"阶段：Stage 11 — External Request Inbox Dry-run")
    lines.append("")

    # Section 1: Request Info
    lines.append("## 1. Request Info")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|-------|-------|")
    lines.append(f"| REQUEST_ID | {request.request_id} |")
    lines.append(f"| SOURCE_TYPE | {request.source_type} |")
    lines.append(f"| SOURCE_REF | {request.source_ref} |")
    lines.append(f"| TITLE | {request.title} |")
    lines.append(f"| REQUESTER | {request.requester} |")
    lines.append(f"| CREATED_AT | {request.created_at} |")
    lines.append(f"| PRIORITY | {request.priority} |")
    lines.append("")

    # Section 2: Safety Gate Result
    lines.append("## 2. Safety Gate Result")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|-------|-------|")
    lines.append(f"| SAFETY_STATUS | {'pass' if safety.ok else 'fail'} |")
    lines.append(f"| RISK_LEVEL | {safety.risk_level} |")
    lines.append(f"| PROMPT_INJECTION_RISK | {safety.prompt_injection_risk} |")
    lines.append(f"| ALLOWED_TO_PLAN | {'yes' if safety.allowed_to_plan else 'no'} |")
    lines.append(f"| ALLOWED_TO_EXECUTE | {'yes' if safety.allowed_to_execute else 'no'} |")
    lines.append(f"| REQUIRES_USER_APPROVAL | {'yes' if safety.requires_user_approval else 'no'} |")
    lines.append(f"| NEXT_ACTION | {safety.next_action} |")
    lines.append("")

    if safety.blocked_reasons:
        lines.append("### Blocked Reasons")
        lines.append("")
        for r in safety.blocked_reasons:
            lines.append(f"- `{r}`")
        lines.append("")

    if safety.warnings:
        lines.append("### Warnings")
        lines.append("")
        for w in safety.warnings:
            lines.append(f"- `{w}`")
        lines.append("")

    # Section 3: Task Proposal
    lines.append("## 3. Task Proposal")
    lines.append("")
    if proposal and safety.allowed_to_plan:
        lines.append("| Field | Value |")
        lines.append("|-------|-------|")
        lines.append(f"| PROPOSAL_ID | {proposal.proposal_id} |")
        lines.append(f"| TITLE | {proposal.title} |")
        lines.append(f"| RISK_LEVEL | {proposal.risk_level} |")
        lines.append(f"| ALLOWED_TO_WRITE_TASKS | {'yes' if proposal.allowed_to_write_tasks else 'no'} |")
        lines.append(f"| ALLOWED_TO_EXECUTE | {'yes' if proposal.allowed_to_execute else 'no'} |")
        lines.append("")
        if proposal.proposed_tasks:
            lines.append("### Proposed Tasks")
            lines.append("")
            for i, t in enumerate(proposal.proposed_tasks, 1):
                lines.append(f"{i}. {t}")
            lines.append("")
    else:
        lines.append("No task proposal generated (safety gate blocked or not allowed to plan).")
        lines.append("")

    # Section 4: Safety Guarantees
    lines.append("## 4. Safety Guarantees")
    lines.append("")
    lines.append("- DOCS_TASKS_MODIFIED=no")
    lines.append("- RUNNER_EXECUTED=no")
    lines.append("- GIT_ADD_EXECUTED=no")
    lines.append("- GIT_COMMIT_EXECUTED=no")
    lines.append("- GIT_PUSH_EXECUTED=no")
    lines.append("- REAL_EXECUTION_CHANGED=no")
    lines.append("- DRY_RUN=yes")
    lines.append("")

    # 结构化状态行
    lines.append("---")
    lines.append("")
    lines.append("```")
    lines.append(f"REQUEST_ID={request.request_id}")
    lines.append(f"SOURCE_TYPE={request.source_type}")
    lines.append(f"PARSE_STATUS=pass")
    lines.append(f"SAFETY_STATUS={'pass' if safety.ok else 'fail'}")
    lines.append(f"PROMPT_INJECTION_RISK={safety.prompt_injection_risk}")
    lines.append(f"ALLOWED_TO_PLAN={'yes' if safety.allowed_to_plan else 'no'}")
    lines.append("ALLOWED_TO_EXECUTE=no")
    lines.append(f"TASK_PROPOSAL_CREATED={'yes' if (proposal and safety.allowed_to_plan) else 'no'}")
    lines.append("DOCS_TASKS_MODIFIED=no")
    lines.append("RUNNER_EXECUTED=no")
    lines.append("GIT_ADD_EXECUTED=no")
    lines.append("GIT_COMMIT_EXECUTED=no")
    lines.append("GIT_PUSH_EXECUTED=no")
    check_result = "pass" if safety.ok else "fail"
    lines.append(f"CHECK_RESULT={check_result}")
    lines.append("```")
    lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


# ---------------------------------------------------------------------------
# 输出函数
# ---------------------------------------------------------------------------

def print_summary(
    record: RequestInboxRecord,
    safety: ExternalRequestSafetyResult,
    proposal: TaskProposal | None,
) -> None:
    """打印处理摘要。"""
    result_str = "pass" if safety.ok else "fail"

    print(f"EXTERNAL_REQUEST_INBOX_RESULT={result_str}")
    print(f"REQUEST_ID={record.request_id}")
    print(f"SOURCE_TYPE=local_inbox")
    print(f"PARSE_STATUS={record.parse_status}")
    print(f"SAFETY_STATUS={record.safety_status}")
    print(f"PROMPT_INJECTION_RISK={safety.prompt_injection_risk}")
    print(f"ALLOWED_TO_PLAN={'yes' if safety.allowed_to_plan else 'no'}")
    print("ALLOWED_TO_EXECUTE=no")
    print(f"TASK_PROPOSAL_CREATED={'yes' if (proposal and safety.allowed_to_plan) else 'no'}")
    print("DOCS_TASKS_MODIFIED=no")
    print("RUNNER_EXECUTED=no")
    print("GIT_ADD_EXECUTED=no")
    print("GIT_COMMIT_EXECUTED=no")
    print("GIT_PUSH_EXECUTED=no")
    print(f"REPORT_PATH={record.report_path}")
    print(f"CHECK_RESULT={result_str}")

    if safety.blocked_reasons:
        print(f"BLOCKED_REASONS={safety.blocked_reasons}")
    if safety.warnings:
        print(f"WARNINGS={safety.warnings}")
    if record.fail_reason:
        print(f"FAIL_REASON={record.fail_reason}")

    if proposal and safety.allowed_to_plan:
        print()
        print(f"PROPOSAL_ID={proposal.proposal_id}")
        print(f"PROPOSAL_TITLE={proposal.title}")
        print(f"PROPOSED_TASKS={proposal.proposed_tasks}")
        print(f"REQUIRED_AGENTS={proposal.required_agents}")
        print(f"PROPOSAL_RISK_LEVEL={proposal.risk_level}")
        print(f"PROPOSAL_NEXT_ACTION={proposal.next_action}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    """CLI dry-run 入口。"""
    import argparse

    parser = argparse.ArgumentParser(
        description="External Request Inbox — local request dry-run",
    )
    parser.add_argument(
        "--request-file", required=True,
        help="Path to request Markdown file",
    )
    parser.add_argument(
        "--output-dir", default="reports/external-requests",
        help="Output directory for reports (default: reports/external-requests)",
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

    # 确定路径
    request_path = Path(args.request_file)
    script_path = Path(__file__).resolve()
    repo_root = script_path.parent.parent
    output_dir = repo_root / args.output_dir

    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    # 1. 解析 request
    request = parse_markdown_request(request_path)

    # 2. 初始化 record
    record = RequestInboxRecord(
        request_path=str(request_path),
        request_id=request.request_id,
        parse_status="pass" if request.fail_reason == "" else "fail",
        safety_status="pending",
        proposal_status="pending",
        report_path="",
        processed_at=timestamp,
        dry_run=True,
        moved_to_processed=False,
        moved_to_rejected=False,
        fail_reason="",
    )

    if request.fail_reason:
        record.safety_status = "fail"
        record.proposal_status = "skipped"
        record.fail_reason = request.fail_reason

        # 写报告
        safety = ExternalRequestSafetyResult(
            ok=False,
            request_id=request.request_id,
            risk_level="high",
            prompt_injection_risk="high",
            blocked_reasons=[f"parse_failed:{request.fail_reason}"],
            warnings=[],
            allowed_to_plan=False,
            allowed_to_execute=False,
            requires_user_approval=True,
            next_action="stop",
        )
        report_path = write_external_request_report(request, safety, None, output_dir)
        record.report_path = str(report_path)

        print_summary(record, safety, None)
        return 1

    # 3. 运行 safety gate
    safety = run_safety_gate(request)
    record.safety_status = "pass" if safety.ok else "fail"

    if not safety.ok:
        record.proposal_status = "skipped"
        record.fail_reason = "; ".join(safety.blocked_reasons)

        # 写报告
        report_path = write_external_request_report(request, safety, None, output_dir)
        record.report_path = str(report_path)

        print_summary(record, safety, None)
        return 1

    # 4. 生成 TaskProposal
    proposal: TaskProposal | None = None
    if safety.allowed_to_plan:
        proposal = build_task_proposal(request, safety)
        record.proposal_status = "created"
    else:
        record.proposal_status = "skipped"

    # 5. 写报告
    report_path = write_external_request_report(request, safety, proposal, output_dir)
    record.report_path = str(report_path)

    # 6. 打印摘要
    print_summary(record, safety, proposal if args.print_proposal else None)

    return 0


if __name__ == "__main__":
    sys.exit(main())
