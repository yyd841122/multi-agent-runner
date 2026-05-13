# T195 Dev Report：规划 Stage 12 产品化与稳定性入口

任务编号：T195
完成时间：2026-05-13
角色：Architect Agent + Stage 12 Productization and Stability Planning Architect
目标：规划 Stage 12 产品化与稳定性入口，只规划不实现。

---

## 1. 规划概述

本任务完成 Stage 12 产品化与稳定性入口规划。Stage 12 的核心目标不是开放真实自动执行，而是对当前框架进行产品化、稳定性、可恢复性、可维护性、可验收性建设。

---

## 2. 前置基础确认

### 2.1 Stage 8 基础

- monitor → verify → report 最小闭环成立。
- task_monitor.py、continuous_verifier.py、execution_report_writer.py 已实现。
- max_tasks=1 受控单步执行稳定，max_tasks>1 fail closed。
- 未开放无限真实连续执行。

### 2.2 Stage 9 基础

- GitBackupGate dry-run 安全链成立。
- git_backup_gate.py 实现文件分类、fail closed、approval record。
- 未开放真实自动 git add / commit / push。

### 2.3 Stage 10 基础

- rework dry-run 安全链成立。
- auto_mending_planner.py 实现 11 种失败分类、15 条决策规则。
- Agent 角色协议层已完善。
- 未开放真实自动返工。

### 2.4 Stage 11 基础

- external request → task proposal dry-run 安全链成立。
- local request inbox、GitHub Issue fixture、统一 proposal bridge 已实现。
- allowed_to_execute=False 硬编码。
- 未开放真实外部执行。

---

## 3. Stage 12 核心规划

### 3.1 为什么先做 run_state_manager / checkpoint

当前系统缺乏统一的运行状态管理。每次执行都是独立的，如果中途被 API 429、进程中断或系统异常打断，无法从断点恢复。run_state_manager 和 checkpoint 是稳定性的基础设施，应在开放任何真实执行能力之前完成。

### 3.2 为什么要正式纳入 API 429 / 5 小时限额恢复机制

auto_mending_planner 已识别 rate_limit_or_api_429 失败类型，但无自动恢复机制。当遇到 429 时，需要人工处理。Stage 12 应建立限额恢复 dry-run 机制，包括检测 429、提取 reset time、写入 checkpoint、等待恢复、恢复前安全检查。

### 3.3 dirty workspace protection

当前 task_monitor.py 检查 dirty workspace，但缺乏统一保护策略。Stage 12 应标准化 dirty workspace 检查，确保 resume、rate-limit recovery、proposal apply 等所有入口点都有 dirty workspace 保护。

### 3.4 proposal approval / apply

当前 proposal 只生成不执行。Stage 12 应建立 proposal approval record，让 proposal 可被人工确认后安全写入 docs/tasks.md 草案。apply 后仍不执行任务，task execution 仍需走受控 runner 流程。

### 3.5 reports index / audit trail

当前 reports/ 下有 dev、checks、task-proposals、external-requests、github-issues、git、continuous-runs 等目录，但缺乏统一索引。Stage 12 应建立 reports index，便于回溯每个阶段的证据。

---

## 4. Stage 12 规划方向

| # | 方向 | 规划内容 |
|---|------|----------|
| 1 | CLI Experience | 统一命令命名、dry-run 参数、输出状态块、--explain/--summary/--json、安全提示 |
| 2 | Run State Manager | RunState dataclass、run_id、task_id、stage、step、status、resume_allowed |
| 3 | Checkpoint & Resume | 步骤级 checkpoint、中断恢复、dirty workspace fail closed |
| 4 | API 429 / 5h Limit Recovery | RateLimitRecoveryState、检测 429、等待恢复、恢复前安全检查 |
| 5 | Dirty Workspace Protection | 统一检查、未分类变更 fail closed、恢复时重新检查 |
| 6 | Proposal Approval & Apply | ProposalApprovalRecord、人工确认、apply 只写草案 |
| 7 | Report Index & Audit Trail | ReportsIndex、汇总所有报告、按 task_id/stage/日期过滤 |
| 8 | Error Codes & Fail Closed | 10 个标准错误码、统一格式 |
| 9 | Future Product Interfaces | Web UI、API、n8n、GitHub Actions、Dashboard、Report Viewer、Approval Center |

---

## 5. 后续任务 T196-T207

| # | 任务 | 角色 |
|---|------|------|
| T196 | 设计 run_state_manager.py 与 checkpoint 数据结构 | Architect |
| T197 | 实现 run_state_manager.py dry-run | Developer |
| T198 | 验证 checkpoint resume fail closed | Validator |
| T199 | 设计 API 429 / 5 小时限额恢复机制 | Architect |
| T200 | 实现 rate-limit recovery dry-run | Developer |
| T201 | 验证 dirty workspace resume protection | Validator |
| T202 | 设计 external proposal approval record | Architect |
| T203 | 实现 proposal approval record dry-run | Developer |
| T204 | 验证 proposal apply 不执行任务 | Validator |
| T205 | 设计 reports index 与 audit trail | Architect |
| T206 | 实现 reports index dry-run | Developer |
| T207 | Stage 12 最终状态审查 | Reviewer |

---

## 6. 未修改说明

1. 本次只做规划，未实现新功能。
2. 未修改 runner.py。
3. 未修改 tools/。
4. 未修改 agents/。
5. 未修改业务代码。
6. 未修改 docs/agent-role-protocol.md。
7. 未实现 run_state_manager.py。
8. 未实现限额恢复。
9. 未实现 proposal apply。
10. 未实现 report index。
11. 未启用外部真实执行。
12. 未创建 Web UI / API / n8n / GitHub Actions。
13. 未执行 Git。

---

## 文件变更

| 文件 | 操作 | 说明 |
|------|------|------|
| docs/stage12-productization-and-stability-plan.md | 新建 | Stage 12 产品化与稳定性规划文档 |
| reports/dev/T195-dev-report.md | 新建 | T195 dev report |
| docs/tasks.md | 修改 | T195 标记为 done，新增 T196-T207 pending，NEXT_PENDING 指向 T196 |

---

```text
TASK=T195
PLANNING_STATUS=done
FILES_CREATED=docs/stage12-productization-and-stability-plan.md, reports/dev/T195-dev-report.md
FILES_MODIFIED=docs/tasks.md
BUSINESS_CODE_CHANGED=no
FRAMEWORK_CODE_CHANGED=no
RUNNER_CHANGED=no
TOOLS_CHANGED=no
AGENTS_CHANGED=no
REAL_EXECUTION_CHANGED=no
CLAUDE_AGENT_SDK_INTEGRATED=no
STAGE12_PLAN_CREATED=yes
PRODUCTIZATION_PLANNED=yes
STABILITY_PLANNED=yes
RUN_STATE_MANAGER_PLANNED=yes
CHECKPOINT_RESUME_PLANNED=yes
RATE_LIMIT_RECOVERY_PLANNED=yes
DIRTY_WORKSPACE_PROTECTION_PLANNED=yes
PROPOSAL_APPROVAL_PLANNED=yes
REPORT_INDEX_PLANNED=yes
REAL_EXTERNAL_EXECUTION_ENABLED=no
CHECK_RESULT=pass
NEXT_PENDING=T196
NEXT_STAGE=Stage 12
```
