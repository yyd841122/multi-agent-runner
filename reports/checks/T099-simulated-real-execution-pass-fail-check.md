# T099 Simulated Real Execution Pass/Fail Check

## Goal

验证 first real-run executor simulated child call 在 pass / fail / unsafe / parse failure 场景下均能正确输出验收状态，并且所有场景都停止等待人工处理。

## Verification Date

2026-05-07

## Verification Environment

- 工作区状态：clean
- 最新提交：e863499 feat: add first real-run executor simulated child call
- CLI 层 E2E 验证（完整 run-project-loop 命令）

## Commands

```bash
# S1: pass
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-run-once --real-execute-once --real-execute-confirm EXECUTE_REAL_RUN_ONCE --simulate-child --child-sample pass

# S2: fail
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-run-once --real-execute-once --real-execute-confirm EXECUTE_REAL_RUN_ONCE --simulate-child --child-sample fail

# S3: missing-check-result
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-run-once --real-execute-once --real-execute-confirm EXECUTE_REAL_RUN_ONCE --simulate-child --child-sample missing-check-result

# S4: dirty-unexpected
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-run-once --real-execute-once --real-execute-confirm EXECUTE_REAL_RUN_ONCE --simulate-child --child-sample dirty-unexpected

# S5: unsafe-unknown
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-run-once --real-execute-once --real-execute-confirm EXECUTE_REAL_RUN_ONCE --simulate-child --child-sample unsafe-unknown

# S6: missing-report-paths
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-run-once --real-execute-once --real-execute-confirm EXECUTE_REAL_RUN_ONCE --simulate-child --child-sample missing-report-paths
```

## Expected Result

| Sample | Expected Acceptance Status | Expected Check Result |
|---|---|---|
| pass | ready_for_human_review | pass |
| fail | blocked | fail |
| missing-check-result | failed_to_parse | fail |
| dirty-unexpected | blocked | fail |
| unsafe-unknown | unsafe_to_continue | fail |
| missing-report-paths | blocked | fail |

所有场景还必须满足：

- REAL_TASK_EXECUTION=no
- RUN_PROJECT_TASK_FULL_CALLED=no
- CLAUDE_CODE_CALLED=no
- BUSINESS_CODE_CHANGED=no
- AUTO_CONTINUE_TO_NEXT_TASK=false
- AUTO_GIT_BACKUP=false
- HUMAN_REVIEW_REQUIRED=true

## Actual Result

### S1：pass → ready_for_human_review

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| EXECUTION_MODE | first_real_run_executor_simulated_child_call | first_real_run_executor_simulated_child_call | PASS |
| SAFETY_GATE_STATUS | passed | passed | PASS |
| REAL_EXECUTE_ALLOWED | true | true | PASS |
| SIMULATED_CHILD_CALL | true | true | PASS |
| CHILD_CHECK_RESULT | pass | pass | PASS |
| CHILD_TASK_STATUS | done | done | PASS |
| PARSE_CHECK_RESULT | pass | pass | PASS |
| ACCEPTANCE_STATUS | ready_for_human_review | ready_for_human_review | PASS |
| CHECK_RESULT | pass | pass | PASS |
| STOP_REASON | first_real_execution_requires_review | first_real_execution_requires_review | PASS |
| NEXT_ACTION | ready_for_human_review | ready_for_human_review | PASS |

### S2：fail → blocked

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| CHILD_CHECK_RESULT | fail | fail | PASS |
| CHILD_TASK_STATUS | failed | failed | PASS |
| ACCEPTANCE_STATUS | blocked | blocked | PASS |
| CHECK_RESULT | fail | fail | PASS |
| STOP_REASON | child_check_result_failed | child_check_result_failed | PASS |
| NEXT_ACTION | review_failure_before_continue | review_failure_before_continue | PASS |

### S3：missing-check-result → failed_to_parse

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| CHILD_CHECK_RESULT | unknown | unknown | PASS |
| PARSE_CHECK_RESULT | fail | fail | PASS |
| ACCEPTANCE_STATUS | failed_to_parse | failed_to_parse | PASS |
| CHECK_RESULT | fail | fail | PASS |
| STOP_REASON | missing_check_result | missing_check_result | PASS |
| NEXT_ACTION | review_parse_failure | review_parse_failure | PASS |

