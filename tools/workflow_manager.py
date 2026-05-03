"""工作流管理器 — 管理 Agent 执行流程"""

from __future__ import annotations


def build_agent_prompt(task: dict) -> str:
    """根据任务信息生成当前 Agent 的执行提示词。"""
    role = task.get("role", "Developer")
    task_id = task.get("id", "")
    title = task.get("title", "")
    status = task.get("status", "")
    goal = task.get("goal", "")
    raw = task.get("raw", "")

    lines = [
        f"# 当前任务执行提示词",
        f"",
        f"你现在是 {role} Agent。",
        f"",
        f"## 当前任务",
        f"",
        f"任务编号：{task_id}",
        f"任务名称：{title}",
        f"状态：{status}",
        f"角色：{role}",
        f"",
        f"## 任务目标",
        f"",
        f"{goal}",
        f"",
        f"## 任务原始内容",
        f"",
        f"{raw}",
        f"",
        f"## 工作要求",
        f"",
        f"1. 只执行当前任务，不要提前实现后续任务。",
        f"2. 严格遵守任务验收标准。",
        f"3. 修改完成后输出修改文件列表。",
        f"4. 完成后生成对应开发报告。",
        f"5. 不要扩大需求范围。",
        f"6. 如果发现任务描述不清楚，先做最小合理假设，并在报告中说明。",
        f"",
        f"请开始执行当前任务。",
    ]
    return "\n".join(lines)
