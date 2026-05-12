# T181 Dev Report：验证 verifier fail 后生成 rework decision

任务编号：T181
完成时间：2026-05-13
角色：Validator
目标：端到端验证 verifier fail → rework decision 生成链路。

---

## 任务说明

本任务只做验证，不实现新功能。验证内容：

1. runner.py 中 verifier fail → rework decision dry-run 接入可被触发（代码确认）。
2. auto_mending_planner.py 能生成 ReworkDecision。
3. 可返工失败类型能生成 ReworkPlan dry-run。
4. fail closed 类型不会生成真实返工。
5. max_tasks>1 仍然 fail closed。
6. max_tasks=1 仍然受控。

---

## 验证结果

### 1. auto_mending_planner 直接 dry-run（syntax_failed）

- AUTO_MENDING_PLANNER_RESULT=pass
- ok=True, REWORK_ALLOWED=yes, AUTO_REWORK_ALLOWED=yes
- ReworkPlan: plan_id=T181-R1-plan, REWORK_PLAN_CREATED=yes
- REAL_REWORK_EXECUTED=no, GIT 未执行

### 2. fail closed 场景（forbidden_file）

- AUTO_MENDING_PLANNER_RESULT=fail
- ok=False, REWORK_ALLOWED=no, AUTO_REWORK_ALLOWED=no
- NEXT_ACTION=stop, FAIL_REASON=forbidden_files_present
- REWORK_PLAN_CREATED=no

### 3. max_tasks>1 fail closed

- DRY_RUN=True, TASK_EXECUTION_PERFORMED=false
- BUSINESS_CODE_CHANGED=false, CLAUDE_CODE_CALLED=false

### 4. max_tasks=1 受控路径

- DRY_RUN=True, TASK_EXECUTION_PERFORMED=false
- 不自动进入 T182，不无限执行

### 5. runner.py rework decision 接入

- 代码确认：runner.py 第 3175-3268 行 Step 3.1 Rework Decision Dry-Run 正确存在。
- 延迟导入 build_rework_decision 和 build_rework_plan_dry_run。
- 12 种 failure_type 模式匹配逻辑正确。
- 输出 REWORK_DECISION_DRY_RUN、REWORK_ALLOWED 等结构化字段。
- 不执行真实返工，不调用 rework_manager，不执行 Git。
- 执行 stage8-monitor-verify-report 时因 dirty workspace 在 Step 1 停止，未触发 Step 3.1，属预期安全行为。

### 6. 安全确认

- 本任务只验证，不修改 runner.py。
- 本任务只验证，不修改 tools/。
- 未执行真实返工。
- 未调用 rework_manager。
- 未执行 Git。

---

## 文件变更

| 文件 | 操作 | 说明 |
|------|------|------|
| reports/checks/T181-verifier-fail-rework-decision-validation.md | 新建 | T181 验证报告 |
| reports/dev/T181-dev-report.md | 新建 | T181 dev report |
| docs/tasks.md | 修改 | T181 标记为 done |

---

```text
TASK=T181
VALIDATION_STATUS=done
FILES_CREATED=reports/checks/T181-verifier-fail-rework-decision-validation.md, reports/dev/T181-dev-report.md
FILES_MODIFIED=docs/tasks.md
BUSINESS_CODE_CHANGED=no
FRAMEWORK_CODE_CHANGED=no
RUNNER_CHANGED=no
TOOLS_CHANGED=no
AGENTS_CHANGED=no
REAL_EXECUTION_CHANGED=no
CLAUDE_AGENT_SDK_INTEGRATED=no
REWORK_DECISION_TRIGGERED=pass
REWORK_DECISION_CREATED=pass
REWORK_PLAN_CREATED=pass
FAIL_CLOSED_CASE_VALIDATED=pass
MAX_TASKS_GT_1_FAIL_CLOSED=pass
MAX_TASKS_1_CONTROLLED_PATH=pass
REAL_REWORK_EXECUTED=no
REWORK_MANAGER_CALLED=no
GIT_COMMANDS_EXECUTED=no
CHECK_RESULT=pass
NEXT_PENDING=T182
NEXT_STAGE=Stage 10
```
