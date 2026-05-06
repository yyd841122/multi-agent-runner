# T089 Simulated Child CHECK_RESULT Fail Check

## Goal

验证 child parser 能正确解析模拟子命令 `CHECK_RESULT=fail`，并确认 fail 后必须停止等待人工处理。

## Commands

### CLI 样例验证

```bash
python runner.py parse-child-output-dry-run --sample fail
```

### 函数级验证

```python
from tools.continuous_task_planner import parse_child_command_output

stdout = '''TASK_ID=T089
CHECK_RESULT=fail
TASK_STATUS=failed
NEXT_PENDING=T089
REAL_TASK_EXECUTION=yes
CLAUDE_CODE_CALLED=unknown
BUSINESS_CODE_CHANGED=unknown
WORKTREE_STATUS=dirty_unknown
REPORT_PATHS=reports/dev/T089-dev-report.md,reports/checks/T089-simulated-child-check-result-fail-check.md'''

result = parse_child_command_output(stdout)
```

## Expected Result

应满足：

- PARSE_STATUS=parsed
- PARSE_CHECK_RESULT=pass
- CHECK_RESULT=fail
- TASK_STATUS=failed
- REPORT_PATHS 可解析（2 个路径）
- unknown 字段不应被错误标记为 no
- fail 后不自动进入下一任务
- fail 后不自动 Git 备份
- fail 后需要人工处理

## Actual Result

### CLI 样例验证（--sample fail）

| 字段 | 值 |
|------|------|
| PARSE_STATUS | parsed |
| PARSE_CHECK_RESULT | pass |
| RAW_STDOUT_PRESENT | True |
| EXIT_CODE | 0 |
| TASK_ID | G008 |
| CHECK_RESULT | fail |
| TASK_STATUS | failed |
| NEXT_PENDING | |
| REAL_TASK_EXECUTION | yes |
| CLAUDE_CODE_CALLED | yes |
| BUSINESS_CODE_CHANGED | no |
| WORKTREE_STATUS | clean |
| REPORT_PATHS | reports/dev/G008-dev-report.md |
| MISSING_REQUIRED_FIELDS | NONE |
| UNKNOWN_FIELDS | NONE |
| HUMAN_REVIEW_REQUIRED | False |

**判定**：PASS — 所有字段正确解析，parse_check_result=pass，check_result=fail

### 函数级验证（自定义 T089 stdout）

构造 stdout 包含 TASK_ID=T089 的完整 fail 输出，解析结果：

| 字段 | 预期 | 实际 | 结果 |
|------|------|------|------|
| check_result | fail | fail | PASS |
| task_status | failed | failed | PASS |
| next_pending | T089 | T089 | PASS |
| real_task_execution | yes | yes | PASS |
| claude_code_called | unknown | unknown | PASS |
| business_code_changed | unknown | unknown | PASS |
| worktree_status | dirty_unknown | dirty_unknown | PASS |
| report_paths 长度 | 2 | 2 | PASS |
| parse_status | parsed | parsed | PASS |
| parse_check_result | pass | pass | PASS |
| missing_required_fields | [] | [] | PASS |
| unknown_fields | [] | [] | PASS |

**所有断言通过**：ALL ASSERTIONS PASSED

### REPORT_PATHS 解析详情

```
report_paths=['reports/dev/T089-dev-report.md', 'reports/checks/T089-simulated-child-check-result-fail-check.md']
```

- 逗号分隔正确
- 前后无多余空格
- 长度 = 2

## Stop Behavior

根据 T084 设计，CHECK_RESULT=fail 时：

| 约束项 | 值 | 来源 |
|--------|------|------|
| 是否自动进入下一任务 | no | T084 设计：fail 必须停止等待人工处理 |
| 是否自动提交 | no | T084 设计：Git 备份策略尚未自动化 |
| 是否自动推送 | no | T084 设计：需人工确认后才操作 |
| 是否需要人工确认 | yes | T084 设计：HUMAN_REVIEW_REQUIRED=true |
| AUTO_CONTINUE_TO_NEXT_TASK | false | continuous_task_planner.py 硬编码 False |
| AUTO_GIT_BACKUP | false | continuous_task_planner.py 硬编码 False |

T084 设计中 fail 场景的停止原因：

| final_status | CHECK_RESULT | 停止原因 | loop_status |
|--------------|-------------|----------|-------------|
| REQUEST_CHANGES | fail | rework_required | stopped_on_rework_required |
| BLOCKED | fail | task_blocked | stopped_on_task_blocked |
| FAILED | fail | task_failed | stopped_on_task_failed |
| 异常 | fail | execution_exception | stopped_on_task_failed |

无论哪种 fail 类型，均需人工处理，不自动继续。

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

## Limitation

本轮是 parser dry-run / sample stdout 验证，不是真实 child 执行验证。parser 解析 CHECK_RESULT=fail 只证明解析逻辑正确，不代表真实任务已执行或失败。真实执行验证留待后续任务。

## Check Result

**pass**

## Next

T090：提交并推送 real-call run-once MVP
