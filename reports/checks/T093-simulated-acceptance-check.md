# T093 Simulated First Real-Run Acceptance Check

## Goal

验证 `run_simulated_first_real_run_acceptance_parser()` 函数和 `simulated-first-real-run-acceptance` CLI 的模拟验收流程。

## Commands

### CLI 样例验证

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

### 函数级验证

使用 `run_simulated_first_real_run_acceptance_parser()` 函数直接调用，覆盖 8 个场景 + 安全约束。

## Expected Result

### 验收状态判断规则

| 场景 | 条件 | 预期 ACCEPTANCE_STATUS | 预期 CHECK_RESULT |
|------|------|----------------------|-------------------|
| pass + clean + report_paths | 正常成功 | ready_for_human_review | pass |
| pass + dirty_reports_only | 成功，只有报告 | ready_for_human_review | pass |
| check_result=fail | 任务失败 | blocked | fail |
| 缺少 CHECK_RESULT | 解析失败 | failed_to_parse | fail |
| dirty_unknown | workspace 无法分类 | unsafe_to_continue | fail |
| dirty_unexpected | 非预期变更 | blocked | fail |
| report_paths 缺失 | 无报告 | blocked | fail |
| task_status=failed | 任务状态失败 | blocked | fail |

### 安全约束

所有场景必须满足：
- `auto_continue_to_next_task=false`
- `auto_git_backup=false`
- `human_review_required=true`

### SAFETY OVERRIDE

CLI 输出必须包含安全覆盖字段，无论 sample 数据如何：
- `REAL_TASK_EXECUTION=no`
- `RUN_PROJECT_TASK_FULL_CALLED=no`
- `CLAUDE_CODE_CALLED=no`
- `BUSINESS_CODE_CHANGED=no`

## Actual Result

### CLI 样例验证

#### 样例 pass

| 字段 | 值 | 结果 |
|------|------|------|
| ACCEPTANCE_STATUS | ready_for_human_review | PASS |
| CHECK_RESULT | pass | PASS |
| CHILD_CHECK_RESULT | pass | PASS |
| CHILD_TASK_STATUS | done | PASS |
| WORKSPACE_CHANGE_CLASSIFICATION | clean | PASS |
| REPORT_PATHS | 2 paths | PASS |
| AUTO_CONTINUE_TO_NEXT_TASK | False | PASS |
| AUTO_GIT_BACKUP | False | PASS |
| HUMAN_REVIEW_REQUIRED | True | PASS |
| SAFETY OVERRIDE | REAL_TASK_EXECUTION=no | PASS |

#### 样例 pass-dirty-reports

| 字段 | 值 | 结果 |
|------|------|------|
| ACCEPTANCE_STATUS | ready_for_human_review | PASS |
| WORKSPACE_CHANGE_CLASSIFICATION | dirty_reports_only | PASS |
| CHECK_RESULT | pass | PASS |
| SAFETY OVERRIDE | BUSINESS_CODE_CHANGED=no | PASS |

#### 样例 fail

| 字段 | 值 | 结果 |
|------|------|------|
| ACCEPTANCE_STATUS | blocked | PASS |
| STOP_REASON | child_check_result_failed | PASS |
| CHECK_RESULT | fail | PASS |
| CHILD_CHECK_RESULT | fail | PASS |

#### 样例 missing-check-result

| 字段 | 值 | 结果 |
|------|------|------|
| ACCEPTANCE_STATUS | failed_to_parse | PASS |
| CHILD_CHECK_RESULT | missing | PASS |
| CHECK_RESULT | fail | PASS |
| STOP_REASON | missing_check_result | PASS |

#### 样例 unsafe-unknown

| 字段 | 值 | 结果 |
|------|------|------|
| ACCEPTANCE_STATUS | unsafe_to_continue | PASS |
| STOP_REASON | dirty_unknown | PASS |
| CHECK_RESULT | fail | PASS |
| SAFETY OVERRIDE | CLAUDE_CODE_CALLED=no | PASS |

#### 样例 dirty-unexpected

| 字段 | 值 | 结果 |
|------|------|------|
| ACCEPTANCE_STATUS | blocked | PASS |
| STOP_REASON | dirty_unexpected | PASS |
| NEXT_ACTION | review_unexpected_changes | PASS |
| CHECK_RESULT | fail | PASS |

#### 样例 missing-report-paths

| 字段 | 值 | 结果 |
|------|------|------|
| ACCEPTANCE_STATUS | blocked | PASS |
| STOP_REASON | missing_report_paths | PASS |
| NEXT_ACTION | check_report_generation | PASS |
| REPORT_PATHS | NONE | PASS |
| CHECK_RESULT | fail | PASS |

#### 样例 task-status-failed

| 字段 | 值 | 结果 |
|------|------|------|
| ACCEPTANCE_STATUS | blocked | PASS |
| STOP_REASON | child_task_status_failed | PASS |
| CHILD_TASK_STATUS | failed | PASS |
| CHECK_RESULT | fail | PASS |

### 函数级验证

**53/53 断言全部 PASS**

- 8 个场景级断言全部 PASS
- 24 个安全约束断言全部 PASS（8 个结果 × 3 个约束）
- 8 个 execution_mode 断言全部 PASS
- 7 个 pass 场景关键字段断言全部 PASS
- 6 个特定场景关键字段断言全部 PASS

### 错误处理验证

| 场景 | 结果 |
|------|------|
| unknown sample name | ValueError with available list PASS |

### SAFETY OVERRIDE 验证

所有 8 个 CLI 样本均输出安全覆盖字段：
- REAL_TASK_EXECUTION=no PASS
- RUN_PROJECT_TASK_FULL_CALLED=no PASS
- CLAUDE_CODE_CALLED=no PASS
- BUSINESS_CODE_CHANGED=no PASS

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
| CLI 安全覆盖是否完整 | yes（所有样本均输出 4 个 no） |

## Check Result

**pass**

## Next

T094：验证 first real-run acceptance pass/fail 场景
