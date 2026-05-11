# Stage 8 Monitor → Verify → Report Architecture

设计时间：2026-05-11
阶段：Stage 8 — 真实连续任务自动推进
任务角色：Architect Agent + Stage 8 Safety Workflow Architect
前置条件：T153 done, T153.1 committed and pushed

---

## 1. Background

### 1.1 当前状态

Stage 8 已完成以下里程碑：

| 里程碑 | 任务 | 状态 |
|--------|------|------|
| Stage 8 planning | T142 | done |
| Safety gate 设计 (G1-G21) | T143 | done |
| Execution gate 设计 (E1-E18) | T149 | done |
| Continuous runner dry-run 实现 | T144-T145 | done |
| Real controlled execution dry-run | T150-T151 | done |
| Single-step trial (max_tasks=1) | T152-T153 | done |

T153 验证结果：15 个场景全部通过（1 default + 2 sample + 1 safe stop + 10 fail-closed + 1 known gap）。所有安全字段始终 False。

### 1.2 为什么需要 monitor → verify → report 架构

当前 Stage 8 的 single-step trial 已经验证了 max_tasks=1 的安全执行能力，但仍然缺少以下闭环能力：

1. **执行前监控（Monitor）**：没有统一的模块在执行前读取任务状态、workspace 状态、checkpoint 状态。当前每次执行前都需要手动确认这些前置条件。

2. **执行后验证（Verify）**：没有统一的模块在执行后验证任务是否正确完成、报告是否生成、是否违反安全边界。当前验证分散在 gate check 中，没有独立的后置验证闭环。

3. **报告归档（Report）**：没有统一的模块生成每轮执行的汇总报告。当前报告散落在 approval record、checkpoint、trial report 等多个文件中，缺少统一的 run report。

### 1.3 该设计服务后续任务

本设计为以下任务提供架构基础：

- T155：实现 task_monitor.py
- T156：实现 continuous_verifier.py
- T157：实现 execution_report_writer.py
- T158：接入 run-project-loop --real-execution --max-tasks 1
- T159：验证 monitor → verify → report 闭环

### 1.4 当前阶段仍然只能 max_tasks=1

本设计明确：当前 Stage 8 仍然只允许 max_tasks=1 的真实受控单步执行。不允许无限真实连续执行。

---

## 2. Design Goal

### 2.1 核心目标

吸收外部自动维护流水线（monitor → verify → mending → report）的思想，将其转换为 multi-agent-runner 的 Stage 8 模块设计。

### 2.2 明确不做

| # | 不做 | 原因 |
|---|------|------|
| 1 | 不把 multi-agent-runner 改成 Claude Agent SDK 项目 | 保持独立框架 |
| 2 | 不引入新依赖 | 保持零外部依赖 |
| 3 | 不改变当前真实执行安全边界 | 安全优先 |
| 4 | 不实现 mending 自动返工 | 当前阶段不自动返工 |
| 5 | 不实现 API 429 自动恢复 | 当前阶段不自动恢复 |
| 6 | 不实现 run state manager | 当前阶段不需要持久化 state |

### 2.3 核心原则

```text
1. Monitor 只读不写 — 采集状态，不做任何修改
2. Verify 只验证不停复 — 检查结果，不自动修复
3. Report 只记录不推进 — 生成报告，不触发下一步
4. 每个模块可独立测试 — 不依赖其他模块的内部状态
5. 失败即停止 — 验证失败不继续
6. 不自动 commit/push — 始终需要人工确认
```

---

## 3. External Pattern Mapping

### 3.1 映射关系

| # | 外部模式 | 本项目对应 | 实现阶段 | 说明 |
|---|----------|-----------|----------|------|
| 1 | monitor.sh | tools/task_monitor.py | T155 | 执行前状态采集与预检 |
| 2 | state.json | reports/state/ (future) | 不在 T154 实现 | 当前用 checkpoint 替代 |
| 3 | verify.sh | tools/continuous_verifier.py | T156 | 执行后结果验证 |
| 4 | mending-agent.ts | tools/auto_mending_planner.py (future) | 不在 T154 实现 | 当前阶段不自动返工 |
| 5 | report-agent.ts | tools/execution_report_writer.py | T157 | 执行报告统一生成 |

