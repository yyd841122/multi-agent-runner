# Human-Reviewed Controlled Apply Gate Design

## Background

T114 Layer 2 tool-use validation timeout (0/3 pass)。Claude Code tool-use 在智谱代理环境下不可靠：
text-only 6/6 pass，但 acceptEdits + tool-use 0/3 pass（120s+ timeout）。

Stage 7 没有暂停或跳过，而是改走 no-tool-use safe execution fallback strategy：
Claude Code / 国内模型只输出 text-only structured proposal，runner 负责解析、校验、应用、测试、报告。

T117-T121 已形成 complete dry-run safety chain：

```text
structured proposal → parser (7/7) → validator (9/9) → patch apply (9/9) → pipeline (8/8) → pass/fail (8/8)
```

Total: 41/41 scenarios validated。所有安全字段在所有场景中均为安全值。

T122 归档确认：

```text
READY_FOR_DIRECT_TOOL_USE_REAL_EXECUTION=no
READY_FOR_AUTOMATIC_REAL_EXECUTION=no
READY_FOR_HUMAN_REVIEWED_CONTROLLED_APPLY_DRY_RUN=yes
READY_FOR_STAGE_8_CONTINUOUS_REAL_EXECUTION=no
```

## Problem

当前问题：

1. **parser / validator / patch dry-run 已完成**：T117-T121 三层校验链路已验证，41/41 dry-run scenarios 通过
2. **pass/fail validation 已完成**：1 个 pass scenario 正确到达 `ready_for_human_review`，7 个 fail scenarios 全部 fail-closed
3. **但还没有人工确认安全门**：`ready_for_human_review` 只代表 dry-run pipeline 校验通过等待人工审查，不等于允许进入 controlled apply
4. **不能把 `ready_for_human_review` 误当成 `ready_for_real_execution`**：dry-run 验证的是解析和校验逻辑，不等于真实 apply 的安全性
5. **缺少从 dry-run 到 controlled apply 之间的人工审查和确认机制**：需要一个明确的 gate，只有满足所有前置条件并且用户明确确认后才允许进入 controlled apply dry-run

## Decision

```text
Stage 7 continues.
No direct tool-use real execution.
No automatic real execution.
Controlled apply must require explicit human review.
Human approval gate must exist before any future apply step.
```

核心决策：

- dry-run pipeline 通过只是进入 human review 的前提，不是进入 controlled apply 的充分条件
- 用户必须显式提供 approval token 才允许进入 controlled apply approval model dry-run
- approval token 不等于真实 apply 许可，只允许进入下一步 dry-run
- 真实 apply 需要单独的、更高级别的确认（后续 T125+ 任务）

## Gate Purpose

Human-reviewed controlled apply gate 的作用：

1. **确认 proposal 已通过 parser**：PARSE_STATUS=parsed，无解析错误
2. **确认 proposal 已通过 allowed scope validator**：VALIDATION_STATUS=validated，无 scope/safety 违规
3. **确认 proposal 已通过 patch apply dry-run**：PATCH_DRY_RUN_STATUS=ready_for_future_apply，patch 格式正确
4. **确认 pass/fail 场景验证已完成**：PIPELINE_STATUS=ready_for_human_review，dry-run pipeline 全部通过
5. **确认用户明确允许进入下一步 controlled apply dry-run**：用户提供 approval token
6. **阻止自动进入真实执行**：READY_FOR_REAL_EXECUTION 始终为 no
7. **阻止跳过任何校验层**：gate 检查所有前置层状态，不能跳过 parser、validator 或 patch dry-run

## Required Preconditions

进入 controlled apply gate 前必须满足的前置条件：