### S4：dirty-unexpected → blocked

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| CHILD_CHECK_RESULT | pass | pass | PASS |
| WORKSPACE_CHANGE_CLASSIFICATION | dirty_unexpected | dirty_unexpected | PASS |
| ACCEPTANCE_STATUS | blocked | blocked | PASS |
| CHECK_RESULT | fail | fail | PASS |
| STOP_REASON | dirty_unexpected | dirty_unexpected | PASS |
| NEXT_ACTION | review_failure_before_continue | review_failure_before_continue | PASS |

### S5：unsafe-unknown → unsafe_to_continue

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| CHILD_CHECK_RESULT | pass | pass | PASS |
| WORKSPACE_CHANGE_CLASSIFICATION | dirty_unknown | dirty_unknown | PASS |
| ACCEPTANCE_STATUS | unsafe_to_continue | unsafe_to_continue | PASS |
| CHECK_RESULT | fail | fail | PASS |
| STOP_REASON | dirty_unknown | dirty_unknown | PASS |
| NEXT_ACTION | manual_review_required | manual_review_required | PASS |

### S6：missing-report-paths → blocked

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| CHILD_CHECK_RESULT | pass | pass | PASS |
| ACCEPTANCE_STATUS | blocked | blocked | PASS |
| CHECK_RESULT | fail | fail | PASS |
| STOP_REASON | missing_report_paths | missing_report_paths | PASS |
| NEXT_ACTION | review_failure_before_continue | review_failure_before_continue | PASS |

### 安全字段验证（所有 6 个场景）

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| REAL_TASK_EXECUTION | no（所有场景） | no | PASS |
| RUN_PROJECT_TASK_FULL_CALLED | no（所有场景） | no | PASS |
| CLAUDE_CODE_CALLED | no（所有场景） | no | PASS |
| BUSINESS_CODE_CHANGED | no（所有场景） | no | PASS |
| AUTO_CONTINUE_TO_NEXT_TASK | false（所有场景） | false | PASS |
| AUTO_GIT_BACKUP | false（所有场景） | false | PASS |
| HUMAN_REVIEW_REQUIRED | true（所有场景） | true | PASS |

## Pass Stop Behavior

S1（pass）验证结果：

- CHECK_RESULT=pass
- ACCEPTANCE_STATUS=ready_for_human_review
- STOP_REASON=first_real_execution_requires_review
- NEXT_ACTION=ready_for_human_review
- AUTO_CONTINUE_TO_NEXT_TASK=false
- AUTO_GIT_BACKUP=false
- HUMAN_REVIEW_REQUIRED=true

即使 simulated child pass，也不能自动进入下一任务。必须等待人工验收。

## Fail Stop Behavior

S2-S6（fail / blocked / unsafe / parse failure）验证结果：

| Sample | ACCEPTANCE_STATUS | NEXT_ACTION |
|--------|-------------------|-------------|
| fail | blocked | review_failure_before_continue |
| missing-check-result | failed_to_parse | review_parse_failure |
| dirty-unexpected | blocked | review_failure_before_continue |
| unsafe-unknown | unsafe_to_continue | manual_review_required |
| missing-report-paths | blocked | review_failure_before_continue |

所有 fail 场景：
- AUTO_CONTINUE_TO_NEXT_TASK=false
- AUTO_GIT_BACKUP=false
- HUMAN_REVIEW_REQUIRED=true

fail 后不能自动返工、不能自动进入下一任务、不能自动提交。必须等待人工处理。

## Safety Check

| 检查项 | 结果 |
|--------|------|
| 是否执行真实任务 | no |
| 是否调用 run-project-task-full | no |
| 是否调用 Claude Code | no |
| 是否修改业务代码 | no |
| 是否自动进入下一任务 | no |
| 是否自动 Git 备份 | no |

验证后 `git status --short` 无输出，工作区保持 clean。

## Limitation

- 当前为 simulated child call，使用内置 sample stdout 构造数据，不验证真实 child stdout 格式
- 不验证真实 child 执行过程中的 stderr 捕获
- 不验证真实 child 执行的 exit code 非 0 场景
- 真实 executor 验证需 T100 实现

## Summary

| 场景 | 结果 |
|------|------|
| S1. pass → ready_for_human_review | PASS |
| S2. fail → blocked | PASS |
| S3. missing-check-result → failed_to_parse | PASS |
| S4. dirty-unexpected → blocked | PASS |
| S5. unsafe-unknown → unsafe_to_continue | PASS |
| S6. missing-report-paths → blocked | PASS |
| 安全字段（7 项 × 6 场景） | PASS |

**总计**：6/6 PASS（含安全字段验证）

## Check Result

pass

## Next

T100：执行第一次真实 run-project-task-full 调用
