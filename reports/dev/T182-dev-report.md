# T182 Dev Report：接入 rework_manager 受控返工 dry-run

任务编号：T182
完成时间：2026-05-13
角色：Developer
目标：对接 auto_mending_planner 与 rework_manager，实现受控返工 dry-run。

---

## 1. runner.py 的具体修改点

**文件**：`runner.py`
**位置**：Step 3.1 Rework Decision Dry-Run 之后，Step 4 Generate Report 之前
**新增**：Step 3.2 Controlled Rework Dry-Run

在 `stage8-monitor-verify-report` 子命令的 Step 3.1 中，当 `rework_decision_data.rework_allowed=True` 时，追加 Step 3.2 受控返工 dry-run。

修改范围：约 60 行新增代码，无已有逻辑变更。

## 2. 受控 rework dry-run 如何接入

在 runner.py Step 3.1 的 try 块内，rework plan 输出完成后，新增 Step 3.2 逻辑：

1. **触发条件**：`rework_decision_data.ok=True` 且 `rework_decision_data.rework_allowed=True`
2. **安全检查**（保守桥接，不调用 rework_manager）：
   - 轮次验证：`1 <= rework_round <= max_rework_rounds`
   - target_files 非空检查
   - failure_type 不属于 fail-closed 类型
   - risk_level=critical 时要求 user_approval
3. **通过时输出**：CONTROLLED_REWORK_DRY_RUN=pass，及 rework 轮次、目标文件、风险等级等
4. **未通过时输出**：CONTROLLED_REWORK_DRY_RUN=fail，及 fail_reason
5. **不触发时输出**：CONTROLLED_REWORK_DRY_RUN=skipped

## 3. 是否调用了 rework_manager 的 dry-run / preparation 路径

**未直接调用 rework_manager.py**。

原因：
- rework_manager.py 面向子项目 game（如 down-100-floors-game），需要 rework_prompt.md 文件和严格确认格式
- 主框架连续执行链路的返工上下文与子项目不同（任务来源、报告路径、文件范围）
- 直接调用会导致路径不匹配和功能耦合

替代方案：
- 在 runner.py 内部实现保守桥接 helper，复用 rework_manager 的安全检查概念（轮次控制、确认要求）
- 不修改 rework_manager.py，保持子项目返工能力不变
- T183 可验证 runner.py 的受控返工 dry-run 输出

## 4. 为什么本任务没有执行真实返工

- Stage 10 当前阶段只实现 dry-run，不开放真实返工
- 所有返工必须经过人工验收（docs/agent-role-protocol.md Section 10 Rule 9-10）
- REAL_REWORK_EXECUTED=no 在所有路径中强制输出

## 5. 为什么没有修改 tools/rework_manager.py

- rework_manager.py 服务于子项目 game 的返工链路，功能独立完整
- 主框架连续执行链路需要不同的返工上下文和输入格式
- 修改 rework_manager.py 会影响已有子项目返工能力
- 保守桥接方案在 runner.py 内部实现，不影响已有模块

## 6. 为什么没有修改 tools/auto_mending_planner.py

- auto_mending_planner.py 已在 T178 实现完整，T179 验证通过
- T180 已正确接入 runner.py
- T182 只需消费 auto_mending_planner 的输出（ReworkDecision / ReworkPlan）
- 不需要修改 auto_mending_planner.py

## 7. 为什么没有执行 run-project-loop real execution

- T182 是实现任务，T183 是验证任务
- 真实验证留给 T183：验证返工后 verify → report → git backup dry-run 链路
- T182 只需确认 py_compile 通过和 dry-run plan 正常

## 8. T183 将负责验证返工后 verify → report → git backup dry-run 链路

T183 验证范围：
1. Step 3.2 controlled rework dry-run 输出正确性
2. 返工后二次 verify 链路（当前 dry-run 模式下不触发，但代码路径存在）
3. 返工后 report 生成
4. 返工后 GitBackupGate dry-run
5. 全链路 fail closed 行为

---

## 文件变更

| 文件 | 操作 | 说明 |
|------|------|------|
| runner.py | 修改 | 新增 Step 3.2 Controlled Rework Dry-Run |
| docs/tasks.md | 修改 | T182 标记为 done |
| reports/dev/T182-dev-report.md | 新建 | T182 dev report |

---

```text
TASK=T182
IMPLEMENTATION_STATUS=done
FILES_CREATED=reports/dev/T182-dev-report.md
FILES_MODIFIED=runner.py, docs/tasks.md
BUSINESS_CODE_CHANGED=no
FRAMEWORK_CODE_CHANGED=yes
RUNNER_CHANGED=yes
TOOLS_CHANGED=no
AGENTS_CHANGED=no
REAL_EXECUTION_CHANGED=controlled_rework_dry_run_only
CLAUDE_AGENT_SDK_INTEGRATED=no
CONTROLLED_REWORK_DRY_RUN_INTEGRATED=yes
REWORK_MANAGER_DRY_RUN_CALLED=no
REWORK_MANAGER_REAL_EXECUTION_CALLED=no
AUTO_MENDING_PLANNER_MODIFIED=no
REWORK_MANAGER_MODIFIED=no
REAL_REWORK_EXECUTED=no
TARGET_FILES_MODIFIED=no
GIT_COMMANDS_EXECUTED=no
RUN_PROJECT_LOOP_REAL_EXECUTED=no
MAX_TASKS_GT_1_ALLOWED=no
PY_COMPILE_STATUS=pass
CHECK_RESULT=pass
NEXT_PENDING=T183
NEXT_STAGE=Stage 10
```
