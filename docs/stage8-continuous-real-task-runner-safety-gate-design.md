# T143：Stage 8 continuous real task runner safety gate 设计

设计时间：2026-05-09
阶段：Stage 8 — 真实连续任务自动推进
任务角色：Designer / Architecture Agent
前置条件：STAGE7_COMPLETE=yes, STAGE8_PLAN_COMPLETE=yes

---

## 1. 设计目标

T143 的目标是为 Stage 8 连续任务自动推进设计最核心的 **safety gate**。

这个 gate 的核心职责是：**在系统从一个已完成任务准备推进到下一个 pending 任务之前，判断当前状态是否允许继续推进**。

### 1.1 Safety gate 要解决的风险

连续任务自动推进相比单任务执行增加了以下风险：

| # | 风险 | 说明 |
|---|------|------|
| 1 | 无限循环 | 没有硬性上限，系统可能无限循环执行 |
| 2 | dirty workspace 级联 | 上一个任务残留的 dirty 文件影响下一个任务 |
| 3 | 跨阶段越权 | 自动推进到不属于当前 Stage 的任务 |
| 4 | 失败后继续 | 当前任务已失败但系统继续推进下一个任务 |
| 5 | 缺少审批链 | 任务之间缺少 approval record 衔接 |
| 6 | 自动 push | 连续推进过程中自动执行 push |
| 7 | 状态不一致 | 缓存的任务状态与实际 tasks.md 不一致 |
| 8 | 速率失控 | 短时间内执行大量任务导致资源耗尽 |

### 1.2 Safety gate 的核心原则

```text
1. Fail-closed — 任何不确定情况一律拒绝推进
2. 每轮独立校验 — 每次推进前必须重新校验全部条件
3. 不信任缓存 — 每轮必须重读 tasks.md 和 workspace 状态
4. 失败即停止 — 任何条件不满足立即停止，不跳过
5. 可审查可追溯 — 每次推进决策都有完整的 gate check 记录
```

### 1.3 设计范围

T143 只设计 safety gate，不实现代码。

T143 不涉及：
- 连续任务的具体执行逻辑（T144/T146）
- pass/fail 场景的验证（T145/T147）
- 成果归档（T148）

---

## 2. Gate 输入

Safety gate 需要以下输入字段来做出推进决策。

### 2.1 运行级别输入

| # | 字段 | 类型 | 来源 | 说明 |
|---|------|------|------|------|
| 1 | `stage` | string | 当前运行配置 | 当前阶段，必须为 `Stage 8` |
| 2 | `run_id` | string | checkpoint | 当前连续运行标识 |
| 3 | `max_tasks` | int | 用户输入 | 单次运行最大任务数，范围 [1, 10] |
| 4 | `tasks_attempted` | int | checkpoint | 已尝试的任务数 |
| 5 | `tasks_completed` | int | checkpoint | 已完成的任务数 |

### 2.2 当前任务输入

| # | 字段 | 类型 | 来源 | 说明 |
|---|------|------|------|------|
| 6 | `current_task_id` | string | tasks.md | 当前已完成或正在处理的任务编号 |
| 7 | `current_task_status` | string | tasks.md | 当前任务状态 |
| 8 | `current_task_stage` | string | tasks.md | 当前任务所属阶段 |
| 9 | `validation_status` | string | validation report | 当前任务验证结果：pass / fail / unknown |
| 10 | `approval_record_status` | string | approval record 文件 | 当前任务 approval record 是否存在且完整 |
| 11 | `approval_record_path` | string | approval record 文件 | approval record 文件路径 |
| 12 | `report_status` | string | report 文件 | 当前任务报告是否存在 |
| 13 | `report_path` | string | report 文件 | 报告文件路径 |
| 14 | `commit_dry_run_status` | string | commit dry-run 结果 | 当前任务 git commit dry-run 是否通过 |
| 15 | `git_backup_status` | string | git backup 结果 | 当前任务 git backup 是否完成 |
| 16 | `rework_required` | bool | 验证结果 | 当前任务是否需要返工 |

### 2.3 下一任务输入

