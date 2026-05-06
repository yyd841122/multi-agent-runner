# T080 Real Confirm Rejection Check

## 验证日期

2026-05-06

## Goal

验证 real-call 模式中错误或缺失的 `--real-confirm` 必须被拒绝。

## Commands

### 场景 1：缺少 --real-confirm

**命令**：`python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-call-dry-run`

**结果**：

| 字段 | 值 | 预期 | 结果 |
|------|-----|------|------|
| REAL_CALL_ALLOWED | False | False | PASS |
| DRY_RUN_EXECUTOR_STARTED | False | False | PASS |
| TASK_EXECUTION_PERFORMED | False | False | PASS |
| RUN_PROJECT_TASK_FULL_CALLED | False | False | PASS |
| CLAUDE_CODE_CALLED | no | no | PASS |
| BUSINESS_CODE_CHANGED | no | no | PASS |
| CHECK_RESULT | fail | fail | PASS |
| STOP_REASON | real_confirm_missing | missing 或 rejected | PASS |

### 场景 2：real-confirm=yes

**命令**：`python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm yes --real-call-dry-run`

**结果**：

| 字段 | 值 | 预期 | 结果 |
|------|-----|------|------|
| REAL_CALL_ALLOWED | False | False | PASS |
| DRY_RUN_EXECUTOR_STARTED | False | False | PASS |
| TASK_EXECUTION_PERFORMED | False | False | PASS |
| RUN_PROJECT_TASK_FULL_CALLED | False | False | PASS |
| CLAUDE_CODE_CALLED | no | no | PASS |
| BUSINESS_CODE_CHANGED | no | no | PASS |
| CHECK_RESULT | fail | fail | PASS |
| STOP_REASON | real_confirm_rejected | rejected | PASS |

### 场景 3：real-confirm=ok

**命令**：`python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm ok --real-call-dry-run`

**结果**：

| 字段 | 值 | 预期 | 结果 |
|------|-----|------|------|
| REAL_CALL_ALLOWED | False | False | PASS |
| DRY_RUN_EXECUTOR_STARTED | False | False | PASS |
| TASK_EXECUTION_PERFORMED | False | False | PASS |
| RUN_PROJECT_TASK_FULL_CALLED | False | False | PASS |
| CLAUDE_CODE_CALLED | no | no | PASS |
| BUSINESS_CODE_CHANGED | no | no | PASS |
| CHECK_RESULT | fail | fail | PASS |
| STOP_REASON | real_confirm_rejected | rejected | PASS |

### 场景 4：real-confirm=确认

**命令**：`python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm 确认 --real-call-dry-run`

**结果**：

| 字段 | 值 | 预期 | 结果 |
|------|-----|------|------|
| REAL_CALL_ALLOWED | False | False | PASS |
| DRY_RUN_EXECUTOR_STARTED | False | False | PASS |
| TASK_EXECUTION_PERFORMED | False | False | PASS |
| RUN_PROJECT_TASK_FULL_CALLED | False | False | PASS |
| CLAUDE_CODE_CALLED | no | no | PASS |
| BUSINESS_CODE_CHANGED | no | no | PASS |
| CHECK_RESULT | fail | fail | PASS |
| STOP_REASON | real_confirm_rejected | rejected | PASS |

### 场景 5：real-confirm=EXECUTE_PROJECT_LOOP（使用 execute confirm 短语代替）

**命令**：`python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_PROJECT_LOOP --real-call-dry-run`

**结果**：

| 字段 | 值 | 预期 | 结果 |
|------|-----|------|------|
| REAL_CALL_ALLOWED | False | False | PASS |
| DRY_RUN_EXECUTOR_STARTED | False | False | PASS |
| TASK_EXECUTION_PERFORMED | False | False | PASS |
| RUN_PROJECT_TASK_FULL_CALLED | False | False | PASS |
| CLAUDE_CODE_CALLED | no | no | PASS |
| BUSINESS_CODE_CHANGED | no | no | PASS |
| CHECK_RESULT | fail | fail | PASS |
| STOP_REASON | real_confirm_rejected | rejected | PASS |

### 场景 6：real-confirm=EXECUTE_REWORK

**命令**：`python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REWORK --real-call-dry-run`

**结果**：

| 字段 | 值 | 预期 | 结果 |
|------|-----|------|------|
| REAL_CALL_ALLOWED | False | False | PASS |
| DRY_RUN_EXECUTOR_STARTED | False | False | PASS |
| TASK_EXECUTION_PERFORMED | False | False | PASS |
| RUN_PROJECT_TASK_FULL_CALLED | False | False | PASS |
| CLAUDE_CODE_CALLED | no | no | PASS |
| BUSINESS_CODE_CHANGED | no | no | PASS |
| CHECK_RESULT | fail | fail | PASS |
| STOP_REASON | real_confirm_rejected | rejected | PASS |

### 场景 7：real-confirm=EXECUTE_REAL_TASK（接近但不精确）

**命令**：`python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK --real-call-dry-run`

**结果**：

