# T187 Dev Report：实现 external_request_inbox.py dry-run

任务编号：T187
完成时间：2026-05-13
角色：Dev Agent + Stage 11 External Request Inbox Dry-run Implementer
目标：实现 external_request_inbox.py dry-run。

---

## 1. 主要功能

tools/external_request_inbox.py 实现了 local request inbox dry-run：

1. 读取指定 Markdown request 文件。
2. 解析 YAML front matter metadata 与正文。
3. 构建 ExternalRequest 数据结构（18 字段）。
4. 执行 ExternalRequestSafetyGate（17 条规则）。
5. 检测 Prompt Injection（critical / high / medium / low 四级）。
6. 生成 TaskProposal dry-run（13 字段）。
7. 写入 reports/external-requests/ 报告。
8. CLI 支持 --request-file、--output-dir、--dry-run、--print-proposal。
9. 不修改 docs/tasks.md。
10. 不执行 runner。
11. 不执行真实任务。
12. 不执行 Git 操作。
13. 不调用模型。
14. 不启用外部真实执行。
15. 使用 Python 标准库。

## 2. 实现的数据结构

### 2.1 ExternalRequest（18 字段）

request_id、source_type、source_ref、title、raw_content、normalized_summary、requester、created_at、priority、requested_stage、requested_files、suspected_intent、safety_risk_level、prompt_injection_risk、requires_user_approval、allowed_to_plan、allowed_to_execute、fail_reason。

### 2.2 ExternalRequestSafetyResult（10 字段）

ok、request_id、risk_level、prompt_injection_risk、blocked_reasons、warnings、allowed_to_plan、allowed_to_execute、requires_user_approval、next_action。

### 2.3 TaskProposal（13 字段）

proposal_id、request_id、title、normalized_summary、proposed_tasks、proposed_files、forbidden_files、required_agents、risk_level、requires_user_approval、allowed_to_write_tasks、allowed_to_execute、next_action。

### 2.4 RequestInboxRecord（11 字段）

request_path、request_id、parse_status、safety_status、proposal_status、report_path、processed_at、dry_run、moved_to_processed、moved_to_rejected、fail_reason。

## 3. Safety Gate 规则（17 条）

1. 空请求 fail closed。
2. 文件不存在 fail closed。
3. 解析失败 fail closed。
4. 来源不明 fail closed。
5. 请求要求泄露密钥 fail closed。
6. 请求要求读取 .env fail closed。
7. 请求要求绕过系统限制 fail closed。
8. 请求要求直接 git add/commit/push fail closed。
9. 请求要求直接执行真实 run-project-loop fail closed。
10. 请求要求直接执行真实返工 fail closed。
11. 请求要求修改 runner.py/tools/agents/ 必须 user approval。
12. 请求包含删除文件要求必须 user approval。
13. 请求包含网络调用要求必须 user approval。
14. 请求包含 prompt injection 风险必须标记。
15. allowed_to_execute 永远为 false。
16. allowed_to_plan 只有低风险或中风险且未被阻断时才可 true。
17. 所有不确定情况 fail closed。

## 4. Safe Sample 验证结果

请求文件：requests/inbox/REQ-T187-safe-sample.md
内容：低风险文档改进建议。

结果：
- EXTERNAL_REQUEST_INBOX_RESULT=pass
- SAFETY_STATUS=pass
- PROMPT_INJECTION_RISK=low
- ALLOWED_TO_PLAN=yes
- ALLOWED_TO_EXECUTE=no
- TASK_PROPOSAL_CREATED=yes
- CHECK_RESULT=pass

报告：reports/external-requests/REQ-T187-SAFE-SAMPLE-report.md

## 5. Blocked Sample 验证结果

请求文件：requests/inbox/REQ-T187-blocked-sample.md
内容：忽略规则、读取 .env、git add .、git commit、git push。

