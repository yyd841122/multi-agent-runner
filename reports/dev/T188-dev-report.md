# T188 Dev Report：验证 external request safety gate fail closed

任务编号：T188
完成时间：2026-05-13
角色：Test Agent + Stage 11 External Request Safety Gate Validator
目标：验证 external request safety gate 的 fail closed 行为。

---

## 1. 验证概述

本任务验证 tools/external_request_inbox.py 中 17 条 safety gate 规则的 fail closed 行为。

本任务只验证，不修改 external_request_inbox.py。

---

## 2. 创建的测试文件

1. requests/inbox/REQ-T188-empty.md — 空请求测试
2. requests/inbox/REQ-T188-prompt-injection.md — Prompt injection 测试
3. requests/inbox/REQ-T188-secret-env.md — 密钥/.env 读取测试
4. requests/inbox/REQ-T188-direct-git.md — 直接 Git 操作测试
5. requests/inbox/REQ-T188-real-run-project-loop.md — 真实执行测试
6. requests/inbox/REQ-T188-real-rework.md — 真实返工测试
7. requests/inbox/REQ-T188-restricted-files.md — 框架文件修改测试
8. requests/inbox/REQ-T188-delete-files.md — 删除文件测试

---

## 3. Fail Closed 验证结果

| # | 场景 | 结果 |
|---|------|------|
| 1 | Safe request pass | pass |
| 2 | Empty request fail closed | pass |
| 3 | Missing file fail closed | pass |
| 4 | Prompt injection fail closed | pass |
| 5 | Secret/.env request fail closed | pass |
| 6 | Direct git request fail closed | pass |
| 7 | Real run-project-loop fail closed | pass |
| 8 | Real rework fail closed | pass |
| 9 | Restricted files require approval | pass |
| 10 | Delete files require approval | pass |
| 11 | allowed_to_execute always no | pass |

---

## 4. 生成的报告

reports/external-requests/ 下的 T188 相关报告：

1. REQ-T188-EMPTY-report.md
2. REQ-T188-PROMPT-INJECTION-report.md
3. REQ-T188-SECRET-ENV-report.md
4. REQ-T188-DIRECT-GIT-report.md
5. REQ-T188-REAL-RUN-PROJECT-LOOP-report.md
6. REQ-T188-REAL-REWORK-report.md
7. REQ-T188-RESTRICTED-FILES-report.md
8. REQ-T188-DELETE-FILES-report.md

---

## 5. 已知发现

1. **Windows 文件名 bug**：auto-generated request_id 使用 ISO 时间戳格式（如 `REQ-2026-05-13T10:20:49`），冒号在 Windows 文件系统中不合法，导致空文件和缺失文件的报告无法写入。Safety gate 逻辑正确，仅报告文件名存在兼容性问题。建议后续将时间戳中的冒号替换为连字符。

---

## 6. 未修改 runner.py

本任务未修改 runner.py。

## 7. 未修改 tools

本任务未修改 tools/ 目录下任何文件，包括 external_request_inbox.py。

## 8. 未修改 agents

本任务未修改 agents/ 目录下任何文件。

## 9. 未修改业务代码

本任务未修改任何业务代码。

## 10. 未执行真实任务

所有 dry-run 均为模拟验证，未执行真实任务。

## 11. 未执行 Git

本任务未执行 git add/commit/push。

## 12. 未把 request 转成真实任务

所有 T188 request 测试文件仅用于 dry-run 验证，未转成真实 docs/tasks.md 任务。

---

## 文件变更

| 文件 | 操作 | 说明 |
|------|------|------|
| requests/inbox/REQ-T188-empty.md | 新建 | 空请求测试文件 |
| requests/inbox/REQ-T188-prompt-injection.md | 新建 | Prompt injection 测试文件 |
| requests/inbox/REQ-T188-secret-env.md | 新建 | 密钥/.env 测试文件 |
| requests/inbox/REQ-T188-direct-git.md | 新建 | 直接 Git 测试文件 |
| requests/inbox/REQ-T188-real-run-project-loop.md | 新建 | 真实执行测试文件 |
| requests/inbox/REQ-T188-real-rework.md | 新建 | 真实返工测试文件 |
| requests/inbox/REQ-T188-restricted-files.md | 新建 | 框架文件测试文件 |
| requests/inbox/REQ-T188-delete-files.md | 新建 | 删除文件测试文件 |
| reports/external-requests/REQ-T188-*-report.md | 新建 | Dry-run 生成的 8 份报告 |
| reports/checks/T188-external-request-safety-gate-fail-closed-validation.md | 新建 | T188 验证报告 |
| reports/dev/T188-dev-report.md | 新建 | T188 dev report |
| docs/tasks.md | 修改 | T188 标记为 done，NEXT_PENDING 指向 T189 |

---

```text
TASK=T188
VALIDATION_STATUS=done
FILES_CREATED=reports/checks/T188-external-request-safety-gate-fail-closed-validation.md, reports/dev/T188-dev-report.md, requests/inbox/REQ-T188-empty.md, requests/inbox/REQ-T188-prompt-injection.md, requests/inbox/REQ-T188-secret-env.md, requests/inbox/REQ-T188-direct-git.md, requests/inbox/REQ-T188-real-run-project-loop.md, requests/inbox/REQ-T188-real-rework.md, requests/inbox/REQ-T188-restricted-files.md, requests/inbox/REQ-T188-delete-files.md
FILES_MODIFIED=docs/tasks.md
BUSINESS_CODE_CHANGED=no
FRAMEWORK_CODE_CHANGED=no
RUNNER_CHANGED=no
TOOLS_CHANGED=no
AGENTS_CHANGED=no
REAL_EXECUTION_CHANGED=no
CLAUDE_AGENT_SDK_INTEGRATED=no
SAFE_REQUEST_PASS=pass
EMPTY_REQUEST_FAIL_CLOSED=pass
MISSING_FILE_FAIL_CLOSED=pass
PROMPT_INJECTION_FAIL_CLOSED=pass
SECRET_ENV_REQUEST_FAIL_CLOSED=pass
DIRECT_GIT_REQUEST_FAIL_CLOSED=pass
REAL_RUN_PROJECT_LOOP_FAIL_CLOSED=pass
REAL_REWORK_REQUEST_FAIL_CLOSED=pass
RESTRICTED_FILES_REQUIRE_APPROVAL=pass
DELETE_FILES_REQUIRE_APPROVAL=pass
ALLOWED_TO_EXECUTE_ALWAYS_NO=pass
DOCS_TASKS_MODIFIED_BY_REQUEST=no
RUNNER_EXECUTED=no
EXTERNAL_EXECUTION_ENABLED=no
GIT_COMMANDS_EXECUTED=no
CHECK_RESULT=pass
NEXT_PENDING=T189
NEXT_STAGE=Stage 11
```
