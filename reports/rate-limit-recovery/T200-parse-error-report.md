# T200 Parse Error Dry-run Report

Generated: 2026-05-15T03:35:26Z

## Status

```text
RATE_LIMIT_RECOVERY_RESULT=pass
COMMAND=parse-error
TASK_ID=T200
STAGE=Stage 12
RUN_ID=RUN-20260515-033526
RATE_LIMIT_DETECTED=yes
ERROR_CODE=1308
REQUEST_ID=sample-request
RESET_AT_RAW=2026-05-12 19:47:46
RESET_AT_UTC=2026-05-12T11:47:46Z
RETRY_AFTER_SECONDS=0
WAIT_REQUIRED=yes
WAIT_UNTIL=2026-05-12T11:47:46Z
REAL_WAIT_STARTED=no
WORKSPACE_RECHECK_REQUIRED=yes
WORKSPACE_RECHECK_DONE=no
RESET_PASSED=no
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
REPORT_PATH=reports\rate-limit-recovery\T200-parse-error-report.md
CHECK_RESULT=pass
```

## Details

- detected: True
- provider: zhipu
- error_code: 1308
- error_message: 已达到 5 小时的使用上限。您的限额将在 2026-05-12 19:47:46 重置。
- request_id: sample-request
- reset_at_raw: 2026-05-12 19:47:46
- reset_at_utc: 2026-05-12T11:47:46Z
- retry_after_seconds: 0
- run_id: RUN-20260515-033526
- checkpoint_id: CP-20260515-033526
- JSON report written to: reports\rate-limit-recovery\T200-rate-limit-recovery-state.json

