# T085 Dev Report

## Task

实现 real-call run-once safety shell。

## Scope

本轮只实现 run-once safety shell，不真实调用 run-project-task-full，不调用 Claude Code，不修改业务代码。

## Changed Files

- tools/continuous_task_planner.py（新增 RealCallRunOnceResult 数据结构 + run_project_loop_real_call_run_once_safety_shell() 函数）
- runner.py（新增 --real-call-run-once 参数 + CLI 互斥检查 + 输出格式化）
- reports/checks/T085-real-call-run-once-safety-shell-check.md（新增，12 个验证场景）
- reports/dev/T085-dev-report.md（新增，本文件）
- docs/tasks.md（状态更新）
- memory/lessons.md（追加经验）
- memory/pitfalls.md（追加避坑）

## Implementation

### RealCallRunOnceResult

26 字段数据结构，所有字符串字段使用小写语义值：

- `execution_mode=real_call_run_once_safety_shell`
- `run_once_requested=true`
- `real_task_execution=no`
- `run_project_task_full_called=no`
- `claude_code_called=no`
- `business_code_changed=no`
- `child_exit_code=not_executed`
- `child_check_result=not_executed`
- `child_task_status=not_executed`
- `auto_continue_to_next_task=false`
- `auto_git_backup=false`
- `human_review_required=true`

### run_project_loop_real_call_run_once_safety_shell()

函数流程：

1. 模式互斥检查（--real-call-dry-run / --adapter-dry-run / --real-call-stub / --dry-run）
2. 调用 validate_real_call_safety() 双重确认
3. safety gate 不通过 → 返回拒绝结果
4. safety gate 通过 → 解析 task_id
5. 解析 subproject_path
6. 构造未来调用的 command 和 function_call（不执行）
7. 返回 RealCallRunOnceResult（pass）

### runner.py --real-call-run-once

CLI 层互斥检查（6 条规则）：

1. 必须配合 --real-call
2. 必须配合 --execute
3. 与 --real-call-dry-run 互斥
4. 与 --adapter-dry-run 互斥
5. 与 --real-call-stub 互斥
6. 与 --dry-run 互斥

## Behavior

- 需要 execute confirm（EXECUTE_PROJECT_LOOP）
- 需要 real confirm（EXECUTE_REAL_TASK_ONCE）
- max_tasks=1 only
- 生成 command / function_call 字符串但不执行
- 不调用 run-project-task-full
- 不调用 Claude Code
- 不修改业务代码
- 不自动进入下一任务
- 不自动 Git 备份

## Safety Rules

- exact real confirm phrase：EXECUTE_REAL_TASK_ONCE
- no run-project-task-full call：RUN_PROJECT_TASK_FULL_CALLED=no
- no Claude Code call：CLAUDE_CODE_CALLED=no
- no business code modification：BUSINESS_CODE_CHANGED=no
- no auto-continue：AUTO_CONTINUE_TO_NEXT_TASK=false
- no auto Git backup：AUTO_GIT_BACKUP=false
- always human review：HUMAN_REVIEW_REQUIRED=true

## Verification

12 个验证场景全部 PASS：

| # | 场景 | 结果 |
|---|------|------|
| 1 | 不带 --real-call-run-once | PASS |
| 2 | 不带 --real-confirm | PASS |
| 3 | 不带 --execute | PASS |
| 4 | confirm 错误 | PASS |
| 5 | real-confirm 错误 | PASS |
| 6 | max_tasks=0 | PASS |
| 7 | max_tasks=2 | PASS |
| 8 | + --real-call-dry-run | PASS |
| 9 | + --real-call-stub | PASS |
| 10 | 正确双确认（dirty workspace） | PASS |
| 11 | command/function_call 构造 | PASS |
| 12 | 所有路径安全保证 | PASS |

注意：clean workspace pass 场景因工作区 dirty 无法实测，通过函数级验证确认数据结构正确。T087 将做完整验证。

## Next

T086：实现 child command parser dry-run
