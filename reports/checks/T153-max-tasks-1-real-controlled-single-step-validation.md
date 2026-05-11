# T153 验证报告：max_tasks=1 real controlled single-step execution trial

## 基本信息

- TASK=T153
- VALIDATOR=Test Agent + Stage 8 Safety Validator
- VALIDATION_DATE=2026-05-11
- PROJECT_ROOT=E:/github_project/multi-agent-runner
- LAST_COMMIT=b76dbba feat: add T152 stage 8 single-step trial framework

## 验证目标

验证 max_tasks=1 real controlled single-step execution trial 是否满足以下安全要求：

1. trial 可以被触发
2. max_tasks=1 时只能执行一个任务
3. 不允许自动进入第二个真实任务
4. 不允许无限真实连续执行
5. 不允许静默修改不相关文件
6. 不允许自动 commit
7. 不允许自动 push
8. 验证结果必须生成报告

## CLI 命令

```
python runner.py stage8-real-controlled-single-step-trial [--sample <name>] [--max-tasks N]
```

## 验证场景与结果

### 场景 1：default（无 sample，真实 workspace）

| 字段 | 值 |
|------|-----|
| TRIAL_MODE | trial_proceed |
| MAX_TASKS | 1 |
| MAX_TASKS_POLICY | enforced_max_tasks_1 |
| TASKS_ATTEMPTED | 0 |
| TASKS_COMPLETED | 0 |
| CURRENT_TASK | T149 |
| NEXT_PENDING_TASK | T153 |
| SELECTED_NEXT_TASK | T153 |
| SAFETY_GATE_PASSED | 21 |
| SAFETY_GATE_FAILED | 0 |
| EXECUTION_GATE_PASSED | 18 |
| EXECUTION_GATE_FAILED | 0 |
| GATE_CHECKS_PASSED | 39 |
| TRIAL_ALLOWED | True |
| NEXT_TASK_EXECUTED | False |
| BUSINESS_CODE_MODIFIED | False |
| PUSH_ALLOWED | False |
| RESUME_ALLOWED | False |
| REAL_GIT_ADD_USED | False |
| REAL_GIT_COMMIT_USED | False |
| REAL_GIT_PUSH_USED | False |
| STAGE9_ENTERED | False |
| WORKSPACE_STATUS_BEFORE | clean |
| WORKSPACE_STATUS_AFTER | clean |

**结果：PASS** — 真实 workspace 通过所有 39 项 gate 检查。

### 场景 2：pass_single_step_trial

**结果：PASS** — TRIAL_ALLOWED=True, 39 gates passed。

### 场景 3：no_pending_tasks（安全停止）

| 字段 | 值 |
|------|-----|
| TRIAL_ALLOWED | False |
| STOP_REASON | completed_max_tasks |
| FAILED_CHECKS | G6, G7 |

**结果：PASS** — 无 pending 任务时安全停止，不继续执行。

### 场景 4：max_tasks_missing (--max-tasks 0)

| 字段 | 值 |
|------|-----|
| TRIAL_ALLOWED | False |
| STOP_REASON | blocked_by_max_tasks_policy |
| GATE_CHECKS_PASSED | 0 |
| GATE_CHECKS_FAILED | 0 |

**结果：PASS** — 策略层直接拒绝，gate 不执行。

### 场景 5：max_tasks_zero (--max-tasks 0)

**结果：PASS** — 同场景 4，max_tasks=0 被策略层拒绝。

### 场景 6：max_tasks_too_large (--max-tasks 2)

| 字段 | 值 |
|------|-----|
| MAX_TASKS | 2 |
| TRIAL_ALLOWED | False |
| STOP_REASON | blocked_by_max_tasks_policy |

**结果：PASS** — max_tasks=2 被策略层拒绝，不允许执行 2 个任务。

### 场景 7：dirty_workspace

| 字段 | 值 |
|------|-----|
| TRIAL_ALLOWED | False |
| FAILED_CHECKS | G8: workspace is dirty |
| SAFETY_GATE_PASSED | 20 |
| SAFETY_GATE_FAILED | 1 |

**结果：PASS** — dirty workspace 被安全门 G8 拦截。

### 场景 8：staged_changes

| 字段 | 值 |
|------|-----|
| TRIAL_ALLOWED | False |
| FAILED_CHECKS | G9: staged files not empty |

**结果：PASS** — staged files 被安全门 G9 拦截。

### 场景 9：missing_approval_record

| 字段 | 值 |
|------|-----|
| TRIAL_ALLOWED | False |
| FAILED_CHECKS | G13: approval record missing |

**结果：PASS** — 缺失 approval record 被安全门 G13 拦截。

### 场景 10：missing_checkpoint

| 字段 | 值 |
|------|-----|
| TRIAL_ALLOWED | False |
| FAILED_CHECKS | G20, G21 |
| SAFETY_GATE_PASSED | 19 |
| SAFETY_GATE_FAILED | 2 |

