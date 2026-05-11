# T167 Dev Report：设计 GitBackupGate 数据结构与规则

## 基本信息

- TASK=T167
- ROLE=Architect Agent + Stage 9 Git Backup Gate Architect
- DATE=2026-05-11
- PROJECT_ROOT=E:/github_project/multi-agent-runner
- LAST_COMMIT=2fef26c docs: plan stage 9 git backup and execution record

## 设计目标

设计 Stage 9 的 GitBackupGate 数据结构与规则。

本任务是设计任务，不实现 Python 代码。

## 本次只做设计

本次只做设计，不实现任何代码，不创建 tools/git_backup_gate.py。

## GitBackupGate 的职责

GitBackupGate 在 continuous verifier pass 后运行，负责：

1. 读取任务执行结果和 continuous run report。
2. 检查 CHECK_RESULT 是否为 pass。
3. 检查 worktree 状态。
4. 分类 changed files（allowed / forbidden / unclassified）。
5. 生成 allowed files 列表。
6. 判断 commit_allowed / push_allowed / approval_required。
7. 生成 git add commands 和 commit message。
8. 输出 GitBackupGateResult。
9. fail closed。

## GitBackupGateResult 字段

共 14 个字段：

1. ok — gate 是否通过
2. task_id — 任务编号
3. changed_files — 所有变更文件
4. allowed_files — 允许提交的文件
5. forbidden_files — 禁止提交的文件
6. unclassified_files — 未分类文件
7. commit_allowed — 是否允许 commit
8. push_allowed — 是否允许 push
9. approval_required — 是否需要人工审批
10. git_add_commands — 建议的 git add 命令列表
11. commit_message — commit message（最终版）
12. backup_record_path — 备份记录路径
13. fail_reason — 失败原因
14. next_action — proceed_to_commit / no_changes / stop

## 文件分类规则

### Allowed Files

- docs/tasks.md
- reports/dev/T{task_id}-dev-report.md
- reports/checks/T{task_id}-*.md
- reports/continuous-runs/T{task_id}-run-report.md
- docs/archive/*.md
- docs/stage*.md
- reports/git/T{task_id}-git-backup-record.md
- 当前任务明确允许的额外路径

### Forbidden Files

- .git/**, .env, *.pem, *.key, *secret*, *token*
- runner.py（除非明确允许）
- tools/*.py（除非明确允许）
- 业务代码（除非明确允许）
- dependency files（除非明确允许）

### Unclassified Files

不在 allowed 也不在 forbidden 的文件。存在时必须 fail closed。

## fail closed 场景

共 12 种 fail closed 场景：

1. tasks_md_not_found
2. continuous_report_missing
3. check_result_not_pass
4. forbidden_files_detected
5. unclassified_files_detected
6. unexpected_dirty_workspace
7. unexpected_staged_files
8. commit_message_invalid
9. approval_record_missing
10. approval_not_granted
11. git_status_failed
12. git_diff_failed

## T168 dry-run 实现范围

T168 应实现：
1. 创建 tools/git_backup_gate.py
2. 实现 run_git_backup_gate() 核心函数
3. 实现文件分类函数
4. 实现 commit message 生成
5. 不执行真实 git 操作
6. 只输出 GitBackupGateResult
7. 使用 Python 标准库
8. 保持 fail closed

## 参考文档

1. docs/stage9-git-backup-and-execution-record-plan.md — Stage 9 规划
2. docs/stage7-real-git-add-commit-approval-gate-design.md — Stage 7 approval gate 设计
3. docs/archive/stage8-final-status-review.md — Stage 8 最终审查
4. docs/archive/stage7-git-commit-dry-run-archive.md — Stage 7 Git commit dry-run 归档

## 未修改的文件

- runner.py：未修改
- tools/task_monitor.py：未修改
- tools/continuous_verifier.py：未修改
- tools/execution_report_writer.py：未修改
- 业务代码：未修改

## 未执行的操作

- 未实现 git_backup_gate.py
- 未执行真实 Git backup
- 未自动 git add
- 未自动 git commit
- 未自动 git push
- 未调用 Claude Agent SDK
- 未进入 Stage 9 实施

## 安全保证

- TASK=T167
- DESIGN_STATUS=done
- BUSINESS_CODE_CHANGED=no
- FRAMEWORK_CODE_CHANGED=no
- RUNNER_CHANGED=no
- TOOLS_CHANGED=no
- REAL_EXECUTION_CHANGED=no
- CLAUDE_AGENT_SDK_INTEGRATED=no
- GIT_BACKUP_GATE_DESIGNED=yes
- GIT_BACKUP_GATE_IMPLEMENTED=no
- AUTO_GIT_BACKUP_IMPLEMENTED=no
- DRY_RUN_IMPLEMENTED=no
- AUTO_COMMIT_TRIGGERED=no
- AUTO_PUSH_TRIGGERED=no
- CHECK_RESULT=pass
- NEXT_PENDING=T168
- NEXT_STAGE=Stage 9

## 文件清单

### 本次新增文件

- docs/stage9-git-backup-gate-design.md
- reports/dev/T167-dev-report.md

### 本次修改文件

- docs/tasks.md（T167 done，NEXT_PENDING → T168）

## 最终状态

```
TASK=T167
DESIGN_STATUS=done
FILES_CREATED=docs/stage9-git-backup-gate-design.md, reports/dev/T167-dev-report.md
FILES_MODIFIED=docs/tasks.md
BUSINESS_CODE_CHANGED=no
FRAMEWORK_CODE_CHANGED=no
RUNNER_CHANGED=no
TOOLS_CHANGED=no
REAL_EXECUTION_CHANGED=no
CLAUDE_AGENT_SDK_INTEGRATED=no
GIT_BACKUP_GATE_DESIGNED=yes
GIT_BACKUP_GATE_IMPLEMENTED=no
AUTO_GIT_BACKUP_IMPLEMENTED=no
DRY_RUN_IMPLEMENTED=no
AUTO_COMMIT_TRIGGERED=no
AUTO_PUSH_TRIGGERED=no
CHECK_RESULT=pass
NEXT_PENDING=T168
NEXT_STAGE=Stage 9
```
