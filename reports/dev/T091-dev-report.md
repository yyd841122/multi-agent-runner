# T091 Dev Report

## Task

设计首次真实调用 run-project-task-full 的验收协议。

## Scope

本轮只生成设计文档，不实现代码，不真实调用。

## Changed Files

- docs/first-real-run-acceptance-protocol.md（新增，验收协议设计文档）
- reports/dev/T091-dev-report.md（新增，本文件）
- memory/lessons.md（追加经验）
- memory/pitfalls.md（追加避坑）
- docs/tasks.md（状态更新）

## Design Summary

### 验收状态模型

定义 `FirstRealRunAcceptanceResult`，包含以下关键字段：

- `acceptance_status`：`ready_for_human_review` / `blocked` / `failed_to_parse` / `unsafe_to_continue`
- `human_review_required`：始终 True
- `auto_continue_to_next_task`：始终 False
- `auto_git_backup`：始终 False

### 成功验收标准

同时满足 10 个条件：调用成功、final_status=COMPLETE、CHECK_RESULT=pass、任务状态 done、workspace 可识别、报告存在、人工验收、不自动继续、不自动 Git backup。

成功后仍然必须停止，输出 `ACCEPTANCE_STATUS=ready_for_human_review`。

### 失败验收标准

4 种失败严重程度：致命（异常/None）、严重（FAILED/BLOCKED/dirty_unexpected）、中等（REQUEST_CHANGES/report 缺失）、低（unknown 字段）。

### 人工验收清单

10 项人工验收清单：
1. 是否只运行一次
2. 是否执行正确 task_id
3. CHECK_RESULT 是否可信
4. 报告是否存在
5. Claude Code 是否调用
6. 业务代码是否修改
7. 修改文件是否符合范围
8. git status 是否可解释
9. 是否需要 Git 备份
10. 是否允许进入下一任务

### Workspace 分类规则

6 种分类：clean / dirty_reports_only / dirty_business_code / dirty_expected / dirty_unexpected / dirty_unknown。每种分类对应不同的验收动作。

### 验证场景

设计 33 个验证场景，覆盖阶段 A（前置拒绝 10 个）、阶段 B（执行结果 9 个）、阶段 C（推断规则 8 个）、阶段 D（停止行为 6 个）。

## Safety Summary

- 首次真实调用后仍然不自动继续（`AUTO_CONTINUE_TO_NEXT_TASK=false`）
- 首次真实调用后仍然不自动 Git backup（`AUTO_GIT_BACKUP=false`）
- 首次真实调用后仍然不自动返工
- 首次真实调用后必须人工验收（`HUMAN_REVIEW_REQUIRED=true`）
- unknown 字段不能写成 no（`CLAUDE_CODE_CALLED=unknown` 不等于 `no`）

## Future Requirement

记录 Rate Limit Recovery / Checkpoint Resume 需求：

- checkpoint：保存当前执行状态
- run state 持久化
- reset time 检测
- resume_allowed 判断
- 恢复后自动继续

**当前阶段不实现**，等首次真实调用跑通后单独设计。

## Recommended Next Tasks

| 任务 | 角色 | 内容 |
|------|------|------|
| T092 | Developer | 实现 first real-run acceptance result model |
| T093 | Developer | 实现 simulated first real-run acceptance parser |
| T094 | Tester | 验证 first real-run acceptance pass/fail 场景 |
| T095 | Architect | 设计首次真实调用 run-project-task-full 执行开关 |
| T096 | Developer | 执行第一次真实 run-project-task-full 调用 |
| T097 | Human | 人工验收第一次真实调用结果 |

## Verification

| 检查项 | 结果 |
|--------|------|
| 工作区初始状态 | clean |
| 是否只修改文档 | yes |
| 是否未修改代码 | yes（runner.py、continuous_task_planner.py、rework_manager.py 未修改） |
| 是否未修改业务代码 | yes |
| 是否未调用 run-project-task-full | yes |
| 是否未调用 Claude Code | yes |

## Next

T092：实现 first real-run acceptance result model
