# T070 Dev Report

## Task

设计 run-project-loop 调用 run-project-task-full 的安全协议。

## Scope

本轮只生成设计文档，不实现代码。

## Changed Files

- docs/run-project-loop-task-execution-design.md（新增，任务执行桥接设计）
- reports/dev/T070-dev-report.md（本文件）
- docs/tasks.md（T070 状态更新，追加 T071-T076）
- memory/lessons.md（追加 task execution bridge 设计经验）
- memory/pitfalls.md（追加 task execution bridge 设计避坑）

## Design Summary

### 调用协议

- **外层命令**：`python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP`
- **内层调用**：`run_project_task_full(project_path, task_id)` — 直接函数调用，非 subprocess
- **MVP 范围**：max_tasks=1，单任务执行后停止等待人工确认

### 状态模型

- **TaskExecutionResult**：单任务真实执行结果（外层视角），13 个字段
- **ProjectLoopExecutionResult**：run-project-loop 真实执行总结果，18 个字段

### 前后置检查

- **前置检查**：复用 T065 safety gate 的 9 项检查
- **后置检查**：8 项检查（final_status / report / task_status / dev_report / workspace / business_code / rework / blocked）

### 责任划分

- **外层 loop**：安全门、计划、调用、结果收集、继续/停止决策
- **内层 full loop**：Developer / Tester / Reviewer / Main Decision 执行

## Safety Summary

### 停止条件（14 个）

涵盖 safety gate 拒绝、执行失败、执行阻塞、返工需求、报告缺失、workspace 异常、框架代码修改等。

### 安全输出字段

| 字段 | 规则 |
|------|------|
| TASK_EXECUTION_PERFORMED | 执行后必须为 true |
| RUN_PROJECT_TASK_FULL_CALLED | 执行后必须为 true |
| CLAUDE_CODE_CALLED | 默认 unknown，不允许假设 no |
| BUSINESS_CODE_CHANGED | 基于 git diff 检测 |
| GIT_BACKUP_REQUIRED | workspace dirty 时为 true |
| HUMAN_REVIEW_REQUIRED | 失败/阻塞/返工时为 true |

### 验证场景（15 个）

涵盖 safety gate 拒绝（5 个）、执行成功（1 个）、执行失败（3 个）、workspace 异常（2 个）、执行异常（1 个）、停止验证（3 个）。

## Recommended Next Tasks

| 任务 | 目标 |
|------|------|
| T071 | 实现 run-project-task-full adapter dry-run |
| T072 | 验证 adapter 不真实执行 |
| T073 | 实现 max_tasks=1 real-call |
| T074 | 验证 CHECK_RESULT=pass 后停止 |
| T075 | 验证 CHECK_RESULT=fail 后停止 |
| T076 | 提交并推送 task execution bridge MVP |

## Verification

- 工作区初始状态：clean ✓
- 只修改文档：✓（design doc + dev report + tasks + memory）
- 未修改代码：✓（未修改 runner.py / continuous_task_planner.py / full_task_runner.py）
- 未修改业务代码：✓
- 未调用 run-project-task-full：✓
- 未调用 Claude Code：✓

## Next

T071：实现 run-project-task-full adapter dry-run
