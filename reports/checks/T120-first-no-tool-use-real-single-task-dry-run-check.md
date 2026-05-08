# T120 First No-Tool-Use Real Single-Task Dry-Run Check

## Command

```bash
python runner.py first-no-tool-use-single-task-dry-run --sample <name>
```

## Safety Rules

| Check | Result |
|-------|--------|
| no real patch applied | yes |
| no command execution | yes |
| no run-project-task-full call | yes |
| no Claude Code call | yes |
| no business code modification | yes |
| no framework code modification | yes |
| no real task execution | yes |
| no auto-continue | yes |
| no auto Git backup | yes |
| no bypass permissions | yes |
| human review required | yes |

## Scenarios

### 1. pass

- Command: `python runner.py first-no-tool-use-single-task-dry-run --sample pass`
- Expected: PIPELINE_STATUS=ready_for_human_review, CHECK_RESULT=pass
- Actual: PIPELINE_STATUS=ready_for_human_review, CHECK_RESULT=pass
- PARSE_STATUS=parsed, VALIDATION_STATUS=validated, PATCH_DRY_RUN_STATUS=ready_for_future_apply
- REAL_PATCH_APPLIED=no, COMMAND_EXECUTION_PERFORMED=no, REAL_TASK_EXECUTION=no
- READY_FOR_HUMAN_REVIEW=yes, READY_FOR_REAL_EXECUTION=no
- **PASS**

### 2. parse-fail

- Command: `python runner.py first-no-tool-use-single-task-dry-run --sample parse-fail`
- Expected: PIPELINE_STATUS=failed_parse, CHECK_RESULT=fail
- Actual: PIPELINE_STATUS=failed_parse, CHECK_RESULT=fail
- PARSE_STATUS=failed_to_parse, VALIDATION_STATUS=failed_parse, PATCH_DRY_RUN_STATUS=failed_parse
- VIOLATIONS=Parse failed: YAML parse error
- **PASS**

### 3. validation-fail

- Command: `python runner.py first-no-tool-use-single-task-dry-run --sample validation-fail`
- Expected: PIPELINE_STATUS=failed_validation, CHECK_RESULT=fail
- Actual: PIPELINE_STATUS=failed_validation, CHECK_RESULT=fail
- PARSE_STATUS=parsed, VALIDATION_STATUS=failed_safety, PATCH_DRY_RUN_STATUS=failed_validation
- VIOLATIONS=auto_continue_to_next_task must be 'no'
- **PASS**

### 4. patch-dry-run-fail

- Command: `python runner.py first-no-tool-use-single-task-dry-run --sample patch-dry-run-fail`
- Expected: PIPELINE_STATUS=failed_patch_dry_run, CHECK_RESULT=fail
- Actual: PIPELINE_STATUS=failed_patch_dry_run, CHECK_RESULT=fail
- PARSE_STATUS=parsed, VALIDATION_STATUS=validated, PATCH_DRY_RUN_STATUS=unsafe_patch
- VIOLATIONS=Patch 'docs/test.md': empty patch content
- **PASS**

### 5. no-patch

- Command: `python runner.py first-no-tool-use-single-task-dry-run --sample no-patch`
- Expected: PIPELINE_STATUS=failed_patch_dry_run, CHECK_RESULT=fail
- Actual: PIPELINE_STATUS=failed_patch_dry_run, CHECK_RESULT=fail
- PARSE_STATUS=parsed, VALIDATION_STATUS=validated, PATCH_DRY_RUN_STATUS=no_patch
- VIOLATIONS=Proposal type 'patch_proposal' requires patches but none found
- **PASS**

### 6. unsafe-command

- Command: `python runner.py first-no-tool-use-single-task-dry-run --sample unsafe-command`
- Expected: PIPELINE_STATUS=failed_validation, CHECK_RESULT=fail
- Actual: PIPELINE_STATUS=failed_validation, CHECK_RESULT=fail
- PARSE_STATUS=parsed, VALIDATION_STATUS=failed_scope, PATCH_DRY_RUN_STATUS=failed_validation
- VIOLATIONS=Target file not in allowed scope: runner.py; Target file in forbidden scope: runner.py
- Fails at T118 validation level (forbidden file target)
- **PASS**

### 7. auto-continue-requested

- Command: `python runner.py first-no-tool-use-single-task-dry-run --sample auto-continue-requested`
- Expected: PIPELINE_STATUS=failed_validation, CHECK_RESULT=fail
- Actual: PIPELINE_STATUS=failed_validation, CHECK_RESULT=fail
- PARSE_STATUS=parsed, VALIDATION_STATUS=failed_safety, PATCH_DRY_RUN_STATUS=failed_validation
- VIOLATIONS=auto_continue_to_next_task must be 'no'
- Fails at T118 validation level (auto_continue safety violation)
- **PASS**

### 8. auto-git-backup-requested

- Command: `python runner.py first-no-tool-use-single-task-dry-run --sample auto-git-backup-requested`
- Expected: PIPELINE_STATUS=failed_validation, CHECK_RESULT=fail
- Actual: PIPELINE_STATUS=failed_validation, CHECK_RESULT=fail
- PARSE_STATUS=parsed, VALIDATION_STATUS=failed_safety, PATCH_DRY_RUN_STATUS=failed_validation
- VIOLATIONS=auto_git_backup must be 'no'
- Fails at T118 validation level (auto_git_backup safety violation)
- **PASS**

## Summary

| Scenario | PARSE_STATUS | VALIDATION_STATUS | PATCH_DRY_RUN_STATUS | PIPELINE_STATUS | CHECK_RESULT |
|----------|-------------|-------------------|----------------------|-----------------|-------------|
| pass | parsed | validated | ready_for_future_apply | ready_for_human_review | pass |
| parse-fail | failed_to_parse | failed_parse | failed_parse | failed_parse | fail |
| validation-fail | parsed | failed_safety | failed_validation | failed_validation | fail |
| patch-dry-run-fail | parsed | validated | unsafe_patch | failed_patch_dry_run | fail |
| no-patch | parsed | validated | no_patch | failed_patch_dry_run | fail |
| unsafe-command | parsed | failed_scope | failed_validation | failed_validation | fail |
| auto-continue-requested | parsed | failed_safety | failed_validation | failed_validation | fail |
| auto-git-backup-requested | parsed | failed_safety | failed_validation | failed_validation | fail |

8/8 PASS.
