# T131 Post-Apply Validation Gate Check

## Task

设计 post-apply validation gate。

## Scope

本轮只做设计，不实现代码，不真实 apply patch，不执行 command。

## Inputs Checked

| # | Input | Source | Status |
|---|-------|--------|--------|
| 1 | real-apply-approval-persistence-and-audit-record-design.md | T129 design | read |
| 2 | T130-real-apply-approval-record-dry-run-check.md | T130 check report | read |
| 3 | T130-dev-report.md | T130 dev report | read |
| 4 | T130-sample-approval-record.md | T130 sample record | read |
| 5 | T130-sample-pre-apply-audit.md | T130 sample record | read |
| 6 | T130-sample-post-apply-audit.md | T130 sample record | read |
| 7 | docs/tasks.md | Task definitions | read |
| 8 | memory/lessons.md | Lessons history | read |
| 9 | memory/pitfalls.md | Pitfalls history | read |

## Design Check

| # | Design Element | Defined | Notes |
|---|---------------|---------|-------|
| 1 | gate purpose | yes | post-apply safety check, before commit/push/Stage 8 |
| 2 | required inputs | yes | 12 inputs from approval/audit records, git status, diff stat |
| 3 | required post-apply checks | yes | 18 checks covering records, files, diff, validation, reports, safety flags |
| 4 | dirty workspace classification | yes | 3 categories: expected_dirty, unexpected_dirty, clean_unexpected |
| 5 | expected vs actual files validation | yes | actual ⊆ expected + allowed reports, any extra file → fail |
| 6 | diff stat validation | yes | 5 rejection conditions: missing, too large, binary, delete, rename |
| 7 | validation command result handling | yes | only verify recorded, not execute; 4 fields tracked |
| 8 | required reports | yes | 3 reports: dev report, post-apply validation check, post-apply audit |
| 9 | pass/fail decision | yes | pass → ready_for_git_backup_dry_run; fail → stop with reason |
| 10 | rejection conditions | yes | 21 hard fail conditions, no soft rejection |
| 11 | T132 boundary | yes | T131 = design only; T132 = dry-run implementation |

### Design Completeness

```text
GATE_PURPOSE_DEFINED=yes
REQUIRED_INPUTS_DEFINED=yes (12 items)
REQUIRED_POST_APPLY_CHECKS_DEFINED=yes (18 checks)
DIRTY_WORKSPACE_CLASSIFICATION_DEFINED=yes (3 categories)
EXPECTED_VS_ACTUAL_FILES_VALIDATION_DEFINED=yes
DIFF_STAT_VALIDATION_DEFINED=yes (5 rejection conditions)
VALIDATION_COMMAND_RESULT_HANDLING_DEFINED=yes
REQUIRED_REPORTS_DEFINED=yes (3 reports)
PASS_FAIL_DECISION_DEFINED=yes
REJECTION_CONDITIONS_DEFINED=yes (21 conditions)
T132_BOUNDARY_DEFINED=yes
DESIGN_COMPLETE=yes
```

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

### Design Safety Rules

| Rule | Status |
|------|--------|
| pass ≠ commit permission | enforced |
| pass ≠ push permission | enforced |
| pass ≠ Stage 8 permission | enforced |
| fail → no Git backup dry-run | enforced |
| all rejection = hard fail | enforced |
| clean_unexpected → stop | enforced |
| unexpected_dirty → stop | enforced |
| gate runs after apply, before commit | by design |

## Decision

```text
POST_APPLY_VALIDATION_GATE_CHECK=pass
READY_FOR_T132=yes
READY_FOR_REAL_APPLY=no
READY_FOR_STAGE_8=no
DESIGN_COMPLETENESS=11/11
SAFETY_CHECKS=11/11
CHECK_RESULT=pass
```

## Next

T132：实现 first real patch apply guarded dry-run
