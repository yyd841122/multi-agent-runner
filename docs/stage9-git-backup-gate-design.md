# Stage 9 GitBackupGate Design

设计时间：2026-05-11
阶段：Stage 9 — 自动 Git 备份与执行记录
设计角色：Architect Agent + Stage 9 Git Backup Gate Architect
前置条件：T166 done, T166.1 committed and pushed

---

## 1. Background

### 1.1 Stage 8 已完成的安全基础

Stage 8 完成了 monitor → verify → report 最小闭环，已验证：

1. max_tasks=1 controlled path 稳定。
2. max_tasks>1 fail closed。
3. continuous run report 结构正确。
4. task_monitor.py marker 解析 bug 已修复。
5. pipeline 已集成到 runner.py。

### 1.2 Stage 8 仍然禁止的操作

Stage 8 仍然禁止自动 git add / commit / push。每轮执行后需要人工执行 Txxx.1 任务来提交推送。这导致大量重复性的手动提交工作。

### 1.3 Stage 9 为什么需要 GitBackupGate

Stage 9 的目标是在严格安全规则下，将人工 Txxx.1 提交流程转化为受控的 Git 备份 gate。GitBackupGate 负责：

1. 判断是否可以安全提交。
2. 分类变更文件。
3. 生成 commit proposal。
4. 生成 approval record。
5. fail closed。

### 1.4 GitBackupGate 的职责边界

GitBackupGate 不负责执行任务，只负责判断是否允许进入 Git 备份流程。它是一个决策 gate，不是执行器。

---

## 2. Design Goal

GitBackupGate 的设计目标：

1. 读取任务执行结果（continuous verifier result）。
2. 读取 continuous run report。
3. 读取 git status。
4. 分类 changed files 为 allowed / forbidden / unclassified。
5. 生成 allowed files 列表。
6. 识别 forbidden files 并记录。
7. 识别 unclassified files 并记录。
8. 判断 commit_allowed。
9. 判断 push_allowed。
10. 判断 approval_required。
11. 生成 git backup approval record 的输入数据。
12. 为 T168 dry-run 实现提供明确数据结构。

---

## 3. Non-goals

本阶段明确不做：

| # | 不做 | 原因 |
|---|------|------|
| 1 | 不执行 git add | 只做分类和判断 |
| 2 | 不执行 git commit | 只做分类和判断 |
| 3 | 不执行 git push | 只做分类和判断 |
| 4 | 不实现自动 Git backup | 只设计 gate |
| 5 | 不修改 runner.py | T167 只做设计 |
| 6 | 不接入 run-project-loop | 后续 T171 任务 |
| 7 | 不实现 API 429 / 5 小时限额恢复 | 超出 Stage 9 范围 |
| 8 | 不实现 auto_mending_planner.py | 超出 Stage 9 范围 |
| 9 | 不实现 run_state_manager.py | 超出 Stage 9 范围 |
| 10 | 不跳过人工确认 | approval gate 必须经过确认 |

---

## 4. GitBackupGate Input

### 4.1 输入字段

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| repo_root | str | yes | 项目根路径 |
| task_id | str | yes | 当前任务编号 |
| expected_next_pending | str | yes | 预期下一个 pending 任务 |
| expected_next_stage | str | yes | 预期下一个阶段 |
| check_result | str | yes | continuous verifier CHECK_RESULT 值 |
| continuous_run_report_path | str | yes | continuous run report 文件路径 |
| changed_files | list[str] | yes | git status --short 获取的变更文件列表 |
| explicitly_allowed_paths | list[str] | no | 当前任务明确允许的额外路径 |
| explicitly_forbidden_paths | list[str] | no | 当前任务明确禁止的额外路径 |
| commit_message_proposal | str | no | 建议 commit message（不提供则自动生成） |
| approval_mode | str | yes | 审批模式：require_user_approval / dry_run / auto_approved |

### 4.2 输入来源

