# T105 Dev Report

## Task

设计 configurable Claude permission mode。

## Scope

本轮只做设计，不修改代码，不调用 Claude Code，不执行真实任务。

## Changed Files

- docs/configurable-claude-permission-mode-design.md（new — 设计文档）
- reports/dev/T105-dev-report.md（new — 本文件）
- docs/tasks.md（modified — T105 状态更新）
- memory/lessons.md（modified — T105 经验追加）
- memory/pitfalls.md（modified — T105 避坑追加）

## Design Summary

### 当前状态

`run_claude_code()` 在 `tools/claude_code_runner.py:39` 硬编码 `--permission-mode acceptEdits`。所有调用方（runner.py / project_runner.py / full_task_runner.py）只传 prompt，无 permission_mode 参数。

### 推荐方案

- **短期**：D + A（底层函数参数 + CLI 参数）
- **中期**：B（环境变量）
- **长期**：C（项目配置）

### 默认值

保持 `acceptEdits` 以兼容历史行为。真实任务诊断时显式传 `default`。

### CLI 参数

`--claude-permission-mode <default|none|acceptEdits|bypassPermissions>`

### 改动范围

| 文件 | 改动 |
|------|------|
| tools/claude_code_runner.py | run_claude_code() 新增 permission_mode 参数 |
| tools/project_runner.py | 透传 permission_mode |
| tools/full_task_runner.py | 透传 permission_mode |
| runner.py | 新增 --claude-permission-mode CLI 参数 |

### 验证场景

20 个验证场景，覆盖默认行为、显式传参、非法值、优先级、安全约束。

## Safety Result

| 检查项 | 结果 |
|--------|------|
| 是否修改代码 | no |
| 是否调用 Claude Code | no |
| 是否运行 run-project-task-full | no |
| 是否修改业务代码 | no |
| 是否修改框架代码 | no |
| 是否自动进入下一任务 | no |
| 是否自动 Git backup | no |

## Next

T106：实现 configurable Claude permission mode
