# T132 Dev Report

## Task

实现 first real patch apply guarded dry-run。

## Scope

本轮只实现 guarded dry-run，不真实 apply patch，不执行 command，不真实执行任务。

## Background

T129 已完成 real apply approval persistence and audit record 设计。T130 已实现 approval record / pre-apply audit / post-apply audit dry-run 生成能力（7/7 scenarios validated）。T131 已设计 post-apply validation gate（12 inputs, 18 checks, 3 workspace classifications, 21 rejection conditions）。

本轮基于 T129/T130/T131，实现 guarded real patch apply 的完整安全链路 dry-run。

## Changed Files

| File | Change Type | Description |
|------|-------------|-------------|
| tools/continuous_task_planner.py | modified | 新增 FirstRealPatchApplyGuardedDryRunResult dataclass、classify_post_apply_workspace_dry_run()、validate_post_apply_state_dry_run()、run_first_real_patch_apply_guarded_dry_run()、_build_guarded_apply_dry_run_sample_files() |
| runner.py | modified | 新增 first-real-patch-apply-guarded-dry-run CLI 命令 |
| reports/apply/T132-sample-guarded-apply-dry-run.md | new | Sample guarded apply dry-run record |
| reports/apply/T132-sample-post-apply-validation.md | new | Sample post-apply validation record |
| reports/checks/T132-first-real-patch-apply-guarded-dry-run-check.md | new | 验证报告 |
| reports/dev/T132-dev-report.md | new | This file |
| docs/tasks.md | modified | T132 status: pending → in_progress → done |
| memory/lessons.md | modified | T132 lesson |
| memory/pitfalls.md | modified | T132 pitfall |

## Implementation

### FirstRealPatchApplyGuardedDryRunResult

Dataclass 包含 40+ 字段，覆盖：
- 模式标识 (dry_run_mode)
- 任务信息 (task_id, task_title)
- Record 路径和检查结果 (approval/pre/post audit paths and check results)
- 文件范围 (expected_target_files, expected_patch_files, actual_changed_files, unexpected_files)
- Diff (diff_stat_after)
- Post-apply validation (post_apply_validation_status, dirty_workspace_classification)
- Ready flags (human_review, git_backup_dry_run, real_apply, command_execution, commit, push, stage_8)
- 安全保证字段（全部为安全值）
- 结果 (stop_reason, violations, check_result, message)

### classify_post_apply_workspace_dry_run()

根据 T131 dirty workspace 分类规则，判断 workspace 状态：
- git_status_after 为空 → clean_unexpected
- actual_changed_files ⊆ expected + allowed reports，且 diff_stat 存在 → expected_dirty
- 其他 → unexpected_dirty

### validate_post_apply_state_dry_run()

模拟 T131 post-apply validation gate 的 18 项检查：
- Record existence (approval_record, pre_apply_audit, post_apply_audit)
- File scope (expected/actual 非空, actual ⊆ expected, 无 forbidden/path_traversal/absolute_path)
- Diff stat present
- Safety flags (human_review_required=yes, no commit/push/stage_8 requested)
- Workspace classification (expected_dirty → pass, others → fail)

### run_first_real_patch_apply_guarded_dry_run()

主函数：支持 12 个 sample 场景（1 pass + 11 fail-closed）：
- pass: 全部通过，生成 2 个 sample 文件
- missing-approval-record: 缺少 approval record → fail
- missing-pre-audit: 缺少 pre-apply audit → fail
- missing-post-audit: 缺少 post-apply audit → fail
- unexpected-file: 意外文件变更 → fail, unexpected_dirty
- forbidden-file: 禁入文件变更 → fail, unexpected_dirty
- missing-diff-stat: diff stat 缺失 → fail, unexpected_dirty
- clean-unexpected: 预期 apply 但 worktree clean → fail, clean_unexpected
- missing-validation-results: 验证结果缺失 + human_review_required=no → fail
- commit-requested: 请求 commit → fail
- push-requested: 请求 push → fail
- stage-8-requested: 请求 Stage 8 → fail

### runner.py first-real-patch-apply-guarded-dry-run CLI

命令格式：`python runner.py first-real-patch-apply-guarded-dry-run --sample <name>`

输出所有关键字段，包括 9 个安全保证字段。

## Generated Dry-Run Records

| File | Description |
|------|-------------|
| reports/apply/T132-sample-guarded-apply-dry-run.md | Guarded apply dry-run record，包含 Metadata、Records、File Scope、Diff Stat、Validation、Safety、Decision |
| reports/apply/T132-sample-post-apply-validation.md | Post-apply validation record，包含 18 项检查结果、workspace classification、decision |

## Safety Rules

| Check | Status |
|-------|--------|
| no real patch apply | yes |
| no command execution | yes |
| no run-project-task-full call | yes |
| no Claude Code call | yes |
| no business code modification | yes |
| no real task execution | yes |
| no auto-continue | yes |
| no auto Git backup | yes |
| no commit | yes |
| no push | yes |
| no Stage 8 continuation | yes |
| human review required | yes |

## Verification

12 个 sample 场景全部通过：

| # | Sample | Validation Status | Classification | Check Result |
|---|--------|-------------------|----------------|--------------|
| 1 | pass | pass | expected_dirty | pass |
| 2 | missing-approval-record | fail | expected_dirty | fail |
| 3 | missing-pre-audit | fail | expected_dirty | fail |
| 4 | missing-post-audit | fail | expected_dirty | fail |
| 5 | unexpected-file | fail | unexpected_dirty | fail |
| 6 | forbidden-file | fail | unexpected_dirty | fail |
| 7 | missing-diff-stat | fail | unexpected_dirty | fail |
| 8 | clean-unexpected | fail | clean_unexpected | fail |
| 9 | missing-validation-results | fail | expected_dirty | fail |
| 10 | commit-requested | fail | expected_dirty | fail |
| 11 | push-requested | fail | expected_dirty | fail |
| 12 | stage-8-requested | fail | expected_dirty | fail |

Total: 12/12 scenarios validated。

## Next

T133：验证 first real patch apply guarded dry-run pass/fail 场景，或根据 docs/tasks.md 中下一任务继续。
