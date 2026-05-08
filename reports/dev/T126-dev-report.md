# T126 Dev Report

## Task

执行 first human-reviewed controlled apply dry-run。

## Scope

本轮只实现完整 human-reviewed controlled apply dry-run，不真实 apply patch，不执行 command，不真实执行任务。

## Background

T123 设计了 human-reviewed controlled apply gate，定义了 approval token、前置条件和拒绝条件。T124 实现了 approval model dry-run，10/10 scenarios 验证通过。T125 实现了 command allowlist validation dry-run，15/15 scenarios 验证通过。T126 将三层组合成 first human-reviewed controlled apply dry-run。

## Changed Files

| File | Change Type | Description |
|------|-------------|-------------|
| tools/continuous_task_planner.py | modified | 新增 FirstHumanReviewedControlledApplyDryRunResult、run_first_human_reviewed_controlled_apply_dry_run()、run_first_human_reviewed_controlled_apply_sample_dry_run()、_run_dirty_worktree_sample() |
| runner.py | modified | 新增 first-human-reviewed-controlled-apply-dry-run CLI 入口 |
| reports/checks/T126-first-human-reviewed-controlled-apply-dry-run-check.md | new | 9 个场景验证报告 |
| reports/dev/T126-dev-report.md | new | This file |
| docs/tasks.md | modified | T126 status update |
| memory/lessons.md | modified | T126 lesson |
| memory/pitfalls.md | modified | T126 pitfall |

## Implementation

### FirstHumanReviewedControlledApplyDryRunResult

33 个字段的数据结构，包含：
- 模式标识 (execution_mode)
- Approval 检查 (approval_token_expected/provided, approval_check_result, approval_ready_for_controlled_apply_dry_run)
- Command allowlist 检查 (command_allowlist_check_result, command_execution_blocked)
- Pipeline 阶段结果 (proposal_parse_status/check_result, scope_validation_status/check_result, patch_dry_run_status/check_result)
- 综合状态 (controlled_apply_dry_run_status: ready_for_human_review / failed_approval / failed_command_allowlist / failed_pipeline)
- 文件/命令信息 (target_files, patch_files, commands_total/allowed/rejected)
- 安全保证字段（全部始终为安全值：real_patch_applied=no, command_execution_performed=no, ready_for_real_apply=no, ready_for_stage_8=no 等）
- Gate 结果 (ready_for_controlled_apply_dry_run, ready_for_real_apply, ready_for_stage_8)
- 失败详情 (stop_reason, violations)
- 最终结果 (check_result, message)

### run_first_human_reviewed_controlled_apply_dry_run()

串联三层：
1. run_first_no_tool_use_single_task_dry_run() — T120 pipeline（parser → validator → patch dry-run）
2. run_controlled_apply_approval_model_dry_run() — T124 approval model
3. run_command_allowlist_validation_dry_run() — T125 command allowlist

判定原则：
- pipeline fail → controlled_apply_dry_run_status=failed_pipeline, check_result=fail
- approval fail → controlled_apply_dry_run_status=failed_approval, check_result=fail
- command allowlist fail → controlled_apply_dry_run_status=failed_command_allowlist, check_result=fail
- 全部 pass → controlled_apply_dry_run_status=ready_for_human_review, check_result=pass

### run_first_human_reviewed_controlled_apply_sample_dry_run()

内置 9 个样本：pass + 8 个 fail 样本。

### runner.py first-human-reviewed-controlled-apply-dry-run CLI

支持两种调用方式：
- `--sample <name>`: 使用内置样本
- `--approval-token <token>`: 使用自定义 token
- 默认：pass sample

## Pipeline

```text
proposal text
  ↓
T117 parse → T118 validate → T119 patch dry-run
  ↓
pipeline result (pass/fail)
  ↓
T124 approval model (token + worktree + preconditions)
  ↓
approval result (pass/fail)
  ↓
T125 command allowlist (string-level classification)
  ↓
controlled apply dry-run decision
  ↓
human review required
```

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

## Verification

9 个 sample 全部验证通过：

| Sample | CHECK_RESULT | CONTROLLED_APPLY_DRY_RUN_STATUS |
|--------|-------------|-------------------------------|
| pass | pass | ready_for_human_review |
| missing-approval | fail | failed_approval |
| wrong-approval | fail | failed_approval |
| pipeline-fail | fail | failed_pipeline |
| command-unsafe | fail | failed_command_allowlist |
| auto-continue-requested | fail | failed_pipeline |
| auto-git-backup-requested | fail | failed_pipeline |
| ready-for-real-apply-unexpected | fail | failed_pipeline |
| dirty-worktree | fail | failed_approval |

所有 9 个场景安全字段均为安全值：
- REAL_PATCH_APPLIED=no (9/9)
- COMMAND_EXECUTION_PERFORMED=no (9/9)
- REAL_TASK_EXECUTION=no (9/9)
- RUN_PROJECT_TASK_FULL_CALLED=no (9/9)
- CLAUDE_CODE_CALLED=no (9/9)
- BUSINESS_CODE_CHANGED=no (9/9)
- READY_FOR_REAL_APPLY=no (9/9)
- READY_FOR_STAGE_8=no (9/9)

## Decision

```text
FIRST_HUMAN_REVIEWED_CONTROLLED_APPLY_DRY_RUN=implemented
READY_FOR_T127=yes
READY_FOR_REAL_APPLY=no
READY_FOR_STAGE_8=no
```

## Next

T127：验证 first human-reviewed controlled apply dry-run pass/fail 场景
