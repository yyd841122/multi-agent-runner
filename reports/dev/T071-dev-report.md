# T071 Dev Report

## Task

实现 run-project-task-full adapter dry-run。

## Scope

本轮只实现 adapter dry-run，不真实调用 run-project-task-full，不调用 Claude Code，不修改业务代码。

## Changed Files

- tools/continuous_task_planner.py（新增 TaskExecutionResult、ProjectLoopExecutionResult、prepare_run_project_task_full_adapter_dry_run()、run_project_loop_task_execution_adapter_dry_run()、_resolve_subproject_path()）
- runner.py（新增 --adapter-dry-run 参数和 adapter dry-run 输出分支）
- reports/checks/T071-task-execution-adapter-dry-run-check.md（新增，验证报告）
- reports/dev/T071-dev-report.md（本文件）

## Implementation

### TaskExecutionResult

新增数据结构（14 个字段）：

- `task_id`：任务 ID
- `command`：未来要执行的函数调用描述
- `adapter_mode`："dry_run" / "real"
- `execution_started`：dry-run 下始终 False
- `execution_finished`：dry-run 下始终 False
- `exit_code`：dry-run 下为 None
- `check_result`："pass" / "fail"
- `task_status`："adapter_dry_run_ready" 等
- `report_paths`：dry-run 下为空
- `workspace_status`："not_checked"
- `business_code_changed`：始终 False
- `rework_required`：始终 False
- `human_review_required`：始终 True
- `next_action`：建议下一步
- `message`：详细消息

### ProjectLoopExecutionResult

新增数据结构（19 个字段）：

- `run_id` / `project`：标识
- `execution_mode`："task_execution_adapter_dry_run"
- `max_tasks`：用户请求的 max_tasks
- `started_task`：adapter 锁定的任务 ID
- `completed_tasks` / `failed_tasks`：始终空
- `stopped_task`：停止的任务
- `task_results`：TaskExecutionResult 列表
- `loop_status`：adapter_dry_run_completed / safety_gate_failed / max_tasks_gt_1_not_supported
- `stop_reason`：停止原因
- `workspace_status`："not_checked"
- `git_backup_required`：始终 False
- `human_review_required`：始终 True
- `task_execution_performed`：始终 False
- `run_project_task_full_called`：始终 False
- `claude_code_called`："no"（字符串，非布尔）
- `business_code_changed`："no"（字符串，非布尔）
- `next_action` / `message`：建议和详细消息

### prepare_run_project_task_full_adapter_dry_run()

职责：

- 接收 project_path 和 task_id
- 构造未来调用描述（command 字段包含函数调用和 CLI 命令）
- 不执行任何调用
- 返回 TaskExecutionResult

### run_project_loop_task_execution_adapter_dry_run()

职责：

1. 调用 safety gate 验证确认和前置条件
2. safety gate 不通过 → 返回失败结果
3. safety gate 通过但 max_tasks != 1 → adapter 拒绝
4. safety gate 通过且 max_tasks=1 → 调用 prepare adapter
5. 生成 ProjectLoopExecutionResult

### _resolve_subproject_path()

根据任务 ID 前缀解析子项目路径（G → projects/down-100-floors-game）。

### runner.py 扩展

run-project-loop 新增 `--adapter-dry-run` 参数：

- 必须配合 `--execute` 使用
- 输出 EXECUTION_MODE / ADAPTER_DRY_RUN / TASK_ID / COMMAND 等字段
- 不带 `--adapter-dry-run` 时保持 T066 stub 行为不变

## Behavior

### adapter dry-run 如何构造未来命令

`prepare_run_project_task_full_adapter_dry_run()` 接收 project_path 和 task_id，在 command 字段中记录：

```
run_project_task_full(project_path='projects/down-100-floors-game', task_id='T071')
```

这是未来真实调用时要执行的函数调用。当前只是字符串记录，不执行。

### 为什么不执行命令

adapter dry-run 的目的是验证从 safety gate 到 adapter 的调用链路是否正确，不包括真实执行。真实调用在 T073 实现。

### 与 execute stub 的区别

| 对比项 | Execute Stub（T066） | Adapter Dry-Run（T071） |
|--------|---------------------|------------------------|
| 目的 | 模拟识别第一个 task | 构造未来调用信息 |
| 输出 | EXECUTE_STUB_STARTED | ADAPTER_DRY_RUN + COMMAND |
| 走向 | → 验证 stub | → 验证 adapter → 真实调用 |
| 包含 project_path | 否 | 是 |
| 包含 command | 否 | 是 |
| 包含 task_results | 否 | 是 |

## Safety Rules

- requires --execute
- requires exact confirm（EXECUTE_PROJECT_LOOP）
- max_tasks=1 only
- no run-project-task-full call
- no Claude Code call
- no business code modification
- claude_code_called 是字符串类型（"no"/"unknown"/"yes"），不是布尔

## Verification

8 个验证场景全部 PASS。详见 `reports/checks/T071-task-execution-adapter-dry-run-check.md`。

## Next

T072：验证 adapter 不真实执行
