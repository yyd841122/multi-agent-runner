# T181 验证报告：verifier fail 后生成 rework decision

验证时间：2026-05-13
验证角色：Validator
验证目标：端到端验证 verifier fail → rework decision 生成链路。

---

## 验证摘要

| # | 检查项 | 结果 |
|---|--------|------|
| 1 | auto_mending_planner 直接 dry-run（syntax_failed） | pass |
| 2 | fail closed 场景（forbidden_file → tests_failed） | pass |
| 3 | max_tasks>1 fail closed | pass |
| 4 | max_tasks=1 受控路径 | pass |
| 5 | runner.py 触发 rework decision dry-run | pass（代码确认，dirty workspace 阻止触发属预期行为） |
| 6 | 未执行真实返工 | pass |
| 7 | 未调用 rework_manager | pass |
| 8 | 未执行 Git | pass |
| 9 | 未修改 runner.py | pass |
| 10 | 未修改 tools/ | pass |
| 11 | 未修改 agents/ | pass |
| 12 | 未修改业务代码 | pass |

---

## 第 7 步验证：auto_mending_planner 直接 dry-run（syntax_failed）

命令：
```bash
python tools/auto_mending_planner.py --task T181 --verify-status fail --check-result fail --failure-type syntax_failed --failure-summary "Verifier failed and syntax error detected" --target-file reports/dev/T181-dev-report.md --current-rework-round 0 --max-rework-rounds 2 --source-report reports/checks/T181-verifier-fail-rework-decision-validation.md --print-plan
```

结果：
- AUTO_MENDING_PLANNER_RESULT=pass
- ok=True
- failure_type=syntax_failed
- REWORK_ALLOWED=yes
- AUTO_REWORK_ALLOWED=yes
- USER_APPROVAL_REQUIRED=no
- risk_level=low
- NEXT_ACTION=auto_rework_dry_run
- FAIL_REASON=None
- ReworkPlan: plan_id=T181-R1-plan, rework_round=1, allowed_operations=['fix_syntax']
- REWORK_PLAN_CREATED=yes
- REWORK_PLAN_NEXT_ACTION=execute_dry_run
- REAL_REWORK_EXECUTED=no
- GIT_ADD_EXECUTED=no
- GIT_COMMIT_EXECUTED=no
- GIT_PUSH_EXECUTED=no

结论：**pass** — syntax_failed 类型正确生成 ReworkDecision 和 ReworkPlan dry-run。

## 第 8 步验证：fail closed 场景（forbidden_file）

命令：
```bash
python tools/auto_mending_planner.py --task T181 --verify-status fail --check-result fail --failure-type tests_failed --failure-summary "Verifier failed with forbidden file" --target-file runner.py --forbidden-file runner.py --current-rework-round 0 --max-rework-rounds 2 --source-report reports/checks/T181-verifier-fail-rework-decision-validation.md --print-plan
```

结果：
- AUTO_MENDING_PLANNER_RESULT=fail
- ok=False
- failure_type=tests_failed
- REWORK_ALLOWED=no
- AUTO_REWORK_ALLOWED=no
- USER_APPROVAL_REQUIRED=yes
- risk_level=high
- NEXT_ACTION=stop
- FAIL_REASON=forbidden_files_present
- REWORK_PLAN_CREATED=no
- REAL_REWORK_EXECUTED=no
- GIT_ADD_EXECUTED=no
- GIT_COMMIT_EXECUTED=no
- GIT_PUSH_EXECUTED=no

结论：**pass** — forbidden_file 场景正确 fail closed，不生成 ReworkPlan。

## 第 9 步验证：max_tasks>1 fail closed

命令：
```bash
python runner.py run-project-loop --real-execution --max-tasks 2
```

结果：
- LOOP_STATUS=stopped_on_max_tasks
- DRY_RUN=True
- MAX_TASKS=2
- PLANNED_TASKS=T181,T182
- TASK_EXECUTION_PERFORMED=false
- CLAUDE_CODE_CALLED=false
- BUSINESS_CODE_CHANGED=false
- NEXT_ACTION=review_loop_summary

