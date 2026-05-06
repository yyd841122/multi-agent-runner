# T086 Dev Report

## Task

实现 child command parser dry-run。

## Scope

本轮只实现 parser dry-run，不真实调用 run-project-task-full，不调用 Claude Code，不修改业务代码。

## Changed Files

- tools/continuous_task_planner.py（新增 workspace 辅助函数 + ChildCommandParseResult + parse_child_command_output()）
- runner.py（新增 parse-child-output-dry-run 命令 + 7 个内置样例）
- reports/checks/T086-child-command-parser-dry-run-check.md（新增，10 个验证场景 + 3 组函数级验证）
- reports/dev/T086-dev-report.md（新增，本文件）
- docs/tasks.md（状态更新）
- memory/lessons.md（追加经验）
- memory/pitfalls.md（追加避坑）

## Implementation

### Workspace 辅助函数

1. `_snapshot_workspace(project_root)` → `set[str]`
   - 调用 `git status --short`，返回行集合
   - 异常时返回空集合

2. `_classify_workspace_changes(before, after)` → `tuple[str, list[str]]`
   - 比较前后快照，分类为 clean / dirty_expected / dirty_unexpected / dirty_business_code
   - 剥离 git status 前缀（前 3 字符）再检查文件路径
   - 有 .html/.css/.js/.py/.yaml/.json 变更（非 reports/ docs/）→ dirty_business_code

3. `_infer_claude_code_called(steps, workspace_status)` → `str`
   - 有 Developer step 且 success → yes
   - 无 steps → no
   - 有 workspace 变化但无 Developer success → unknown

4. `_infer_business_code_changed(workspace_status, changed_files)` → `str`
   - clean → no
   - 有业务代码文件变更 → yes
   - 无法分类 → unknown

### ChildCommandParseResult

20 字段数据结构：

- `raw_stdout_present` / `raw_stderr_present` / `exit_code`
- `task_id` / `check_result` / `task_status` / `next_pending`
- `real_task_execution` / `claude_code_called` / `business_code_changed` / `worktree_status`
- `report_paths`（list[str]）
- `missing_required_fields` / `unknown_fields`（list[str]）
- `parse_status`（parsed / parsed_with_missing_fields / parse_failed）
- `parse_check_result`（pass / fail）
- `stop_reason` / `human_review_required` / `message`

### parse_child_command_output(stdout_text, stderr_text="", exit_code=0)

解析流程：

1. 空 stdout → 立即返回 parse_failed
2. 逐行解析 KEY=value（只识别 _PARSER_KNOWN_KEYS 中的 key）
3. 忽略非 KEY=value 行
4. 收集缺失必需字段（CHECK_RESULT）和缺失可选字段
5. 确定 parse_status 和 parse_check_result
6. REPORT_PATHS 逗号分隔为 list
7. 组装消息

### parse-child-output-dry-run CLI

新增命令 `python runner.py parse-child-output-dry-run --sample <type>`

内置 7 个样例：
- `pass` / `fail` / `missing-check-result` / `missing-optional`
- `with-logs` / `empty` / `exit-code-nonzero`

## Behavior

### KEY=value 解析

- 只识别已知 key（_PARSER_KNOWN_KEYS 中的 11 个 key）
- 等号分割，取第一个 = 分割
- 大小写保持，不强制转换 key

### 缺失字段处理

- 缺少 CHECK_RESULT → parse_check_result=fail, stop_reason=missing_check_result
- 缺少 TASK_STATUS → task_status=unknown，加入 unknown_fields
- 缺少 CLAUDE_CODE_CALLED → claude_code_called=unknown，加入 unknown_fields
- 缺少 BUSINESS_CODE_CHANGED → business_code_changed=unknown，加入 unknown_fields
- 缺少 WORKTREE_STATUS → worktree_status=unknown，加入 unknown_fields

### unknown 字段处理

- unknown 字段不变成 no，保持 unknown
- unknown_fields 列表记录所有值为 unknown 的字段名

### 普通日志行处理

- 不含 = 的行被忽略
- 含 = 但 key 不在 _PARSER_KNOWN_KEYS 中的行也被忽略

### REPORT_PATHS 处理

- 逗号分隔为 list[str]
- 每个路径 strip 空格
- 空值过滤

## Safety Rules

- no run-project-task-full call：RUN_PROJECT_TASK_FULL_CALLED=no（parser 不执行任何命令）
- no Claude Code call：CLAUDE_CODE_CALLED 未由 parser 调用
- no business code modification：parser 只解析字符串
- missing CHECK_RESULT fails safely：parse_check_result=fail
- unknown fields do not become no：保持 unknown 值

## Verification

| # | 场景 | 结果 |
|---|------|------|
| 1 | 完整 pass stdout | PASS |
| 2 | 完整 fail stdout | PASS |
| 3 | 缺少 CHECK_RESULT | PASS |
| 4 | 缺少 TASK_STATUS | PASS |
| 5 | 缺少 CLAUDE_CODE_CALLED | PASS |
| 6 | 缺少 BUSINESS_CODE_CHANGED | PASS |
| 7 | REPORT_PATHS 多路径解析 | PASS |
| 8 | 普通日志行忽略 | PASS |
| 9 | exit_code 非 0 | PASS |
| 10 | 空 stdout | PASS |

额外函数级验证：
- _classify_workspace_changes: 4 组分类全部 PASS
- _infer_claude_code_called: 3 组推断全部 PASS
- _infer_business_code_changed: 3 组推断全部 PASS

## Next

T087：验证 real-call-run-once 拒绝场景
