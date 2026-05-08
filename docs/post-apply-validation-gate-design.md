# Post-Apply Validation Gate Design

## Background

T129 已设计 approval persistence and audit record schema，定义了：
- approval_record_version: "1.0"，包含 approval_scope、evidence（8 项检查）、safety（6 个安全声明）、proposal_fingerprint、decision
- audit_record_version: "1.0"，包含 git state（before/after）、changes（expected/actual/unexpected/diff_stat）、validation、safety、decision
- required evidence（20 项）和 invalidation conditions（15 条）

T130 已实现 approval record / pre-apply audit / post-apply audit dry-run 生成能力：
- 7/7 scenarios validated（1 pass + 6 fail-closed）
- reports/apply/ 目录下生成了 3 个 sample dry-run records
- 只有 pass 场景写入文件，fail-closed 场景不生成文件

当前仍不能 real apply。当前仍不能 command execution。当前仍不能 automatic git backup。

下一步需要设计 real apply 后的 validation gate：用于判断 patch apply 后的工作区、文件范围、diff、验证结果和报告是否符合预期。

该 gate 是未来 guarded real patch apply 的后置安全门，在 apply 发生之后、commit/push/Stage 8 之前执行。

## Problem

当前问题：

1. **approval/audit dry-run 已经能生成 evidence records**：但未来如果 real patch apply 发生，apply 后的验证没有设计
2. **没有 apply 后 worktree 状态校验规则**：apply 后 dirty workspace 是否符合预期没有判断标准
3. **没有 expected vs actual files 对比规则**：无法确认 apply 只影响了预期文件
4. **没有 diff stat 校验规则**：无法判断 apply 的变更量是否在合理范围
5. **没有 dirty workspace 分类规则**：apply 后的 dirty 状态可能是 expected_dirty、unexpected_dirty 或 clean_unexpected
6. **没有验证命令结果归档规则**：apply 后的 validation command 结果如何记录
7. **没有 report existence 校验规则**：apply 后必须生成的报告是否确实存在
8. **没有 pass/fail 决策规则**：无法判断 apply 后是否允许进入下一步 Git backup dry-run
9. **不能在 apply 后直接进入 commit / push / Stage 8**：必须经过 post-apply validation gate

## Decision

```text
Stage 7 continues.
No real apply yet.
No command execution yet.
No automatic Git backup yet.
Post-apply validation gate must be designed before guarded real patch apply.
Gate is a post-apply safety check, not a pre-apply approval.
Gate runs after apply, before commit/push/Stage 8.
```

## Gate Purpose

Post-apply validation gate 的作用：

1. **验证 apply 后 worktree 状态**：检查 git status 是否符合预期
2. **验证 actual changed files 是否符合 expected files**：actual_files 必须是 expected_files 的子集
3. **验证 diff stat 是否可接受**：变更量、变更类型在合理范围
4. **验证 business/framework change classification 是否正确**：变更分类正确
5. **验证 required reports 是否存在**：dev report、check report、post-apply audit 存在
6. **验证 validation commands 是否已记录**：命令结果已归档（本 gate 不执行命令）
7. **判断是否允许进入下一步 Git backup dry-run 或 human review**：pass → ready_for_git_backup_dry_run
8. **阻止直接 commit / push / Stage 8**：即使 gate pass，仍不允许自动 commit/push/Stage 8

## Required Inputs

Post-apply validation gate 至少需要以下输入：

| # | Input | Source | Required |
|---|-------|--------|----------|
| 1 | task_id | 从 docs/tasks.md 读取 | yes |
| 2 | approval_record_path | 来自 T129/T130 approval record | yes |
| 3 | pre_apply_audit_path | 来自 T129/T130 pre-apply audit | yes |
| 4 | post_apply_audit_path | 来自 T129/T130 post-apply audit | yes |
| 5 | expected_target_files | 来自 proposal / approval_record.approval_scope.target_files | yes |
| 6 | expected_patch_files | 来自 proposal / approval_record.approval_scope.patch_files | yes |
| 7 | actual_changed_files | 来自 git status after apply | yes |
| 8 | git_status_after | 来自 git status --short after apply | yes |
| 9 | diff_stat_after | 来自 git diff --stat after apply | yes |
| 10 | validation_results | 来自 post-apply audit record | yes |
| 11 | report_paths | 来自任务执行结果 | yes |
| 12 | human_review_required | 来自 approval_record.safety.human_review_required | yes |

