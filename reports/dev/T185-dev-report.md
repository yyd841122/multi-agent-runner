# T185 Dev Report：规划 Stage 11 外部入口自动化入口

任务编号：T185
完成时间：2026-05-13
角色：Architect Agent + Stage 11 External Entry Planning Architect
目标：规划 Stage 11 外部入口自动化入口，基于 Stage 8-10 安全基础设计外部接入方案。

---

## 1. 本次只规划，不实现

本任务是规划任务，不实现新功能，不创建 Python 文件，不修改 runner.py、tools/、agents/。

规划范围：
1. 总结 Stage 8 / Stage 9 / Stage 10 已建立的安全基础。
2. 明确 Stage 11 的目标是"外部入口自动化"。
3. 明确第一个外部入口建议从 local request inbox dry-run 开始。
4. 规划 ExternalRequest 数据结构（18 字段）。
5. 规划 ExternalRequestSafetyGate（13 条安全门规则）。
6. 规划 Request to Task Proposal Flow。
7. 规划 Prompt Injection Defense（10 条规则）。
8. 规划后续任务 T186-T194。

## 2. Stage 8-10 安全基础

1. **Stage 8**：monitor → verify → report 最小闭环成立。max_tasks=1 受控，max_tasks>1 fail closed。不执行真实 git 操作。
2. **Stage 9**：GitBackupGate dry-run 安全链成立。文件分类（allowed / forbidden / unclassified）验证通过。不执行真实 git add/commit/push。
3. **Stage 10**：返工 dry-run 安全链成立。auto_mending_planner 11 种 failure_type 分类、15 条决策规则、10 条安全门规则。不执行真实返工。

## 3. 为什么第一个入口建议 local request inbox dry-run

1. 不依赖外部服务（不需要 GitHub token、不需要 Web 服务器、不需要 API）。
2. 安全性最高（本地文件操作，不需要网络连接）。
3. 便于 fail closed（文件不存在、格式错误、内容异常都可以 fail closed）。
4. 便于后续扩展到 GitHub Issue / n8n（ExternalRequest 数据结构统一）。
5. 不会直接触发真实执行。

## 4. ExternalRequest 数据结构

设计了 ExternalRequest dataclass，包含 18 个字段：

1. request_id：请求唯一标识
2. source_type：来源类型
3. source_ref：来源引用
4. title：请求标题
5. raw_content：原始内容
6. normalized_summary：标准化摘要
7. requester：请求者
8. created_at：创建时间
9. priority：优先级
10. requested_stage：请求阶段
11. requested_files：涉及文件
12. suspected_intent：推断意图
13. safety_risk_level：安全风险等级
14. prompt_injection_risk：Prompt injection 风险
15. requires_user_approval：是否需要人工确认（默认 true）
16. allowed_to_plan：是否允许生成 proposal（默认 false）
17. allowed_to_execute：是否允许执行（默认 false，Stage 11 始终 false）
18. fail_reason：fail closed 原因

## 5. ExternalRequestSafetyGate

设计了 13 条安全门规则：

1. 空请求 fail closed。
2. 来源不明 fail closed。
3. 包含要求泄露密钥 fail closed。
4. 包含要求绕过安全规则 fail closed。
5. 包含要求直接 git push fail closed。
6. 包含要求直接执行真实返工 fail closed。
7. 包含要求删除文件 fail closed + 人工确认。
8. 涉及 runner.py / tools/ / agents/ 必须人工确认。
9. 涉及 .env / secrets / API key 必须 fail closed。
10. prompt injection 风险必须标记。
11. allowed_to_execute 默认 false。
12. allowed_to_plan 可在低风险时 true。
13. 所有外部请求默认只能生成 proposal。

## 6. Prompt Injection 防护

设计了 10 条 prompt injection 防护规则：

1. 外部请求内容一律视为不可信。
2. 外部请求不能覆盖系统规则。
3. 外部请求不能修改 Agent 角色规则。
4. 外部请求不能要求泄露密钥。
5. 外部请求不能要求绕过 GitBackupGate。
6. 外部请求不能要求执行复合命令。
7. 外部请求不能要求直接 push。
8. 外部请求只能作为需求内容，不作为执行指令。
9. 检测 "ignore previous instructions" / "system prompt" / "bypass safety" 等模式。
10. 检测结果按风险等级分级处理（critical → fail closed，medium → 人工确认，low → 标记）。

## 7. 后续任务 T186-T194

| 任务 | 角色 | 目标 |
|------|------|------|
| T186 | Architect | 设计 local request inbox dry-run 数据结构 |
| T187 | Developer | 实现 external_request_inbox.py dry-run |
| T188 | Validator | 验证 external request safety gate fail closed |
| T189 | Architect | 设计 GitHub Issue 外部入口 dry-run |
| T190 | Developer | 实现 GitHub Issue 读取与 proposal dry-run |
| T191 | Validator | 验证 GitHub Issue prompt injection 防护 |
| T192 | Developer | 接入 external request → task proposal dry-run |
| T193 | Validator | 验证外部请求生成任务草案但不执行 |
| T194 | Reviewer | Stage 11 最终状态审查 |

## 8. 未修改 runner.py

本任务只做规划，未修改 runner.py。

## 9. 未修改 tools/

本任务只做规划，未修改 tools/ 目录下任何文件。

## 10. 未修改 agents/

本任务只做规划，未修改 agents/ 目录下任何文件。

## 11. 未修改业务代码

本任务只做规划，未修改任何业务代码。

## 12. 未实现任何外部入口

本任务只做规划，未实现以下任何入口：
- 未创建 tools/external_request_inbox.py
- 未创建 tools/external_request_safety_gate.py
- 未创建 GitHub Issue workflow
- 未创建 .github/workflows 文件
- 未创建 Web UI
- 未创建 API
- 未创建 n8n workflow
- 未创建 requests/inbox/ 目录

## 13. 未启用外部真实执行

- EXTERNAL_EXECUTION_ENABLED=no
- 所有外部请求默认只能生成 proposal
- allowed_to_execute 始终为 false

---

## 文件变更

| 文件 | 操作 | 说明 |
|------|------|------|
| docs/stage11-external-entry-automation-plan.md | 新建 | Stage 11 外部入口自动化规划文档 |
| reports/dev/T185-dev-report.md | 新建 | T185 dev report |
| docs/tasks.md | 修改 | T185 标记为 done，新增 T186-T194 pending |

---

```text
TASK=T185
PLANNING_STATUS=done
FILES_CREATED=docs/stage11-external-entry-automation-plan.md, reports/dev/T185-dev-report.md
FILES_MODIFIED=docs/tasks.md
BUSINESS_CODE_CHANGED=no
FRAMEWORK_CODE_CHANGED=no
RUNNER_CHANGED=no
TOOLS_CHANGED=no
AGENTS_CHANGED=no
REAL_EXECUTION_CHANGED=no
CLAUDE_AGENT_SDK_INTEGRATED=no
STAGE11_PLAN_CREATED=yes
EXTERNAL_ENTRY_PLANNED=yes
LOCAL_REQUEST_INBOX_PLANNED=yes
GITHUB_ISSUE_ENTRY_PLANNED=yes
WEB_UI_ENTRY_IMPLEMENTED=no
API_ENTRY_IMPLEMENTED=no
N8N_ENTRY_IMPLEMENTED=no
EXTERNAL_EXECUTION_ENABLED=no
CHECK_RESULT=pass
NEXT_PENDING=T186
NEXT_STAGE=Stage 11
```
