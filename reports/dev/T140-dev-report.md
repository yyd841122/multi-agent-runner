# T140 Dev Report：实现 real Git add/commit dry-run with approval record

## 本次目标

实现 T139 设计中的 real Git add/commit dry-run with approval record 能力：
- 新增 `RealGitAddCommitDryRunResult` 数据结构
- 新增 planned files 校验函数
- 新增 commit message 校验函数
- 新增 approval record 生成函数
- 新增 dry-run 主函数 `run_real_git_add_commit_dry_run`
- 新增 CLI 入口 `python runner.py git-commit-dry-run`
- 生成示例 approval record
- 不执行真实 git add / commit / push

## 修改文件

### 1. `tools/continuous_task_planner.py`

**改动目的**：新增 T140 dry-run 全部实现

**新增内容**：

- `RealGitAddCommitDryRunResult` dataclass：T140 dry-run 结果数据结构，包含 35+ 字段
- `SENSITIVE_FILE_PATTERNS`：敏感文件模式列表（.env, .pem, .key 等）
- `SENSITIVE_FILENAME_KEYWORDS`：敏感文件名关键词（secret, token, credential, password）
- `DEFAULT_ALLOWED_SCOPE`：默认允许的文件范围（docs/, reports/, memory/）
- `validate_planned_files_for_git_dry_run()`：planned files 安全校验函数
- `validate_commit_message_for_git_dry_run()`：commit message 安全校验函数
- `build_real_git_add_commit_approval_record_content()`：approval record Markdown 生成函数
- `run_real_git_add_commit_dry_run()`：dry-run 主函数，支持 15 个 sample 场景

### 2. `runner.py`

**改动目的**：新增 T140 CLI 入口

**新增内容**：

- import `run_real_git_add_commit_dry_run`
- CLI 入口 `git-commit-dry-run [--sample <name>]`
- 帮助文本条目

### 3. `reports/git/t140-real-git-add-commit-approval-record.md`（自动生成）

**改动目的**：pass 场景的示例 approval record

## 新增能力

1. **Planned files 校验**：检测敏感文件、Stage 8 相关文件、push 相关文件、二进制文件、out-of-scope 文件
2. **Commit message 校验**：检测空 message、task id 不匹配、unsafe patterns、real execution claims
3. **Approval record 生成**：YAML 格式的完整审批记录，包含 task/git/files/commit/safety/validation/decision 七大块
4. **16 个 gate checks**：分 5 组校验 dry-run 约束、文件校验、commit message、安全标志、强制失败场景
5. **15 个 sample 场景**：1 pass + 14 fail-closed

## Dry-run 行为

- `dry_run = True`
- `real_execution_allowed = False`
- `push_allowed = False`
- 不执行真实 `git add`
- 不执行真实 `git commit`
- 不执行真实 `git push`
- 不改变 Git 暂存区
- 只生成 approval record 文件

## 不执行真实 git add/commit/push 的证明

1. `run_real_git_add_commit_dry_run()` 函数内无 `subprocess` 调用
2. 无 `os.system` 调用
3. 无 `git add` / `git commit` / `git push` 命令字符串
4. 唯一的文件写入是 approval record（Markdown 文本文件）
5. 所有安全标志字段硬编码为安全值

## 运行命令

```powershell
# Pass 场景
python runner.py git-commit-dry-run --sample pass

# Fail 场景示例
python runner.py git-commit-dry-run --sample sensitive-file
python runner.py git-commit-dry-run --sample unsafe-commit-message
python runner.py git-commit-dry-run --sample real-execution-allowed-true
python runner.py git-commit-dry-run --sample push-allowed-true
python runner.py git-commit-dry-run --sample stage-8-requested
python runner.py git-commit-dry-run --sample git-add-requested
python runner.py git-commit-dry-run --sample git-commit-requested
python runner.py git-commit-dry-run --sample git-push-requested
python runner.py git-commit-dry-run --sample empty-commit-message
python runner.py git-commit-dry-run --sample mismatched-task-id
python runner.py git-commit-dry-run --sample real-execution-claim
python runner.py git-commit-dry-run --sample out-of-scope-file
python runner.py git-commit-dry-run --sample stage-8-file
python runner.py git-commit-dry-run --sample no-files
```

## Pass 场景输出结果

```
EXECUTION_MODE=real_git_add_commit_dry_run
TASK_ID=T140
APPROVAL_RECORD_GENERATED=yes
APPROVAL_RECORD_PATH=reports/git/t140-real-git-add-commit-approval-record.md
DRY_RUN=True
REAL_EXECUTION_ALLOWED=False
PUSH_ALLOWED=False
VALIDATION_REQUIRED=True
PLANNED_FILES_VALID=yes
COMMIT_MESSAGE_VALID=yes
CHECK_RESULT=pass
```

## 后续 T141 验证建议

1. 逐一运行 15 个 sample 场景，确认所有 fail 场景均输出 `CHECK_RESULT=fail`
2. 确认 pass 场景只生成 approval record，不执行真实 Git 操作
3. 确认 `real_execution_allowed` 始终为 `False`
4. 确认 `push_allowed` 始终为 `False`
5. 确认 `ready_for_stage_8` 始终为 `no`
6. 验证 sensitive-file 场景正确拒绝 `.env` 文件
7. 验证 unsafe-commit-message 场景拒绝 unsafe patterns
8. 验证 real-execution-claim 场景拒绝声称已执行的 commit message