### 3.2 模式转换原则

```text
外部模式的本质是：执行前检查 → 执行后验证 → 失败自动修复 → 报告归档

本项目当前只做前三步的一部分：
  - 执行前检查 → task_monitor.py
  - 执行后验证 → continuous_verifier.py
  - 报告归档 → execution_report_writer.py

跳过的部分（不实现）：
  - 失败自动修复 → 当前阶段不自动返工
  - state.json 持久化 → 当前用 checkpoint 替代
  - resume 自动恢复 → 当前阶段不自动恢复
```

### 3.3 与现有模块的关系

```text
现有 Stage 8 模块：
  tools/continuous_task_planner.py — 包含 dry-run、single-step trial、gate check
  runner.py — CLI 入口

新增 Stage 8 模块（T155-T157）：
  tools/task_monitor.py — 新增，Monitor 功能
  tools/continuous_verifier.py — 新增，Verify 功能
  tools/execution_report_writer.py — 新增，Report 功能

不新增的模块（future）：
  tools/auto_mending_planner.py — future，Mending 功能
  tools/run_state_manager.py — future，State 持久化

关系：
  Monitor 不替代 continuous_task_planner.py 的 gate check
  Verify 不替代 continuous_task_planner.py 的 gate check
  Report 不替代现有的 approval record / checkpoint 生成

它们是 additional layer，不是 replacement。
```

---

## 4. Proposed Stage 8 Flow

### 4.1 当前建议流程

```text
┌─────────────────────────────────────┐
│ 1. TaskMonitor                      │
│   - 读取 docs/tasks.md             │
│   - 识别 NEXT_PENDING              │
│   - 识别 NEXT_STAGE                │
│   - 检查 workspace 状态            │
│   - 检查 checkpoint 状态           │
│   - 输出 TaskMonitorResult         │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│ 2. SafetyGate (G1-G21)              │
│   - 复用 continuous_task_planner    │
│   - 已有 gate check 逻辑           │
│   - 如果失败 → stop                │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│ 3. ControlledRunner                 │
│   - max_tasks=1 single-step trial   │
│   - 复用 continuous_task_planner    │
│   - 当前阶段不真实执行             │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│ 4. ContinuousVerifier               │
│   - 检查任务状态更新               │
│   - 检查报告生成                   │
│   - 检查 CHECK_RESULT              │
│   - 检查 forbidden path            │
│   - 检查 max_tasks 超限            │
│   - 输出 ContinuousVerifyResult    │
│   - 失败 → stop                    │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│ 5. ExecutionReportWriter            │
│   - 生成 reports/continuous-runs/   │
│   - 汇总 monitor 结果              │
│   - 汇总 gate 结果                 │
│   - 汇总 execution 结果            │
│   - 汇总 verify 结果               │
│   - 汇总 final status              │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│ 6. Stop                             │
│   - 当前阶段不自动继续             │
│   - 等待人工确认                   │
└─────────────────────────────────────┘
```

### 4.2 安全约束

| # | 约束 | 说明 |
|---|------|------|
| 1 | 当前阶段仍然 max_tasks=1 | 不允许 max_tasks>1 |
| 2 | 不允许无限真实连续执行 | 完成一个任务后必须 stop |
| 3 | 不允许静默进入下一个真实任务 | 每次推进都需要人工确认 |
| 4 | 不允许自动 commit | 需要人工确认后执行 Txxx.1 |
| 5 | 不允许自动 push | push 始终禁止 |
| 6 | 执行后必须生成报告 | 每轮执行必须有完整报告 |
| 7 | 验证失败必须 stop | Verify 失败不继续 |
| 8 | 不自动进入 Stage 9 | Stage boundary 检查始终生效 |

### 4.3 与现有流程的关系

```text
现有流程（T152-T153 已验证）：
  continuous_task_planner.py → gate check → trial result → approval record → checkpoint

新增流程（T155-T157 设计）：
  task_monitor.py → gate check → controlled runner → continuous_verifier.py → execution_report_writer.py

关系：
  - gate check 复用现有逻辑，不重新实现
  - Monitor 在 gate check 之前运行，提供预检
  - Verifier 在 gate check 之后运行，提供后置验证
  - Report 汇总所有结果

不改变：
  - 不改变 gate check 逻辑
  - 不改变 trial result 结构
  - 不改变 approval record 格式
  - 不改变 checkpoint 格式
```

