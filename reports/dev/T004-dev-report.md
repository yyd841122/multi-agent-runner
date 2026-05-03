# T004 开发报告 — 生成当前任务提示词

## 任务信息

- 任务编号：T004
- 角色：Developer Agent
- 状态：完成

## 修改文件列表

| 文件 | 改动说明 |
|------|----------|
| `docs/tasks.md` | T004 改为 in_progress，追加 T005（自动调用 Claude Code） |
| `tools/workflow_manager.py` | 实现 `build_agent_prompt(task)` 函数 |
| `runner.py` | 新增 `generate-prompt` 命令和 `generate_prompt()` 函数 |
| `prompts/current_prompt.md` | 由 runner 自动生成（不再手动维护） |
| `reports/dev/T004-dev-report.md` | 新建开发报告 |

## 实现内容

### tools/workflow_manager.py

- `build_agent_prompt(task)` — 根据任务 dict 生成结构化提示词，包含角色、任务编号、名称、状态、目标、原始内容、工作要求

### runner.py

- `generate_prompt()` — 读取 tasks.md → 找到 pending 任务 → 调用 build_agent_prompt → 写入 prompts/current_prompt.md
- 新增 `generate-prompt` 命令支持

## 验收标准自查

- [x] runner.py 可以根据 pending 任务生成提示词
- [x] prompts/current_prompt.md 内容包含任务编号、任务名称、角色、目标、验收标准
- [x] 暂时不调用 Claude Code

## 运行结果

1. `python runner.py` → 识别 T005 为下一个 pending 任务
2. `python runner.py generate-prompt` → 生成 prompts/current_prompt.md，内容包含 T005 完整信息

## 是否完成

是。
