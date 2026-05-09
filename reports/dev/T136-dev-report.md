# T136 Dev Report

## Task

实现 guarded Git backup dry-run。

## Scope

本轮只实现 Git backup dry-run，不执行 git add / commit / push，不真实执行任务。

## Background

T135 已完成 guarded Git backup dry-run gate 设计，定义了 17 个 required inputs、22 项 gate checks、backup record schema v1.0、commit message rules、25 个 rejection conditions。

T136 基于 T135 设计实现 guarded Git backup dry-run，只做预览和记录生成。

## Changed Files

| File | Change Type | Description |
|------|-------------|-------------|
| tools/continuous_task_planner.py | modified | 新增 GuardedGitBackupDryRunResult dataclass、validate_guarded_git_backup_commit_message_dry_run()、build_guarded_git_backup_dry_run_record_content()、run_guarded_git_backup_dry_run() |
| runner.py | modified | 新增 guarded-git-backup-dry-run CLI 命令 |
| reports/git-backup/T136-sample-backup-record.md | new | Pass 场景 sample backup record |
| reports/checks/T136-guarded-git-backup-dry-run-check.md | new | 14 场景验证检查报告 |
| reports/dev/T136-dev-report.md | new | This file |
| docs/tasks.md | modified | T136 status: pending → in_progress → done |

## Implementation

### GuardedGitBackupDryRunResult

新增 dataclass，包含 45+ 字段：
- 模式标识：dry_run_mode = guarded_git_backup_dry_run
- 任务信息：task_id, task_title
- Git 状态：last_commit_before_backup, branch, remote, worktree_status
- 文件信息：expected/actual/staged_planned/unexpected files, diff_stat
- Reports：dev_report_path, check_report_path, apply_record_paths
- Commit message：commit_message, commit_message_valid, rejection_reasons
- 前置校验：guarded_apply_check_result, post_apply_validation_check_result
- Ready flags：ready_for_git_backup_dry_run, ready_for_real_git_add/commit/push, ready_for_stage_8
- 安全保证字段：real_git_add/commit/push_performed 全部 no
- 结果：rejection_reasons, check_result, message

### validate_guarded_git_backup_commit_message_dry_run()

校验规则：
- 必须非空
- 建议包含 task id 或任务关键词
- 长度不超过 500 字符
- 拒绝 10 个 unsafe patterns（real patch applied, pushed to, stage 8, auto continue, auto backup, unattended, production, bypass, forced backup）
- 无 dry-run context 时拒绝 git add/commit/push 执行暗示

### build_guarded_git_backup_dry_run_record_content()

基于 T135 schema v1.0 生成 Markdown + YAML fenced block：
- 包含 git state、files、reports、commit、safety、validation、decision 完整字段
- 明确标记 DRY-RUN
- 所有安全字段设为 no
- human_review_required=yes

### run_guarded_git_backup_dry_run()

支持 14 个 sample 场景：
- pass: 所有 22 gate checks 通过，生成 backup record
- 13 个 fail 场景：各自触发对应 rejection condition

Gate checks 实现 7 组 22 项检查：
- Group 1 Workspace State (3 checks)
- Group 2 Guarded Apply Validation (4 checks)
- Group 3 Safety Flags (4 checks)
- Group 4 File Validation (4 checks)
- Group 5 Records Validation (1 check)
- Group 6 Commit Message (2 checks)
- Group 7 Backup Record (4 checks)

### runner.py CLI

新增命令：`python runner.py guarded-git-backup-dry-run --sample <name>`

输出包含全部安全字段和决策字段。

## Generated Dry-Run Records

- reports/git-backup/T136-sample-backup-record.md（pass 场景生成）

## Safety Rules

| # | Check | Status |
|---|-------|--------|
| 1 | no git add | guaranteed |
| 2 | no git commit | guaranteed |
| 3 | no git push | guaranteed |
| 4 | no real patch apply | guaranteed |
| 5 | no command execution | guaranteed |
| 6 | no run-project-task-full call | guaranteed |
| 7 | no Claude Code call | guaranteed |
| 8 | no business code modification | guaranteed |
| 9 | no real task execution | guaranteed |
| 10 | no auto-continue | guaranteed |
| 11 | no auto Git backup | guaranteed |
| 12 | no Stage 8 continuation | guaranteed |
| 13 | human review required | guaranteed |

## Verification

| # | Sample | CHECK_RESULT | Safety Fields |
|---|--------|-------------|---------------|
| 1 | pass | pass | all no |
| 2 | guarded-apply-failed | fail | all no |
| 3 | post-apply-validation-failed | fail | all no |
| 4 | not-ready-for-git-backup | fail | all no |
| 5 | unexpected-file | fail | all no |
| 6 | missing-dev-report | fail | all no |
| 7 | missing-check-report | fail | all no |
| 8 | missing-apply-record | fail | all no |
| 9 | missing-diff-stat | fail | all no |
| 10 | unsafe-commit-message | fail | all no |
| 11 | git-add-requested | fail | all no |
| 12 | git-commit-requested | fail | all no |
| 13 | git-push-requested | fail | all no |
| 14 | stage-8-requested | fail | all no |

14/14 scenarios validated. 1 pass + 13 fail-closed.

## Decision

```text
IMPLEMENTATION_STATUS=done
GUARDED_GIT_BACKUP_DRY_RUN=implemented
BACKUP_RECORD_GENERATED=yes
SCENARIOS_TOTAL=14
SCENARIOS_PASS=14/14
FAIL_CLOSED_SCENARIOS_PASS=13/13
READY_FOR_T137=yes
READY_FOR_REAL_GIT_ADD=no
READY_FOR_REAL_COMMIT=no
READY_FOR_REAL_PUSH=no
READY_FOR_STAGE_8=no
HUMAN_REVIEW_REQUIRED=yes
```

## Next

T137：验证 guarded Git backup dry-run pass/fail 场景
