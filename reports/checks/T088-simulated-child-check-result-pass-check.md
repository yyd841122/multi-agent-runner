# T088 Simulated Child CHECK_RESULT Pass Check

## Goal

验证 child parser 能正确解析模拟子命令 `CHECK_RESULT=pass`，并确认 pass 后仍然停止等待人工验收。

## Commands

### CLI 样例验证

```bash
python runner.py parse-child-output-dry-run --sample pass
```

### 函数级验证

```python
from tools.continuous_task_planner import parse_child_command_output

stdout = '''TASK_ID=T088
CHECK_RESULT=pass
TASK_STATUS=done
NEXT_PENDING=T089
REAL_TASK_EXECUTION=yes
CLAUDE_CODE_CALLED=unknown
BUSINESS_CODE_CHANGED=yes
WORKTREE_STATUS=dirty_reports_only
REPORT_PATHS=reports/dev/T088-dev-report.md,reports/checks/T088-simulated-child-check-result-pass-check.md'''

result = parse_child_command_output(stdout)
```

## Expected Result

应满足：

- PARSE_STATUS=parsed
- PARSE_CHECK_RESULT=pass
- CHECK_RESULT=pass
- TASK_STATUS=done
- REPORT_PATHS 可解析（2 个路径）
- 缺失字段不应被错误标记为 no
- pass 后不自动进入下一任务
- pass 后不自动 Git 备份

## Actual Result

### CLI 样例验证（--sample pass）

| 字段 | 值 |
|------|------|
| PARSE_STATUS | parsed |
| PARSE_CHECK_RESULT | pass |
| RAW_STDOUT_PRESENT | True |
| EXIT_CODE | 0 |
| TASK_ID | G008 |
| CHECK_RESULT | pass |
| TASK_STATUS | done |
| NEXT_PENDING | G009 |
| REAL_TASK_EXECUTION | yes |
| CLAUDE_CODE_CALLED | yes |
| BUSINESS_CODE_CHANGED | yes |
| WORKTREE_STATUS | dirty_business_code |
| REPORT_PATHS | reports/dev/G008-dev-report.md,reports/test/G008-test-report.md |
| MISSING_REQUIRED_FIELDS | NONE |
| UNKNOWN_FIELDS | NONE |
| HUMAN_REVIEW_REQUIRED | False |

**判定**：PASS — 所有字段正确解析，parse_check_result=pass

### 函数级验证（自定义 T088 stdout）

构造 stdout 包含 TASK_ID=T088 的完整 pass 输出，解析结果：

| 字段 | 预期 | 实际 | 结果 |
|------|------|------|------|
| check_result | pass | pass | PASS |
| task_status | done | done | PASS |
| next_pending | T089 | T089 | PASS |
| real_task_execution | yes | yes | PASS |
| claude_code_called | unknown | unknown | PASS |
| business_code_changed | yes | yes | PASS |
| worktree_status | dirty_reports_only | dirty_reports_only | PASS |
| report_paths 长度 | 2 | 2 | PASS |
| parse_status | parsed | parsed | PASS |
| parse_check_result | pass | pass | PASS |
| missing_required_fields | [] | [] | PASS |
| unknown_fields | [] | [] | PASS |

**所有断言通过**：ALL ASSERTIONS PASSED

### REPORT_PATHS 解析详情

```
report_paths=['reports/dev/T088-dev-report.md', 'reports/checks/T088-simulated-child-check-result-pass-check.md']
```

- 逗号分隔正确
- 前后无多余空格
- 长度 = 2

## Stop Behavior

根据 T084 设计（`run-project-task-full-real-call-minimal-design.md`），即使 CHECK_RESULT=pass：

| 约束项 | 值 | 来源 |
|--------|------|------|
| 是否自动进入下一任务 | no | T084 设计：第一个真实调用必须人工验收 |
| 是否自动提交 | no | T084 设计：Git 备份策略尚未自动化 |
| 是否自动推送 | no | T084 设计：需人工确认后才操作 |
| 是否需要人工确认 | yes | T084 设计：HUMAN_REVIEW_REQUIRED=true |
| AUTO_CONTINUE_TO_NEXT_TASK | no | continuous_task_planner.py 硬编码 False |
| AUTO_GIT_BACKUP | no | continuous_task_planner.py 硬编码 False |

T084 设计给出的 5 个停止理由：

1. 第一个真实调用必须人工验收
2. 业务代码可能已变更，需要人工确认
3. Claude Code 是否调用需确认（输出 unknown，不是确认值）
4. Git 备份策略尚未自动化
5. 这是 MVP 安全边界，不是长期限制

## Safety Check

| 安全项 | 结果 |
|--------|------|
| 是否执行真实任务 | no |
| 是否调用 run-project-task-full | no |
| 是否调用 Claude Code | no |
| 是否修改业务代码 | no |
| 是否自动进入下一任务 | no |
| 是否自动 Git 备份 | no |

执行前后 `git status --short` 均 clean。

## Check Result

**pass**

## Next

T089：验证 simulated child CHECK_RESULT=fail
