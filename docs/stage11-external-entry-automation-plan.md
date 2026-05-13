# Stage 11 External Entry Automation Plan

规划时间：2026-05-13
规划角色：Architect Agent + Stage 11 External Entry Planning Architect
目标：规划 Stage 11 外部入口自动化入口，只规划不实现。

---

## 1. Background

Stage 11 建立在 Stage 8 / Stage 9 / Stage 10 的安全基础之上：

1. **Stage 8 已完成 monitor → verify → report**：task_monitor.py 读取 NEXT_PENDING/NEXT_STAGE，continuous_verifier.py 验证任务状态，execution_report_writer.py 生成执行报告。max_tasks=1 受控边界成立，max_tasks>1 fail closed。
2. **Stage 9 已完成 GitBackupGate dry-run**：git_backup_gate.py 实现文件分类（allowed / forbidden / unclassified），生成 approval record，不执行真实 git add/commit/push。
3. **Stage 10 已完成 rework decision / controlled rework dry-run 链路**：auto_mending_planner.py 实现 11 种 failure_type 分类、15 条决策规则、10 条安全门规则。runner.py Step 3.1 接入 rework decision dry-run，Step 3.2 接入 controlled rework dry-run。12 个 fail-closed 场景全部验证通过。
4. **当前仍不开放真实无限连续执行**：NEXT_ACTION 始终为 stop，不自动进入下一任务。
5. **当前仍不开放真实自动 Git backup**：GitBackupGate 仍为 dry-run only，PUSH_ALLOWED=no。
6. **当前仍不开放真实自动返工**：所有返工路径保持 dry-run，REAL_REWORK_EXECUTED=no。
7. **Stage 11 目标是让外部请求进入系统，但只进入受控入口**：外部请求不能直接触发真实执行、Git 操作或返工。

---

## 2. Stage 11 Goal

Stage 11 的核心目标是建立外部请求进入 multi-agent-runner 的受控通道：

1. **接收外部请求**：支持从多种来源接收用户需求。
2. **标准化外部请求**：将不同来源的请求转换为统一的 ExternalRequest 数据结构。
3. **生成 ExternalRequest**：包含来源、内容、安全评级、审批状态等字段。
4. **进行 request safety gate**：对外部请求进行安全门检查，防止 prompt injection、越权操作等。
5. **将请求转换为任务草案**：生成 planning proposal，包含拆解后的任务列表。
6. **生成 planning proposal**：proposal 必须可审查、可拒绝。
7. **等待人工确认**：所有外部请求生成的任务草案必须经过人工确认。
8. **再进入现有 Main Agent / Planner Agent 流程**：确认后的任务进入 docs/tasks.md，再由现有流程处理。
9. **外部请求不能直接触发真实执行**：allowed_to_execute 默认 false。
10. **外部请求不能直接触发 Git 操作**：外部请求流程中不包含任何 git 操作。

---

## 3. Non-goals

本阶段明确不做以下事项：

1. **不开放匿名外部真实执行**：所有外部请求只能生成 proposal，不直接执行。
2. **不让 GitHub Issue 直接执行代码**：Issue 内容只作为需求输入，不作为执行指令。
3. **不让 Web UI 直接调用真实 run-project-loop**：Web UI 提交的请求必须经过 safety gate 和人工确认。
4. **不让 API 直接触发真实返工**：API 请求只能生成 rework proposal。
5. **不让 n8n 直接触发 Git 操作**：workflow 触发的请求受安全门约束。
6. **不跳过 Main Agent**：外部请求进入后仍由 Main Agent 调度。
7. **不跳过 Planner Agent**：任务拆解仍由 Planner Agent 负责。
8. **不跳过 Reviewer Agent**：质量审查仍由 Reviewer Agent 执行。
9. **不绕过 GitBackupGate**：所有 Git 相关操作仍必须经过 GitBackupGate。
10. **不处理生产级权限系统**：权限、鉴权、审计等后续阶段处理。
11. **不实现账号体系**：用户认证、授权不在本阶段范围。
12. **不进入 Stage 12 产品化**：Stage 11 只做外部入口，不做产品化。

