# T123 Dev Report

## Task

设计 human-reviewed controlled apply gate。

## Scope

本轮只做设计，不实现代码，不真实执行任务。

## Background

T117-T122 已完成 no-tool-use dry-run 链路：

- T117：proposal parser dry-run（7/7）
- T118：allowed scope validator dry-run（9/9）
- T119：controlled patch apply dry-run（9/9）
- T120：first no-tool-use single-task dry-run（8/8）
- T121：pass/fail 验证（8/8，1 pass + 7 fail closed）
- T122：归档 Stage 7 no-tool-use execution 阶段成果

T122 确认 `ready_for_human_review` 不等于 `ready_for_real_execution`，需要设计人工确认安全门。

## Changed Files

| File | Change Type | Description |
|------|-------------|-------------|
| docs/human-reviewed-controlled-apply-gate-design.md | new | Gate design document |
| reports/checks/T123-human-reviewed-controlled-apply-gate-check.md | new | Gate check report |
| reports/dev/T123-dev-report.md | new | This file |
| docs/tasks.md | modified | T123 status update |
| memory/lessons.md | modified | T123 lesson |
| memory/pitfalls.md | modified | T123 pitfall |

## Gate Summary

### Approval Token

- Token: `APPROVE_CONTROLLED_APPLY_DRY_RUN`
- Rules: exact match, case sensitive, single use per gate
- Permissions: 只允许进入 controlled apply approval model dry-run
- Restrictions: 不允许 real commit, push, Stage 8, skip validator/patch dry-run, real patch apply

### Preconditions (12)

1. worktree clean
2. single task selected
3. proposal parsed successfully
4. scope validation passed
5. patch dry-run passed
6. pass/fail validation completed
7. no business code changed unexpectedly
8. no command execution requested
9. no auto-continue requested
10. no auto-git-backup requested
11. human review required=yes
12. ready_for_real_execution=no

### Rejection Conditions (17)

覆盖 dirty workspace、missing/wrong token、parse/validation/patch failure、scope violation、path traversal、absolute path、auto-continue、auto-git-backup、command execution、unexpected ready_for_real_execution 等。

### Dirty Workspace Protection

- gate 前必须检查 git status
- dirty workspace 必须停止（包括 dirty_expected）
- 不允许覆盖已有未提交改动
- 恢复方式：git stash 或 separate commit

### Allowed After Approval (6)

enter dry-run, generate apply decision, preview target files, preview patch impact, prepare report, stop before real apply

### Forbidden After Approval (10)

real patch apply, command execution, git commit/push, auto-continue, run-project-task-full, Claude Code tool-use write, business code modification, Stage 8, bypass safety gate

### Gate Output Format

- Pass: 11 fields including CONTROLLED_APPLY_GATE_STATUS=pass
- Fail: 11 fields + REJECTION_REASON + NEXT_ACTION

## Safety Rules

| Check | Result |
|-------|--------|
| no real patch apply | yes |
| no command execution | yes |
| no run-project-task-full call | yes |
| no Claude Code call | yes |
| no business code modification | yes |
| no real task execution | yes |
| no auto-continue | yes |
| no auto Git backup | yes |
| human review required | yes |
| no code implementation | yes |

## Decision

```text
HUMAN_REVIEWED_CONTROLLED_APPLY_GATE=designed
READY_FOR_CONTROLLED_APPLY_APPROVAL_MODEL_DRY_RUN=yes
READY_FOR_REAL_APPLY=no
READY_FOR_STAGE_8=no
HUMAN_REVIEW_REQUIRED=yes
```

## Next

T124：实现 controlled apply approval model dry-run
