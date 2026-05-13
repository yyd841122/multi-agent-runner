# Stage 12 Productization and Stability Plan

规划时间：2026-05-13
规划角色：Architect Agent + Stage 12 Productization and Stability Planning Architect
目标：规划 Stage 12 产品化与稳定性入口，只规划不实现。

---

## 1. Background

Stage 12 建立在以下基础上：

1. **Stage 8**：monitor → verify → report 最小闭环。task_monitor.py、continuous_verifier.py、execution_report_writer.py 已实现并集成到 runner.py。max_tasks=1 受控单步执行稳定。max_tasks>1 fail closed。
2. **Stage 9**：GitBackupGate dry-run 安全链。git_backup_gate.py 实现文件分类（allowed/forbidden/unclassified）、fail closed、approval record 生成、guarded git backup dry-run 接入 run-project-loop。
3. **Stage 10**：rework decision / controlled rework dry-run 安全链。auto_mending_planner.py 实现 11 种失败类型分类、15 条决策规则、10 条安全门规则。verifier fail → rework decision dry-run → controlled rework dry-run → verify → report → GitBackupGate dry-run 链路成立。Agent 角色协议层（agent-role-protocol.md + 6 个 Agent 文件）已完善。
4. **Stage 11**：external request → task proposal dry-run 安全链。external_request_inbox.py 实现 local request inbox dry-run（18 字段 ExternalRequest、10 字段 ExternalRequestSafetyResult、17 条安全门规则、4 级 prompt injection 检测）。github_issue_entry.py 实现 GitHub Issue local fixture dry-run（20 字段 GitHubIssueRequest）。external_request_task_proposal.py 实现统一 proposal bridge。所有外部入口 allowed_to_execute=False，proposal 只生成不执行。

当前系统已经形成多条安全 dry-run 链路：

- **monitor → verify → report** 链路（Stage 8）
- **GitBackupGate** 链路（Stage 9）
- **verifier fail → rework decision → controlled rework → verify → report → git backup** 链路（Stage 10）
- **external request → safety gate → task proposal** 链路（Stage 11）

当前仍未开放：

1. 真实外部自动执行。
2. 真实自动返工。
3. 真实自动 Git backup。
4. API 429 / 5 小时限额自动恢复。
5. run_state_manager.py。

Stage 12 的核心是**产品化与稳定性**，而不是盲目增加真实执行能力。在开放任何真实执行能力之前，必须先确保：

1. 运行状态可追踪。
2. 中断后可恢复。
3. 限额恢复有计划。
4. dirty workspace 风险可控。
5. 外部请求 proposal 有可追溯的审批流程。
6. 报告可检索和审计。

---

## 2. Stage 12 Goal

Stage 12 的目标：

1. **让 multi-agent-runner 更稳定**。当前系统已经有多条 dry-run 链路，但缺乏统一的运行状态管理和错误恢复能力。Stage 12 应建立稳定性基础设施。
2. **让运行状态可追踪**。每次执行应记录 run_id、task_id、stage、step、status、timestamp 等状态信息，便于回溯和审计。
3. **让中断后可恢复**。遇到 API 429、进程中断、系统异常等情况后，应能从 checkpoint 恢复，而不是从头开始。
4. **让 API 429 / 5 小时限额有计划地恢复**。当前 auto_mending_planner 已识别 rate_limit_or_api_429 失败类型，但无自动恢复机制。Stage 12 应正式规划并实现限额恢复 dry-run。
5. **让 dirty workspace 风险可控**。当前 task_monitor.py 检查 dirty workspace，但缺乏统一的 dirty workspace 保护策略。Stage 12 应建立标准化保护。
6. **让外部请求 proposal 可以被人工确认后安全 apply**。当前 proposal 只生成不执行，Stage 12 应建立 proposal approval record，让 proposal 可被人工确认后安全地写入 docs/tasks.md 草案（仍不执行）。
7. **让报告更易检索和审计**。当前 reports/ 下有 dev、checks、task-proposals、external-requests、github-issues、git、continuous-runs 等目录，但缺乏统一索引。Stage 12 应建立 reports index。
8. **让 CLI 更清晰可用**。当前 CLI 有多个子命令，但缺乏统一命名和输出规范。Stage 12 应规划 CLI 标准化。
9. **让错误码和 fail closed 行为标准化**。当前各工具的 fail closed 消息不统一。Stage 12 应建立标准错误码。
10. **为未来产品化 UI / API / n8n 做准备**。Stage 12 不实现 UI/API/n8n，但应为这些未来接口做好数据结构和状态管理准备。

