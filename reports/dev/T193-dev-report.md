# T193 Dev Report：验证外部请求生成任务草案但不执行

任务编号：T193
完成时间：2026-05-13
角色：Test Agent + Stage 11 External Request Task Proposal Non-execution Validator
目标：验证外部请求可以生成任务草案，但绝不能执行。

---

## 1. 验证概述

本任务验证 tools/external_request_task_proposal.py 的统一 proposal bridge，确认外部请求可以生成 TaskProposal dry-run，但绝不执行真实操作。验证 4 个场景：local inbox safe/blocked、GitHub issue safe/blocked。

---

## 2. 验证结果总表

| # | 场景 | 结果 | 状态 |
|---|------|------|------|
| 1 | Local inbox safe proposal | pass: SAFETY=pass, PLAN=yes, EXECUTE=no, PROPOSAL=yes | pass |
| 2 | Local inbox blocked fail closed | fail: RISK=critical, blocked=secrets+git+injection | pass |
| 3 | GitHub issue safe proposal | pass: SAFETY=pass, PLAN=yes, EXECUTE=no, PROPOSAL=yes | pass |
| 4 | GitHub issue blocked fail closed | fail: RISK=critical, blocked=secrets+bypass+git+real_exec+injection | pass |

---

## 3. Local Inbox 验证结果

### 3.1 Safe Request (REQ-T187-safe-sample.md)

- EXTERNAL_REQUEST_TASK_PROPOSAL_RESULT=pass
- SAFETY_STATUS=pass
- PROMPT_INJECTION_RISK=low
- ALLOWED_TO_PLAN=yes
- ALLOWED_TO_EXECUTE=no
- TASK_PROPOSAL_CREATED=yes
- PROPOSAL_NEXT_ACTION=wait_for_approval
- DOCS_TASKS_MODIFIED=no
- RUNNER_EXECUTED=no
- GIT_ADD/COMMIT/PUSH_EXECUTED=no

### 3.2 Blocked Request (REQ-T187-blocked-sample.md)

- EXTERNAL_REQUEST_TASK_PROPOSAL_RESULT=fail
- SAFETY_STATUS=fail
- PROMPT_INJECTION_RISK=critical
- ALLOWED_TO_PLAN=no
- ALLOWED_TO_EXECUTE=no
- TASK_PROPOSAL_CREATED=no
- BLOCKED_REASONS: secrets(.env), git operations(git push/add/commit), prompt injection (critical: ignore_previous, high: secrets/git)

---

## 4. GitHub Issue 验证结果

### 4.1 Safe Fixture (ISSUE-T190-safe.md)

- EXTERNAL_REQUEST_TASK_PROPOSAL_RESULT=pass
- SAFETY_STATUS=pass
- PROMPT_INJECTION_RISK=low
- ALLOWED_TO_PLAN=yes
- ALLOWED_TO_EXECUTE=no
- TASK_PROPOSAL_CREATED=yes
- PROPOSAL_NEXT_ACTION=wait_for_approval
- DOCS_TASKS_MODIFIED=no
- RUNNER_EXECUTED=no
- GIT_ADD/COMMIT/PUSH_EXECUTED=no
- GITHUB_API_ACCESSED=no
- GH_CLI_CALLED=no
- GITHUB_WORKFLOW_CREATED=no

### 4.2 Blocked Fixture (ISSUE-T190-blocked.md)

- EXTERNAL_REQUEST_TASK_PROPOSAL_RESULT=fail
- SAFETY_STATUS=fail
- PROMPT_INJECTION_RISK=critical
- ALLOWED_TO_PLAN=no
- ALLOWED_TO_EXECUTE=no
- TASK_PROPOSAL_CREATED=no
- BLOCKED_REASONS: secrets(.env), bypass safety, git push/add, real execution(run-project-loop), prompt injection (critical+high)
- GITHUB_API_ACCESSED=no
- GH_CLI_CALLED=no
- GITHUB_WORKFLOW_CREATED=no

---

## 5. reports/task-proposals/ 生成的报告

