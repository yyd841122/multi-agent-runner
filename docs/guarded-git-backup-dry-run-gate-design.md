# Guarded Git Backup Dry-Run Gate Design

## Background

T129-T133 完成 guarded real patch apply dry-run 链路：

- T129：设计 real apply approval persistence and audit record（approval record + audit record schema, 20 required evidence, 15 invalidation conditions）
- T130：实现 real apply approval record dry-run（7/7 scenarios validated）
- T131：设计 post-apply validation gate（12 inputs, 18 checks, 3 workspace classifications, 21 rejection conditions）
- T132：实现 first real patch apply guarded dry-run（12/12 scenarios validated）
- T133：验证 pass/fail 场景（12/12 scenarios, 1 pass + 11 fail-closed）

T134 已归档 T129-T133 全部成果。当前状态：

```text
READY_FOR_GIT_BACKUP_DRY_RUN=yes
READY_FOR_NEXT_STAGE_7_STEP=yes
READY_FOR_REAL_APPLY=no
READY_FOR_COMMIT=no
READY_FOR_PUSH=no
READY_FOR_STAGE_8=no
```

当前需要设计 guarded Git backup dry-run gate，作为 guarded apply dry-run → Git backup dry-run 之间的安全门。

## Problem

当前问题：

1. **guarded apply dry-run 已经能到达 Git backup dry-run readiness**：T132 pass 场景输出 `READY_FOR_GIT_BACKUP_DRY_RUN=yes`
2. **但还没有 Git backup 前置安全门**：无法验证 Git backup dry-run 是否可以安全进入
3. **不能把 `ready_for_git_backup_dry_run` 误判为 commit / push 许可**：Git backup dry-run 只允许预览备份信息，不执行任何 Git 操作
4. **不能在没有 backup record 和 staged files validation 的情况下执行 Git 操作**：必须先验证所有前置条件
5. **commit message 生成规则未定义**：未来的 commit 需要符合结构和内容安全要求
6. **backup record schema 未设计**：Git backup 的结构化记录缺失
7. **commit/push 禁止条件未明确**：即使在 gate pass 后也不能执行真实 Git 操作

## Decision

```text
Stage 7 continues.
No real git add yet.
No real git commit yet.
No real git push yet.
No Stage 8 yet.
Git backup must first be modeled as dry-run.
```

## Gate Purpose

Guarded Git backup dry-run gate 的作用：

1. 验证 guarded apply dry-run 已通过（前置链路完整性）
2. 验证 post-apply validation 已通过（文件范围和 diff 校验）
3. 验证 expected_dirty 状态可解释（workspace 分类正确）
4. 验证 actual changed files 属于 expected files（无意外变更）
5. 验证 no unexpected files（无新增未预期文件）
6. 验证 commit message 可生成（结构和内容安全）
7. 验证 backup record 可生成（完整审计记录）
8. **阻止**真实 git add / commit / push
9. **阻止**Stage 8 continuation

## Required Inputs

Git backup dry-run gate 需要 17 个输入：

| # | Input | Source | Required |
|---|-------|--------|----------|
| 1 | task_id | task definition | yes |
| 2 | task_title | task definition | yes |
| 3 | last_commit_before_backup | git HEAD | yes |
| 4 | guarded_apply_check_result | T132/T133 output | yes |
| 5 | post_apply_validation_check_result | T131/T132 output | yes |
| 6 | ready_for_git_backup_dry_run | T132/T133 output | yes |
| 7 | expected_changed_files | T129 audit record | yes |
| 8 | actual_changed_files | git status --short | yes |
| 9 | diff_stat | git diff --stat | yes |
| 10 | dev_report_path | task output | yes |
| 11 | check_report_path | task output | yes |
| 12 | apply_record_paths | T130/T132 output | yes |
| 13 | human_review_required | T132/T133 output | yes |
| 14 | ready_for_real_apply | T132/T133 output | yes |
| 15 | ready_for_commit | T132/T133 output | yes |
| 16 | ready_for_push | T132/T133 output | yes |
| 17 | ready_for_stage_8 | T132/T133 output | yes |

