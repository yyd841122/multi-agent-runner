# T174 Dev Report：规划 Stage 10 真实返工闭环接入入口

## 基本信息

- TASK=T174
- ROLE=Architect Agent + Stage 10 Rework Loop Planning Architect
- DATE=2026-05-12
- PROJECT_ROOT=E:/github_project/multi-agent-runner
- LAST_COMMIT=d47ba6c docs: add stage 9 final planning review
- 备注：本任务只做规划，不实现新功能

## 规划目标

规划 Stage 10：真实返工闭环接入入口。

## 已阅读文档

1. docs/tasks.md — 确认 T173 done、T174 pending、NEXT_PENDING=T174、NEXT_STAGE=Stage 10
2. docs/archive/stage9-final-planning-review.md — Stage 9 最终审查
3. docs/archive/stage8-final-status-review.md — Stage 8 最终审查
4. tools/rework_manager.py — 已有返工管理系统（821 行）
5. tools/continuous_verifier.py — 连续验证器（失败分类参考）
6. docs/rework-protocol.md — 返工协议（搜索确认存在）
7. docs/rework-execution-confirmation-protocol.md — 返工执行确认协议（搜索确认存在）
8. docs/full-loop-resume-design.md — 完整循环恢复设计（搜索确认存在）
9. templates/rework/ — 3 个返工模板（搜索确认存在）

## 规划成果

### 1. Stage 10 规划文档

文件：docs/stage10-real-rework-loop-plan.md

包含 11 个章节：

1. Background — Stage 8/9 已完成能力、已有返工基础设施、当前限制
2. Stage 10 Goal — 8 个具体目标、5 个不做的事
3. Non-goals — 10 条明确排除项
4. Proposed Rework Loop — 13 节点完整流程图、节点说明、最大轮次控制
5. ReworkDecision Data Structure — 15 字段 dataclass 草案、字段取值范围
6. Failure Classification Rules — 11 种失败类型、自动返工判断规则、返工优先级
7. Rework Safety Gate — 10 条安全门规则、检查流程、返工后安全保证
8. auto_mending_planner.py Scope — 模块定位、T175 dry-run 范围、与 rework_manager.py 关系
9. Integration Points — 5 个接入点（verifier 桥接、report 记录、runner 接入、git backup、rework 记录）
10. Suggested Stage 10 Tasks — T175-T182 共 8 个任务
11. Recommended Next Step — NEXT_PENDING=T175、NEXT_STAGE=Stage 10

### 2. ReworkDecision 数据结构

设计了 15 字段 dataclass：

- ok, task_id, verify_status
- failure_type, rework_allowed, auto_rework_allowed, user_approval_required
- rework_reason, target_files, forbidden_files, risk_level
- max_rework_rounds, current_rework_round
- next_action, fail_reason

### 3. 失败分类

11 种失败类型，按优先级 P0-P5 排序：
- P0: rate_limit_or_api_429（停止）
- P1: forbidden_file_changed, unclassified_changes, max_tasks_violation（停止）
- P2: dirty_workspace（停止）
- P3: syntax_failed, tests_failed, report_missing（自动返工）
- P4: check_result_failed, verifier_failed（条件返工）
- P5: unknown_failure（停止）

### 4. 返工安全门

10 条安全门规则，全部 fail closed：
- forbidden files / unclassified files / dirty workspace 一律 fail closed
- max_rework_rounds 超限停止
- missing failure_type / target_files 停止
- runner.py / tools/ 涉及需人工确认
- allowed scope 限制
- 返工后必须再次 verify

### 5. auto_mending_planner.py 后续范围

T175 只做 dry-run：
- 输入 verifier result、failure_type、changed files
- 输出 ReworkDecision、rework plan 草案
- 不修改文件、不执行返工、不调用真实模型
- fail closed

### 6. 后续任务 T175-T182

| 任务 | 角色 | 目标 |
|------|------|------|
| T175 | Architect | 设计 auto_mending_planner.py dry-run 数据结构 |
| T176 | Developer | 实现 auto_mending_planner.py dry-run |
| T177 | Validator | 验证 auto_mending_planner fail closed |
| T178 | Developer | 接入 verifier fail → rework decision dry-run |
| T179 | Validator | 验证 verifier fail 后生成 rework decision |
| T180 | Developer | 接入 rework_manager 受控返工 dry-run |
| T181 | Validator | 验证返工后 verify → report → git backup dry-run 链路 |
| T182 | Reviewer | Stage 10 最终状态审查 |

## 未修改的文件