---

## 5. New Proposed Modules

### 5.1 tools/task_monitor.py

#### 职责

执行前的状态采集与预检。只读不写。

#### 具体功能

| # | 功能 | 输入 | 输出 |
|---|------|------|------|
| 1 | 读取 docs/tasks.md | PROJECT_ROOT | tasks 列表 |
| 2 | 识别 NEXT_PENDING | tasks 列表 | next_pending_task_id |
| 3 | 识别 NEXT_STAGE | tasks 列表 | next_stage |
| 4 | 检查 git worktree 状态 | PROJECT_ROOT | workspace_status (clean/dirty) |
| 5 | 检查 staged files | PROJECT_ROOT | staged_files 列表 |
| 6 | 检查 checkpoint 是否存在 | checkpoint path | checkpoint_exists (bool) |
| 7 | 检查 approval record 是否存在 | approval record path | approval_record_exists (bool) |
| 8 | 检查当前 branch | PROJECT_ROOT | current_branch |
| 9 | 检查 last commit | PROJECT_ROOT | last_commit |

#### 输出结构

```python
@dataclass
class TaskMonitorResult:
    # 基本状态
    project_root: str
    monitor_timestamp: str

    # 任务状态
    next_pending_task_id: str | None
    next_pending_task_title: str | None
    next_pending_task_stage: str | None
    next_pending_task_role: str | None
    next_pending_task_status: str | None

    # 当前任务状态
    current_task_id: str | None
    current_task_status: str | None

    # Workspace 状态
    workspace_status: str  # clean / dirty
    staged_files: list[str]
    current_branch: str
    last_commit: str

    # Checkpoint 状态
    checkpoint_exists: bool
    checkpoint_path: str | None

    # Approval Record 状态
    approval_record_exists: bool
    approval_record_path: str | None

    # Monitor 决策
    monitor_passed: bool
    monitor_issues: list[str]  # 发现的问题列表
    monitor_stop_reason: str | None  # 如果需要停止，停止原因

    # 安全保证
    monitor_modified_files: bool  # 始终 False，Monitor 只读
```

#### 失败策略

```text
Monitor 失败时：
  - monitor_passed = False
  - monitor_issues 列出所有问题
  - monitor_stop_reason 给出停止原因
  - 不修改任何文件
  - 不调用 gate check
  - 不执行任何任务

Monitor 不做：
  - 不修复 dirty workspace
  - 不创建缺失的 checkpoint
  - 不创建缺失的 approval record
  - 不自动推进任务
```

### 5.2 tools/continuous_verifier.py

#### 职责

执行后的结果验证。只验证不修复。

#### 具体功能

| # | 功能 | 输入 | 输出 |
|---|------|------|------|
| 1 | 检查任务状态是否正确更新 | tasks.md, task_id | status_updated_correctly (bool) |
| 2 | 检查报告是否生成 | reports/ dir, task_id | report_exists (bool) |
| 3 | 检查 CHECK_RESULT 是否存在且为 pass | report file | check_result_pass (bool) |
| 4 | 检查是否执行超过 max_tasks=1 | max_tasks, tasks_attempted | within_limit (bool) |
| 5 | 检查是否误进入下一任务 | tasks.md | no_unauthorized_advance (bool) |
| 6 | 检查 forbidden path 修改 | git diff, forbidden_paths | no_forbidden_changes (bool) |
| 7 | 检查 unclassified changes | git diff, expected_paths | no_unclassified_changes (bool) |
| 8 | 检查 workspace 状态一致性 | workspace before/after | workspace_consistent (bool) |
| 9 | 检查 approval record 完整性 | approval record file | approval_record_complete (bool) |
| 10 | 检查 checkpoint 一致性 | checkpoint file | checkpoint_consistent (bool) |

#### 输出结构

