# T178 Dev Report：实现 auto_mending_planner.py dry-run

## 基本信息

- TASK=T178
- ROLE=Developer Agent + Stage 10 Auto Mending Planner Dry-run Implementer
- DATE=2026-05-12
- PROJECT_ROOT=E:/github_project/multi-agent-runner
- LAST_COMMIT=a0ee0a3 docs: design stage 10 auto mending planner
- 备注：本任务只实现 dry-run，不执行真实返工，不调用模型，不执行 Git
- 备注2：T178 执行过程中曾尝试 git diff --no-index /dev/null 查看新文件，被用户拒绝。改为使用 Read 文件方式检查新文件内容。从 T178_RESUME 中断点恢复后完成所有验证步骤。

## 实现目标

实现 tools/auto_mending_planner.py dry-run 模块，包含 classify_failure、build_rework_decision、build_rework_plan_dry_run。

## 已完成工作

### 1. 创建 tools/auto_mending_planner.py

实现 dry-run 模块，使用 Python 标准库，不引入第三方依赖。

### 2. FailureClassification 实现

6 字段 dataclass：
- failure_type: str
- severity: str（P0-P5）
- is_reworkable: bool
- requires_user_approval: bool
- default_next_action: str
- reason: str

11 种 failure_type 分类完整实现：
- rate_limit_or_api_429（P0）
- forbidden_file_changed（P1）
- unclassified_changes（P1）
- max_tasks_violation（P1）
- dirty_workspace（P2）
- report_missing（P3）
- syntax_failed（P3）
- tests_failed（P3）
- check_result_failed（P4）
- verifier_failed（P4）
- unknown_failure（P5）

### 3. ReworkDecision 实现

17 字段 dataclass：
- ok: bool
- task_id: str
- verify_status: str
- check_result: str
- failure_type: str | None
- failure_summary: str | None
- rework_allowed: bool
- auto_rework_allowed: bool
- user_approval_required: bool
- target_files: list[str]
- forbidden_files: list[str]
- unclassified_files: list[str]
- risk_level: str（low/medium/high/critical）
- current_rework_round: int
- max_rework_rounds: int
- next_action: str
- fail_reason: str | None

### 4. ReworkPlan 实现

12 字段 dataclass：
- task_id: str
- plan_id: str（Txxx-R{n}-plan）
- rework_round: int
- target_files: list[str]
- allowed_operations: list[str]
- forbidden_operations: list[str]
- proposed_steps: list[str]
- verification_steps: list[str]
- rollback_notes: list[str]
- required_reports: list[str]
- approval_required: bool
- next_action: str

### 5. 实现的函数

| 函数 | 用途 |
|------|------|
| normalize_list(values) | 规范化字符串列表 |
| classify_failure(failure_type) | 返回 FailureClassification |
| validate_target_files(target_files, forbidden_files, unclassified_files) | 验证目标文件 |
| build_rework_decision(...) | 生成 ReworkDecision |
| build_rework_plan_dry_run(decision) | 生成 ReworkPlan |
| print_decision(decision) | 打印决策 |
| print_plan(plan) | 打印计划 |
| main() | CLI dry-run 入口 |

### 6. 决策规则实现

15 条决策规则全部实现：

1. check_result=pass 且 verify_status=pass → no_rework_needed
2. failure_type 为空 → fail closed（missing_failure_type）
3. forbidden_files 非空 → fail closed（forbidden_files_present）
4. unclassified_files 非空 → fail closed（unclassified_files_present）
5. current_rework_round >= max_rework_rounds → fail closed
6. source_report_path 为空 → fail closed（missing_source_report）
7. rate_limit_or_api_429 → wait_for_rate_limit_recovery
8. forbidden_file_changed → fail closed
9. unclassified_changes → fail closed
10. dirty_workspace → fail closed
11. max_tasks_violation → fail closed
12. unknown_failure → fail closed
13. syntax_failed/tests_failed/report_missing/check_result_failed 且 target_files 明确 → 可返工
14. 涉及 runner.py 或 tools/ → user_approval_required=True
15. 任何不确定情况 → fail closed

### 7. 安全门规则

10 条安全门规则全部实现：

1. forbidden files 一律 fail closed
2. unclassified files 一律 fail closed
3. dirty workspace 一律 fail closed
4. max_rework_rounds 超限一律 fail closed
5. missing failure_type 一律 fail closed
6. missing target_files 一律 fail closed
7. missing source_report 一律 fail closed
8. runner.py / tools/ 涉及必须人工确认
9. 不允许自动 git add/commit/push
10. 返工后必须再次 verify（记录在 ReworkPlan 中）