| # | 字段 | 类型 | 来源 | 说明 |
|---|------|------|------|------|
| 17 | `next_pending_task_id` | string | tasks.md | 下一个 pending 任务编号 |
| 18 | `next_pending_task_stage` | string | tasks.md | 下一个任务所属阶段 |

### 2.4 工作区输入

| # | 字段 | 类型 | 来源 | 说明 |
|---|------|------|------|------|
| 19 | `workspace_status` | string | git status --short | 工作区状态：clean / dirty |
| 20 | `staged_files` | list | git diff --cached | 暂存区文件列表 |
| 21 | `current_branch` | string | git branch --show-current | 当前分支 |
| 22 | `last_commit` | string | git log --oneline -1 | 最近提交 |

### 2.5 安全标志输入

| # | 字段 | 类型 | 来源 | 说明 |
|---|------|------|------|------|
| 23 | `push_allowed` | bool | 安全配置 | 是否允许 push，必须为 false |
| 24 | `real_execution_allowed` | bool | 安全配置 | 是否允许真实执行 |
| 25 | `stage_boundary_check` | string | stage 校验 | 当前是否在 Stage 8 边界内 |
| 26 | `rate_limit_status` | string | 运行状态 | 是否触发速率限制 |
| 27 | `manual_stop_requested` | bool | 用户信号 | 是否有手动停止请求 |

### 2.6 Checkpoint 输入

| # | 字段 | 类型 | 来源 | 说明 |
|---|------|------|------|------|
| 28 | `checkpoint_exists` | bool | checkpoint 文件 | 是否存在当前运行的 checkpoint |
| 29 | `checkpoint_path` | string | checkpoint 文件 | checkpoint 文件路径 |
| 30 | `checkpoint_consistent` | bool | checkpoint 校验 | checkpoint 内容是否与当前状态一致 |

---

## 3. Gate 输出

Safety gate 在完成所有检查后输出以下结构。

### 3.1 输出字段

| # | 字段 | 类型 | 说明 |
|---|------|------|------|
| 1 | `allowed` | bool | 是否允许推进到下一个任务 |
| 2 | `decision` | string | 决策类型：`advance` / `stop` / `blocked` |
| 3 | `stop_reason` | string | 如果不允许推进，停止原因 |
| 4 | `next_task_id` | string | 如果允许推进，下一个任务编号 |
| 5 | `stage` | string | 当前阶段 |
| 6 | `max_tasks_remaining` | int | 剩余可执行任务数 |
| 7 | `required_actions` | list | 如果 blocked，需要执行的动作列表 |
| 8 | `failure_reasons` | list | 如果 blocked，所有不通过的原因列表 |
| 9 | `checkpoint_required` | bool | 是否需要生成 checkpoint |
| 10 | `approval_record_required` | bool | 是否需要生成 approval record |
| 11 | `git_backup_required` | bool | 是否需要执行 git backup |
| 12 | `manual_review_required` | bool | 是否需要人工审查 |
| 13 | `notes` | string | 补充说明 |

### 3.2 输出结构示例

#### 允许推进（advance）

```yaml
allowed: true
decision: advance
stop_reason: null
next_task_id: T145
stage: Stage 8
max_tasks_remaining: 1
required_actions: []
failure_reasons: []
checkpoint_required: true
approval_record_required: true
git_backup_required: true
manual_review_required: false
notes: "All gate checks passed. Workspace clean. Approval record exists. Ready for next task."
```

#### 正常停止（stop）

```yaml
allowed: false
decision: stop
stop_reason: completed_max_tasks
next_task_id: null
stage: Stage 8
max_tasks_remaining: 0
required_actions:
  - "Review run summary"
  - "If more tasks needed, start a new run"
failure_reasons: []
checkpoint_required: true
approval_record_required: false
git_backup_required: false
manual_review_required: false
notes: "Reached max_tasks limit. All attempted tasks completed successfully."
```

#### 阻塞停止（blocked）

