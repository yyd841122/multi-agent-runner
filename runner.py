"""multi-agent-runner 入口"""

# 在所有 import 之前加载 .env，确保 API Key 可用
try:
    from tools.env_loader import load_dotenv_file
    load_dotenv_file(".env", override=False)
except Exception:
    pass

import re
import sys
from pathlib import Path

from tools.task_manager import (
    load_tasks_file,
    parse_tasks,
    find_next_pending_task,
    find_current_in_progress_task,
    update_task_status,
    save_tasks_file,
)
from tools.workflow_manager import build_agent_prompt
from tools.claude_code_runner import load_prompt, run_claude_code
from tools.report_manager import (
    save_execution_report,
    append_run_log,
    load_latest_claude_output,
    analyze_claude_output,
    has_completion_evidence,
)
from tools.planner_runner import run_planner
from tools.main_agent import decide_next_action, save_main_decision
from tools.reviewer_runner import run_reviewer_for_game_task
from tools.project_runner import run_project_next
from tools.tester_runner import run_tester_for_game_task
from tools.tester_runner import run_behavior_tester_for_game_task
from tools.tester_runner import run_collision_tester_for_game_task
from tools.main_agent import run_combined_decision_for_game_task
from tools.main_agent import run_enhanced_combined_decision_for_game_task
from tools.rework_manager import generate_rework_prompt_for_game_task, MAX_REWORK_ROUNDS, prepare_rework_execution, execute_confirmed_rework, prepare_full_loop_resume
from tools.full_task_runner import run_project_task_full
from tools.continuous_task_planner import build_continuous_task_plan
from tools.continuous_task_planner import run_project_loop_dry_run
from tools.continuous_task_planner import validate_execute_loop_safety, run_project_loop_execute_stub
from tools.continuous_task_planner import run_project_loop_task_execution_adapter_dry_run
from tools.continuous_task_planner import run_project_loop_real_call_stub
from tools.continuous_task_planner import validate_real_call_safety
from tools.continuous_task_planner import run_project_loop_real_call_dry_run_executor
from tools.continuous_task_planner import run_project_loop_real_call_run_once_safety_shell
from tools.continuous_task_planner import parse_child_command_output
from tools.continuous_task_planner import evaluate_first_real_run_acceptance

PROJECT_ROOT = Path(__file__).parent
TASKS_FILE = PROJECT_ROOT / "docs" / "tasks.md"
PROMPT_FILE = PROJECT_ROOT / "prompts" / "current_prompt.md"
CLAUDE_OUTPUT_DIR = PROJECT_ROOT / "reports" / "claude"
CLAUDE_OUTPUT_FILE = CLAUDE_OUTPUT_DIR / "latest-output.md"
CLAUDE_HISTORY_DIR = CLAUDE_OUTPUT_DIR / "history"
RUN_LOG_FILE = PROJECT_ROOT / "reports" / "run-log.md"
DEV_REPORTS_DIR = PROJECT_ROOT / "reports" / "dev"
GAME_REQUIREMENT_FILE = PROJECT_ROOT / "projects" / "down-100-floors-game" / "requirement.md"

GAME_PROJECT_DIR = PROJECT_ROOT / "projects" / "down-100-floors-game"
GAME_TASKS_FILE = GAME_PROJECT_DIR / "docs" / "tasks.md"
GAME_REPORTS_DIR = GAME_PROJECT_DIR / "reports" / "dev"


def show_next_pending():
    """显示下一个 pending 任务。"""
    content = load_tasks_file(TASKS_FILE)
    tasks = parse_tasks(content)
    next_task = find_next_pending_task(tasks)

    if next_task:
        print("下一个 pending 任务：")
        print(f"任务编号：{next_task['id']}")
        print(f"任务名称：{next_task['title']}")
        print(f"角色：{next_task['role']}")
        print(f"状态：{next_task['status']}")
        print(f"目标：{next_task['goal']}")
    else:
        print("当前没有 pending 任务。")


def change_status(task_id: str, new_status: str):
    """修改指定任务的状态。"""
    content = load_tasks_file(TASKS_FILE)
    try:
        content = update_task_status(content, task_id, new_status)
    except ValueError as e:
        print(e)
        return
    save_tasks_file(TASKS_FILE, content)
    print("任务状态已更新：")
    print(f"任务编号：{task_id}")
    print(f"新状态：{new_status}")


def generate_prompt():
    """根据下一个 pending 任务生成提示词并写入文件。"""
    content = load_tasks_file(TASKS_FILE)
    tasks = parse_tasks(content)
    next_task = find_next_pending_task(tasks)

    if not next_task:
        print("当前没有 pending 任务，无法生成提示词。")
        return

    prompt = build_agent_prompt(next_task)
    PROMPT_FILE.write_text(prompt, encoding="utf-8")

    print("已生成当前任务提示词：")
    print(f"  {PROMPT_FILE}")
    print(f"任务编号：{next_task['id']}")
    print(f"任务名称：{next_task['title']}")
    print(f"角色：{next_task['role']}")


def save_latest_output(result: dict):
    """保存 Claude Code 最新输出。"""
    CLAUDE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Claude Code Execution Output",
        "",
        "## Return Code",
        "",
        str(result["returncode"]),
        "",
        "## Stdout",
        "",
        result["stdout"] if result["stdout"] else "(无输出)",
        "",
        "## Stderr",
        "",
        result["stderr"] if result["stderr"] else "(无输出)",
        "",
    ]

    if result.get("timed_out"):
        lines.extend([
            "## Timed Out",
            "",
            "True",
            "",
            "## Timeout Seconds",
            "",
            str(result.get("timeout_seconds", 600)),
            "",
        ])

    CLAUDE_OUTPUT_FILE.write_text("\n".join(lines), encoding="utf-8")


def get_current_task() -> dict | None:
    """获取当前 pending 任务信息（用于报告关联）。"""
    content = load_tasks_file(TASKS_FILE)
    tasks = parse_tasks(content)
    return find_next_pending_task(tasks)


def run_current():
    """读取 current_prompt.md 并调用 Claude Code 执行。"""
    if not PROMPT_FILE.exists():
        print("提示词文件不存在：prompts/current_prompt.md")
        print("请先运行：python runner.py generate-prompt")
        return

    prompt = load_prompt(PROMPT_FILE)
    print("正在调用 Claude Code...")
    print()

    # 获取当前任务信息
    task = get_current_task()

    # 执行 Claude Code
    result = run_claude_code(prompt)

    # 保存最新输出
    save_latest_output(result)

    # 保存历史报告
    history_path = save_execution_report(result, CLAUDE_HISTORY_DIR, task)

    # 追加运行日志
    append_run_log(RUN_LOG_FILE, task, result, history_path)

    # 输出结果摘要
    if result["success"]:
        print("已调用 Claude Code 执行当前提示词。")
    else:
        print("Claude Code 执行失败。")
    print(f"最新输出已保存：{CLAUDE_OUTPUT_FILE}")
    print(f"历史报告已保存：{history_path}")
    print(f"退出码：{result['returncode']}")
    print(f"耗时：{result['duration_seconds']} 秒")


def check_result():
    """读取最新执行结果并给出判断建议。"""
    try:
        content = load_latest_claude_output(CLAUDE_OUTPUT_FILE)
    except FileNotFoundError as e:
        print(e)
        print("请先运行：python runner.py run-current")
        return

    analysis = analyze_claude_output(content)

    print("执行结果判断：")
    print(f"退出码：{analysis['returncode']}")
    print(f"是否成功：{analysis['success']}")
    print(f"是否限额：{analysis['is_rate_limited']}")
    print(f"建议：{analysis['message']}")


def auto_complete_success():
    """如果最近执行结果成功且有完成证据，自动把当前 in_progress 任务标记为 done。"""
    # 找到当前 in_progress 任务
    content = load_tasks_file(TASKS_FILE)
    tasks = parse_tasks(content)
    task = find_current_in_progress_task(tasks)

    if not task:
        print("当前没有 in_progress 任务，无法自动完成。")
        return

    task_id = task["id"]

    # 读取最新执行结果
    try:
        output_content = load_latest_claude_output(CLAUDE_OUTPUT_FILE)
    except FileNotFoundError as e:
        print(e)
        print("请先运行：python runner.py run-current")
        return

    analysis = analyze_claude_output(output_content)

    if not analysis["success"]:
        print("执行结果未成功，不自动完成任务。")
        print(f"任务编号：{task_id}")
        print("请查看 reports/claude/latest-output.md")
        return

    if not has_completion_evidence(task, DEV_REPORTS_DIR):
        report_file = DEV_REPORTS_DIR / f"{task_id}-dev-report.md"
        print("Claude Code 执行成功，但缺少完成证据，不自动完成任务。")
        print(f"任务编号：{task_id}")
        print(f"缺少文件：{report_file}")
        print(f"任务状态：in_progress")
        return

    # 有完成证据，自动 done
    try:
        content = update_task_status(content, task_id, "done")
    except ValueError as e:
        print(e)
        return
    save_tasks_file(TASKS_FILE, content)
    print("执行结果成功，已自动完成任务：")
    print(f"任务编号：{task_id}")
    print(f"新状态：done")


