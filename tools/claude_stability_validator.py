"""Claude Code stability validation dry-run planner and report skeleton generator.

T112: 只生成 dry-run plan 和报告 skeleton，不调用 Claude Code，不执行真实任务，
不创建诊断目标文件，不进入 run-project-task-full。
"""

from dataclasses import dataclass, field
from typing import List


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class StabilityValidationCommandPlan:
    """单条验证命令的 dry-run 计划。"""
    layer: str
    scenario_id: str
    description: str
    permission_mode: str
    command_kind: str  # "text_only" / "tool_use" / "runner_text_only" / "runner_tool_use"
    expected_tool_use: bool
    expected_file_change: bool
    timeout_seconds: int
    target_file: str = ""  # 仅 Layer 2/3 tool-use 场景有值
    safety_notes: List[str] = field(default_factory=list)


@dataclass
class StabilityValidationPlanResult:
    """一层或多层验证的 dry-run 计划结果。"""
    plan_id: str
    layer: str  # "1" / "2" / "3" / "all"
    dry_run: bool  # True（本模块始终为 dry-run）
    command_count: int
    commands: List[StabilityValidationCommandPlan]
    real_task_execution: str  # "no"
    run_project_task_full_called: str  # "no"
    claude_code_called: str  # "no"
    bypass_permissions_used: str  # "no"
    business_code_changed: str  # "no"
    framework_code_changed: str  # "no"
    auto_continue_to_next_task: bool  # False
    auto_git_backup: bool  # False
    human_review_required: bool  # True
    check_result: str  # "pass" / "fail"
    next_action: str
    message: str


# ---------------------------------------------------------------------------
# Layer 1: Text-only Stability Dry-run Plan
# ---------------------------------------------------------------------------

def build_layer_1_text_only_stability_plan() -> StabilityValidationPlanResult:
    """生成 Layer 1 text-only 稳定性验证 dry-run 计划。

    6 次调用：3x default text-only + 3x acceptEdits text-only。
    不调用 Claude Code，只生成计划。
    """
    commands: List[StabilityValidationCommandPlan] = []

    # 3x default text-only
    for i in range(1, 4):
        commands.append(StabilityValidationCommandPlan(
            layer="1",
            scenario_id=f"L1-default-text-{i:02d}",
            description=f"Layer 1 default text-only test #{i}",
            permission_mode="default",
            command_kind="text_only",
            expected_tool_use=False,
            expected_file_change=False,
            timeout_seconds=60,
            safety_notes=[
                "只验证文本输出，不触发 tool-use",
                "不创建文件",
                "预期秒级返回（< 30 秒）",
            ],
        ))

    # 3x acceptEdits text-only
    for i in range(1, 4):
        commands.append(StabilityValidationCommandPlan(
            layer="1",
            scenario_id=f"L1-acceptedits-text-{i:02d}",
            description=f"Layer 1 acceptEdits text-only test #{i}",
            permission_mode="acceptEdits",
            command_kind="text_only",
            expected_tool_use=False,
            expected_file_change=False,
            timeout_seconds=60,
            safety_notes=[
                "只验证文本输出，不触发 tool-use",
                "不创建文件",
                "预期秒级返回（< 30 秒）",
            ],
        ))

    return StabilityValidationPlanResult(
        plan_id="L1-dry-run-plan",
        layer="1",
        dry_run=True,
        command_count=len(commands),
        commands=commands,
        real_task_execution="no",
        run_project_task_full_called="no",
        claude_code_called="no",
        bypass_permissions_used="no",
        business_code_changed="no",
        framework_code_changed="no",
        auto_continue_to_next_task=False,
        auto_git_backup=False,
        human_review_required=True,
        check_result="pass",
        next_action="ready_for_T113_layer_1_execution",
        message="Layer 1 text-only stability dry-run plan: 6 commands (3x default + 3x acceptEdits), all text-only, no Claude Code called.",
    )


# ---------------------------------------------------------------------------
# Layer 2: Controlled Single-file Tool-use Dry-run Plan
# ---------------------------------------------------------------------------