```yaml
allowed: false
decision: blocked
stop_reason: blocked_by_dirty_workspace
next_task_id: null
stage: Stage 8
max_tasks_remaining: 2
required_actions:
  - "Review dirty workspace files"
  - "Commit or revert changes"
  - "Restart run after workspace is clean"
failure_reasons:
  - "Workspace is dirty: 2 uncommitted files"
  - "File reports/dev/T144-dev-report.md not in expected scope"
checkpoint_required: true
approval_record_required: false
git_backup_required: false
manual_review_required: true
notes: "Workspace dirty after task completion. Manual review required."
```

---

## 4. 必须通过的条件（Gate Pass 条件）

Safety gate 允许推进（`allowed=true`）时，以下所有条件必须同时满足。

### 4.1 阶段边界条件

| # | 条件 | 检查方式 | 失败归类 |
|---|------|----------|----------|
| G1 | `stage` 必须为 `Stage 8` | 校验 stage 字段 | blocked_by_stage_boundary |
| G2 | `next_pending_task_stage` 必须为 `Stage 8` | 读取 tasks.md 校验 | blocked_by_stage_boundary |
| G3 | 不允许跨入 Stage 9 或更高阶段 | 校验 next task stage | blocked_by_stage_boundary |

### 4.2 任务计数条件

| # | 条件 | 检查方式 | 失败归类 |
|---|------|----------|----------|
| G4 | `max_tasks` 必须存在且为正整数 | 校验 max_tasks 字段 | blocked_by_unknown_error |
| G5 | `max_tasks` 必须 ≤ 10 | 校验 max_tasks 上限 | blocked_by_unknown_error |
| G6 | `tasks_attempted` < `max_tasks` | 比较 tasks_attempted 与 max_tasks | completed_max_tasks |
| G7 | `next_pending_task_id` 必须存在 | 检查是否有 pending 任务 | no_pending_tasks |

### 4.3 工作区条件

| # | 条件 | 检查方式 | 失败归类 |
|---|------|----------|----------|
| G8 | `workspace_status` 必须为 `clean` | git status --short | blocked_by_dirty_workspace |
| G9 | `staged_files` 必须为空 | git diff --cached --name-only | blocked_by_staged_changes |
| G10 | `current_branch` 必须明确且安全 | git branch --show-current | blocked_by_git_safety_gate |
| G11 | `last_commit` 必须已记录 | git log --oneline -1 | blocked_by_git_safety_gate |

### 4.4 当前任务完成条件

| # | 条件 | 检查方式 | 失败归类 |
|---|------|----------|----------|
| G12 | `validation_status` 必须为 `pass` | 检查 validation report | blocked_by_validation_failure |
| G13 | `approval_record_status` 必须为 `exists` | 检查 approval record 文件 | blocked_by_missing_approval_record |
| G14 | `report_status` 必须为 `exists` | 检查 report 文件 | blocked_by_missing_report |
| G15 | `rework_required` 必须为 `false` | 检查验证结果 | blocked_by_rework_required |

### 4.5 安全标志条件

| # | 条件 | 检查方式 | 失败归类 |
|---|------|----------|----------|
| G16 | `push_allowed` 必须为 `false` | 校验安全标志 | blocked_by_git_safety_gate |
| G17 | `real_execution_allowed` 必须为 `false` 或处于明确受控 dry-run 状态 | 校验安全标志 | blocked_by_git_safety_gate |
| G18 | `rate_limit_status` 必须为 `clear` | 校验运行状态 | blocked_by_rate_limit |
| G19 | `manual_stop_requested` 必须为 `false` | 校验用户信号 | manual_stop_required |

### 4.6 Checkpoint 条件

| # | 条件 | 检查方式 | 失败归类 |
|---|------|----------|----------|
| G20 | `checkpoint_exists` 必须为 `true` | 检查 checkpoint 文件 | blocked_by_unknown_error |
| G21 | `checkpoint_consistent` 必须为 `true` | 校验 checkpoint 内容 | blocked_by_unknown_error |

### 4.7 Gate Check 总结

```text
总计 21 项 gate check (G1-G21)

全部通过 → allowed=true, decision=advance
任一失败 → allowed=false, decision=stop/blocked

不存在部分通过。
```

---

## 5. 必须拒绝的条件（Gate Fail 条件）

以下任一条件触发时，gate 必须拒绝推进。

### 5.1 工作区异常

