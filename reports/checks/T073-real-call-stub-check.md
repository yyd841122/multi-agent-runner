# T073 Real-Call Stub Check

## Goal

验证 `--real-call-stub` 的正确行为：
- 不带 `--real-call-stub` 时原 execute stub / adapter dry-run 行为不变
- `--real-call-stub` 必须配合 `--execute`
- 错误参数正确拒绝
- 正确参数时构造 real-call stub
- 未调用 run-project-task-full、未调用 Claude Code、未修改业务代码

## Commands

| # | 场景 | 验证方式 |
|---|------|----------|
| 1 | 不带 --real-call-stub | CLI: execute stub 行为不变 |
| 2 | --real-call-stub 不带 --execute | CLI: 报错 |
| 3 | --real-call-stub + confirm 错误 | CLI: confirm_rejected |
| 4 | --real-call-stub + max_tasks=0 | CLI: invalid_max_tasks |
| 5 | --real-call-stub + max_tasks=2 | Python: max_tasks_gt_1_not_supported |
| 6 | 正确参数 real-call stub | Python: stub started, check_result=pass |
| 7 | command 构造但未执行 | Python: command 存在, execution_performed=false |
| 8 | RUN_PROJECT_TASK_FULL_CALLED=false | Python: 验证字段 |
| 9 | 未调用 Claude Code、未修改业务代码 | Python: 全部安全字段 |

## Expected Result

### 场景 1：不带 --real-call-stub → 原 execute stub 行为

输出包含 EXECUTE_MODE_REQUESTED=true，不包含 REAL_CALL 相关字段。

### 场景 2：--real-call-stub 不带 --execute

```
ERROR：--real-call-stub 必须配合 --execute 使用。
```

### 场景 3-9

所有路径确认：
- TASK_EXECUTION_PERFORMED=false
- RUN_PROJECT_TASK_FULL_CALLED=false
- CLAUDE_CODE_CALLED=no
- BUSINESS_CODE_CHANGED=no

## Actual Result

### 场景 1：不带 --real-call-stub

```bash
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP
```

输出包含 EXECUTE_MODE_REQUESTED=true，不包含 REAL_CALL 相关字段。

结果：**PASS**

### 场景 2：--real-call-stub 不带 --execute

```bash
python runner.py run-project-loop --project . --max-tasks 1 --real-call-stub
```

```
ERROR：--real-call-stub 必须配合 --execute 使用。
```

结果：**PASS**

### 场景 3：confirm 错误

```bash
python runner.py run-project-loop --project . --max-tasks 1 --execute --real-call-stub --confirm yes
```

```
EXECUTION_MODE=real_call_stub
REAL_CALL_REQUESTED=True
REAL_CALL_STUB_STARTED=False
LOOP_STATUS=safety_gate_failed
STOP_REASON=confirm_rejected
CHECK_RESULT=fail
TASK_EXECUTION_PERFORMED=False
RUN_PROJECT_TASK_FULL_CALLED=False
CLAUDE_CODE_CALLED=no
BUSINESS_CODE_CHANGED=no
EXIT_CODE=not_executed
```

结果：**PASS**

### 场景 4：max_tasks=0

```bash
python runner.py run-project-loop --project . --max-tasks 0 --execute --real-call-stub --confirm EXECUTE_PROJECT_LOOP
```

```
EXECUTION_MODE=real_call_stub
REAL_CALL_REQUESTED=True
REAL_CALL_STUB_STARTED=False
LOOP_STATUS=safety_gate_failed
STOP_REASON=invalid_max_tasks
CHECK_RESULT=fail
TASK_EXECUTION_PERFORMED=False
RUN_PROJECT_TASK_FULL_CALLED=False
CLAUDE_CODE_CALLED=no
BUSINESS_CODE_CHANGED=no
```

结果：**PASS**

### 场景 5：max_tasks=2

dirty workspace 下 safety gate 先拒绝（initial_worktree_dirty）。
使用 Python 函数调用 mock clean workspace 验证 max_tasks!=1 分支：

```python
# mock _check_workspace_clean to return True
result = run_project_loop_real_call_stub('.', 2, 'EXECUTE_PROJECT_LOOP')
# LOOP_STATUS=max_tasks_gt_1_not_supported
# STOP_REASON=max_tasks_gt_1_not_supported_in_real_call_stub
# CHECK_RESULT=fail
# REAL_CALL_STUB_STARTED=False
```

结果：**PASS**（Python 函数调用验证 + 代码逻辑验证）

