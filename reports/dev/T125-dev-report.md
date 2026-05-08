# T125 Dev Report

## Task

实现 command allowlist validation dry-run。

## Scope

本轮只实现 command allowlist validation dry-run，不执行 command，不真实执行任务。

## Background

T124 approval model dry-run 已完成，10/10 scenarios 验证通过。T125 补全 command 校验层，实现 command allowlist validation dry-run。

## Changed Files

| File | Change Type | Description |
|------|-------------|-------------|
| tools/continuous_task_planner.py | modified | 新增 CommandAllowlistValidationDryRunResult、run_command_allowlist_validation_dry_run()、_classify_command()、_get_command_sample() |
| runner.py | modified | 新增 command-allowlist-dry-run CLI 入口 |
| reports/checks/T125-command-allowlist-validation-dry-run-check.md | new | 15 个场景验证报告 |
| reports/dev/T125-dev-report.md | new | This file |
| docs/tasks.md | modified | T125 status update |
| memory/lessons.md | modified | T125 lesson |
| memory/pitfalls.md | modified | T125 pitfall |

## Implementation

### CommandAllowlistValidationDryRunResult

25 个字段的数据结构，包含：
- 模式标识 (validation_mode)
- 输入 (command_sample, commands)
- 统计 (commands_total, commands_allowed, commands_rejected)
- 分类 (allowed_commands, rejected_commands, rejection_reasons, allowlist_categories, forbidden_patterns_detected)
- 安全保证字段 (command_execution_blocked, real_patch_applied, real_task_execution 等，始终为安全值)
- Gate 结果 (ready_for_command_execution, ready_for_controlled_apply_dry_run, check_result, message)

### _classify_command()

字符串级别命令分类函数：
- 先检查禁止模式（FORBIDDEN_COMMAND_PATTERNS），命中即标记 forbidden
- 再检查允许类别（COMMAND_ALLOWLIST_CATEGORIES），匹配即标记 allowed
- 未知命令标记 unknown（保守原则：不确定就拒绝）

### run_command_allowlist_validation_dry_run()

接受参数化输入的 command allowlist validation dry-run 函数：
- 逐条判断 command 是否属于允许类别
- 识别 allowlist category
- 识别 forbidden patterns
- 汇总 allowed/rejected/rejection_reasons
- 如果全部命令允许，check_result=pass
- 如果任意命令拒绝，check_result=fail
- 始终 command_execution_blocked=yes
- 始终 ready_for_command_execution=no

### runner.py command-allowlist-dry-run CLI

支持两种调用方式：
- `--sample <name>`: 使用内置 sample（15 个样本）
- `--command "command"`: 使用自定义命令
- 默认：pass-status sample

## Allowlist Rules

### Allowed Categories

| Category | Commands |
|----------|----------|
| status | git status, git log, git diff, git branch, git remote, git tag |
| validation | python runner.py, uv run python runner.py, python -c, uv run python -c |
| test | pytest, uv run pytest, python -m pytest, uv run python -m pytest |

### Forbidden Categories

| Category | Patterns |
|----------|----------|
| Git write | git add, git commit, git push, git reset, git checkout ., git clean, git stash, git merge, git rebase |
| File destruction | rm, del, rmdir, Remove-Item |
| Shell chaining | &&, ;, pipe (\|), redirect (> >>) |
| Network execution | curl \| bash, irm, iex, powershell -ExecutionPolicy Bypass |
| Dangerous | chmod +x, move /Y, copy /Y |
| Framework | run-project-task-full, run_project_task_full |
| Claude Code tool-use | claude --permission-mode acceptEdits, claude --permission-mode bypassPermissions |

## Safety Rules

| Check | Result |
|-------|--------|
| no command execution | yes |
| no real patch apply | yes |
| no run-project-task-full call | yes |
| no Claude Code call | yes |
| no business code modification | yes |
| no real task execution | yes |
| no auto-continue | yes |
| no auto Git backup | yes |
| human review required | yes |

## Verification

15 个 sample 全部验证通过：

| Sample | CHECK_RESULT | COMMANDS_ALLOWED | COMMANDS_REJECTED |
|--------|-------------|-----------------|-------------------|
| pass-status | pass | 3 | 0 |
| pass-validation | pass | 2 | 0 |
| pass-test | pass | 2 | 0 |
| empty-command | fail | 0 | 1 |
| git-add | fail | 0 | 1 |
| git-commit | fail | 0 | 1 |
| git-push | fail | 0 | 1 |
| git-reset | fail | 0 | 1 |
| rm-command | fail | 0 | 1 |
| pipe-command | fail | 0 | 1 |
| redirect-command | fail | 0 | 1 |
| run-project-task-full | fail | 0 | 1 |
| claude-acceptedits | fail | 0 | 1 |
| unknown-command | fail | 0 | 1 |
| mixed-safe-unsafe | fail | 2 | 2 |

所有 15 个场景安全字段均为安全值：
- COMMAND_EXECUTION_BLOCKED=yes (15/15)
- READY_FOR_COMMAND_EXECUTION=no (15/15)
- REAL_PATCH_APPLIED=no (15/15)
- REAL_TASK_EXECUTION=no (15/15)
- RUN_PROJECT_TASK_FULL_CALLED=no (15/15)
- CLAUDE_CODE_CALLED=no (15/15)
- BUSINESS_CODE_CHANGED=no (15/15)

## Decision

```text
COMMAND_ALLOWLIST_VALIDATION_DRY_RUN=implemented
READY_FOR_T126=yes
READY_FOR_REAL_APPLY=no
READY_FOR_STAGE_8=no
```

## Next

T126：执行 first human-reviewed controlled apply dry-run