```text
repo_root → PROJECT_ROOT
task_id → 从 task_monitor 获取
expected_next_pending → 从 task_monitor 获取
expected_next_stage → 从 task_monitor 获取
check_result → 从 continuous run report 读取
continuous_run_report_path → reports/continuous-runs/Txxx-run-report.md
changed_files → 从 git status --short 获取
explicitly_allowed_paths → 当前任务配置
explicitly_forbidden_paths → 当前任务配置
commit_message_proposal → 可选，默认自动生成
approval_mode → 默认 require_user_approval
```

---

## 5. GitBackupGateResult Data Structure

### 5.1 Python Dataclass 草案

```python
from dataclasses import dataclass, field

@dataclass
class GitBackupGateResult:
    """GitBackupGate 输出结果。"""

    # 基本信息
    project_root: str
    gate_timestamp: str
    task_id: str
    stage: str

    # 检查结果
    check_result_pass: bool           # CHECK_RESULT 是否为 pass
    continuous_report_exists: bool    # continuous run report 是否存在
    worktree_status: str              # clean / dirty

    # 文件分类
    changed_files: list[str]          # 所有变更文件
    allowed_files: list[str]          # 允许提交的文件
    forbidden_files: list[str]        # 禁止提交的文件
    unclassified_files: list[str]     # 未分类文件

    # 决策
    ok: bool                          # gate 是否通过
    commit_allowed: bool              # 是否允许 commit
    push_allowed: bool                # 是否允许 push
    approval_required: bool           # 是否需要人工审批

    # Commit 信息
    commit_message: str               # commit message（最终版）
    git_add_commands: list[str]       # 建议的 git add 命令列表

    # 备份记录
    backup_record_path: str           # 备份记录路径

    # 失败
    fail_reason: str | None           # 失败原因（None 表示成功）
    next_action: str                  # proceed_to_commit / no_changes / stop

    # 安全保证
    gate_modified_files: bool = False # 始终 False，gate 只读不写
```

### 5.2 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| ok | bool | gate 是否通过（所有条件满足时为 True） |
| commit_allowed | bool | 是否允许 commit（ok=True 时为 True） |
| push_allowed | bool | 是否允许 push（commit_allowed=True 且 approval 通过时为 True） |
| approval_required | bool | 是否需要人工审批（始终 True，除非 dry_run 模式） |
| git_add_commands | list[str] | 建议的 git add 命令（每个文件一条） |
| fail_reason | str \| None | 失败原因，None 表示成功 |
| next_action | str | proceed_to_commit / no_changes / stop |
| gate_modified_files | bool | 始终 False，gate 只读不写 |

### 5.3 输出规则

```text
ok=True 的条件（全部满足）：
  - check_result_pass = True
  - continuous_report_exists = True
  - forbidden_files 为空
  - unclassified_files 为空
  - allowed_files 非空
  - fail_reason = None

ok=False 的条件（任一满足）：
  - check_result_pass = False
  - continuous_report_exists = False
  - forbidden_files 非空
  - unclassified_files 非空
  - allowed_files 为空
  - fail_reason 非空
```

---

## 6. File Classification Rules

### 6.1 Allowed Files

以下文件默认允许提交（但需与当前 task_id 匹配）：

