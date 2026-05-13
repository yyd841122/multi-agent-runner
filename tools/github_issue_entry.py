"""GitHub Issue Entry — Local fixture dry-run.

遵循 docs/stage11-github-issue-entry-design.md 设计。
读取本地 GitHub Issue fixture 文件，解析、安全门检查、生成 TaskProposal dry-run。
不修改 docs/tasks.md，不执行 runner，不调用模型，不执行 Git。
不访问 GitHub API，不调用 gh CLI，不创建 workflow。

T190 实现。
"""

from __future__ import annotations

import json
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
    "github_issue",
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

# 敏感 label（即使有也不影响安全判定）
DANGEROUS_LABELS: list[str] = [
    "auto-run",
    "auto-execute",
    "approved",
    "safe",
    "verified",
]

# 允许的 repository 列表（T190 dry-run 阶段允许所有）
ALLOWED_REPOSITORIES: list[str] = [
    "yyd841122/multi-agent-runner",
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
class GitHubIssueRequest:
    """GitHub Issue 请求数据结构，用于标准化来自 GitHub Issue 的外部输入。"""

    # Issue 基础标识
    issue_id: str
    issue_number: str
    repository: str

    # Issue 内容（不可信）
    title: str
    body: str

    # Issue 作者信息（不可信）
    author: str
    author_association: str

    # Issue 元数据（不可信）
    labels: list[str]
    assignees: list[str]
    milestone: str
    state: str

    # 时间
    created_at: str
    updated_at: str

    # Issue 链接
    issue_url: str

    # 数据源信息
    source_mode: str
    raw_payload_path: str

    # Comments
    comments_included: bool
    comments: list[str]

    # 信任评估
    trusted_author: bool
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
# GitHub Issue Fixture 解析（Markdown frontmatter 格式）
# ---------------------------------------------------------------------------

def parse_github_issue_fixture(path: Path) -> GitHubIssueRequest:
    """解析 GitHub Issue fixture 文件（Markdown frontmatter 格式）。

    支持 JSON 和 Markdown frontmatter 两种格式。
    解析失败时 fail_reason 记录原因。
    """
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")

    raw_text = read_text_file(path)
    if not raw_text or not raw_text.strip():
        return GitHubIssueRequest(
            issue_id="", issue_number="", repository="",
            title="", body="",
            author="", author_association="NONE",
            labels=[], assignees=[], milestone="", state="open",
            created_at=timestamp, updated_at=timestamp,
            issue_url="", source_mode="local_fixture",
            raw_payload_path=str(path),
            comments_included=False, comments=[],
            trusted_author=False, fail_reason="empty_file",
        )

    # 尝试 JSON 格式
    if raw_text.strip().startswith("{"):
        try:
            data = json.loads(raw_text)
            return _build_from_json(data, str(path))
        except json.JSONDecodeError:
            pass

    # 尝试 Markdown frontmatter 格式
    metadata: dict[str, str] = {}
    content = raw_text

    front_matter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)", raw_text, re.DOTALL)
    if front_matter_match:
        front_matter_text = front_matter_match.group(1)
        content = front_matter_match.group(2)

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

    # 提取 title
    title = metadata.get("title", "")
    if not title:
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("# "):
                title = line[2:].strip()
                break
            elif line and not line.startswith("#"):
                title = line[:100]
                break

    body = content.strip()

    # 解析 labels（逗号分隔）
    labels_raw = metadata.get("labels", "")
    labels = normalize_list(labels_raw.split(",")) if labels_raw else []

    # 解析 assignees（逗号分隔）
    assignees_raw = metadata.get("assignees", "")
    assignees = normalize_list(assignees_raw.split(",")) if assignees_raw else []

    # author_association 信任映射
    author_association = metadata.get("author_association", "NONE")
    trusted_author = author_association in ("OWNER", "MEMBER", "COLLABORATOR")

    # comments 默认不处理
    comments_included_raw = metadata.get("comments_included", "false")
    comments_included = comments_included_raw.lower() in ("true", "yes", "1")

    return GitHubIssueRequest(
        issue_id=metadata.get("issue_id", f"ISSUE-{timestamp}"),
        issue_number=metadata.get("issue_number", ""),
        repository=metadata.get("repository", ""),
        title=title,
        body=body,
        author=metadata.get("author", ""),
        author_association=author_association,
        labels=labels,
        assignees=assignees,
        milestone=metadata.get("milestone", ""),
        state=metadata.get("state", "open"),
        created_at=metadata.get("created_at", timestamp),
        updated_at=metadata.get("updated_at", timestamp),
        issue_url=metadata.get("issue_url", ""),
        source_mode=metadata.get("source_mode", "local_fixture"),
        raw_payload_path=str(path),
        comments_included=comments_included,
        comments=[],
        trusted_author=trusted_author,
        fail_reason="",
    )