def run_next():
    """单步自动闭环：生成提示词 → 标记 in_progress → 调用 Claude Code → 判断结果 → 成功且有证据则 done。"""
    # 1. 找到下一个 pending 任务
    content = load_tasks_file(TASKS_FILE)
    tasks = parse_tasks(content)
    task = find_next_pending_task(tasks)

    if not task:
        print("当前没有 pending 任务，无法执行 run-next。")
        return

    task_id = task["id"]
    task_title = task["title"]
    print(f"找到 pending 任务：{task_id} {task_title}")

    # 2. 标记为 in_progress
    print(f"正在将 {task_id} 标记为 in_progress...")
    try:
        content = update_task_status(content, task_id, "in_progress")
    except ValueError as e:
        print(e)
        return
    save_tasks_file(TASKS_FILE, content)

    # 3. 重新读取，获取最新任务信息
    content = load_tasks_file(TASKS_FILE)
    tasks = parse_tasks(content)
    task = None
    for t in tasks:
        if t["id"] == task_id:
            task = t
            break

    # 4. 生成 current_prompt.md
    print("正在生成提示词...")
    prompt = build_agent_prompt(task)
    PROMPT_FILE.write_text(prompt, encoding="utf-8")

    # 5. 调用 Claude Code
    print("正在调用 Claude Code...")
    print()
    result = run_claude_code(prompt)

    # 6. 保存执行结果和历史报告
    save_latest_output(result)
    history_path = save_execution_report(result, CLAUDE_HISTORY_DIR, task)
    append_run_log(RUN_LOG_FILE, task, result, history_path)

    # 7. 判断结果
    analysis = analyze_claude_output(
        CLAUDE_OUTPUT_FILE.read_text(encoding="utf-8")
    )

    # 8. 成功且有完成证据则 done，否则保持 in_progress
    if not analysis["success"]:
        print()
        print("run-next 单步执行失败：")
        print(f"任务编号：{task_id}")
        print(f"任务名称：{task_title}")
        print(f"执行结果：失败")
        print(f"任务状态：in_progress")
        print("请查看 reports/claude/latest-output.md")
        return

    if not has_completion_evidence(task, DEV_REPORTS_DIR):
        report_file = DEV_REPORTS_DIR / f"{task_id}-dev-report.md"
        print()
        print("run-next 单步执行完成（Claude Code 成功，但缺少完成证据）：")
        print(f"任务编号：{task_id}")
        print(f"任务名称：{task_title}")
        print(f"执行结果：成功")
        print(f"任务状态：in_progress")
        print(f"缺少文件：{report_file}")
        print("Claude Code 执行成功，但缺少完成证据，不自动标记 done。")
        return

    # 有完成证据，自动 done
    content = load_tasks_file(TASKS_FILE)
    try:
        content = update_task_status(content, task_id, "done")
    except ValueError as e:
        print(e)
        return
    save_tasks_file(TASKS_FILE, content)

    print()
    print("run-next 单步执行完成：")
    print(f"任务编号：{task_id}")
    print(f"任务名称：{task_title}")
    print(f"执行结果：成功")
    print(f"任务状态：done")


def retry_current():
    """重新执行当前 in_progress 任务：重新生成 prompt → 调用 Claude Code → 判断结果 → 有证据则 done。"""
    # 1. 找到当前 in_progress 任务
    content = load_tasks_file(TASKS_FILE)
    tasks = parse_tasks(content)
    task = find_current_in_progress_task(tasks)

    if not task:
        print("当前没有 in_progress 任务，无法执行 retry-current。")
        return

    task_id = task["id"]
    task_title = task["title"]
    print(f"找到 in_progress 任务：{task_id} {task_title}")

    # 2. 重新生成 current_prompt.md
    print("正在重新生成提示词...")
    prompt = build_agent_prompt(task)
    PROMPT_FILE.write_text(prompt, encoding="utf-8")

    # 3. 调用 Claude Code
    print("正在调用 Claude Code...")
    print()
    result = run_claude_code(prompt)

    # 4. 保存执行结果和历史报告
    save_latest_output(result)
    history_path = save_execution_report(result, CLAUDE_HISTORY_DIR, task)
    append_run_log(RUN_LOG_FILE, task, result, history_path)

    # 5. 判断结果
    analysis = analyze_claude_output(
        CLAUDE_OUTPUT_FILE.read_text(encoding="utf-8")
    )

    # 6. 根据结果和完成证据决定状态
    if not analysis["success"]:
        print()
        print("retry-current 执行失败：")
        print(f"任务编号：{task_id}")
        print(f"执行结果：失败")
        print(f"任务状态：in_progress")
        print("请查看 reports/claude/latest-output.md")
        return

    if not has_completion_evidence(task, DEV_REPORTS_DIR):
        report_file = DEV_REPORTS_DIR / f"{task_id}-dev-report.md"
        print()
        print("retry-current 执行完成（Claude Code 成功，但缺少完成证据）：")
        print(f"任务编号：{task_id}")
        print(f"执行结果：成功")
        print(f"任务状态：in_progress")
        print(f"缺少文件：{report_file}")
        return

    # 有完成证据，自动 done
    content = load_tasks_file(TASKS_FILE)
    try:
        content = update_task_status(content, task_id, "done")
    except ValueError as e:
        print(e)
        return
    save_tasks_file(TASKS_FILE, content)

    print()
    print("retry-current 执行完成：")
    print(f"任务编号：{task_id}")
    print(f"执行结果：成功")
    print(f"完成证据：存在")
    print(f"任务状态：done")


def _execute_one_task(content: str) -> tuple[str, str]:
    """执行单个 pending 任务的单步闭环。

    Args:
        content: 当前 tasks.md 文件内容

    Returns:
        (status, message) 元组：
        - status: "done" / "success_no_evidence" / "failed"
        - message: 描述信息
    """
    tasks = parse_tasks(content)
    task = find_next_pending_task(tasks)

    if not task:
        return "no_pending", "没有 pending 任务"

    task_id = task["id"]
    task_title = task["title"]

    print(f"\n{'=' * 60}")
    print(f"开始执行任务：{task_id} {task_title}")
    print(f"{'=' * 60}")

    # 标记为 in_progress
    print(f"  正在将 {task_id} 标记为 in_progress...")
    try:
        content = update_task_status(content, task_id, "in_progress")
    except ValueError as e:
        return "failed", str(e)
    save_tasks_file(TASKS_FILE, content)

    # 重新读取最新任务信息
    content = load_tasks_file(TASKS_FILE)
    tasks = parse_tasks(content)
    task = None
    for t in tasks:
        if t["id"] == task_id:
            task = t
            break

    # 生成提示词
    print("  正在生成提示词...")
    prompt = build_agent_prompt(task)
    PROMPT_FILE.write_text(prompt, encoding="utf-8")

    # 调用 Claude Code
    print("  正在调用 Claude Code...")
    result = run_claude_code(prompt)

    # 保存执行结果和历史报告
    save_latest_output(result)
    history_path = save_execution_report(result, CLAUDE_HISTORY_DIR, task)
    append_run_log(RUN_LOG_FILE, task, result, history_path)

    # 判断结果
    analysis = analyze_claude_output(
        CLAUDE_OUTPUT_FILE.read_text(encoding="utf-8")
    )

    # 失败
    if not analysis["success"]:
        print(f"  ✗ 任务 {task_id} 执行失败（退出码 {analysis['returncode']}）")
        return "failed", f"任务 {task_id} 执行失败"

    # 成功但缺少完成证据
    if not has_completion_evidence(task, DEV_REPORTS_DIR):
        report_file = DEV_REPORTS_DIR / f"{task_id}-dev-report.md"
        print(f"  ✗ 任务 {task_id} 执行成功但缺少完成证据：{report_file}")
        return "success_no_evidence", f"任务 {task_id} 缺少完成证据：{report_file}"

    # 成功且有完成证据，标记 done
    content = load_tasks_file(TASKS_FILE)
    try:
        content = update_task_status(content, task_id, "done")
    except ValueError as e:
        return "failed", str(e)
    save_tasks_file(TASKS_FILE, content)

    print(f"  ✓ 任务 {task_id} 已完成（done）")
    return "done", f"任务 {task_id} 完成"


def run_loop(max_rounds: int = 10):
    """多任务自动执行循环：连续执行 pending 任务，直到没有 pending 任务或达到最大轮数。"""
    print(f"开始多任务自动执行循环（最大轮数：{max_rounds}）")
    print()

    completed_tasks = []
    stop_reason = None

    for round_num in range(1, max_rounds + 1):
        print(f"--- 第 {round_num}/{max_rounds} 轮 ---")

        content = load_tasks_file(TASKS_FILE)
        status, message = _execute_one_task(content)

        if status == "no_pending":
            stop_reason = "所有 pending 任务已执行完毕"
            break
        elif status == "done":
            completed_tasks.append(message)
            # 继续下一轮
        elif status == "success_no_evidence":
            stop_reason = f"任务执行成功但缺少完成证据，循环停止。{message}"
            break
        elif status == "failed":
            stop_reason = f"任务执行失败，循环停止。{message}"
            break

    else:
        # for 循环正常结束（达到最大轮数）
        stop_reason = f"已达到最大轮数限制（{max_rounds} 轮）"

    # 打印汇总
    print()
    print("=" * 60)
    print("多任务执行循环结束")
    print("=" * 60)
    print(f"停止原因：{stop_reason}")
    print(f"已完成任务数：{len(completed_tasks)}")
    if completed_tasks:
        for i, msg in enumerate(completed_tasks, 1):
            print(f"  {i}. {msg}")
    print()