T193 生成的 4 个报告：

1. PROPOSAL-local_inbox-REQ-T187-SAFE-SAMPLE-20260513204208-report.md
2. PROPOSAL-local_inbox-REQ-T187-BLOCKED-SAMPLE-20260513204214-report.md
3. PROPOSAL-github_issue-GH-ISSUE-yyd841122-multi-agent-runner-190-20260513204227-report.md
4. PROPOSAL-github_issue-GH-ISSUE-yyd841122-multi-agent-runner-191-20260513204234-report.md

---

## 6. docs/tasks.md 污染检查

- git diff -- docs/tasks.md 无差异
- 无来自外部请求的真实任务被写入 docs/tasks.md
- 外部请求内容不会污染任务列表

---

## 7. 未修改说明

1. 本任务只验证，不修改工具。
2. 未修改 runner.py。
3. 未修改 tools/external_request_task_proposal.py。
4. 未修改 tools/external_request_inbox.py。
5. 未修改 tools/github_issue_entry.py。
6. 未修改其他 tools。
7. 未修改 agents。
8. 未修改业务代码。
9. 未访问 GitHub API。
10. 未调用 gh CLI。
11. 未创建 workflow。
12. 未启用外部真实执行。
13. 未执行 runner。
14. 未执行 Git。
15. 未把 proposal 转成真实任务。

---

## 文件变更

| 文件 | 操作 | 说明 |
|------|------|------|
| reports/checks/T193-external-request-task-proposal-non-execution-validation.md | 新建 | T193 验证报告 |
| reports/dev/T193-dev-report.md | 新建 | T193 dev report |
| reports/task-proposals/PROPOSAL-*-20260513204208-report.md | 新建 | T193 dry-run 报告 |
| reports/task-proposals/PROPOSAL-*-20260513204214-report.md | 新建 | T193 dry-run 报告 |
| reports/task-proposals/PROPOSAL-*-20260513204227-report.md | 新建 | T193 dry-run 报告 |
| reports/task-proposals/PROPOSAL-*-20260513204234-report.md | 新建 | T193 dry-run 报告 |
| docs/tasks.md | 修改 | T193 标记为 done，NEXT_PENDING 指向 T194 |

---

```text
TASK=T193
VALIDATION_STATUS=done
FILES_CREATED=reports/checks/T193-external-request-task-proposal-non-execution-validation.md, reports/dev/T193-dev-report.md
FILES_MODIFIED=docs/tasks.md
BUSINESS_CODE_CHANGED=no
FRAMEWORK_CODE_CHANGED=no
RUNNER_CHANGED=no
TOOLS_CHANGED=no
AGENTS_CHANGED=no
REAL_EXECUTION_CHANGED=no
CLAUDE_AGENT_SDK_INTEGRATED=no
LOCAL_INBOX_SAFE_PROPOSAL_CREATED=pass
LOCAL_INBOX_BLOCKED_FAIL_CLOSED=pass
GITHUB_ISSUE_SAFE_PROPOSAL_CREATED=pass
GITHUB_ISSUE_BLOCKED_FAIL_CLOSED=pass
TASK_PROPOSAL_DRY_RUN_ONLY=pass
DOCS_TASKS_NOT_MODIFIED_BY_EXTERNAL_REQUEST=pass
RUNNER_NOT_EXECUTED=pass
REAL_TASK_NOT_EXECUTED=pass
REAL_REWORK_NOT_EXECUTED=pass
REAL_GIT_BACKUP_NOT_EXECUTED=pass
GITHUB_API_NOT_ACCESSED=pass
GH_CLI_NOT_CALLED=pass
GITHUB_WORKFLOW_NOT_CREATED=pass
ALLOWED_TO_EXECUTE_ALWAYS_NO=pass
USER_APPROVAL_REQUIRED=pass
EXTERNAL_EXECUTION_ENABLED=no
GIT_COMMANDS_EXECUTED=no
CHECK_RESULT=pass
NEXT_PENDING=T194
NEXT_STAGE=Stage 11
```
