# Stage 6 Real-call Safety MVP Summary

## Goal

本文档是 real-call safety MVP 的小结，范围是 Stage 6 中 T077-T082 完成的安全设计和验证工作。

**重要**：这是 real-call safety / dry-run executor MVP，不是真实执行 MVP。当前系统仍然没有真实调用 `run_project_task_full()`，没有调用 Claude Code，没有修改业务代码。

## Completed Scope

| # | 任务 | 角色 | 说明 |
|---|------|------|------|
| T077 | real task execution safety design | Designer | 设计 21 个停止条件、双重确认协议、安全输出字段 |
| T078 | real-call double-confirm safety gate | Developer | 实现 `validate_real_call_safety()`、RealCallSafetyResult（20 字段） |
| T079 | real-call dry-run executor | Developer | 实现 `run_project_loop_real_call_dry_run_executor()`、RealCallDryRunExecutorResult（24 字段） |
| T080 | real confirm rejection validation | Tester | 验证 9 个拒绝场景（7 个错误值 + 2 个对照组） |
| T081 | simulated CHECK_RESULT=pass validation | Tester | 验证 17 个字段全部 PASS |
| T082 | simulated CHECK_RESULT=fail validation | Tester | 验证 8 个 fail-stop 设计约束全部 PASS |

## Implemented Commands

### 正确双确认命令（real-call dry-run executor）

```bash
python runner.py run-project-loop \
  --project . \
  --max-tasks 1 \
  --execute \
  --confirm EXECUTE_PROJECT_LOOP \
  --real-call \
  --real-confirm EXECUTE_REAL_TASK_ONCE \
  --real-call-dry-run
```

### 拒绝验证命令示例

```bash
# 缺少 real-confirm → real_confirm_missing
python runner.py run-project-loop --project . --max-tasks 1 \
  --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-call-dry-run

# 错误 real-confirm → real_confirm_rejected
python runner.py run-project-loop --project . --max-tasks 1 \
  --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm yes --real-call-dry-run

# 错误 execute confirm → execute_safety_gate_failed
python runner.py run-project-loop --project . --max-tasks 1 \
  --execute --confirm yes --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-dry-run
```

## Current Capabilities

当前系统可以：

1. **识别 `--real-call`**：区分普通 execute mode 和 real-call mode
2. **校验 `--real-confirm EXECUTE_REAL_TASK_ONCE`**：精确匹配第二重确认短语
3. **区分 execute confirm 和 real confirm**：两层确认独立校验，不能互相替代
4. **拒绝错误 real confirm**：`yes`、`ok`、`确认`、`EXECUTE_PROJECT_LOOP`、`EXECUTE_REWORK`、`EXECUTE_REAL_TASK` 全部拒绝
5. **通过双重确认后进入 real-call dry-run executor**：构造未来真实调用信息
6. **构造未来真实调用 command**：`python runner.py run-project-task-full --project <path> --task <id>`
7. **构造未来 function_call**：`run_project_task_full(project_path='<path>', task_id='<id>')`
8. **输出 dry-run executor result**：24 个结构化字段
9. **验证 simulated pass 后必须停止**：`AUTO_CONTINUE_TO_NEXT_TASK=False`
10. **验证 simulated fail 后必须停止**：8 个 fail-stop 设计约束全部 PASS
11. **明确输出安全字段**：
    - `RUN_PROJECT_TASK_FULL_CALLED=false`
    - `CLAUDE_CODE_CALLED=no`
    - `BUSINESS_CODE_CHANGED=no`
    - `AUTO_CONTINUE_TO_NEXT_TASK=false`
    - `AUTO_GIT_BACKUP=false`

## Important Non-capabilities

当前系统仍然**不能**：

| # | 不能 | 说明 |
|---|------|------|
| 1 | 真实调用 run-project-task-full | dry-run executor 只构造 command/function_call 字符串，不执行 |
| 2 | 真实执行任务 | `TASK_EXECUTION_PERFORMED` 始终 `False` |
| 3 | 调用 Claude Code | `CLAUDE_CODE_CALLED` 始终 `no` |
| 4 | 修改业务代码 | `BUSINESS_CODE_CHANGED` 始终 `no` |
| 5 | 自动进入下一任务 | `AUTO_CONTINUE_TO_NEXT_TASK` 始终 `False` |
| 6 | 自动 Git 备份 | `AUTO_GIT_BACKUP` 始终 `False` |
| 7 | 自动返工 | Non-goals 明确规定 |
| 8 | 执行多个任务 | `max_tasks` 限制为 1 |
| 9 | 无人值守连续推进 | MVP 阶段不做 |

## Safety Guarantees

### 双重确认

| 层级 | 确认短语 | 用途 |
|------|----------|------|
| 第一重 | `EXECUTE_PROJECT_LOOP` | 进入 execute mode |
| 第二重 | `EXECUTE_REAL_TASK_ONCE` | 允许真实调用构造 |

两层确认独立校验：
- 缺少第一重 → `execute_safety_gate_failed`
- 缺少第二重 → `real_confirm_missing`
- 第二重值错误 → `real_confirm_rejected`
- 即使两层都通过 → dry-run executor 仍然不执行真实任务

### max_tasks=1 Only

real-call 模式强制 `max_tasks=1`：
- `max_tasks=0` → 拒绝
- `max_tasks=2` → 拒绝
- `max_tasks>1` → 拒绝