| # | Condition | Check | Failure Action |
|---|-----------|-------|----------------|
| 1 | worktree clean | `git status --short` 无输出 | stop and report |
| 2 | single task selected | 当前只有一个任务在执行 | stop and report |
| 3 | proposal parsed successfully | PARSE_STATUS=parsed | stop and report |
| 4 | scope validation passed | VALIDATION_STATUS=validated | stop and report |
| 5 | patch dry-run passed | PATCH_DRY_RUN_STATUS=ready_for_future_apply | stop and report |
| 6 | pass/fail validation completed | PIPELINE_STATUS=ready_for_human_review | stop and report |
| 7 | no business code changed unexpectedly | BUSINESS_CODE_CHANGED=no | stop and report |
| 8 | no command execution requested | COMMAND_EXECUTION_PERFORMED=no | stop and report |
| 9 | no auto-continue requested | AUTO_CONTINUE_TO_NEXT_TASK=no | stop and report |
| 10 | no auto-git-backup requested | AUTO_GIT_BACKUP=no | stop and report |
| 11 | human review required | HUMAN_REVIEW_REQUIRED=yes | stop and report |
| 12 | ready_for_real_execution is no | READY_FOR_REAL_EXECUTION=no | stop and report |

12 项前置条件全部通过后，gate 才进入 approval token 检查阶段。

## Human Approval Token

### Token Definition

```
APPROVE_CONTROLLED_APPLY_DRY_RUN
```

### Token Rules

| Rule | Description |
|------|-------------|
| exact match | token 必须完全等于 `APPROVE_CONTROLLED_APPLY_DRY_RUN`，不接受任何变体 |
| case sensitive | token 区分大小写，`approve_controlled_apply_dry_run` 不合法 |
| single use per gate | 每次 gate 通过只允许一次 controlled apply dry-run，不缓存 |
| no partial match | 不接受前缀、后缀或包含匹配 |

### Token Permissions

Token 只允许：

| Permission | Scope |
|------------|-------|
| enter controlled apply approval model dry-run | T124 |
| generate apply decision | dry-run only |
| preview target files | read-only |
| preview patch impact | dry-run only |
| prepare human-reviewed apply report | report generation |

### Token Restrictions

Token 不允许：

| Restriction | Reason |
|-------------|--------|
| real commit | Git operations 需要 separate approval |
| push | push 需要 separate human confirmation |
| enter Stage 8 | Stage 8 continuous execution 是独立阶段 |
| skip validator | T118 scope validation 是必要校验层 |
| skip patch dry-run | T119 patch format check 是必要校验层 |
| real patch apply | approval token 只允许 dry-run，真实 apply 需要更高级别确认 |
| real command execution | 命令执行需要单独 allowlist 和 approval |

## Allowed After Approval

Approval 通过后只允许以下操作：

| # | Action | Scope |
|---|--------|-------|
| 1 | enter controlled apply approval model dry-run | T124 implementation |
| 2 | generate apply decision | dry-run output only |
| 3 | preview target files | read file contents |
| 4 | preview patch impact | compute diff preview |
| 5 | prepare human-reviewed apply report | generate report file |
| 6 | stop before real apply | unless future task explicitly allows |

所有操作仍然是 dry-run 性质。Approval 不授予任何真实执行权限。

## Forbidden Even After Approval

以下操作即使 approval 通过后仍然禁止：

| # | Forbidden Action | Reason |
|---|-----------------|--------|
| 1 | automatic real patch apply | 需要 separate real-apply approval |
| 2 | automatic command execution | 需要 command allowlist + separate approval |
| 3 | automatic git commit | Git operations 需要 dedicated step |
| 4 | automatic git push | push 需要 human confirmation |
| 5 | automatic next task continuation | AUTO_CONTINUE_TO_NEXT_TASK=no 是硬约束 |
| 6 | run-project-task-full real call | 真实任务调用是 Stage 8+ 范围 |
| 7 | Claude Code tool-use write | tool-use 不稳定，不用于文件修改 |
| 8 | business code modification without separate explicit approval | 所有真实修改需要更高级别确认 |
| 9 | Stage 8 continuous execution | Stage 8 是独立阶段，不能通过 gate 跳过 |
| 10 | bypass any safety gate | 安全校验不可绕过 |

