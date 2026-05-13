# T186 Dev Report：设计 local request inbox dry-run 数据结构

任务编号：T186
完成时间：2026-05-13
角色：Architect Agent + Stage 11 Local Request Inbox Design Architect
目标：设计 local request inbox dry-run 数据结构，只设计不实现。

---

## 1. 本次只设计，不实现

本任务是设计任务，不实现新功能，不创建 Python 文件，不修改 runner.py、tools/、agents/。

设计范围：
1. 设计 local request inbox 的目录结构。
2. 设计 ExternalRequest 数据结构（18 字段）。
3. 设计 ExternalRequestSafetyResult 数据结构（10 字段）。
4. 设计 TaskProposal 数据结构（13 字段）。
5. 设计 RequestInboxRecord 数据结构（11 字段）。
6. 设计 request 文件格式（YAML front matter + Markdown）。
7. 设计 safety gate 规则（15 条）。
8. 设计 prompt injection 检测规则（13 条）。
9. 设计 request → proposal dry-run 流程。
10. 设计 reports/external-requests/ 报告格式。
11. 明确 T187 实现范围。

## 2. 设计的数据结构

### 2.1 ExternalRequest（18 字段）

标准化外部请求数据结构，用于接收来自不同来源的用户需求。

字段：request_id、source_type、source_ref、title、raw_content、normalized_summary、requester、created_at、priority、requested_stage、requested_files、suspected_intent、safety_risk_level、prompt_injection_risk、requires_user_approval、allowed_to_plan、allowed_to_execute、fail_reason。

安全默认值：safety_risk_level 默认 high，prompt_injection_risk 默认 high，requires_user_approval 默认 True，allowed_to_plan 默认 False，allowed_to_execute 默认 False。

### 2.2 ExternalRequestSafetyResult（10 字段）

安全门检查结果，记录请求是否通过安全检查。

字段：ok、request_id、risk_level、prompt_injection_risk、blocked_reasons、warnings、allowed_to_plan、allowed_to_execute、requires_user_approval、next_action。

### 2.3 TaskProposal（13 字段）

外部请求生成的任务提案，包含拆解后的任务列表。

字段：proposal_id、request_id、title、normalized_summary、proposed_tasks、proposed_files、forbidden_files、required_agents、risk_level、requires_user_approval、allowed_to_write_tasks、allowed_to_execute、next_action。

Stage 11 约束：allowed_to_write_tasks 始终 False，allowed_to_execute 始终 False。

### 2.4 RequestInboxRecord（11 字段）

请求处理记录，记录每个请求文件的处理状态。

字段：request_path、request_id、parse_status、safety_status、proposal_status、report_path、processed_at、dry_run、moved_to_processed、moved_to_rejected、fail_reason。

Stage 11 约束：dry_run 始终 True，moved_to_processed 始终 False，moved_to_rejected 始终 False。

## 3. Request 文件格式

采用 YAML front matter + Markdown 正文格式。metadata 字段全部可选。缺少字段时由工具自动生成默认值。正文一律视为不可信内容。

## 4. Safety Gate 规则（15 条）

1. 空请求 fail closed。
2. 解析失败 fail closed。
3. 来源不明 fail closed。
4. 请求要求泄露密钥 fail closed。
5. 请求要求读取 .env fail closed。
6. 请求要求绕过系统限制 fail closed。
7. 请求要求直接 git add/commit/push fail closed。
8. 请求要求直接执行真实 run-project-loop fail closed。
9. 请求要求直接执行真实返工 fail closed。
10. 请求要求修改 runner.py/tools/agents/ 必须 user approval。
11. 请求包含删除文件要求必须 user approval。
12. 请求包含网络调用要求必须 user approval。
13. 请求包含 prompt injection 风险必须标记。
14. allowed_to_execute 默认 false。
15. allowed_to_plan 只有低风险请求才可 true。

## 5. Prompt Injection 检测规则（13 条）

涵盖英文和中文的常见 prompt injection 模式，分 critical / high / medium / low 四级。涉及密钥/绕过安全/直接 Git/删除文件的模式必须 fail closed。

## 6. T187 实现范围

T187 应只实现 dry-run：
1. 创建 tools/external_request_inbox.py。
2. 使用 Python 标准库。
3. 读取 requests/inbox/ 下指定文件。
4. 解析 Markdown YAML front matter 和正文。
5. 构建 ExternalRequest。
6. 执行 safety gate。
7. 构建 TaskProposal dry-run。
8. 写 reports/external-requests/ 报告。
9. 不移动 request 文件。
10. 不修改 docs/tasks.md。
11. 不执行 runner。
12. 不执行 Git。
13. 不调用模型。
14. fail closed。

## 7. 未创建 tools/external_request_inbox.py

本任务只做设计，未创建 tools/external_request_inbox.py。

## 8. 未修改 runner.py

本任务只做设计，未修改 runner.py。

## 9. 未修改 tools/

本任务只做设计，未修改 tools/ 目录下任何文件。

## 10. 未修改 agents/

本任务只做设计，未修改 agents/ 目录下任何文件。

## 11. 未修改业务代码

本任务只做设计，未修改任何业务代码。

## 12. 未创建 requests/ 目录

本任务只做设计，未创建 requests/inbox/、requests/processed/、requests/rejected/ 目录。

## 13. 未创建 reports/external-requests/ 目录

本任务只做设计，未创建 reports/external-requests/ 目录。

## 14. 未启用外部真实执行

- EXTERNAL_EXECUTION_ENABLED=no
- 所有外部请求默认只能生成 proposal
- allowed_to_execute 始终为 false

## 15. 未执行 Git

- GIT_ADD_EXECUTED=no
- GIT_COMMIT_EXECUTED=no
- GIT_PUSH_EXECUTED=no

---

## 文件变更

| 文件 | 操作 | 说明 |
|------|------|------|
| docs/stage11-local-request-inbox-design.md | 新建 | Local request inbox 设计文档 |
| reports/dev/T186-dev-report.md | 新建 | T186 dev report |
| docs/tasks.md | 修改 | T186 标记为 done，NEXT_PENDING 指向 T187 |

---

```text
TASK=T186
DESIGN_STATUS=done
FILES_CREATED=docs/stage11-local-request-inbox-design.md, reports/dev/T186-dev-report.md
FILES_MODIFIED=docs/tasks.md
BUSINESS_CODE_CHANGED=no
FRAMEWORK_CODE_CHANGED=no
RUNNER_CHANGED=no
TOOLS_CHANGED=no
AGENTS_CHANGED=no
REAL_EXECUTION_CHANGED=no
CLAUDE_AGENT_SDK_INTEGRATED=no
LOCAL_REQUEST_INBOX_DESIGNED=yes
EXTERNAL_REQUEST_DESIGNED=yes
SAFETY_RESULT_DESIGNED=yes
TASK_PROPOSAL_DESIGNED=yes
REQUEST_INBOX_RECORD_DESIGNED=yes
PROMPT_INJECTION_RULES_DESIGNED=yes
EXTERNAL_REQUEST_INBOX_IMPLEMENTED=no
EXTERNAL_EXECUTION_ENABLED=no
GIT_COMMANDS_EXECUTED=no
CHECK_RESULT=pass
NEXT_PENDING=T187
NEXT_STAGE=Stage 11
```
