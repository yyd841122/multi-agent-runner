# T085 Real-Call Run-Once Safety Shell Check

## 验证目标

验证 `--real-call-run-once` 参数的拒绝场景和安全 shell pass 行为。

## 验证环境

- 工作区状态：dirty（T085 实现文件已修改但未提交）
- 已知限制：clean workspace pass 场景需要提交后验证，当前通过函数级验证确认

## 验证场景

### 场景 1：不带 --real-call-run-once → T079 real-call dry-run executor 行为保持不变

**命令**：
```bash
python runner.py run-project-loop --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-dry-run
```

**预期**：EXECUTION_MODE=real_call_dry_run_executor

**实际**：PASS
- EXECUTION_MODE=real_call_dry_run_executor
- 不触发 --real-call-run-once 分支

### 场景 2：--real-call-run-once 不带 --real-confirm → 拒绝

**命令**：
```bash
python runner.py run-project-loop --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-call-run-once
```

**预期**：REAL_CALL_ALLOWED=false, CHECK_RESULT=fail, real_confirm_missing

**实际**：PASS
- EXECUTION_MODE=real_call_run_once_safety_shell
- REAL_CALL_ALLOWED=False
- RUN_ONCE_SAFETY_SHELL_STARTED=False
- CHECK_RESULT=fail
- stop_reason 包含 real_confirm_missing

### 场景 3：--real-call-run-once 不带 --execute → 拒绝

**命令**：
```bash
python runner.py run-project-loop --max-tasks 1 --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-run-once
```

**预期**：CLI 层拒绝（--real-call 必须配合 --execute）

**实际**：PASS
- ERROR：--real-call 必须配合 --execute 使用

### 场景 4：--real-call-run-once confirm 错误 → 拒绝

**命令**：
```bash
python runner.py run-project-loop --max-tasks 1 --execute --confirm WRONG_CONFIRM --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-run-once
```

**预期**：CHECK_RESULT=fail, confirm_rejected

**实际**：PASS
- CHECK_RESULT=fail
- RUN_ONCE_SAFETY_SHELL_STARTED=False

### 场景 5：--real-call-run-once real-confirm 错误 → 拒绝

**命令**：
```bash
python runner.py run-project-loop --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm WRONG_CONFIRM --real-call-run-once
```

**预期**：CHECK_RESULT=fail, real_confirm_rejected

**实际**：PASS
- CHECK_RESULT=fail
- RUN_ONCE_SAFETY_SHELL_STARTED=False

### 场景 6：--real-call-run-once max_tasks=0 → 拒绝

**命令**：
```bash
python runner.py run-project-loop --max-tasks 0 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-run-once
```

**预期**：CHECK_RESULT=fail

**实际**：PASS
- CHECK_RESULT=fail
- RUN_ONCE_SAFETY_SHELL_STARTED=False

### 场景 7：--real-call-run-once max_tasks=2 → 拒绝

**命令**：
```bash
python runner.py run-project-loop --max-tasks 2 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-run-once
```

**预期**：CHECK_RESULT=fail, max_tasks_not_one

**实际**：PASS
- CHECK_RESULT=fail
- RUN_ONCE_SAFETY_SHELL_STARTED=False

### 场景 8：--real-call-run-once 同时传 --real-call-dry-run → 拒绝

**命令**：
```bash
python runner.py run-project-loop --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-run-once --real-call-dry-run
```

**预期**：CLI 层互斥拒绝

**实际**：PASS
- ERROR：--real-call-run-once 和 --real-call-dry-run 互斥

### 场景 9：--real-call-run-once 同时传 --real-call-stub → 拒绝

**命令**：
```bash
python runner.py run-project-loop --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-run-once --real-call-stub
```

**预期**：CLI 层互斥拒绝

**实际**：PASS
- ERROR：--real-call 和 --real-call-stub 互斥

### 场景 10：正确双确认 + max_tasks=1 + real-call-run-once（dirty workspace）

**命令**：
```bash
python runner.py run-project-loop --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-run-once
```

**预期**：因工作区 dirty 被 safety gate 拒绝

**实际**：PASS
- EXECUTION_MODE=real_call_run_once_safety_shell
- REAL_CALL_ALLOWED=False
- STOP_REASON=execute_safety_gate_failed:initial_worktree_dirty
- REAL_TASK_EXECUTION=no
- RUN_PROJECT_TASK_FULL_CALLED=no
- CLAUDE_CODE_CALLED=no
- BUSINESS_CODE_CHANGED=no
- AUTO_CONTINUE_TO_NEXT_TASK=false
- AUTO_GIT_BACKUP=false
- HUMAN_REVIEW_REQUIRED=true
- CHECK_RESULT=fail

**说明**：clean workspace 下的 pass 路径需要提交后验证（T087 将做完整验证）。函数级验证确认数据结构正确，所有字段符合预期。

### 场景 11：输出包含未来 command / function_call（函数级验证）

**验证方式**：直接构造 RealCallRunOnceResult 并验证字段值

**实际**：PASS
- command 包含 `python runner.py run-project-task-full --project ... --task ...`
- function_call 包含 `run_project_task_full(project_path=..., task_id=...)`
- real_task_execution=no
- run_project_task_full_called=no
- 未执行 command / function_call

### 场景 12：所有路径安全保证

**验证项**：
- 所有路径未调用 run-project-task-full：PASS（RUN_PROJECT_TASK_FULL_CALLED=no 在所有场景）
- 所有路径未调用 Claude Code：PASS（CLAUDE_CODE_CALLED=no 在所有场景）
- 所有路径未修改业务代码：PASS（BUSINESS_CODE_CHANGED=no 在所有场景）
- 所有路径未自动进入下一任务：PASS（AUTO_CONTINUE_TO_NEXT_TASK=false 在所有场景）
- 所有路径未自动 Git 备份：PASS（AUTO_GIT_BACKUP=false 在所有场景）

## 验证总结

| 场景 | 结果 |
|------|------|
| 1. 不带 --real-call-run-once | PASS |
| 2. 不带 --real-confirm | PASS |
| 3. 不带 --execute | PASS |
| 4. confirm 错误 | PASS |
| 5. real-confirm 错误 | PASS |
| 6. max_tasks=0 | PASS |
| 7. max_tasks=2 | PASS |
| 8. + --real-call-dry-run | PASS |
| 9. + --real-call-stub | PASS |
| 10. 正确双确认（dirty workspace） | PASS |
| 11. command/function_call 构造 | PASS |
| 12. 所有路径安全保证 | PASS |

**总计**：12/12 PASS
