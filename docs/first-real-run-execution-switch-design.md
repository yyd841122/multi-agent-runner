# First Real Run Execution Switch Design

## Background

Stage 7 已完成首次真实调用验收协议和模拟验收链路：

- **T091**：设计首次真实调用 run-project-task-full 的验收协议
- **T092**：实现 `FirstRealRunAcceptanceResult` 数据结构 + `evaluate_first_real_run_acceptance()`
- **T093**：实现 simulated first real-run acceptance parser（8 个内置 sample + CLI）
- **T094**：验证 first real-run acceptance pass/fail 场景（8/8 CLI + 53/53 断言）

当前系统具备：

- `--real-call-run-once`：进入 safety shell，构造 command/function_call 但不执行
- 双重确认：`--confirm EXECUTE_PROJECT_LOOP` + `--real-confirm EXECUTE_REAL_TASK_ONCE`
- `RealCallRunOnceResult`（26 字段）
- `ChildCommandParseResult`（20 字段）
- `FirstRealRunAcceptanceResult`（26 字段）
- `parse_child_command_output()`：解析 child stdout KEY=value 格式
- `evaluate_first_real_run_acceptance()`：评估验收状态
- `run_simulated_first_real_run_acceptance_parser()`：模拟验收链路
- `simulated-first-real-run-acceptance` CLI

当前系统仍然**没有**真实调用 `run_project_task_full()`。

## Goal

本设计定义首次真实调用 `run_project_task_full()` 的执行开关：

1. 新增 `--real-execute-once` 参数请求真实执行
2. 新增 `--real-execute-confirm EXECUTE_REAL_RUN_ONCE` 第三重确认
3. 定义真实执行 preflight checks
4. 定义真实执行流程
5. 定义真实执行输出字段
6. 定义失败停止规则
7. 定义 timeout / rate limit 处理策略

## Scope

| # | 范围 | 说明 |
|---|------|------|
| 1 | max_tasks=1 | 只执行一个 pending task |
| 2 | 单次真实调用 | 只调用一次 `run_project_task_full()` |
| 3 | Python 函数调用 | 同进程调用，不是 subprocess |
| 4 | 调用后立即进入 acceptance result | 复用已有验收协议 |
| 5 | 调用后立即停止 | 不自动进入下一任务 |
| 6 | 必须等待人工验收 | 不自动 Git backup |

## Non-goals

| # | 不做 | 原因 |
|---|------|------|
| 1 | max_tasks>1 真实执行 | 首次真实调用只验证单任务 |
| 2 | 连续任务自动执行 | 首次真实调用必须人工验收 |
| 3 | 自动 Git backup | 需要人工确认 workspace 变化 |
| 4 | 自动返工 | 需要人工确认 |
| 5 | 自动修复 | 需要人工确认 |
| 6 | 无人值守执行 | 首次真实调用必须人工验收 |
| 7 | 5 小时限额恢复 | 当前阶段不实现 |
| 8 | 外部触发执行 | 当前阶段不实现 |
| 9 | checkpoint / resume | 当前阶段不实现 |
| 10 | rate limit 自动恢复 | 当前阶段只 stop and report |

## Command Design

### 完整命令

```bash
python runner.py run-project-loop \
  --project . \
  --max-tasks 1 \
  --execute \
  --confirm EXECUTE_PROJECT_LOOP \
  --real-call \
  --real-confirm EXECUTE_REAL_TASK_ONCE \
  --real-call-run-once \
  --real-execute-once \
  --real-execute-confirm EXECUTE_REAL_RUN_ONCE
```

### 参数说明

| 参数 | 层级 | 作用 |
|------|------|------|
| `--execute` | 基础 | 进入 execute mode |
| `--confirm EXECUTE_PROJECT_LOOP` | 第一重确认 | 确认进入 execute mode |
| `--real-call` | 基础 | 请求 real-call 能力 |
| `--real-confirm EXECUTE_REAL_TASK_ONCE` | 第二重确认 | 确认 real-call 请求 |
| `--real-call-run-once` | 基础 | 进入 run-once 链路（safety shell 或真实执行） |
| `--real-execute-once` | 执行请求 | 请求真实执行一次（区别于 safety shell） |
| `--real-execute-confirm EXECUTE_REAL_RUN_ONCE` | 第三重确认 | 确认真实执行请求 |

### 参数依赖关系

