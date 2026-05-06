# T092 First Real-Run Acceptance Model Check

## Goal

验证 `FirstRealRunAcceptanceResult` 数据结构和 `evaluate_first_real_run_acceptance()` 函数的验收状态判断逻辑。

## Commands

### CLI 样例验证

```bash
python runner.py first-real-run-acceptance-dry-run --sample pass
python runner.py first-real-run-acceptance-dry-run --sample pass-dirty-reports
python runner.py first-real-run-acceptance-dry-run --sample fail
python runner.py first-real-run-acceptance-dry-run --sample missing-check-result
python runner.py first-real-run-acceptance-dry-run --sample unsafe-unknown
```

### 函数级验证

使用 `evaluate_first_real_run_acceptance()` 函数直接调用，覆盖 10 个场景 + 27 个安全断言。

## Expected Result

### 验收状态判断规则

| 场景 | 条件 | 预期 ACCEPTANCE_STATUS | 预期 CHECK_RESULT |
|------|------|----------------------|-------------------|
| pass + clean + report_paths | 正常成功 | ready_for_human_review | pass |
| pass + dirty_reports_only | 成功，只有报告 | ready_for_human_review | pass |
| pass + dirty_business_code | 成功，有业务变更 | ready_for_human_review | pass |
| check_result=fail | 任务失败 | blocked | fail |
| task_status=failed | 任务状态失败 | blocked | fail |
| 缺少 CHECK_RESULT | 解析失败 | failed_to_parse | fail |
| report_paths 缺失 | 无报告 | blocked | fail |
| dirty_unexpected | 非预期变更 | blocked | fail |
| dirty_unknown | 无法分类 | unsafe_to_continue | fail |
| unknown 字段 + clean | 可识别 | ready_for_human_review | pass |

### 安全约束

所有场景必须满足：
- `auto_continue_to_next_task=false`
- `auto_git_backup=false`
- `human_review_required=true`

## Actual Result

### CLI 样例验证

#### 样例 pass

| 字段 | 值 | 结果 |
|------|------|------|
| ACCEPTANCE_STATUS | ready_for_human_review | PASS |
| CHECK_RESULT | pass | PASS |
| CHILD_CHECK_RESULT | pass | PASS |
| CHILD_TASK_STATUS | done | PASS |
| AUTO_CONTINUE_TO_NEXT_TASK | False | PASS |
| AUTO_GIT_BACKUP | False | PASS |
| HUMAN_REVIEW_REQUIRED | True | PASS |

#### 样例 pass-dirty-reports

| 字段 | 值 | 结果 |
|------|------|------|
| ACCEPTANCE_STATUS | ready_for_human_review | PASS |
| WORKSPACE_CHANGE_CLASSIFICATION | dirty_reports_only | PASS |
| CHECK_RESULT | pass | PASS |

#### 样例 fail

| 字段 | 值 | 结果 |
|------|------|------|
| ACCEPTANCE_STATUS | blocked | PASS |
| STOP_REASON | child_check_result_failed | PASS |
| CHECK_RESULT | fail | PASS |

#### 样例 missing-check-result

| 字段 | 值 | 结果 |
|------|------|------|
| ACCEPTANCE_STATUS | failed_to_parse | PASS |
| CHILD_CHECK_RESULT | missing | PASS |
| CHECK_RESULT | fail | PASS |

#### 样例 unsafe-unknown

| 字段 | 值 | 结果 |
|------|------|------|
| ACCEPTANCE_STATUS | unsafe_to_continue | PASS |
| STOP_REASON | dirty_unknown | PASS |
| CLAUDE_CODE_CALLED | unknown | PASS |
| BUSINESS_CODE_CHANGED | unknown | PASS |

### 函数级验证

**49/49 断言全部 PASS**

- 10 个场景级断言全部 PASS
- 27 个安全约束断言全部 PASS（9 个结果 × 3 个约束）
- 12 个关键字段断言全部 PASS

### 优先级验证

| 优先级 | 状态 | 说明 |
|--------|------|------|
| failed_to_parse > blocked | PASS | 缺少 CHECK_RESULT 时直接 failed_to_parse，不进入 blocked |
| blocked > unsafe_to_continue | PASS | check_result=fail 时直接 blocked，不进入 unsafe |
| blocked > ready_for_human_review | PASS | dirty_unexpected 时 blocked，不进入 ready |
| unsafe_to_continue > ready_for_human_review | PASS | dirty_unknown 时 unsafe，不进入 ready |
| ready_for_human_review 最低优先级 | PASS | 所有条件满足才进入 ready |

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
| unknown 字段是否写成 no | no（保持 unknown） |

## Check Result

**pass**

## Next

T093：实现 simulated first real-run acceptance parser
