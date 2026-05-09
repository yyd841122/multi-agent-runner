# T132 First Real Patch Apply Guarded Dry-Run Check

## Task

实现 first real patch apply guarded dry-run。

## Scope

本轮只实现 guarded dry-run，不真实 apply patch，不执行 command，不真实执行任务。

## Scenarios Verified

| # | Sample | Post-Apply Validation | Workspace Classification | Check Result |
|---|--------|-----------------------|-------------------------|--------------|
| 1 | pass | pass | expected_dirty | pass |
| 2 | missing-approval-record | fail | expected_dirty | fail |
| 3 | missing-pre-audit | fail | expected_dirty | fail |
| 4 | missing-post-audit | fail | expected_dirty | fail |
| 5 | unexpected-file | fail | unexpected_dirty | fail |
| 6 | forbidden-file | fail | unexpected_dirty | fail |
| 7 | missing-diff-stat | fail | unexpected_dirty | fail |
| 8 | clean-unexpected | fail | clean_unexpected | fail |
| 9 | missing-validation-results | fail | expected_dirty | fail |
| 10 | commit-requested | fail | expected_dirty | fail |
| 11 | push-requested | fail | expected_dirty | fail |
| 12 | stage-8-requested | fail | expected_dirty | fail |

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
REAL_PATCH_APPLIED=no
CHECK_RESULT=pass
```

### Fail-Closed Scenario Verification

All 11 fail scenarios verified:

| Field | Value |
|-------|-------|
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

## Generated Dry-Run Records

| # | File | Present |
|---|------|---------|
| 1 | reports/apply/T132-sample-guarded-apply-dry-run.md | yes |
| 2 | reports/apply/T132-sample-post-apply-validation.md | yes |

### Guarded Apply Dry-Run Record Content Check

| Section | Present |
|---------|---------|
| Metadata (dry_run_mode, task_id, generated_at) | yes |
| Approval & Audit Records (3 records, all exists) | yes |
| File Scope (expected, actual, unexpected) | yes |
| Diff Stat (files_changed, insertions, deletions) | yes |
| Post-Apply Validation (status, classification, human_review) | yes |
| Safety (6 fields, all safe values) | yes |
| Decision (ready_for_human_review=yes, ready_for_git_backup_dry_run=yes, check_result=pass) | yes |

### Post-Apply Validation Record Content Check

| Section | Present |
|---------|---------|
| Metadata (task_id, generated_at) | yes |
| Validation Checks (18 items, all pass) | yes |
| Workspace Classification (expected_dirty) | yes |
| Decision (status=pass, ready flags) | yes |

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
FIRST_REAL_PATCH_APPLY_GUARDED_DRY_RUN=implemented
GUARDED_APPLY_SCENARIOS_TOTAL=12
GUARDED_APPLY_SCENARIOS_PASS=12/12
PASS_SCENARIO_RESULT=pass
FAIL_CLOSED_SCENARIOS_PASS=11/11
READY_FOR_T133=yes
READY_FOR_REAL_APPLY=no
READY_FOR_STAGE_8=no
CHECK_RESULT=pass
```

## Next

T133：验证 first real patch apply guarded dry-run pass/fail 场景，或根据 docs/tasks.md 中下一任务继续。
