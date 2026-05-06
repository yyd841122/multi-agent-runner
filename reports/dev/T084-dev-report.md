# T084 Dev Report

## Task

设计真实调用 run-project-task-full 的最小实现协议。

## Scope

本轮只生成设计文档，不实现代码。

## Changed Files

- docs/run-project-task-full-real-call-minimal-design.md（新增，真实调用最小实现协议）
- reports/dev/T084-dev-report.md（新增，本文件）
- memory/lessons.md（追加真实调用最小实现设计经验）
- memory/pitfalls.md（追加真实调用最小实现设计避坑）
- docs/tasks.md（状态更新）

## Design Summary

### 调用方式

- **推荐 Python 函数调用**（非 subprocess），直接调用 `run_project_task_full(project_path, task_id)`
- 新增 `--real-call-run-once` 参数触发真实调用
- 复用 `validate_real_call_safety()` 双重确认安全门

### 前置检查

16 项 preflight checks，复用 safety gate 的 9 层检查 + 额外 7 项（task 状态、模式互斥等）

### 输出解析

- `final_status → CHECK_RESULT` 映射：COMPLETE → pass，其他 → fail
- 缺失字段处理：缺少 final_status → fail，无法确认字段 → unknown

### Workspace 分类

- 执行前后 `git status --short` 快照比较
- 分类：clean / dirty_expected / dirty_unexpected / dirty_unknown

### 停止规则

- 无论 pass/fail 都停止
- AUTO_CONTINUE_TO_NEXT_TASK=no
- AUTO_GIT_BACKUP=no
- HUMAN_REVIEW_REQUIRED=true

## Safety Summary

### 真实调用边界

- max_tasks=1 only
- 必须通过双重确认（EXECUTE_PROJECT_LOOP + EXECUTE_REAL_TASK_ONCE）
- 必须工作区 clean
- 必须有 planned pending task
- `--real-call-run-once` 与 `--real-call-dry-run` / `--real-call-stub` / `--adapter-dry-run` / `--dry-run` 互斥

### 人工验收点

- 真实执行后必须人工验收
- pass 后也不自动继续
- fail 后也不自动返工
- Git 备份需要人工确认

### 安全输出字段

```
EXECUTION_MODE=real_call_run_once
REAL_TASK_EXECUTION=yes/no
RUN_PROJECT_TASK_FULL_CALLED=yes/no/attempted
CLAUDE_CODE_CALLED=yes/no/unknown
BUSINESS_CODE_CHANGED=yes/no/unknown
AUTO_CONTINUE_TO_NEXT_TASK=no
AUTO_GIT_BACKUP=no
HUMAN_REVIEW_REQUIRED=true
```

## Recommended Next Tasks

| 任务 | 角色 | 说明 |
|------|------|------|
| T085 | Developer | 实现 real-call run-once safety shell（数据结构 + preflight + 拒绝场景） |
| T086 | Developer | 实现 child command parser（FullTaskLoopResult 解析 + workspace 检测 + 推断函数） |
| T087 | Tester | 验证 real-call-run-once 拒绝场景（11 个） |
| T088 | Tester | 验证 simulated child CHECK_RESULT=pass |
| T089 | Tester | 验证 simulated child CHECK_RESULT=fail |
| T090 | Developer | 实现真实调用（连接真实 run_project_task_full） |
| T091 | Tester | 验证真实执行 |
| T092 | Reporter | 提交并推送 real-call run-once MVP |

## Verification

| 检查项 | 结果 |
|--------|------|
| 工作区初始状态 | clean |
| 是否只修改文档 | yes |
| 是否未修改代码 | yes（未修改 runner.py / continuous_task_planner.py / rework_manager.py） |
| 是否未修改业务代码 | yes |
| 是否未调用 run-project-task-full | yes |
| 是否未调用 Claude Code | yes |

## Next

T085：实现 real-call run-once safety shell
