# T059 Dev Report

## Task

实现 continuous task planner（dry-run 计划生成）

## Scope

本轮只实现 dry-run 计划生成模块和 runner.py 命令入口，不执行任务，不调用 Claude Code。

## Changed Files

- tools/continuous_task_planner.py（新增，计划生成核心模块）
- runner.py（新增 `plan-project-loop` 命令入口）
- reports/dev/T059-dev-report.md（本文件）

## Implementation Summary

### tools/continuous_task_planner.py

核心数据结构：

- `PlannedTask`：计划中的单个任务（task_id, title, status, order, reason）
- `ContinuousTaskPlan`：连续任务推进计划（15 个字段，含 plan_status, stop_reason, next_action 等）

核心函数：

- `_validate_max_tasks(max_tasks)`：校验 max_tasks，< 1 返回无效，> 10 裁剪到硬上限
- `build_continuous_task_plan(project_root, max_tasks, dry_run)`：从 docs/tasks.md 读取任务列表，生成执行计划

计划状态（plan_status）：
- `planned`：正常生成计划
- `no_pending_task`：没有 pending 任务
- `invalid_max_tasks`：max_tasks 参数无效

### runner.py 新增命令

`plan-project-loop --project <path> [--max-tasks N]`

输出格式：
```
PLAN_STATUS=planned
NEXT_PENDING=T059
PLANNED_TASKS=T059,T060,T061
MAX_TASKS=3
HARD_LIMIT=10
DRY_RUN=True
NEXT_ACTION=ready_for_run_project_loop
```

### 设计决策

1. **文件名 `continuous_task_planner.py`**：而非设计文档中建议的 `continuous_runner.py`，因为 T059 只做计划生成，不含运行逻辑，命名更准确
2. **复用 `task_manager.parse_tasks()` 和 `load_tasks_file()`**：不重复实现任务解析
3. **命令名 `plan-project-loop`**：而非 `run-project-loop`，因为当前只做 dry-run 计划，真正的 `run-project-loop` 将在 T060 实现

## Verification Results

| # | 场景 | 结果 |
|---|------|------|
| 1 | 默认 max_tasks=3 | PASS — PLANNED_TASKS=T059,T060,T061 |
| 2 | max_tasks=1 | PASS — PLANNED_TASKS=T059 |
| 3 | max_tasks=3 显式 | PASS — PLANNED_TASKS=T059,T060,T061 |
| 4 | max_tasks=0 被拒绝 | PASS — PLAN_STATUS=invalid_max_tasks |
| 5 | max_tasks=100 裁剪为 10 | PASS — MAX_TASKS=10, PLANNED_TASKS 全部 5 个 pending |
| 6 | 没有执行任何任务 | PASS — 只有框架代码变化，无任务执行 |
| 7 | 没有调用 Claude Code | PASS — continuous_task_planner.py 无 claude 引用 |
| 8 | 没有修改业务代码 | PASS — 无 .html/.css/.js/.env 变化 |

## Safety Summary

- T059 始终 dry_run=True，不执行任何任务
- 不调用 Claude Code
- 不修改业务代码
- max_tasks 硬上限 10

## Recommended Next Tasks

| 任务 | 目标 |
|------|------|
| T060 | 实现 run-project-loop 命令（runner.py 集成 execute 分支） |
| T061 | 验证 max_tasks=1 dry-run |
| T062 | 验证 max_tasks=3 dry-run |
| T063 | 提交并推送第六阶段 MVP |

## Verification

| 检查项 | 结果 |
|--------|------|
| 工作区初始状态 | clean |
| 只修改框架代码 | yes |
| 未修改业务代码 | yes |
| 未调用 Claude Code | yes |
| dry-run 模式 | yes |

## Next

T060：实现 run-project-loop 命令（execute 分支）