```
--execute
  └── --confirm EXECUTE_PROJECT_LOOP       （第一重确认）
        └── --real-call
              └── --real-confirm EXECUTE_REAL_TASK_ONCE   （第二重确认）
                    └── --real-call-run-once
                          └── --real-execute-once
                                └── --real-execute-confirm EXECUTE_REAL_RUN_ONCE   （第三重确认）
```

### 无 --real-execute-once 时

当只有 `--real-call-run-once` 但没有 `--real-execute-once` 时，仍然只走 safety shell（当前已有行为），构造 command/function_call 但不执行。

```bash
# 这条命令只走 safety shell，不真实执行
python runner.py run-project-loop \
  --project . \
  --max-tasks 1 \
  --execute \
  --confirm EXECUTE_PROJECT_LOOP \
  --real-call \
  --real-confirm EXECUTE_REAL_TASK_ONCE \
  --real-call-run-once
```

## Triple Confirmation Protocol

### 三重确认设计

| 层级 | 参数 | 确认短语 | 语义 |
|------|------|----------|------|
| 第一重 | `--confirm` | `EXECUTE_PROJECT_LOOP` | 确认进入 execute mode |
| 第二重 | `--real-confirm` | `EXECUTE_REAL_TASK_ONCE` | 确认 real-call 请求 |
| 第三重 | `--real-execute-confirm` | `EXECUTE_REAL_RUN_ONCE` | 确认真实执行请求 |

### 第三重确认规则

| 输入 | 结果 |
|------|------|
| 缺少 `--real-execute-confirm` | 拒绝，real_execute_confirm_missing |
| `--real-execute-confirm yes` | 拒绝，real_execute_confirm_rejected |
| `--real-execute-confirm ok` | 拒绝，real_execute_confirm_rejected |
| `--real-execute-confirm 确认` | 拒绝，real_execute_confirm_rejected |
| `--real-execute-confirm EXECUTE_PROJECT_LOOP` | 拒绝，real_execute_confirm_rejected |
| `--real-execute-confirm EXECUTE_REAL_TASK_ONCE` | 拒绝，real_execute_confirm_rejected |
| `--real-execute-confirm EXECUTE_REAL_RUN_ONCE` | 通过 |

### 三个确认短语不能互相替代

- `EXECUTE_PROJECT_LOOP` 只能用于 `--confirm`
- `EXECUTE_REAL_TASK_ONCE` 只能用于 `--real-confirm`
- `EXECUTE_REAL_RUN_ONCE` 只能用于 `--real-execute-confirm`
- 任何错位都必须拒绝

## Preflight Checks

真实执行前必须**同时**满足以下所有条件：

| # | 检查项 | 检查方式 | 不满足时 |
|---|--------|----------|----------|
| 1 | workspace clean | `git status --short` | 拒绝 |
| 2 | execute safety gate pass | `validate_execute_loop_safety()` | 拒绝 |
| 3 | real-call safety gate pass | `validate_real_call_safety()` | 拒绝 |
| 4 | run-once safety shell pass | `run_project_loop_real_call_run_once_safety_shell()` | 拒绝 |
| 5 | first confirm accepted | `EXECUTE_PROJECT_LOOP` 精确匹配 | 拒绝 |
| 6 | real confirm accepted | `EXECUTE_REAL_TASK_ONCE` 精确匹配 | 拒绝 |
| 7 | real_execute_once requested | `--real-execute-once` 存在 | 拒绝 |
| 8 | real_execute_confirm accepted | `EXECUTE_REAL_RUN_ONCE` 精确匹配 | 拒绝 |
| 9 | max_tasks=1 | 参数检查 | 拒绝 |
| 10 | planned task 非空 | safety gate 返回 | 拒绝 |
| 11 | task_id 是 pending | 重新读取 tasks.md | 拒绝 |
| 12 | run_project_task_full 可调用 | 函数入口存在性检查 | 拒绝 |
| 13 | 无 pending rework | 检查 rework_manager | 拒绝 |
| 14 | 无未提交文件 | 检查 git status | 拒绝 |
| 15 | 无未备份变更 | 检查 git status | 拒绝 |
| 16 | 无 `--dry-run` | 互斥检查 | 拒绝 |
| 17 | 无 `--adapter-dry-run` | 互斥检查 | 拒绝 |
| 18 | 无 `--real-call-stub` | 互斥检查 | 拒绝 |
| 19 | 无 `--real-call-dry-run` | 互斥检查 | 拒绝 |

任一不满足必须输出：