def build_layer_2_tool_use_stability_plan() -> StabilityValidationPlanResult:
    """生成 Layer 2 受控单文件 tool-use 稳定性验证 dry-run 计划。

    3 次调用：acceptEdits + 创建临时诊断文件。
    不调用 Claude Code，只生成计划。不创建目标文件。
    """
    target_files = [
        "reports/diagnostics/tool-use/T114-tool-use-check-01.txt",
        "reports/diagnostics/tool-use/T114-tool-use-check-02.txt",
        "reports/diagnostics/tool-use/T114-tool-use-check-03.txt",
    ]

    commands: List[StabilityValidationCommandPlan] = []

    for i, target in enumerate(target_files, 1):
        commands.append(StabilityValidationCommandPlan(
            layer="2",
            scenario_id=f"L2-tool-use-{i:02d}",
            description=f"Layer 2 controlled tool-use test #{i}: create {target}",
            permission_mode="acceptEdits",
            command_kind="tool_use",
            expected_tool_use=True,
            expected_file_change=True,
            timeout_seconds=120,
            target_file=target,
            safety_notes=[
                "只在 reports/diagnostics/tool-use/ 目录下创建文件",
                "不使用 bypassPermissions",
                "不修改业务代码",
                "不修改框架代码",
                "任何一次 timeout 立即停止",
                "本轮 dry-run 不创建目标文件",
            ],
        ))

    return StabilityValidationPlanResult(
        plan_id="L2-dry-run-plan",
        layer="2",
        dry_run=True,
        command_count=len(commands),
        commands=commands,
        real_task_execution="no",
        run_project_task_full_called="no",
        claude_code_called="no",
        bypass_permissions_used="no",
        business_code_changed="no",
        framework_code_changed="no",
        auto_continue_to_next_task=False,
        auto_git_backup=False,
        human_review_required=True,
        check_result="pass",
        next_action="ready_for_T114_layer_2_execution",
        message="Layer 2 tool-use stability dry-run plan: 3 commands (acceptEdits + file creation), no Claude Code called, no target files created.",
    )


# ---------------------------------------------------------------------------
# Layer 3: Runner-level Minimal Claude Call Dry-run Plan
# ---------------------------------------------------------------------------

def build_layer_3_runner_level_stability_plan() -> StabilityValidationPlanResult:
    """生成 Layer 3 runner 封装最小调用 dry-run 计划。

    2 次调用：text-only via runner + controlled tool-use via runner。
    不调用 Claude Code，不进入 run-project-task-full。
    """
    commands: List[StabilityValidationCommandPlan] = [
        StabilityValidationCommandPlan(
            layer="3",
            scenario_id="L3-runner-text-01",
            description="Layer 3 runner-level text-only test: call run_claude_code() with minimal text prompt",
            permission_mode="default",
            command_kind="runner_text_only",
            expected_tool_use=False,
            expected_file_change=False,
            timeout_seconds=60,
            target_file="",
            safety_notes=[
                "通过 runner 封装调用 Claude Code",
                "不进入 run-project-task-full",
                "只验证 text-only 最小路径",
                "不修改业务代码",
                "不修改框架代码",
            ],
        ),
        StabilityValidationCommandPlan(
            layer="3",
            scenario_id="L3-runner-tool-use-01",
            description="Layer 3 runner-level tool-use test: call run_claude_code() to create a temp file",
            permission_mode="acceptEdits",
            command_kind="runner_tool_use",
            expected_tool_use=True,
            expected_file_change=True,
            timeout_seconds=120,
            target_file="reports/diagnostics/runner/T115-runner-check-01.txt",
            safety_notes=[
                "通过 runner 封装调用 Claude Code",
                "不进入 run-project-task-full",
                "只在 reports/diagnostics/runner/ 目录下创建文件",
                "不修改业务代码",
                "不修改框架代码",
                "本轮 dry-run 不创建目标文件",
            ],
        ),
    ]

    return StabilityValidationPlanResult(
        plan_id="L3-dry-run-plan",
        layer="3",
        dry_run=True,
        command_count=len(commands),
        commands=commands,
        real_task_execution="no",
        run_project_task_full_called="no",
        claude_code_called="no",
        bypass_permissions_used="no",
        business_code_changed="no",
        framework_code_changed="no",
        auto_continue_to_next_task=False,
        auto_git_backup=False,
        human_review_required=True,
        check_result="pass",
        next_action="ready_for_T115_layer_3_execution",
        message="Layer 3 runner-level dry-run plan: 2 commands (text-only + tool-use via runner), no Claude Code called, no run-project-task-full.",
    )


# ---------------------------------------------------------------------------
# Report Skeleton Generator
# ---------------------------------------------------------------------------

