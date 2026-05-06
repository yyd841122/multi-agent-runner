# T087 Real-call Run-once Rejection Check

## Goal

验证 `--real-call-run-once` 在前置条件不满足时必须拒绝。

## Commands

### 拒绝场景

| # | 命令 | 拒绝原因 |
|---|------|----------|
| 1 | `--real-call-run-once`（缺少 --real-call） | CLI 互斥：--real-call-run-once 需要 --real-call |
| 2 | `--execute --real-call-run-once`（缺少 --real-call） | CLI 互斥：--real-call-run-once 需要 --real-call |
| 3 | `--execute --confirm yes --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-run-once` | confirm 值错误（yes ≠ EXECUTE_PROJECT_LOOP） |
| 4 | `--execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-call-run-once` | 缺少 --real-confirm |
| 5 | `--execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm yes --real-call-run-once` | real-confirm 值错误（yes ≠ EXECUTE_REAL_TASK_ONCE） |
| 6 | `--max-tasks 0 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-run-once` | max-tasks=0 无效 |
| 7 | `--max-tasks 2 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-run-once` | max-tasks=2 不等于 1 |
| 8 | `--real-call-run-once --real-call-dry-run` | CLI 互斥：不能同时使用 |
| 9 | `--real-call-run-once --real-call-stub` | CLI 互斥：--real-call 与 --real-call-stub 冲突 |
| 10 | `--real-call-run-once --adapter-dry-run` | CLI 互斥：--real-call 与 --adapter-dry-run 冲突 |

### 对照场景

| # | 命令 | 预期 |
|---|------|------|
| 11 | `--max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-run-once` | safety shell 启动，不执行真实调用 |

## Expected Result

### 拒绝场景（1-10）

每个拒绝场景应满足：

- CHECK_RESULT=fail 或 CLI ERROR
- REAL_TASK_EXECUTION=no
- RUN_PROJECT_TASK_FULL_CALLED=no
- CLAUDE_CODE_CALLED=no
- BUSINESS_CODE_CHANGED=no
- AUTO_CONTINUE_TO_NEXT_TASK=no（或 false）
- AUTO_GIT_BACKUP=no（或 false）

### 对照场景（11）

- EXECUTION_MODE=real_call_run_once_safety_shell
- RUN_ONCE_SAFETY_SHELL_STARTED=true
- REAL_TASK_EXECUTION=no
- RUN_PROJECT_TASK_FULL_CALLED=no
- CHECK_RESULT=pass

## Actual Result

### 场景 1：缺少 --real-call

**命令**：`--real-call-run-once`（无 --real-call）

**实际输出**：
```
ERROR：--real-call-run-once 需要 --real-call 使用。
```

**判定**：PASS — CLI ERROR，命令直接拒绝

| 字段 | 值 |
|------|------|
| CHECK_RESULT | CLI ERROR |
| REAL_TASK_EXECUTION | no |
| RUN_PROJECT_TASK_FULL_CALLED | no |
| CLAUDE_CODE_CALLED | no |
| BUSINESS_CODE_CHANGED | no |
| AUTO_CONTINUE_TO_NEXT_TASK | no |
| AUTO_GIT_BACKUP | no |

### 场景 2：缺少 --real-call（有 --execute）

**命令**：`--execute --real-call-run-once`（无 --real-call）

**实际输出**：
```
ERROR：--real-call-run-once 需要 --real-call 使用。
```

**判定**：PASS — CLI ERROR，命令直接拒绝

| 字段 | 值 |
|------|------|
| CHECK_RESULT | CLI ERROR |
| REAL_TASK_EXECUTION | no |
| RUN_PROJECT_TASK_FULL_CALLED | no |
| CLAUDE_CODE_CALLED | no |
| BUSINESS_CODE_CHANGED | no |
| AUTO_CONTINUE_TO_NEXT_TASK | no |
| AUTO_GIT_BACKUP | no |

