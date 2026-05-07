# T097 Execute-once Rejection Check

## Goal

验证 `--real-execute-once` 在真实执行前置条件不满足时必须拒绝，并确认正确三重确认只进入 safety gate，不真实执行任务。

## Verification Date

2026-05-07

## Verification Environment

- 工作区状态：clean（T096.1 已提交）
- 最新提交：5ceb951 feat: add first real-run execute-once safety gate

## Commands and Results

### 拒绝场景

#### R1：--real-execute-once 不带任何前置参数

```
python runner.py run-project-loop --project . --max-tasks 1 --real-execute-once
```

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| CLI ERROR | 必须配合 --real-call-run-once | ERROR: --real-execute-once 必须与 --real-call-run-once 使用 | PASS |

#### R2：--real-execute-once 只带 --execute

```
python runner.py run-project-loop --project . --max-tasks 1 --execute --real-execute-once
```

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| CLI ERROR | 必须配合 --real-call-run-once | ERROR: --real-execute-once 必须与 --real-call-run-once 使用 | PASS |

#### R3：缺少 --real-call

```
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-execute-once
```

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| CLI ERROR | 必须配合 --real-call-run-once | ERROR: --real-execute-once 必须与 --real-call-run-once 使用 | PASS |

#### R4：缺少 --real-confirm

```
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-execute-once
```

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| CLI ERROR | 必须配合 --real-call-run-once | ERROR: --real-execute-once 必须与 --real-call-run-once 使用 | PASS |

#### R5：缺少 --real-call-run-once

```
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-execute-once
```

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| CLI ERROR | 必须配合 --real-call-run-once | ERROR: --real-execute-once 必须与 --real-call-run-once 使用 | PASS |

#### R6：缺少 --real-execute-confirm

```
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-run-once --real-execute-once
```

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| REAL_EXECUTE_CONFIRM_STATUS | missing | missing | PASS |
| REAL_EXECUTE_ALLOWED | false | false | PASS |
| STOP_REASON | real_execute_confirm_missing | real_execute_confirm_missing | PASS |
| CHECK_RESULT | fail | fail | PASS |

#### R7：--real-execute-confirm yes

```
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-run-once --real-execute-once --real-execute-confirm yes
```

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| REAL_EXECUTE_CONFIRM_STATUS | rejected | rejected | PASS |
| REAL_EXECUTE_ALLOWED | false | false | PASS |
| STOP_REASON | real_execute_confirm_rejected | real_execute_confirm_rejected | PASS |
| CHECK_RESULT | fail | fail | PASS |

#### R8：--real-execute-confirm ok

```
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-run-once --real-execute-once --real-execute-confirm ok
```

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| REAL_EXECUTE_CONFIRM_STATUS | rejected | rejected | PASS |
| REAL_EXECUTE_ALLOWED | false | false | PASS |
| STOP_REASON | real_execute_confirm_rejected | real_execute_confirm_rejected | PASS |
| CHECK_RESULT | fail | fail | PASS |

#### R9：--real-execute-confirm 确认

```
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-run-once --real-execute-once --real-execute-confirm 确认
```

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| REAL_EXECUTE_CONFIRM_STATUS | rejected | rejected | PASS |
| REAL_EXECUTE_ALLOWED | false | false | PASS |
| STOP_REASON | real_execute_confirm_rejected | real_execute_confirm_rejected | PASS |
| CHECK_RESULT | fail | fail | PASS |

#### R10：--real-execute-confirm EXECUTE_PROJECT_LOOP（错位）

```
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-run-once --real-execute-once --real-execute-confirm EXECUTE_PROJECT_LOOP
```

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| REAL_EXECUTE_CONFIRM_STATUS | rejected | rejected | PASS |
| REAL_EXECUTE_ALLOWED | false | false | PASS |
| STOP_REASON | real_execute_confirm_rejected | real_execute_confirm_rejected | PASS |
| CHECK_RESULT | fail | fail | PASS |

#### R11：--real-execute-confirm EXECUTE_REAL_TASK_ONCE（错位）

```
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-run-once --real-execute-once --real-execute-confirm EXECUTE_REAL_TASK_ONCE
```

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| REAL_EXECUTE_CONFIRM_STATUS | rejected | rejected | PASS |
| REAL_EXECUTE_ALLOWED | false | false | PASS |
| STOP_REASON | real_execute_confirm_rejected | real_execute_confirm_rejected | PASS |
| CHECK_RESULT | fail | fail | PASS |

#### R12：max_tasks=0

```
python runner.py run-project-loop --project . --max-tasks 0 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-run-once --real-execute-once --real-execute-confirm EXECUTE_REAL_RUN_ONCE
```

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| REAL_EXECUTE_ALLOWED | false | false | PASS |
| STOP_REASON | execute_safety_gate_failed:invalid_max_tasks | execute_safety_gate_failed:invalid_max_tasks | PASS |
| CHECK_RESULT | fail | fail | PASS |

#### R13：max_tasks=2

