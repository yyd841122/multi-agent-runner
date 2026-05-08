# Real Apply Approval Persistence and Audit Record Design

## Background

T114 Layer 2 tool-use validation timeout (0/3 pass)。Claude Code tool-use 在智谱代理环境下不可靠。Stage 7 转向 no-tool-use safe execution fallback strategy。

T117-T122 完成 no-tool-use dry-run 链路（已归档于 T122）：
- parser (7/7) → validator (9/9) → patch dry-run (9/9) → pipeline (8/8) → pass/fail (8/8)

T123-T128 完成 human-reviewed controlled apply dry-run 链路（已归档于 T128）：
- gate design → approval model (10/10) → command allowlist (15/15) → controlled apply (9/9) → pass/fail (9/9)

Grand total: 84/84 scenarios validated。所有安全字段在所有场景中均为安全值。

当前仍不能 real apply。下一步需要 approval persistence and audit record，确保未来任何 real apply 决策都有持久化、可审计、可追溯的记录。

## Problem

当前问题：

1. **approval model dry-run 已验证 token 和前置条件检查逻辑**：但 approval decision 只在内存中生成，进程结束后消失
2. **command allowlist dry-run 已验证命令分类逻辑**：但 allowlist 判断结果没有持久化
3. **controlled apply dry-run 已验证 pass/fail 行为**：但 pass/fail 结果没有持久化
4. **没有可追溯的 approval evidence**：未来 real apply 时无法回顾"当时为什么批准了"
5. **没有 apply 前后审计快照**：无法确认 apply 是否只影响了预期文件
6. **没有 invalidation 机制**：如果 proposal 或 patch 在 approval 后被篡改，无法检测

不能在没有持久化 approval evidence 的情况下进入 real apply。

## Decision

```text
Stage 7 continues.
No real apply yet.
No command execution yet.
No automatic Git backup yet.
Before any future real apply, approval and audit records must be:
  1. Designed (T129, this task)
  2. Implemented as dry-run (T130, next task)
  3. Validated (T130 verification)
Only after approval persistence is verified can T131+ post-apply validation gate be designed.
```

## Approval Record Purpose

Approval record 的作用：

1. **记录谁批准了 controlled apply**：区分 human approval 和 automatic approval
2. **记录批准时间**：精确到秒的时间戳
3. **记录批准 token**：确认使用了正确的 approval token
4. **记录关联 task id**：批准是针对哪个任务
5. **记录关联 proposal summary**：被批准的 proposal 的关键信息摘要
6. **记录关联 patch files**：被批准的 patch 文件列表
7. **记录关联 validation results**：所有前置检查的结果
8. **记录当前仍不允许 automatic commit / push**：硬约束声明
9. **作为未来 real apply 的前置 evidence**：没有 approval record 不允许 real apply
10. **支持 invalidation**：approval 后如果 proposal/patch 变化，approval record 失效

## Approval Record Schema

