"""
Planner Agent 自动拆解任务 MVP

读取项目需求文件，构造 Planner prompt，通过 model_adapter 调用 planner 模型，
将 Planner 输出保存到 reports/planner/。
"""

from datetime import datetime
from pathlib import Path

from tools.model_adapter import ModelRequest, call_model


def load_requirement(path: str | Path) -> str:
    """读取项目需求文件。"""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"需求文件不存在: {path}")
    return path.read_text(encoding="utf-8")


def build_planner_prompt(requirement: str, workflow_id: str = "game_web_mvp") -> str:
    """根据需求内容构造 Planner Agent prompt。

    要求 Planner 输出符合 T014 Agent 输出协议的格式。
    """
    return f"""你是 Planner Agent。

你的任务是根据以下项目需求，生成一份任务拆解草案。

## 输出格式要求

请严格按照以下格式输出：

# Planner Agent Output

## Agent

Planner Agent

## Task

任务：根据项目需求生成任务清单草案

## Status

PASS / FAIL / RETRY / BLOCKED / INFO

## Plan Summary

（一句话总结规划思路）

## Generated Tasks

为每个任务使用以下格式：

### TXXX 任务名称

状态：pending
角色：Developer / Tester / Reviewer / Reporter
目标：（一句话目标）

#### 验收标准

- （具体可验证的标准）

---

## Assumptions

- （规划假设）

## Risks

- （风险提示）

## Evidence

- reports/planner/<task-id>-planner-report.md

## Next Action

建议下一步：

## 规划原则

1. 每个任务必须小而明确
2. 每个任务必须可独立验证
3. 任务按执行顺序排列
4. 每个任务指定唯一的 Agent 角色
5. 验收标准必须具体可检查
6. 不要一次性引入太多复杂功能
7. 不要超出 MVP 范围
8. 不要包含 Out of Scope 的内容

## 当前 Workflow

workflow_id: {workflow_id}

## 项目需求

{requirement}
"""


def save_planner_output(content: str, output_dir: str | Path = "reports/planner") -> Path:
    """保存 Planner Agent 输出。"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_file = output_dir / f"T017-planner-output.md"

    output_file.write_text(content, encoding="utf-8")
    return output_file


def run_planner(
    requirement_path: str | Path,
    workflow_id: str = "game_web_mvp",
) -> Path:
    """运行 Planner Agent，生成任务拆解草案并保存。

    Args:
        requirement_path: 需求文件路径
        workflow_id: workflow 标识

    Returns:
        输出文件路径
    """
    # 1. 读取需求
    requirement = load_requirement(requirement_path)
    print(f"已读取需求文件：{requirement_path}")

    # 2. 构造 Planner prompt
    prompt = build_planner_prompt(requirement, workflow_id)
    print("已构造 Planner prompt")

    # 3. 调用模型
    request = ModelRequest(
        agent="planner",
        prompt=prompt,
        system_prompt="你是 Planner Agent，负责根据项目需求生成任务清单草案。输出必须严格遵循指定的 markdown 格式。",
    )
    response = call_model(request)
    print(f"模型调用完成：provider={response.provider}, model={response.model}, success={response.success}")

    # 4. 构造输出内容
    output_lines = [
        f"# Planner Agent 自动拆解输出",
        "",
        f"## 调用信息",
        "",
        f"- provider: {response.provider}",
        f"- model: {response.model}",
        f"- agent: {response.agent}",
        f"- success: {response.success}",
        f"- timestamp: {datetime.now().isoformat()}",
        "",
    ]

    if response.error:
        output_lines.extend([
            f"## Error",
            "",
            f"{response.error}",
            "",
        ])

    output_lines.extend([
        f"## 模型响应内容",
        "",
        response.content,
        "",
    ])

    # 5. 保存输出
    output_content = "\n".join(output_lines)
    output_path = save_planner_output(output_content)
    print(f"Planner 输出已保存：{output_path}")

    return output_path
