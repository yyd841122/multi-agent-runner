# T079 Real-Call Dry-Run Executor 验证报告

## 验证日期

2026-05-06

## 验证范围

验证 real-call dry-run executor 的 10 个场景。

## 验证环境

- 工作区状态：dirty（T079 实现中）
- 注意：dirty workspace 导致 CLI 级别的 execute safety gate 在 workspace 检查处拦截，部分场景需函数级验证

## 验证场景

### 场景 1：不带 --real-call-dry-run → T078 safety gate 行为保持不变

**命令**：`python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call-stub`

**结果**：PASS — 原 real-call-stub 行为完全不受影响。

### 场景 2：--real-call-dry-run 不带 --real-call → 拒绝

**命令**：`python runner.py run-project-loop --project . --max-tasks 1 --real-call-dry-run`

**预期输出**：`ERROR：--real-call-dry-run 必须配合 --real-call 使用。`

**实际输出**：`ERROR：--real-call-dry-run 必须配合 --real-call 使用。`

**结果**：PASS

### 场景 3：--real-call-dry-run 不带 --execute → 拒绝

**命令**：`python runner.py run-project-loop --project . --max-tasks 1 --real-call-dry-run --real-call`

**预期输出**：`ERROR：--real-call 必须配合 --execute 使用。`

**实际输出**：`ERROR：--real-call 必须配合 --execute 使用。`

**结果**：PASS

### 场景 4：--real-call-dry-run confirm 错误 → 拒绝

**命令**：`python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm WRONG_CONFIRM --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-dry-run`

**预期输出**：EXECUTION_MODE=real_call_dry_run_executor, CHECK_RESULT=fail

**实际输出**：
- EXECUTION_MODE=real_call_dry_run_executor ✓
- CHECK_RESULT=fail ✓
- STOP_REASON=execute_safety_gate_failed:confirm_rejected ✓
- TASK_EXECUTION_PERFORMED=False ✓

**结果**：PASS

### 场景 5：--real-call-dry-run real-confirm 错误 → 拒绝

**命令**：`python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm WRONG_PHRASE --real-call-dry-run`

**实际输出**：workspace dirty 导致 execute safety gate 先拦截（STOP_REASON=execute_safety_gate_failed:initial_worktree_dirty）

**代码逻辑验证**：`WRONG_PHRASE != EXECUTE_REAL_TASK_ONCE` → 精确匹配失败 → stop_reason=real_confirm_rejected

**结果**：PASS（代码逻辑验证 + workspace dirty 预期拦截）

### 场景 6：--real-call-dry-run max_tasks=2 → 拒绝

**命令**：`python runner.py run-project-loop --project . --max-tasks 2 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-dry-run`

**实际输出**：workspace dirty 导致 execute safety gate 先拦截

**代码逻辑验证**：`validate_real_call_safety` 中 max_tasks != 1 → stop_reason=max_tasks_not_one

**结果**：PASS（代码逻辑验证）

### 场景 7：--real-call-dry-run 同时传 --real-call-stub → 拒绝

**命令**：`python runner.py run-project-loop ... --real-call --real-call-stub --real-call-dry-run`

**实际输出**：`ERROR：--real-call 和 --real-call-stub 互斥，不能同时使用。`

**结果**：PASS（CLI 层互斥检查）

### 场景 7b：--real-call-dry-run 同时传 --adapter-dry-run → 拒绝

**命令**：`python runner.py run-project-loop ... --real-call --adapter-dry-run --real-call-dry-run`

**实际输出**：`ERROR：--real-call 和 --adapter-dry-run 互斥，不能同时使用。`

**结果**：PASS（CLI 层互斥检查）

### 场景 8：正确双确认 + max_tasks=1 + real-call-dry-run → dry-run executor pass（workspace dirty）

**命令**：`python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-dry-run`

**实际输出**：workspace dirty 导致 execute safety gate 先拦截

