# T130 Real Apply Approval Record Dry-Run Check

## Task

实现 real apply approval record dry-run。

## Scope

本轮只实现 approval/audit record dry-run，不真实 apply patch，不执行 command，不真实执行任务。

## Scenarios Verified

| # | Sample | Approval Record Generated | Check Result |
|---|--------|--------------------------|--------------|
| 1 | pass | yes | pass |
| 2 | missing-token | no | fail |
| 3 | invalid-token | no | fail |
| 4 | missing-evidence | no | fail |
| 5 | real-apply-requested | no | fail |
| 6 | command-execution-requested | no | fail |
| 7 | stage-8-requested | no | fail |

### Pass Scenario Details

- APPROVAL_RECORD_GENERATED=yes
- PRE_APPLY_AUDIT_GENERATED=yes
- POST_APPLY_AUDIT_GENERATED=yes
- READY_FOR_APPROVAL_RECORD_DRY_RUN=yes
- EVIDENCE_COMPLETE=yes

### Fail-Closed Scenario Verification

All 6 fail scenarios verified:

| Field | Value |
|-------|-------|
| APPROVAL_RECORD_GENERATED | no |
| READY_FOR_REAL_APPLY | no |
| READY_FOR_COMMAND_EXECUTION | no |
| READY_FOR_STAGE_8 | no |
| REAL_PATCH_APPLIED | no |
| COMMAND_EXECUTION_PERFORMED | no |
| REAL_TASK_EXECUTION | no |
| RUN_PROJECT_TASK_FULL_CALLED | no |
| CLAUDE_CODE_CALLED | no |
| BUSINESS_CODE_CHANGED | no |
| CHECK_RESULT | fail |

## Generated Dry-Run Records

| # | File | Present |
|---|------|---------|
| 1 | reports/apply/T130-sample-approval-record.md | yes |
| 2 | reports/apply/T130-sample-pre-apply-audit.md | yes |
| 3 | reports/apply/T130-sample-post-apply-audit.md | yes |

### Approval Record Content Check

| Section | Present |
|---------|---------|
| Metadata (version, id, task_id, task_title, generated_at) | yes |
| Approval (mode, token, approved_by, approved_at) | yes |
| Scope (allowed_files, target_files, patch_files, forbidden_files) | yes |
| Evidence (8 checks) | yes |
| Safety (6 fields, all safe values) | yes |
| Fingerprint (proposal_hash, patch_hash, target_files_hash) | yes |
| Decision (ready_for_real_apply=no, approval_valid=yes) | yes |

### Pre-Apply Audit Record Content Check

| Section | Present |
|---------|---------|
| Metadata (version, id, task_id, linked_approval_id, phase=pre_apply) | yes |
| Git State (head_before, worktree_status_before) | yes |
| Changes (to be determined in post_apply) | yes |
| Validation (empty) | yes |
| Safety (5 fields, all no) | yes |
| Decision (requires_human_review=yes, audit_phase_complete=no) | yes |

### Post-Apply Audit Record Content Check

| Section | Present |
|---------|---------|
| Metadata (version, id, task_id, linked_approval_id, phase=post_apply) | yes |
| Git State (head_before, head_after, status_before, status_after) | yes |
| Changes (expected_files=[], actual_files=[], unexpected_files=[]) | yes |
| Validation (empty) | yes |
| Safety (5 fields, all no) | yes |
| Decision (requires_human_review=yes, audit_phase_complete=yes) | yes |

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
| 9 | human review required | guaranteed |
| 10 | no commit | guaranteed |
| 11 | no push | guaranteed |

## Decision

```text
REAL_APPLY_APPROVAL_RECORD_DRY_RUN=implemented
APPROVAL_RECORD_SCENARIOS_TOTAL=7
APPROVAL_RECORD_SCENARIOS_PASS=7/7
PASS_SCENARIO_RESULT=pass
FAIL_CLOSED_SCENARIOS_PASS=6/6
READY_FOR_T131=yes
READY_FOR_REAL_APPLY=no
READY_FOR_STAGE_8=no
CHECK_RESULT=pass
```

## Next

T131：设计 post-apply validation gate
