"""Claude Code 执行器 — 调用 Claude Code CLI 完成编码任务"""

from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path


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
        }
    """
    started_at = datetime.now()
    result = subprocess.run(
        [command, "--permission-mode", "acceptEdits", "--print", prompt],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
    )
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
    }
