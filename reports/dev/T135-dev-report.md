# T135 Dev Report

## Task

设计 guarded Git backup dry-run gate。

## Scope

本轮只做设计，不实现代码，不执行 Git 操作。

## Background

T129-T134 已完成 guarded real patch apply dry-run 全链路：

- T129-T131：approval persistence + post-apply validation gate 设计
- T132-T133：guarded dry-run 实现 + pass/fail 验证（12/12 scenarios）
- T134：归档总结，确认 READY_FOR_GIT_BACKUP_DRY_RUN=yes

当前需要设计 guarded Git backup dry-run gate，作为从 guarded apply dry-run 到 Git backup dry-run 之间的安全门。

## Changed Files

| File | Change Type | Description |
|------|-------------|-------------|
| docs/tasks.md | modified | T135 status: pending → in_progress → done |
| docs/guarded-git-backup-dry-run-gate-design.md | new | Guarded Git backup dry-run gate 设计文档 |
| reports/checks/T135-guarded-git-backup-dry-run-gate-check.md | new | 设计检查报告 |
| reports/dev/T135-dev-report.md | new | This file |
| memory/lessons.md | modified | T135 lesson |
| memory/pitfalls.md | modified | T135 pitfall |

## Design Summary

### Required Inputs

17 个输入，来源于 task definition、git state、T132/T133 output 和 task reports。

### Required Gate Checks

22 项检查，分为 7 组：

1. **Workspace State** (3 checks): worktree classification, actual vs expected files, forbidden files
2. **Guarded Apply Validation** (4 checks): apply check pass, post-apply validation, readiness flags
3. **Safety Flags** (4 checks): commit/push/stage8 readiness, human review
4. **File Validation** (4 checks): unexpected files, diff stat, reports existence
5. **Records Validation** (1 check): apply records existence
6. **Commit Message** (2 checks): generated and safe
7. **Backup Record** (4 checks): generated, no real git operations

### Backup Record Schema

Version 1.0，包含 40+ 字段：git state、files、reports、commit preview、safety declarations、validation results、decision。

### Commit Message Rules

- Structure: `<type>: <short summary>`
- Required: task id, task achievement description
- Forbidden: misleading claims, real apply/push/Stage 8 implication
- Unsafe patterns: 8 个拒绝模式

### Rejection Conditions

25 个拒绝条件，覆盖 workspace、apply validation、safety flags、file validation、records、commit message、backup record 和 operation requests。

### Allowed After Gate Pass

5 个允许操作：generate record、preview files、preview commit message、preview decision、stop for review。

### Forbidden After Gate Pass

8 个禁止操作：real git add/commit/push、auto backup、auto continue、Stage 8、command exec、business code modification。

### T136 Boundary

T135 只设计 gate，不实现代码。T136 基于 T135 设计实现 gate 逻辑和 CLI 命令入口。

## Safety Rules

| Check | Status |
|-------|--------|
| no real patch apply | guaranteed |
| no command execution | guaranteed |
| no run-project-task-full call | guaranteed |
| no Claude Code call | guaranteed |
| no business code modification | guaranteed |
| no git add | guaranteed |
| no git commit | guaranteed |
| no git push | guaranteed |
| no auto-continue | guaranteed |
| no Stage 8 continuation | guaranteed |
| human review required | guaranteed |

## Decision

```text
DESIGN_STATUS=done
READY_FOR_GUARDED_GIT_BACKUP_DRY_RUN_IMPLEMENTATION=yes
READY_FOR_REAL_GIT_ADD=no
READY_FOR_REAL_COMMIT=no
READY_FOR_REAL_PUSH=no
READY_FOR_STAGE_8=no
HUMAN_REVIEW_REQUIRED=yes
```

## Next

T136：实现 guarded Git backup dry-run
