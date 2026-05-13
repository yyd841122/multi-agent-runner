# Stage 11 Local Request Inbox Design

设计时间：2026-05-13
设计角色：Architect Agent + Stage 11 Local Request Inbox Design Architect
目标：设计 local request inbox dry-run 数据结构，只设计不实现。

---

## 1. Background

1. Stage 11 的第一个外部入口建议从 local request inbox dry-run 开始。
2. local request inbox 是最安全的外部入口模拟方式。
3. 它不依赖 GitHub token。
4. 它不依赖 Web UI。
5. 它不依赖 API 鉴权。
6. 它不依赖 n8n。
7. 它只读取本地 request 文件并生成 proposal。
8. 它不直接执行任务。
9. 它不直接修改 docs/tasks.md。
10. 它不执行 Git。

Stage 8-10 安全基础：
- Stage 8：monitor → verify → report 最小闭环成立，max_tasks=1 受控。
- Stage 9：GitBackupGate dry-run 安全链成立，文件分类验证通过。
- Stage 10：返工 dry-run 安全链成立，auto_mending_planner 11 种 failure_type 分类、15 条决策规则、10 条安全门规则。

---

## 2. Design Goal

local request inbox dry-run 的目标：

1. 从本地 inbox 目录读取 request 文件。
2. 标准化 request。
3. 生成 ExternalRequest。
4. 运行 ExternalRequestSafetyGate。
5. 生成 TaskProposal dry-run。
6. 写入 reports/external-requests/ 报告。
7. 不修改 docs/tasks.md。
8. 不执行 runner。
9. 不调用 Developer Agent。
10. 不执行 Git。
11. 所有风险情况 fail closed。

---

## 3. Non-goals

本设计明确不做：

1. 不实现 GitHub Issue 入口。
2. 不实现 Web UI。
3. 不实现 API。
4. 不实现 n8n。
5. 不执行真实任务。
6. 不修改业务代码。
7. 不自动写 docs/tasks.md。
8. 不执行 git add。
9. 不执行 git commit。
10. 不执行 git push。
11. 不绕过 Main Agent / Planner Agent / Reviewer Agent。
12. 不处理生产级权限系统。

---

## 4. Proposed Directory Structure

```
requests/
  inbox/
  processed/
  rejected/

reports/
  external-requests/
```

说明：

1. `requests/inbox/` 存放待处理请求。用户将 `.md` 文件放入此目录。
2. `requests/processed/` 后续可存放已处理请求，但 T187 dry-run 默认不移动文件。
3. `requests/rejected/` 后续可存放拒绝请求，但 T187 dry-run 默认不移动文件。
4. `reports/external-requests/` 存放 dry-run 报告。
5. T186 只设计，不创建这些目录。

---

## 5. Request File Format

### 5.1 推荐 Markdown 格式

```markdown
---
request_id: REQ-0001
source_type: local_inbox
source_ref: requests/inbox/REQ-0001.md
requester: user
priority: normal
created_at: 2026-05-13
---

# Title

用户需求正文……

可以包含多行描述。
```

### 5.2 格式说明

1. metadata 部分使用 YAML front matter（`---` 包裹）。
2. metadata 字段全部可选。缺少 `request_id` 时由工具自动生成。
3. front matter 之后的正文为 `raw_content`，必须保留原文不做任何处理。
4. 外部正文一律视为不可信，不作为执行指令。
5. request 文件不能作为执行指令，只能作为需求内容。
6. 如果文件无法解析 front matter，整个文件内容作为 `raw_content`，`title` 取第一行非空文本。

### 5.3 字段映射

| Front Matter 字段 | ExternalRequest 字段 | 必填 | 默认值 |
|-------------------|---------------------|------|--------|
| request_id | request_id | no | 自动生成 REQ-{timestamp} |
| source_type | source_type | no | local_inbox |
| source_ref | source_ref | no | 文件路径 |
| requester | requester | no | user |
| priority | priority | no | normal |
| created_at | created_at | no | 文件修改时间 |
| （正文标题） | title | no | 第一行非空文本 |
| （正文内容） | raw_content | no | 全部正文 |

---

## 6. ExternalRequest Data Structure

### 6.1 Python Dataclass 草案