---

## 3. Non-goals

Stage 12 初期明确不做：

1. **不立即开放真实外部自动执行**。external_request_inbox.py 和 github_issue_entry.py 仍保持 allowed_to_execute=False。
2. **不立即开放 GitHub Issue 自动执行**。仍使用 local fixture dry-run。
3. **不立即开放 proposal 自动写入 docs/tasks.md**。proposal 仍需人工确认。
4. **不立即开放真实自动返工**。auto_mending_planner 仍为 dry-run。
5. **不立即开放真实自动 Git backup**。GitBackupGate 仍为 dry-run。
6. **不立即创建 Web UI**。无前端界面。
7. **不立即创建 API 服务**。无 HTTP API 端点。
8. **不立即创建 n8n workflow**。无 n8n 集成。
9. **不立即创建 GitHub Actions workflow**。无 .github/workflows 文件。
10. **不跳过人工确认**。所有关键操作仍需人工确认。
11. **不绕过 dirty workspace 检查**。dirty workspace 必须优先于 resume。
12. **不绕过 GitBackupGate**。所有 Git 操作仍必须经过 GitBackupGate。
13. **不绕过 Agent Role Protocol**。所有 Agent 仍必须遵守 agent-role-protocol.md。

---

## 4. Key Productization Areas

### 4.1 CLI Experience

规划：

1. **统一命令命名**。当前子命令包括 stage8-monitor-verify-report、run-project-loop 等。应统一为 `{action} {target}` 格式，例如 `monitor`、`verify`、`report`、`backup`、`rework`、`proposal`。
2. **统一 dry-run / real-execution 参数**。所有子命令统一支持 `--dry-run`（默认 True）和 `--real-execution`（默认 False，需额外确认）。
3. **统一输出状态块**。所有工具输出统一的状态块格式，包含 TASK、STATUS、CHECK_RESULT、NEXT_PENDING、NEXT_STAGE 等标准字段。
4. **提供 --explain / --summary / --json**。`--explain` 输出详细说明，`--summary` 输出简要摘要，`--json` 输出 JSON 格式（便于未来 API 接入）。
5. **提供安全提示**。所有涉及真实执行路径的命令必须在执行前输出安全提示，并要求确认。
6. **避免误触发真实执行**。`--real-execution` 必须与 `--confirm` 配合使用，单独指定无效。

### 4.2 Run State Manager

规划未来创建：

```
tools/run_state_manager.py
```

职责：

1. **记录当前 run_id**：每次执行分配唯一 run_id。
2. **记录 task_id**：当前执行的 task_id。
3. **记录 stage**：当前 Stage 编号。
4. **记录 started_at / updated_at**：执行开始和最后更新时间。
5. **记录 current_step**：当前执行步骤（monitor / trial / verify / report / backup / rework / proposal）。
6. **记录 last_successful_step**：最后一个成功完成的步骤。
7. **记录 status**：当前状态（running / paused / completed / failed / waiting_for_rate_limit_reset / waiting_for_approval）。
8. **记录 resume_allowed**：是否允许从中断处恢复。
9. **记录 dirty_workspace_detected**：是否检测到 dirty workspace。
10. **记录 blocked_reason**：如果被阻塞，记录具体原因。

RunState 数据结构（规划）：

