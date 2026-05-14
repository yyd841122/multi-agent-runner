# Stage 12 Rate-limit Recovery Design

设计时间：2026-05-14
设计角色：Architect Agent + Stage 12 Rate-limit Recovery Design Architect
目标：设计 API 429 / 5 小时限额恢复机制，只设计不实现。

---

## 1. Background

1. 项目曾多次遇到 API 429 / 5 小时限额中断。当 Claude Code / 国内模型 API 返回 HTTP 429 时，当前系统会检测到 `is_rate_limited=True`（`report_manager.py:analyze_claude_output()`），但无自动恢复机制。
2. 当前系统已有 `tools/run_state_manager.py` dry-run，支持 `simulate-rate-limit` 子命令和 `RateLimitState` 数据结构。
3. 当前已有 checkpoint resume fail closed 验证（T198），确认了 evaluate-resume 在 unclassified changes、NEXT_PENDING mismatch、NEXT_STAGE mismatch、rate limit wait 等场景下的 fail-closed 行为。
4. `auto_mending_planner.py` 已识别 `rate_limit_or_api_429` 失败类型（P0 severity），`next_action=wait_for_rate_limit_recovery`，但不执行等待。
5. `runner.py` 在 verify fail 路径中通过 `fail_reason` 判断是否为 429（第 3210 行），但仅在 rework decision 层面处理。
6. 未来需要在长时间自动化执行中支持中断等待和恢复，但恢复必须优先安全，不允许盲目继续。
7. **本设计只规划，不实现代码。** T200 才会实现 rate-limit recovery dry-run。
8. **本设计不启用真实等待。** 等待逻辑由外部调度器或人工处理。
9. **本设计不启用真实自动恢复。** 恢复前必须通过完整的安全检查。

---

## 2. Design Goal

rate-limit recovery 的设计目标：

1. **识别 API 429 / 5 小时限额错误。** 支持多种错误格式：HTTP 429、provider error code 1308、中文限额消息等。
2. **提取 reset_at。** 从错误信息中解析限额恢复时间，支持中文格式、ISO 格式、Unix timestamp、Retry-After header 等。
3. **写入 RateLimitRecoveryState。** 记录完整的错误上下文、影响范围、checkpoint 关联。
4. **写入 checkpoint。** 在 rate-limit 触发时写入 checkpoint，记录中断点的完整状态。
5. **将 RunState 标记为 waiting_for_rate_limit_reset。** 明确标记当前执行状态。
6. **停止当前执行。** 不继续执行后续步骤。
7. **到期后重新检查 workspace。** reset_at 到期后必须重新执行 git status 检查。
8. **重新验证 NEXT_PENDING / NEXT_STAGE。** 确认任务状态未变化。
9. **判断 resume_allowed。** 综合所有检查结果生成 RecoveryDecision。
10. **如果安全，允许从 checkpoint resume。** 从 last_successful_step 的下一步恢复。
11. **如果不安全，fail closed 并等待人工确认。** 输出 blocked_reason 和建议行动。

---

## 3. Non-goals

本设计明确不做：

1. **不实现 tools/rate_limit_recovery.py。** 本任务只设计，T200 才实现。
2. **不修改 runner.py。** runner.py 的修改将在后续任务中规划。
3. **不修改 tools/run_state_manager.py。** 当前 run_state_manager.py 的 simulate-rate-limit 已满足 dry-run 需求。
4. **不创建 runtime/。** 不创建任何运行时目录或文件。
5. **不创建真实 checkpoint。** checkpoint 只在 dry-run 模式下输出到 reports/。
6. **不启用真实等待。** 不执行 time.sleep() 或任何等待逻辑。
7. **不启用自动恢复。** 恢复流程由外部调度器或人工触发。
8. **不执行真实任务。** 不涉及任务执行。
9. **不执行真实返工。** 不涉及 auto_mending_planner 的执行。
10. **不执行真实 Git backup。** 不涉及 GitBackupGate 的执行。
11. **不绕过人工确认。** 所有不确定情况必须 fail closed 并等待人工确认。
12. **不绕过 dirty workspace 检查。** 恢复前必须重新检查 workspace。
13. **不绕过 NEXT_PENDING / NEXT_STAGE 检查。** 恢复前必须重新验证任务状态。

---

## 4. Error Detection Rules

### 4.1 需要识别的错误类型

