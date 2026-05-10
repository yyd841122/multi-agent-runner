# Stage 8 Real Controlled Continuous Execution Plan

设计时间：2026-05-10
阶段：Stage 8 — 真实连续任务自动推进（后半段）
任务角色：Planner / Architecture Agent
前置条件：Stage 8 planning/dry-run 链路完成（T143-T148），dry-run 全场景验证通过

---

## 1. 目标定义

### 1.1 Stage 8 后半段目标

Stage 8 后半段的目标是**真实受控连续任务推进**。

即在 Stage 8 前半段（T143-T148）已完成的 safety gate、dry-run planner、single-step advance dry-run 全链路基础之上，逐步引入**真实受控执行**能力，实现从 dry-run 到真实受控推进的渐进过渡。

### 1.2 真实受控推进应做到

| # | 能力 | 说明 |
|---|------|------|
| 1 | safety gate 通过后可以真实推进一个 task step | 每次只允许一个受控 step |
| 2 | 每个 step 后必须重新检查状态 | 不允许跳过状态检查 |
| 3 | 允许通过 max_tasks 控制执行 1～2 个任务 | 当前上限暂定为 2 |
| 4 | 遇到任何异常立即停止 | 失败即停止 |
| 5 | 不允许无人值守无限循环 | 有 max_tasks 硬性上限 |
| 6 | 每个真实 step 都有完整的审计追踪 | approval record + checkpoint + report |

### 1.3 真实受控推进不是

| # | 不是什么 | 说明 |
|---|----------|------|
| 1 | 不是直接全自动无限执行 | max_tasks 有上限，每步需要 gate |
| 2 | 不是直接进入 Stage 9 | Stage 8 不自动跨入 Stage 9 |
| 3 | 不是直接自动 push | push 始终禁止 |
| 4 | 不是绕过人类确认 | 每个真实 step 都需要 approval record |
| 5 | 不是绕过 Git 安全门 | 所有 Git 操作必须通过 gate |
| 6 | 不是一次放开所有权限 | 分层渐进，每层只增加最小必要权限 |

---

## 2. 与现有 dry-run 链路的关系

### 2.1 必须复用的前半段成果

| # | 成果 | 来源 | 复用方式 |
|---|------|------|----------|
| 1 | Stage 8 planning 文档 | Stage 8 planning | 作为总体设计基础 |
| 2 | 21 项 gate check (G1-G21) | T143 | 作为真实执行的 gate 基础 |
| 3 | Safety gate 评估函数 | T144 | `evaluate_stage8_continuous_runner_safety_gate()` |
| 4 | Continuous runner dry-run planner | T144 | 作为真实执行的 dry-run 验证层 |
| 5 | 14 种 stop_reason | T144 | 作为真实执行的停止原因分类 |
| 6 | Checkpoint 生成 | T144/T146 | 作为真实执行的检查点模板 |
| 7 | Single-step advance dry-run | T146 | 作为真实单步推进的 dry-run 验证层 |
| 8 | Next pending task selection | T146 | 作为真实执行的任务选取逻辑 |
| 9 | Pass / safe stop / fail 验证 | T145/T147 | 32 个场景全部验证通过，作为安全基线 |
| 10 | Fail-closed 保证 | T143-T147 | 所有不确定情况一律拒绝 |
| 11 | 归档文档 | T148 | 作为 Stage 8 前半段完整记录 |

### 2.2 真实受控推进的增量能力

| # | 增量能力 | 说明 | 所属 Layer |
|---|----------|------|-----------|
| 1 | Execution gate 设计 | 专门用于真实执行的 gate check | Layer 1 |
| 2 | Real controlled execution dry-run | 真实执行的 dry-run 模拟 | Layer 2 |
| 3 | max_tasks=1 真实受控试运行 | 单任务真实执行 | Layer 3 |
| 4 | max_tasks=2 真实受控连续推进 | 两任务连续真实执行 | Layer 4 |

### 2.3 不修改前半段成果

```text
真实受控推进不允许：
  - 修改 T144 的 gate check 逻辑
  - 修改 T146 的 single-step advance 逻辑
  - 修改 T145/T147 的验证标准
  - 绕过 T143 的任何 gate check
  - 覆写 T148 的归档记录
```

---

## 3. 真实受控推进的边界

### 3.1 核心边界

