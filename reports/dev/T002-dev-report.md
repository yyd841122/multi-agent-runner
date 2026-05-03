# T002 开发报告 — 读取任务清单并找到下一个 pending 任务

## 任务信息

- 任务编号：T002
- 角色：Developer Agent
- 状态：完成

## 修改文件列表

| 文件 | 改动说明 |
|------|----------|
| `docs/tasks.md` | 追加 T002（in_progress）和 T003（pending）任务定义 |
| `tools/task_manager.py` | 实现任务解析：load_tasks_file、parse_tasks、find_next_pending_task |
| `runner.py` | 集成 task_manager，启动时输出下一个 pending 任务 |

## 实现内容

### tools/task_manager.py

- `load_tasks_file(path)` — 读取 tasks.md 文件内容
- `parse_tasks(content)` — 用正则解析任务块，提取 id、title、status、role、goal
- `find_next_pending_task(tasks)` — 遍历任务列表，返回第一个 pending 任务

### runner.py

- 导入 task_manager 三个函数
- 启动时读取 `docs/tasks.md`，解析并输出下一个 pending 任务
- 无 pending 任务时输出提示

## 验收标准自查

- [x] runner.py 可以读取 docs/tasks.md
- [x] 可以解析任务编号、任务名称、状态、角色、目标
- [x] 可以找到第一个状态为 pending 的任务
- [x] 如果没有 pending 任务，可以给出明确提示

## 运行结果

运行 `python runner.py` 后，正确识别 T003 为下一个 pending 任务。

## 是否完成

是。
