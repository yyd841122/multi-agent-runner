# T093 Dev Report

## Task

实现 simulated first real-run acceptance parser。

## Scope

本轮只实现模拟验收解析器和 CLI，不真实调用 run-project-task-full，不调用 Claude Code，不修改业务代码。

## Changed Files

- tools/continuous_task_planner.py（新增 _SIMULATED_ACCEPTANCE_SAMPLES + run_simulated_first_real_run_acceptance_parser）
- runner.py（新增 simulated-first-real-run-acceptance CLI + import）
- reports/dev/T093-dev-report.md（新增，本文件）
- reports/checks/T093-simulated-acceptance-check.md（新增，验证报告）
- docs/tasks.md（状态更新）

## Implementation

### _SIMULATED_ACCEPTANCE_SAMPLES

8 个内置 sample，覆盖所有验收状态：

| # | Sample | ACCEPTANCE_STATUS | CHECK_RESULT | STOP_REASON |
|---|--------|-------------------|--------------|-------------|
| 1 | pass | ready_for_human_review | pass | first_real_execution_requires_review |
| 2 | pass-dirty-reports | ready_for_human_review | pass | first_real_execution_requires_review |
| 3 | fail | blocked | fail | child_check_result_failed |
| 4 | missing-check-result | failed_to_parse | fail | missing_check_result |
| 5 | unsafe-unknown | unsafe_to_continue | fail | dirty_unknown |
| 6 | dirty-unexpected | blocked | fail | dirty_unexpected |
| 7 | missing-report-paths | blocked | fail | missing_report_paths |
| 8 | task-status-failed | blocked | fail | child_task_status_failed |

每个 sample 包含：
- stdout：模拟子命令 KEY=value 输出
- workspace_after / workspace_classification：模拟 workspace 状态
- claude_code_called / business_code_changed：推断字段
- expected_acceptance_status：预期验收状态（用于测试断言）

### run_simulated_first_real_run_acceptance_parser()

链式调用：
1. 从 _SIMULATED_ACCEPTANCE_SAMPLES 获取 sample 数据
2. parse_child_command_output() 解析 stdout
3. evaluate_first_real_run_acceptance() 评估验收状态
4. 返回 FirstRealRunAcceptanceResult

未知 sample 名时抛出 ValueError。

### simulated-first-real-run-acceptance CLI

runner.py 新增命令，支持 --sample 参数，8 个内置 sample。

安全覆盖字段（无论 sample 数据如何）：
- REAL_TASK_EXECUTION=no
- RUN_PROJECT_TASK_FULL_CALLED=no
- CLAUDE_CODE_CALLED=no
- BUSINESS_CODE_CHANGED=no

## Behavior

### ready_for_human_review（pass, pass-dirty-reports）

正常成功路径，check_result=pass，但仍停止等待人工验收。

### blocked（fail, dirty-unexpected, missing-report-paths, task-status-failed）

任一失败条件命中，不自动继续：
- fail → child_check_result_failed
- dirty-unexpected → review_unexpected_changes
- missing-report-paths → check_report_generation
- task-status-failed → review_failure_before_continue

### failed_to_parse（missing-check-result）

解析失败，child_check_result=missing，不保留 parser 降级值。

### unsafe_to_continue（unsafe-unknown）

workspace dirty_unknown，需要人工审查所有变更。

## Safety Rules

- no run-project-task-full call：模拟验证，SAFETY OVERRIDE 显示 no
- no Claude Code call：parse → evaluate 链路不调用外部命令
- no business code modification：只做判断和输出
- no auto-continue：auto_continue_to_next_task 始终 False
- no auto Git backup：auto_git_backup 始终 False
- human review always required：human_review_required 始终 True

## Verification

| # | 场景 | 验证方式 | 结果 |
|---|------|----------|------|
| 1 | pass + clean + report_paths | CLI + 函数 | PASS |
| 2 | pass + dirty_reports_only | CLI + 函数 | PASS |
| 3 | check_result=fail | CLI + 函数 | PASS |
| 4 | 缺少 CHECK_RESULT | CLI + 函数 | PASS |
| 5 | dirty_unknown | CLI + 函数 | PASS |
| 6 | dirty_unexpected | CLI + 函数 | PASS |
| 7 | report_paths 缺失 | CLI + 函数 | PASS |
| 8 | task_status=failed | CLI + 函数 | PASS |
| 9 | unknown sample name | CLI | ValueError PASS |
| 10 | SAFETY OVERRIDE 字段 | CLI | PASS |

函数级断言：53/53 全部 PASS（含 32 个安全约束 + 12 个关键字段断言）。

## Next

T094：验证 first real-run acceptance pass/fail 场景
