# Stage 8 Planning：真实连续任务自动推进方案

设计时间：2026-05-09
阶段：Stage 8 — 真实连续任务自动推进
任务角色：Planner / Architecture Agent
前置条件：STAGE7_COMPLETE=yes, STAGE8_READY_FOR_PLANNING=yes

---

## 1. Stage 8 目标

Stage 8 的目标是**真实连续任务自动推进**。

即系统在完成一个任务后，可以在安全边界内自动选择下一个 pending 任务继续执行。

### 1.1 Stage 8 是什么

- 多个任务之间的**连续推进控制**
- 每个任务仍然走 Stage 7 已有的单任务安全链路
- 任务之间增加 **checkpoint、approval record、workspace 检查**
- 每轮推进都有明确的 **stop reason**

### 1.2 Stage 8 不是什么

Stage 8 **明确不是**：

| # | 不是什么 | 说明 |
|---|----------|------|
| 1 | 不是无限循环 | 有 max_tasks 硬性上限 |
| 2 | 不是无人值守全自动 | 每轮推进需要 gate check 通过 |
| 3 | 不是绕过人工验收 | approval record 必须生成并可审查 |
| 4 | 不是自动 push | push 始终禁止 |
| 5 | 不是自动跨阶段 | 不允许自动进入 Stage 9+ |
| 6 | 不是直接打开所有真实执行权限 | 每个权限需单独 gate 授权 |
| 7 | 不是去掉 Stage 7 的安全保护 | Stage 8 在 Stage 7 安全链路之上运行 |

### 1.3 核心原则

```text
1. 每个任务独立安全 — 复用 Stage 7 的全部安全链路
2. 任务间严格隔离 — 每个任务开始前 workspace 必须 clean
3. 失败即停止 — 任何任务失败立即停止连续推进
4. 不自动 push — 始终不 push 到 remote
5. 不自动跨阶段 — 不允许从 Stage 8 进入 Stage 9
6. 可审查可追溯 — 每个任务都有独立的 approval record 和 report
```

---

## 2. Stage 8 与 Stage 7 的区别

### 2.1 Stage 7 重点

Stage 7 的核心是**真实单任务自动执行**：

- 一次只处理一个任务
- 每个任务有独立的安全链路
- 任务之间没有自动衔接
- 每个任务完成后需要人工确认才能开始下一个

Stage 7 已建立的安全能力：

| # | 安全能力 | 来源 | Stage 8 复用 |
|---|----------|------|-------------|
| 1 | no-tool-use proposal schema | T115-T116 | 作为任务的 proposal 生成方式 |
| 2 | proposal parser dry-run | T117 | 作为任务执行前的解析校验 |
| 3 | allowed scope validator | T118 | 作为任务文件范围校验 |
| 4 | controlled patch apply dry-run | T119-T120 | 作为 patch apply 的安全方式 |
| 5 | approval model dry-run | T124 | 作为任务审批模型 |
| 6 | command allowlist validation | T125 | 作为命令白名单校验 |
| 7 | human-reviewed controlled apply dry-run | T126 | 作为带审批的 controlled apply |
| 8 | guarded real patch apply dry-run | T130-T132 | 作为真实 patch apply 守卫 |
| 9 | guarded Git backup dry-run | T136 | 作为 Git 备份守卫 |
| 10 | real Git add/commit dry-run | T140 | 作为 Git 提交守卫 |
| 11 | pass/fail validation | T121/T127/T133/T137/T141 | 作为每条链路的验证标准 |
| 12 | fail-closed 原则 | 全链路 | 作为所有 gate 的默认行为 |

### 2.2 Stage 8 新增重点

Stage 8 在 Stage 7 之上新增以下能力：

| # | 新增能力 | 说明 |
|---|----------|------|
| 1 | 任务循环控制 | 自动从 pending 列表中选取下一个任务 |
| 2 | max_tasks 限制 | 单次连续运行的任务数量硬性上限 |
| 3 | stop reason | 明确的停止原因和处理建议 |
| 4 | workspace 隔离 | 每轮开始前强制检查 workspace 状态 |
| 5 | checkpoint | 每轮完成后生成运行检查点 |
| 6 | run summary | 整次连续运行的汇总报告 |
| 7 | 任务间状态重读 | 每轮重新读取 docs/tasks.md |