```python
@dataclass
class ContinuousVerifyResult:
    # 基本信息
    project_root: str
    verify_timestamp: str
    task_id: str
    max_tasks: int

    # 验证项
    status_updated_correctly: bool
    report_exists: bool
    check_result_pass: bool
    within_max_tasks_limit: bool
    no_unauthorized_advance: bool
    no_forbidden_path_changes: bool
    no_unclassified_changes: bool
    workspace_consistent: bool
    approval_record_complete: bool
    checkpoint_consistent: bool

    # 验证汇总
    verify_passed: bool
    verify_passed_count: int
    verify_failed_count: int
    verify_issues: list[str]  # 所有失败项的描述

    # 失败时停止
    verify_stop_reason: str | None

    # 安全保证
    verifier_modified_files: bool  # 始终 False，Verifier 只读
```

#### 失败策略

```text
Verifier 失败时：
  - verify_passed = False
  - verify_issues 列出所有失败项
  - verify_stop_reason 给出停止原因
  - 不修复任何问题
  - 不自动返工
  - 不继续推进下一任务
  - 不自动 commit / push

Verifier 不做：
  - 不修复任务状态
  - 不生成缺失的报告
  - 不修改 CHECK_RESULT
  - 不回滚变更
  - 不自动返工
```

#### Forbidden Paths

```text
forbidden_paths（Verifier 必须检查的路径）：
  - .env
  - .git/
  - credentials*
  - *.key
  - *.pem
  - node_modules/
  - __pycache__/

如果 Verifier 发现这些路径有变更，必须 fail closed。
```

### 5.3 tools/execution_report_writer.py

#### 职责

统一生成每轮执行的汇总报告。只记录不推进。

#### 具体功能

| # | 功能 | 输入 | 输出 |
|---|------|------|------|
| 1 | 生成 reports/continuous-runs/Txxx-run-report.md | 所有模块结果 | 报告文件 |
| 2 | 汇总 Monitor 结果 | TaskMonitorResult | monitor_summary |
| 3 | 汇总 Safety Gate 结果 | gate result | safety_gate_summary |
| 4 | 汇总 Execution 结果 | trial result | execution_summary |
| 5 | 汇总 Verify 结果 | ContinuousVerifyResult | verify_summary |
| 6 | 记录 Rework Decision | rework status | rework_decision |
| 7 | 记录 Git Decision | git status | git_decision |
| 8 | 记录 Final Status | all results | final_status |

#### 输出结构

生成 `reports/continuous-runs/Txxx-run-report.md`，格式见第 7 节。

#### 失败策略

```text
Report Writer 失败时：
  - 尝试生成最小报告（至少包含 task_id、timestamp、failure_reason）
  - 不自动 commit / push
  - 不自动推进

Report Writer 不做：
  - 不调用 gate check
  - 不执行任务
  - 不修改 docs/tasks.md
  - 不修改任何其他文件
```

### 5.4 future tools/auto_mending_planner.py

本模块是未来模块，不在 T154 实现。

#### 未来职责

1. 根据 verifier 失败原因判断是否可自动返工
2. 对低风险问题（报告缺失、格式错误）生成返工计划
3. 对高风险问题（dirty workspace、forbidden path、unclassified changes）停止等待人工确认
4. 返工计划包含：返工任务 ID、返工原因、允许修改的文件范围、返工验证标准

#### 当前阶段不实现的原因

```text
1. 自动返工需要成熟的 verify 闭环
2. 当前 Stage 8 只允许 max_tasks=1，不适合自动返工
3. 返工可能引入新的问题，需要更完善的安全网
4. 当前阶段由人工判断是否返工更安全
```

### 5.5 future tools/run_state_manager.py

本模块是未来模块，不在 T154 实现。

#### 未来职责

1. 维护 reports/state/run-state.json
2. 维护 reports/state/checkpoint.json
3. 支持 API 429 / 5 小时限制后的 checkpoint resume
4. 判断 resume_allowed
5. 保护 dirty workspace

#### 当前阶段不实现的原因

```text
1. 当前用 checkpoint 文件（YAML/Markdown）已足够
2. resume 自动恢复需要更完善的状态持久化
3. API 429 恢复需要 rate limit 检测和自动等待
4. 当前阶段由人工判断是否恢复更安全
```