```python
@dataclass
class RunState:
    run_id: str                    # 格式：RUN-YYYYMMDDHHMMSS
    task_id: str                   # 例如 T196
    stage: str                     # 例如 Stage 12
    started_at: str                # ISO 8601
    updated_at: str                # ISO 8601
    current_step: str              # monitor / trial / verify / report / backup / rework / proposal
    last_successful_step: str      # 最后成功步骤
    status: str                    # running / paused / completed / failed / waiting_for_rate_limit_reset / waiting_for_approval
    resume_allowed: bool           # 是否允许恢复
    dirty_workspace_detected: bool # 是否检测到 dirty workspace
    blocked_reason: Optional[str]  # 阻塞原因
    error_code: Optional[str]      # 标准错误码
    checkpoint_data: Optional[dict] # 步骤级 checkpoint 数据
```

### 4.3 Checkpoint and Resume

规划：

1. **每个关键步骤写 checkpoint**。在 monitor、verify、report、backup、rework 等关键步骤完成后写 checkpoint，记录步骤状态和关键数据。
2. **中断后读取 checkpoint**。系统启动时检查是否存在未完成的 run_state，如果有，读取 checkpoint 判断恢复可能性。
3. **判断是否可恢复**。根据 run_state.status、dirty_workspace_detected、blocked_reason 判断。
4. **如果工作区 dirty 且存在未分类变更，必须 fail closed**。不允许在 dirty workspace 上盲目恢复。
5. **如果上次中断在 Git 操作前后，必须人工确认**。Git 操作前后的中断可能导致文件系统状态不一致。
6. **如果上次中断在外部 request proposal 阶段，只能恢复到 dry-run**。不允许从 proposal 阶段直接跳到执行。
7. **不允许盲目继续真实执行**。所有恢复路径必须经过安全检查。

Resume 流程（规划）：

```
1. 检测到未完成 run_state
2. 检查 dirty_workspace_detected
   → dirty: 检查未分类文件
     → 有未分类文件: fail closed (E_WORKTREE_DIRTY)
     → 只有已分类文件: 提示人工确认
   → clean: 继续
3. 检查 status
   → waiting_for_rate_limit_reset: 检查限额是否已恢复
   → waiting_for_approval: 等待人工确认
   → failed: 不自动恢复，等待人工确认
   → paused: 从 last_successful_step 恢复
4. 重新验证 NEXT_PENDING / NEXT_STAGE
   → 不一致: fail closed (E_NEXT_PENDING_MISMATCH / E_STAGE_MISMATCH)
   → 一致: 继续
5. 从 last_successful_step 的下一步恢复执行
```

### 4.4 API 429 / 5-hour Limit Recovery

必须正式纳入规划。

未来机制说明：

1. **检测 API 429**。当 runner 或工具调用 API 时收到 429 响应，捕获错误信息。
2. **提取 reset time**。从 429 响应头或错误信息中提取限额重置时间（reset_time）。
3. **写入 checkpoint**。将当前执行状态、步骤、task_id、reset_time 写入 run_state checkpoint。
4. **设置 run_state=waiting_for_rate_limit_reset**。标记当前执行正在等待限额恢复。
5. **等待限额恢复**。计算 wait_seconds = reset_time - now。如果 wait_seconds > 0，暂停执行。
6. **恢复前重新检查 workspace**。限额恢复后，先执行 dirty workspace 检查。
7. **恢复前重新验证 NEXT_PENDING / NEXT_STAGE**。确认任务状态未变化。
8. **恢复前检查未分类文件**。确认没有意外文件变更。
9. **如果 safe，允许从 checkpoint resume**。从 last_successful_step 继续。
10. **如果 dirty workspace 或任务状态不一致，停止等待人工确认**。fail closed。

RateLimitRecoveryState 数据结构（规划）：