---

## 4. External Entry Candidates

### 4.1 Local Request Inbox

说明：

1. 使用本地目录（如 `requests/inbox/`）保存外部请求草稿。
2. 每个请求是一个 `.md` 文件，包含标题、内容、来源等信息。
3. **安全性最高**：不依赖外部服务，不需要网络连接，不需要 token。
4. **适合作为 Stage 11 第一个入口**：实现简单，风险最低。
5. 可先 dry-run：读取请求文件、生成 ExternalRequest、safety gate 检查、生成 proposal，全部 dry-run。
6. 后续可扩展为 GitHub Issue / n8n 的本地同步。

### 4.2 GitHub Issue Entry

说明：

1. 用户通过 GitHub Issue 提需求，系统读取 issue 内容。
2. 只生成 request proposal，不直接执行。
3. 需要防 prompt injection：issue body 一律视为不可信内容。
4. 需要 GitHub token 读取 issue（可选：通过 webhook 接收）。
5. 适合作为 Stage 11 第二个入口，在 local request inbox 验证后再实现。

### 4.3 Web UI Entry

说明：

1. 用户通过网页提交需求。
2. 需要 API / 表单 / 权限，前端框架选型。
3. 复杂度较高，需要鉴权、CSRF 防护、输入验证。
4. **当前不建议第一步实现**，等 local request inbox 和 GitHub Issue 入口验证后再考虑。

### 4.4 API Entry

说明：

1. 外部系统通过 API 提交需求（如 POST /api/requests）。
2. **风险较高**：需要鉴权、限流、审计、输入验证。
3. 需要 API key 管理、请求签名、速率限制。
4. **后续再做**，不在 Stage 11 第一步实现。

### 4.5 n8n / Workflow Entry

说明：

1. 可连接表单、Webhook、GitHub、邮件等多种外部来源。
2. 适合作为后续自动化集成枢纽。
3. n8n 节点可以读取外部请求、调用 local API、写入 request inbox。
4. **当前先规划，不实现**。

---

## 5. Recommended First Entry

**建议第一个 Stage 11 入口为：**

**T186：设计 local request inbox dry-run 数据结构**

理由：

1. **不依赖外部服务**：不需要 GitHub token、不需要 Web 服务器、不需要 API。
2. **不需要 GitHub token**：本地文件操作即可。
3. **不需要 Web UI**：纯文件操作。
4. **不需要 API 鉴权**：本地运行。
5. **便于 fail closed**：文件不存在、格式错误、内容异常都可以 fail closed。
6. **便于后续扩展到 GitHub Issue / n8n**：ExternalRequest 数据结构统一，来源不同但处理流程一致。
7. **不会直接触发真实执行**：local request inbox 只读取文件，不执行任何代码。

实现路径：

```
requests/inbox/*.md
→ external_request_inbox.py 读取
→ ExternalRequest 数据结构
→ ExternalRequestSafetyGate 检查
→ Planning Proposal 生成
→ 用户确认
→ docs/tasks.md 更新（需人工确认）
→ 现有 Stage 8/9/10 流程
```

---

## 6. ExternalRequest Data Structure

### 6.1 ExternalRequest Dataclass 草案