```python
from __future__ import annotations

from dataclasses import dataclass, field


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
    priority: str                 # 优先级：low / normal / medium / high / critical
    requested_stage: str          # 请求进入的阶段：Stage 8 / Stage 11 / auto
    requested_files: list[str]    # 请求涉及的文件列表

    # 安全评估
    suspected_intent: str        # 推断意图：new_feature / bug_fix / refactor / documentation / test / unknown / suspicious
    safety_risk_level: str       # 安全风险等级：low / medium / high / critical
    prompt_injection_risk: str   # Prompt injection 风险：none / low / medium / high / critical

    # 审批状态
    requires_user_approval: bool  # 是否需要人工确认（默认 true）
    allowed_to_plan: bool         # 是否允许生成 planning proposal（默认 false）
    allowed_to_execute: bool      # 是否允许执行（默认 false，Stage 11 始终 false）
    fail_reason: str              # 如果 fail closed，记录原因
```

### 6.2 字段说明

| # | 字段 | 类型 | 默认值 | 说明 |
|---|------|------|--------|------|
| 1 | request_id | str | 自动生成 | 请求唯一标识 |
| 2 | source_type | str | local_inbox | 来源类型 |
| 3 | source_ref | str | 文件路径 | 来源引用 |
| 4 | title | str | 空字符串 | 请求标题 |
| 5 | raw_content | str | 原文 | 原始内容，不做任何处理 |
| 6 | normalized_summary | str | 空字符串 | 系统生成摘要 |
| 7 | requester | str | user | 请求者标识 |
| 8 | created_at | str | 当前时间 | 创建时间 ISO 8601 |
| 9 | priority | str | normal | 优先级 |
| 10 | requested_stage | str | auto | 请求阶段 |
| 11 | requested_files | list[str] | 空列表 | 涉及文件 |
| 12 | suspected_intent | str | unknown | 推断意图 |
| 13 | safety_risk_level | str | high | 安全风险（默认 high，safety gate 通过后降级） |
| 14 | prompt_injection_risk | str | high | Prompt injection 风险（默认 high，检查后降级） |
| 15 | requires_user_approval | bool | True | 是否需要人工确认 |
| 16 | allowed_to_plan | bool | False | 是否允许生成 proposal |
| 17 | allowed_to_execute | bool | False | 是否允许执行（Stage 11 始终 False） |
| 18 | fail_reason | str | 空字符串 | fail closed 原因 |

---

## 7. ExternalRequestSafetyResult Data Structure

### 7.1 Python Dataclass 草案

```python
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExternalRequestSafetyResult:
    """外部请求安全门检查结果。"""

    # 基础标识
    ok: bool                       # 安全门是否通过
    request_id: str                # 请求唯一标识

    # 风险评估
    risk_level: str                # 最终风险等级：low / medium / high / critical
    prompt_injection_risk: str     # Prompt injection 风险：none / low / medium / high / critical

    # 阻止原因
    blocked_reasons: list[str]     # 被阻止的原因列表（空列表表示无阻止）
    warnings: list[str]            # 警告列表（不阻止但需注意）

    # 审批决策
    allowed_to_plan: bool          # 是否允许生成 planning proposal
    allowed_to_execute: bool       # 是否允许执行（Stage 11 始终 False）
    requires_user_approval: bool   # 是否需要人工确认

    # 后续动作
    next_action: str               # generate_proposal / reject / wait_for_approval / stop
```

### 7.2 字段说明

| # | 字段 | 类型 | 默认值 | 说明 |
|---|------|------|--------|------|
| 1 | ok | bool | False | 安全门是否通过 |
| 2 | request_id | str | 必填 | 请求唯一标识 |
| 3 | risk_level | str | high | 最终风险等级 |
| 4 | prompt_injection_risk | str | high | Prompt injection 风险 |
| 5 | blocked_reasons | list[str] | 空列表 | 被阻止的原因 |
| 6 | warnings | list[str] | 空列表 | 警告列表 |
| 7 | allowed_to_plan | bool | False | 是否允许生成 proposal |
| 8 | allowed_to_execute | bool | False | 是否允许执行 |
| 9 | requires_user_approval | bool | True | 是否需要人工确认 |
| 10 | next_action | str | stop | 后续动作 |

---

## 8. TaskProposal Data Structure

