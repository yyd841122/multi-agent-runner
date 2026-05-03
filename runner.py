"""multi-agent-runner 入口"""

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

PROJECT_ROOT = Path(__file__).parent
TASKS_FILE = PROJECT_ROOT / "docs" / "tasks.md"
PROMPT_FILE = PROJECT_ROOT / "prompts" / "current_prompt.md"
CLAUDE_OUTPUT_DIR = PROJECT_ROOT / "reports" / "claude"
CLAUDE_OUTPUT_FILE = CLAUDE_OUTPUT_DIR / "latest-output.md"
CLAUDE_HISTORY_DIR = CLAUDE_OUTPUT_DIR / "history"
RUN_LOG_FILE = PROJECT_ROOT / "reports" / "run-log.md"
DEV_REPORTS_DIR = PROJECT_ROOT / "reports" / "dev"
GAME_REQUIREMENT_FILE = PROJECT_ROOT / "projects" / "down-100-floors-game" / "requirement.md"


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


if __name__ == "__main__":
    main()
