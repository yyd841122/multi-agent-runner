# Stage 10 Real Rework Loop Plan

规划时间：2026-05-12
规划角色：Architect Agent + Stage 10 Rework Loop Planning Architect
规划范围：真实返工闭环接入入口
前置条件：T173 done, T173.1 committed and pushed, Stage 9 dry-run 安全链完成

---

## 1. Background

Stage 10 建立在 Stage 8 和 Stage 9 的安全基础之上。

### 1.1 Stage 8 已完成能力

| # | 能力 | 说明 |
|---|------|------|
| 1 | task_monitor.py | 执行前读取 tasks.md，检查 NEXT_PENDING / NEXT_STAGE、worktree 状态 |
| 2 | continuous_verifier.py | 执行后验证任务状态更新、报告生成、CHECK_RESULT、安全边界 |
| 3 | execution_report_writer.py | 生成 reports/continuous-runs/Txxx-run-report.md |
| 4 | stage8-monitor-verify-report 子命令 | Monitor → Trial → Verifier → Report Writer 完整 pipeline |
| 5 | max_tasks=1 受控路径 | 单步受控执行，T163 验证通过 |
| 6 | max_tasks>1 fail closed | 入口强制 max_tasks==1，T163 验证通过 |
| 7 | no auto git add/commit/push | runner.py 中不存在真实 git 操作 |
| 8 | no unlimited continuation | NEXT_ACTION 始终为 stop |

### 1.2 Stage 9 已完成能力

| # | 能力 | 说明 |
|---|------|------|
| 1 | GitBackupGate dry-run | 文件分类（allowed / forbidden / unclassified），fail closed |
| 2 | approval record 生成 | 10 个章节，记录 gate 结果、变更文件、git 命令草案 |
| 3 | guarded git backup dry-run | 接入 run-project-loop，Step 5 集成到 runner.py |
| 4 | max_tasks=1 受控边界 | run-project-loop --max-tasks 1 dry-run 通过 |
| 5 | max_tasks>1 fail closed | run-project-loop --max-tasks 2 fail closed |

### 1.3 已有返工基础设施

| # | 模块 | 说明 |
|---|------|------|
| 1 | tools/rework_manager.py | 821 行，完整的返工管理：ReworkContext、prompt 生成、确认校验、执行检查、full loop resume |
| 2 | docs/rework-protocol.md | 返工协议：触发条件、输入来源、命名规则 |
| 3 | docs/rework-execution-confirmation-protocol.md | 严格确认协议：ReworkExecutionCheckResult、模糊确认黑名单 |
| 4 | docs/full-loop-resume-design.md | 完整循环恢复设计：resume 状态模型 |
| 5 | templates/rework/ | 3 个模板：rework-task、rework-prompt、rework-execution-confirmation |

### 1.4 当前限制

| # | 限制 | 说明 |
|---|------|------|
| 1 | 仍未开放无限真实连续执行 | max_tasks=1 限制 |
| 2 | 仍未开放真实自动 git add/commit/push | dry-run only |
| 3 | verifier 失败后无法自动生成返工计划 | 缺少 auto_mending_planner |
| 4 | rework_manager.py 面向子项目 game | 主框架连续执行链路尚未接入 |
| 5 | 缺少 verifier fail → rework decision 桥接 | continuous_verifier 输出与 rework_manager 输入未对接 |
| 6 | 缺少返工后二次 verify → report → git backup 链路 | 返工闭环不完整 |
| 7 | 仍未实现 API 429 / 5 小时限额自动恢复 | 属于未来范围 |

---

## 2. Stage 10 Goal

Stage 10 的核心目标是：**让验证失败后能够生成受控返工计划**。

具体目标：

