# T149：Stage 8 Real Controlled Continuous Execution Gate 设计

设计时间：2026-05-10
阶段：Stage 8 — 真实连续任务自动推进
任务角色：Designer / Architecture Agent
前置条件：Stage 8 planning/dry-run 链路完成（T143-T148），Stage 8 real controlled continuous execution plan 完成

---

## 1. 设计目标

T149 的目标是为 Stage 8 真实受控连续推进设计 **execution gate**。

这个 gate 的核心职责是：**在系统从 dry-run single-step advance 准备升级到 real controlled single-step execution trial 之前，判断当前状态是否允许启动真实受控执行**。

### 1.1 Execution gate 要解决的问题

| # | 问题 | 说明 |
|---|------|------|
| 1 | 直接从 dry-run 跳到真实执行 | 没有 intermediate gate 控制过渡 |
| 2 | dirty workspace 下启动真实执行 | 上一个 dry-run 残留影响真实执行 |
| 3 | 跳过 approval record 启动真实执行 | 真实执行必须有审批记录 |
| 4 | 跳过 checkpoint 启动真实执行 | 真实执行必须有完整检查点 |
| 5 | 跨 Stage 进入 Stage 9 | 真实执行不允许跨 Stage |
| 6 | 自动 push | 真实执行过程中自动执行 push |
| 7 | 未审批文件进入 Git 流程 | 非白名单文件被 commit |
| 8 | allowed_scope 不明确 | 执行范围模糊导致不可控变更 |
| 9 | command_allowlist 不明确 | 执行命令不受控 |

### 1.2 Execution gate 的核心原则

```text
1. Fail-closed — 任何不确定情况一律拒绝真实执行
2. 复用 G1-G21 — 不替代 T143 safety gate，在其之上叠加
3. 单步授权 — 每次只授权一个 real controlled step
4. 审批必须 human — approved_by 必须为 human
5. 白名单约束 — 只允许 planned_files 和 command_allowlist 内的操作
6. push 永远禁止 — 不受任何条件豁免
7. 可审查可追溯 — 每次真实执行决策都有完整 gate check 记录
```

### 1.3 设计范围

T149 只设计 execution gate，不实现代码。

T149 不涉及：
- execution gate 的具体实现（T150）
- dry-run 的 pass/fail 验证（T151）
- 真实执行的试运行（T152）
- 真实执行的验证（T153）
- 成果归档（T154）

---

## 2. 与 T143 / T144 / T146 的关系

### 2.1 必须复用的前半段成果

| # | 成果 | 来源 | 复用方式 |
|---|------|------|----------|
| 1 | 21 项 gate check (G1-G21) | T143 | 作为 execution gate 的前置检查层 |
| 2 | Safety gate 评估函数 | T144 | `evaluate_stage8_continuous_runner_safety_gate()` |
| 3 | Continuous runner dry-run planner | T144 | 作为真实执行的 dry-run 验证层 |
| 4 | 14 种 stop_reason | T144 | 作为 execution gate stop_reason 的基础 |
| 5 | Checkpoint 生成 | T144/T146 | 作为真实执行 checkpoint 的基础模板 |
| 6 | Single-step advance dry-run | T146 | 作为真实单步推进的 dry-run 验证层 |
| 7 | Next pending task selection | T146 | 作为真实执行的任务选取逻辑 |
| 8 | T145/T147 验证结果 | T145/T147 | 32 个场景全部验证通过，作为安全基线 |
| 9 | Fail-closed 保证 | T143-T147 | 所有不确定情况一律拒绝 |
| 10 | Real controlled execution plan | Stage 8 planning | 作为 execution gate 的总体设计依据 |

### 2.2 Execution gate 的增量能力

T149 execution gate 在 T143 G1-G21 之上增加以下能力：

| # | 增量能力 | 对应 Gate | 说明 |
|---|----------|-----------|------|
| 1 | allowed_scope 校验 | E10 | 确保真实执行范围明确 |
| 2 | command_allowlist 校验 | E11 | 确保执行命令受控 |
| 3 | real_execution_allowed 审批 gate | E12 | 真实执行必须经过单独审批 |
| 4 | planned_files 校验 | E17 | 确保文件变更范围受控 |
| 5 | execution_mode 校验 | E18 | 确保执行模式正确 |
| 6 | approval record v2.0 完整性 | E7+ | 增加 real execution 专属字段校验 |

### 2.3 Gate 层次关系

```text
执行流程：

Step 1: G1-G21 safety gate check（T143 复用）
  → 全部通过 → 进入 Step 2
  → 任一失败 → blocked, stop

Step 2: E1-E18 execution gate check（T149 新增）
  → 全部通过 → allowed_for_real_controlled_single_step
  → 任一失败 → blocked, stop

Step 3: 真实受控单步执行（T152）
  → 执行 1 个 task step
  → 生成 approval record v2.0
  → 生成 checkpoint v2.0
  → 生成 execution report
  → 不 push

不允许：
  - 跳过 G1-G21 直接进入 E1-E18
  - 跳过 E1-E18 直接真实执行
  - 部分通过即执行
  - 自动 push
  - 跨入 Stage 9
```

### 2.4 不替代不绕过

```text
T149 execution gate 不替代：
  - T143 的 G1-G21 safety gate
  - T144 的 dry-run planner
  - T146 的 single-step advance dry-run

T149 execution gate 不绕过：
  - push_allowed=false
  - real_execution_allowed 约束
  - sensitive file protection
  - command allowlist
  - stage boundary check
```

---

## 3. Gate 输入设计

Execution gate 需要以下输入字段来做出真实执行决策。

### 3.1 运行级别输入

| # | 字段 | 类型 | 来源 | 说明 |
|---|------|------|------|------|
| 1 | `stage` | string | 当前运行配置 | 当前阶段，必须为 `Stage 8` |
| 2 | `mode` | string | 执行配置 | 必须为 `real_controlled_single_step_execution` |
| 3 | `current_task_id` | string | tasks.md | 当前已完成或正在处理的任务编号 |
| 4 | `next_pending_task_id` | string | tasks.md | 下一个 pending 任务编号 |
| 5 | `selected_next_task` | string | tasks.md | 选中的下一个待执行任务 |
| 6 | `max_tasks` | int | 用户输入 | 单次运行最大任务数，范围 [1, 2] |
| 7 | `tasks_attempted` | int | checkpoint | 已尝试的任务数 |
| 8 | `tasks_completed` | int | checkpoint | 已完成的任务数 |

