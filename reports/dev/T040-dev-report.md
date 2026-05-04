# T040 开发报告 — 自动返工协议设计

## 任务信息

- 任务编号：T040
- 角色：Architect
- 状态：完成

## 修改文件列表

| 文件 | 改动说明 |
|------|----------|
| `docs/tasks.md` | T040 状态 pending → in_progress → done |
| `docs/rework-protocol.md` | 新建 — 返工协议（14 章） |
| `docs/main-agent-decision-protocol.md` | 追加返工决策扩展章节 |
| `docs/project-runner-protocol.md` | 追加返工任务支持章节 |
| `templates/rework/rework-task-template.md` | 新建 — 返工任务模板 |
| `templates/rework/rework-prompt-template.md` | 新建 — 返工 prompt 模板 |
| `memory/lessons.md` | 追加 T040 经验（5 条） |
| `memory/pitfalls.md` | 追加 T040 避坑（6 条） |
| `reports/final/T040-rework-protocol.md` | 新建 — 协议报告（10 章） |
| `reports/dev/T040-dev-report.md` | 新建 — 开发报告 |

## 完成内容

- 创建返工协议文档（14 章）
- 定义返工触发条件（5 种可触发 / 4 种不触发）
- 定义返工输入来源（7 类报告）
- 定义返工任务命名规则（G004-R1 格式）
- 定义返工 prompt 生成规则（12 项必须内容）
- 定义返工完成证据路径
- 定义返工后验证链路
- 定义人工确认边界
- 创建返工任务模板和 prompt 模板
- 更新 main-agent-decision-protocol.md 和 project-runner-protocol.md

## 验收标准自查

- [x] 创建 docs/rework-protocol.md
- [x] 创建返工任务模板
- [x] 创建返工 prompt 模板
- [x] 明确返工触发条件
- [x] 明确返工输入来源
- [x] 明确返工任务命名规则
- [x] 明确返工完成证据路径
- [x] 明确人工确认边界
- [x] 不自动执行返工

## 限制遵守

- 未修改任何 Python 代码
- 未实现返工工具
- 未执行返工
- 未修改小游戏业务代码
- 未执行测试、审查、综合决策命令
- 未调用 DeepSeek API
- 未开始 T041
- 所有文档使用简体中文
- 文件名、路径、代码关键字保持英文

## 是否完成

是。