| # | 触发条件 | stop_reason | 对应 Gate |
|---|----------|-------------|-----------|
| 1 | `workspace_status` = `dirty` | blocked_by_dirty_workspace | G8 |
| 2 | `staged_files` 不为空 | blocked_by_staged_changes | G9 |
| 3 | `current_branch` 未知或不安全 | blocked_by_git_safety_gate | G10 |
| 4 | `last_commit` 未记录 | blocked_by_git_safety_gate | G11 |

### 5.2 当前任务未通过

| # | 触发条件 | stop_reason | 对应 Gate |
|---|----------|-------------|-----------|
| 5 | `validation_status` = `fail` | blocked_by_validation_failure | G12 |
| 6 | `approval_record_status` = `missing` | blocked_by_missing_approval_record | G13 |
| 7 | `report_status` = `missing` | blocked_by_missing_report | G14 |
| 8 | `rework_required` = `true` | blocked_by_rework_required | G15 |

### 5.3 阶段越权

| # | 触发条件 | stop_reason | 对应 Gate |
|---|----------|-------------|-----------|
| 9 | `next_pending_task_stage` 不属于 Stage 8 | blocked_by_stage_boundary | G2 |
| 10 | 尝试进入 Stage 9 或更高 | blocked_by_stage_boundary | G3 |

### 5.4 计数越界

| # | 触发条件 | stop_reason | 对应 Gate |
|---|----------|-------------|-----------|
| 11 | `max_tasks` 缺失 | blocked_by_unknown_error | G4 |
| 12 | `max_tasks` > 10 | blocked_by_unknown_error | G5 |
| 13 | `tasks_attempted` ≥ `max_tasks` | completed_max_tasks | G6 |
| 14 | 无 pending 任务 | no_pending_tasks | G7 |

### 5.5 安全标志异常

| # | 触发条件 | stop_reason | 对应 Gate |
|---|----------|-------------|-----------|
| 15 | `push_allowed` = `true` | blocked_by_git_safety_gate | G16 |
| 16 | `real_execution_allowed` = `true` 且没有明确审批 gate | blocked_by_git_safety_gate | G17 |
| 17 | `rate_limit_status` = `triggered` | blocked_by_rate_limit | G18 |
| 18 | `manual_stop_requested` = `true` | manual_stop_required | G19 |

### 5.6 Checkpoint 异常

| # | 触发条件 | stop_reason | 对应 Gate |
|---|----------|-------------|-----------|
| 19 | `checkpoint_exists` = `false` | blocked_by_unknown_error | G20 |
| 20 | `checkpoint_consistent` = `false` | blocked_by_unknown_error | G21 |

### 5.7 拒绝原则

```text
1. 所有拒绝均为 fail-closed — 不存在 "部分拒绝"
2. 拒绝后必须保留现场 — 不自动清理、不自动回滚
3. 拒绝后必须记录 stop_reason — 不允许无原因停止
4. 拒绝后必须输出 required_actions — 不允许只报错不给建议
5. 拒绝后不允许继续推进 — 必须等待人工介入或修复后重新 gate
```

---

## 6. stop_reason 设计

### 6.1 stop_reason 完整列表

#### 正常停止

| # | stop_reason | 触发条件 | resume 允许 | 后续建议 |
|---|-------------|----------|-------------|----------|
| 1 | `completed_max_tasks` | `tasks_attempted` ≥ `max_tasks`，且所有任务都通过 | 否（需新开 run） | 审查 run summary，如需继续可新开一轮 |

| # | stop_reason | 触发条件 | resume 允许 | 后续建议 |
|---|-------------|----------|-------------|----------|
| 2 | `no_pending_tasks` | 没有状态为 pending 的任务 | 否（需新开 run） | 检查是否需要新增任务或归档当前 Stage |

#### 异常停止

