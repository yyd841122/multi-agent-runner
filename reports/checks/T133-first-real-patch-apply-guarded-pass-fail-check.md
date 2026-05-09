# T133 First Real Patch Apply Guarded Dry-Run Pass/Fail Check

## Task

验证 first real patch apply guarded dry-run pass/fail 场景。

## Scope

本轮只验证 T132 guarded dry-run pipeline，不真实 apply patch，不执行 command，不真实执行任务。

## Background

T129 设计了 real apply approval persistence and audit record。T130 实现了 approval record / pre-apply audit / post-apply audit dry-run 生成能力（7/7 scenarios validated）。T131 设计了 post-apply validation gate（18 checks, 3 workspace classifications, 21 rejection conditions）。T132 实现了 first real patch apply guarded dry-run（12/12 scenarios validated）。

本轮独立验证 T132 pipeline 的 pass/fail 场景稳定性。

## Scenarios Verified

| # | Sample | POST_APPLY_VALIDATION | DIRTY_WORKSPACE_CLASS | READY_FOR_GIT_BACKUP_DRY_RUN | READY_FOR_REAL_APPLY | READY_FOR_COMMIT | READY_FOR_PUSH | READY_FOR_STAGE_8 | CHECK_RESULT |
|---|--------|-----------------------|-----------------------|------------------------------|----------------------|------------------|----------------|-------------------|--------------|
| 1 | pass | pass | expected_dirty | yes | no | no | no | no | pass |
| 2 | missing-approval-record | fail | expected_dirty | no | no | no | no | no | fail |
| 3 | missing-pre-audit | fail | expected_dirty | no | no | no | no | no | fail |
| 4 | missing-post-audit | fail | expected_dirty | no | no | no | no | no | fail |
| 5 | unexpected-file | fail | unexpected_dirty | no | no | no | no | no | fail |
| 6 | forbidden-file | fail | unexpected_dirty | no | no | no | no | no | fail |
| 7 | missing-diff-stat | fail | unexpected_dirty | no | no | no | no | no | fail |
| 8 | clean-unexpected | fail | clean_unexpected | no | no | no | no | no | fail |
| 9 | missing-validation-results | fail | expected_dirty | no | no | no | no | no | fail |
| 10 | commit-requested | fail | expected_dirty | no | no | no | no | no | fail |
| 11 | push-requested | fail | expected_dirty | no | no | no | no | no | fail |
| 12 | stage-8-requested | fail | expected_dirty | no | no | no | no | no | fail |

### Pass Scenario Details

```text
APPROVAL_RECORD_CHECK_RESULT=pass
PRE_APPLY_AUDIT_CHECK_RESULT=pass
POST_APPLY_AUDIT_CHECK_RESULT=pass
POST_APPLY_VALIDATION_STATUS=pass
DIRTY_WORKSPACE_CLASSIFICATION=expected_dirty
READY_FOR_HUMAN_REVIEW=yes
READY_FOR_GIT_BACKUP_DRY_RUN=yes
READY_FOR_REAL_APPLY=no
READY_FOR_COMMIT=no
READY_FOR_PUSH=no
READY_FOR_STAGE_8=no
CHECK_RESULT=pass
```

### Fail-Closed Scenario Verification

All 11 fail scenarios verified:

| Field | Value (all 11 scenarios) |
|-------|--------------------------|
| REAL_PATCH_APPLIED | no |
| COMMAND_EXECUTION_PERFORMED | no |
| REAL_TASK_EXECUTION | no |
| RUN_PROJECT_TASK_FULL_CALLED | no |
| CLAUDE_CODE_CALLED | no |
| BUSINESS_CODE_CHANGED | no |
| READY_FOR_REAL_APPLY | no |
| READY_FOR_COMMAND_EXECUTION | no |
| READY_FOR_COMMIT | no |
| READY_FOR_PUSH | no |
| READY_FOR_STAGE_8 | no |
| HUMAN_REVIEW_REQUIRED | yes |
| CHECK_RESULT | fail |

### Workspace Classification Verification

| Classification | Scenarios |
|---------------|-----------|
| expected_dirty | pass, missing-approval-record, missing-pre-audit, missing-post-audit, missing-validation-results, commit-requested, push-requested, stage-8-requested |
| unexpected_dirty | unexpected-file, forbidden-file, missing-diff-stat |
| clean_unexpected | clean-unexpected |

## Expected Results

- pass scenario: CHECK_RESULT=pass, DIRTY_WORKSPACE_CLASSIFICATION=expected_dirty, READY_FOR_GIT_BACKUP_DRY_RUN=yes
- Other 11 scenarios: CHECK_RESULT=fail, fail closed
- All scenarios: READY_FOR_REAL_APPLY=no
- All scenarios: READY_FOR_COMMIT=no
- All scenarios: READY_FOR_PUSH=no
- All scenarios: READY_FOR_STAGE_8=no
- All scenarios: REAL_PATCH_APPLIED=no
- All scenarios: COMMAND_EXECUTION_PERFORMED=no
- All scenarios: CLAUDE_CODE_CALLED=no
- All scenarios: RUN_PROJECT_TASK_FULL_CALLED=no
- All scenarios: BUSINESS_CODE_CHANGED=no

All expected results confirmed.

## Side Effects

```text
git status --short:
 M docs/tasks.md
 M reports/apply/T132-sample-guarded-apply-dry-run.md
 M reports/apply/T132-sample-post-apply-validation.md
```

- docs/tasks.md: T133 pending → in_progress（预期修改）
- reports/apply/T132-*.md: pass 场景重新生成 sample 文件，仅 generated_at 时间戳变化（正常行为）
- projects/down-100-floors-game/**: 无变化
- 无业务代码变更
- 无真实 patch apply
- 无 command execution
- 无 commit / push
- 无 Stage 8 continuation

## Safety Review

| # | Check | Result |
|---|-------|--------|
| 1 | no real patch applied | guaranteed |
| 2 | no command executed | guaranteed |
| 3 | no Claude Code called | guaranteed |
| 4 | no run-project-task-full called | guaranteed |
| 5 | no business code changed | guaranteed |
| 6 | no auto-continue | guaranteed |
| 7 | no auto Git backup | guaranteed |
| 8 | no Stage 8 continuation | guaranteed |
| 9 | no commit | guaranteed |
| 10 | no push | guaranteed |
| 11 | human review required | guaranteed |

## Decision

```text
FIRST_REAL_PATCH_APPLY_GUARDED_PASS_FAIL_VALIDATION=pass
GUARDED_APPLY_SCENARIOS_TOTAL=12
GUARDED_APPLY_SCENARIOS_PASS=12/12
PASS_SCENARIO_RESULT=pass
FAIL_CLOSED_SCENARIOS_PASS=11/11
READY_FOR_T134=yes
READY_FOR_REAL_APPLY=no
READY_FOR_COMMIT=no
READY_FOR_PUSH=no
READY_FOR_STAGE_8=no
CHECK_RESULT=pass
```

## Next

T134：归档 Stage 7 guarded real patch apply dry-run 成果。