### 3.2 工作区输入

| # | 字段 | 类型 | 来源 | 说明 |
|---|------|------|------|------|
| 9 | `workspace_status` | string | git status --short | 工作区状态：clean / dirty |
| 10 | `staged_files` | list | git diff --cached | 暂存区文件列表 |
| 11 | `current_branch` | string | git branch --show-current | 当前分支 |
| 12 | `last_commit` | string | git log --oneline -1 | 最近提交 |

### 3.3 审批记录输入

| # | 字段 | 类型 | 来源 | 说明 |
|---|------|------|------|------|
| 13 | `approval_record_path` | string | approval record 文件 | approval record 文件路径 |
| 14 | `approval_record_status` | string | approval record 文件 | 状态：exists / missing |
| 15 | `approval_record_approved_by` | string | approval record 文件 | 审批人，必须为 human |
| 16 | `approval_record_approval_status` | string | approval record 文件 | 审批状态：approved / pending / rejected |

### 3.4 检查点与报告输入

| # | 字段 | 类型 | 来源 | 说明 |
|---|------|------|------|------|
| 17 | `checkpoint_path` | string | checkpoint 文件 | checkpoint 文件路径 |
| 18 | `checkpoint_status` | string | checkpoint 文件 | 状态：exists / missing |
| 19 | `checkpoint_consistent` | bool | checkpoint 校验 | checkpoint 内容是否与当前状态一致 |
| 20 | `report_path` | string | report 文件 | 报告文件路径 |
| 21 | `report_status` | string | report 文件 | 状态：exists / missing / will_generate |

### 3.5 执行范围输入

| # | 字段 | 类型 | 来源 | 说明 |
|---|------|------|------|------|
| 22 | `allowed_scope` | list | approval record | 允许的文件/目录范围 |
| 23 | `planned_files` | list | approval record | 计划变更的文件列表 |
| 24 | `command_allowlist` | list | approval record | 允许执行的命令列表 |

### 3.6 安全标志输入

| # | 字段 | 类型 | 来源 | 说明 |
|---|------|------|------|------|
| 25 | `validation_status` | string | validation report | 当前任务验证结果：pass / fail / unknown |
| 26 | `rework_required` | bool | 验证结果 | 当前任务是否需要返工 |
| 27 | `manual_review_required` | bool | gate 判断 | 是否需要人工审查 |
| 28 | `manual_stop_requested` | bool | 用户信号 | 是否有手动停止请求 |
| 29 | `rate_limit_status` | string | 运行状态 | 是否触发速率限制 |
| 30 | `stage_boundary_check` | string | stage 校验 | 当前是否在 Stage 8 边界内 |

### 3.7 执行控制输入

| # | 字段 | 类型 | 来源 | 说明 |
|---|------|------|------|------|
| 31 | `real_execution_requested` | bool | 执行请求 | 是否请求真实执行 |
| 32 | `real_execution_allowed` | bool | 安全配置 | 是否允许真实执行（只能由 gate 设置） |
| 33 | `push_allowed` | bool | 安全配置 | 是否允许 push，必须为 false |
| 34 | `resume_allowed` | bool | 安全配置 | 是否允许 resume，默认 false |
| 35 | `dirty_workspace_policy` | string | 安全配置 | dirty workspace 处理策略：block |
| 36 | `git_backup_required` | bool | 安全配置 | 是否需要 git backup |
| 37 | `commit_required` | bool | 安全配置 | 是否需要 commit |

### 3.8 输入字段统计

```text
总计 37 个输入字段，分 7 组：
  - 运行级别输入：8 个
  - 工作区输入：4 个
  - 审批记录输入：4 个
  - 检查点与报告输入：5 个
  - 执行范围输入：3 个
  - 安全标志输入：6 个
  - 执行控制输入：7 个
```

---

## 4. Gate 输出设计

Execution gate 在完成所有检查后输出以下结构。

### 4.1 输出字段

| # | 字段 | 类型 | 说明 |
|---|------|------|------|
| 1 | `allowed` | bool | 是否允许真实受控执行 |
| 2 | `decision` | string | 决策类型：`allowed_for_real_controlled_single_step` / `stop` / `blocked` |
| 3 | `execution_mode` | string | 执行模式：`real_controlled_single_step` / null |
| 4 | `selected_next_task` | string | 选中的下一个待执行任务 |
| 5 | `stop_reason` | string | 如果不允许执行，停止原因 |
| 6 | `required_actions` | list | 如果 blocked，需要执行的动作列表 |
| 7 | `failure_reasons` | list | 如果 blocked，所有不通过的原因列表 |
| 8 | `approval_record_required` | bool | 是否需要生成 approval record v2.0 |
| 9 | `checkpoint_required` | bool | 是否需要生成 checkpoint v2.0 |
| 10 | `report_required` | bool | 是否需要生成 execution report |
| 11 | `manual_review_required` | bool | 是否需要人工审查 |
| 12 | `git_backup_required` | bool | 是否需要执行 git backup |
| 13 | `commit_gate_required` | bool | 是否需要在执行后通过 commit gate |
| 14 | `push_gate_required` | bool | 是否需要在执行后通过 push gate（始终 false） |
| 15 | `resume_allowed` | bool | 是否允许 resume（始终 false） |
| 16 | `notes` | string | 补充说明 |

### 4.2 输出结构示例

#### 允许真实受控执行

```yaml
allowed: true
decision: allowed_for_real_controlled_single_step
execution_mode: real_controlled_single_step
selected_next_task: T152
stop_reason: null
required_actions:
  - "Generate approval record v2.0"
  - "Generate checkpoint v2.0 (pre-execution)"
  - "Execute task within allowed_scope"
  - "Run validation after execution"
  - "Generate execution report"
failure_reasons: []
approval_record_required: true
checkpoint_required: true
report_required: true
manual_review_required: false
git_backup_required: true
commit_gate_required: true
push_gate_required: false
resume_allowed: false
notes: "All G1-G21 and E1-E18 gate checks passed. Ready for real controlled single-step execution."
```