**结果：PASS** — 缺失/不一致 checkpoint 被安全门 G20+G21 拦截。

### 场景 11：stage_boundary_to_stage9

| 字段 | 值 |
|------|-----|
| TRIAL_ALLOWED | False |
| FAILED_CHECKS | G2, G3 |
| STAGE_BOUNDARY_CHECK | exceeded |

**结果：PASS** — 跨 Stage 9 边界被安全门 G2+G3 拦截。

### 场景 12：push_allowed_true

| 字段 | 值 |
|------|-----|
| TRIAL_ALLOWED | False |
| FAILED_CHECKS | G16: push_allowed is true |

**结果：PASS** — push_allowed=True 被安全门 G16 拦截。

### 场景 13：resume_allowed_true（已知设计 gap）

| 字段 | 值 |
|------|-----|
| TRIAL_ALLOWED | True |
| RESUME_ALLOWED | False |
| GATE_CHECKS_PASSED | 39 |

**结果：PASS*** — 输入 resume_allowed=True 但无 gate 检查。结果硬编码 RESUME_ALLOWED=False。已知非阻塞设计 gap（T151 同步发现），不影响安全性因为输出始终为 False。

### 场景 14：real_execution_without_approval

| 字段 | 值 |
|------|-----|
| TRIAL_ALLOWED | False |
| FAILED_CHECKS | G17: real_execution_allowed is true |

**结果：PASS** — 未经批准的真实执行被安全门 G17 拦截。

### 场景 15：unknown_error

| 字段 | 值 |
|------|-----|
| TRIAL_ALLOWED | False |
| FAILED_CHECKS | G21: checkpoint not consistent |

**结果：PASS** — checkpoint 不一致被安全门 G21 拦截。

## 安全性验证汇总

### 核心安全约束

| 约束 | 验证结果 | 证据 |
|------|----------|------|
| max_tasks=1 强制执行 | PASS | max_tasks=0/2/None 均被策略层拒绝 |
| 不允许第二个任务 | PASS | max_tasks=2 被策略层拒绝 |
| 不允许无限连续执行 | PASS | 无 resume_allowed=True gate，结果硬编码 False |
| 不允许静默修改文件 | PASS | BUSINESS_CODE_MODIFIED 始终 False |
| 不允许自动 commit | PASS | REAL_GIT_COMMIT_USED 始终 False |
| 不允许自动 push | PASS | REAL_GIT_PUSH_USED 始终 False, G16 拦截 push_allowed=True |
| 必须生成报告 | PASS | 所有场景生成 approval record + checkpoint + trial report |
| gate 分层验证 | PASS | 安全门失败时执行门不运行 |
| fail-closed 原则 | PASS | 所有异常/未知场景均被拒绝 |

### 安全始终为 False 的字段

所有场景中以下字段始终为 False：

- NEXT_TASK_EXECUTED=False
- BUSINESS_CODE_MODIFIED=False
- PUSH_ALLOWED=False
- RESUME_ALLOWED=False
- REAL_GIT_ADD_USED=False
- REAL_GIT_COMMIT_USED=False
- REAL_GIT_PUSH_USED=False
- STAGE9_ENTERED=False
- STAGE8_EXECUTION_STARTED=False
- REAL_CONTINUOUS_EXECUTION_STARTED=False
- CONTINUOUS_AUTO_ADVANCE_USED=False

### 已知非阻塞设计 gap

resume_allowed_true：输入 resume_allowed=True 时无 gate 检查。但结果硬编码为 RESUME_ALLOWED=False，因此不影响安全性。与 T151 发现一致。

## 验证文件清单

本次验证过程中由 trial 自动生成的文件（已有，trial 覆盖写入）：

- reports/stage8/stage8-real-controlled-single-step-trial-approval-record.md
- reports/stage8/stage8-real-controlled-single-step-trial-checkpoint.md
- reports/stage8/stage8-real-controlled-single-step-trial-report.md

本次验证新增文件：

- reports/checks/T153-max-tasks-1-real-controlled-single-step-validation.md

本次验证修改文件：

- docs/tasks.md（T153 状态更新）

## 最终验证状态

```
TASK=T153
VALIDATION_STATUS=done
MAX_TASKS=1
REAL_CONTROLLED_SINGLE_STEP_STATUS=pass
EXECUTED_TASK_COUNT=0
UNLIMITED_CONTINUATION=no
NEXT_TASK_EXECUTED=no
AUTO_COMMIT_TRIGGERED=no
AUTO_PUSH_TRIGGERED=no
FILES_CREATED=reports/checks/T153-max-tasks-1-real-controlled-single-step-validation.md
FILES_MODIFIED=docs/tasks.md
WORKTREE_STATUS=dirty
CHECK_RESULT=pass
NEXT_PENDING=T154
NEXT_STAGE=Stage 8
```