| # | stop_reason | 触发条件 | resume 允许 | 后续建议 |
|---|-------------|----------|-------------|----------|
| 3 | `blocked_by_dirty_workspace` | `git status --short` 有输出 | 否 | 检查 dirty 文件，提交或回滚后再重新运行 |
| 4 | `blocked_by_staged_changes` | `git diff --cached` 有文件 | 否 | 检查 staged 文件，确认是否为当前任务预期 |
| 5 | `blocked_by_validation_failure` | 当前任务 validation = fail | 否 | 查看 validation report，修复后重新运行 |
| 6 | `blocked_by_rework_required` | rework_required = true | 否 | 查看 rework 原因，执行返工后重新运行 |
| 7 | `blocked_by_unapproved_changes` | 检测到未审批变更 | 否 | 检查变更内容，审批或拒绝后继续 |
| 8 | `blocked_by_stage_boundary` | next task 不属于 Stage 8 | 否 | 确认是否需要跨 Stage，需单独授权 |
| 9 | `blocked_by_missing_approval_record` | approval record 不存在 | 否 | 生成缺失的 approval record 后重新运行 |
| 10 | `blocked_by_missing_report` | 任务报告不存在 | 否 | 生成缺失的报告后重新运行 |
| 11 | `blocked_by_git_safety_gate` | push_allowed=true 或分支不安全 | 否 | 查看 gate 拒绝原因，修复后重新运行 |
| 12 | `blocked_by_rate_limit` | 速率限制触发 | 否 | 等待冷却后重新运行 |
| 13 | `manual_stop_required` | 用户请求停止 | 否 | 人工确认后可新开一轮 |
| 14 | `blocked_by_unknown_error` | 未分类错误 | 否 | 查看错误日志，人工介入分析 |

### 6.2 resume_allowed 设计

```text
resume_allowed 默认值：false

所有 stop_reason 的 resume_allowed 均为 false。

原因：
1. 当前 Stage 8 不实现 checkpoint 自动 resume
2. 任何停止都需要人工审查后才继续
3. rate-limit recovery 和 checkpoint resume 预留给后续专题
4. 继续运行应通过新开一轮实现，而不是自动恢复

rate-limit recovery / checkpoint resume：
- 仅保留后续设计入口
- 本任务不实现
- 不在 gate 中预留自动 resume 逻辑
```

---

## 7. Checkpoint 要求

### 7.1 Safety gate 与 checkpoint 的交互

```text
Gate 判断前：
  1. 读取当前 checkpoint
  2. 校验 checkpoint 中的 run_id 与当前 run_id 一致
  3. 校验 checkpoint 中的 stage 为 Stage 8
  4. 校验 checkpoint 内容与实际状态一致

Gate 判断后：
  1. 将 gate 判断结果写入 checkpoint
  2. 更新 checkpoint 中的 current_task / next_pending_task
  3. 更新 checkpoint 中的 workspace_status_after
  4. 记录 stop_reason（如果停止）
  5. 记录 approval_records 和 reports_generated
```

### 7.2 Checkpoint 必须包含的字段

```yaml
checkpoint_version: "1.0"
run_id: "stage8-run-001"
stage: "Stage 8"
mode: "continuous_real_task_auto_advance"

timing:
  started_at: "2026-05-09T14:00:00"
  ended_at: null
  last_checkpoint_at: "2026-05-09T14:10:00"

limits:
  max_tasks: 2
  tasks_attempted: 1
  tasks_completed: 1

current_state:
  current_task: "T144"
  last_completed_task: "T144"
  next_pending_task: "T145"
  stop_reason: null

workspace:
  status_before: "clean"
  status_after: "clean"

records:
  approval_records:
    - "reports/approval/t144-stage8-approval.md"
  reports_generated:
    - "reports/dev/T144-dev-report.md"
  commits_created:
    - "abc1234 feat: implement T144 ..."
  pushes_created: []  # 始终为空

gate_result:
  allowed: true
  decision: advance
  gate_checks_passed: 21
  gate_checks_failed: 0
  failure_reasons: []

errors: []

resume:
  resume_allowed: false

notes: |
  Checkpoint after gate passed for T144→T145.
  All 21 gate checks passed.
```

### 7.3 Checkpoint 关键约束

