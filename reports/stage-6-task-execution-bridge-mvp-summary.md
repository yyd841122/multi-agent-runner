# Stage 6 Task Execution Bridge MVP Summary

## Goal

本小结范围是 **task execution bridge MVP**，即从 execute stub 到真实调用 `run_project_task_full` 之间的桥接层设计与实现。

**这不是真实执行 MVP。** 当前系统仍然没有真实调用 `run_project_task_full`、没有调用 Claude Code、没有修改业务代码、没有自动进入下一任务。

## Completed Scope

已完成：

| # | 任务 | 内容 |
|---|------|------|
| T070 | task execution bridge 设计 | 安全协议、数据结构、停止条件、安全输出字段 |
| T071 | adapter dry-run 实现 | TaskExecutionResult / ProjectLoopExecutionResult、adapter 函数 |
| T072 | adapter 不真实执行验证 | 4 场景全覆盖，TASK_EXECUTION_PERFORMED=false |
| T073 | real-call stub 实现 | RealCallStubResult、run_project_loop_real_call_stub() |
| T074 | CHECK_RESULT=pass 后停止验证 | 13 字段全 PASS |
| T075 | CHECK_RESULT=fail 后停止验证 | 设计约束 + 代码逻辑 + CLI 实测三层验证 |

## Implemented Commands

### adapter dry-run

```bash
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --adapter-dry-run
```

### real-call stub

```bash
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call-stub
```

## Current Capabilities

当前系统可以：

1. **构造未来调用信息**：adapter 和 real-call stub 都能构造 `run_project_task_full()` 的调用参数（project_path, task_id, command）
2. **输出 TaskExecutionResult**：14 字段，包含 check_result / task_status / business_code_changed 等
3. **输出 ProjectLoopExecutionResult**：19 字段，包含 loop_status / stop_reason / human_review_required 等
4. **输出 RealCallStubResult**：19 字段，包含 preflight_status / exit_code / check_result 等
5. **通过 adapter dry-run 验证不真实执行**：TASK_EXECUTION_PERFORMED=false
6. **通过 real-call stub 进入真实调用占位流程**：command 构造完毕但不执行
7. **CHECK_RESULT=pass 后停止**：LOOP_STATUS=real_call_stub_completed
8. **CHECK_RESULT=fail 后停止**：所有 fail 路径通过 return 终止
9. **明确输出安全字段**：RUN_PROJECT_TASK_FULL_CALLED=false, CLAUDE_CODE_CALLED=no, BUSINESS_CODE_CHANGED=no

## Important Non-capabilities

当前系统仍然 **不能**：

1. 真实调用 `run_project_task_full()`
2. 真实执行任务（调用 Claude Code）
3. 调用 Claude Code
4. 修改业务代码
5. 自动进入下一任务
6. 自动 Git 备份
7. 执行多个任务（max_tasks>1）
8. 无人值守连续推进

## Safety Guarantees

| 安全保证 | 说明 |
|----------|------|
| max_tasks=1 only | adapter 和 real-call stub 都只支持 max_tasks=1 |
| exact confirm required | 必须精确匹配 EXECUTE_PROJECT_LOOP |
| adapter dry-run 不执行命令 | TASK_EXECUTION_PERFORMED=false |
| real-call stub 不执行命令 | TASK_EXECUTION_PERFORMED=false |
| CHECK_RESULT=pass 后停止 | LOOP_STATUS=real_call_stub_completed |
| CHECK_RESULT=fail 后停止 | 所有 fail 路径通过 return 终止 |
| TASK_EXECUTION_PERFORMED | 始终 false |
| RUN_PROJECT_TASK_FULL_CALLED | 始终 false |
| CLAUDE_CODE_CALLED | 始终 "no" |
| BUSINESS_CODE_CHANGED | 始终 "no" |
| HUMAN_REVIEW_REQUIRED | 始终 True |
| 14 个停止条件 | T070 设计文档明确定义 |

## Verification Summary

| 任务 | 验证方式 | 验证场景数 | 结果 |
|------|----------|-----------|------|
| T071 adapter dry-run | CLI 实测 | 8 场景 | 全 PASS |
| T072 adapter 不真实执行 | CLI 实测 | 4 场景 | 全 PASS |
| T073 real-call stub | CLI 实测 | 9 场景 | 全 PASS |
| T074 pass 后停止 | CLI 实测 | 13 字段 | 全 PASS |
| T075 fail 后停止 | 设计约束 + 代码逻辑 + CLI | 2 CLI + 设计验证 | 全 PASS |

## Key Files

| 文件 | 作用 |
|------|------|
| `tools/continuous_task_planner.py` | TaskExecutionResult / ProjectLoopExecutionResult / RealCallStubResult / adapter / real-call stub |
| `runner.py` | --adapter-dry-run / --real-call-stub 参数和输出分支 |
| `docs/run-project-loop-task-execution-design.md` | T070 设计文档，14 个停止条件，安全输出字段 |
| `reports/checks/T071-task-execution-adapter-dry-run-check.md` | T071 验证报告 |
| `reports/checks/T072-adapter-no-real-execution-check.md` | T072 验证报告 |
| `reports/checks/T073-real-call-stub-check.md` | T073 验证报告 |
| `reports/checks/T074-check-result-pass-stop-check.md` | T074 验证报告 |
| `reports/checks/T075-check-result-fail-stop-check.md` | T075 验证报告 |
| `docs/tasks.md` | 任务状态跟踪 |

## Data Structure Summary

### TaskExecutionResult（adapter dry-run）

14 字段：task_id, command, adapter_mode, execution_started, execution_finished, exit_code, check_result, task_status, report_paths, workspace_status, business_code_changed, rework_required, human_review_required, next_action, message

### ProjectLoopExecutionResult（adapter dry-run loop）

19 字段：run_id, project, execution_mode, max_tasks, started_task, completed_tasks, failed_tasks, stopped_task, task_results, loop_status, stop_reason, workspace_status, git_backup_required, human_review_required, task_execution_performed, run_project_task_full_called, claude_code_called, business_code_changed, next_action, message

### RealCallStubResult（real-call stub）

19 字段：project, run_id, execution_mode, real_call_requested, real_call_stub_started, max_tasks, planned_tasks, task_id, command, preflight_status, task_execution_performed, run_project_task_full_called, claude_code_called, business_code_changed, exit_code, check_result, task_status, loop_status, stop_reason, human_review_required, next_action, message

## Recommended Next Step

**T077：设计 max_tasks=1 真实调用 run-project-task-full 安全协议**

注意：下一步仍然建议先设计，不直接实现真实执行。真实调用需要：
1. 确认 `run_project_task_full()` 的输出契约
2. 设计 real-call bridge（从 stub 到真实调用的转换）
3. 设计真实执行后的 workspace 检查和结果验证
4. 设计真实执行的安全边界和人工确认机制

## Final Status

```
TASK_EXECUTION_BRIDGE_MVP_STATUS=done
REAL_TASK_EXECUTION=no
RUN_PROJECT_TASK_FULL_CALLED=no
CLAUDE_CODE_CALLED=no
BUSINESS_CODE_CHANGED=no
CHECK_RESULT=pass
NEXT_PENDING=T077
```

## Commit Chain

```
0d9ad45 test: verify check-result fail stops loop
9e4ebd4 test: verify check-result pass stops loop
27936e5 feat: add max-tasks-one real-call stub
ff52db5 test: verify adapter no real execution
be06893 feat: add task execution adapter dry-run
af2e12e docs: design run-project-loop task execution bridge
```