def _build_from_json(data: dict, raw_path: str) -> GitHubIssueRequest:
    """从 JSON 数据构建 GitHubIssueRequest。"""
    author_association = data.get("author_association", "NONE")
    trusted_author = author_association in ("OWNER", "MEMBER", "COLLABORATOR")

    labels_raw = data.get("labels", [])
    labels = []
    if isinstance(labels_raw, list):
        labels = [str(l).strip() for l in labels_raw if l]
    elif isinstance(labels_raw, str):
        labels = normalize_list(labels_raw.split(","))

    assignees_raw = data.get("assignees", [])
    assignees = []
    if isinstance(assignees_raw, list):
        assignees = [str(a).strip() for a in assignees_raw if a]
    elif isinstance(assignees_raw, str):
        assignees = normalize_list(assignees_raw.split(","))

    return GitHubIssueRequest(
        issue_id=str(data.get("issue_id", "")),
        issue_number=str(data.get("issue_number", "")),
        repository=data.get("repository", ""),
        title=data.get("title", ""),
        body=data.get("body", ""),
        author=data.get("author", ""),
        author_association=author_association,
        labels=labels,
        assignees=assignees,
        milestone=data.get("milestone", ""),
        state=data.get("state", "open"),
        created_at=data.get("created_at", ""),
        updated_at=data.get("updated_at", ""),
        issue_url=data.get("issue_url", ""),
        source_mode="local_fixture",
        raw_payload_path=raw_path,
        comments_included=False,
        comments=[],
        trusted_author=trusted_author,
        fail_reason="",
    )


# ---------------------------------------------------------------------------
# GitHub Issue → ExternalRequest 映射
# ---------------------------------------------------------------------------

def github_issue_to_external_request(issue: GitHubIssueRequest) -> ExternalRequest:
    """将 GitHubIssueRequest 转换为 ExternalRequest。

    遵循 docs/stage11-github-issue-entry-design.md Section 6 映射规则。
    """
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")

    # request_id: GH-ISSUE-{repo}-{number}
    repo_slug = issue.repository.replace("/", "-") if issue.repository else "unknown"
    issue_num = issue.issue_number if issue.issue_number else "0"
    request_id = f"GH-ISSUE-{repo_slug}-{issue_num}"

    # raw_content: title + body
    raw_parts: list[str] = []
    if issue.title:
        raw_parts.append(issue.title)
    if issue.body:
        raw_parts.append(issue.body)
    raw_content = "\n\n".join(raw_parts)

    # priority 由 labels 推断
    priority = "normal"
    labels_lower = [l.lower() for l in issue.labels]
    if any(l in labels_lower for l in ["priority: critical", "priority:urgent", "urgent", "critical"]):
        priority = "critical"
    elif any(l in labels_lower for l in ["priority: high", "priority:high"]):
        priority = "high"
    elif any(l in labels_lower for l in ["priority: low", "priority:low"]):
        priority = "low"

    # suspected_intent 由 labels 和 title/body 推断
    content_lower = raw_content.lower()
    suspected_intent = "unknown"
    if any(l in labels_lower for l in ["bug"]) or any(w in content_lower for w in ["bug", "修复", "fix"]):
        suspected_intent = "bug_fix"
    elif any(l in labels_lower for l in ["enhancement"]) or any(w in content_lower for w in ["新增", "增加", "add"]):
        suspected_intent = "new_feature"
    elif any(l in labels_lower for l in ["refactor"]) or any(w in content_lower for w in ["重构", "refactor"]):
        suspected_intent = "refactor"
    elif any(l in labels_lower for l in ["documentation"]) or any(w in content_lower for w in ["文档", "doc"]):
        suspected_intent = "documentation"
    elif any(l in labels_lower for l in ["test"]) or any(w in content_lower for w in ["测试", "test"]):
        suspected_intent = "test"
    elif any(l in labels_lower for l in ["security", "vulnerability"]):
        suspected_intent = "suspicious"

    return ExternalRequest(
        request_id=request_id,
        source_type="github_issue",
        source_ref=issue.issue_url or issue.raw_payload_path,
        title=issue.title,
        raw_content=raw_content,
        normalized_summary="",
        requester=issue.author,
        created_at=issue.created_at,
        priority=priority,
        requested_stage="auto",
        requested_files=[],
        suspected_intent=suspected_intent,
        safety_risk_level="high",
        prompt_injection_risk="high",
        requires_user_approval=True,
        allowed_to_plan=False,
        allowed_to_execute=False,
        fail_reason="",
    )