def build_stability_report_skeleton(layer: str) -> str:
    """根据 layer 生成稳定性验证报告 skeleton markdown。

    Args:
        layer: "1" / "2" / "3"

    Returns:
        Markdown 字符串。
    """
    if layer == "1":
        return _build_layer_1_report_skeleton()
    elif layer == "2":
        return _build_layer_2_report_skeleton()
    elif layer == "3":
        return _build_layer_3_report_skeleton()
    else:
        return f"# Error: Unknown layer '{layer}'\n\nNo report skeleton available.\n"


def _build_layer_1_report_skeleton() -> str:
    return """# Layer 1 Stability Validation Check

## Goal

验证 Claude Code 文本输出路径在连续多次调用中保持稳定，不触发 tool-use，不写文件，不修改项目。

## Planned Commands

| # | Scenario ID | Permission Mode | Kind | Timeout |
|---|-------------|-----------------|------|---------|
| 1 | L1-default-text-01 | default | text_only | 60s |
| 2 | L1-default-text-02 | default | text_only | 60s |
| 3 | L1-default-text-03 | default | text_only | 60s |
| 4 | L1-acceptedits-text-01 | acceptEdits | text_only | 60s |
| 5 | L1-acceptedits-text-02 | acceptEdits | text_only | 60s |
| 6 | L1-acceptedits-text-03 | acceptEdits | text_only | 60s |

## Expected Result

- 6/6 全部 pass
- 每次输出包含 "OK" 或等价确认
- 无 tool-use 触发
- 无文件变更
- 无超时
- 全部秒级返回（< 30 秒）

## Actual Result

*(待 T113 执行后填写)*

## Timeout Settings

- 每次调用超时上限：60 秒

## Permission Mode

- 测试 1-3：default（不传 --permission-mode）
- 测试 4-6：acceptEdits（--permission-mode acceptEdits）

## Stdout/Stderr Summary

*(待 T113 执行后填写)*

## Changed Files

*(待 T113 执行后填写)*

## Safety Check

| 检查项 | 结果 |
|--------|------|
| 是否运行 run-project-task-full | no |
| 是否调用 Claude Code | *(待 T113 执行后填写)* |
| 是否执行真实任务 | no |
| 是否修改业务代码 | no |
| 是否修改框架代码 | no |
| 是否使用 bypassPermissions | no |
| 是否自动 Git backup | no |

## Check Result

*(待 T113 执行后填写)*

```text
LAYER_1_STATUS=pending
TEXT_ONLY_STABILITY=pending
DEFAULT_TEXT_PASS_COUNT=0/3
ACCEPTEDITS_TEXT_PASS_COUNT=0/3
```

## Next

T113：执行 Layer 1 text-only stability validation
"""


def _build_layer_2_report_skeleton() -> str:
    return """# Layer 2 Stability Validation Check

## Goal

验证受控 tool-use 写文件是否稳定，只在安全路径下创建临时诊断文件。

## Planned Commands

| # | Scenario ID | Permission Mode | Kind | Target File | Timeout |
|---|-------------|-----------------|------|-------------|---------|
| 1 | L2-tool-use-01 | acceptEdits | tool_use | reports/diagnostics/tool-use/T114-tool-use-check-01.txt | 120s |
| 2 | L2-tool-use-02 | acceptEdits | tool_use | reports/diagnostics/tool-use/T114-tool-use-check-02.txt | 120s |
| 3 | L2-tool-use-03 | acceptEdits | tool_use | reports/diagnostics/tool-use/T114-tool-use-check-03.txt | 120s |

## Expected Result

- 3/3 成功创建
- 文件内容正确（包含 "diagnostic ok"）
- 无超时
- 无额外文件变更
- 无业务代码变更
- 无框架代码变更

## Actual Result

*(待 T114 执行后填写)*

## Timeout Settings

- 每次调用超时上限：120 秒

## Permission Mode

- 全部使用 acceptEdits（--permission-mode acceptEdits）

## Stdout/Stderr Summary

*(待 T114 执行后填写)*

## Changed Files

*(待 T114 执行后填写)*

## Safety Check

| 检查项 | 结果 |
|--------|------|
| 是否运行 run-project-task-full | no |
| 是否调用 Claude Code | *(待 T114 执行后填写)* |
| 是否执行真实任务 | no |
| 是否修改业务代码 | no |
| 是否修改框架代码 | no |
| 是否使用 bypassPermissions | no |
| 是否自动 Git backup | no |

## Check Result

*(待 T114 执行后填写)*

```text
LAYER_2_STATUS=pending
TOOL_USE_STABILITY=pending
TOOL_USE_TEST_1=pending
TOOL_USE_TEST_2=pending
TOOL_USE_TEST_3=pending
TOOL_USE_PASS_COUNT=0/3
```

## Next

T114：执行 Layer 2 controlled single-file tool-use stability validation
"""