## Required Gate Checks

Git backup dry-run gate 包含 22 项检查，分为 7 组：

### Group 1: Workspace State (3 checks)

| # | Check | Expected | Reject If |
|---|-------|----------|-----------|
| 1 | worktree state classification | expected_dirty | clean or unexpected_dirty |
| 2 | actual files subset of expected files | all actual in expected | any actual outside expected |
| 3 | no forbidden files changed | none of forbidden patterns | any forbidden file changed |

Forbidden file patterns:

- `projects/down-100-floors-game/**`（业务示例项目代码）
- `tools/rework_manager.py`
- `tools/continuous_task_planner.py`（未授权修改）
- `runner.py`（未授权修改）
- `.env`
- `*.pyc`
- `__pycache__/**`

### Group 2: Guarded Apply Validation (4 checks)

| # | Check | Expected | Reject If |
|---|-------|----------|-----------|
| 4 | guarded apply check pass | pass | fail or missing |
| 5 | post-apply validation check pass | pass | fail or missing |
| 6 | ready_for_git_backup_dry_run | yes | no or missing |
| 7 | ready_for_real_apply | no | yes |

### Group 3: Safety Flags (4 checks)

| # | Check | Expected | Reject If |
|---|-------|----------|-----------|
| 8 | ready_for_commit | no | yes |
| 9 | ready_for_push | no | yes |
| 10 | ready_for_stage_8 | no | yes |
| 11 | human_review_required | yes | no |

### Group 4: File Validation (4 checks)

| # | Check | Expected | Reject If |
|---|-------|----------|-----------|
| 12 | no unexpected files | empty list | any unexpected file |
| 13 | diff stat present | non-empty | empty or missing |
| 14 | dev report exists | file exists | file missing |
| 15 | check report exists | file exists | file missing |

### Group 5: Records Validation (1 check)

| # | Check | Expected | Reject If |
|---|-------|----------|-----------|
| 16 | apply records exist | all listed paths exist | any path missing |

### Group 6: Commit Message (2 checks)

| # | Check | Expected | Reject If |
|---|-------|----------|-----------|
| 17 | commit message generated | non-empty string | empty or missing |
| 18 | commit message safe | no unsafe content | contains unsafe pattern |

### Group 7: Backup Record (4 checks)

| # | Check | Expected | Reject If |
|---|-------|----------|-----------|
| 19 | backup record dry-run generated | yes | no |
| 20 | real_git_add_performed | no | yes |
| 21 | real_git_commit_performed | no | yes |
| 22 | real_git_push_performed | no | yes |

## Git Backup Dry-Run Record Schema

```yaml
backup_record_version: "1.0"
backup_id: ""
task_id: ""
task_title: ""
backup_mode: "guarded_git_backup_dry_run"
generated_at: ""

git:
  head_before_backup: ""
  branch: "main"
  remote: "origin"
  worktree_status: "expected_dirty"

files:
  expected_changed_files: []
  actual_changed_files: []
  staged_files_planned: []
  unexpected_files: []
  forbidden_files_found: []

reports:
  dev_report: ""
  check_report: ""
  apply_records: []

commit:
  commit_message: ""
  commit_type: ""
  commit_scope: ""
  commit_allowed: "no"
  push_allowed: "no"

safety:
  real_git_add_performed: "no"
  real_git_commit_performed: "no"
  real_git_push_performed: "no"
  auto_continue_allowed: "no"
  stage_8_allowed: "no"
  command_execution_performed: "no"
  business_code_modified: "no"

validation:
  gate_checks_total: 22
  gate_checks_passed: 0
  gate_checks_failed: 0
  failed_checks: []

decision:
  ready_for_git_backup_dry_run: "no"
  ready_for_git_add: "no"
  ready_for_commit: "no"
  ready_for_push: "no"
  ready_for_stage_8: "no"
  human_review_required: "yes"
  check_result: "fail"

notes: ""
```

### Field Descriptions

