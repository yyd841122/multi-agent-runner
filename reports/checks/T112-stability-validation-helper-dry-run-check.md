# T112 Stability Validation Helper Dry-run Check

## Goal

验证 stability validation helper 的 dry-run plan 和 report skeleton 生成能力，确认不调用 Claude Code、不执行真实任务、不创建诊断目标文件。

## Verification Scenarios

### 1. layer=1 → 6 commands

**Input**: `python runner.py claude-stability-plan --layer 1`

**Expected**: COMMAND_COUNT=6, CHECK_RESULT=pass

**Actual**: COMMAND_COUNT=6, CHECK_RESULT=pass

**Result**: PASS

### 2. layer=2 → 3 commands

**Input**: `python runner.py claude-stability-plan --layer 2`

**Expected**: COMMAND_COUNT=3, CHECK_RESULT=pass

**Actual**: COMMAND_COUNT=3, CHECK_RESULT=pass

**Result**: PASS

### 3. layer=3 → 2 commands

**Input**: `python runner.py claude-stability-plan --layer 3`

**Expected**: COMMAND_COUNT=2, CHECK_RESULT=pass

**Actual**: COMMAND_COUNT=2, CHECK_RESULT=pass

**Result**: PASS

### 4. layer=all → 11 commands total

**Input**: `python runner.py claude-stability-plan --layer all`

**Expected**: COMMAND_COUNT=11, CHECK_RESULT=pass

**Actual**: COMMAND_COUNT=11, CHECK_RESULT=pass

**Result**: PASS

### 5. layer=invalid → fail

**Input**: `python runner.py claude-stability-plan --layer invalid`

**Expected**: COMMAND_COUNT=0, CHECK_RESULT=fail

**Actual**: COMMAND_COUNT=0, CHECK_RESULT=fail

**Result**: PASS

### 6. report skeleton layer=1 包含 Goal / Planned Commands / Safety Check

**Input**: `build_stability_report_skeleton("1")`

**Expected**: 包含 "Goal", "Planned Commands", "Safety Check" 章节

**Actual**: 包含 "## Goal", "## Planned Commands", "## Safety Check" 章节

**Result**: PASS

### 7. report skeleton layer=2 包含 controlled tool-use

**Input**: `build_stability_report_skeleton("2")`

**Expected**: 包含 "tool_use" 或 "controlled tool-use"

**Actual**: 包含 "tool_use" 和 "reports/diagnostics/tool-use/"

**Result**: PASS

### 8. report skeleton layer=3 包含 runner-level

**Input**: `build_stability_report_skeleton("3")`

**Expected**: 包含 "runner" 或 "runner-level"

**Actual**: 包含 "runner_text_only", "runner_tool_use", "reports/diagnostics/runner/"

**Result**: PASS

### 9. 所有 plan 均 CLAUDE_CODE_CALLED=no

**Expected**: layer=1/2/3/all 的 CLAUDE_CODE_CALLED=no

**Actual**: 全部 CLAUDE_CODE_CALLED=no

**Result**: PASS

### 10. 所有 plan 均 RUN_PROJECT_TASK_FULL_CALLED=no

**Expected**: layer=1/2/3/all 的 RUN_PROJECT_TASK_FULL_CALLED=no

**Actual**: 全部 RUN_PROJECT_TASK_FULL_CALLED=no

**Result**: PASS

### 11. 所有 plan 均 BYPASS_PERMISSIONS_USED=no

**Expected**: layer=1/2/3/all 的 BYPASS_PERMISSIONS_USED=no

**Actual**: 全部 BYPASS_PERMISSIONS_USED=no

**Result**: PASS

### 12. 所有 plan 均不修改业务代码

**Expected**: BUSINESS_CODE_CHANGED=no

**Actual**: 全部 BUSINESS_CODE_CHANGED=no

**Result**: PASS

### 13. 不创建 reports/diagnostics/tool-use 目标文件

**Expected**: reports/diagnostics/tool-use/ 目录不存在

**Actual**: 目录不存在（dry-run 不创建文件）

**Result**: PASS

## Summary

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

**Total: 13/13 PASS**

## Safety Check

| 检查项 | 结果 |
|--------|------|
| 是否运行 run-project-task-full | no |
| 是否调用 Claude Code | no |
| 是否执行真实任务 | no |
| 是否使用 bypassPermissions | no |
| 是否修改业务代码 | no |
| 是否创建诊断目标文件 | no |
| 是否自动 Git backup | no |

## Check Result

```text
CHECK_RESULT=pass
ALL_SCENARIOS_PASS=13/13
CLAUDE_CODE_CALLED=no
REAL_TASK_EXECUTION=no
NEXT_ACTION=ready_for_report_and_task_update
```