```python
@dataclass
class RateLimitRecoveryState:
    run_id: str                    # 关联的 run_id
    rate_limited_at: str           # ISO 8601
    reset_time: str                # ISO 8601，限额预计恢复时间
    wait_seconds: int              # 等待秒数
    current_step: str              # 被中断的步骤
    recovery_attempts: int         # 恢复尝试次数（限制最大 3 次）
    max_recovery_attempts: int     # 默认 3
    status: str                    # waiting / recovered / failed / abandoned
```

**当前 T195 不实现该机制。** 该机制将在 T199-T200 中设计和实现 dry-run。

### 4.5 Dirty Workspace Protection

规划：

1. **每次执行前检查 git status --short**。在 monitor、resume、rate-limit recovery 等所有入口点执行检查。
2. **识别允许变更文件**。使用 GitBackupGate 的 allowed/forbidden/unclassified 分类标准。
3. **未分类变更 fail closed**。如果存在 unclassified 文件变更，立即停止，输出 E_UNCLASSIFIED_FILE_CHANGE。
4. **已生成报告但未提交时可进入 commit task**。如果 dirty 状态仅由已生成的报告文件组成，允许进入 Txxx.1 commit 任务。
5. **外部请求不能覆盖已有 dirty 状态**。如果当前工作区已经 dirty，外部请求 proposal 应标记为 blocked。
6. **恢复时必须重新检查**。resume 和 rate-limit recovery 都必须重新检查 dirty workspace。

DirtyWorkspaceCheck 数据结构（规划）：

```python
@dataclass
class DirtyWorkspaceCheck:
    is_clean: bool                 # 工作区是否 clean
    changed_files: List[str]       # 变更文件列表
    allowed_files: List[str]       # 允许的变更文件
    forbidden_files: List[str]     # 禁止的变更文件
    unclassified_files: List[str]  # 未分类的变更文件
    can_proceed: bool              # 是否可以继续
    blocked_reason: Optional[str]  # 阻塞原因
```

### 4.6 Proposal Approval and Apply

规划：

1. **external request 只生成 proposal**。保持现有行为，external_request_task_proposal.py 只生成 TaskProposal dry-run。
2. **proposal 必须人工确认**。PROPOSAL_NEXT_ACTION=wait_for_approval 保持不变。
3. **后续可实现 proposal approval record**。建立 ProposalApprovalRecord 数据结构，记录审批人、审批时间、审批决定。
4. **apply proposal 只写 docs/tasks.md 草案**。审批通过后，将 proposal 内容写入 docs/tasks.md 作为 pending 任务。apply 后仍不执行任务。
5. **apply 后仍不执行任务**。task execution 必须另走受控 runner 流程（stage8-monitor-verify-report 或 run-project-loop）。
6. **task execution 必须另走受控 runner 流程**。不允许从 proposal 直接跳到执行。

ProposalApprovalRecord 数据结构（规划）：

```python
@dataclass
class ProposalApprovalRecord:
    proposal_id: str               # 关联的 proposal_id
    approved_by: str               # 审批人
    approved_at: str               # ISO 8601
    decision: str                  # approved / rejected / deferred
    applied_to_tasks: bool         # 是否已写入 docs/tasks.md
    applied_task_id: Optional[str] # 写入后的 task_id
    task_executed: bool            # 是否已执行（始终为 False）
    notes: Optional[str]           # 审批备注
```

### 4.7 Report Index and Audit Trail

规划：

1. **建立 reports index**。创建 tools/report_index.py，扫描 reports/ 下所有目录，生成统一索引。
2. **汇总 reports/dev**。所有 Txxx-dev-report.md 的任务编号、角色、目标、CHECK_RESULT 摘要。
3. **汇总 reports/checks**。所有 Txxx-*-validation.md 的验证场景和结果摘要。
4. **汇总 reports/task-proposals**。所有 PROPOSAL-*-report.md 的 proposal_id、来源、安全状态摘要。
5. **汇总 reports/external-requests**。所有外部请求处理记录。
6. **汇总 reports/github-issues**。所有 GitHub Issue dry-run 处理记录。
7. **汇总 reports/git**。所有 Git backup approval record。
8. **汇总 archive 文档**。docs/archive/ 下所有阶段最终审查文档。
9. **便于回溯每个阶段的证据**。index 应支持按 task_id、stage、日期、CHECK_RESULT 过滤。

