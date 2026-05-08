# T126 First Human-Reviewed Controlled Apply Dry-Run Check

## Task

执行 first human-reviewed controlled apply dry-run。

## Scope

本轮只实现完整 human-reviewed controlled apply dry-run，不真实 apply patch，不执行 command，不真实执行任务。

## Command

```bash
python runner.py first-human-reviewed-controlled-apply-dry-run --sample <name>
```

## Safety Rules

| Check | Result |
|-------|--------|
| no real patch apply | yes |
| no command execution | yes |
| no run-project-task-full call | yes |
| no Claude Code call | yes |
| no business code modification | yes |
| no framework code modification | yes |
| no real task execution | yes |
| no auto-continue | yes |
| no auto Git backup | yes |
| no bypass permissions | yes |
| no Stage 8 continuation | yes |
| human review required | yes |

## Scenarios

### 1. pass

- Command: `python runner.py first-human-reviewed-controlled-apply-dry-run --sample pass`
- Expected: CHECK_RESULT=pass, CONTROLLED_APPLY_DRY_RUN_STATUS=ready_for_human_review
- Actual: CHECK_RESULT=pass, CONTROLLED_APPLY_DRY_RUN_STATUS=ready_for_human_review
- APPROVAL_CHECK_RESULT=pass, COMMAND_ALLOWLIST_CHECK_RESULT=pass
- PROPOSAL_PARSE_CHECK_RESULT=pass, SCOPE_VALIDATION_CHECK_RESULT=pass, PATCH_DRY_RUN_CHECK_RESULT=pass
- READY_FOR_CONTROLLED_APPLY_DRY_RUN=yes
- **PASS**

### 2. missing-approval

- Command: `python runner.py first-human-reviewed-controlled-apply-dry-run --sample missing-approval`
- Expected: CHECK_RESULT=fail, CONTROLLED_APPLY_DRY_RUN_STATUS=failed_approval
- Actual: CHECK_RESULT=fail, CONTROLLED_APPLY_DRY_RUN_STATUS=failed_approval
- APPROVAL_CHECK_RESULT=fail
- **PASS**

### 3. wrong-approval

- Command: `python runner.py first-human-reviewed-controlled-apply-dry-run --sample wrong-approval`
- Expected: CHECK_RESULT=fail, CONTROLLED_APPLY_DRY_RUN_STATUS=failed_approval
- Actual: CHECK_RESULT=fail, CONTROLLED_APPLY_DRY_RUN_STATUS=failed_approval
- APPROVAL_CHECK_RESULT=fail
- **PASS**

### 4. pipeline-fail

- Command: `python runner.py first-human-reviewed-controlled-apply-dry-run --sample pipeline-fail`
- Expected: CHECK_RESULT=fail, CONTROLLED_APPLY_DRY_RUN_STATUS=failed_pipeline
- Actual: CHECK_RESULT=fail, CONTROLLED_APPLY_DRY_RUN_STATUS=failed_pipeline
- PROPOSAL_PARSE_CHECK_RESULT=fail (scope violation in unsafe-scope sample)
- **PASS**

### 5. command-unsafe

- Command: `python runner.py first-human-reviewed-controlled-apply-dry-run --sample command-unsafe`
- Expected: CHECK_RESULT=fail, CONTROLLED_APPLY_DRY_RUN_STATUS=failed_command_allowlist
- Actual: CHECK_RESULT=fail, CONTROLLED_APPLY_DRY_RUN_STATUS=failed_command_allowlist
- COMMAND_ALLOWLIST_CHECK_RESULT=fail
- APPROVAL_CHECK_RESULT=pass (approval passes first)
- COMMANDS_REJECTED=1 (git add blocked)
- **PASS**

### 6. auto-continue-requested

- Command: `python runner.py first-human-reviewed-controlled-apply-dry-run --sample auto-continue-requested`
- Expected: CHECK_RESULT=fail
- Actual: CHECK_RESULT=fail, CONTROLLED_APPLY_DRY_RUN_STATUS=failed_pipeline
- Pipeline fails because auto-continue proposal violates safety constraints
- **PASS**

### 7. auto-git-backup-requested

- Command: `python runner.py first-human-reviewed-controlled-apply-dry-run --sample auto-git-backup-requested`
- Expected: CHECK_RESULT=fail
- Actual: CHECK_RESULT=fail, CONTROLLED_APPLY_DRY_RUN_STATUS=failed_pipeline
- Pipeline fails because auto-git-backup proposal violates safety constraints
- **PASS**

### 8. ready-for-real-apply-unexpected

- Command: `python runner.py first-human-reviewed-controlled-apply-dry-run --sample ready-for-real-apply-unexpected`
- Expected: CHECK_RESULT=fail
- Actual: CHECK_RESULT=fail, CONTROLLED_APPLY_DRY_RUN_STATUS=failed_pipeline
- Pipeline fails because ready_for_real_apply proposal violates safety constraints
- **PASS**

### 9. dirty-worktree

- Command: `python runner.py first-human-reviewed-controlled-apply-dry-run --sample dirty-worktree`
- Expected: CHECK_RESULT=fail, CONTROLLED_APPLY_DRY_RUN_STATUS=failed_approval
- Actual: CHECK_RESULT=fail, CONTROLLED_APPLY_DRY_RUN_STATUS=failed_approval
- Approval model rejects dirty worktree
- **PASS**

## Summary

| Sample | CHECK_RESULT | CONTROLLED_APPLY_DRY_RUN_STATUS |
|--------|-------------|-------------------------------|
| pass | pass | ready_for_human_review |
| missing-approval | fail | failed_approval |
| wrong-approval | fail | failed_approval |
| pipeline-fail | fail | failed_pipeline |
| command-unsafe | fail | failed_command_allowlist |
| auto-continue-requested | fail | failed_pipeline |
| auto-git-backup-requested | fail | failed_pipeline |
| ready-for-real-apply-unexpected | fail | failed_pipeline |
| dirty-worktree | fail | failed_approval |

9/9 PASS.

## Safety Verification

| Check | All 9 Scenarios |
|-------|-----------------|
| REAL_PATCH_APPLIED=no | yes (9/9) |
| COMMAND_EXECUTION_PERFORMED=no | yes (9/9) |
| REAL_TASK_EXECUTION=no | yes (9/9) |
| RUN_PROJECT_TASK_FULL_CALLED=no | yes (9/9) |
| CLAUDE_CODE_CALLED=no | yes (9/9) |
| BUSINESS_CODE_CHANGED=no | yes (9/9) |
| READY_FOR_REAL_APPLY=no | yes (9/9) |
| READY_FOR_STAGE_8=no | yes (9/9) |
| HUMAN_REVIEW_REQUIRED=yes | yes (9/9) |

## Decision

```text
FIRST_HUMAN_REVIEWED_CONTROLLED_APPLY_DRY_RUN_CHECK=pass
READY_FOR_T127=yes
READY_FOR_REAL_APPLY=no
READY_FOR_STAGE_8=no
```

## Next

T127：验证 first human-reviewed controlled apply dry-run pass/fail 场景