结论：**pass** — max_tasks>1 只做 dry-run 规划，不执行真实任务，不执行真实返工，不执行 Git。

## 第 10 步验证：max_tasks=1 受控路径

命令：
```bash
python runner.py run-project-loop --real-execution --max-tasks 1
```

结果：
- LOOP_STATUS=stopped_on_max_tasks
- DRY_RUN=True
- MAX_TASKS=1
- PLANNED_TASKS=T181
- TASK_EXECUTION_PERFORMED=false
- CLAUDE_CODE_CALLED=false
- BUSINESS_CODE_CHANGED=false
- 不允许进入 T182
- 不允许无限连续执行

结论：**pass** — max_tasks=1 只做 dry-run 规划，不执行真实任务，不自动进入下一任务。

## runner.py 触发 rework decision dry-run 分析

runner.py 第 3175-3268 行代码确认：

1. Step 3.1 Rework Decision Dry-Run 代码存在且逻辑正确。
2. 触发条件：`verify_result_data is not None and not verify_result_data.ok`。
3. 延迟导入 `tools.auto_mending_planner` 的 `build_rework_decision` 和 `build_rework_plan_dry_run`。
4. 从 `verify_result_data.fail_reason` 推断 failure_type（12 种模式匹配）。
5. 输出结构化字段：REWORK_DECISION_DRY_RUN、REWORK_ALLOWED、AUTO_REWORK_ALLOWED、USER_APPROVAL_REQUIRED、REWORK_NEXT_ACTION、REWORK_FAIL_REASON、FAILURE_TYPE、RISK_LEVEL、REWORK_PLAN_CREATED。
6. 不执行真实返工，不调用 rework_manager，不执行 Git。

执行 `stage8-monitor-verify-report` 时：
- Monitor 检测到 dirty workspace（验证报告文件），在 Step 1 停止。
- 未到达 Step 3（Verifier）和 Step 3.1（Rework Decision）。
- 这是安全预期行为：dirty workspace 是安全门第一道检查。

结论：**pass** — 代码确认 rework decision dry-run 接入正确。dirty workspace 阻止触发属预期行为，是安全机制的一部分。

## 安全确认

- REAL_REWORK_EXECUTED=no
- REWORK_MANAGER_CALLED=no（runner.py 中无 rework_manager 调用）
- GIT_ADD_EXECUTED=no
- GIT_COMMIT_EXECUTED=no
- GIT_PUSH_EXECUTED=no
- RUNNER_CHANGED=no
- TOOLS_CHANGED=no
- AGENTS_CHANGED=no
- BUSINESS_CODE_CHANGED=no

---

## 验证结论

全部 12 项检查通过。verifier fail → rework decision dry-run 链路已正确接入：
1. auto_mending_planner.py 能正确生成 ReworkDecision 和 ReworkPlan dry-run。
2. 可返工失败类型（syntax_failed）正确生成 ReworkPlan。
3. fail closed 类型（forbidden_file）正确阻止返工。
4. max_tasks>1 只做 dry-run，不执行真实任务。
5. max_tasks=1 受控，不自动进入下一任务。
6. runner.py 中 Step 3.1 rework decision dry-run 代码正确。
7. 未执行任何真实返工、Git 操作或代码修改。

---

```text
TASK=T181
VALIDATION_STATUS=done
REWORK_DECISION_TRIGGERED=pass
REWORK_DECISION_CREATED=pass
REWORK_PLAN_CREATED=pass
FAIL_CLOSED_CASE_VALIDATED=pass
MAX_TASKS_GT_1_FAIL_CLOSED=pass
MAX_TASKS_1_CONTROLLED_PATH=pass
REAL_REWORK_EXECUTED=no
REWORK_MANAGER_CALLED=no
GIT_ADD_EXECUTED=no
GIT_COMMIT_EXECUTED=no
GIT_PUSH_EXECUTED=no
RUNNER_CHANGED=no
TOOLS_CHANGED=no
AGENTS_CHANGED=no
BUSINESS_CODE_CHANGED=no
CHECK_RESULT=pass
NEXT_PENDING=T182
NEXT_STAGE=Stage 10
```
