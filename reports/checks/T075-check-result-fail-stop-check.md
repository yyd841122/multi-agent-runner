# T075 CHECK_RESULT Fail Stop Check

## Goal

验证未来 task execution 返回 `CHECK_RESULT=fail` 时，外层 loop 必须停止等待人工处理。

## Current Implementation Status

当前仍是 real-call stub 阶段：

- `run_project_loop_real_call_stub()` 不真实调用 `run_project_task_full()`
- 当前 fail 场景来自 safety gate 拒绝和参数校验失败
- 尚未实现真实 `run_project_task_full()` 调用后的 fail 处理
- 本轮是 **fail stop 设计约束验证**，不是完整代码路径执行验证
- 真实 fail 路径将在后续 real-call bridge 实现时补充

## Evidence

### 1. T070 设计文档中的 fail stop 规则

来源：`docs/run-project-loop-task-execution-design.md`

**核心规则**（第 394 行）：

> MVP 中，无论任务成功还是失败，执行完一个任务后都必须停止。不自动进入下一个任务。

**Stop Conditions 表格**（第 377-393 行）列出 14 个停止条件：

| # | 停止条件 | stop_reason | loop_status |
|---|---------|-------------|-------------|
| 1 | safety gate 不通过 | 继承 safety gate | 继承 safety gate |
| 4 | `run_project_task_full` 抛出异常 | execution_exception | stopped_on_task_failed |
| 5 | final_status=FAILED | task_failed | stopped_on_task_failed |
| 6 | final_status=BLOCKED | task_blocked | stopped_on_task_blocked |
| 7 | final_status=REQUEST_CHANGES | rework_required | stopped_on_rework_required |
| 8 | Full Loop Report 缺失 | report_missing | stopped_on_check_fail |
| 9 | 任务状态未更新为 done | task_status_not_updated | stopped_on_check_fail |
| 10 | Dev Report 缺失 | dev_report_missing | stopped_on_check_fail |
| 11 | workspace 有非预期变更 | unexpected_code_change | stopped_on_dirty_worktree |
| 12 | 框架代码被修改 | framework_code_modified | stopped_on_dirty_worktree |

**final_status 分类处理**（第 352-357 行）：

| final_status | 处理 |
|--------------|------|
| `FAILED` | 停止，输出 task_failed |
| `BLOCKED` | 停止，输出 human_review_required=true |
| `REQUEST_CHANGES` | 停止，输出 rework_required=true |

所有 fail 路径都明确要求 **停止**。

### 2. T073 real-call stub 代码中的 fail 路径验证

**代码路径分析**（`tools/continuous_task_planner.py` 第 1153-1293 行）：

`run_project_loop_real_call_stub()` 有 3 个 fail 路径，每个都通过 `return` 语句结束函数：

| # | fail 路径 | 行号 | check_result | loop_status | 是否继续 |
|---|----------|------|-------------|-------------|---------|
| 1 | safety gate 不通过 | 1218-1227 | fail | safety_gate_failed | 否（return） |
| 2 | max_tasks != 1 | 1230-1241 | fail | max_tasks_gt_1_not_supported | 否（return） |
| 3 | no planned task | 1246-1253 | fail | safety_gate_failed | 否（return） |

关键：每个 fail 路径都通过 `return _fail_result(...)` 直接返回，函数终止。不存在继续执行的逻辑。

### 3. T073 check report 中的 fail 场景实际验证

来源：`reports/checks/T073-real-call-stub-check.md`

| # | 场景 | CHECK_RESULT | LOOP_STATUS | STOP_REASON | 自动继续 |
|---|------|-------------|-------------|-------------|---------|
| 3 | confirm 错误 | fail | safety_gate_failed | confirm_rejected | no |
| 4 | max_tasks=0 | fail | safety_gate_failed | invalid_max_tasks | no |
| 5 | max_tasks=2 | fail | max_tasks_gt_1_not_supported | max_tasks_gt_1_not_supported_in_real_call_stub | no |

### 4. T074 pass stop 验证结论

来源：`reports/checks/T074-check-result-pass-stop-check.md`

CHECK_RESULT=pass 后：
- LOOP_STATUS=real_call_stub_completed → 停止
- STOP_REASON=real_call_stub_only → 明确停止
- HUMAN_REVIEW_REQUIRED=True → 需人工确认

**推导**：pass 后已停止，fail 后更不可能继续。

### 5. 本轮 CLI 实测 fail 场景

