"""Task Monitor — 执行前状态采集与预检。

遵循 docs/stage8-monitor-verify-report-architecture.md 设计。
只读不写，不修改任何文件，不执行任何任务。

T155 实现。
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class TaskMonitorResult:
    """任务监控结果。"""

    # 基本状态
    project_root: str
    monitor_timestamp: str

    # 任务状态
    next_pending: str | None
    next_stage: str | None

    # Workspace 状态
    worktree_status: str  # clean / dirty

    # State 文件状态
    run_state_exists: bool
    checkpoint_exists: bool

    # Monitor 决策
    ok: bool
    resume_required: bool
    rate_limit_blocked: bool
    real_execution_allowed: bool
    fail_reason: str | None
    next_action: str  # continue_to_safety_gate / stop

    # 安全保证
    monitor_modified_files: bool = False  # 始终 False


# ---------------------------------------------------------------------------
# 基础工具函数
# ---------------------------------------------------------------------------

def read_text_file(path: Path) -> str:
    """读取文本文件内容，不存在则返回空字符串。"""
    if path.exists() and path.is_file():
        return path.read_text(encoding="utf-8")
    return ""


def parse_next_pending(tasks_text: str) -> str | None:
    """从 tasks.md 文本中识别 NEXT_PENDING。

    支持格式：
      <!-- NEXT_PENDING=Txxx -->
      NEXT_PENDING=Txxx
    """
    # 优先匹配 HTML 注释格式
    m = re.search(r"<!--\s*NEXT_PENDING\s*=\s*(T\d+)\s*-->", tasks_text)
    if m:
        return m.group(1)

    # 回退匹配纯文本格式
    m = re.search(r"^NEXT_PENDING\s*=\s*(T\d+)\s*$", tasks_text, re.MULTILINE)
    if m:
        return m.group(1)

    return None


def parse_next_stage(tasks_text: str) -> str | None:
    """从 tasks.md 文本中识别 NEXT_STAGE。

    支持格式：
      <!-- NEXT_STAGE=Stage N -->
      NEXT_STAGE=Stage N
    """
    # 优先匹配 HTML 注释格式
    m = re.search(r"<!--\s*NEXT_STAGE\s*=\s*(Stage\s+\d+)\s*-->", tasks_text)
    if m:
        return m.group(1)

    # 回退匹配纯文本格式
    m = re.search(r"^NEXT_STAGE\s*=\s*(Stage\s+\d+)\s*$", tasks_text, re.MULTILINE)
    if m:
        return m.group(1)

    return None


def get_git_worktree_status(repo_root: Path) -> str:
    """通过 git status --short 检查工作区状态。

    只允许调用 git status，不允许调用 git add/commit/push。
    有输出 → dirty，无输出 → clean。
    """
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout.strip()
        return "dirty" if output else "clean"
    except Exception:
        # fail-closed: 无法判断时返回 dirty
        return "dirty"


def check_state_files(repo_root: Path) -> tuple[bool, bool]:
    """检查 run-state.json 和 checkpoint.json 是否存在。

    Returns:
        (run_state_exists, checkpoint_exists)
    """
    state_dir = repo_root / "reports" / "state"

    run_state_path = state_dir / "run-state.json"
    checkpoint_path = state_dir / "checkpoint.json"

    run_state_exists = run_state_path.exists() and run_state_path.is_file()
    checkpoint_exists = checkpoint_path.exists() and checkpoint_path.is_file()

    return run_state_exists, checkpoint_exists


# ---------------------------------------------------------------------------
# 核心函数
# ---------------------------------------------------------------------------

def monitor_project(repo_root: Path) -> TaskMonitorResult:
    """执行项目监控，采集执行前状态。

    只读不写，不修改任何文件。
    dirty workspace 时 fail closed。
    docs/tasks.md 不存在时 fail closed。
    NEXT_PENDING 缺失时 fail closed。
    NEXT_STAGE 缺失时 fail closed。
    """
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    project_root = str(repo_root)

    # 检查 docs/tasks.md 是否存在
    tasks_file = repo_root / "docs" / "tasks.md"
    if not tasks_file.exists() or not tasks_file.is_file():
        return TaskMonitorResult(
            project_root=project_root,
            monitor_timestamp=timestamp,
            next_pending=None,
            next_stage=None,
            worktree_status="unknown",
            run_state_exists=False,
            checkpoint_exists=False,
            ok=False,
            resume_required=False,
            rate_limit_blocked=False,
            real_execution_allowed=False,
            fail_reason="tasks_md_not_found",
            next_action="stop",
        )

    # 读取 tasks.md
    tasks_text = read_text_file(tasks_file)

    # 识别 NEXT_PENDING
    next_pending = parse_next_pending(tasks_text)
    if next_pending is None:
        return TaskMonitorResult(
            project_root=project_root,
            monitor_timestamp=timestamp,
            next_pending=None,
            next_stage=None,
            worktree_status="unknown",
            run_state_exists=False,
            checkpoint_exists=False,
            ok=False,
            resume_required=False,
            rate_limit_blocked=False,
            real_execution_allowed=False,
            fail_reason="next_pending_missing",
            next_action="stop",
        )

    # 识别 NEXT_STAGE
    next_stage = parse_next_stage(tasks_text)
    if next_stage is None:
        return TaskMonitorResult(
            project_root=project_root,
            monitor_timestamp=timestamp,
            next_pending=next_pending,
            next_stage=None,
            worktree_status="unknown",
            run_state_exists=False,
            checkpoint_exists=False,
            ok=False,
            resume_required=False,
            rate_limit_blocked=False,
            real_execution_allowed=False,
            fail_reason="next_stage_missing",
            next_action="stop",
        )

    # 检查 git worktree 状态
    worktree_status = get_git_worktree_status(repo_root)
    if worktree_status == "dirty":
        return TaskMonitorResult(
            project_root=project_root,
            monitor_timestamp=timestamp,
            next_pending=next_pending,
            next_stage=next_stage,
            worktree_status="dirty",
            run_state_exists=False,
            checkpoint_exists=False,
            ok=False,
            resume_required=False,
            rate_limit_blocked=False,
            real_execution_allowed=False,
            fail_reason="dirty_workspace",
            next_action="stop",
        )

    # 检查 state 文件
    run_state_exists, checkpoint_exists = check_state_files(repo_root)

    # 判断 resume_required
    resume_required = checkpoint_exists

    # 当前 T155 阶段默认值
    rate_limit_blocked = False

    # Monitor 通过，real_execution_allowed 表示监控层允许进入后续安全门
    real_execution_allowed = True

    return TaskMonitorResult(
        project_root=project_root,
        monitor_timestamp=timestamp,
        next_pending=next_pending,
        next_stage=next_stage,
        worktree_status="clean",
        run_state_exists=run_state_exists,
        checkpoint_exists=checkpoint_exists,
        ok=True,
        resume_required=resume_required,
        rate_limit_blocked=rate_limit_blocked,
        real_execution_allowed=real_execution_allowed,
        fail_reason=None,
        next_action="continue_to_safety_gate",
    )


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def _format_cli_output(result: TaskMonitorResult) -> str:
    """格式化 CLI 输出。"""
    lines = []

    if result.ok:
        lines.append("MONITOR_RESULT=pass")
        lines.append(f"NEXT_PENDING={result.next_pending}")
        lines.append(f"NEXT_STAGE={result.next_stage}")
        lines.append(f"WORKTREE_STATUS={result.worktree_status}")
        lines.append(f"RESUME_REQUIRED={'yes' if result.resume_required else 'no'}")
        lines.append(f"RUN_STATE_EXISTS={'yes' if result.run_state_exists else 'no'}")
        lines.append(f"CHECKPOINT_EXISTS={'yes' if result.checkpoint_exists else 'no'}")
        lines.append(f"RATE_LIMIT_BLOCKED={'yes' if result.rate_limit_blocked else 'no'}")
        lines.append(f"REAL_EXECUTION_ALLOWED={'yes' if result.real_execution_allowed else 'no'}")
        lines.append(f"NEXT_ACTION={result.next_action}")
    else:
        lines.append("MONITOR_RESULT=fail")
        lines.append(f"FAIL_REASON={result.fail_reason}")
        lines.append(f"NEXT_ACTION={result.next_action}")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    # 确定项目根目录
    script_path = Path(__file__).resolve()
    root = script_path.parent.parent

    result = monitor_project(root)
    output = _format_cli_output(result)
    print(output)

    # 非 ok 时以非零退出码退出
    if not result.ok:
        sys.exit(1)
