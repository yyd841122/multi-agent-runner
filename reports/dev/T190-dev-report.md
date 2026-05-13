# T190 Dev Report：实现 GitHub Issue 读取与 proposal dry-run

任务编号：T190
完成时间：2026-05-13
角色：Dev Agent + Stage 11 GitHub Issue Entry Dry-run Implementer
目标：实现 GitHub Issue 读取、内容解析、proposal 生成 dry-run。

---

## 1. 实现概述

本任务创建 tools/github_issue_entry.py，实现本地 GitHub Issue fixture dry-run。

---

## 2. github_issue_entry.py 主要功能

1. **GitHubIssueRequest dataclass**：20 字段，记录 issue_id, issue_number, repository, title, body, author, author_association, labels, assignees, milestone, state, created_at, updated_at, issue_url, source_mode, raw_payload_path, comments_included, comments, trusted_author, fail_reason。
2. **parse_github_issue_fixture**：解析 Markdown frontmatter 格式的 fixture 文件，也支持 JSON 格式。
3. **github_issue_to_external_request**：将 GitHubIssueRequest 映射为 ExternalRequest，request_id 格式为 GH-ISSUE-{repo}-{number}。
4. **validate_github_issue**：GitHub Issue 专用预检查（空 issue、缺失 issue_number、缺失 repository、closed issue）。
5. **detect_prompt_injection**：对齐 external_request_inbox.py 的 prompt injection 检测逻辑。
6. **run_safety_gate**：对齐 external_request_inbox.py 的 17 条 safety gate 规则。
7. **build_task_proposal**：生成 TaskProposal dry-run。
8. **build_github_issue_report**：生成 reports/github-issues/ 报告，包含 Issue Info、Safety Gate Result、Task Proposal、Safety Guarantees、Author Trust、Labels Audit 6 个章节。

---

## 3. 复用策略

github_issue_entry.py 中的 ExternalRequest、ExternalRequestSafetyResult、TaskProposal dataclass 和 safety gate / prompt injection 检测逻辑与 external_request_inbox.py **对齐但独立实现**，而非直接 import。原因：github_issue_entry.py 作为独立工具，不依赖 external_request_inbox.py 的内部实现，便于后续独立演进。两边的安全规则和检测逻辑保持一致。

---

## 4. GitHub Issue Fixture 格式

使用 Markdown frontmatter 格式：

- YAML front matter 包含 issue 元数据（issue_id, issue_number, repository, author, labels 等）
- 正文为 issue body
- title 从 `# heading` 或 front matter 提取

---

## 5. Safe Fixture 验证结果

fixtures/github-issues/ISSUE-T190-safe.md：

- GITHUB_ISSUE_ENTRY_RESULT=pass
- SAFETY_STATUS=pass
- PROMPT_INJECTION_RISK=low
- ALLOWED_TO_PLAN=yes
- ALLOWED_TO_EXECUTE=no
- TASK_PROPOSAL_CREATED=yes
- CHECK_RESULT=pass

生成报告：reports/github-issues/GH-ISSUE-yyd841122-multi-agent-runner-190-report.md

---

## 6. Blocked Fixture 验证结果

fixtures/github-issues/ISSUE-T190-blocked.md：

- GITHUB_ISSUE_ENTRY_RESULT=fail
- SAFETY_STATUS=fail
- PROMPT_INJECTION_RISK=critical
- ALLOWED_TO_PLAN=no
- ALLOWED_TO_EXECUTE=no
- TASK_PROPOSAL_CREATED=no
- BLOCKED_REASONS 包含：secrets_disclosure_requested:.env, read_env_requested, bypass_safety, git_operation_requested:git push, git_operation_requested:git add ., real_execution_requested, prompt_injection (critical: ignore_previous_instructions, reveal_system_prompt; high: secrets, git, real execution; medium: framework_file)
- CHECK_RESULT=fail

生成报告：reports/github-issues/GH-ISSUE-yyd841122-multi-agent-runner-191-report.md

---

## 7. 生成的 reports/github-issues/ 报告

1. GH-ISSUE-yyd841122-multi-agent-runner-190-report.md（safe issue）
2. GH-ISSUE-yyd841122-multi-agent-runner-191-report.md（blocked issue）

---

## 8. 未访问 GitHub API

本任务未访问 GitHub API。

## 9. 未调用 gh CLI

本任务未调用 gh CLI。

## 10. 未创建 workflow

本任务未创建 .github/workflows。

## 11. 未修改 runner.py

本任务未修改 runner.py。

## 12. 未修改其他 tools

本任务未修改 tools/external_request_inbox.py 和其他 tools。

## 13. 未修改 agents

本任务未修改 agents/ 目录下任何文件。

## 14. 未修改业务代码

本任务未修改任何业务代码。

## 15. 未启用外部真实执行

本任务未启用任何外部真实执行。

## 16. 未执行 Git

本任务未执行 git add/commit/push。

## 17. 未把 issue 转成真实任务

所有 fixture 仅用于 dry-run 验证，未转成 docs/tasks.md 中的真实任务。

---

## 文件变更

| 文件 | 操作 | 说明 |
|------|------|------|
| tools/github_issue_entry.py | 新建 | GitHub Issue entry dry-run 实现 |
| fixtures/github-issues/ISSUE-T190-safe.md | 新建 | Safe issue fixture |
| fixtures/github-issues/ISSUE-T190-blocked.md | 新建 | Blocked issue fixture |
| reports/github-issues/GH-ISSUE-yyd841122-multi-agent-runner-190-report.md | 新建 | Safe issue dry-run 报告 |
| reports/github-issues/GH-ISSUE-yyd841122-multi-agent-runner-191-report.md | 新建 | Blocked issue dry-run 报告 |
| reports/dev/T190-dev-report.md | 新建 | T190 dev report |
| docs/tasks.md | 修改 | T190 标记为 done，NEXT_PENDING 指向 T191 |

---

```text
TASK=T190
IMPLEMENTATION_STATUS=done
FILES_CREATED=tools/github_issue_entry.py, fixtures/github-issues/ISSUE-T190-safe.md, fixtures/github-issues/ISSUE-T190-blocked.md, reports/dev/T190-dev-report.md
FILES_MODIFIED=docs/tasks.md
BUSINESS_CODE_CHANGED=no
FRAMEWORK_CODE_CHANGED=yes
RUNNER_CHANGED=no
TOOLS_CHANGED=yes
AGENTS_CHANGED=no
REAL_EXECUTION_CHANGED=no
CLAUDE_AGENT_SDK_INTEGRATED=no
GITHUB_ISSUE_ENTRY_IMPLEMENTED=yes
LOCAL_FIXTURE_MODE_IMPLEMENTED=yes
GITHUB_ISSUE_REQUEST_IMPLEMENTED=yes
ISSUE_TO_EXTERNAL_REQUEST_MAPPING_IMPLEMENTED=yes
TASK_PROPOSAL_DRY_RUN_IMPLEMENTED=yes
PROMPT_INJECTION_DETECTION_REUSED_OR_ALIGNED=yes
SAFE_ISSUE_DRY_RUN=pass
BLOCKED_ISSUE_DRY_RUN=pass
DOCS_TASKS_MODIFIED_BY_ISSUE=no
RUNNER_EXECUTED=no
GITHUB_API_ACCESSED=no
GITHUB_WORKFLOW_CREATED=no
EXTERNAL_EXECUTION_ENABLED=no
GIT_COMMANDS_EXECUTED=no
PY_COMPILE_STATUS=pass
CHECK_RESULT=pass
NEXT_PENDING=T191
NEXT_STAGE=Stage 11
```
