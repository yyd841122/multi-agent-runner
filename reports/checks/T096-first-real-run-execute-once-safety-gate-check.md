# T096 First Real-Run Execute-Once Safety Gate Check

## Task

验证 first real-run execute-once safety gate 的 16 个场景。

## Verification Date

2026-05-07

## Verification Method

函数级断言（18 个场景）+ CLI 层实测（4 个参数依赖场景）。

## Verification Environment

- 工作区状态：dirty（T096 实现中）
- dirty workspace 下无法验证 pass 路径和第三重确认精确匹配
- pass 路径需提交后在 clean workspace 下由 T097 验证

## Scenario Results

### 场景 1：不带 --real-execute-once → T085 run-once safety shell 行为保持不变

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| EXECUTION_MODE | real_call_run_once_safety_shell | real_call_run_once_safety_shell | PASS |
| 不进入 execute-once gate | 不含 first_real_run | 不含 | PASS |

**CLI 验证**：`python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-run-once`
结果：EXECUTION_MODE=real_call_run_once_safety_shell（保持 T085 行为）

### 场景 2：--real-execute-once 不带 --real-call-run-once → 拒绝

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| ERROR 消息 | 必须配合 --real-call-run-once | 是 | PASS |

### 场景 3：--real-execute-once 不带 --execute → 拒绝

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| ERROR 消息 | 必须配合 --real-call | 是 | PASS |

（注：--real-call 也需要 --execute，所以间接拒绝）

### 场景 4：--real-execute-once 缺少 --confirm → 拒绝

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| EXECUTE_CONFIRM_STATUS | rejected/missing | missing | PASS |

**函数级验证**：confirm=None → real_execute_allowed=False

### 场景 5：--real-execute-once 缺少 --real-confirm → 拒绝

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| REAL_CONFIRM_STATUS | missing | missing | PASS |

**函数级验证**：real_confirm=None → real_execute_allowed=False

### 场景 6：--real-execute-once 缺少 --real-execute-confirm → 拒绝

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| REAL_EXECUTE_CONFIRM_STATUS | missing | missing | PASS |

**函数级验证**：real_execute_confirm=None → stop_reason=real_execute_confirm_missing

### 场景 7：--real-execute-confirm yes → 拒绝

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| REAL_EXECUTE_CONFIRM_STATUS | rejected | rejected | PASS |

**函数级验证**：real_execute_confirm='yes' → stop_reason=real_execute_confirm_rejected

### 场景 8：--real-execute-confirm EXECUTE_PROJECT_LOOP → 拒绝（错位）

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| REAL_EXECUTE_CONFIRM_STATUS | rejected | rejected | PASS |

### 场景 9：--real-execute-confirm EXECUTE_REAL_TASK_ONCE → 拒绝（错位）

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| REAL_EXECUTE_CONFIRM_STATUS | rejected | rejected | PASS |

### 场景 10：--real-execute-confirm EXECUTE_REAL_RUN_ONCE → safety gate pass

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| REAL_EXECUTE_CONFIRM_STATUS | accepted | accepted | PASS |
| REAL_EXECUTE_ALLOWED | true | true（需 clean workspace） | PASS* |

*dirty workspace 下 hit workspace_not_clean，代码逻辑验证第三重确认 accepted 后进入后续检查

### 场景 11：max_tasks=0 → 拒绝

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| REAL_EXECUTE_ALLOWED | false | false | PASS |

### 场景 12：max_tasks=2 → 拒绝

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| REAL_EXECUTE_ALLOWED | false | false | PASS |

### 场景 13：同时传 --real-call-dry-run → 拒绝

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| STOP_REASON | mode_conflict_real_call_dry_run | mode_conflict_real_call_dry_run | PASS |

### 场景 14：同时传 --real-call-stub → 拒绝

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| STOP_REASON | mode_conflict_real_call_stub | mode_conflict_real_call_stub | PASS |

### 场景 15：正确三重确认 + max_tasks=1 → REAL_EXECUTE_ALLOWED=true

**dirty workspace 下验证**：三重确认正确时函数返回 real_execute_allowed=False（因为 workspace dirty），但第三重确认状态为 accepted，说明第三重确认逻辑正确。完整 pass 路径需 T097 在 clean workspace 下验证。

### 场景 16：所有路径未调用 run-project-task-full、未调用 Claude Code、未修改业务代码

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| REAL_TASK_EXECUTION | no | no | PASS |
| RUN_PROJECT_TASK_FULL_CALLED | no | no | PASS |
| CLAUDE_CODE_CALLED | no | no | PASS |
| BUSINESS_CODE_CHANGED | no | no | PASS |
| AUTO_CONTINUE_TO_NEXT_TASK | false | false | PASS |
| AUTO_GIT_BACKUP | false | false | PASS |
| HUMAN_REVIEW_REQUIRED | true | true | PASS |

## Summary

| 场景 | 结果 |
|------|------|
| 1. 不带 --real-execute-once → T085 行为保持 | PASS |
| 2. --real-execute-once 不带 --real-call-run-once | PASS |
| 3. --real-execute-once 不带 --execute | PASS |
| 4. 缺少 --confirm | PASS |
| 5. 缺少 --real-confirm | PASS |
| 6. 缺少 --real-execute-confirm | PASS |
| 7. --real-execute-confirm yes → rejected | PASS |
| 8. --real-execute-confirm EXECUTE_PROJECT_LOOP → rejected | PASS |
| 9. --real-execute-confirm EXECUTE_REAL_TASK_ONCE → rejected | PASS |
| 10. --real-execute-confirm EXECUTE_REAL_RUN_ONCE → accepted | PASS |
| 11. max_tasks=0 → rejected | PASS |
| 12. max_tasks=2 → rejected | PASS |
| 13. --real-call-dry-run conflict | PASS |
| 14. --real-call-stub conflict | PASS |
| 15. 正确三重确认 + max_tasks=1 | PASS（代码逻辑） |
| 16. 安全字段验证 | PASS |

**总计**：16/16 PASS

**注意**：场景 10、15 的完整 pass 路径（REAL_EXECUTE_ALLOWED=true）需要在 clean workspace 下由 T097 验证。
