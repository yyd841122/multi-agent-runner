# Stage 11 GitHub Issue Entry Dry-run Design

设计时间：2026-05-13
设计角色：Architect Agent + Stage 11 GitHub Issue External Entry Design Architect
目标：设计 GitHub Issue → ExternalRequest 的转换流程，只设计不实现。

---

## 1. Background

1. Stage 11 已经通过 local request inbox dry-run 建立第一个外部入口基础（T186-T188）。
2. ExternalRequest 数据结构已设计并实现，支持 source_type 字段扩展。
3. ExternalRequestSafetyGate 已实现 17 条安全门规则，fail closed 行为已验证。
4. TaskProposal dry-run 已实现，allowed_to_execute 始终为 false。
5. GitHub Issue 是 Stage 11 规划的第二类外部入口候选。
6. GitHub Issue 内容必须视为不可信外部输入。
7. GitHub Issue 不能直接触发真实执行。
8. GitHub Issue 不能直接触发 Git 操作。
9. GitHub Issue 只能生成 proposal。
10. 所有 proposal 必须等待人工确认。
11. 本设计不创建 workflow，不访问 GitHub API，不启用真实执行。

### 1.1 已有基础

| 组件 | 状态 | 来源 |
|------|------|------|
| ExternalRequest dataclass | 已实现 | tools/external_request_inbox.py |
| ExternalRequestSafetyResult dataclass | 已实现 | tools/external_request_inbox.py |
| TaskProposal dataclass | 已实现 | tools/external_request_inbox.py |
| RequestInboxRecord dataclass | 已实现 | tools/external_request_inbox.py |
| Safety gate (17 rules) | 已验证 | T188 fail closed 验证通过 |
| Prompt injection detection | 已实现 | tools/external_request_inbox.py |
| Local request inbox CLI | 已实现 | tools/external_request_inbox.py |

### 1.2 需要新增

| 组件 | 说明 |
|------|------|
| GitHubIssueRequest dataclass | GitHub Issue 专用数据结构 |
| IssueToExternalRequest mapping | Issue → ExternalRequest 转换规则 |
| GitHub Issue safety rules 扩展 | 基于 Issue 特征的安全规则 |
| GitHub Issue fixture format | 本地模拟 issue 文件格式 |
| reports/github-issues/ 报告格式 | GitHub Issue 专用报告 |

---

## 2. Design Goal

GitHub Issue entry dry-run 的目标：

1. 接收或读取 GitHub Issue 数据（从本地 fixture 文件）。
2. 标准化 issue title / body / labels / author / url。
3. 转换为 ExternalRequest。
4. 运行 ExternalRequestSafetyGate。
5. 生成 TaskProposal dry-run。
6. 写入 reports/github-issues/ 报告。
7. 不修改 docs/tasks.md。
8. 不执行 runner。
9. 不执行 Git。
10. 不创建 GitHub comment。
11. 不关闭 issue。
12. 不添加 label。
13. 所有风险情况 fail closed。

---

## 3. Non-goals

本设计明确不做：

1. 不创建 GitHub Actions workflow。
2. 不访问 GitHub API。
3. 不配置 GitHub token。
4. 不读取真实线上 issue。
5. 不创建 Webhook。
6. 不创建 Web UI。
7. 不创建 API。
8. 不创建 n8n workflow。
9. 不执行真实任务。
10. 不修改业务代码。
11. 不自动写 docs/tasks.md。
12. 不执行 git add。
13. 不执行 git commit。
14. 不执行 git push。
15. 不评论 issue。
16. 不关闭 issue。
17. 不处理生产级权限系统。

---

## 4. Proposed Data Source Modes

### 4.1 Local GitHub Issue Fixture

说明：

1. 使用本地 JSON 文件模拟 GitHub Issue 数据。
2. 安全性最高：不依赖网络，不依赖 token，不依赖外部服务。
3. T190 应优先实现这种模式。
4. 不依赖 GitHub token。
5. 不访问网络。
6. fixture 文件格式基于 GitHub REST API v3 response 的子集。

### 4.2 GitHub CLI Export

说明：

1. 后续可由人工用 `gh issue view <number> --json` 导出为 JSON 文件。
2. 工具只读取导出的本地文件。
3. 不直接调用 `gh` CLI。
4. 不直接访问 GitHub API。
5. 导出操作由人工手动完成，系统不自动化。