### 8.1 Python Dataclass 草案

```python
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TaskProposal:
    """外部请求生成的任务提案。"""

    # 基础标识
    proposal_id: str              # 提案唯一标识，格式：PROP-{timestamp}
    request_id: str               # 关联的外部请求 ID
    title: str                    # 提案标题

    # 内容
    normalized_summary: str       # 标准化摘要

    # 提案任务
    proposed_tasks: list[str]     # 建议的任务列表（如 ["T-new-1: xxx", "T-new-2: xxx"]）
    proposed_files: list[str]     # 预计涉及的文件
    forbidden_files: list[str]    # 禁止涉及的文件

    # Agent 规划
    required_agents: list[str]    # 需要参与的 Agent（如 ["Developer", "Tester"]）

    # 风险评估
    risk_level: str               # 风险等级：low / medium / high / critical
    requires_user_approval: bool  # 是否需要人工确认（始终 True）

    # 审批状态
    allowed_to_write_tasks: bool  # 是否允许写入 docs/tasks.md（Stage 11 始终 False）
    allowed_to_execute: bool      # 是否允许执行（Stage 11 始终 False）
    next_action: str              # wait_for_approval / reject / stop
```

### 8.2 字段说明

| # | 字段 | 类型 | 默认值 | 说明 |
|---|------|------|--------|------|
| 1 | proposal_id | str | 自动生成 | 提案唯一标识 |
| 2 | request_id | str | 必填 | 关联的外部请求 ID |
| 3 | title | str | 空字符串 | 提案标题 |
| 4 | normalized_summary | str | 空字符串 | 标准化摘要 |
| 5 | proposed_tasks | list[str] | 空列表 | 建议的任务列表 |
| 6 | proposed_files | list[str] | 空列表 | 预计涉及的文件 |
| 7 | forbidden_files | list[str] | 空列表 | 禁止涉及的文件 |
| 8 | required_agents | list[str] | 空列表 | 需要参与的 Agent |
| 9 | risk_level | str | high | 风险等级 |
| 10 | requires_user_approval | bool | True | 是否需要人工确认 |
| 11 | allowed_to_write_tasks | bool | False | 是否允许写入 tasks.md |
| 12 | allowed_to_execute | bool | False | 是否允许执行 |
| 13 | next_action | str | wait_for_approval | 后续动作 |

---

## 9. RequestInboxRecord Data Structure

### 9.1 Python Dataclass 草案

```python
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RequestInboxRecord:
    """请求收件箱处理记录。"""

    # 文件信息
    request_path: str             # 请求文件路径
    request_id: str               # 请求唯一标识

    # 处理状态
    parse_status: str             # 解析状态：pass / fail
    safety_status: str            # 安全检查状态：pass / fail
    proposal_status: str          # 提案生成状态：created / skipped / failed

    # 输出
    report_path: str              # 报告文件路径

    # 时间
    processed_at: str             # 处理时间（ISO 8601）

    # Dry-run 标记
    dry_run: bool                 # 是否 dry-run（Stage 11 始终 True）
    moved_to_processed: bool      # 是否移动到 processed（Stage 11 始终 False）
    moved_to_rejected: bool       # 是否移动到 rejected（Stage 11 始终 False）

    # 失败原因
    fail_reason: str              # 失败原因（空字符串表示无失败）
```

### 9.2 字段说明

| # | 字段 | 类型 | 默认值 | 说明 |
|---|------|------|--------|------|
| 1 | request_path | str | 必填 | 请求文件路径 |
| 2 | request_id | str | 自动生成 | 请求唯一标识 |
| 3 | parse_status | str | pending | 解析状态 |
| 4 | safety_status | str | pending | 安全检查状态 |
| 5 | proposal_status | str | pending | 提案生成状态 |
| 6 | report_path | str | 自动生成 | 报告文件路径 |
| 7 | processed_at | str | 当前时间 | 处理时间 |
| 8 | dry_run | bool | True | 是否 dry-run |
| 9 | moved_to_processed | bool | False | 是否移动到 processed |
| 10 | moved_to_rejected | bool | False | 是否移动到 rejected |
| 11 | fail_reason | str | 空字符串 | 失败原因 |

---

## 10. Safety Gate Rules