### 8. CLI 参数

支持 12 个参数：
- --task（必填）
- --verify-status（必填）
- --check-result（必填）
- --failure-type
- --failure-summary
- --target-file（可重复）
- --forbidden-file（可重复）
- --unclassified-file（可重复）
- --current-rework-round
- --max-rework-rounds
- --source-report
- --print-plan

### 9. 已验证的 dry-run 场景

| 场景 | 预期 | 实际 | 结果 |
|------|------|------|------|
| pass 无需返工 | RESULT=pass, REWORK_ALLOWED=no, NEXT=no_rework_needed | 一致 | pass |
| syntax_failed + tools/ | RESULT=pass, REWORK_ALLOWED=yes, AUTO=no, APPROVAL=yes, PLAN=yes | 一致 | pass |
| forbidden file | RESULT=fail, REWORK_ALLOWED=no, NEXT=stop | 一致 | pass |
| rate_limit | RESULT=pass, NEXT=wait_for_rate_limit_recovery | 一致 | pass |

### 10. fail closed 行为确认

所有 fail closed 场景正确拦截：
- forbidden_files_present → stop
- unclassified_files_present → stop
- missing_failure_type → stop
- max_rework_rounds_exceeded → stop
- missing_source_report → stop
- target_files 为空 → stop
- forbidden_file_changed → stop
- unclassified_changes → stop
- dirty_workspace → stop
- max_tasks_violation → stop
- unknown_failure → stop

## 未修改的文件

- runner.py：未修改
- tools/rework_manager.py：未修改
- tools/continuous_verifier.py：未修改
- tools/execution_report_writer.py：未修改
- tools/git_backup_gate.py：未修改
- agents/*.md：未修改
- docs/agent-role-protocol.md：未修改
- 业务代码：未修改

## 安全保证

- TASK=T178
- IMPLEMENTATION_STATUS=done
- FILES_CREATED=tools/auto_mending_planner.py, reports/dev/T178-dev-report.md
- FILES_MODIFIED=docs/tasks.md
- BUSINESS_CODE_CHANGED=no
- FRAMEWORK_CODE_CHANGED=yes
- RUNNER_CHANGED=no
- TOOLS_CHANGED=yes
- AGENTS_CHANGED=no
- REAL_EXECUTION_CHANGED=no
- CLAUDE_AGENT_SDK_INTEGRATED=no
- AUTO_MENDING_PLANNER_IMPLEMENTED=yes
- DRY_RUN_IMPLEMENTED=yes
- REWORK_DECISION_IMPLEMENTED=yes
- REWORK_PLAN_IMPLEMENTED=yes
- FAILURE_CLASSIFICATION_IMPLEMENTED=yes
- REAL_REWORK_EXECUTED=no
- GIT_COMMANDS_EXECUTED=no
- PY_COMPILE_STATUS=pass
- DRY_RUN_SELF_CHECK=pass
- CHECK_RESULT=pass
- NEXT_PENDING=T179
- NEXT_STAGE=Stage 10

## 文件清单

### 本次新增文件

- tools/auto_mending_planner.py
- reports/dev/T178-dev-report.md

### 本次修改文件

- docs/tasks.md（T178 done，NEXT_PENDING → T179）

## 最终状态

```
TASK=T178
IMPLEMENTATION_STATUS=done
FILES_CREATED=tools/auto_mending_planner.py, reports/dev/T178-dev-report.md
FILES_MODIFIED=docs/tasks.md
BUSINESS_CODE_CHANGED=no
FRAMEWORK_CODE_CHANGED=yes
RUNNER_CHANGED=no
TOOLS_CHANGED=yes
AGENTS_CHANGED=no
REAL_EXECUTION_CHANGED=no
CLAUDE_AGENT_SDK_INTEGRATED=no
AUTO_MENDING_PLANNER_IMPLEMENTED=yes
DRY_RUN_IMPLEMENTED=yes
REWORK_DECISION_IMPLEMENTED=yes
REWORK_PLAN_IMPLEMENTED=yes
FAILURE_CLASSIFICATION_IMPLEMENTED=yes
REAL_REWORK_EXECUTED=no
GIT_COMMANDS_EXECUTED=no
PY_COMPILE_STATUS=pass
DRY_RUN_SELF_CHECK=pass
CHECK_RESULT=pass
NEXT_PENDING=T179
NEXT_STAGE=Stage 10
```