---

## 3. 连续任务推进边界

### 3.1 核心边界规则

| # | 边界规则 | 说明 |
|---|----------|------|
| 1 | 每轮最多执行一个 task step | 不允许在一个 step 中处理多个任务 |
| 2 | 每个任务完成后必须重新检查状态 | 不允许跳过状态检查 |
| 3 | 每个任务之间必须重新读取 docs/tasks.md | 不允许使用缓存的任务列表 |
| 4 | 不允许跳过 pending 顺序 | 必须按顺序选取下一个 pending 任务 |
| 5 | 不允许自动跨 Stage | 不允许从 Stage 8 自动进入 Stage 9 |
| 6 | 不允许自动 push | push 始终禁止 |
| 7 | 不允许无限循环 | max_tasks 提供硬性上限 |
| 8 | 必须有 max_tasks | 单次运行必须指定最大任务数 |
| 9 | 必须有 stop_reason | 每次停止必须有明确原因 |
| 10 | 必须有 checkpoint | 每轮完成后必须生成 checkpoint |
| 11 | 必须有 run summary | 整次运行结束后必须生成汇总 |

### 3.2 max_tasks 设计

```text
max_tasks 安全上限：
  - 默认值：1
  - 最小值：1
  - 建议上限：5
  - 绝对上限：10

  max_tasks=1 时等价于 Stage 7 的单任务执行
  max_tasks>1 时才启用连续推进

  max_tasks 不允许为 0 或负数
  max_tasks 不允许超过绝对上限 10
```

### 3.3 任务选取规则

```text
任务选取规则：
  1. 读取 docs/tasks.md
  2. 找到第一个状态为 pending 的任务
  3. 确认该任务属于当前 Stage（Stage 8）
  4. 确认该任务没有被 blockedBy 依赖阻塞
  5. 选取该任务为当前任务
  6. 如果没有符合条件的 pending 任务，stop_reason=no_pending_tasks

  不允许：
  - 跳过前面的 pending 任务
  - 选取非当前 Stage 的任务
  - 选取被阻塞的任务
  - 自行创建新任务
```

### 3.4 单轮执行流程

```text
单轮执行流程：

  ┌─────────────────────────────────────┐
  │ Step 0: pre-loop check              │
  │   - 读取 docs/tasks.md              │
  │   - 确认 max_tasks > 0              │
  │   - 确认 tasks_attempted < max_tasks│
  │   - 确认 stop_reason == null        │
  └──────────────┬──────────────────────┘
                 │
  ┌──────────────▼──────────────────────┐
  │ Step 1: workspace check             │
  │   - git status --short              │
  │   - 如果 dirty → stop               │
  │   - 如果 clean → 继续               │
  └──────────────┬──────────────────────┘
                 │
  ┌──────────────▼──────────────────────┐
  │ Step 2: task selection              │
  │   - 选取下一个 pending 任务         │
  │   - 如果无 pending → stop           │
  └──────────────┬──────────────────────┘
                 │
  ┌──────────────▼──────────────────────┐
  │ Step 3: task execution              │
  │   - 复用 Stage 7 安全链路           │
  │   - 执行当前任务                    │
  │   - 生成 report 和 approval record  │
  └──────────────┬──────────────────────┘
                 │
  ┌──────────────▼──────────────────────┐
  │ Step 4: post-task validation        │
  │   - 验证任务结果                    │
  │   - 如果 fail → stop               │
  │   - 如果 pass → 继续               │
  └──────────────┬──────────────────────┘
                 │
  ┌──────────────▼──────────────────────┐
  │ Step 5: checkpoint                  │
  │   - 生成当前轮 checkpoint           │
  │   - 更新 tasks_attempted            │
  │   - 更新 tasks_completed            │
  └──────────────┬──────────────────────┘
                 │
  ┌──────────────▼──────────────────────┐
  │ Step 6: loop decision               │
  │   - tasks_attempted < max_tasks ?   │
  │   - 还有 pending 任务吗？           │
  │   - stop_reason == null ?           │
  │   - 全部 yes → 回到 Step 0          │
  │   - 任一 no → 进入 Step 7           │
  └──────────────┬──────────────────────┘
                 │
  ┌──────────────▼──────────────────────┐
  │ Step 7: run summary                 │
  │   - 生成 run summary                │
  │   - 记录 stop_reason                │
  │   - 输出最终状态                    │
  └─────────────────────────────────────┘
```