#### 安全停止

```yaml
allowed: false
decision: stop
execution_mode: null
selected_next_task: null
stop_reason: completed_max_tasks
required_actions:
  - "Review execution summary"
  - "If more tasks needed, start a new run"
failure_reasons: []
approval_record_required: false
checkpoint_required: true
report_required: true
manual_review_required: false
git_backup_required: false
commit_gate_required: false
push_gate_required: false
resume_allowed: false
notes: "Reached max_tasks limit. All attempted tasks completed successfully."
```

#### 阻塞停止

```yaml
allowed: false
decision: blocked
execution_mode: null
selected_next_task: null
stop_reason: blocked_by_missing_approval_record
required_actions:
  - "Generate approval record v2.0 for next task"
  - "Get human approval"
  - "Re-run execution gate after approval record is complete"
failure_reasons:
  - "Approval record does not exist for next task"
  - "Real controlled execution requires complete approval record v2.0"
approval_record_required: true
checkpoint_required: false
report_required: false
manual_review_required: true
git_backup_required: false
commit_gate_required: false
push_gate_required: false
resume_allowed: false
notes: "Execution gate blocked: approval record missing. Manual review required."
```

---

## 5. Pass 条件设计

Execution gate 允许真实受控执行（`allowed=true`）时，以下所有条件必须同时满足。

### 5.1 阶段与任务条件（E1-E6）

| # | Gate Check | 条件 | 检查方式 | 失败归类 |
|---|------------|------|----------|----------|
| E1 | 当前 Stage 是 Stage 8 | `stage` = `Stage 8` | 校验 stage 字段 | blocked_by_stage_boundary |
| E2 | next task 属于 Stage 8 | `next_pending_task_stage` = `Stage 8` | 读取 tasks.md 校验 | blocked_by_stage_boundary |
| E3 | 不进入 Stage 9 | `stage_boundary_check` = `within` | 校验 stage boundary | blocked_by_stage_boundary |
| E4 | max_tasks 有明确安全上限 | `max_tasks` 存在且 1 ≤ max_tasks ≤ 2 | 校验 max_tasks 字段 | blocked_by_unknown_error |
| E5 | 当前任务状态明确 | `current_task_id` 存在或明确为首次运行 | 读取 tasks.md | blocked_by_unknown_error |
| E6 | next task 明确 | `next_pending_task_id` 和 `selected_next_task` 存在 | 检查 tasks.md | no_pending_tasks |

### 5.2 工作区条件（E7-E8，复用 G8-G9 并增强）

| # | Gate Check | 条件 | 检查方式 | 失败归类 |
|---|------------|------|----------|----------|
| E7 | workspace clean | `workspace_status` = `clean` | git status --short | blocked_by_dirty_workspace |
| E8 | staged files 为空 | `staged_files` = [] | git diff --cached --name-only | blocked_by_staged_changes |

### 5.3 审批与记录条件（E9-E12）

| # | Gate Check | 条件 | 检查方式 | 失败归类 |
|---|------------|------|----------|----------|
| E9 | approval record 存在且完整 | `approval_record_status` = `exists` | 检查 approval record 文件 | blocked_by_missing_approval_record |
| E10 | checkpoint 存在且完整 | `checkpoint_status` = `exists` 且 `checkpoint_consistent` = `true` | 检查 checkpoint 文件 | blocked_by_missing_checkpoint |
| E11 | report 存在或将在本 step 生成 | `report_status` = `exists` 或 `will_generate` | 检查 report 文件 | blocked_by_missing_report |
| E12 | validation status 为 pass | `validation_status` = `pass` | 检查 validation report | blocked_by_validation_failure |

### 5.4 执行范围条件（E13-E15）

| # | Gate Check | 条件 | 检查方式 | 失败归类 |
|---|------------|------|----------|----------|
| E13 | allowed_scope 明确 | `allowed_scope` 非空 list | 校验 allowed_scope 字段 | blocked_by_missing_allowed_scope |
| E14 | command_allowlist 明确 | `command_allowlist` 非空 list | 校验 command_allowlist 字段 | blocked_by_missing_command_allowlist |
| E15 | planned_files 明确 | `planned_files` 非空 list 或明确为 [] | 校验 planned_files 字段 | blocked_by_unapproved_changes |

### 5.5 安全标志条件（E16-E18，复用 G16-G19 并增强）

| # | Gate Check | 条件 | 检查方式 | 失败归类 |
|---|------------|------|----------|----------|
| E16 | real_execution_allowed 必须经过单独 gate | `real_execution_allowed` 只能由 execution gate 设置，不能外部传入 | 校验审批链 | blocked_by_real_execution_gate |
| E17 | push_allowed 必须保持 false | `push_allowed` = `false` | 校验安全标志 | blocked_by_git_safety_gate |
| E18 | 无阻塞标志 | `rework_required` = `false`, `manual_stop_requested` = `false`, `rate_limit_status` = `clear` | 校验安全标志 | 各对应 stop_reason |

### 5.6 Pass 条件总结

```text
G1-G21 (T143) 全部通过 + E1-E18 (T149) 全部通过
→ allowed=true
→ decision=allowed_for_real_controlled_single_step
→ execution_mode=real_controlled_single_step

任一 gate check 失败
→ allowed=false
→ decision=stop 或 blocked
→ 对应 stop_reason

不存在部分通过。
```

---

## 6. Fail 条件设计

以下任一条件触发时，execution gate 必须拒绝真实受控执行。

### 6.1 工作区异常

| # | 触发条件 | stop_reason | 对应 Gate |
|---|----------|-------------|-----------|
| 1 | `workspace_status` = `dirty` | blocked_by_dirty_workspace | E7 |
| 2 | `staged_files` 不为空 | blocked_by_staged_changes | E8 |

### 6.2 审批与记录缺失

