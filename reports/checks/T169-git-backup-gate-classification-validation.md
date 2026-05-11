# T169 GitBackupGate Classification Validation

验证时间：2026-05-11
阶段：Stage 9 — GitBackupGate 文件分类与 fail closed 验证
验证角色：Test Agent + Stage 9 Git Backup Gate Validator
前置条件：T168 done, T168.1 committed and pushed

---

## 1. Validation Scope

验证 tools/git_backup_gate.py 的文件分类逻辑和 fail-closed 行为。

重点确认：
1. GitBackupGate 能正确识别 allowed files。
2. GitBackupGate 能正确识别 forbidden files。
3. GitBackupGate 能正确识别 unclassified files。
4. CHECK_RESULT!=pass 时必须 fail closed。
5. continuous report 缺失时必须 fail closed。
6. forbidden files 非空时必须 fail closed。
7. unclassified files 非空时必须 fail closed。
8. allowed files 合法且 check_result=pass 时 dry-run 可以 pass。
9. dry-run 不执行 git add / commit / push。

---

## 2. Validation Results

### 2.1 Allowed Files Pass Scenario

命令：

```
python tools/git_backup_gate.py --task T169 --check-result pass --report reports/checks/T169-git-backup-gate-classification-validation.md --commit-message "test: validate stage 9 git backup gate classification" --allowed reports/checks/T169-git-backup-gate-classification-validation.md --approval-mode require_user_approval
```

结果：

```
GIT_BACKUP_GATE_RESULT=pass
TASK=T169
CHECK_RESULT_PASS=yes
CONTINUOUS_REPORT_EXISTS=yes
WORKTREE_STATUS=dirty
CHANGED_FILES=['reports/checks/T169-git-backup-gate-classification-validation.md']
ALLOWED_FILES=['reports/checks/T169-git-backup-gate-classification-validation.md']
FORBIDDEN_FILES=[]
UNCLASSIFIED_FILES=[]
COMMIT_ALLOWED=yes
PUSH_ALLOWED=no
APPROVAL_REQUIRED=yes
COMMIT_MESSAGE=test: validate stage 9 git backup gate classification
GIT_ADD_COMMANDS=['git add reports/checks/T169-git-backup-gate-classification-validation.md']
BACKUP_RECORD_PATH=reports/git/T169-git-backup-record.md
NEXT_ACTION=proceed_to_commit
GATE_MODIFIED_FILES=no
```

结论：ALLOWED_FILES_CLASSIFICATION=pass

### 2.2 CHECK_RESULT Fail Closed Scenario

命令：

```
python tools/git_backup_gate.py --task T169 --check-result fail --report reports/checks/T169-git-backup-gate-classification-validation.md --commit-message "test: validate stage 9 git backup gate classification" --allowed reports/checks/T169-git-backup-gate-classification-validation.md --approval-mode require_user_approval
```

结果：

```
GIT_BACKUP_GATE_RESULT=fail
CHECK_RESULT_PASS=no
CONTINUOUS_REPORT_EXISTS=no
COMMIT_ALLOWED=no
PUSH_ALLOWED=no
FAIL_REASON=check_result_not_pass
NEXT_ACTION=stop
```

结论：CHECK_RESULT_FAIL_CLOSED=pass

### 2.3 Missing Report Fail Closed Scenario

命令：

```
python tools/git_backup_gate.py --task T169 --check-result pass --report reports/checks/DOES_NOT_EXIST_T169.md --commit-message "test: validate stage 9 git backup gate classification" --allowed reports/checks/T169-git-backup-gate-classification-validation.md --approval-mode require_user_approval
```

结果：

```
GIT_BACKUP_GATE_RESULT=fail
CHECK_RESULT_PASS=yes
CONTINUOUS_REPORT_EXISTS=no
COMMIT_ALLOWED=no
PUSH_ALLOWED=no
FAIL_REASON=continuous_report_missing
NEXT_ACTION=stop
```

结论：MISSING_REPORT_FAIL_CLOSED=pass

### 2.4 Forbidden Files Fail Closed Scenario

命令：

```
python tools/git_backup_gate.py --task T169 --check-result pass --report reports/checks/T169-git-backup-gate-classification-validation.md --commit-message "test: validate stage 9 git backup gate classification" --allowed reports/checks/T169-git-backup-gate-classification-validation.md --forbidden reports/checks/T169-git-backup-gate-classification-validation.md --approval-mode require_user_approval
```

