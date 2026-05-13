# T189 Dev Report：设计 GitHub Issue 外部入口 dry-run

任务编号：T189
完成时间：2026-05-13
角色：Architect Agent + Stage 11 GitHub Issue External Entry Design Architect
目标：设计 GitHub Issue → ExternalRequest 的转换流程。

---

## 1. 设计概述

本任务设计 GitHub Issue 外部入口 dry-run，只设计不实现。

---

## 2. 设计成果

### 2.1 GitHubIssueRequest 数据结构

设计了 20 字段的 GitHubIssueRequest dataclass：

- issue_id, issue_number, repository
- title, body（不可信）
- author, author_association（不可信）
- labels, assignees, milestone, state（不可信）
- created_at, updated_at, issue_url
- source_mode, raw_payload_path
- comments_included, comments（不可信）
- trusted_author, fail_reason

### 2.2 IssueToExternalRequest 映射

设计了 18 字段的映射规则：

- request_id = GH-ISSUE-{repository}-{issue_number}
- source_type = github_issue
- raw_content = title + body + selected comments
- requester = issue author
- priority 由 labels 推断，默认 normal
- allowed_to_execute 固定 false
- requires_user_approval 默认 true

### 2.3 GitHub Issue Safety Rules

设计了 20 条安全门规则（在 local inbox 17 条基础上增加 3 条 Issue 专用规则）：

- 空 issue fail closed
- 缺失 title/body fail closed 或 marked incomplete
- 来源不明 fail closed
- 未知 repository fail closed
- issue author 默认不可信
- external contributor 默认高风险
- 密钥泄露 fail closed
- .env 读取 fail closed
- 绕过系统限制 fail closed
- Git 操作 fail closed
- 真实执行 fail closed
- 真实返工 fail closed
- 框架文件修改 user approval
- 删除文件 user approval 或 blocked
- 网络调用 user approval
- labels 不可信
- allowed_to_execute 永远 false
- allowed_to_plan 条件通过
- comments 需 safety gate 检查
- 所有不确定情况 fail closed

### 2.4 Prompt Injection 防护

设计了 11 条防护原则和 7 种 GitHub Issue 特有风险：

- Issue 标题注入
- Issue 正文注入
- Comment 注入
- Label 欺骗
- Author 欺骗
- Milestone 欺骗
- 复合攻击

### 2.5 Labels 处理规则

设计了 10 条 label 处理规则：

- labels 只能作为 hints
- label=urgent 不得绕过安全门
- label=auto-run 不得触发真实执行
- label=approved 也不得自动执行
- label=safe 不得降低风险
- label=security 必须提升审查等级

### 2.6 Comments 处理规则

设计了 6 条 comments 处理规则：

- T190 默认不读取 comments
- 后续读取时限制数量和长度
- comments 不能作为执行指令
- maintainer comment 也不直接触发执行
- /run /execute /push 必须 fail closed

### 2.7 Dry-run 流程

设计了完整流程：

GitHub issue fixture → parse GitHubIssueRequest → map to ExternalRequest → run safety gate → if blocked: rejected report → if allowed: TaskProposal → github issue report → wait for approval → no tasks.md update → no runner → no Git

### 2.8 报告格式

设计了 reports/github-issues/ 报告格式，包含 ISSUE_ID, ISSUE_NUMBER, REPOSITORY, SOURCE_TYPE, SAFETY_STATUS, PROMPT_INJECTION_RISK, ALLOWED_TO_PLAN, ALLOWED_TO_EXECUTE 等 15 个字段。

### 2.9 T190 实现范围

明确了 T190 只实现 dry-run：

- 17 项实现（创建 github_issue_entry.py，读取本地 fixture，解析 JSON，构建 GitHubIssueRequest，转换为 ExternalRequest，复用 safety gate，构建 TaskProposal，写报告等）
- 13 项不实现（不访问 GitHub API，不创建 workflow，不读取 comments，不修改 runner.py 等）

---

## 3. 未创建 tools/github_issue_entry.py

本任务未创建 tools/github_issue_entry.py，仅设计数据结构和流程。

## 4. 未创建 .github/workflows

本任务未创建任何 GitHub Actions workflow 文件。

## 5. 未访问 GitHub API

本任务未访问 GitHub API，未调用 gh CLI。

## 6. 未修改 runner.py

本任务未修改 runner.py。

## 7. 未修改 tools

本任务未修改 tools/ 目录下任何文件。

## 8. 未修改 agents

本任务未修改 agents/ 目录下任何文件。

## 9. 未修改业务代码

本任务未修改任何业务代码。

## 10. 未启用外部真实执行

本任务未启用任何外部真实执行。

## 11. 未执行 Git

本任务未执行 git add/commit/push。

---

## 文件变更

| 文件 | 操作 | 说明 |
|------|------|------|
| docs/stage11-github-issue-entry-design.md | 新建 | GitHub Issue 外部入口设计文档 |
| reports/dev/T189-dev-report.md | 新建 | T189 dev report |
| docs/tasks.md | 修改 | T189 标记为 done，NEXT_PENDING 指向 T190 |

---

```text
TASK=T189
DESIGN_STATUS=done
FILES_CREATED=docs/stage11-github-issue-entry-design.md, reports/dev/T189-dev-report.md
FILES_MODIFIED=docs/tasks.md
BUSINESS_CODE_CHANGED=no
FRAMEWORK_CODE_CHANGED=no
RUNNER_CHANGED=no
TOOLS_CHANGED=no
AGENTS_CHANGED=no
REAL_EXECUTION_CHANGED=no
CLAUDE_AGENT_SDK_INTEGRATED=no
GITHUB_ISSUE_ENTRY_DESIGNED=yes
GITHUB_ISSUE_REQUEST_DESIGNED=yes
ISSUE_TO_EXTERNAL_REQUEST_MAPPING_DESIGNED=yes
GITHUB_ISSUE_SAFETY_RULES_DESIGNED=yes
PROMPT_INJECTION_DEFENSE_DESIGNED=yes
LABELS_METADATA_HANDLING_DESIGNED=yes
COMMENTS_HANDLING_DESIGNED=yes
GITHUB_ISSUE_ENTRY_IMPLEMENTED=no
GITHUB_API_ACCESSED=no
GITHUB_WORKFLOW_CREATED=no
EXTERNAL_EXECUTION_ENABLED=no
GIT_COMMANDS_EXECUTED=no
CHECK_RESULT=pass
NEXT_PENDING=T190
NEXT_STAGE=Stage 11
```
