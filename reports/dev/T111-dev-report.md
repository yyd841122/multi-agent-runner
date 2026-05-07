# T111 Dev Report

## Task

设计 layered Claude Code stability validation protocol。

## Scope

本轮只做协议设计，不调用 Claude Code，不执行真实任务，不修改代码。

## Changed Files

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| docs/layered-claude-code-stability-validation-protocol.md | new | 分层稳定性验证协议文档 |
| reports/dev/T111-dev-report.md | new | 本文件 |
| docs/tasks.md | modified | T111 状态更新 |
| memory/lessons.md | modified | 追加 T111 经验 |
| memory/pitfalls.md | modified | 追加 T111 避坑记录 |

## Protocol Summary

### Layer 1: Text-only Stability

- 目标：验证 Claude Code 文本输出路径稳定
- 测试：default text-only 3 次 + acceptEdits text-only 3 次
- 通过标准：6/6 全部 pass，秒级返回
- 超时上限：60 秒
- 失败处理：停止后续层，检查网络/API

### Layer 2: Controlled Single-file Tool-use Stability

- 目标：验证受控 tool-use 写文件是否稳定
- 测试：acceptEdits + 创建临时文件，最多 3 次
- 通过标准：3/3 成功创建，无超时
- 超时上限：120 秒
- 文件范围：`reports/diagnostics/tool-use/`
- 失败处理：停止后续层，考虑路线 B

### Layer 3: Runner-level Minimal Claude Call

- 目标：验证 runner 封装层调用 Claude Code 的最小路径
- 测试：通过 `run_claude_code()` 调用，text-only + controlled tool-use
- 通过标准：2/2 pass，runner 封装正常
- 超时上限：60 秒/120 秒
- 失败处理：排查 runner 链路，考虑路线 B/C

### Layer 4: run-project-task-full Smoke Gate

- 目标：恢复 G008/G009 smoke test 的人工批准门
- 不是自动执行，需要 T116 人工决策
- 允许条件：Layer 1-3 全部通过 + 人工批准

### Stop Rules

- 任何一层出现 timeout、unexpected file modification、business code changed、framework code changed、Claude Code no response、API 429、permission mode mismatch、tool-use unexpected behavior、dirty_unknown workspace 时必须停止

### Safety Rules

- 不自动进入下一层
- 不自动 Git backup
- 不自动重试
- 任何异常都人工验收
- 不修改业务代码
- 不修改框架代码
- 不使用 bypassPermissions
- 不执行 run-project-task-full（Layer 1-3）
- Layer 4 需要人工决策

## Evidence Summary

### 证据表（来自 T100-T110）

| Task | Scenario | Result | Layer 依据 |
|------|----------|--------|-----------|
| T100 | full run-project-task-full | timeout (600s) | Layer 4 尚未通过 |
| T102 | G008 smoke task | timeout (600s) | Layer 4 尚未通过 |
| T103 | acceptEdits + tool-use | timeout (120s) | Layer 2 需验证 |
| T103 | default text-only | pass | Layer 1 有先例 |
| T103 | acceptEdits text-only | pass | Layer 1 有先例 |
| T107 | default text-only | pass | Layer 1 有先例 |
| T108 | default text-only | pass | Layer 1 有先例 |
| T108 | acceptEdits text-only | pass | Layer 1 有先例 |
| T108 | acceptEdits + tool-use | unexpected_pass | Layer 2 需验证稳定性 |
| T109 | compatibility assessment | unstable | 分层验证的必要性 |

## Safety Result

| 检查项 | 结果 |
|--------|------|
| 是否运行 run-project-task-full | no |
| 是否调用 Claude Code | no |
| 是否执行真实任务 | no |
| 是否修改业务代码 | no |
| 是否修改框架代码 | no |
| 是否使用 bypassPermissions | no |
| 是否自动 Git backup | no |

## Decision

```text
T111_PROTOCOL_STATUS=done
LAYERED_VALIDATION_PROTOCOL=yes
NEXT_EXECUTION_ALLOWED=no
NEXT_REAL_TASK_ALLOWED=no
NEXT_SMOKE_TEST_ALLOWED=no
```

## Next

T112：实现 text-only stability check dry-run/report skeleton
