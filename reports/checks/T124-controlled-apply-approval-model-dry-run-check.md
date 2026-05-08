# T124 Controlled Apply Approval Model Dry-Run Check

## Task

实现 controlled apply approval model dry-run。

## Scope

本轮只实现 approval model dry-run，不真实 apply patch，不执行 command，不真实执行任务。

## Command

```bash
python runner.py controlled-apply-approval-dry-run --sample <name>
```

## Safety Rules

| Check | Result |
|-------|--------|
| no patch applied | yes |
| no command execution | yes |
| no Claude Code call | yes |
| no run-project-task-full call | yes |
| no business code modification | yes |
| no framework code modification | yes |
| no real task execution | yes |
| no auto-continue | yes |
| no auto Git backup | yes |
| no bypass permissions | yes |
| human review required | yes |

## Scenarios

### 1. pass

- Command: `python runner.py controlled-apply-approval-dry-run --sample pass`
- Expected: CHECK_RESULT=pass, READY_FOR_CONTROLLED_APPLY_DRY_RUN=yes
- Actual: CHECK_RESULT=pass, READY_FOR_CONTROLLED_APPLY_DRY_RUN=yes
- APPROVAL_TOKEN_PRESENT=yes, APPROVAL_TOKEN_VALID=yes
- WORKTREE_CLEAN_PASS=yes, PREVIOUS_PIPELINE_PASS=yes
- HUMAN_REVIEW_REQUIRED_PASS=yes, READY_FOR_REAL_APPLY_PASS=yes
- AUTO_CONTINUE_PASS=yes, AUTO_GIT_BACKUP_PASS=yes
- REJECTION_REASONS=NONE
- READY_FOR_REAL_APPLY_AFTER_APPROVAL=no
- **PASS**

### 2. missing-token

- Command: `python runner.py controlled-apply-approval-dry-run --sample missing-token`
- Expected: CHECK_RESULT=fail
- Actual: CHECK_RESULT=fail
- APPROVAL_TOKEN_PRESENT=no, APPROVAL_TOKEN_VALID=not_applicable
- REJECTION_REASONS=missing_approval_token
- **PASS**

### 3. wrong-token

- Command: `python runner.py controlled-apply-approval-dry-run --sample wrong-token`
- Expected: CHECK_RESULT=fail
- Actual: CHECK_RESULT=fail
- APPROVAL_TOKEN_PRESENT=yes, APPROVAL_TOKEN_VALID=no
- REJECTION_REASONS=invalid_approval_token
- **PASS**

### 4. dirty-worktree

- Command: `python runner.py controlled-apply-approval-dry-run --sample dirty-worktree`
- Expected: CHECK_RESULT=fail
- Actual: CHECK_RESULT=fail
- REJECTION_REASONS=dirty_worktree
- **PASS**

### 5. pipeline-not-ready

- Command: `python runner.py controlled-apply-approval-dry-run --sample pipeline-not-ready`
- Expected: CHECK_RESULT=fail
- Actual: CHECK_RESULT=fail
- REJECTION_REASONS=previous_pipeline_not_ready_for_human_review
- **PASS**

### 6. pipeline-failed

- Command: `python runner.py controlled-apply-approval-dry-run --sample pipeline-failed`
- Expected: CHECK_RESULT=fail
- Actual: CHECK_RESULT=fail
- REJECTION_REASONS=previous_pipeline_check_failed
- **PASS**

### 7. human-review-missing

- Command: `python runner.py controlled-apply-approval-dry-run --sample human-review-missing`
- Expected: CHECK_RESULT=fail
- Actual: CHECK_RESULT=fail
- REJECTION_REASONS=human_review_not_required
- **PASS**

### 8. ready-for-real-apply-unexpected

- Command: `python runner.py controlled-apply-approval-dry-run --sample ready-for-real-apply-unexpected`
- Expected: CHECK_RESULT=fail
- Actual: CHECK_RESULT=fail
- REJECTION_REASONS=ready_for_real_apply_unexpected
- **PASS**

### 9. auto-continue-requested

- Command: `python runner.py controlled-apply-approval-dry-run --sample auto-continue-requested`
- Expected: CHECK_RESULT=fail
- Actual: CHECK_RESULT=fail
- REJECTION_REASONS=auto_continue_requested
- **PASS**

### 10. auto-git-backup-requested

- Command: `python runner.py controlled-apply-approval-dry-run --sample auto-git-backup-requested`
- Expected: CHECK_RESULT=fail
- Actual: CHECK_RESULT=fail
- REJECTION_REASONS=auto_git_backup_requested
- **PASS**

## Summary

| Sample | CHECK_RESULT | READY_FOR_CONTROLLED_APPLY_DRY_RUN | READY_FOR_REAL_APPLY_AFTER_APPROVAL | REJECTION_REASONS |
|--------|-------------|-----------------------------------|------------------------------------|-------------------|
| pass | pass | yes | no | NONE |
| missing-token | fail | no | no | missing_approval_token |
| wrong-token | fail | no | no | invalid_approval_token |
| dirty-worktree | fail | no | no | dirty_worktree |
| pipeline-not-ready | fail | no | no | previous_pipeline_not_ready_for_human_review |
| pipeline-failed | fail | no | no | previous_pipeline_check_failed |
| human-review-missing | fail | no | no | human_review_not_required |
| ready-for-real-apply-unexpected | fail | no | no | ready_for_real_apply_unexpected |
| auto-continue-requested | fail | no | no | auto_continue_requested |
| auto-git-backup-requested | fail | no | no | auto_git_backup_requested |

10/10 PASS.

## Safety Verification

| Check | All 10 Scenarios |
|-------|-----------------|
| REAL_PATCH_APPLIED=no | yes (10/10) |
| COMMAND_EXECUTION_PERFORMED=no | yes (10/10) |
| REAL_TASK_EXECUTION=no | yes (10/10) |
| RUN_PROJECT_TASK_FULL_CALLED=no | yes (10/10) |
| CLAUDE_CODE_CALLED=no | yes (10/10) |
| BUSINESS_CODE_CHANGED=no | yes (10/10) |
| READY_FOR_REAL_APPLY_AFTER_APPROVAL=no | yes (10/10) |

## Decision

```text
CONTROLLED_APPLY_APPROVAL_MODEL_DRY_RUN_CHECK=pass
READY_FOR_T125=yes
READY_FOR_REAL_APPLY=no
READY_FOR_STAGE_8=no
```

## Next

T125：实现 command allowlist validation dry-run
