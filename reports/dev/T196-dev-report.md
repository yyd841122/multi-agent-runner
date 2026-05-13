# T196 Dev Report：设计 run_state_manager.py 与 checkpoint 数据结构

任务编号：T196
完成时间：2026-05-13
角色：Architect Agent + Stage 12 Run State and Checkpoint Design Architect
目标：设计 run_state_manager.py 与 checkpoint 数据结构，只设计不实现。

---

## 1. 设计概述

本任务完成 run_state_manager.py 与 checkpoint 数据结构的设计。设计文档为 docs/stage12-run-state-and-checkpoint-design.md，包含 16 个章节。

---

## 2. 设计的核心数据结构

### 2.1 RunState（25 字段）

RunState 记录一次执行的完整生命周期。包含身份标识（run_id、project_root、repo_name）、任务关联（current_task、current_stage、next_pending、next_stage）、执行上下文（command、mode）、状态追踪（status、started_at、updated_at）、步骤追踪（current_step、last_successful_step、total_steps）、恢复控制（resume_allowed、resume_reason、blocked_reason）、工作区状态（dirty_workspace_detected、unclassified_changes）、限额状态（rate_limit_detected、rate_limit_reset_at）、检查点（checkpoint_path）、错误（last_error）、元数据（metadata）。

用途：为每次执行提供唯一标识和完整状态记录，支持中断恢复和审计追踪。

### 2.2 Checkpoint（22 字段）

Checkpoint 记录每个关键步骤的完整快照。包含身份标识、步骤信息、执行记录、文件变更、Git 状态快照（git_status_before/after）、任务状态快照（next_pending/stage before/after）、安全检查（resume_allowed_after_checkpoint）、备注。

用途：为每个关键步骤记录完整上下文，支持从中断点精确恢复。

### 2.3 ResumeDecision（16 字段）

ResumeDecision 判断是否允许从中断处恢复。包含判断结果（ok）、恢复决策（can_resume、resume_from_checkpoint、resume_step）、人工确认（requires_user_confirmation）、工作区检查（dirty_workspace_detected、unclassified_changes）、任务一致性（next_pending_matches、next_stage_matches）、限额检查（rate_limit_wait_required）、阻塞信息（blocked_reason、warnings）、下一步行动（next_action）。

用途：明确判断是否可以恢复，所有不确定状态必须 fail closed。

### 2.4 DirtyWorkspaceSnapshot（10 字段）

DirtyWorkspaceSnapshot 记录工作区状态快照。包含快照时间、git status 输出、分类结果（allowed/modified/untracked/staged/unclassified）、安全判断（safe_to_continue、safe_to_commit、fail_reason）。

用途：在 resume 和 rate-limit recovery 时统一记录和判断工作区状态。

### 2.5 RateLimitState（14 字段）

RateLimitState 记录 API 限额状态。包含检测信息（detected、provider、error_code、error_message）、请求上下文（request_id、reset_at、wait_seconds）、影响范围（captured_at、affected_task、affected_step）、恢复信息（checkpoint_path、resume_allowed_after_reset、requires_workspace_recheck）、备注。

用途：为 API 429 / 5 小时限额恢复提供状态记录。requires_workspace_recheck 始终为 True，确保恢复前必须重新检查工作区。

---

## 3. API 429 / 5 小时限额恢复设计

限额恢复流程已设计为 8 步：检测 429 → 解析 reset_at → 写入 RateLimitState → 写入 Checkpoint → 更新 RunState → 停止操作 → 外部等待 → 恢复流程。恢复流程包含 5 层安全检查：reset_at 是否已过、git status 重新检查、NEXT_PENDING / NEXT_STAGE 重新验证、变更分类、ResumeDecision 生成。

---

## 4. Dirty Workspace Fail Closed 规则

设计了 10 条 fail closed 规则，包括：未分类变更、NEXT_PENDING 不匹配、NEXT_STAGE 不匹配、checkpoint 缺失、task_id 不匹配、git 操作中断、文件写入中断、rate limit 未到、外部请求不可信、用户未确认。

---

## 5. T197 实现范围

T197 应只实现 dry-run：创建 tools/run_state_manager.py，实现 5 个 dataclass，支持 create-run-state、write-checkpoint、evaluate-resume、simulate-rate-limit 四个 dry-run 功能，输出 reports/run-state/ 报告。不修改 runner.py，不接入真实执行，不执行 Git，fail closed。

---

## 6. 未修改说明

1. 本次只做设计，未实现 Python 代码。
2. 未创建 tools/run_state_manager.py。
3. 未修改 runner.py。
4. 未修改 tools/。
5. 未修改 agents/。
6. 未修改业务代码。
7. 未创建 runtime/ 目录。
8. 未创建 checkpoint 文件。
9. 未启用真实恢复。
10. 未启用 rate-limit recovery。
11. 未执行 Git。
12. 未创建 .github/workflows。
13. 未启用外部真实执行。

---

## 文件变更

| 文件 | 操作 | 说明 |
|------|------|------|
| docs/stage12-run-state-and-checkpoint-design.md | 新建 | Run state 与 checkpoint 设计文档 |
| reports/dev/T196-dev-report.md | 新建 | T196 dev report |
| docs/tasks.md | 修改 | T196 标记为 done，NEXT_PENDING 指向 T197 |

---

```text
TASK=T196
DESIGN_STATUS=done
FILES_CREATED=docs/stage12-run-state-and-checkpoint-design.md, reports/dev/T196-dev-report.md
FILES_MODIFIED=docs/tasks.md
BUSINESS_CODE_CHANGED=no
FRAMEWORK_CODE_CHANGED=no
RUNNER_CHANGED=no
TOOLS_CHANGED=no
AGENTS_CHANGED=no
REAL_EXECUTION_CHANGED=no
CLAUDE_AGENT_SDK_INTEGRATED=no
RUN_STATE_MANAGER_DESIGNED=yes
RUN_STATE_DESIGNED=yes
CHECKPOINT_DESIGNED=yes
RESUME_DECISION_DESIGNED=yes
DIRTY_WORKSPACE_SNAPSHOT_DESIGNED=yes
RATE_LIMIT_STATE_DESIGNED=yes
RESUME_ALLOWED_RULES_DESIGNED=yes
RATE_LIMIT_RECOVERY_FLOW_DESIGNED=yes
DIRTY_WORKSPACE_RESUME_FLOW_DESIGNED=yes
RUN_STATE_MANAGER_IMPLEMENTED=no
CHECKPOINT_FILES_CREATED=no
REAL_RESUME_ENABLED=no
GIT_COMMANDS_EXECUTED=no
CHECK_RESULT=pass
NEXT_PENDING=T197
NEXT_STAGE=Stage 12
```
