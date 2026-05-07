# T094 First Real-run Acceptance Pass/Fail Check

## Goal

验证 first real-run acceptance parser 在 pass / fail / blocked / unsafe / parse failure 场景下均能正确输出验收状态，并且所有场景都停止等待人工处理。

## Commands

### CLI 验证命令

```bash
python runner.py simulated-first-real-run-acceptance --sample pass
python runner.py simulated-first-real-run-acceptance --sample pass-dirty-reports
python runner.py simulated-first-real-run-acceptance --sample fail
python runner.py simulated-first-real-run-acceptance --sample missing-check-result
python runner.py simulated-first-real-run-acceptance --sample unsafe-unknown
python runner.py simulated-first-real-run-acceptance --sample dirty-unexpected
python runner.py simulated-first-real-run-acceptance --sample missing-report-paths
python runner.py simulated-first-real-run-acceptance --sample task-status-failed
```

### Unknown 字段验证

```python
# 直接调用 evaluate_first_real_run_acceptance 传入 unknown 值
evaluate_first_real_run_acceptance(..., claude_code_called='unknown', business_code_changed='unknown')
```

## Expected Result

| Sample | Expected Acceptance Status | Expected Check Result |
|--------|---------------------------|----------------------|
| pass | ready_for_human_review | pass |
| pass-dirty-reports | ready_for_human_review | pass |
| fail | blocked | fail |
| missing-check-result | failed_to_parse | fail |
| unsafe-unknown | unsafe_to_continue | fail |
| dirty-unexpected | blocked | fail |
| missing-report-paths | blocked | fail |
| task-status-failed | blocked | fail |

所有场景还必须满足：

- HUMAN_REVIEW_REQUIRED=true
- AUTO_CONTINUE_TO_NEXT_TASK=false
- AUTO_GIT_BACKUP=false
- REAL_TASK_EXECUTION=no（SAFETY OVERRIDE）
- RUN_PROJECT_TASK_FULL_CALLED=no（SAFETY OVERRIDE）
- CLAUDE_CODE_CALLED=no（SAFETY OVERRIDE）
- BUSINESS_CODE_CHANGED=no（SAFETY OVERRIDE）

## Actual Result

### Sample pass

| 字段 | 实际值 | 预期值 | 结果 |
|------|--------|--------|------|
| ACCEPTANCE_STATUS | ready_for_human_review | ready_for_human_review | PASS |
| CHECK_RESULT | pass | pass | PASS |
| CHILD_CHECK_RESULT | pass | pass | PASS |
| CHILD_TASK_STATUS | done | done | PASS |
| WORKSPACE_CHANGE_CLASSIFICATION | clean | clean | PASS |
| REPORT_PATHS | 2 paths | 2 paths | PASS |
| STOP_REASON | first_real_execution_requires_review | first_real_execution_requires_review | PASS |
| NEXT_ACTION | review_real_task_execution_result | review_real_task_execution_result | PASS |
| HUMAN_REVIEW_REQUIRED | True | True | PASS |
| AUTO_CONTINUE_TO_NEXT_TASK | False | False | PASS |
| AUTO_GIT_BACKUP | False | False | PASS |
| SAFETY OVERRIDE | 4 no | 4 no | PASS |

### Sample pass-dirty-reports

| 字段 | 实际值 | 预期值 | 结果 |
|------|--------|--------|------|
| ACCEPTANCE_STATUS | ready_for_human_review | ready_for_human_review | PASS |
| CHECK_RESULT | pass | pass | PASS |
| WORKSPACE_CHANGE_CLASSIFICATION | dirty_reports_only | dirty_reports_only | PASS |
| STOP_REASON | first_real_execution_requires_review | first_real_execution_requires_review | PASS |
| NEXT_ACTION | review_real_task_execution_result | review_real_task_execution_result | PASS |
| HUMAN_REVIEW_REQUIRED | True | True | PASS |
| AUTO_CONTINUE_TO_NEXT_TASK | False | False | PASS |
| AUTO_GIT_BACKUP | False | False | PASS |
| SAFETY OVERRIDE | 4 no | 4 no | PASS |

### Sample fail

