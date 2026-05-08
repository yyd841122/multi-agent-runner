# T131 Dev Report

## Task

设计 post-apply validation gate。

## Scope

本轮只做设计，不实现代码，不真实执行任务。

## Background

T129 已设计 approval persistence and audit record schema（approval record + pre/post-apply audit）。T130 已实现 approval/audit record dry-run 生成能力（7/7 scenarios validated）。

当前仍不能 real apply。下一步需要在 guarded real patch apply 之前，设计 apply 后的 validation gate，确保 apply 后的 worktree 状态、文件范围、diff、验证结果和报告符合预期。

## Changed Files

| File | Change Type | Description |
|------|-------------|-------------|
| docs/post-apply-validation-gate-design.md | new | Post-apply validation gate 设计文档 |
| reports/checks/T131-post-apply-validation-gate-check.md | new | 设计验证报告 |
| reports/dev/T131-dev-report.md | new | This file |
| docs/tasks.md | modified | T131 status: pending → in_progress → done |
| memory/lessons.md | modified | T131 lesson |
| memory/pitfalls.md | modified | T131 pitfall |

## Design Summary

### Required Inputs (12 items)

gate 需要 12 个输入：task_id、approval_record_path、pre_apply_audit_path、post_apply_audit_path、expected_target_files、expected_patch_files、actual_changed_files、git_status_after、diff_stat_after、validation_results、report_paths、human_review_required。

### Required Post-Apply Checks (18 checks)

18 项检查覆盖 6 个类别：
1. Record existence（3 项）：approval record、pre-apply audit、post-apply audit 存在
2. ID consistency（1 项）：task_id 一致
3. File scope（7 项）：expected/actual 非空、actual ⊆ expected、无意外文件、无禁入文件、无路径逃逸、无绝对路径
4. Diff validation（1 项）：diff stat 存在
5. Validation & reports（2 项）：validation results 存在、required reports 存在
6. Safety flags（4 项）：human_review_required=yes、ready_for_commit/push/stage_8=no

### Dirty Workspace Classification (3 categories)

- **expected_dirty**：只有预期文件变更，可进入 human review 和 Git backup dry-run
- **unexpected_dirty**：有意外变更，必须停止
- **clean_unexpected**：预期有 apply 但 worktree 意外 clean，必须停止

### Expected vs Actual Files Validation

actual_changed_files 必须是 expected_target_files 或 expected_patch_files 的子集（加上 allowed report patterns）。任何额外文件都 fail。

### Diff Stat Validation (5 rejection conditions)

拒绝：missing diff stat、diff too large、unexpected binary、unexpected delete、unexpected rename。

### Validation Command Result Handling

本 gate 只验证 command result 是否已记录（4 个字段），不负责执行 command。未来 command execution 由独立 executor gate 控制。

### Required Reports (3 reports)

dev report、post-apply validation check、post-apply audit 必须存在。

### Pass/Fail Decision

- pass → READY_FOR_HUMAN_REVIEW=yes, READY_FOR_GIT_BACKUP_DRY_RUN=yes, READY_FOR_COMMIT=no
- fail → READY_FOR_HUMAN_REVIEW=yes, READY_FOR_GIT_BACKUP_DRY_RUN=no, STOP_REASON=<reason>

### Rejection Conditions (21 conditions)

21 个 hard fail 条件，无 soft rejection。

### T132 Boundary

T131 只设计，T132 实现 first real patch apply guarded dry-run。两者不重叠。

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

## Decision

```text
READY_FOR_T132=yes
READY_FOR_REAL_APPLY=no
READY_FOR_COMMAND_EXECUTION=no
READY_FOR_COMMIT=no
READY_FOR_PUSH=no
READY_FOR_STAGE_8=no
```

## Next

T132：实现 first real patch apply guarded dry-run