---

## 4. stop reason 设计

### 4.1 stop reason 列表

| # | stop_reason | 含义 | 后续处理 |
|---|-------------|------|----------|
| 1 | `completed_max_tasks` | 已完成 max_tasks 个任务，达到上限 | 审查 run summary，如需继续可新开一轮 |
| 2 | `no_pending_tasks` | 没有更多 pending 任务可执行 | 检查是否需要新增任务或归档当前 Stage |
| 3 | `blocked_by_dirty_workspace` | 工作区存在未归档内容，不 clean | 检查 dirty 内容，决定提交或回滚 |
| 4 | `blocked_by_validation_failure` | 当前任务 validation 未通过 | 查看 validation report，修复后重新运行 |
| 5 | `blocked_by_rework_required` | 当前任务需要返工 | 查看 rework 原因，执行返工后重新运行 |
| 6 | `blocked_by_unapproved_changes` | 检测到未审批的变更 | 检查变更内容，审批或拒绝后继续 |
| 7 | `blocked_by_stage_boundary` | 下一个 pending 任务属于不同 Stage | 确认是否需要跨 Stage，需要单独授权 |
| 8 | `blocked_by_missing_approval_record` | 缺少必要的 approval record | 生成缺失的 approval record 后重新运行 |
| 9 | `blocked_by_git_safety_gate` | Git 安全 gate 未通过 | 查看 gate 拒绝原因，修复后重新运行 |
| 10 | `blocked_by_unknown_error` | 未知错误 | 查看错误日志，人工介入分析 |
| 11 | `blocked_by_rate_limit` | 触发速率限制 | 等待冷却后重新运行（本阶段仅记录，不自动恢复） |
| 12 | `manual_stop_required` | 需要人工确认后才能继续 | 人工确认后可新开一轮 |

### 4.2 stop reason 分类

```text
正常停止（预期行为）：
  - completed_max_tasks
  - no_pending_tasks

异常停止（需要干预）：
  - blocked_by_dirty_workspace
  - blocked_by_validation_failure
  - blocked_by_rework_required
  - blocked_by_unapproved_changes
  - blocked_by_stage_boundary
  - blocked_by_missing_approval_record
  - blocked_by_git_safety_gate
  - blocked_by_unknown_error
  - blocked_by_rate_limit
  - manual_stop_required
```

### 4.3 stop reason 后续处理原则

```text
1. 正常停止：可以安全地新开一轮运行
2. 异常停止：必须先解决阻塞原因，才能继续
3. 所有 stop_reason 都必须记录在 run summary 中
4. 不允许自动忽略 stop_reason
5. 不允许自动绕过阻塞
6. rate_limit 仅记录，不自动恢复（后续专题）
```

---

## 5. dirty workspace 保护

### 5.1 保护规则

| # | 规则 | 说明 |
|---|------|------|
| 1 | 每轮开始前检查 git status --short | 必须检查 |
| 2 | 如果 dirty workspace 存在未归档内容，必须停止 | stop_reason=blocked_by_dirty_workspace |
| 3 | 如果 dirty workspace 是当前任务预期结果，必须进入提交/归档 gate | 不允许跳过 gate |
| 4 | 不允许在 dirty workspace 上直接开始下一任务 | 必须先处理 dirty 内容 |
| 5 | 不允许自动清理用户文件 | 用户文件必须由用户确认 |
| 6 | 不允许覆盖未分类修改 | 未分类修改必须先分类处理 |

### 5.2 workspace 状态分类

```text
clean：
  git status --short 无输出
  → 可以安全开始下一任务

expected_dirty：
  dirty 内容全部是当前任务的预期输出
  → 进入提交/归档 gate → 提交后变为 clean → 再开始下一任务

unexpected_dirty：
  dirty 内容包含非当前任务的修改
  → 停止，stop_reason=blocked_by_dirty_workspace
  → 人工确认后处理
```

