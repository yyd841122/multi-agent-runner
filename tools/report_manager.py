"""报告管理器 — 生成和管理执行报告"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


def load_latest_claude_output(path: str | Path) -> str:
    """读取 reports/claude/latest-output.md。"""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"执行结果文件不存在：{path}")
    return p.read_text(encoding="utf-8")


def analyze_claude_output(content: str) -> dict:
    """根据 latest-output.md 内容分析执行结果。"""
    # 提取 Return Code
    returncode_match = re.search(r"## Return Code\s*\n\s*(\d+)", content)
    if returncode_match:
        returncode = int(returncode_match.group(1))
    else:
        returncode = -1

    success = returncode == 0

    # 提取 Stderr 段落用于限额检测（避免 stdout 代码内容误匹配）
    stderr_match = re.search(r"## Stderr\s*\n\s*(.*?)(?:\n## |\Z)", content, re.DOTALL)
    stderr_text = stderr_match.group(1) if stderr_match else ""

    is_rate_limited = bool(
        re.search(r"429|rate.limit|使用上限|Usage limit", stderr_text, re.IGNORECASE)
    )

    # 生成建议
    if success:
        message = "执行成功，建议可以完成当前任务。"
    elif is_rate_limited:
        message = "API 使用上限，请等待额度重置后再执行。"
    else:
        message = "执行失败，需要查看 latest-output.md 并修复。"

    return {
        "returncode": returncode,
        "success": success,
        "is_rate_limited": is_rate_limited,
        "message": message,
    }


def has_completion_evidence(task: dict, reports_dir: str | Path = "reports/dev") -> bool:
    """检查任务是否存在开发报告，作为最小完成证据。"""
    task_id = task.get("id", "")
    if not task_id:
        return False
    report_path = Path(reports_dir) / f"{task_id}-dev-report.md"
    return report_path.exists()


def save_execution_report(result: dict, output_dir: str | Path, task: dict | None = None) -> Path:
    """保存本次 Claude Code 执行详细报告。

    Args:
        result: run_claude_code 的返回结果
        output_dir: 保存目录 (reports/claude/history/)
        task: 当前任务信息 (可选)

    Returns:
        保存的文件路径
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"{timestamp}-claude-output.md"
    filepath = output_dir / filename

    task_id = task.get("id", "N/A") if task else "N/A"
    task_title = task.get("title", "N/A") if task else "N/A"
    task_role = task.get("role", "N/A") if task else "N/A"

    lines = [
        "# Claude Code Execution Report",
        "",
        "## Task",
        "",
        f"任务编号：{task_id}",
        f"任务名称：{task_title}",
        f"角色：{task_role}",
        "",
        "## Timing",
        "",
        f"开始时间：{result.get('started_at', 'N/A')}",
        f"结束时间：{result.get('ended_at', 'N/A')}",
        f"耗时：{result.get('duration_seconds', 0)} 秒",
        "",
        "## Result",
        "",
        f"退出码：{result.get('returncode', 'N/A')}",
        f"是否成功：{'是' if result.get('success') else '否'}",
        "",
        "## Stdout",
        "",
        result.get("stdout") or "(无输出)",
        "",
        "## Stderr",
        "",
        result.get("stderr") or "(无输出)",
        "",
    ]
    filepath.write_text("\n".join(lines), encoding="utf-8")
    return filepath


def append_run_log(
    log_path: str | Path,
    task: dict | None,
    result: dict,
    report_path: str | Path,
) -> None:
    """追加本次执行摘要到 reports/run-log.md。"""
    log_path = Path(log_path)

    task_id = task.get("id", "N/A") if task else "N/A"
    task_title = task.get("title", "N/A") if task else "N/A"

    success_mark = "成功" if result.get("success") else "失败"
    started_at = result.get("started_at", "N/A")
    duration = result.get("duration_seconds", 0)

    entry = (
        f"\n## {task_id} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"\n"
        f"- 任务：{task_title}\n"
        f"- 状态：{success_mark}\n"
        f"- 退出码：{result.get('returncode', 'N/A')}\n"
        f"- 开始时间：{started_at}\n"
        f"- 耗时：{duration} 秒\n"
        f"- 历史报告：{report_path}\n"
    )

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(entry)
