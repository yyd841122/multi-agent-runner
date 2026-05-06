# T073 Dev Report

## Task

实现 max_tasks=1 real-call stub。

## Scope

本轮只实现 real-call stub，不真实调用 run-project-task-full，不调用 Claude Code，不修改业务代码。

## Changed Files

- tools/continuous_task_planner.py（新增 RealCallStubResult、run_project_loop_real_call_stub()）
- runner.py（新增 --real-call-stub 参数和 real-call stub 输出分支）
- reports/checks/T073-real-call-stub-check.md（新增，验证报告）
- reports/dev/T073-dev-report.md（本文件）
- docs/tasks.md（状态更新）

## Implementation

### RealCallStubResult

新增数据结构（19 个字段）：

- `project`：项目路径
- `run_id`：唯一标识
- `execution_mode`："real_call_stub"
- `real_call_requested`：始终 True
- `real_call_stub_started`：是否启动 stub
- `max_tasks`：用户请求的 max_tasks
- `planned_tasks`：safety gate 通过时的 planned task ID 列表
- `task_id`：第一个 planned task（stub 目标）
- `command`：未来要执行的命令描述
- `preflight_status`："passed" / "failed"
- `task_execution_performed`：始终 False
- `run_project_task_full_called`：始终 False
- `claude_code_called`："no"（字符串）
- `business_code_changed`："no"（字符串）
- `exit_code`："not_executed"
- `check_result`："pass" / "fail"
- `task_status`："real_call_stub_ready" 等
- `loop_status`：real_call_stub_completed / safety_gate_failed / max_tasks_gt_1_not_supported
- `stop_reason`：停止原因
- `human_review_required`：始终 True
- `next_action`：建议下一步
- `message`：详细消息

### run_project_loop_real_call_stub()

职责：

1. 调用 safety gate 验证确认和前置条件
2. safety gate 不通过 → 返回失败结果（real_call_stub_started=false, check_result=fail）
3. safety gate 通过但 max_tasks != 1 → 拒绝
4. safety gate 通过且 max_tasks=1 → 解析 planned first task，构造 run-project-task-full 调用信息
5. 不执行该调用
6. 不调用 Claude Code，不修改业务代码

### runner.py 扩展

run-project-loop 新增 `--real-call-stub` 参数：

- 必须配合 `--execute` 使用
- 与 `--adapter-dry-run` 互斥
- 输出 EXECUTION_MODE / REAL_CALL_REQUESTED / REAL_CALL_STUB_STARTED / TASK_ID / COMMAND 等字段
- 不带 `--real-call-stub` 时保持 T066 execute stub 或 T071 adapter dry-run 行为不变

## Behavior

### --real-call-stub 如何构造未来命令

`run_project_loop_real_call_stub()` 通过 safety gate 获取 planned_tasks，取第一个 task_id，解析子项目路径，在 command 字段中记录：

```
run_project_task_full(project_path='projects/down-100-floors-game', task_id='T073')
```

这是未来真实调用时要执行的函数调用。当前只是字符串记录，不执行。

### 为什么不执行命令

real-call stub 的目的是验证从 safety gate 到真实调用信息的完整构造链路，确认 command、preflight_status、安全字段等全部正确，但不实际调用 `run_project_task_full()`。真实调用在 T074-T075 验证后实现。

### 与 adapter dry-run 的区别

| 对比项 | Adapter Dry-Run（T071） | Real-Call Stub（T073） |
|--------|------------------------|----------------------|
| 目的 | 验证 adapter 数据结构 | 验证完整调用构造链路 |
| 输出 | ADAPTER_DRY_RUN + COMMAND | REAL_CALL_STUB + COMMAND + PREFLIGHT_STATUS + EXIT_CODE |
| 包含 preflight_status | 否 | 是 |
| 包含 exit_code | 否 | 是 |
| 包含 check_result | 否（继承 adapter） | 是 |
| next_action | ready_for_T072 | ready_for_T074 |

### 与 execute stub 的区别

| 对比项 | Execute Stub（T066） | Real-Call Stub（T073） |
|--------|---------------------|----------------------|
| 目的 | 模拟识别第一个 task | 构造真实调用命令信息 |
| 输出 | EXECUTE_STUB_STARTED | REAL_CALL_STUB_STARTED + COMMAND |
| 包含 command | 否 | 是 |
| 包含 preflight_status | 否 | 是 |
| 走向 | → adapter dry-run | → T074 验证 → 真实调用 |

## Safety Rules

- requires --execute
- requires exact confirm（EXECUTE_PROJECT_LOOP）
- max_tasks=1 only
- no run-project-task-full call
- no Claude Code call
- no business code modification
- no task status auto-advance
- no Git backup automation
- claude_code_called 是字符串类型（"no"），不是布尔
- business_code_changed 是字符串类型（"no"），不是布尔

## Verification

9 个验证场景全部 PASS。详见 `reports/checks/T073-real-call-stub-check.md`。

| # | 场景 | 结果 |
|---|------|------|
| 1 | 不带 --real-call-stub → stub 行为不变 | PASS |
| 2 | --real-call-stub 不带 --execute | PASS |
| 3 | confirm 错误 → confirm_rejected | PASS |
| 4 | max_tasks=0 → invalid_max_tasks | PASS |
| 5 | max_tasks=2 → max_tasks_gt_1_not_supported | PASS |
| 6 | 正确参数 → stub pass | PASS |
| 7 | command 构造但未执行 | PASS |
| 8 | RUN_PROJECT_TASK_FULL_CALLED=false | PASS |
| 9 | 未调用 Claude Code、未修改业务代码 | PASS |

## Note

本次执行曾因 API 429 中断，但中断发生在开发报告生成阶段（第 7 步），代码实现（第 3-5 步）和验证（第 6 步）均已完成。本报告从中断点继续完成。

## Next

T074：验证 CHECK_RESULT=pass 后停止
