# T082 Simulated CHECK_RESULT Fail Check

## 验证日期

2026-05-06

## Goal

验证未来 child `CHECK_RESULT=fail` 时，外层 loop 必须停止等待人工处理。

## Current Implementation Status

当前仍是 real-call dry-run executor 阶段：

- 当前不会真实调用 `run_project_task_full()`
- 当前 child result 是 `not_executed`
- 当前真实 fail 子调用路径尚未实现
- 本轮是 **fail-stop 设计约束验证**，不是完整真实 fail 执行验证
- 真实 fail 路径验证需等待 real-call bridge 实现后补充

## Dry-run Command

```bash
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-dry-run
```

## Current Actual Result

当前 dry-run 输出摘要：

| 字段 | 值 |
|------|-----|
| EXECUTION_MODE | real_call_dry_run_executor |
| TASK_ID | T082 |
| CHILD_RESULT_MODE | not_executed |
| SIMULATED_CHECK_RESULT | not_executed |
| TASK_EXECUTION_PERFORMED | False |
| RUN_PROJECT_TASK_FULL_CALLED | False |
| CLAUDE_CODE_CALLED | no |
| BUSINESS_CODE_CHANGED | no |
| AUTO_CONTINUE_TO_NEXT_TASK | False |
| AUTO_GIT_BACKUP | False |
| HUMAN_REVIEW_REQUIRED | True |
| CHECK_RESULT | pass |
| STOP_REASON | real_call_dry_run_only |

额外字段：

| 字段 | 值 |
|------|-----|
| RUN_ID | loop-20260506-201147-a13dcc |
| MAX_TASKS | 1 |
| COMMAND | python runner.py run-project-task-full --project E:\github_project\multi-agent-runner\projects --task T082 |
| FUNCTION_CALL | run_project_task_full(project_path='E:\github_project\multi-agent-runner\projects', task_id='T082') |
| NEXT_ACTION | ready_for_T080_real_confirm_rejection_validation |

## Expected Future Fail Behavior

未来真实 child `CHECK_RESULT=fail` 时应满足：

| 检查项 | 预期值 | 验证来源 |
|--------|--------|----------|
| CHECK_RESULT | fail | T077 设计：FAILED/BLOCKED/REQUEST_CHANGES → fail |
| AUTO_CONTINUE_TO_NEXT_TASK | no | T075 代码：所有 fail 路径 return 终止；T077 设计："无论 pass/fail 都停止" |
| AUTO_GIT_BACKUP | no | T077 设计："MVP 不自动 Git 备份" |
| HUMAN_REVIEW_REQUIRED | true | T077 设计："始终 True" |
| NEXT_ACTION | review_failure_before_continue | T077 设计："stop_reason=task_failed + next_action=review..." |
| 不自动进入下一任务 | - | T077 设计："第一个真实调用必须人工验收" |
| 不自动提交 | - | T077 设计："push 需要人工确认" |
| 不自动推送 | - | T077 设计："push 需要人工确认" |
| 不自动返工 | - | T077 Non-goals："自动返工真实执行 → 返工需要人工确认" |

### final_status → CHECK_RESULT 映射验证

| final_status | CHECK_RESULT | 后续行为 | 依据 |
|--------------|-------------|----------|------|
| FAILED | fail | 停止，task_failed | T077 设计第 339 行 |
| BLOCKED | fail | 停止，task_blocked | T077 设计第 340 行 |
| REQUEST_CHANGES | fail | 停止，rework_required | T077 设计第 341 行 |
| 异常 | fail | 停止，execution_exception | T077 设计第 342 行 |
| COMPLETE | pass | 停止（MVP 不自动继续） | T077 设计第 336 行 |

## Evidence

### 1. T075 fail-stop 验证报告

`reports/checks/T075-check-result-fail-stop-check.md`：

- T070 设计文档规定了 14 个停止条件，所有 fail 场景都要求停止
- `run_project_loop_real_call_stub()` 所有 fail 路径通过 `return _fail_result(...)` 终止函数，不存在继续逻辑
- CLI 实测 2 个 fail 场景均正确停止
- T074 pass 验证推导：pass 后已停止，fail 后更不可能继续

