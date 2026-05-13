# Stage 12 Run State and Checkpoint Design

设计时间：2026-05-13
设计角色：Architect Agent + Stage 12 Run State and Checkpoint Design Architect
目标：设计 run_state_manager.py 与 checkpoint 数据结构，只设计不实现。

---

## 1. Background

1. Stage 12 的核心目标是**产品化与稳定性**。当前系统已有 Stage 8-11 的多条 dry-run 安全链，但缺乏统一的运行状态管理。
2. 当前缺少统一 **run state**。每次执行是独立的，无法追踪 run_id、task_id、步骤、状态等结构化信息。各工具各自输出 `KEY=value` 格式的状态块，但没有持久化的状态记录。
3. 当前缺少 **checkpoint resume**。如果执行中途被 API 429、进程中断、系统异常打断，无法从断点恢复，只能从头开始。
4. 当前遇到过 **API 429 / 5 小时限额中断**。auto_mending_planner 已识别 `rate_limit_or_api_429` 失败类型，但无自动恢复机制。用户需要手动等待限额恢复后重新执行。
5. 当前遇到过 **Claude Code 长时间卡住**的问题。进程可能被意外终止，此时缺乏状态记录来判断中断前的进度。
6. run_state_manager 的目标是让**中断、恢复、限额等待、dirty workspace 保护**全部可审计、可追踪、可回溯。
7. **本设计不实现代码。** T197 才会实现 tools/run_state_manager.py dry-run。

---

## 2. Design Goal

run_state_manager 的设计目标：

1. **记录当前运行状态**。每次执行分配唯一 run_id，记录完整的执行生命周期。
2. **记录当前任务和阶段**。通过 current_task、current_stage、next_pending、next_stage 关联 docs/tasks.md 中的任务。
3. **记录当前步骤**。通过 current_step 和 last_successful_step 追踪执行管线中的位置。
4. **记录最后成功步骤**。中断后从 last_successful_step 的下一步恢复。
5. **记录当前是否可恢复**。通过 resume_allowed 和 resume_reason 明确判断。
6. **记录中断原因**。通过 blocked_reason 和 last_error 明确记录。
7. **记录 API 429 / reset time**。通过 RateLimitState 记录限额状态和恢复时间。
8. **记录 dirty workspace 状态**。通过 DirtyWorkspaceSnapshot 记录工作区快照。
9. **支持 fail closed resume decision**。通过 ResumeDecision 明确判断是否允许恢复，不确定则 fail closed。
10. **为后续 dry-run 实现提供结构**。所有数据结构设计完成后，T197 实现 dry-run 写入和读取。

---

## 3. Non-goals

本设计明确不做：

1. **不实现 tools/run_state_manager.py**。只设计数据结构和规则。
2. **不修改 runner.py**。后续 T197 dry-run 也不修改 runner.py。
3. **不接入真实自动恢复**。所有恢复路径在 T198 验证前为 dry-run。
4. **不等待真实 rate limit reset**。RateLimitState 只记录状态，不执行等待。
5. **不执行真实任务**。设计不涉及任务执行。
6. **不执行真实返工**。与 auto_mending_planner 解耦。
7. **不执行真实 Git backup**。与 GitBackupGate 解耦。
8. **不修改 docs/tasks.md 之外的业务流程**。run_state_manager 只读取 docs/tasks.md。
9. **不绕过人工确认**。所有 resume 必须经过人工确认或 fail closed。
10. **不开放真实外部执行**。与 external_request_task_proposal 解耦。

---

## 4. Proposed File Layout

设计未来文件路径：

```
runtime/
  run-state/
    current-run-state.json          # 当前活跃 run state（最新一次执行）
    runs/
      RUN-YYYYMMDD-HHMMSS.json      # 历史执行记录（每次执行一个文件）
  checkpoints/
    RUN-YYYYMMDD-HHMMSS/
      checkpoint-001.json            # 步骤 1 的 checkpoint
      checkpoint-002.json            # 步骤 2 的 checkpoint
      checkpoint-003.json            # 步骤 3 的 checkpoint
  rate-limits/
    latest-rate-limit.json           # 最新限额状态
```