### Real-call Dry-run Executor 不执行命令

dry-run executor 安全规则：
- `task_execution_performed=False` — 始终
- `run_project_task_full_called=False` — 始终
- `auto_continue_to_next_task=False` — 始终
- `auto_git_backup=False` — 始终
- `human_review_required=True` — 始终

### Pass 后停止

即使外层 `CHECK_RESULT=pass`：
- 不自动进入下一任务
- 不自动 Git 备份
- 需要人工确认

### Fail 后停止

外层 `CHECK_RESULT=fail` 时：
- 不自动进入下一任务
- 不自动 Git 备份
- 不自动返工
- 需要人工确认

### 安全输出字段保证

```
REAL_TASK_EXECUTION=no
RUN_PROJECT_TASK_FULL_CALLED=no
CLAUDE_CODE_CALLED=no
BUSINESS_CODE_CHANGED=no
AUTO_CONTINUE_TO_NEXT_TASK=no
AUTO_GIT_BACKUP=no
```

## Verification Summary

| 任务 | 验证内容 | 结果 |
|------|----------|------|
| T078 | real-call double-confirm safety gate（12 场景） | PASS |
| T080 | real confirm rejection validation（9 场景） | PASS |
| T081 | simulated CHECK_RESULT=pass validation（17 字段） | PASS |
| T082 | simulated CHECK_RESULT=fail validation（8 fail-stop 约束） | PASS |

### T078 Safety Gate 验证

12 个场景全覆盖：
- 不带 `--real-call` → 原行为保持
- `--real-call` 不带 `--execute` → 拒绝
- 缺少 `--real-confirm` → 拒绝
- 错误 `--real-confirm` → 拒绝
- `max_tasks!=1` → 拒绝
- 模式互斥 → 拒绝
- 正确双确认 → 通过（但不执行）

### T080 Real Confirm 拒绝验证

9 个场景全覆盖：
- 7 个错误 real-confirm 值全部拒绝（`yes`、`ok`、`确认`、`EXECUTE_PROJECT_LOOP`、`EXECUTE_REWORK`、`EXECUTE_REAL_TASK`、缺失）
- 1 个错误 execute confirm + 正确 real confirm → 仍被第一层拒绝
- 1 个正确双确认（对照组，不执行）

### T081 Pass 验证

17 个字段全部 PASS：
- `EXECUTION_MODE=real_call_dry_run_executor`
- `REAL_CALL_ALLOWED=True`
- `TASK_EXECUTION_PERFORMED=False`
- `AUTO_CONTINUE_TO_NEXT_TASK=False`
- `CHECK_RESULT=pass`

### T082 Fail-Stop 验证

8 个 fail-stop 设计约束全部 PASS：
1. fail → `CHECK_RESULT=fail`
2. fail → 不自动进入下一任务
3. fail → 不自动 Git 备份
4. fail → 需人工确认
5. fail → 不自动提交/推送
6. fail → 不自动返工
7. 异常 → fail
8. 无法确认字段输出 `unknown`

## Key Files

| 文件 | 说明 |
|------|------|
| `tools/continuous_task_planner.py` | RealCallSafetyResult（20 字段）、validate_real_call_safety()、RealCallDryRunExecutorResult（24 字段）、run_project_loop_real_call_dry_run_executor() |
| `runner.py` | `--real-call`、`--real-confirm`、`--real-call-dry-run` CLI 参数和输出分支 |
| `docs/run-project-loop-real-task-execution-safety-design.md` | T077 设计文档：21 个停止条件、双重确认协议、安全输出字段 |
| `reports/checks/T080-real-confirm-rejection-check.md` | T080 验证报告：9 个拒绝场景 |
| `reports/checks/T081-simulated-check-result-pass-check.md` | T081 验证报告：17 字段 PASS |
| `reports/checks/T082-simulated-check-result-fail-check.md` | T082 验证报告：8 fail-stop 约束 PASS |
| `docs/tasks.md` | 任务状态追踪 |

## Commit History

Stage 6 real-call safety MVP 提交链：

```
d332726 test: verify simulated check-result fail
0001ded test: verify simulated check-result pass
f5b36c4 test: verify real confirm rejection
5f78851 feat: add real-call dry-run executor
0837d3b feat: add real-call double-confirm safety gate
65e65f5 docs: design real task execution safety
```

## Recommended Next Step

**T084：设计真实调用 run-project-task-full 的最小实现协议**

注意：下一步仍然建议先设计，不直接实现真实执行。真实调用需要：
1. 设计 `run_project_loop_real_call_execute()` 函数
2. 设计 `RealCallExecuteResult` 数据结构
3. 设计 workspace 变化检测机制
4. 设计 `CLAUDE_CODE_CALLED` 和 `BUSINESS_CODE_CHANGED` 推断逻辑
5. 设计真实执行后的验证方案

## Final Status

```
REAL_CALL_SAFETY_MVP_STATUS=done
REAL_TASK_EXECUTION=no
RUN_PROJECT_TASK_FULL_CALLED=no
CLAUDE_CODE_CALLED=no
BUSINESS_CODE_CHANGED=no
AUTO_CONTINUE_TO_NEXT_TASK=no
AUTO_GIT_BACKUP=no
CHECK_RESULT=pass
NEXT_PENDING=T084
```
