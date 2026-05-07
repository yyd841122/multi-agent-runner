# T096 Dev Report

## Task

实现 first real-run execute-once safety gate。

## Scope

本轮只实现真实执行前 safety gate（第三重确认 + 新参数 + preflight 扩展），不真实调用 run-project-task-full，不调用 Claude Code，不修改业务代码。

## Changed Files

- tools/continuous_task_planner.py（新增 FirstRealRunExecuteOnceSafetyResult + validate_first_real_run_execute_once_safety + REAL_EXECUTE_CONFIRM_PHRASE）
- runner.py（新增 --real-execute-once + --real-execute-confirm CLI 参数 + execute-once safety gate 分支）
- reports/checks/T096-first-real-run-execute-once-safety-gate-check.md（新增，验证报告）
- reports/dev/T096-dev-report.md（新增，本文件）
- docs/tasks.md（状态更新）

## Implementation

### FirstRealRunExecuteOnceSafetyResult

新增数据结构，25 个字段，覆盖：

- 三重确认状态：execute_confirm_status、real_confirm_status、real_execute_confirm_status
- 执行控制：real_execute_once_requested、real_execute_allowed
- 安全标记：real_task_execution="no"、run_project_task_full_called="no"、claude_code_called="no"、business_code_changed="no"
- 安全限制：auto_continue_to_next_task="false"、auto_git_backup="false"、human_review_required="true"
- 诊断：check_result、stop_reason、next_action、message

### REAL_EXECUTE_CONFIRM_PHRASE

新增常量 `REAL_EXECUTE_CONFIRM_PHRASE = "EXECUTE_REAL_RUN_ONCE"`。

三个确认短语不能互相替代：
- EXECUTE_PROJECT_LOOP → --confirm
- EXECUTE_REAL_TASK_ONCE → --real-confirm
- EXECUTE_REAL_RUN_ONCE → --real-execute-confirm

### validate_first_real_run_execute_once_safety()

新增函数，检查顺序：

1. 无 --real-execute-once → 返回不请求结果
2. 模式互斥检查（--real-call-dry-run、--adapter-dry-run、--real-call-stub、--dry-run）
3. 复用 validate_real_call_safety() 做双重确认前置检查
4. 第三重确认缺失 → real_execute_confirm_missing
5. 第三重确认错误 → real_execute_confirm_rejected
6. max_tasks != 1 → max_tasks_not_one
7. planned task 为空 → no_planned_tasks
8. workspace dirty → workspace_not_clean
9. 全部通过 → real_execute_allowed=true

### run-project-loop --real-execute-once --real-execute-confirm

新增两个 CLI 参数，依赖链：

```
--execute → --confirm EXECUTE_PROJECT_LOOP → --real-call → --real-confirm EXECUTE_REAL_TASK_ONCE → --real-call-run-once → --real-execute-once → --real-execute-confirm EXECUTE_REAL_RUN_ONCE
```

## Behavior

- 三重确认：EXECUTE_PROJECT_LOOP + EXECUTE_REAL_TASK_ONCE + EXECUTE_REAL_RUN_ONCE
- max_tasks=1 only（不等于 1 时拒绝）
- preflight check 复用已有 validate_real_call_safety() + 新增第三重确认
- 本轮不执行真实调用（safety gate only）
- pass 后 next_action=ready_for_T098_simulated_child_call
- 不带 --real-execute-once 时保持 T085 --real-call-run-once safety shell 行为不变

## Safety Rules

- no run-project-task-full call：run_project_task_full_called="no"（硬编码）
- no Claude Code call：claude_code_called="no"（硬编码）
- no business code modification：business_code_changed="no"（硬编码）
- no auto-continue：auto_continue_to_next_task="false"（硬编码）
- no auto Git backup：auto_git_backup="false"（硬编码）
- human review required：human_review_required="true"（硬编码）

## Verification

16 个验证场景全部 PASS（函数级断言 + CLI 层实测）。

详细结果见：reports/checks/T096-first-real-run-execute-once-safety-gate-check.md

## Next

T097：验证 execute-once 拒绝场景（clean workspace 下完整验证）
