# T015 开发报告 — 项目需求输入规范化

## 任务信息

- 任务编号：T015
- 角色：Developer Agent
- 状态：完成

## 修改文件列表

| 文件 | 改动说明 |
|------|----------|
| `docs/tasks.md` | T015 状态更新为 in_progress |
| `docs/requirement-protocol.md` | 新建 — 需求协议文档（14 个章节） |
| `templates/requirement-template.md` | 新建 — 需求输入空白模板 |
| `projects/down-100-floors-game/requirement.md` | 新建 — 小游戏验证项目需求示例 |
| `reports/dev/T015-dev-report.md` | 新建 — 开发报告 |

## 完成内容

- 定义需求文件标准格式，包含 16 个标准字段
- 明确机器可读字段和人工说明字段
- 定义 9 种项目类型枚举
- 定义技术栈约束结构（前端/后端/数据库/运行环境/禁止使用）
- 定义功能范围控制：Core Features + MVP Scope + Out of Scope
- 创建空白模板 `templates/requirement-template.md`
- 创建小游戏验证项目需求 `projects/down-100-floors-game/requirement.md`
- 明确 Planner Agent 读取需求文件的流程
- 提供后续接入 runner.py 的建议

## 验收标准自查

- [x] 创建 docs/requirement-protocol.md
- [x] 创建 templates/requirement-template.md
- [x] 创建 projects/down-100-floors-game/requirement.md 示例
- [x] 需求格式包含项目目标、项目类型、技术栈、功能范围、验收标准和不做事项
- [x] 格式服务于后续 Planner Agent 自动拆解任务
- [x] 不修改 Python 执行逻辑
- [x] 不修改 T016 及后续任务状态

## 是否完成

是。