| # | 触发条件 | stop_reason | 对应 Gate |
|---|----------|-------------|-----------|
| 3 | `approval_record_status` = `missing` | blocked_by_missing_approval_record | E9 |
| 4 | `checkpoint_status` = `missing` | blocked_by_missing_checkpoint | E10 |
| 5 | `report_status` = `missing` 且非 `will_generate` | blocked_by_missing_report | E11 |
| 6 | `validation_status` = `fail` | blocked_by_validation_failure | E12 |

### 6.3 执行范围缺失

| # | 触发条件 | stop_reason | 对应 Gate |
|---|----------|-------------|-----------|
| 7 | `allowed_scope` 缺失或为空 | blocked_by_missing_allowed_scope | E13 |
| 8 | `command_allowlist` 缺失或为空 | blocked_by_missing_command_allowlist | E14 |
| 9 | `planned_files` 不在 allowed_scope 内 | blocked_by_unapproved_changes | E15 |

### 6.4 阶段越权

| # | 触发条件 | stop_reason | 对应 Gate |
|---|----------|-------------|-----------|
| 10 | `next_pending_task_stage` 不属于 Stage 8 | blocked_by_stage_boundary | E2 |
| 11 | 尝试进入 Stage 9 | blocked_by_stage_boundary | E3 |
| 12 | `max_tasks` 缺失 | blocked_by_unknown_error | E4 |
| 13 | `max_tasks` > 2 | blocked_by_unknown_error | E4 |

### 6.5 安全标志异常

| # | 触发条件 | stop_reason | 对应 Gate |
|---|----------|-------------|-----------|
| 14 | `push_allowed` = `true` | blocked_by_git_safety_gate | E17 |
| 15 | `real_execution_allowed` = `true` 但未经过 execution gate 审批 | blocked_by_real_execution_gate | E16 |
| 16 | `rework_required` = `true` | blocked_by_rework_required | E18 |
| 17 | `manual_stop_requested` = `true` | manual_stop_required | E18 |
| 18 | `rate_limit_status` = `triggered` | blocked_by_rate_limit | E18 |

### 6.6 未知错误

| # | 触发条件 | stop_reason | 对应 Gate |
|---|----------|-------------|-----------|
| 19 | checkpoint 内容与实际状态不一致 | blocked_by_unknown_error | E10 |
| 20 | 任何未预期异常 | blocked_by_unknown_error | - |

### 6.7 拒绝原则

```text
1. 所有拒绝均为 fail-closed — 不存在 "部分拒绝"
2. 拒绝后必须保留现场 — 不自动清理、不自动回滚
3. 拒绝后必须记录 stop_reason — 不允许无原因停止
4. 拒绝后必须输出 required_actions — 不允许只报错不给建议
5. 拒绝后必须输出 failure_reasons — 每个失败原因都需记录
6. 拒绝后不允许继续执行 — 必须等待人工介入或修复后重新 gate
7. 拒绝后不允许自动 resume — resume_allowed 始终 false
```

---

## 7. stop_reason 设计

### 7.1 完整 stop_reason 列表

#### 正常停止

| # | stop_reason | 触发条件 | resume 允许 | 后续建议动作 |
|---|-------------|----------|-------------|-------------|
| 1 | `allowed_for_real_controlled_single_step` | G1-G21 + E1-E18 全部通过 | 否（执行后需新开 run） | 按 approval record v2.0 执行单步 |
| 2 | `completed_max_tasks` | `tasks_attempted` ≥ `max_tasks` | 否（新开 run） | 审查 execution summary |
| 3 | `no_pending_tasks` | 无 pending 任务 | 否（新开 run） | 检查是否需新增任务 |

#### 安全停止（gate 拦截）

| # | stop_reason | 触发条件 | resume 允许 | 后续建议动作 |
|---|-------------|----------|-------------|-------------|
| 4 | `blocked_by_dirty_workspace` | workspace dirty | 否 | 检查 dirty 文件，提交或回滚 |
| 5 | `blocked_by_staged_changes` | staged files 不为空 | 否 | 检查 staged 文件 |
| 6 | `blocked_by_validation_failure` | validation fail | 否 | 查看 validation report |
| 7 | `blocked_by_rework_required` | rework_required = true | 否 | 执行返工 |
| 8 | `blocked_by_unapproved_changes` | planned_files 不在 allowed_scope 内 | 否 | 审批或拒绝变更 |
| 9 | `blocked_by_stage_boundary` | next task 不属于 Stage 8 | 否 | 确认跨 Stage 需求 |
| 10 | `blocked_by_missing_approval_record` | approval record 不存在 | 否 | 生成 approval record v2.0 |
| 11 | `blocked_by_missing_checkpoint` | checkpoint 不存在或不一致 | 否 | 生成 checkpoint v2.0 |
| 12 | `blocked_by_missing_report` | report 不存在且无生成计划 | 否 | 生成 report |
| 13 | `blocked_by_missing_allowed_scope` | allowed_scope 缺失或为空 | 否 | 明确执行范围 |
| 14 | `blocked_by_missing_command_allowlist` | command_allowlist 缺失或为空 | 否 | 明确命令白名单 |
| 15 | `blocked_by_git_safety_gate` | push_allowed=true 或 Git 安全异常 | 否 | 修复安全标志 |
| 16 | `blocked_by_real_execution_gate` | real_execution_allowed 未经审批 | 否 | 修复 execution gate 审批链 |
| 17 | `blocked_by_push_policy` | 任何 push 尝试 | 否 | 移除 push 请求 |

#### 运行状态停止

| # | stop_reason | 触发条件 | resume 允许 | 后续建议动作 |
|---|-------------|----------|-------------|-------------|
| 18 | `blocked_by_rate_limit` | 速率限制触发 | 否 | 等待冷却后重新运行 |
| 19 | `manual_stop_required` | 用户请求停止 | 否 | 人工确认后可新开一轮 |
| 20 | `blocked_by_unknown_error` | 未分类错误 | 否 | 查看错误日志，人工分析 |

### 7.2 Stop Reason 分类