def _build_layer_3_report_skeleton() -> str:
    return """# Layer 3 Stability Validation Check

## Goal

验证 runner 封装层调用 Claude Code 的最小路径，不进入 run-project-task-full。

## Planned Commands

| # | Scenario ID | Permission Mode | Kind | Target File | Timeout |
|---|-------------|-----------------|------|-------------|---------|
| 1 | L3-runner-text-01 | default | runner_text_only | (none) | 60s |
| 2 | L3-runner-tool-use-01 | acceptEdits | runner_tool_use | reports/diagnostics/runner/T115-runner-check-01.txt | 120s |

## Expected Result

- 2/2 全部 pass
- runner 封装调用正常
- permission_mode 正确传递
- stdout/stderr 正确捕获
- 无业务代码变更
- 无框架代码变更

## Actual Result

*(待 T115 执行后填写)*

## Timeout Settings

- text-only: 60 秒
- tool-use: 120 秒

## Permission Mode

- 测试 1：default（不传 --permission-mode）
- 测试 2：acceptEdits（--permission-mode acceptEdits）

## Stdout/Stderr Summary

*(待 T115 执行后填写)*

## Changed Files

*(待 T115 执行后填写)*

## Safety Check

| 检查项 | 结果 |
|--------|------|
| 是否运行 run-project-task-full | no |
| 是否调用 Claude Code | *(待 T115 执行后填写)* |
| 是否执行真实任务 | no |
| 是否修改业务代码 | no |
| 是否修改框架代码 | no |
| 是否使用 bypassPermissions | no |
| 是否自动 Git backup | no |

## Check Result

*(待 T115 执行后填写)*

```text
LAYER_3_STATUS=pending
RUNNER_LEVEL_CLAUDE_CALL=pending
RUNNER_TEXT_ONLY=pending
RUNNER_TOOL_USE=pending
RUNNER_PERMISSION_MODE_CORRECT=pending
```

## Next

T115：执行 Layer 3 runner-level minimal Claude call validation
"""


# ---------------------------------------------------------------------------
# CLI 入口辅助
# ---------------------------------------------------------------------------

def build_stability_plan_for_layer(layer: str) -> StabilityValidationPlanResult:
    """根据 layer 字符串构建 dry-run 计划。

    Args:
        layer: "1" / "2" / "3" / "all"

    Returns:
        StabilityValidationPlanResult
    """
    if layer == "1":
        return build_layer_1_text_only_stability_plan()
    elif layer == "2":
        return build_layer_2_tool_use_stability_plan()
    elif layer == "3":
        return build_layer_3_runner_level_stability_plan()
    elif layer == "all":
        return _build_all_layers_plan()
    else:
        return StabilityValidationPlanResult(
            plan_id="invalid",
            layer=layer,
            dry_run=True,
            command_count=0,
            commands=[],
            real_task_execution="no",
            run_project_task_full_called="no",
            claude_code_called="no",
            bypass_permissions_used="no",
            business_code_changed="no",
            framework_code_changed="no",
            auto_continue_to_next_task=False,
            auto_git_backup=False,
            human_review_required=True,
            check_result="fail",
            next_action="stop",
            message=f"Invalid layer '{layer}'. Must be 1, 2, 3, or all.",
        )


def _build_all_layers_plan() -> StabilityValidationPlanResult:
    """构建所有层（1+2+3）的合并 dry-run 计划。"""
    l1 = build_layer_1_text_only_stability_plan()
    l2 = build_layer_2_tool_use_stability_plan()
    l3 = build_layer_3_runner_level_stability_plan()

    all_commands = l1.commands + l2.commands + l3.commands

    return StabilityValidationPlanResult(
        plan_id="L1-L2-L3-dry-run-plan",
        layer="all",
        dry_run=True,
        command_count=len(all_commands),
        commands=all_commands,
        real_task_execution="no",
        run_project_task_full_called="no",
        claude_code_called="no",
        bypass_permissions_used="no",
        business_code_changed="no",
        framework_code_changed="no",
        auto_continue_to_next_task=False,
        auto_git_backup=False,
        human_review_required=True,
        check_result="pass",
        next_action="ready_for_T113_layer_1_execution",
        message=f"All layers (1+2+3) dry-run plan: {len(all_commands)} commands total, no Claude Code called.",
    )
