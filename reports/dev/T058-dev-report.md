# T058 Dev Report

## Task

设计连续任务自动推进协议

## Scope

本轮只生成设计文档和任务状态更新，不实现代码。

## Changed Files

- docs/continuous-task-auto-advance-design.md（新增，设计文档）
- docs/tasks.md（T058 done + T059-T063 pending）
- reports/dev/T058-dev-report.md（本文件）

## Design Summary

核心设计：

1. **新增 `run-project-loop` 命令**：复用 `run-project-task-full`，连续执行多个 pending 任务
2. **默认 dry-run**：只输出计划，不执行任务，需要 `--execute` 才真实执行
3. **`max_tasks` 控制**：默认 3，硬上限 10
4. **任务间安全检查**：每个任务完成后检查工作区、状态、报告
5. **11 种 stop_reason**：覆盖任务失败、工作区异常、rework candidate、达到上限等
6. **9 条 continue 条件**：全部满足才能进入下一个任务

状态模型：

- `ContinuousRunState`：15 个字段，跟踪整个运行周期
- `TaskRunResult`：7 个字段，记录单个任务结果
- `loop_status`：11 种状态枚举

CLI 参数：

- `--project`（必填）、`--max-tasks`（默认 3）、`--start-task`（可选）、`--dry-run`（默认）、`--execute`（需显式传入）

## Safety Summary

停止条件（11 种）：

1. 任务失败（FAILED）
2. 任务阻塞（BLOCKED）
3. 出现 rework candidate（REQUEST_CHANGES）
4. 工作区出现 .py 或 .env 变化
5. 任务状态无法确认
6. 无 pending 任务
7. 达到 max_tasks
8. Developer 超时
9. API 429
10. .env 被修改
11. 工作区初始 dirty

永不自动执行：git push、execute-rework、删除文件、修改 .py/.env

## Recommended Next Tasks

| 任务 | 目标 |
|------|------|
| T059 | 实现 continuous task planner（tools/continuous_runner.py） |
| T060 | 实现 run-project-loop 命令（runner.py 集成） |
| T061 | 验证 max_tasks=1 dry-run |
| T062 | 验证 max_tasks=3 dry-run |
| T063 | 提交并推送第六阶段 MVP |

## Verification

| 检查项 | 结果 |
|--------|------|
| 工作区初始状态 | clean |
| 只修改文档 | yes |
| 未修改代码 | yes |
| 未修改业务代码 | yes |

## Next

T059：实现 continuous task planner
