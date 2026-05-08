# T129 Dev Report

## Task

设计 real apply approval persistence and audit record。

## Scope

本轮只做设计，不实现代码，不真实执行任务。

## Background

T123-T128 已完成 human-reviewed controlled apply dry-run chain，84/84 scenarios validated。当前需要 approval persistence and audit record 设计，确保未来 real apply 决策有持久化、可审计、可追溯的记录。

## Changed Files

| File | Change Type | Description |
|------|-------------|-------------|
| docs/real-apply-approval-persistence-and-audit-record-design.md | new | approval persistence 和 audit record 设计文档 |
| reports/checks/T129-real-apply-approval-persistence-audit-check.md | new | 设计检查报告 |
| reports/dev/T129-dev-report.md | new | This file |
| docs/tasks.md | modified | T129 status: pending → in_progress → done |
| memory/lessons.md | modified | T129 lesson |
| memory/pitfalls.md | modified | T129 pitfall |

## Design Summary

### Approval Record Schema

- **元数据**：version (1.0)、approval_id (APR-YYYYMMDD-HHMMSS-<6hex>)、task_id、task_title
- **批准信息**：approval_mode、approval_token、approved_by、approved_at
- **批准范围**：allowed_files、target_files、patch_files、forbidden_files
- **前置证据**：8 项 check results (parser → validator → patch → pipeline → approval → command → controlled_apply → pass_fail)
- **安全声明**：5 项安全字段（全部为安全值）
- **指纹**：proposal_hash、patch_hash、target_files_hash（用于 invalidation 检测）
- **决策**：ready_for_real_apply=no、ready_for_apply_record_dry_run=yes、approval_valid=yes/invalidated/expired

### Audit Record Schema

- **两阶段**：pre_apply（apply 前快照）和 post_apply（apply 后快照）
- **Git 状态**：HEAD before/after、worktree status before/after
- **文件变更**：expected vs actual vs unexpected files、diff_stat
- **验证命令**：commands_planned、commands_executed、command_results
- **安全检查**：business_code_changed、framework_code_changed、unexpected_dirty_workspace、real_patch_applied、command_execution_performed
- **决策**：requires_human_review=yes、ready_for_commit=no、ready_for_push=no

### File Path Design

- 推荐：`reports/apply/` 单目录方案
- 文件：`T{xxx}-approval-record.md`、`T{xxx}-pre-apply-audit.md`、`T{xxx}-post-apply-audit.md`
- 理由：内聚性、简单性、与现有目录模式一致

### Required Evidence

- 20 项 evidence 在未来 real apply 前必须全部满足
- 覆盖：workspace、task、proposal、token、8 项 pipeline checks、scope、safety、approval validity、audit completeness、fingerprint consistency

### Invalidation Conditions

- 15 个条件：14 hard invalidation + 1 soft invalidation
- Hard：dirty workspace、token 问题、record 缺失、内容篡改、safety violation
- Soft：approval 超过 24 小时（人工决定是否接受）

### T130 Boundary

- T129：设计 schema、定义 evidence、定义 invalidation
- T130：实现 approval record dry-run、audit record dry-run、fingerprint 计算、invalidation 检查

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
| no Stage 8 continuation | yes |
| human review required | yes |

## Decision

```text
REAL_APPLY_APPROVAL_PERSISTENCE_DESIGNED=yes
AUDIT_RECORD_DESIGNED=yes
READY_FOR_APPROVAL_RECORD_DRY_RUN=yes
READY_FOR_REAL_APPLY=no
READY_FOR_COMMAND_EXECUTION=no
READY_FOR_STAGE_8=no
HUMAN_REVIEW_REQUIRED=yes
```

- ready for T130 approval record dry-run
- not ready for real apply
- not ready for command execution
- not ready for Stage 8

## Next

T130：实现 real apply approval record dry-run
