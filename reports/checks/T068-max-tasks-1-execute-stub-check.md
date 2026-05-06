# T068 Max Tasks 1 Execute Stub Check

## Goal

验证 `run-project-loop --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP` 可以进入 execute stub，但不执行真实任务。

同时验证 max_tasks=2/3 被 stub 正确拒绝。

## Commands

```bash
# 场景 1：max_tasks=1 execute stub
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP

# 场景 2：max_tasks=2 stub 拒绝
python runner.py run-project-loop --project . --max-tasks 2 --execute --confirm EXECUTE_PROJECT_LOOP

# 场景 3：max_tasks=3 stub 拒绝
python runner.py run-project-loop --project . --max-tasks 3 --execute --confirm EXECUTE_PROJECT_LOOP
```

## Expected Result

### max_tasks=1 应满足：

- EXECUTE_ALLOWED=true
- EXECUTE_STUB_STARTED=true
- STUB_TASK=T068
- TASK_EXECUTION_PERFORMED=false
- CLAUDE_CODE_CALLED=false
- BUSINESS_CODE_CHANGED=false
- LOOP_STATUS=execute_stub_completed
- STOP_REASON=execute_stub_only
- CHECK_RESULT=pass

### max_tasks=2/3 应满足：

- EXECUTE_ALLOWED=true
- EXECUTE_STUB_STARTED=false
- STOP_REASON=max_tasks_gt_1_not_supported_in_stub
- CHECK_RESULT=fail
- TASK_EXECUTION_PERFORMED=false
- CLAUDE_CODE_CALLED=false
- BUSINESS_CODE_CHANGED=false

## Actual Result

### 场景 1：max_tasks=1 execute stub

```bash
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP
```

```
EXECUTE_MODE_REQUESTED=true
EXECUTE_ALLOWED=True
EXECUTE_STUB_STARTED=True
RUN_ID=loop-20260506-082534-f1a069
MAX_TASKS=1
PLANNED_TASKS=T068
STUB_TASK=T068
COMPLETED_TASKS=T068
FAILED_TASKS=NONE
TASK_EXECUTION_PERFORMED=False
CLAUDE_CODE_CALLED=False
BUSINESS_CODE_CHANGED=False
LOOP_STATUS=execute_stub_completed
STOP_REASON=execute_stub_only
HUMAN_REVIEW_REQUIRED=False
NEXT_ACTION=ready_for_T067_validation
CHECK_RESULT=pass
```

结果：**PASS**

说明：NEXT_ACTION=ready_for_T067_validation 是 T066 实现时的遗留命名，可接受，建议后续优化为 ready_for_T069_execute_mvp_summary。

### 场景 2：max_tasks=2 stub 拒绝

```bash
python runner.py run-project-loop --project . --max-tasks 2 --execute --confirm EXECUTE_PROJECT_LOOP
```

```
EXECUTE_MODE_REQUESTED=true
EXECUTE_ALLOWED=True
EXECUTE_STUB_STARTED=False
RUN_ID=loop-20260506-082543-475d72
MAX_TASKS=2
PLANNED_TASKS=T068,T069
COMPLETED_TASKS=NONE
FAILED_TASKS=NONE
TASK_EXECUTION_PERFORMED=False
CLAUDE_CODE_CALLED=False
BUSINESS_CODE_CHANGED=False
LOOP_STATUS=max_tasks_gt_1_not_supported
STOP_REASON=max_tasks_gt_1_not_supported_in_stub
HUMAN_REVIEW_REQUIRED=False
NEXT_ACTION=use_max_tasks_1_for_stub
CHECK_RESULT=fail
```

结果：**PASS**

### 场景 3：max_tasks=3 stub 拒绝

```bash
python runner.py run-project-loop --project . --max-tasks 3 --execute --confirm EXECUTE_PROJECT_LOOP
```

```
EXECUTE_MODE_REQUESTED=true
EXECUTE_ALLOWED=True
EXECUTE_STUB_STARTED=False
RUN_ID=loop-20260506-082543-93eec1
MAX_TASKS=3
PLANNED_TASKS=T068,T069
COMPLETED_TASKS=NONE
FAILED_TASKS=NONE
TASK_EXECUTION_PERFORMED=False
CLAUDE_CODE_CALLED=False
BUSINESS_CODE_CHANGED=False
LOOP_STATUS=max_tasks_gt_1_not_supported
STOP_REASON=max_tasks_gt_1_not_supported_in_stub
HUMAN_REVIEW_REQUIRED=False
NEXT_ACTION=use_max_tasks_1_for_stub
CHECK_RESULT=fail
```

结果：**PASS**

## Safety Check

| 检查项 | 结果 |
|--------|------|
| 是否执行真实任务 | no — 所有场景 TASK_EXECUTION_PERFORMED=false |
| 是否调用 Claude Code | no — 所有场景 CLAUDE_CODE_CALLED=false |
| 是否修改业务代码 | no — BUSINESS_CODE_CHANGED=false |
| 是否调用 run-project-task-full | no — execute stub 不调用 |
| 工作区是否保持 clean | yes — git status --short 无输出 |
| projects/down-100-floors-game/** 无变化 | yes — 无任何文件变化 |

## Summary

| # | 场景 | EXECUTE_STUB_STARTED | STOP_REASON | CHECK_RESULT | 结果 |
|---|------|---------------------|-------------|-------------|------|
| 1 | max_tasks=1 | true | execute_stub_only | pass | PASS |
| 2 | max_tasks=2 | false | max_tasks_gt_1_not_supported_in_stub | fail | PASS |
| 3 | max_tasks=3 | false | max_tasks_gt_1_not_supported_in_stub | fail | PASS |

全部 3 个场景通过。

## Check Result

pass

## Next

T069：提交并推送 execute mode safety MVP