```yaml
approval_record_version: "1.0"
approval_id: ""                    # 格式: APR-YYYYMMDD-HHMMSS-<6hex>
task_id: ""                        # 关联任务 ID
task_title: ""                     # 任务标题

# 批准信息
approval_mode: "human_reviewed_controlled_apply"
approval_token: "APPROVE_CONTROLLED_APPLY_DRY_RUN"
approved_by: "human"               # human / automatic_rejected
approved_at: ""                    # ISO 8601 timestamp

# 批准范围
approval_scope:
  allowed_files: []                # allowed_files from proposal
  target_files: []                 # target_files from proposal
  patch_files: []                  # patch files from proposal
  forbidden_files: []              # forbidden_files from proposal

# 前置检查证据
evidence:
  proposal_parse_check: "pass"     # T117 parser result
  scope_validation_check: "pass"   # T118 validator result
  patch_dry_run_check: "pass"      # T119 patch dry-run result
  pipeline_check: "pass"           # T120 pipeline result
  approval_model_check: "pass"     # T124 approval model result
  command_allowlist_check: "pass"  # T125 command allowlist result
  controlled_apply_check: "pass"   # T126 controlled apply result
  pass_fail_validation_check: "pass" # T127 pass/fail result

# 安全声明
safety:
  real_patch_apply_allowed: "no"
  command_execution_allowed: "no"
  auto_git_backup_allowed: "no"
  auto_continue_allowed: "no"
  stage_8_allowed: "no"
  human_review_required: "yes"

# Proposal 摘要（用于 invalidation 检查）
proposal_fingerprint:
  proposal_hash: ""                # proposal 文本的 SHA-256 前 16 字符
  patch_hash: ""                   # patch 文件的 SHA-256 前 16 字符
  target_files_hash: ""            # target_files 排序后拼接的 SHA-256 前 16 字符

# 决策
decision:
  ready_for_real_apply: "no"       # 始终为 no（T129 只设计，不允许 real apply）
  ready_for_apply_record_dry_run: "yes"
  approval_valid: "yes"            # yes / invalidated / expired

# 备注
notes: ""
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| approval_record_version | string | yes | Schema 版本号 |
| approval_id | string | yes | 唯一标识，格式 APR-YYYYMMDD-HHMMSS-<6hex> |
| task_id | string | yes | 关联任务 ID |
| task_title | string | yes | 任务标题 |
| approval_mode | string | yes | 固定为 human_reviewed_controlled_apply |
| approval_token | string | yes | 必须完全匹配 APPROVE_CONTROLLED_APPLY_DRY_RUN |
| approved_by | string | yes | human 或 automatic_rejected |
| approved_at | string | yes | ISO 8601 时间戳 |
| approval_scope.allowed_files | list | yes | 允许修改的文件列表 |
| approval_scope.target_files | list | yes | 目标修改文件列表 |
| approval_scope.patch_files | list | yes | patch 文件列表 |
| approval_scope.forbidden_files | list | yes | 禁止修改的文件列表 |
| evidence.* | string | yes | 每个前置检查结果，值为 pass/fail |
| safety.* | string | yes | 安全声明，T129 阶段全部为安全值 |
| proposal_fingerprint.proposal_hash | string | yes | proposal 内容哈希 |
| proposal_fingerprint.patch_hash | string | yes | patch 内容哈希 |
| proposal_fingerprint.target_files_hash | string | yes | target_files 哈希 |
| decision.ready_for_real_apply | string | yes | 始终为 no |
| decision.ready_for_apply_record_dry_run | string | yes | T130 dry-run 就绪标志 |
| decision.approval_valid | string | yes | yes / invalidated / expired |
| notes | string | no | 备注 |

## Audit Record Purpose

Audit record 的作用：

1. **记录 apply 前状态**：git HEAD、worktree status、文件快照
2. **记录 apply 后状态**：git HEAD、worktree status、文件快照
3. **记录 diff 摘要**：哪些文件变化了，变化了多少行
4. **记录 touched files**：预期 vs 实际 touched files
5. **记录验证命令和结果**：apply 后执行的验证命令
6. **记录是否出现 unexpected dirty workspace**：检测非预期变更
7. **记录是否需要人工复核**：无论结果如何都标记需要人工复核
8. **支持 pre/post 对比**：pre-apply 和 post-audit 是同一个 audit record 的两个 phase

## Audit Record Schema

```yaml
audit_record_version: "1.0"
audit_id: ""                       # 格式: AUD-YYYYMMDD-HHMMSS-<6hex>
task_id: ""                        # 关联任务 ID
linked_approval_id: ""             # 关联 approval_record 的 approval_id
phase: "pre_apply"                 # pre_apply / post_apply

# Git 状态
git:
  head_before: ""                  # apply 前 git HEAD commit hash
  head_after: ""                   # apply 后 git HEAD commit hash
  worktree_status_before: ""       # apply 前 git status --short 输出
  worktree_status_after: ""        # apply 后 git status --short 输出

# 文件变更
changes:
  expected_files: []               # 预期变更文件列表
  actual_files: []                 # 实际变更文件列表
  unexpected_files: []             # 非预期变更文件列表
  diff_stat: ""                    # diff --stat 摘要

# 验证命令
validation:
  commands_planned: []             # 计划执行的验证命令
  commands_executed: []            # 实际执行的验证命令
  command_results: []              # 命令执行结果

# 安全检查
safety:
  business_code_changed: "no"      # yes/no
  framework_code_changed: "no"     # yes/no
  unexpected_dirty_workspace: "no" # yes/no
  real_patch_applied: "no"         # yes/no
  command_execution_performed: "no" # yes/no

# 决策
decision:
  requires_human_review: "yes"     # 始终为 yes
  ready_for_commit: "no"           # 始终为 no（T129 阶段）
  ready_for_push: "no"             # 始终为 no（T129 阶段）
  audit_phase_complete: "no"       # pre_apply + post_apply 都完成时为 yes