```text
正常停止（预期行为）：
  1. allowed_for_real_controlled_single_step  — gate 通过，允许执行
  2. completed_max_tasks                       — 达到上限
  3. no_pending_tasks                          — 无待执行任务

安全停止（gate 拦截）：
  4-17. blocked_by_*                           — 各种安全拦截

运行状态停止：
  18. blocked_by_rate_limit                    — 速率限制
  19. manual_stop_required                     — 手动停止
  20. blocked_by_unknown_error                 — 未知错误
```

### 7.3 处理原则

```text
1. allowed_for_real_controlled_single_step → 按 approval record v2.0 执行
2. completed_max_tasks / no_pending_tasks → 可以安全地新开一轮
3. blocked_by_* → 必须修复 gate 失败原因后再继续
4. 所有 stop_reason 都必须记录在 checkpoint 和 execution report 中
5. 不允许自动忽略 stop_reason
6. 不允许自动绕过阻塞
7. 不允许在 stop 后自动 resume
8. resume_allowed 默认 false，不允许自动修改为 true
9. push_allowed 必须保持 false，不允许任何条件豁免
```

---

## 8. Approval Record 要求

### 8.1 Real Controlled Execution Approval Record Schema v2.0

```yaml
approval_record_version: "2.0"
approval_id: "T152-real-controlled-execution-approval"
generated_at: "2026-05-10T15:02:00"

task:
  task_id: "T152"
  stage: "Stage 8"
  operation_type: "real_controlled_single_step_execution"
  execution_mode: "real_controlled_single_step"

agent:
  selected_agent: "Developer"
  agent_role: "implementer"

execution:
  planned_action: "Execute T152 real controlled single-step execution trial"
  planned_files:
    - "tools/continuous_task_planner.py"
    - "runner.py"
  allowed_scope:
    - "tools/"
    - "runner.py"
    - "docs/"
    - "reports/"
  command_allowlist:
    - "python runner.py"
    - "git status --short"
    - "git diff"
    - "git log --oneline"
    - "git add"
    - "git commit"
  real_execution_requested: true
  real_execution_allowed: true
  push_allowed: false
  resume_allowed: false
  stage_boundary_check: "within_stage_8"

approval:
  approval_status: "approved"
  approved_by: "human"
  approval_time: "2026-05-10T15:01:00"

validation:
  validation_required: true
  validation_status: "pending"
  validation_report_path: "null"

git:
  git_backup_required: true
  commit_required: true
  commit_message_template: "feat: add T152 stage 8 real controlled single-step execution trial"

decision:
  final_status: "approved_for_execution"
  ready_for_execution: true
  ready_for_git_commit: false
  ready_for_push: false
  ready_for_stage_9: false

notes: |
  Approval for T152 real controlled single-step execution.
  max_tasks=1. push_allowed=false. resume_allowed=false.
  approved_by=human required.
```

### 8.2 关键约束

| # | 约束 | 说明 |
|---|------|------|
| 1 | `approval_record_version` 必须为 `2.0` | 区分 v1.0（dry-run）和 v2.0（real execution） |
| 2 | `operation_type` 必须为 `real_controlled_single_step_execution` | 明确操作类型 |
| 3 | `execution_mode` 必须为 `real_controlled_single_step` | 明确执行模式 |
| 4 | `push_allowed` 必须为 `false` | 始终禁止 push |
| 5 | `resume_allowed` 必须为 `false` | 不允许自动 resume |
| 6 | `real_execution_allowed` 必须由 execution gate 设置 | 不允许外部传入 |
| 7 | `real_execution_requested` 必须为 `true` | 明确请求真实执行 |
| 8 | `allowed_scope` 必须明确列出 | 不允许通配符或模糊范围 |
| 9 | `command_allowlist` 必须明确列出 | 不允许执行白名单外的命令 |
| 10 | `approved_by` 必须为 `human` | 当前阶段不允许自动审批 |
| 11 | `approval_status` 从 `pending` 开始 | 审批后才更新为 `approved` |
| 12 | `stage_boundary_check` 必须为 `within_stage_8` | 不允许跨 Stage |
| 13 | `ready_for_push` 始终为 `false` | Stage 8 不允许 push |
| 14 | `ready_for_stage_9` 始终为 `false` | Stage 8 不允许进入 Stage 9 |
| 15 | `final_status` 从 `pending` 开始 | 执行后更新为 `completed` / `failed` |

### 8.3 与 T143 approval record 的区别

| # | 字段 | T143 v1.0 | T149 v2.0 | 说明 |
|---|------|-----------|-----------|------|
| 1 | `approval_record_version` | 1.0 | 2.0 | 版本区分 |
| 2 | `operation_type` | 单任务审批 | `real_controlled_single_step_execution` | 操作类型更明确 |
| 3 | `execution_mode` | 无 | `real_controlled_single_step` | 新增执行模式 |
| 4 | `real_execution_requested` | 无 | true | 新增真实执行请求标志 |
| 5 | `real_execution_allowed` | 无 | true（由 gate 设置） | 新增真实执行许可 |
| 6 | `command_allowlist` | 无 | 必须列出 | 新增命令白名单 |
| 7 | `commit_message_template` | 无 | 必须提供 | 新增 commit 消息模板 |

---

## 9. Checkpoint 要求

### 9.1 Real Controlled Execution Checkpoint Schema v2.0

```yaml
checkpoint_version: "2.0"
run_id: "stage8-real-run-001"
stage: "Stage 8"
mode: "real_controlled_single_step_execution"
real_controlled_execution: true

timing:
  started_at: "2026-05-10T15:00:00"
  ended_at: null
  last_checkpoint_at: "2026-05-10T15:05:00"

limits:
  max_tasks: 1
  tasks_attempted: 0
  tasks_completed: 0

current_state:
  current_task: "T152"
  last_completed_task: "null"
  next_pending_task: "T152"
  selected_next_task: "T152"
  stop_reason: null

workspace:
  status_before: "clean"
  status_after: "clean"
  staged_files_before: []
  staged_files_after: []
  current_branch: "main"
  last_commit_before: "1272b47 docs: add stage 8 real controlled continuous execution plan"
  last_commit_after: "null"

records:
  approval_record_path: "reports/stage8/real-execution-approval-T152.md"
  checkpoint_path: "reports/stage8/real-execution-checkpoint-T152.md"
  reports_generated: []
  commits_created: []
  pushes_created: []

validation:
  validation_status: "pending"
  validation_report_path: "null"

resume:
  resume_allowed: false
  manual_review_required: false

errors: []

notes: |
  Real controlled execution checkpoint for T152.
  Pre-execution state recorded.
  G1-G21 + E1-E18 gate checks passed.
```

