# T168 Dev Report：实现 git_backup_gate.py dry-run

## 基本信息

- TASK=T168
- ROLE=Dev Agent + Stage 9 Git Backup Gate Dry-run Implementer
- DATE=2026-05-11
- PROJECT_ROOT=E:/github_project/multi-agent-runner
- LAST_COMMIT=343180f docs: design stage 9 git backup gate

## 实现目标

实现 Stage 9 的 GitBackupGate dry-run 模块 tools/git_backup_gate.py。

## git_backup_gate.py 主要功能

### 核心数据结构

GitBackupGateResult 数据类，包含 14 个字段：

1. project_root — 项目根路径
2. gate_timestamp — gate 运行时间戳
3. task_id — 任务编号
4. check_result_pass — CHECK_RESULT 是否为 pass
5. continuous_report_exists — continuous run report 是否存在
6. worktree_status — 工作区状态（clean / dirty）
7. changed_files — 所有变更文件
8. allowed_files — 允许提交的文件
9. forbidden_files — 禁止提交的文件
10. unclassified_files — 未分类文件
11. ok — gate 是否通过
12. commit_allowed — 是否允许 commit
13. push_allowed — 是否允许 push
14. approval_required — 是否需要人工审批
15. commit_message — commit message
16. git_add_commands — 建议的 git add 命令列表
17. backup_record_path — 备份记录路径
18. fail_reason — 失败原因
19. next_action — proceed_to_commit / no_changes / stop
20. gate_modified_files — 始终 False，gate 只读不写

### 核心函数

1. read_text_file(path) — 读取文本文件
2. get_git_changed_files(repo_root) — 通过 git status --short 获取变更文件
3. normalize_paths(paths) — 规范化路径列表
4. classify_changed_files(changed_files, allowed, forbidden) — 分类变更文件
5. build_git_add_commands(allowed_files) — 生成逐个文件的 git add 命令
6. validate_commit_message(message) — 校验 commit message
7. run_git_backup_gate_dry_run(...) — 核心函数，执行 dry-run
8. print_result(result) — 格式化输出

### 文件分类规则

#### Allowed Files

- explicitly_allowed_paths 中列出的文件

#### Forbidden Files（默认规则）

- .git/、.env、.env.local、.env.production
- secrets、secret、api_key
- .github/、requirements.txt、package.json、pyproject.toml
- .pem、.key、.p12、.pfx、id_rsa、id_ed25519
- token、credential、password
- .pyc、.pyo、.so、.dll、.exe
- runner.py（精确匹配）
- explicitly_forbidden_paths 中列出的文件

#### Unclassified Files

- 不在 allowed 也不在 forbidden 的文件
- 存在时必须 fail closed

### fail closed 规则

按顺序检查，任一不通过立即返回 fail：

1. check_result != pass → check_result_not_pass
2. continuous_report 不存在 → continuous_report_missing
3. git status 失败 → git_status_failed
4. changed_files 为空 → no_changes
5. forbidden_files 非空 → forbidden_files_detected
6. unclassified_files 非空 → unclassified_files_detected
7. allowed_files 为空 → no_allowed_files
8. commit_message 无效 → commit_message_invalid

全部通过时：ok=True, commit_allowed=True, next_action=proceed_to_commit。

## dry-run 自检

### 基础 dry-run（第 9 步）

命令：

```
python tools/git_backup_gate.py --task T168 --check-result pass --report docs/stage9-git-backup-gate-design.md --commit-message "feat: add stage 9 git backup gate dry run" --allowed tools/git_backup_gate.py --allowed docs/tasks.md --approval-mode require_user_approval
```

结果：GIT_BACKUP_GATE_RESULT=pass
- CHANGED_FILES=['tools/git_backup_gate.py']
- ALLOWED_FILES=['tools/git_backup_gate.py']
- COMMIT_ALLOWED=yes
- APPROVAL_REQUIRED=yes
- NEXT_ACTION=proceed_to_commit

### 最终 dry-run（第 12 步）

命令：

```
python tools/git_backup_gate.py --task T168 --check-result pass --report reports/dev/T168-dev-report.md --commit-message "feat: add stage 9 git backup gate dry run" --allowed tools/git_backup_gate.py --allowed reports/dev/T168-dev-report.md --allowed docs/tasks.md --approval-mode require_user_approval
```

结果：T168 原始执行中因 API 429 在第 15 步中断。本次 resume 恢复后补跑成功。