# 备注
notes: ""
```

### Audit Phase 说明

Audit record 有两个 phase：

1. **pre_apply**：在 patch apply 前记录状态快照
   - `git.head_before` 和 `git.worktree_status_before` 填写实际值
   - `git.head_after`、`git.worktree_status_after`、`changes.*` 留空
   - `validation.*` 留空（apply 后才执行验证）
   - `safety.real_patch_applied` 为 "no"（尚未 apply）
   - `decision.audit_phase_complete` 为 "no"

2. **post_apply**：在 patch apply 后记录状态快照
   - `git.head_after` 和 `git.worktree_status_after` 填写实际值
   - `changes.*` 填写实际对比结果
   - `validation.*` 填写实际验证结果
   - `safety.*` 填写实际安全检查结果
   - `decision.audit_phase_complete` 为 "yes"

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| audit_record_version | string | yes | Schema 版本号 |
| audit_id | string | yes | 唯一标识，格式 AUD-YYYYMMDD-HHMMSS-<6hex> |
| task_id | string | yes | 关联任务 ID |
| linked_approval_id | string | yes | 关联的 approval_id |
| phase | string | yes | pre_apply 或 post_apply |
| git.head_before | string | yes(pre) | apply 前 HEAD commit hash |
| git.head_after | string | yes(post) | apply 后 HEAD commit hash |
| git.worktree_status_before | string | yes(pre) | apply 前 git status 输出 |
| git.worktree_status_after | string | yes(post) | apply 后 git status 输出 |
| changes.expected_files | list | yes(post) | 预期变更文件 |
| changes.actual_files | list | yes(post) | 实际变更文件 |
| changes.unexpected_files | list | yes(post) | 非预期变更文件 |
| changes.diff_stat | string | yes(post) | diff --stat 摘要 |
| validation.commands_planned | list | yes | 计划验证命令 |
| validation.commands_executed | list | yes(post) | 实际执行命令 |
| validation.command_results | list | yes(post) | 命令结果 |
| safety.* | string | yes | 安全检查结果 |
| decision.* | string | yes | 决策字段 |

## File Path Design

### 推荐方案

```text
reports/apply/
  Txxx-approval-record.md          # approval record
  Txxx-pre-apply-audit.md          # pre-apply audit record
  Txxx-post-apply-audit.md         # post-apply audit record
