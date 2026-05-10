# T146 Dev Report: Real Single-Step Continuous Advance Dry-Run

任务编号：T146
角色：Developer
日期：2026-05-10

---

## 1. 本次目标

在 T144 continuous runner dry-run planner 基础上，实现 single-step continuous advance dry-run。模拟从 current completed state 到 next pending task selection 的单步推进 dry-run，不执行真实任务。

同时修复 T145 验证报告中记录的 checkpoint minor gaps。

## 2. 修改文件

| 文件 | 修改类型 | 说明 |
|------|----------|------|
| `tools/continuous_task_planner.py` | 修改/追加 | 修复 checkpoint minor gaps（`last_commit`、`manual_review_required`），新增 `Stage8SingleStepAdvanceDryRunResult` 数据结构、14 个 sample 场景、single-step advance dry-run 主函数、report 生成函数 |
| `runner.py` | 修改 | 新增 import、CLI 入口 `stage8-single-step-dry-run`、help 文本 |
| `reports/stage8/stage8-single-step-advance-dry-run-checkpoint.md` | 新增 | single-step advance dry-run checkpoint |
| `reports/stage8/stage8-single-step-continuous-advance-dry-run-report.md` | 新增 | single-step advance dry-run report |
| `reports/dev/T146-dev-report.md` | 新增 | 本 dev report |
| `docs/tasks.md` | 修改 | 更新 T146 状态 |

## 3. T145 Minor Gaps 修复

### 3.1 修复内容

| # | Gap | 修复方式 |
|---|-----|----------|
| 1 | checkpoint 缺少 `last_commit` 字段输出 | 在 `Stage8ContinuousRunnerCheckpoint` dataclass 新增 `last_commit` 字段，在 `build_stage8_continuous_runner_checkpoint_content()` 函数中输出 |
| 2 | checkpoint 缺少 `manual_review_required` 字段输出 | 在 `build_stage8_continuous_runner_checkpoint_content()` 函数中补充输出 |
| 3 | checkpoint 创建时缺少 `last_commit` 赋值 | 在 T144 主函数的 checkpoint 构建中添加 `last_commit=gate_input.last_commit` |

### 3.2 安全语义不变

- `resume_allowed` 仍为 False
- `push_allowed` 仍为 False
- `real_execution_allowed` 仍为 False
- 仅为输出字段补齐，不改变任何安全判断逻辑

## 4. 新增数据结构

### 4.1 Stage8SingleStepAdvanceDryRunResult

single-step advance dry-run 结果，包含以下字段组：

- **运行标识**：run_id, task_id, dry_run(True), stage, mode
- **计划**：max_tasks, tasks_attempted, tasks_completed
- **任务**：current_task, next_pending_task, selected_next_task
- **工作区**：workspace_status_before/after, staged_files, current_branch, last_commit
- **安全标志**：push_allowed(False), real_execution_allowed(False), resume_allowed(False), stage_boundary_check, rework_required, rate_limit_status, manual_stop_requested, manual_review_required
- **Gate 结果**：advance_allowed, advance_decision, stop_reason, safety_gate_result, failure_reasons, required_actions
- **Gate check 详情**：gate_checks_passed, gate_checks_failed, failed_checks
- **报告路径**：checkpoint_path, advance_report_path
- **安全追踪**：stage8_execution_started(False), continuous_auto_advance_used(False), real_git_add/commit/push_used(False), stage9_entered(False)
- **其他**：notes, message

## 5. 新增主函数

### 5.1 run_stage8_single_step_continuous_advance_dry_run()

复用 T144 safety gate 评估逻辑 `evaluate_stage8_continuous_runner_safety_gate()`：

1. 构建 gate input（sample 或真实 workspace 数据）
2. 评估 gate（复用 T144 21 项 gate check）
3. 确定 selected_next_task（仅当 gate 通过时）
4. 生成 checkpoint
5. 生成 advance report
6. 返回 dry-run 结果

不执行任何真实操作。

## 6. 新增 CLI 入口

```bash
python runner.py stage8-single-step-dry-run --sample <name> --max-tasks <N>
```

支持参数：
- `--sample <name>`：指定 sample 场景
- `--max-tasks <N>`：最大任务数（仅非 sample 模式下使用）

## 7. Sample 场景

| # | Sample | 类型 | 预期结果 |
|---|--------|------|----------|
| 1 | pass_select_next_task | Pass | advance, selected_next_task=T146 |
| 2 | pass_no_execution | Pass | advance, selected_next_task=T146 |
| 3 | no_pending_tasks | Safe stop | stop, stop_reason=no_pending_tasks |
| 4 | max_tasks_reached | Safe stop | stop, stop_reason=completed_max_tasks |
| 5 | dirty_workspace | Fail | blocked, stop_reason=blocked_by_dirty_workspace |
| 6 | staged_changes | Fail | blocked, stop_reason=blocked_by_staged_changes |
| 7 | missing_approval_record | Fail | blocked, stop_reason=blocked_by_missing_approval_record |
| 8 | missing_report | Fail | blocked, stop_reason=blocked_by_missing_report |
| 9 | stage_boundary_to_stage9 | Fail | blocked, stop_reason=blocked_by_stage_boundary |
| 10 | push_allowed_true | Fail | blocked, stop_reason=blocked_by_git_safety_gate |
| 11 | real_execution_allowed_true | Fail | blocked, stop_reason=blocked_by_git_safety_gate |
| 12 | manual_stop_requested | Fail | blocked, stop_reason=manual_stop_required |
| 13 | rate_limit_blocked | Fail | blocked, stop_reason=blocked_by_rate_limit |
| 14 | unknown_error | Fail | blocked, stop_reason=blocked_by_unknown_error |

## 8. 安全保证

| # | 保证项 | 值 |
|---|--------|-----|
| 1 | dry_run | True |
| 2 | stage8_execution_started | False |
| 3 | continuous_auto_advance_used | False |
| 4 | real_git_add_used | False |
| 5 | real_git_commit_used | False |
| 6 | real_git_push_used | False |
| 7 | push_allowed | False |
| 8 | real_execution_allowed | False |
| 9 | resume_allowed | False |
| 10 | stage9_entered | False |

## 9. 未执行真实连续任务证明

- T146 仅实现 dry-run，所有 sample 使用模拟数据
- 真实 workspace 模式仅读取状态（git status, git branch, git log），不修改
- checkpoint 和 report 是 dry-run 输出文件，不影响项目业务代码
- 不调用 Claude Code，不执行真实任务

## 10. 后续 T147 验证建议

1. 验证全部 14 个 sample 的 pass/fail 行为
2. 验证 checkpoint 的 `last_commit` 和 `manual_review_required` 字段已修复
3. 验证 advance report 的所有必需字段
4. 验证 git 副作用（无 staged changes、无新 commit、无 push）
5. 验证 21 项 gate check 覆盖度
6. 验证所有安全标志始终为安全值
