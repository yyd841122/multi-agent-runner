# T200 Evaluate Recovery Dry-run Report

Generated: 2026-05-15T03:37:01Z

## Status

```text
RATE_LIMIT_RECOVERY_RESULT=fail
COMMAND=evaluate-recovery
TASK_ID=T200
STAGE=Stage 12
RUN_ID=RUN-20260515-033701
RATE_LIMIT_DETECTED=yes
ERROR_CODE=
REQUEST_ID=
RESET_AT_RAW=
RESET_AT_UTC=2000-01-01T00:00:00Z
RETRY_AFTER_SECONDS=0
WAIT_REQUIRED=no
WAIT_UNTIL=2000-01-01T00:00:00Z
REAL_WAIT_STARTED=no
WORKSPACE_RECHECK_REQUIRED=yes
WORKSPACE_RECHECK_DONE=yes
RESET_PASSED=yes
NEXT_PENDING_MATCHES=no
NEXT_STAGE_MATCHES=no
RECOVERY_ALLOWED=no
USER_CONFIRMATION_REQUIRED=yes
RUNTIME_CREATED=no
CHECKPOINT_FILES_CREATED=no
REAL_RESUME_ENABLED=no
RUNNER_EXECUTED=no
GIT_ADD_EXECUTED=no
GIT_COMMIT_EXECUTED=no
GIT_PUSH_EXECUTED=no
REPORT_PATH=reports\rate-limit-recovery\T200-evaluate-recovery-report.md
CHECK_RESULT=fail
```

## Details

- ok: False
- can_wait: False
- can_resume: False
- reset_passed: True
- workspace_clean: False
- dirty_workspace_detected: False
- unclassified_changes: []
- next_pending_matches: False
- next_stage_matches: False
- checkpoint_valid: True
- user_confirmation_required: True
- blocked_reason: E_NEXT_PENDING_MISMATCH or E_STAGE_MISMATCH
- warnings: ['NEXT_PENDING mismatch: actual=T201, expected=T200', 'NEXT_STAGE mismatch: actual=Stage 12, expected=Stage 99']
- next_action: fail_closed
- JSON report written to: reports\rate-limit-recovery\T200-recovery-decision.json

