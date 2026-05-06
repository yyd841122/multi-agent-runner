# T092 Dev Report

## Task

实现 first real-run acceptance result model。

## Scope

本轮只实现验收结果模型和评估函数，不真实调用 run-project-task-full，不调用 Claude Code，不修改业务代码。

## Changed Files

- tools/continuous_task_planner.py（新增 FirstRealRunAcceptanceResult + evaluate_first_real_run_acceptance）
- runner.py（新增 first-real-run-acceptance-dry-run CLI + import）
- reports/checks/T092-first-real-run-acceptance-model-check.md（新增，验证报告）
- reports/dev/T092-dev-report.md（新增，本文件）
- docs/tasks.md（状态更新）

## Implementation

### FirstRealRunAcceptanceResult

26 字段数据结构，覆盖首次真实调用后的所有验收需求：

- 标识字段：run_id, project, task_id, execution_mode
- 执行状态：real_task_execution, run_project_task_full_called
- 子调用结果：child_exit_code, child_check_result, child_task_status
- 解析状态：parsed_stdout_status, parsed_stderr_status
- 推断字段：claude_code_called, business_code_changed
- Workspace：workspace_status_before, workspace_status_after, workspace_change_classification
- 报告：report_paths
- 验收决策：human_review_required, auto_continue_to_next_task, auto_git_backup, acceptance_status, acceptance_required_reason, stop_reason, next_action, check_result
- 消息：message

### evaluate_first_real_run_acceptance()

接收 ChildCommandParseResult，按优先级判断验收状态：

1. **failed_to_parse**（最高）：parse_check_result=fail 或缺少 CHECK_RESULT
2. **blocked**：check_result=fail / task_status=failed / dirty_unexpected / report_paths 缺失
3. **unsafe_to_continue**：dirty_unknown
4. **ready_for_human_review**（最低）：所有条件满足

### first-real-run-acceptance-dry-run CLI

新增命令，5 个内置样例：

- `pass`：正常成功，workspace clean
- `pass-dirty-reports`：成功，只有报告变更
- `fail`：任务失败
- `missing-check-result`：缺少 CHECK_RESULT
- `unsafe-unknown`：workspace dirty_unknown

## Behavior

### ready_for_human_review

满足所有条件时输出。check_result=pass，但仍停止等待人工验收。

### blocked

任一失败条件命中时输出。check_result=fail，不自动继续。

### failed_to_parse

解析失败时输出。child_check_result 设为 missing（不保留 parser 降级的 unknown）。

### unsafe_to_continue

workspace 无法分类时输出。check_result=fail，需要人工审查所有变更。

### unknown 字段处理

- unknown 字段保留为 unknown，不写成 no
- unknown + clean workspace → 仍为 ready_for_human_review（降级，不阻塞）
- unknown + dirty_unknown → unsafe_to_continue

## Safety Rules

- no run-project-task-full call：RUN_PROJECT_TASK_FULL_CALLED 只取参数值
- no Claude Code call：evaluate 函数不调用任何外部命令
- no business code modification：evaluate 函数只做判断
- no auto-continue：auto_continue_to_next_task 始终 False
- no auto Git backup：auto_git_backup 始终 False
- human review always required：human_review_required 始终 True

## Verification

| # | 场景 | 验证方式 | 结果 |
|---|------|----------|------|
| 1 | pass + clean + report_paths | CLI + 函数 | PASS |
| 2 | pass + dirty_reports_only | CLI + 函数 | PASS |
| 3 | pass + dirty_business_code | 函数 | PASS |
| 4 | check_result=fail | CLI + 函数 | PASS |
| 5 | task_status=failed | 函数 | PASS |
| 6 | 缺少 CHECK_RESULT | CLI + 函数 | PASS |
| 7 | report_paths 缺失 | 函数 | PASS |
| 8 | dirty_unexpected | 函数 | PASS |
| 9 | dirty_unknown | CLI + 函数 | PASS |
| 10 | unknown 字段 + clean | 函数 | PASS |

额外安全约束：49/49 断言全部 PASS（含 27 个跨场景安全约束）。

## Next

T093：实现 simulated first real-run acceptance parser