```
REAL_TASK_EXECUTION=no
RUN_PROJECT_TASK_FULL_CALLED=no
CLAUDE_CODE_CALLED=no
BUSINESS_CODE_CHANGED=no
AUTO_CONTINUE_TO_NEXT_TASK=no
AUTO_GIT_BACKUP=no
HUMAN_REVIEW_REQUIRED=true
CHECK_RESULT=fail
```

### Preflight 复用策略

1-6 复用已有 `validate_real_call_safety()` + `run_project_loop_real_call_run_once_safety_shell()`
7-8 是新增第三重确认检查
9-19 复用已有 safety shell 的检查逻辑，部分在 safety shell 内部已实现

## Invocation Strategy

### 方案 A：Python 函数调用（推荐）

```python
from tools.full_task_runner import run_project_task_full

try:
    loop_result = run_project_task_full(
        project_path=subproject_path,
        task_id=task_id,
    )
except Exception as e:
    # CHECK_RESULT=fail, stop_reason=execution_exception
```

优点：

1. **已有稳定入口**：`run_project_task_full()` 在 `tools/full_task_runner.py` 已实现
2. **结构化返回**：直接获得 `FullTaskLoopResult` 对象，不需要解析 stdout
3. **无编码问题**：同进程执行，不需要处理 GBK/UTF-8
4. **无 shell 注入风险**：不经过 shell
5. **异常可直接捕获**：try/except 包裹
6. **前序设计已结论**：T077、T084 均推荐 Python 函数调用

缺点：

1. 函数调用超时需要额外机制（Windows signal.alarm 不完全支持）
2. 同进程执行，如果 `run_project_task_full()` 有严重错误可能影响外层

### 方案 B：subprocess 调用

```python
import subprocess

result = subprocess.run(
    ["python", "runner.py", "run-project-task-full",
     "--project", str(subproject_path), "--task", task_id],
    capture_output=True, text=True, timeout=600,
)
```

优点：

1. 进程隔离
2. 超时控制简单（timeout 参数）

缺点：

1. **需要解析 stdout**：Windows 编码可能有 GBK 乱码
2. **exit_code 语义有限**：只能区分进程级成功/失败
3. **路径和环境问题**：Python 路径、工作目录
4. **额外复杂度**：超过 MVP 需要

### 推荐方案：方案 A（Python 函数调用）

理由：

1. T077、T084 设计文档已有明确结论
2. `run_project_task_full()` 已有稳定实现
3. `FullTaskLoopResult` 已包含 final_status、steps、report_paths
4. 减少不必要的复杂度
5. 后续如需隔离可再改为 subprocess

## Execution Flow

```
1. preflight checks（复用 validate_real_call_safety() + safety shell）
   → 不通过 → 返回拒绝结果

2. 第三重确认检查
   → 缺少 --real-execute-once → 返回 safety shell 结果
   → 缺少 --real-execute-confirm → 拒绝
   → 确认短语错误 → 拒绝
   → 确认短语正确 → 继续

3. 生成 run_id

4. 记录 workspace before snapshot（git status --short → before_snapshot）

5. 解析 planned task（从 safety shell 结果获取 task_id 和 subproject_path）

6. 标记 RUN_PROJECT_TASK_FULL_CALLED=attempted

7. 真实调用 run_project_task_full(project_path, task_id)
   try:
       loop_result = run_project_task_full(project_path, task_id)
   except Exception as e:
       → CHECK_RESULT=fail, stop_reason=execution_exception

8. 捕获 FullTaskLoopResult

9. 映射 final_status → CHILD_CHECK_RESULT
   COMPLETE → pass
   REQUEST_CHANGES → fail
   BLOCKED → fail
   FAILED → fail
   None → missing

10. 记录 workspace after snapshot（git status --short → after_snapshot）

11. 比较 workspace 变化
    before == after → clean
    before != after → 分类变更

12. 分类 workspace changes（复用 _classify_workspace_changes）

13. 推断 CLAUDE_CODE_CALLED（复用 _infer_claude_code_called）

14. 推断 BUSINESS_CODE_CHANGED（复用 _infer_business_code_changed）

15. 收集 report_paths（从 loop_result.steps 收集非空 report_path）

16. 重新读取 tasks.md 获取 CHILD_TASK_STATUS

17. 构建 ChildCommandParseResult（适配 evaluate_first_real_run_acceptance 的输入）

18. 调用 evaluate_first_real_run_acceptance() 评估验收状态

19. 构建 FirstRealRunAcceptanceResult

20. 输出结构化最终结果

21. 停止等待人工验收
```

