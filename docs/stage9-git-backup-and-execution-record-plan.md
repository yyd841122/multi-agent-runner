# Stage 9 Git Backup and Execution Record Plan

规划时间：2026-05-11
阶段：Stage 8 → Stage 9 过渡规划
规划角色：Architect Agent + Stage 9 Git Backup Planning Architect
规划范围：Stage 9 自动 Git 备份与执行记录入口

---

## 1. Background

### 1.1 Stage 8 已完成的安全基础

Stage 8 完成了 monitor → verify → report 最小闭环（T153-T165，共 13 个任务），已验证：

1. **max_tasks=1 controlled path** 已验证稳定（T163 真实受控验证通过）。
2. **max_tasks>1 fail closed** 已验证成立。
3. **continuous run report** 已生成并确认结构正确。
4. **task_monitor.py marker bug** 已修复并复验。
5. **monitor → verify → report pipeline** 已集成到 runner.py。

### 1.2 当前仍禁止的操作

当前仍禁止自动 git add / commit / push。每轮执行后需要人工执行 Txxx.1 任务来提交推送。

### 1.3 Stage 7 已有 Git 安全基础

Stage 7 已完成 real Git add/commit approval gate 设计（T139）和 dry-run 实现（T140-T142），包括：

1. Approval gate 设计（文件范围限制、敏感文件保护、commit message 校验）。
2. Dry-run 数据结构（35+ 字段）。
3. Planned files 校验和 commit message 校验。
4. 15 个 pass/fail 场景验证。

Stage 9 应在 Stage 7 approval gate 和 Stage 8 monitor → verify → report 基础上，规划受控的自动 Git 备份能力。

---

## 2. Stage 9 Goal

Stage 9 的核心目标是在安全门下实现受控的自动 Git 备份与执行记录：

1. **建立 GitBackupGate**：在 continuous verifier pass 后，自动分类变更文件，判断是否可以安全提交。
2. **建立执行记录归档机制**：每轮 Git 备份生成独立记录，包含完整的审批、分类、提交信息。
3. **建立 commit / push approval gate**：在 GitBackupGate pass 后，生成 commit proposal 和 push proposal，等待确认后执行。
4. **建立变更文件分类**：将 changed files 分为 allowed、forbidden、unclassified 三类，只有全部 allowed 时才允许继续。
5. **建立 commit message 生成规则**：根据任务内容自动生成符合项目风格的 commit message。
6. **建立只允许白名单文件提交的机制**：只有明确允许的文件类型和路径才能被 add。
7. **建立失败时 fail closed 的机制**：任何异常、未分类文件、forbidden 文件都立即停止。

---

## 3. Non-goals

Stage 9 明确不做以下事项：

| # | 不做 | 原因 |
|---|------|------|
| 1 | 不开放无限真实连续执行 | 当前仍以 max_tasks=1 为安全边界 |
| 2 | 不跳过人工验收 | 每轮执行后仍需人工确认 |
| 3 | 不提交未分类文件 | 未分类文件必须 fail closed |
| 4 | 不使用 git add . | 必须逐个文件 add |
| 5 | 不使用 git add -A | 必须逐个文件 add |
| 6 | 不在 dirty workspace 未分类时继续 | 必须先分类所有变更 |
| 7 | 不在 forbidden path 变化时继续 | forbidden 变更必须 fail closed |
| 8 | 不绕过 approval gate | 必须通过 GitBackupGate 检查 |
| 9 | 不解决 API 429 / 5 小时限额自动恢复 | 属于未来范围 |
| 10 | 不实现自动 mending 返工闭环 | 属于未来范围 |

---

## 4. Proposed GitBackupGate

### 4.1 职责

GitBackupGate 在 continuous verifier pass 后运行，负责：

1. 读取执行结果（continuous run report）。
2. 读取 continuous verifier 结果。
3. 检查 CHECK_RESULT 是否为 pass。
4. 检查 worktree 状态。
5. 分类 changed files（allowed / forbidden / unclassified）。
6. 生成 git add allowlist。
7. 生成 commit message proposal。
8. 输出 GitBackupGateResult。
9. fail closed。