```
python runner.py run-project-loop --project . --max-tasks 2 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-run-once --real-execute-once --real-execute-confirm EXECUTE_REAL_RUN_ONCE
```

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| REAL_EXECUTE_ALLOWED | false | false | PASS |
| STOP_REASON | max_tasks_not_one | max_tasks_not_one | PASS |
| CHECK_RESULT | fail | fail | PASS |

#### R14：--real-call-dry-run 冲突

```
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-run-once --real-execute-once --real-execute-confirm EXECUTE_REAL_RUN_ONCE --real-call-dry-run
```

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| CLI ERROR | 模式互斥 | ERROR: --real-call-run-once 与 --real-call-dry-run 互斥 | PASS |

#### R15：--real-call-stub 冲突

```
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-run-once --real-execute-once --real-execute-confirm EXECUTE_REAL_RUN_ONCE --real-call-stub
```

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| CLI ERROR | 模式互斥 | ERROR: --real-call 与 --real-call-stub 互斥 | PASS |

#### R16：--adapter-dry-run 冲突

```
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-run-once --real-execute-once --real-execute-confirm EXECUTE_REAL_RUN_ONCE --adapter-dry-run
```

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| CLI ERROR | 模式互斥 | ERROR: --real-call 与 --adapter-dry-run 互斥 | PASS |

### 正确三重确认对照验证

#### P1：正确三重确认 + max_tasks=1 + clean workspace

```
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-run-once --real-execute-once --real-execute-confirm EXECUTE_REAL_RUN_ONCE
```

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| EXECUTION_MODE | first_real_run_execute_once_safety_gate | first_real_run_execute_once_safety_gate | PASS |
| REAL_EXECUTE_ONCE_REQUESTED | true | true | PASS |
| REAL_EXECUTE_CONFIRM_STATUS | accepted | accepted | PASS |
| REAL_EXECUTE_ALLOWED | true | true | PASS |
| REAL_TASK_EXECUTION | no | no | PASS |
| RUN_PROJECT_TASK_FULL_CALLED | no | no | PASS |
| CLAUDE_CODE_CALLED | no | no | PASS |
| BUSINESS_CODE_CHANGED | no | no | PASS |
| AUTO_CONTINUE_TO_NEXT_TASK | false | false | PASS |
| AUTO_GIT_BACKUP | false | false | PASS |
| HUMAN_REVIEW_REQUIRED | true | true | PASS |
| CHECK_RESULT | pass | pass | PASS |

## Triple Confirmation Check

三重确认不可互相替代：

| 确认短语 | 对应参数 | 用途 |
|----------|----------|------|
| EXECUTE_PROJECT_LOOP | --confirm | 进入 execute mode |
| EXECUTE_REAL_TASK_ONCE | --real-confirm | 进入 real-call run-once 链路 |
| EXECUTE_REAL_RUN_ONCE | --real-execute-confirm | 允许进入首次真实执行 safety gate |

精确匹配验证结果：

| 输入值 | 预期状态 | 实际状态 | 结果 |
|--------|----------|----------|------|
| 缺失 --real-execute-confirm | missing | missing | PASS |
| yes | rejected | rejected | PASS |
| ok | rejected | rejected | PASS |
| 确认 | rejected | rejected | PASS |
| EXECUTE_PROJECT_LOOP | rejected | rejected | PASS |
| EXECUTE_REAL_TASK_ONCE | rejected | rejected | PASS |
| EXECUTE_REAL_RUN_ONCE | accepted | accepted | PASS |

## Safety Check

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| 是否执行真实任务 | no | no | PASS |
| 是否调用 run-project-task-full | no | no | PASS |
| 是否调用 Claude Code | no | no | PASS |
| 是否修改业务代码 | no | no | PASS |
| 是否自动进入下一任务 | no | no | PASS |
| 是否自动 Git 备份 | no | no | PASS |
| 工作区是否保持 clean | yes | yes | PASS |

## Summary

| 场景 | 结果 |
|------|------|
| R1. 不带任何前置参数 | PASS |
| R2. 只带 --execute | PASS |
| R3. 缺少 --real-call | PASS |
| R4. 缺少 --real-confirm | PASS |
| R5. 缺少 --real-call-run-once | PASS |
| R6. 缺少 --real-execute-confirm | PASS |
| R7. --real-execute-confirm yes | PASS |
| R8. --real-execute-confirm ok | PASS |
| R9. --real-execute-confirm 确认 | PASS |
| R10. --real-execute-confirm EXECUTE_PROJECT_LOOP | PASS |
| R11. --real-execute-confirm EXECUTE_REAL_TASK_ONCE | PASS |
| R12. max_tasks=0 | PASS |
| R13. max_tasks=2 | PASS |
| R14. --real-call-dry-run 冲突 | PASS |
| R15. --real-call-stub 冲突 | PASS |
| R16. --adapter-dry-run 冲突 | PASS |
| P1. 正确三重确认 + clean workspace | PASS |

**总计**：17/17 PASS（16 拒绝 + 1 正确对照）

## Limitation

当前只验证 execute-once safety gate，不实现真实 executor，不真实调用 run-project-task-full。

## Check Result

pass

## Next

T098：实现 first real-run executor simulated child call
