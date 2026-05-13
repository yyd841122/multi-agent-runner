# T192 Dev Report：接入 external request → task proposal dry-run

任务编号：T192
完成时间：2026-05-13
角色：Dev Agent + Stage 11 External Request to Task Proposal Dry-run Integrator
目标：建立统一的 task proposal 生成桥接层。

---

## 1. 实现概述

本任务创建 tools/external_request_task_proposal.py，作为统一 proposal bridge，将 local_inbox 和 github_issue 两类外部请求统一经过 safety gate 后生成 TaskProposal dry-run。

---

## 2. external_request_task_proposal.py 主要功能

1. **UnifiedTaskProposalResult dataclass**：20 字段，统一记录 dry-run 结果。
2. **process_local_inbox**：调用 external_request_inbox.py 的 parse_markdown_request → run_safety_gate → build_task_proposal。
3. **process_github_issue**：调用 github_issue_entry.py 的 parse_github_issue_fixture → validate_github_issue → github_issue_to_external_request → run_safety_gate → build_task_proposal。
4. **build_unified_report**：生成 reports/task-proposals/ 统一报告，包含 Safety Gate Result、Task Proposal、Safety Guarantees 三个章节。
5. **print_unified_summary**：输出结构化状态行。
6. **main() CLI**：支持 --source-type、--request-file、--fixture-file、--output-dir、--dry-run、--print-proposal。

---

## 3. 复用策略

- 从 external_request_inbox.py 导入：parse_markdown_request、run_safety_gate、build_task_proposal、ExternalRequest、ExternalRequestSafetyResult、TaskProposal。
- 从 github_issue_entry.py 导入：parse_github_issue_fixture、validate_github_issue、github_issue_to_external_request、run_safety_gate、build_task_proposal、GitHubIssueRequest。
- 使用保守兼容导入方式（try/except 包导入和直接导入）。
- 不复制代码，不修改原工具。

---

## 4. Local Inbox 验证结果

### Safe Request (REQ-T187-safe-sample.md)

- EXTERNAL_REQUEST_TASK_PROPOSAL_RESULT=pass
- SAFETY_STATUS=pass
- PROMPT_INJECTION_RISK=low
- ALLOWED_TO_PLAN=yes
- ALLOWED_TO_EXECUTE=no
- TASK_PROPOSAL_CREATED=yes
- DOCS_TASKS_MODIFIED=no
- RUNNER_EXECUTED=no
- GIT_ADD/COMMIT/PUSH_EXECUTED=no

### Blocked Request (REQ-T187-blocked-sample.md)

- EXTERNAL_REQUEST_TASK_PROPOSAL_RESULT=fail
- SAFETY_STATUS=fail
- PROMPT_INJECTION_RISK=critical
- ALLOWED_TO_PLAN=no
- ALLOWED_TO_EXECUTE=no
- TASK_PROPOSAL_CREATED=no
- BLOCKED_REASONS: secrets(.env), git operations, prompt injection (critical)

---

## 5. GitHub Issue 验证结果

### Safe Fixture (ISSUE-T190-safe.md)

- EXTERNAL_REQUEST_TASK_PROPOSAL_RESULT=pass
- SAFETY_STATUS=pass
- PROMPT_INJECTION_RISK=low
- ALLOWED_TO_PLAN=yes
- ALLOWED_TO_EXECUTE=no
- TASK_PROPOSAL_CREATED=yes
- DOCS_TASKS_MODIFIED=no
- RUNNER_EXECUTED=no
- GITHUB_API_ACCESSED=no
- GH_CLI_CALLED=no
- GITHUB_WORKFLOW_CREATED=no

### Blocked Fixture (ISSUE-T190-blocked.md)

- EXTERNAL_REQUEST_TASK_PROPOSAL_RESULT=fail
- SAFETY_STATUS=fail
- PROMPT_INJECTION_RISK=critical
- ALLOWED_TO_PLAN=no
- ALLOWED_TO_EXECUTE=no
- TASK_PROPOSAL_CREATED=no
- BLOCKED_REASONS: secrets(.env), bypass safety, git push/add, real execution, prompt injection (critical+high)
- GITHUB_API_ACCESSED=no
- GH_CLI_CALLED=no
- GITHUB_WORKFLOW_CREATED=no

---

## 6. 生成的 reports/task-proposals/ 报告

1. PROPOSAL-local_inbox-REQ-T187-SAFE-SAMPLE-*-report.md
2. PROPOSAL-local_inbox-REQ-T187-BLOCKED-SAMPLE-*-report.md
3. PROPOSAL-github_issue-GH-ISSUE-yyd841122-multi-agent-runner-190-*-report.md
4. PROPOSAL-github_issue-GH-ISSUE-yyd841122-multi-agent-runner-191-*-report.md

---

## 7. 未修改说明

1. 未修改 runner.py。
2. 未修改 external_request_inbox.py。
3. 未修改 github_issue_entry.py。
4. 未修改其他 tools。
5. 未修改 agents。
6. 未修改业务代码。
7. 未启用外部真实执行。
8. 未执行 Git。
9. 未访问 GitHub API。
10. 未调用 gh CLI。
11. 未创建 workflow。
12. 未把 request / issue 转成真实 docs/tasks.md 任务。

---

## 文件变更

| 文件 | 操作 | 说明 |
|------|------|------|
| tools/external_request_task_proposal.py | 新建 | 统一 proposal bridge |
| reports/task-proposals/*-report.md | 新建 | 4 个 dry-run 报告 |
| reports/dev/T192-dev-report.md | 新建 | T192 dev report |
| docs/tasks.md | 修改 | T192 标记为 done，NEXT_PENDING 指向 T193 |

---

```text
TASK=T192
IMPLEMENTATION_STATUS=done
FILES_CREATED=tools/external_request_task_proposal.py, reports/dev/T192-dev-report.md
FILES_MODIFIED=docs/tasks.md
BUSINESS_CODE_CHANGED=no
FRAMEWORK_CODE_CHANGED=yes
RUNNER_CHANGED=no
TOOLS_CHANGED=yes
AGENTS_CHANGED=no
REAL_EXECUTION_CHANGED=no
CLAUDE_AGENT_SDK_INTEGRATED=no
EXTERNAL_REQUEST_TASK_PROPOSAL_BRIDGE_IMPLEMENTED=yes
LOCAL_INBOX_TO_TASK_PROPOSAL_DRY_RUN=pass
LOCAL_INBOX_BLOCKED_FAIL_CLOSED=pass
GITHUB_ISSUE_TO_TASK_PROPOSAL_DRY_RUN=pass
GITHUB_ISSUE_BLOCKED_FAIL_CLOSED=pass
DOCS_TASKS_MODIFIED_BY_EXTERNAL_REQUEST=no
RUNNER_EXECUTED=no
GITHUB_API_ACCESSED=no
GH_CLI_CALLED=no
GITHUB_WORKFLOW_CREATED=no
EXTERNAL_EXECUTION_ENABLED=no
GIT_COMMANDS_EXECUTED=no
PY_COMPILE_STATUS=pass
CHECK_RESULT=pass
NEXT_PENDING=T193
NEXT_STAGE=Stage 11
```