| 字段 | 值 | 预期 | 结果 |
|------|-----|------|------|
| REAL_CALL_ALLOWED | False | False | PASS |
| DRY_RUN_EXECUTOR_STARTED | False | False | PASS |
| TASK_EXECUTION_PERFORMED | False | False | PASS |
| RUN_PROJECT_TASK_FULL_CALLED | False | False | PASS |
| CLAUDE_CODE_CALLED | no | no | PASS |
| BUSINESS_CODE_CHANGED | no | no | PASS |
| CHECK_RESULT | fail | fail | PASS |
| STOP_REASON | real_confirm_rejected | rejected | PASS |

## Expected Result

错误 real confirm 场景应满足：

- REAL_CALL_ALLOWED=false ✓（7/7 场景）
- DRY_RUN_EXECUTOR_STARTED=false ✓（7/7 场景）
- TASK_EXECUTION_PERFORMED=false ✓（7/7 场景）
- RUN_PROJECT_TASK_FULL_CALLED=false ✓（7/7 场景）
- CLAUDE_CODE_CALLED=no ✓（7/7 场景）
- BUSINESS_CODE_CHANGED=no ✓（7/7 场景）
- CHECK_RESULT=fail ✓（7/7 场景）

## Actual Result

所有 7 个拒绝场景全部 PASS。

STOP_REASON 分布：
- real_confirm_missing：1 场景（场景 1，缺少 --real-confirm）
- real_confirm_rejected：6 场景（场景 2-7，提供了错误值）

精确匹配验证：
- `yes` → 拒绝 ✓
- `ok` → 拒绝 ✓
- `确认` → 拒绝 ✓
- `EXECUTE_PROJECT_LOOP`（execute confirm 短语）→ 拒绝 ✓
- `EXECUTE_REWORK` → 拒绝 ✓
- `EXECUTE_REAL_TASK`（缺少 _ONCE 后缀）→ 拒绝 ✓

## Execute Confirm vs Real Confirm

### 场景 8：错误 execute confirm + 正确 real confirm

**命令**：`python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm yes --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-dry-run`

**结果**：

| 字段 | 值 | 结果 |
|------|-----|------|
| REAL_CALL_ALLOWED | False | PASS |
| DRY_RUN_EXECUTOR_STARTED | False | PASS |
| CHECK_RESULT | fail | PASS |
| STOP_REASON | execute_safety_gate_failed:confirm_rejected | PASS |
| TASK_EXECUTION_PERFORMED | False | PASS |
| RUN_PROJECT_TASK_FULL_CALLED | False | PASS |
| CLAUDE_CODE_CALLED | no | PASS |
| BUSINESS_CODE_CHANGED | no | PASS |

**说明**：即使 real confirm 正确，execute confirm 错误仍然被第一层 safety gate 拒绝。execute confirm 和 real confirm 是两层独立校验，不能互相替代。

### 场景 9：正确双确认（对照组）

**命令**：`python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-dry-run`

**结果**：

| 字段 | 值 | 结果 |
|------|-----|------|
| REAL_CALL_ALLOWED | True | PASS |
| DRY_RUN_EXECUTOR_STARTED | True | PASS |
| CHECK_RESULT | pass | PASS |
| TASK_EXECUTION_PERFORMED | False | PASS |
| RUN_PROJECT_TASK_FULL_CALLED | False | PASS |
| CLAUDE_CODE_CALLED | no | PASS |
| BUSINESS_CODE_CHANGED | no | PASS |

**说明**：正确双确认通过 safety gate，dry-run executor 启动，但仍然不执行真实任务。

### 关键区别

| 确认类型 | 短语 | 作用 |
|----------|------|------|
| execute confirm | `EXECUTE_PROJECT_LOOP` | 进入 execute mode，允许执行模式 |
| real confirm | `EXECUTE_REAL_TASK_ONCE` | 进入 real-call dry-run executor，允许构造未来调用 |

- 两者不能互相替代
- 两者都必须精确匹配（exact match）
- 缺少任一层确认都会被拒绝
- 即使通过，dry-run executor 仍然不执行真实任务

## Safety Check

| 检查项 | 结果 |
|--------|------|
| 是否执行真实任务 | no ✓ |
| 是否调用 run-project-task-full | no ✓ |
| 是否调用 Claude Code | no ✓ |
| 是否修改业务代码 | no ✓ |
| 工作区变化 | clean（无变化）✓ |
| projects/down-100-floors-game/** | 无变化 ✓ |

## Check Result

**PASS** — 全部 9 个场景验证通过。

| 场景 | 描述 | 结果 |
|------|------|------|
| 1 | 缺少 --real-confirm | PASS |
| 2 | real-confirm=yes | PASS |
| 3 | real-confirm=ok | PASS |
| 4 | real-confirm=确认 | PASS |
| 5 | real-confirm=EXECUTE_PROJECT_LOOP | PASS |
| 6 | real-confirm=EXECUTE_REWORK | PASS |
| 7 | real-confirm=EXECUTE_REAL_TASK | PASS |
| 8 | 错误 execute confirm + 正确 real confirm | PASS |
| 9 | 正确双确认（对照组，不执行） | PASS |

## Next

T081：验证 simulated CHECK_RESULT=pass