| 类别 | 路径模式 | 说明 |
|------|----------|------|
| 任务文件 | docs/tasks.md | 任务状态更新 |
| 开发报告 | reports/dev/T{task_id}-dev-report.md | 当前任务开发报告 |
| 验证报告 | reports/checks/T{task_id}-*.md | 当前任务验证报告 |
| 连续运行报告 | reports/continuous-runs/T{task_id}-run-report.md | 当前任务连续运行报告 |
| 归档文档 | docs/archive/*.md | 归档文档 |
| Stage 文档 | docs/stage*.md | Stage 设计文档 |
| Git 备份记录 | reports/git/T{task_id}-git-backup-record.md | Git 备份记录 |
| Stage 8 报告 | reports/stage8/*.md | Stage 8 相关报告 |

额外允许条件：
- explicitly_allowed_paths 中列出的路径。
- 路径必须与当前 task_id 明确相关。

**重要**：只有当前任务明确允许的文件才可以进入 allowed。不在上述白名单中且不在 explicitly_allowed_paths 中的文件，需要进一步判断。

### 6.2 Forbidden Files

以下文件始终禁止提交：

| 类别 | 路径/模式 | 说明 |
|------|-----------|------|
| Git 内部 | .git/** | Git 内部文件 |
| 环境变量 | .env, .env.*, *.env | 环境变量文件 |
| 密钥 | *.pem, *.key, *.p12, *.pfx | 证书和密钥 |
| SSH 密钥 | id_rsa, id_ed25519 | SSH 密钥 |
| 敏感文件 | *secret*, *token*, *credential*, *password* | 敏感信息文件 |
| CI/CD 配置 | .github/** | 除非在 explicitly_allowed_paths 中 |
| 框架核心 | runner.py | 除非在 explicitly_allowed_paths 中 |
| 工具模块 | tools/*.py | 除非在 explicitly_allowed_paths 中 |
| 业务代码 | 业务代码目录 | 除非在 explicitly_allowed_paths 中 |
| 包管理 | package.json, pyproject.toml, requirements.txt | 除非在 explicitly_allowed_paths 中 |
| 二进制 | *.pyc, *.pyo, *.so, *.dll, *.exe | 编译产物 |

额外禁止条件：
- explicitly_forbidden_paths 中列出的路径。
- 即使在 explicitly_allowed_paths 中，如果同时匹配 forbidden 模式（如 .env），仍然 forbidden。

### 6.3 Unclassified Files

任何既不在 allowed，也不在 forbidden 列表中，且无法归属当前任务的文件，都必须归入 unclassified。

**处理规则**：

- 只要 unclassified_files 非空，GitBackupGate 必须 fail closed。
- fail_reason 包含 "unclassified_files_detected"。
- next_action = "stop"。
- 不允许静默跳过 unclassified files。
- 不允许将 unclassified files 自动归入 allowed。

---

## 7. Decision Rules

### 7.1 commit_allowed 判断

| # | 条件 | 结果 |
|---|------|------|
| 1 | check_result != "pass" | commit_allowed = False |
| 2 | continuous run report 缺失 | commit_allowed = False |
| 3 | changed_files 为空 | commit_allowed = False, next_action = "no_changes" |
| 4 | forbidden_files 非空 | commit_allowed = False |
| 5 | unclassified_files 非空 | commit_allowed = False |
| 6 | allowed_files 为空 | commit_allowed = False |
| 7 | 以上全部不满足 | commit_allowed = True |

### 7.2 push_allowed 判断

| # | 条件 | 结果 |
|---|------|------|
| 1 | commit_allowed = False | push_allowed = False |
| 2 | approval_required = True 且未审批 | push_allowed = False |
| 3 | 没有 approval record | push_allowed = False |
| 4 | 以上全部不满足 | push_allowed = True |

push_allowed 必须依赖 commit_allowed。commit 不允许则 push 也不允许。

### 7.3 approval_required 判断

| # | approval_mode | approval_required |
|---|---------------|-------------------|
| 1 | require_user_approval | True |
| 2 | dry_run | False（dry-run 不需要审批） |
| 3 | auto_approved | False（保留但当前阶段不使用） |

当前阶段建议默认使用 require_user_approval。

### 7.4 fail closed 策略

所有失败情况都必须 fail closed：

- 不允许静默跳过检查。
- 不允许将 fail 降级为 warning。
- 不允许自动重试。
- fail_reason 必须明确说明失败原因。
- next_action 必须为 "stop"。

---

## 8. Git Add Command Policy

### 8.1 策略规则

| # | 规则 | 说明 |
|---|------|------|
| 1 | 只允许逐个 git add allowed_files | 每个 allowed_file 一条命令 |
| 2 | 禁止 git add . | 不允许全目录 add |
| 3 | 禁止 git add -A | 不允许全目录 add |
| 4 | 禁止 git add --all | 不允许全目录 add |
| 5 | 禁止把 cd 与 git add 合并 | 所有命令独立执行 |
| 6 | git add 命令必须由 approval record 明确列出 | 未列出的不允许 add |
| 7 | git add 前必须检查 git status --short | 确认变更文件 |
| 8 | git add 后必须检查 git diff --cached --name-only | 确认暂存区 |

### 8.2 git_add_commands 生成规则

```text
对于 allowed_files 中的每个文件 file：
  git add {file}

示例：
  git add docs/tasks.md
  git add reports/dev/T167-dev-report.md
  git add docs/stage9-git-backup-gate-design.md
```

不允许生成复合命令。

---

## 9. Commit Message Policy

### 9.1 生成规则

| 任务类型 | 前缀 | 示例 |
|----------|------|------|
| 文档任务 | docs: | docs: add stage 9 git backup gate design |
| 功能任务 | feat: | feat: add git backup gate dry-run |
| 修复任务 | fix: | fix: correct file classification rule |
| 验证任务 | test: | test: validate git backup gate fail closed |
| 归档任务 | docs: archive | docs: archive stage 9 git backup results |

### 9.2 约束

| # | 约束 | 说明 |
|---|------|------|
| 1 | commit message 必须从任务类型生成 | 不允许随意填写 |
| 2 | commit message 必须简短明确 | 建议不超过 80 字符 |
| 3 | commit message 不允许包含 secret | 安全检查 |
| 4 | commit message 不允许为空 | 必须有内容 |
| 5 | commit message 不允许声明未完成的能力 | 如 "auto push completed" |
| 6 | commit message 不允许包含 unsafe patterns | real_execution_completed, auto_continue 等 |

### 9.3 自动生成逻辑

```text
如果提供了 commit_message_proposal：
  使用 commit_message_proposal（需通过 unsafe pattern 检查）
否则：
  根据任务角色生成：
    Developer → feat: <简短描述>
    Validator → test: <简短描述>
    Architect → docs: <简短描述>
    Reviewer → docs: <简短描述>
    Archivist → docs: archive <简短描述>
    Planner → docs: plan <简短描述>
    Bugfix Agent → fix: <简短描述>
```

---

## 10. Backup Record Design

### 10.1 路径

```text
reports/git/Txxx-git-backup-record.md
```

### 10.2 记录内容

```markdown
# Txxx Git Backup Record

## 1. Task Info

| Field | Value |
|-------|-------|
| TASK | Txxx |
| GATE_TIMESTAMP | YYYY-MM-DDTHH:MM:SS |
| STAGE | Stage 9 |

## 2. Gate Result

| Field | Value |
|-------|-------|
| GIT_BACKUP_GATE_RESULT | pass/fail |
| CHECK_RESULT | pass/fail |
| COMMIT_ALLOWED | true/false |
| PUSH_ALLOWED | true/false |
| APPROVAL_REQUIRED | true/false |

## 3. File Classification

| Field | Value |
|-------|-------|
| CHANGED_FILES | [...] |
| ALLOWED_FILES | [...] |
| FORBIDDEN_FILES | [...] |
| UNCLASSIFIED_FILES | [...] |

## 4. Commit Info

| Field | Value |
|-------|-------|
| COMMIT_MESSAGE | ... |
| GIT_ADD_COMMANDS | [...] |

## 5. Execution Status

| Field | Value |
|-------|-------|
| COMMIT_STATUS | pending/done/failed/skipped |
| PUSH_STATUS | pending/done/failed/skipped |
| LAST_COMMIT | xxxxxxx |
| WORKTREE_STATUS | clean/dirty |

## 6. Final Status

| Field | Value |
|-------|-------|
| NEXT_PENDING | Txxx |
| NEXT_STAGE | Stage N |
```

### 10.3 生成时机

- GitBackupGate 运行后立即生成（包含 gate result 和 file classification）。
- commit 成功后更新 COMMIT_STATUS。
- push 成功后更新 PUSH_STATUS 和 LAST_COMMIT。

---

## 11. Fail Closed Scenarios

以下情况必须 fail closed：

| # | 场景 | fail_reason |
|---|------|-------------|
| 1 | docs/tasks.md 缺失 | tasks_md_not_found |
| 2 | continuous run report 缺失 | continuous_report_missing |
| 3 | CHECK_RESULT 不是 pass | check_result_not_pass |
| 4 | forbidden files 检测到 | forbidden_files_detected |
| 5 | unclassified files 检测到 | unclassified_files_detected |
| 6 | dirty workspace 与 expected changed files 不匹配 | unexpected_dirty_workspace |
| 7 | staged files 已包含未预期路径 | unexpected_staged_files |
| 8 | commit message 无效 | commit_message_invalid |
| 9 | approval record 缺失 | approval_record_missing |
| 10 | approval_required 但未审批 | approval_not_granted |
| 11 | git status 命令失败 | git_status_failed |
| 12 | git diff 命令失败 | git_diff_failed |

每种失败场景都必须：
- ok = False
- commit_allowed = False
- push_allowed = False
- fail_reason 明确说明原因
- next_action = "stop"
- 不允许静默继续

---

## 12. Suggested T168 Implementation Scope

T168 应只实现 dry-run：

| # | 范围 | 说明 |
|---|------|------|
| 1 | 创建 tools/git_backup_gate.py | 新文件 |
| 2 | 实现 run_git_backup_gate() | 核心函数 |
| 3 | 实现文件分类函数 | classify_changed_files() |
| 4 | 实现 commit message 生成 | generate_commit_message() |
| 5 | 实现 GitBackupGateResult | dataclass |
| 6 | 不执行 git add | 只读判断 |
| 7 | 不执行 git commit | 只读判断 |
| 8 | 不执行 git push | 只读判断 |
| 9 | 只输出 GitBackupGateResult | 到 stdout |
| 10 | 只生成或建议 approval record | 不执行真实操作 |
| 11 | 使用 Python 标准库 | 不引入新依赖 |
| 12 | 保持 fail closed | 所有异常情况 stop |

T168 不修改 runner.py，不接入 run-project-loop。

---

## 13. Acceptance Criteria

T167 完成标准：

| # | 标准 | 状态 |
|---|------|------|
| 1 | GitBackupGate 设计文档已创建 | done |
| 2 | GitBackupGateResult 数据结构已明确 | done |
| 3 | 文件分类规则（allowed / forbidden / unclassified）已明确 | done |
| 4 | commit_allowed / push_allowed / approval_required 判断规则已明确 | done |
| 5 | fail closed 规则已明确（12 种场景） | done |
| 6 | git add / commit / push 策略已明确 | done |
| 7 | commit message 生成规则已明确 | done |
| 8 | backup record 格式已明确 | done |
| 9 | T168 dry-run 实现范围已明确 | done |
| 10 | 未实现 Python 代码 | confirmed |
| 11 | 未修改 runner.py | confirmed |
| 12 | 未修改 tools/ | confirmed |
| 13 | NEXT_PENDING=T168 | confirmed |
| 14 | NEXT_STAGE=Stage 9 | confirmed |

---

```text
DESIGN_STATUS=done
GIT_BACKUP_GATE_RESULT_FIELDS=14
FILE_CLASSIFICATION_CATEGORIES=3
FAIL_CLOSED_SCENARIOS=12
GIT_ADD_RULES=8
COMMIT_MESSAGE_TYPES=5
BACKUP_RECORD_FIELDS=18
T168_SCOPE_ITEMS=12
PYTHON_CODE_IMPLEMENTED=no
RUNNER_MODIFIED=no
TOOLS_MODIFIED=no
NEXT_PENDING=T168
NEXT_STAGE=Stage 9
```
