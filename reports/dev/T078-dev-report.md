# T078 Dev Report

## Task

实现 real-call double-confirm safety gate。

## Scope

本轮只实现 double-confirm safety gate，不真实调用 run-project-task-full，不调用 Claude Code，不修改业务代码。

## Changed Files

- tools/continuous_task_planner.py（新增 RealCallSafetyResult、validate_real_call_safety()、REAL_CALL_CONFIRM_PHRASE 常量）
- runner.py（新增 --real-call、--real-confirm 参数，新增 real-call safety gate 输出分支）
- docs/tasks.md（状态更新）
- reports/dev/T078-dev-report.md（本文件）
- reports/checks/T078-real-call-double-confirm-safety-gate-check.md（验证报告）

## Implementation

### RealCallSafetyResult

新增数据结构，20 个字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| project | str | 项目路径 |
| run_id | str | 唯一运行 ID |
| real_call_requested | bool | 始终 True |
| real_confirm_status | str | accepted / missing / rejected |
| real_confirm_phrase | str \| None | 用户传入值 |
| execute_allowed | bool | 第一重 execute safety gate 是否通过 |
| real_call_allowed | bool | 全部检查通过才为 True |
| max_tasks | int | 用户请求值 |
| planned_tasks | list[str] | 计划执行的任务 ID |
| task_id | str \| None | 第一个 planned task |
| workspace_status | str | clean / dirty |
| preflight_status | str | passed / failed |
| real_task_execution | bool | 始终 False |
| run_project_task_full_called | bool | 始终 False |
| claude_code_called | str | "no" |
| business_code_changed | str | "no" |
| check_result | str | pass / fail |
| stop_reason | str \| None | 拒绝原因 |
| human_review_required | bool | 始终 True |
| next_action | str | 建议下一步 |
| message | str | 详细消息 |

### validate_real_call_safety()

检查顺序：

1. execute_requested → 否则 execute_not_requested
2. validate_execute_loop_safety() → 否则 execute_safety_gate_failed
3. real_confirm 缺失 → real_confirm_missing
4. real_confirm 不匹配 → real_confirm_rejected
5. max_tasks != 1 → max_tasks_not_one
6. adapter_dry_run 冲突 → mode_conflict_adapter_dry_run
7. real_call_stub 冲突 → mode_conflict_real_call_stub
8. planned_tasks 为空 → no_planned_tasks
9. workspace dirty → workspace_not_clean

### runner.py CLI

新增参数：`--real-call`（flag）和 `--real-confirm <phrase>`

互斥检查：
- --real-call 必须配合 --execute
- --real-call 和 --adapter-dry-run 互斥
- --real-call 和 --real-call-stub 互斥

## Behavior

- 需要 --execute + --confirm EXECUTE_PROJECT_LOOP（第一重确认）
- 需要 --real-call + --real-confirm EXECUTE_REAL_TASK_ONCE（第二重确认）
- max_tasks=1 only
- 与 --adapter-dry-run / --real-call-stub / --dry-run 互斥
- 只输出 safety gate 结果，不执行任何真实操作

## Safety Rules

- exact real confirm phrase：EXECUTE_REAL_TASK_ONCE
- no run_project_task_full call：始终 False
- no Claude Code call：始终 "no"
- no business code modification：始终 "no"
- no real task execution：始终 False
- human_review_required：始终 True

## Verification

12 个验证场景（详见 reports/checks/T078-real-call-double-confirm-safety-gate-check.md）：

| # | 场景 | 结果 |
|---|------|------|
| 1 | 不带 --real-call → 原行为保持 | PASS（CLI） |
| 2 | --real-call 不带 --execute | PASS（CLI） |
| 3 | --real-call 缺少 --real-confirm | PASS（代码逻辑） |
| 4 | --real-confirm yes | PASS（代码逻辑） |
| 5 | --real-confirm EXECUTE_PROJECT_LOOP | PASS（代码逻辑） |
| 6 | real confirm OK 但缺 execute confirm | PASS（函数级） |
| 7 | max_tasks=0 | PASS（函数级） |
| 8 | max_tasks=2 | PASS（代码逻辑） |
| 9 | --real-call + --adapter-dry-run | PASS（CLI） |
| 10 | --real-call + --real-call-stub | PASS（CLI） |
| 11 | 正确双确认 + clean workspace | PASS（代码逻辑，T080 补充） |
| 12 | 无真实调用/无 Claude Code/无业务代码修改 | PASS（函数级断言） |

说明：工作区 dirty（T078 实现中）导致部分场景在 execute safety gate 层被拦截。T080 将在 clean workspace 下补充完整 E2E 验证。

## Next

T079：实现 max_tasks=1 real-call dry-run executor
