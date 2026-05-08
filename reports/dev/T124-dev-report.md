# T124 Dev Report

## Task

实现 controlled apply approval model dry-run。

## Scope

本轮只实现 approval model dry-run，不真实 apply patch，不执行 command，不真实执行任务。

## Background

T123 设计了 human-reviewed controlled apply gate，定义了 approval token (`APPROVE_CONTROLLED_APPLY_DRY_RUN`)、12 个前置条件、17 个拒绝条件、dirty workspace 保护、6 个 allowed actions、10 个 forbidden actions、gate output format 和 T124 boundary。

T124 在 T123 设计基础上实现 approval model dry-run。

## Changed Files

| File | Change Type | Description |
|------|-------------|-------------|
| tools/continuous_task_planner.py | modified | 新增 ControlledApplyApprovalDryRunResult、run_controlled_apply_approval_model_dry_run()、run_controlled_apply_approval_model_sample_dry_run() |
| runner.py | modified | 新增 controlled-apply-approval-dry-run CLI 入口 |
| reports/checks/T124-controlled-apply-approval-model-dry-run-check.md | new | 10 个场景验证报告 |
| reports/dev/T124-dev-report.md | new | This file |
| docs/tasks.md | modified | T124 status update |
| memory/lessons.md | modified | T124 lesson |
| memory/pitfalls.md | modified | T124 pitfall |

## Implementation

### ControlledApplyApprovalDryRunResult

33 个字段的数据结构，包含：
- 模式标识 (approval_mode)
- Token 检查 (approval_token_expected, approval_token_provided, approval_token_present, approval_token_valid)
- 前置条件检查 (worktree, pipeline, human_review, ready_for_real_apply, auto_continue, auto_git_backup)
- 安全保证字段 (real_patch_applied, command_execution_performed, real_task_execution 等，始终为 no)
- Gate 结果 (ready_for_controlled_apply_dry_run, ready_for_real_apply_after_approval, rejection_reasons, check_result)

### run_controlled_apply_approval_model_dry_run()

接受参数化输入的 approval model dry-run 函数：
- 检查 approval_token 是否存在和完全匹配 `APPROVE_CONTROLLED_APPLY_DRY_RUN`
- 检查 worktree_status == "clean"
- 检查 previous_pipeline_status == "ready_for_human_review" 且 previous_pipeline_check_result == "pass"
- 检查 human_review_required == "yes"
- 检查 ready_for_real_apply == "no"
- 检查 auto_continue_to_next_task == "no"
- 检查 auto_git_backup == "no"
- 汇总 rejection_reasons，全部通过时 READY_FOR_CONTROLLED_APPLY_DRY_RUN=yes

### run_controlled_apply_approval_model_sample_dry_run()

内置 10 个样本：pass + 9 个 fail 样本。

### runner.py controlled-apply-approval-dry-run CLI

支持两种调用方式：
- `--sample <name>`: 使用内置样本
- `--approval-token <token>`: 使用自定义 token（模拟 clean pipeline pass）

## Behavior

### Approval token 如何校验

Token 必须完全匹配 `APPROVE_CONTROLLED_APPLY_DRY_RUN`（case sensitive, exact match）。None 或空字符串标记为 missing_approval_token，非匹配值标记为 invalid_approval_token。

### Worktree 如何校验

函数只根据传入的 worktree_status 参数判断，不检查真实 git status。传入 "dirty" 时标记为 dirty_worktree 并 fail。

### Previous pipeline 如何校验

previous_pipeline_status 必须为 "ready_for_human_review" 且 previous_pipeline_check_result 必须为 "pass"。两者任一不满足都 fail。

### Human review 如何校验

human_review_required 必须为 "yes"。为 "no" 时标记为 human_review_not_required 并 fail。

### Ready for real apply 为什么必须 no

approval model dry-run 只允许进入 controlled apply dry-run，不等于真实 apply。ready_for_real_apply=yes 是异常状态，必须拦截。

### Auto continue / auto git backup 如何拒绝

auto_continue_to_next_task 和 auto_git_backup 必须为 "no"。任何 "yes" 值都触发对应 rejection。

### 为什么 approval 只允许 controlled apply dry-run

approval token 只授予 controlled apply dry-run 准备状态，不授予真实执行、commit、push 或 Stage 8 权限。

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

## Verification

10 个 sample 全部验证通过：

| Sample | CHECK_RESULT | REJECTION_REASONS |
|--------|-------------|-------------------|
| pass | pass | NONE |
| missing-token | fail | missing_approval_token |
| wrong-token | fail | invalid_approval_token |
| dirty-worktree | fail | dirty_worktree |
| pipeline-not-ready | fail | previous_pipeline_not_ready_for_human_review |
| pipeline-failed | fail | previous_pipeline_check_failed |
| human-review-missing | fail | human_review_not_required |
| ready-for-real-apply-unexpected | fail | ready_for_real_apply_unexpected |
| auto-continue-requested | fail | auto_continue_requested |
| auto-git-backup-requested | fail | auto_git_backup_requested |

所有 10 个场景安全字段均为安全值：
- REAL_PATCH_APPLIED=no (10/10)
- COMMAND_EXECUTION_PERFORMED=no (10/10)
- REAL_TASK_EXECUTION=no (10/10)
- READY_FOR_REAL_APPLY_AFTER_APPROVAL=no (10/10)

## Decision

```text
CONTROLLED_APPLY_APPROVAL_MODEL_DRY_RUN=implemented
READY_FOR_COMMAND_ALLOWLIST_VALIDATION_DRY_RUN=yes
READY_FOR_REAL_APPLY=no
READY_FOR_STAGE_8=no
```

## Next

T125：实现 command allowlist validation dry-run
