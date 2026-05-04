"""Rework Manager — 自动生成返工 prompt 或人工介入报告。

遵循 docs/rework-protocol.md 协议。
同一任务最多允许 MAX_REWORK_ROUNDS 次返工，超过后生成人工介入报告。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

MAX_REWORK_ROUNDS = 3


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class ReworkContext:
    """返工上下文。"""
    project_root: Path
    original_task_id: str
    rework_task_id: str
    rework_round: int
    max_rework_rounds: int
    original_task_block: str
    failure_sources: dict[str, str]
    allowed_files: list[str]
    blocked_files: list[str]


# ---------------------------------------------------------------------------
# 基础工具函数
# ---------------------------------------------------------------------------

def load_text_if_exists(path: str | Path) -> str:
    """如果文件存在则读取，否则返回空字符串。"""
    p = Path(path)
    if p.exists():
        return p.read_text(encoding="utf-8")
    return ""


def extract_task_block(tasks_content: str, task_id: str) -> str:
    """从子项目 tasks.md 中提取指定任务块。

    匹配格式：## <task-id> <标题> ... 直到下一个 ## 或文件末尾。
    """
    pattern = re.compile(
        rf"^## {re.escape(task_id)}\s.*$(.*?)(?=^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(tasks_content)
    if match:
        return match.group(0).strip()
    return ""


def should_generate_rework_prompt(rework_round: int) -> bool:
    """判断是否允许生成返工 prompt。"""
    return 1 <= rework_round <= MAX_REWORK_ROUNDS


def collect_failure_sources(project_root: Path, task_id: str) -> dict[str, str]:
    """收集与任务相关的 Tester / Behavior Tester / Reviewer / Main Agent 报告内容。"""
    sources = {}

    # Tester 报告
    tester_path = project_root / "reports" / "test" / f"{task_id}-test-report.md"
    tester_content = load_text_if_exists(tester_path)
    if tester_content:
        sources["tester"] = tester_content

    # Behavior Tester 报告
    behavior_path = project_root / "reports" / "test" / f"{task_id}-behavior-test-report.md"
    behavior_content = load_text_if_exists(behavior_path)
    if behavior_content:
        sources["behavior_tester"] = behavior_content

    # Reviewer 报告
    reviewer_path = project_root / "reports" / "review" / f"{task_id}-review-report.md"
    reviewer_content = load_text_if_exists(reviewer_path)
    if reviewer_content:
        sources["reviewer"] = reviewer_content

    # Main Decision 报告（优先 v2）
    main_v2_path = project_root / "reports" / "final" / f"{task_id}-main-decision-v2.md"
    main_path = project_root / "reports" / "final" / f"{task_id}-main-decision.md"
    main_content = load_text_if_exists(main_v2_path) or load_text_if_exists(main_path)
    if main_content:
        sources["main_agent"] = main_content

    return sources


# ---------------------------------------------------------------------------
# Prompt 生成
# ---------------------------------------------------------------------------

def build_rework_prompt(context: ReworkContext) -> str:
    """根据 ReworkContext 构造返工 prompt。"""
    fs = context.failure_sources

    # 失败来源摘要
    tester_summary = fs.get("tester", "（无 Tester 报告）")
    behavior_summary = fs.get("behavior_tester", "（无 Behavior Tester 报告）")
    reviewer_summary = fs.get("reviewer", "（无 Reviewer 报告）")
    main_summary = fs.get("main_agent", "（无 Main Agent 报告）")

    # 检查当前 Main Decision 是否为 COMPLETE
    is_complete = "COMPLETE" in main_summary

    allowed_lines = "\n".join(f"- {f}" for f in context.allowed_files)
    blocked_lines = "\n".join(f"- {f}" for f in context.blocked_files)

    important_note = ""
    if is_complete:
        important_note = """
## 重要说明

当前 {} 的现有 Main Decision 为 COMPLETE。
本文件用于验证自动生成返工 prompt 的能力。
真实返工时，应以 Tester / Reviewer / Main Agent 的失败项为准。
""".format(context.original_task_id)

    return f"""# Rework Prompt

你现在是 Developer Agent。

## 当前项目

{context.project_root}

## 原任务

{context.original_task_id} {context.original_task_block.split(chr(10))[0].replace('## ' + context.original_task_id, '').strip()}

## 返工任务

{context.rework_task_id} 修复 {context.original_task_id} 中发现的问题

## 返工次数限制

当前返工轮次：R{context.rework_round}
最大返工次数：{context.max_rework_rounds}

如果本轮返工后仍未通过 Tester / Reviewer / Main Agent，系统后续最多只允许继续返工到 R{context.max_rework_rounds}。
超过 R{context.max_rework_rounds} 后必须人工介入，不再自动生成新的返工 prompt。
{important_note}
## 返工目标

只修复失败项，不新增无关功能。

## 原任务内容

{context.original_task_block}

## 失败来源摘要

### Tester

{tester_summary}

### Behavior Tester

{behavior_summary}

### Reviewer

{reviewer_summary}

### Main Agent

{main_summary}

## 允许修改文件

{allowed_lines}