```
GIT_BACKUP_GATE_RESULT=pass
TASK=T168
CHECK_RESULT_PASS=yes
CONTINUOUS_REPORT_EXISTS=yes
WORKTREE_STATUS=dirty
CHANGED_FILES=['docs/tasks.md', 'reports/dev/T168-dev-report.md', 'tools/git_backup_gate.py']
ALLOWED_FILES=['docs/tasks.md', 'reports/dev/T168-dev-report.md', 'tools/git_backup_gate.py']
FORBIDDEN_FILES=[]
UNCLASSIFIED_FILES=[]
COMMIT_ALLOWED=yes
PUSH_ALLOWED=no
APPROVAL_REQUIRED=yes
COMMIT_MESSAGE=feat: add stage 9 git backup gate dry run
GIT_ADD_COMMANDS=['git add docs/tasks.md', 'git add reports/dev/T168-dev-report.md', 'git add tools/git_backup_gate.py']
BACKUP_RECORD_PATH=reports/git/T168-git-backup-record.md
NEXT_ACTION=proceed_to_commit
GATE_MODIFIED_FILES=no
```

## 是否出现 expected fail closed

基础 dry-run 未出现 fail closed，因为只有 tools/git_backup_gate.py 一个变更文件，已列入 --allowed。

最终 dry-run 也未出现 fail closed，3 个 changed files 全部在 allowed 列表中。

## API 429 恢复说明

T168 原始执行在第 15 步（git diff -- tools/git_backup_gate.py）时触发 API 429 中断。恢复时确认：
- tools/git_backup_gate.py 已创建且完整。
- reports/dev/T168-dev-report.md 已创建但最终 dry-run 结果缺失。
- docs/tasks.md 已正确更新（T168 done, NEXT_PENDING=T169）。
- 未执行 git add/commit/push。

恢复操作：补跑 py_compile（pass）、补跑最终 dry-run（pass）、补充 dev report 中最终 dry-run 结果和恢复说明。

## 未修改的文件

- runner.py：未修改
- tools/task_monitor.py：未修改
- tools/continuous_verifier.py：未修改
- tools/execution_report_writer.py：未修改
- 业务代码：未修改

## 未执行的操作

- 未执行 git add
- 未执行 git commit
- 未执行 git push
- 未创建 reports/git/ 目录
- 未创建 T168-git-backup-record.md
- 未生成 approval record
- 未接入 run-project-loop
- 未调用 Claude Agent SDK

## 安全保证

- TASK=T168
- IMPLEMENTATION_STATUS=done
- BUSINESS_CODE_CHANGED=no
- FRAMEWORK_CODE_CHANGED=yes
- RUNNER_CHANGED=no
- TOOLS_CHANGED=yes
- REAL_EXECUTION_CHANGED=no
- CLAUDE_AGENT_SDK_INTEGRATED=no
- GIT_BACKUP_GATE_IMPLEMENTED=yes
- DRY_RUN_IMPLEMENTED=yes
- AUTO_GIT_BACKUP_IMPLEMENTED=no
- REAL_GIT_ADD_EXECUTED=no
- REAL_GIT_COMMIT_EXECUTED=no
- REAL_GIT_PUSH_EXECUTED=no
- PY_COMPILE_STATUS=pass
- DRY_RUN_SELF_CHECK=pass（resume 恢复后补跑通过）
- CHECK_RESULT=pass
- NEXT_PENDING=T169
- NEXT_STAGE=Stage 9

## 文件清单

### 本次新增文件

- tools/git_backup_gate.py
- reports/dev/T168-dev-report.md

### 本次修改文件

- docs/tasks.md（T168 done，NEXT_PENDING → T169）

## 最终状态

```
TASK=T168
IMPLEMENTATION_STATUS=done
FILES_CREATED=tools/git_backup_gate.py, reports/dev/T168-dev-report.md
FILES_MODIFIED=docs/tasks.md
BUSINESS_CODE_CHANGED=no
FRAMEWORK_CODE_CHANGED=yes
RUNNER_CHANGED=no
TOOLS_CHANGED=yes
REAL_EXECUTION_CHANGED=no
CLAUDE_AGENT_SDK_INTEGRATED=no
GIT_BACKUP_GATE_IMPLEMENTED=yes
DRY_RUN_IMPLEMENTED=yes
AUTO_GIT_BACKUP_IMPLEMENTED=no
REAL_GIT_ADD_EXECUTED=no
REAL_GIT_COMMIT_EXECUTED=no
REAL_GIT_PUSH_EXECUTED=no
PY_COMPILE_STATUS=pass
DRY_RUN_SELF_CHECK=pass
CHECK_RESULT=pass
NEXT_PENDING=T169
NEXT_STAGE=Stage 9
```