## Required Post-Apply Checks

Post-apply validation gate 至少包含以下检查：

| # | Check | Description | Required |
|---|-------|-------------|----------|
| 1 | approval_record_exists | approval record 文件存在 | yes |
| 2 | pre_apply_audit_exists | pre-apply audit record 文件存在 | yes |
| 3 | post_apply_audit_exists | post-apply audit record 文件存在 | yes |
| 4 | task_id_matches | approval/audit records 中 task_id 一致 | yes |
| 5 | expected_files_not_empty | expected_target_files 非空 | yes |
| 6 | actual_files_not_empty | actual_changed_files 非空 | yes |
| 7 | actual_files_subset_of_expected | actual_changed_files ⊆ expected_target_files ∪ expected_patch_files | yes |
| 8 | no_unexpected_files | 无 expected 之外的文件变更 | yes |
| 9 | no_forbidden_files | 无 forbidden_files 变更 | yes |
| 10 | no_path_traversal | 无 `../` 或路径逃逸 | yes |
| 11 | no_absolute_paths | 无绝对路径 | yes |
| 12 | diff_stat_present | diff_stat_after 非空 | yes |
| 13 | validation_results_present | validation_results 非空 | yes |
| 14 | required_reports_present | dev report + check report + post-apply audit 存在 | yes |
| 15 | human_review_required_yes | human_review_required == "yes" | yes |
| 16 | ready_for_commit_no | ready_for_commit == "no" by default | yes |
| 17 | ready_for_push_no | ready_for_push == "no" by default | yes |
| 18 | ready_for_stage_8_no | ready_for_stage_8 == "no" | yes |

### 检查顺序

```text
1. Record existence checks (1-3)
2. ID consistency check (4)
3. File scope checks (5-11)
4. Diff stat check (12)
5. Validation results check (13)
6. Report existence check (14)
7. Safety flag checks (15-18)
```

任何一步失败，gate 立即 fail，记录 STOP_REASON。

## Dirty Workspace Classification

Apply 后 dirty workspace 分为三类：

### expected_dirty

```yaml
classification: expected_dirty
description: "只有预期文件变更，diff stat 存在，无意外文件，验证结果已记录"
conditions:
  - only expected files changed
  - diff stat present
  - no unexpected files
  - validation results recorded
action: "允许进入 human review 和 Git backup dry-run，不允许自动 commit"
```

### unexpected_dirty

```yaml
classification: unexpected_dirty
description: "有意外文件变更或禁入文件变更，diff stat 缺失，git status 不明确"
conditions:
  - unexpected files changed
  - forbidden files changed
  - generated files outside reports/apply or reports/checks or reports/dev
  - missing diff stat
  - ambiguous git status
action: "必须停止，不允许进入 Git backup dry-run，需人工检查"
```

### clean_unexpected

```yaml
classification: clean_unexpected
description: "预期有 apply 但 worktree 意外 clean"
conditions:
  - apply expected changes but worktree clean unexpectedly
action: "必须停止并人工检查，可能 apply 未生效或 patch 为空"
```

### 分类规则

```text
if git_status_after is empty:
    classification = clean_unexpected
elif actual_changed_files ⊆ (expected_target_files ∪ expected_patch_files ∪ allowed_report_paths):
    if diff_stat_present and no_unexpected_files:
        classification = expected_dirty
    else:
        classification = unexpected_dirty
else:
    classification = unexpected_dirty
```

**注意**：expected_dirty 不等于允许 commit。expected_dirty 只表示变更符合预期范围，仍需 human review 和 Git backup gate 才能考虑 commit。

## Expected vs Actual Files Validation

### 来源

- **expected_target_files**：来自 proposal / approval_record.approval_scope.target_files
- **expected_patch_files**：来自 proposal / approval_record.approval_scope.patch_files
- **actual_changed_files**：来自 `git status --short` after apply（剥离状态前缀）

### 校验规则

