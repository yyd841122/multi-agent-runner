# Stage 6 MVP Summary

## Stage 6 Goal

第六阶段目标：从单任务闭环升级到连续多任务自动推进（Continuous Task Auto Advance），实现 `plan-project-loop` 和 `run-project-loop` 命令。

## MVP Completed Scope

当前 MVP 已完成：

| 任务 | 内容 | 状态 |
|------|------|------|
| T058 | continuous task auto advance protocol design | done |
| T059 | continuous task planner dry-run | done |
| T060 | run-project-loop dry-run | done |
| T061 | max_tasks=1 validation | done |
| T062 | max_tasks=3 validation | done |

## Implemented Commands

```bash
# 计划生成
python runner.py plan-project-loop --project . --max-tasks 3

# Loop dry-run（单任务）
python runner.py run-project-loop --project . --max-tasks 1 --dry-run

# Loop dry-run（多任务）
python runner.py run-project-loop --project . --max-tasks 3 --dry-run
```

## Current Capabilities

当前系统已经可以：

- 读取 `docs/tasks.md` 并识别所有 pending 任务
- 识别 NEXT_PENDING（第一个 pending 任务）
- 根据 max_tasks 限制生成 planned_tasks 列表
- 生成 loop dry-run result（ContinuousLoopRunResult）
- 输出唯一 RUN_ID（`loop-YYYYMMDD-HHMMSS-<6hex>`）
- 输出 STOP_REASON（max_tasks_reached / all_planned_tasks_simulated）
- 输出 NEXT_ACTION（review_loop_summary / fix_parameters_or_check_tasks）
- 输出 NEXT_TASK（下一个未 planned 的 pending 任务）
- 验证 max_tasks=1 只规划 1 个任务
- 验证 max_tasks=3 最多规划 3 个任务
- 验证 max_tasks=0 被拒绝
- 验证 max_tasks=11 安全裁剪到 10

## Important Non-capabilities

当前仍然**不能**：

- 真实执行任务（不调用 run-project-task-full）
- 调用 Claude Code
- 自动修改业务代码
- 自动 Git 备份
- 自动返工
- 使用 `--execute`（明确拒绝）
- 无人值守连续推进
- 自动更新任务状态（dry-run 不修改 tasks.md）

## Safety Guarantees

| 安全机制 | 说明 |
|----------|------|
| dry-run only | 默认且当前唯一模式 |
| max_tasks 默认 3 | 合理默认值 |
| max_tasks 硬上限 10 | 防止一次性规划过多任务 |
| max_tasks=0 拒绝 | 返回 invalid_max_tasks |
| max_tasks>10 裁剪 | 自动修正到硬上限 |
| TASK_EXECUTION_PERFORMED=false | 始终 |
| CLAUDE_CODE_CALLED=false | 始终 |
| BUSINESS_CODE_CHANGED=false | 始终 |
| --execute 明确拒绝 | 提示 not supported |

## Verification Summary

| 验证 | 场景 | 结果 |
|------|------|------|
| T059 | planner dry-run 默认 max_tasks=3 | PASS |
| T059 | planner dry-run max_tasks=1 | PASS |
| T059 | planner dry-run max_tasks=0 拒绝 | PASS |
| T059 | planner dry-run max_tasks=100 裁剪 | PASS |
| T060 | loop dry-run max_tasks=1 | PASS |
| T060 | loop dry-run max_tasks=3 | PASS |
| T060 | loop dry-run max_tasks=0 拒绝 | PASS |
| T060 | loop dry-run max_tasks=11 裁剪 | PASS |
| T060 | loop dry-run RUN_ID 格式 | PASS |
| T061 | max_tasks=1 只规划 1 个任务 | PASS |
| T061 | max_tasks=1 STOP_REASON=max_tasks_reached | PASS |
| T062 | max_tasks=3 最多规划 3 个任务 | PASS |
| T062 | max_tasks=3 自然结束（pending < max_tasks） | PASS |

## Key Files

| 文件 | 作用 |
|------|------|
| `tools/continuous_task_planner.py` | 计划生成 + loop dry-run 核心模块 |
| `runner.py` | CLI 命令入口（plan-project-loop / run-project-loop） |
| `docs/continuous-task-auto-advance-design.md` | 连续任务自动推进协议设计 |
| `reports/dev/T059-dev-report.md` | T059 开发报告 |
| `reports/dev/T060-dev-report.md` | T060 开发报告 |
| `reports/checks/T061-max-tasks-1-check.md` | T061 验证报告 |
| `reports/checks/T062-max-tasks-3-check.md` | T062 验证报告 |
| `docs/tasks.md` | 任务列表（T058-T063 已 done） |

## Git Commit History (Stage 6)

```
286703c test: verify run-project-loop max-tasks-3 dry-run
bbf6be8 test: verify run-project-loop max-tasks-1 dry-run
b0859a5 feat: add run-project-loop dry-run
e55a12a feat: add continuous task planner dry-run
08ceffe docs: design continuous task auto advance
```

## Recommended Next Step

T064：设计 run-project-loop execute mode 安全协议

注意：下一步仍然建议先设计，不直接实现真实执行。execute mode 需要解决：
- 任务间状态管理
- 单任务闭环（run-project-task-full）集成
- 失败任务的停止条件
- 返工任务的自动识别和跳过
- 人工介入边界的明确定义
- 每轮 loop 后的安全检查

## Final Status

```
STAGE_6_MVP_STATUS=done
CHECK_RESULT=pass
NEXT_PENDING=T064
NEXT_RECOMMENDED_TASK=设计 run-project-loop execute mode 安全协议
```