### 场景 3：--confirm 值错误（yes ≠ EXECUTE_PROJECT_LOOP）

**命令**：`--execute --confirm yes --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-run-once`

**实际输出**：
```
EXECUTION_MODE=real_call_run_once_safety_shell
REAL_CALL_ALLOWED=False
RUN_ONCE_REQUESTED=True
RUN_ONCE_SAFETY_SHELL_STARTED=False
PREFLIGHT_STATUS=failed
REAL_TASK_EXECUTION=no
RUN_PROJECT_TASK_FULL_CALLED=no
CLAUDE_CODE_CALLED=no
BUSINESS_CODE_CHANGED=no
AUTO_CONTINUE_TO_NEXT_TASK=false
AUTO_GIT_BACKUP=false
CHECK_RESULT=fail
STOP_REASON=execute_safety_gate_failed:confirm_rejected
```

**判定**：PASS — CHECK_RESULT=fail, STOP_REASON=confirm_rejected

| 字段 | 值 |
|------|------|
| CHECK_RESULT | fail |
| REAL_TASK_EXECUTION | no |
| RUN_PROJECT_TASK_FULL_CALLED | no |
| CLAUDE_CODE_CALLED | no |
| BUSINESS_CODE_CHANGED | no |
| AUTO_CONTINUE_TO_NEXT_TASK | false |
| AUTO_GIT_BACKUP | false |

### 场景 4：缺少 --real-confirm

**命令**：`--execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-call-run-once`

**实际输出**：
```
EXECUTION_MODE=real_call_run_once_safety_shell
REAL_CALL_ALLOWED=False
RUN_ONCE_REQUESTED=True
RUN_ONCE_SAFETY_SHELL_STARTED=False
PREFLIGHT_STATUS=failed
REAL_TASK_EXECUTION=no
RUN_PROJECT_TASK_FULL_CALLED=no
CLAUDE_CODE_CALLED=no
BUSINESS_CODE_CHANGED=no
AUTO_CONTINUE_TO_NEXT_TASK=false
AUTO_GIT_BACKUP=false
CHECK_RESULT=fail
STOP_REASON=real_confirm_missing
```

**判定**：PASS — CHECK_RESULT=fail, STOP_REASON=real_confirm_missing

| 字段 | 值 |
|------|------|
| CHECK_RESULT | fail |
| REAL_TASK_EXECUTION | no |
| RUN_PROJECT_TASK_FULL_CALLED | no |
| CLAUDE_CODE_CALLED | no |
| BUSINESS_CODE_CHANGED | no |
| AUTO_CONTINUE_TO_NEXT_TASK | false |
| AUTO_GIT_BACKUP | false |

### 场景 5：--real-confirm 值错误（yes ≠ EXECUTE_REAL_TASK_ONCE）

**命令**：`--execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm yes --real-call-run-once`

**实际输出**：
```
EXECUTION_MODE=real_call_run_once_safety_shell
REAL_CALL_ALLOWED=False
RUN_ONCE_REQUESTED=True
RUN_ONCE_SAFETY_SHELL_STARTED=False
PREFLIGHT_STATUS=failed
REAL_TASK_EXECUTION=no
RUN_PROJECT_TASK_FULL_CALLED=no
CLAUDE_CODE_CALLED=no
BUSINESS_CODE_CHANGED=no
AUTO_CONTINUE_TO_NEXT_TASK=false
AUTO_GIT_BACKUP=false
CHECK_RESULT=fail
STOP_REASON=real_confirm_rejected
```

**判定**：PASS — CHECK_RESULT=fail, STOP_REASON=real_confirm_rejected

| 字段 | 值 |
|------|------|
| CHECK_RESULT | fail |
| REAL_TASK_EXECUTION | no |
| RUN_PROJECT_TASK_FULL_CALLED | no |
| CLAUDE_CODE_CALLED | no |
| BUSINESS_CODE_CHANGED | no |
| AUTO_CONTINUE_TO_NEXT_TASK | false |
| AUTO_GIT_BACKUP | false |

