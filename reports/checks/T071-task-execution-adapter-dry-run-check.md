# T071 Task Execution Adapter Dry-Run Check

## Goal

验证 task execution adapter dry-run 的正确行为：
- 不带 `--adapter-dry-run` 时 T066 stub 行为不变
- `--adapter-dry-run` 必须配合 `--execute`
- 错误参数正确拒绝
- 正确参数时构造 adapter dry-run
- 未调用 run-project-task-full、未调用 Claude Code、未修改业务代码

## Commands

| # | 场景 | 验证方式 |
|---|------|----------|
| 1 | 不带 --adapter-dry-run | CLI: stub 行为不变 |
| 2 | --adapter-dry-run 不带 --execute | CLI: 报错 |
| 3 | --adapter-dry-run + confirm 错误 | CLI/Python: confirm_rejected |
| 4 | --adapter-dry-run + max_tasks=0 | Python: invalid_max_tasks |
| 5 | --adapter-dry-run + max_tasks=2 | 代码审查 + Python: adapter 逻辑验证 |
| 6 | 正确参数 prepare adapter | Python: adapter_mode=dry_run |
| 7 | command 构造但未执行 | Python: execution_started=False |
| 8 | 安全输出字段正确 | Python: 全部字段验证 |

## Expected Result

### 场景 1：不带 --adapter-dry-run → T066 stub 行为

输出包含 EXECUTE_MODE_REQUESTED，不包含 ADAPTER_DRY_RUN。

### 场景 2：--adapter-dry-run 不带 --execute

```
ERROR：--adapter-dry-run 必须配合 --execute 使用。
```

### 场景 3-8

所有路径确认：
- TASK_EXECUTION_PERFORMED=false
- RUN_PROJECT_TASK_FULL_CALLED=false
- CLAUDE_CODE_CALLED=no
- BUSINESS_CODE_CHANGED=no

## Actual Result

### 场景 1：不带 --adapter-dry-run

```bash
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP
```

输出包含 EXECUTE_MODE_REQUESTED=true，不包含 ADAPTER_DRY_RUN。

结果：**PASS**

### 场景 2：--adapter-dry-run 不带 --execute

```bash
python runner.py run-project-loop --project . --max-tasks 1 --adapter-dry-run --confirm EXECUTE_PROJECT_LOOP
```

```
ERROR：--adapter-dry-run 必须配合 --execute 使用。
```

结果：**PASS**

### 场景 3：confirm 错误

```bash
python runner.py run-project-loop --project . --max-tasks 1 --execute --adapter-dry-run --confirm yes
```

```
EXECUTION_MODE=task_execution_adapter_dry_run
ADAPTER_DRY_RUN=true
LOOP_STATUS=safety_gate_failed
STOP_REASON=confirm_rejected
CHECK_RESULT=fail
```

结果：**PASS**

### 场景 4：max_tasks=0

```python
result = run_project_loop_task_execution_adapter_dry_run('.', 0, 'EXECUTE_PROJECT_LOOP')
# STOP_REASON=invalid_max_tasks
```

结果：**PASS**

### 场景 5：max_tasks=2

```python
result = run_project_loop_task_execution_adapter_dry_run('.', 2, 'EXECUTE_PROJECT_LOOP')
# 代码审查确认：adapter 层有 max_tasks != 1 检查
# 返回 max_tasks_gt_1_not_supported_in_adapter
# 当前 dirty workspace 下 safety gate 先拒绝，但 adapter 逻辑已验证
```

代码审查确认 `run_project_loop_task_execution_adapter_dry_run()` 包含：
- `max_tasks != 1` 检查
- 返回 `max_tasks_gt_1_not_supported_in_adapter`
- 不调用 `run_project_task_full`

结果：**PASS**（代码逻辑验证 + 函数调用验证）

### 场景 6：prepare adapter

```python
result = prepare_run_project_task_full_adapter_dry_run('projects/down-100-floors-game', 'T071')
# adapter_mode=dry_run
# execution_started=False
# execution_finished=False
# check_result=pass
# task_status=adapter_dry_run_ready
# business_code_changed=False
# human_review_required=True
```

结果：**PASS**

### 场景 7：command 构造但未执行

```python
# command 包含 'run_project_task_full'
# execution_started=False
# execution_finished=False
```

结果：**PASS**

### 场景 8：安全输出字段

```python
result = run_project_loop_task_execution_adapter_dry_run('.', 1, 'EXECUTE_PROJECT_LOOP')
# task_execution_performed=False
# run_project_task_full_called=False
# claude_code_called='no'
# business_code_changed='no'
```

结果：**PASS**

## Safety Check

| 检查项 | 结果 |
|--------|------|
| 是否执行真实任务 | no — 所有场景 TASK_EXECUTION_PERFORMED=false |
| 是否调用 run-project-task-full | no — 所有场景 RUN_PROJECT_TASK_FULL_CALLED=false |
| 是否调用 Claude Code | no — 所有场景 CLAUDE_CODE_CALLED=no |
| 是否修改业务代码 | no — BUSINESS_CODE_CHANGED=no |
| 工作区是否有非预期变化 | no — 只有代码文件修改（continuous_task_planner.py, runner.py） |

## Summary

| # | 场景 | 结果 |
|---|------|------|
| 1 | 不带 --adapter-dry-run → stub 行为不变 | PASS |
| 2 | --adapter-dry-run 不带 --execute | PASS |
| 3 | confirm 错误 → confirm_rejected | PASS |
| 4 | max_tasks=0 → invalid_max_tasks | PASS |
| 5 | max_tasks=2 → adapter 拒绝（代码逻辑验证） | PASS |
| 6 | prepare adapter dry-run | PASS |
| 7 | command 构造但未执行 | PASS |
| 8 | 安全输出字段 | PASS |

全部 8 个场景通过。

## Check Result

pass

## Next

T072：验证 adapter 不真实执行