# ---------------------------------------------------------------------------
# GitHub Issue 专用预检查
# ---------------------------------------------------------------------------

def validate_github_issue(issue: GitHubIssueRequest) -> list[str]:
    """GitHub Issue 专用预检查规则。

    在通用 safety gate 之前执行。
    返回 blocked_reasons 列表，空表示通过。
    """
    blocked: list[str] = []

    # 规则 1：空 issue（title 和 body 都为空）
    if not issue.title.strip() and not issue.body.strip():
        blocked.append("empty_issue")

    # 规则 2：缺失 issue_number
    if not issue.issue_number.strip():
        blocked.append("missing_issue_number")

    # 规则 3：缺失 repository
    if not issue.repository.strip():
        blocked.append("missing_repository")

    # 规则 4：未知 repository（可选检查，dry-run 阶段允许非白名单仓库但警告）
    # T190 阶段不强制 repository 白名单

    # 规则 5：closed issue 不处理
    if issue.state.lower() == "closed":
        blocked.append("issue_closed")

    # 规则 6：敏感 label 检测（warning，不阻断）
    # 敏感 label 在 warnings 中记录，不在 blocked 中

    return blocked


# ---------------------------------------------------------------------------
# Prompt Injection 检测（对齐 external_request_inbox.py）
# ---------------------------------------------------------------------------

