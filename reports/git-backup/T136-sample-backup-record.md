# Git Backup Dry-Run Record

```yaml
backup_record_version: "1.0"
backup_id: "T136-backup-dry-run"
task_id: "T136"
task_title: "实现 guarded Git backup dry-run"
backup_mode: "guarded_git_backup_dry_run"
generated_at: "2026-05-09T10:20:29"

git:
  head_before_backup: "281f30f"
  branch: "main"
  remote: "origin"
  worktree_status: "expected_dirty"

files:
  expected_changed_files:
    - "tools/continuous_task_planner.py"
    - "runner.py"
    - "docs/tasks.md"
    - "reports/checks/T136-guarded-git-backup-dry-run-check.md"
    - "reports/dev/T136-dev-report.md"
    - "reports/git-backup/T136-sample-backup-record.md"
  actual_changed_files:
    - "tools/continuous_task_planner.py"
    - "runner.py"
    - "docs/tasks.md"
    - "reports/checks/T136-guarded-git-backup-dry-run-check.md"
    - "reports/dev/T136-dev-report.md"
    - "reports/git-backup/T136-sample-backup-record.md"
  staged_files_planned:
    - "tools/continuous_task_planner.py"
    - "runner.py"
    - "docs/tasks.md"
    - "reports/checks/T136-guarded-git-backup-dry-run-check.md"
    - "reports/dev/T136-dev-report.md"
    - "reports/git-backup/T136-sample-backup-record.md"
  unexpected_files:
  forbidden_files_found: []

reports:
  dev_report: "reports/dev/T136-dev-report.md"
  check_report: "reports/checks/T136-guarded-git-backup-dry-run-check.md"
  apply_records:
    - "reports/apply-records/T132-apply-record.md"
    - "reports/apply-records/T133-apply-record.md"

commit:
  commit_message: "feat: add guarded git backup dry run"
  commit_type: "test"
  commit_scope: "T136"
  commit_allowed: "no"
  push_allowed: "no"

safety:
  real_git_add_performed: "no"
  real_git_commit_performed: "no"
  real_git_push_performed: "no"
  auto_continue_allowed: "no"
  stage_8_allowed: "no"
  command_execution_performed: "no"
  business_code_modified: "no"

validation:
  gate_checks_total: 22
  gate_checks_passed: 22
  gate_checks_failed: 0
  failed_checks:

decision:
  ready_for_git_backup_dry_run: "yes"
  ready_for_git_add: "no"
  ready_for_commit: "no"
  ready_for_push: "no"
  ready_for_stage_8: "no"
  human_review_required: "yes"
  check_result: "pass"

notes: |
  This is a DRY-RUN backup record. No real git operations were performed.
  Guarded apply check: pass.
  Post-apply validation check: pass.
  Rejection reasons: [].
```