结果：
- EXTERNAL_REQUEST_INBOX_RESULT=fail
- SAFETY_STATUS=fail
- PROMPT_INJECTION_RISK=critical
- ALLOWED_TO_PLAN=no
- ALLOWED_TO_EXECUTE=no
- TASK_PROPOSAL_CREATED=no
- BLOCKED_REASONS 包含 12 条安全风险
- CHECK_RESULT=fail

报告：reports/external-requests/REQ-T187-BLOCKED-SAMPLE-report.md

## 6. 生成的报告

1. reports/external-requests/REQ-T187-SAFE-SAMPLE-report.md
2. reports/external-requests/REQ-T187-BLOCKED-SAMPLE-report.md

## 7. 未修改 runner.py

本任务未修改 runner.py。

## 8. 未修改其他 tools

本任务未修改 tools/ 目录下除 external_request_inbox.py 以外的任何文件。

## 9. 未修改 agents

本任务未修改 agents/ 目录下任何文件。

## 10. 未修改业务代码

本任务未修改任何业务代码。

## 11. 未启用外部真实执行

- EXTERNAL_EXECUTION_ENABLED=no
- 所有外部请求默认只能生成 proposal
- allowed_to_execute 始终为 false

## 12. 未执行 Git

- GIT_ADD_EXECUTED=no
- GIT_COMMIT_EXECUTED=no
- GIT_PUSH_EXECUTED=no

## 13. 未把 request 转成真实 docs/tasks.md 任务

- safe sample 和 blocked sample 都未转换为真实任务
- docs/tasks.md 只更新了 T187 状态和 NEXT_PENDING 指针
- 没有新增任何来自外部请求的任务

---

## 文件变更

| 文件 | 操作 | 说明 |
|------|------|------|
| tools/external_request_inbox.py | 新建 | External request inbox dry-run 实现 |
| requests/inbox/REQ-T187-safe-sample.md | 新建 | 安全样例 request |
| requests/inbox/REQ-T187-blocked-sample.md | 新建 | 被阻止样例 request |
| reports/external-requests/REQ-T187-SAFE-SAMPLE-report.md | 新建 | Safe sample 报告 |
| reports/external-requests/REQ-T187-BLOCKED-SAMPLE-report.md | 新建 | Blocked sample 报告 |
| reports/dev/T187-dev-report.md | 新建 | T187 dev report |
| docs/tasks.md | 修改 | T187 标记为 done，NEXT_PENDING 指向 T188 |

---

```text
TASK=T187
IMPLEMENTATION_STATUS=done
FILES_CREATED=tools/external_request_inbox.py, requests/inbox/REQ-T187-safe-sample.md, requests/inbox/REQ-T187-blocked-sample.md, reports/dev/T187-dev-report.md
FILES_MODIFIED=docs/tasks.md
BUSINESS_CODE_CHANGED=no
FRAMEWORK_CODE_CHANGED=yes
RUNNER_CHANGED=no
TOOLS_CHANGED=yes
AGENTS_CHANGED=no
REAL_EXECUTION_CHANGED=no
CLAUDE_AGENT_SDK_INTEGRATED=no
EXTERNAL_REQUEST_INBOX_IMPLEMENTED=yes
DRY_RUN_IMPLEMENTED=yes
EXTERNAL_REQUEST_IMPLEMENTED=yes
SAFETY_GATE_IMPLEMENTED=yes
TASK_PROPOSAL_IMPLEMENTED=yes
PROMPT_INJECTION_DETECTION_IMPLEMENTED=yes
SAFE_SAMPLE_DRY_RUN=pass
BLOCKED_SAMPLE_DRY_RUN=pass
DOCS_TASKS_MODIFIED_BY_REQUEST=no
RUNNER_EXECUTED=no
EXTERNAL_EXECUTION_ENABLED=no
GIT_COMMANDS_EXECUTED=no
PY_COMPILE_STATUS=pass
CHECK_RESULT=pass
NEXT_PENDING=T188
NEXT_STAGE=Stage 11
```