| # | 错误类型 | 检测规则 | 示例 |
|---|---------|---------|------|
| 1 | HTTP 429 | 状态码为 429 | `429 Too Many Requests` |
| 2 | Provider error code 1308 | error.code == "1308" | `{"error":{"code":"1308",...}}` |
| 3 | 中文 5 小时限额 | message 包含 "5 小时" + "上限" 或 "使用上限" | `已达到 5 小时的使用上限` |
| 4 | reset time 信息 | message 包含 "重置" + 时间格式 | `限额将在 2026-05-12 19:47:46 重置` |
| 5 | rate limit 关键字 | message 包含 "rate limit"（不区分大小写） | `Rate limit exceeded` |
| 6 | quota exceeded | message 包含 "quota exceeded" 或 "配额" | `Quota exceeded for quota metric` |
| 7 | too many requests | message 包含 "too many requests" | `Too many requests` |
| 8 | CLI stdout 429 | stdout 中出现 "429" | Claude Code CLI 输出包含 429 |
| 9 | CLI stderr 429 | stderr 中出现 "429" | Claude Code CLI stderr 包含 429 |
| 10 | JSON error payload | 包含 code / message / request_id 字段 | 标准 API error response |

### 4.2 检测优先级

1. 优先解析 JSON error payload（如果响应体是 JSON）。
2. 其次解析 HTTP 状态码。
3. 其次解析 stderr 内容（Claude Code CLI 输出）。
4. 最后做关键字匹配。

### 4.3 示例错误

实际遇到过的错误格式：

```json
429 {"error":{"code":"1308","message":"已达到 5 小时的使用上限。您的限额将在 2026-05-12 19:47:46 重置。"},"request_id":"req_abc123"}
```

### 4.4 当前系统已有检测

- `report_manager.py:analyze_claude_output()`（第 33-35 行）：通过 regex `429|rate.limit|使用上限|Usage limit` 在 stderr 中检测 rate limit。
- `runner.py`（第 3210 行）：verify fail 时检查 fail_reason 中是否包含 "429" 或 "rate_limit"。
- `auto_mending_planner.py`：`rate_limit_or_api_429` failure type（P0 severity），next_action=`wait_for_rate_limit_recovery`。

### 4.5 未来检测增强方向

T200 应实现 `detect-rate-limit` dry-run 子命令，支持：

1. 输入：error text（stdin 或 --error-text 参数）。
2. 解析 JSON payload（如果可解析）。
3. 提取 error.code、error.message、request_id。
4. 在非 JSON 文本中做关键字匹配。
5. 输出 RateLimitRecoveryState。

---

## 5. Reset Time Extraction

### 5.1 支持的格式

| # | 格式 | 正则表达式 | 示例 |
|---|------|-----------|------|
| 1 | 中文格式 | `您的限额将在\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s*重置` | `您的限额将在 2026-05-12 19:47:46 重置` |
| 2 | ISO 8601 UTC | `(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)` | `2026-05-12T19:47:46Z` |
| 3 | ISO 8601 偏移 | `(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2})` | `2026-05-12T19:47:46+08:00` |
| 4 | Unix timestamp | `["']?reset["']?\s*[:=]\s*(\d{10,})` | `"reset": 1747076866` |
| 5 | Retry-After header | `retry-after\s*:\s*(\d+)`（秒数） | `Retry-After: 3600` |
| 6 | Provider-specific reset field | `["']?x-ratelimit-reset["']?\s*[:=]\s*(\d+)` | `x-ratelimit-reset: 1747076866` |

### 5.2 提取规则

1. **优先级顺序**：中文格式 > JSON 字段 > HTTP header > Unix timestamp。
2. **时区处理**：所有提取的时间必须转换为 UTC。中文格式按 UTC+8 处理（除非明确标注其他时区）。
3. **保存原始字符串**：提取后必须同时保存 `reset_at_raw`（原始字符串）和 `reset_at_utc`（标准化 UTC ISO 8601 字符串）。
4. **计算 wait_seconds**：`wait_seconds = max(0, (reset_at - now).total_seconds())`。

### 5.3 Fail Closed 规则

1. **如果无法提取 reset_at**，必须 fail closed。使用默认 5 小时后（18000 秒），并标记 `reset_at_raw=""`。
2. **如果提取的时间已过期**（`reset_at < now`），不视为 rate limit 事件。
3. **如果提取的时间格式无法解析**，必须 fail closed。