## Required Output Fields

首次真实执行完成后必须输出以下字段：

```
EXECUTION_MODE=first_real_run_execute_once
TASK_ID=<task_id>
REAL_TASK_EXECUTION=yes
RUN_PROJECT_TASK_FULL_CALLED=yes/attempted/no
REAL_EXECUTE_ONCE_REQUESTED=true
REAL_EXECUTE_CONFIRM_STATUS=accepted
CHILD_EXIT_CODE=not_applicable
CHILD_CHECK_RESULT=pass/fail/missing
CHILD_TASK_STATUS=done/failed/unknown
PARSE_CHECK_RESULT=not_applicable
ACCEPTANCE_STATUS=ready_for_human_review/blocked/failed_to_parse/unsafe_to_continue
CLAUDE_CODE_CALLED=yes/no/unknown
BUSINESS_CODE_CHANGED=yes/no/unknown
WORKSPACE_STATUS_BEFORE=clean
WORKSPACE_STATUS_AFTER=clean/dirty_reports_only/dirty_business_code/dirty_expected/dirty_unexpected/dirty_unknown
WORKSPACE_CHANGE_CLASSIFICATION=<same as WORKSPACE_STATUS_AFTER>
REPORT_PATHS=<paths>
AUTO_CONTINUE_TO_NEXT_TASK=false
AUTO_GIT_BACKUP=false
HUMAN_REVIEW_REQUIRED=true
STOP_REASON=<reason>
NEXT_ACTION=review_real_task_execution_result
CHECK_RESULT=pass/fail
```

### 拒绝场景输出

```
EXECUTION_MODE=first_real_run_execute_once
REAL_EXECUTE_ONCE_REQUESTED=true/false
REAL_EXECUTE_CONFIRM_STATUS=missing/rejected/accepted
REAL_TASK_EXECUTION=no
RUN_PROJECT_TASK_FULL_CALLED=no
CLAUDE_CODE_CALLED=no
BUSINESS_CODE_CHANGED=no
AUTO_CONTINUE_TO_NEXT_TASK=false
AUTO_GIT_BACKUP=false
HUMAN_REVIEW_REQUIRED=true
CHECK_RESULT=fail
STOP_REASON=<reason>
NEXT_ACTION=fix_real_execute_preconditions
```

## Execution Report

首次真实执行必须生成报告：

**路径**：`reports/checks/T096-first-real-run-execution-check.md`

报告至少包含：

| # | 内容 | 来源 |
|---|------|------|
| 1 | run_id | 生成 |
| 2 | task_id | planned task |
| 3 | 执行命令 | CLI 输入 |
| 4 | 三重确认状态 | 第一重/第二重/第三重 |
| 5 | preflight check 结果 | 19 项检查结果 |
| 6 | workspace before | git status --short |
| 7 | child execution result | FullTaskLoopResult |
| 8 | child stdout 摘要 | 不适用（函数调用） |
| 9 | child stderr 摘要 | 不适用（函数调用） |
| 10 | parser result | ChildCommandParseResult |
| 11 | acceptance result | FirstRealRunAcceptanceResult |
| 12 | workspace after | git status --short |
| 13 | workspace classification | _classify_workspace_changes |
| 14 | changed files | before/after diff |
| 15 | 是否调用 Claude Code | 推断结果 |
| 16 | 是否修改业务代码 | 推断结果 |
| 17 | 是否需要人工验收 | 是（硬编码） |
| 18 | 是否允许继续 | 否（硬编码） |
| 19 | 是否允许 Git backup | 否（硬编码） |

## Stop Rules

以下情况必须停止并等待人工处理：

### 前置条件拒绝

| # | 条件 | STOP_REASON |
|---|------|-------------|
| 1 | 缺少第三重确认 | real_execute_confirm_missing |
| 2 | 第三重确认错误 | real_execute_confirm_rejected |
| 3 | workspace dirty | workspace_not_clean |
| 4 | max_tasks != 1 | max_tasks_not_one |
| 5 | planned task 为空 | no_planned_tasks |
| 6 | task_id 非 pending | task_not_pending |
| 7 | run_project_task_full 不可调用 | function_not_available |

### 执行后失败

