# Stage 10 Auto Mending Planner Design

设计时间：2026-05-12
设计角色：Architect Agent + Stage 10 Auto Mending Planner Design Architect
前置条件：T175-T176 done, Agent 角色协议层已补强
设计范围：auto_mending_planner.py dry-run 数据结构设计

---

## 1. Background

### 1.1 已有能力

| # | 能力 | 模块 | Stage |
|---|------|------|-------|
| 1 | 执行前 Monitor | task_monitor.py | Stage 8 |
| 2 | 执行后 Verifier | continuous_verifier.py | Stage 8 |
| 3 | 执行报告生成 | execution_report_writer.py | Stage 8 |
| 4 | Git Backup Gate dry-run | git_backup_gate.py | Stage 9 |
| 5 | 子项目返工管理 | rework_manager.py | Stage 5-6 |
| 6 | Agent 角色协议 | agents/*.md + docs/agent-role-protocol.md | Stage 10 (T175-T176) |

### 1.2 当前缺口

continuous_verifier.py 输出 `ContinuousVerifyResult(ok=False, fail_reason=...)` 后，系统无法自动生成返工决策。当前流程在 verifier fail 时直接停止，缺少以下桥接：

1. **fail_reason → failure_type 分类**：verifier 返回 fail_reason 字符串，但没有结构化的 failure_type。
2. **failure_type → 返工决策**：缺少根据 failure_type 判断是否允许返工的逻辑。
3. **返工决策 → 返工计划**：缺少根据决策生成受控返工计划的模块。

### 1.3 auto_mending_planner.py 定位

auto_mending_planner.py 只负责 dry-run 规划，不直接执行返工：

1. 接收 verifier 失败结果。
2. 分类 failure_type。
3. 判断是否允许返工。
4. 生成 ReworkDecision。
5. 生成 ReworkPlan 草案。
6. 所有不确定情况 fail closed。

真实返工必须经过 rework_manager.py 和人工确认。

---

## 2. Design Goal

auto_mending_planner.py 的目标：

1. 接收 verifier 失败结果（ContinuousVerifyResult 或等价输入）。
2. 分类 failure_type（11 种标准类型）。
3. 判断是否允许返工（rework_allowed）。
4. 判断是否允许 auto rework dry-run（auto_rework_allowed）。
5. 生成 ReworkDecision（结构化返工决策）。
6. 生成 ReworkPlan 草案（受控返工计划）。
7. 明确 target_files（允许修改的文件列表）。
8. 明确 forbidden_files（禁止修改的文件列表）。
9. 明确 risk_level（风险等级）。
10. 明确 next_action（下一步动作）。
11. 所有不确定情况 fail closed。

---

## 3. Non-goals

本设计不做以下事项：

1. 不执行真实返工。
2. 不修改任何业务文件。
3. 不调用真实模型。
4. 不调用 Claude Agent SDK。
5. 不执行 git add。
6. 不执行 git commit。
7. 不执行 git push。
8. 不绕过 verifier。
9. 不绕过 GitBackupGate。
10. 不实现 run_state_manager.py。
11. 不处理 API 429 自动恢复。

---

## 4. Input Model

auto_mending_planner.py 的输入模型，定义为 `MendingPlannerInput`：

### 4.1 字段定义

| # | 字段 | 类型 | 必填 | 说明 |
|---|------|------|------|------|
| 1 | task_id | str | yes | 当前任务编号（如 T177） |
| 2 | verifier_status | str | yes | verifier 结果：pass / fail |
| 3 | check_result | str | yes | 报告中 CHECK_RESULT：pass / fail |
| 4 | failure_type | str \| None | no | 失败类型（见 Section 8），可从 fail_reason 推断 |
| 5 | failure_summary | str | no | 失败原因摘要（来自 verifier fail_reason） |
| 6 | failed_files | list[str] | no | 失败涉及的文件列表 |
| 7 | changed_files | list[str] | yes | 所有变更文件列表（来自 git status） |
| 8 | allowed_files | list[str] | yes | 当前任务允许修改的文件列表 |
| 9 | forbidden_files | list[str] | yes | 禁止修改的文件列表 |
| 10 | unclassified_files | list[str] | no | 未分类文件列表 |
| 11 | current_rework_round | int | yes | 当前返工轮次（0-based，0=首次执行） |
| 12 | max_rework_rounds | int | yes | 最大返工轮次（默认 3） |
| 13 | user_approval_required | bool | no | 是否需要人工确认 |
| 14 | rework_policy | str | no | 返工策略：auto_dry_run / manual_only / disabled |
| 15 | source_report_path | str | yes | 来源报告路径（verifier report 或 dev report） |

### 4.2 字段来源

| 字段 | 来源 | 说明 |
|------|------|------|
| task_id | tasks.md NEXT_PENDING | 当前任务编号 |
| verifier_status | continuous_verifier.py | ContinuousVerifyResult.ok 转换 |
| check_result | execution report | CHECK_RESULT 字段 |
| failure_type | auto_mending_planner 推断 | 从 fail_reason 解析 |
| failure_summary | continuous_verifier.py | ContinuousVerifyResult.fail_reason |
| failed_files | continuous_verifier.py | ContinuousVerifyResult 中相关字段 |
| changed_files | git status --short | 通过 git_backup_gate.py 获取 |
| allowed_files | 当前任务定义 | 任务明确允许修改的文件 |
| forbidden_files | agent-role-protocol.md | 三级文件权限模型 |
| unclassified_files | git_backup_gate.py | classify_changed_files 输出 |
| current_rework_round | tasks.md 或报告 | 当前返工轮次 |
| max_rework_rounds | 默认 3 | 与 rework_manager.py 一致 |
| user_approval_required | auto_mending_planner 判断 | 基于安全规则 |
| rework_policy | 默认 auto_dry_run | 控制返工模式 |
| source_report_path | verifier report | 报告文件路径 |

### 4.3 Python dataclass 草案

```python
@dataclass
class MendingPlannerInput:
    """auto_mending_planner 输入。"""

    # 基础信息
    task_id: str
    verifier_status: str                    # pass / fail
    check_result: str                       # pass / fail
    failure_summary: str | None = None

    # 文件信息
    changed_files: list[str] = field(default_factory=list)
    allowed_files: list[str] = field(default_factory=list)
    forbidden_files: list[str] = field(default_factory=list)
    unclassified_files: list[str] = field(default_factory=list)
    failed_files: list[str] = field(default_factory=list)

    # 返工控制
    current_rework_round: int = 0
    max_rework_rounds: int = 3
    rework_policy: str = "auto_dry_run"
    user_approval_required: bool = False

    # 来源
    source_report_path: str = ""
```

注意：failure_type 不在输入中，而是由 auto_mending_planner 内部推断生成。

---

## 5. FailureClassification

### 5.1 数据结构

```python
@dataclass
class FailureClassification:
    """失败分类结果。"""

    failure_type: str           # 失败类型标识
    severity: str               # 严重程度：P0 / P1 / P2 / P3 / P4 / P5
    is_reworkable: bool         # 是否可返工
    requires_user_approval: bool  # 是否需要人工确认
    default_next_action: str    # 默认下一步动作
    reason: str                 # 分类原因说明
```

### 5.2 failure_type 取值范围

| # | failure_type | severity | is_reworkable | requires_user_approval | default_next_action |
|---|-------------|----------|---------------|----------------------|---------------------|
| 1 | report_missing | P3 | True | False | auto_rework_dry_run |
| 2 | check_result_failed | P4 | True | False | auto_rework_dry_run |
| 3 | verifier_failed | P4 | True | True | manual_rework |
| 4 | tests_failed | P3 | True | False | auto_rework_dry_run |
| 5 | syntax_failed | P3 | True | False | auto_rework_dry_run |
| 6 | forbidden_file_changed | P1 | False | True | stop |
| 7 | unclassified_changes | P1 | False | True | stop |
| 8 | dirty_workspace | P2 | False | True | stop |
| 9 | max_tasks_violation | P1 | False | True | stop |
| 10 | rate_limit_or_api_429 | P0 | False | True | wait_for_rate_limit_recovery |
| 11 | unknown_failure | P5 | False | True | stop |

### 5.3 分类逻辑

classify_failure 函数的判断顺序（按优先级从高到低）：

1. **rate_limit_or_api_429**（P0）：fail_reason 包含 "429" 或 "rate_limit"。
2. **forbidden_file_changed**（P1）：forbidden_files 非空。
3. **unclassified_changes**（P1）：unclassified_files 非空。
4. **max_tasks_violation**（P1）：fail_reason 包含 "max_tasks"。
5. **dirty_workspace**（P2）：fail_reason 包含 "dirty" 或 changed_files 非空且未分类。
6. **syntax_failed**（P3）：fail_reason 包含 "syntax" 或 "py_compile"。
7. **tests_failed**（P3）：fail_reason 包含 "test"。
8. **report_missing**（P3）：fail_reason 包含 "report_missing" 或 "task_not_done"。
9. **check_result_failed**（P4）：check_result != "pass"。
10. **verifier_failed**（P4）：verifier_status == "fail" 但 fail_reason 无明确匹配。
11. **unknown_failure**（P5）：以上均不匹配。

---

## 6. ReworkDecision Data Structure

### 6.1 数据结构

```python
@dataclass
class ReworkDecision:
    """返工决策 — 由 auto_mending_planner.py 生成。"""

    # 基础信息
    ok: bool                              # 决策是否成功生成
    task_id: str                          # 当前任务编号
    verify_status: str                    # verifier 结果：pass / fail
    check_result: str                     # CHECK_RESULT：pass / fail

    # 失败分类
    failure_type: str | None              # 失败类型（见 Section 5）
    failure_summary: str | None           # 失败原因摘要

    # 返工判断
    rework_allowed: bool                  # 是否允许返工
    auto_rework_allowed: bool             # 是否允许自动返工 dry-run
    user_approval_required: bool          # 是否需要人工确认

    # 返工范围
    target_files: list[str]               # 需要修改的文件列表
    forbidden_files: list[str]            # 禁止修改的文件列表
    unclassified_files: list[str]         # 未分类文件列表
    risk_level: str                       # 风险等级：low / medium / high / critical

    # 返工轮次控制
    current_rework_round: int             # 当前返工轮次（0-based）
    max_rework_rounds: int                # 最大返工轮次（默认 3）

    # 结果
    next_action: str                      # 下一步动作
    fail_reason: str | None               # 决策失败原因（ok=False 时）
```

### 6.2 字段取值范围

| 字段 | 有效值 | 说明 |
|------|--------|------|
| verify_status | pass, fail | 对应 ContinuousVerifyResult.ok |
| check_result | pass, fail | 来自报告 CHECK_RESULT |
| failure_type | report_missing, check_result_failed, verifier_failed, tests_failed, syntax_failed, forbidden_file_changed, unclassified_changes, dirty_workspace, max_tasks_violation, rate_limit_or_api_429, unknown_failure, None | None 表示无法分类 |
| risk_level | low, medium, high, critical | 由 failure_type 和 target_files 决定 |
| next_action | auto_rework_dry_run, manual_rework, wait_for_rate_limit_recovery, stop, no_rework_needed | 根据决策结果 |

### 6.3 risk_level 判定规则

| 条件 | risk_level |
|------|-----------|
| target_files 包含 runner.py 或 tools/ | critical |
| failure_type 为 forbidden_file_changed / unclassified_changes | high |
| failure_type 为 dirty_workspace / max_tasks_violation | high |
| failure_type 为 verifier_failed / check_result_failed | medium |
| failure_type 为 syntax_failed / tests_failed / report_missing | low |
| 其他 | medium |

### 6.4 next_action 判定规则

| 条件 | next_action |
|------|------------|
| check_result=pass 且 verify_status=pass | no_rework_needed |
| failure_type=rate_limit_or_api_429 | wait_for_rate_limit_recovery |
| failure_type 为 forbidden/unclassified/dirty/max_tasks/unknown | stop |
| rework_allowed=False | stop |
| auto_rework_allowed=True 且 target_files 明确 | auto_rework_dry_run |
| rework_allowed=True 但 user_approval_required=True | manual_rework |
| 其他 | stop |

---

## 7. ReworkPlan Data Structure

### 7.1 数据结构

```python
@dataclass
class ReworkPlan:
    """返工计划 — 由 auto_mending_planner.py 生成。"""

    # 基础信息
    task_id: str                          # 当前任务编号
    plan_id: str                          # 计划编号：Txxx-R{n}-plan
    rework_round: int                     # 返工轮次（1-based）

    # 返工范围
    target_files: list[str]               # 需要修改的文件列表
    allowed_operations: list[str]         # 允许的操作列表
    forbidden_operations: list[str]       # 禁止的操作列表

    # 计划内容
    proposed_steps: list[str]             # 建议的修复步骤
    verification_steps: list[str]         # 返工后的验证步骤
    rollback_notes: str                   # 回滚说明

    # 报告要求
    required_reports: list[str]           # 返工后必须生成的报告

    # 决策
    approval_required: bool               # 是否需要人工确认
    next_action: str                      # 下一步动作
```

### 7.2 字段取值范围

| 字段 | 有效值 | 说明 |
|------|--------|------|
| plan_id | Txxx-R{n}-plan | 计划编号格式 |
| rework_round | 1, 2, 3 | 与 MAX_REWORK_ROUNDS 一致 |
| allowed_operations | fix_syntax, fix_tests, generate_report, fix_check_result 等 | 根据 failure_type 决定 |
| forbidden_operations | modify_runner, modify_tools, git_add, git_commit, git_push, add_dependency, expand_scope 等 | 始终禁止的操作 |
| next_action | execute_dry_run, wait_for_approval, stop | 根据决策 |

### 7.3 allowed_operations 判定规则

| failure_type | allowed_operations |
|-------------|-------------------|
| syntax_failed | [fix_syntax] |
| tests_failed | [fix_tests] |
| report_missing | [generate_report] |
| check_result_failed | [fix_check_result, regenerate_report] |
| verifier_failed | [fix_verifier_issues] |
| 其他 | []（不允许自动返工） |

### 7.4 forbidden_operations（始终包含）

```python
FORBIDDEN_OPERATIONS_ALWAYS = [
    "modify_runner",
    "modify_tools",
    "git_add",
    "git_commit",
    "git_push",
    "add_dependency",
    "expand_scope",
    "modify_business_code_outside_scope",
]
```

### 7.5 proposed_steps 生成规则

根据 failure_type 生成建议步骤：

| failure_type | proposed_steps |
|-------------|---------------|
| syntax_failed | 1. 定位语法错误文件 2. 修复语法 3. py_compile 验证 |
| tests_failed | 1. 定位失败测试 2. 分析失败原因 3. 修复相关代码 4. 重新运行测试 |
| report_missing | 1. 确认报告路径 2. 生成缺失报告 3. 验证报告格式 |
| check_result_failed | 1. 定位 CHECK_RESULT=fail 原因 2. 修复问题 3. 重新生成报告 |
| verifier_failed | 1. 分析 verifier fail_reason 2. 针对性修复 3. 重新运行 verifier |

---

## 8. Failure Type Rules

### 8.1 report_missing

- **是否允许自动返工**：yes
- **auto_rework_allowed**：True（如果 target_files 明确且不包含 runner.py / tools/）
- **风险等级**：low
- **返工操作**：generate_report
- **条件**：任务已完成执行，但未生成 dev report 或 continuous run report

### 8.2 check_result_failed

- **是否允许自动返工**：yes
- **auto_rework_allowed**：True（如果 target_files 明确）
- **风险等级**：medium
- **返工操作**：fix_check_result, regenerate_report
- **条件**：报告存在但 CHECK_RESULT != pass

### 8.3 verifier_failed

- **是否允许自动返工**：conditional
- **auto_rework_allowed**：取决于 fail_reason
- **风险等级**：medium
- **返工操作**：根据 fail_reason 决定
- **条件**：continuous_verifier 返回 fail，需要 user_approval
- **特殊说明**：verifier_failed 是兜底类型，当 fail_reason 无明确匹配时使用

### 8.4 tests_failed

- **是否允许自动返工**：yes
- **auto_rework_allowed**：True（如果 target_files 明确且不包含 runner.py / tools/）
- **风险等级**：low
- **返工操作**：fix_tests
- **条件**：测试未通过

### 8.5 syntax_failed

- **是否允许自动返工**：yes
- **auto_rework_allowed**：True（如果 target_files 明确且不包含 runner.py / tools/）
- **风险等级**：low
- **返工操作**：fix_syntax
- **条件**：py_compile 或语法检查失败

### 8.6 forbidden_file_changed

- **必须 fail closed**：yes
- **rework_allowed**：False
- **auto_rework_allowed**：False
- **next_action**：stop
- **风险等级**：high
- **条件**：修改了文件权限模型中 Forbidden 级别的文件
- **人工确认**：必须人工介入分析原因

### 8.7 unclassified_changes

- **必须 fail closed**：yes
- **rework_allowed**：False
- **auto_rework_allowed**：False
- **next_action**：stop
- **风险等级**：high
- **条件**：变更文件中有未在 allowed 或 forbidden 中分类的文件
- **人工确认**：必须人工分类后再决定

### 8.8 dirty_workspace

- **必须 fail closed**：yes（除非全部变更已分类）
- **rework_allowed**：False（除非 unclassified_files 为空且 forbidden_files 为空）
- **auto_rework_allowed**：False
- **next_action**：stop
- **风险等级**：high
- **条件**：工作区有未提交变更，且变更未完全分类
- **特殊说明**：如果全部变更已在 allowed_files 中分类，则降级为 normal rework

### 8.9 max_tasks_violation

- **必须 fail closed**：yes
- **rework_allowed**：False
- **auto_rework_allowed**：False
- **next_action**：stop
- **风险等级**：high
- **条件**：max_tasks != 1，违反受控执行原则
- **人工确认**：必须修正参数

### 8.10 rate_limit_or_api_429

- **必须停止等待恢复**：yes
- **rework_allowed**：False
- **auto_rework_allowed**：False
- **next_action**：wait_for_rate_limit_recovery
- **风险等级**：不适用
- **条件**：API 返回 429 或调用限制
- **特殊说明**：不做自动返工，不做自动重试，等待人工确认或限额恢复

### 8.11 unknown_failure

- **必须 fail closed**：yes
- **rework_allowed**：False
- **auto_rework_allowed**：False
- **next_action**：stop
- **风险等级**：不适用
- **条件**：fail_reason 无法匹配任何已知类型
- **人工确认**：必须人工介入分析

---

## 9. Decision Rules

### 9.1 基础规则

| # | 条件 | 结果 |
|---|------|------|
| 1 | check_result=pass 且 verify_status=pass | ok=True, next_action=no_rework_needed |
| 2 | failure_type 为空或 None | ok=False, fail_reason="missing_failure_type" |
| 3 | forbidden_files 非空 | ok=False, fail_reason="forbidden_files_present" |
| 4 | unclassified_files 非空 | ok=False, fail_reason="unclassified_files_present" |
| 5 | current_rework_round >= max_rework_rounds | ok=False, fail_reason="max_rework_rounds_exceeded" |
| 6 | source_report_path 为空 | ok=False, fail_reason="missing_source_report" |

### 9.2 特定 failure_type 规则

| # | 条件 | 结果 |
|---|------|------|
| 7 | failure_type=rate_limit_or_api_429 | next_action=wait_for_rate_limit_recovery |
| 8 | failure_type=syntax_failed 且 target_files 明确 | rework_allowed=True, auto_rework_allowed=True |
| 9 | failure_type=tests_failed 且 target_files 明确 | rework_allowed=True, auto_rework_allowed=True |
| 10 | failure_type=report_missing | rework_allowed=True, auto_rework_allowed=True |
| 11 | failure_type=check_result_failed 且 target_files 明确 | rework_allowed=True, auto_rework_allowed=True |

### 9.3 安全规则

| # | 条件 | 结果 |
|---|------|------|
| 12 | target_files 包含 runner.py 或 tools/ | user_approval_required=True |
| 13 | 涉及 runner.py / tools/ | user_approval_required=True |
| 14 | 所有 auto_rework_allowed=True 的情况 | 也必须先 dry-run |
| 15 | 任何不确定情况 | fail closed（ok=False） |

### 9.4 auto_rework_allowed 判定条件

auto_rework_allowed=True 必须同时满足以下全部条件：

1. failure_type 在可自动返工列表中（report_missing / check_result_failed / tests_failed / syntax_failed）。
2. target_files 不为空。
3. target_files 不包含 runner.py。
4. target_files 不包含 tools/ 目录下的文件。
5. risk_level 不是 critical。
6. current_rework_round < max_rework_rounds。
7. forbidden_files 为空。
8. unclassified_files 为空。
9. source_report_path 非空。
10. rework_policy 不是 "disabled"。

---

## 10. Rework Safety Gate

### 10.1 安全门规则

返工执行前必须通过以下全部检查：

| # | 检查项 | 条件 | 失败动作 |
|---|--------|------|---------|
| 1 | forbidden files | forbidden_files 一律 fail closed | ok=False, next_action=stop |
| 2 | unclassified files | unclassified_files 一律 fail closed | ok=False, next_action=stop |
| 3 | dirty workspace | 工作区未分类变更一律 fail closed | ok=False, next_action=stop |
| 4 | max rework rounds | current_rework_round >= max_rework_rounds 时停止 | ok=False, next_action=stop |
| 5 | missing failure_type | failure_type 为空时停止 | ok=False, next_action=stop |
| 6 | missing target_files | target_files 为空时停止 | ok=False, next_action=stop |
| 7 | missing source_report | source_report_path 为空时停止 | ok=False, next_action=stop |
| 8 | runner.py / tools/ | 涉及这些文件时 user_approval_required=True | 标记需要人工确认 |
| 9 | no auto git | 返工不能自动 git add/commit/push | 始终 dry-run |
| 10 | post-rework verify | 返工后必须再次 verify | 记录在 ReworkPlan 中 |

### 10.2 安全门检查流程

```text
MendingPlannerInput 输入
  → 检查 source_report_path（空 → fail closed）
  → classify_failure → FailureClassification
  → 检查 forbidden_files（非空 → fail closed）
  → 检查 unclassified_files（非空 → fail closed）
  → 检查 max_rework_rounds（超限 → fail closed）
  → 检查 failure_type（空 → fail closed）
  → 检查 target_files（空 → fail closed）
  → 检查 runner.py / tools/ 涉及（是 → user_approval_required）
  → 判断 risk_level
  → 判断 rework_allowed
  → 判断 auto_rework_allowed
  → 生成 ReworkDecision
  → 如果 rework_allowed：生成 ReworkPlan
  → 输出结果
```

### 10.3 返工后安全保证

返工完成后，必须经过以下链路：

1. **continuous_verifier** — 再次验证任务状态、报告、安全边界。
2. **execution_report_writer** — 生成返工后的执行报告。
3. **GitBackupGate dry-run** — 分类返工变更文件，生成 approval record。
4. **stop for user approval** — 始终等待用户确认，不自动进入下一任务。

---

## 11. Integration with Existing Modules

### 11.1 整体流程

```text
Task execution (runner.py, max_tasks=1)
  → Monitor (task_monitor.py)
  → Controlled execution
  → Verifier (continuous_verifier.py)
  → if pass: GitBackupGate dry-run → stop
  → if fail: auto_mending_planner.py
      → classify_failure → FailureClassification
      → build_rework_decision → ReworkDecision
      → build_rework_plan_dry_run → ReworkPlan（如果允许）
      → 输出结果
  → if ReworkDecision.rework_allowed:
      → rework_manager.py（受控返工 dry-run）
      → 第二次 verify (continuous_verifier.py)
      → 第二次 report (execution_report_writer.py)
      → GitBackupGate dry-run
      → stop for user approval
  → if ReworkDecision.rework_allowed=False:
      → stop, 等待人工介入
```

### 11.2 与 continuous_verifier.py 的交接

| 对接项 | 说明 |
|--------|------|
| 输入 | ContinuousVerifyResult（ok, fail_reason, check_result_pass 等） |
| 转换 | ContinuousVerifyResult.ok → MendingPlannerInput.verifier_status |
| 转换 | ContinuousVerifyResult.fail_reason → MendingPlannerInput.failure_summary |
| 转换 | ContinuousVerifyResult.forbidden_files_changed → 检查 forbidden_files |
| 转换 | ContinuousVerifyResult.unclassified_changes → 检查 unclassified_files |

### 11.3 与 rework_manager.py 的交接

| 对接项 | 说明 |
|--------|------|
| 关系 | auto_mending_planner 是决策层，rework_manager 是执行层 |
| 输入 | ReworkDecision.rework_allowed=True 时，传递 target_files 和 rework_plan |
| 输出 | rework_manager 生成 rework prompt，执行受控返工 |
| 轮次 | 两者共享 max_rework_rounds=3 |
| 确认 | rework_manager 要求严格确认格式 |

### 11.4 与 execution_report_writer.py 的交接

| 对接项 | 说明 |
|--------|------|
| 记录 | ReworkDecision 应记录在 execution report 中 |
| 字段 | 新增 REWORK_DECISION / REWORK_ALLOWED / REWORK_REASON |
| 时序 | 返工决策在 verifier 之后、rework 之前记录 |

### 11.5 与 git_backup_gate.py 的交接

| 对接项 | 说明 |
|--------|------|
| 时序 | 返工完成后执行 GitBackupGate dry-run |
| 输入 | 返工后的 changed_files |
| 输出 | 分类结果（allowed / forbidden / unclassified） |
| 保证 | 始终 dry-run，不自动 git add/commit/push |

### 11.6 与 runner.py 的接入（T180/T182）

| 对接项 | 说明 |
|--------|------|
| 接入点 | runner.py stage8-monitor-verify-report 子命令 |
| 时机 | Step 4 Verifier fail 后 |
| 新增步骤 | Step 4.1 调用 auto_mending_planner dry-run |
| 判断 | 根据 ReworkDecision.next_action 决定下一步 |

---

## 12. T178 Implementation Scope

T178 应只实现 dry-run：

### 12.1 实现范围

1. 创建 `tools/auto_mending_planner.py`。
2. 定义 `MendingPlannerInput` dataclass。
3. 定义 `FailureClassification` dataclass。
4. 定义 `ReworkDecision` dataclass。
5. 定义 `ReworkPlan` dataclass。
6. 实现 `classify_failure(input_data) -> FailureClassification`。
7. 实现 `build_rework_decision(input_data) -> ReworkDecision`。
8. 实现 `build_rework_plan_dry_run(decision) -> ReworkPlan | None`。
9. 实现 `check_rework_safety_gate(decision) -> bool`。
10. 实现 CLI dry-run 入口（`python -m tools.auto_mending_planner --dry-run`）。

### 12.2 实现限制

1. 不修改文件。
2. 不执行返工。
3. 不调用模型。
4. 不执行 Git。
5. 使用 Python 标准库（dataclasses, re, pathlib, json）。
6. fail closed。
7. 不引入第三方依赖。

### 12.3 CLI 接口草案

```bash
# dry-run：根据 verifier 结果生成返工决策
python -m tools.auto_mending_planner --dry-run \
  --task-id T178 \
  --verifier-status fail \
  --check-result fail \
  --failure-summary "task_not_done" \
  --source-report reports/continuous-runs/T178-run-report.md

# 输出 ReworkDecision + ReworkPlan（如果允许）
```

### 12.4 T178 不做的事

1. 不修改 runner.py。
2. 不修改 continuous_verifier.py。
3. 不修改 rework_manager.py。
4. 不修改 execution_report_writer.py。
5. 不修改 git_backup_gate.py。
6. 不调用 Claude Agent SDK。
7. 不执行真实返工。
8. 不执行 Git 操作。

---

## 13. Acceptance Criteria

T177 完成标准：

| # | 标准 | 状态 |
|---|------|------|
| 1 | docs/stage10-auto-mending-planner-design.md 已创建 | yes |
| 2 | FailureClassification 已设计（6 字段，11 种类型） | yes |
| 3 | ReworkDecision 已设计（17 字段） | yes |
| 4 | ReworkPlan 已设计（12 字段） | yes |
| 5 | MendingPlannerInput 已设计（15 字段） | yes |
| 6 | failure_type 规则已设计（11 种类型） | yes |
| 7 | fail closed 规则已设计（10 条安全门） | yes |
| 8 | 与 existing modules 的集成点已设计 | yes |
| 9 | T178 dry-run 范围已明确 | yes |
| 10 | 未创建 tools/auto_mending_planner.py | yes |
| 11 | 未修改 runner.py | yes |
| 12 | 未修改 tools/ | yes |
| 13 | NEXT_PENDING=T178 | yes |
| 14 | NEXT_STAGE=Stage 10 | yes |

---

```text
T177_DESIGN_STATUS=done
AUTO_MENDING_PLANNER_DESIGNED=yes
AUTO_MENDING_PLANNER_IMPLEMENTED=no
REWORK_DECISION_DESIGNED=yes
REWORK_PLAN_DESIGNED=yes
FAILURE_CLASSIFICATION_DESIGNED=yes
MENDING_PLANNER_INPUT_DESIGNED=yes
FAILURE_TYPE_RULES_DESIGNED=yes
REWORK_SAFETY_GATE_DESIGNED=yes
INTEGRATION_POINTS_DESIGNED=yes
T178_SCOPE_DEFINED=yes
CHECK_RESULT=pass
NEXT_PENDING=T178
NEXT_STAGE=Stage 10
```