## Rejection Conditions

以下任何条件触发时，gate 必须拒绝：

| # | Condition | Check Method | Severity |
|---|-----------|-------------|----------|
| 1 | dirty workspace | `git status --short` 有输出 | hard reject |
| 2 | missing approval token | token 为空 | hard reject |
| 3 | wrong approval token | token 不等于 `APPROVE_CONTROLLED_APPLY_DRY_RUN` | hard reject |
| 4 | proposal parse failed | PARSE_STATUS != parsed | hard reject |
| 5 | scope validation failed | VALIDATION_STATUS != validated | hard reject |
| 6 | patch dry-run failed | PATCH_DRY_RUN_STATUS != ready_for_future_apply | hard reject |
| 7 | pipeline not ready for human review | PIPELINE_STATUS != ready_for_human_review | hard reject |
| 8 | target file outside allowed scope | file not in allowed_files | hard reject |
| 9 | forbidden file touched | file in forbidden_files | hard reject |
| 10 | path traversal detected | ".." in file paths | hard reject |
| 11 | absolute path detected | path starts with "/" or contains ":" | hard reject |
| 12 | auto_continue requested | AUTO_CONTINUE_TO_NEXT_TASK=yes | hard reject |
| 13 | auto_git_backup requested | AUTO_GIT_BACKUP=yes | hard reject |
| 14 | command execution requested | COMMAND_EXECUTION_PERFORMED=yes | hard reject |
| 15 | ready_for_real_execution=yes | READY_FOR_REAL_EXECUTION=yes appears unexpectedly | hard reject |
| 16 | human_review_required=no | HUMAN_REVIEW_REQUIRED != yes | hard reject |
| 17 | business_code_changed unexpectedly | BUSINESS_CODE_CHANGED != no | hard reject |

所有 rejection 都必须包含明确的 rejection reason 和建议的 next action。

## Dirty Workspace Protection

### 原则

1. **apply gate 前必须检查 git status**
2. **dirty workspace 必须停止**
3. **未分类变更必须停止**
4. **不允许覆盖已有未提交改动**
5. **不允许在 dirty 状态下进入 controlled apply**

### 检查流程

```text
git status --short
  ↓
有输出？
  ├─ no → workspace clean, continue
  └─ yes → 分类变更
       ├─ dirty_expected (只有 reports/ docs/ memory/ 变更) → still reject (需要先 commit 或 stash)
       ├─ dirty_business_code (有 .py .js .html .css 变更) → hard reject
       └─ dirty_unexpected (有未知文件) → hard reject
```

### 为什么 dirty_expected 也拒绝

即使变更都在预期路径（reports/、docs/、memory/），仍然拒绝进入 controlled apply，原因：

1. **controlled apply 需要干净的工作区来准确检测 apply 后的变更**
2. **已有未提交变更可能与 apply 产生冲突**
3. **保持 apply 前后 diff 的唯一性**

### 恢复方式

```text
dirty workspace → human decides:
  ├─ git stash → 进入 gate → gate pass → git stash pop → review
  └─ git commit (separate commit) → 进入 gate → gate pass → review
```

## Gate Output Format

### Gate Pass Output

```text
CONTROLLED_APPLY_GATE_STATUS=pass
HUMAN_APPROVAL_TOKEN_PRESENT=yes
HUMAN_APPROVAL_TOKEN_VALID=yes
READY_FOR_CONTROLLED_APPLY_DRY_RUN=yes
READY_FOR_REAL_APPLY=no
REAL_PATCH_APPLIED=no
COMMAND_EXECUTION_PERFORMED=no
AUTO_CONTINUE_TO_NEXT_TASK=no
AUTO_GIT_BACKUP=no
HUMAN_REVIEW_REQUIRED=yes
CHECK_RESULT=pass
NEXT_TASK=T124
```

### Gate Fail Output