| # | 约束 | 说明 |
|---|------|------|
| 1 | 不得覆盖未归档状态 | checkpoint 写入前必须确认前一个 checkpoint 已被处理 |
| 2 | 必须记录 stop_reason | 停止时 stop_reason 不得为空 |
| 3 | 必须记录当前和下一个任务 | current_task 和 next_pending_task 不得同时为空 |
| 4 | 必须记录 workspace 状态 | status_before 和 status_after 都必须有值 |
| 5 | 必须记录 approval_records 路径 | 所有已生成的 approval record 都要记录 |
| 6 | 必须记录 reports 路径 | 所有已生成的 report 都要记录 |
| 7 | resume_allowed 默认 false | 不允许自动修改为 true |
| 8 | pushes_created 始终为空 | Stage 8 不允许 push |

### 7.4 Checkpoint 文件路径

```text
reports/checkpoints/stage8-run-{run_id}-checkpoint.md
```

---

## 8. 与 Stage 7 gate 的关系

T143 safety gate 在 Stage 7 安全链路之上运行，不复用也不替代 Stage 7 的任何 gate，而是增加一层**任务间推进控制**。

### 8.1 复用的 Stage 7 安全原则

| # | Stage 7 安全原则 | Stage 8 复用方式 |
|---|------------------|-----------------|
| 1 | fail-closed 原则 | T143 gate 默认拒绝，全部条件通过才允许 |
| 2 | no-tool-use fallback | 每个 Stage 8 任务仍可使用 no-tool-use 方式执行 |
| 3 | allowed scope validator | 每个 Stage 8 任务仍需通过文件范围校验 |
| 4 | human-reviewed controlled apply gate | 每个 Stage 8 任务仍需通过审批 gate |
| 5 | real patch apply dry-run | 每个 Stage 8 任务仍需通过 patch apply 守卫 |
| 6 | guarded Git backup dry-run | 每个 Stage 8 任务仍需通过 Git 备份守卫 |
| 7 | real Git add/commit dry-run approval record | 每个 Stage 8 任务仍需生成 approval record |
| 8 | command allowlist | 每个 Stage 8 任务仍需通过命令白名单 |
| 9 | pass/fail validation | 每个 Stage 8 任务仍需独立验证 |
| 10 | archive-first principle | Stage 8 成果也遵循先归档后推进 |

### 8.2 Stage 7 gate 与 Stage 8 gate 的层次关系

```text
Stage 7 gate — 单任务内的安全控制（任务执行过程中）
  ├── proposal parser dry-run
  ├── allowed scope validator
  ├── controlled apply gate
  ├── real patch apply dry-run
  ├── guarded Git backup dry-run
  └── real Git add/commit dry-run

Stage 8 gate — 任务间的推进控制（任务与任务之间）
  ├── workspace isolation check
  ├── max_tasks limit check
  ├── stage boundary check
  ├── approval record completeness check
  ├── report completeness check
  ├── checkpoint consistency check
  ├── safety flags check
  └── stop reason management

执行顺序：
  Stage 7 gate → 任务执行 → Stage 7 gate → Stage 8 gate → 下一个任务

不允许：
  - 绕过 Stage 7 gate 直接进入 Stage 8 gate
  - 绕过 Stage 8 gate 直接推进下一个任务
  - 修改 Stage 7 gate 的安全逻辑
  - 在 Stage 7 gate 上开例外
```

### 8.3 不替代不绕过

```text
T143 safety gate 不替代以下 Stage 7 能力：
  - 不替代单任务内的 gate check
  - 不替代 approval record 生成
  - 不替代 validation 执行
  - 不替代 report 生成

T143 safety gate 不绕过以下 Stage 7 约束：
  - 不绕过 push_allowed=false
  - 不绕过 real_execution_allowed 约束
  - 不绕过 sensitive file protection
  - 不绕过 command allowlist
```

---

## 9. 与后续任务关系

### 9.1 任务链

| 任务 | 角色 | 内容 | 与 T143 的关系 |
|------|------|------|---------------|
| T143 | Designer | 设计 Stage 8 continuous real task runner safety gate | 当前任务 |
| T144 | Developer | 实现 Stage 8 continuous runner dry-run planner | 基于 T143 gate 设计实现 dry-run planner |
| T145 | Validator | 验证 Stage 8 continuous runner dry-run pass/fail 场景 | 验证 T144 是否正确实现 T143 gate |
| T146 | Developer | 实现 real single-step continuous advance dry-run | 基于 T143 gate 和 T144 planner 实现单步推进 |
| T147 | Validator | 验证 real single-step continuous advance dry-run pass/fail 场景 | 验证 T146 是否正确实现单步推进 |
| T148 | Archiver | 归档 Stage 8 planning / dry-run 成果 | 归档 T143-T147 全部成果 |