### 4.3 GitHub API Read-only Mode

说明：

1. 后续可规划。
2. 需要 token、权限、限流、安全审计。
3. 当前不实现。
4. 即使实现也必须是 read-only，不允许写操作。

### 4.4 GitHub Actions Event Mode

说明：

1. 后续可规划。
2. 风险较高：GitHub Actions event payload 可能被伪造。
3. 必须先有严格 prompt injection 防护。
4. 当前不实现。
5. 即使实现也必须经过完整 safety gate。

### 4.5 模式选择建议

| 阶段 | 模式 | 优先级 |
|------|------|--------|
| T190 | Local fixture | P0 — 必须实现 |
| 后续 | GitHub CLI export | P1 — 建议实现 |
| 后续 | GitHub API read-only | P2 — 可规划 |
| 后续 | GitHub Actions event | P3 — 风险评估后再定 |

---

## 5. GitHubIssueRequest Data Structure

### 5.1 Python Dataclass 草案

```python
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GitHubIssueRequest:
    """GitHub Issue 请求数据结构，用于标准化来自 GitHub Issue 的外部输入。"""

    # Issue 基础标识
    issue_id: int                    # GitHub Issue 内部 ID（数字）
    issue_number: int                # GitHub Issue 编号（仓库内可见编号）
    repository: str                  # 仓库名称（格式：owner/repo）

    # Issue 内容
    title: str                       # Issue 标题（不可信）
    body: str                        # Issue 正文（不可信）

    # Issue 作者信息
    author: str                      # Issue 作者用户名（不可信）
    author_association: str          # 作者关联类型：OWNER / MEMBER / COLLABORATOR / CONTRIBUTOR / NONE

    # Issue 元数据
    labels: list[str]                # Issue 标签列表（不可信，只能作为 hints）
    assignees: list[str]             # Issue 指派人列表
    milestone: str                   # Issue 里程碑
    state: str                       # Issue 状态：open / closed

    # 时间
    created_at: str                  # Issue 创建时间（ISO 8601）
    updated_at: str                  # Issue 更新时间（ISO 8601）

    # Issue 链接
    issue_url: str                   # Issue URL

    # 数据源信息
    source_mode: str                 # 数据源模式：local_fixture / gh_export / api_readonly

    # 原始数据路径
    raw_payload_path: str            # 原始 fixture 文件路径

    # Comments
    comments_included: bool          # 是否包含 comments
    comments: list[dict]             # Comment 列表（每个包含 author, body, created_at）

    # 信任评估
    trusted_author: bool             # 作者是否可信（默认 false）
    fail_reason: str                 # 解析失败原因
```

### 5.2 字段说明

| # | 字段 | 类型 | 默认值 | 说明 |
|---|------|------|--------|------|
| 1 | issue_id | int | 0 | GitHub Issue 内部 ID |
| 2 | issue_number | int | 0 | 仓库内 Issue 编号 |
| 3 | repository | str | 空字符串 | 仓库名 owner/repo |
| 4 | title | str | 空字符串 | Issue 标题（不可信） |
| 5 | body | str | 空字符串 | Issue 正文（不可信） |
| 6 | author | str | 空字符串 | 作者用户名（不可信） |
| 7 | author_association | str | NONE | 作者关联类型 |
| 8 | labels | list[str] | 空列表 | 标签（不可信，只能作为 hints） |
| 9 | assignees | list[str] | 空列表 | 指派人列表 |
| 10 | milestone | str | 空字符串 | 里程碑 |
| 11 | state | str | open | Issue 状态 |
| 12 | created_at | str | 空字符串 | 创建时间 ISO 8601 |
| 13 | updated_at | str | 空字符串 | 更新时间 ISO 8601 |
| 14 | issue_url | str | 空字符串 | Issue URL |
| 15 | source_mode | str | local_fixture | 数据源模式 |
| 16 | raw_payload_path | str | 空字符串 | 原始 fixture 文件路径 |
| 17 | comments_included | bool | False | 是否包含 comments |
| 18 | comments | list[dict] | 空列表 | Comment 列表 |
| 19 | trusted_author | bool | False | 作者是否可信（默认 false） |
| 20 | fail_reason | str | 空字符串 | 解析失败原因 |