### 9.2 关键约束

| # | 约束 | 说明 |
|---|------|------|
| 1 | `checkpoint_version` 必须为 `2.0` | 区分 v1.0（dry-run）和 v2.0（real execution） |
| 2 | `mode` 必须为 `real_controlled_single_step_execution` | 区分 dry-run 和真实执行 |
| 3 | `real_controlled_execution` 必须为 `true` | 标记为真实执行模式 |
| 4 | `resume_allowed` 默认 `false` | 不允许自动 resume |
| 5 | `pushes_created` 始终为空 | 任何 push 都禁止 |
| 6 | `last_commit_before` 必须在执行前记录 | 作为执行基线 |
| 7 | `last_commit_after` 在执行后更新 | 确认执行后的 commit |
| 8 | `staged_files_before` / `staged_files_after` 都必须记录 | 确认执行前后 staged 变化 |
| 9 | `approval_record_path` 必须指向真实存在的文件 | 真实 step 必须有审批 |
| 10 | `validation_status` 从 `pending` 开始 | 执行后更新为 `pass` / `fail` |

### 9.3 与 T143 checkpoint 的区别

| # | 字段 | T143 v1.0 | T149 v2.0 | 说明 |
|---|------|-----------|-----------|------|
| 1 | `checkpoint_version` | 1.0 | 2.0 | 版本区分 |
| 2 | `mode` | `continuous_real_task_auto_advance` | `real_controlled_single_step_execution` | 模式更明确 |
| 3 | `real_controlled_execution` | 无 | `true` | 新增真实执行标志 |
| 4 | `staged_files_before` | 无 | 必须记录 | 新增执行前 staged 文件 |
| 5 | `staged_files_after` | 无 | 必须记录 | 新增执行后 staged 文件 |
| 6 | `last_commit_before` | 无 | 必须记录 | 新增执行前 commit 基线 |
| 7 | `last_commit_after` | 无 | 执行后更新 | 新增执行后 commit |
| 8 | `approval_record_path` | 无 | 必须指向真实文件 | 新增审批记录路径 |
| 9 | `validation_status` | 无 | `pending` → `pass` / `fail` | 新增验证状态追踪 |

---

## 10. Git 策略

### 10.1 T149 Git 边界

| # | 策略 | 说明 |
|---|------|------|
| 1 | T149 不允许真实 git add / commit / push | 只做设计，不执行 |
| 2 | 后续真实执行试运行也不自动 push | push 始终禁止 |
| 3 | 不允许 `git add .` | 必须指定具体文件白名单 |
| 4 | 不允许 `git add -A` | 必须指定具体文件白名单 |
| 5 | 提交必须走指定文件白名单 | planned_files 和 allowed_scope 内的文件 |
| 6 | commit gate 与 push gate 应分离 | commit 需审批，push 始终禁止 |
| 7 | commit message 需校验 | 必须符合 commit message 规范 |
| 8 | 不允许 `git commit --no-verify` | 必须经过 hooks |
| 9 | 不允许 `git reset --hard` | 不允许 force 操作 |

### 10.2 真实受控 step 的 Git 流程（设计，供 T152 参考）

```text
真实受控 step 的 Git 处理流程：

1. 执行前：
   - 记录 last_commit_before
   - 记录 staged_files_before
   - 确认 workspace clean

2. 执行任务：
   - 在 allowed_scope 内产出代码变更
   - 不执行 planned_files 外的变更
   - 不执行 command_allowlist 外的命令

3. 变更检查：
   - 对比 planned_files vs 实际变更
   - 实际变更超出 allowed_scope → 阻塞，停止
   - 实际变更在 allowed_scope 内 → 继续

4. Git approval gate：
   - 审批变更内容
   - 确认 commit message
   - 确认文件列表

5. git add（仅白名单文件）：
   - 逐个文件 git add
   - 不使用 git add . 或 git add -A

6. git commit（需 approval record v2.0）：
   - commit message 需校验
   - 不使用 --no-verify
   - 不使用 -m "auto"

7. 执行后：
   - 记录 last_commit_after
   - 记录 staged_files_after
   - 不 push

禁止：
  - git push
  - git add .
  - git add -A
  - git commit --no-verify
  - git commit -m "auto"
  - git reset --hard
  - 任何 force 操作
```

### 10.3 Stage 9 才处理完整 Git 自动化

```text
Stage 8 真实受控推进阶段：
  - 允许受控 git add（白名单文件）
  - 允许受控 git commit（需审批）
  - 不允许 git push

Stage 9（未来）：
  - 自动 Git 备份与执行记录
  - Git commit/push 的完整自动化
  - 不在 Stage 8 实现
```

---

## 11. CLI / workflow 建议

### 11.1 建议的 dry-run 命令（供 T150 参考）

只做设计，不实现。

```bash
# T150 dry-run 入口（建议）
python runner.py stage8-real-controlled-execution-dry-run --max-tasks 1
python runner.py stage8-real-controlled-execution-dry-run --sample pass_real_controlled
python runner.py stage8-real-controlled-execution-dry-run --sample fail_dirty_workspace
python runner.py stage8-real-controlled-execution-dry-run --sample fail_missing_approval
```

### 11.2 建议的 dry-run sample 场景（供 T150 参考）

