"""Execution Report Writer — 统一生成连续执行报告。

遵循 docs/stage8-monitor-verify-report-architecture.md Section 7 设计。
只写报告文件，不修改 docs/tasks.md，不调用 gate check，不执行任务。
失败时生成最小报告。

T157 实现。
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class ExecutionReportData:
    """执行报告数据。"""

    # Task Info
    task_id: str
    stage: str
    mode: str
    project_root: str
    run_timestamp: str
    max_tasks: int

    # Monitor Result
    monitor_result: str  # pass / fail
    next_pending_before: str | None
    next_stage_before: str | None
    worktree_before: str  # clean / dirty

    # Safety Gate Result
    safety_result: str  # pass / fail / skipped
    real_execution_allowed: bool

    # Execution Result
    execution_status: str  # completed / skipped / sample
    files_created: list[str]
    files_modified: list[str]

    # Verify Result
    verify_result: str  # pass / fail / skipped
    check_result: str  # pass / fail

    # Rework Decision
    rework_required: bool
    rework_decision: str  # none / pending / skipped

    # Git Decision
    git_commit_allowed: bool
    git_push_allowed: bool
    auto_commit_triggered: bool
    auto_push_triggered: bool

    # Final Status
    final_worktree_status: str  # clean / dirty
    next_pending_after: str | None
    next_stage_after: str | None


@dataclass
class ExecutionReportWriteResult:
    """报告写入结果。"""

    ok: bool
    report_path: str
    task_id: str
    report_status: str  # written / failed
    fail_reason: str | None
    next_action: str  # review_report / stop


# ---------------------------------------------------------------------------
# 基础工具函数
# ---------------------------------------------------------------------------

def ensure_directory(path: Path) -> None:
    """确保目录存在。"""
    path.mkdir(parents=True, exist_ok=True)


def normalize_list(value: list[str] | str | None) -> list[str]:
    """将值规范化为字符串列表。"""
    if value is None:
        return []
    if isinstance(value, str):
        if not value.strip():
            return []
        return [v.strip() for v in value.split(",") if v.strip()]
    return list(value)


# ---------------------------------------------------------------------------
# 报告渲染
# ---------------------------------------------------------------------------

def render_execution_report(data: ExecutionReportData) -> str:
    """渲染执行报告为 Markdown。

    包含 8 个章节：
    1. Task Info
    2. Monitor Result
    3. Safety Gate Result
    4. Execution Result
    5. Verify Result
    6. Rework Decision
    7. Git Decision
    8. Final Status
    """
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    files_created_str = ", ".join(data.files_created) if data.files_created else "(none)"
    files_modified_str = ", ".join(data.files_modified) if data.files_modified else "(none)"

    lines: list[str] = []

    lines.append(f"# {data.task_id} Continuous Run Report")
    lines.append("")

    # ---- 1. Task Info ----
    lines.append("## 1. Task Info")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|-------|-------|")
    lines.append(f"| TASK | {data.task_id} |")
    lines.append(f"| RUN_TIMESTAMP | {now} |")
    lines.append(f"| MAX_TASKS | {data.max_tasks} |")
    lines.append(f"| STAGE | {data.stage} |")
    lines.append(f"| MODE | {data.mode} |")
    lines.append(f"| PROJECT_ROOT | {data.project_root} |")
    lines.append("")

    # ---- 2. Monitor Result ----
    lines.append("## 2. Monitor Result")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|-------|-------|")
    lines.append(f"| MONITOR_RESULT | {data.monitor_result} |")
    lines.append(f"| NEXT_PENDING_BEFORE | {data.next_pending_before or 'N/A'} |")
    lines.append(f"| NEXT_STAGE_BEFORE | {data.next_stage_before or 'N/A'} |")
    lines.append(f"| WORKTREE_BEFORE | {data.worktree_before} |")
    lines.append("")

    # ---- 3. Safety Gate Result ----
    lines.append("## 3. Safety Gate Result")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|-------|-------|")
    lines.append(f"| SAFETY_RESULT | {data.safety_result} |")
    lines.append(f"| REAL_EXECUTION_ALLOWED | {data.real_execution_allowed} |")
    lines.append("")

    # ---- 4. Execution Result ----
    lines.append("## 4. Execution Result")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|-------|-------|")
    lines.append(f"| EXECUTION_STATUS | {data.execution_status} |")
    lines.append(f"| FILES_CREATED | {files_created_str} |")
    lines.append(f"| FILES_MODIFIED | {files_modified_str} |")
    lines.append("")

    # ---- 5. Verify Result ----
    lines.append("## 5. Verify Result")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|-------|-------|")
    lines.append(f"| VERIFY_RESULT | {data.verify_result} |")
    lines.append(f"| CHECK_RESULT | {data.check_result} |")
    lines.append("")

    # ---- 6. Rework Decision ----
    lines.append("## 6. Rework Decision")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|-------|-------|")
    lines.append(f"| REWORK_REQUIRED | {data.rework_required} |")
    lines.append(f"| REWORK_DECISION | {data.rework_decision} |")
    lines.append("")

    # ---- 7. Git Decision ----
    lines.append("## 7. Git Decision")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|-------|-------|")
    lines.append(f"| GIT_COMMIT_ALLOWED | {data.git_commit_allowed} |")
    lines.append(f"| GIT_PUSH_ALLOWED | {data.git_push_allowed} |")
    lines.append(f"| AUTO_COMMIT_TRIGGERED | {data.auto_commit_triggered} |")
    lines.append(f"| AUTO_PUSH_TRIGGERED | {data.auto_push_triggered} |")
    lines.append("")

    # ---- 8. Final Status ----
    lines.append("## 8. Final Status")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|-------|-------|")
    lines.append(f"| FINAL_WORKTREE_STATUS | {data.final_worktree_status} |")
    lines.append(f"| NEXT_PENDING_AFTER | {data.next_pending_after or 'N/A'} |")
    lines.append(f"| NEXT_STAGE_AFTER | {data.next_stage_after or 'N/A'} |")
    lines.append("")

    # ---- 结构化状态行 ----
    lines.append("---")
    lines.append("")
    lines.append("```")
    lines.append(f"TASK={data.task_id}")
    lines.append(f"STAGE={data.stage}")
    lines.append(f"MODE={data.mode}")
    lines.append(f"MONITOR_RESULT={data.monitor_result}")
    lines.append(f"SAFETY_RESULT={data.safety_result}")
    lines.append(f"EXECUTION_STATUS={data.execution_status}")
    lines.append(f"VERIFY_RESULT={data.verify_result}")
    lines.append(f"CHECK_RESULT={data.check_result}")
    lines.append(f"REWORK_REQUIRED={'yes' if data.rework_required else 'no'}")
    lines.append(f"AUTO_COMMIT_TRIGGERED={'yes' if data.auto_commit_triggered else 'no'}")
    lines.append(f"AUTO_PUSH_TRIGGERED={'yes' if data.auto_push_triggered else 'no'}")
    lines.append(f"NEXT_PENDING={data.next_pending_after or 'N/A'}")
    lines.append(f"NEXT_STAGE={data.next_stage_after or 'N/A'}")
    lines.append("```")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 核心函数
# ---------------------------------------------------------------------------

def write_execution_report(
    repo_root: Path,
    data: ExecutionReportData,
) -> ExecutionReportWriteResult:
    """写入执行报告到 reports/continuous-runs/{task_id}-run-report.md。

    只写报告文件，不修改其他文件。
    """
    reports_dir = repo_root / "reports" / "continuous-runs"
    report_path = reports_dir / f"{data.task_id}-run-report.md"
    report_path_str = f"reports/continuous-runs/{data.task_id}-run-report.md"

    try:
        ensure_directory(reports_dir)

        content = render_execution_report(data)
        report_path.write_text(content, encoding="utf-8")

        return ExecutionReportWriteResult(
            ok=True,
            report_path=report_path_str,
            task_id=data.task_id,
            report_status="written",
            fail_reason=None,
            next_action="review_report",
        )
    except Exception as e:
        # 尝试生成最小报告
        try:
            ensure_directory(reports_dir)
            minimal = (
                f"# {data.task_id} Continuous Run Report (MINIMAL)\n\n"
                f"Report generation failed.\n\n"
                f"TASK={data.task_id}\n"
                f"CHECK_RESULT=fail\n"
                f"FAIL_REASON={e}\n"
            )
            report_path.write_text(minimal, encoding="utf-8")
        except Exception:
            pass

        return ExecutionReportWriteResult(
            ok=False,
            report_path=report_path_str,
            task_id=data.task_id,
            report_status="failed",
            fail_reason=str(e),
            next_action="stop",
        )


def build_sample_report_data(task_id: str, stage: str) -> ExecutionReportData:
    """构建 sample 报告数据，用于自检。"""
    return ExecutionReportData(
        task_id=task_id,
        stage=stage,
        mode="sample_report",
        project_root="E:/github_project/multi-agent-runner",
        run_timestamp=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        max_tasks=1,
        monitor_result="pass",
        next_pending_before=task_id,
        next_stage_before=stage,
        worktree_before="clean",
        safety_result="pass",
        real_execution_allowed=False,
        execution_status="sample",
        files_created=[],
        files_modified=[],
        verify_result="pass",
        check_result="pass",
        rework_required=False,
        rework_decision="none",
        git_commit_allowed=False,
        git_push_allowed=False,
        auto_commit_triggered=False,
        auto_push_triggered=False,
        final_worktree_status="clean",
        next_pending_after=_next_task_id(task_id),
        next_stage_after=stage,
    )


def _next_task_id(task_id: str) -> str:
    """推算下一个任务编号，如 T157 → T158。"""
    try:
        num = int(task_id[1:])
        return f"T{num + 1}"
    except (ValueError, IndexError):
        return "T???"


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def _parse_cli_args(args: list[str]) -> dict[str, str]:
    """解析 CLI 参数。"""
    parsed: dict[str, str] = {}
    i = 0
    while i < len(args):
        if args[i] == "--task" and i + 1 < len(args):
            parsed["task"] = args[i + 1]
            i += 2
        elif args[i] == "--stage" and i + 1 < len(args):
            parsed["stage"] = args[i + 1]
            i += 2
        else:
            i += 1
    return parsed


if __name__ == "__main__":
    parsed = _parse_cli_args(sys.argv[1:])

    task_id = parsed.get("task", "")
    stage = parsed.get("stage", "Stage 8")

    if not task_id:
        print("REPORT_WRITE_RESULT=error")
        print("FAIL_REASON=missing_task_id")
        print("Usage: python tools/execution_report_writer.py --task Txxx --stage \"Stage N\"")
        sys.exit(1)

    script_path = Path(__file__).resolve()
    root = script_path.parent.parent

    data = build_sample_report_data(task_id, stage)
    result = write_execution_report(root, data)

    if result.ok:
        print(f"REPORT_WRITE_RESULT=pass")
        print(f"TASK={result.task_id}")
        print(f"REPORT_STATUS={result.report_status}")
        print(f"REPORT_PATH={result.report_path}")
        print(f"NEXT_ACTION={result.next_action}")
    else:
        print(f"REPORT_WRITE_RESULT=fail")
        print(f"TASK={result.task_id}")
        print(f"FAIL_REASON={result.fail_reason}")
        print(f"NEXT_ACTION={result.next_action}")
        sys.exit(1)
