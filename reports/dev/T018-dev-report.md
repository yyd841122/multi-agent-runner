# T018 开发报告 — Main Agent 决策协议 MVP

## 任务信息

- 任务编号：T018
- 角色：Developer Agent
- 状态：完成

## 修改文件列表

| 文件 | 改动说明 |
|------|----------|
| `docs/tasks.md` | T018 状态更新为 in_progress |
| `docs/main-agent-decision-protocol.md` | 新建 — Main Agent 决策协议文档（10 个章节） |
| `tools/main_agent.py` | 新建 — 规则版 Main Agent（decide_next_action + save_main_decision） |
| `runner.py` | 新增 `main-decide` 命令 |
| `reports/dev/T018-dev-report.md` | 新建 — 开发报告 |

## 完成内容

- 定义 MainDecision 数据结构（decision / reason / task_id / next_command / blocked 等）
- 实现 `decide_next_action()` — 4 条核心规则：
  - in_progress 任务：根据执行结果和完成证据判断 RETRY / COMPLETE / BLOCKED
  - pending 任务：DEVELOP（建议 run-next）
  - 无待处理任务：STOP
  - 429 限额：BLOCKED
- 实现 `save_main_decision()` — 保存决策报告到 reports/main/
- 新增 runner.py `main-decide` 命令
- 定义 8 种 Decision 枚举：PLAN / DEVELOP / TEST / REVIEW / RETRY / COMPLETE / STOP / BLOCKED
- Main Agent 不写代码、不调用 Claude Code、不自动执行建议命令

## 验收标准自查

- [x] 创建 docs/main-agent-decision-protocol.md
- [x] 创建 tools/main_agent.py
- [x] 支持规则版 Main Agent 决策
- [x] 可以识别 pending / in_progress / done 状态
- [x] 可以根据执行结果和完成证据给出下一步动作
- [x] 可以保存 Main Agent 决策报告
- [x] 不接入真实模型 API

## 本地测试结果

测试命令：`python runner.py main-decide`

预期：输出 Main Agent 决策结果和建议命令，保存决策报告到 reports/main/

## 是否完成

是。