| # | Sample | 类型 | 说明 |
|---|--------|------|------|
| 1 | `pass_real_controlled` | pass | max_tasks=1, workspace clean, approval/checkpoint/report 完整 |
| 2 | `pass_select_next_task` | pass | 正确选择 next pending task |
| 3 | `stop_no_pending_tasks` | safe stop | 无 pending tasks |
| 4 | `stop_max_tasks_reached` | safe stop | 达到 max_tasks 上限 |
| 5 | `fail_dirty_workspace` | fail | workspace dirty |
| 6 | `fail_staged_changes` | fail | staged files 不为空 |
| 7 | `fail_missing_approval_record` | fail | approval record 缺失 |
| 8 | `fail_missing_checkpoint` | fail | checkpoint 缺失 |
| 9 | `fail_missing_report` | fail | report 缺失 |
| 10 | `fail_missing_allowed_scope` | fail | allowed_scope 缺失 |
| 11 | `fail_missing_command_allowlist` | fail | command_allowlist 缺失 |
| 12 | `fail_stage_boundary` | fail | next task 属于 Stage 9 |
| 13 | `fail_validation_failure` | fail | validation fail |
| 14 | `fail_push_allowed_true` | fail | push_allowed=true |
| 15 | `fail_real_execution_gate` | fail | real_execution_allowed 未审批 |
| 16 | `fail_rate_limit` | fail | rate limit blocked |
| 17 | `fail_rework_required` | fail | rework required |
| 18 | `fail_unknown_error` | fail | unknown error |

### 11.3 重要说明

```text
1. T149 不新增 CLI
2. T149 不实现代码
3. T149 不执行真实连续任务
4. T150 仍应先做 dry-run
5. T150 应实现 T149 设计的 E1-E18 execution gate check
6. T150 应实现 T149 设计的 approval record v2.0 生成
7. T150 应实现 T149 设计的 checkpoint v2.0 生成
8. T150 不允许直接执行真实任务
```

---

## 12. pass / fail 场景设计

### 12.1 Pass 场景

#### P1：max_tasks=1，workspace clean，approval/checkpoint/report 完整

```yaml
场景描述：所有 gate check 通过，允许进入 real controlled single-step execution
输入：
  stage: Stage 8
  mode: real_controlled_single_step_execution
  max_tasks: 1
  tasks_attempted: 0
  tasks_completed: 0
  workspace_status: clean
  staged_files: []
  current_branch: main
  last_commit: "1272b47 docs: add stage 8 real controlled continuous execution plan"
  approval_record_status: exists
  approval_record_approved_by: human
  approval_record_approval_status: approved
  checkpoint_status: exists
  checkpoint_consistent: true
  report_status: will_generate
  validation_status: pass
  rework_required: false
  manual_stop_requested: false
  rate_limit_status: clear
  stage_boundary_check: within
  allowed_scope: ["tools/", "runner.py", "docs/", "reports/"]
  planned_files: ["tools/continuous_task_planner.py", "runner.py"]
  command_allowlist: ["python runner.py", "git status --short", "git diff", "git log --oneline"]
  real_execution_requested: true
  push_allowed: false
  resume_allowed: false
  next_pending_task_id: T152
  next_pending_task_stage: Stage 8
  selected_next_task: T152
预期输出：
  allowed: true
  decision: allowed_for_real_controlled_single_step
  execution_mode: real_controlled_single_step
  selected_next_task: T152
  stop_reason: null
  gate_checks_passed: 39 (G1-G21 + E1-E18)
  gate_checks_failed: 0
```

#### P2：no pending tasks，安全停止

```yaml
场景描述：所有任务已完成，没有 pending 任务
输入：
  stage: Stage 8
  next_pending_task_id: null
  max_tasks: 1
  tasks_attempted: 1
  tasks_completed: 1
预期输出：
  allowed: false
  decision: stop
  stop_reason: no_pending_tasks
  execution_mode: null
```

#### P3：current task done，next pending task 是 Stage 8，gate 允许继续规划

```yaml
场景描述：当前任务完成，下一个 pending task 属于 Stage 8
输入：
  stage: Stage 8
  current_task_id: T149
  next_pending_task_id: T150
  next_pending_task_stage: Stage 8
  validation_status: pass
  approval_record_status: exists
  checkpoint_status: exists
  workspace_status: clean
  staged_files: []
  max_tasks: 1
  tasks_attempted: 0
  push_allowed: false
  allowed_scope: ["tools/", "runner.py"]
  command_allowlist: ["python runner.py"]
  planned_files: ["tools/continuous_task_planner.py"]
  real_execution_requested: true
预期输出：
  allowed: true
  decision: allowed_for_real_controlled_single_step
  selected_next_task: T150
```

### 12.2 Fail 场景

#### F1：dirty workspace

```yaml
场景描述：工作区有未提交的修改
输入：
  workspace_status: dirty
  staged_files: []
预期输出：
  allowed: false
  decision: blocked
  stop_reason: blocked_by_dirty_workspace
  failure_reasons: ["Workspace is dirty"]
```

#### F2：staged changes

```yaml
场景描述：暂存区有文件
输入：
  workspace_status: clean
  staged_files: ["docs/extra.md"]
预期输出：
  allowed: false
  decision: blocked
  stop_reason: blocked_by_staged_changes
  failure_reasons: ["Staged files not empty: docs/extra.md"]
```

#### F3：missing approval record

```yaml
场景描述：缺少 approval record v2.0
输入：
  approval_record_status: missing
预期输出：
  allowed: false
  decision: blocked
  stop_reason: blocked_by_missing_approval_record
  failure_reasons: ["Approval record v2.0 does not exist for next task"]
```

#### F4：missing checkpoint

```yaml
场景描述：缺少 checkpoint v2.0
输入：
  checkpoint_status: missing
预期输出：
  allowed: false
  decision: blocked
  stop_reason: blocked_by_missing_checkpoint
  failure_reasons: ["Checkpoint v2.0 does not exist"]
```

#### F5：missing report

```yaml
场景描述：缺少报告且无生成计划
输入：
  report_status: missing
预期输出：
  allowed: false
  decision: blocked
  stop_reason: blocked_by_missing_report
  failure_reasons: ["Report does not exist and no generation plan"]
```

#### F6：missing allowed scope

```yaml
场景描述：allowed_scope 缺失
输入：
  allowed_scope: []
预期输出：
  allowed: false
  decision: blocked
  stop_reason: blocked_by_missing_allowed_scope
  failure_reasons: ["allowed_scope is empty or missing"]
```

#### F7：missing command allowlist

```yaml
场景描述：command_allowlist 缺失
输入：
  command_allowlist: []
预期输出：
  allowed: false
  decision: blocked
  stop_reason: blocked_by_missing_command_allowlist
  failure_reasons: ["command_allowlist is empty or missing"]
```