| # | 边界规则 | 说明 |
|---|----------|------|
| 1 | 默认 max_tasks=1 | 真实受控试运行默认只执行 1 个任务 |
| 2 | 最大上限暂定 max_tasks<=2 | 当前阶段不允许超过 2 |
| 3 | 每轮只能选择一个 next pending task | 不允许并行推进 |
| 4 | 每轮必须先通过 safety gate | 复用 G1-G21 全部检查 |
| 5 | 每轮必须生成 approval record | 真实 step 必须有审批记录 |
| 6 | 每轮必须生成 checkpoint | 真实 step 必须有检查点 |
| 7 | 每轮必须生成 report | 真实 step 必须有执行报告 |
| 8 | 每轮结束后必须检查 workspace | dirty workspace 不能进入下一轮 |
| 9 | dirty workspace 不能进入下一轮 | 必须先处理 dirty 内容 |
| 10 | validation fail 必须停止 | 失败即停止 |
| 11 | rework required 必须停止 | 需要返工即停止 |
| 12 | missing approval record 必须停止 | 缺少审批即停止 |
| 13 | stage boundary 必须停止 | 跨 Stage 即停止 |
| 14 | Stage 8 不允许进入 Stage 9 | 不自动跨入 |
| 15 | 不允许自动 push | push 始终禁止 |
| 16 | 不允许自动提交未审批文件 | 只允许通过文件白名单 |

### 3.2 max_tasks 递进策略

```text
Layer 1 (planning):
  max_tasks: N/A (只做设计)

Layer 2 (dry-run):
  max_tasks: 1-2 (dry-run 模拟)

Layer 3 (real trial):
  max_tasks: 1 (真实试运行，只允许 1 个任务)

Layer 4 (real continuous):
  max_tasks: 2 (真实连续推进，允许 2 个任务)

注意：前半段 T143 原始设计 max_tasks 绝对上限为 10，
但真实受控推进阶段暂定 max_tasks<=2，
等 Layer 4 验证通过后再考虑逐步放开上限。
```

---

## 4. 真实执行分层

### Layer 1：real controlled single-step execution planning

| 属性 | 内容 |
|------|------|
| **目标** | 设计真实受控执行的 execution gate，定义真实执行所需的安全检查 |
| **输入** | T143 safety gate 设计、T144/T146 dry-run 实现代码、T145/T147 验证报告 |
| **输出** | Execution gate 设计文档，包含新增 gate check、approval record schema、checkpoint schema |
| **安全 gate** | 复用 G1-G21 + 新增 execution gate check (E1-En) |
| **停止条件** | 设计完成即停止，不执行任何真实操作 |
| **允许** | 阅读已有代码、编写设计文档、更新 tasks.md |
| **禁止** | 实现代码、执行真实任务、git add/commit/push、进入 Stage 9 |

### Layer 2：real controlled single-step execution dry-run

| 属性 | 内容 |
|------|------|
| **目标** | 在 dry-run 模式下模拟真实受控执行全流程，验证 execution gate 和 approval record |
| **输入** | Layer 1 的 execution gate 设计、T144/T146 已有 dry-run 基础 |
| **输出** | Dry-run 实现代码、sample scenarios（pass + fail）、dry-run checkpoint/report |
| **安全 gate** | G1-G21 + E1-En 全部 gate check |
| **停止条件** | Dry-run 全场景验证通过 |
| **允许** | 实现 dry-run 代码、运行 dry-run sample scenarios、生成 dry-run checkpoint/report |
| **禁止** | 执行真实任务、真实 git add/commit/push、进入 Stage 9、设置 real_execution_allowed=true |

### Layer 3：max_tasks=1 real controlled single-step execution trial

| 属性 | 内容 |
|------|------|
| **目标** | 在 max_tasks=1 条件下，执行一次真实受控单步推进试运行 |
| **输入** | Layer 2 dry-run 验证通过的代码、真实的 next pending task |
| **输出** | 真实执行结果、approval record、checkpoint、execution report |
| **安全 gate** | G1-G21 + E1-En + 真实执行审批 gate |
| **停止条件** | 执行完 1 个任务即停止，或任何 gate 未通过即停止 |
| **允许** | 真实执行 1 个任务、受控 git add（仅白名单文件）、受控 git commit（需 approval） |
| **禁止** | 执行超过 1 个任务、git push、自动进入下一任务、进入 Stage 9、git add . / git add -A |

### Layer 4：max_tasks=2 real controlled continuous execution trial

