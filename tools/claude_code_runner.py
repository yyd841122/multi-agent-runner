"""Claude Code 执行器 — 调用 Claude Code CLI 完成编码任务"""

from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

# Claude Code 子进程超时时间（秒）
CLAUDE_CODE_TIMEOUT_SECONDS = 600


def load_prompt(path: str | Path) -> str:
    """读取 prompts/current_prompt.md。"""
    return Path(path).read_text(encoding="utf-8")


def run_claude_code(prompt: str, command: str = "claude") -> dict:
    """调用 Claude Code CLI 执行 prompt。

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
        }
    """
    timeout = CLAUDE_CODE_TIMEOUT_SECONDS
    started_at = datetime.now()

    try:
        result = subprocess.run(
            [command, "--permission-mode", "acceptEdits", "--print", prompt],
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
    }