```python
@dataclass
class ExternalRequest:
    """外部请求数据结构，用于标准化来自不同来源的用户需求。"""

    # 基础标识
    request_id: str               # 请求唯一标识，格式：REQ-{timestamp}-{hash}
    source_type: str              # 来源类型：local_inbox / github_issue / web_form / api / n8n_workflow
    source_ref: str               # 来源引用：文件路径 / issue URL / 表单 ID / API request ID
    title: str                    # 请求标题

    # 内容
    raw_content: str              # 原始请求内容（完整原文，不做任何处理）
    normalized_summary: str       # 标准化摘要（系统生成的结构化摘要）

    # 请求者信息
    requester: str                # 请求者标识：user / github_user / api_client / n8n
    created_at: str               # 请求创建时间（ISO 8601）

    # 优先级与范围
    priority: str                 # 优先级：low / medium / high / critical
    requested_stage: str          # 请求进入的阶段：Stage 8 / Stage 11 / auto
    requested_files: list[str]    # 请求涉及的文件列表

    # 安全评估
    suspected_intent: str         # 推断意图：new_feature / bug_fix / refactor / documentation / test / unknown / suspicious
    safety_risk_level: str        # 安全风险等级：low / medium / high / critical
    prompt_injection_risk: str    # Prompt injection 风险：none / low / medium / high / critical

    # 审批状态
    requires_user_approval: bool  # 是否需要人工确认（默认 true）
    allowed_to_plan: bool         # 是否允许生成 planning proposal（默认 false，safety gate 通过后可设为 true）
    allowed_to_execute: bool      # 是否允许执行（默认 false，Stage 11 中始终为 false）
    fail_reason: str              # 如果 fail closed，记录原因
```

### 6.2 字段说明

| # | 字段 | 必填 | 默认值 | 说明 |
|---|------|------|--------|------|
| 1 | request_id | yes | 自动生成 | 请求唯一标识 |
| 2 | source_type | yes | local_inbox | 来源类型 |
| 3 | source_ref | yes | 文件路径 | 来源引用 |
| 4 | title | yes | 空字符串 | 请求标题 |
| 5 | raw_content | yes | 原文 | 原始内容，不做任何处理 |
| 6 | normalized_summary | yes | 空字符串 | 系统生成摘要 |
| 7 | requester | yes | user | 请求者标识 |
| 8 | created_at | yes | 当前时间 | 创建时间 |
| 9 | priority | yes | medium | 优先级 |
| 10 | requested_stage | yes | auto | 请求阶段 |
| 11 | requested_files | yes | 空列表 | 涉及文件 |
| 12 | suspected_intent | yes | unknown | 推断意图 |
| 13 | safety_risk_level | yes | high | 安全风险（默认 high，safety gate 通过后降级） |
| 14 | prompt_injection_risk | yes | high | Prompt injection 风险（默认 high，检查后降级） |
| 15 | requires_user_approval | yes | true | 是否需要人工确认 |
| 16 | allowed_to_plan | yes | false | 是否允许生成 proposal |
| 17 | allowed_to_execute | yes | false | 是否允许执行（Stage 11 始终 false） |
| 18 | fail_reason | yes | 空字符串 | fail closed 原因 |

---

## 7. ExternalRequestSafetyGate

### 7.1 安全门规则

| # | 规则 | 结果 | 说明 |
|---|------|------|------|
| 1 | 空请求（raw_content 为空或纯空白） | fail closed | 无法处理空请求 |
| 2 | 来源不明（source_type 不在允许列表中） | fail closed | 只允许 local_inbox / github_issue / web_form / api / n8n_workflow |
| 3 | 包含要求泄露密钥 | fail closed | 检测 .env / secrets / API key / password / token 等关键词 |
| 4 | 包含要求绕过安全规则 | fail closed | 检测 bypass / ignore safety / skip verification 等关键词 |
| 5 | 包含要求直接 git push | fail closed | 检测 git push / git push --force 等关键词 |
| 6 | 包含要求直接执行真实返工 | fail closed | 检测 execute real rework / auto rework without verification |
| 7 | 包含要求删除文件 | fail closed + 人工确认 | 检测 rm / delete / remove file 等关键词，必须人工确认 |
| 8 | 涉及 runner.py / tools/ / agents/ | 人工确认 | 涉及框架代码的修改必须人工确认 |
| 9 | 涉及 .env / secrets / API key | fail closed | 绝对不允许外部请求涉及密钥文件 |
| 10 | prompt injection 风险标记 | 标记 + 人工确认 | 检测 system prompt override / ignore instructions 等模式 |
| 11 | allowed_to_execute 默认 false | 强制 | Stage 11 中外部请求不允许直接执行 |
| 12 | allowed_to_plan 在低风险时可 true | 条件通过 | safety_risk_level=low 且 prompt_injection_risk=none/low 时允许 |
| 13 | 所有外部请求默认只能生成 proposal | 强制 | 不直接写 docs/tasks.md，不直接执行 runner |