### 5.3 workspace 检查流程

```text
workspace_check():
  status = git status --short

  if status is empty:
    return "clean"

  changed_files = parse(status)
  expected_files = current_task.planned_files

  unexpected = changed_files - expected_files

  if unexpected is empty:
    return "expected_dirty"  # 进入提交 gate
  else:
    return "unexpected_dirty"  # 停止，报告 unexpected 文件
```

---

## 6. checkpoint 设计

### 6.1 checkpoint 数据结构

```yaml
checkpoint_version: "1.0"
run_id: "stage8-run-001"
stage: "Stage 8"
mode: "continuous_real_task_auto_advance"

timing:
  started_at: "2026-05-09T14:00:00"
  ended_at: null  # 运行中为 null，结束后填写
  last_checkpoint_at: "2026-05-09T14:05:00"

limits:
  max_tasks: 2
  tasks_attempted: 1
  tasks_completed: 1

current_state:
  current_task: null  # 当前无正在执行的任务
  last_completed_task: "T144"
  next_pending_task: "T145"
  stop_reason: null  # 运行中为 null

workspace:
  status_before: "clean"
  status_after: "clean"

records:
  approval_records:
    - "reports/approval/t144-approval-record.md"
  reports_generated:
    - "reports/dev/T144-dev-report.md"
  commits_created:
    - "abc1234 feat: implement T144 ..."
  pushes_created: []  # 始终为空

errors: []

resume:
  resume_allowed: false  # 默认 false
  # resume 仅在后续 rate-limit recovery 专题中实现
  # 当前阶段不允许自动 resume

notes: |
  Checkpoint generated after T144 completion.
  Workspace clean. Next task is T145.
```

### 6.2 关键约束

```text
1. resume_allowed 默认 false
   - 不允许自动 resume
   - rate-limit recovery 和 checkpoint resume 是后续专题

2. checkpoint 在以下时机生成：
   - 每个任务完成后
   - 每次 stop 后

3. checkpoint 文件路径：
   reports/checkpoints/stage8-run-{run_id}-checkpoint.md

4. checkpoint 必须包含：
   - 当前运行状态
   - workspace 前后状态
   - 已生成的所有 records 和 reports
   - 已创建的 commits
   - 错误记录
   - resume 状态

5. 不允许：
   - 篡改已生成的 checkpoint
   - 跳过 checkpoint 生成
   - 在 checkpoint 中伪造完成状态
```

---

## 7. approval record 设计

### 7.1 每任务 approval record

Stage 8 每个任务必须有独立的 approval record。

```yaml
approval_record_version: "1.0"
approval_id: "T144-stage8-approval"
generated_at: "2026-05-09T14:03:00"

task:
  task_id: "T144"
  task_type: "implementation"
  task_title: "实现 Stage 8 continuous runner dry-run planner"
  stage: "Stage 8"
  run_id: "stage8-run-001"

agent:
  selected_agent: "Developer"
  agent_role: "implementer"

execution:
  planned_files:
    - "tools/continuous_runner.py"
    - "runner.py"
  allowed_scope:
    - "tools/"
    - "runner.py"
    - "docs/"
    - "reports/"
  command_allowlist:
    - "python runner.py"
  validation_required: true
  git_backup_required: true
  commit_required: true

safety:
  push_allowed: false
  real_execution_allowed: false  # dry-run 阶段
  stage_boundary_check: "within_stage_8"
  dry_run: true
  auto_continue_allowed: false
  auto_push_allowed: false
  auto_cross_stage_allowed: false

validation:
  scope_valid: true
  files_valid: true
  commands_valid: true
  workspace_clean_before: true
  workspace_clean_after: true

decision:
  final_status: "pass"
  ready_for_next_task: true
  ready_for_real_execution: false
  ready_for_push: false
  ready_for_stage_9: false
```

### 7.2 关键约束

