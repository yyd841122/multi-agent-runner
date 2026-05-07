# T102 First Real Run Smoke Test Check

## Goal

验证一个极小真实任务 G008 是否可以通过 run-project-task-full 完成。

## Execution Target

- Project: projects/down-100-floors-game
- Task: G008 Smoke Test Marker
- Expected output: projects/down-100-floors-game/reports/smoke/G008-smoke-marker.md
- Command: `python runner.py run-project-task-full --project projects/down-100-floors-game --task G008`

## Preflight

- Safety gate (run-project-loop 三重确认): CHECK_RESULT=pass
- Workspace before execution: dirty（docs/tasks.md、子项目 docs/tasks.md 已编辑）
- Stash 后执行 safety gate 通过，stash pop 后执行 G008
- Task id: G008（子项目第一个 pending）

## Real Execution

| 检查项 | 结果 |
|--------|------|
| 执行命令 | `python runner.py run-project-task-full --project projects/down-100-floors-game --task G008` |
| 是否尝试执行 | yes |
| 是否启动 Claude Code | yes |
| 是否超时 | yes |
| child_exit_code | 124 |
| timeout_seconds | 600 |
| 开始时间 | 2026-05-07 17:30:10 |
| 耗时 | 600.1 秒 |
| stdout | (无输出) |
| stderr | "Claude Code execution timed out after 600 seconds." |

## Changed Files

| 文件 | 变更类型 | 是否预期 |
|------|----------|----------|
| docs/tasks.md | modified | yes — T102 验收标准补充 |
| projects/down-100-floors-game/docs/tasks.md | modified | yes — G008 任务新增 |
| projects/down-100-floors-game/prompts/current_prompt.md | modified | yes — G008 prompt |
| reports/run-log.md | modified | yes — G008 运行日志 |
| projects/down-100-floors-game/reports/final/G008-full-loop-report.md | new | yes — 闭环报告 |
| reports/claude/history/20260507-174010-claude-output.md | new | yes — Claude 输出历史 |

**风险文件检查**：无 runner.py、tools/*.py、index.html、style.css、script.js 变更。

## Smoke Marker Check

| 检查项 | 结果 |
|--------|------|
| smoke marker 文件是否存在 | no |
| smoke marker 内容是否正确 | N/A — 文件不存在 |
| 是否修改游戏业务代码 | no |
| 是否修改框架代码 | no |

## Current Finding

T100（框架级任务）和 G008（极小 smoke task）均在 600 秒后超时：

- T100: returncode=124, timeout 600s, Developer BLOCKED
- G008: returncode=124, timeout 600s, Developer BLOCKED

G008 的 prompt 极小且无歧义（只创建一个 smoke marker 文件），仍然超时。

因此当前问题不再主要是任务复杂度或 prompt 矛盾，而是 Claude Code CLI / 模型代理 / API / 网络 / subprocess 执行链路需要诊断。

可能的根因：
1. Claude Code 通过 subprocess 调用时，prompt 作为命令行参数传递，长 prompt 可能影响启动
2. Claude Code 在 subprocess 模式下可能卡在权限确认或初始化阶段
3. 模型 API 连接不稳定或超时
4. 代理/网络问题导致 API 请求无法完成
5. Claude Code --print 模式在 subprocess 中的行为与交互模式不同

## Safety Check

| 检查项 | 结果 |
|--------|------|
| 是否只执行一次 | PASS |
| 是否自动进入下一任务 | no |
| 是否自动 Git backup | no |
| 是否自动返工 | no |
| 是否需要人工验收 | yes |

## Check Result

```text
CHECK_RESULT=review_required
```

原因：G008 smoke task 未完成，Claude Code 超时，需要诊断 Claude Code 执行链路问题。

## Recommended Next

T103：诊断 Claude Code CLI / 模型代理 / API 超时问题

诊断方向：
1. 检查 Claude Code subprocess 调用方式（prompt 参数传递方式）
2. 测试 Claude Code 在 subprocess 中的最小执行能力
3. 检查 API 连接、代理设置、网络状态
4. 尝试不同的 Claude Code 调用参数（如 --max-turns、--model）
5. 如有必要，调整 timeout 或调用方式