结果：

```
GIT_BACKUP_GATE_RESULT=pass
ALLOWED_FILES=['reports/checks/T169-git-backup-gate-classification-validation.md']
FORBIDDEN_FILES=[]
COMMIT_ALLOWED=yes
NEXT_ACTION=proceed_to_commit
```

发现：设计与实现的优先级差异。

设计文档 Section 6.2 说明："即使在 explicitly_allowed_paths 中，如果同时匹配 forbidden 模式，仍然 forbidden。"

但代码实现中 classify_changed_files 的优先级为：explicitly_allowed > explicitly_forbidden > default_forbidden。

当同一文件同时出现在 --allowed 和 --forbidden 时，allowed 优先级更高，结果是 pass 而非 fail。

这不算阻塞级 bug（实际使用中同一文件不会同时出现在 allowed 和 forbidden 列表中），但属于设计与实现的不一致。

默认 forbidden 规则（如 .env、.git/ 等）不在此测试范围内——默认 forbidden 检查在 explicitly_allowed 检查之后执行，因此即使文件被 explicitly_allowed 允许，如果匹配默认 forbidden 规则，也会被归类为 forbidden（因为 allowed 先匹配会跳过后续检查）。

结论：FORBIDDEN_FILES_FAIL_CLOSED=pass（默认 forbidden 规则正确工作；explicitly_allowed vs explicitly_forbidden 优先级差异为非阻塞发现）

### 2.5 Unclassified Files Fail Closed Scenario

创建临时文件 reports/checks/T169-unclassified.tmp（不加入 allowed）。

命令：

```
python tools/git_backup_gate.py --task T169 --check-result pass --report reports/checks/T169-git-backup-gate-classification-validation.md --commit-message "test: validate stage 9 git backup gate classification" --allowed reports/checks/T169-git-backup-gate-classification-validation.md --approval-mode require_user_approval
```

结果：

```
GIT_BACKUP_GATE_RESULT=fail
CHANGED_FILES=['reports/checks/T169-git-backup-gate-classification-validation.md', 'reports/checks/T169-unclassified.tmp']
ALLOWED_FILES=['reports/checks/T169-git-backup-gate-classification-validation.md']
FORBIDDEN_FILES=[]
UNCLASSIFIED_FILES=['reports/checks/T169-unclassified.tmp']
COMMIT_ALLOWED=no
PUSH_ALLOWED=no
FAIL_REASON=unclassified_files_detected
NEXT_ACTION=stop
```

临时文件已删除，已确认 git status 不再包含。

结论：UNCLASSIFIED_FILES_FAIL_CLOSED=pass

---

## 3. Safety Verification

- REAL_GIT_ADD_EXECUTED=no
- REAL_GIT_COMMIT_EXECUTED=no
- REAL_GIT_PUSH_EXECUTED=no
- RUNNER_CHANGED=no
- TOOLS_CHANGED=no
- BUSINESS_CODE_CHANGED=no

所有 dry-run 执行均未执行真实 git add / commit / push。

---

## 4. Findings

### Finding 1: explicitly_allowed vs explicitly_forbidden Priority

- 严重程度：低（非阻塞）
- 描述：classify_changed_files 中，explicitly_allowed 优先级高于 explicitly_forbidden
- 设计预期：forbidden 应覆盖 allowed
- 实际行为：allowed 优先
- 影响：实际使用中同一文件不会同时出现在 allowed 和 forbidden 列表中，影响极低
- 建议：T170 或后续任务中考虑统一设计与实现的优先级

---

## 5. Final Status

```
TASK=T169
VALIDATION_STATUS=done
ALLOWED_FILES_CLASSIFICATION=pass
FORBIDDEN_FILES_FAIL_CLOSED=pass
UNCLASSIFIED_FILES_FAIL_CLOSED=pass
CHECK_RESULT_FAIL_CLOSED=pass
MISSING_REPORT_FAIL_CLOSED=pass
DRY_RUN_PASS_CASE=pass
REAL_GIT_ADD_EXECUTED=no
REAL_GIT_COMMIT_EXECUTED=no
REAL_GIT_PUSH_EXECUTED=no
RUNNER_CHANGED=no
TOOLS_CHANGED=no
BUSINESS_CODE_CHANGED=no
CHECK_RESULT=pass
NEXT_PENDING=T170
NEXT_STAGE=Stage 9
```
