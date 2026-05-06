# T067 Execute Confirm Rejection Check

## Goal

验证 execute mode 中错误 confirm 或缺失 confirm 必须被拒绝。

## Commands

| # | 命令 | 预期 confirm_status |
|---|------|---------------------|
| 1 | `--execute`（缺少 --confirm） | missing |
| 2 | `--execute --confirm yes` | rejected |
| 3 | `--execute --confirm ok` | rejected |
| 4 | `--execute --confirm 确认` | rejected |
| 5 | `--execute --confirm 同意` | rejected |
| 6 | `--execute --confirm EXECUTE_REWORK` | rejected |
| 7 | `--execute --confirm EXECUTE_PROJECT_LOOP_WRONG` | rejected |
| 8 | `--execute --dry-run --confirm EXECUTE_PROJECT_LOOP` | 互斥报错 |

## Expected Result

每个错误确认场景应满足：

- EXECUTE_MODE_REQUESTED=true
- EXECUTE_ALLOWED=false
- EXECUTE_STUB_STARTED=false
- TASK_EXECUTION_PERFORMED=false
- CLAUDE_CODE_CALLED=false
- BUSINESS_CODE_CHANGED=false
- CHECK_RESULT=fail

## Actual Result

### 场景 1：缺少 --confirm

```bash
python runner.py run-project-loop --project . --max-tasks 1 --execute
```

```
EXECUTE_MODE_REQUESTED=true
EXECUTE_ALLOWED=False
EXECUTE_STUB_STARTED=False
TASK_EXECUTION_PERFORMED=False
CLAUDE_CODE_CALLED=False
BUSINESS_CODE_CHANGED=False
STOP_REASON=confirm_missing
CHECK_RESULT=fail
```

结果：**PASS**

### 场景 2：--confirm yes

```bash
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm yes
```

```
EXECUTE_MODE_REQUESTED=true
EXECUTE_ALLOWED=False
EXECUTE_STUB_STARTED=False
TASK_EXECUTION_PERFORMED=False
CLAUDE_CODE_CALLED=False
BUSINESS_CODE_CHANGED=False
STOP_REASON=confirm_rejected
CHECK_RESULT=fail
```

结果：**PASS**

### 场景 3：--confirm ok

```bash
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm ok
```

```
EXECUTE_MODE_REQUESTED=true
EXECUTE_ALLOWED=False
EXECUTE_STUB_STARTED=False
TASK_EXECUTION_PERFORMED=False
CLAUDE_CODE_CALLED=False
BUSINESS_CODE_CHANGED=False
STOP_REASON=confirm_rejected
CHECK_RESULT=fail
```

结果：**PASS**

### 场景 4：--confirm 确认

```bash
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm 确认
```

```
EXECUTE_MODE_REQUESTED=true
EXECUTE_ALLOWED=False
EXECUTE_STUB_STARTED=False
TASK_EXECUTION_PERFORMED=False
CLAUDE_CODE_CALLED=False
BUSINESS_CODE_CHANGED=False
STOP_REASON=confirm_rejected
CHECK_RESULT=fail
```

结果：**PASS**

### 场景 5：--confirm 同意

```bash
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm 同意
```

```
EXECUTE_MODE_REQUESTED=true
EXECUTE_ALLOWED=False
EXECUTE_STUB_STARTED=False
TASK_EXECUTION_PERFORMED=False
CLAUDE_CODE_CALLED=False
BUSINESS_CODE_CHANGED=False
STOP_REASON=confirm_rejected
CHECK_RESULT=fail
```

结果：**PASS**

### 场景 6：--confirm EXECUTE_REWORK

```bash
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_REWORK
```

```
EXECUTE_MODE_REQUESTED=true
EXECUTE_ALLOWED=False
EXECUTE_STUB_STARTED=False
TASK_EXECUTION_PERFORMED=False
CLAUDE_CODE_CALLED=False
BUSINESS_CODE_CHANGED=False
STOP_REASON=confirm_rejected
CHECK_RESULT=fail
```

结果：**PASS**

### 场景 7：--confirm EXECUTE_PROJECT_LOOP_WRONG

```bash
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP_WRONG
```

```
EXECUTE_MODE_REQUESTED=true
EXECUTE_ALLOWED=False
EXECUTE_STUB_STARTED=False
TASK_EXECUTION_PERFORMED=False
CLAUDE_CODE_CALLED=False
BUSINESS_CODE_CHANGED=False
STOP_REASON=confirm_rejected
CHECK_RESULT=fail
```

结果：**PASS**

## Mutual Exclusion Check

```bash
python runner.py run-project-loop --project . --max-tasks 1 --dry-run --execute --confirm EXECUTE_PROJECT_LOOP
```

```
ERROR：--execute 和 --dry-run 互斥，不能同时使用。
```

结果：**PASS**

## Safety Check

| 检查项 | 结果 |
|--------|------|
| 是否执行真实任务 | no — 所有场景 TASK_EXECUTION_PERFORMED=false |
| 是否调用 Claude Code | no — 所有场景 CLAUDE_CODE_CALLED=false |
| 是否修改业务代码 | no — BUSINESS_CODE_CHANGED=false，git status clean |
| 是否调用 run-project-task-full | no — confirm 拒绝不会调用 |
| 工作区是否保持 clean | yes — git status --short 无输出 |

## Summary

| # | 场景 | STOP_REASON | 结果 |
|---|------|-------------|------|
| 1 | 缺少 --confirm | confirm_missing | PASS |
| 2 | --confirm yes | confirm_rejected | PASS |
| 3 | --confirm ok | confirm_rejected | PASS |
| 4 | --confirm 确认 | confirm_rejected | PASS |
| 5 | --confirm 同意 | confirm_rejected | PASS |
| 6 | --confirm EXECUTE_REWORK | confirm_rejected | PASS |
| 7 | --confirm EXECUTE_PROJECT_LOOP_WRONG | confirm_rejected | PASS |
| 8 | --execute --dry-run 互斥 | ERROR 互斥报错 | PASS |

全部 8 个拒绝场景通过。

## Check Result

pass

## Next

T068：验证 max_tasks=1 execute stub