def detect_prompt_injection(raw_content: str) -> tuple[str, list[str]]:
    """检测 prompt injection 风险。

    对齐 tools/external_request_inbox.py 中的 detect_prompt_injection 逻辑。
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

    # 密钥/绕过/直接执行关键词检测
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

    if has_critical:
        return "critical", detected
    if has_high:
        return "high", detected
    if has_medium:
        return "medium", detected

    return "low", detected


# ---------------------------------------------------------------------------
# Safety Gate（对齐 external_request_inbox.py，增加 GitHub Issue 专用规则）
# ---------------------------------------------------------------------------

def run_safety_gate(request: ExternalRequest) -> ExternalRequestSafetyResult:
    """执行外部请求安全门检查。

    对齐 tools/external_request_inbox.py 的 run_safety_gate 逻辑。
    17 条通用规则 + GitHub Issue 专用扩展。
    allowed_to_execute 永远为 False（Stage 11 强制）。
    """
    blocked_reasons: list[str] = []
    warnings: list[str] = []
    requires_user_approval = True
    allowed_to_plan = False
    allowed_to_execute = False  # Stage 11 始终 False

    # 规则 1：空请求 fail closed
    if not request.raw_content or not request.raw_content.strip():
        return ExternalRequestSafetyResult(
            ok=False, request_id=request.request_id,
            risk_level="high", prompt_injection_risk="high",
            blocked_reasons=["empty_request"], warnings=[],
            allowed_to_plan=False, allowed_to_execute=False,
            requires_user_approval=True, next_action="stop",
        )

    # 规则 2：文件不存在 fail closed
    if request.fail_reason == "empty_file":
        return ExternalRequestSafetyResult(
            ok=False, request_id=request.request_id,
            risk_level="high", prompt_injection_risk="high",
            blocked_reasons=["file_empty_or_not_found"], warnings=[],
            allowed_to_plan=False, allowed_to_execute=False,
            requires_user_approval=True, next_action="stop",
        )

    # 规则 3：解析失败 fail closed
    if request.fail_reason and request.fail_reason not in ("", "empty_file"):
        return ExternalRequestSafetyResult(
            ok=False, request_id=request.request_id,
            risk_level="high", prompt_injection_risk="high",
            blocked_reasons=[f"parse_failed:{request.fail_reason}"],
            warnings=[], allowed_to_plan=False, allowed_to_execute=False,
            requires_user_approval=True, next_action="stop",
        )

    # 规则 4：来源不明 fail closed
    if request.source_type not in ALLOWED_SOURCE_TYPES:
        blocked_reasons.append(f"unknown_source_type:{request.source_type}")

    # 规则 5-9：内容安全检查
    content_lower = request.raw_content.lower()

    # 规则 5：请求要求泄露密钥 fail closed
    for kw in SECRETS_KEYWORDS:
        if kw.lower() in content_lower and (
            "read" in content_lower or "读取" in content_lower
            or "show" in content_lower or "expose" in content_lower
            or "泄露" in content_lower or "输出" in content_lower
        ):
            blocked_reasons.append(f"secrets_disclosure_requested:{kw}")
            break

    # 直接检测 .env 读取
    if ".env" in content_lower and (
        "read" in content_lower or "读取" in content_lower or "load" in content_lower
    ):
        if "read_env_requested" not in str(blocked_reasons):
            blocked_reasons.append("read_env_requested")

    # 规则 6：请求要求读取 .env fail closed（二次检查）
    if ".env" in content_lower and any(
        w in content_lower for w in ["read", "读取", "load", "open", "cat "]
    ):
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

    # 规则 15：allowed_to_execute 永远为 False
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
    """根据 ExternalRequest 和 SafetyResult 生成 TaskProposal dry-run。"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    proposal_id = f"PROP-{timestamp}"

    if not safety.allowed_to_plan:
        return TaskProposal(
            proposal_id=proposal_id, request_id=request.request_id,
            title="", normalized_summary="",
            proposed_tasks=[], proposed_files=[], forbidden_files=[],
            required_agents=[], risk_level=safety.risk_level,
            requires_user_approval=True,
            allowed_to_write_tasks=False, allowed_to_execute=False,
            next_action="stop",
        )

    # 意图推断
    content_lower = request.raw_content.lower()
    intent = "unknown"
    if any(w in content_lower for w in ["bug", "修复", "fix"]):
        intent = "bug_fix"
    elif any(w in content_lower for w in ["refactor", "重构", "重写"]):
        intent = "refactor"
    elif any(w in content_lower for w in ["test", "测试"]):
        intent = "test"
    elif any(w in content_lower for w in ["doc", "文档", "readme"]):
        intent = "documentation"
    elif any(w in content_lower for w in ["add", "新增", "增加", "create", "新建"]):
        intent = "new_feature"

    # 任务拆解
    proposed_tasks: list[str] = []
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

    # Agent 规划
    required_agents: list[str] = []
    if intent in ("bug_fix", "new_feature", "refactor"):
        required_agents.extend(["Developer", "Tester"])
    elif intent == "test":
        required_agents.append("Tester")
    elif intent == "documentation":
        required_agents.append("Developer")
    else:
        required_agents.extend(["Planner", "Developer"])

    forbidden_files = [".env", "secrets/", "runner.py", ".git/"]
    summary = request.raw_content[:200] if request.raw_content else ""

    return TaskProposal(
        proposal_id=proposal_id, request_id=request.request_id,
        title=request.title, normalized_summary=summary,
        proposed_tasks=proposed_tasks, proposed_files=[],
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


def build_github_issue_report(
    issue: GitHubIssueRequest,
    external_request: ExternalRequest,
    safety: ExternalRequestSafetyResult,
    proposal: TaskProposal | None,
    output_dir: Path,
) -> Path:
    """写入 GitHub Issue 处理报告。"""
    ensure_directory(output_dir)

    # 报告文件名
    repo_slug = issue.repository.replace("/", "-") if issue.repository else "unknown"
    num = issue.issue_number if issue.issue_number else "0"
    report_filename = f"GH-ISSUE-{repo_slug}-{num}-report.md"
    report_path = output_dir / report_filename

    lines: list[str] = []
    lines.append(f"# GH-ISSUE-{repo_slug}-{num} GitHub Issue Report")
    lines.append("")
    lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}")
    lines.append("阶段：Stage 11 — GitHub Issue Entry Dry-run")
    lines.append("")

    # Section 1: Issue Info
    lines.append("## 1. Issue Info")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|-------|-------|")
    lines.append(f"| ISSUE_ID | {issue.issue_id} |")
    lines.append(f"| ISSUE_NUMBER | {issue.issue_number} |")
    lines.append(f"| REPOSITORY | {issue.repository} |")
    lines.append(f"| TITLE | {issue.title} |")
    lines.append(f"| AUTHOR | {issue.author} |")
    lines.append(f"| AUTHOR_ASSOCIATION | {issue.author_association} |")
    lines.append(f"| TRUSTED_AUTHOR | {'yes' if issue.trusted_author else 'no'} |")
    lines.append(f"| LABELS | {', '.join(issue.labels) if issue.labels else '(none)'} |")
    lines.append(f"| STATE | {issue.state} |")
    lines.append(f"| ISSUE_URL | {issue.issue_url} |")
    lines.append(f"| SOURCE_MODE | {issue.source_mode} |")
    lines.append(f"| SOURCE_TYPE | github_issue |")
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
    lines.append("- GITHUB_API_ACCESSED=no")
    lines.append("- GITHUB_WORKFLOW_CREATED=no")
    lines.append("- DRY_RUN=yes")
    lines.append("")

    # Section 5: Author Trust
    lines.append("## 5. Author Trust")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|-------|-------|")
    lines.append(f"| AUTHOR | {issue.author} |")
    lines.append(f"| AUTHOR_ASSOCIATION | {issue.author_association} |")
    lines.append(f"| TRUSTED_AUTHOR | {'yes' if issue.trusted_author else 'no'} |")
    lines.append("")

    # Section 6: Labels Audit
    lines.append("## 6. Labels Audit")
    lines.append("")
    if issue.labels:
        lines.append("| Label | Processing |")
        lines.append("|-------|------------|")
        for lbl in issue.labels:
            lbl_lower = lbl.lower()
            if lbl_lower in DANGEROUS_LABELS:
                lines.append(f"| {lbl} | ignored + warning (dangerous label) |")
            elif lbl_lower in ("security", "vulnerability"):
                lines.append(f"| {lbl} | audit level elevated |")
            else:
                lines.append(f"| {lbl} | hint only |")
        lines.append("")
    else:
        lines.append("(no labels)")
        lines.append("")

    # 结构化状态行
    lines.append("---")
    lines.append("")
    lines.append("```")
    lines.append(f"ISSUE_ID={issue.issue_id}")
    lines.append(f"ISSUE_NUMBER={issue.issue_number}")
    lines.append(f"REPOSITORY={issue.repository}")
    lines.append("SOURCE_TYPE=github_issue")
    lines.append(f"SOURCE_MODE={issue.source_mode}")
    lines.append(f"PARSE_STATUS={'pass' if not external_request.fail_reason else 'fail'}")
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
    lines.append("GITHUB_API_ACCESSED=no")
    lines.append("GITHUB_WORKFLOW_CREATED=no")
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
    issue: GitHubIssueRequest,
    safety: ExternalRequestSafetyResult,
    proposal: TaskProposal | None,
    report_path: str,
) -> None:
    """打印处理摘要。"""
    result_str = "pass" if safety.ok else "fail"

    print(f"GITHUB_ISSUE_ENTRY_RESULT={result_str}")
    print(f"ISSUE_ID={issue.issue_id}")
    print(f"ISSUE_NUMBER={issue.issue_number}")
    print(f"REPOSITORY={issue.repository}")
    print("SOURCE_TYPE=github_issue")
    print(f"SOURCE_MODE={issue.source_mode}")
    print(f"PARSE_STATUS={'pass' if not issue.fail_reason else 'fail'}")
    print(f"SAFETY_STATUS={result_str}")
    print(f"PROMPT_INJECTION_RISK={safety.prompt_injection_risk}")
    print(f"ALLOWED_TO_PLAN={'yes' if safety.allowed_to_plan else 'no'}")
    print("ALLOWED_TO_EXECUTE=no")
    print(f"TASK_PROPOSAL_CREATED={'yes' if (proposal and safety.allowed_to_plan) else 'no'}")
    print("DOCS_TASKS_MODIFIED=no")
    print("RUNNER_EXECUTED=no")
    print("GIT_ADD_EXECUTED=no")
    print("GIT_COMMIT_EXECUTED=no")
    print("GIT_PUSH_EXECUTED=no")
    print("GITHUB_API_ACCESSED=no")
    print("GITHUB_WORKFLOW_CREATED=no")
    print(f"REPORT_PATH={report_path}")
    print(f"CHECK_RESULT={result_str}")

    if safety.blocked_reasons:
        print(f"BLOCKED_REASONS={safety.blocked_reasons}")
    if safety.warnings:
        print(f"WARNINGS={safety.warnings}")
    if issue.fail_reason:
        print(f"FAIL_REASON={issue.fail_reason}")

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
        description="GitHub Issue Entry — local fixture dry-run",
    )
    parser.add_argument(
        "--fixture-file", required=True,
        help="Path to GitHub Issue fixture file (JSON or Markdown)",
    )
    parser.add_argument(
        "--output-dir", default="reports/github-issues",
        help="Output directory for reports (default: reports/github-issues)",
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

    fixture_path = Path(args.fixture_file)
    script_path = Path(__file__).resolve()
    repo_root = script_path.parent.parent
    output_dir = repo_root / args.output_dir

    # 1. 解析 GitHub Issue fixture
    issue = parse_github_issue_fixture(fixture_path)

    # 2. GitHub Issue 专用预检查
    issue_blocked = validate_github_issue(issue)
    if issue_blocked:
        # 预检查失败，直接 fail closed
        safety = ExternalRequestSafetyResult(
            ok=False,
            request_id=f"GH-ISSUE-{issue.repository.replace('/', '-') if issue.repository else 'unknown'}-{issue.issue_number or '0'}",
            risk_level="high",
            prompt_injection_risk="high",
            blocked_reasons=issue_blocked,
            warnings=[],
            allowed_to_plan=False,
            allowed_to_execute=False,
            requires_user_approval=True,
            next_action="stop",
        )
        external_request = ExternalRequest(
            request_id=safety.request_id,
            source_type="github_issue",
            source_ref=str(fixture_path),
            title=issue.title,
            raw_content="",
            normalized_summary="",
            requester=issue.author,
            created_at=issue.created_at,
            priority="normal",
            requested_stage="auto",
            requested_files=[],
            suspected_intent="unknown",
            safety_risk_level="high",
            prompt_injection_risk="high",
            requires_user_approval=True,
            allowed_to_plan=False,
            allowed_to_execute=False,
            fail_reason="; ".join(issue_blocked),
        )
        report_path = build_github_issue_report(issue, external_request, safety, None, output_dir)
        print_summary(issue, safety, None, str(report_path))
        return 1

    # 3. 映射到 ExternalRequest
    external_request = github_issue_to_external_request(issue)

    # 4. 运行 safety gate
    safety = run_safety_gate(external_request)

    if not safety.ok:
        report_path = build_github_issue_report(
            issue, external_request, safety, None, output_dir,
        )
        print_summary(issue, safety, None, str(report_path))
        return 1

    # 5. 生成 TaskProposal
    proposal: TaskProposal | None = None
    if safety.allowed_to_plan:
        proposal = build_task_proposal(external_request, safety)

    # 6. 写报告
    report_path = build_github_issue_report(
        issue, external_request, safety, proposal, output_dir,
    )

    # 7. 打印摘要
    print_summary(issue, safety, proposal if args.print_proposal else None, str(report_path))

    return 0


if __name__ == "__main__":
    sys.exit(main())
