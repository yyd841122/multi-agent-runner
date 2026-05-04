# T025 开发报告 — 实现通用 run-project-next MVP

## 任务信息

- 任务编号：T025
- 角色：Developer Agent
- 状态：完成

## 修改文件列表

| 文件 | 改动说明 |
|------|----------|
| `tools/project_runner.py` | 新建 — 通用 project runner 模块 |
| `runner.py` | 新增 `run-project-next` 命令 + `_handle_run_project_next` 输出格式化 |
| `docs/tasks.md` | T025 状态更新为 done |
| `projects/down-100-floors-game/docs/tasks.md` | 追加 G003 实现玩家角色显示任务 |

## 完成内容

### tools/project_runner.py（新建）

- `validate_project_root()` — 校验项目路径存在性
- `get_project_tasks_file()` — 返回子项目 tasks.md 路径
- `get_project_dev_report_path()` — 返回子项目开发报告路径
- `parse_project_tasks()` — 通用任务解析（支持任意前缀 G/T/P 等）
- `find_next_pending_project_task()` — 找到第一个 pending 任务
- `update_project_task_status()` — 更新子项目任务状态
- `build_project_task_prompt()` — 生成子项目任务 Claude Code prompt
- `run_project_next()` — 主执行函数（完整闭环）

### runner.py 新增

- import `run_project_next`
- `run-project-next` 命令路由（支持 `--project <path>` 和简化 `<path>` 两种形式）
- `_handle_run_project_next()` — 结果格式化输出
- 帮助文本新增 `run-project-next` 说明

### G003 任务追加

在 `projects/down-100-floors-game/docs/tasks.md` 中追加 G003 实现玩家角色显示任务（pending），用于真实验收。

## 验收标准自查

- [x] 创建 tools/project_runner.py
- [x] runner.py 新增 run-project-next 命令
- [x] 支持 `--project <project-path>` 参数
- [x] 可以读取 `<project>/docs/tasks.md`
- [x] 可以找到第一个 pending 任务
- [x] 可以把任务标记为 in_progress
- [x] 可以生成子项目任务 prompt
- [x] 可以调用 Claude Code 执行
- [x] 可以检查 `<project>/reports/dev/<task-id>-dev-report.md`
- [x] 成功且有完成证据时自动标记 done
- [x] 暂时只实现单任务执行，不做多任务循环
- [x] 保留 run-game-next 作为兼容命令
- [x] 不破坏已有命令

## 注意事项

**run-project-next 需要在普通 PowerShell 中验收，避免 Claude Code 嵌套调用。**

验收步骤：
```powershell
python runner.py run-project-next --project projects/down-100-floors-game
```

然后检查：
```powershell
Test-Path projects\down-100-floors-game\reports\dev\G003-dev-report.md
Get-Content projects\down-100-floors-game\docs\tasks.md -Encoding UTF8
```

## 限制遵守

- 未删除 run-game-next 命令
- 未接入真实模型 API
- 未做多任务循环
- 未修改 tools/model_adapter.py / planner_runner.py / main_agent.py / reviewer_runner.py / claude_code_runner.py
- 未修改 config.yaml / workflows/*.yaml / agents/*.md
- 未在 Claude Code 会话内执行 run-project-next
- 未实现 G003 业务内容
- 所有文档使用简体中文
- 文件名、路径、命令保持英文

## 是否完成

是。