| Field | Description |
|-------|-------------|
| backup_record_version | Schema 版本，固定 "1.0" |
| backup_id | 唯一备份标识，格式 `backup-<task_id>-<timestamp>` |
| task_id | 关联任务 ID |
| task_title | 关联任务标题 |
| backup_mode | 固定 "guarded_git_backup_dry_run" |
| git.head_before_backup | 备份前 HEAD commit hash |
| git.branch | 当前分支 |
| git.remote | 远程仓库名 |
| git.worktree_status | 工作区分类（expected_dirty / unexpected_dirty / clean） |
| files.expected_changed_files | 预期变更文件列表 |
| files.actual_changed_files | 实际变更文件列表 |
| files.staged_files_planned | 计划 staged 的文件列表（dry-run preview） |
| files.unexpected_files | 意外文件列表 |
| files.forbidden_files_found | 禁止文件列表 |
| commit.commit_message | 生成的 commit message（dry-run preview） |
| commit.commit_type | 提交类型（docs/test/feat/fix/refactor） |
| commit.commit_scope | 提交范围（task ID 或功能描述） |
| safety.* | 7 个安全声明，全部必须为 "no" |
| validation.gate_checks_total | 总检查数（固定 22） |
| validation.gate_checks_passed | 通过检查数 |
| validation.failed_checks | 失败检查项列表 |
| decision.* | 8 个决策字段 |

## Commit Message Rules

### Structure

```
<type>: <short summary>
```

### Type Classification

| File Pattern | Type | Example |
|-------------|------|---------|
| `docs/*.md` | docs | `docs: archive guarded git backup dry run gate design` |
| `reports/**/*.md` | docs | `docs: add T135 check report` |
| `memory/*.md` | docs | `docs: update lessons and pitfalls` |
| `tools/*.py` | feat/fix/test/refactor | `feat: add guarded git backup dry run` |
| `runner.py` | feat/fix/refactor | `feat: add git backup dry-run command` |
| Mixed (docs + code) | 按主要变更类型 | `feat: add guarded git backup dry run` |

### Required Content

1. **必须包含 task id**：commit message body 或 title 中需包含任务编号
2. **必须描述当前任务成果**：清晰说明本次提交包含什么
3. **使用英文**：保持与已有提交风格一致

### Forbidden Content

1. **不得包含 auto-generated misleading claim**：不能声称"all tests passed"如果只是 dry-run
2. **不得暗示已 real apply**：不能包含 "applied patch"、"real execution" 等措辞
3. **不得暗示已 push**：不能包含 "pushed to remote"
4. **不得暗示 Stage 8**：不能包含 "stage 8"、"continuous execution"

### Unsafe Commit Message Patterns

以下模式被视为 unsafe：

- `real patch applied`
- `real execution completed`
- `pushed to`
- `stage 8`
- `auto continue`
- `auto backup`
- `unattended`
- `production`

### Examples

Safe:
```
docs: design guarded git backup dry run gate

T135 design document for Git backup dry-run safety gate.
Defined 22 gate checks, backup record schema, commit message rules,
25 rejection conditions, and T136 implementation boundary.
```

```
test: validate guarded git backup dry run scenarios

T137 pass/fail validation for guarded Git backup dry-run.
12/12 scenarios validated: 1 pass + 11 fail-closed.
```

Unsafe (会被 gate 拒绝):
```
feat: real patch applied and pushed to main
auto backup completed, continuing to next task
```

## Rejection Conditions

Git backup dry-run gate 的 25 个拒绝条件：