```text
expected_all = expected_target_files + expected_patch_files
allowed_report_patterns = [
    "reports/dev/T<task_id>-dev-report.md",
    "reports/checks/T<task_id>-post-apply-validation-check.md",
    "reports/apply/T<task_id>-post-apply-audit.md"
]

for file in actual_changed_files:
    if file in expected_all:
        continue  # expected
    elif file matches allowed_report_patterns:
        continue  # allowed report
    else:
        fail: unexpected file <file>
```

### 核心约束

1. actual_changed_files 必须是 expected_target_files 或 expected_patch_files 的子集（加上 allowed reports）
2. 任何额外文件都 fail
3. forbidden_files 中的文件被变更直接 fail
4. allowed_files 不在 expected 中的文件被变更也 fail

## Diff Stat Validation

### 必须记录的字段

```yaml
diff_stat_validation:
  diff_stat_after: ""           # git diff --stat 完整输出
  files_changed_count: 0        # 变更文件数
  insertions_count: 0           # 插入行数
  deletions_count: 0            # 删除行数
  large_diff_flag: "no"         # 是否为 large diff
```

### 拒绝条件

| # | Condition | Description | Severity |
|---|-----------|-------------|----------|
| 1 | missing diff stat | diff_stat_after 为空 | hard fail |
| 2 | diff too large for single task | files_changed_count > 20 或 insertions_count > 500 或 deletions_count > 500 | hard fail |
| 3 | unexpected binary file | 二进制文件变更不在预期范围 | hard fail |
| 4 | unexpected delete | 删除了预期之外的文件 | hard fail |
| 5 | unexpected rename | 重命名了预期之外的文件 | hard fail |

### Large Diff Flag

```text
large_diff_flag = "yes" if:
    files_changed_count > 10
    OR insertions_count > 200
    OR deletions_count > 200
```

large_diff_flag == "yes" 不等于 fail。但 large diff 需要 extra human review。

## Validation Command Result Handling

### 原则

本 gate 只验证 command result 是否已记录，不负责执行 command。

未来 command execution 必须由独立 executor gate 控制（Stage 8+）。

### 记录字段

```yaml
validation_command_handling:
  validation_commands_planned: []      # 来自 proposal 的 proposed_commands
  validation_commands_executed: []     # 来自 post-apply audit 的实际执行命令
  validation_command_results: []       # 每条命令的执行结果
  validation_pass_count: 0             # pass 的命令数
  validation_fail_count: 0             # fail 的命令数
```

### 校验规则

1. validation_commands_planned 不必与 validation_commands_executed 完全一致（T131 阶段不执行命令）
2. validation_command_results 必须存在（即使是空列表，表示"未执行任何验证命令"）
3. validation_fail_count > 0 不等于 gate fail，但需要记录
4. 本 gate 不负责执行命令，只负责确认命令结果字段已填写

## Required Reports

Post-apply validation gate 至少要求以下报告存在：

| # | Report | Path Pattern | Required |
|---|--------|-------------|----------|
| 1 | dev report | reports/dev/T{task_id}-dev-report.md | yes |
| 2 | post-apply validation check | reports/checks/T{task_id}-post-apply-validation-check.md | yes |
| 3 | post-apply audit | reports/apply/T{task_id}-post-apply-audit.md | yes |

### 校验方式

```text
for required_report in required_reports:
    if not file_exists(required_report):
        fail: missing required report <required_report>
```

## Pass Decision

只有全部 18 项检查通过且 workspace 分类为 expected_dirty 时：

```text
POST_APPLY_VALIDATION_GATE=pass
WORKSPACE_CLASSIFICATION=expected_dirty
READY_FOR_HUMAN_REVIEW=yes
READY_FOR_GIT_BACKUP_DRY_RUN=yes
READY_FOR_COMMIT=no
READY_FOR_PUSH=no
READY_FOR_STAGE_8=no
STOP_REASON=none
```

**关键约束**：
- pass 不等于可以 commit
- pass 不等于可以 push
- pass 只表示 apply 结果通过验证，允许进入 human review 和 Git backup dry-run
- commit / push 需要独立的 Git backup gate（未来任务）

## Fail Decision

任一检查失败时：

