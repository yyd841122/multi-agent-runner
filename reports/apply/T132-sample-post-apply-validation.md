# Post-Apply Validation Record (T132 Dry-Run)

> **DRY-RUN RECORD** — This is a simulated post-apply validation. No real patch apply, no command execution.

## Metadata

| Field | Value |
|-------|-------|
| task_id | T132 |
| generated_at | 2026-05-09T08:07:00Z |

## Validation Checks (18 items)

| # | Check | Result |
|---|-------|--------|
| 1 | approval_record_exists | pass |
| 2 | pre_apply_audit_exists | pass |
| 3 | post_apply_audit_exists | pass |
| 4 | task_id_matches | pass |
| 5 | expected_files_not_empty | pass |
| 6 | actual_files_not_empty | pass |
| 7 | actual_files_subset_of_expected | pass |
| 8 | no_unexpected_files | pass |
| 9 | no_forbidden_files | pass |
| 10 | no_path_traversal | pass |
| 11 | no_absolute_paths | pass |
| 12 | diff_stat_present | pass |
| 13 | validation_results_present | pass |
| 14 | required_reports_present | pass |
| 15 | human_review_required_yes | pass |
| 16 | ready_for_commit_no | pass |
| 17 | ready_for_push_no | pass |
| 18 | ready_for_stage_8_no | pass |

## Workspace Classification

| Field | Value |
|-------|-------|
| classification | expected_dirty |
| diff_stat_present | yes |
| no_unexpected_files | yes |

## Decision

| Field | Value |
|-------|-------|
| post_apply_validation_status | pass |
| ready_for_human_review | yes |
| ready_for_git_backup_dry_run | yes |
| ready_for_commit | no |
| ready_for_push | no |
| ready_for_stage_8 | no |
| check_result | pass |