### 5.3 author_association 信任映射

| author_association | trusted_author | 风险等级 |
|-------------------|----------------|----------|
| OWNER | true（但仍需 safety gate） | low |
| MEMBER | true（但仍需 safety gate） | low |
| COLLABORATOR | true（但仍需 safety gate） | low |
| CONTRIBUTOR | false | medium |
| NONE / 其他 | false | high |

说明：即使 trusted_author=true，Issue 内容仍必须经过完整 safety gate 检查。trusted_author 只影响优先级和报告中的信任标记，不影响安全检查结果。

### 5.4 GitHub Issue Fixture 文件格式

T190 使用本地 JSON 文件模拟 GitHub Issue 数据：

```json
{
  "issue_id": 123456,
  "issue_number": 42,
  "repository": "owner/repo",
  "title": "Add feature X",
  "body": "Please add feature X that does Y.",
  "author": "octocat",
  "author_association": "CONTRIBUTOR",
  "labels": ["enhancement", "good-first-issue"],
  "assignees": [],
  "milestone": "",
  "state": "open",
  "created_at": "2026-05-13T10:00:00Z",
  "updated_at": "2026-05-13T10:00:00Z",
  "issue_url": "https://github.com/owner/repo/issues/42"
}
```

Fixture 文件存放路径：`requests/github-fixtures/`

---

## 6. IssueToExternalRequest Mapping

### 6.1 映射规则

| # | ExternalRequest 字段 | 映射来源 | 说明 |
|---|---------------------|----------|------|
| 1 | request_id | `GH-ISSUE-{repository}-{issue_number}` | 格式：仓库名中 / 替换为 - |
| 2 | source_type | 固定值 `github_issue` | 标识来源为 GitHub Issue |
| 3 | source_ref | issue_url 或 local fixture path | 优先使用 issue_url |
| 4 | title | issue title | 直接映射（不可信） |
| 5 | raw_content | issue title + "\n\n" + issue body + selected comments | 拼接内容（不可信） |
| 6 | normalized_summary | 系统生成 | 由 safety gate 或 proposal 生成 |
| 7 | requester | issue author | 直接映射（不可信） |
| 8 | created_at | issue created_at | 直接映射 |
| 9 | priority | 由 labels 推断，默认 normal | 见 6.2 优先级映射 |
| 10 | requested_stage | 固定值 `auto` | 不允许 Issue 指定阶段 |
| 11 | requested_files | 从正文和 labels 推断 | 必须不可信 |
| 12 | suspected_intent | 由 title/body 低风险推断 | 见 6.3 意图推断 |
| 13 | safety_risk_level | 默认 `high`，safety gate 后降级 | 与 local inbox 一致 |
| 14 | prompt_injection_risk | 默认 `high`，检测后降级 | 与 local inbox 一致 |
| 15 | requires_user_approval | 默认 `true` | 始终需要人工确认 |
| 16 | allowed_to_plan | 默认 `false` | safety gate 通过后可设为 true |
| 17 | allowed_to_execute | 固定值 `false` | Stage 11 始终 false |
| 18 | fail_reason | 空 | 映射无失败时为空 |

### 6.2 优先级映射

| Label | priority | 说明 |
|-------|----------|------|
| priority: critical / urgent | critical | 最高优先级（但仍需 safety gate） |
| priority: high | high | 高优先级 |
| priority: medium | normal | 中优先级（默认） |
| 无 priority label | normal | 默认 |
| priority: low | low | 低优先级 |

注意：priority label 不可信，只能作为 hints。高优先级 label 不能绕过安全门。

### 6.3 意图推断

| 关键词 / Label | suspected_intent |
|---------------|-----------------|
| label=bug / fix / "修复" | bug_fix |
| label=enhancement / "新增" / "增加" / "add" | new_feature |
| label=refactor / "重构" | refactor |
| label=documentation / "文档" | documentation |
| label=test / "测试" | test |
| label=security / "安全" | suspicious（提升审查等级） |
| 无匹配 | unknown |

---

## 7. GitHub Issue Safety Rules

### 7.1 安全门规则（20 条）