```text
POST_APPLY_VALIDATION_GATE=fail
WORKSPACE_CLASSIFICATION=unexpected_dirty|clean_unexpected
READY_FOR_HUMAN_REVIEW=yes
READY_FOR_GIT_BACKUP_DRY_RUN=no
READY_FOR_COMMIT=no
READY_FOR_PUSH=no
READY_FOR_STAGE_8=no
STOP_REASON=<具体失败原因>
FAILED_CHECKS=<失败的检查项列表>
```

**关键约束**：
- fail 后仍然 READY_FOR_HUMAN_REVIEW=yes（需要人工检查失败原因）
- fail 后不允许 Git backup dry-run
- fail 后不允许 commit / push / Stage 8

## Rejection Conditions

以下任一条件触发时，gate 必须 fail：

| # | Condition | Category | Severity |
|---|-----------|----------|----------|
| 1 | missing approval record | record existence | hard fail |
| 2 | missing pre-apply audit | record existence | hard fail |
| 3 | missing post-apply audit | record existence | hard fail |
| 4 | task id mismatch | consistency | hard fail |
| 5 | actual files empty | file scope | hard fail |
| 6 | unexpected files changed | file scope | hard fail |
| 7 | forbidden files changed | file scope | hard fail |
| 8 | path traversal detected | file scope | hard fail |
| 9 | absolute path detected | file scope | hard fail |
| 10 | missing diff stat | diff validation | hard fail |
| 11 | diff too large | diff validation | hard fail |
| 12 | unexpected delete | diff validation | hard fail |
| 13 | unexpected rename | diff validation | hard fail |
| 14 | missing validation results | validation | hard fail |
| 15 | missing required report | report existence | hard fail |
| 16 | human_review_required not yes | safety flags | hard fail |
| 17 | ready_for_stage_8 requested | safety flags | hard fail |
| 18 | commit requested | safety flags | hard fail |
| 19 | push requested | safety flags | hard fail |
| 20 | workspace classification is clean_unexpected | workspace | hard fail |
| 21 | workspace classification is unexpected_dirty | workspace | hard fail |

### 所有 rejection 都是 hard fail

Post-apply validation gate 不区分 hard/soft rejection。所有失败都是 hard fail，必须人工介入。

## Relationship to T132

### T131 与 T132 的边界

| | T131 (本轮) | T132 (下一步) |
|---|---|---|
| 性质 | 设计 | dry-run 实现 |
| 产出 | 设计文档 + 检查规则定义 | 代码实现 + dry-run 验证 |
| 是否实现代码 | 否 | 是 |
| 是否 real apply | 否 | 否（guarded dry-run） |
| 是否执行 command | 否 | 否 |

### T132 应实现的内容

1. post-apply validation gate 检查函数（18 项检查）
2. dirty workspace 分类函数
3. expected vs actual files 对比函数
4. diff stat 校验函数
5. report existence 检查函数
6. pass/fail 决策函数
7. dry-run CLI 入口
8. 内置 dry-run 样本验证

### T131 不实现的内容

1. 不实现代码
2. 不 real apply patch
3. 不执行 command
4. 不调用 Claude Code
5. 不修改业务代码
6. 不修改 T123-T130 pipeline 逻辑
7. 不进入 Stage 8

## Decision Summary

```text
POST_APPLY_VALIDATION_GATE_DESIGNED=yes
READY_FOR_FIRST_REAL_PATCH_APPLY_GUARDED_DRY_RUN=yes
READY_FOR_REAL_APPLY=no
READY_FOR_COMMAND_EXECUTION=no
READY_FOR_COMMIT=no
READY_FOR_PUSH=no
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
| no commit | guaranteed |
| no push | guaranteed |
| no Stage 8 continuation | guaranteed |
| human review required | guaranteed |
| gate purpose defined | designed |
| required inputs defined | designed (12 items) |
| required post-apply checks defined | designed (18 checks) |
| dirty workspace classification defined | designed (3 categories) |
| expected vs actual files validation defined | designed |
| diff stat validation defined | designed (5 rejection conditions) |
| validation command result handling defined | designed |
| required reports defined | designed (3 reports) |
| pass/fail decision defined | designed |
| rejection conditions defined | designed (21 conditions) |
| T132 boundary defined | designed |
