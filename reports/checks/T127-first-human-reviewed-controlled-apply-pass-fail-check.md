# T127 First Human-Reviewed Controlled Apply Pass/Fail Check

## Task

验证 first human-reviewed controlled apply dry-run pass/fail 场景。

## Scope

本轮只验证 T126 dry-run pipeline，不真实 apply patch，不执行 command，不真实执行任务。

## Background

T123 设计了 human-reviewed controlled apply gate，定义了 approval token、前置条件和拒绝条件。T124 实现了 approval model dry-run，10/10 scenarios 验证通过。T125 实现了 command allowlist validation dry-run，15/15 scenarios 验证通过。T126 将三层组合成 first human-reviewed controlled apply dry-run，9/9 scenarios 验证通过。T127 独立验证 T126 的 pass/fail 场景稳定性。

## Scenarios

### 1. pass

- Command: `python runner.py first-human-reviewed-controlled-apply-dry-run --sample pass`
- Expected: CHECK_RESULT=pass, CONTROLLED_APPLY_DRY_RUN_STATUS=ready_for_human_review
- Actual: CHECK_RESULT=pass, CONTROLLED_APPLY_DRY_RUN_STATUS=ready_for_human_review
- APPROVAL_CHECK_RESULT=pass, COMMAND_ALLOWLIST_CHECK_RESULT=pass
- PROPOSAL_PARSE_CHECK_RESULT=pass, SCOPE_VALIDATION_CHECK_RESULT=pass, PATCH_DRY_RUN_CHECK_RESULT=pass
- READY_FOR_CONTROLLED_APPLY_DRY_RUN=yes
- **PASS**

### 2. missing-approval

- Command: `python runner.py first-human-reviewed-controlled-apply-dry-run --sample missing-approval`
- Expected: CHECK_RESULT=fail, CONTROLLED_APPLY_DRY_RUN_STATUS=failed_approval
- Actual: CHECK_RESULT=fail, CONTROLLED_APPLY_DRY_RUN_STATUS=failed_approval
- APPROVAL_CHECK_RESULT=fail, COMMAND_ALLOWLIST_CHECK_RESULT=not_evaluated
- Stop reason: missing_approval_token
- **PASS**

### 3. wrong-approval

- Command: `python runner.py first-human-reviewed-controlled-apply-dry-run --sample wrong-approval`
- Expected: CHECK_RESULT=fail, CONTROLLED_APPLY_DRY_RUN_STATUS=failed_approval
- Actual: CHECK_RESULT=fail, CONTROLLED_APPLY_DRY_RUN_STATUS=failed_approval
- APPROVAL_CHECK_RESULT=fail, COMMAND_ALLOWLIST_CHECK_RESULT=not_evaluated
- Stop reason: invalid_approval_token
- **PASS**

### 4. pipeline-fail

- Command: `python runner.py first-human-reviewed-controlled-apply-dry-run --sample pipeline-fail`
- Expected: CHECK_RESULT=fail, CONTROLLED_APPLY_DRY_RUN_STATUS=failed_pipeline
- Actual: CHECK_RESULT=fail, CONTROLLED_APPLY_DRY_RUN_STATUS=failed_pipeline
- PROPOSAL_PARSE_CHECK_RESULT=fail, SCOPE_VALIDATION_CHECK_RESULT=fail, PATCH_DRY_RUN_CHECK_RESULT=fail
- Pipeline fails: unsafe-scope sample violates scope constraints
- **PASS**

### 5. command-unsafe

- Command: `python runner.py first-human-reviewed-controlled-apply-dry-run --sample command-unsafe`
- Expected: CHECK_RESULT=fail, CONTROLLED_APPLY_DRY_RUN_STATUS=failed_command_allowlist
- Actual: CHECK_RESULT=fail, CONTROLLED_APPLY_DRY_RUN_STATUS=failed_command_allowlist
- APPROVAL_CHECK_RESULT=pass, COMMAND_ALLOWLIST_CHECK_RESULT=fail
- COMMANDS_REJECTED=1 (git add blocked)
- **PASS**

