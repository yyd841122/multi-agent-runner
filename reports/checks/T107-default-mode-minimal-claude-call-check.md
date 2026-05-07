# T107 Default Mode Minimal Claude Call Check

## Task

验证 configurable Claude permission mode 实现后，default mode 不传 `--permission-mode`，并确认 Claude Code 最小文本调用可以返回。

## Background

T103 诊断结论：

- text-only：正常（`claude --print "OK"` 秒级返回）
- acceptEdits text-only：正常（`claude --acceptEdits --print "OK"` 秒级返回）
- acceptEdits + tool-use：超时（`claude --acceptEdits --print "创建文件..."` 120 秒无响应）

T106 实现了 configurable Claude permission mode，支持 default / none / acceptEdits / bypassPermissions 四种模式。

本轮验证 default mode 下 Claude Code 最小文本调用是否可以正常返回。

## Dry-run Mapping Check

| # | Mode | CLAUDE_PERMISSION_ARG_PASSED | 结果 |
|---|------|------------------------------|------|
| 1 | default | no | PASS |
| 2 | none | no | PASS |
| 3 | acceptEdits | yes | PASS |
| 4 | bypassPermissions | yes | PASS |

**结果：4/4 PASS**

确认：

- `--claude-permission-mode default` 映射为不传 `--permission-mode`
- `--claude-permission-mode none` 映射为不传 `--permission-mode`
- `--claude-permission-mode acceptEdits` 映射为 `--permission-mode acceptEdits`
- `--claude-permission-mode bypassPermissions` 映射为 `--permission-mode bypassPermissions`

## Minimal Claude Call

| 项 | 值 |
|----|-----|
| command | `claude --print "只回复 OK，不要解释，不要调用工具。"` |
| 是否传 `--permission-mode` | no |
| 是否返回 OK | yes |
| 是否超时 | no |
| 是否触发工具调用 | no |
| 响应时间 | 秒级 |

**DEFAULT_MODE_MINIMAL_PRINT_STATUS=pass**

## Safety Check

| # | 检查项 | 结果 |
|---|--------|------|
| 1 | 是否运行 run-project-task-full | no |
| 2 | 是否执行真实任务 | no |
| 3 | 是否调用 tool-use | no |
| 4 | 是否写文件 | no |
| 5 | 是否修改业务代码 | no |
| 6 | 是否修改框架代码 | no |

**结果：6/6 PASS**

## Result

```text
DEFAULT_MODE_MINIMAL_PRINT_STATUS=pass
CHECK_RESULT=pass
```
