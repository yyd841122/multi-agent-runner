"""Claude Code 执行器 — 调用 Claude Code CLI 完成编码任务"""

from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

# Claude Code 子进程超时时间（秒）
CLAUDE_CODE_TIMEOUT_SECONDS = 600

# 允许的 permission mode 值
VALID_PERMISSION_MODES = {"acceptEdits", "default", "none", "bypassPermissions"}


def build_claude_permission_args(permission_mode: str | None) -> list[str]:
    """根据 permission_mode 构造 Claude CLI 参数列表。

    Args:
        permission_mode: 权限模式。
            None / "" / "acceptEdits" → ["--permission-mode", "acceptEdits"]
            "default" / "none" → []  (不传 --permission-mode)
            "bypassPermissions" → ["--permission-mode", "bypassPermissions"]
            其他 → 抛出 ValueError

    Returns:
        传递给 Claude CLI 的参数列表。
    """
    if permission_mode is None or permission_mode == "" or permission_mode == "acceptEdits":
        return ["--permission-mode", "acceptEdits"]
    if permission_mode in ("default", "none"):
        return []
    if permission_mode == "bypassPermissions":
        return ["--permission-mode", "bypassPermissions"]
    raise ValueError(
        f"未知的 permission_mode: '{permission_mode}'。"
        f"允许值：{', '.join(sorted(VALID_PERMISSION_MODES))}"
    )


def load_prompt(path: str | Path) -> str:
    """读取 prompts/current_prompt.md。"""
    return Path(path).read_text(encoding="utf-8")


def run_claude_code(
    prompt: str,
    command: str = "claude",
    permission_mode: str | None = "acceptEdits",
) -> dict:
    """调用 Claude Code CLI 执行 prompt。

    Args:
        prompt: 执行提示词。
        command: Claude CLI 命令路径。
        permission_mode: 权限模式，默认 acceptEdits。
            "acceptEdits" → 传 --permission-mode acceptEdits
            "default" / "none" → 不传 --permission-mode
            "bypassPermissions" → 传 --permission-mode bypassPermissions

    返回:
        {
            "success": bool,
            "returncode": int,
            "stdout": str,
            "stderr": str,
            "started_at": str,
            "ended_at": str,
            "duration_seconds": float,
            "timed_out": bool,
            "timeout_seconds": int | None,
            "permission_mode": str,
            "permission_args_passed": bool,
        }
    """
    timeout = CLAUDE_CODE_TIMEOUT_SECONDS
    started_at = datetime.now()

    # 构造权限参数
    try:
        perm_args = build_claude_permission_args(permission_mode)
    except ValueError:
        return {
            "success": False,
            "returncode": 2,
            "stdout": "",
            "stderr": f"未知的 permission_mode: '{permission_mode}'。允许值：{', '.join(sorted(VALID_PERMISSION_MODES))}",
            "started_at": started_at.strftime("%Y-%m-%d %H:%M:%S"),
            "ended_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "duration_seconds": 0.0,
            "timed_out": False,
            "timeout_seconds": None,
            "permission_mode": str(permission_mode),
            "permission_args_passed": False,
        }

    # 构造完整命令
    cmd = [command]
    cmd.extend(perm_args)
    cmd.extend(["--print", prompt])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        ended_at = datetime.now()
        duration = (ended_at - started_at).total_seconds()
        return {
            "success": False,
            "returncode": 124,
            "stdout": "",
            "stderr": (
                f"Claude Code execution timed out after {timeout} seconds.\n"
                f"This task was not automatically completed.\n"
                f"Please inspect files and retry manually if needed."
            ),
            "started_at": started_at.strftime("%Y-%m-%d %H:%M:%S"),
            "ended_at": ended_at.strftime("%Y-%m-%d %H:%M:%S"),
            "duration_seconds": round(duration, 2),
            "timed_out": True,
            "timeout_seconds": timeout,
            "permission_mode": str(permission_mode) if permission_mode else "acceptEdits",
            "permission_args_passed": len(perm_args) > 0,
        }

    ended_at = datetime.now()
    duration = (ended_at - started_at).total_seconds()

    return {
        "success": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "started_at": started_at.strftime("%Y-%m-%d %H:%M:%S"),
        "ended_at": ended_at.strftime("%Y-%m-%d %H:%M:%S"),
        "duration_seconds": round(duration, 2),
        "timed_out": False,
        "timeout_seconds": None,
        "permission_mode": str(permission_mode) if permission_mode else "acceptEdits",
        "permission_args_passed": len(perm_args) > 0,
    }