### 5.4 Reset At 后仍需 Recheck

reset_at 到期后仍必须重新检查 workspace，不允许直接 resume：

1. reset_at 到期只表示 API 限额可能恢复，不代表 workspace 状态安全。
2. 必须重新执行 git status --short。
3. 必须重新验证 NEXT_PENDING / NEXT_STAGE。
4. 必须重新检查 unclassified files。

---

## 6. RateLimitRecoveryState Data Structure

RateLimitRecoveryState 记录 rate-limit 事件的完整上下文。

```python
@dataclass
class RateLimitRecoveryState:
    """RateLimitRecoveryState - API rate-limit 事件完整记录"""

    # === 检测信息 ===
    detected: bool                              # 是否检测到 rate-limit
    provider: str                               # API 提供商：anthropic / domestic / unknown
    error_code: str                             # HTTP 状态码或 provider error code，例如 429 / 1308
    error_message: str                          # 错误信息原文
    raw_payload: str                            # 原始错误响应全文（用于审计）
    request_id: str                             # API request ID（如果可提取）

    # === Reset Time ===
    reset_at_raw: str                           # 原始 reset time 字符串（如 "2026-05-12 19:47:46"）
    reset_at_utc: str                           # 标准化 UTC ISO 8601 字符串（如 "2026-05-12T11:47:46Z"）
    retry_after_seconds: int                    # Retry-After 值（秒），0 表示无此字段

    # === 捕获上下文 ===
    captured_at: str                            # ISO 8601，事件捕获时间
    affected_task: str                          # 受影响的 task_id
    affected_stage: str                         # 受影响的 stage
    affected_step: str                          # 受影响的步骤名称

    # === 关联 ===
    run_id: str                                 # 关联的 run_id
    checkpoint_id: str                          # 中断时写入的 checkpoint_id
    checkpoint_path: str                        # checkpoint 文件路径
    run_state_path: str                         # RunState 文件路径

    # === 恢复控制 ===
    workspace_recheck_required: bool            # 恢复前是否需要重新检查 workspace（始终 True）
    next_pending_before_wait: str               # rate-limit 触发时的 NEXT_PENDING
    next_stage_before_wait: str                 # rate-limit 触发时的 NEXT_STAGE
    resume_allowed_after_reset: bool            # reset 后是否允许 resume（需通过安全检查）
    requires_user_confirmation: bool            # 是否需要人工确认
    blocked_reason: str                         # 阻塞原因（如果有）

    # === 备注 ===
    notes: str                                  # 补充说明
```

### RateLimitRecoveryState 字段说明

| # | 字段 | 类型 | 说明 |
|---|------|------|------|
| 1 | detected | bool | 是否检测到 rate-limit |
| 2 | provider | str | API 提供商 |
| 3 | error_code | str | HTTP 状态码或 provider error code |
| 4 | error_message | str | 错误信息原文 |
| 5 | raw_payload | str | 原始错误响应全文 |
| 6 | request_id | str | API request ID |
| 7 | reset_at_raw | str | 原始 reset time 字符串 |
| 8 | reset_at_utc | str | 标准化 UTC ISO 8601 |
| 9 | retry_after_seconds | int | Retry-After 值（秒） |
| 10 | captured_at | str | 事件捕获时间 |
| 11 | affected_task | str | 受影响的 task_id |
| 12 | affected_stage | str | 受影响的 stage |
| 13 | affected_step | str | 受影响的步骤 |
| 14 | run_id | str | 关联的 run_id |
| 15 | checkpoint_id | str | 中断时写入的 checkpoint_id |
| 16 | checkpoint_path | str | checkpoint 文件路径 |
| 17 | run_state_path | str | RunState 文件路径 |
| 18 | workspace_recheck_required | bool | 是否需要 workspace recheck（始终 True） |
| 19 | next_pending_before_wait | str | rate-limit 触发时的 NEXT_PENDING |
| 20 | next_stage_before_wait | str | rate-limit 触发时的 NEXT_STAGE |
| 21 | resume_allowed_after_reset | bool | reset 后是否允许 resume |
| 22 | requires_user_confirmation | bool | 是否需要人工确认 |
| 23 | blocked_reason | str | 阻塞原因 |
| 24 | notes | str | 补充说明 |

---

## 7. RecoveryDecision Data Structure

RecoveryDecision 综合所有检查结果，判断是否允许从 rate-limit 中断恢复。