ReportsIndex 数据结构（规划）：

```python
@dataclass
class ReportsIndexEntry:
    report_type: str               # dev_report / check / task_proposal / external_request / github_issue / git_backup / archive
    task_id: str                   # 关联的 task_id
    file_path: str                 # 报告文件路径
    check_result: str              # pass / fail / partial_pass
    created_at: str                # ISO 8601
    stage: str                     # 关联的 stage
    summary: str                   # 摘要（100 字以内）
```

### 4.8 Error Codes and Fail Closed Standard

规划统一错误码：

| # | 错误码 | 说明 | 触发场景 |
|---|--------|------|----------|
| 1 | E_WORKTREE_DIRTY | 工作区存在未分类变更 | resume 时检测到 dirty workspace 且有 unclassified 文件 |
| 2 | E_RATE_LIMITED | API 限额触发 | 收到 429 响应 |
| 3 | E_NEXT_PENDING_MISMATCH | NEXT_PENDING 不一致 | resume 时 NEXT_PENDING 与 checkpoint 不匹配 |
| 4 | E_STAGE_MISMATCH | NEXT_STAGE 不一致 | resume 时 NEXT_STAGE 与 checkpoint 不匹配 |
| 5 | E_UNCLASSIFIED_FILE_CHANGE | 存在未分类文件变更 | GitBackupGate 检测到 unclassified 文件 |
| 6 | E_EXTERNAL_REQUEST_BLOCKED | 外部请求被安全门阻止 | external_request_inbox safety gate fail |
| 7 | E_PROMPT_INJECTION_RISK | 检测到 prompt injection | safety gate 检测到 high/critical 风险 |
| 8 | E_GIT_BACKUP_NOT_APPROVED | Git backup 未获批准 | GitBackupGate approval record 中 COMMIT_ALLOWED=no 或 PUSH_ALLOWED=no |
| 9 | E_REWORK_NOT_ALLOWED | 返工不被允许 | auto_mending_planner rework_allowed=False |
| 10 | E_RESUME_NOT_ALLOWED | 不允许恢复 | run_state.resume_allowed=False |

所有错误码应遵循以下规范：

1. 每个错误码有唯一标识。
2. 每个错误码有明确说明。
3. 每个错误码有触发场景。
4. 所有错误码触发时必须 fail closed。
5. 所有错误码应写入 run_state.error_code。
6. 所有错误码应在报告中体现。

### 4.9 Future Product Interfaces

只规划，不实现：

1. **Web UI**。未来可创建前端界面，展示任务状态、报告、proposal 列表、approval 流程。
2. **API**。未来可创建 HTTP API 端点，供 Web UI 和外部工具调用。API 应基于 run_state_manager 的数据结构。
3. **n8n**。未来可创建 n8n workflow，实现外部触发和自动化流水线。
4. **GitHub Actions**。未来可创建 .github/workflows，实现 GitHub Issue 自动处理。
5. **Dashboard**。未来可创建仪表盘，展示项目进度、任务统计、错误分布。
6. **Report Viewer**。未来可创建报告查看器，便于浏览和检索 reports/ 下的所有报告。
7. **Approval Center**。未来可创建审批中心，统一管理 proposal approval、git backup approval、rework approval。

这些接口的实现需要：
- run_state_manager.py 已就绪。
- API 429 / 5 小时限额恢复机制已验证。
- dirty workspace 保护已标准化。
- 错误码已标准化。
- 所有 dry-run 安全链已验证。

---

## 5. Recommended Stage 12 Task Sequence