| 属性 | 内容 |
|------|------|
| **目标** | 在 max_tasks=2 条件下，执行最多 2 个真实受控连续推进 |
| **输入** | Layer 3 验证通过的代码、真实的 next pending tasks |
| **输出** | 连续执行结果、每任务 approval record、每任务 checkpoint、run summary |
| **安全 gate** | G1-G21 + E1-En + 每任务重新 gate |
| **停止条件** | 完成 2 个任务即停止，或任何 gate 未通过即停止 |
| **允许** | 真实执行最多 2 个任务、每任务间重新 gate、受控 git add/commit |
| **禁止** | 执行超过 2 个任务、git push、绕过中间 gate、进入 Stage 9、git add . / git add -A |

---

## 5. Safety Gate 要求

### 5.1 真实受控执行前的必须条件

在复用 T143 的 G1-G21 基础上，真实受控执行还需满足以下条件：

| # | 条件 | 检查方式 | 失败归类 |
|---|------|----------|----------|
| E1 | 当前 Stage 是 Stage 8 | 校验 stage 字段 | blocked_by_stage_boundary |
| E2 | next pending task 是 Stage 8 | 读取 tasks.md 校验 | blocked_by_stage_boundary |
| E3 | 工作区 clean | git status --short | blocked_by_dirty_workspace |
| E4 | staged files 为空 | git diff --cached --name-only | blocked_by_staged_changes |
| E5 | 当前任务状态明确 | 读取 tasks.md | blocked_by_unknown_error |
| E6 | next task 明确 | 读取 tasks.md | no_pending_tasks |
| E7 | approval record 存在 | 检查 approval record 文件 | blocked_by_missing_approval_record |
| E8 | checkpoint 存在 | 检查 checkpoint 文件 | blocked_by_missing_checkpoint |
| E9 | validation rule 存在 | 检查 validation 配置 | blocked_by_unknown_error |
| E10 | allowed scope 明确 | 检查 allowed_scope 字段 | blocked_by_unapproved_changes |
| E11 | command allowlist 明确 | 检查 command_allowlist 字段 | blocked_by_command_allowlist |
| E12 | real_execution_allowed 必须经过单独 gate | 校验 execution gate 审批 | blocked_by_real_execution_gate |
| E13 | push_allowed 必须保持 false | 校验安全标志 | blocked_by_git_safety_gate |
| E14 | resume_allowed 默认 false | 校验 resume 状态 | blocked_by_unknown_error |
| E15 | max_tasks 有明确上限 | 校验 max_tasks <= 2 | blocked_by_unknown_error |
| E16 | stop_reason 可追踪 | 校验 stop_reason 记录 | blocked_by_unknown_error |

### 5.2 Gate 层次关系

```text
Layer 1 Gate (dry-run 前):
  G1-G21 (T143 已有) — 任务间推进安全检查

Layer 2 Gate (dry-run + execution):
  G1-G21 + E1-E16 — 真实执行安全检查

真实执行流程：
  G1-G21 gate check → 通过 → E1-E16 execution gate check → 通过 → 真实执行 → post-execution check

不允许：
  - 跳过 G1-G21 直接进入 E1-E16
  - 跳过 E1-E16 直接真实执行
  - 部分通过即执行
```

### 5.3 Fail-closed 保证

```text
1. 任何 gate check 失败 → 立即停止，不执行
2. 任何输入字段缺失 → 立即停止，不执行
3. 任何状态不确定 → 立即停止，不执行
4. gate 判断结果必须记录在 checkpoint 中
5. gate 失败后不允许自动重试
6. gate 失败后必须输出 required_actions
```

---

## 6. Checkpoint 要求

### 6.1 真实受控执行 Checkpoint Schema

```yaml
checkpoint_version: "2.0"
run_id: "stage8-real-run-001"
stage: "Stage 8"
mode: "real_controlled_continuous_execution"
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
  last_commit_before: "7c45f24 docs: archive stage 8 planning and dry-run chain"
  last_commit_after: "null"

records:
  approval_record_path: "reports/stage8/real-execution-approval-T152.md"
  checkpoint_path: "reports/stage8/real-execution-checkpoint-T152.md"
  reports_generated: []
  commits_created: []
  pushes_created: []  # 始终为空

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
```

### 6.2 关键约束