```

### 选择理由

选择 `reports/apply/` 单目录方案，理由：

1. **内聚性**：approval record 和 audit record 是同一个 apply 流程的三个阶段（approve → pre-check → post-check），放在同一目录便于查找和关联
2. **简单性**：单目录比三个目录更容易管理，`ls reports/apply/T129-*` 即可看到所有相关文件
3. **一致性**：与现有 `reports/checks/`、`reports/dev/`、`reports/diagnostics/` 的按功能分目录模式一致
4. **扩展性**：未来如果有更多 apply 相关记录（如 rollback record），可以直接在同一目录下添加

### 备选方案（不推荐）

```text
reports/approvals/Txxx-approval-record.md
reports/audit/Txxx-pre-apply-audit.md
reports/audit/Txxx-post-apply-audit.md
```

不推荐理由：approval 和 audit 是强关联的，拆成两个目录增加查找复杂度，且 audit record 必须通过 linked_approval_id 关联 approval record，分目录增加了关联成本。

### 命名规范

| 文件 | 格式 | 示例 |
|------|------|------|
| approval record | `T{task_id}-approval-record.md` | `T129-approval-record.md` |
| pre-apply audit | `T{task_id}-pre-apply-audit.md` | `T129-pre-apply-audit.md` |
| post-apply audit | `T{task_id}-post-apply-audit.md` | `T129-post-apply-audit.md` |

## Required Evidence Before Future Real Apply

未来允许 real apply 前，必须提供以下 evidence：

| # | Evidence | Source | Required |
|---|----------|--------|----------|
| 1 | clean worktree | `git status --short` 无输出 | yes |
| 2 | current task id | 从 docs/tasks.md 读取 | yes |
| 3 | approved proposal | approval_record 中记录的 proposal_fingerprint | yes |
| 4 | approval token exact match | approval_record.approval_token == APPROVE_CONTROLLED_APPLY_DRY_RUN | yes |
| 5 | parser pass | evidence.proposal_parse_check == pass | yes |
| 6 | scope validator pass | evidence.scope_validation_check == pass | yes |
| 7 | patch dry-run pass | evidence.patch_dry_run_check == pass | yes |
| 8 | pipeline pass | evidence.pipeline_check == pass | yes |
| 9 | approval model pass | evidence.approval_model_check == pass | yes |
| 10 | command allowlist pass | evidence.command_allowlist_check == pass | yes |
| 11 | pass/fail validation pass | evidence.pass_fail_validation_check == pass | yes |
| 12 | expected target files | approval_scope.target_files 非空 | yes |
| 13 | expected patch files | approval_scope.patch_files 非空 | yes |
| 14 | no auto-continue | safety.auto_continue_allowed == no | yes |
| 15 | no auto-git-backup | safety.auto_git_backup_allowed == no | yes |
| 16 | human review required | safety.human_review_required == yes | yes |
| 17 | approval valid | decision.approval_valid == yes | yes |
| 18 | pre-apply audit complete | audit record phase == pre_apply，audit_phase_complete == yes | yes |
| 19 | proposal not changed | proposal_fingerprint 与当前 proposal 内容一致 | yes |
| 20 | patch not changed | proposal_fingerprint 与当前 patch 内容一致 | yes |

20 项 evidence 全部满足后，才允许进入 future real apply 步骤。

## Invalidation Conditions

以下任何条件触发时，approval record 必须标记为 `invalidated`：

| # | Condition | Detection Method | Severity |
|---|-----------|-----------------|----------|
| 1 | dirty workspace before apply | `git status --short` 有输出 | hard invalidation |
| 2 | approval token missing | approval_record.approval_token 为空 | hard invalidation |
| 3 | approval token mismatch | token 不等于 APPROVE_CONTROLLED_APPLY_DRY_RUN | hard invalidation |
| 4 | approval record missing | 文件不存在 | hard invalidation |
| 5 | audit pre-check missing | pre-apply audit record 不存在 | hard invalidation |
| 6 | proposal changed after approval | proposal_hash 与当前内容不一致 | hard invalidation |
| 7 | patch changed after approval | patch_hash 与当前内容不一致 | hard invalidation |
| 8 | target files changed after approval | target_files_hash 与当前内容不一致 | hard invalidation |
| 9 | validation result changed | evidence 中任一 check 变为 fail | hard invalidation |
| 10 | unexpected file change | post-apply audit 发现 unexpected_files 非空 | hard invalidation |
| 11 | auto_continue requested | safety.auto_continue_allowed == yes | hard invalidation |
| 12 | auto_git_backup requested | safety.auto_git_backup_allowed == yes | hard invalidation |
| 13 | Stage 8 requested | safety.stage_8_allowed == yes | hard invalidation |
| 14 | real_apply flag appears unexpectedly | decision.ready_for_real_apply == yes (unexpected) | hard invalidation |
| 15 | approval expired | approved_at 超过 24 小时 | soft invalidation |

### Hard vs Soft Invalidation

- **Hard invalidation**：approval 立即失效，必须重新走完整 approval 流程
- **Soft invalidation**：approval 标记为 expired，但可以由人工决定是否接受（需要单独确认）

### Invalidation 后的恢复

```text
approval invalidated → human decides:
  ├─ hard invalidation → must restart from proposal parsing (T117)
  └─ soft invalidation → human confirms "revalidate with current state" → re-check fingerprints → update approval_record
```

## Relationship to T130

### T129 与 T130 的边界

| | T129 (本轮) | T130 (下一步) |
|---|---|---|
| 性质 | 设计 | dry-run 实现 |
| 产出 | 设计文档 + schema 定义 | 代码实现 + dry-run 验证 |
| 是否实现代码 | 否 | 是 |
| 是否生成 approval record | 否（只定义 schema） | 是（dry-run 生成） |
| 是否生成 audit record | 否（只定义 schema） | 是（dry-run 生成） |
| 是否修改 pipeline | 否 | 在现有 pipeline 基础上扩展 |

### T130 应实现的内容

1. approval record 生成函数（根据 T126 controlled apply dry-run result 生成）
2. audit record 生成函数（pre-apply 和 post-apply 两个 phase）
3. proposal fingerprint 计算（SHA-256 前 16 字符）
4. invalidation 检查函数
5. required evidence 检查函数（20 项 evidence 逐项验证）
6. dry-run CLI 入口
7. 内置 dry-run 样本验证

### T129 不实现的内容

1. 不实现代码
2. 不生成真实的 approval record
3. 不生成真实的 audit record
4. 不修改 T117-T128 pipeline 逻辑
5. 不真实 apply patch
6. 不执行 command
7. 不调用 Claude Code
8. 不修改业务代码

## Decision Summary

```text
REAL_APPLY_APPROVAL_PERSISTENCE_DESIGNED=yes
AUDIT_RECORD_DESIGNED=yes
READY_FOR_APPROVAL_RECORD_DRY_RUN=yes
READY_FOR_REAL_APPLY=no
READY_FOR_COMMAND_EXECUTION=no
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
| approval record schema defined | designed |
| audit record schema defined | designed |
| required evidence list defined | designed (20 items) |
| invalidation conditions defined | designed (15 conditions) |