```text
1. push_allowed 始终 false
   - 除非后续单独设计 push gate
   - 当前阶段不允许任何自动 push

2. real_execution_allowed
   - dry-run 阶段：false
   - 未来真实执行阶段：需要单独 gate 授权

3. stage_boundary_check
   - 必须确认当前任务在 Stage 8 范围内
   - 不允许自动跨入 Stage 9+

4. 每个 approval record 必须与对应任务的 report 一起生成
5. approval record 必须在 checkpoint 中被引用
6. 不允许跳过 approval record 生成
```

---

## 8. CLI / workflow 设计

### 8.1 未来命令建议

本节只做设计，不实现。

```powershell
# 基本连续运行（dry-run）
python runner.py run-project-loop --max-tasks 2 --dry-run

# 带真实执行确认的连续运行
python runner.py run-project-loop --real-execution --max-tasks 2 --confirm

# 带真实执行确认 + Git dry-run 的连续运行
python runner.py run-project-loop --real-execution --max-tasks 2 --confirm --dry-run-git

# 仅生成 run plan 不执行
python runner.py run-project-loop --plan-only --max-tasks 2
```

### 8.2 参数设计

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--max-tasks` | int | 1 | 单次运行最大任务数，范围 [1, 10] |
| `--dry-run` | flag | true | 默认 dry-run，不执行真实操作 |
| `--real-execution` | flag | false | 启用真实执行（需配合 --confirm） |
| `--confirm` | flag | false | 每任务确认 |
| `--dry-run-git` | flag | true | Git 操作 dry-run |
| `--plan-only` | flag | false | 只生成计划不执行 |
| `--run-id` | string | auto | 指定 run_id |

### 8.3 安全约束

```text
1. Stage 8 planning 不新增真实 CLI
   - 本文档只定义 CLI 设计方向
   - 真实 CLI 在后续实现任务中逐步接入

2. --max-tasks 必须有默认安全上限
   - 默认值 1
   - 绝对上限 10
   - 不允许超过上限

3. --confirm 不能绕过每任务 gate
   - --confirm 只表示用户同意运行
   - 每个任务仍然需要通过各自的 gate check
   - gate check 不通过时即使有 --confirm 也会停止

4. --dry-run 默认为 true
   - 必须显式传入 --real-execution 才能执行真实操作
   - --real-execution 在本 planning 阶段仍然无效

5. 不允许通过参数绕过以下限制：
   - push_allowed=false
   - auto_cross_stage=false
   - auto_continue=false（max_tasks 以外的继续）
   - workspace clean check
```

---

## 9. pass / fail 场景设计

### 9.1 Pass 场景

| # | 场景 | 预期行为 |
|---|------|----------|
| P1 | max_tasks=1，成功执行 1 个任务后停止 | 执行 1 个任务，生成 report + approval record + checkpoint，stop_reason=completed_max_tasks |
| P2 | max_tasks=2，连续执行 2 个安全任务后停止 | 连续执行 2 个任务，每个任务都有完整安全链路，stop_reason=completed_max_tasks |
| P3 | no pending tasks 时安全停止 | 没有更多 pending 任务，stop_reason=no_pending_tasks |
| P4 | 每任务完成后都有 report 和 approval record | 每个 pass 任务都生成完整文档 |
| P5 | 工作区 clean 后才进入下一任务 | 每轮 workspace 检查通过后才继续 |
| P6 | max_tasks 达到后即使还有 pending 任务也停止 | 遵守 max_tasks 限制 |

### 9.2 Fail 场景

| # | 场景 | 预期行为 |
|---|------|----------|
| F1 | 工作区 dirty | stop_reason=blocked_by_dirty_workspace |
| F2 | 当前任务 validation fail | stop_reason=blocked_by_validation_failure |
| F3 | 缺少 approval record | stop_reason=blocked_by_missing_approval_record |
| F4 | 出现 unapproved file | stop_reason=blocked_by_unapproved_changes |
| F5 | 尝试跨 Stage | stop_reason=blocked_by_stage_boundary |
| F6 | 尝试 push | stop_reason=blocked_by_git_safety_gate |
| F7 | 尝试无限循环 | max_tasks 限制强制停止 |
| F8 | max_tasks 为空或过大 | 拒绝启动，要求修正 max_tasks |
| F9 | rework required | stop_reason=blocked_by_rework_required |
| F10 | rate limit | stop_reason=blocked_by_rate_limit |
| F11 | unknown error | stop_reason=blocked_by_unknown_error |
| F12 | max_tasks=0 或负数 | 拒绝启动，要求修正 max_tasks |
| F13 | max_tasks > 10 | 拒绝启动，要求修正 max_tasks |

### 9.3 验证原则

```text
1. 所有 pass 场景必须验证：
   - 任务正确完成
   - report + approval record 生成
   - checkpoint 生成
   - workspace 前后状态正确
   - stop_reason 正确