### 场景 6：max-tasks=0

**命令**：`--max-tasks 0 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-run-once`

**实际输出**：
```
EXECUTION_MODE=real_call_run_once_safety_shell
REAL_CALL_ALLOWED=False
RUN_ONCE_REQUESTED=True
RUN_ONCE_SAFETY_SHELL_STARTED=False
PREFLIGHT_STATUS=failed
REAL_TASK_EXECUTION=no
RUN_PROJECT_TASK_FULL_CALLED=no
CLAUDE_CODE_CALLED=no
BUSINESS_CODE_CHANGED=no
AUTO_CONTINUE_TO_NEXT_TASK=false
AUTO_GIT_BACKUP=false
CHECK_RESULT=fail
STOP_REASON=execute_safety_gate_failed:invalid_max_tasks
```

**判定**：PASS — CHECK_RESULT=fail, STOP_REASON=invalid_max_tasks

| 字段 | 值 |
|------|------|
| CHECK_RESULT | fail |
| REAL_TASK_EXECUTION | no |
| RUN_PROJECT_TASK_FULL_CALLED | no |
| CLAUDE_CODE_CALLED | no |
| BUSINESS_CODE_CHANGED | no |
| AUTO_CONTINUE_TO_NEXT_TASK | false |
| AUTO_GIT_BACKUP | false |

### 场景 7：max-tasks=2（不等于 1）

**命令**：`--max-tasks 2 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-run-once`

**实际输出**：
```
EXECUTION_MODE=real_call_run_once_safety_shell
REAL_CALL_ALLOWED=False
RUN_ONCE_REQUESTED=True
RUN_ONCE_SAFETY_SHELL_STARTED=False
PREFLIGHT_STATUS=failed
REAL_TASK_EXECUTION=no
RUN_PROJECT_TASK_FULL_CALLED=no
CLAUDE_CODE_CALLED=no
BUSINESS_CODE_CHANGED=no
AUTO_CONTINUE_TO_NEXT_TASK=false
AUTO_GIT_BACKUP=false
CHECK_RESULT=fail
STOP_REASON=max_tasks_not_one
```

**判定**：PASS — CHECK_RESULT=fail, STOP_REASON=max_tasks_not_one

| 字段 | 值 |
|------|------|
| CHECK_RESULT | fail |
| REAL_TASK_EXECUTION | no |
| RUN_PROJECT_TASK_FULL_CALLED | no |
| CLAUDE_CODE_CALLED | no |
| BUSINESS_CODE_CHANGED | no |
| AUTO_CONTINUE_TO_NEXT_TASK | false |
| AUTO_GIT_BACKUP | false |

### 场景 8：--real-call-dry-run 互斥

**命令**：`--real-call-run-once --real-call-dry-run`

**实际输出**：
```
ERROR：--real-call-run-once 与 --real-call-dry-run 冲突，不能同时使用。
```

**判定**：PASS — CLI ERROR，命令直接拒绝

| 字段 | 值 |
|------|------|
| CHECK_RESULT | CLI ERROR |
| REAL_TASK_EXECUTION | no |
| RUN_PROJECT_TASK_FULL_CALLED | no |
| CLAUDE_CODE_CALLED | no |
| BUSINESS_CODE_CHANGED | no |
| AUTO_CONTINUE_TO_NEXT_TASK | no |
| AUTO_GIT_BACKUP | no |

### 场景 9：--real-call-stub 互斥

**命令**：`--real-call-run-once --real-call-stub`

**实际输出**：
```
ERROR：--real-call 与 --real-call-stub 冲突，不能同时使用。
```

**判定**：PASS — CLI ERROR，命令直接拒绝