---

## 6. Safety Rules

### 6.1 核心安全规则

| # | 规则 | 适用模块 | 说明 |
|---|------|----------|------|
| 1 | dirty workspace must stop | Monitor, Verifier | workspace 不 clean 时不继续 |
| 2 | unclassified changes must stop | Verifier | 检测到未分类变更时停止 |
| 3 | forbidden paths must fail closed | Verifier | 检测到 forbidden path 变更时 fail closed |
| 4 | missing report must fail verification | Verifier | 报告缺失时验证失败 |
| 5 | missing CHECK_RESULT must fail verification | Verifier | CHECK_RESULT 缺失时验证失败 |
| 6 | real execution must stay max_tasks=1 | Monitor, Verifier, Runner | 当前阶段最多 1 个任务 |
| 7 | no auto git commit | 所有模块 | 除非 explicit git backup gate passes |
| 8 | no auto git push | 所有模块 | 除非 explicit git backup gate passes |
| 9 | no silent continuation after failure | Verifier | 验证失败后不静默继续 |
| 10 | no automatic transition to Stage 9 | Monitor, Verifier | 不允许自动跨阶段 |
| 11 | no Claude Agent SDK integration | 所有模块 | 当前阶段不接入 SDK |
| 12 | no new dependency | 所有模块 | 不引入新依赖 |

### 6.2 模块级安全约束

```text
task_monitor.py:
  - 只读不写（monitor_modified_files 始终 False）
  - 不调用 gate check
  - 不执行任务
  - 不修改 docs/tasks.md

continuous_verifier.py:
  - 只读不写（verifier_modified_files 始终 False）
  - 不修复问题
  - 不自动返工
  - 不修改任何文件

execution_report_writer.py:
  - 只写报告文件
  - 不修改 docs/tasks.md
  - 不调用 gate check
  - 不执行任务
  - 不自动 commit / push
```

### 6.3 数据流安全

```text
数据流方向：
  docs/tasks.md → task_monitor.py (只读)
  git status → task_monitor.py (只读)
  checkpoint → task_monitor.py (只读)

  gate result → continuous_verifier.py (只读)
  trial result → continuous_verifier.py (只读)
  report file → continuous_verifier.py (只读)

  monitor result → execution_report_writer.py (只读)
  gate result → execution_report_writer.py (只读)
  verify result → execution_report_writer.py (只读)

  execution_report_writer.py → reports/continuous-runs/ (只写)

不允许反向数据流：
  不允许 report writer 修改 monitor result
  不允许 verifier 修改 gate result
  不允许 monitor 修改 docs/tasks.md
```

---

## 7. Report Format

### 7.1 reports/continuous-runs/Txxx-run-report.md 模板

