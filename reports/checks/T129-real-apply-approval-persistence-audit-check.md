# T129 Real Apply Approval Persistence and Audit Check

## Task

设计 real apply approval persistence and audit record。

## Scope

本轮只做设计，不实现代码，不真实 apply patch，不执行 command。

## Inputs Checked

| # | File | Present | Used For |
|---|------|---------|----------|
| 1 | docs/stage-7-human-reviewed-controlled-apply-archive-summary.md | yes | T123-T128 归档结论 |
| 2 | docs/human-reviewed-controlled-apply-gate-design.md | yes | approval token、前置条件、拒绝条件 |
| 3 | reports/checks/T128-stage-7-human-reviewed-controlled-apply-archive-check.md | yes | T128 归档检查 |
| 4 | reports/dev/T128-dev-report.md | yes | T128 归档 dev report |
| 5 | docs/tasks.md | yes | T129 任务定义 |
| 6 | memory/lessons.md | yes | 历史经验 |
| 7 | memory/pitfalls.md | yes | 历史避坑 |

7/7 inputs present。

## Design Check

| # | Design Element | Defined | Notes |
|---|---------------|---------|-------|
| 1 | approval record purpose | yes | 10 项作用明确 |
| 2 | approval record schema | yes | 6 个 section，version/id/approval/scope/evidence/safety/fingerprint/decision |
| 3 | approval record field definitions | yes | 每个字段有类型、必填、说明 |
| 4 | audit record purpose | yes | 8 项作用明确 |
| 5 | audit record schema | yes | 6 个 section，version/id/git/changes/validation/safety/decision |
| 6 | audit record field definitions | yes | pre_apply 和 post_apply 两个 phase |
| 7 | file path design | yes | 推荐 reports/apply/ 单目录方案，有理由 |
| 8 | required evidence list | yes | 20 项 evidence |
| 9 | invalidation conditions | yes | 15 个条件（14 hard + 1 soft） |
| 10 | T130 boundary | yes | T129 设计 vs T130 实现边界清晰 |

10/10 design elements defined。

## Schema Completeness

### Approval Record Schema

| Section | Fields | Required Fields |
|---------|--------|----------------|
| metadata | version, id, task_id, task_title | 4/4 |
| approval | mode, token, approved_by, approved_at | 4/4 |
| scope | allowed_files, target_files, patch_files, forbidden_files | 4/4 |
| evidence | 8 check results | 8/8 |
| safety | 5 safety declarations | 5/5 |
| fingerprint | proposal_hash, patch_hash, target_files_hash | 3/3 |
| decision | 3 decision fields | 3/3 |

### Audit Record Schema

| Section | Fields | Required Fields |
|---------|--------|----------------|
| metadata | version, id, task_id, linked_approval_id, phase | 5/5 |
| git | head_before, head_after, status_before, status_after | 4/4 |
| changes | expected_files, actual_files, unexpected_files, diff_stat | 4/4 |
| validation | commands_planned, commands_executed, command_results | 3/3 |
| safety | 5 safety checks | 5/5 |
| decision | 3 decision fields | 3/3 |

## Safety Review

| # | Check | Result |
|---|-------|--------|
| 1 | no real patch applied | guaranteed (design only) |
| 2 | no command executed | guaranteed (design only) |
| 3 | no Claude Code called | guaranteed (design only) |
| 4 | no run-project-task-full called | guaranteed (design only) |
| 5 | no business code changed | guaranteed (design only) |
| 6 | no auto-continue | guaranteed (safety.auto_continue_allowed == no) |
| 7 | no auto Git backup | guaranteed (safety.auto_git_backup_allowed == no) |
| 8 | no Stage 8 continuation | guaranteed (safety.stage_8_allowed == no) |
| 9 | human review required | guaranteed (safety.human_review_required == yes) |
| 10 | no code implementation | guaranteed (T129 is design only) |

## Decision

```text
REAL_APPLY_APPROVAL_PERSISTENCE_CHECK=pass
READY_FOR_T130=yes
READY_FOR_REAL_APPLY=no
READY_FOR_STAGE_8=no
```

## Next

T130：实现 real apply approval record dry-run