说明：

1. **T196 只设计，不创建 runtime/**。设计文档只描述路径和格式。
2. **T197 可实现 dry-run 写入**。T197 实现时可以选择写入 `reports/run-state/`（dry-run 报告）或 `runtime/`（但为 dry-run 模式）。具体由 T197 决定。
3. **后续真实接入前必须先验证 dirty workspace protection**。不允许在没有 dirty workspace 保护的情况下创建真实 runtime/ 文件。
4. **所有文件使用 JSON 格式**。便于人类阅读和程序解析，不引入额外依赖。

---

## 5. RunState Data Structure

RunState 记录一次执行的完整生命周期。

```python
from dataclasses import dataclass, field
from typing import Optional, List, Dict

@dataclass
class RunState:
    """Run State - 记录一次执行的完整生命周期"""

    # === 身份标识 ===
    run_id: str                           # 格式：RUN-YYYYMMDD-HHMMSS，例如 RUN-20260513-143022
    project_root: str                     # 项目根目录绝对路径
    repo_name: str                        # 仓库名称，例如 multi-agent-runner

    # === 任务关联 ===
    current_task: str                     # 当前任务 ID，例如 T196
    current_stage: str                    # 当前阶段，例如 Stage 12
    next_pending: str                     # 当前 NEXT_PENDING，例如 T197
    next_stage: str                       # 当前 NEXT_STAGE，例如 Stage 12

    # === 执行上下文 ===
    command: str                          # 触发命令，例如 stage8-monitor-verify-report --max-tasks 1
    mode: str                             # 执行模式：dry_run / real_execution（始终为 dry_run）

    # === 状态 ===
    status: str                           # 运行状态枚举，见 Section 10
    started_at: str                       # ISO 8601，执行开始时间
    updated_at: str                       # ISO 8601，最后更新时间

    # === 步骤追踪 ===
    current_step: str                     # 当前步骤名称，例如 monitor / trial / verify / report / backup / rework / proposal
    last_successful_step: Optional[str]   # 最后成功完成的步骤
    total_steps: int                      # 预期总步骤数

    # === 恢复控制 ===
    resume_allowed: bool                  # 是否允许从中断处恢复
    resume_reason: Optional[str]          # 允许/不允许恢复的原因
    blocked_reason: Optional[str]         # 阻塞原因

    # === 工作区状态 ===
    dirty_workspace_detected: bool        # 是否检测到 dirty workspace
    unclassified_changes: List[str]       # 未分类文件变更列表

    # === 限额状态 ===
    rate_limit_detected: bool             # 是否检测到 API 429
    rate_limit_reset_at: Optional[str]    # ISO 8601，限额预计恢复时间

    # === 检查点 ===
    checkpoint_path: Optional[str]        # 最新 checkpoint 文件路径

    # === 错误 ===
    last_error: Optional[str]             # 最后错误信息

    # === 元数据 ===
    metadata: Dict[str, str] = field(default_factory=dict)  # 扩展元数据
```

### RunState 字段说明

| # | 字段 | 类型 | 说明 |
|---|------|------|------|
| 1 | run_id | str | 唯一执行 ID，格式 RUN-YYYYMMDD-HHMMSS |
| 2 | project_root | str | 项目根目录绝对路径 |
| 3 | repo_name | str | 仓库名称 |
| 4 | current_task | str | 当前执行的任务 ID |
| 5 | current_stage | str | 当前所属阶段 |
| 6 | next_pending | str | docs/tasks.md 中的 NEXT_PENDING |
| 7 | next_stage | str | docs/tasks.md 中的 NEXT_STAGE |
| 8 | command | str | 触发执行的命令 |
| 9 | mode | str | dry_run 或 real_execution |
| 10 | status | str | 运行状态枚举 |
| 11 | started_at | str | ISO 8601 开始时间 |
| 12 | updated_at | str | ISO 8601 最后更新时间 |
| 13 | current_step | str | 当前步骤 |
| 14 | last_successful_step | str | 最后成功步骤 |
| 15 | total_steps | int | 预期总步骤数 |
| 16 | resume_allowed | bool | 是否允许恢复 |
| 17 | resume_reason | str | 恢复原因说明 |
| 18 | blocked_reason | str | 阻塞原因 |
| 19 | dirty_workspace_detected | bool | 是否有 dirty workspace |
| 20 | unclassified_changes | List[str] | 未分类变更文件 |
| 21 | rate_limit_detected | bool | 是否有 API 429 |
| 22 | rate_limit_reset_at | str | 限额恢复时间 |
| 23 | checkpoint_path | str | 最新 checkpoint 路径 |
| 24 | last_error | str | 最后错误 |
| 25 | metadata | Dict[str, str] | 扩展元数据 |

---

## 6. Checkpoint Data Structure

Checkpoint 记录每个关键步骤的完整快照。

```python
@dataclass
class Checkpoint:
    """Checkpoint - 记录关键步骤的完整快照"""

    # === 身份标识 ===
    checkpoint_id: str                    # 格式：CP-YYYYMMDD-HHMMSS-NNN，例如 CP-20260513-143025-001
    run_id: str                           # 关联的 run_id
    task_id: str                          # 关联的 task_id

    # === 步骤信息 ===
    stage: str                            # 所属阶段，例如 Stage 12
    step_name: str                        # 步骤名称，例如 monitor / verify / report / backup / rework
    step_index: int                       # 步骤序号（从 1 开始）
    created_at: str                       # ISO 8601，checkpoint 创建时间
    status: str                           # 步骤状态：success / failed / skipped

    # === 执行记录 ===
    command_planned: Optional[str]        # 计划执行的命令
    command_executed: Optional[str]       # 实际执行的命令
    output_summary: Optional[str]         # 输出摘要（200 字以内）

    # === 文件变更 ===
    files_expected: List[str]             # 预期变更文件列表
    files_changed: List[str]              # 实际变更文件列表

    # === Git 状态快照 ===
    git_status_before: Optional[str]      # 步骤前 git status --short 输出
    git_status_after: Optional[str]       # 步骤后 git status --short 输出

    # === 任务状态快照 ===
    next_pending_before: Optional[str]    # 步骤前 NEXT_PENDING
    next_pending_after: Optional[str]     # 步骤后 NEXT_PENDING
    next_stage_before: Optional[str]      # 步骤前 NEXT_STAGE
    next_stage_after: Optional[str]       # 步骤后 NEXT_STAGE

    # === 安全检查 ===
    resume_allowed_after_checkpoint: bool  # 此 checkpoint 后是否允许恢复
    fail_closed_reason: Optional[str]      # fail closed 原因（如果有）

    # === 备注 ===
    notes: Optional[str]                   # 补充说明
```

### Checkpoint 字段说明

| # | 字段 | 类型 | 说明 |
|---|------|------|------|
| 1 | checkpoint_id | str | 唯一 checkpoint ID |
| 2 | run_id | str | 关联 run_id |
| 3 | task_id | str | 关联 task_id |
| 4 | stage | str | 所属阶段 |
| 5 | step_name | str | 步骤名称 |
| 6 | step_index | int | 步骤序号 |
| 7 | created_at | str | 创建时间 |
| 8 | status | str | 步骤状态 |
| 9 | command_planned | str | 计划命令 |
| 10 | command_executed | str | 实际命令 |
| 11 | output_summary | str | 输出摘要 |
| 12 | files_expected | List[str] | 预期变更文件 |
| 13 | files_changed | List[str] | 实际变更文件 |
| 14 | git_status_before | str | 步骤前 git status |
| 15 | git_status_after | str | 步骤后 git status |
| 16 | next_pending_before | str | 步骤前 NEXT_PENDING |
| 17 | next_pending_after | str | 步骤后 NEXT_PENDING |
| 18 | next_stage_before | str | 步骤前 NEXT_STAGE |
| 19 | next_stage_after | str | 步骤后 NEXT_STAGE |
| 20 | resume_allowed_after_checkpoint | bool | 是否允许恢复 |
| 21 | fail_closed_reason | str | fail closed 原因 |
| 22 | notes | str | 备注 |

---

## 7. ResumeDecision Data Structure

ResumeDecision 判断是否允许从中断处恢复。

```python
@dataclass
class ResumeDecision:
    """ResumeDecision - 判断是否允许从中断处恢复"""

    # === 判断结果 ===
    ok: bool                              # 总体判断：是否可以恢复

    # === 关联信息 ===
    run_id: str                           # 关联的 run_id
    task_id: str                          # 关联的 task_id

    # === 恢复决策 ===
    can_resume: bool                      # 是否可以恢复
    resume_from_checkpoint: Optional[str] # 从哪个 checkpoint 恢复（checkpoint_id）
    resume_step: Optional[str]            # 恢复到哪个步骤

    # === 人工确认 ===
    requires_user_confirmation: bool      # 是否需要人工确认

    # === 工作区检查 ===
    dirty_workspace_detected: bool        # 是否检测到 dirty workspace
    unclassified_changes: List[str]       # 未分类变更列表

    # === 任务一致性 ===
    next_pending_matches: bool            # NEXT_PENDING 是否与 checkpoint 一致
    next_stage_matches: bool              # NEXT_STAGE 是否与 checkpoint 一致

    # === 限额检查 ===
    rate_limit_wait_required: bool        # 是否需要等待限额恢复
    rate_limit_reset_at: Optional[str]    # 限额恢复时间

    # === 阻塞信息 ===
    blocked_reason: Optional[str]         # 阻塞原因
    warnings: List[str]                   # 警告列表

    # === 下一步行动 ===
    next_action: str                      # 建议的下一步：resume / fail_closed / wait_for_rate_limit / wait_for_user_confirmation
```

### ResumeDecision 字段说明

| # | 字段 | 类型 | 说明 |
|---|------|------|------|
| 1 | ok | bool | 总体判断 |
| 2 | run_id | str | 关联 run_id |
| 3 | task_id | str | 关联 task_id |
| 4 | can_resume | bool | 是否可以恢复 |
| 5 | resume_from_checkpoint | str | 恢复起始 checkpoint |
| 6 | resume_step | str | 恢复步骤 |
| 7 | requires_user_confirmation | bool | 是否需要人工确认 |
| 8 | dirty_workspace_detected | bool | 是否有 dirty workspace |
| 9 | unclassified_changes | List[str] | 未分类变更 |
| 10 | next_pending_matches | bool | NEXT_PENDING 是否一致 |
| 11 | next_stage_matches | bool | NEXT_STAGE 是否一致 |
| 12 | rate_limit_wait_required | bool | 是否需等待限额 |
| 13 | rate_limit_reset_at | str | 限额恢复时间 |
| 14 | blocked_reason | str | 阻塞原因 |
| 15 | warnings | List[str] | 警告列表 |
| 16 | next_action | str | 建议行动 |

---

## 8. DirtyWorkspaceSnapshot Data Structure

DirtyWorkspaceSnapshot 记录某个时间点的工作区状态快照。

```python
@dataclass
class DirtyWorkspaceSnapshot:
    """DirtyWorkspaceSnapshot - 工作区状态快照"""

    # === 快照时间 ===
    captured_at: str                      # ISO 8601，快照捕获时间

    # === git status 原始输出 ===
    git_status_short: str                 # git status --short 完整输出

    # === 分类结果 ===
    allowed_files: List[str]              # 允许的变更文件（按 GitBackupGate 标准）
    modified_files: List[str]             # 所有已修改文件（M 标记）
    untracked_files: List[str]            # 所有未追踪文件（?? 标记）
    staged_files: List[str]              # 所有已暂存文件（A/M 标记）
    unclassified_files: List[str]         # 未分类文件（不在 allowed 也不在 forbidden 列表）

    # === 安全判断 ===
    safe_to_continue: bool                # 是否可以安全继续执行
    safe_to_commit: bool                  # 是否可以安全进入 commit 任务
    fail_reason: Optional[str]            # fail closed 原因
```

### DirtyWorkspaceSnapshot 字段说明

| # | 字段 | 类型 | 说明 |
|---|------|------|------|
| 1 | captured_at | str | 快照时间 |
| 2 | git_status_short | str | git status --short 输出 |
| 3 | allowed_files | List[str] | 允许的变更文件 |
| 4 | modified_files | List[str] | 已修改文件 |
| 5 | untracked_files | List[str] | 未追踪文件 |
| 6 | staged_files | List[str] | 已暂存文件 |
| 7 | unclassified_files | List[str] | 未分类文件 |
| 8 | safe_to_continue | bool | 是否可安全继续 |
| 9 | safe_to_commit | bool | 是否可安全 commit |
| 10 | fail_reason | str | fail closed 原因 |

---

## 9. RateLimitState Data Structure

RateLimitState 记录 API 限额状态。

```python
@dataclass
class RateLimitState:
    """RateLimitState - API 限额状态"""

    # === 检测信息 ===
    detected: bool                        # 是否检测到 API 429
    provider: Optional[str]               # API 提供商，例如 anthropic / openai / domestic
    error_code: Optional[str]             # HTTP 状态码，例如 429
    error_message: Optional[str]          # 错误信息原文

    # === 请求上下文 ===
    request_id: Optional[str]             # 关联的 API request ID
    reset_at: Optional[str]               # ISO 8601，限额预计恢复时间
    wait_seconds: Optional[int]           # 预计等待秒数

    # === 影响范围 ===
    captured_at: str                      # ISO 8601，捕获时间
    affected_task: Optional[str]          # 受影响的 task_id
    affected_step: Optional[str]          # 受影响的步骤

    # === 恢复信息 ===
    checkpoint_path: Optional[str]        # 中断时的 checkpoint 路径
    resume_allowed_after_reset: bool      # 限额恢复后是否允许恢复
    requires_workspace_recheck: bool      # 恢复前是否需要重新检查 workspace（始终为 True）

    # === 备注 ===
    notes: Optional[str]                  # 补充说明
```

### RateLimitState 字段说明

| # | 字段 | 类型 | 说明 |
|---|------|------|------|
| 1 | detected | bool | 是否检测到 429 |
| 2 | provider | str | API 提供商 |
| 3 | error_code | str | HTTP 状态码 |
| 4 | error_message | str | 错误信息 |
| 5 | request_id | str | API request ID |
| 6 | reset_at | str | 限额恢复时间 |
| 7 | wait_seconds | int | 等待秒数 |
| 8 | captured_at | str | 捕获时间 |
| 9 | affected_task | str | 受影响任务 |
| 10 | affected_step | str | 受影响步骤 |
| 11 | checkpoint_path | str | 中断时 checkpoint |
| 12 | resume_allowed_after_reset | bool | 恢复后是否允许 resume |
| 13 | requires_workspace_recheck | bool | 是否需要重新检查（始终 True） |
| 14 | notes | str | 备注 |

---

## 10. Run Status Values

RunState.status 枚举值：

| # | 状态值 | 说明 |
|---|--------|------|
| 1 | `initialized` | RunState 已创建，执行尚未开始 |
| 2 | `running` | 执行进行中 |
| 3 | `paused` | 执行暂停（例如等待用户返回），可恢复 |
| 4 | `waiting_for_rate_limit_reset` | 等待 API 限额恢复，可恢复 |
| 5 | `interrupted` | 执行被中断（进程崩溃、系统异常等），需判断是否可恢复 |
| 6 | `failed_closed` | 执行因安全检查失败而终止，不可自动恢复，需人工介入 |
| 7 | `completed` | 执行成功完成 |
| 8 | `cancelled` | 执行被用户取消 |
| 9 | `requires_user_confirmation` | 执行需要用户确认后才能继续（例如 resume 或 rate-limit recovery） |

### 状态转换规则

```
initialized → running
running → paused
running → waiting_for_rate_limit_reset
running → interrupted
running → failed_closed
running → completed
running → requires_user_confirmation
paused → running（经 resume 检查）
waiting_for_rate_limit_reset → requires_user_confirmation（限额恢复后）
interrupted → requires_user_confirmation（需人工判断）
requires_user_confirmation → running（用户确认后）
requires_user_confirmation → failed_closed（用户拒绝）
failed_closed → [终态，不可自动恢复]
completed → [终态]
cancelled → [终态]
```

---

## 11. Resume Allowed Rules

### 允许 resume 的条件（全部必须满足）

| # | 条件 | 说明 |
|---|------|------|
| 1 | run_id 存在 | 有对应的 RunState 记录 |
| 2 | checkpoint 存在 | 至少有一个有效的 Checkpoint |
| 3 | current_task 与 checkpoint task_id 一致 | 任务未发生变化 |
| 4 | NEXT_PENDING 与预期一致 | docs/tasks.md 中的 NEXT_PENDING 与 RunState.next_pending 一致 |
| 5 | NEXT_STAGE 与预期一致 | docs/tasks.md 中的 NEXT_STAGE 与 RunState.next_stage 一致 |
| 6 | 工作区 clean 或只包含已分类变更 | 无未分类文件 |
| 7 | 没有未分类变更 | DirtyWorkspaceSnapshot.unclassified_files 为空 |
| 8 | 上次中断点不是危险 Git 操作中间状态 | checkpoint.status != 'failed' 且 step_name 不在 git 操作步骤 |
| 9 | 上次中断点不是真实返工中间状态 | 无 REAL_REWORK_EXECED=yes 的记录 |
| 10 | rate limit reset time 已过 | 如果有 rate_limit_detected，reset_at < now |

### 必须 fail closed 的情况

| # | 情况 | 错误码 | 说明 |
|---|------|--------|------|
| 1 | 工作区 dirty 且存在未分类变更 | E_WORKTREE_DIRTY | DirtyWorkspaceSnapshot.unclassified_files 非空 |
| 2 | NEXT_PENDING 不匹配 | E_NEXT_PENDING_MISMATCH | RunState.next_pending != docs/tasks.md 中的 NEXT_PENDING |
| 3 | NEXT_STAGE 不匹配 | E_STAGE_MISMATCH | RunState.next_stage != docs/tasks.md 中的 NEXT_STAGE |
| 4 | checkpoint 文件缺失 | E_RESUME_NOT_ALLOWED | 无有效 checkpoint |
| 5 | checkpoint task_id 不匹配 | E_NEXT_PENDING_MISMATCH | Checkpoint.task_id != RunState.current_task |
| 6 | 上次中断发生在 git add / commit / push 过程中 | E_GIT_BACKUP_NOT_APPROVED | step_name 涉及 git 操作且 status != success |
| 7 | 上次中断发生在文件写入过程中且变更未分类 | E_UNCLASSIFIED_FILE_CHANGE | step 涉及文件写入且有 unclassified 变更 |
| 8 | rate limit reset time 未到 | E_RATE_LIMITED | now < rate_limit_reset_at |
| 9 | 外部请求来源不可信 | E_EXTERNAL_REQUEST_BLOCKED | source 不在受信列表中 |
| 10 | 用户未确认 resume | E_RESUME_NOT_ALLOWED | requires_user_confirmation=True 且用户未确认 |

---

## 12. Rate Limit Recovery Flow

设计流程：

```
1. API 429 检测
   ├── runner / tool 调用 API 时收到 429 响应
   └── 捕获 error_code、error_message、request_id

2. 解析 reset_at
   ├── 从 429 响应头提取 x-ratelimit-reset 或 retry-after
   ├── 如果无法提取 reset_at，使用默认 5 小时后
   └── 计算 wait_seconds = reset_at - now

3. 写入 RateLimitState
   ├── 创建 RateLimitState 数据结构
   ├── 记录 detected=True, provider, error_code, reset_at, wait_seconds
   ├── 记录 affected_task, affected_step
   └── requires_workspace_recheck=True（始终）

4. 写入 Checkpoint
   ├── 创建当前步骤的 Checkpoint
   ├── 记录 git_status_before / git_status_after
   ├── 记录 next_pending / next_stage 快照
   └── resume_allowed_after_checkpoint=True（限额恢复后可恢复）

5. 更新 RunState
   ├── status = waiting_for_rate_limit_reset
   ├── rate_limit_detected = True
   ├── rate_limit_reset_at = reset_at
   ├── resume_allowed = True（等待限额恢复后）
   └── checkpoint_path = 最新 checkpoint

6. 停止当前操作
   └── 不继续执行后续步骤

7. 等待（外部处理）
   ├── 用户可手动等待后重新启动
   └── 或系统定时检查（未来功能）

8. 恢复流程
   ├── 重载 RunState
   ├── 检查 reset_at 是否已过
   │   ├── 未过：继续等待，输出剩余秒数
   │   └── 已过：继续恢复流程
   ├── 检查 git status（重新捕获 DirtyWorkspaceSnapshot）
   │   ├── dirty + unclassified：fail closed (E_WORKTREE_DIRTY)
   │   └── clean 或只有 allowed：继续
   ├── 检查 NEXT_PENDING / NEXT_STAGE（重新读取 docs/tasks.md）
   │   ├── 不一致：fail closed (E_NEXT_PENDING_MISMATCH / E_STAGE_MISMATCH)
   │   └── 一致：继续
   ├── 分类变更（compare with checkpoint git_status_before）
   ├── 生成 ResumeDecision
   │   ├── ok=True：从 last_successful_step 下一步恢复
   │   └── ok=False：fail closed，输出 blocked_reason
   └── 如果 ok：resume from safe checkpoint
       └── 如果 not ok：fail closed and ask user
```

**T196 不实现等待、不实现自动恢复。** 该流程仅为设计，T199-T200 设计和实现 rate-limit recovery dry-run。

---

## 13. Dirty Workspace Resume Flow

设计流程：

```
1. resume 请求
   └── 用户或系统发起 resume 请求

2. git status --short
   ├── 执行 git status --short
   └── 捕获完整输出

3. 与 checkpoint 中的 allowed_files 对比
   ├── 读取最近 checkpoint 的 files_expected / files_changed
   ├── 读取 checkpoint 的 git_status_before / git_status_after
   └── 按 GitBackupGate 的 allowed / forbidden / unclassified 标准分类

4. 检测未分类变更
   ├── 对比当前 git status 与 checkpoint 记录
   ├── 识别新增文件（不在 allowed 也不在 forbidden 列表）
   └── 标记为 unclassified

5. 判断
   ├── 有 unclassified 变更 → fail closed
   │   ├── ResumeDecision.ok = False
   │   ├── ResumeDecision.blocked_reason = "E_UNCLASSIFIED_FILE_CHANGE"
   │   └── 输出未分类文件列表
   ├── 只有 allowed 的报告/docs 变更 → 允许 commit task 或用户确认
   │   ├── DirtyWorkspaceSnapshot.safe_to_commit = True
   │   ├── ResumeDecision.requires_user_confirmation = True
   │   └── 建议先完成 Txxx.1 commit task
   └── clean → 允许 resume
       ├── ResumeDecision.ok = True
       ├── ResumeDecision.can_resume = True
       └── 从 last_successful_step 下一步恢复

6. 写入 ResumeDecision 报告
   └── 记录完整的判断过程和结果
```

---

## 14. Integration Points

规划后续接入点：

| # | 接入点 | 工具 | 接入方式 | 时机 |
|---|--------|------|----------|------|
| 1 | run_id 创建 | runner.py | 执行开始时创建 RunState | 后续任务 |
| 2 | NEXT_PENDING / NEXT_STAGE 验证 | task_monitor.py | RunState 使用 parse_next_pending / parse_next_stage | 后续任务 |
| 3 | Git safety snapshot | git_backup_gate.py | Checkpoint 记录 git_status_before / after | 后续任务 |
| 4 | rework checkpoint | auto_mending_planner.py | 记录 rework decision 步骤的 Checkpoint | 后续任务 |
| 5 | proposal checkpoint | external_request_task_proposal.py | 记录 proposal 步骤的 Checkpoint | 后续任务 |
| 6 | run state dry-run 报告 | reports/run-state/ | T197 dry-run 输出路径 | T197 |
| 7 | 真实 run state 文件 | runtime/ | 后续任务决定是否使用此路径 | 后续任务 |

### 解耦原则

1. **run_state_manager 不直接调用其他工具**。它只提供数据结构和读写接口。
2. **其他工具不直接依赖 run_state_manager**。它们通过 CLI 或接口调用。
3. **runner.py 作为编排层**，负责在各工具之间传递 run state。
4. **所有接入都是可选的**。即使没有 run_state_manager，现有工具仍可独立运行。

---

## 15. T197 Implementation Scope

T197 应只实现 dry-run：

| # | 内容 | 说明 |
|---|------|------|
| 1 | 创建 tools/run_state_manager.py | 使用 Python 标准库，不引入第三方依赖 |
| 2 | 实现 RunState dataclass | 按 Section 5 设计实现 |
| 3 | 实现 Checkpoint dataclass | 按 Section 6 设计实现 |
| 4 | 实现 ResumeDecision dataclass | 按 Section 7 设计实现 |
| 5 | 实现 DirtyWorkspaceSnapshot dataclass | 按 Section 8 设计实现 |
| 6 | 实现 RateLimitState dataclass | 按 Section 9 设计实现 |
| 7 | 支持 create-run-state dry-run | 创建 RunState 并输出到 reports/run-state/ |
| 8 | 支持 write-checkpoint dry-run | 创建 Checkpoint 并输出到 reports/run-state/ |
| 9 | 支持 evaluate-resume dry-run | 模拟恢复判断并输出 ResumeDecision |
| 10 | 支持 simulate-rate-limit dry-run | 模拟 API 429 场景并输出 RateLimitState |
| 11 | 输出 reports/run-state/ 报告 | dry-run 模式的输出路径 |
| 12 | 不修改 runner.py | T197 不修改 runner.py |
| 13 | 不接入真实执行 | 所有功能为 dry-run |
| 14 | 不执行 Git | 不执行 git add / commit / push |
| 15 | 不创建真实自动恢复 | resume 只输出 ResumeDecision，不执行恢复 |
| 16 | fail closed | 所有不确定状态必须 fail closed |

---

## 16. Acceptance Criteria

T196 完成标准：

| # | 标准 | 状态 |
|---|------|------|
| 1 | docs/stage12-run-state-and-checkpoint-design.md 已创建 | pending |
| 2 | RunState 已设计（25 字段） | pending |
| 3 | Checkpoint 已设计（22 字段） | pending |
| 4 | ResumeDecision 已设计（16 字段） | pending |
| 5 | DirtyWorkspaceSnapshot 已设计（10 字段） | pending |
| 6 | RateLimitState 已设计（14 字段） | pending |
| 7 | Resume allowed rules 已设计（10 条允许、10 条 fail closed） | pending |
| 8 | Rate limit recovery flow 已设计 | pending |
| 9 | Dirty workspace resume flow 已设计 | pending |
| 10 | T197 implementation scope 已明确（16 条） | pending |
| 11 | 未创建 tools/run_state_manager.py | pending |
| 12 | 未修改 runner.py | pending |
| 13 | 未修改 tools/ | pending |
| 14 | NEXT_PENDING=T197 | pending |
| 15 | NEXT_STAGE=Stage 12 | pending |
