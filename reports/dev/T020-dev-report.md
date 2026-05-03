# T020 开发报告 — 使用 runner 自动执行小游戏第一个开发任务

## 任务信息

- 任务编号：T020
- 角色：Developer Agent
- 状态：完成

## 修改文件列表

| 文件 | 改动说明 |
|------|----------|
| `docs/tasks.md` | T020 状态更新为 in_progress |
| `runner.py` | 新增 `run-game-next` 命令 + 游戏任务解析函数 + 游戏项目常量 |
| `reports/dev/T020-dev-report.md` | 新建 — 开发报告 |

## 完成内容

- 新增 `run-game-next` 命令，完整闭环：
  1. 读取 `projects/down-100-floors-game/docs/tasks.md`
  2. 解析 G 前缀任务，找到第一个 pending
  3. 标记为 in_progress
  4. 生成包含明确边界的 G002 prompt
  5. 调用 Claude Code 执行
  6. 保存执行结果到主项目 reports/claude/
  7. 检查完成证据 `projects/down-100-floors-game/reports/dev/G002-dev-report.md`
  8. 有证据则标记 done，缺少证据则保持 in_progress
- 游戏任务解析函数：`parse_game_tasks` / `find_next_pending_game_task` / `update_game_task_status`
- G002 prompt 明确限制：只做基础页面布局，不实现游戏逻辑
- G002 prompt 明确完成证据：必须创建 `G002-dev-report.md`

## 验收标准自查

- [x] runner.py 新增 run-game-next 命令
- [x] 可以读取 projects/down-100-floors-game/docs/tasks.md
- [x] 可以找到 G002 pending 任务
- [x] 可以自动生成 G002 执行提示词
- [x] 可以自动调用 Claude Code 修改小游戏项目文件
- [x] 可以生成 projects/down-100-floors-game/reports/dev/G002-dev-report.md（由 Claude Code 执行时生成）
- [x] 成功且有完成证据时，G002 自动标记为 done
- [x] 不实现玩家移动、平台、重力、碰撞等复杂游戏逻辑

## 注意事项

`run-game-next` 需要在普通 PowerShell 中验收，避免 Claude Code 嵌套调用。

验收命令：
```
python runner.py run-game-next
```

验收检查：
```
Test-Path projects\down-100-floors-game\reports\dev\G002-dev-report.md
Get-Content projects\down-100-floors-game\docs\tasks.md -Encoding UTF8
```

## 是否完成

是。
