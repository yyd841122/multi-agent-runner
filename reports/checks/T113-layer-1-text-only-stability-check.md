# T113 Layer 1 Text-only Stability Check

## Goal

验证 Claude Code text-only 输出链路在连续多次调用中保持稳定，不触发 tool-use，不写文件，不修改项目。

## Preflight

- **workspace before**: clean
- **dry-run plan result**: LAYER=1, DRY_RUN=true, COMMAND_COUNT=6, CHECK_RESULT=pass
- **command count**: 6 (3x default text-only + 3x acceptEdits text-only)

## Commands

### Default text-only (3 次)

| # | Command | Timeout | Output | Time | Result |
|---|---------|---------|--------|------|--------|
| 1 | `claude --print "只回复 OK，不要解释，不要调用工具。"` | 60s | OK | <5s | pass |
| 2 | `claude --print "只回复 OK，不要解释，不要调用工具。"` | 60s | 好的 | <5s | pass |
| 3 | `claude --print "只回复 OK，不要解释，不要调用工具。"` | 60s | 好的 | <5s | pass |

### acceptEdits text-only (3 次)

| # | Command | Timeout | Output | Time | Result |
|---|---------|---------|--------|------|--------|
| 4 | `claude --permission-mode acceptEdits --print "只回复 OK，不要解释，不要调用工具。"` | 60s | OK | <5s | pass |
| 5 | `claude --permission-mode acceptEdits --print "只回复 OK，不要解释，不要调用工具。"` | 60s | OK | <5s | pass |
| 6 | `claude --permission-mode acceptEdits --print "只回复 OK，不要解释，不要调用工具。"` | 60s | OK | <5s | pass |

## Expected Result

- 6/6 返回 OK 或等价确认
- 无 tool-use 触发
- 无文件修改
- 无 timeout
- 不运行 run-project-task-full

## Actual Result

| 检查项 | 结果 |
|--------|------|
| 6/6 返回 OK 或等价确认 | 6/6 pass（run 1: "OK", run 2: "好的", run 3: "好的", run 4: "OK", run 5: "OK", run 6: "OK"） |
| 无 tool-use 触发 | 无（全部纯文本输出） |
| 无文件修改 | 无（workspace 保持 clean） |
| 无 timeout | 无（全部 <5s 秒级返回） |
| 不运行 run-project-task-full | no |

## Timeout Settings

- 每次调用超时上限：60 秒
- 实际全部 <5 秒

## Permission Mode

- 测试 1-3：default（不传 --permission-mode）
- 测试 4-6：acceptEdits（--permission-mode acceptEdits）

## Stdout/Stderr Summary

- 所有 6 次调用 stdout 正常返回文本
- 无 stderr 输出
- 无异常信息

## Changed Files

- 无文件变更（workspace 保持 clean）

## Safety Check

| 检查项 | 结果 |
|--------|------|
| 是否运行 run-project-task-full | no |
| 是否调用 Claude Code | yes（text-only，6 次调用） |
| 是否调用 tool-use | no |
| 是否写文件 | no |
| 是否执行真实任务 | no |
| 是否修改业务代码 | no |
| 是否修改框架代码 | no |
| 是否使用 bypassPermissions | no |
| 是否自动 Git backup | no |

## Layer 1 Result

```text
LAYER_1_STATUS=pass
TEXT_ONLY_STABILITY=stable
DEFAULT_TEXT_PASS_COUNT=3/3
DEFAULT_TEXT_FAIL_COUNT=0/3
ACCEPTEDITS_TEXT_PASS_COUNT=3/3
ACCEPTEDITS_TEXT_FAIL_COUNT=0/3
CHECK_RESULT=pass
```

## Next

T114：执行 Layer 2 controlled single-file tool-use stability validation
