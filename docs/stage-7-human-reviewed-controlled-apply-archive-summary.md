# Stage 7 Human-Reviewed Controlled Apply Archive Summary

## Background

T114 Layer 2 tool-use validation timeout (0/3 pass)。Claude Code tool-use 在智谱代理环境下不可靠：text-only 6/6 pass，但 acceptEdits + tool-use 0/3 pass（120s+ timeout）。

Stage 7 转向 no-tool-use safe execution fallback strategy：Claude Code / 国内模型只输出 text-only structured proposal，runner 负责解析、校验、应用、测试、报告。

T117-T122 完成 no-tool-use dry-run 链路（已归档于 T122）。
T123-T127 完成 human-reviewed controlled apply dry-run 链路（本轮归档）。

## Completed Work

| Task | Title | Scenarios | Status |
|------|-------|-----------|--------|
| T123 | 设计 human-reviewed controlled apply gate | — (design only) | done |
| T124 | 实现 controlled apply approval model dry-run | 10/10 | done |
| T125 | 实现 command allowlist validation dry-run | 15/15 | done |
| T126 | 执行 first human-reviewed controlled apply dry-run | 9/9 | done |
| T127 | 验证 pass/fail 场景 | 9/9 | done |

### T123 Human-Reviewed Controlled Apply Gate Design

设计人工确认安全门，定义：

- Approval token: `APPROVE_CONTROLLED_APPLY_DRY_RUN`
- 12 个前置条件
- 17 个拒绝条件
- Dirty workspace 保护
- 6 个 allowed actions、10 个 forbidden actions
- Gate output format（pass/fail 各有明确字段）

### T124 Controlled Apply Approval Model Dry-Run

实现 approval model dry-run，包含：

- `ControlledApplyApprovalDryRunResult`：33 个字段的数据结构
- `run_controlled_apply_approval_model_dry_run()`：参数化 approval 检查
- `run_controlled_apply_approval_model_sample_dry_run()`：10 个内置样本
- CLI 入口：`python runner.py controlled-apply-approval-dry-run`

10/10 场景验证：1 pass + 9 fail (missing-token, wrong-token, dirty-worktree, pipeline-not-ready, pipeline-failed, human-review-missing, ready-for-real-apply-unexpected, auto-continue-requested, auto-git-backup-requested)

### T125 Command Allowlist Validation Dry-Run

实现 command allowlist validation dry-run，包含：

- `CommandAllowlistValidationDryRunResult`：25 个字段的数据结构
- `_classify_command()`：字符串级别命令分类（allowed/forbidden/unknown）
- `run_command_allowlist_validation_dry_run()`：参数化 command allowlist 检查
- CLI 入口：`python runner.py command-allowlist-dry-run`

允许类别：status (git status/log/diff/branch/remote/tag)、validation (python runner.py, uv run python runner.py, python -c, uv run python -c)、test (pytest, uv run pytest, python -m pytest, uv run python -m pytest)

禁止类别：git write、file destruction、shell chaining、network execution、dangerous、framework (run-project-task-full)、Claude Code tool-use (acceptEdits, bypassPermissions)

15/15 场景验证：3 pass + 12 fail

### T126 First Human-Reviewed Controlled Apply Dry-Run

将三层组合成完整 human-reviewed controlled apply dry-run，包含：

- `FirstHumanReviewedControlledApplyDryRunResult`：33 个字段的数据结构
- `run_first_human_reviewed_controlled_apply_dry_run()`：串联三层 pipeline
- `run_first_human_reviewed_controlled_apply_sample_dry_run()`：9 个内置样本
- CLI 入口：`python runner.py first-human-reviewed-controlled-apply-dry-run`

9/9 场景验证：1 pass + 8 fail (missing-approval, wrong-approval, pipeline-fail, command-unsafe, auto-continue-requested, auto-git-backup-requested, ready-for-real-apply-unexpected, dirty-worktree)

### T127 Pass/Fail Validation

独立验证 T126 的 9 个内置样本，确认：

- pass 场景正确到达 `ready_for_human_review`
- 8 个 fail 场景全部 fail closed
- 3 个 fail 层次全覆盖：pipeline (4)、approval (3)、command allowlist (1)
- 所有安全字段在所有场景中均为安全值
- 无副作用

## Implementation Chain

T117-T127 完整链路：

