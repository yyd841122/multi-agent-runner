# T095 Dev Report

## Task

设计首次真实调用 run-project-task-full 执行开关。

## Scope

本轮只生成设计文档，不实现代码，不真实调用 run_project_task_full。

## Changed Files

- docs/first-real-run-execution-switch-design.md（新增，执行开关设计文档）
- reports/dev/T095-dev-report.md（新增，本文件）
- docs/tasks.md（状态更新）
- memory/lessons.md（追加经验）
- memory/pitfalls.md（追加避坑记录）

## Design Summary

### 三重确认协议

| 层级 | 参数 | 确认短语 | 语义 |
|------|------|----------|------|
| 第一重 | `--confirm` | `EXECUTE_PROJECT_LOOP` | 确认进入 execute mode |
| 第二重 | `--real-confirm` | `EXECUTE_REAL_TASK_ONCE` | 确认 real-call 请求 |
| 第三重 | `--real-execute-confirm` | `EXECUTE_REAL_RUN_ONCE` | 确认真实执行请求 |

三个确认短语不能互相替代，任何错位都必须拒绝。

### 执行开关

- `--real-execute-once`：请求真实执行一次（区别于 safety shell）
- 没有 `--real-execute-once` 时仍然只走 safety shell
- 有 `--real-execute-once` 但没有第三重确认时拒绝

### Preflight Checks

19 项前置检查，复用已有 `validate_real_call_safety()` + safety shell 逻辑，新增第三重确认检查。

### 执行流程

1. preflight checks → 2. 第三重确认 → 3. workspace before snapshot → 4. 真实调用 `run_project_task_full()` → 5. 捕获 `FullTaskLoopResult` → 6. workspace after snapshot → 7. 分类变更 → 8. 推断字段 → 9. 验收评估 → 10. 输出结果 → 11. 停止等待人工验收

### 输出字段

首次真实执行完成后输出 25+ 字段，包括 EXECUTION_MODE、TASK_ID、REAL_TASK_EXECUTION、ACCEPTANCE_STATUS、CLAUDE_CODE_CALLED、BUSINESS_CODE_CHANGED 等。

### 调用方式

推荐 Python 函数调用 `run_project_task_full(project_path, task_id)`，不是 subprocess。理由：已有稳定函数入口，直接获得 `FullTaskLoopResult`，无编码和环境问题。

## Safety Summary

首次真实调用后仍然：

- 不自动进入下一任务（`AUTO_CONTINUE_TO_NEXT_TASK=false`）
- 不自动 Git 备份（`AUTO_GIT_BACKUP=false`）
- 不自动返工
- 必须等待人工验收（`HUMAN_REVIEW_REQUIRED=true`）

无论 pass/fail 都停止等待人工确认。

## Rate Limit Note

API 429 / 5 小时限制当前阶段只 stop and report，不自动恢复。未来需要：

1. checkpoint（保存当前执行状态）
2. run state 持久化
3. reset time 检测
4. resume_allowed 判断
5. dirty workspace protection

这些能力等首次真实调用跑通后单独设计。

## Recommended Next Tasks

| 任务 | 角色 | 内容 |
|------|------|------|
| T096 | Developer | 实现 first real-run execute-once safety gate |
| T097 | Tester | 验证 execute-once 拒绝场景 |
| T098 | Developer | 实现 first real-run executor simulated child call |
| T099 | Tester | 验证 simulated real execution pass/fail |
| T100 | Developer | 执行第一次真实 run-project-task-full 调用 |
| T101 | Human | 人工验收第一次真实调用结果 |

## Verification

| 检查项 | 结果 |
|--------|------|
| 工作区初始状态 clean | yes |
| 只修改文档 | yes |
| 未修改代码 | yes |
| 未修改业务代码 | yes |
| 未调用 run-project-task-full | yes |
| 未调用 Claude Code | yes |

## Next

T096：实现 first real-run execute-once safety gate