| # | 约束 | 说明 |
|---|------|------|
| 1 | resume_allowed=false by default | 不允许自动 resume |
| 2 | push_allowed=false | Stage 8 不允许 push |
| 3 | pushes_created 始终为空 | 任何 push 都禁止 |
| 4 | last_commit_before 必须在执行前记录 | 作为执行基线 |
| 5 | last_commit_after 在执行后更新 | 确认执行后的 commit |
| 6 | staged_files_before / staged_files_after 都必须记录 | 确认执行前后 staged 变化 |
| 7 | approval_record_path 必须指向真实存在的文件 | 真实 step 必须有审批 |
| 8 | validation_status 从 pending 开始 | 执行后更新为 pass/fail |
| 9 | mode 必须为 real_controlled_continuous_execution | 区分 dry-run 和真实执行 |
| 10 | real_controlled_execution 必须为 true | 标记为真实执行模式 |

---

## 7. Approval Record 要求

### 7.1 真实受控执行 Approval Record Schema

```yaml
approval_record_version: "2.0"
approval_id: "T152-real-execution-approval"
generated_at: "2026-05-10T15:02:00"

task:
  task_id: "T152"
  stage: "Stage 8"
  operation_type: "real_controlled_single_step_execution"

agent:
  selected_agent: "Developer"
  agent_role: "implementer"

execution:
  planned_action: "Execute T152 real controlled single-step"
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
    - "git log"
  validation_required: true
  git_backup_required: true
  commit_required: true
  real_execution_allowed: true
  push_allowed: false
  stage_boundary_check: "within_stage_8"

approval:
  approval_status: "approved"
  approved_by: "human"
  approval_time: "2026-05-10T15:01:00"

decision:
  final_status: "approved_for_execution"
  ready_for_execution: true
  ready_for_git_commit: false
  ready_for_push: false
  ready_for_stage_9: false

notes: |
  Approval for T152 real controlled single-step execution.
  max_tasks=1. push_allowed=false.
```

### 7.2 关键约束

| # | 约束 | 说明 |
|---|------|------|
| 1 | push_allowed=false | 始终禁止 push |
| 2 | real_execution_allowed 必须经过 execution gate 审批 | 不允许默认为 true |
| 3 | allowed_scope 必须明确列出 | 不允许通配符或模糊范围 |
| 4 | command_allowlist 必须明确列出 | 不允许执行白名单外的命令 |
| 5 | approved_by 必须为 human | 当前阶段不允许自动审批 |
| 6 | approval_status 从 pending 开始 | 审批后才更新为 approved |
| 7 | final_status 从 pending 开始 | 执行后更新为 completed/failed |
| 8 | stage_boundary_check 必须为 within_stage_8 | 不允许跨 Stage |
| 9 | ready_for_push 始终为 false | Stage 8 不允许 push |
| 10 | ready_for_stage_9 始终为 false | Stage 8 不允许进入 Stage 9 |

---

## 8. Stop Reason 设计

### 8.1 完整 Stop Reason 列表

| # | stop_reason | 触发条件 | 是否允许 resume | 后续动作 |
|---|-------------|----------|-----------------|----------|
| 1 | completed_max_tasks | tasks_attempted >= max_tasks，全部通过 | 否（新开 run） | 审查 run summary |
| 2 | no_pending_tasks | 无 pending 任务 | 否（新开 run） | 检查是否需新增任务 |
| 3 | blocked_by_dirty_workspace | git status 有输出 | 否 | 检查 dirty 文件，提交或回滚 |
| 4 | blocked_by_staged_changes | git diff --cached 有文件 | 否 | 检查 staged 文件 |
| 5 | blocked_by_validation_failure | validation_status = fail | 否 | 查看 validation report |
| 6 | blocked_by_rework_required | rework_required = true | 否 | 执行返工 |
| 7 | blocked_by_unapproved_changes | 检测到未审批变更 | 否 | 审批或拒绝 |
| 8 | blocked_by_stage_boundary | next task 不属于 Stage 8 | 否 | 确认跨 Stage 需求 |
| 9 | blocked_by_missing_approval_record | approval record 不存在 | 否 | 生成 approval record |
| 10 | blocked_by_missing_report | report 不存在 | 否 | 生成 report |
| 11 | blocked_by_git_safety_gate | push_allowed=true 或分支不安全 | 否 | 修复安全标志 |
| 12 | blocked_by_rate_limit | 速率限制触发 | 否 | 等待冷却 |
| 13 | manual_stop_required | 用户请求停止 | 否 | 人工确认 |
| 14 | blocked_by_unknown_error | 未分类错误 | 否 | 人工分析 |
| 15 | blocked_by_real_execution_gate | execution gate 未通过 | 否 | 修复 gate 失败原因 |
| 16 | blocked_by_command_allowlist | 命令不在白名单内 | 否 | 更新白名单或修改操作 |
| 17 | blocked_by_missing_checkpoint | checkpoint 不存在 | 否 | 生成 checkpoint |