```markdown
# Run Report: Txxx

## Task Info

| 字段 | 值 |
|------|-----|
| TASK | Txxx |
| RUN_TIMESTAMP | YYYY-MM-DDTHH:MM:SS |
| MAX_TASKS | 1 |
| STAGE | Stage 8 |
| MODE | real_controlled_single_step |
| PROJECT_ROOT | E:/github_project/multi-agent-runner |

## Monitor Result

| 字段 | 值 |
|------|-----|
| MONITOR_PASSED | true/false |
| NEXT_PENDING_TASK_ID | Txxx |
| NEXT_PENDING_TASK_STAGE | Stage 8 |
| WORKSPACE_STATUS | clean/dirty |
| STAGED_FILES | [] |
| CURRENT_BRANCH | main |
| LAST_COMMIT | xxxxxx ... |
| CHECKPOINT_EXISTS | true/false |
| APPROVAL_RECORD_EXISTS | true/false |
| MONITOR_ISSUES | [] |
| MONITOR_STOP_REASON | null/... |

## Safety Gate Result

| 字段 | 值 |
|------|-----|
| GATE_PASSED | true/false |
| SAFETY_GATE_PASSED | N |
| SAFETY_GATE_FAILED | N |
| EXECUTION_GATE_PASSED | N |
| EXECUTION_GATE_FAILED | N |
| STOP_REASON | null/... |
| FAILURE_REASONS | [] |

## Execution Result

| 字段 | 值 |
|------|-----|
| TRIAL_ALLOWED | true/false |
| TRIAL_DECISION | trial_proceed/trial_blocked |
| NEXT_TASK_EXECUTED | false |
| BUSINESS_CODE_MODIFIED | false |
| TASKS_ATTEMPTED | N |
| TASKS_COMPLETED | N |
| PUSH_ALLOWED | false |
| RESUME_ALLOWED | false |
| REAL_GIT_ADD_USED | false |
| REAL_GIT_COMMIT_USED | false |
| REAL_GIT_PUSH_USED | false |

## Verify Result

| 字段 | 值 |
|------|-----|
| VERIFY_PASSED | true/false |
| STATUS_UPDATED_CORRECTLY | true/false |
| REPORT_EXISTS | true/false |
| CHECK_RESULT_PASS | true/false |
| WITHIN_MAX_TASKS_LIMIT | true/false |
| NO_UNAUTHORIZED_ADVANCE | true/false |
| NO_FORBIDDEN_PATH_CHANGES | true/false |
| NO_UNCLASSIFIED_CHANGES | true/false |
| WORKSPACE_CONSISTENT | true/false |
| APPROVAL_RECORD_COMPLETE | true/false |
| CHECKPOINT_CONSISTENT | true/false |
| VERIFY_ISSUES | [] |
| VERIFY_STOP_REASON | null/... |

## Rework Decision

| 字段 | 值 |
|------|-----|
| REWORK_REQUIRED | false |
| REWORK_REASON | null |
| REWORK_PLAN | null |
| AUTO_MENDING_TRIGGERED | false |

## Git Decision

| 字段 | 值 |
|------|-----|
| GIT_BACKUP_REQUIRED | true/false |
| GIT_COMMIT_DECISION | pending/manual |
| GIT_PUSH_DECISION | blocked |
| WORKSPACE_STATUS_BEFORE | clean |
| WORKSPACE_STATUS_AFTER | clean |

## Final Status

| 字段 | 值 |
|------|-----|
| RUN_STATUS | completed/blocked/failed |
| OVERALL_CHECK_RESULT | pass/fail |
| NEXT_PENDING | Txxx |
| NEXT_STAGE | Stage 8 |
| NOTES | ... |
```

### 7.2 报告文件路径规则

```text
reports/continuous-runs/Txxx-run-report.md

其中 Txxx 是任务编号。

例如：
  reports/continuous-runs/T154-run-report.md
  reports/continuous-runs/T155-run-report.md
```

### 7.3 报告生成时机

```text
报告在以下时机生成：
  1. 每轮执行完成后（无论 pass 还是 fail）
  2. Monitor 失败时也生成（包含 monitor 失败信息）
  3. Verifier 失败时也生成（包含 verify 失败信息）

报告不在以下时机生成：
  - 不在执行前生成
  - 不在 gate check 中间生成
  - 不自动触发下一轮执行
```

---

## 8. Suggested Next Tasks

### 8.1 任务链

| 任务 | 角色 | 目标 | 依赖 |
|------|------|------|------|
| T155 | Developer | 实现 task_monitor.py | T154 |
| T156 | Developer | 实现 continuous_verifier.py | T154 |
| T157 | Developer | 实现 execution_report_writer.py | T154 |
| T158 | Developer | 接入 run-project-loop --real-execution --max-tasks 1 | T155, T156, T157 |
| T159 | Validator | 验证 monitor → verify → report 闭环 | T158 |

### 8.2 任务详情

#### T155：实现 task_monitor.py

目标：实现执行前状态采集模块。

具体内容：
1. 实现 `run_task_monitor(project_root)` 函数
2. 读取 docs/tasks.md，识别 NEXT_PENDING、NEXT_STAGE
3. 检查 git worktree 状态、staged files、current branch、last commit
4. 检查 checkpoint 是否存在
5. 检查 approval record 是否存在
6. 输出 TaskMonitorResult
7. dirty workspace 时 fail closed
8. 不修改任何文件

#### T156：实现 continuous_verifier.py

目标：实现执行后结果验证模块。

