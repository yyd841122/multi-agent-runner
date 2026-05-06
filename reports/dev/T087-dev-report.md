# T087 Dev Report

## Task

验证 real-call-run-once 拒绝场景。

## Scope

本轮只做验证，不实现新功能。验证 `--real-call-run-once` 在前置条件不满足时必须拒绝。

## Changed Files

- reports/checks/T087-real-call-run-once-rejection-check.md（新增，10 拒绝场景 + 1 对照场景）
- reports/dev/T087-dev-report.md（新增，本文件）
- docs/tasks.md（状态更新）

## Verification

### 拒绝场景验证（10 个）

| # | 拒绝原因 | 拒绝类型 | 结果 |
|---|----------|----------|------|
| 1 | 缺少 --real-call | CLI ERROR | PASS |
| 2 | 缺少 --real-call（有 --execute） | CLI ERROR | PASS |
| 3 | --confirm 值错误（yes） | CHECK_RESULT=fail, confirm_rejected | PASS |
| 4 | 缺少 --real-confirm | CHECK_RESULT=fail, real_confirm_missing | PASS |
| 5 | --real-confirm 值错误（yes） | CHECK_RESULT=fail, real_confirm_rejected | PASS |
| 6 | max-tasks=0 | CHECK_RESULT=fail, invalid_max_tasks | PASS |
| 7 | max-tasks=2 | CHECK_RESULT=fail, max_tasks_not_one | PASS |
| 8 | --real-call-dry-run 互斥 | CLI ERROR | PASS |
| 9 | --real-call-stub 互斥 | CLI ERROR | PASS |
| 10 | --adapter-dry-run 互斥 | CLI ERROR | PASS |

### 对照场景验证（1 个）

| # | 场景 | 结果 |
|---|------|------|
| 11 | 正确参数 safety shell | EXECUTION_MODE=real_call_run_once_safety_shell, RUN_ONCE_SAFETY_SHELL_STARTED=true, CHECK_RESULT=pass, REAL_TASK_EXECUTION=no |

### 所有场景安全字段确认

所有 11 个场景均满足：

- REAL_TASK_EXECUTION=no
- RUN_PROJECT_TASK_FULL_CALLED=no
- CLAUDE_CODE_CALLED=no
- BUSINESS_CODE_CHANGED=no
- AUTO_CONTINUE_TO_NEXT_TASK=no/false
- AUTO_GIT_BACKUP=no/false

## Safety Result

- 是否执行真实任务：no
- 是否调用 run-project-task-full：no
- 是否调用 Claude Code：no
- 是否修改业务代码：no
- 是否自动进入下一任务：no
- 是否自动 Git 备份：no
- 工作区验证：执行前后均 clean
- 业务代码：projects/down-100-floors-game/** 无变化

## Next

T088：验证 simulated child CHECK_RESULT=pass