### 8.2 Stop Reason 分类

```text
正常停止（预期行为）：
  1. completed_max_tasks
  2. no_pending_tasks

安全停止（gate 拦截）：
  3. blocked_by_dirty_workspace
  4. blocked_by_staged_changes
  5. blocked_by_validation_failure
  6. blocked_by_rework_required
  7. blocked_by_unapproved_changes
  8. blocked_by_stage_boundary
  9. blocked_by_missing_approval_record
  10. blocked_by_missing_report
  11. blocked_by_git_safety_gate
  15. blocked_by_real_execution_gate
  16. blocked_by_command_allowlist
  17. blocked_by_missing_checkpoint

运行状态停止：
  12. blocked_by_rate_limit
  13. manual_stop_required
  14. blocked_by_unknown_error
```

### 8.3 Stop Reason 处理原则

```text
1. 正常停止 → 可以安全地新开一轮
2. 安全停止 → 必须修复 gate 失败原因后再继续
3. 运行状态停止 → 等待条件恢复或人工介入
4. 所有 stop_reason 都必须记录在 checkpoint 和 run summary 中
5. 不允许自动忽略 stop_reason
6. 不允许自动绕过阻塞
7. 不允许在 stop 后自动 resume
```

---

## 9. Git 策略

### 9.1 Stage 8 后半段 Git 边界

| # | 策略 | 说明 |
|---|------|------|
| 1 | 不自动 push | push 始终禁止，留给 Stage 9 |
| 2 | 不无条件自动 commit | 需要通过 approval gate 后才允许 commit |
| 3 | 不允许 git add . | 必须指定具体文件白名单 |
| 4 | 不允许 git add -A | 必须指定具体文件白名单 |
| 5 | 只允许通过指定文件白名单 | planned_files 和 allowed_scope 内的文件 |
| 6 | Git commit 需审批 | commit 前必须通过 Git approval gate |
| 7 | Git commit message 需校验 | 必须符合 commit message 规范 |

### 9.2 真实受控 step 的 Git 流程

```text
真实受控 step 的 Git 处理：

Layer 3 (max_tasks=1 trial):
  1. 执行前：记录 last_commit_before
  2. 执行任务：产出代码变更
  3. 变更检查：对比 planned_files vs 实际变更
  4. Git approval gate：审批变更内容
  5. git add（仅白名单文件）
  6. git commit（需 approval record）
  7. 记录 last_commit_after
  8. 不 push

Layer 4 (max_tasks=2):
  每个任务重复 Layer 3 的流程
  任务之间必须 workspace clean

禁止：
  - git push
  - git add .
  - git add -A
  - git commit --no-verify
  - git commit -m "auto"
  - git reset --hard
  - 任何 force 操作
```

### 9.3 Git 完整自动化留给 Stage 9

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

## 10. 风险清单

### 10.1 主要风险与防护方案

| # | 风险 | 影响 | 防护方案 |
|---|------|------|----------|
| 1 | 连续任务误推进 | 执行了不该执行的任务 | G1-G21 + E1-E16 双层 gate check，fail-closed |
| 2 | dirty workspace 叠加 | 上一个任务残留影响下一个 | 每轮强制 workspace clean check |
| 3 | 未审批文件被带入下一轮 | 非预期文件被 commit | planned_files 白名单 + git add 只允许白名单文件 |
| 4 | next task 选择错误 | 选错任务执行 | 按 pending 顺序选取 + stage boundary check |
| 5 | 跨 Stage | 自动进入 Stage 9 | G2/G3 stage boundary check |
| 6 | Git 状态不一致 | commit 后状态与预期不符 | last_commit_before/after 对比 |
| 7 | checkpoint 不完整 | 无法追踪执行状态 | checkpoint schema v2.0 强制字段 |
| 8 | approval record 缺失 | 无法审计执行决策 | E7 gate check + 真实执行前强制检查 |
| 9 | Claude Code 卡住 | 任务执行不结束 | max_tasks 限制 + manual_stop 机制 |
| 10 | rate limit | 模型调用限频 | G18 rate limit check + 停止等待 |
| 11 | 模型输出不稳定 | 执行结果不一致 | validation check + rework 机制 |
| 12 | 人工验收缺失 | 未审查即执行下一步 | approval record 要求 approved_by=human |

