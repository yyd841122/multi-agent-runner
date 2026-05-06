# T086 Child Command Parser Dry-Run Check

## 验证目标

验证 `parse_child_command_output()` 函数和 workspace 辅助函数的解析和降级行为。

## 验证场景

### 场景 1：完整 pass stdout → parse_check_result=pass

**命令**：
```bash
python runner.py parse-child-output-dry-run --sample pass
```

**预期**：parse_status=parsed, parse_check_result=pass, 所有字段已解析

**实际**：PASS
- PARSE_STATUS=parsed
- PARSE_CHECK_RESULT=pass
- TASK_ID=G008
- CHECK_RESULT=pass
- TASK_STATUS=done
- NEXT_PENDING=G009
- CLAUDE_CODE_CALLED=yes
- BUSINESS_CODE_CHANGED=yes
- WORKTREE_STATUS=dirty_business_code
- REPORT_PATHS=reports/dev/G008-dev-report.md,reports/test/G008-test-report.md
- MISSING_REQUIRED_FIELDS=NONE
- UNKNOWN_FIELDS=NONE
- HUMAN_REVIEW_REQUIRED=False

### 场景 2：完整 fail stdout → parse_check_result=pass 但 check_result=fail

**命令**：
```bash
python runner.py parse-child-output-dry-run --sample fail
```

**预期**：parse_check_result=pass（解析成功），CHECK_RESULT=fail（子命令失败）

**实际**：PASS
- PARSE_STATUS=parsed
- PARSE_CHECK_RESULT=pass
- CHECK_RESULT=fail
- TASK_STATUS=failed
- FINAL_STATUS=FAILED
- HUMAN_REVIEW_REQUIRED=False

### 场景 3：缺少 CHECK_RESULT → parse_check_result=fail

**命令**：
```bash
python runner.py parse-child-output-dry-run --sample missing-check-result
```

**预期**：parse_check_result=fail, stop_reason=missing_check_result

**实际**：PASS
- PARSE_STATUS=parse_failed
- PARSE_CHECK_RESULT=fail
- MISSING_REQUIRED_FIELDS=CHECK_RESULT
- STOP_REASON=missing_check_result
- HUMAN_REVIEW_REQUIRED=True

### 场景 4：缺少 TASK_STATUS → task_status=unknown

**命令**：
```bash
python runner.py parse-child-output-dry-run --sample missing-optional
```

**预期**：task_status=unknown, claude_code_called=unknown, 加入 unknown_fields

**实际**：PASS
- PARSE_STATUS=parsed_with_missing_fields
- PARSE_CHECK_RESULT=pass
- TASK_STATUS=unknown
- CLAUDE_CODE_CALLED=unknown
- BUSINESS_CODE_CHANGED=unknown
- WORKTREE_STATUS=unknown
- UNKNOWN_FIELDS=TASK_STATUS,CLAUDE_CODE_CALLED,BUSINESS_CODE_CHANGED,WORKTREE_STATUS
- HUMAN_REVIEW_REQUIRED=True

### 场景 5：缺少 CLAUDE_CODE_CALLED → claude_code_called=unknown

（通过场景 4 验证，CLAUDE_CODE_CALLED 在 unknown_fields 中）

**实际**：PASS

### 场景 6：缺少 BUSINESS_CODE_CHANGED → business_code_changed=unknown

（通过场景 4 验证，BUSINESS_CODE_CHANGED 在 unknown_fields 中）

**实际**：PASS

### 场景 7：REPORT_PATHS 多路径解析正确

**验证方式**：函数级验证

```python
stdout = "TASK_ID=G008\nCHECK_RESULT=pass\nREPORT_PATHS=a.md,b.md,c.md\n..."
result = parse_child_command_output(stdout)
assert len(result.report_paths) == 3
```

**实际**：PASS
- report_paths 长度 = 3
- 路径按逗号分隔正确

### 场景 8：stdout 含普通日志行，parser 忽略非 KEY=value 行

**命令**：
```bash
python runner.py parse-child-output-dry-run --sample with-logs
```

**预期**：parse_status=parsed，忽略 [INFO] 和 [DEBUG] 行

**实际**：PASS
- PARSE_STATUS=parsed
- PARSE_CHECK_RESULT=pass
- TASK_ID=G008
- CHECK_RESULT=pass
- CLAUDE_CODE_CALLED=yes
- 日志行 `[INFO]` 和 `[DEBUG]` 被正确忽略

### 场景 9：exit_code 非 0 且 CHECK_RESULT=pass → parse_check_result=pass，message 说明 exit_code 非 0

**命令**：
```bash
python runner.py parse-child-output-dry-run --sample exit-code-nonzero
```

**预期**：parse_check_result=pass，message 包含 exit_code 非 0 提示

**实际**：PASS
- PARSE_STATUS=parsed
- PARSE_CHECK_RESULT=pass
- EXIT_CODE=2
- CHECK_RESULT=pass
- Message 包含 "exit_code=2 非 0，需要后续执行层处理"

### 场景 10：空 stdout → parse_check_result=fail

**命令**：
```bash
python runner.py parse-child-output-dry-run --sample empty
```

**预期**：parse_status=parse_failed, stop_reason=empty_stdout

**实际**：PASS
- PARSE_STATUS=parse_failed
- PARSE_CHECK_RESULT=fail
- RAW_STDOUT_PRESENT=False
- STOP_REASON=empty_stdout
- HUMAN_REVIEW_REQUIRED=True
- 所有可选字段值为 unknown

## 函数级额外验证

### _snapshot_workspace()

- 已通过 git status --short 调用验证
- 返回 set[str]

### _classify_workspace_changes()

| 输入 | 分类结果 | PASS |
|------|----------|------|
| 无变更 | clean | PASS |
| 只有 reports/ 变更 | dirty_expected | PASS |
| 有 .html/.js/.py 等变更 | dirty_business_code | PASS |
| 有未知变更 | dirty_unexpected | PASS |

### _infer_claude_code_called()

| 输入 | 输出 | PASS |
|------|------|------|
| Developer step + success | yes | PASS |
| 无 Developer step + dirty | unknown | PASS |
| 空 steps | no | PASS |

### _infer_business_code_changed()

| 输入 | 输出 | PASS |
|------|------|------|
| clean | no | PASS |
| dirty_business_code + .html | yes | PASS |
| dirty_unexpected + .txt | unknown | PASS |

## 验证总结

| 场景 | 结果 |
|------|------|
| 1. 完整 pass stdout | PASS |
| 2. 完整 fail stdout | PASS |
| 3. 缺少 CHECK_RESULT | PASS |
| 4. 缺少 TASK_STATUS | PASS |
| 5. 缺少 CLAUDE_CODE_CALLED | PASS |
| 6. 缺少 BUSINESS_CODE_CHANGED | PASS |
| 7. REPORT_PATHS 多路径 | PASS |
| 8. 普通日志行忽略 | PASS |
| 9. exit_code 非 0 | PASS |
| 10. 空 stdout | PASS |
| 额外: workspace 分类 | PASS |
| 额外: CLAUDE_CODE_CALLED 推断 | PASS |
| 额外: BUSINESS_CODE_CHANGED 推断 | PASS |

**总计**：10/10 场景 PASS + 3 组函数级验证 PASS
