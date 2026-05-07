# T112 Dev Report

## Task

实现 stability validation helper dry-run/report skeleton。

## Scope

本轮只实现 dry-run plan 和 report skeleton，不调用 Claude Code，不执行真实任务。

## Changed Files

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| tools/claude_stability_validator.py | new | 稳定性验证 dry-run 规划模块 |
| runner.py | modified | 新增 claude-stability-plan CLI 命令 |
| reports/checks/T112-stability-validation-helper-dry-run-check.md | new | 验证报告 |
| reports/dev/T112-dev-report.md | new | 本文件 |

## Implementation

### tools/claude_stability_validator.py

新增模块，包含以下内容：

**数据结构：**

- `StabilityValidationCommandPlan`: 单条验证命令的 dry-run 计划（layer, scenario_id, description, permission_mode, command_kind, expected_tool_use, expected_file_change, timeout_seconds, target_file, safety_notes）
- `StabilityValidationPlanResult`: 一层或多层验证的 dry-run 计划结果（20 个字段，包含全部安全输出字段）

**函数：**

- `build_layer_1_text_only_stability_plan()`: Layer 1 dry-run 计划，6 次调用（3x default + 3x acceptEdits text-only），timeout=60s
- `build_layer_2_tool_use_stability_plan()`: Layer 2 dry-run 计划，3 次调用（acceptEdits + 创建临时文件），timeout=120s，目标文件 `reports/diagnostics/tool-use/T114-tool-use-check-0{1,2,3}.txt`
- `build_layer_3_runner_level_stability_plan()`: Layer 3 dry-run 计划，2 次调用（text-only via runner + tool-use via runner），timeout=60s/120s
- `build_stability_report_skeleton(layer)`: 根据 layer 生成报告 skeleton markdown
- `build_stability_plan_for_layer(layer)`: CLI 入口辅助，支持 "1"/"2"/"3"/"all"/invalid

### runner.py

新增 `claude-stability-plan` CLI 命令：

```
python runner.py claude-stability-plan --layer <1|2|3|all> [--skeleton]
```

行为：
- 只输出计划，不调用 Claude Code
- 不执行命令
- 不写诊断目标文件
- 不运行 run-project-task-full
- `--skeleton` 可选显示报告 skeleton preview

输出字段：
- STABILITY_PLAN_STATUS, LAYER, DRY_RUN, COMMAND_COUNT
- REAL_TASK_EXECUTION, RUN_PROJECT_TASK_FULL_CALLED
- CLAUDE_CODE_CALLED, BYPASS_PERMISSIONS_USED, CHECK_RESULT

## Safety Result

| 检查项 | 结果 |
|--------|------|
| 是否运行 run-project-task-full | no |
| 是否调用 Claude Code | no |
| 是否执行真实任务 | no |
| 是否使用 bypassPermissions | no |
| 是否修改业务代码 | no |
| 是否修改框架代码 | no（runner.py 新增命令入口，非框架核心逻辑） |
| 是否创建诊断目标文件 | no |
| 是否自动 Git backup | no |

## Verification

13/13 验证场景全部 PASS：

| # | Scenario | Result |
|---|----------|--------|
| 1 | layer=1 → 6 commands | PASS |
| 2 | layer=2 → 3 commands | PASS |
| 3 | layer=3 → 2 commands | PASS |
| 4 | layer=all → 11 commands | PASS |
| 5 | layer=invalid → fail | PASS |
| 6 | skeleton layer=1 | PASS |
| 7 | skeleton layer=2 | PASS |
| 8 | skeleton layer=3 | PASS |
| 9 | CLAUDE_CODE_CALLED=no | PASS |
| 10 | RUN_PROJECT_TASK_FULL_CALLED=no | PASS |
| 11 | BYPASS_PERMISSIONS_USED=no | PASS |
| 12 | BUSINESS_CODE_CHANGED=no | PASS |
| 13 | no diagnostics files created | PASS |

## Next

T113：执行 Layer 1 text-only stability validation