### 6. auto-continue-requested

- Command: `python runner.py first-human-reviewed-controlled-apply-dry-run --sample auto-continue-requested`
- Expected: CHECK_RESULT=fail, CONTROLLED_APPLY_DRY_RUN_STATUS=failed_pipeline
- Actual: CHECK_RESULT=fail, CONTROLLED_APPLY_DRY_RUN_STATUS=failed_pipeline
- Pipeline fails: auto-continue proposal violates safety constraints
- **PASS**

### 7. auto-git-backup-requested

- Command: `python runner.py first-human-reviewed-controlled-apply-dry-run --sample auto-git-backup-requested`
- Expected: CHECK_RESULT=fail, CONTROLLED_APPLY_DRY_RUN_STATUS=failed_pipeline
- Actual: CHECK_RESULT=fail, CONTROLLED_APPLY_DRY_RUN_STATUS=failed_pipeline
- Pipeline fails: auto-git-backup proposal violates safety constraints
- **PASS**

### 8. ready-for-real-apply-unexpected

- Command: `python runner.py first-human-reviewed-controlled-apply-dry-run --sample ready-for-real-apply-unexpected`
- Expected: CHECK_RESULT=fail, CONTROLLED_APPLY_DRY_RUN_STATUS=failed_pipeline
- Actual: CHECK_RESULT=fail, CONTROLLED_APPLY_DRY_RUN_STATUS=failed_pipeline
- Pipeline fails: ready_for_real_apply proposal violates safety constraints
- **PASS**

### 9. dirty-worktree

- Command: `python runner.py first-human-reviewed-controlled-apply-dry-run --sample dirty-worktree`
- Expected: CHECK_RESULT=fail, CONTROLLED_APPLY_DRY_RUN_STATUS=failed_approval
- Actual: CHECK_RESULT=fail, CONTROLLED_APPLY_DRY_RUN_STATUS=failed_approval
- Approval model rejects dirty worktree, pipeline passes
- Stop reason: dirty_worktree
- **PASS**

## Summary

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

9/9 PASS.

## Expected Results

- pass 场景: CHECK_RESULT=pass, READY_FOR_CONTROLLED_APPLY_DRY_RUN=yes
- 其他 8 个场景: CHECK_RESULT=fail, fail closed
- 所有 9 个场景 READY_FOR_REAL_APPLY=no
- 所有 9 个场景 READY_FOR_STAGE_8=no
- 所有 9 个场景不真实 apply patch
- 所有 9 个场景不执行 command
- 所有 9 个场景不调用 Claude Code
- 所有 9 个场景不调用 run-project-task-full
- 所有 9 个场景不修改业务代码

全部符合预期。

## Safety Verification

| Check | All 9 Scenarios |
|-------|-----------------|
| REAL_PATCH_APPLIED=no | yes (9/9) |
| COMMAND_EXECUTION_PERFORMED=no | yes (9/9) |
| REAL_TASK_EXECUTION=no | yes (9/9) |
| RUN_PROJECT_TASK_FULL_CALLED=no | yes (9/9) |
| CLAUDE_CODE_CALLED=no | yes (9/9) |
| BUSINESS_CODE_CHANGED=no | yes (9/9) |
| READY_FOR_REAL_APPLY=no | yes (9/9) |
| READY_FOR_STAGE_8=no | yes (9/9) |
| HUMAN_REVIEW_REQUIRED=yes | yes (9/9) |

## Side Effects

验证前后 git status 检查：
- 验证前: 只有 docs/tasks.md 被 T127 in_progress 更新修改
- 验证后: 无新增文件变化
- 业务代码: 无变化
- projects/down-100-floors-game/: 无变化
- 无真实 patch apply
- 无 command execution

## Decision

```text
FIRST_HUMAN_REVIEWED_CONTROLLED_APPLY_PASS_FAIL_VALIDATION=pass
READY_FOR_T128=yes
READY_FOR_REAL_APPLY=no
READY_FOR_STAGE_8=no
```

## Next

T128：归档 Stage 7 human-reviewed controlled apply dry-run 成果
