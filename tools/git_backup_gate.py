"""Git Backup Gate — Continuous verifier pass 后的 Git 备份决策 gate。

遵循 docs/stage9-git-backup-gate-design.md 设计。
只读不写（dry-run），不执行 git add/commit/push，不写入 backup record。
失败时 fail closed。

T168 dry-run 实现。
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# 常量：默认 forbidden 规则
# ---------------------------------------------------------------------------

DEFAULT_FORBIDDEN_PATTERNS: list[str] = [
    ".git/",
    ".env",
    ".env.local",
    ".env.production",
    "secrets",
    "secret",
    "api_key",
    ".github/",
    "requirements.txt",
    "package.json",
    "pyproject.toml",
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    "id_rsa",
    "id_ed25519",
    "token",
    "credential",
    "password",
    ".pyc",
    ".pyo",
    ".so",
    ".dll",
    ".exe",
]

# 默认 forbidden 路径（精确匹配或前缀匹配）
DEFAULT_FORBIDDEN_EXACT: list[str] = [
    "runner.py",
]


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class GitBackupGateResult:
    """GitBackupGate 输出结果。"""

    # 基本信息
    project_root: str
    gate_timestamp: str
    task_id: str

    # 检查结果
    check_result_pass: bool
    continuous_report_exists: bool
    worktree_status: str  # clean / dirty

    # 文件分类
    changed_files: list[str]
    allowed_files: list[str]
    forbidden_files: list[str]
    unclassified_files: list[str]

    # 决策
    ok: bool
    commit_allowed: bool
    push_allowed: bool
    approval_required: bool

    # Commit 信息
    commit_message: str
    git_add_commands: list[str]

    # 备份记录
    backup_record_path: str

    # 失败
    fail_reason: str | None
    next_action: str  # proceed_to_commit / no_changes / stop

    # 安全保证
    gate_modified_files: bool = False  # 始终 False，gate 只读不写


# ---------------------------------------------------------------------------
# 基础工具函数
# ---------------------------------------------------------------------------

def read_text_file(path: Path) -> str:
    """读取文本文件内容，不存在则返回空字符串。"""
    if path.exists() and path.is_file():
        return path.read_text(encoding="utf-8")
    return ""


def get_git_changed_files(repo_root: Path) -> list[str]:
    """通过 git status --short 获取变更文件列表。

    只允许调用 git status，不允许调用 git add/commit/push。
    """
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=30,
        )
        lines = result.stdout.strip().splitlines()
        files: list[str] = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # git status --short 格式：XY filename
            parts = line.split(None, 1)
            if len(parts) >= 2:
                files.append(parts[1])
            elif len(parts) == 1 and parts[0]:
                files.append(parts[0])
        return files
    except Exception:
        # fail-closed: 无法获取时返回特殊标记
        return ["<git_status_failed>"]


def normalize_paths(paths: list[str]) -> list[str]:
    """规范化路径列表：去空白、去重、统一分隔符。"""
    seen: set[str] = set()
    result: list[str] = []
    for p in paths:
        p = p.strip().replace("\\", "/")
        if p and p not in seen:
            seen.add(p)
            result.append(p)
    return result


# ---------------------------------------------------------------------------
# 文件分类函数
# ---------------------------------------------------------------------------

def _is_default_forbidden(filepath: str) -> bool:
    """判断文件是否命中默认 forbidden 规则。"""
    normalized = filepath.replace("\\", "/")

    # 精确匹配
    for exact in DEFAULT_FORBIDDEN_EXACT:
        if normalized == exact:
            return True

    # 模式匹配（子串或前缀）
    for pattern in DEFAULT_FORBIDDEN_PATTERNS:
        if pattern.endswith("/"):
            # 前缀匹配（目录）
            if normalized.startswith(pattern) or "/" + pattern in normalized or normalized == pattern.rstrip("/"):
                return True
        elif pattern.startswith("."):
            # 后缀或子串匹配（扩展名或隐藏文件）
            if normalized.endswith(pattern) or "/" + pattern in normalized or normalized == pattern:
                return True
        else:
            # 子串匹配
            if pattern in normalized:
                return True

    return False


def classify_changed_files(
    changed_files: list[str],
    explicitly_allowed_paths: list[str],
    explicitly_forbidden_paths: list[str],
) -> tuple[list[str], list[str], list[str]]:
    """分类变更文件为 allowed / forbidden / unclassified。

    规则：
    1. 如果文件在 explicitly_allowed_paths 中，进入 allowed。
    2. 如果文件在 explicitly_forbidden_paths 中，进入 forbidden。
    3. 如果文件命中默认 forbidden 规则，进入 forbidden。
    4. 其他文件进入 unclassified。

    Returns:
        (allowed_files, forbidden_files, unclassified_files)
    """
    allowed_set = set(normalize_paths(explicitly_allowed_paths))
    forbidden_set = set(normalize_paths(explicitly_forbidden_paths))

    allowed: list[str] = []
    forbidden: list[str] = []
    unclassified: list[str] = []

    for f in changed_files:
        normalized = f.replace("\\", "/")

        # 先检查 explicitly_allowed（最高优先级）
        if normalized in allowed_set:
            allowed.append(normalized)
            continue

        # 再检查 explicitly_forbidden
        if normalized in forbidden_set:
            forbidden.append(normalized)
            continue

        # 检查默认 forbidden 规则
        if _is_default_forbidden(normalized):
            forbidden.append(normalized)
            continue

        # 未分类
        unclassified.append(normalized)

    return allowed, forbidden, unclassified


# ---------------------------------------------------------------------------
# git add 命令生成
# ---------------------------------------------------------------------------

def build_git_add_commands(allowed_files: list[str]) -> list[str]:
    """为每个 allowed file 生成独立的 git add 命令。

    禁止生成 git add .、git add -A、git add --all。
    """
    commands: list[str] = []
    for f in allowed_files:
        commands.append(f"git add {f}")
    return commands


# ---------------------------------------------------------------------------
# commit message 校验
# ---------------------------------------------------------------------------

UNSAFE_PATTERNS: list[str] = [
    "real_execution_completed",
    "auto_continue",
    "auto_push_completed",
    "auto_commit_completed",
    "unlimited_execution",
    "real_continuous_execution",
]


def validate_commit_message(message: str) -> bool:
    """校验 commit message 是否有效。

    无效条件：
    - 空消息
    - 包含 unsafe pattern
    - 包含 secret/key/password 相关内容
    """
    if not message or not message.strip():
        return False

    lower = message.lower()
    for pattern in UNSAFE_PATTERNS:
        if pattern in lower:
            return False

    # 禁止包含敏感关键词
    sensitive_keywords = ["secret", "password", "api_key", "credential", "token="]
    for kw in sensitive_keywords:
        if kw in lower:
            return False

    return True


# ---------------------------------------------------------------------------
# 核心函数
# ---------------------------------------------------------------------------

def run_git_backup_gate_dry_run(
    repo_root: Path,
    task_id: str,
    check_result: str,
    continuous_run_report_path: str,
    explicitly_allowed_paths: list[str],
    explicitly_forbidden_paths: list[str],
    commit_message: str,
    approval_mode: str,
) -> GitBackupGateResult:
    """执行 GitBackupGate dry-run。

    只读不写，不执行 git add/commit/push。
    所有失败场景必须 fail closed。
    """
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    project_root = str(repo_root)

    # ---- 基础默认值 ----
    ok = False
    commit_allowed = False
    push_allowed = False
    fail_reason: str | None = None
    next_action = "stop"
    changed_files: list[str] = []
    allowed_files: list[str] = []
    forbidden_files: list[str] = []
    unclassified_files: list[str] = []
    git_add_commands: list[str] = []

    # ---- 检查 CHECK_RESULT ----
    check_result_pass = check_result.strip().lower() == "pass"
    if not check_result_pass:
        return GitBackupGateResult(
            project_root=project_root,
            gate_timestamp=timestamp,
            task_id=task_id,
            check_result_pass=False,
            continuous_report_exists=False,
            worktree_status="unknown",
            changed_files=[],
            allowed_files=[],
            forbidden_files=[],
            unclassified_files=[],
            ok=False,
            commit_allowed=False,
            push_allowed=False,
            approval_required=True,
            commit_message=commit_message,
            git_add_commands=[],
            backup_record_path=f"reports/git/{task_id}-git-backup-record.md",
            fail_reason="check_result_not_pass",
            next_action="stop",
        )

    # ---- 检查 continuous run report 是否存在 ----
    report_path = repo_root / continuous_run_report_path
    continuous_report_exists = report_path.exists() and report_path.is_file()
    if not continuous_report_exists:
        return GitBackupGateResult(
            project_root=project_root,
            gate_timestamp=timestamp,
            task_id=task_id,
            check_result_pass=True,
            continuous_report_exists=False,
            worktree_status="unknown",
            changed_files=[],
            allowed_files=[],
            forbidden_files=[],
            unclassified_files=[],
            ok=False,
            commit_allowed=False,
            push_allowed=False,
            approval_required=True,
            commit_message=commit_message,
            git_add_commands=[],
            backup_record_path=f"reports/git/{task_id}-git-backup-record.md",
            fail_reason="continuous_report_missing",
            next_action="stop",
        )

    # ---- 检查 git status ----
    worktree_status = "dirty"
    changed_files = get_git_changed_files(repo_root)

    if changed_files and changed_files == ["<git_status_failed>"]:
        return GitBackupGateResult(
            project_root=project_root,
            gate_timestamp=timestamp,
            task_id=task_id,
            check_result_pass=True,
            continuous_report_exists=True,
            worktree_status="unknown",
            changed_files=[],
            allowed_files=[],
            forbidden_files=[],
            unclassified_files=[],
            ok=False,
            commit_allowed=False,
            push_allowed=False,
            approval_required=True,
            commit_message=commit_message,
            git_add_commands=[],
            backup_record_path=f"reports/git/{task_id}-git-backup-record.md",
            fail_reason="git_status_failed",
            next_action="stop",
        )

    worktree_status = "dirty" if changed_files else "clean"

    # ---- changed_files 为空 ----
    if not changed_files:
        return GitBackupGateResult(
            project_root=project_root,
            gate_timestamp=timestamp,
            task_id=task_id,
            check_result_pass=True,
            continuous_report_exists=True,
            worktree_status="clean",
            changed_files=[],
            allowed_files=[],
            forbidden_files=[],
            unclassified_files=[],
            ok=False,
            commit_allowed=False,
            push_allowed=False,
            approval_required=True,
            commit_message=commit_message,
            git_add_commands=[],
            backup_record_path=f"reports/git/{task_id}-git-backup-record.md",
            fail_reason=None,
            next_action="no_changes",
        )

    # ---- 分类文件 ----
    allowed_files, forbidden_files, unclassified_files = classify_changed_files(
        changed_files, explicitly_allowed_paths, explicitly_forbidden_paths
    )

    # ---- forbidden files 检查 ----
    if forbidden_files:
        return GitBackupGateResult(
            project_root=project_root,
            gate_timestamp=timestamp,
            task_id=task_id,
            check_result_pass=True,
            continuous_report_exists=True,
            worktree_status=worktree_status,
            changed_files=changed_files,
            allowed_files=allowed_files,
            forbidden_files=forbidden_files,
            unclassified_files=unclassified_files,
            ok=False,
            commit_allowed=False,
            push_allowed=False,
            approval_required=True,
            commit_message=commit_message,
            git_add_commands=[],
            backup_record_path=f"reports/git/{task_id}-git-backup-record.md",
            fail_reason="forbidden_files_detected",
            next_action="stop",
        )

    # ---- unclassified files 检查 ----
    if unclassified_files:
        return GitBackupGateResult(
            project_root=project_root,
            gate_timestamp=timestamp,
            task_id=task_id,
            check_result_pass=True,
            continuous_report_exists=True,
            worktree_status=worktree_status,
            changed_files=changed_files,
            allowed_files=allowed_files,
            forbidden_files=[],
            unclassified_files=unclassified_files,
            ok=False,
            commit_allowed=False,
            push_allowed=False,
            approval_required=True,
            commit_message=commit_message,
            git_add_commands=[],
            backup_record_path=f"reports/git/{task_id}-git-backup-record.md",
            fail_reason="unclassified_files_detected",
            next_action="stop",
        )

    # ---- allowed_files 为空 ----
    if not allowed_files:
        return GitBackupGateResult(
            project_root=project_root,
            gate_timestamp=timestamp,
            task_id=task_id,
            check_result_pass=True,
            continuous_report_exists=True,
            worktree_status=worktree_status,
            changed_files=changed_files,
            allowed_files=[],
            forbidden_files=[],
            unclassified_files=[],
            ok=False,
            commit_allowed=False,
            push_allowed=False,
            approval_required=True,
            commit_message=commit_message,
            git_add_commands=[],
            backup_record_path=f"reports/git/{task_id}-git-backup-record.md",
            fail_reason="no_allowed_files",
            next_action="stop",
        )

    # ---- commit message 校验 ----
    if not validate_commit_message(commit_message):
        return GitBackupGateResult(
            project_root=project_root,
            gate_timestamp=timestamp,
            task_id=task_id,
            check_result_pass=True,
            continuous_report_exists=True,
            worktree_status=worktree_status,
            changed_files=changed_files,
            allowed_files=allowed_files,
            forbidden_files=[],
            unclassified_files=[],
            ok=False,
            commit_allowed=False,
            push_allowed=False,
            approval_required=True,
            commit_message=commit_message,
            git_add_commands=[],
            backup_record_path=f"reports/git/{task_id}-git-backup-record.md",
            fail_reason="commit_message_invalid",
            next_action="stop",
        )

    # ---- 全部通过 ----
    git_add_commands = build_git_add_commands(allowed_files)
    approval_required = approval_mode == "require_user_approval"

    ok = True
    commit_allowed = True
    push_allowed = commit_allowed and not approval_required
    next_action = "proceed_to_commit"

    return GitBackupGateResult(
        project_root=project_root,
        gate_timestamp=timestamp,
        task_id=task_id,
        check_result_pass=True,
        continuous_report_exists=True,
        worktree_status=worktree_status,
        changed_files=changed_files,
        allowed_files=allowed_files,
        forbidden_files=[],
        unclassified_files=[],
        ok=ok,
        commit_allowed=commit_allowed,
        push_allowed=push_allowed,
        approval_required=approval_required,
        commit_message=commit_message,
        git_add_commands=git_add_commands,
        backup_record_path=f"reports/git/{task_id}-git-backup-record.md",
        fail_reason=None,
        next_action=next_action,
    )


# ---------------------------------------------------------------------------
# Approval Record 生成
# ---------------------------------------------------------------------------

def ensure_directory(path: Path) -> None:
    """确保目录存在，不存在则创建。"""
    path.mkdir(parents=True, exist_ok=True)


def render_git_backup_approval_record(result: GitBackupGateResult) -> str:
    """渲染 Git backup approval record Markdown 内容。

    只生成记录，不执行任何真实 Git 操作。
    """
    gate_result_str = "pass" if result.ok else "fail"
    timestamp = result.gate_timestamp

    lines: list[str] = []
    lines.append(f"# {result.task_id} Git Backup Approval Record")
    lines.append("")
    lines.append(f"生成时间：{timestamp}")
    lines.append(f"阶段：Stage 9 — Git Backup Gate Approval Record")
    lines.append("")

    # Section 1: Gate Result
    lines.append("## 1. Gate Result")
    lines.append("")
    lines.append(f"| Field | Value |")
    lines.append(f"|-------|-------|")
    lines.append(f"| TASK | {result.task_id} |")
    lines.append(f"| GIT_BACKUP_GATE_RESULT | {gate_result_str} |")
    lines.append(f"| GATE_TIMESTAMP | {result.gate_timestamp} |")
    lines.append(f"| CHECK_RESULT_PASS | {'yes' if result.check_result_pass else 'no'} |")
    lines.append(f"| CONTINUOUS_REPORT_EXISTS | {'yes' if result.continuous_report_exists else 'no'} |")
    lines.append(f"| WORKTREE_STATUS | {result.worktree_status} |")
    if result.fail_reason:
        lines.append(f"| FAIL_REASON | {result.fail_reason} |")
    lines.append(f"| NEXT_ACTION | {result.next_action} |")
    lines.append("")

    # Section 2: Changed Files
    lines.append("## 2. Changed Files")
    lines.append("")
    for f in result.changed_files:
        lines.append(f"- `{f}`")
    if not result.changed_files:
        lines.append("(none)")
    lines.append("")

    # Section 3: Allowed Files
    lines.append("## 3. Allowed Files")
    lines.append("")
    for f in result.allowed_files:
        lines.append(f"- `{f}`")
    if not result.allowed_files:
        lines.append("(none)")
    lines.append("")

    # Section 4: Forbidden Files
    lines.append("## 4. Forbidden Files")
    lines.append("")
    for f in result.forbidden_files:
        lines.append(f"- `{f}`")
    if not result.forbidden_files:
        lines.append("(none)")
    lines.append("")

    # Section 5: Unclassified Files
    lines.append("## 5. Unclassified Files")
    lines.append("")
    for f in result.unclassified_files:
        lines.append(f"- `{f}`")
    if not result.unclassified_files:
        lines.append("(none)")
    lines.append("")

    # Section 6: Proposed Git Add Commands
    lines.append("## 6. Proposed Git Add Commands")
    lines.append("")
    lines.append("```")
    for cmd in result.git_add_commands:
        lines.append(cmd)
    if not result.git_add_commands:
        lines.append("(no commands)")
    lines.append("```")
    lines.append("")

    # Section 7: Proposed Commit Message
    lines.append("## 7. Proposed Commit Message")
    lines.append("")
    lines.append("```")
    lines.append(result.commit_message)
    lines.append("```")
    lines.append("")

    # Section 8: Approval Requirement
    lines.append("## 8. Approval Requirement")
    lines.append("")
    lines.append(f"| Field | Value |")
    lines.append(f"|-------|-------|")
    lines.append(f"| APPROVAL_REQUIRED | {'yes' if result.approval_required else 'no'} |")
    lines.append(f"| APPROVAL_STATUS | pending |")
    lines.append("")

    # Section 9: Commit and Push Decision
    lines.append("## 9. Commit and Push Decision")
    lines.append("")
    lines.append(f"| Field | Value |")
    lines.append(f"|-------|-------|")
    lines.append(f"| COMMIT_ALLOWED | {'yes' if result.commit_allowed else 'no'} |")
    lines.append(f"| PUSH_ALLOWED | {'yes' if result.push_allowed else 'no'} |")
    lines.append(f"| COMMIT_STATUS | pending |")
    lines.append(f"| PUSH_STATUS | pending |")
    lines.append("")

    # Section 10: Safety Notes
    lines.append("## 10. Safety Notes")
    lines.append("")
    lines.append(f"- REAL_GIT_ADD_EXECUTED=no")
    lines.append(f"- REAL_GIT_COMMIT_EXECUTED=no")
    lines.append(f"- REAL_GIT_PUSH_EXECUTED=no")
    lines.append(f"- GATE_MODIFIED_FILES={'yes' if result.gate_modified_files else 'no'}")
    lines.append(f"- RECORD_GENERATED_BY=git_backup_gate_dry_run")
    lines.append("")

    # Final Status
    lines.append("---")
    lines.append("")
    lines.append("```")
    lines.append(f"TASK={result.task_id}")
    lines.append(f"GIT_BACKUP_GATE_RESULT={gate_result_str}")
    lines.append(f"COMMIT_ALLOWED={'yes' if result.commit_allowed else 'no'}")
    lines.append(f"PUSH_ALLOWED={'yes' if result.push_allowed else 'no'}")
    lines.append(f"APPROVAL_REQUIRED={'yes' if result.approval_required else 'no'}")
    lines.append(f"REAL_GIT_ADD_EXECUTED=no")
    lines.append(f"REAL_GIT_COMMIT_EXECUTED=no")
    lines.append(f"REAL_GIT_PUSH_EXECUTED=no")
    lines.append("```")
    lines.append("")

    return "\n".join(lines)


def write_git_backup_approval_record(
    repo_root: Path, result: GitBackupGateResult
) -> Path:
    """将 Git backup approval record 写入文件。

    路径：reports/git/{task_id}-git-backup-approval-record.md

    只写入记录，不执行任何真实 Git 操作。
    """
    record_dir = repo_root / "reports" / "git"
    ensure_directory(record_dir)

    record_path = record_dir / f"{result.task_id}-git-backup-approval-record.md"
    content = render_git_backup_approval_record(result)
    record_path.write_text(content, encoding="utf-8")

    return record_path


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------

def print_result(result: GitBackupGateResult) -> None:
    """格式化输出 GitBackupGateResult。"""
    if result.ok:
        print(f"GIT_BACKUP_GATE_RESULT=pass")
    else:
        print(f"GIT_BACKUP_GATE_RESULT=fail")

    print(f"TASK={result.task_id}")
    print(f"CHECK_RESULT_PASS={'yes' if result.check_result_pass else 'no'}")
    print(f"CONTINUOUS_REPORT_EXISTS={'yes' if result.continuous_report_exists else 'no'}")
    print(f"WORKTREE_STATUS={result.worktree_status}")
    print(f"CHANGED_FILES={result.changed_files}")
    print(f"ALLOWED_FILES={result.allowed_files}")
    print(f"FORBIDDEN_FILES={result.forbidden_files}")
    print(f"UNCLASSIFIED_FILES={result.unclassified_files}")
    print(f"COMMIT_ALLOWED={'yes' if result.commit_allowed else 'no'}")
    print(f"PUSH_ALLOWED={'yes' if result.push_allowed else 'no'}")
    print(f"APPROVAL_REQUIRED={'yes' if result.approval_required else 'no'}")
    print(f"COMMIT_MESSAGE={result.commit_message}")
    print(f"GIT_ADD_COMMANDS={result.git_add_commands}")
    print(f"BACKUP_RECORD_PATH={result.backup_record_path}")

    if result.fail_reason:
        print(f"FAIL_REASON={result.fail_reason}")

    print(f"NEXT_ACTION={result.next_action}")
    print(f"GATE_MODIFIED_FILES={'yes' if result.gate_modified_files else 'no'}")


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def _parse_cli_args(args: list[str]) -> dict:
    """解析 CLI 参数。"""
    parsed: dict = {
        "allowed": [],
        "forbidden": [],
    }
    i = 0
    while i < len(args):
        if args[i] == "--task" and i + 1 < len(args):
            parsed["task"] = args[i + 1]
            i += 2
        elif args[i] == "--check-result" and i + 1 < len(args):
            parsed["check_result"] = args[i + 1]
            i += 2
        elif args[i] == "--report" and i + 1 < len(args):
            parsed["report"] = args[i + 1]
            i += 2
        elif args[i] == "--commit-message" and i + 1 < len(args):
            parsed["commit_message"] = args[i + 1]
            i += 2
        elif args[i] == "--allowed" and i + 1 < len(args):
            parsed["allowed"].append(args[i + 1])
            i += 2
        elif args[i] == "--forbidden" and i + 1 < len(args):
            parsed["forbidden"].append(args[i + 1])
            i += 2
        elif args[i] == "--approval-mode" and i + 1 < len(args):
            parsed["approval_mode"] = args[i + 1]
            i += 2
        elif args[i] == "--write-approval-record":
            parsed["write_approval_record"] = True
            i += 1
        else:
            i += 1
    return parsed


if __name__ == "__main__":
    parsed = _parse_cli_args(sys.argv[1:])

    task_id = parsed.get("task", "")
    check_result = parsed.get("check_result", "")
    report = parsed.get("report", "")
    commit_message = parsed.get("commit_message", "")
    allowed = parsed.get("allowed", [])
    forbidden = parsed.get("forbidden", [])
    approval_mode = parsed.get("approval_mode", "require_user_approval")
    write_approval_record = parsed.get("write_approval_record", False)

    if not task_id or not check_result or not report or not commit_message:
        print("GIT_BACKUP_GATE_RESULT=error")
        print("FAIL_REASON=missing_required_args")
        print('Usage: python tools/git_backup_gate.py --task Txxx --check-result pass --report path/to/report.md --commit-message "type: description" --allowed path1 --allowed path2 --forbidden path3 --approval-mode require_user_approval --write-approval-record')
        sys.exit(1)

    script_path = Path(__file__).resolve()
    root = script_path.parent.parent

    result = run_git_backup_gate_dry_run(
        repo_root=root,
        task_id=task_id,
        check_result=check_result,
        continuous_run_report_path=report,
        explicitly_allowed_paths=allowed,
        explicitly_forbidden_paths=forbidden,
        commit_message=commit_message,
        approval_mode=approval_mode,
    )

    print_result(result)

    if write_approval_record:
        record_path = write_git_backup_approval_record(root, result)
        print(f"APPROVAL_RECORD_PATH={record_path}")

    if not result.ok:
        sys.exit(1)
