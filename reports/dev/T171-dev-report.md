# T171 Dev Report：接入 guarded git backup dry-run 到 run-project-loop

## 基本信息

- TASK=T171
- ROLE=Dev Agent + Stage 9 Guarded Git Backup Integration Implementer
- DATE=2026-05-12
- PROJECT_ROOT=E:/github_project/multi-agent-runner
- LAST_COMMIT=e98a21b feat: generate stage 9 git backup approval record
- 备注：本次从网络中断点恢复，跳过已完成的前置确认步骤

## 实现目标

在 runner.py 的 stage8-monitor-verify-report pipeline 后端接入 GitBackupGate dry-run。

## runner.py 修改点

### 修改位置

runner.py `stage8-monitor-verify-report` 子命令，Step 4（Report）Final Output 区域之后。

### 修改内容

在 `AUTO_PUSH_TRIGGERED=no` 输出后、`NEXT_ACTION=stop` 输出前，追加 Step 5: GitBackupGate dry-run。

### 具体逻辑

1. 只在 `overall_pass=True` 时运行 Step 5
2. 使用延迟导入（在 if 分支内 import），不增加顶部 import 依赖
3. 调用 `tools.git_backup_gate.run_git_backup_gate_dry_run`
4. 使用 report 的 task_id、check_result="pass"、continuous_run_report_path=report_path 作为输入
5. 如果 dry-run pass，调用 `write_git_backup_approval_record` 写入 approval record
6. 输出结构化字段：GIT_BACKUP_DRY_RUN、GATE_OK、COMMIT_ALLOWED、PUSH_ALLOWED、APPROVAL_REQUIRED
7. 输出 GIT_BACKUP_APPROVAL_RECORD_CREATED、GIT_BACKUP_APPROVAL_RECORD_PATH
8. 始终输出 REAL_GIT_ADD_EXECUTED=no、REAL_GIT_COMMIT_EXECUTED=no、REAL_GIT_PUSH_EXECUTED=no
9. 异常时 fail closed，输出 GIT_BACKUP_DRY_RUN=error

### 未改变的内容

- Step 1 Monitor：未改变
- Step 2 Trial：未改变
- Step 3 Verifier：未改变
- Step 4 Report：未改变
- max_tasks=1 安全边界：未改变
- max_tasks>1 fail closed：未改变
- AUTO_COMMIT_TRIGGERED=no：未改变
- AUTO_PUSH_TRIGGERED=no：未改变

## GitBackupGate dry-run 如何接入

1. runner.py 通过延迟导入 `tools.git_backup_gate` 中的 `run_git_backup_gate_dry_run` 和 `write_git_backup_approval_record`
2. 在 stage8-monitor-verify-report pipeline 的 Step 4 Report 完成后
3. 只在 overall_pass=True 时运行
4. 使用 report_data.task_id 作为 task_id
5. 使用 report_result.report_path 作为 continuous_run_report_path
6. explicitly_allowed_paths 和 explicitly_forbidden_paths 传入空列表（由 gate 自动分类）
7. commit_message 自动生成
8. approval_mode 固定为 require_user_approval

## Approval record 如何生成

1. 当 GitBackupGate dry-run pass 时，调用 write_git_backup_approval_record
2. 写入路径：reports/git/{task_id}-git-backup-approval-record.md
3. approval record 包含 10 个章节（Gate Result、Changed Files、Allowed/Forbidden/Unclassified Files、Proposed Git Add Commands、Proposed Commit Message、Approval Requirement、Commit and Push Decision、Safety Notes）

## 为什么没有执行真实 Git backup

- T171 是代码接入任务，不是验证任务
- 只将 GitBackupGate dry-run 接入 runner.py pipeline
- 不执行真实 git add / commit / push
- 真实验证留给 T172

## 为什么没有执行 run-project-loop real execution

- T171 只验证 plan-project-loop 输出（确认 NEXT_PENDING=T171）
- 不执行 stage8-monitor-verify-report（那属于 T172 验证范围）
- 不执行 run-project-loop --real-execution

## 未修改的文件

- tools/git_backup_gate.py：未修改
- tools/task_monitor.py：未修改
- tools/continuous_verifier.py：未修改
- tools/execution_report_writer.py：未修改
- 业务代码：未修改

## 安全保证

- TASK=T171
- IMPLEMENTATION_STATUS=done
- BUSINESS_CODE_CHANGED=no
- FRAMEWORK_CODE_CHANGED=yes
- RUNNER_CHANGED=yes
- TOOLS_CHANGED=no
- REAL_EXECUTION_CHANGED=guarded_git_backup_dry_run_only
- CLAUDE_AGENT_SDK_INTEGRATED=no
- GIT_BACKUP_DRY_RUN_INTEGRATED=yes
- APPROVAL_RECORD_GENERATION_INTEGRATED=yes
- AUTO_GIT_BACKUP_IMPLEMENTED=no
- REAL_GIT_ADD_EXECUTED=no
- REAL_GIT_COMMIT_EXECUTED=no
- REAL_GIT_PUSH_EXECUTED=no
- RUN_PROJECT_LOOP_REAL_EXECUTED=no
- PY_COMPILE_STATUS=pass
- CHECK_RESULT=pass
- NEXT_PENDING=T172
- NEXT_STAGE=Stage 9

## 文件清单

### 本次新增文件

- reports/dev/T171-dev-report.md

### 本次修改文件

- runner.py（追加 Step 5 GitBackupGate dry-run）
- docs/tasks.md（T171 done，NEXT_PENDING → T172）

## T172 将负责验证

T172 将验证完整的 monitor → verify → report → git backup gate pipeline dry-run，包括：
1. stage8-monitor-verify-report --max-tasks 1 完整执行
2. Step 5 GitBackupGate dry-run 是否正确触发
3. approval record 是否正确生成
4. fail closed 场景是否正确工作

## 最终状态

```
TASK=T171
IMPLEMENTATION_STATUS=done
FILES_CREATED=reports/dev/T171-dev-report.md
FILES_MODIFIED=runner.py, docs/tasks.md
BUSINESS_CODE_CHANGED=no
FRAMEWORK_CODE_CHANGED=yes
RUNNER_CHANGED=yes
TOOLS_CHANGED=no
REAL_EXECUTION_CHANGED=guarded_git_backup_dry_run_only
CLAUDE_AGENT_SDK_INTEGRATED=no
GIT_BACKUP_DRY_RUN_INTEGRATED=yes
APPROVAL_RECORD_GENERATION_INTEGRATED=yes
AUTO_GIT_BACKUP_IMPLEMENTED=no
REAL_GIT_ADD_EXECUTED=no
REAL_GIT_COMMIT_EXECUTED=no
REAL_GIT_PUSH_EXECUTED=no
RUN_PROJECT_LOOP_REAL_EXECUTED=no
PY_COMPILE_STATUS=pass
CHECK_RESULT=pass
NEXT_PENDING=T172
NEXT_STAGE=Stage 9
```
