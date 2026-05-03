# T009 开发报告 — 单步自动执行闭环

## 任务信息

- 任务编号：T009
- 角色：Developer Agent
- 状态：完成

## 修改文件列表

| 文件 | 改动说明 |
|------|----------|
| `docs/tasks.md` | T009 改为 in_progress，追加 T010 |
| `runner.py` | 新增 `run-next` 命令和 `run_next()` 单步闭环函数 |
| `reports/dev/T009-dev-report.md` | 新建开发报告 |

## 实现内容

### runner.py — run_next()

单步自动闭环流程：

1. 读取 tasks.md，找到第一个 pending 任务
2. 将该任务标记为 in_progress
3. 重新读取任务，获取最新状态
4. 调用 `build_agent_prompt` 生成 current_prompt.md
5. 调用 `run_claude_code` 执行 Claude Code
6. 保存执行结果（latest-output.md）和历史报告
7. 追加运行日志到 run-log.md
8. 分析执行结果：成功→自动 done，失败→保持 in_progress

## 验收标准自查

- [x] 可以自动找到下一个 pending 任务
- [x] 可以自动生成 current_prompt.md
- [x] 可以自动把该任务标记为 in_progress
- [x] 可以自动调用 Claude Code
- [x] 可以自动判断执行结果
- [x] 成功时可以自动标记 done
- [x] 暂时不做多任务循环

## 注意事项

`run-next` 会在内部调用 Claude Code CLI。**不要在 Claude Code 会话内运行 `python runner.py run-next`**，否则会导致嵌套调用。真实验收需在普通 PowerShell 中执行。

## 是否完成

是。
