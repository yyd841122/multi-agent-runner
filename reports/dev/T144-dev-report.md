# T144 Dev Report: Stage 8 Continuous Runner Dry-Run Planner

任务编号：T144
角色：Developer
日期：2026-05-09

---

## 1. 本次目标

实现 Stage 8 continuous runner dry-run planner。基于 T143 safety gate 设计，将 21 项 gate check (G1-G21) 落成代码层面的 dry-run planner。

只做规划，不做执行。

## 2. 修改文件

| 文件 | 修改类型 | 说明 |
|------|----------|------|
| `tools/continuous_task_planner.py` | 追加 | 新增 Stage 8 数据结构、safety gate 评估、checkpoint 生成、dry-run planner 主函数、18 个 sample 场景 |
| `runner.py` | 修改 | 新增 import、CLI 入口 `stage8-continuous-dry-run`、help 文本 |
| `reports/stage8/stage8-continuous-runner-dry-run-checkpoint.md` | 新增 | dry-run checkpoint 示例 |
| `reports/dev/T144-dev-report.md` | 新增 | 本 dev report |
| `docs/tasks.md` | 修改 | 更新 T144 状态 |

## 3. 新增数据结构

### 3.1 Stage8SafetyGateInput

gate 输入数据，包含 30 个字段，覆盖：
- 运行级别（stage, run_id, max_tasks, tasks_attempted, tasks_completed）
- 当前任务（current_task_id, validation_status, approval_record_status, report_status, rework_required）
- 下一任务（next_pending_task_id, next_pending_task_stage）
- 工作区（workspace_status, staged_files, current_branch, last_commit）
- 安全标志（push_allowed, real_execution_allowed, rate_limit_status, manual_stop_requested）
- Checkpoint（checkpoint_exists, checkpoint_consistent）

### 3.2 Stage8SafetyGateOutput

gate 输出数据，包含 T143 设计的 13 个输出字段 + 3 个内部追踪字段。

### 3.3 Stage8ContinuousRunnerDryRunResult

dry-run planner 总结果，包含 45+ 字段，覆盖运行标识、计划、任务状态、工作区、安全标志、gate 结果、checkpoint、安全追踪。

### 3.4 Stage8ContinuousRunnerCheckpoint

checkpoint 数据结构，用于模拟 checkpoint 写入，包含 version, run_id, stage, mode, timing, limits, current_state, workspace, records, resume, errors, notes。

## 4. 新增 dry-run planner

### 4.1 evaluate_stage8_continuous_runner_safety_gate()

实现 T143 设计的 21 项 gate check (G1-G21)：

| Gate | 检查内容 |
|------|----------|
| G1 | stage 必须为 Stage 8 |
| G2 | next_pending_task_stage 必须为 Stage 8 |
| G3 | 不允许跨入 Stage 9+ |
| G4 | max_tasks 必须存在且为正整数 |
| G5 | max_tasks <= 10 |
| G6 | tasks_attempted < max_tasks |
| G7 | next_pending_task_id 必须存在 |
| G8 | workspace_status 必须为 clean |
| G9 | staged_files 必须为空 |
| G10 | current_branch 必须明确 |
| G11 | last_commit 必须已记录 |
| G12 | validation_status 必须为 pass |
| G13 | approval_record_status 必须为 exists |
| G14 | report_status 必须为 exists |
| G15 | rework_required 必须为 false |
| G16 | push_allowed 必须为 false |
| G17 | real_execution_allowed 必须为 false |
| G18 | rate_limit_status 必须为 clear |
| G19 | manual_stop_requested 必须为 false |
| G20 | checkpoint_exists 必须为 true |
| G21 | checkpoint_consistent 必须为 true |

### 4.2 run_stage8_continuous_runner_dry_run_planner()

dry-run planner 主函数。支持两种模式：
- sample 模式：使用预定义的 sample 数据
- live 模式：使用真实 workspace 数据

## 5. 新增 stop_reason

支持 14 种 stop_reason：

| # | stop_reason | 类型 |
|---|-------------|------|
| 1 | completed_max_tasks | 正常 |
| 2 | no_pending_tasks | 正常 |
| 3 | blocked_by_dirty_workspace | 异常 |
| 4 | blocked_by_staged_changes | 异常 |
| 5 | blocked_by_validation_failure | 异常 |
| 6 | blocked_by_rework_required | 异常 |
| 7 | blocked_by_unapproved_changes | 异常（预留） |
| 8 | blocked_by_stage_boundary | 异常 |
| 9 | blocked_by_missing_approval_record | 异常 |
| 10 | blocked_by_missing_report | 异常 |
| 11 | blocked_by_git_safety_gate | 异常 |
| 12 | blocked_by_rate_limit | 异常 |
| 13 | manual_stop_required | 异常 |
| 14 | blocked_by_unknown_error | 异常 |