```python
@dataclass
class RecoveryDecision:
    """RecoveryDecision - rate-limit 恢复决策"""

    # === 总体判断 ===
    ok: bool                                    # 总体判断：是否可以恢复
    can_wait: bool                              # 是否可以等待（reset_at 可解析）
    can_resume: bool                            # 是否可以恢复（所有检查通过）

    # === 关联信息 ===
    run_id: str                                 # 关联的 run_id
    task_id: str                                # 关联的 task_id
    stage: str                                  # 关联的 stage

    # === Reset 检查 ===
    reset_at_utc: str                           # 标准化 reset_at
    reset_passed: bool                          # reset_at 是否已过

    # === Workspace 检查 ===
    workspace_clean: bool                       # 工作区是否 clean
    dirty_workspace_detected: bool              # 是否检测到 dirty workspace
    unclassified_changes: List[str]             # 未分类文件列表

    # === 一致性检查 ===
    next_pending_matches: bool                  # NEXT_PENDING 是否一致
    next_stage_matches: bool                    # NEXT_STAGE 是否一致

    # === Checkpoint 检查 ===
    checkpoint_valid: bool                      # checkpoint 是否有效

    # === 人工确认 ===
    user_confirmation_required: bool            # 是否需要人工确认

    # === 阻塞信息 ===
    blocked_reason: str                         # 阻塞原因
    warnings: List[str]                         # 警告列表

    # === 下一步行动 ===
    next_action: str                            # 建议行动：resume / fail_closed / wait_for_rate_limit / wait_for_user_confirmation
```

### RecoveryDecision 字段说明

| # | 字段 | 类型 | 说明 |
|---|------|------|------|
| 1 | ok | bool | 总体判断 |
| 2 | can_wait | bool | 是否可以等待 |
| 3 | can_resume | bool | 是否可以恢复 |
| 4 | run_id | str | 关联 run_id |
| 5 | task_id | str | 关联 task_id |
| 6 | stage | str | 关联 stage |
| 7 | reset_at_utc | str | 标准化 reset_at |
| 8 | reset_passed | bool | reset_at 是否已过 |
| 9 | workspace_clean | bool | 工作区是否 clean |
| 10 | dirty_workspace_detected | bool | 是否有 dirty workspace |
| 11 | unclassified_changes | List[str] | 未分类文件 |
| 12 | next_pending_matches | bool | NEXT_PENDING 是否一致 |
| 13 | next_stage_matches | bool | NEXT_STAGE 是否一致 |
| 14 | checkpoint_valid | bool | checkpoint 是否有效 |
| 15 | user_confirmation_required | bool | 是否需要人工确认 |
| 16 | blocked_reason | str | 阻塞原因 |
| 17 | warnings | List[str] | 警告列表 |
| 18 | next_action | str | 建议行动 |

### RecoveryDecision next_action 枚举

| # | next_action | 说明 | 触发条件 |
|---|-------------|------|---------|
| 1 | `wait_for_rate_limit` | 等待限额恢复 | reset_at 未到 |
| 2 | `fail_closed` | 不允许恢复 | 安全检查失败 |
| 3 | `wait_for_user_confirmation` | 等待人工确认 | dirty workspace 但只有 allowed files |
| 4 | `resume` | 允许恢复 | 所有检查通过 |

---

## 8. Recovery Flow

### 8.1 完整流程

```
API call / Claude Code call running
  │
  ▼
error captured (stdout / stderr / HTTP response)
  │
  ▼
detect rate-limit（按 Error Detection Rules 第 4 节）
  │
  ├─ not rate-limit → 其他错误处理
  │
  ▼ rate-limit detected
parse reset_at（按 Reset Time Extraction 第 5 节）
  │
  ├─ 无法提取 → 使用默认 5 小时后，标记 reset_at_raw=""
  │
  ▼
write RateLimitRecoveryState
  │
  ▼
write checkpoint
  │
  ▼
update RunState → status=waiting_for_rate_limit_reset
  │
  ▼
stop current operation
  │
  ▼
output WAIT_UNTIL=reset_at_utc
output RECOVERY_STATE_PATH=reports/rate-limit-recovery/Txxx-*.json
  │
  ▼
── 等待（外部处理）──
  │
  ▼
user or scheduler returns later
  │
  ▼
reload RunState
  │
  ▼
reload checkpoint
  │
  ▼
check reset_at passed
  │
  ├─ 未过 → 输出剩余秒数，继续等待
  │
  ▼ 已过
git status --short → DirtyWorkspaceSnapshot
  │
  ▼
verify NEXT_PENDING / NEXT_STAGE
  │
  ▼
classify workspace changes
  │
  ▼
build RecoveryDecision
  │
  ├─ ok=True + user_confirmation_required=False → resume
  ├─ ok=True + user_confirmation_required=True → wait_for_user_confirmation
  └─ ok=False → fail_closed
```