### 场景 6：正确参数 real-call stub

dirty workspace 下 safety gate 先拒绝。使用 Python 函数调用 mock clean workspace：

```python
# mock _check_workspace_clean to return True
result = run_project_loop_real_call_stub('.', 1, 'EXECUTE_PROJECT_LOOP')
```

```
EXECUTION_MODE=real_call_stub
REAL_CALL_REQUESTED=True
REAL_CALL_STUB_STARTED=True
TASK_ID=T073
COMMAND=run_project_task_full(project_path='projects', task_id='T073')
PREFLIGHT_STATUS=passed
TASK_EXECUTION_PERFORMED=False
RUN_PROJECT_TASK_FULL_CALLED=False
CLAUDE_CODE_CALLED=no
BUSINESS_CODE_CHANGED=no
EXIT_CODE=not_executed
CHECK_RESULT=pass
LOOP_STATUS=real_call_stub_completed
STOP_REASON=real_call_stub_only
HUMAN_REVIEW_REQUIRED=True
NEXT_ACTION=ready_for_T074_check_result_pass_validation
```

验证：

| 字段 | 预期 | 实际 | 结果 |
|------|------|------|------|
| EXECUTION_MODE | real_call_stub | real_call_stub | PASS |
| REAL_CALL_REQUESTED | true | True | PASS |
| REAL_CALL_STUB_STARTED | true | True | PASS |
| TASK_ID | T073 | T073 | PASS |
| COMMAND | 包含 run_project_task_full | 包含 | PASS |
| TASK_EXECUTION_PERFORMED | false | False | PASS |
| RUN_PROJECT_TASK_FULL_CALLED | false | False | PASS |
| CLAUDE_CODE_CALLED | no | no | PASS |
| BUSINESS_CODE_CHANGED | no | no | PASS |
| EXIT_CODE | not_executed | not_executed | PASS |
| CHECK_RESULT | pass | pass | PASS |
| LOOP_STATUS | real_call_stub_completed | real_call_stub_completed | PASS |
| STOP_REASON | real_call_stub_only | real_call_stub_only | PASS |
| HUMAN_REVIEW_REQUIRED | true | True | PASS |
| NEXT_ACTION | ready_for_T074... | ready_for_T074... | PASS |

结果：**PASS**

### 场景 7：command 构造但未执行

```python
has_command = 'run_project_task_full' in result.command  # True
execution_performed = result.task_execution_performed  # False
full_called = result.run_project_task_full_called  # False
```

结果：**PASS**

### 场景 8：RUN_PROJECT_TASK_FULL_CALLED=false

已在场景 6-7 中验证：`RUN_PROJECT_TASK_FULL_CALLED=False`。

结果：**PASS**

### 场景 9：未调用 Claude Code、未修改业务代码

```python
result.claude_code_called == "no"  # True
result.business_code_changed == "no"  # True
result.task_execution_performed == False  # True
result.run_project_task_full_called == False  # True
```

结果：**PASS**

## Side Effect Check

| 检查项 | 结果 |
|--------|------|
| 是否执行真实任务 | no — 所有场景 TASK_EXECUTION_PERFORMED=false |
| 是否调用 run-project-task-full | no — 所有场景 RUN_PROJECT_TASK_FULL_CALLED=false |
| 是否调用 Claude Code | no — 所有场景 CLAUDE_CODE_CALLED=no |
| 是否修改业务代码 | no — BUSINESS_CODE_CHANGED=no |
| 是否新增业务报告 | no — 只有预期代码文件修改 |
| workspace 仅有预期文件 | yes — git status 只有 runner.py 和 continuous_task_planner.py |

## Summary

| # | 场景 | 结果 |
|---|------|------|
| 1 | 不带 --real-call-stub → stub 行为不变 | PASS |
| 2 | --real-call-stub 不带 --execute | PASS |
| 3 | confirm 错误 → confirm_rejected | PASS |
| 4 | max_tasks=0 → invalid_max_tasks | PASS |
| 5 | max_tasks=2 → max_tasks_gt_1_not_supported | PASS |
| 6 | 正确参数 → stub pass | PASS |
| 7 | command 构造但未执行 | PASS |
| 8 | RUN_PROJECT_TASK_FULL_CALLED=false | PASS |
| 9 | 未调用 Claude Code、未修改业务代码 | PASS |

全部 9 个场景通过。

## Check Result

pass

## Next

T074：验证 CHECK_RESULT=pass 后停止