GitHub Issue 安全门在 local inbox 17 条规则基础上增加 3 条 Issue 专用规则：

| # | 规则 | 结果 | 说明 |
|---|------|------|------|
| 1 | 空 issue（title 和 body 都为空） | fail closed | 无法处理空 issue |
| 2 | 缺失 title 或 body | fail closed 或 marked incomplete | 缺少核心信息 |
| 3 | 来源不明（source_type 不是 github_issue） | fail closed | 只允许已知来源 |
| 4 | 未知 repository | fail closed | 不在允许的仓库列表中 |
| 5 | issue author 默认不可信 | 标记 | 所有作者内容需检查 |
| 6 | external contributor（author_association=NONE/CONTRIBUTOR） | 默认高风险 | 外部贡献者 |
| 7 | 请求泄露密钥（.env / secrets / API key / password / token） | fail closed | 绝对禁止 |
| 8 | 请求读取 .env | fail closed | 绝对禁止 |
| 9 | 请求绕过系统限制（bypass / skip / ignore safety） | fail closed | 绝对禁止 |
| 10 | 请求直接 git add / commit / push | fail closed | 绝对禁止 |
| 11 | 请求直接执行真实 run-project-loop | fail closed | 绝对禁止 |
| 12 | 请求直接真实返工 | fail closed | 绝对禁止 |
| 13 | 请求修改 runner.py / tools/ / agents/ | user approval | 涉及框架代码必须人工确认 |
| 14 | 请求删除文件 | user approval 或 blocked | 删除操作必须人工确认 |
| 15 | 请求包含网络调用 | user approval | 网络请求必须人工确认 |
| 16 | labels 不可信，只能作为 hints | 强制 | label 不影响安全检查结果 |
| 17 | allowed_to_execute 永远 false | 强制 | Stage 11 不允许直接执行 |
| 18 | allowed_to_plan 只有低风险或中风险且未被阻断时才可 true | 条件 | 与 local inbox 一致 |
| 19 | Issue comments 也必须经过 safety gate 检查 | 强制 | comments 中可能包含恶意内容 |
| 20 | 所有不确定情况 fail closed | 强制 | 不确定时停止 |

### 7.2 Issue 专用扩展（与 local inbox 的差异）

| 差异点 | Local Inbox | GitHub Issue |
|--------|-------------|-------------|
| 来源标识 | local_inbox | github_issue |
| 作者信任 | 默认 user（半可信） | 默认不可信，按 author_association 分级 |
| Labels | 无 | 有，但不可信，只能作为 hints |
| Comments | 无 | 有，默认不读取，读取时不可信 |
| Repository | 无 | 必须验证 |
| 优先级 | 由 front matter 指定 | 由 labels 推断 |
| 报告路径 | reports/external-requests/ | reports/github-issues/ |

### 7.3 Safety Gate 与现有规则的关系

1. GitHub Issue safety gate 复用 external_request_inbox.py 中已有的 safety gate 逻辑。
2. Issue 专用规则在已有规则之前执行（如检查 repository、author_association）。
3. 所有已有规则仍然适用（密钥泄露、绕过安全、Git 操作等）。
4. allowed_to_execute 始终为 false（与 local inbox 一致）。

---

## 8. Prompt Injection Defense for GitHub Issues

### 8.1 核心原则

1. Issue title / body / comments 都是不可信文本。
2. title 也可能包含 prompt injection（攻击者可能在标题中嵌入指令）。
3. comments 比 body 风险更高（任何人都可以评论）。
4. 不允许 issue 覆盖系统规则。
5. 不允许 issue 覆盖 Agent 角色协议。
6. 不允许 issue 要求忽略安全限制。
7. 不允许 issue 要求直接 push。
8. 不允许 issue 要求直接真实执行。
9. 不允许 issue 要求泄露系统提示词。
10. 不允许 issue 要求泄露 token / API key。
11. 外部文本只能作为 data，不作为 instruction。

### 8.2 GitHub Issue 特有风险