### 8.2 安全硬约束

以下情况**绝对不允许**自动 resume：

1. **不允许在 reset_at 前 resume。** `reset_at > now` 时必须继续等待。
2. **不允许 workspace dirty 未分类时 resume。** 有 unclassified files 时必须 fail closed。
3. **不允许 NEXT_PENDING 不匹配时 resume。** 与 checkpoint 记录不一致时必须 fail closed。
4. **不允许 NEXT_STAGE 不匹配时 resume。** 与 checkpoint 记录不一致时必须 fail closed。
5. **不允许 checkpoint 缺失时 resume。** 无有效 checkpoint 时必须 fail closed。
6. **不允许 Git 操作中断点自动 resume。** git add / commit / push 中间状态必须人工确认。
7. **不允许真实返工中断点自动 resume。** controlled rework 执行中中断必须人工确认。
8. **不允许未确认的外部请求 resume。** external request apply 中断必须人工确认。

---

## 9. Workspace Recheck Rules

恢复前**必须**执行 `git status --short`。

### 9.1 判断规则

| # | workspace 状态 | 判断 | 行动 |
|---|---------------|------|------|
| 1 | clean | 可以继续 | 进入 resume decision |
| 2 | dirty 但全是 allowed files | 需要人工确认 | `requires_user_confirmation=True` |
| 3 | dirty 且包含 unclassified files | fail closed | `E_UNCLASSIFIED_FILE_CHANGE` |
| 4 | 有 staged files | fail closed 或人工确认 | 检查 staged files 是否为 allowed |
| 5 | 有 deleted files | fail closed | `E_UNCLASSIFIED_FILE_CHANGE` |
| 6 | runner.py / tools / agents 变化 | fail closed | 禁止修改框架代码后 resume |
| 7 | docs/tasks.md 状态与 checkpoint 不一致 | fail closed | `E_NEXT_PENDING_MISMATCH` 或 `E_STAGE_MISMATCH` |

### 9.2 Workspace Recheck 流程

```
git status --short
  │
  ▼
classify_workspace_changes()
  │
  ├─ unclassified_files 非空 → fail_closed
  │   blocked_reason="E_UNCLASSIFIED_FILE_CHANGE: ..."
  │
  ├─ runner.py / tools/ / agents/ 变更 → fail_closed
  │   blocked_reason="E_FORBIDDEN_FILE_CHANGE: ..."
  │
  ├─ dirty 但只有 allowed files → wait_for_user_confirmation
  │   requires_user_confirmation=True
  │   可以建议先进入 commit task
  │
  └─ clean → 继续 resume decision
```

### 9.3 与 T198 验证结果的一致性

T198 已验证：
- clean workspace + evaluate-resume → pass
- allowed files only + evaluate-resume → pass（需要 user confirmation）
- unclassified file + evaluate-resume → fail closed（E_UNCLASSIFIED_FILE_CHANGE）
- rate limit wait + evaluate-resume → fail closed（E_RATE_LIMITED）

本设计的 workspace recheck 规则与 T198 验证结果完全一致。

---

## 10. NEXT_PENDING / NEXT_STAGE Recheck

### 10.1 恢复前必须重新读取 docs/tasks.md

要求：

1. 使用 `task_monitor.py:parse_next_pending()` 读取当前 NEXT_PENDING。
2. 使用 `task_monitor.py:parse_next_stage()` 读取当前 NEXT_STAGE。
3. 当前 NEXT_PENDING 必须等于 checkpoint 记录的 `next_pending_before_wait`。
4. 当前 NEXT_STAGE 必须等于 checkpoint 记录的 `next_stage_before_wait`。

### 10.2 不一致处理