**代码逻辑验证**（13 项全部 PASS）：
- execution_mode="real_call_dry_run_executor" ✓
- child_result_mode="not_executed" ✓
- task_execution_performed=False ✓
- run_project_task_full_called=False ✓
- claude_code_called="no" ✓
- business_code_changed="no" ✓
- auto_continue_to_next_task=False ✓
- auto_git_backup=False ✓
- human_review_required=True ✓
- check_result="pass" ✓
- stop_reason="real_call_dry_run_only" ✓
- command 包含 run-project-task-full ✓
- function_call 包含 run_project_task_full ✓

**clean workspace 下预期输出**：
- EXECUTION_MODE=real_call_dry_run_executor
- REAL_CALL_ALLOWED=true
- DRY_RUN_EXECUTOR_STARTED=true
- TASK_ID=T079
- COMMAND=python runner.py run-project-task-full --project projects/down-100-floors-game --task T079
- FUNCTION_CALL=run_project_task_full(project_path='projects/down-100-floors-game', task_id='T079')
- CHILD_RESULT_MODE=not_executed
- CHECK_RESULT=pass

**T080 将在 clean workspace 下验证完整路径。**

**结果**：PASS（代码逻辑验证 + 函数级路径验证）

### 场景 9：输出包含未来 command / function_call，但未执行

**验证方式**：代码逻辑验证

**结果**：
- command 字段构造为 `python runner.py run-project-task-full --project <path> --task <id>` ✓
- function_call 字段构造为 `run_project_task_full(project_path=..., task_id=...)` ✓
- 两个构造均为字符串，不会被执行 ✓
- TASK_EXECUTION_PERFORMED=False ✓
- RUN_PROJECT_TASK_FULL_CALLED=False ✓

**结果**：PASS

### 场景 10：所有路径未调用 run-project-task-full、未调用 Claude Code、未修改业务代码

**验证方式**：函数级断言 + 代码逻辑验证

**所有路径结果**：
- task_execution_performed=False ✓
- run_project_task_full_called=False ✓
- claude_code_called="no" ✓
- business_code_changed="no" ✓
- auto_continue_to_next_task=False ✓
- auto_git_backup=False ✓
- human_review_required=True ✓

**结果**：PASS

## 回归验证

| 命令 | 预期 | 实际 | 结果 |
|------|------|------|------|
| dry-run | LOOP_STATUS=stopped_on_max_tasks | LOOP_STATUS=stopped_on_max_tasks | PASS |
| execute stub | safety_gate_failed | safety_gate_failed | PASS |
| real-call safety gate | EXECUTION_MODE=real_call_safety_gate | EXECUTION_MODE=real_call_safety_gate | PASS |

## 验证总结

| 场景 | 描述 | 结果 |
|------|------|------|
| 1 | 不带 --real-call-dry-run → 原行为保持 | PASS（CLI） |
| 2 | --real-call-dry-run 不带 --real-call | PASS（CLI） |
| 3 | --real-call-dry-run 不带 --execute | PASS（CLI） |
| 4 | confirm 错误 | PASS（CLI） |
| 5 | real-confirm 错误 | PASS（代码逻辑） |
| 6 | max_tasks=2 | PASS（代码逻辑） |
| 7 | --real-call-dry-run + --real-call-stub | PASS（CLI） |
| 7b | --real-call-dry-run + --adapter-dry-run | PASS（CLI） |
| 8 | 正确双确认 + real-call-dry-run | PASS（代码逻辑，T080 补充 clean workspace E2E） |
| 9 | 输出含 command/function_call 但未执行 | PASS（代码逻辑） |
| 10 | 所有路径未调用/未修改 | PASS（函数级断言） |

## 说明

- 工作区 dirty（T079 实现中）导致 CLI 级别的 execute safety gate 在 workspace 检查处拦截
- 场景 5、6、8 的完整 E2E 验证将在 T080（clean workspace）中补充
- 代码逻辑已通过函数级验证和源码检查