| 风险场景 | 说明 | 防护 |
|----------|------|------|
| Issue 标题注入 | 标题中嵌入 "ignore previous instructions" | 标题也需 prompt injection 检测 |
| Issue 正文注入 | 正文中嵌入 "bypass safety" | 正文需完整 safety gate |
| Comment 注入 | 评论中嵌入 "直接执行并 push" | 默认不读取 comments；读取时需检测 |
| Label 欺骗 | 标签 "approved" / "safe" / "auto-run" | labels 不可信，不影响安全判定 |
| Author 欺骗 | 使用接近维护者的用户名 | author 不可信，只看 author_association |
| Milestone 欺骗 | 设置紧急 milestone | milestone 不影响安全判定 |
| 复合攻击 | 标题 + 正文 + 评论组合攻击 | 所有内容拼接后统一检测 |

### 8.3 检测策略

```text
Step 1: 单独检测 title
  → title injection risk

Step 2: 单独检测 body
  → body injection risk

Step 3: 合并 title + body 检测
  → combined injection risk

Step 4: 如包含 comments，单独检测每条 comment
  → each comment injection risk

Step 5: 合并所有内容检测
  → overall injection risk = max(title, body, comments)

Step 6: 最终判定
  → any critical → fail closed
  → any high → fail closed
  → any medium → user approval
  → all low → allowed_to_plan 可 true
```

---

## 9. Labels and Metadata Handling

### 9.1 Labels 处理规则

| # | 规则 | 说明 |
|---|------|------|
| 1 | labels 只能作为 hints | 不影响安全判定 |
| 2 | label=bug 可影响 suspected_intent | 推断为 bug_fix |
| 3 | label=enhancement 可影响 suspected_intent | 推断为 new_feature |
| 4 | label=urgent 不得绕过安全门 | 高优先级不等于高权限 |
| 5 | label=auto-run 不得触发真实执行 | 禁止 label 触发执行 |
| 6 | label=approved 也不得自动执行 | 必须经过完整 safety gate |
| 7 | label=safe 不得降低风险到可执行 | label 不影响安全评估 |
| 8 | label=security 必须提升审查等级 | 涉及安全的 Issue 需更严格审查 |
| 9 | label 涉及 runner/tools/agents 必须 user approval | 框架相关 label 需人工确认 |
| 10 | 所有 label 都必须可审计 | 报告中记录所有 label |

### 9.2 敏感 Label 处理

| Label | 处理方式 | 说明 |
|-------|----------|------|
| auto-run / auto-execute | ignored + warning | 忽略并记录警告 |
| approved / safe / verified | ignored + warning | 忽略并记录警告 |
| urgent / critical / priority:high | 优先级提升，不影响安全 | 优先级 ≠ 权限 |
| security / vulnerability | 审查等级提升 | 更严格的安全检查 |
| runner / tools / agents | user approval | 涉及框架代码 |
| good-first-issue / help-wanted | 不影响安全 | 仅影响 intent 推断 |

### 9.3 Metadata 处理规则

| 元数据 | 处理方式 | 说明 |
|--------|----------|------|
| milestone | 不影响安全判定 | 仅作为信息记录 |
| assignees | 不影响安全判定 | 仅作为信息记录 |
| state | 只有 open 才处理 | closed issue 不处理 |
| created_at / updated_at | 不影响安全判定 | 仅作为信息记录 |
| repository | 必须验证 | 不在允许列表中则 fail closed |

---

## 10. Comments Handling

### 10.1 处理规则

| # | 规则 | 说明 |
|---|------|------|
| 1 | 默认 T190 不读取 comments | 最小风险策略 |
| 2 | 后续如读取 comments，必须限制数量和长度 | 防止大量评论攻击 |
| 3 | comments 不能作为执行指令 | 评论内容一律视为不可信数据 |
| 4 | maintainer comment 也不能直接触发真实执行 | 即使是仓库维护者的评论 |
| 5 | comment 中的 /run、/execute、/push 必须 fail closed 或 wait approval | 命令式评论必须拦截 |
| 6 | comments 必须进入 prompt injection 检测 | 与 body 检测标准一致 |

### 10.2 Comments 读取限制

| 限制项 | 默认值 | 说明 |
|--------|--------|------|
| max_comments | 0（不读取） | T190 不读取 |
| max_comment_length | 1000 字符 | 单条评论最大长度 |
| max_total_comments_length | 5000 字符 | 评论总长度限制 |

### 10.3 后续 Comments 支持路径