### 9.2 T143 对 T144 的设计约束

T143 为 T144 提供以下约束：

```text
1. T144 必须实现 T143 定义的 21 项 gate check (G1-G21)
2. T144 必须生成 T143 定义的 gate 输出结构
3. T144 必须遵循 T143 定义的 fail-closed 原则
4. T144 必须实现 T143 定义的 checkpoint 读写要求
5. T144 仍然不允许：
   - 真实连续任务执行
   - 真实 git add / commit / push
   - 自动跨入 Stage 9
   - 修改业务代码
```

### 9.3 T143 对 T146 的设计约束

T143 为 T146 提供以下约束：

```text
1. T146 的 single-step advance 必须通过 T143 的全部 gate check
2. T146 每次推进都必须生成 gate 输出记录
3. T146 的 stop_reason 必须从 T143 定义的 14 种中选择
4. T146 不允许绕过任何 gate check
```

---

## 10. Pass / fail 场景设计

### 10.1 Pass 场景

#### P1：max_tasks=1，工作区 clean，允许推进 1 个任务

```yaml
场景描述：max_tasks=1，工作区 clean，next task 属于 Stage 8
输入：
  stage: Stage 8
  max_tasks: 1
  tasks_attempted: 0
  tasks_completed: 0
  workspace_status: clean
  staged_files: []
  validation_status: pass  # 首次启动时前一个任务已完成
  approval_record_status: exists
  report_status: exists
  next_pending_task_id: T144
  next_pending_task_stage: Stage 8
  push_allowed: false
  real_execution_allowed: false
  rework_required: false
  rate_limit_status: clear
  manual_stop_requested: false
  checkpoint_exists: true
  checkpoint_consistent: true
预期输出：
  allowed: true
  decision: advance
  next_task_id: T144
  max_tasks_remaining: 1
  gate_checks_passed: 21
  gate_checks_failed: 0
```

#### P2：max_tasks=2，完成第一个任务后重新 gate，再允许第二个任务

```yaml
场景描述：max_tasks=2，已完成 1 个任务，重新 gate 检查后允许推进第二个
输入：
  stage: Stage 8
  max_tasks: 2
  tasks_attempted: 1
  tasks_completed: 1
  workspace_status: clean
  staged_files: []
  current_task_id: T144
  validation_status: pass
  approval_record_status: exists
  report_status: exists
  next_pending_task_id: T145
  next_pending_task_stage: Stage 8
  push_allowed: false
  rework_required: false
  checkpoint_exists: true
预期输出：
  allowed: true
  decision: advance
  next_task_id: T145
  max_tasks_remaining: 1
```

#### P3：no pending task 时安全停止

```yaml
场景描述：所有任务已完成，没有 pending 任务
输入：
  stage: Stage 8
  max_tasks: 3
  tasks_attempted: 2
  tasks_completed: 2
  next_pending_task_id: null
预期输出：
  allowed: false
  decision: stop
  stop_reason: no_pending_tasks
```

#### P4：当前任务完成且报告、approval record、checkpoint 都存在

```yaml
场景描述：完整的通过场景，所有文档齐全
输入：
  stage: Stage 8
  validation_status: pass
  approval_record_status: exists
  approval_record_path: reports/approval/t144-stage8-approval.md
  report_status: exists
  report_path: reports/dev/T144-dev-report.md
  checkpoint_exists: true
  checkpoint_path: reports/checkpoints/stage8-run-001-checkpoint.md
预期输出：
  allowed: true
  decision: advance
  gate_checks_passed: 21
```

#### P5：push_allowed=false 时正常通过

```yaml
场景描述：push_allowed 为 false，不影响 gate 通过
输入：
  push_allowed: false
  其他条件全部满足
预期输出：
  allowed: true
  decision: advance
```