### 4.2 流程

```text
Task completed
  ↓
continuous_verifier pass
  ↓
execution_report_writer done
  ↓
GitBackupGate
  ├─ 读取 continuous run report
  ├─ 检查 CHECK_RESULT
  ├─ 读取 git status --short
  ├─ 分类 changed files
  ├─ 检查 forbidden files → fail closed
  ├─ 检查 unclassified files → fail closed
  ├─ 生成 commit message proposal
  └─ 输出 GitBackupGateResult
  ↓
if ok:
  → 生成 approval record
  → 等待用户确认
  → git add exact allowlist
  → git commit
  → git push
  → write git backup record
else:
  → fail closed
  → 输出 fail reason
  → stop
```

### 4.3 GitBackupGateResult 字段

```python
@dataclass
class GitBackupGateResult:
    # 基本信息
    project_root: str
    gate_timestamp: str
    task_id: str
    stage: str

    # 检查结果
    check_result_pass: bool          # CHECK_RESULT 是否为 pass
    worktree_status: str             # clean / dirty
    changed_files: list[str]         # 所有变更文件

    # 文件分类
    allowed_files: list[str]         # 允许提交的文件
    forbidden_files: list[str]       # 禁止提交的文件
    unclassified_files: list[str]    # 未分类文件

    # 决策
    ok: bool                         # gate 是否通过
    commit_allowed: bool             # 是否允许 commit
    push_allowed: bool               # 是否允许 push
    approval_required: bool          # 是否需要人工审批

    # Commit 信息
    commit_message_proposal: str     # 建议 commit message

    # 失败
    fail_reason: str | None          # 失败原因
    next_action: str                 # proceed_to_commit / stop
```

### 4.4 Fail-closed 规则

| 场景 | fail_reason | 行为 |
|------|-------------|------|
| CHECK_RESULT 不是 pass | check_result_not_pass | stop |
| worktree 状态异常 | worktree_dirty_unclassified | stop |
| 存在 forbidden files | forbidden_files_detected | stop |
| 存在 unclassified files | unclassified_files_detected | stop |
| commit message 无法生成 | commit_message_generation_failed | stop |
| approval record 缺失 | approval_record_missing | stop |

---

## 5. File Classification Rules

### 5.1 Allowed Files

以下文件类型和路径默认允许提交（但需与当前 task_id 匹配）：