| # | 条件 | STOP_REASON |
|---|------|-------------|
| 8 | 调用抛出异常 | execution_exception |
| 9 | FullTaskLoopResult 为 None | missing_full_task_result |
| 10 | final_status 不是四种之一 | unexpected_final_status |
| 11 | CHILD_CHECK_RESULT=fail | child_check_result_failed |
| 12 | 缺少 CHECK_RESULT | missing_check_result |
| 13 | CHILD_TASK_STATUS=failed | child_task_status_failed |
| 14 | acceptance_status=failed_to_parse | failed_to_parse |
| 15 | acceptance_status=blocked | blocked |
| 16 | acceptance_status=unsafe_to_continue | unsafe_to_continue |
| 17 | workspace dirty_unknown | dirty_unknown |
| 18 | claude_code_called=unknown | （不阻塞，但标记 human_review） |
| 19 | business_code_changed=unknown | （不阻塞，但标记 human_review） |
| 20 | timeout | execution_timeout |
| 21 | exception | execution_exception |
| 22 | encoding error | execution_encoding_error |

### 失败后行为

所有失败场景必须：

- `AUTO_CONTINUE_TO_NEXT_TASK=false`
- `AUTO_GIT_BACKUP=false`
- `HUMAN_REVIEW_REQUIRED=true`
- `NEXT_ACTION=review_failure_before_continue`

## Timeout and Rate Limit Handling

### 当前阶段策略：Stop and Report

如果真实执行过程中出现 API 429 或 5 小时调用限制：

- **立即停止**，不自动等待恢复
- **记录错误**到执行报告
- **输出 rate_limit_detected=yes**
- **NEXT_ACTION=wait_for_rate_limit_reset**

### 不实现的能力

| # | 未来需求 | 说明 |
|---|----------|------|
| 1 | checkpoint | 保存当前执行状态（已完成的步骤、剩余步骤） |
| 2 | run state 持久化 | 将 `FirstRealRunAcceptanceResult` 保存到文件 |
| 3 | reset time 检测 | 检测 API 限额重置时间 |
| 4 | resume_allowed 判断 | 判断是否可以恢复执行 |
| 5 | 恢复后自动继续 | 从 checkpoint 处继续 |

### 记录未来需求

T095/T096 首次真实执行阶段不实现自动恢复。未来需要：

1. **checkpoint**：保存当前执行状态（已完成的步骤、剩余步骤）
2. **run state 持久化**：将 `FirstRealRunAcceptanceResult` 保存到文件
3. **reset time 检测**：检测 API 限额重置时间
4. **resume_allowed 判断**：判断是否可以恢复执行
5. **dirty workspace protection**：恢复前检查 workspace 是否被外部修改

## Validation Plan

### 至少 23 个验证场景

#### 阶段 A：前置条件拒绝（不真实执行）

| # | 场景 | 条件 | 预期 |
|---|------|------|------|
| 1 | 无 `--real-execute-once` | 只有 `--real-call-run-once` | 走 safety shell，不真实执行 |
| 2 | 有 `--real-execute-once` 但无第三重确认 | 缺少 `--real-execute-confirm` | 拒绝，real_execute_confirm_missing |
| 3 | 第三重确认 `yes` | `--real-execute-confirm yes` | 拒绝，real_execute_confirm_rejected |
| 4 | 第三重确认 `EXECUTE_PROJECT_LOOP` | 错位使用第一重短语 | 拒绝，real_execute_confirm_rejected |
| 5 | 第三重确认 `EXECUTE_REAL_TASK_ONCE` | 错位使用第二重短语 | 拒绝，real_execute_confirm_rejected |
| 6 | 第三重确认 `EXECUTE_REAL_RUN_ONCE` | 正确短语 | 通过，进入真实执行 preflight |
| 7 | max_tasks=2 | `--max-tasks 2` | 拒绝，max_tasks_not_one |
| 8 | workspace dirty | 有未提交变更 | 拒绝，workspace_not_clean |
| 9 | planned task 为空 | 无 pending 任务 | 拒绝，no_planned_tasks |
| 10 | run_project_task_full 不可调用 | 函数入口检查失败 | 拒绝，function_not_available |

#### 阶段 B：真实执行结果验收（使用模拟 FullTaskLoopResult）

