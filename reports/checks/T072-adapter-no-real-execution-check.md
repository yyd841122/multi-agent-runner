# T072 Adapter No Real Execution Check

## Goal

验证 `--adapter-dry-run` 只构造未来命令，不真实调用 `run-project-task-full`。

## Commands

```bash
# 场景 1：正确参数 adapter dry-run
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --adapter-dry-run

# 场景 2：不带 --execute
python runner.py run-project-loop --project . --max-tasks 1 --adapter-dry-run

# 场景 3：confirm 错误
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm yes --adapter-dry-run

# 场景 4：max_tasks=2
python runner.py run-project-loop --project . --max-tasks 2 --execute --confirm EXECUTE_PROJECT_LOOP --adapter-dry-run
```

## Expected Result

### 成功场景（场景 1）

- EXECUTION_MODE=task_execution_adapter_dry_run
- ADAPTER_DRY_RUN=true
- TASK_EXECUTION_PERFORMED=false
- RUN_PROJECT_TASK_FULL_CALLED=false
- CLAUDE_CODE_CALLED=no
- BUSINESS_CODE_CHANGED=false
- TASK_ID=T072
- COMMAND 存在
- CHECK_RESULT=pass

### 拒绝场景（场景 2-4）

- CHECK_RESULT=fail 或 error
- TASK_EXECUTION_PERFORMED=false
- RUN_PROJECT_TASK_FULL_CALLED=false
- CLAUDE_CODE_CALLED=no
- BUSINESS_CODE_CHANGED=false

## Actual Result

### 场景 1：正确参数 adapter dry-run

```bash
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --adapter-dry-run
```

输出：

```
EXECUTION_MODE=task_execution_adapter_dry_run
ADAPTER_DRY_RUN=true
RUN_ID=loop-20260506-085227-ebcee2
MAX_TASKS=1
TASK_ID=T072
TASK_EXECUTION_PERFORMED=False
RUN_PROJECT_TASK_FULL_CALLED=False
CLAUDE_CODE_CALLED=no
BUSINESS_CODE_CHANGED=no
LOOP_STATUS=adapter_dry_run_completed
STOP_REASON=adapter_dry_run_only
HUMAN_REVIEW_REQUIRED=True
CHECK_RESULT=pass
NEXT_ACTION=ready_for_T072_adapter_validation
COMMAND=run_project_task_full(project_path='E:\github_project\multi-agent-runner\projects', task_id='T072')
```

验证：

| 字段 | 预期 | 实际 | 结果 |
|------|------|------|------|
| EXECUTION_MODE | task_execution_adapter_dry_run | task_execution_adapter_dry_run | PASS |
| ADAPTER_DRY_RUN | true | true | PASS |
| TASK_EXECUTION_PERFORMED | false | False | PASS |
| RUN_PROJECT_TASK_FULL_CALLED | false | False | PASS |
| CLAUDE_CODE_CALLED | no | no | PASS |
| BUSINESS_CODE_CHANGED | false | no | PASS |
| TASK_ID | T072 | T072 | PASS |
| COMMAND | 存在 | 存在 | PASS |
| CHECK_RESULT | pass | pass | PASS |

结果：**PASS**

### 场景 2：不带 --execute

```bash
python runner.py run-project-loop --project . --max-tasks 1 --adapter-dry-run
```

输出：

```
ERROR：--adapter-dry-run 必须配合 --execute 使用。
```

结果：**PASS**（正确拒绝，未进入执行流程）

### 场景 3：confirm 错误

```bash
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm yes --adapter-dry-run
```

输出：

```
EXECUTION_MODE=task_execution_adapter_dry_run
ADAPTER_DRY_RUN=true
LOOP_STATUS=safety_gate_failed
STOP_REASON=confirm_rejected
TASK_EXECUTION_PERFORMED=False
RUN_PROJECT_TASK_FULL_CALLED=False
CLAUDE_CODE_CALLED=no
BUSINESS_CODE_CHANGED=no
CHECK_RESULT=fail
```

验证：

| 字段 | 预期 | 实际 | 结果 |
|------|------|------|------|
| CHECK_RESULT | fail | fail | PASS |
| TASK_EXECUTION_PERFORMED | false | False | PASS |
| RUN_PROJECT_TASK_FULL_CALLED | false | False | PASS |
| CLAUDE_CODE_CALLED | no | no | PASS |
| BUSINESS_CODE_CHANGED | false | no | PASS |

结果：**PASS**

### 场景 4：max_tasks=2

```bash
python runner.py run-project-loop --project . --max-tasks 2 --execute --confirm EXECUTE_PROJECT_LOOP --adapter-dry-run
```

输出：

```
EXECUTION_MODE=task_execution_adapter_dry_run
ADAPTER_DRY_RUN=true
MAX_TASKS=2
LOOP_STATUS=max_tasks_gt_1_not_supported
STOP_REASON=max_tasks_gt_1_not_supported_in_adapter
TASK_EXECUTION_PERFORMED=False
RUN_PROJECT_TASK_FULL_CALLED=False
CLAUDE_CODE_CALLED=no
BUSINESS_CODE_CHANGED=no
CHECK_RESULT=fail
```

验证：

| 字段 | 预期 | 实际 | 结果 |
|------|------|------|------|
| CHECK_RESULT | fail | fail | PASS |
| TASK_EXECUTION_PERFORMED | false | False | PASS |
| RUN_PROJECT_TASK_FULL_CALLED | false | False | PASS |
| CLAUDE_CODE_CALLED | no | no | PASS |
| BUSINESS_CODE_CHANGED | false | no | PASS |

结果：**PASS**

## Side Effect Check

| 检查项 | 结果 |
|--------|------|
| 是否执行真实任务 | no — 所有场景 TASK_EXECUTION_PERFORMED=false |
| 是否调用 run-project-task-full | no — 所有场景 RUN_PROJECT_TASK_FULL_CALLED=false |
| 是否调用 Claude Code | no — 所有场景 CLAUDE_CODE_CALLED=no |
| 是否修改业务代码 | no — BUSINESS_CODE_CHANGED=no |
| 是否新增业务报告 | no — git status 无变化 |
| projects/down-100-floors-game/** 无变化 | yes — git status clean |

验证后 `git status --short` 无输出，确认无副作用。

## Summary

| # | 场景 | 结果 |
|---|------|------|
| 1 | 正确参数 adapter dry-run | PASS |
| 2 | 不带 --execute → 拒绝 | PASS |
| 3 | confirm 错误 → confirm_rejected | PASS |
| 4 | max_tasks=2 → adapter 拒绝 | PASS |

全部 4 个场景通过。所有路径确认：TASK_EXECUTION_PERFORMED=false, RUN_PROJECT_TASK_FULL_CALLED=false, CLAUDE_CODE_CALLED=no, BUSINESS_CODE_CHANGED=no。

## Check Result

pass

## Next

T073：实现 max_tasks=1 real-call stub