| # | Condition | Group |
|---|-----------|-------|
| 1 | worktree clean unexpectedly | workspace |
| 2 | worktree has unexpected files | workspace |
| 3 | forbidden files changed | workspace |
| 4 | actual files not subset of expected files | workspace |
| 5 | guarded apply check failed | apply validation |
| 6 | post-apply validation failed | apply validation |
| 7 | ready_for_git_backup_dry_run not yes | apply validation |
| 8 | ready_for_real_apply is yes | safety flags |
| 9 | ready_for_commit is yes | safety flags |
| 10 | ready_for_push is yes | safety flags |
| 11 | ready_for_stage_8 is yes | safety flags |
| 12 | human_review_required is not yes | safety flags |
| 13 | missing dev report | file validation |
| 14 | missing check report | file validation |
| 15 | missing apply record | records |
| 16 | missing diff stat | file validation |
| 17 | commit message missing | commit |
| 18 | commit message unsafe | commit |
| 19 | backup record not generated | backup record |
| 20 | real_git_add_performed is yes | backup record |
| 21 | real_git_commit_performed is yes | backup record |
| 22 | real_git_push_performed is yes | backup record |
| 23 | git add requested | operation request |
| 24 | git commit requested | operation request |
| 25 | git push requested | operation request |

## Allowed After Gate Pass

Gate pass 后只允许以下操作：

| # | Allowed Action | Description |
|---|----------------|-------------|
| 1 | generate backup dry-run record | 生成 backup_record 并写入 reports/backup/ |
| 2 | preview files that would be staged | 列出计划 staged 的文件列表 |
| 3 | preview commit message | 生成并预览 commit message |
| 4 | preview backup decision | 显示 gate 决策和所有安全字段 |
| 5 | stop for human review | 必须停止等待人工审查 |

## Forbidden Even After Gate Pass

Gate pass 后仍禁止以下操作：

| # | Forbidden Action | Reason |
|---|------------------|--------|
| 1 | real git add | Stage 7 不允许真实 git 操作 |
| 2 | real git commit | Stage 7 不允许真实 git 操作 |
| 3 | real git push | Stage 7 不允许真实 git 操作 |
| 4 | automatic backup | 不允许自动执行备份 |
| 5 | automatic next task continuation | 不允许自动进入下一任务 |
| 6 | Stage 8 transition | 不允许进入 Stage 8 |
| 7 | command execution | 不允许执行 proposed commands |
| 8 | business code modification | 不允许修改业务代码 |

## Relationship to T136

```text
T135（本任务）: 设计 guarded Git backup dry-run gate
  - 定义 required inputs (17 项)
  - 定义 gate checks (22 项, 7 组)
  - 定义 backup record schema (1.0)
  - 定义 commit message rules
  - 定义 rejection conditions (25 条)
  - 定义 allowed/forbidden after gate pass
  - 不实现代码
  - 不执行 Git 操作

T136: 实现 guarded Git backup dry-run
  - 基于 T135 设计实现 gate 逻辑
  - 实现 backup record dry-run 生成
  - 实现 commit message 生成
  - 实现 staged files preview
  - 实现 gate checks 验证
  - 实现 CLI 命令入口
  - 仍不允许真实 git add / commit / push
  - 不进入 T137

T137: 验证 guarded Git backup dry-run pass/fail 场景
  - 独立验证 T136 实现的 pass/fail 稳定性
  - 确认 pass 只到达 Git backup dry-run readiness
  - 确认 fail 全部 fail closed

T138: 归档 Stage 7 Git backup dry-run 成果
  - 总结 T135-T137 全部成果
  - 确认下一步方向
```

## Decision Summary

```text
GUARDED_GIT_BACKUP_DRY_RUN_GATE_DESIGNED=yes
GATE_INPUTS_DEFINED=17
GATE_CHECKS_DEFINED=22
GATE_GROUPS_DEFINED=7
REJECTION_CONDITIONS_DEFINED=25
BACKUP_RECORD_SCHEMA_VERSION=1.0
COMMIT_MESSAGE_RULES_DEFINED=yes
ALLOWED_ACTIONS_AFTER_PASS=5
FORBIDDEN_ACTIONS_AFTER_PASS=8
T136_BOUNDARY_DEFINED=yes
READY_FOR_GUARDED_GIT_BACKUP_DRY_RUN_IMPLEMENTATION=yes
READY_FOR_REAL_GIT_ADD=no
READY_FOR_REAL_COMMIT=no
READY_FOR_REAL_PUSH=no
READY_FOR_STAGE_8=no
HUMAN_REVIEW_REQUIRED=yes
```