- runner.py：未修改
- tools/rework_manager.py：未修改
- tools/git_backup_gate.py：未修改
- tools/task_monitor.py：未修改
- tools/continuous_verifier.py：未修改
- tools/execution_report_writer.py：未修改
- agents/*.md：未修改
- 业务代码：未修改

## T174_FIX 修正记录

### 问题发现

用户检查 agents/ 目录后发现：agents/*.md 文件（main_agent.md、planner_agent.md、developer_agent.md、tester_agent.md、reviewer_agent.md、reporter_agent.md）内容过于简单，每个文件仅约 10 行早期占位描述，缺少完整的角色职责、禁止事项、输入输出格式、文件范围、交接关系、Git 操作限制和失败报告规范。

### 修正措施

1. 本次修正不是推翻 Stage 8 / Stage 9 的成果，而是补齐 Agent Role Protocol Layer。
2. Stage 10 将先补强 Agent 角色协议层，再继续 auto_mending_planner。
3. 在 docs/stage10-real-rework-loop-plan.md 中新增 Section 3.1 Agent Role Protocol Remediation 章节。
4. T175 已调整为：完善 agents/*.md 角色职责、边界与输出规范。
5. T176 已调整为：验证 Agent 角色规范覆盖主流程。
6. auto_mending_planner 相关任务已顺延到 T177-T184。
7. 未修改 agents/*.md。
8. 未创建 docs/agent-role-protocol.md。
9. 未修改 runner.py。
10. 未修改 tools/。
11. 未执行真实返工。
12. 未执行 git add / commit / push。

### T174_FIX 状态

- T174_FIX_STATUS=done
- AGENT_ROLE_PROTOCOL_GAP_FOUND=yes
- AGENT_ROLE_PROTOCOL_REMEDIATION_PLANNED=yes
- AGENTS_MD_MODIFIED=no
- DOCS_AGENT_ROLE_PROTOCOL_CREATED=no
- AUTO_MENDING_PLANNER_TASKS_SHIFTED=yes

## 安全保证

- TASK=T174
- PLANNING_STATUS=done
- FILES_CREATED=docs/stage10-real-rework-loop-plan.md, reports/dev/T174-dev-report.md
- FILES_MODIFIED=docs/tasks.md
- BUSINESS_CODE_CHANGED=no
- FRAMEWORK_CODE_CHANGED=no
- RUNNER_CHANGED=no
- TOOLS_CHANGED=no
- REAL_EXECUTION_CHANGED=no
- CLAUDE_AGENT_SDK_INTEGRATED=no
- STAGE10_PLAN_CREATED=yes
- AUTO_MENDING_PLANNER_PLANNED=yes
- AUTO_MENDING_PLANNER_IMPLEMENTED=no
- REWORK_LOOP_IMPLEMENTED=no
- REAL_REWORK_EXECUTED=no
- AGENT_ROLE_PROTOCOL_GAP_FOUND=yes
- AGENT_ROLE_PROTOCOL_REMEDIATION_PLANNED=yes
- AGENTS_MD_MODIFIED=no
- DOCS_AGENT_ROLE_PROTOCOL_CREATED=no
- AUTO_MENDING_PLANNER_TASKS_SHIFTED=yes
- CHECK_RESULT=pass
- NEXT_PENDING=T175
- NEXT_STAGE=Stage 10

## 文件清单

### 本次新增文件

- docs/stage10-real-rework-loop-plan.md
- reports/dev/T174-dev-report.md

### 本次修改文件

- docs/tasks.md（T174 done，新增 T175-T184 pending，NEXT_PENDING → T175，NEXT_STAGE → Stage 10）

## 最终状态

```
TASK=T174
PLANNING_STATUS=done
FILES_CREATED=docs/stage10-real-rework-loop-plan.md, reports/dev/T174-dev-report.md
FILES_MODIFIED=docs/tasks.md
BUSINESS_CODE_CHANGED=no
FRAMEWORK_CODE_CHANGED=no
RUNNER_CHANGED=no
TOOLS_CHANGED=no
REAL_EXECUTION_CHANGED=no
CLAUDE_AGENT_SDK_INTEGRATED=no
STAGE10_PLAN_CREATED=yes
AUTO_MENDING_PLANNER_PLANNED=yes
AUTO_MENDING_PLANNER_IMPLEMENTED=no
REWORK_LOOP_IMPLEMENTED=no
REAL_REWORK_EXECUTED=no
AGENT_ROLE_PROTOCOL_GAP_FOUND=yes
AGENT_ROLE_PROTOCOL_REMEDIATION_PLANNED=yes
AGENTS_MD_MODIFIED=no
DOCS_AGENT_ROLE_PROTOCOL_CREATED=no
AUTO_MENDING_PLANNER_TASKS_SHIFTED=yes
CHECK_RESULT=pass
NEXT_PENDING=T175
NEXT_STAGE=Stage 10
```
