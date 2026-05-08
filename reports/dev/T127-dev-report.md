# T127 Dev Report

## Task

验证 first human-reviewed controlled apply dry-run pass/fail 场景。

## Scope

本轮只做验证，不实现新功能，不真实执行任务。

## Background

T126 first human-reviewed controlled apply dry-run 已实现，9/9 内置样本验证通过。T127 独立验证 T126 的 pass/fail 场景稳定性，确认 pipeline 在 pass 和各类 fail 场景下行为正确且 fail closed。

## Changed Files

| File | Change Type | Description |
|------|-------------|-------------|
| docs/tasks.md | modified | T127 status: pending → in_progress → done |
| reports/checks/T127-first-human-reviewed-controlled-apply-pass-fail-check.md | new | 9 个场景验证报告 |
| reports/dev/T127-dev-report.md | new | This file |
| memory/lessons.md | modified | T127 lesson |
| memory/pitfalls.md | modified | T127 pitfall |

## Verification

9 个 sample 全部验证通过：

| Sample | CHECK_RESULT | CONTROLLED_APPLY_DRY_RUN_STATUS | Fail Layer |
|--------|-------------|-------------------------------|------------|
| pass | pass | ready_for_human_review | — |
| missing-approval | fail | failed_approval | approval |
| wrong-approval | fail | failed_approval | approval |
| pipeline-fail | fail | failed_pipeline | pipeline |
| command-unsafe | fail | failed_command_allowlist | command allowlist |
| auto-continue-requested | fail | failed_pipeline | pipeline |
| auto-git-backup-requested | fail | failed_pipeline | pipeline |
| ready-for-real-apply-unexpected | fail | failed_pipeline | pipeline |
| dirty-worktree | fail | failed_approval | approval |

验证结果与 T126 一致：
- pass 场景: READY_FOR_CONTROLLED_APPLY_DRY_RUN=yes
- 8 个 fail 场景: 全部 fail closed
- 所有场景 READY_FOR_REAL_APPLY=no
- 所有场景 READY_FOR_STAGE_8=no

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
| no Stage 8 continuation | yes |
| human review required | yes |

## Result

pass/fail 场景完全符合预期：
- 1 个 pass 场景正确到达 ready_for_human_review
- 8 个 fail 场景全部 fail closed
- 3 个 fail 层次全部覆盖: pipeline (4)、approval (3)、command allowlist (1)
- 安全字段全部为安全值
- 无副作用

## Decision

```text
FIRST_HUMAN_REVIEWED_CONTROLLED_APPLY_PASS_FAIL_VALIDATION=pass
READY_FOR_T128=yes
READY_FOR_REAL_APPLY=no
READY_FOR_STAGE_8=no
```

## Next

T128：归档 Stage 7 human-reviewed controlled apply dry-run 成果
