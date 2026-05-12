# T177 Dev Report：设计 auto_mending_planner.py dry-run 数据结构

## 基本信息

- TASK=T177
- ROLE=Architect Agent + Stage 10 Auto Mending Planner Design Architect
- DATE=2026-05-12
- PROJECT_ROOT=E:/github_project/multi-agent-runner
- LAST_COMMIT=0930127 test: validate agent role protocol coverage
- 备注：本任务只做设计，不实现 Python 代码，不创建 tools/auto_mending_planner.py

## 设计目标

设计 auto_mending_planner.py dry-run 数据结构，为 T178 实现做准备。

## 已完成工作

### 1. 创建 docs/stage10-auto-mending-planner-design.md

包含 13 个章节：

1. **Background** — Stage 8/9 已有能力、当前缺口、auto_mending_planner.py 定位。
2. **Design Goal** — 11 项目标（接收失败结果、分类、判断、生成决策和计划）。
3. **Non-goals** — 11 项不做（不执行返工、不修改文件、不调用模型等）。
4. **Input Model** — MendingPlannerInput（15 字段），包含字段定义、来源映射、dataclass 草案。
5. **FailureClassification** — 6 字段 dataclass，11 种 failure_type 分类，分类逻辑优先级。
6. **ReworkDecision** — 17 字段 dataclass，字段取值范围，risk_level 判定规则，next_action 判定规则。
7. **ReworkPlan** — 12 字段 dataclass，allowed_operations 判定，forbidden_operations，proposed_steps 规则。
8. **Failure Type Rules** — 11 种 failure_type 详细规则（是否允许返工、风险等级、操作类型）。
9. **Decision Rules** — 15 条决策规则（基础规则 6 条、特定规则 5 条、安全规则 4 条）。
10. **Rework Safety Gate** — 10 条安全门规则、检查流程、返工后安全保证。
11. **Integration with Existing Modules** — 6 个模块交接（continuous_verifier、rework_manager、execution_report_writer、git_backup_gate、runner.py）。
12. **T178 Implementation Scope** — 实现范围（10 项）、限制（7 项）、CLI 接口草案、不做的事（8 项）。
13. **Acceptance Criteria** — 14 项完成标准。

### 2. 设计的 4 个数据结构

| 数据结构 | 字段数 | 用途 |
|---------|--------|------|
| MendingPlannerInput | 15 | auto_mending_planner 输入模型 |
| FailureClassification | 6 | 失败分类结果 |
| ReworkDecision | 17 | 返工决策 |
| ReworkPlan | 12 | 返工计划 |

### 3. FailureClassification 用途

将 verifier 的 fail_reason 分类为 11 种标准 failure_type，每种类型有明确的严重程度（P0-P5）、是否可返工、是否需要人工确认、默认下一步动作。

### 4. ReworkDecision 用途

根据 FailureClassification 和安全门规则，生成结构化返工决策。包含返工允许状态、自动返工允许状态、目标文件、禁止文件、风险等级、返工轮次控制、下一步动作。

### 5. ReworkPlan 用途

如果返工允许，生成受控返工计划草案。包含目标文件、允许操作、禁止操作、建议步骤、验证步骤、回滚说明、报告要求。

### 6. failure_type 分类规则

| failure_type | 可自动返工 | 风险等级 |
|-------------|-----------|---------|
| report_missing | yes | low |
| check_result_failed | yes | medium |
| verifier_failed | conditional | medium |
| tests_failed | yes | low |
| syntax_failed | yes | low |
| forbidden_file_changed | no（fail closed） | high |
| unclassified_changes | no（fail closed） | high |
| dirty_workspace | no（fail closed） | high |
| max_tasks_violation | no（fail closed） | high |
| rate_limit_or_api_429 | no（等待恢复） | — |
| unknown_failure | no（fail closed） | — |

### 7. fail closed 规则

10 条安全门规则：

1. forbidden files 一律 fail closed。
2. unclassified files 一律 fail closed。
3. dirty workspace 未分类一律 fail closed。
4. max_rework_rounds 超限一律 fail closed。
5. 缺少 target_files 一律 fail closed。
6. 缺少 source_report_path 一律 fail closed。
7. 涉及 runner.py / tools/ 必须人工确认。
8. 涉及 Git 操作必须交给 GitBackupGate。
9. 不允许自动 git add / commit / push。
10. 返工后必须再次 verify。

### 8. T178 实现范围

T178 只实现 dry-run：
- 创建 tools/auto_mending_planner.py。
- 定义 4 个 dataclass。
- 实现 classify_failure、build_rework_decision、build_rework_plan_dry_run。
- 实现 CLI dry-run。
- 不修改文件、不执行返工、不调用模型、不执行 Git。

## 未创建的文件

- tools/auto_mending_planner.py：未创建（T178 才实现）。

## 未修改的文件

- runner.py：未修改。
- tools/rework_manager.py：未修改。
- tools/continuous_verifier.py：未修改。
- tools/execution_report_writer.py：未修改。
- tools/git_backup_gate.py：未修改。
- agents/*.md：未修改。
- docs/agent-role-protocol.md：未修改。
- 业务代码：未修改。

## 安全保证

- TASK=T177
- DESIGN_STATUS=done
- FILES_CREATED=docs/stage10-auto-mending-planner-design.md, reports/dev/T177-dev-report.md
- FILES_MODIFIED=docs/tasks.md
- BUSINESS_CODE_CHANGED=no
- FRAMEWORK_CODE_CHANGED=no
- RUNNER_CHANGED=no
- TOOLS_CHANGED=no
- AGENTS_CHANGED=no
- REAL_EXECUTION_CHANGED=no
- CLAUDE_AGENT_SDK_INTEGRATED=no
- AUTO_MENDING_PLANNER_DESIGNED=yes
- AUTO_MENDING_PLANNER_IMPLEMENTED=no
- REWORK_DECISION_DESIGNED=yes
- REWORK_PLAN_DESIGNED=yes
- FAILURE_CLASSIFICATION_DESIGNED=yes
- REAL_REWORK_EXECUTED=no
- GIT_COMMANDS_EXECUTED=no
- CHECK_RESULT=pass
- NEXT_PENDING=T178
- NEXT_STAGE=Stage 10

## 文件清单

### 本次新增文件

- docs/stage10-auto-mending-planner-design.md
- reports/dev/T177-dev-report.md

### 本次修改文件

- docs/tasks.md（T177 done，NEXT_PENDING → T178）

## 最终状态

```
TASK=T177
DESIGN_STATUS=done
FILES_CREATED=docs/stage10-auto-mending-planner-design.md, reports/dev/T177-dev-report.md
FILES_MODIFIED=docs/tasks.md
BUSINESS_CODE_CHANGED=no
FRAMEWORK_CODE_CHANGED=no
RUNNER_CHANGED=no
TOOLS_CHANGED=no
AGENTS_CHANGED=no
REAL_EXECUTION_CHANGED=no
CLAUDE_AGENT_SDK_INTEGRATED=no
AUTO_MENDING_PLANNER_DESIGNED=yes
AUTO_MENDING_PLANNER_IMPLEMENTED=no
REWORK_DECISION_DESIGNED=yes
REWORK_PLAN_DESIGNED=yes
FAILURE_CLASSIFICATION_DESIGNED=yes
REAL_REWORK_EXECUTED=no
GIT_COMMANDS_EXECUTED=no
CHECK_RESULT=pass
NEXT_PENDING=T178
NEXT_STAGE=Stage 10
```