```text
T190: 不读取 comments（max_comments=0）
  ↓
后续迭代 1: 读取最多 5 条 comments，仅 maintainer/owner/collaborator
  ↓
后续迭代 2: 读取所有 comments，但限制总长度
  ↓
后续迭代 3: comments 也可影响 proposal（但仍不可信）
```

---

## 11. Issue to Proposal Dry-run Flow

### 11.1 完整流程

```text
GitHub issue fixture (requests/github-fixtures/*.json)
  ↓
parse JSON → GitHubIssueRequest
  ↓
validate GitHubIssueRequest (repository, author, state)
  ↓
map GitHubIssueRequest → ExternalRequest (Section 6 mapping)
  ↓
run ExternalRequestSafetyGate (17 existing rules + 3 Issue-specific rules)
  ↓
if blocked: write rejected dry-run report → stop
  ↓ (safety gate 通过)
build TaskProposal dry-run
  ↓
write github issue report (reports/github-issues/)
  ↓
wait for user approval
  ↓
no docs/tasks.md update
no runner execution
no Git
```

### 11.2 关键约束

1. **不直接写 docs/tasks.md**：proposal 生成后必须经过人工确认。
2. **不直接执行 runner**：GitHub Issue 流程中不调用 runner.py。
3. **不直接调用 Developer Agent**：Issue 不能直接触发代码生成。
4. **不直接调用 Git Backup Agent**：Issue 不能直接触发 Git 操作。
5. **不创建 GitHub comment**：不会在 Issue 上评论。
6. **不关闭 Issue**：不会改变 Issue 状态。
7. **不添加 Label**：不会修改 Issue labels。
8. **dry-run 始终为 True**：Stage 11 所有 GitHub Issue 处理均为 dry-run。
9. **allowed_to_execute 始终为 False**：Stage 11 不允许 Issue 触发执行。

### 11.3 失败处理

| 失败场景 | 处理 |
|----------|------|
| fixture 文件不存在 | fail closed，写 rejected report |
| fixture JSON 解析失败 | fail closed，写 rejected report |
| 缺少必要字段 | fail closed，写 rejected report |
| repository 不匹配 | fail closed，写 rejected report |
| safety gate 阻断 | fail closed，写 rejected report |
| proposal 生成失败 | fail closed，写 rejected report |
| 报告写入失败 | 记录错误，不继续 |

---

## 12. Report Format

### 12.1 报告路径

`reports/github-issues/GH-ISSUE-{repo}-{number}-report.md`

### 12.2 报告字段