| 字段 | 实际值 | 预期值 | 结果 |
|------|--------|--------|------|
| ACCEPTANCE_STATUS | blocked | blocked | PASS |
| CHECK_RESULT | fail | fail | PASS |
| CHILD_CHECK_RESULT | fail | fail | PASS |
| STOP_REASON | child_check_result_failed | child_check_result_failed | PASS |
| NEXT_ACTION | review_failure_before_continue | review_failure_before_continue | PASS |
| HUMAN_REVIEW_REQUIRED | True | True | PASS |
| AUTO_CONTINUE_TO_NEXT_TASK | False | False | PASS |
| AUTO_GIT_BACKUP | False | False | PASS |

### Sample missing-check-result

| 字段 | 实际值 | 预期值 | 结果 |
|------|--------|--------|------|
| ACCEPTANCE_STATUS | failed_to_parse | failed_to_parse | PASS |
| CHECK_RESULT | fail | fail | PASS |
| CHILD_CHECK_RESULT | missing | missing | PASS |
| STOP_REASON | missing_check_result | missing_check_result | PASS |
| NEXT_ACTION | review_parse_failure | review_parse_failure | PASS |
| REPORT_PATHS | NONE | NONE | PASS |
| HUMAN_REVIEW_REQUIRED | True | True | PASS |
| AUTO_CONTINUE_TO_NEXT_TASK | False | False | PASS |
| AUTO_GIT_BACKUP | False | False | PASS |

### Sample unsafe-unknown

| 字段 | 实际值 | 预期值 | 结果 |
|------|--------|--------|------|
| ACCEPTANCE_STATUS | unsafe_to_continue | unsafe_to_continue | PASS |
| CHECK_RESULT | fail | fail | PASS |
| WORKSPACE_CHANGE_CLASSIFICATION | dirty_unknown | dirty_unknown | PASS |
| STOP_REASON | dirty_unknown | dirty_unknown | PASS |
| NEXT_ACTION | manual_review_required | manual_review_required | PASS |
| HUMAN_REVIEW_REQUIRED | True | True | PASS |
| AUTO_CONTINUE_TO_NEXT_TASK | False | False | PASS |
| AUTO_GIT_BACKUP | False | False | PASS |

### Sample dirty-unexpected

| 字段 | 实际值 | 预期值 | 结果 |
|------|--------|--------|------|
| ACCEPTANCE_STATUS | blocked | blocked | PASS |
| CHECK_RESULT | fail | fail | PASS |
| WORKSPACE_CHANGE_CLASSIFICATION | dirty_unexpected | dirty_unexpected | PASS |
| STOP_REASON | dirty_unexpected | dirty_unexpected | PASS |
| NEXT_ACTION | review_unexpected_changes | review_unexpected_changes | PASS |
| HUMAN_REVIEW_REQUIRED | True | True | PASS |
| AUTO_CONTINUE_TO_NEXT_TASK | False | False | PASS |
| AUTO_GIT_BACKUP | False | False | PASS |

### Sample missing-report-paths

| 字段 | 实际值 | 预期值 | 结果 |
|------|--------|--------|------|
| ACCEPTANCE_STATUS | blocked | blocked | PASS |
| CHECK_RESULT | fail | fail | PASS |
| REPORT_PATHS | NONE | NONE | PASS |
| STOP_REASON | missing_report_paths | missing_report_paths | PASS |
| NEXT_ACTION | check_report_generation | check_report_generation | PASS |
| HUMAN_REVIEW_REQUIRED | True | True | PASS |
| AUTO_CONTINUE_TO_NEXT_TASK | False | False | PASS |
| AUTO_GIT_BACKUP | False | False | PASS |

### Sample task-status-failed

| 字段 | 实际值 | 预期值 | 结果 |
|------|--------|--------|------|
| ACCEPTANCE_STATUS | blocked | blocked | PASS |
| CHECK_RESULT | fail | fail | PASS |
| CHILD_TASK_STATUS | failed | failed | PASS |
| STOP_REASON | child_task_status_failed | child_task_status_failed | PASS |
| NEXT_ACTION | review_failure_before_continue | review_failure_before_continue | PASS |
| HUMAN_REVIEW_REQUIRED | True | True | PASS |
| AUTO_CONTINUE_TO_NEXT_TASK | False | False | PASS |
| AUTO_GIT_BACKUP | False | False | PASS |

### SAFETY OVERRIDE 汇总

所有 8 个 CLI 样本均输出安全覆盖字段：

