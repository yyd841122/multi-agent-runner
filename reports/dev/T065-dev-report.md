# T065 Dev Report

## Task

实现 execute mode safety gate — execute mode 的确认协议、前置检查和 execute 硬限制。

## Scope

本轮只实现 safety gate，不执行真实任务，不调用 Claude Code，不修改业务代码。

## Changed Files

- tools/continuous_task_planner.py（新增 ExecuteLoopSafetyResult、validate_execute_loop_safety()、辅助检查函数）
- runner.py（扩展 run-project-loop 命令，支持 --execute --confirm）
- reports/checks/T065-execute-safety-gate-check.md（新增，验证报告）
- reports/dev/T065-dev-report.md（本文件）

## Implementation

### ExecuteLoopSafetyResult

新增数据结构（19 个字段）：

- `project` / `run_id`：标识
- `execute_requested`：始终 True（进入此流程说明用户传了 --execute）
- `confirm_status`：`accepted` / `missing` / `rejected`
- `confirm_phrase`：用户传入的原始值
- `max_tasks` / `execute_hard_limit`：execute mode 硬限制 3
- `planned_tasks`：计划执行的任务 ID 列表
- `workspace_status`：`clean` / `dirty` / `unknown`
- `preflight_status`：`passed` / `failed`
- `execute_allowed`：全部检查通过才为 True
- `task_execution_performed`：始终 False
- `claude_code_called`：始终 False
- `business_code_changed`：始终 False
- `human_review_required`：始终 False
- `stop_reason`：拒绝原因
- `next_action` / `message`：建议和详细消息

### validate_execute_loop_safety()

核心函数，按顺序检查：

1. **确认短语**：缺失 → `confirm_missing`，不匹配 → `confirm_rejected`
2. **max_tasks**：< 1 → `invalid_max_tasks`，> 3 → `execute_max_tasks_exceeded`
3. **工作区**：dirty → `initial_worktree_dirty`
4. **in_progress 任务**：存在 → `existing_in_progress`
5. **pending rework**：存在 → `pending_rework_exists`
6. **planned_tasks**：为空 → `no_pending_tasks`

全部通过 → `execute_allowed=True`，`preflight_status=passed`

### 辅助函数

- `_check_workspace_clean(project_root)`：通过 `git status --short` 检查
- `_check_no_in_progress_tasks(project_root)`：读取 tasks.md 检查
- `_check_no_pending_rework(project_root)`：检查无 rework prompt 文件

### runner.py 扩展

`run-project-loop` 分支新增 `--confirm` 参数解析和 execute 分支：

- **情况 A**：不带 `--execute` → 保持原有 dry-run 行为
- **情况 B**：带 `--execute` → 调用 `validate_execute_loop_safety()` 输出 safety gate 结果
- **互斥**：`--execute --dry-run` 同时传入时报错

## Behavior

### dry-run 行为保持不变

不带 `--execute` 时，`run-project-loop` 行为与 T060 完全一致。

### confirm 拒绝

| 输入 | confirm_status | stop_reason |
|------|---------------|-------------|
| 缺少 --confirm | missing | confirm_missing |
| yes / ok / 确认 / EXECUTE_REWORK | rejected | confirm_rejected |

### max_tasks execute 限制

| max_tasks | 结果 | stop_reason |
|-----------|------|-------------|
| 0 | 拒绝 | invalid_max_tasks |
| 1 | 合法 | — |
| 3 | 合法 | — |
| 4 | 拒绝 | execute_max_tasks_exceeded |
| 11 | 拒绝 | execute_max_tasks_exceeded |

### safety gate pass 但不执行任务

当全部检查通过时：
- EXECUTE_ALLOWED=true
- TASK_EXECUTION_PERFORMED=false
- CLAUDE_CODE_CALLED=false
- BUSINESS_CODE_CHANGED=false
- NEXT_ACTION=ready_for_T066_execute_stub

## Safety Rules

- 确认短语精确匹配 EXECUTE_PROJECT_LOOP
- execute max_tasks 硬限制 = 3（dry-run 仍为 10）
- 工作区必须 clean
- planned_tasks 必须非空
- 不调用 run-project-task-full
- 不调用 Claude Code
- 不修改业务代码
- --execute 和 --dry-run 互斥

## Verification

10 个场景 + 3 个额外验证，全部 PASS。详见 `reports/checks/T065-execute-safety-gate-check.md`。

## Next

T066：实现 max_tasks=1 execute stub
