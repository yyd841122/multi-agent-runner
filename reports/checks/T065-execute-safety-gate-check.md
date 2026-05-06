# T065 Execute Safety Gate Check

## Goal

验证 execute mode safety gate 的确认协议、max_tasks 限制和工作区检查。

## Scenarios

### 场景 1：不带 --execute → dry-run 行为不变

```bash
python runner.py run-project-loop --max-tasks 1
```

预期：LOOP_STATUS=stopped_on_max_tasks, DRY_RUN=True

实际：
```
LOOP_STATUS=stopped_on_max_tasks
DRY_RUN=True
PLANNED_TASKS=T065
TASK_EXECUTION_PERFORMED=false
CLAUDE_CODE_CALLED=false
BUSINESS_CODE_CHANGED=false
```

结果：**PASS**

### 场景 2：--execute 缺少 --confirm → 拒绝

```bash
python runner.py run-project-loop --execute --max-tasks 1
```

预期：CONFIRM_STATUS=missing, EXECUTE_ALLOWED=false

实际：
```
EXECUTE_MODE_REQUESTED=True
CONFIRM_STATUS=missing
EXECUTE_ALLOWED=False
STOP_REASON=confirm_missing
TASK_EXECUTION_PERFORMED=False
CLAUDE_CODE_CALLED=False
```

结果：**PASS**

### 场景 3：--confirm yes → 拒绝

```bash
python runner.py run-project-loop --execute --confirm yes --max-tasks 1
```

预期：CONFIRM_STATUS=rejected, EXECUTE_ALLOWED=false

实际：
```
CONFIRM_STATUS=rejected
EXECUTE_ALLOWED=False
STOP_REASON=confirm_rejected
```

结果：**PASS**

### 场景 4：--confirm 确认 → 拒绝

```bash
python runner.py run-project-loop --execute --confirm 确认 --max-tasks 1
```

预期：CONFIRM_STATUS=rejected

实际：
```
CONFIRM_STATUS=rejected
STOP_REASON=confirm_rejected
```

结果：**PASS**

### 场景 5：--confirm EXECUTE_REWORK → 拒绝

```bash
python runner.py run-project-loop --execute --confirm EXECUTE_REWORK --max-tasks 1
```

预期：CONFIRM_STATUS=rejected

实际：
```
CONFIRM_STATUS=rejected
STOP_REASON=confirm_rejected
```

结果：**PASS**

### 场景 6：正确 confirm + max_tasks=0 → 拒绝

```bash
python runner.py run-project-loop --execute --confirm EXECUTE_PROJECT_LOOP --max-tasks 0
```

预期：CONFIRM_STATUS=accepted, EXECUTE_ALLOWED=false, STOP_REASON=invalid_max_tasks

实际：
```
CONFIRM_STATUS=accepted
EXECUTE_ALLOWED=False
STOP_REASON=invalid_max_tasks
```

结果：**PASS**

### 场景 7：正确 confirm + max_tasks=4 → 拒绝

```bash
python runner.py run-project-loop --execute --confirm EXECUTE_PROJECT_LOOP --max-tasks 4
```

预期：CONFIRM_STATUS=accepted, EXECUTE_ALLOWED=false, STOP_REASON=execute_max_tasks_exceeded

实际：
```
CONFIRM_STATUS=accepted
EXECUTE_ALLOWED=False
STOP_REASON=execute_max_tasks_exceeded
EXECUTE_HARD_LIMIT=3
```

结果：**PASS**

### 场景 8：正确 confirm + max_tasks=1 + dirty workspace → 拒绝

```bash
python runner.py run-project-loop --execute --confirm EXECUTE_PROJECT_LOOP --max-tasks 1
```

预期：CONFIRM_STATUS=accepted, WORKSPACE_STATUS=dirty, EXECUTE_ALLOWED=false

实际：
```
CONFIRM_STATUS=accepted
WORKSPACE_STATUS=dirty
EXECUTE_ALLOWED=False
STOP_REASON=initial_worktree_dirty
NEXT_ACTION=commit_or_stash_changes
```

结果：**PASS**（工作区 dirty 因为 T065 正在开发中，safety gate 正确检测）

### 场景 9：正确 confirm + max_tasks=3 + dirty workspace → 拒绝

```bash
python runner.py run-project-loop --execute --confirm EXECUTE_PROJECT_LOOP --max-tasks 3
```

预期：CONFIRM_STATUS=accepted, max_tasks=3 合法，但 workspace dirty 拒绝

实际：
```
CONFIRM_STATUS=accepted
MAX_TASKS=3
EXECUTE_HARD_LIMIT=3
WORKSPACE_STATUS=dirty
EXECUTE_ALLOWED=False
STOP_REASON=initial_worktree_dirty
```

结果：**PASS**

### 场景 10：--execute --dry-run 互斥

```bash
python runner.py run-project-loop --execute --dry-run --max-tasks 1
```

预期：报错，互斥

实际：
```
ERROR：--execute 和 --dry-run 互斥，不能同时使用。
```

结果：**PASS**

### 额外验证

| # | 场景 | 结果 |
|---|------|------|
| A | max_tasks=11 execute mode 拒绝 | PASS — STOP_REASON=execute_max_tasks_exceeded |
| B | --confirm ok 拒绝 | PASS — CONFIRM_STATUS=rejected |
| C | dry-run max_tasks=3 行为不变 | PASS — PLANNED_TASKS=T065,T066,T067 |

## Safety Check

| 检查项 | 结果 |
|--------|------|
| 是否执行真实任务 | no — 所有场景 TASK_EXECUTION_PERFORMED=false |
| 是否调用 Claude Code | no — 所有场景 CLAUDE_CODE_CALLED=false |
| 是否修改业务代码 | no — BUSINESS_CODE_CHANGED=false |
| 是否调用 run-project-task-full | no — validate_execute_loop_safety 不调用 |
| dry-run 行为是否保持不变 | yes — 场景 1 和 C 确认 |

## Summary

| 场景 | 预期 | 实际 | 结果 |
|------|------|------|------|
| 1. 不带 --execute | dry-run | dry-run | PASS |
| 2. 缺少 --confirm | 拒绝 missing | missing | PASS |
| 3. --confirm yes | 拒绝 rejected | rejected | PASS |
| 4. --confirm 确认 | 拒绝 rejected | rejected | PASS |
| 5. --confirm EXECUTE_REWORK | 拒绝 rejected | rejected | PASS |
| 6. max_tasks=0 | 拒绝 invalid | invalid_max_tasks | PASS |
| 7. max_tasks=4 | 拒绝 exceeded | execute_max_tasks_exceeded | PASS |
| 8. max_tasks=1 dirty | 拒绝 dirty | initial_worktree_dirty | PASS |
| 9. max_tasks=3 dirty | 拒绝 dirty | initial_worktree_dirty | PASS |
| 10. --execute --dry-run | 互斥报错 | 报错 | PASS |

全部 10 个场景 + 3 个额外验证通过。

## Check Result

pass

## Next

T066：实现 max_tasks=1 execute stub
