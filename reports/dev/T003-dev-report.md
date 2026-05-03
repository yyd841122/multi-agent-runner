# T003 开发报告 — 实现任务状态自动更新

## 任务信息

- 任务编号：T003
- 角色：Developer Agent
- 状态：完成

## 修改文件列表

| 文件 | 改动说明 |
|------|----------|
| `docs/tasks.md` | 原 T003 改为 T004，新增 T003 任务定义 |
| `tools/task_manager.py` | 新增 `update_task_status`、`save_tasks_file` 函数 |
| `runner.py` | 支持 `complete`、`start` 命令，新增用法提示 |
| `reports/dev/T003-dev-report.md` | 新建开发报告 |

## 实现内容

### tools/task_manager.py 新增

- `save_tasks_file(path, content)` — 将内容写回 tasks.md
- `update_task_status(content, task_id, new_status)` — 用正则定位任务块中的"状态"行并替换，找不到时抛出 ValueError

### runner.py 新增

- `show_next_pending()` — 显示下一个 pending 任务（原有逻辑抽取为函数）
- `change_status(task_id, new_status)` — 读取→更新状态→写回
- 命令行参数解析：
  - 无参数 → 显示下一个 pending 任务
  - `complete T00x` → 状态改为 done
  - `start T00x` → 状态改为 in_progress
  - 其他 → 显示用法提示

## 验收标准自查

- [x] 可以通过命令把指定任务状态改为 done
- [x] 可以通过命令把指定任务状态改为 in_progress
- [x] 修改后 docs/tasks.md 内容保持原有结构
- [x] 如果任务编号不存在，给出明确提示
- [x] 不需要手动修改任务状态

## 运行结果

验证命令及预期输出：

1. `python runner.py` → 识别 T004 为下一个 pending 任务
2. `python runner.py complete T003` → T003 状态变为 done
3. `python runner.py start T004` → T004 状态变为 in_progress
4. `python runner.py` → 当前没有 pending 任务

## 是否完成

是。