### 10.2 Fail 场景

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

#### F2：staged files 不为空

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

#### F3：validation fail

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

#### F4：missing approval record

```yaml
场景描述：缺少 approval record
输入：
  approval_record_status: missing
预期输出：
  allowed: false
  decision: blocked
  stop_reason: blocked_by_missing_approval_record
  failure_reasons: ["Approval record not found for current task"]
```

#### F5：missing report

```yaml
场景描述：缺少任务报告
输入：
  report_status: missing
预期输出：
  allowed: false
  decision: blocked
  stop_reason: blocked_by_missing_report
  failure_reasons: ["Report not found for current task"]
```

#### F6：next task 属于 Stage 9

```yaml
场景描述：下一个 pending 任务属于 Stage 9
输入：
  next_pending_task_id: T149
  next_pending_task_stage: Stage 9
预期输出：
  allowed: false
  decision: blocked
  stop_reason: blocked_by_stage_boundary
  failure_reasons: ["Next task T149 belongs to Stage 9, not Stage 8"]
```

#### F7：max_tasks 缺失

```yaml
场景描述：max_tasks 未设置
输入：
  max_tasks: null
预期输出：
  allowed: false
  decision: blocked
  stop_reason: blocked_by_unknown_error
  failure_reasons: ["max_tasks is required"]
```

#### F8：max_tasks 超过上限

```yaml
场景描述：max_tasks > 10
输入：
  max_tasks: 15
预期输出：
  allowed: false
  decision: blocked
  stop_reason: blocked_by_unknown_error
  failure_reasons: ["max_tasks exceeds absolute limit 10"]
```

#### F9：rework_required

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

#### F10：manual_stop_requested

```yaml
场景描述：用户请求手动停止
输入：
  manual_stop_requested: true
预期输出：
  allowed: false
  decision: blocked
  stop_reason: manual_stop_required
  failure_reasons: ["Manual stop requested"]
```

#### F11：rate_limit

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

#### F12：push_allowed=true

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

#### F13：real_execution_allowed=true 但没有明确审批

```yaml
场景描述：real_execution_allowed 被设置为 true 但没有审批
输入：
  real_execution_allowed: true
预期输出：
  allowed: false
  decision: blocked
  stop_reason: blocked_by_git_safety_gate
  failure_reasons: ["real_execution_allowed=true requires explicit gate authorization"]
```

#### F14：unknown error

```yaml
场景描述：发生未分类错误
输入：
  checkpoint_exists: false
  checkpoint_consistent: false
预期输出：
  allowed: false
  decision: blocked
  stop_reason: blocked_by_unknown_error
  failure_reasons: ["Checkpoint missing or inconsistent"]
```

### 10.3 场景统计

```text
Pass 场景：5 个 (P1-P5)
Fail 场景：14 个 (F1-F14)
总计：19 个场景

验证原则：
  1. 所有 pass 场景必须返回 allowed=true
  2. 所有 fail 场景必须返回 allowed=false
  3. 所有 fail 场景必须有明确的 stop_reason
  4. 所有 fail 场景必须有 failure_reasons
  5. 不存在 "部分通过" 的中间状态
```

---

## 11. 后续建议

```text
NEXT_PENDING=T144
NEXT_STAGE=Stage 8
```

T144 应实现 Stage 8 continuous runner dry-run planner，具体应包括：

1. 实现 T143 定义的 21 项 gate check (G1-G21)
2. 实现 gate 输入采集和输出生成
3. 实现 checkpoint 读写
4. 实现 run summary 生成
5. 实现 dry-run planner CLI 入口

T144 仍然不允许：
- 真实连续任务执行
- 真实 git add / commit / push
- 自动跨入 Stage 9
- 修改业务代码
- 绕过任何 gate check

---

## 设计元数据

- 设计角色：Designer / Architecture Agent
- 设计日期：2026-05-09
- 设计基准提交：daffd7f docs: add stage 8 continuous real task auto advance plan
- 前置条件：STAGE7_COMPLETE=yes, STAGE8_PLAN_COMPLETE=yes
- 设计结论：T143_SAFETY_GATE_DESIGN_COMPLETE=yes
