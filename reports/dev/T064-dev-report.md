# T064 Dev Report

## Task

设计 run-project-loop execute mode 安全协议。

## Scope

本轮只生成设计文档，不实现代码。定义 execute mode 的安全边界、确认机制、状态模型、前置检查、继续条件、停止条件和 CLI 方案。

## Changed Files

- docs/run-project-loop-execute-safety-design.md（新增，execute mode 安全协议设计）
- reports/dev/T064-dev-report.md（本文件）
- docs/tasks.md（更新 T064 状态为 done，追加 T065-T069）
- memory/lessons.md（追加 execute mode 设计经验）
- memory/pitfalls.md（追加 execute mode 设计避坑）

## Design Summary

### execute mode 核心设计

1. **确认协议**：`--execute --confirm EXECUTE_PROJECT_LOOP`，精确匹配，不接受 yes/ok/确认等模糊确认
2. **状态模型**：`ExecuteLoopState` 包含 21 个字段，覆盖执行状态、确认状态、工作区状态、Git 状态
3. **前置检查**：9 项 preflight check，任一不满足即停止
4. **继续条件**：10 项条件全部满足才允许进入下一个任务
5. **停止条件**：19 种停止条件，覆盖确认失败、执行失败、工作区异常、安全边界等
6. **CLI 方案**：推荐方案 A（在 run-project-loop 上启用 --execute），复用现有命令入口
7. **硬限制差异**：dry-run max_tasks 硬限制 10，execute mode 硬限制 3

### 关键设计决策

| 决策 | 结论 | 原因 |
|------|------|------|
| CLI 方案 | 方案 A（复用 run-project-loop） | 最小改动，复用 planner，用户熟悉 |
| 确认短语 | EXECUTE_PROJECT_LOOP | 精确匹配，避免模糊确认 |
| execute max_tasks 硬限制 | 3（MVP 只允许 1） | 真实执行失败代价高 |
| rework 处理 | 停止，不自动执行 execute-rework | rework 需要人工确认 |
| Git backup | 停止并提醒，不自动 push | push 需要人工确认 |

## Safety Summary

### 确认机制

- 默认 dry-run，不传 `--execute` 时行为不变
- `--execute` 必须配合 `--confirm EXECUTE_PROJECT_LOOP`
- yes/ok/y/确认/同意/continue/true/1 全部拒绝
- `--execute` 和 `--dry-run` 互斥

### 前置检查（9 项）

工作区 clean、确认正确、max_tasks 合法、planned_tasks 非空、NEXT_PENDING 存在、run_project_task_full 可用、无 pending rework、无 in_progress 任务

### 停止条件（19 种）

涵盖确认失败（3 种）、执行失败（6 种）、工作区异常（2 种）、安全边界（4 种）、自然结束（2 种）、其他（2 种）

### 永不自动执行

git push、execute-rework、删除文件、修改 .py/.env、无限循环、跳过 Tester/Reviewer

## Recommended Next Tasks

| 任务 | 目标 |
|------|------|
| T065 | 实现 execute mode safety gate（preflight 检查、确认协议、execute 硬限制） |
| T066 | 实现 max_tasks=1 execute stub（最小 execute 实现） |
| T067 | 验证 execute confirm 拒绝场景（场景 1-9, 15） |
| T068 | 验证 max_tasks=1 execute stub（场景 10-14, 16-17） |
| T069 | 提交并推送 execute mode safety MVP |

## Verification

| 检查项 | 结果 |
|--------|------|
| 工作区初始状态 | clean |
| 只修改文档 | yes |
| 未修改代码 | yes — 未修改 runner.py / continuous_task_planner.py / rework_manager.py |
| 未修改业务代码 | yes |
| 未调用 Claude Code | yes |
| 未执行真实任务 | yes |

## Next

T065：实现 execute mode safety gate
