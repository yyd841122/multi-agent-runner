# T125 Command Allowlist Validation Dry-Run Check

## Task

实现 command allowlist validation dry-run。

## Scope

本轮只实现 command allowlist validation dry-run，不执行 command，不真实执行任务。

## Command

```bash
python runner.py command-allowlist-dry-run --sample <name>
```

## Safety Rules

| Check | Result |
|-------|--------|
| no command execution | yes |
| no real patch apply | yes |
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

### 1. pass-status

- Command: `python runner.py command-allowlist-dry-run --sample pass-status`
- Expected: CHECK_RESULT=pass, COMMANDS_ALLOWED=3
- Actual: CHECK_RESULT=pass, COMMANDS_ALLOWED=3, COMMANDS_REJECTED=0
- ALLOWLIST_CATEGORIES=status
- FORBIDDEN_PATTERNS_DETECTED=NONE
- READY_FOR_CONTROLLED_APPLY_DRY_RUN=yes
- **PASS**

### 2. pass-validation

- Command: `python runner.py command-allowlist-dry-run --sample pass-validation`
- Expected: CHECK_RESULT=pass, COMMANDS_ALLOWED=2
- Actual: CHECK_RESULT=pass, COMMANDS_ALLOWED=2, COMMANDS_REJECTED=0
- ALLOWLIST_CATEGORIES=validation
- FORBIDDEN_PATTERNS_DETECTED=NONE
- READY_FOR_CONTROLLED_APPLY_DRY_RUN=yes
- **PASS**

### 3. pass-test

- Command: `python runner.py command-allowlist-dry-run --sample pass-test`
- Expected: CHECK_RESULT=pass, COMMANDS_ALLOWED=2
- Actual: CHECK_RESULT=pass, COMMANDS_ALLOWED=2, COMMANDS_REJECTED=0
- ALLOWLIST_CATEGORIES=test
- FORBIDDEN_PATTERNS_DETECTED=NONE
- READY_FOR_CONTROLLED_APPLY_DRY_RUN=yes
- **PASS**

### 4. empty-command

- Command: `python runner.py command-allowlist-dry-run --sample empty-command`
- Expected: CHECK_RESULT=fail, COMMANDS_REJECTED=1
- Actual: CHECK_RESULT=fail, COMMANDS_REJECTED=1
- FORBIDDEN_PATTERNS_DETECTED=empty_command
- **PASS**

### 5. git-add

- Command: `python runner.py command-allowlist-dry-run --sample git-add`
- Expected: CHECK_RESULT=fail, COMMANDS_REJECTED=1
- Actual: CHECK_RESULT=fail, COMMANDS_REJECTED=1
- FORBIDDEN_PATTERNS_DETECTED=git add
- **PASS**

### 6. git-commit

- Command: `python runner.py command-allowlist-dry-run --sample git-commit`
- Expected: CHECK_RESULT=fail, COMMANDS_REJECTED=1
- Actual: CHECK_RESULT=fail, COMMANDS_REJECTED=1
- FORBIDDEN_PATTERNS_DETECTED=git commit
- **PASS**

### 7. git-push

- Command: `python runner.py command-allowlist-dry-run --sample git-push`
- Expected: CHECK_RESULT=fail, COMMANDS_REJECTED=1
- Actual: CHECK_RESULT=fail, COMMANDS_REJECTED=1
- FORBIDDEN_PATTERNS_DETECTED=git push
- **PASS**

### 8. git-reset

- Command: `python runner.py command-allowlist-dry-run --sample git-reset`
- Expected: CHECK_RESULT=fail, COMMANDS_REJECTED=1
- Actual: CHECK_RESULT=fail, COMMANDS_REJECTED=1
- FORBIDDEN_PATTERNS_DETECTED=git reset
- **PASS**

### 9. rm-command

- Command: `python runner.py command-allowlist-dry-run --sample rm-command`
- Expected: CHECK_RESULT=fail, COMMANDS_REJECTED=1
- Actual: CHECK_RESULT=fail, COMMANDS_REJECTED=1
- FORBIDDEN_PATTERNS_DETECTED=rm
- **PASS**

### 10. pipe-command

- Command: `python runner.py command-allowlist-dry-run --sample pipe-command`
- Expected: CHECK_RESULT=fail, COMMANDS_REJECTED=1
- Actual: CHECK_RESULT=fail, COMMANDS_REJECTED=1
- FORBIDDEN_PATTERNS_DETECTED=|
- **PASS**