2. 所有 fail 场景必须验证：
   - 正确停止
   - stop_reason 正确
   - 不产生副作用
   - 不继续推进
   - 不 push
   - 不跨 Stage
   - 现场保留供人工检查

3. 验证方式：
   - 与 Stage 7 一致的 pass/fail 验证报告
   - 每个 fail 场景都有明确的拒绝原因
   - 所有 fail 场景均为 fail-closed
```

---

## 10. 与后续阶段关系

### 10.1 阶段路线图

| 阶段 | 核心目标 | 与 Stage 8 关系 |
|------|----------|----------------|
| Stage 8 | 真实连续任务自动推进 | 当前阶段 |
| Stage 9 | 自动 Git 备份与执行记录 | Stage 8 的 checkpoint/approval record 自动归档 |
| Stage 10 | 真实返工闭环接入 | Stage 8 的 stop_reason 触发返工时自动处理 |
| Stage 11 | 外部入口自动化 | Stage 8 的 CLI 接入外部触发 |
| Stage 12 | 产品化与稳定性 | 全链路集成和稳定性保障 |

### 10.2 Stage 8 不提前实现的内容

```text
Stage 8 不应提前实现 Stage 9/10/11/12 的完整能力：

  - 不实现自动 Git 备份归档（Stage 9）
  - 不实现自动返工闭环（Stage 10）
  - 不实现外部触发入口（Stage 11）
  - 不实现产品化功能（Stage 12）
  - 不实现 rate-limit 自动恢复（后续专题）
  - 不实现 checkpoint 自动 resume（后续专题）
```

### 10.3 Stage 8 为后续阶段预留的入口

```text
1. stop_reason 包含 rate_limit → 为 Stage 9/10 的自动恢复预留
2. checkpoint 包含 resume_allowed → 为后续 checkpoint resume 预留
3. CLI 包含 --run-id → 为后续外部触发和恢复预留
4. approval record 包含 stage_boundary_check → 为跨阶段管理预留
```

---

## 11. 后续任务拆解建议

### 11.1 Stage 8 最小任务链

基于本 planning 设计，建议以下最小任务链：

| 任务 | 角色 | 内容 | 状态 |
|------|------|------|------|
| T143 | Designer | 设计 Stage 8 continuous real task runner safety gate | pending |
| T144 | Developer | 实现 Stage 8 continuous runner dry-run planner | pending |
| T145 | Validator | 验证 Stage 8 continuous runner dry-run pass/fail 场景 | pending |
| T146 | Developer | 实现 real single-step continuous advance dry-run | pending |
| T147 | Validator | 验证 real single-step continuous advance dry-run pass/fail 场景 | pending |
| T148 | Archiver | 归档 Stage 8 planning / dry-run 成果 | pending |

### 11.2 任务链说明

```text
T143: 设计阶段
  - 设计 continuous runner 的 safety gate
  - 定义 gate check 列表
  - 定义 checkpoint schema
  - 定义 run summary schema
  - 不实现代码

T144: 实现阶段（dry-run planner）
  - 实现 continuous runner dry-run planner
  - 实现 checkpoint 生成
  - 实现 run summary 生成
  - 不执行真实连续任务

T145: 验证阶段
  - 验证 dry-run planner 的 pass/fail 场景
  - 确认 fail-closed 行为
  - 确认无副作用

T146: 实现阶段（single-step advance）
  - 在 dry-run planner 基础上实现 single-step advance
  - 复用 Stage 7 安全链路
  - 不执行真实连续多任务