| # | 不一致类型 | 说明 | 行动 |
|---|-----------|------|------|
| 1 | NEXT_PENDING 不匹配 | 任务已被人工推进 | fail closed，停止 |
| 2 | NEXT_STAGE 不匹配 | Stage 发生变化 | fail closed，停止 |
| 3 | 任务已标记 done 但 checkpoint 仍认为 running | 人工完成了任务 | fail closed，停止等待人工确认 |
| 4 | docs/tasks.md 无法解析 | 文件损坏或格式错误 | fail closed |

### 10.3 与现有工具的集成

- `task_monitor.py:parse_next_pending()` — 使用 `re.findall() + matches[-1]` 取最后一个匹配（T160 修复后）。
- `task_monitor.py:parse_next_stage()` — 同上。
- T200 dry-run 可以直接调用这两个函数，无需修改 task_monitor.py。

---

## 11. Dangerous Resume Points

不允许自动 resume 的中断点：

| # | 中断点 | 原因 | 行动 |
|---|--------|------|------|
| 1 | git add 之后 commit 之前 | 暂存区与工作区不一致 | `requires_user_confirmation=True` |
| 2 | git commit 之后 push 之前 | 本地有未推送的 commit | `requires_user_confirmation=True` |
| 3 | git push 过程中 | push 可能部分完成 | fail closed |
| 4 | 文件写入中间状态 | 文件可能不完整 | fail closed |
| 5 | docs/tasks.md 状态修改中间状态 | 任务状态可能不一致 | fail closed |
| 6 | runner 真实执行中 | 执行状态不可预测 | fail closed |
| 7 | controlled rework 写文件中 | 返工可能不完整 | fail closed |
| 8 | GitBackupGate real action 中 | Git 操作不可预测 | fail closed |
| 9 | external request apply 中 | 外部请求可能部分应用 | fail closed |
| 10 | proposal apply 中 | proposal 可能部分写入 | fail closed |
| 11 | unknown step | 无法判断中断点安全性 | fail closed |

### 判断逻辑

这些情况都必须 `requires_user_confirmation=True` 或直接 fail closed。判断依据是 checkpoint 中的 `step_name` 和 `status`：

1. 如果 checkpoint 不存在 → fail closed。
2. 如果 checkpoint 存在但 step_name 涉及 git/runner/rework/backup/proposal → `requires_user_confirmation=True`。
3. 如果 checkpoint 存在且 status != "success" → fail closed。
4. 如果 checkpoint 的 step_name 为 unknown → fail closed。

---

## 12. Integration with run_state_manager.py

### 12.1 已有基础设施

`tools/run_state_manager.py`（T197 实现）已提供：

| # | 已有内容 | 说明 |
|---|---------|------|
| 1 | `RateLimitState` dataclass | 14 字段，记录 rate-limit 状态 |
| 2 | `simulate_rate_limit_state()` | 模拟 rate-limit 场景 |
| 3 | `cmd_simulate_rate_limit()` | CLI 子命令 |
| 4 | `evaluate_resume()` | Resume 决策逻辑 |
| 5 | `classify_workspace_changes()` | Workspace 变更分类 |
| 6 | `read_git_status_short()` | Git status 读取 |
| 7 | reports/run-state/ 输出路径 | dry-run 报告目录 |

### 12.2 T200 需要新增

| # | 新增内容 | 说明 |
|---|---------|------|
| 1 | `RateLimitRecoveryState` dataclass | 24 字段，完整 rate-limit 事件记录 |
| 2 | `RecoveryDecision` dataclass | 18 字段，恢复决策 |
| 3 | `detect-rate-limit` dry-run 子命令 | 解析错误文本，生成 RateLimitRecoveryState |
| 4 | `plan-wait` dry-run 子命令 | 计算 wait_seconds，输出等待计划 |
| 5 | `evaluate-rate-limit-resume` dry-run 子命令 | 综合检查，生成 RecoveryDecision |
| 6 | reports/rate-limit-recovery/ 输出路径 | dry-run 报告目录 |

### 12.3 不修改现有内容

| # | 不修改 | 说明 |
|---|--------|------|
| 1 | `RateLimitState` | 保留，作为 rate-limit 基础状态 |
| 2 | `ResumeDecision` | 保留，作为通用 resume 决策 |
| 3 | `evaluate_resume()` | 保留，recovery 决策可调用它 |
| 4 | 现有 CLI 子命令 | 保留，不修改参数或行为 |
| 5 | runner.py | 不修改 |

---

## 13. T200 Implementation Scope

### 13.1 推荐方案

**推荐创建 `tools/rate_limit_recovery.py`**，而非扩展 `run_state_manager.py`。

