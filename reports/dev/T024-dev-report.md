# T024 开发报告 — 通用 project runner 协议设计

## 任务信息

- 任务编号：T024
- 角色：Architect Agent
- 状态：完成

## 修改文件列表

| 文件 | 改动说明 |
|------|----------|
| `docs/tasks.md` | T024 状态更新为 in_progress |
| `docs/project-runner-protocol.md` | 新建 — 通用 project runner 协议（15 章） |
| `templates/project-runner/project-config-template.yaml` | 新建 — 项目配置模板（带注释） |
| `reports/final/T024-project-runner-protocol.md` | 新建 — 协议设计报告 |
| `memory/lessons.md` | 追加 T024 协议设计经验 |
| `memory/pitfalls.md` | 追加 T024 协议设计避坑 |
| `reports/dev/T024-dev-report.md` | 新建 — 开发报告 |

## 完成内容

- 定义项目标准目录约定
- 设计 project.yaml 配置格式（10 个配置段）
- 定义命令形式（最小命令 + 可选扩展 + 兼容命令）
- 定义 prompt 生成规则（10 项必须内容 + 模板结构）
- 定义完成证据规则（3 个 Agent 类型 + 路径动态计算）
- 定义报告保存规则（5 种报告类型 + 主框架日志）
- 定义状态更新规则（4 种条件 + 扩展状态预留）
- 定义失败处理规则（8 种失败场景 + 6 条处理原则）
- 定义安全规则（8 条安全约束）
- 提供 T025 实现建议（最小实现路径 + 代码组织 + 验证步骤）

## 验收标准自查

- [x] 创建 docs/project-runner-protocol.md
- [x] 创建 templates/project-runner/project-config-template.yaml
- [x] 明确 project runner 的命令形式
- [x] 明确项目路径参数
- [x] 明确子项目任务文件路径
- [x] 明确任务编号前缀规则
- [x] 明确完成证据路径
- [x] 明确 prompt 生成规则
- [x] 明确报告保存规则
- [x] 明确失败处理规则
- [x] 不修改 Python 执行逻辑

## 限制遵守

- 未修改 runner.py
- 未修改 tools/*.py
- 未修改 agents/*.md
- 未修改 config.yaml
- 未修改 workflows/*.yaml
- 未修改 projects/down-100-floors-game/*
- 未实现 run-project-next
- 未接入真实模型 API
- 未执行自动开发命令
- 所有文档使用简体中文
- 文件名、路径、命令保持英文

## 是否完成

是。