```text
ISSUE_ID=123456
ISSUE_NUMBER=42
REPOSITORY=owner/repo
SOURCE_TYPE=github_issue
SOURCE_MODE=local_fixture
PARSE_STATUS=pass/fail
SAFETY_STATUS=pass/fail
PROMPT_INJECTION_RISK=low/medium/high/critical
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

### 12.3 报告章节

| 章节 | 内容 |
|------|------|
| 1. Issue Info | issue_id, issue_number, repository, title, author, labels, state, url |
| 2. Safety Gate Result | safety_status, risk_level, prompt_injection_risk, blocked_reasons, warnings |
| 3. Task Proposal | proposal_id, title, proposed_tasks, proposed_files, required_agents, risk_level |
| 4. Safety Guarantees | DOCS_TASKS_MODIFIED=no, RUNNER_EXECUTED=no, GIT_*=no |
| 5. Author Trust | author, author_association, trusted_author |
| 6. Labels Audit | 所有 labels 及其处理方式 |

### 12.4 报告说明

1. 每个 GitHub Issue fixture 处理后生成一份报告。
2. 报告包含完整的处理链路状态。
3. DOCS_TASKS_MODIFIED 始终为 no。
4. RUNNER_EXECUTED 始终为 no。
5. GIT_ADD/COMMIT/PUSH 始终为 no。
6. ALLOWED_TO_EXECUTE 始终为 no。
7. 报告写入 reports/github-issues/ 目录。

---

## 13. T190 Implementation Scope

T190 应只实现 dry-run：

1. 创建 `tools/github_issue_entry.py`。
2. 使用 Python 标准库（dataclass、re、json、pathlib、datetime）。
3. 读取本地 GitHub Issue fixture JSON 文件（`requests/github-fixtures/*.json`）。
4. 不访问 GitHub API。
5. 不调用 `gh` CLI。
6. 不创建 workflow。
7. 解析 issue title / body / labels / author。
8. 构建 GitHubIssueRequest。
9. 转换为 ExternalRequest（Section 6 映射规则）。
10. 复用或对齐 external_request_inbox safety gate 逻辑。
11. 构建 TaskProposal dry-run。
12. 写 `reports/github-issues/` 报告。
13. 不修改 docs/tasks.md。
14. 不执行 runner。
15. 不执行 Git。
16. 不调用模型。
17. fail closed。

### 13.1 T190 不做的事情

1. 不读取 comments（max_comments=0）。
2. 不创建 GitHub Actions workflow。
3. 不创建 Web UI。
4. 不创建 API。
5. 不创建 n8n workflow。
6. 不修改 runner.py。
7. 不修改 tools/external_request_inbox.py。
8. 不修改 tools/ 下其他文件。
9. 不修改 agents/。
10. 不执行 git add/commit/push。
11. 不调用 Claude Agent SDK。
12. 不访问网络。
13. 不调用 GitHub API。

### 13.2 T190 需要的 fixture 目录

```
requests/
  github-fixtures/
    issue-001-safe.json        # 正常 feature 请求
    issue-002-bug-report.json  # Bug 报告
    ...（测试 fixture）
```

### 13.3 T190 CLI 入口

```bash
python tools/github_issue_entry.py \
  --fixture-file requests/github-fixtures/issue-001-safe.json \
  --output-dir reports/github-issues
```

### 13.4 T190 与 external_request_inbox.py 的关系

| 关系 | 说明 |
|------|------|
| 复用数据结构 | ExternalRequest, ExternalRequestSafetyResult, TaskProposal |
| 复用 safety gate | 17 条规则直接复用或对齐 |
| 复用 prompt injection detection | 检测规则直接复用 |
| 新增数据结构 | GitHubIssueRequest |
| 新增映射逻辑 | IssueToExternalRequest |
| 独立 CLI | 独立的 CLI 入口，不修改 external_request_inbox.py |
| 独立报告目录 | reports/github-issues/ |

---

## 14. Acceptance Criteria

T189 完成标准：

1. docs/stage11-github-issue-entry-design.md 已创建。
2. GitHubIssueRequest 已设计（20 字段）。
3. IssueToExternalRequest mapping 已设计（18 字段映射）。
4. GitHub Issue safety rules 已设计（20 条规则）。
5. Prompt injection defense 已设计（11 条原则 + 7 种特有风险）。
6. Labels and metadata handling 已设计（10 条 label 规则 + 敏感 label 处理）。
7. Comments handling 已设计（6 条规则 + 读取限制）。
8. Issue to proposal dry-run flow 已设计（完整流程 + 失败处理）。
9. Report format 已设计（reports/github-issues/）。
10. T190 implementation scope 已明确（17 项实现 + 13 项不实现）。
11. 未创建 tools/github_issue_entry.py。
12. 未创建 .github/workflows。
13. 未访问 GitHub API。
14. 未修改 runner.py。
15. 未修改 tools/。
16. NEXT_PENDING=T190。
17. NEXT_STAGE=Stage 11。

---

```text
TASK=T189
DESIGN_STATUS=done
GITHUB_ISSUE_ENTRY_DESIGNED=yes
GITHUB_ISSUE_REQUEST_DESIGNED=yes
ISSUE_TO_EXTERNAL_REQUEST_MAPPING_DESIGNED=yes
GITHUB_ISSUE_SAFETY_RULES_DESIGNED=yes
PROMPT_INJECTION_DEFENSE_DESIGNED=yes
LABELS_METADATA_HANDLING_DESIGNED=yes
COMMENTS_HANDLING_DESIGNED=yes
REPORT_FORMAT_DESIGNED=yes
T190_SCOPE_DEFINED=yes
GITHUB_ISSUE_ENTRY_IMPLEMENTED=no
GITHUB_API_ACCESSED=no
GITHUB_WORKFLOW_CREATED=no
EXTERNAL_EXECUTION_ENABLED=no
NEXT_PENDING=T190
NEXT_STAGE=Stage 11
```