| # | 场景 | 条件 | 预期 |
|---|------|------|------|
| 11 | child CHECK_RESULT=pass | final_status=COMPLETE | ready_for_human_review, 停止 |
| 12 | child CHECK_RESULT=fail | final_status=FAILED | blocked, 停止 |
| 13 | child 缺少 CHECK_RESULT | final_status=None | failed_to_parse, 停止 |
| 14 | child exit_code!=0 | 不适用（函数调用无 exit_code） | 不适用 |
| 15 | child stdout 解析失败 | 不适用（函数调用无 stdout） | 不适用 |
| 16 | child 产生 business code change | workspace 有 .py/.html 变更 | BUSINESS_CODE_CHANGED=yes, human review |
| 17 | child 产生 dirty_unknown | workspace 有变化但无法分类 | unsafe_to_continue, 停止 |

#### 阶段 C：停止和后备行为

| # | 场景 | 条件 | 预期 |
|---|------|------|------|
| 18 | pass 后不自动进入下一任务 | final_status=COMPLETE | AUTO_CONTINUE_TO_NEXT_TASK=false |
| 19 | pass 后不自动 Git backup | final_status=COMPLETE | AUTO_GIT_BACKUP=false |
| 20 | API 429 / rate limit | 执行中遇到 429 | 当前阶段 stop and report |
| 21 | timeout | 执行超时 | stop and report |
| 22 | exception | 执行抛出异常 | stop and report |
| 23 | pass 后仍需人工验收 | final_status=COMPLETE | HUMAN_REVIEW_REQUIRED=true, ACCEPTANCE_STATUS=ready_for_human_review |

## Recommended Implementation Roadmap

| 任务 | 角色 | 内容 |
|------|------|------|
| T096 | Developer | 实现 first real-run execute-once safety gate（第三重确认 + 新参数 + preflight 扩展） |
| T097 | Tester | 验证 execute-once 拒绝场景（阶段 A 场景 1-10） |
| T098 | Developer | 实现 first real-run executor simulated child call（模拟 FullTaskLoopResult 验证执行链路） |
| T099 | Tester | 验证 simulated real execution pass/fail（阶段 B 场景 11-17，使用模拟数据） |
| T100 | Developer | 执行第一次真实 run-project-task-full 调用（解除 simulated，连接真实执行） |
| T101 | Human | 人工验收第一次真实调用结果（使用验收清单） |

### T096 详细说明

实现内容：

- 新增 `--real-execute-once` CLI 参数
- 新增 `--real-execute-confirm` CLI 参数
- 新增第三重确认检查逻辑
- 新增 `run_project_loop_real_execute_once()` 函数骨架
- 复用 `validate_real_call_safety()` + safety shell 做前置检查
- preflight checks 扩展（task 状态检查、函数入口检查等）

不包含：

- 真实调用 `run_project_task_full()`
- 真实解析 `FullTaskLoopResult`

### T097 详细说明

验证拒绝场景（阶段 A 全部场景），确认第三重确认逻辑正确。

### T098 详细说明

实现模拟执行链路：

- 模拟 `FullTaskLoopResult` 输入
- 模拟 workspace 变化
- 复用 `evaluate_first_real_run_acceptance()` 评估验收状态
- 验证执行流程（snapshot → 调用 → snapshot → 分类 → 推断 → 验收 → 输出）

不包含：

- 真实调用 `run_project_task_full()`

### T099 详细说明

验证模拟执行 pass/fail 场景，确认执行链路正确。

### T100 详细说明

解除 simulated，连接真实 `run_project_task_full()`：
- 选择一个安全的子项目 pending 任务
- 执行 `run_project_task_full(project_path, task_id)`
- 捕获 `FullTaskLoopResult`
- 构建验收结果
- 停止等待人工确认

### T101 详细说明

人工验收：
- 使用 T091 设计的 10 项验收清单
- 逐项确认或标记问题
- 决定是否继续下一任务
- 决定是否执行 Git 提交

## Final Decision

| 决策项 | 结论 |
|--------|------|
| 执行开关 | `--real-execute-once` + `--real-execute-confirm EXECUTE_REAL_RUN_ONCE` |
| 第三重确认短语 | `EXECUTE_REAL_RUN_ONCE`（唯一有效值） |
| 首次真实执行范围 | max_tasks=1，单任务，Python 函数调用，执行后停止 |
| 是否自动进入下一任务 | 否，无论 pass/fail 都停止等待人工验收 |
| 是否自动 Git backup | 否，首次真实执行后需要人工确认 workspace 变化 |
| rate-limit recovery 是否本阶段实现 | 否，当前阶段只 stop and report，未来单独做 checkpoint resume |
| 调用方式 | Python 函数调用 `run_project_task_full(project_path, task_id)` |
| 下一步任务 | T096：实现 first real-run execute-once safety gate |
