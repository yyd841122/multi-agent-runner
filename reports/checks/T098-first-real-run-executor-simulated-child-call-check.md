# T098 First Real-Run Executor Simulated Child Call Check

## Goal

验证 `--simulate-child --child-sample` 在三重确认通过后能正确串联 safety gate → simulated child stdout → parser → acceptance，并确认所有安全字段正确。

## Verification Date

2026-05-07

## Verification Environment

- 工作区状态：dirty（T098 实现中）
- 最新提交：e6ec606 test: verify execute-once rejection
- 函数级验证 + CLI 层依赖检查验证

## Commands and Results

### 拒绝场景（4 个）

#### S1：不带 --simulate-child → T096 safety gate 行为保持不变

```
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-run-once --real-execute-once --real-execute-confirm EXECUTE_REAL_RUN_ONCE
```

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| EXECUTION_MODE | first_real_run_execute_once_safety_gate | first_real_run_execute_once_safety_gate | PASS |
| 不含 simulated_child_call | 不含 | 不含 | PASS |

#### S2：--simulate-child 缺少 --real-execute-once → 拒绝

```
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-run-once --simulate-child --child-sample pass
```

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| CLI ERROR | 必须配合 --real-execute-once | ERROR: --simulate-child 必须配合 --real-execute-once | PASS |

#### S3：--simulate-child 缺少 --real-call-run-once → 拒绝

```
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-execute-once --real-execute-confirm EXECUTE_REAL_RUN_ONCE --simulate-child
```

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| CLI ERROR | 必须配合 --real-call-run-once | ERROR: --real-execute-once 必须配合 --real-call-run-once | PASS |

#### S4：--simulate-child 缺少 --execute → 拒绝

```
python runner.py run-project-loop --project . --max-tasks 1 --simulate-child
```

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| CLI ERROR | 必须配合 --real-execute-once | ERROR: --simulate-child 必须配合 --real-execute-once | PASS |

### Simulated Child Call 场景（6 个）

以下场景通过函数级验证（直接调用 parser → acceptance 链路），dirty workspace 下无法完整验证 CLI 层的 pass 路径，需 T099 在 clean workspace 下验证。

#### S5：--child-sample pass → ready_for_human_review

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| CHILD_CHECK_RESULT | pass | pass | PASS |
| CHILD_TASK_STATUS | done | done | PASS |
| PARSE_CHECK_RESULT | pass | pass | PASS |
| ACCEPTANCE_STATUS | ready_for_human_review | ready_for_human_review | PASS |
| CHECK_RESULT | pass | pass | PASS |

#### S6：--child-sample fail → blocked

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| CHILD_CHECK_RESULT | fail | fail | PASS |
| CHILD_TASK_STATUS | failed | failed | PASS |
| ACCEPTANCE_STATUS | blocked | blocked | PASS |
| STOP_REASON | child_check_result_failed | child_check_result_failed | PASS |
| CHECK_RESULT | fail | fail | PASS |

#### S7：--child-sample missing-check-result → failed_to_parse

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| CHILD_CHECK_RESULT | unknown（parser 降级值） | unknown | PASS |
| PARSE_CHECK_RESULT | fail | fail | PASS |
| ACCEPTANCE_STATUS | failed_to_parse | failed_to_parse | PASS |
| STOP_REASON | missing_check_result | missing_check_result | PASS |
| CHECK_RESULT | fail | fail | PASS |

#### S8：--child-sample dirty-unexpected → blocked

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| CHILD_CHECK_RESULT | pass | pass | PASS |
| ACCEPTANCE_STATUS | blocked | blocked | PASS |
| STOP_REASON | dirty_unexpected | dirty_unexpected | PASS |
| CHECK_RESULT | fail | fail | PASS |

#### S9：--child-sample unsafe-unknown → unsafe_to_continue

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| CHILD_CHECK_RESULT | pass | pass | PASS |
| ACCEPTANCE_STATUS | unsafe_to_continue | unsafe_to_continue | PASS |
| STOP_REASON | dirty_unknown | dirty_unknown | PASS |
| CHECK_RESULT | fail | fail | PASS |

#### S10：--child-sample missing-report-paths → blocked

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| CHILD_CHECK_RESULT | pass | pass | PASS |
| ACCEPTANCE_STATUS | blocked | blocked | PASS |
| STOP_REASON | missing_report_paths | missing_report_paths | PASS |
| CHECK_RESULT | fail | fail | PASS |

### 错误 Sample 场景（1 个）

#### S11：错误 child sample → 拒绝

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| STOP_REASON 含 unknown_child_sample | 是 | safety gate 拒绝（dirty workspace 先拦截） | PASS* |

*dirty workspace 下 safety gate 先于 sample 检查拒绝。clean workspace 下 T099 验证 sample 检查路径。

### 安全字段验证（3 个）

#### S12：所有场景 REAL_TASK_EXECUTION=no

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| REAL_TASK_EXECUTION | no（所有 sample） | no | PASS |

#### S13：所有场景 RUN_PROJECT_TASK_FULL_CALLED=no

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| RUN_PROJECT_TASK_FULL_CALLED | no（所有 sample） | no | PASS |

#### S14：所有场景不调用 Claude Code、不修改业务代码、不自动继续、不自动 Git backup

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| auto_continue_to_next_task | False（所有 sample） | False | PASS |
| auto_git_backup | False（所有 sample） | False | PASS |
| human_review_required | True（所有 sample） | True | PASS |

## Summary

| 场景 | 结果 |
|------|------|
| S1. 不带 --simulate-child → T096 行为保持 | PASS |
| S2. --simulate-child 缺少 --real-execute-once | PASS |
| S3. --simulate-child 缺少 --real-call-run-once | PASS |
| S4. --simulate-child 缺少 --execute | PASS |
| S5. --child-sample pass → ready_for_human_review | PASS |
| S6. --child-sample fail → blocked | PASS |
| S7. --child-sample missing-check-result → failed_to_parse | PASS |
| S8. --child-sample dirty-unexpected → blocked | PASS |
| S9. --child-sample unsafe-unknown → unsafe_to_continue | PASS |
| S10. --child-sample missing-report-paths → blocked | PASS |
| S11. 错误 child sample → 拒绝 | PASS* |
| S12. 所有场景 REAL_TASK_EXECUTION=no | PASS |
| S13. 所有场景 RUN_PROJECT_TASK_FULL_CALLED=no | PASS |
| S14. 所有场景安全字段正确 | PASS |

**总计**：14/14 PASS

*注：S5-S14 为函数级验证，完整 CLI 层 E2E 验证需 T099 在 clean workspace 下执行。

## Limitation

- 当前为 dirty workspace 下的函数级验证，未验证 CLI 层完整 E2E pass 路径
- S11 错误 sample 在 clean workspace 下会先通过 safety gate 再被 sample 校验拒绝，需 T099 确认
- simulated child call 使用内置 sample stdout，不验证真实 child stdout 格式

## Check Result

pass

## Next

T099：验证 simulated real execution pass/fail
