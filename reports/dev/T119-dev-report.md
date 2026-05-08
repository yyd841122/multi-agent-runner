# T119 Dev Report

## Task

实现 controlled patch apply dry-run。

## Scope

本轮只实现 patch apply dry-run，不真实 apply patch，不执行 command，不真实执行任务。

## Background

- T115 设计了 no-tool-use safe execution fallback strategy
- T116 设计了 no-tool-use execution proposal schema
- T117 实现了 proposal parser dry-run（7/7 scenarios pass）
- T118 实现了 allowed scope validator dry-run（9/9 scenarios pass）
- T119 在 T117 parser + T118 validator 基础上实现 patch apply dry-run

## Changed Files

| File | Change Type | Description |
|------|-------------|-------------|
| tools/continuous_task_planner.py | modified | Added patch apply helper functions, dataclass, dry-run function, 9 samples, and run function |
| runner.py | modified | Added no-tool-use-patch-apply-dry-run CLI command |
| docs/tasks.md | modified | T119 status update |
| reports/checks/T119-controlled-patch-apply-dry-run-check.md | new | Check report for 9 scenarios |
| reports/dev/T119-dev-report.md | new | This file |
| memory/lessons.md | modified | Patch apply dry-run lesson |
| memory/pitfalls.md | modified | Patch apply implementation pitfall |

## Implementation

### Helper Functions

三个 patch 解析辅助函数：

- `_extract_diff_file(diff_text, marker_prefix)`: 从 unified diff 行提取文件路径（`--- a/file` 或 `+++ b/file`）
- `_is_patch_empty(content)`: 检查 patch 内容是否为空或只有空白
- `_is_valid_unified_diff(content)`: 检查 unified diff 格式（`--- a/`, `+++ b/`, `@@ ... @@`）

### NoToolUseControlledPatchApplyDryRunResult

Dataclass with 30 fields tracking patch apply dry-run result：

- Parse + Validation 状态：parse_status, parse_check_result, validation_status, validation_check_result, patch_dry_run_status
- Proposal 基本信息：proposal_version, execution_mode, task_id, change_type
- 文件信息：target_files, patch_files, patch_count, empty_patch
- Scope 校验：allowed_scope_pass, forbidden_scope_pass
- Patch 解析：patch_parse_pass, patch_file_consistency_pass
- 安全保证（硬编码）：patch_apply_blocked=True, command_execution_blocked=True, real_patch_applied="no", real_task_execution="no" 等
- 人工审查：human_review_required="yes"
- 就绪状态：ready_for_future_controlled_apply
- 违规列表：violations
- 最终结果：check_result, message

### run_no_tool_use_controlled_patch_apply_dry_run()

七步校验流程：

1. 复用 `validate_no_tool_use_allowed_scope_dry_run()` (T118 validator)
2. 如果 parse fail，返回 `patch_dry_run_status=failed_parse`
3. 如果 validation fail，返回 `patch_dry_run_status=failed_validation`
4. 从原始 YAML 中提取 `patches` 数据
5. 检查 proposal type 是否需要 patches（patch_proposal / mixed_safe_proposal 需要）
6. 逐个检查 patches：格式、空内容、文件一致性、scope
7. 确定 `patch_dry_run_status` 和 `ready_for_future_controlled_apply`

### 9 Patch Apply Samples

| Sample | Description | Expected CHECK_RESULT |
|--------|-------------|----------------------|
| pass | 完全合法的 proposal with valid unified diff | pass |
| no-patch | patch_proposal 但没有 patches 节 | fail |
| empty-patch | patch content 为空 | fail |
| patch-file-mismatch | patch file 不在 target_files 列表中 | fail |
| patch-outside-allowed | target_file 不在 allowed_files 内（T118 拦截） | fail |
| patch-forbidden-file | target_file 在 forbidden_files 中（T118 拦截） | fail |
| invalid-patch-format | unified diff 格式不正确 | fail |
| validation-fail | auto_continue=yes（T118 safety 拦截） | fail |
| parse-fail | 无效 YAML 语法（T117 parser 拦截） | fail |

### runner.py CLI

New command：`python runner.py no-tool-use-patch-apply-dry-run [--sample <name>]`

## Behavior

### Validator Reuse

Patch apply dry-run 复用 T118 的 `validate_no_tool_use_allowed_scope_dry_run()` 进行 scope 和 safety 校验。如果 validator 返回 parse fail 或 validation fail，patch apply 直接返回对应状态，不继续 patch 解析。

### Patch Format Validation

对每个 patch content 检查：
1. 空内容检测
2. unified diff 格式检查（必须有 `--- a/file`, `+++ b/file`, `@@ ... @@`）

### File Consistency Check

每个 patch 的 `file` 字段必须在 `target_files` 列表中存在。

### Patch Scope Check

每个 patch 的 `file` 字段还需通过 allowed_scope 和 forbidden_scope 检查。

### 不应用 Patch / 不执行 Command

`patch_apply_blocked` 和 `command_execution_blocked` 始终为 True。`real_patch_applied` 始终为 "no"。即使 proposal 中包含有效 patches，patch apply dry-run 只记录和预览，不实际应用。

## Safety Rules

| Check | Result |
|-------|--------|
| no patch applied | yes |
| no command execution | yes |
| no Claude Code call | yes |
| no business code modification | yes |
| no framework code modification | yes |
| no real task execution | yes |
| no auto-continue | yes |
| no auto Git backup | yes |
| human review required | yes |
| no bypass permissions | yes |

## Verification

9 scenarios verified in `reports/checks/T119-controlled-patch-apply-dry-run-check.md`：

| Scenario | PARSE_STATUS | VALIDATION_STATUS | PATCH_DRY_RUN_STATUS | CHECK_RESULT |
|----------|-------------|-------------------|----------------------|-------------|
| pass | parsed | validated | ready_for_future_apply | pass |
| no-patch | parsed | validated | no_patch | fail |
| empty-patch | parsed | validated | unsafe_patch | fail |
| patch-file-mismatch | parsed | validated | unsafe_patch | fail |
| patch-outside-allowed | parsed | failed_scope | failed_validation | fail |
| patch-forbidden-file | parsed | failed_scope | failed_validation | fail |
| invalid-patch-format | parsed | validated | unsafe_patch | fail |
| validation-fail | parsed | failed_scope | failed_validation | fail |
| parse-fail | failed_to_parse | failed_parse | failed_parse | fail |

9/9 PASS.

## Next

T120: 执行 first no-tool-use real single-task dry-run