def main_decide():
    """Main Agent 决策：根据任务状态、执行结果和完成证据决定下一步动作。"""
    # 1. 读取任务
    content = load_tasks_file(TASKS_FILE)
    tasks = parse_tasks(content)

    # 2. 尝试读取最近执行结果
    latest_result = None
    try:
        output_content = load_latest_claude_output(CLAUDE_OUTPUT_FILE)
        latest_result = analyze_claude_output(output_content)
    except FileNotFoundError:
        pass

    # 3. 检查当前 in_progress 任务的完成证据
    evidence_exists = None
    in_progress_task = find_current_in_progress_task(tasks)
    if in_progress_task:
        evidence_exists = has_completion_evidence(in_progress_task, DEV_REPORTS_DIR)

    # 4. 决策
    decision = decide_next_action(tasks, latest_result, evidence_exists)

    # 5. 保存决策报告
    report_path = save_main_decision(decision)

    # 6. 输出结果
    print("Main Agent 决策：")
    print(f"  Decision：{decision.decision}")
    if decision.task_id:
        print(f"  任务编号：{decision.task_id}")
    print(f"  原因：{decision.reason}")
    if decision.next_command:
        print(f"  建议命令：{decision.next_command}")
    if decision.blocked:
        print("  ** 被阻塞 **")
    print(f"  报告已保存：{report_path}")


# ---------------------------------------------------------------------------
# 通用 project runner 入口
# ---------------------------------------------------------------------------

def _handle_run_project_next(project_path: str):
    """处理 run-project-next 命令，格式化输出结果。"""
    result = run_project_next(project_path)

    print()

    if result["task_id"] is None:
        if not result["success"]:
            print(f"run-project-next 执行失败：")
            print(f"  {result['message']}")
        else:
            print(f"run-project-next：")
            print(f"  {result['message']}")
        return

    task_id = result["task_id"]
    task_title = result["task_title"]

    if not result["success"]:
        if result.get("timed_out"):
            timeout_secs = result.get("timeout_seconds", 600)
            print(f"run-project-next 执行失败：")
            print(f"项目路径：{result['project_path']}")
            print(f"任务编号：{task_id}")
            print(f"任务名称：{task_title}")
            print(f"执行结果：超时")
            print(f"任务状态：in_progress")
            print(f"错误原因：Claude Code execution timed out after {timeout_secs} seconds.")
            print(f"请查看 reports/claude/latest-output.md")
            print(f"建议：不要重复盲目执行，先检查文件状态和完成证据。")
        else:
            print(f"run-project-next 执行失败：")
            print(f"项目路径：{result['project_path']}")
            print(f"任务编号：{task_id}")
            print(f"任务名称：{task_title}")
            print(f"执行结果：失败")
            print(f"任务状态：{result['task_status']}")
            print(f"请查看 reports/claude/latest-output.md")
    elif not result["evidence_found"]:
        print(f"run-project-next 执行完成（Claude Code 成功，但缺少完成证据）：")
        print(f"项目路径：{result['project_path']}")
        print(f"任务编号：{task_id}")
        print(f"任务名称：{task_title}")
        print(f"执行结果：成功")
        print(f"任务状态：{result['task_status']}")
        print(f"缺少文件：{result['message'].split('：')[-1] if '：' in result['message'] else '完成证据文件'}")
    elif result.get("completed_with_model_error"):
        print(f"run-project-next 执行完成（完成证据存在，但模型返回错误）：")
        print(f"项目路径：{result['project_path']}")
        print(f"任务编号：{task_id}")
        print(f"任务名称：{task_title}")
        print(f"模型返回码：{result.get('model_returncode', 'N/A')}")
        print(f"任务状态：done")
        print(f"完成证据：存在")
        print(f"说明：Claude Code 返回错误，但开发报告存在且任务已标记 done。")
        print(f"建议：请人工确认文件内容后继续执行 Tester。")
    else:
        print(f"run-project-next 执行完成：")
        print(f"项目路径：{result['project_path']}")
        print(f"任务编号：{task_id}")
        print(f"任务名称：{task_title}")
        print(f"执行结果：成功")
        print(f"完成证据：存在")
        print(f"任务状态：done")


# ---------------------------------------------------------------------------
# 游戏项目任务解析（G 前缀，复用 task_manager 的 load/save）
# ---------------------------------------------------------------------------

def parse_game_tasks(content: str) -> list[dict]:
    """解析游戏项目 tasks.md（G 前缀任务）。"""
    pattern = re.compile(r"^## (G\d+)\s+(.+)$", re.MULTILINE)
    matches = list(pattern.finditer(content))

    tasks: list[dict] = []
    for i, match in enumerate(matches):
        task_id = match.group(1)
        title = match.group(2).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        raw = content[start:end].strip()

        status = _extract_game_field(raw, "状态")
        role = _extract_game_field(raw, "角色")
        goal = _extract_game_field(raw, "目标")

        tasks.append({
            "id": task_id,
            "title": title,
            "status": status,
            "role": role,
            "goal": goal,
            "raw": raw,
        })
    return tasks


def _extract_game_field(text: str, field_name: str) -> str:
    """从游戏任务正文中提取字段值。"""
    pattern = re.compile(rf"^{re.escape(field_name)}[：:]\s*(.+)$", re.MULTILINE)
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def find_next_pending_game_task(tasks: list[dict]) -> dict | None:
    """找到游戏项目中第一个 pending 任务。"""
    for task in tasks:
        if task["status"] == "pending":
            return task
    return None


def update_game_task_status(content: str, task_id: str, new_status: str) -> str:
    """更新游戏项目任务状态。"""
    pattern = re.compile(
        rf"(^## {re.escape(task_id)}\s[^\n]*\n+状态[：:]\s*)(\S+)",
        re.MULTILINE,
    )
    match = pattern.search(content)
    if not match:
        raise ValueError(f"未找到游戏任务：{task_id}")
    return content[: match.start(2)] + new_status + content[match.end(2):]


def build_game_task_prompt(task: dict) -> str:
    """为游戏项目任务生成 Claude Code 提示词。"""
    task_id = task.get("id", "")
    title = task.get("title", "")
    goal = task.get("goal", "")
    raw = task.get("raw", "")

    return f"""# {task_id}：{title}

你现在是 Developer Agent。

## 当前项目

projects/down-100-floors-game

## 当前任务

{task_id} {title}

## 任务目标

{goal}

## 任务原始内容

{raw}

## 允许修改文件

- projects/down-100-floors-game/index.html
- projects/down-100-floors-game/style.css
- projects/down-100-floors-game/script.js
- projects/down-100-floors-game/reports/dev/{task_id}-dev-report.md

## 需要实现

1. 游戏标题：Down 100 Floors Game Demo
2. 游戏区域容器
3. 开始按钮
4. 层数或分数显示
5. 游戏状态提示
6. 基础说明文字
7. 页面样式简单清晰

## 不允许实现

- 玩家移动
- 平台生成
- 重力
- 碰撞检测
- 游戏结束逻辑
- 角色技能
- 微信小游戏发布
- 抖音小游戏发布
- 登录、排行、支付、广告

## 完成证据

必须创建：

projects/down-100-floors-game/reports/dev/{task_id}-dev-report.md

报告内容包含：

- 任务编号
- 修改文件列表
- 完成内容
- 验收标准自查
- 是否完成

请直接修改文件，不要只输出建议代码。


请开始执行 {task_id}。"""


def run_game_next():
    """单步自动执行小游戏项目的下一个 pending 任务。"""
    # 1. 读取游戏任务
    content = load_tasks_file(GAME_TASKS_FILE)
    tasks = parse_game_tasks(content)
    task = find_next_pending_game_task(tasks)

    if not task:
        print("小游戏项目没有 pending 任务。")
        return

    task_id = task["id"]
    task_title = task["title"]
    print(f"找到小游戏 pending 任务：{task_id} {task_title}")

    # 2. 标记为 in_progress
    print(f"正在将 {task_id} 标记为 in_progress...")
    content = update_game_task_status(content, task_id, "in_progress")
    save_tasks_file(GAME_TASKS_FILE, content)

    # 3. 生成 prompt
    print("正在生成提示词...")
    prompt = build_game_task_prompt(task)

    game_prompts_dir = GAME_PROJECT_DIR / "prompts"
    game_prompts_dir.mkdir(parents=True, exist_ok=True)
    (game_prompts_dir / "current_prompt.md").write_text(prompt, encoding="utf-8")

    # 4. 调用 Claude Code
    print("正在调用 Claude Code...")
    print()
    result = run_claude_code(prompt)

    # 5. 保存执行结果到主项目
    save_latest_output(result)
    history_path = save_execution_report(result, CLAUDE_HISTORY_DIR, task)
    append_run_log(RUN_LOG_FILE, task, result, history_path)

    # 6. 判断结果
    analysis = analyze_claude_output(
        CLAUDE_OUTPUT_FILE.read_text(encoding="utf-8")
    )

    if not analysis["success"]:
        print()
        print(f"run-game-next 执行失败：")
        print(f"任务编号：{task_id}")
        print(f"任务名称：{task_title}")
        print(f"执行结果：失败")
        print(f"任务状态：in_progress")
        print("请查看 reports/claude/latest-output.md")
        return

    # 7. 检查完成证据
    evidence_path = GAME_REPORTS_DIR / f"{task_id}-dev-report.md"
    if not evidence_path.exists():
        print()
        print(f"run-game-next 执行完成（Claude Code 成功，但缺少完成证据）：")
        print(f"任务编号：{task_id}")
        print(f"任务名称：{task_title}")
        print(f"执行结果：成功")
        print(f"任务状态：in_progress")
        print(f"缺少文件：{evidence_path}")
        return

    # 8. 有完成证据，标记 done
    content = load_tasks_file(GAME_TASKS_FILE)
    content = update_game_task_status(content, task_id, "done")
    save_tasks_file(GAME_TASKS_FILE, content)

    print()
    print(f"run-game-next 执行完成：")
    print(f"任务编号：{task_id}")
    print(f"任务名称：{task_title}")
    print(f"执行结果：成功")
    print(f"完成证据：存在")
    print(f"任务状态：done")