安全门按顺序检查，任何规则命中即执行对应动作：

| # | 规则 | 结果 | 说明 |
|---|------|------|------|
| 1 | 空请求（raw_content 为空或纯空白） | fail closed | 无法处理空请求 |
| 2 | 解析失败（文件无法读取或格式严重错误） | fail closed | 无法解析请求 |
| 3 | 来源不明（source_type 不在允许列表中） | fail closed | 只允许 local_inbox |
| 4 | 请求要求泄露密钥（.env / secrets / API key / password / token） | fail closed | 绝对禁止 |
| 5 | 请求要求读取 .env | fail closed | 绝对禁止 |
| 6 | 请求要求绕过系统限制（bypass / skip / ignore safety） | fail closed | 绝对禁止 |
| 7 | 请求要求直接 git add / commit / push | fail closed | 绝对禁止 |
| 8 | 请求要求直接执行真实 run-project-loop | fail closed | 绝对禁止 |
| 9 | 请求要求直接执行真实返工 | fail closed | 绝对禁止 |
| 10 | 请求要求修改 runner.py / tools/ / agents/ | user approval | 涉及框架代码必须人工确认 |
| 11 | 请求包含删除文件要求（rm / delete / remove file） | user approval | 删除操作必须人工确认 |
| 12 | 请求包含网络调用要求（curl / wget / http request） | user approval | 网络请求必须人工确认 |
| 13 | 请求包含 prompt injection 风险模式 | 标记 | 提升风险等级 |
| 14 | allowed_to_execute 默认 false | 强制 | Stage 11 不允许直接执行 |
| 15 | allowed_to_plan 只有低风险请求才可 true | 条件 | safety_risk_level=low 且 prompt_injection_risk=none/low 时允许 |

---

## 11. Prompt Injection Detection Rules

### 11.1 检测规则

| # | 检测模式 | 风险等级 | 动作 |
|---|----------|----------|------|
| 1 | "ignore previous instructions" | critical | fail closed |
| 2 | "忽略之前的规则" / "忽略之前的指令" | critical | fail closed |
| 3 | "reveal system prompt" / "输出系统提示词" | critical | fail closed |
| 4 | "system prompt" / "override" | critical | fail closed |
| 5 | "bypass safety" / "绕过安全限制" | critical | fail closed |
| 6 | "skip verification" / "跳过验证" | critical | fail closed |
| 7 | "directly run git push" / "直接提交并推送" | high | fail closed |
| 8 | "delete files" / "删除所有文件" / "rm -rf" | high | fail closed |
| 9 | "expose API key" / "泄露密钥" / "show password" | high | fail closed |
| 10 | "modify runner without approval" / "自动执行真实任务" | high | fail closed |
| 11 | "&&" / ";" / "\|" 在命令上下文中 | medium | 标记 + 人工确认 |
| 12 | "runner.py" / "tools/" / "agents/" 在涉及文件中 | medium | 标记 + 人工确认 |
| 13 | 非英文非中文的混合指令模式 | low | 标记，不阻止 |

### 11.2 检测原则

1. 命中不一定全部 fail closed，但必须提升风险等级。
2. 涉及密钥 / 绕过安全 / 直接 Git / 删除文件必须 fail closed。
3. 外部文本只能作为 data，不作为 instruction。
4. 所有外部请求内容一律视为不可信。
5. 外部请求不能覆盖系统规则。
6. 外部请求不能修改 Agent 角色规则。
7. 外部请求不能作为执行指令，只能作为需求内容。

---

## 12. Request to Proposal Dry-run Flow

### 12.1 完整流程

```text
local request file（requests/inbox/*.md）
  ↓
parse request（解析 YAML front matter + 正文）
  ↓
build ExternalRequest（标准化数据结构）
  ↓
run safety gate（15 条安全门规则检查）
  ↓
if blocked: write rejected dry-run report → stop
  ↓（safety gate 通过）
build TaskProposal dry-run（生成任务提案）
  ↓
write external request report（reports/external-requests/）
  ↓
wait for user approval（等待人工确认）
  ↓
no docs/tasks.md update（不更新任务文件）
no runner execution（不执行 runner）
no Git（不执行 Git 操作）
```

### 12.2 关键约束