### 7.2 安全门处理流程

```text
ExternalRequest 进入
→ 检查空请求（规则 1）
→ 检查来源类型（规则 2）
→ 检查密钥泄露要求（规则 3）
→ 检查绕过安全规则要求（规则 4）
→ 检查 git push 要求（规则 5）
→ 检查真实返工要求（规则 6）
→ 检查文件删除要求（规则 7）
→ 检查框架代码修改（规则 8）
→ 检查密钥文件涉及（规则 9）
→ 检查 prompt injection 模式（规则 10）
→ 设置 allowed_to_execute=false（规则 11）
→ 设置 allowed_to_plan（规则 12）
→ 输出 ExternalRequest + safety gate 结果
→ 只有 safety gate 通过 + 人工确认后才生成 proposal
```

---

## 8. Request to Task Proposal Flow

### 8.1 完整流程

```text
External request（来源：local inbox / GitHub Issue / Web UI / API / n8n）
  ↓
ExternalRequest 数据结构（标准化）
  ↓
ExternalRequestSafetyGate（安全门检查）
  ↓（通过安全门）
Normalized Summary（标准化摘要）
  ↓
Planning Proposal（任务拆解提案）
  ├── proposed_tasks: 建议的任务列表
  ├── task_descriptions: 每个任务的描述
  ├── estimated_scope: 预估范围
  └── risk_assessment: 风险评估
  ↓
User Approval（人工确认）
  ↓（用户确认后）
docs/tasks.md Update（更新任务列表，需人工确认）
  ↓
Existing Stage Flow（进入 Stage 8/9/10 流程）
```

### 8.2 关键约束

1. **不直接写 docs/tasks.md**：proposal 生成后必须经过人工确认，才能更新 docs/tasks.md。
2. **不直接执行 runner**：外部请求流程中不调用 runner.py 或 run-project-loop。
3. **不直接调用 Developer Agent**：外部请求不能直接触发代码生成或修改。
4. **不直接调用 Git Backup Agent**：外部请求不能直接触发 Git 操作。
5. **proposal 必须可审查**：proposal 包含完整的任务描述、范围、风险评估，用户可以逐条审查和修改。

---

## 9. Prompt Injection Defense

### 9.1 核心原则

