# T077 Dev Report

## Task

设计 max_tasks=1 真实调用 run-project-task-full 安全协议。

## Scope

本轮只生成设计文档，不实现代码。

## Changed Files

- docs/run-project-loop-real-task-execution-safety-design.md（新增，设计文档）
- reports/dev/T077-dev-report.md（本文件）
- docs/tasks.md（状态更新）
- memory/lessons.md（经验追加）
- memory/pitfalls.md（经验追加）

## Design Summary

### 双重确认

| 确认层级 | 短语 | 用途 |
|----------|------|------|
| 第一重 | EXECUTE_PROJECT_LOOP | 进入 execute mode（已有） |
| 第二重 | EXECUTE_REAL_TASK_ONCE | 允许真实调用（新增） |

### CLI 推荐

方案 A：扩展现有 `run-project-loop`：

```bash
python runner.py run-project-loop --project . --max-tasks 1 \
  --execute --confirm EXECUTE_PROJECT_LOOP \
  --real-call --real-confirm EXECUTE_REAL_TASK_ONCE
```

### 真实调用边界

- max_tasks=1 only
- 直接函数调用 `run_project_task_full()`（非 subprocess）
- 捕获 `FullTaskLoopResult`（final_status / steps / report_path）
- workspace 前后快照比较
- 无论 pass/fail 都停止等待人工确认

### 输出解析

| final_status | CHECK_RESULT | 后续 |
|--------------|-------------|------|
| COMPLETE | pass | 停止等待人工确认 |
| FAILED | fail | 停止等待人工处理 |
| BLOCKED | fail | 停止等待人工处理 |
| REQUEST_CHANGES | fail | 停止等待人工处理 |
| 异常 | fail | 停止 |

### 停止规则

- 21 个停止条件（含 preflight 11 项 + 执行结果 10 项）
- 无论 pass/fail 都不自动进入下一任务
- 不自动 Git 备份
- HUMAN_REVIEW_REQUIRED 始终 true

## Safety Summary

### 前置检查

13 项 preflight 检查，任一不满足拒绝执行。

### 安全输出字段

- REAL_TASK_EXECUTION=yes/no
- RUN_PROJECT_TASK_FULL_CALLED=yes/no
- CLAUDE_CODE_CALLED=yes/no/unknown（无法确认时输出 unknown，不写 no）
- BUSINESS_CODE_CHANGED=yes/no/unknown（无法分类时输出 unknown）
- AUTO_CONTINUE_TO_NEXT_TASK=no（始终）
- AUTO_GIT_BACKUP=no（始终）
- HUMAN_REVIEW_REQUIRED=true（始终）

## Recommended Next Tasks

| 任务 | 内容 |
|------|------|
| T078 | 实现 real-call double-confirm safety gate |
| T079 | 实现 max_tasks=1 real-call dry-run executor |
| T080 | 验证 real confirm 拒绝场景（场景 1-10） |
| T081 | 验证 simulated CHECK_RESULT=pass（场景 11, 16-17） |
| T082 | 验证 simulated CHECK_RESULT=fail（场景 12-15, 18） |
| T083 | 提交并推送 real-call safety MVP |

## Verification

| 检查项 | 结果 |
|--------|------|
| 工作区初始状态 | clean |
| 是否只修改文档 | yes — 新增设计文档 + 更新 tasks/memory |
| 是否未修改代码 | yes — 未修改 runner.py / continuous_task_planner.py |
| 是否未修改业务代码 | yes — 未修改 projects/ |
| 是否未调用 run-project-task-full | yes |
| 是否未调用 Claude Code | yes |

## Next

T078：实现 real-call double-confirm safety gate