| # | 任务 | 角色 | 目标 |
|---|------|------|------|
| T196 | 设计 run_state_manager.py 与 checkpoint 数据结构 | Architect | 设计 RunState、Checkpoint、ResumePolicy 数据结构 |
| T197 | 实现 run_state_manager.py dry-run | Developer | 实现 run_state_manager.py，支持 dry-run 状态记录和读取 |
| T198 | 验证 checkpoint resume fail closed | Validator | 验证 resume 在 dirty workspace、status mismatch、blocked 等场景下 fail closed |
| T199 | 设计 API 429 / 5 小时限额恢复机制 | Architect | 设计 RateLimitRecoveryState、恢复流程、安全检查 |
| T200 | 实现 rate-limit recovery dry-run | Developer | 实现限额检测、checkpoint 写入、恢复流程 dry-run |
| T201 | 验证 dirty workspace resume protection | Validator | 验证 resume 时 dirty workspace 检查、未分类文件 fail closed |
| T202 | 设计 external proposal approval record | Architect | 设计 ProposalApprovalRecord、审批流程、apply 安全规则 |
| T203 | 实现 proposal approval record dry-run | Developer | 实现 approval record dry-run，apply 只写 docs/tasks.md 草案 |
| T204 | 验证 proposal apply 不执行任务 | Validator | 验证 apply 后 task 不被执行，execution 仍需走 runner 流程 |
| T205 | 设计 reports index 与 audit trail | Architect | 设计 ReportsIndex 数据结构、过滤规则、输出格式 |
| T206 | 实现 reports index dry-run | Developer | 实现 report_index.py dry-run，生成 reports index |
| T207 | Stage 12 最终状态审查 | Reviewer | 审查 T196-T206 全部成果，确认 Stage 12 安全链 |

注意：

- 这些任务只是规划，T195 不实现它们。
- 每个任务的详细设计将在该任务执行时完成。
- 任务顺序可能根据实际执行情况调整。
- 任何任务都不允许绕过现有安全链。

---

## 6. Safety Policy for Stage 12

Stage 12 安全策略：

1. **Stage 12 不代表开放真实自动执行**。Stage 12 的首要目标是稳定性和可恢复性，不是开放真实执行。
2. **Stage 12 首要目标是稳定性**。所有新工具必须从 dry-run 开始，验证通过后才考虑真实路径。
3. **所有恢复机制必须 fail closed**。checkpoint resume 遇到任何不确定状态必须停止，等待人工确认。
4. **dirty workspace 必须优先于 resume**。恢复前必须检查 dirty workspace，dirty 时优先处理 dirty 状态。
5. **rate-limit resume 必须重新验证任务状态**。限额恢复后必须重新验证 NEXT_PENDING / NEXT_STAGE / 工作区状态。
6. **proposal apply 必须人工确认**。apply 操作必须经过 approval record，不允许自动 apply。
7. **Git 操作仍必须经过 GitBackupGate**。所有 Git 相关操作仍受 GitBackupGate 约束。
8. **rework 仍必须经过 auto_mending_planner**。所有返工操作仍受 auto_mending_planner 约束。
9. **外部请求仍必须经过 safety gate**。所有外部请求仍受 external_request_inbox safety gate 约束。
10. **所有新工具默认 dry-run**。run_state_manager.py、rate-limit recovery、proposal approval record、report index 等新工具默认 dry-run。

---

## 7. Recommended Next Step

```text
NEXT_PENDING=T196
NEXT_STAGE=Stage 12
```

建议 T196 任务名为：

**T196：设计 run_state_manager.py 与 checkpoint 数据结构**

T196 职责：

1. 设计 RunState dataclass（run_id、task_id、stage、started_at、updated_at、current_step、last_successful_step、status、resume_allowed、dirty_workspace_detected、blocked_reason、error_code、checkpoint_data）。
2. 设计 Checkpoint dataclass（step、timestamp、data）。
3. 设计 ResumePolicy（何时允许恢复、何时必须 fail closed）。
4. 只设计，不实现 run_state_manager.py。

注意：

- T196 只做数据结构设计，不实现代码。
- T197 才会实现 run_state_manager.py dry-run。
- T198 才会验证 checkpoint resume fail closed。