def main():
    print("=" * 50)
    print("项目名称：multi-agent-runner")
    print("当前阶段：MVP 骨架初始化")
    print("runner initialized")
    print("=" * 50)
    print()

    args = sys.argv[1:]

    if not args:
        show_next_pending()
    elif args[0] == "complete" and len(args) >= 2:
        change_status(args[1], "done")
    elif args[0] == "start" and len(args) >= 2:
        change_status(args[1], "in_progress")
    elif args[0] == "generate-prompt":
        generate_prompt()
    elif args[0] == "run-current":
        run_current()
    elif args[0] == "check-result":
        check_result()
    elif args[0] == "auto-complete-success":
        auto_complete_success()
    elif args[0] == "run-next":
        run_next()
    elif args[0] == "retry-current":
        retry_current()
    elif args[0] == "run-loop":
        max_rounds = int(args[1]) if len(args) >= 2 else 10
        run_loop(max_rounds)
    elif args[0] == "plan-project":
        run_planner(GAME_REQUIREMENT_FILE)
    elif args[0] == "main-decide":
        main_decide()
    elif args[0] == "run-game-next":
        run_game_next()
    elif args[0] == "run-project-next":
        # 支持 --project <path> 或直接 <path>
        if len(args) >= 3 and args[1] == "--project":
            project_path = args[2]
        elif len(args) >= 2 and not args[1].startswith("-"):
            project_path = args[1]
        else:
            print("请提供项目路径：")
            print("  python runner.py run-project-next --project projects/down-100-floors-game")
            return
        _handle_run_project_next(project_path)
    elif args[0] == "review-game-task":
        task_id = args[1] if len(args) >= 2 else "G002"
        report_path, parsed = run_reviewer_for_game_task(task_id)
        print()
        print("Reviewer 审查报告已生成：")
        print(f"  {report_path}")
        print()
        if parsed and parsed.success:
            print("结构化审查结果：")
            print(f"  Status：{parsed.status}")
            print(f"  Decision：{parsed.decision}")
            print(f"  Issues：{len(parsed.issues) if parsed.issues else 0}")
        elif parsed:
            print(f"结构化审查结果解析失败：{parsed.error}")
        else:
            print("结构化审查结果解析失败：模型调用未成功")
    elif args[0] == "test-game-task":
        task_id = args[1] if len(args) >= 2 else "G003"
        report_path, result = run_tester_for_game_task(task_id)
        print()
        print("Tester 测试报告已生成：")
        print(f"  {report_path}")
        print()
        print("测试结果：")
        print(f"  Status：{result.status}")
        print(f"  Result：{result.result}")
        print(f"  Passed：{result.passed_count}")
        print(f"  Failed：{result.failed_count}")
    elif args[0] == "decide-game-task":
        task_id = args[1] if len(args) >= 2 else "G003"
        report_path, decision = run_combined_decision_for_game_task(task_id)
        print()
        print("Main Agent 综合决策报告已生成：")
        print(f"  {report_path}")
        print()
        print("综合决策：")
        print(f"  Decision：{decision.decision}")
        print(f"  Reason：{decision.reason}")
        print(f"  Next Action：{decision.next_action}")
    elif args[0] == "test-game-behavior":
        task_id = args[1] if len(args) >= 2 else "G004"
        report_path, result = run_behavior_tester_for_game_task(task_id)
        print()
        print("Tester 行为测试报告已生成：")
        print(f"  {report_path}")
        print()
        print("行为测试结果：")
        print(f"  Status：{result.status}")
        print(f"  Result：{result.result}")
        print(f"  Passed：{result.passed_count}")
        print(f"  Failed：{result.failed_count}")
    elif args[0] == "test-game-collision":
        task_id = args[1] if len(args) >= 2 else "G007"
        report_path, result = run_collision_tester_for_game_task(task_id)
        print()
        print("Tester 碰撞测试报告已生成：")
        print(f"  {report_path}")
        print()
        print("碰撞测试结果：")
        print(f"  Status：{result.status}")
        print(f"  Result：{result.result}")
        print(f"  Passed：{result.passed_count}")
        print(f"  Failed：{result.failed_count}")
    elif args[0] == "decide-game-task-v2":
        task_id = args[1] if len(args) >= 2 else "G004"
        report_path, decision = run_enhanced_combined_decision_for_game_task(task_id)
        print()
        print("Main Agent 增强综合决策报告已生成：")
        print(f"  {report_path}")
        print()
        print("增强综合决策：")
        print(f"  Decision：{decision.decision}")
        print(f"  Reason：{decision.reason}")
        print(f"  Next Action：{decision.next_action}")
    elif args[0] == "run-project-task-full":
        # 解析 --project 和 --task 参数
        project_path = None
        task_id = None
        i = 1
        while i < len(args):
            if args[i] == "--project" and i + 1 < len(args):
                project_path = args[i + 1]
                i += 2
            elif args[i] == "--task" and i + 1 < len(args):
                task_id = args[i + 1]
                i += 2
            else:
                i += 1

        if not project_path or not task_id:
            print("缺少参数：--project 或 --task")
            print("用法：python runner.py run-project-task-full --project <project-path> --task <task-id>")
            return

        loop_result = run_project_task_full(project_path, task_id)

        print()
        print("run-project-task-full 执行完成：")
        print(f"项目路径：{loop_result.project_path}")
        print(f"任务编号：{loop_result.task_id}")
        print(f"最终状态：{loop_result.final_status}")
        print()
        print("阶段结果：")
        for step in loop_result.steps:
            status_text = step.status
            print(f"  - {step.name}：{status_text}")
        print()
        if loop_result.full_loop_report_path:
            print(f"完整闭环报告：{loop_result.full_loop_report_path}")
        if loop_result.next_action:
            print(f"下一步：{loop_result.next_action}")
    elif args[0] == "generate-rework-prompt":
        task_id = args[1] if len(args) >= 2 else "G004"
        rework_round = int(args[2]) if len(args) >= 3 else 1
        report_path, result_type = generate_rework_prompt_for_game_task(task_id, rework_round)
        print()
        if result_type == "rework_prompt":
            print("返工 prompt 已生成：")
            print(f"  {report_path}")
            print()
            print(f"返工任务编号：{task_id}-R{rework_round}")
            print(f"当前返工轮次：{rework_round} / {MAX_REWORK_ROUNDS}")
            print("注意：本命令只生成 prompt，不执行返工。")
        else:
            print(f"已达到最大返工次数限制：{MAX_REWORK_ROUNDS}")
            print("不再生成新的返工 prompt。")
            print()
            print("人工介入报告已生成：")
            print(f"  {report_path}")
            print()
            print("请人工检查失败原因后再决定下一步。")
    elif args[0] == "execute-rework":
        # 解析参数
        project_path = None
        task_id = None
        round_number = None
        confirm_text = None
        dry_run = True
        real_execution = False
        resume = False
        i = 1
        while i < len(args):
            if args[i] == "--project" and i + 1 < len(args):
                project_path = args[i + 1]
                i += 2
            elif args[i] == "--task" and i + 1 < len(args):
                task_id = args[i + 1]
                i += 2
            elif args[i] == "--round" and i + 1 < len(args):
                round_number = int(args[i + 1])
                i += 2
            elif args[i] == "--confirm" and i + 1 < len(args):
                confirm_text = args[i + 1]
                i += 2
            elif args[i] == "--no-dry-run":
                dry_run = False
                i += 1
            elif args[i] == "--real-execution":
                real_execution = True
                i += 1
            elif args[i] == "--resume":
                resume = True
                i += 1
            else:
                i += 1

        if not project_path or not task_id or round_number is None:
            print("缺少参数：--project / --task / --round")
            print("用法：python runner.py execute-rework --project <path> --task <id> --round <n> [--confirm \"...\"] [--real-execution] [--resume]")
            return

        if resume:
            # T056.5 full loop resume 分支
            # --resume 必须配合 --real-execution
            if not real_execution:
                print("错误：--resume 必须配合 --real-execution 使用")
                return
            # --resume 必须配合 --confirm
            if not confirm_text:
                print("错误：--resume 必须配合 --confirm 使用")
                return

            result = prepare_full_loop_resume(
                project_root=Path(project_path),
                task_id=task_id,
                round_number=round_number,
                confirm=confirm_text,
                real_execution=True,
            )

            print()
            print(f"resume_requested={result.resume_requested}")
            print(f"resume_allowed={result.resume_allowed}")
            print(f"resume_target={result.resume_target}")
            print(f"resume_reason={result.resume_reason}")
            print(f"loop_status={result.loop_status}")
            print(f"EXECUTION_MODE={result.execution_mode}")
            print(f"candidate_status={result.candidate_status}")
            print(f"execution_allowed={result.execution_allowed}")
            print(f"real_execution_performed={result.real_execution_performed}")
            print(f"CHECK_RESULT={result.safety_status}")
            print(f"Message：{result.message}")
            print(f"NEXT_ACTION={result.next_action}")
        elif real_execution:
            # T056.2 confirmed rework execution 分支
            result = execute_confirmed_rework(
                project_root=Path(project_path),
                task_id=task_id,
                round_number=round_number,
                confirm=confirm_text,
                real_execution=True,
            )

            print()
            print(f"execution_allowed={result.execution_allowed}")
            print(f"real_execution_requested={result.real_execution_requested}")
            print(f"real_execution_performed={result.real_execution_performed}")
            print(f"EXECUTION_MODE={result.execution_mode}")
            print(f"CHECK_RESULT={result.safety_status}")
            print(f"confirmation_status={result.confirmation_status}")
            print(f"round_status={result.round_status}")
            print(f"Message：{result.message}")
            print(f"NEXT_ACTION={result.next_action}")
        else:
            # T056 dry-run safety check（保持原有行为）
            result = prepare_rework_execution(
                project_root=Path(project_path),
                task_id=task_id,
                round_number=round_number,
                confirm=confirm_text,
                dry_run=dry_run,
            )

            print()
            if result.status == "BLOCKED":
                print("execute-rework 被阻止：")
                print(f"Status：BLOCKED")
                print(f"Reason：{result.reason}")
                print(f"Next Action：请使用严格确认格式")
            elif result.status == "MANUAL_INTERVENTION":
                print("execute-rework 进入人工介入：")
                print(f"Status：MANUAL_INTERVENTION")
                print(f"Reason：{result.reason}")
                print(f"Next Action：请人工检查失败原因")
            elif result.status == "READY_TO_EXECUTE":
                print("execute-rework 检查通过：")
                print(f"Status：READY_TO_EXECUTE")
                print(f"Dry Run：{'True' if dry_run else 'False'}")
                print(f"Reason：{result.reason}")

            if result.report_path:
                print(f"Report：{result.report_path}")
    elif args[0] == "parse-child-output-dry-run":
        # T086: child command output parser dry-run
        sample_type = "pass"
        if len(args) >= 3 and args[1] == "--sample":
            sample_type = args[2]
        elif len(args) >= 2 and not args[1].startswith("-"):
            sample_type = args[1]

        # 内置样例 stdout
        _SAMPLE_PASS = (
            "TASK_ID=G008\n"
            "CHECK_RESULT=pass\n"
            "TASK_STATUS=done\n"
            "NEXT_PENDING=G009\n"
            "REAL_TASK_EXECUTION=yes\n"
            "CLAUDE_CODE_CALLED=yes\n"
            "BUSINESS_CODE_CHANGED=yes\n"
            "WORKTREE_STATUS=dirty_business_code\n"
            "REPORT_PATHS=reports/dev/G008-dev-report.md,reports/test/G008-test-report.md\n"
            "FINAL_STATUS=COMPLETE\n"
            "FULL_LOOP_REPORT=reports/G008-full-loop-report.md\n"
        )
        _SAMPLE_FAIL = (
            "TASK_ID=G008\n"
            "CHECK_RESULT=fail\n"
            "TASK_STATUS=failed\n"
            "NEXT_PENDING=\n"
            "REAL_TASK_EXECUTION=yes\n"
            "CLAUDE_CODE_CALLED=yes\n"
            "BUSINESS_CODE_CHANGED=no\n"
            "WORKTREE_STATUS=clean\n"
            "REPORT_PATHS=reports/dev/G008-dev-report.md\n"
            "FINAL_STATUS=FAILED\n"
            "FULL_LOOP_REPORT=reports/G008-full-loop-report.md\n"
        )
        _SAMPLE_MISSING_CHECK_RESULT = (
            "TASK_ID=G008\n"
            "TASK_STATUS=done\n"
            "REAL_TASK_EXECUTION=yes\n"
            "CLAUDE_CODE_CALLED=yes\n"
            "BUSINESS_CODE_CHANGED=no\n"
            "WORKTREE_STATUS=clean\n"
        )
        _SAMPLE_MISSING_OPTIONAL = (
            "TASK_ID=G008\n"
            "CHECK_RESULT=pass\n"
            "REAL_TASK_EXECUTION=yes\n"
        )
        _SAMPLE_WITH_LOGS = (
            "[INFO] Starting task execution...\n"
            "[DEBUG] Validating preconditions...\n"
            "TASK_ID=G008\n"
            "CHECK_RESULT=pass\n"
            "TASK_STATUS=done\n"
            "[INFO] Task completed successfully.\n"
            "CLAUDE_CODE_CALLED=yes\n"
            "BUSINESS_CODE_CHANGED=no\n"
            "WORKTREE_STATUS=clean\n"
            "REPORT_PATHS=reports/dev/G008-dev-report.md\n"
            "[INFO] Writing report...\n"
        )
        _SAMPLE_EMPTY = ""
        _SAMPLE_EXIT_CODE_NONZERO = (
            "TASK_ID=G008\n"
            "CHECK_RESULT=pass\n"
            "TASK_STATUS=done\n"
            "CLAUDE_CODE_CALLED=yes\n"
            "BUSINESS_CODE_CHANGED=no\n"
            "WORKTREE_STATUS=clean\n"
            "REPORT_PATHS=reports/dev/G008-dev-report.md\n"
        )

        _SAMPLES = {
            "pass": _SAMPLE_PASS,
            "fail": _SAMPLE_FAIL,
            "missing-check-result": _SAMPLE_MISSING_CHECK_RESULT,
            "missing-optional": _SAMPLE_MISSING_OPTIONAL,
            "with-logs": _SAMPLE_WITH_LOGS,
            "empty": _SAMPLE_EMPTY,
            "exit-code-nonzero": _SAMPLE_EXIT_CODE_NONZERO,
        }

        stdout_text = _SAMPLES.get(sample_type, _SAMPLE_PASS)
        exit_code = 2 if sample_type == "exit-code-nonzero" else 0

        result = parse_child_command_output(
            stdout_text=stdout_text,
            stderr_text="",
            exit_code=exit_code,
        )

        print()
        print(f"PARSE_STATUS={result.parse_status}")
        print(f"PARSE_CHECK_RESULT={result.parse_check_result}")
        print(f"RAW_STDOUT_PRESENT={result.raw_stdout_present}")
        print(f"RAW_STDERR_PRESENT={result.raw_stderr_present}")
        print(f"EXIT_CODE={result.exit_code}")
        print(f"TASK_ID={result.task_id}")
        print(f"CHECK_RESULT={result.check_result}")
        print(f"TASK_STATUS={result.task_status}")
        print(f"NEXT_PENDING={result.next_pending}")
        print(f"REAL_TASK_EXECUTION={result.real_task_execution}")
        print(f"CLAUDE_CODE_CALLED={result.claude_code_called}")
        print(f"BUSINESS_CODE_CHANGED={result.business_code_changed}")
        print(f"WORKTREE_STATUS={result.worktree_status}")
        report_paths_str = ",".join(result.report_paths) if result.report_paths else "NONE"
        print(f"REPORT_PATHS={report_paths_str}")
        missing_str = ",".join(result.missing_required_fields) if result.missing_required_fields else "NONE"
        print(f"MISSING_REQUIRED_FIELDS={missing_str}")
        unknown_str = ",".join(result.unknown_fields) if result.unknown_fields else "NONE"
        print(f"UNKNOWN_FIELDS={unknown_str}")
        print(f"STOP_REASON={result.stop_reason or 'NONE'}")
        print(f"HUMAN_REVIEW_REQUIRED={result.human_review_required}")
        print()
        print(f"Message：{result.message}")
    elif args[0] == "first-real-run-acceptance-dry-run":
        # T092: first real-run acceptance dry-run
        sample_type = "pass"
        if len(args) >= 3 and args[1] == "--sample":
            sample_type = args[2]
        elif len(args) >= 2 and not args[1].startswith("-"):
            sample_type = args[1]

        # 内置样例
        _ACCEPTANCE_SAMPLES = {
            "pass": {
                "stdout": (
                    "TASK_ID=T092\n"
                    "CHECK_RESULT=pass\n"
                    "TASK_STATUS=done\n"
                    "REAL_TASK_EXECUTION=yes\n"
                    "CLAUDE_CODE_CALLED=yes\n"
                    "BUSINESS_CODE_CHANGED=no\n"
                    "WORKTREE_STATUS=clean\n"
                    "REPORT_PATHS=reports/dev/T092-dev-report.md,reports/checks/T092-first-real-run-acceptance-model-check.md\n"
                ),
                "workspace_after": "clean",
                "workspace_classification": "clean",
                "claude_code_called": "yes",
                "business_code_changed": "no",
            },
            "pass-dirty-reports": {
                "stdout": (
                    "TASK_ID=T092\n"
                    "CHECK_RESULT=pass\n"
                    "TASK_STATUS=done\n"
                    "REAL_TASK_EXECUTION=yes\n"
                    "CLAUDE_CODE_CALLED=yes\n"
                    "BUSINESS_CODE_CHANGED=no\n"
                    "WORKTREE_STATUS=dirty_reports_only\n"
                    "REPORT_PATHS=reports/dev/T092-dev-report.md\n"
                ),
                "workspace_after": "dirty_reports_only",
                "workspace_classification": "dirty_reports_only",
                "claude_code_called": "yes",
                "business_code_changed": "no",
            },
            "fail": {
                "stdout": (
                    "TASK_ID=T092\n"
                    "CHECK_RESULT=fail\n"
                    "TASK_STATUS=failed\n"
                    "REAL_TASK_EXECUTION=yes\n"
                    "CLAUDE_CODE_CALLED=unknown\n"
                    "BUSINESS_CODE_CHANGED=unknown\n"
                    "WORKTREE_STATUS=dirty_unknown\n"
                    "REPORT_PATHS=reports/dev/T092-dev-report.md\n"
                ),
                "workspace_after": "dirty_unknown",
                "workspace_classification": "dirty_unknown",
                "claude_code_called": "unknown",
                "business_code_changed": "unknown",
            },
            "missing-check-result": {
                "stdout": (
                    "TASK_ID=T092\n"
                    "TASK_STATUS=done\n"
                    "REAL_TASK_EXECUTION=yes\n"
                    "CLAUDE_CODE_CALLED=yes\n"
                    "WORKTREE_STATUS=clean\n"
                ),
                "workspace_after": "clean",
                "workspace_classification": "clean",
                "claude_code_called": "yes",
                "business_code_changed": "no",
            },
            "unsafe-unknown": {
                "stdout": (
                    "TASK_ID=T092\n"
                    "CHECK_RESULT=pass\n"
                    "TASK_STATUS=done\n"
                    "REAL_TASK_EXECUTION=yes\n"
                    "CLAUDE_CODE_CALLED=unknown\n"
                    "BUSINESS_CODE_CHANGED=unknown\n"
                    "WORKTREE_STATUS=dirty_unknown\n"
                    "REPORT_PATHS=reports/dev/T092-dev-report.md\n"
                ),
                "workspace_after": "dirty_unknown",
                "workspace_classification": "dirty_unknown",
                "claude_code_called": "unknown",
                "business_code_changed": "unknown",
            },
        }

        sample = _ACCEPTANCE_SAMPLES.get(sample_type, _ACCEPTANCE_SAMPLES["pass"])

        # 先解析 child output
        child_result = parse_child_command_output(
            stdout_text=sample["stdout"],
            stderr_text="",
            exit_code=0,
        )

        # 再评估 acceptance
        acceptance = evaluate_first_real_run_acceptance(
            project_path=PROJECT_ROOT,
            task_id="T092",
            child_parse_result=child_result,
            workspace_status_before="clean",
            workspace_status_after=sample["workspace_after"],
            workspace_change_classification=sample["workspace_classification"],
            run_project_task_full_called="yes",
            claude_code_called=sample["claude_code_called"],
            business_code_changed=sample["business_code_changed"],
        )

        print()
        print(f"EXECUTION_MODE={acceptance.execution_mode}")
        print(f"RUN_ID={acceptance.run_id}")
        print(f"TASK_ID={acceptance.task_id}")
        print(f"REAL_TASK_EXECUTION={acceptance.real_task_execution}")
        print(f"RUN_PROJECT_TASK_FULL_CALLED={acceptance.run_project_task_full_called}")
        print(f"CHILD_EXIT_CODE={acceptance.child_exit_code}")
        print(f"CHILD_CHECK_RESULT={acceptance.child_check_result}")
        print(f"CHILD_TASK_STATUS={acceptance.child_task_status}")
        print(f"CLAUDE_CODE_CALLED={acceptance.claude_code_called}")
        print(f"BUSINESS_CODE_CHANGED={acceptance.business_code_changed}")
        print(f"WORKSPACE_STATUS_BEFORE={acceptance.workspace_status_before}")
        print(f"WORKSPACE_STATUS_AFTER={acceptance.workspace_status_after}")
        print(f"WORKSPACE_CHANGE_CLASSIFICATION={acceptance.workspace_change_classification}")
        report_str = ",".join(acceptance.report_paths) if acceptance.report_paths else "NONE"
        print(f"REPORT_PATHS={report_str}")
        print(f"AUTO_CONTINUE_TO_NEXT_TASK={acceptance.auto_continue_to_next_task}")
        print(f"AUTO_GIT_BACKUP={acceptance.auto_git_backup}")
        print(f"HUMAN_REVIEW_REQUIRED={acceptance.human_review_required}")
        print(f"ACCEPTANCE_STATUS={acceptance.acceptance_status}")
        print(f"STOP_REASON={acceptance.stop_reason}")
        print(f"NEXT_ACTION={acceptance.next_action}")
        print(f"CHECK_RESULT={acceptance.check_result}")
        print()
        print(f"Message：{acceptance.message}")
    elif args[0] == "plan-project-loop":
        # T059 continuous task planner dry-run
        max_tasks_val = 3
        i = 1
        while i < len(args):
            if args[i] == "--max-tasks" and i + 1 < len(args):
                max_tasks_val = int(args[i + 1])
                i += 2
            else:
                i += 1

        plan = build_continuous_task_plan(
            project_root=PROJECT_ROOT,
            max_tasks=max_tasks_val,
            dry_run=True,
        )

        print()
        print(f"PLAN_STATUS={plan.plan_status}")
        print(f"NEXT_PENDING={plan.next_pending or 'NONE'}")
        planned_ids = ",".join(t.task_id for t in plan.planned_tasks)
        print(f"PLANNED_TASKS={planned_ids or 'NONE'}")
        print(f"MAX_TASKS={plan.max_tasks}")
        print(f"HARD_LIMIT={plan.hard_limit}")
        print(f"DRY_RUN={plan.dry_run}")
        print(f"HUMAN_REVIEW_REQUIRED={plan.human_review_required}")
        print(f"STOP_REASON={plan.stop_reason or 'NONE'}")
        print(f"Message：{plan.message}")
        print(f"NEXT_ACTION={plan.next_action}")
    elif args[0] == "run-project-loop":
        # T060 run-project-loop dry-run + T065 execute mode safety gate + T071 adapter dry-run + T073 real-call stub + T078 real-call safety gate
        max_tasks_val = 3
        execute_mode = False
        dry_run_flag = False
        adapter_dry_run = False
        real_call_stub = False
        real_call = False
        real_call_dry_run = False
        real_call_run_once = False
        real_confirm_text = None
        confirm_text = None
        i = 1
        while i < len(args):
            if args[i] == "--max-tasks" and i + 1 < len(args):
                max_tasks_val = int(args[i + 1])
                i += 2
            elif args[i] == "--execute":
                execute_mode = True
                i += 1
            elif args[i] == "--dry-run":
                dry_run_flag = True
                i += 1
            elif args[i] == "--adapter-dry-run":
                adapter_dry_run = True
                i += 1
            elif args[i] == "--real-call-stub":
                real_call_stub = True
                i += 1
            elif args[i] == "--real-call":
                real_call = True
                i += 1
            elif args[i] == "--real-call-dry-run":
                real_call_dry_run = True
                i += 1
            elif args[i] == "--real-call-run-once":
                real_call_run_once = True
                i += 1
            elif args[i] == "--real-confirm" and i + 1 < len(args):
                real_confirm_text = args[i + 1]
                i += 2
            elif args[i] == "--confirm" and i + 1 < len(args):
                confirm_text = args[i + 1]
                i += 2
            else:
                i += 1

        # --execute 和 --dry-run 互斥
        if execute_mode and dry_run_flag:
            print()
            print("ERROR：--execute 和 --dry-run 互斥，不能同时使用。")
            print("请去掉其中一个参数后重试。")
            return

        # --adapter-dry-run 必须配合 --execute
        if adapter_dry_run and not execute_mode:
            print()
            print("ERROR：--adapter-dry-run 必须配合 --execute 使用。")
            return

        # --real-call-stub 必须配合 --execute
        if real_call_stub and not execute_mode:
            print()
            print("ERROR：--real-call-stub 必须配合 --execute 使用。")
            return

        # --adapter-dry-run 和 --real-call-stub 互斥
        if adapter_dry_run and real_call_stub:
            print()
            print("ERROR：--adapter-dry-run 和 --real-call-stub 互斥，不能同时使用。")
            return

        # --real-call 必须配合 --execute
        if real_call and not execute_mode:
            print()
            print("ERROR：--real-call 必须配合 --execute 使用。")
            return

        # --real-call 和 --adapter-dry-run 互斥
        if real_call and adapter_dry_run:
            print()
            print("ERROR：--real-call 和 --adapter-dry-run 互斥，不能同时使用。")
            return

        # --real-call 和 --real-call-stub 互斥
        if real_call and real_call_stub:
            print()
            print("ERROR：--real-call 和 --real-call-stub 互斥，不能同时使用。")
            return

        # --real-call-dry-run 必须配合 --real-call
        if real_call_dry_run and not real_call:
            print()
            print("ERROR：--real-call-dry-run 必须配合 --real-call 使用。")
            return

        # --real-call-dry-run 必须配合 --execute
        if real_call_dry_run and not execute_mode:
            print()
            print("ERROR：--real-call-dry-run 必须配合 --execute 使用。")
            return

        # --real-call-dry-run 和 --dry-run 互斥
        if real_call_dry_run and dry_run_flag:
            print()
            print("ERROR：--real-call-dry-run 和 --dry-run 互斥，不能同时使用。")
            return

        # --real-call-dry-run 和 --adapter-dry-run 互斥
        if real_call_dry_run and adapter_dry_run:
            print()
            print("ERROR：--real-call-dry-run 和 --adapter-dry-run 互斥，不能同时使用。")
            return

        # --real-call-dry-run 和 --real-call-stub 互斥
        if real_call_dry_run and real_call_stub:
            print()
            print("ERROR：--real-call-dry-run 和 --real-call-stub 互斥，不能同时使用。")
            return

        # --real-call-run-once 必须配合 --real-call
        if real_call_run_once and not real_call:
            print()
            print("ERROR：--real-call-run-once 必须配合 --real-call 使用。")
            return

        # --real-call-run-once 必须配合 --execute
        if real_call_run_once and not execute_mode:
            print()
            print("ERROR：--real-call-run-once 必须配合 --execute 使用。")
            return

        # --real-call-run-once 和 --real-call-dry-run 互斥
        if real_call_run_once and real_call_dry_run:
            print()
            print("ERROR：--real-call-run-once 和 --real-call-dry-run 互斥，不能同时使用。")
            return

        # --real-call-run-once 和 --adapter-dry-run 互斥
        if real_call_run_once and adapter_dry_run:
            print()
            print("ERROR：--real-call-run-once 和 --adapter-dry-run 互斥，不能同时使用。")
            return

        # --real-call-run-once 和 --real-call-stub 互斥
        if real_call_run_once and real_call_stub:
            print()
            print("ERROR：--real-call-run-once 和 --real-call-stub 互斥，不能同时使用。")
            return

        # --real-call-run-once 和 --dry-run 互斥
        if real_call_run_once and dry_run_flag:
            print()
            print("ERROR：--real-call-run-once 和 --dry-run 互斥，不能同时使用。")
            return

        if real_call_run_once and execute_mode and real_call:
            # T085: real-call run-once safety shell
            result = run_project_loop_real_call_run_once_safety_shell(
                project_root=PROJECT_ROOT,
                max_tasks=max_tasks_val,
                confirm=confirm_text,
                real_confirm=real_confirm_text,
                real_call_dry_run=real_call_dry_run,
                adapter_dry_run=adapter_dry_run,
                real_call_stub=real_call_stub,
                dry_run_flag=dry_run_flag,
            )

            print()
            print(f"EXECUTION_MODE={result.execution_mode}")
            print(f"REAL_CALL_ALLOWED={result.real_call_allowed}")
            print(f"RUN_ONCE_REQUESTED={result.run_once_requested}")
            print(f"RUN_ONCE_SAFETY_SHELL_STARTED={result.run_once_safety_shell_started}")
            print(f"RUN_ID={result.run_id}")
            if result.task_id:
                print(f"TASK_ID={result.task_id}")
            if result.command:
                print(f"COMMAND={result.command}")
            if result.function_call:
                print(f"FUNCTION_CALL={result.function_call}")
            print(f"PREFLIGHT_STATUS={result.preflight_status}")
            print(f"REAL_TASK_EXECUTION={result.real_task_execution}")
            print(f"RUN_PROJECT_TASK_FULL_CALLED={result.run_project_task_full_called}")
            print(f"CLAUDE_CODE_CALLED={result.claude_code_called}")
            print(f"BUSINESS_CODE_CHANGED={result.business_code_changed}")
            print(f"CHILD_EXIT_CODE={result.child_exit_code}")
            print(f"CHILD_CHECK_RESULT={result.child_check_result}")
            print(f"CHILD_TASK_STATUS={result.child_task_status}")
            print(f"AUTO_CONTINUE_TO_NEXT_TASK={result.auto_continue_to_next_task}")
            print(f"AUTO_GIT_BACKUP={result.auto_git_backup}")
            print(f"HUMAN_REVIEW_REQUIRED={result.human_review_required}")
            print(f"CHECK_RESULT={result.check_result}")
            print(f"STOP_REASON={result.stop_reason or 'NONE'}")
            print(f"NEXT_ACTION={result.next_action}")
            print()
            print(f"Message：{result.message}")
        elif execute_mode and real_call and real_call_dry_run:
            # T079: real-call dry-run executor
            result = run_project_loop_real_call_dry_run_executor(
                project_root=PROJECT_ROOT,
                max_tasks=max_tasks_val,
                confirm=confirm_text,
                real_confirm=real_confirm_text,
            )

            print()
            print(f"EXECUTION_MODE={result.execution_mode}")
            print(f"REAL_CALL_ALLOWED={result.real_call_allowed}")
            print(f"DRY_RUN_EXECUTOR_STARTED={result.dry_run_executor_started}")
            print(f"RUN_ID={result.run_id}")
            print(f"MAX_TASKS={result.max_tasks}")
            if result.task_id:
                print(f"TASK_ID={result.task_id}")
            if result.command:
                print(f"COMMAND={result.command}")
            if result.function_call:
                print(f"FUNCTION_CALL={result.function_call}")
            print(f"CHILD_RESULT_MODE={result.child_result_mode}")
            print(f"SIMULATED_EXIT_CODE={result.simulated_exit_code}")
            print(f"SIMULATED_CHECK_RESULT={result.simulated_check_result}")
            print(f"SIMULATED_TASK_STATUS={result.simulated_task_status}")
            print(f"TASK_EXECUTION_PERFORMED={result.task_execution_performed}")
            print(f"RUN_PROJECT_TASK_FULL_CALLED={result.run_project_task_full_called}")
            print(f"CLAUDE_CODE_CALLED={result.claude_code_called}")
            print(f"BUSINESS_CODE_CHANGED={result.business_code_changed}")
            print(f"AUTO_CONTINUE_TO_NEXT_TASK={result.auto_continue_to_next_task}")
            print(f"AUTO_GIT_BACKUP={result.auto_git_backup}")
            print(f"HUMAN_REVIEW_REQUIRED={result.human_review_required}")
            print(f"CHECK_RESULT={result.check_result}")
            print(f"STOP_REASON={result.stop_reason or 'NONE'}")
            print(f"NEXT_ACTION={result.next_action}")
            print()
            print(f"Message：{result.message}")
        elif execute_mode and real_call:
            # T078: real-call double-confirm safety gate
            safety = validate_real_call_safety(
                project_root=PROJECT_ROOT,
                max_tasks=max_tasks_val,
                execute_requested=execute_mode,
                confirm=confirm_text,
                real_call_requested=real_call,
                real_confirm=real_confirm_text,
                adapter_dry_run=adapter_dry_run,
                real_call_stub=real_call_stub,
            )

            print()
            print(f"EXECUTION_MODE=real_call_safety_gate")
            print(f"REAL_CALL_REQUESTED={safety.real_call_requested}")
            print(f"REAL_CONFIRM_STATUS={safety.real_confirm_status}")
            print(f"EXECUTE_ALLOWED={safety.execute_allowed}")
            print(f"REAL_CALL_ALLOWED={safety.real_call_allowed}")
            print(f"RUN_ID={safety.run_id}")
            print(f"MAX_TASKS={safety.max_tasks}")
            if safety.planned_tasks:
                planned_str = ",".join(safety.planned_tasks)
                print(f"PLANNED_TASKS={planned_str}")
            if safety.task_id:
                print(f"TASK_ID={safety.task_id}")
            print(f"WORKSPACE_STATUS={safety.workspace_status}")
            print(f"PREFLIGHT_STATUS={safety.preflight_status}")
            print(f"REAL_TASK_EXECUTION={'yes' if safety.real_task_execution else 'no'}")
            print(f"RUN_PROJECT_TASK_FULL_CALLED={'yes' if safety.run_project_task_full_called else 'no'}")
            print(f"CLAUDE_CODE_CALLED={safety.claude_code_called}")
            print(f"BUSINESS_CODE_CHANGED={safety.business_code_changed}")
            print(f"CHECK_RESULT={safety.check_result}")
            print(f"HUMAN_REVIEW_REQUIRED={safety.human_review_required}")
            print(f"STOP_REASON={safety.stop_reason or 'NONE'}")
            print(f"NEXT_ACTION={safety.next_action}")
            print()
            print(f"Message：{safety.message}")
        elif execute_mode and real_call_stub:
            # T073: real-call stub
            stub = run_project_loop_real_call_stub(
                project_root=PROJECT_ROOT,
                max_tasks=max_tasks_val,
                confirm=confirm_text,
            )

            print()
            print(f"EXECUTION_MODE={stub.execution_mode}")
            print(f"REAL_CALL_REQUESTED={stub.real_call_requested}")
            print(f"REAL_CALL_STUB_STARTED={stub.real_call_stub_started}")
            print(f"RUN_ID={stub.run_id}")
            print(f"MAX_TASKS={stub.max_tasks}")
            if stub.task_id:
                print(f"TASK_ID={stub.task_id}")
            if stub.command:
                print(f"COMMAND={stub.command}")
            print(f"PREFLIGHT_STATUS={stub.preflight_status}")
            print(f"TASK_EXECUTION_PERFORMED={stub.task_execution_performed}")
            print(f"RUN_PROJECT_TASK_FULL_CALLED={stub.run_project_task_full_called}")
            print(f"CLAUDE_CODE_CALLED={stub.claude_code_called}")
            print(f"BUSINESS_CODE_CHANGED={stub.business_code_changed}")
            print(f"EXIT_CODE={stub.exit_code}")
            print(f"CHECK_RESULT={stub.check_result}")
            print(f"LOOP_STATUS={stub.loop_status}")
            print(f"STOP_REASON={stub.stop_reason or 'NONE'}")
            print(f"HUMAN_REVIEW_REQUIRED={stub.human_review_required}")
            print(f"NEXT_ACTION={stub.next_action}")
            print()
            print(f"Message：{stub.message}")
        elif execute_mode and adapter_dry_run:
            # T071: task execution adapter dry-run
            adapter = run_project_loop_task_execution_adapter_dry_run(
                project_root=PROJECT_ROOT,
                max_tasks=max_tasks_val,
                confirm=confirm_text,
            )

            print()
            print(f"EXECUTION_MODE={adapter.execution_mode}")
            print(f"ADAPTER_DRY_RUN=true")
            print(f"RUN_ID={adapter.run_id}")
            print(f"MAX_TASKS={adapter.max_tasks}")
            if adapter.started_task:
                print(f"TASK_ID={adapter.started_task}")
            print(f"TASK_EXECUTION_PERFORMED={adapter.task_execution_performed}")
            print(f"RUN_PROJECT_TASK_FULL_CALLED={adapter.run_project_task_full_called}")
            print(f"CLAUDE_CODE_CALLED={adapter.claude_code_called}")
            print(f"BUSINESS_CODE_CHANGED={adapter.business_code_changed}")
            print(f"LOOP_STATUS={adapter.loop_status}")
            print(f"STOP_REASON={adapter.stop_reason or 'NONE'}")
            print(f"HUMAN_REVIEW_REQUIRED={adapter.human_review_required}")
            print(f"CHECK_RESULT={'pass' if adapter.loop_status == 'adapter_dry_run_completed' else 'fail'}")
            print(f"NEXT_ACTION={adapter.next_action}")
            if adapter.task_results:
                tr = adapter.task_results[0]
                print(f"COMMAND={tr.command}")
            print()
            print(f"Message：{adapter.message}")
        elif execute_mode:
            # T066: execute mode → safety gate + execute stub
            stub = run_project_loop_execute_stub(
                project_root=PROJECT_ROOT,
                max_tasks=max_tasks_val,
                confirm=confirm_text,
            )

            print()
            print(f"EXECUTE_MODE_REQUESTED=true")
            print(f"EXECUTE_ALLOWED={stub.execute_allowed}")
            print(f"EXECUTE_STUB_STARTED={stub.execute_stub_started}")
            print(f"RUN_ID={stub.run_id}")
            print(f"MAX_TASKS={stub.max_tasks}")
            planned_str = ",".join(stub.planned_tasks)
            print(f"PLANNED_TASKS={planned_str or 'NONE'}")
            if stub.stub_task:
                print(f"STUB_TASK={stub.stub_task}")
            print(f"COMPLETED_TASKS={','.join(stub.completed_tasks) or 'NONE'}")
            print(f"FAILED_TASKS={','.join(stub.failed_tasks) or 'NONE'}")
            print(f"TASK_EXECUTION_PERFORMED={stub.task_execution_performed}")
            print(f"CLAUDE_CODE_CALLED={stub.claude_code_called}")
            print(f"BUSINESS_CODE_CHANGED={stub.business_code_changed}")
            print(f"LOOP_STATUS={stub.loop_status}")
            print(f"STOP_REASON={stub.stop_reason or 'NONE'}")
            print(f"HUMAN_REVIEW_REQUIRED={stub.human_review_required}")
            print(f"NEXT_ACTION={stub.next_action}")
            print(f"CHECK_RESULT={'pass' if stub.execute_stub_started else 'fail'}")
            print()
            print(f"Message：{stub.message}")
        else:
            # T060: dry-run（保持原有行为）
            result = run_project_loop_dry_run(
                project_root=PROJECT_ROOT,
                max_tasks=max_tasks_val,
            )

            print()
            print(f"LOOP_STATUS={result.loop_status}")
            print(f"RUN_ID={result.run_id}")
            print(f"DRY_RUN={result.dry_run}")
            print(f"MAX_TASKS={result.max_tasks}")
            planned_str = ",".join(result.planned_tasks)
            completed_str = ",".join(result.completed_tasks)
            failed_str = ",".join(result.failed_tasks)
            print(f"PLANNED_TASKS={planned_str or 'NONE'}")
            print(f"COMPLETED_TASKS={completed_str or 'NONE'}")
            print(f"FAILED_TASKS={failed_str or 'NONE'}")
            print(f"CURRENT_TASK={result.current_task or 'NONE'}")
            print(f"NEXT_TASK={result.next_task or 'NONE'}")
            print(f"STOP_REASON={result.stop_reason or 'NONE'}")
            print(f"HUMAN_REVIEW_REQUIRED={result.human_review_required}")
            print(f"TASK_EXECUTION_PERFORMED=false")
            print(f"CLAUDE_CODE_CALLED=false")
            print(f"BUSINESS_CODE_CHANGED=false")
            print(f"NEXT_ACTION={result.next_action}")
            print()
            # 每个任务的详细结果
            if result.task_results:
                print("--- Task Results ---")
                for tr in result.task_results:
                    print(f"  {tr.task_id}: status={tr.task_status}, "
                          f"execution_performed={tr.execution_performed}, "
                          f"stop_reason={tr.stop_reason or 'NONE'}, "
                          f"next_action={tr.next_action}")
                print()
            print(f"Message：{result.message}")
    else:
        print("用法：")
        print("  python runner.py                          显示下一个 pending 任务")
        print("  python runner.py complete <T编号>          将任务状态改为 done")
        print("  python runner.py start <T编号>             将任务状态改为 in_progress")
        print("  python runner.py generate-prompt           生成下一个 pending 任务的提示词")
        print("  python runner.py run-current               调用 Claude Code 执行当前提示词")
        print("  python runner.py check-result              判断最新执行结果")
        print("  python runner.py auto-complete-success     成功时自动完成当前 in_progress 任务")
        print("  python runner.py run-next                  单步自动闭环执行下一个 pending 任务")
        print("  python runner.py retry-current             重新执行当前 in_progress 任务")
        print("  python runner.py run-loop [最大轮数]        多任务自动执行循环（默认 10 轮）")
        print("  python runner.py plan-project               运行 Planner Agent 生成任务拆解草案")
        print("  python runner.py main-decide                Main Agent 根据当前状态决策下一步动作")
        print("  python runner.py run-game-next              自动执行小游戏项目下一个 pending 任务")
        print("  python runner.py run-project-next --project <path>  通用：执行指定子项目下一个 pending 任务")
        print("  python runner.py review-game-task [任务编号]  审查小游戏项目指定任务（默认 G002）")
        print("  python runner.py test-game-task [任务编号]   测试小游戏项目指定任务（默认 G003）")
        print("  python runner.py test-game-behavior [任务编号]  行为检查小游戏项目指定任务（默认 G004）")
        print("  python runner.py test-game-collision [任务编号]  碰撞检查小游戏项目指定任务（默认 G007）")
        print("  python runner.py decide-game-task [任务编号] 综合决策小游戏项目指定任务（默认 G003）")
        print("  python runner.py decide-game-task-v2 [任务编号]  增强综合决策（含行为测试，默认 G004）")
        print("  python runner.py generate-rework-prompt [任务编号] [轮次]  生成返工 prompt（默认 G004 轮次 1）")
        print("  python runner.py execute-rework --project <path> --task <id> --round <n> [--confirm \"...\"] [--real-execution] [--resume]  返工执行安全检查、confirmed stub 或 resume stub")
        print("  python runner.py run-project-task-full --project <path> --task <id>  单任务完整闭环（Developer/Tester/Reviewer/Decision）")
        print("  python runner.py plan-project-loop [--max-tasks N]  连续任务推进计划（dry-run）")
        print("  python runner.py run-project-loop [--max-tasks N] [--dry-run]  连续任务模拟推进（dry-run）")


if __name__ == "__main__":
    main()