### 11. redirect-command

- Command: `python runner.py command-allowlist-dry-run --sample redirect-command`
- Expected: CHECK_RESULT=fail, COMMANDS_REJECTED=1
- Actual: CHECK_RESULT=fail, COMMANDS_REJECTED=1
- FORBIDDEN_PATTERNS_DETECTED=>
- **PASS**

### 12. run-project-task-full

- Command: `python runner.py command-allowlist-dry-run --sample run-project-task-full`
- Expected: CHECK_RESULT=fail, COMMANDS_REJECTED=1
- Actual: CHECK_RESULT=fail, COMMANDS_REJECTED=1
- FORBIDDEN_PATTERNS_DETECTED=run-project-task-full
- **PASS**

### 13. claude-acceptedits

- Command: `python runner.py command-allowlist-dry-run --sample claude-acceptedits`
- Expected: CHECK_RESULT=fail, COMMANDS_REJECTED=1
- Actual: CHECK_RESULT=fail, COMMANDS_REJECTED=1
- FORBIDDEN_PATTERNS_DETECTED=claude --permission-mode acceptEdits
- **PASS**

### 14. unknown-command

- Command: `python runner.py command-allowlist-dry-run --sample unknown-command`
- Expected: CHECK_RESULT=fail, COMMANDS_REJECTED=1
- Actual: CHECK_RESULT=fail, COMMANDS_REJECTED=1
- FORBIDDEN_PATTERNS_DETECTED=unknown_command
- **PASS**

### 15. mixed-safe-unsafe

- Command: `python runner.py command-allowlist-dry-run --sample mixed-safe-unsafe`
- Expected: CHECK_RESULT=fail, COMMANDS_ALLOWED=2, COMMANDS_REJECTED=2
- Actual: CHECK_RESULT=fail, COMMANDS_ALLOWED=2, COMMANDS_REJECTED=2
- ALLOWLIST_CATEGORIES=status, test
- FORBIDDEN_PATTERNS_DETECTED=git add, rm
- **PASS**

## Summary

| Sample | CHECK_RESULT | COMMANDS_TOTAL | COMMANDS_ALLOWED | COMMANDS_REJECTED | FORBIDDEN_PATTERNS_DETECTED |
|--------|-------------|----------------|-----------------|-------------------|---------------------------|
| pass-status | pass | 3 | 3 | 0 | NONE |
| pass-validation | pass | 2 | 2 | 0 | NONE |
| pass-test | pass | 2 | 2 | 0 | NONE |
| empty-command | fail | 1 | 0 | 1 | empty_command |
| git-add | fail | 1 | 0 | 1 | git add |
| git-commit | fail | 1 | 0 | 1 | git commit |
| git-push | fail | 1 | 0 | 1 | git push |
| git-reset | fail | 1 | 0 | 1 | git reset |
| rm-command | fail | 1 | 0 | 1 | rm |
| pipe-command | fail | 1 | 0 | 1 | \| |
| redirect-command | fail | 1 | 0 | 1 | > |
| run-project-task-full | fail | 1 | 0 | 1 | run-project-task-full |
| claude-acceptedits | fail | 1 | 0 | 1 | claude --permission-mode acceptEdits |
| unknown-command | fail | 1 | 0 | 1 | unknown_command |
| mixed-safe-unsafe | fail | 4 | 2 | 2 | git add, rm |

15/15 PASS.

## Safety Verification

| Check | All 15 Scenarios |
|-------|-----------------|
| COMMAND_EXECUTION_BLOCKED=yes | yes (15/15) |
| READY_FOR_COMMAND_EXECUTION=no | yes (15/15) |
| REAL_PATCH_APPLIED=no | yes (15/15) |
| REAL_TASK_EXECUTION=no | yes (15/15) |
| RUN_PROJECT_TASK_FULL_CALLED=no | yes (15/15) |
| CLAUDE_CODE_CALLED=no | yes (15/15) |
| BUSINESS_CODE_CHANGED=no | yes (15/15) |
| HUMAN_REVIEW_REQUIRED=yes | yes (15/15) |

## Decision

```text
COMMAND_ALLOWLIST_VALIDATION_DRY_RUN_CHECK=pass
READY_FOR_T126=yes
READY_FOR_REAL_APPLY=no
READY_FOR_STAGE_8=no
```

## Next

T126：执行 first human-reviewed controlled apply dry-run