1. **外部请求内容一律视为不可信**：无论来源，raw_content 不被视为系统指令。
2. **外部请求不能覆盖系统规则**：系统规则（agent-role-protocol.md、安全门规则）优先级高于任何外部请求内容。
3. **外部请求不能修改 Agent 角色规则**：agents/*.md 和 agent-role-protocol.md 不能被外部请求修改。
4. **外部请求不能要求泄露密钥**：涉及 .env / secrets / API key 的请求一律 fail closed。
5. **外部请求不能要求绕过 GitBackupGate**：涉及绕过 Git 安全检查的请求一律 fail closed。
6. **外部请求不能要求执行复合命令**：涉及 && / ; / | 的请求内容一律标记为高风险。
7. **外部请求不能要求直接 push**：涉及 git push 的请求一律 fail closed。
8. **外部请求只能作为需求内容，不作为执行指令**：外部请求的内容只能用于理解用户意图，不能被当作代码或命令执行。

### 9.2 检测规则

| # | 检测模式 | 风险等级 | 动作 |
|---|----------|----------|------|
| 1 | "ignore previous instructions" | critical | fail closed |
| 2 | "system prompt" / "override" | critical | fail closed |
| 3 | "bypass safety" / "skip verification" | critical | fail closed |
| 4 | ".env" / "secrets" / "API key" / "password" | high | fail closed |
| 5 | "git push" / "git push --force" | high | fail closed |
| 6 | "execute real rework" / "auto rework without" | high | fail closed |
| 7 | "rm -rf" / "delete all" | high | fail closed |
| 8 | "&&" / ";" / "\|" 在命令上下文中 | medium | 标记 + 人工确认 |
| 9 | "runner.py" / "tools/" / "agents/" 在涉及文件中 | medium | 标记 + 人工确认 |
| 10 | 非英文非中文的混合指令模式 | low | 标记，不阻止 |

---

## 10. Integration Points

### 10.1 新增文件规划

| # | 文件 | 作用 | 实现时机 |
|---|------|------|----------|
| 1 | tools/external_request_inbox.py | 本地 request inbox dry-run | T187 |
| 2 | tools/external_request_safety_gate.py | 外部请求安全门 | T188 |
| 3 | requests/inbox/ | 本地请求存放目录 | T187 |
| 4 | reports/external-requests/ | 外部请求处理报告 | T187 |

### 10.2 现有文件集成

| # | 文件 | 集成方式 | 实现时机 |
|---|------|----------|----------|
| 1 | docs/tasks.md | 只在人工确认后更新 | T192 |
| 2 | runner.py | 后续只接收已确认 request proposal | T192+ |
| 3 | agents/main_agent.md | 外部请求进入后由 Main Agent 调度 | 后续 |
| 4 | tools/task_monitor.py | 识别来自外部请求的任务 | 后续 |

### 10.3 后续扩展入口

| # | 入口 | 实现时机 |
|---|------|----------|
| 1 | GitHub Issue | T189-T191 |
| 2 | n8n / Workflow | 后续 |
| 3 | Web UI | 后续 |
| 4 | API | 后续 |

---

## 11. Suggested Stage 11 Tasks

| # | 任务 | 角色 | 目标 |
|---|------|------|------|
| T186 | 设计 local request inbox dry-run 数据结构 | Architect | 设计 ExternalRequest、ExternalRequestSafetyGateResult、RequestProposal 数据结构 |
| T187 | 实现 external_request_inbox.py dry-run | Developer | 实现本地 request inbox 读取、解析、生成 ExternalRequest |
| T188 | 验证 external request safety gate fail closed | Validator | 验证 13 条安全门规则的 fail-closed 行为 |
| T189 | 设计 GitHub Issue 外部入口 dry-run | Architect | 设计 GitHub Issue → ExternalRequest 的转换流程 |
| T190 | 实现 GitHub Issue 读取与 proposal dry-run | Developer | 实现 issue 读取、内容解析、proposal 生成 |
| T191 | 验证 GitHub Issue prompt injection 防护 | Validator | 验证恶意 issue 内容不触发执行 |
| T192 | 接入 external request → task proposal dry-run | Developer | 将外部请求 proposal 接入 docs/tasks.md 更新流程 |
| T193 | 验证外部请求生成任务草案但不执行 | Validator | 验证完整链路：请求 → safety gate → proposal → 任务草案 → 不执行 |
| T194 | Stage 11 最终状态审查 | Reviewer | 审查 T186-T193 全部成果，确认安全链 |

注意：这些任务只是规划，T185 不实现它们。

---

## 12. Recommended Next Step

```text
NEXT_PENDING=T186
NEXT_STAGE=Stage 11
```

T186 任务：**设计 local request inbox dry-run 数据结构**

T186 职责：
1. 设计 ExternalRequest dataclass 的完整字段定义。
2. 设计 ExternalRequestSafetyGateResult dataclass。
3. 设计 RequestProposal dataclass。
4. 只设计数据结构，不实现 Python 文件。
5. 不修改 runner.py、tools/、agents/。

---

```text
TASK=T185
PLANNING_STATUS=done
STAGE11_PLAN_CREATED=yes
EXTERNAL_ENTRY_PLANNED=yes
LOCAL_REQUEST_INBOX_PLANNED=yes
GITHUB_ISSUE_ENTRY_PLANNED=yes
WEB_UI_ENTRY_IMPLEMENTED=no
API_ENTRY_IMPLEMENTED=no
N8N_ENTRY_IMPLEMENTED=no
EXTERNAL_EXECUTION_ENABLED=no
NEXT_PENDING=T186
NEXT_STAGE=Stage 11
```