1. **verifier 失败后生成返工判断**：continuous_verifier 输出 fail 时，自动生成 ReworkDecision。
2. **区分可自动返工和必须人工确认**：基于 failure_type 和 risk_level 分类。
3. **生成 rework plan**：输出结构化的返工计划（目标文件、修复方向、限制范围）。
4. **调用 auto_mending_planner**：新增模块，输入 verifier result，输出 ReworkDecision 和 rework plan。
5. **返工后再次 verify**：返工执行后重新走 continuous_verifier。
6. **返工后再次 report**：返工后重新生成 execution_report。
7. **返工后经过 GitBackupGate dry-run**：保持 Stage 9 安全链。
8. **所有失败必须 fail closed**：任何不确定状态都停止，不自动修复。

### 2.1 Stage 10 不做的事

1. 不开放无限真实连续执行。
2. 不跳过人工验收。
3. 不绕过 verifier。
4. 不绕过 GitBackupGate。
5. 不自动提交未分类变更。

---

## 3. Non-goals

明确本阶段不做：

1. 不开放无限真实连续执行。
2. 不跳过人工验收。
3. 不绕过 verifier。
4. 不绕过 GitBackupGate。
5. 不自动提交未分类变更。
6. 不处理 API 429 / 5 小时限额自动恢复。
7. 不直接实现 run_state_manager.py。
8. 不直接实现真实多轮自动返工。
9. 不接入外部入口。
10. 不进入 Stage 11。

---

## 3.1 Agent Role Protocol Remediation

### 3.1.1 问题发现

在 T174 完成后的检查中发现：`agents/*.md` 文件仍停留在早期占位状态，每个文件仅约 10 行简单描述。这不是 runner/tools/reports 执行框架的错误，而是 Agent 角色协议层的缺失。

