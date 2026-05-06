# T066 Dev Report

## Task

实现 max_tasks=1 execute stub。

## Scope

本轮只实现 execute stub，不执行真实任务，不调用 Claude Code，不修改业务代码。

## Changed Files

- tools/continuous_task_planner.py（新增 ExecuteLoopStubResult、run_project_loop_execute_stub()）
- runner.py（修改 run-project-loop execute 分支，调用 execute stub）
- reports/checks/T066-execute-stub-check.md（新增，验证报告）
- reports/dev/T066-dev-report.md（本文件）

## Implementation

### ExecuteLoopStubResult

新增数据结构（19 个字段）：

- `project` / `run_id`：标识
- `execute_mode`：始终 "execute"
- `execute_allowed`：safety gate 是否通过
- `execute_stub_started`：stub 是否启动（只有 execute_allowed=true 且 max_tasks=1 时为 true）
- `max_tasks`：用户请求的 max_tasks
- `planned_tasks`：safety gate 通过时的 planned task ID 列表
- `stub_task`：第一个 planned task（stub 模拟目标）
- `completed_tasks`：stub 模拟完成的任务
- `failed_tasks` / `skipped_tasks`：始终空
- `task_execution_performed`：始终 False
- `claude_code_called`：始终 False
- `business_code_changed`：始终 False
- `loop_status`：execute_stub_completed / safety_gate_failed / max_tasks_gt_1_not_supported
- `stop_reason`：停止原因
- `human_review_required`：始终 False
- `next_action` / `message`：建议和详细消息

### run_project_loop_execute_stub()

核心函数，职责：

1. 调用 `validate_execute_loop_safety()` 进行 safety gate 检查
2. 如果 safety gate 不通过 → `execute_stub_started=false, loop_status=safety_gate_failed`
3. 如果 safety gate 通过但 max_tasks != 1 → `execute_stub_started=false, stop_reason=max_tasks_gt_1_not_supported_in_stub`
4. 如果 safety gate 通过且 max_tasks=1 → `execute_stub_started=true, stub_task=planned_tasks[0], loop_status=execute_stub_completed`

禁止：

- 调用 run-project-task-full
- 调用 Claude Code
- 修改 docs/tasks.md 的任务状态
- 修改业务代码

### runner.py 扩展

`run-project-loop` 的 execute 分支改为调用 `run_project_loop_execute_stub()`：

- 输出 EXECUTE_MODE_REQUESTED / EXECUTE_ALLOWED / EXECUTE_STUB_STARTED
- 输出 STUB_TASK / COMPLETED_TASKS / FAILED_TASKS
- 输出 TASK_EXECUTION_PERFORMED / CLAUDE_CODE_CALLED / BUSINESS_CODE_CHANGED
- 输出 LOOP_STATUS / STOP_REASON / NEXT_ACTION / CHECK_RESULT
- CHECK_RESULT = pass（stub started）/ fail（stub 未启动）

## Behavior

### dry-run 行为保持不变

不带 `--execute` 时，`run-project-loop` 行为与 T060 完全一致。

### safety gate fail 行为保持不变

confirm 错误、max_tasks 非法、工作区 dirty 等场景的拒绝行为与 T065 完全一致。

### max_tasks=1 进入 stub

当 safety gate 全部通过且 max_tasks=1 时：
- EXECUTE_STUB_STARTED=true
- STUB_TASK=planned_tasks[0]
- TASK_EXECUTION_PERFORMED=false
- LOOP_STATUS=execute_stub_completed

### max_tasks>1 当前拒绝

当 safety gate 全部通过但 max_tasks=2 或 3 时：
- EXECUTE_STUB_STARTED=false
- STOP_REASON=max_tasks_gt_1_not_supported_in_stub
- CHECK_RESULT=fail

### stub 不执行真实任务

所有路径始终：
- TASK_EXECUTION_PERFORMED=false
- CLAUDE_CODE_CALLED=false
- BUSINESS_CODE_CHANGED=false

## Safety Rules

- 确认短语精确匹配 EXECUTE_PROJECT_LOOP
- safety gate required（调用 validate_execute_loop_safety）
- max_tasks=1 only（T066 只支持 stub）
- no run-project-task-full call
- no Claude Code call
- no business code modification

## Verification

10 个验证场景：6 个运行验证 PASS + 4 个代码逻辑验证 PASS。详见 `reports/checks/T066-execute-stub-check.md`。

## Next

T067：验证 execute confirm 拒绝场景
