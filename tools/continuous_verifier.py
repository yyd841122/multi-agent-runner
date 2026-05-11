"""Continuous Verifier — 执行后结果确定性验证。

遵循 docs/stage8-monitor-verify-report-architecture.md 设计。
只读不写，不修改任何文件，不修复任何问题。
验证失败时 fail closed。

T156 实现。
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

FORBIDDEN_PATHS: list[str] = [
    "runner.py",
    ".git/",
    ".github/",
    "pyproject.toml",
    "requirements.txt",
    "package.json",
]


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class ContinuousVerifyResult:
    """连续任务执行后验证结果。"""

    # 基本信息
    project_root: str
    verify_timestamp: str
    task_id: str

    # 任务状态验证
    expected_next_pending: str
    actual_next_pending: str | None
    expected_next_stage: str
    actual_next_stage: str | None
    task_marked_done: bool

    # 报告验证
    report_exists: bool
    check_result_pass: bool

    # 安全边界验证
    max_tasks_one_confirmed: bool
    unlimited_continuation: bool
    next_task_executed: bool
    auto_commit_triggered: bool
    auto_push_triggered: bool

    # 文件变更验证
    forbidden_files_changed: bool
    unclassified_changes: bool
    unclassified_files: list[str]

    # 汇总
    ok: bool
    fail_reason: str | None
    next_action: str  # continue_to_report_writer / stop

    # 安全保证
    verifier_modified_files: bool = False  # 始终 False


# ---------------------------------------------------------------------------
# 基础工具函数
# ---------------------------------------------------------------------------

def read_text_file(path: Path) -> str:
    """读取文本文件内容，不存在则返回空字符串。"""
    if path.exists() and path.is_file():
        return path.read_text(encoding="utf-8")
    return ""


def parse_next_pending(tasks_text: str) -> str | None:
    """从 tasks.md 文本中识别最后一个 NEXT_PENDING。

    文件中可能存在多个 NEXT_PENDING（每个任务完成时记录），
    取最后一个作为当前实际值。

    支持格式：
      <!-- NEXT_PENDING=Txxx -->
      NEXT_PENDING=Txxx
    """
    matches = re.findall(r"<!--\s*NEXT_PENDING\s*=\s*(T\d+)\s*-->", tasks_text)
    if matches:
        return matches[-1]

    matches = re.findall(r"^NEXT_PENDING\s*=\s*(T\d+)\s*$", tasks_text, re.MULTILINE)
    if matches:
        return matches[-1]

    return None


def parse_next_stage(tasks_text: str) -> str | None:
    """从 tasks.md 文本中识别最后一个 NEXT_STAGE。

    文件中可能存在多个 NEXT_STAGE（每个任务完成时记录），
    取最后一个作为当前实际值。

    支持格式：
      <!-- NEXT_STAGE=Stage N -->
      NEXT_STAGE=Stage N
    """
    matches = re.findall(r"<!--\s*NEXT_STAGE\s*=\s*(Stage\s+\d+)\s*-->", tasks_text)
    if matches:
        return matches[-1]

    matches = re.findall(r"^NEXT_STAGE\s*=\s*(Stage\s+\d+)\s*$", tasks_text, re.MULTILINE)
    if matches:
        return matches[-1]

    return None


def is_task_marked_done(tasks_text: str, task_id: str) -> bool:
    """判断指定任务是否已标记为 done。

    兼容中文格式「状态：done」和英文格式「status: done」。
    使用逐行扫描确保可靠性。
    """
    lines = tasks_text.split("\n")
    in_task = False
    for line in lines:
        # 匹配任务标题行
        if re.match(rf"^## {re.escape(task_id)}\b", line):
            in_task = True
            continue
        # 遇到下一个任务标题，停止扫描
        if in_task and line.startswith("## "):
            break
        # 在任务块内检查状态
        if in_task:
            if re.match(r"^状态\s*[：:]\s*done\s*$", line.strip()):
                return True
            if re.match(r"^status\s*[：:]\s*done\s*$", line.strip(), re.IGNORECASE):
                return True
    return False


def report_contains_check_result_pass(report_text: str) -> bool:
    """检查报告是否包含 CHECK_RESULT=pass。"""
    return bool(re.search(r"CHECK_RESULT\s*=\s*pass", report_text))


def report_confirms_max_tasks_one(report_text: str) -> bool:
    """检查报告是否确认 MAX_TASKS=1。"""
    return bool(re.search(r"MAX_TASKS\s*=\s*1\b", report_text))


def report_confirms_no_unlimited_continuation(report_text: str) -> bool:
    """检查报告是否确认无无限连续执行。

    匹配 UNLIMITED_CONTINUATION=no 或 REAL_CONTINUOUS_EXECUTION_STARTED=no
    或 CONTINUOUS_AUTO_ADVANCE_USED=no。
    """
    if re.search(r"UNLIMITED_CONTINUATION\s*=\s*no", report_text):
        return True
    if re.search(r"REAL_CONTINUOUS_EXECUTION_STARTED\s*=\s*no", report_text):
        return True
    if re.search(r"CONTINUOUS_AUTO_ADVANCE_USED\s*=\s*(?:False|no)", report_text):
        return True
    return False


def report_confirms_no_next_task_executed(report_text: str) -> bool:
    """检查报告是否确认 next_task_executed=no/False。"""
    if re.search(r"NEXT_TASK_EXECUTED\s*=\s*(?:False|no)", report_text):
        return True
    return False


def report_confirms_no_auto_commit_push(report_text: str) -> tuple[bool, bool]:
    """检查报告是否确认无自动 commit/push。

    Returns:
        (no_auto_commit, no_auto_push)
    """
    no_commit = bool(re.search(r"AUTO_COMMIT_TRIGGERED\s*=\s*(?:False|no)", report_text))
    if not no_commit:
        no_commit = bool(re.search(r"REAL_GIT_COMMIT_USED\s*=\s*(?:False|no)", report_text))

    no_push = bool(re.search(r"AUTO_PUSH_TRIGGERED\s*=\s*(?:False|no)", report_text))
    if not no_push:
        no_push = bool(re.search(r"REAL_GIT_PUSH_USED\s*=\s*(?:False|no)", report_text))

    return no_commit, no_push


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
        # fail-closed: 无法获取时返回非空列表
        return ["<unknown>"]


def classify_changed_files(
    changed_files: list[str],
    allowed_paths: list[str],
) -> tuple[bool, list[str]]:
    """判断变更文件是否全部在 allowed_paths 内。

    Args:
        changed_files: 实际变更的文件列表
        allowed_paths: 允许变更的文件/路径列表

    Returns:
        (has_unclassified, unclassified_files)
    """
    unclassified: list[str] = []
    for f in changed_files:
        if f in allowed_paths:
            continue
        # 检查是否为 allowed_paths 中某个路径的子路径
        matched = False
        for ap in allowed_paths:
            if f.startswith(ap):
                matched = True
                break
        if not matched:
            unclassified.append(f)

    return len(unclassified) > 0, unclassified


# ---------------------------------------------------------------------------
# 核心函数
# ---------------------------------------------------------------------------

def verify_continuous_result(
    repo_root: Path,
    task_id: str,
    expected_next_pending: str,
    expected_next_stage: str,
    report_path: str,
    allowed_paths: list[str],
) -> ContinuousVerifyResult:
    """执行连续任务执行后验证。

    只读不写，不修改任何文件。
    验证失败时 fail closed。
    """
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    project_root = str(repo_root)

    # ---- 读取 docs/tasks.md ----
    tasks_file = repo_root / "docs" / "tasks.md"
    if not tasks_file.exists() or not tasks_file.is_file():
        return ContinuousVerifyResult(
            project_root=project_root,
            verify_timestamp=timestamp,
            task_id=task_id,
            expected_next_pending=expected_next_pending,
            actual_next_pending=None,
            expected_next_stage=expected_next_stage,
            actual_next_stage=None,
            task_marked_done=False,
            report_exists=False,
            check_result_pass=False,
            max_tasks_one_confirmed=False,
            unlimited_continuation=True,
            next_task_executed=True,
            auto_commit_triggered=True,
            auto_push_triggered=True,
            forbidden_files_changed=True,
            unclassified_changes=True,
            unclassified_files=["<all>"],
            ok=False,
            fail_reason="tasks_md_not_found",
            next_action="stop",
        )

    tasks_text = read_text_file(tasks_file)

    # ---- 检查任务是否标记为 done ----
    task_marked_done = is_task_marked_done(tasks_text, task_id)

    # ---- 识别 NEXT_PENDING ----
    actual_next_pending = parse_next_pending(tasks_text)

    # ---- 识别 NEXT_STAGE ----
    actual_next_stage = parse_next_stage(tasks_text)

    # ---- 读取报告文件 ----
    report_file = repo_root / report_path
    report_exists = report_file.exists() and report_file.is_file()
    report_text = read_text_file(report_file) if report_exists else ""

    # ---- 报告内容验证 ----
    check_result_pass = report_contains_check_result_pass(report_text) if report_text else False
    max_tasks_one_confirmed = report_confirms_max_tasks_one(report_text) if report_text else False
    no_unlimited = report_confirms_no_unlimited_continuation(report_text) if report_text else False
    no_next_task = report_confirms_no_next_task_executed(report_text) if report_text else False
    no_auto_commit, no_auto_push = (
        report_confirms_no_auto_commit_push(report_text) if report_text else (False, False)
    )

    # 转换为 fail-closed 布尔值
    unlimited_continuation = not no_unlimited
    next_task_executed = not no_next_task
    auto_commit_triggered = not no_auto_commit
    auto_push_triggered = not no_auto_push

    # ---- 文件变更验证 ----
    changed_files = get_git_changed_files(repo_root)

    # forbidden path 检查
    forbidden_files_changed = False
    for f in changed_files:
        for fp in FORBIDDEN_PATHS:
            if f == fp or f.startswith(fp):
                # 即使在 allowed_paths 中也 fail closed
                forbidden_files_changed = True
                break
        if forbidden_files_changed:
            break

    # unclassified changes 检查
    unclassified_changes, unclassified_files = classify_changed_files(
        changed_files, allowed_paths
    )

    # ---- 汇总判断 ----
    fail_reasons: list[str] = []

    if not task_marked_done:
        fail_reasons.append(f"task_not_done:{task_id}")
    if actual_next_pending != expected_next_pending:
        fail_reasons.append(
            f"next_pending_mismatch:expected={expected_next_pending},actual={actual_next_pending}"
        )
    if actual_next_stage != expected_next_stage:
        fail_reasons.append(
            f"next_stage_mismatch:expected={expected_next_stage},actual={actual_next_stage}"
        )
    if not report_exists:
        fail_reasons.append("missing_report")
    if not check_result_pass:
        fail_reasons.append("check_result_not_pass")
    if not max_tasks_one_confirmed:
        fail_reasons.append("max_tasks_not_one")
    if unlimited_continuation:
        fail_reasons.append("unlimited_continuation_detected")
    if next_task_executed:
        fail_reasons.append("next_task_executed_detected")
    if auto_commit_triggered:
        fail_reasons.append("auto_commit_detected")
    if auto_push_triggered:
        fail_reasons.append("auto_push_detected")
    if forbidden_files_changed:
        fail_reasons.append("forbidden_files_changed")
    if unclassified_changes:
        fail_reasons.append(f"unclassified_changes:{unclassified_files}")

    ok = len(fail_reasons) == 0
    fail_reason = "; ".join(fail_reasons) if fail_reasons else None

    return ContinuousVerifyResult(
        project_root=project_root,
        verify_timestamp=timestamp,
        task_id=task_id,
        expected_next_pending=expected_next_pending,
        actual_next_pending=actual_next_pending,
        expected_next_stage=expected_next_stage,
        actual_next_stage=actual_next_stage,
        task_marked_done=task_marked_done,
        report_exists=report_exists,
        check_result_pass=check_result_pass,
        max_tasks_one_confirmed=max_tasks_one_confirmed,
        unlimited_continuation=unlimited_continuation,
        next_task_executed=next_task_executed,
        auto_commit_triggered=auto_commit_triggered,
        auto_push_triggered=auto_push_triggered,
        forbidden_files_changed=forbidden_files_changed,
        unclassified_changes=unclassified_changes,
        unclassified_files=unclassified_files,
        ok=ok,
        fail_reason=fail_reason,
        next_action="continue_to_report_writer" if ok else "stop",
    )


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def _format_cli_output(result: ContinuousVerifyResult) -> str:
    """格式化 CLI 输出。"""
    lines = []

    if result.ok:
        lines.append("VERIFY_RESULT=pass")
        lines.append(f"TASK={result.task_id}")
        lines.append(f"EXPECTED_NEXT_PENDING={result.expected_next_pending}")
        lines.append(f"ACTUAL_NEXT_PENDING={result.actual_next_pending}")
        lines.append(f"EXPECTED_NEXT_STAGE={result.expected_next_stage}")
        lines.append(f"ACTUAL_NEXT_STAGE={result.actual_next_stage}")
        lines.append(f"TASK_MARKED_DONE={'yes' if result.task_marked_done else 'no'}")
        lines.append(f"REPORT_EXISTS={'yes' if result.report_exists else 'no'}")
        lines.append(f"CHECK_RESULT_PASS={'yes' if result.check_result_pass else 'no'}")
        lines.append(f"MAX_TASKS_ONE_CONFIRMED={'yes' if result.max_tasks_one_confirmed else 'no'}")
        lines.append(f"UNLIMITED_CONTINUATION={'yes' if result.unlimited_continuation else 'no'}")
        lines.append(f"NEXT_TASK_EXECUTED={'yes' if result.next_task_executed else 'no'}")
        lines.append(f"AUTO_COMMIT_TRIGGERED={'yes' if result.auto_commit_triggered else 'no'}")
        lines.append(f"AUTO_PUSH_TRIGGERED={'yes' if result.auto_push_triggered else 'no'}")
        lines.append(f"FORBIDDEN_FILES_CHANGED={'yes' if result.forbidden_files_changed else 'no'}")
        lines.append(f"UNCLASSIFIED_CHANGES={'yes' if result.unclassified_changes else 'no'}")
        lines.append(f"NEXT_ACTION={result.next_action}")
    else:
        lines.append("VERIFY_RESULT=fail")
        lines.append(f"TASK={result.task_id}")
        lines.append(f"FAIL_REASON={result.fail_reason}")
        lines.append(f"NEXT_ACTION={result.next_action}")

    return "\n".join(lines)


def _parse_cli_args(args: list[str]) -> dict[str, list[str] | str]:
    """解析 CLI 参数。"""
    parsed: dict[str, list[str] | str] = {"allowed": []}
    i = 0
    while i < len(args):
        if args[i] == "--task" and i + 1 < len(args):
            parsed["task"] = args[i + 1]
            i += 2
        elif args[i] == "--expected-next" and i + 1 < len(args):
            parsed["expected_next"] = args[i + 1]
            i += 2
        elif args[i] == "--expected-stage" and i + 1 < len(args):
            parsed["expected_stage"] = args[i + 1]
            i += 2
        elif args[i] == "--report" and i + 1 < len(args):
            parsed["report"] = args[i + 1]
            i += 2
        elif args[i] == "--allowed" and i + 1 < len(args):
            parsed["allowed"].append(args[i + 1])  # type: ignore[union-attr]
            i += 2
        else:
            i += 1
    return parsed


if __name__ == "__main__":
    parsed = _parse_cli_args(sys.argv[1:])

    task_id = parsed.get("task", "")
    expected_next = parsed.get("expected_next", "")
    expected_stage = parsed.get("expected_stage", "")
    report = parsed.get("report", "")
    allowed = parsed.get("allowed", [])
    if isinstance(allowed, str):
        allowed = [allowed]

    if not task_id or not expected_next or not expected_stage or not report:
        print("VERIFY_RESULT=error")
        print("FAIL_REASON=missing_required_args")
        print("Usage: python tools/continuous_verifier.py --task Txxx --expected-next Tyyy --expected-stage \"Stage N\" --report path/to/report.md --allowed path1 --allowed path2")
        sys.exit(1)

    script_path = Path(__file__).resolve()
    root = script_path.parent.parent

    result = verify_continuous_result(
        repo_root=root,
        task_id=task_id,
        expected_next_pending=expected_next,
        expected_next_stage=expected_stage,
        report_path=report,
        allowed_paths=allowed,
    )

    output = _format_cli_output(result)
    print(output)

    if not result.ok:
        sys.exit(1)