所有 stop_reason 的 resume_allowed 均为 false。

## 6. 新增 checkpoint

`build_stage8_continuous_runner_checkpoint_content()` 生成 YAML 格式的 Markdown checkpoint。

输出路径：`reports/stage8/stage8-continuous-runner-dry-run-checkpoint.md`

## 7. CLI 用法

```bash
# sample 模式（18 个场景）
python runner.py stage8-continuous-dry-run --sample pass_max_tasks_1
python runner.py stage8-continuous-dry-run --sample pass_max_tasks_2_first_task
python runner.py stage8-continuous-dry-run --sample no_pending_tasks
python runner.py stage8-continuous-dry-run --sample dirty_workspace
python runner.py stage8-continuous-dry-run --sample staged_changes
python runner.py stage8-continuous-dry-run --sample validation_failure
python runner.py stage8-continuous-dry-run --sample missing_approval_record
python runner.py stage8-continuous-dry-run --sample missing_report
python runner.py stage8-continuous-dry-run --sample stage_boundary_to_stage9
python runner.py stage8-continuous-dry-run --sample max_tasks_missing
python runner.py stage8-continuous-dry-run --sample max_tasks_too_large
python runner.py stage8-continuous-dry-run --sample max_tasks_reached
python runner.py stage8-continuous-dry-run --sample rework_required
python runner.py stage8-continuous-dry-run --sample manual_stop_requested
python runner.py stage8-continuous-dry-run --sample rate_limit_blocked
python runner.py stage8-continuous-dry-run --sample push_allowed_true
python runner.py stage8-continuous-dry-run --sample real_execution_allowed_true
python runner.py stage8-continuous-dry-run --sample unknown_error

# live 模式
python runner.py stage8-continuous-dry-run --max-tasks 1
python runner.py stage8-continuous-dry-run --max-tasks 2
```

## 8. Sample 输出

### pass_max_tasks_1

```
GATE_CHECKS_PASSED=21
GATE_CHECKS_FAILED=0
ALLOWED=True
DECISION=advance
STOP_REASON=None
STAGE8_EXECUTION_STARTED=False
CONTINUOUS_AUTO_ADVANCE_USED=False
```

### dirty_workspace

```
GATE_CHECKS_PASSED=20
GATE_CHECKS_FAILED=1
ALLOWED=False
DECISION=blocked
STOP_REASON=blocked_by_dirty_workspace
```

### max_tasks_reached

```
GATE_CHECKS_PASSED=20
GATE_CHECKS_FAILED=1
ALLOWED=False
DECISION=stop
STOP_REASON=completed_max_tasks
```

## 9. 安全保证

| # | 安全标志 | 值 |
|---|----------|-----|
| 1 | dry_run | True |
| 2 | stage8_execution_started | False |
| 3 | continuous_auto_advance_used | False |
| 4 | real_execution_allowed | False |
| 5 | push_allowed | False |
| 6 | resume_allowed | False |
| 7 | real_git_add_used | False |
| 8 | real_git_commit_used | False |
| 9 | real_git_push_used | False |
| 10 | stage9_entered | False |

## 10. 未执行真实连续任务证明

- `run_stage8_continuous_runner_dry_run_planner()` 函数内无 subprocess 调用执行任务
- 无 os.system 调用
- 无 git add/commit/push 命令
- 唯一的文件写入是 checkpoint（Markdown 文本文件）和 dev report
- 所有 sample 场景使用静态数据，不读取/修改真实 workspace

## 11. 后续 T145 验证建议

T145 应验证：

1. 3 个 pass 场景均返回 allowed=True, decision=advance
2. 14 个 fail 场景均返回 allowed=False
3. 每个 fail 场景有明确 stop_reason
4. 每个 fail 场景有 failure_reasons
5. gate_checks_passed + gate_checks_failed = 21
6. 所有场景 STAGE8_EXECUTION_STARTED=False
7. 所有场景 CONTINUOUS_AUTO_ADVANCE_USED=False
8. 所有场景 REAL_GIT_ADD/COMMIT/PUSH_USED=False
9. 所有场景 STAGE9_ENTERED=False
10. checkpoint 文件正确生成
11. resume_allowed 始终 False
