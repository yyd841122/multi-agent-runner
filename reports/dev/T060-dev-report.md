# T060 Dev Report

## Task

实现 run-project-loop dry-run — 连续任务模拟推进，不执行真实任务。

## Scope

本轮只实现 loop dry-run 模拟推进，复用 T059 planner 输出，为每个 planned task 生成模拟结果，不调用 run-project-task-full，不调用 Claude Code，不修改业务代码。

## Changed Files

- tools/continuous_task_planner.py（扩展：新增 TaskRunResult、ContinuousLoopRunResult、run_project_loop_dry_run()）
- runner.py（新增 run-project-loop 命令入口）
- reports/dev/T060-dev-report.md（本文件）

## Implementation

### TaskRunResult

单任务 dry-run 模拟结果数据结构：

- `task_id` / `title`：任务标识
- `dry_run=True`：始终 True
- `execution_performed=False`：始终 False
- `check_result=pass`：模拟通过
- `task_status=dry_run_planned`：模拟状态
- `stop_reason`：None 或 `max_tasks_reached`
- `next_action`：`continue_to_next_planned_task` / `review_loop_summary`

### ContinuousLoopRunResult

Loop 级别总结果数据结构：

- `run_id`：`loop-YYYYMMDD-HHMMSS-<6位hex>` 格式
- `dry_run=True`
- `planned_tasks` / `completed_tasks`：task_id 列表（dry-run 中两者相同）
- `failed_tasks=[]` / `skipped_tasks=[]`：始终空
- `loop_status`：`dry_run_completed` / `stopped_on_max_tasks` / `no_pending_task` / `invalid_max_tasks`
- `stop_reason`：`max_tasks_reached` / `all_planned_tasks_simulated` / 错误信息
- `task_results`：每个任务的 TaskRunResult 列表
- `next_action`：`review_loop_summary` / `fix_parameters_or_check_tasks`

### run_project_loop_dry_run()

核心函数逻辑：

1. 调用 `build_continuous_task_plan()` 获取计划
2. 如果 plan_status 不是 planned，返回停止状态（invalid_max_tasks / no_pending_task）
3. 遍历 planned_tasks，为每个生成 TaskRunResult
4. 最后一个 planned task 判断是否达到 max_tasks 上限
5. 检查是否还有未 planned 的 pending task，确定 next_task
6. 生成 ContinuousLoopRunResult

### run-project-loop CLI

命令：`python runner.py run-project-loop [--max-tasks N] [--dry-run]`

- 默认 dry-run
- `--execute` 被明确拒绝，提示 not supported
- 输出包含：LOOP_STATUS、RUN_ID、DRY_RUN、MAX_TASKS、PLANNED_TASKS、COMPLETED_TASKS、FAILED_TASKS、STOP_REASON、TASK_EXECUTION_PERFORMED=false、CLAUDE_CODE_CALLED=false、BUSINESS_CODE_CHANGED=false、NEXT_ACTION
- 额外输出每个 task 的详细结果

## Behavior

### 如何复用 planner

- `run_project_loop_dry_run()` 内部调用 `build_continuous_task_plan()` 获取计划
- 复用 T059 的 max_tasks 校验、任务解析和 pending 任务收集逻辑
- 不重复实现任务读取

### 如何模拟 planned_tasks

- 每个 planned task 生成一个 `TaskRunResult`，标记 `dry_run=True`、`execution_performed=False`
- 非最后一个 task 的 `next_action=continue_to_next_planned_task`
- 最后一个 task 根据是否达到 max_tasks 设置 `stop_reason`

### max_tasks 行为

- `< 1`：返回 `invalid_max_tasks`
- `> 10`：裁剪到 10（由 planner 的 `_validate_max_tasks` 处理）
- `1-10`：正常取前 N 个 pending task

### stop_reason 行为

| 场景 | loop_status | stop_reason |
|------|------------|-------------|
| max_tasks=0 | invalid_max_tasks | max_tasks=0 无效 |
| 无 pending | no_pending_task | 没有 pending 任务 |
| pending < max_tasks | dry_run_completed | all_planned_tasks_simulated |
| pending >= max_tasks | stopped_on_max_tasks | max_tasks_reached |

## Safety Rules

- dry-run only：本轮不实现 --execute
- no run-project-task-full call：continuous_task_planner.py 中无 run_project_task_full 引用
- no Claude Code call：不调用 claude_code_runner
- no business code modification：只修改框架代码
- --execute not supported：明确拒绝并提示

## Verification

| # | 场景 | 结果 |
|---|------|------|
| 1 | max_tasks=1 dry-run 只模拟 1 个任务 | PASS — PLANNED_TASKS=T060, STOP_REASON=max_tasks_reached |
| 2 | max_tasks=3 dry-run 最多模拟 3 个任务 | PASS — PLANNED_TASKS=T060,T061,T062, NEXT_TASK=T063 |
| 3 | max_tasks=0 被拒绝 | PASS — LOOP_STATUS=invalid_max_tasks |
| 4 | max_tasks=11 安全处理（裁剪到 10） | PASS — MAX_TASKS=10 |
| 5 | 输出包含 RUN_ID | PASS — 格式 loop-YYYYMMDD-HHMMSS-<6hex> |
| 6 | 输出包含 TASK_EXECUTION_PERFORMED=false | PASS |
| 7 | 输出包含 CLAUDE_CODE_CALLED=false | PASS |
| 8 | 不调用 run-project-task-full | PASS — 代码中无引用 |
| 9 | 不修改业务代码 | PASS — 只修改 runner.py 和 continuous_task_planner.py |

## Next

T061：验证 max_tasks=1 dry-run