T147: 验证阶段
  - 验证 single-step advance dry-run 的 pass/fail 场景
  - 确认 fail-closed 行为
  - 确认无副作用

T148: 归档阶段
  - 归档 Stage 8 planning/dry-run 全部成果
  - 更新 tasks.md
  - 不进入 Stage 9
```

### 11.3 任务边界

```text
T143-T148 遵循与 Stage 7 一致的边界原则：

  - 不允许真实自动 git add
  - 不允许真实自动 git commit
  - 不允许真实自动 git push
  - 不允许自动跨入 Stage 9
  - 不允许无限循环
  - 不允许绕过 gate check
  - 不允许 real_execution_allowed=true（dry-run 阶段）
  - 不允许 push_allowed=true
  - 不允许自动 resume
  - 不允许修改业务代码
```

---

## 12. 与 Stage 7 的集成方式

### 12.1 复用策略

Stage 8 不重新实现 Stage 7 的安全能力，而是直接复用：

```text
每个 Stage 8 任务的执行流程：

  1. 选取 pending 任务（Stage 8 新增）
  2. workspace check（Stage 8 新增）
  3. → 复用 Stage 7 的 proposal parser
  4. → 复用 Stage 7 的 allowed scope validator
  5. → 复用 Stage 7 的 controlled apply gate
  6. → 复用 Stage 7 的 guarded patch apply dry-run
  7. → 复用 Stage 7 的 Git backup dry-run
  8. → 复用 Stage 7 的 Git add/commit dry-run
  9. → 复用 Stage 7 的 pass/fail validation
  10. 生成 approval record（Stage 8 扩展）
  11. 生成 checkpoint（Stage 8 新增）
  12. 判断是否继续（Stage 8 新增）
  13. 生成 run summary（Stage 8 新增）
```

### 12.2 新增与复用的边界

```text
Stage 8 新增：
  - 任务循环控制逻辑
  - max_tasks 限制
  - stop reason 判断
  - workspace 隔离检查
  - checkpoint 生成
  - run summary 生成
  - 每任务 approval record 扩展字段

Stage 7 复用：
  - 全部安全链路
  - 全部 gate check
  - 全部 validation
  - fail-closed 原则

不允许：
  - 修改 Stage 7 已有的安全逻辑
  - 绕过 Stage 7 的任何 gate
  - 在 Stage 7 安全链路上开例外
```

---

## 13. 设计总结

### 13.1 设计决策

```text
STAGE8_PLAN_COMPLETE=yes
STAGE8_EXECUTION_STARTED=no
CONTINUOUS_AUTO_ADVANCE_USED=no
REAL_GIT_ADD_ALLOWED=no
REAL_GIT_COMMIT_ALLOWED=no
REAL_GIT_PUSH_ALLOWED=no
AUTO_CROSS_STAGE_ALLOWED=no
RATE_LIMIT_RECOVERY_ENABLED=no
CHECKPOINT_RESUME_ENABLED=no
```

### 13.2 下一步

```text
NEXT_PENDING=T143
NEXT_STAGE=Stage 8

T143 应设计 Stage 8 continuous real task runner safety gate。
T143 仍然不允许：
  - 真实 git add / commit / push
  - 自动连续任务执行
  - 自动跨入 Stage 9
  - 修改业务代码
```

### 13.3 风险提示

```text
1. 连续推进增加状态管理复杂度
   - 缓解：每轮强制重读 tasks.md，不使用缓存

2. 多任务间 workspace 状态可能不一致
   - 缓解：每轮强制 workspace check

3. max_tasks 过大可能导致长时间运行
   - 缓解：绝对上限 10，默认 1

4. 任务失败后的恢复策略
   - 缓解：失败即停止，人工介入

5. 与后续阶段的边界可能模糊
   - 缓解：明确禁止跨阶段，预留入口但不实现
```

---

## 设计元数据

- 设计角色：Planner / Architecture Agent
- 设计日期：2026-05-09
- 设计基准提交：b00a93d docs: add stage 7 final status review
- 工作区状态：clean
- 前置条件：STAGE7_COMPLETE=yes
- 设计结论：STAGE8_PLAN_COMPLETE=yes