**场景 A：confirm 错误 → CHECK_RESULT=fail**

```bash
python runner.py run-project-loop --project . --max-tasks 1 --execute --real-call-stub --confirm wrong_confirm
```

```
CHECK_RESULT=fail
LOOP_STATUS=safety_gate_failed
STOP_REASON=confirm_rejected
HUMAN_REVIEW_REQUIRED=True
TASK_EXECUTION_PERFORMED=False
RUN_PROJECT_TASK_FULL_CALLED=False
CLAUDE_CODE_CALLED=no
BUSINESS_CODE_CHANGED=no
NEXT_ACTION=fix_real_call_preconditions
```

**场景 B：max_tasks=0 → CHECK_RESULT=fail**

```bash
python runner.py run-project-loop --project . --max-tasks 0 --execute --real-call-stub --confirm EXECUTE_PROJECT_LOOP
```

```
CHECK_RESULT=fail
LOOP_STATUS=safety_gate_failed
STOP_REASON=invalid_max_tasks
HUMAN_REVIEW_REQUIRED=True
TASK_EXECUTION_PERFORMED=False
RUN_PROJECT_TASK_FULL_CALLED=False
CLAUDE_CODE_CALLED=no
BUSINESS_CODE_CHANGED=no
NEXT_ACTION=fix_real_call_preconditions
```

## Expected Fail Behavior

| 检查项 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| CHECK_RESULT=fail | fail | fail | PASS |
| AUTO_CONTINUE_TO_NEXT_TASK=no | 无继续逻辑 | 函数 return 结束 | PASS |
| AUTO_GIT_BACKUP=no | 无备份逻辑 | 无 Git 操作 | PASS |
| HUMAN_REVIEW_REQUIRED=true | True | True | PASS |
| RUN_PROJECT_TASK_FULL_CALLED=no/false | False | False | PASS |
| CLAUDE_CODE_CALLED=no | "no" | "no" | PASS |
| BUSINESS_CODE_CHANGED=no | "no" | "no" | PASS |
| NEXT_ACTION 包含 review/fix | fix_real_call_preconditions | fix_real_call_preconditions | PASS |

## Verification Result

### 设计约束验证

1. **T070 设计文档**：明确规定了 14 个停止条件，所有 fail 场景都要求停止。**通过。**

2. **代码逻辑验证**：`run_project_loop_real_call_stub()` 所有 fail 路径通过 `return _fail_result(...)` 终止函数，不存在继续逻辑。**通过。**

3. **CLI 实测验证**：confirm 错误和 max_tasks=0 两个 fail 场景实测，均正确停止，输出完整安全字段。**通过。**

4. **T074 pass 验证推导**：pass 后已停止，fail 后更不可能继续。逻辑一致。**通过。**

### 局限性

- 当前 fail 路径仅包含 safety gate 拒绝和参数校验失败
- **尚未实现** `run_project_task_full()` 真实调用后的 fail 处理（final_status=FAILED/BLOCKED/REQUEST_CHANGES）
- 真实 fail 路径验证需等待 real-call bridge 实现后补充
- 当前验证结论基于设计约束 + 代码逻辑分析 + CLI fail 场景实测

## Side Effect Check

| 检查项 | 结果 |
|--------|------|
| 是否执行真实任务 | no — TASK_EXECUTION_PERFORMED=false |
| 是否调用 run-project-task-full | no — RUN_PROJECT_TASK_FULL_CALLED=false |
| 是否调用 Claude Code | no — CLAUDE_CODE_CALLED=no |
| 是否修改业务代码 | no — BUSINESS_CODE_CHANGED=no |
| 是否自动提交 | no — git status 保持 clean |
| 是否自动推送 | no — 无 push 操作 |
| 是否生成 T076 报告 | no — 无 T076 相关文件 |

## Summary

CHECK_RESULT=fail 后的停止行为验证：

1. **设计约束明确**：T070 文档规定了所有 fail 场景必须停止
2. **代码逻辑正确**：所有 fail 路径通过 return 终止，不存在继续逻辑
3. **CLI 实测通过**：2 个 fail 场景均正确停止
4. **推导一致**：pass 后已停止，fail 后更不可能继续
5. **无副作用**：未执行任务、未调用 run-project-task-full、未修改业务代码

验证结论：**fail stop 设计约束验证通过。真实 fail 路径需后续 real-call bridge 实现时补充。**

## Check Result

pass

## Next

T076：提交并推送 task execution bridge MVP