| 安全字段 | 值 | 8/8 结果 |
|----------|------|---------|
| REAL_TASK_EXECUTION | no | PASS |
| RUN_PROJECT_TASK_FULL_CALLED | no | PASS |
| CLAUDE_CODE_CALLED | no | PASS |
| BUSINESS_CODE_CHANGED | no | PASS |

## Pass Stop Behavior

pass 场景（pass, pass-dirty-reports）停止约束验证：

| 约束项 | pass | pass-dirty-reports | 说明 |
|--------|------|-------------------|------|
| ACCEPTANCE_STATUS | ready_for_human_review | ready_for_human_review | 即使成功也需人工验收 |
| STOP_REASON | first_real_execution_requires_review | first_real_execution_requires_review | 首次执行必须审查 |
| NEXT_ACTION | review_real_task_execution_result | review_real_task_execution_result | 引导人工审查 |
| AUTO_CONTINUE | False | False | 不自动进入下一任务 |
| AUTO_GIT_BACKUP | False | False | 不自动 Git 备份 |
| HUMAN_REVIEW | True | True | 必须人工验收 |

**结论**：即使 simulated child CHECK_RESULT=pass，也不会自动继续，必须等待人工验收。

## Fail Stop Behavior

fail / blocked / unsafe / parse failure 场景停止约束验证：

| Sample | ACCEPTANCE_STATUS | STOP_REASON | NEXT_ACTION |
|--------|-------------------|-------------|-------------|
| fail | blocked | child_check_result_failed | review_failure_before_continue |
| missing-check-result | failed_to_parse | missing_check_result | review_parse_failure |
| unsafe-unknown | unsafe_to_continue | dirty_unknown | manual_review_required |
| dirty-unexpected | blocked | dirty_unexpected | review_unexpected_changes |
| missing-report-paths | blocked | missing_report_paths | check_report_generation |
| task-status-failed | blocked | child_task_status_failed | review_failure_before_continue |

所有 fail 场景确认：

- AUTO_CONTINUE_TO_NEXT_TASK=False（不自动进入下一任务）
- AUTO_GIT_BACKUP=False（不自动 Git 备份）
- HUMAN_REVIEW_REQUIRED=True（必须人工处理）
- NEXT_ACTION 引导到具体审查步骤（不自动返工、不自动提交）

**结论**：fail 后不能自动返工、不能自动进入下一任务、不能自动提交，必须等待人工处理。

## Unknown Field Rule

通过直接调用 `evaluate_first_real_run_acceptance()` 验证 unknown 字段行为：

### 测试 1：claude_code_called=unknown + business_code_changed=unknown

| 字段 | 值 | 说明 |
|------|------|------|
| acceptance_status | blocked | unknown 导致 blocked |
| human_review_required | True | unknown 必须人工审查 |
| auto_continue_to_next_task | False | unknown 阻止自动继续 |

### 测试 2：business_code_changed=unknown（单独）

| 字段 | 值 | 说明 |
|------|------|------|
| acceptance_status | blocked | unknown 导致 blocked |
| human_review_required | True | unknown 必须人工审查 |
| auto_continue_to_next_task | False | unknown 阻止自动继续 |

### 断言结果

- unknown 值不会得到 ready_for_human_review：PASS
- unknown 值必须触发 human_review_required=True：PASS
- unknown 值必须阻止 auto_continue：PASS
- unknown 不允许被写成 no：PASS（unknown 导致 blocked，不是 ready_for_human_review）

## Safety Check

| 安全项 | 结果 |
|--------|------|
| 是否执行真实任务 | no |
| 是否调用 run-project-task-full | no |
| 是否调用 Claude Code | no |
| 是否修改业务代码 | no |
| 是否自动进入下一任务 | no（所有场景 auto_continue=false） |
| 是否自动 Git 备份 | no（所有场景 auto_git_backup=false） |
| 是否需要人工审查 | yes（所有场景 human_review=true） |
| 工作区是否保持 clean | yes（验证前后均 clean） |
| 是否修改代码文件 | no（只新增验证报告和更新 tasks.md） |

## Check Result

**pass**

8/8 CLI 样本验证通过
8/8 SAFETY OVERRIDE 验证通过
6/6 fail 停止约束验证通过
2/2 pass 停止约束验证通过
3/3 unknown 字段断言验证通过

## Next

T095：设计首次真实调用 run-project-task-full 执行开关
