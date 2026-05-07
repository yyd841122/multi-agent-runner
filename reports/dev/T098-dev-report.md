# T098 Dev Report

## Task

实现 first real-run executor simulated child call。

## Scope

本轮只实现 simulated child call，不真实调用 run-project-task-full，不调用 Claude Code，不修改业务代码。

## Changed Files

- tools/continuous_task_planner.py（新增 FirstRealRunExecutorSimulatedResult + run_first_real_run_executor_simulated_child_call + _SIMULATED_CHILD_SAMPLES）
- runner.py（新增 --simulate-child + --child-sample CLI 参数 + simulated child call 分支）
- reports/checks/T098-first-real-run-executor-simulated-child-call-check.md（新增，验证报告）
- reports/dev/T098-dev-report.md（新增，本文件）
- docs/tasks.md（状态更新）

## Implementation

### FirstRealRunExecutorSimulatedResult

新增数据结构，28 个字段，覆盖：

- 标识：project、run_id、task_id、execution_mode
- Safety gate：safety_gate_status、real_execute_allowed
- Simulated child：simulated_child_call、child_sample、child_stdout_present、child_stderr_present、child_exit_code
- Child 结果：child_check_result、child_task_status、parse_check_result
- Acceptance：acceptance_status、workspace_status_before、workspace_status_after、workspace_change_classification
- 安全标记：real_task_execution="no"、run_project_task_full_called="no"、claude_code_called="no"、business_code_changed="no"
- 安全限制：auto_continue_to_next_task="false"、auto_git_backup="false"、human_review_required="true"
- 诊断：check_result、stop_reason、next_action、message

### _SIMULATED_CHILD_SAMPLES

内置 6 种 child sample：

| Sample | CHILD_CHECK_RESULT | ACCEPTANCE_STATUS |
|--------|--------------------|-------------------|
| pass | pass | ready_for_human_review |
| fail | fail | blocked |
| missing-check-result | unknown | failed_to_parse |
| dirty-unexpected | pass | blocked |
| unsafe-unknown | pass | unsafe_to_continue |
| missing-report-paths | pass | blocked |

每个 sample 包含 stdout 模板、workspace 状态、expected acceptance status。

### run_first_real_run_executor_simulated_child_call()

新增函数，执行链路：

1. 调用 validate_first_real_run_execute_once_safety() 做三重确认
2. safety gate 不通过 → 直接返回失败结果
3. 验证 sample 存在
4. 构造 simulated child stdout（不执行任何真实命令）
5. 调用 parse_child_command_output() 解析
6. 调用 evaluate_first_real_run_acceptance() 评估验收状态
7. 构造完整 FirstRealRunExecutorSimulatedResult

### run-project-loop --simulate-child --child-sample

新增两个 CLI 参数：

```
--simulate-child    必须 --execute + --real-call + --real-call-run-once + --real-execute-once + --real-execute-confirm
--child-sample      指定 sample 名称（默认 pass）
```

依赖链：

```
--execute → --confirm EXECUTE_PROJECT_LOOP
  → --real-call → --real-confirm EXECUTE_REAL_TASK_ONCE
    → --real-call-run-once
      → --real-execute-once → --real-execute-confirm EXECUTE_REAL_RUN_ONCE
        → --simulate-child → --child-sample <sample>
```

## Behavior

- 三重确认通过后才允许 simulated child call
- 根据 sample 构造 child stdout，不执行任何真实命令
- parse_child_command_output() 解析 KEY=value 格式
- evaluate_first_real_run_acceptance() 评估验收状态
- pass/fail 后都停止，不自动进入下一任务

## Safety Rules

- no run-project-task-full call：run_project_task_full_called="no"（硬编码）
- no Claude Code call：claude_code_called="no"（硬编码）
- no business code modification：business_code_changed="no"（硬编码）
- no auto-continue：auto_continue_to_next_task="false"（硬编码）
- no auto Git backup：auto_git_backup="false"（硬编码）
- human review always required：human_review_required="true"（硬编码）

## Verification

14 个验证场景全部 PASS（4 CLI 拒绝 + 6 sample 函数级验证 + 1 错误 sample + 3 安全字段验证）。

详细结果见：reports/checks/T098-first-real-run-executor-simulated-child-call-check.md

## Next

T099：验证 simulated real execution pass/fail