具体内容：
1. 实现 `run_continuous_verify(project_root, task_id, max_tasks)` 函数
2. 检查任务状态是否正确更新
3. 检查报告是否生成且 CHECK_RESULT 为 pass
4. 检查 max_tasks 限制
5. 检查 forbidden path
6. 检查 unclassified changes
7. 输出 ContinuousVerifyResult
8. 验证失败时 fail closed，不自动修复

#### T157：实现 execution_report_writer.py

目标：实现执行报告统一生成模块。

具体内容：
1. 实现 `write_run_report(project_root, task_id, monitor_result, gate_result, execution_result, verify_result)` 函数
2. 按 Section 7 定义的模板生成报告
3. 汇总所有模块结果
4. 生成 reports/continuous-runs/Txxx-run-report.md
5. 只写报告文件，不修改其他文件

#### T158：接入 run-project-loop --real-execution --max-tasks 1

目标：将 Monitor → Gate → Runner → Verifier → Report 串联接入 runner.py CLI。

具体内容：
1. 在 runner.py 新增 CLI 入口
2. 调用 task_monitor → gate → runner → verifier → report 的完整流程
3. max_tasks=1 强制执行
4. 不自动 commit / push
5. 验证失败时 stop

#### T159：验证 monitor → verify → report 闭环

目标：验证 T155-T158 实现的完整闭环。

具体内容：
1. 验证 Monitor 正确采集状态
2. 验证 Verifier 正确验证结果
3. 验证 Report 正确生成报告
4. 验证完整闭环 pass/fail 场景
5. 验证安全约束（不 commit、不 push、不跨阶段）

### 8.3 任务边界

```text
T155-T157 可以并行开发（模块独立）
T158 依赖 T155 + T156 + T157 全部完成
T159 依赖 T158 完成

不允许：
  - T155 修改 continuous_task_planner.py
  - T156 修改 continuous_task_planner.py
  - T157 修改 docs/tasks.md
  - T158 修改业务代码
  - T159 执行真实任务推进
```

---

## 9. Non-goals

本阶段明确不做以下事项：

| # | 不做 | 原因 |
|---|------|------|
| 1 | 不接入 Claude Agent SDK | 保持独立框架 |
| 2 | 不实现无限真实连续执行 | 当前只允许 max_tasks=1 |
| 3 | 不实现自动 Git commit | 需要人工确认 |
| 4 | 不实现自动 Git push | 始终禁止 |
| 5 | 不实现 API 429 自动恢复 | 当前阶段不自动恢复 |
| 6 | 不实现 mending 自动返工 | 当前阶段不自动返工 |
| 7 | 不修改业务代码 | 本阶段只做框架扩展 |
| 8 | 不修改 runner.py | T154 只做设计，不实现 |
| 9 | 不修改 tools/ | T154 只做设计，不实现 |
| 10 | 不引入新依赖 | 保持零外部依赖 |

---

## 设计元数据

- 设计角色：Architect Agent + Stage 8 Safety Workflow Architect
- 设计日期：2026-05-11
- 设计基准提交：5272e8b test: validate stage 8 max tasks one controlled trial
- 前置条件：T153 done, T153.1 committed and pushed
- 设计结论：T154_MONITOR_VERIFY_REPORT_DESIGN_COMPLETE=yes
- 下一步：T155（实现 task_monitor.py）

```text
T154 设计状态验证：
  STAGE8_MONITOR_VERIFY_REPORT_DESIGN=yes
  TASK_MONITOR_DESKIPPED=no
  CONTINUOUS_VERIFIER_DESKIPPED=no
  EXECUTION_REPORT_WRITER_DESKIPPED=no
  AUTO_MENDING_PLANNER_DESKIPPED=yes  (future, not T154)
  RUN_STATE_MANAGER_DESKIPPED=yes  (future, not T154)
  CLAUDE_AGENT_SDK_INTEGRATED=no
  MAX_TASKS_EXCEEDED_1=no
  REAL_CONTINUOUS_EXECUTION_STARTED=no
  AUTO_COMMIT_TRIGGERED=no
  AUTO_PUSH_TRIGGERED=no
  STAGE9_ENTERED=no
  BUSINESS_CODE_MODIFIED=no
```
