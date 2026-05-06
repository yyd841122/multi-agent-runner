# T079 Dev Report

## Task

实现 max_tasks=1 real-call dry-run executor。

## Scope

本轮只实现 real-call dry-run executor，不真实调用 run-project-task-full，不调用 Claude Code，不修改业务代码。

## Changed Files

- tools/continuous_task_planner.py（新增 RealCallDryRunExecutorResult、run_project_loop_real_call_dry_run_executor()）
- runner.py（新增 --real-call-dry-run 参数、新增 dry-run executor 输出分支）
- docs/tasks.md（状态更新）
- reports/dev/T079-dev-report.md（本文件）
- reports/checks/T079-real-call-dry-run-executor-check.md（验证报告）

## Implementation

### RealCallDryRunExecutorResult

新增数据结构，24 个字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| project | str | 项目路径 |
| run_id | str | 唯一运行 ID |
| execution_mode | str | "real_call_dry_run_executor" |
| real_call_allowed | bool | real-call safety gate 是否通过 |
| dry_run_executor_started | bool | executor 是否启动 |
| max_tasks | int | 用户请求值 |
| task_id | str \| None | 当前 NEXT_PENDING |
| command | str | 未来要执行的 CLI 命令 |
| function_call | str | 未来要执行的函数调用描述 |
| child_result_mode | str | "not_executed" |
| simulated_exit_code | str | "not_executed" |
| simulated_check_result | str | "not_executed" |
| simulated_task_status | str | "dry_run_only" |
| task_execution_performed | bool | 始终 False |
| run_project_task_full_called | bool | 始终 False |
| claude_code_called | str | "no" |
| business_code_changed | str | "no" |
| auto_continue_to_next_task | bool | 始终 False |
| auto_git_backup | bool | 始终 False |
| human_review_required | bool | 始终 True |
| check_result | str | "pass" / "fail" |
| stop_reason | str \| None | 停止原因 |
| next_action | str | 建议下一步 |
| message | str | 详细消息 |

### run_project_loop_real_call_dry_run_executor()

职责：

1. 调用 validate_real_call_safety()（复用 T078 双重确认安全门）
2. 如果 safety gate 不通过，返回 dry-run executor result：dry_run_executor_started=false，check_result=fail
3. 如果 safety gate 通过：
   - 解析 planned task（safety.task_id）
   - 解析 subproject path（_resolve_subproject_path）
   - 构造未来真实调用 command
   - 构造 function_call 描述
   - 不执行 command
   - 不调用函数
   - 不调用 Claude Code
   - 不修改业务代码
4. 返回 RealCallDryRunExecutorResult

### runner.py CLI

新增参数：`--real-call-dry-run`（flag）

互斥检查：
- --real-call-dry-run 必须配合 --real-call
- --real-call-dry-run 必须配合 --execute
- --real-call-dry-run 和 --dry-run 互斥
- --real-call-dry-run 和 --adapter-dry-run 互斥
- --real-call-dry-run 和 --real-call-stub 互斥

输出分支优先级：--real-call-dry-run > T078 safety gate > T073 real-call-stub > T071 adapter > T066 execute stub > T060 dry-run

## Behavior

- 需要 execute confirm（EXECUTE_PROJECT_LOOP）
- 需要 real confirm（EXECUTE_REAL_TASK_ONCE）
- max_tasks=1 only
- 生成 command 和 function_call（字符串，不执行）
- 不执行 command / function_call
- pass 后仍然停止等待人工确认

## Safety Rules

- exact real confirm phrase：EXECUTE_REAL_TASK_ONCE
- no run_project_task_full call：始终 False
- no Claude Code call：始终 "no"
- no business code modification：始终 "no"
- no auto-continue：始终 False
- no auto Git backup：始终 False
- human_review_required：始终 True

## Verification

11 个验证场景（详见 reports/checks/T079-real-call-dry-run-executor-check.md）：

| # | 场景 | 结果 |
|---|------|------|
| 1 | 不带 --real-call-dry-run → 原行为保持 | PASS（CLI） |
| 2 | --real-call-dry-run 不带 --real-call | PASS（CLI） |
| 3 | --real-call-dry-run 不带 --execute | PASS（CLI） |
| 4 | confirm 错误 | PASS（CLI） |
| 5 | real-confirm 错误 | PASS（代码逻辑） |
| 6 | max_tasks=2 | PASS（代码逻辑） |
| 7 | --real-call-dry-run + --real-call-stub | PASS（CLI） |
| 7b | --real-call-dry-run + --adapter-dry-run | PASS（CLI） |
| 8 | 正确双确认 + max_tasks=1 + real-call-dry-run | PASS（代码逻辑，T080 补充 clean workspace E2E） |
| 9 | 输出含 command/function_call 但未执行 | PASS（代码逻辑） |
| 10 | 所有路径未调用/未修改 | PASS（函数级断言） |

说明：工作区 dirty（T079 实现中）导致 CLI 级别的 execute safety gate 在 workspace 检查处拦截。T080 将在 clean workspace 下补充完整 E2E 验证。

## Next

T080：验证 real confirm 拒绝场景