| 类别 | 路径模式 | 说明 |
|------|----------|------|
| 任务文件 | docs/tasks.md | 任务状态更新 |
| 开发报告 | reports/dev/Txxx-dev-report.md | 开发报告 |
| 验证报告 | reports/checks/Txxx-*.md | 验证报告 |
| 连续运行报告 | reports/continuous-runs/Txxx-run-report.md | 连续运行报告 |
| 归档文档 | docs/archive/*.md | 归档文档 |
| Git 备份记录 | reports/git/Txxx-git-backup-record.md | Git 备份记录 |
| Stage 8 报告 | reports/stage8/*.md | Stage 8 相关报告 |

允许条件：
- 文件路径必须在上述白名单范围内。
- 文件必须与当前 task_id 明确相关。
- 文件不得包含敏感信息。

### 5.2 Forbidden Files

以下文件始终禁止提交：

| 类别 | 路径/模式 | 说明 |
|------|-----------|------|
| Git 内部 | .git/** | Git 内部文件 |
| 环境变量 | .env, .env.*, *.env | 环境变量文件 |
| 密钥 | *.pem, *.key, *.p12, *.pfx | 证书和密钥 |
| SSH 密钥 | id_rsa, id_ed25519 | SSH 密钥 |
| 敏感文件 | *secret*, *token*, *credential*, *password* | 包含敏感信息的文件 |
| CI/CD 配置 | .github/**（除非当前任务明确允许） | CI/CD 配置 |
| 包管理 | package.json, pyproject.toml, requirements.txt（除非当前任务明确允许） | 依赖配置 |
| 框架核心 | runner.py（除非当前任务明确允许） | 框架核心代码 |
| 工具模块 | tools/*.py（除非当前任务明确允许） | 工具模块 |
| 业务代码 | 业务代码目录（除非当前任务明确允许） | 业务代码 |

### 5.3 Unclassified Files

任何不在 allowed 也不在 forbidden 列表中，且无法根据当前 task_id 判断归属的文件，都必须归入 unclassified。

**处理规则**：unclassified files 存在时必须 fail closed，不允许继续。

---

## 6. Commit and Push Approval Flow

### 6.1 完整流程

```text
Step 1: continuous_verifier pass
  ↓
Step 2: execution_report_writer done
  ↓
Step 3: GitBackupGate classify changes
  ↓
Step 4: generate approval record (reports/git/Txxx-git-backup-record.md)
  ↓
Step 5: user or approval gate confirms
  ↓
Step 6: git add <exact allowlist> (逐个文件)
  ↓
Step 7: git diff --cached --name-only (验证暂存区)
  ↓
Step 8: git commit -m "<approved message>"
  ↓
Step 9: git push
  ↓
Step 10: git status --short (确认 clean)
  ↓
Step 11: write git backup report
```

### 6.2 安全约束

| # | 约束 | 说明 |
|---|------|------|
| 1 | git add 必须逐个文件执行 | 禁止 git add . |
| 2 | 禁止 git add -A | 必须指定具体文件 |
| 3 | commit 前必须检查 git diff --cached --name-only | 确认暂存区与 allowlist 一致 |
| 4 | push 前必须 commit 成功 | commit 失败不 push |
| 5 | push 后必须确认 worktree clean | 确认最终状态 |
| 6 | 禁止 cd && git 复合命令 | 所有命令必须独立执行 |
| 7 | 每个 Txxx.1 任务只处理一个 Txxx 的文件 | 不跨任务提交 |
| 8 | commit message 必须与 task_id 匹配 | 不伪造其他任务 |

### 6.3 Commit Message 生成规则

建议格式：

```text
<type>: <short description>

类型包括：
  docs: 文档变更（reports/、docs/）
  feat: 新功能（tools/、runner.py）
  fix: Bug 修复
  test: 验证测试
  refactor: 重构
```

约束：
- commit message 必须包含或隐含当前 task_id 的范围。
- 不能声明未完成的能力。
- 不能包含 unsafe patterns（如 "auto push"、"auto commit"、"real execution completed"）。

---

## 7. Execution Record

### 7.1 执行记录路径

```text
reports/git/Txxx-git-backup-record.md
```

### 7.2 执行记录字段

| 字段 | 类型 | 说明 |
|------|------|------|
| TASK | str | 任务编号 |
| CHECK_RESULT | str | pass / fail |
| FILES_TO_ADD | list[str] | 允许 add 的文件列表 |
| FILES_FORBIDDEN | list[str] | 被拒绝的文件列表 |
| FILES_UNCLASSIFIED | list[str] | 未分类的文件列表 |
| COMMIT_MESSAGE | str | commit message |
| COMMIT_STATUS | str | done / failed / skipped |
| PUSH_STATUS | str | done / failed / skipped |
| LAST_COMMIT | str | 最后一次 commit hash |
| WORKTREE_STATUS | str | clean / dirty |
| NEXT_PENDING | str | 下一个 pending 任务 |
| NEXT_STAGE | str | 下一个阶段 |

### 7.3 记录生成时机

- GitBackupGate 运行完成后生成（无论 pass 还是 fail）。
- commit 成功后更新 COMMIT_STATUS。
- push 成功后更新 PUSH_STATUS 和 LAST_COMMIT。

---

## 8. Safety Rules

Stage 9 必须遵守的安全规则：

| # | 规则 | 说明 |
|---|------|------|
| 1 | dirty workspace with unclassified changes must stop | 未分类变更必须停止 |
| 2 | forbidden files must fail closed | 禁止文件必须 fail closed |
| 3 | missing CHECK_RESULT must fail closed | CHECK_RESULT 缺失必须 fail closed |
| 4 | failed verifier must stop | verifier 失败必须停止 |
| 5 | no git add . | 禁止全目录 add |
| 6 | no git add -A | 禁止全目录 add |
| 7 | no auto commit without approval | 未审批不允许 commit |
| 8 | no auto push without approval | 未审批不允许 push |
| 9 | no compound cd && git commands | 所有命令必须独立执行 |
| 10 | no silent continuation after failed backup | 备份失败不静默继续 |
| 11 | GitBackupGate 只读不执行 | 分类阶段不修改任何文件 |
| 12 | commit message 必须经过校验 | 不允许未经校验的 message |
| 13 | staged files 必须与 allowlist 一致 | 不允许额外文件进入暂存区 |
| 14 | push 后必须确认 clean | 不允许 push 后仍有脏文件 |

---

## 9. Suggested Stage 9 Tasks

| 任务 | 角色 | 目标 | 依赖 |
|------|------|------|------|
| T167 | Architect | 设计 GitBackupGate 数据结构与规则 | T166 |
| T168 | Developer | 实现 git_backup_gate.py dry-run | T167 |
| T169 | Validator | 验证 GitBackupGate 文件分类与 fail closed | T168 |
| T170 | Developer | 生成 Git backup approval record | T168 |
| T171 | Developer | 接入 guarded git backup dry-run 到 run-project-loop | T169, T170 |
| T172 | Validator | 验证 guarded git backup dry-run | T171 |
| T173 | Reviewer | Stage 9 最终规划审查 | T172 |

### T167：设计 GitBackupGate 数据结构与规则

设计 GitBackupGate 的详细数据结构、文件分类规则、commit message 生成规则。只做设计，不实现代码。

### T168：实现 git_backup_gate.py dry-run

实现 tools/git_backup_gate.py，包含文件分类、commit message 生成、GitBackupGateResult 输出。只读不写，不执行真实 git 操作。

### T169：验证 GitBackupGate 文件分类与 fail closed

验证 git_backup_gate.py 的文件分类逻辑和 fail-closed 行为。包含 allowed / forbidden / unclassified 三类文件的测试。

### T170：生成 Git backup approval record

实现 Git backup approval record 生成逻辑。生成 reports/git/Txxx-git-backup-record.md。

### T171：接入 guarded git backup dry-run 到 run-project-loop

将 GitBackupGate 接入 runner.py 的 stage8-monitor-verify-report pipeline 后端。仍然 dry-run，不执行真实 git 操作。

### T172：验证 guarded git backup dry-run

验证完整的 monitor → verify → report → git backup gate pipeline。确认 dry-run 行为正确。

### T173：Stage 9 最终规划审查

审查 Stage 9 的设计、实现和验证结果。确认可以进入受控真实 Git 备份。

---

## 10. Recommended Next Step

### 10.1 状态确认

```text
NEXT_PENDING=T167
NEXT_STAGE=Stage 9
```

### 10.2 建议

T166 完成后，建议执行 T167：设计 GitBackupGate 数据结构与规则。

### 10.3 前置确认

真正执行 Stage 9 前（即 T168 开始实现前），需要用户确认：

1. Stage 8 monitor → verify → report 最小闭环已审查通过（T165 done）。
2. Stage 9 规划已确认（T166 done）。
3. 用户明确同意进入 Stage 9 实施。

T167-T173 只是任务列表规划，不代表自动进入实施。

---

```text
PLANNING_STATUS=done
PLANNING_SCOPE=Stage_9_git_backup_and_execution_record
STAGE8_FOUNDATION=established
STAGE7_GIT_APPROVAL_GATE_EXISTS=yes
GIT_BACKUP_GATE_PLANNED=yes
FILE_CLASSIFICATION_RULES=defined
COMMIT_PUSH_APPROVAL_FLOW=defined
SAFETY_RULES=14
SUGGESTED_TASKS=T167-T173
AUTO_GIT_BACKUP_IMPLEMENTED=no
STAGE9_EXECUTION_STARTED=no
NEXT_PENDING=T167
NEXT_STAGE=Stage 9
```