| 字段 | 值 |
|------|------|
| CHECK_RESULT | CLI ERROR |
| REAL_TASK_EXECUTION | no |
| RUN_PROJECT_TASK_FULL_CALLED | no |
| CLAUDE_CODE_CALLED | no |
| BUSINESS_CODE_CHANGED | no |
| AUTO_CONTINUE_TO_NEXT_TASK | no |
| AUTO_GIT_BACKUP | no |

### 场景 10：--adapter-dry-run 互斥

**命令**：`--real-call-run-once --adapter-dry-run`

**实际输出**：
```
ERROR：--real-call 与 --adapter-dry-run 冲突，不能同时使用。
```

**判定**：PASS — CLI ERROR，命令直接拒绝

| 字段 | 值 |
|------|------|
| CHECK_RESULT | CLI ERROR |
| REAL_TASK_EXECUTION | no |
| RUN_PROJECT_TASK_FULL_CALLED | no |
| CLAUDE_CODE_CALLED | no |
| BUSINESS_CODE_CHANGED | no |
| AUTO_CONTINUE_TO_NEXT_TASK | no |
| AUTO_GIT_BACKUP | no |

### 对照场景 11：正确参数 safety shell

**命令**：`--max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-run-once`

**实际输出**：
```
EXECUTION_MODE=real_call_run_once_safety_shell
REAL_CALL_ALLOWED=True
RUN_ONCE_REQUESTED=True
RUN_ONCE_SAFETY_SHELL_STARTED=True
TASK_ID=T087
COMMAND=python runner.py run-project-task-full --project ... --task T087
PREFLIGHT_STATUS=passed
REAL_TASK_EXECUTION=no
RUN_PROJECT_TASK_FULL_CALLED=no
CLAUDE_CODE_CALLED=no
BUSINESS_CODE_CHANGED=no
AUTO_CONTINUE_TO_NEXT_TASK=false
AUTO_GIT_BACKUP=false
CHECK_RESULT=pass
STOP_REASON=run_once_safety_shell_only
```

**判定**：PASS — safety shell 正确启动，未执行真实调用

| 字段 | 值 |
|------|------|
| EXECUTION_MODE | real_call_run_once_safety_shell |
| RUN_ONCE_SAFETY_SHELL_STARTED | true |
| REAL_TASK_EXECUTION | no |
| RUN_PROJECT_TASK_FULL_CALLED | no |
| CHECK_RESULT | pass |

## Safety Check

| 安全项 | 结果 |
|--------|------|
| 是否执行真实任务 | no |
| 是否调用 run-project-task-full | no |
| 是否调用 Claude Code | no |
| 是否修改业务代码 | no |
| 是否自动进入下一任务 | no |
| 是否自动 Git 备份 | no |

## Verification Summary

| # | 场景 | 拒绝类型 | 结果 |
|---|------|----------|------|
| 1 | 缺少 --real-call | CLI ERROR | PASS |
| 2 | 缺少 --real-call（有 --execute） | CLI ERROR | PASS |
| 3 | --confirm 值错误 | CHECK_RESULT=fail | PASS |
| 4 | 缺少 --real-confirm | CHECK_RESULT=fail | PASS |
| 5 | --real-confirm 值错误 | CHECK_RESULT=fail | PASS |
| 6 | max-tasks=0 | CHECK_RESULT=fail | PASS |
| 7 | max-tasks=2 | CHECK_RESULT=fail | PASS |
| 8 | --real-call-dry-run 互斥 | CLI ERROR | PASS |
| 9 | --real-call-stub 互斥 | CLI ERROR | PASS |
| 10 | --adapter-dry-run 互斥 | CLI ERROR | PASS |
| 11 | 正确参数对照 | CHECK_RESULT=pass (safety shell) | PASS |

**总计**：10/10 拒绝场景 PASS + 1/1 对照场景 PASS

## Check Result

**pass**

## Next

T088：验证 simulated child CHECK_RESULT=pass