```text
CONTROLLED_APPLY_GATE_STATUS=fail
HUMAN_APPROVAL_TOKEN_PRESENT=<yes/no>
HUMAN_APPROVAL_TOKEN_VALID=<yes/no>
READY_FOR_CONTROLLED_APPLY_DRY_RUN=no
READY_FOR_REAL_APPLY=no
REAL_PATCH_APPLIED=no
COMMAND_EXECUTION_PERFORMED=no
AUTO_CONTINUE_TO_NEXT_TASK=no
AUTO_GIT_BACKUP=no
HUMAN_REVIEW_REQUIRED=yes
CHECK_RESULT=fail
REJECTION_REASON=<具体拒绝原因>
NEXT_ACTION=<建议的下一步操作>
```

### Field Definitions

| Field | Type | Values | Description |
|-------|------|--------|-------------|
| CONTROLLED_APPLY_GATE_STATUS | string | pass / fail | Gate 整体状态 |
| HUMAN_APPROVAL_TOKEN_PRESENT | string | yes / no | 是否提供了 approval token |
| HUMAN_APPROVAL_TOKEN_VALID | string | yes / no / not_applicable | token 是否有效（未提供时为 not_applicable） |
| READY_FOR_CONTROLLED_APPLY_DRY_RUN | string | yes / no | 是否可以进入 T124 |
| READY_FOR_REAL_APPLY | string | no | 始终为 no |
| REAL_PATCH_APPLIED | string | no | 始终为 no（gate 不 apply） |
| COMMAND_EXECUTION_PERFORMED | string | no | 始终为 no（gate 不执行命令） |
| AUTO_CONTINUE_TO_NEXT_TASK | string | no | 始终为 no |
| AUTO_GIT_BACKUP | string | no | 始终为 no |
| HUMAN_REVIEW_REQUIRED | string | yes | 始终为 yes |
| CHECK_RESULT | string | pass / fail | 综合检查结果 |
| REJECTION_REASON | string | (fail only) | 拒绝的具体原因 |
| NEXT_ACTION | string | (fail only) | 建议的下一步操作 |

## Relationship to T124

### T123 与 T124 的边界

| | T123 (本轮) | T124 (下一步) |
|---|---|---|
| 性质 | gate 设计 | approval model dry-run 实现 |
| 产出 | 设计文档 | 代码实现 |
| 是否实现代码 | 否 | 是 |
| 是否执行 apply | 否 | dry-run only |
| 是否需要 approval token | 设计 token 规则 | 实现并验证 token |
| 是否修改 pipeline | 否 | 在 pipeline 基础上扩展 |

### T124 应实现的内容

1. controlled apply approval model dry-run
2. approval token 验证逻辑
3. gate 前置条件检查逻辑
4. gate output 格式生成
5. dry-run apply preview（不真实 apply）
6. controlled apply dry-run report 生成

### T123 不实现的内容

1. 不实现代码
2. 不修改 T117-T121 pipeline 逻辑
3. 不真实 apply patch
4. 不执行 command
5. 不调用 Claude Code
6. 不修改业务代码

## Decision Summary

```text
HUMAN_REVIEWED_CONTROLLED_APPLY_GATE=designed
READY_FOR_CONTROLLED_APPLY_APPROVAL_MODEL_DRY_RUN=yes
READY_FOR_REAL_APPLY=no
READY_FOR_STAGE_8=no
HUMAN_REVIEW_REQUIRED=yes
```

### 安全保证

| Check | Status |
|-------|--------|
| no real patch applied | guaranteed |
| no command execution | guaranteed |
| no Claude Code call | guaranteed |
| no run-project-task-full call | guaranteed |
| no business code modification | guaranteed |
| no auto-continue | guaranteed |
| no auto Git backup | guaranteed |
| no bypass permissions | guaranteed |
| human review required | guaranteed |
| approval token required for controlled apply | designed |
| dirty workspace blocks gate | designed |
| fail-closed on any precondition failure | designed |