当前 agents/*.md 缺少以下关键内容：

| # | 缺失项 | 说明 |
|---|--------|------|
| 1 | 角色定位 | 只有笼统描述，缺少精确边界 |
| 2 | 核心职责 | 只有一句话，缺少具体职责清单 |
| 3 | 禁止事项 | 完全缺失 |
| 4 | 输入格式 | 完全缺失 |
| 5 | 输出格式 | 完全缺失 |
| 6 | 可修改文件范围 | 完全缺失 |
| 7 | 不可修改文件范围 | 完全缺失 |
| 8 | 与其他 Agent 的交接关系 | 完全缺失 |
| 9 | Git 操作限制 | 完全缺失 |
| 10 | 失败报告规范 | 完全缺失 |

### 3.1.2 影响分析

如果不补强 Agent 角色协议层，后续系统会变成：
- **脚本自动化**：只有 runner/tools 执行管道，没有真正的多 Agent 协作语义。
- **角色边界模糊**：Developer 可能越权修改 runner.py，Tester 可能不知道该检查什么。
- **交接不明确**：Planner 输出的任务拆解格式不固定，Developer 无法可靠解析。
- **返工无依据**：auto_mending_planner 无法根据角色边界判断返工是否安全。

### 3.1.3 补救方案

Stage 10 必须优先补强 Agent Role Protocol Layer，包括：

| # | 文件 | 说明 |
|---|------|------|
| 1 | agents/main_agent.md | 调度与决策中心：接收需求、分配任务、协调子 Agent、最终验收 |
| 2 | agents/planner_agent.md | 计划与任务拆解：将需求拆解为可执行子任务、确定依赖关系 |
| 3 | agents/developer_agent.md | 开发实现：按计划生成代码、遵循文件范围限制 |
| 4 | agents/tester_agent.md | 测试验证：运行测试用例、检查输出、生成测试报告 |
| 5 | agents/reviewer_agent.md | 审查评估：代码审查、需求符合度检查、问题与改进建议 |
| 6 | agents/reporter_agent.md | 报告汇总：汇总执行结果、生成最终报告、供用户验收 |
| 7 | docs/agent-role-protocol.md | Agent 角色协议总纲：统一规范、交接格式、安全边界 |

### 3.1.4 任务顺序调整

基于以上分析，Stage 10 后续任务顺序调整为：

1. **T175**：完善 agents/*.md 角色职责、边界与输出规范（优先）
2. **T176**：验证 Agent 角色规范覆盖主流程
3. T177-T184：auto_mending_planner 及后续返工闭环任务（顺延）

auto_mending_planner.py 的设计和实现应在 Agent 角色协议层补强之后进行，因为 auto_mending_planner 的返工决策需要依赖明确的角色边界来判断返工是否安全。

---

## 4. Proposed Rework Loop

### 4.1 完整流程

```text
Task execution
  → monitor (task_monitor.py)
  → controlled execution (runner.py, max_tasks=1)
  → report (execution_report_writer.py)
  → verifier (continuous_verifier.py)
  → if pass: GitBackupGate dry-run → stop for user approval
  → if fail: ReworkDecision (auto_mending_planner.py)
  → rework safety gate (auto_mending_planner.py)
  → rework plan (auto_mending_planner.py)
  → controlled rework execution (runner.py, max_tasks=1)
  → second verify (continuous_verifier.py)
  → second report (execution_report_writer.py)
  → GitBackupGate dry-run
  → stop for user approval
```

### 4.2 流程节点说明

| # | 节点 | 模块 | 输入 | 输出 |
|---|------|------|------|------|
| 1 | Task execution | runner.py | task prompt | 执行结果 |
| 2 | Monitor | task_monitor.py | tasks.md | MONITOR_RESULT |
| 3 | Controlled execution | runner.py | max_tasks=1 | 执行输出 |
| 4 | Report | execution_report_writer.py | verifier result | run report |
| 5 | Verifier | continuous_verifier.py | tasks.md, reports | VERIFY_RESULT |
| 6 | ReworkDecision | auto_mending_planner.py | verifier result, failure_type | ReworkDecision |
| 7 | Rework safety gate | auto_mending_planner.py | ReworkDecision | pass / fail |
| 8 | Rework plan | auto_mending_planner.py | ReworkDecision | rework plan |
| 9 | Controlled rework execution | runner.py | rework prompt, max_tasks=1 | 执行输出 |
| 10 | Second verify | continuous_verifier.py | tasks.md, reports | VERIFY_RESULT |
| 11 | Second report | execution_report_writer.py | verifier result | run report |
| 12 | GitBackupGate dry-run | git_backup_gate.py | changed files | approval record |
| 13 | Stop for user approval | — | approval record | 用户确认 |

### 4.3 返工闭环最大轮次

- 最大返工轮次：3（与 rework_manager.py MAX_REWORK_ROUNDS 一致）
- 超过 3 轮后生成人工介入报告，停止自动返工
- 每轮返工都必须经过完整的 verify → report → git backup dry-run 链路

---

## 5. ReworkDecision Data Structure

### 5.1 dataclass 草案

```python
@dataclass
class ReworkDecision:
    """返工决策 — 由 auto_mending_planner.py 生成。"""

    # 基础信息
    ok: bool                          # 决策是否成功生成
    task_id: str                      # 当前任务编号
    verify_status: str                # verifier 结果：pass / fail

    # 失败分类
    failure_type: str | None          # 失败类型（见 Section 6）
    rework_allowed: bool              # 是否允许返工
    auto_rework_allowed: bool         # 是否允许自动返工（无需人工确认）
    user_approval_required: bool      # 是否需要人工确认

    # 返工范围
    rework_reason: str                # 返工原因摘要
    target_files: list[str]           # 需要修改的文件列表
    forbidden_files: list[str]        # 禁止修改的文件列表
    risk_level: str                   # 风险等级：low / medium / high / critical

    # 返工轮次控制
    max_rework_rounds: int            # 最大返工轮次（默认 3）
    current_rework_round: int         # 当前返工轮次（0-based，0=首次执行）

    # 结果
    next_action: str                  # 下一步：auto_rework / manual_rework / stop
    fail_reason: str | None           # 决策失败原因（ok=False 时）
```

### 5.2 字段取值范围

| 字段 | 有效值 |
|------|--------|
| verify_status | pass, fail |
| failure_type | report_missing, check_result_failed, verifier_failed, tests_failed, syntax_failed, forbidden_file_changed, unclassified_changes, dirty_workspace, max_tasks_violation, rate_limit_or_api_429, unknown_failure |
| risk_level | low, medium, high, critical |
| next_action | auto_rework, manual_rework, stop |

---

## 6. Failure Classification Rules

### 6.1 失败类型定义

| # | failure_type | 说明 | 可自动返工 | 人工确认 |
|---|-------------|------|-----------|---------|
| 1 | report_missing | 执行后未生成报告 | yes | no |
| 2 | check_result_failed | 报告中 CHECK_RESULT != pass | yes | no |
| 3 | verifier_failed | continuous_verifier 返回 fail | conditional | conditional |
| 4 | tests_failed | 测试未通过 | yes | no |
| 5 | syntax_failed | py_compile 或语法检查失败 | yes | no |
| 6 | forbidden_file_changed | 修改了禁止文件 | no | yes |
| 7 | unclassified_changes | 修改了未分类文件 | no | yes |
| 8 | dirty_workspace | 工作区有未提交变更 | no | yes |
| 9 | max_tasks_violation | max_tasks != 1 | no | yes |
| 10 | rate_limit_or_api_429 | API 限流 | no | yes |
| 11 | unknown_failure | 未知失败类型 | no | yes |

### 6.2 自动返工判断规则

可自动返工的条件（全部满足）：

1. failure_type 在可自动返工列表中（1-5）。
2. target_files 不包含 runner.py、tools/ 目录下的文件。
3. risk_level 不是 critical。
4. current_rework_round < max_rework_rounds。
5. dirty_workspace == False（工作区已分类）。
6. forbidden_files 为空。
7. unclassified_changes 为空。

必须人工确认的条件（任一满足）：

1. failure_type 在 6-11 中。
2. target_files 包含 runner.py 或 tools/ 下的文件（除非任务明确允许）。
3. risk_level == critical。
4. current_rework_round >= max_rework_rounds。
5. forbidden_files 非空。
6. unclassified_changes 非空。

### 6.3 返工优先级

| 优先级 | failure_type | 返工策略 |
|--------|-------------|---------|
| P0 | rate_limit_or_api_429 | 停止，等待限额恢复 |
| P1 | forbidden_file_changed | 停止，人工确认 |
| P1 | unclassified_changes | 停止，人工确认 |
| P1 | max_tasks_violation | 停止，修正参数 |
| P2 | dirty_workspace | 停止，清理工作区 |
| P3 | syntax_failed | 自动返工（修复语法） |
| P3 | tests_failed | 自动返工（修复测试） |
| P3 | report_missing | 自动返工（补充报告） |
| P4 | check_result_failed | 自动返工（修正结果） |
| P4 | verifier_failed | 条件返工（根据 fail_reason 判断） |
| P5 | unknown_failure | 停止，人工确认 |

---

## 7. Rework Safety Gate

### 7.1 安全门规则

返工执行前必须通过以下全部检查：

| # | 检查项 | 条件 | 失败动作 |
|---|--------|------|---------|
| 1 | forbidden files | forbidden_files 一律 fail closed | 停止，生成人工介入报告 |
| 2 | unclassified files | unclassified files 一律 fail closed | 停止，生成人工介入报告 |
| 3 | dirty workspace | 工作区未分类变更一律 fail closed | 停止，要求清理 |
| 4 | max rework rounds | current_rework_round >= max_rework_rounds 时停止 | 停止，生成人工介入报告 |
| 5 | missing failure_type | failure_type 为空时停止 | 停止，无法判断返工方向 |
| 6 | missing target_files | target_files 为空时停止 | 停止，无法确定返工范围 |
| 7 | runner.py / tools/ | 涉及这些文件时要求人工确认 | 除非任务明确允许 |
| 8 | allowed scope | 业务代码修改受 allowed scope 限制 | 超出范围时停止 |
| 9 | no auto git add/commit/push | 返工不能自动 git add/commit/push | 始终 dry-run |
| 10 | post-rework verify | 返工后必须再次 verify | 未通过时继续返工或停止 |

### 7.2 安全门检查流程

```text
ReworkDecision 输入
  → 检查 forbidden_files（非空 → fail closed）
  → 检查 unclassified_changes（非空 → fail closed）
  → 检查 dirty_workspace（是 → fail closed）
  → 检查 max_rework_rounds（超限 → fail closed）
  → 检查 failure_type（空 → fail closed）
  → 检查 target_files（空 → fail closed）
  → 检查 runner.py / tools/ 涉及（是 → user_approval_required）
  → 检查 allowed scope（超出 → fail closed）
  → 通过 → 允许返工
```

### 7.3 返工后安全保证

返工完成后，必须经过以下链路：

1. **continuous_verifier** — 再次验证任务状态、报告、安全边界。
2. **execution_report_writer** — 生成返工后的执行报告。
3. **GitBackupGate dry-run** — 分类返工变更文件，生成 approval record。
4. **stop for user approval** — 始终等待用户确认，不自动进入下一任务。

---

## 8. auto_mending_planner.py Scope

### 8.1 模块定位

`tools/auto_mending_planner.py` 是 Stage 10 的核心新增模块，负责：

1. 接收 continuous_verifier 的失败结果。
2. 分类失败类型。
3. 生成 ReworkDecision。
4. 生成 rework plan 草案。
5. 输出返工安全门检查结果。

### 8.2 T177 dry-run 范围

T177 只做 dry-run，不实现真实返工：

1. 输入 verifier result（ContinuousVerificationResult）。
2. 输入 failure_type（从 fail_reason 解析或手动指定）。
3. 输入 changed files（从 git status 获取）。
4. 输出 ReworkDecision（dataclass）。
5. 输出 rework plan 草案（markdown）。
6. 不修改文件。
7. 不执行返工。
8. 不调用真实模型。
9. 不调用 Claude Agent SDK。
10. fail closed。

### 8.3 auto_mending_planner.py 与 rework_manager.py 的关系

| 对比项 | auto_mending_planner.py | rework_manager.py |
|--------|------------------------|-------------------|
| 定位 | 主框架连续执行链路的返工决策 | 子项目 game 的返工 prompt 生成 |
| 输入 | ContinuousVerificationResult | game 项目 reports |
| 输出 | ReworkDecision + rework plan | rework prompt + execution check |
| 安全门 | 内置 rework safety gate | 复用 execute_confirmed_rework |
| 轮次控制 | max_rework_rounds=3 | MAX_REWORK_ROUNDS=3 |

auto_mending_planner.py 是面向主框架连续执行链路的新模块，不替代 rework_manager.py。两者并行存在，各自服务于不同的执行路径。

### 8.4 后续可实现能力

| # | 能力 | 任务 |
|---|------|------|
| 1 | auto_mending_planner dry-run | T178 |
| 2 | fail closed 验证 | T179 |
| 3 | verifier fail → rework decision 接入 | T180 |
| 4 | verifier fail 后生成 rework decision 验证 | T181 |
| 5 | rework_manager 受控返工 dry-run 接入 | T182 |
| 6 | 返工后 verify → report → git backup dry-run 链路验证 | T183 |

---

## 9. Integration Points

### 9.1 continuous_verifier.py 输出桥接

continuous_verifier.py 输出 `ContinuousVerificationResult`，包含：
- `ok: bool`
- `fail_reason: str | None`
- 各检查项的 bool 结果

auto_mending_planner.py 将接收此结果，解析 fail_reason，分类 failure_type，生成 ReworkDecision。

### 9.2 execution_report_writer.py 记录返工决策

返工决策应记录在 execution report 中：
- 新增 `REWORK_DECISION` 字段。
- 新增 `REWORK_ALLOWED` 字段。
- 新增 `REWORK_REASON` 字段。

### 9.3 runner.py 接入方式

在 runner.py 的 stage8-monitor-verify-report 子命令中：
- Step 4 Verifier fail 后，新增 Step 4.1 调用 auto_mending_planner dry-run。
- Step 4.1 输出 ReworkDecision。
- 根据 next_action 决定是否进入 Step 5 或停止。

### 9.4 GitBackupGate 返工后 dry-run

返工执行后，GitBackupGate Step 5 仍然执行 dry-run：
- 分类返工变更文件。
- 生成 approval record。
- 不自动 git add/commit/push。

### 9.5 reports/rework/ 返工记录

主项目新增 `reports/rework/` 目录，保存返工记录：
- `reports/rework/Txxx-rework-decision-R{n}.md` — 返工决策。
- `reports/rework/Txxx-rework-plan-R{n}.md` — 返工计划。
- `reports/rework/Txxx-rework-result-R{n}.md` — 返工结果。

---

## 10. Suggested Stage 10 Tasks

| # | 任务 | 角色 | 目标 |
|---|------|------|------|
| T175 | Architect | 完善 agents/*.md 角色职责、边界与输出规范 | 为每个 Agent 补充完整角色定义：核心职责、禁止事项、输入输出格式、文件范围、交接关系、Git 限制、失败报告规范 |
| T176 | Validator | 验证 Agent 角色规范覆盖主流程 | 确认 agents/*.md 覆盖 monitor → verify → report → git backup → rework 主流程 |
| T177 | Architect | 设计 auto_mending_planner.py dry-run 数据结构 | 设计 ReworkDecision dataclass、failure classification rules、rework safety gate rules |
| T178 | Developer | 实现 auto_mending_planner.py dry-run | 实现 classify_failure、generate_rework_decision、check_rework_safety_gate |
| T179 | Validator | 验证 auto_mending_planner fail closed | 验证所有 fail-closed 场景 |
| T180 | Developer | 接入 verifier fail → rework decision dry-run | 在 runner.py 中接入 auto_mending_planner dry-run |
| T181 | Validator | 验证 verifier fail 后生成 rework decision | 端到端验证 verifier fail → rework decision 生成 |
| T182 | Developer | 接入 rework_manager 受控返工 dry-run | 对接 auto_mending_planner 与 rework_manager |
| T183 | Validator | 验证返工后 verify → report → git backup dry-run 链路 | 验证完整返工闭环 dry-run |
| T184 | Reviewer | Stage 10 最终状态审查 | 审查 T175-T183 全部成果 |

---

## 11. Recommended Next Step

### 11.1 状态转换

```text
NEXT_PENDING=T175
NEXT_STAGE=Stage 10
```

### 11.2 T175 任务建议

任务名：完善 agents/*.md 角色职责、边界与输出规范

T175 职责：
1. 为 agents/main_agent.md 补充完整角色定义。
2. 为 agents/planner_agent.md 补充完整角色定义。
3. 为 agents/developer_agent.md 补充完整角色定义。
4. 为 agents/tester_agent.md 补充完整角色定义。
5. 为 agents/reviewer_agent.md 补充完整角色定义。
6. 为 agents/reporter_agent.md 补充完整角色定义。
7. 生成 docs/agent-role-protocol.md Agent 角色协议总纲。
8. 只做角色定义，不修改 runner.py、tools/、业务代码。

---

```text
PLANNING_STATUS=done
STAGE10_PLAN_CREATED=yes
AUTO_MENDING_PLANNER_PLANNED=yes
AUTO_MENDING_PLANNER_IMPLEMENTED=no
REWORK_LOOP_IMPLEMENTED=no
REAL_REWORK_EXECUTED=no
SUGGESTED_TASKS=T175-T184
NEXT_PENDING=T175
NEXT_STAGE=Stage 10
```
