# T180 Dev Report：接入 verifier fail → rework decision dry-run

## 基本信息

- TASK=T180
- ROLE=Dev Agent + Stage 10 Rework Decision Dry-run Integration Implementer
- DATE=2026-05-12
- PROJECT_ROOT=E:/github_project/multi-agent-runner
- LAST_COMMIT=66123cf test: validate stage 10 auto mending planner fail closed
- 备注：本任务只接入 dry-run，不执行真实返工，不修改 tools/auto_mending_planner.py

## 实现目标

把 verifier fail → rework decision dry-run 接入 runner.py 的 stage8-monitor-verify-report 子命令。

## 已完成工作

### 1. runner.py 修改点

在 runner.py 的 `stage8-monitor-verify-report` 子命令中，Step 3 Continuous Verifier 失败后，新增 **Step 3.1: Rework Decision Dry-Run (Stage 10)**。

修改位置：runner.py 第 3171 行之后（Step 3 verifier fail 分支和 Step 4 report 之间）。

### 2. 延迟导入

```python
from tools.auto_mending_planner import (
    build_rework_decision,
    build_rework_plan_dry_run,
)
```

仅在 verifier 失败时才导入，不影响成功路径的性能。

### 3. failure_type 推断逻辑

从 `verify_result_data.fail_reason` 推断 failure_type，使用 12 种模式匹配：

| 关键词 | failure_type |
|--------|-------------|
| syntax / py_compile | syntax_failed |
| test | tests_failed |
| report + (missing / not_found) | report_missing |
| check_result | check_result_failed |
| forbidden | forbidden_file_changed |
| unclassified | unclassified_changes |
| dirty | dirty_workspace |
| max_tasks | max_tasks_violation |
| 429 / rate_limit | rate_limit_or_api_429 |
| 其他 | verifier_failed |

### 4. rework decision dry-run 输出

结构化输出字段：

```
REWORK_DECISION_DRY_RUN=pass/fail
REWORK_ALLOWED=yes/no
AUTO_REWORK_ALLOWED=yes/no
USER_APPROVAL_REQUIRED=yes/no
REWORK_NEXT_ACTION=...
REWORK_FAIL_REASON=...
FAILURE_TYPE=...
RISK_LEVEL=...
REAL_REWORK_EXECUTED=no
REWORK_PLAN_CREATED=yes/no
REWORK_PLAN_ID=...（如果 plan 生成）
REWORK_PLAN_NEXT_ACTION=...（如果 plan 生成）
```

### 5. report_data 增强

ExecutionReportData 新增两个字段：

- `rework_required`: 根据是否有 rework decision 且 rework_allowed=True 设置
- `rework_decision`: "none" / "rework_allowed_dry_run" / "no_rework_needed" / "fail_closed"

### 6. 不改变已有成功路径

- check_result=pass 且 verify_status=pass 时，不触发 rework decision dry-run
- Step 4 report 和 Step 5 GitBackupGate 逻辑不变
- max_tasks=1 安全边界不变

## 未修改的文件

- tools/auto_mending_planner.py：未修改
- tools/rework_manager.py：未修改
- tools/continuous_verifier.py：未修改
- tools/execution_report_writer.py：未修改
- tools/git_backup_gate.py：未修改
- agents/*.md：未修改
- docs/agent-role-protocol.md：未修改
- 业务代码：未修改

## 设计说明

1. **为什么只在 verifier fail 后触发**：rework decision 只在检测到失败时才有意义。pass 的情况下不需要返工决策。

2. **为什么不直接调用 rework_manager**：T180 只做 dry-run 决策，真实返工由 rework_manager 在 T182 中接入。安全原则要求先 dry-run 再真实执行。

3. **为什么没有修改 auto_mending_planner.py**：auto_mending_planner.py 在 T178 中已经实现完整的 dry-run 功能，T180 只需要调用它的接口。

4. **为什么没有执行 run-project-loop real execution**：T180 是接入代码，不是验证任务。真实验证留给 T181。

5. **为什么 failure_type 用推断而非直接传入**：continuous_verifier.py 当前只输出 fail_reason 字符串，没有结构化的 failure_type。推断是一个合理的桥接方案。

6. **T181 将负责什么**：T181 将端到端验证 verifier fail → rework decision 生成链路，包括运行 stage8-monitor-verify-report 并确认 Step 3.1 输出正确。

## 安全保证

- TASK=T180
- IMPLEMENTATION_STATUS=done
- FILES_CREATED=reports/dev/T180-dev-report.md
- FILES_MODIFIED=runner.py, docs/tasks.md
- BUSINESS_CODE_CHANGED=no
- FRAMEWORK_CODE_CHANGED=yes
- RUNNER_CHANGED=yes
- TOOLS_CHANGED=no
- AGENTS_CHANGED=no
- REAL_EXECUTION_CHANGED=rework_decision_dry_run_only
- CLAUDE_AGENT_SDK_INTEGRATED=no
- VERIFIER_FAIL_REWORK_DECISION_INTEGRATED=yes
- REWORK_DECISION_DRY_RUN_INTEGRATED=yes
- REWORK_PLAN_DRY_RUN_INTEGRATED=yes
- AUTO_MENDING_PLANNER_MODIFIED=no
- REWORK_MANAGER_CALLED=no
- REAL_REWORK_EXECUTED=no
- GIT_COMMANDS_EXECUTED=no
- RUN_PROJECT_LOOP_REAL_EXECUTED=no
- MAX_TASKS_GT_1_ALLOWED=no
- PY_COMPILE_STATUS=pass
- CHECK_RESULT=pass
- NEXT_PENDING=T181
- NEXT_STAGE=Stage 10

## 文件清单

### 本次新增文件

- reports/dev/T180-dev-report.md

### 本次修改文件

- runner.py（新增 Step 3.1 rework decision dry-run）
- docs/tasks.md（T180 done，NEXT_PENDING → T181）

## 最终状态

```
TASK=T180
IMPLEMENTATION_STATUS=done
FILES_CREATED=reports/dev/T180-dev-report.md
FILES_MODIFIED=runner.py, docs/tasks.md
BUSINESS_CODE_CHANGED=no
FRAMEWORK_CODE_CHANGED=yes
RUNNER_CHANGED=yes
TOOLS_CHANGED=no
AGENTS_CHANGED=no
REAL_EXECUTION_CHANGED=rework_decision_dry_run_only
CLAUDE_AGENT_SDK_INTEGRATED=no
VERIFIER_FAIL_REWORK_DECISION_INTEGRATED=yes
REWORK_DECISION_DRY_RUN_INTEGRATED=yes
REWORK_PLAN_DRY_RUN_INTEGRATED=yes
AUTO_MENDING_PLANNER_MODIFIED=no
REWORK_MANAGER_CALLED=no
REAL_REWORK_EXECUTED=no
GIT_COMMANDS_EXECUTED=no
RUN_PROJECT_LOOP_REAL_EXECUTED=no
MAX_TASKS_GT_1_ALLOWED=no
PY_COMPILE_STATUS=pass
CHECK_RESULT=pass
NEXT_PENDING=T181
NEXT_STAGE=Stage 10
```