理由：

1. **避免影响已有工具。** `run_state_manager.py` 已通过 T197-T198 实现和验证，修改可能引入回归。
2. **职责清晰。** rate-limit recovery 是独立的关注点，应有独立工具。
3. **解耦。** 未来可以独立演进，不影响 run_state_manager 的稳定性。
4. **T200 实现风险更低。** 新文件比修改已有文件更安全。

### 13.2 实现范围

T200 应只实现 dry-run：

| # | 内容 | 说明 |
|---|------|------|
| 1 | 创建 `tools/rate_limit_recovery.py` | 使用 Python 标准库 |
| 2 | 实现 `RateLimitRecoveryState` dataclass | 按 Section 6 设计 |
| 3 | 实现 `RecoveryDecision` dataclass | 按 Section 7 设计 |
| 4 | 支持 `parse-error` dry-run | 解析错误文本，检测 rate-limit，提取 reset_at |
| 5 | 支持 `plan-wait` dry-run | 计算 wait_seconds，输出等待计划 |
| 6 | 支持 `evaluate-recovery` dry-run | 综合检查，生成 RecoveryDecision |
| 7 | 写 reports/rate-limit-recovery/ | dry-run 输出路径 |
| 8 | 不修改 runner.py | 不修改 |
| 9 | 不启用真实等待 | 不执行 time.sleep() |
| 10 | 不启用真实 resume | 不执行任何恢复操作 |
| 11 | 不执行 Git | 不执行 git add/commit/push |
| 12 | fail closed | 所有不确定状态必须 fail closed |

### 13.3 CLI 子命令设计

```
# 解析错误文本，检测 rate-limit
python tools/rate_limit_recovery.py parse-error \
  --task T200 \
  --stage "Stage 12" \
  --error-text '429 {"error":{"code":"1308","message":"已达到 5 小时的使用上限。您的限额将在 2026-05-12 19:47:46 重置。"},"request_id":"req_abc123"}'

# 计算等待计划
python tools/rate_limit_recovery.py plan-wait \
  --task T200 \
  --stage "Stage 12" \
  --reset-at "2026-05-12T11:47:46Z"

# 评估恢复决策
python tools/rate_limit_recovery.py evaluate-recovery \
  --task T200 \
  --stage "Stage 12" \
  --reset-at "2026-05-12T11:47:46Z" \
  --expected-next-pending T200 \
  --expected-next-stage "Stage 12" \
  --allowed-file reports/dev/T200-dev-report.md
```

### 13.4 输出格式

所有子命令输出结构化 `KEY=VALUE` 状态行，与现有工具一致：

```
RATE_LIMIT_RECOVERY_RESULT=pass
COMMAND=parse-error
TASK_ID=T200
RATE_LIMIT_DETECTED=yes
RESET_AT_RAW=2026-05-12 19:47:46
RESET_AT_UTC=2026-05-12T11:47:46Z
WAIT_SECONDS=18000
CHECK_RESULT=pass
```

---

## 14. Acceptance Criteria

T199 完成标准：

| # | 标准 | 状态 |
|---|------|------|
| 1 | docs/stage12-rate-limit-recovery-design.md 已创建 | pass |
| 2 | Error Detection Rules 已设计（10 种检测类型） | pass |
| 3 | Reset Time Extraction 已设计（6 种格式 + fail closed 规则） | pass |
| 4 | RateLimitRecoveryState 已设计（24 字段） | pass |
| 5 | RecoveryDecision 已设计（18 字段） | pass |
| 6 | Recovery Flow 已设计（完整流程 + 8 条安全硬约束） | pass |
| 7 | Workspace Recheck Rules 已设计（7 种判断 + 流程） | pass |
| 8 | NEXT_PENDING / NEXT_STAGE Recheck 已设计（4 种不一致处理） | pass |
| 9 | Dangerous Resume Points 已设计（11 种中断点） | pass |
| 10 | T200 implementation scope 已明确（推荐独立工具 + 12 条范围） | pass |
| 11 | 未创建 rate-limit recovery 工具 | pass |
| 12 | 未修改 run_state_manager.py | pass |
| 13 | 未修改 runner.py | pass |
| 14 | 未创建 runtime/ | pass |
| 15 | 未启用真实恢复 | pass |
| 16 | NEXT_PENDING=T200 | pass |
| 17 | NEXT_STAGE=Stage 12 | pass |