```text
structured proposal
  → T117 parser dry-run (7/7)
  → T118 allowed scope validator dry-run (9/9)
  → T119 controlled patch apply dry-run (9/9)
  → T120 first no-tool-use single-task dry-run (8/8)
  → T121 pass/fail validation (8/8)
  → T122 archive (no-tool-use chain archived)
  → T123 human-reviewed controlled apply gate design
  → T124 controlled apply approval model dry-run (10/10)
  → T125 command allowlist validation dry-run (15/15)
  → T126 first human-reviewed controlled apply dry-run (9/9)
  → T127 pass/fail validation (9/9)
  → T128 archive (human-reviewed controlled apply chain archived)
  → human review
```

Total scenarios validated: 7 + 9 + 9 + 8 + 8 + 10 + 15 + 9 + 9 = **84/84**

## Safety Guarantees

| # | Guarantee | Status |
|---|-----------|--------|
| 1 | no real patch apply | guaranteed |
| 2 | no command execution | guaranteed |
| 3 | no Claude Code call | guaranteed |
| 4 | no run-project-task-full call | guaranteed |
| 5 | no business code modification | guaranteed |
| 6 | no auto-continue | guaranteed |
| 7 | no auto Git backup | guaranteed |
| 8 | no bypass permissions | guaranteed |
| 9 | no Stage 8 continuation | guaranteed |
| 10 | human review required | guaranteed |

所有 84 个场景中，安全字段均为安全值。

## Validation Summary

| Task | Validation | Scenarios | Result |
|------|-----------|-----------|--------|
| T117 | proposal parser dry-run | 7/7 | pass |
| T118 | allowed scope validator dry-run | 9/9 | pass |
| T119 | controlled patch apply dry-run | 9/9 | pass |
| T120 | first no-tool-use single-task dry-run | 8/8 | pass |
| T121 | no-tool-use pass/fail validation | 8/8 | pass |
| T124 | approval model dry-run | 10/10 | pass |
| T125 | command allowlist validation dry-run | 15/15 | pass |
| T126 | human-reviewed controlled apply dry-run | 9/9 | pass |
| T127 | pass/fail validation | 9/9 | pass |

T117-T121 no-tool-use dry-run chain 已归档于 T122。

## Current Decision

```text
STAGE_7_HUMAN_REVIEWED_CONTROLLED_APPLY_DRY_RUN_CHAIN=validated
READY_FOR_DIRECT_TOOL_USE_REAL_EXECUTION=no
READY_FOR_AUTOMATIC_REAL_EXECUTION=no
READY_FOR_REAL_APPLY=no
READY_FOR_COMMAND_EXECUTION=no
READY_FOR_STAGE_8_CONTINUOUS_REAL_EXECUTION=no
READY_FOR_NEXT_STAGE_7_STEP=yes
HUMAN_REVIEW_REQUIRED=yes
```

## Remaining Gaps

在进入 real apply 之前，仍缺少以下安全门：

| # | Gap | Description |
|---|-----|-------------|
| 1 | no real patch apply | 仍没有真实 apply patch 能力 |
| 2 | no command execution | 仍没有真实 command 执行能力 |
| 3 | no real business task execution | 仍没有真实业务任务执行 |
| 4 | no automatic Git backup step | apply 后没有自动 Git 备份 |
| 5 | no real apply approval persistence | approval 没有持久化记录 |
| 6 | no post-apply validation | apply 后没有验证 step |
| 7 | no dirty workspace recovery | dirty workspace 后没有恢复机制 |
| 8 | no rework loop integration | 返工闭环未接入 |
| 9 | no rate-limit recovery implementation | 5 小时限额恢复未实现 |
| 10 | no checkpoint resume | 断点续做未实现 |

## Recommended Next Tasks

| Task | Title | Description |
|------|-------|-------------|
| T129 | 设计 real apply approval persistence and audit record | 设计 real apply 前的 approval 持久化和审计记录 |
| T130 | 实现 real apply approval record dry-run | 实现 approval record dry-run |
| T131 | 设计 post-apply validation gate | 设计 apply 后验证门 |
| T132 | 实现 first real patch apply guarded dry-run | 实现 guarded real patch apply dry-run |

注意：这些只是建议，不是实现。下一步仍属 Stage 7，不进入 Stage 8。

## Final Summary

```text
STAGE_7_HUMAN_REVIEWED_CONTROLLED_APPLY_ARCHIVE=complete
HUMAN_REVIEWED_CONTROLLED_APPLY_DRY_RUN_CHAIN=validated
READY_FOR_NEXT_STAGE_7_STEP=yes
READY_FOR_REAL_APPLY=no
READY_FOR_STAGE_8=no
HUMAN_REVIEW_REQUIRED=yes
```
