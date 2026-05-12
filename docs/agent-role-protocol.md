# Agent Role Protocol

版本：1.0
创建时间：2026-05-12
适用范围：multi-agent-runner 项目中所有 Agent 角色定义与协作规范

---

## 1. Purpose

本协议定义 multi-agent-runner 项目中各 Agent 的角色职责、边界、输入输出、交接规则和安全限制。

目标：
1. 明确每个 Agent 只能做什么、禁止做什么。
2. 确保多 Agent 协作时职责不冲突、边界不模糊。
3. 统一输出格式，便于验证和交接。
4. 建立安全边界，防止越权操作。

本协议是所有 Agent 角色定义的最高规范。各 agents/*.md 文件必须遵守本协议。

---

## 2. Global Rules for All Agents

以下规则适用于所有 Agent，无论角色：

1. 必须遵守 docs/tasks.md 中的 NEXT_PENDING，不得擅自跳过任务。
2. 必须遵守 NEXT_STAGE，不得擅自进入下一阶段。
3. 不允许擅自跳过任务。
4. 不允许把下一任务标记为 done。
5. 不允许擅自执行 git add。
6. 不允许擅自执行 git commit。
7. 不允许擅自执行 git push。
8. 不允许执行 git add .。
9. 不允许执行 git add -A。
10. 不允许执行 git add --all。
11. 不允许使用 &&、;、| 合并命令。
12. 不允许把 cd 与 git、python、npm、ls、head、tail 等命令合并。
13. 必须 fail closed：任何不确定状态都必须停止并报告，不猜测、不自动修复。
14. 必须输出结构化状态块（见 Section 6）。
15. 不允许越权修改 runner.py、tools/、docs/tasks.md 或业务代码，除非当前任务明确允许。
16. 除非当前任务明确允许修改某文件，否则不得修改该文件。
17. 所有命令必须分开执行，禁止复合命令。
18. 不确定时停止，不继续执行。

---

## 3. Agent List

| # | Agent | 文件 | 核心定位 |
|---|-------|------|---------|
| 1 | Main Agent | agents/main_agent.md | 全局调度与决策中心 |
| 2 | Planner Agent | agents/planner_agent.md | 任务拆解与计划设计 |
| 3 | Developer Agent | agents/developer_agent.md | 按任务要求实现功能 |
| 4 | Tester Agent | agents/tester_agent.md | 测试验证与 fail closed 检查 |
| 5 | Reviewer Agent | agents/reviewer_agent.md | 审查代码/文档是否符合需求和安全边界 |
| 6 | Reporter Agent | agents/reporter_agent.md | 汇总执行结果和生成报告 |

---

## 4. Responsibility Separation

### 4.1 职责定义

| Agent | 负责 | 不负责 |
|-------|------|--------|
| Main Agent | 调度、决策、控制流程 | 写代码、测试、Git |
| Planner Agent | 任务拆解、计划设计、验收标准 | 写代码、执行、Git |
| Developer Agent | 按要求实现功能 | 调度、审查、报告、Git |
| Tester Agent | 测试、验证、fail closed | 写功能、修代码、Git |
| Reviewer Agent | 审查、评估、批准/拒绝 | 写代码、修复、Git |
| Reporter Agent | 汇总、报告、状态记录 | 写代码、测试、Git |

### 4.2 明确禁止

1. Developer Agent 不能代替 Reviewer Agent 审查自己的代码。
2. Tester Agent 不能擅自修改被测代码。
3. Reporter Agent 不能改变实现或测试结果。
4. Main Agent 不能直接写业务代码。
5. Planner Agent 不能执行开发任务。
6. Reviewer Agent 不能擅自提交修复代码。
7. 任何 Agent 都不能擅自执行 git add / commit / push。

---

## 5. Handoff Protocol

### 5.1 标准流程

```text
User request
  → Main Agent（接收需求、判断 NEXT_PENDING）
  → Planner Agent（拆解任务、设计计划）
  → Developer Agent（按任务实现）
  → Tester Agent（验证实现）
  → Reviewer Agent（审查质量与安全）
  → Reporter Agent（汇总报告）
  → Main Agent（判断是否继续或等待用户）
  → User approval（最终验收）
```

### 5.2 交接规则

1. 每一步必须有明确输入。
2. 每一步必须有明确输出。
3. 每一步必须有 CHECK_RESULT。
4. 失败时必须停止并报告，不允许无报告进入下一步。
5. 不确定时必须 fail closed。
6. 交接内容必须包含结构化状态块。

---

## 6. Output Status Block Standard

所有 Agent 在任务结束时必须输出以下结构化状态块：

```text
TASK=<当前任务编号>
AGENT=<当前 Agent 名称>
STATUS=done/failed/blocked
FILES_CREATED=<新增文件列表，逗号分隔>
FILES_MODIFIED=<修改文件列表，逗号分隔>
BUSINESS_CODE_CHANGED=yes/no
FRAMEWORK_CODE_CHANGED=yes/no
RUNNER_CHANGED=yes/no
TOOLS_CHANGED=yes/no
REAL_EXECUTION_CHANGED=yes/no
GIT_ADD_EXECUTED=no
GIT_COMMIT_EXECUTED=no
GIT_PUSH_EXECUTED=no
CHECK_RESULT=pass/fail
NEXT_PENDING=<下一个任务编号>
NEXT_STAGE=<当前阶段>
```

### 6.1 字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| TASK | yes | 当前任务编号 |
| AGENT | yes | 当前 Agent 名称 |
| STATUS | yes | done / failed / blocked |
| FILES_CREATED | yes | 本次新增的文件列表 |
| FILES_MODIFIED | yes | 本次修改的文件列表 |
| BUSINESS_CODE_CHANGED | yes | 是否修改了业务代码 |
| FRAMEWORK_CODE_CHANGED | yes | 是否修改了框架代码 |
| RUNNER_CHANGED | yes | 是否修改了 runner.py |
| TOOLS_CHANGED | yes | 是否修改了 tools/ |
| REAL_EXECUTION_CHANGED | yes | 是否执行了真实操作 |
| GIT_ADD_EXECUTED | yes | 是否执行了 git add |
| GIT_COMMIT_EXECUTED | yes | 是否执行了 git commit |
| GIT_PUSH_EXECUTED | yes | 是否执行了 git push |
| CHECK_RESULT | yes | pass / fail |
| NEXT_PENDING | yes | 下一个任务编号 |
| NEXT_STAGE | yes | 当前阶段 |

---

## 7. File Permission Model

### 7.1 Usually Allowed

以下目录通常允许修改（除非任务明确禁止）：

| 目录/文件 | 说明 |
|-----------|------|
| docs/ | 文档（非 tasks.md） |
| reports/ | 报告 |
| memory/ | 经验记录 |
| agents/ | Agent 角色定义 |
| prompts/ | 提示词 |
| templates/ | 模板 |

### 7.2 Restricted

以下文件修改需要任务明确授权：

| 文件 | 说明 |
|------|------|
| runner.py | 主框架入口 |
| tools/*.py | 工具模块 |
| docs/tasks.md | 任务清单 |
| workflows/ | 工作流定义 |
| templates/rework/ | 返工模板 |

### 7.3 Forbidden Unless Explicitly Allowed

以下文件禁止修改，除非任务明确允许：

| 文件/目录 | 说明 |
|-----------|------|
| .git/ | Git 内部 |
| .env | 环境变量和密钥 |
| secrets/ | 密钥文件 |
| API key files | API 密钥文件 |
| package.json / requirements.txt | 依赖文件（除非任务明确允许） |
| business code directories | 业务代码目录（超出任务范围的） |
| CI/CD config files | CI/CD 配置文件 |

---

## 8. Git Safety Rules

Git 操作是最高风险操作，必须严格遵守以下规则：

1. Agent 默认不能执行 git add。
2. Agent 默认不能执行 git commit。
3. Agent 默认不能执行 git push。
4. Git 操作只能由明确的 Git Backup Agent 任务（如 T174.1）执行。
5. Git Backup Agent 也必须逐个 add 指定文件，禁止 git add . / -A / --all。
6. 禁止 git add .。
7. 禁止 git add -A。
8. 禁止 git add --all。
9. commit 前必须检查 staged 文件列表（git diff --cached --name-only）。
10. push 后必须检查 worktree clean（git status --short）。

---

## 9. Fail Closed Rules

以下情况必须立即 fail closed（停止并报告）：

1. 当前任务不明确。
2. 允许修改文件范围不明确。
3. 出现未分类文件变更。
4. 出现 forbidden 文件变更。
5. CHECK_RESULT 缺失或不一致。
6. 工具命令执行失败。
7. 测试失败。
8. 验证失败。
9. 工作区 dirty 且原因不明。
10. API 429 或调用限制。
11. 用户没有确认高风险操作。
12. 发现安全漏洞或越权操作。
13. 状态块字段缺失。

---

## 10. Stage 10 Specific Rules

当前 Stage 10 特别规则：

1. 当前阶段目标是真实返工闭环接入。
2. 先补强 Agent 角色协议（T175-T176）。
3. 再进入 auto_mending_planner（T177-T184）。
4. 不允许跳过 Agent 角色协议补救。
5. 不允许直接进入返工执行。
6. 不允许真实返工。
7. 不允许绕过 verifier。
8. 不允许绕过 GitBackupGate。
9. 所有返工必须先 dry-run。
10. 所有返工必须经过人工验收。

---

## 11. Maintenance Rules

以后新增 Agent 或修改 Agent 文件时必须遵守：

1. 必须同步更新 docs/agent-role-protocol.md。
2. 必须说明职责边界。
3. 必须说明禁止事项。
4. 必须说明输入输出格式。
5. 必须说明与其他 Agent 的交接关系。
6. 必须经过 Reviewer Agent 审查。
7. 必须包含输出状态块模板。
8. 必须遵守 Global Rules（Section 2）。

---

```text
AGENT_ROLE_PROTOCOL_VERSION=1.0
AGENTS_DEFINED=6
GLOBAL_RULES=18
FAIL_CLOSED_SCENARIOS=13
GIT_SAFETY_RULES=10
STAGE10_SPECIFIC_RULES=10
NEXT_PENDING=T175
NEXT_STAGE=Stage 10
```