### 10.2 分层风险缓解

```text
Layer 1 → 风险最低：只做设计，不执行任何操作
Layer 2 → 风险低：dry-run 模拟，无真实执行
Layer 3 → 风险中等：max_tasks=1，单任务真实执行，失败影响范围有限
Layer 4 → 风险较高：max_tasks=2，需 Layer 3 验证通过后才进行

每层都保持 fail-closed 原则：
  - 任何层出现异常 → 立即停止
  - 不允许跳层执行
  - 不允许上层失败后继续下层
```

---

## 11. 后续任务拆解建议

### 11.1 建议任务链

| # | 任务 | 角色 | 目标 | Layer |
|---|------|------|------|-------|
| 1 | T149 | Designer | 设计 Stage 8 real controlled continuous execution gate | Layer 1 |
| 2 | T150 | Developer | 实现 Stage 8 real controlled continuous execution dry-run | Layer 2 |
| 3 | T151 | Validator | 验证 Stage 8 real controlled continuous execution dry-run | Layer 2 |
| 4 | T152 | Developer | 实现 max_tasks=1 real controlled single-step execution trial | Layer 3 |
| 5 | T153 | Validator | 验证 max_tasks=1 real controlled single-step execution trial | Layer 3 |
| 6 | T154 | Archiver | 归档 Stage 8 real controlled continuous execution 成果 | - |

### 11.2 任务链说明

```text
T149: 设计阶段
  - 在 T143 G1-G21 基础上设计 execution gate (E1-E16)
  - 定义真实执行的 approval record schema v2.0
  - 定义真实执行的 checkpoint schema v2.0
  - 定义 Layer 3/Layer 4 的边界和约束
  - 不实现代码，不执行真实操作

T150: 实现阶段（dry-run）
  - 在 T144/T146 基础上实现 real controlled execution dry-run
  - 实现 E1-E16 execution gate check
  - 实现 approval record 生成
  - 实现 checkpoint v2.0 生成
  - 不执行真实任务

T151: 验证阶段
  - 验证 T150 dry-run 的 pass/fail 场景
  - 确认 E1-E16 全部 gate check 正确
  - 确认 fail-closed 行为
  - 确认无副作用

T152: 实现阶段（real trial）
  - max_tasks=1 条件下的真实受控单步执行
  - 需要在 T150/T151 验证通过后执行
  - 需要人工审批 approval record
  - 需要通过 E1-E16 execution gate
  - 受控 git add/commit

T153: 验证阶段（real trial）
  - 验证 T152 真实执行的结果
  - 确认 workspace 状态正确
  - 确认 checkpoint 完整
  - 确认 approval record 完整
  - 确认无意外副作用

T154: 归档阶段
  - 归档 Stage 8 真实受控连续推进全部成果
  - 更新 tasks.md
  - 不进入 Stage 9
```

### 11.3 任务边界

```text
T149-T154 遵循以下边界原则：

  - 每个任务只做该层允许的操作
  - Layer 1 只做设计
  - Layer 2 只做 dry-run
  - Layer 3 才允许真实执行（需前置验证全部通过）
  - 归档任务不执行真实操作
  - 不允许跨任务跳过验证
  - 不允许绕过任何 gate check
  - 不允许自动 push
  - 不允许进入 Stage 9
  - 不允许修改 T143-T148 的已有成果
```

---

## 12. 后续边界说明

```text
NEXT_PENDING=T149
NEXT_STAGE=Stage 8
```

T149 仍然只做 safety gate / execution gate 设计，不直接真实执行连续任务。

T149 应设计的内容：
1. 在 T143 G1-G21 基础上设计 E1-E16 execution gate check
2. 定义 approval record schema v2.0
3. 定义 checkpoint schema v2.0
4. 定义 Layer 3/Layer 4 的具体 pass/fail 场景
5. 为 T150 dry-run 实现提供设计约束

T149 不允许：
  - 实现代码
  - 执行真实任务
  - 真实 git add / commit / push
  - 自动跨入 Stage 9
  - 修改业务代码

---

## 设计元数据

- 设计角色：Planner / Architecture Agent
- 设计日期：2026-05-10
- 设计基准提交：7c45f24 docs: archive stage 8 planning and dry-run chain
- 工作区状态：clean
- 前置条件：Stage 8 planning/dry-run 链路完成（T143-T148）
- 设计结论：STAGE8_REAL_CONTROLLED_EXECUTION_PLAN_COMPLETE=yes