### 2. T077 real task execution safety design

`docs/run-project-loop-real-task-execution-safety-design.md`：

- "无论任务成功还是失败，执行完一个任务后都必须停止。不自动进入下一个任务。"
- 21 个停止条件覆盖所有 fail 场景
- `AUTO_CONTINUE_TO_NEXT_TASK=no`, `AUTO_GIT_BACKUP=no`, `HUMAN_REVIEW_REQUIRED=true` 始终
- CLAUDE_CODE_CALLED 无法确认时输出 `unknown`，不写 `no`
- BUSINESS_CODE_CHANGED 无法确认时输出 `unknown`

### 3. T081 pass-stop 验证报告

`reports/checks/T081-simulated-check-result-pass-check.md`：

- 外层 CHECK_RESULT=pass 时：停止，不执行真实任务，需人工确认
- 推导：pass 后已停止 → fail 后更不可能继续

### 4. 当前 dry-run executor 安全字段

代码验证（`tools/continuous_task_planner.py` 第 1302-1474 行）：

- `task_execution_performed=False` — 始终
- `run_project_task_full_called=False` — 始终
- `auto_continue_to_next_task=False` — 始终
- `auto_git_backup=False` — 始终
- `human_review_required=True` — 始终
- 函数通过 `return` 结束，不存在循环或继续逻辑

## Fail-Stop Design Constraint Verification

| # | 约束 | 验证方式 | 结果 |
|---|------|----------|------|
| 1 | fail 后 CHECK_RESULT=fail | T077 设计映射 + T075 实测 | PASS |
| 2 | fail 后不自动进入下一任务 | T075 代码逻辑（return 终止）+ T077 设计 | PASS |
| 3 | fail 后不自动 Git 备份 | T077 Non-goals 明确 + 代码无备份逻辑 | PASS |
| 4 | fail 后需人工确认 | T077 设计 human_review_required=True + T075 实测 | PASS |
| 5 | fail 后不自动提交/推送 | T077 Non-goals + 当前 dry-run executor 无 commit 逻辑 | PASS |
| 6 | fail 后不自动返工 | T077 Non-goals："自动返工真实执行 → 返工需要人工确认" | PASS |
| 7 | 异常也视为 fail | T077 设计：execution_exception → CHECK_RESULT=fail | PASS |
| 8 | 无法确认字段输出 unknown | T077 设计：CLAUDE_CODE_CALLED/BUSINESS_CODE_CHANGED | PASS |

## Side Effect Check

| 检查项 | 结果 |
|--------|------|
| 是否执行真实任务 | no — TASK_EXECUTION_PERFORMED=False |
| 是否调用 run-project-task-full | no — RUN_PROJECT_TASK_FULL_CALLED=False |
| 是否调用 Claude Code | no — CLAUDE_CODE_CALLED=no |
| 是否修改业务代码 | no — BUSINESS_CODE_CHANGED=no |
| 是否自动提交 | no — git status 保持 clean |
| 是否自动推送 | no — 无 push 操作 |
| 工作区 git status | clean ✓ |

## Limitation

当前验证是 fail-stop 设计约束验证，不是完整真实 fail 路径验证：

- 当前 dry-run executor 不真实执行子任务，`SIMULATED_CHECK_RESULT=not_executed`
- 真实 `CHECK_RESULT=fail` 子调用路径（final_status=FAILED/BLOCKED/REQUEST_CHANGES）尚未实现
- 真实 fail 路径验证需等待 real-call bridge（`run_project_loop_real_call_execute()`）实现后补充
- 当前验证结论基于：
  1. T075 fail-stop 验证报告（代码逻辑 + CLI 实测）
  2. T077 设计文档（21 个停止条件 + 安全输出字段）
  3. T081 pass-stop 验证（pass 后已停止，fail 后更不可能继续）
  4. 当前 dry-run executor 安全字段确认

## Check Result

**PASS** — fail-stop 设计约束验证通过。真实 fail 路径需后续 real-call bridge 实现时补充。

## Next

T083：提交并推送 real-call safety MVP