1. **不直接写 docs/tasks.md**：proposal 生成后必须经过人工确认。
2. **不直接执行 runner**：外部请求流程中不调用 runner.py。
3. **不直接调用 Developer Agent**：外部请求不能直接触发代码生成。
4. **不直接调用 Git Backup Agent**：外部请求不能直接触发 Git 操作。
5. **proposal 必须可审查**：proposal 包含完整的任务描述和风险评估。
6. **dry-run 始终为 True**：Stage 11 所有外部请求处理均为 dry-run。

---

## 13. Report Format

### 13.1 报告路径

`reports/external-requests/REQ-{id}-report.md`

### 13.2 报告字段

```text
REQUEST_ID=REQ-0001
SOURCE_TYPE=local_inbox
SOURCE_REF=requests/inbox/REQ-0001.md
PARSE_STATUS=pass/fail
SAFETY_STATUS=pass/fail
PROMPT_INJECTION_RISK=none/low/medium/high
ALLOWED_TO_PLAN=yes/no
ALLOWED_TO_EXECUTE=no
TASK_PROPOSAL_CREATED=yes/no
DOCS_TASKS_MODIFIED=no
RUNNER_EXECUTED=no
GIT_ADD_EXECUTED=no
GIT_COMMIT_EXECUTED=no
GIT_PUSH_EXECUTED=no
CHECK_RESULT=pass/fail
```

### 13.3 报告说明

1. 每个处理过的 request 生成一份报告。
2. 报告包含完整的处理链路状态。
3. DOCS_TASKS_MODIFIED 始终为 no（Stage 11 dry-run 不修改 tasks.md）。
4. RUNNER_EXECUTED 始终为 no。
5. GIT_ADD/COMMIT/PUSH 始终为 no。

---

## 14. T187 Implementation Scope

T187 应只实现 dry-run：

1. 创建 `tools/external_request_inbox.py`。
2. 使用 Python 标准库（dataclass、re、pathlib、datetime）。
3. 读取 `requests/inbox/` 下指定文件。
4. 解析 Markdown YAML front matter 和正文。
5. 构建 ExternalRequest。
6. 执行 safety gate（15 条规则）。
7. 构建 TaskProposal dry-run。
8. 写 `reports/external-requests/` 报告。
9. 不移动 request 文件。
10. 不修改 docs/tasks.md。
11. 不执行 runner。
12. 不执行 Git。
13. 不调用模型。
14. fail closed。

### 14.1 T187 不做的事情

1. 不创建 GitHub Issue workflow。
2. 不创建 Web UI。
3. 不创建 API。
4. 不创建 n8n workflow。
5. 不修改 runner.py。
6. 不修改 tools/ 下其他文件。
7. 不修改 agents/。
8. 不执行 git add/commit/push。
9. 不调用 Claude Agent SDK。

---

## 15. Acceptance Criteria

T186 完成标准：

1. docs/stage11-local-request-inbox-design.md 已创建。
2. ExternalRequest 已设计（18 字段）。
3. ExternalRequestSafetyResult 已设计（10 字段）。
4. TaskProposal 已设计（13 字段）。
5. RequestInboxRecord 已设计（11 字段）。
6. request 文件格式已设计（YAML front matter + Markdown）。
7. safety gate 规则已设计（15 条）。
8. prompt injection 检测规则已设计（13 条）。
9. request → proposal dry-run 流程已设计。
10. T187 实现范围已明确。
11. 未创建 tools/external_request_inbox.py。
12. 未修改 runner.py。
13. 未修改 tools/。
14. NEXT_PENDING=T187。
15. NEXT_STAGE=Stage 11。

---

```text
TASK=T186
DESIGN_STATUS=done
LOCAL_REQUEST_INBOX_DESIGNED=yes
EXTERNAL_REQUEST_DESIGNED=yes
SAFETY_RESULT_DESIGNED=yes
TASK_PROPOSAL_DESIGNED=yes
REQUEST_INBOX_RECORD_DESIGNED=yes
PROMPT_INJECTION_RULES_DESIGNED=yes
EXTERNAL_REQUEST_INBOX_IMPLEMENTED=no
EXTERNAL_EXECUTION_ENABLED=no
NEXT_PENDING=T187
NEXT_STAGE=Stage 11
```
