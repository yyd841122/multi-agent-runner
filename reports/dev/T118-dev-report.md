# T118 Dev Report

## Task

实现 allowed scope validator dry-run。

## Scope

本轮只实现 validator dry-run，不应用 patch，不执行 command，不真实执行任务。

## Background

- T115 设计了 no-tool-use safe execution fallback strategy
- T116 设计了 no-tool-use execution proposal schema（22 required fields, 5 proposal types, 30 validation rules, 20 failure cases）
- T117 实现了 proposal parser dry-run（7/7 scenarios pass）
- T117 parser 只解析结构，不做 scope 校验、patch 校验或 command 执行
- T118 在 T117 parser 基础上实现 scope 和 safety 校验

## Changed Files

| File | Change Type | Description |
|------|-------------|-------------|
| tools/continuous_task_planner.py | modified | Added validator dataclass, helper functions, validate function, 9 dry-run samples, and run function |
| runner.py | modified | Added no-tool-use-validate-scope CLI command |
| docs/tasks.md | modified | T118 status update |
| reports/checks/T118-allowed-scope-validator-dry-run-check.md | new | Check report for 9 scenarios |
| reports/dev/T118-dev-report.md | new | This file |
| memory/lessons.md | modified | Validator dry-run lesson |
| memory/pitfalls.md | modified | Validator implementation pitfall |

## Implementation

### Helper Functions

五个最小路径匹配函数：

- `_has_path_traversal(file_path)`: 检查路径是否包含 `..` 组件
- `_is_absolute_path(file_path)`: 检查路径是否以 `/` 或 `C:` 开头
- `_path_matches_pattern(file_path, pattern)`: 支持精确匹配、递归通配 `/**`、单层通配 `*`（使用 stdlib fnmatch）
- `_is_path_in_scope(file_path, allowed_patterns)`: 检查文件是否被 allowed_files 覆盖，保守原则空列表则 fail
- `_is_path_forbidden(file_path, forbidden_patterns)`: 检查文件是否命中 forbidden_files

### NoToolUseAllowedScopeValidationResult

Dataclass with 28 fields tracking validation result：

- Parse 状态：parse_status, parse_check_result, validation_status
- Proposal 基本信息：proposal_version, execution_mode, task_id, change_type
- Scope 信息：allowed_files, forbidden_files, target_files, proposed_commands, expected_reports
- Scope 校验结果：allowed_scope_pass, forbidden_scope_pass
- Safety 校验结果：safety_declarations_pass, human_review_required_pass, auto_continue_pass, auto_git_backup_pass
- 安全保证（硬编码）：command_execution_blocked=True, patch_apply_blocked=True, real_task_execution="no" 等
- 违规列表：violations
- 最终结果：check_result, message

### validate_no_tool_use_allowed_scope_dry_run()

七步校验流程：

1. 调用 `parse_no_tool_use_execution_proposal()` 解析 proposal
2. 如果 parse fail，返回 `validation_status=failed_parse`
3. 从原始 YAML 中提取 `scope.allowed_files` 和 `scope.forbidden_files`
4. 校验 target_files：路径逃逸 → 绝对路径 → allowed 覆盖 → forbidden 命中
5. 校验 safety declarations：human_review_required=yes, auto_continue=no, auto_git_backup=no 等
6. 确定 `validation_status`：validated / failed_scope / failed_safety / failed_parse
7. 返回完整 validation result

### run_no_tool_use_allowed_scope_validator_dry_run()

内置 9 个 sample 对应 9 个校验场景：

| Sample | Description | Expected CHECK_RESULT |
|--------|-------------|----------------------|
| pass | 完全合法的 proposal | pass |
| target-outside-allowed | target_file 不在 allowed_files 内 | fail |
| forbidden-file | target_file 命中 forbidden_files | fail |
| path-traversal | target_file 包含 `../` | fail |
| absolute-path | target_file 是绝对路径 `/etc/passwd` | fail |
| missing-human-review | human_review_required="no" | fail |
| auto-continue-requested | auto_continue_to_next_task="yes" | fail |
| auto-git-backup-requested | auto_git_backup="yes" | fail |
| parse-fail | 无效 YAML 语法 | fail |

### runner.py CLI

New command：`python runner.py no-tool-use-validate-scope [--sample <name>]`

## Behavior

### Parser Reuse

Validator 复用 T117 的 `parse_no_tool_use_execution_proposal()` 进行结构解析。如果 parser 返回 parse_status != "parsed"，validator 立即返回 failed_parse，不继续 scope/safety 校验。

### Allowed Files 校验

对每个 target_file：
1. 先检查路径逃逸（`..` 在路径组件中）
2. 再检查绝对路径（以 `/` 或 `C:` 开头）
3. 然后检查是否被 allowed_files 覆盖（精确匹配、递归通配、fnmatch）

### Forbidden Files 校验

对每个 target_file，检查是否匹配任何 forbidden_files 模式。

### Path Traversal 处理

将路径按 `/` 分割后检查是否有 `..` 组件。检测到后立即标记 allowed_scope_pass=False 并跳过后续检查。

### Absolute Path 处理

检查路径是否以 `/` 开头或第二字符为 `:`。检测到后同样跳过后续检查。

### Safety Declarations 校验

从原始 YAML 的 `safety` 节提取 7 个字段值，逐个校验：
- `human_review_required` 必须 "yes"
- `auto_continue_to_next_task` 必须 "no"
- `auto_git_backup` 必须 "no"
- `real_task_execution` 必须 "no"
- `run_project_task_full_called` 必须 "no"
- `claude_code_tool_use_used` 必须 "no"

### 不执行 Command / 不应用 Patch

Validator 是纯校验逻辑，`command_execution_blocked` 和 `patch_apply_blocked` 始终为 True。即使 proposal 中包含 commands 和 patches，validator 只记录它们的存在，不执行、不应用。

## Safety Rules

| Check | Result |
|-------|--------|
| no validator | yes |
| no patch apply | yes |
| no command execution | yes |
| no run-project-task-full call | yes |
| no Claude Code call | yes |
| no business code modification | yes |
| no real task execution | yes |
| no auto-continue | yes |
| no auto Git backup | yes |
| human review required | yes |
| no bypass permissions | yes |

## Verification

9 scenarios verified in `reports/checks/T118-allowed-scope-validator-dry-run-check.md`：

| Scenario | PARSE_STATUS | VALIDATION_STATUS | CHECK_RESULT |
|----------|-------------|-------------------|-------------|
| pass | parsed | validated | pass |
| target-outside-allowed | parsed | failed_scope | fail |
| forbidden-file | parsed | failed_scope | fail |
| path-traversal | parsed | failed_scope | fail |
| absolute-path | parsed | failed_scope | fail |
| missing-human-review | parsed | failed_safety | fail |
| auto-continue-requested | parsed | failed_safety | fail |
| auto-git-backup-requested | parsed | failed_safety | fail |
| parse-fail | failed_to_parse | failed_parse | fail |

9/9 PASS.

## Next

T119: 实现 controlled patch apply dry-run