## 禁止修改文件

{blocked_lines}

## 必须生成完成证据

{context.project_root}/reports/dev/{context.rework_task_id}-dev-report.md

## 限制要求

1. 不修改主框架文件。
2. 不修改禁止文件。
3. 不扩大任务范围。
4. 不实现无关功能。
5. 只修复失败项。
6. 修改后写清楚修复内容和验证建议。
7. 返工完成后仍需重新执行 Tester / Reviewer / Main Agent。
8. 如果返工到 R{context.max_rework_rounds} 后仍未通过，必须停止自动返工并人工介入。

请开始返工。
"""


def save_rework_prompt(content: str, output_path: str | Path) -> Path:
    """保存返工 prompt。"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return output_path


# ---------------------------------------------------------------------------
# 人工介入报告
# ---------------------------------------------------------------------------

def save_manual_intervention_report(
    task_id: str,
    rework_round: int,
    failure_sources: dict[str, str],
    output_path: str | Path,
) -> Path:
    """超过最大返工次数时，生成人工介入报告。"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    tester_summary = failure_sources.get("tester", "（无 Tester 报告）")
    behavior_summary = failure_sources.get("behavior_tester", "（无 Behavior Tester 报告）")
    reviewer_summary = failure_sources.get("reviewer", "（无 Reviewer 报告）")
    main_summary = failure_sources.get("main_agent", "（无 Main Agent 报告）")

    report = f"""# {task_id} Manual Intervention Report

## Task

原始任务编号：{task_id}

## Rework Limit

最大返工次数：{MAX_REWORK_ROUNDS}
当前请求轮次：{rework_round}
是否允许继续自动返工：否

## Reason

已达到最大返工次数限制（{MAX_REWORK_ROUNDS}）。系统不再生成新的返工 prompt，避免无限返工循环。

## Failure Sources

### Tester

{tester_summary}

### Behavior Tester

{behavior_summary}

### Reviewer

{reviewer_summary}

### Main Agent

{main_summary}

## Suggested Manual Checks

- 检查失败项是否来自真实代码问题
- 检查 Tester 规则是否过于严格
- 检查 Reviewer 是否误判
- 检查 Main Agent 决策规则是否需要调整
- 人工确认后再决定是否创建新的修复任务

## Next Action

请人工介入，分析失败原因后再决定是否继续返工。
"""

    output_path.write_text(report, encoding="utf-8")
    return output_path


# ---------------------------------------------------------------------------
# 主函数
# ---------------------------------------------------------------------------

def generate_rework_prompt_for_game_task(
    task_id: str = "G004",
    rework_round: int = 1,
) -> tuple[Path, str]:
    """为 down-100-floors-game 生成返工 prompt 或人工介入报告。

    Args:
        task_id: 原始任务编号
        rework_round: 返工轮次（1-based）

    Returns:
        (文件路径, 结果类型)
        结果类型："rework_prompt" 或 "manual_intervention"
    """
    runner_root = Path(__file__).parent.parent
    game_project = runner_root / "projects" / "down-100-floors-game"

    # 收集失败来源
    failure_sources = collect_failure_sources(game_project, task_id)

    # 情况 B：超过最大返工次数
    if not should_generate_rework_prompt(rework_round):
        intervention_path = (
            game_project / "reports" / "final" / f"{task_id}-manual-intervention-report.md"
        )
        save_manual_intervention_report(
            task_id=task_id,
            rework_round=rework_round,
            failure_sources=failure_sources,
            output_path=intervention_path,
        )
        return intervention_path, "manual_intervention"

    # 情况 A：允许生成返工 prompt
    rework_task_id = f"{task_id}-R{rework_round}"

    # 读取原任务块
    tasks_file = game_project / "docs" / "tasks.md"
    tasks_content = load_text_if_exists(tasks_file)
    task_block = extract_task_block(tasks_content, task_id)
    if not task_block:
        task_block = f"（未找到 {task_id} 任务块）"

    # 读取 project.yaml 配置
    allowed_files = ["index.html", "style.css", "script.js", "docs/tasks.md", "reports/", "memory/"]
    blocked_files = ["requirement.md", "docs/future-platform-plan.md", "docs/character-system-plan.md", "project.yaml"]

    try:
        from tools.project_runner import load_project_runner_config
        config = load_project_runner_config(game_project)
        if config.loaded_from_yaml:
            allowed_files = config.allowed_files
            blocked_files = config.blocked_files
    except Exception:
        pass  # 回退默认值

    # 构造上下文
    context = ReworkContext(
        project_root=game_project,
        original_task_id=task_id,
        rework_task_id=rework_task_id,
        rework_round=rework_round,
        max_rework_rounds=MAX_REWORK_ROUNDS,
        original_task_block=task_block,
        failure_sources=failure_sources,
        allowed_files=allowed_files,
        blocked_files=blocked_files,
    )

    # 生成 prompt
    prompt_content = build_rework_prompt(context)
    prompt_path = game_project / "prompts" / "rework_prompt.md"
    save_rework_prompt(prompt_content, prompt_path)

    return prompt_path, "rework_prompt"