#### F8：validation fail

```yaml
场景描述：当前任务验证未通过
输入：
  validation_status: fail
预期输出：
  allowed: false
  decision: blocked
  stop_reason: blocked_by_validation_failure
  failure_reasons: ["Current task validation failed"]
```

#### F9：next task 属于 Stage 9

```yaml
场景描述：下一个 pending 任务属于 Stage 9
输入：
  next_pending_task_id: T155
  next_pending_task_stage: Stage 9
预期输出：
  allowed: false
  decision: blocked
  stop_reason: blocked_by_stage_boundary
  failure_reasons: ["Next task T155 belongs to Stage 9, not Stage 8"]
```

#### F10：max_tasks 过大

```yaml
场景描述：max_tasks 超过安全上限
输入：
  max_tasks: 5
预期输出：
  allowed: false
  decision: blocked
  stop_reason: blocked_by_unknown_error
  failure_reasons: ["max_tasks exceeds safety limit 2 for real controlled execution"]
```

#### F11：push_allowed=true

```yaml
场景描述：push_allowed 被设置为 true
输入：
  push_allowed: true
预期输出：
  allowed: false
  decision: blocked
  stop_reason: blocked_by_git_safety_gate
  failure_reasons: ["push_allowed must be false"]
```

#### F12：resume_allowed=true 未审批

```yaml
场景描述：resume_allowed 被设置为 true 但未经过 resume gate
输入：
  resume_allowed: true
预期输出：
  allowed: false
  decision: blocked
  stop_reason: blocked_by_unknown_error
  failure_reasons: ["resume_allowed must be false"]
```

#### F13：rate_limit blocked

```yaml
场景描述：触发速率限制
输入：
  rate_limit_status: triggered
预期输出：
  allowed: false
  decision: blocked
  stop_reason: blocked_by_rate_limit
  failure_reasons: ["Rate limit triggered"]
```

#### F14：rework_required

```yaml
场景描述：当前任务需要返工
输入：
  rework_required: true
预期输出：
  allowed: false
  decision: blocked
  stop_reason: blocked_by_rework_required
  failure_reasons: ["Current task requires rework"]
```

#### F15：unknown error

```yaml
场景描述：发生未分类错误
输入：
  checkpoint_consistent: false
预期输出：
  allowed: false
  decision: blocked
  stop_reason: blocked_by_unknown_error
  failure_reasons: ["Checkpoint is not consistent"]
```

### 12.3 场景统计

```text
Pass 场景：3 个 (P1-P3)
Fail 场景：15 个 (F1-F15)
总计：18 个场景

验证原则：
  1. 所有 pass 场景必须返回 allowed=true
  2. 所有 fail 场景必须返回 allowed=false
  3. 所有 fail 场景必须有明确的 stop_reason
  4. 所有 fail 场景必须有 failure_reasons
  5. 不存在 "部分通过" 的中间状态
```

---

## 13. 后续任务关系

### 13.1 任务链

| # | 任务 | 角色 | 与 T149 的关系 |
|---|------|------|---------------|
| 1 | T149 | Designer | 当前任务：设计 execution gate |
| 2 | T150 | Developer | 基于 T149 gate 设计实现 dry-run，包括 E1-E18 |
| 3 | T151 | Validator | 验证 T150 dry-run 的 pass/fail 场景 |
| 4 | T152 | Developer | 基于 T150/T151 实现 max_tasks=1 真实受控执行 |
| 5 | T153 | Validator | 验证 T152 真实执行结果 |
| 6 | T154 | Archiver | 归档 T149-T153 全部成果 |

### 13.2 T149 对 T150 的设计约束

```text
1. T150 必须实现 T149 定义的 18 项 execution gate check (E1-E18)
2. T150 必须复用 T143 的 21 项 safety gate check (G1-G21)
3. T150 必须实现 T149 定义的 approval record v2.0 生成
4. T150 必须实现 T149 定义的 checkpoint v2.0 生成
5. T150 必须实现 T149 定义的 execution gate 输出结构
6. T150 必须实现 T149 定义的 20 种 stop_reason
7. T150 必须遵循 T149 定义的 fail-closed 原则
8. T150 仍然不允许：
   - 真实连续任务执行
   - 真实 git add / commit / push
   - 自动跨入 Stage 9
   - 修改业务代码
   - 绕过任何 gate check
```

### 13.3 T149 对 T152 的设计约束

```text
1. T152 的真实执行必须先通过 T149 的全部 E1-E18 gate check
2. T152 必须使用 T149 定义的 approval record v2.0
3. T152 必须使用 T149 定义的 checkpoint v2.0
4. T152 的 stop_reason 必须从 T149 定义的 20 种中选择
5. T152 不允许绕过任何 gate check
6. T152 不允许自动 push
7. T152 不允许跨入 Stage 9
```

---

## 14. 后续建议

```text
NEXT_PENDING=T150
NEXT_STAGE=Stage 8
```

T150 仍然应先实现 dry-run，不得直接执行真实连续任务。

T150 应实现的内容：
1. 在 T144/T146 基础上实现 real controlled execution dry-run
2. 实现 T149 定义的 E1-E18 execution gate check
3. 实现 T149 定义的 approval record v2.0 生成
4. 实现 T149 定义的 checkpoint v2.0 生成
5. 实现 T149 定义的 20 种 stop_reason
6. 实现 18 个 sample 场景（3 pass + 15 fail）

T150 不允许：
  - 执行真实连续任务
  - 真实 git add / commit / push
  - 自动跨入 Stage 9
  - 修改业务代码
  - 绕过任何 gate check

---

## 设计元数据

- 设计角色：Designer / Architecture Agent
- 设计日期：2026-05-10
- 设计基准提交：1272b47 docs: add stage 8 real controlled continuous execution plan
- 工作区状态：clean
- 前置条件：Stage 8 planning/dry-run 链路完成（T143-T148），Stage 8 real controlled continuous execution plan 完成
- 设计结论：T149_EXECUTION_GATE_DESIGN_COMPLETE=yes
