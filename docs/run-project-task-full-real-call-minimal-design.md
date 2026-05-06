# Run Project Task Full Real Call Minimal Design

## Background

Real-call safety MVP 已完成（T077-T083）：

- **T077**：设计 21 个停止条件、双重确认协议、安全输出字段
- **T078**：实现 `validate_real_call_safety()`，RealCallSafetyResult（20 字段）
- **T079**：实现 `run_project_loop_real_call_dry_run_executor()`，RealCallDryRunExecutorResult（24 字段）
- **T080**：验证 9 个拒绝场景全部 PASS
- **T081**：验证 simulated CHECK_RESULT=pass，17 字段全部 PASS
- **T082**：验证 simulated CHECK_RESULT=fail，8 fail-stop 设计约束全部 PASS
- **T083**：生成 real-call safety MVP 小结

当前系统具备：

- `--real-call` / `--real-confirm EXECUTE_REAL_TASK_ONCE` / `--real-call-dry-run` CLI 参数
- `validate_real_call_safety()` 双重确认安全门
- `run_project_loop_real_call_dry_run_executor()` 构造 command/function_call 但不执行
- pass/fail 后都正确停止

当前系统仍然**没有**：

- 真实调用 `run_project_task_full()`
- 捕获真实 `FullTaskLoopResult`
- 解析真实 `CHECK_RESULT` / `TASK_STATUS`
- 识别真实 workspace 变化
- 推断 Claude Code 是否被调用
- 真实执行后的人工验收流程

## Goal

设计从 `run_project_loop_real_call_dry_run_executor()` 升级到真实调用 `run_project_task_full()` 的最小实现协议。

核心问题：

1. 用什么方式真实调用 `run_project_task_full()`
2. 如何捕获和解析 `FullTaskLoopResult`
3. 如何检查 workspace 变化
4. 如何推断 `CLAUDE_CODE_CALLED` 和 `BUSINESS_CODE_CHANGED`
5. 如何设计安全输出字段
6. 如何设计验证方案

## MVP Scope

| # | 能力 | 说明 |
|---|------|------|
| 1 | max_tasks=1 真实调用 | 只调用一个任务 |
| 2 | 双重确认 | EXECUTE_PROJECT_LOOP + EXECUTE_REAL_TASK_ONCE |
| 3 | 复用 safety gate | 9 层检查不变 |
| 4 | Python 函数调用 | 直接调用 `run_project_task_full()`，不是 subprocess |
| 5 | 捕获 FullTaskLoopResult | 解析 final_status 和 steps |
| 6 | CHECK_RESULT 映射 | COMPLETE → pass，其他 → fail |
| 7 | workspace 前后检查 | 执行前后 `git status --short` 比较 |
| 8 | CLAUDE_CODE_CALLED 推断 | 基于 steps 和 workspace 变化推断 |
| 9 | BUSINESS_CODE_CHANGED 推断 | 基于 workspace 变化分类 |
| 10 | 停止等待人工确认 | 无论 pass/fail 都停止 |

## Non-goals

| # | 不做 | 原因 |
|---|------|------|
| 1 | max_tasks>1 连续执行 | MVP 先验证单任务 |
| 2 | 自动进入下一任务 | 第一次真实调用必须人工验收 |
| 3 | 自动 Git commit/push | 需要人工确认 |
| 4 | 自动返工 | 需要人工确认 |
| 5 | 失败后继续执行 | 失败必须停止 |
| 6 | subprocess 调用 | Python 函数调用更简单 |
| 7 | 函数调用超时 | Claude Code 内部已有 600s 超时 |
| 8 | 跨仓库执行 | 超出 MVP 范围 |
| 9 | 无人值守长循环 | MVP 不做 |
| 10 | 自动部署 | 超出范围 |

## Command Design

### 外层命令

```bash
python runner.py run-project-loop \
  --project . \
  --max-tasks 1 \
  --execute \
  --confirm EXECUTE_PROJECT_LOOP \
  --real-call \
  --real-confirm EXECUTE_REAL_TASK_ONCE \
  --real-call-run-once
```

说明：

- `--real-call-run-once` 是新增参数，触发真实调用
- 不复用 `--real-call-dry-run`
- 不复用 `--real-call-stub`
- 必须和 `--real-call` + `--real-confirm` 同时使用

### 内层调用

```python
from tools.full_task_runner import run_project_task_full, FullTaskLoopResult

loop_result: FullTaskLoopResult = run_project_task_full(
    project_path=subproject_path,
    task_id=task_id,
)
```

当前 `run-project-task-full` CLI 入口在 `runner.py:1000-1036`：

```bash
python runner.py run-project-task-full --project <path> --task <task_id>
```

## Invocation Strategy

### 方案 A：Python 函数调用（推荐）

```python
from tools.full_task_runner import run_project_task_full

try:
    loop_result: FullTaskLoopResult = run_project_task_full(
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
6. **T077 设计文档已有结论**：直接函数调用更简单

缺点：

1. 函数调用超时需要额外机制（Windows signal.alarm 不完全支持）
2. 同进程执行，如果 `run_project_task_full()` 有严重错误可能影响外层

### 方案 B：subprocess 调用 runner.py

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

1. T077 设计文档已有明确结论
2. `run_project_task_full()` 已有稳定实现
3. `FullTaskLoopResult` 已包含 final_status、steps、report_paths
4. 减少不必要的复杂度
5. 后续如需隔离可再改为 subprocess

## Preflight Checks

真实调用前必须同时满足：

| # | 检查项 | 检查方式 | 不满足时 |
|---|--------|----------|----------|
| 1 | workspace clean | `git status --short` | 拒绝 |
| 2 | execute safety gate pass | `validate_execute_loop_safety()` | 拒绝 |
| 3 | first confirm accepted | `EXECUTE_PROJECT_LOOP` 精确匹配 | 拒绝 |
| 4 | real confirm accepted | `EXECUTE_REAL_TASK_ONCE` 精确匹配 | 拒绝 |
| 5 | max_tasks=1 | 参数检查 | 拒绝 |
| 6 | planned_tasks 非空 | safety gate 返回 | 拒绝 |
| 7 | task_id 合法 | 前缀匹配 | 拒绝 |
| 8 | task 当前状态是 pending | 重新读取 tasks.md | 拒绝 |
| 9 | run_project_task_full 可调用 | 函数入口存在性检查 | 拒绝 |
| 10 | 无 pending rework | 检查 rework_manager | 拒绝 |
| 11 | 无未提交报告 | 检查 reports/ 目录 | 拒绝 |
| 12 | 无未备份变更 | 检查 git status | 拒绝 |
| 13 | 无 --adapter-dry-run | 互斥检查 | 拒绝 |
| 14 | 无 --real-call-stub | 互斥检查 | 拒绝 |
| 15 | 无 --real-call-dry-run | 互斥检查 | 拒绝 |
| 16 | 无 --dry-run | 互斥检查 | 拒绝 |

任一不满足必须输出：

```
REAL_TASK_EXECUTION=no
RUN_PROJECT_TASK_FULL_CALLED=no
CLAUDE_CODE_CALLED=no
BUSINESS_CODE_CHANGED=no
CHECK_RESULT=fail
HUMAN_REVIEW_REQUIRED=true
```

## Execution Flow

```
1. preflight check（复用 validate_real_call_safety()）
   → 不通过 → 返回拒绝结果

2. 额外 preflight
   → task 状态不是 pending → 拒绝
   → --real-call-dry-run 同时存在 → 拒绝

3. 快照 workspace（git status --short → before_snapshot）

4. 解析 subproject_path

5. 标记 RUN_PROJECT_TASK_FULL_CALLED=attempted

6. 真实调用 run_project_task_full(project_path, task_id)
   try:
       loop_result = run_project_task_full(project_path, task_id)
   except Exception as e:
       → CHECK_RESULT=fail, stop_reason=execution_exception

7. 捕获 FullTaskLoopResult

8. 映射 final_status → CHECK_RESULT
   COMPLETE → pass
   REQUEST_CHANGES → fail
   BLOCKED → fail
   FAILED → fail

9. 快照 workspace（git status --short → after_snapshot）

10. 比较 workspace 变化
    before == after → clean
    before != after → 分类变更

11. 推断 CLAUDE_CODE_CALLED
    有 Developer step 且 success → yes
    无 steps → no
    有变化但无 Developer success → unknown

12. 推断 BUSINESS_CODE_CHANGED
    clean → no
    有 .html/.css/.js/.py 等变化（排除 reports/ docs/）→ yes
    有变化但无法分类 → unknown

13. 重新读取 tasks.md 获取 TASK_STATUS

14. 收集 report_paths

15. 输出 RealCallRunOnceResult

16. 停止，等待人工确认
```

## Output Parsing Rules

### 输入来源

`FullTaskLoopResult` 包含：

```python
@dataclass
class FullTaskLoopResult:
    project_path: str
    task_id: str
    final_status: str           # COMPLETE / REQUEST_CHANGES / BLOCKED / FAILED
    steps: list[FullTaskStepResult]
    full_loop_report_path: str | None
    next_action: str
```

### 解析规则

| 输出字段 | 解析来源 | 规则 |
|----------|----------|------|
| `TASK_ID` | `loop_result.task_id` | 直接取值 |
| `CHECK_RESULT` | `loop_result.final_status` | COMPLETE → pass，其他 → fail |
| `TASK_STATUS` | 重新读取 tasks.md | 读取任务实际状态 |
| `FINAL_STATUS` | `loop_result.final_status` | 直接取值 |
| `BUSINESS_CODE_CHANGED` | workspace 变化分类 | yes/no/unknown |
| `CLAUDE_CODE_CALLED` | steps + workspace 推断 | yes/no/unknown |
| `REPORT_PATHS` | `loop_result.steps[*].report_path` | 收集非空 report_path |
| `WORKTREE_STATUS` | `git status --short` | 执行后比较 |
| `FULL_LOOP_REPORT` | `loop_result.full_loop_report_path` | 直接取值 |

### 缺失字段处理

| 缺失情况 | 处理 |
|----------|------|
| `final_status` 为 None | CHECK_RESULT=fail, stop_reason=missing_final_status |
| `final_status` 不是四种之一 | CHECK_RESULT=fail, stop_reason=unexpected_final_status |
| `steps` 为空 | CHECK_RESULT=fail, stop_reason=empty_steps |
| `full_loop_report_path` 为 None | 警告但继续，标记 report_missing |
| `CLAUDE_CODE_CALLED` 无法确认 | 输出 unknown，不写 no |
| `BUSINESS_CODE_CHANGED` 无法分类 | 输出 unknown |

### final_status → CHECK_RESULT 映射

| final_status | CHECK_RESULT | 后续行为 |
|--------------|-------------|----------|
| COMPLETE | pass | 停止等待人工确认 |
| REQUEST_CHANGES | fail | 停止等待人工处理 |
| BLOCKED | fail | 停止等待人工处理 |
| FAILED | fail | 停止等待人工处理 |
| 异常 | fail | 停止等待人工处理 |

## Workspace Classification

### 执行前快照

```python
def _snapshot_workspace(project_root: Path) -> set[str]:
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=str(project_root),
        capture_output=True, text=True,
    )
    return set(result.stdout.strip().splitlines()) if result.stdout.strip() else set()
```

### 执行后比较和分类

```python
def _classify_workspace_changes(
    before: set[str], after: set[str]
) -> tuple[str, list[str]]:
    new_files = after - before
    if not new_files:
        return "clean", []

    changed = list(new_files)

    # 预期变更前缀
    expected_prefixes = ("reports/", "docs/tasks.md")
    unexpected = [f for f in changed
                  if not any(f.startswith(p) for p in expected_prefixes)]

    if unexpected:
        return "dirty_unexpected", changed
    return "dirty_expected", changed
```

### 结果分类

| 分类 | 说明 | BUSINESS_CODE_CHANGED |
|------|------|----------------------|
| clean | 无文件变化 | no |
| dirty_expected | 只有报告/docs/tasks.md 变化 | no |
| dirty_unexpected | 有未知变化 | unknown 或 yes |
| dirty_business_code | .html/.css/.js/.py 等变化 | yes |

如果无法分类：

```
WORKTREE_STATUS=dirty_unknown
BUSINESS_CODE_CHANGED=unknown
HUMAN_REVIEW_REQUIRED=true
```

## CLAUDE_CODE_CALLED Inference

```python
def _infer_claude_code_called(
    loop_result: FullTaskLoopResult,
    workspace_status: str,
) -> str:
    # 无 steps → 未调用
    if not loop_result.steps:
        return "no"

    # 有 Developer step 且 success → 已调用
    for step in loop_result.steps:
        if step.name == "Developer" and step.success:
            return "yes"

    # workspace 有变化 → unknown
    if workspace_status != "clean":
        return "unknown"

    # 默认 unknown（宁可多报告）
    return "unknown"
```

## BUSINESS_CODE_CHANGED Inference

```python
def _infer_business_code_changed(
    workspace_status: str,
    changed_files: list[str],
) -> str:
    if workspace_status == "clean":
        return "no"

    business_extensions = (".html", ".css", ".js", ".py", ".yaml", ".json")
    business_files = [
        f for f in changed_files
        if any(f.strip().endswith(ext) for ext in business_extensions)
        and not f.strip().startswith(("reports/", "docs/"))
    ]

    if business_files:
        return "yes"

    return "unknown"
```

## Post Execution Stop Rules

### 无论 pass/fail 都停止

即使真实调用返回 CHECK_RESULT=pass（final_status=COMPLETE），MVP 也必须停止：

```
AUTO_CONTINUE_TO_NEXT_TASK=no
AUTO_GIT_BACKUP=no
HUMAN_REVIEW_REQUIRED=true
NEXT_ACTION=review_real_task_execution_result
```

### 停止原因

| final_status | CHECK_RESULT | 停止原因 | loop_status |
|--------------|-------------|----------|-------------|
| COMPLETE | pass | real_task_execution_completed | task_execution_completed |
| REQUEST_CHANGES | fail | rework_required | stopped_on_rework_required |
| BLOCKED | fail | task_blocked | stopped_on_task_blocked |
| FAILED | fail | task_failed | stopped_on_task_failed |
| 异常 | fail | execution_exception | stopped_on_task_failed |

### 为什么 pass 后也停止

1. 第一个真实调用必须人工验收
2. 业务代码可能已变更，需要人工确认
3. Claude Code 是否调用需确认（输出 unknown，不是确认值）
4. Git 备份策略尚未自动化
5. 这是 MVP 安全边界，不是长期限制

## Safety Output Fields

### 拒绝场景输出

```
EXECUTION_MODE=real_call_run_once
REAL_CALL_REQUESTED=true
REAL_TASK_EXECUTION=no
RUN_PROJECT_TASK_FULL_CALLED=no
CLAUDE_CODE_CALLED=no
BUSINESS_CODE_CHANGED=no
CHECK_RESULT=fail
LOOP_STATUS=preflight_failed
STOP_REASON=<reason>
HUMAN_REVIEW_REQUIRED=true
NEXT_ACTION=fix_real_call_preconditions
```

### 真实执行后输出

```
EXECUTION_MODE=real_call_run_once
REAL_CALL_REQUESTED=true
REAL_TASK_EXECUTION=yes
RUN_PROJECT_TASK_FULL_CALLED=yes
CLAUDE_CODE_CALLED=yes/no/unknown
BUSINESS_CODE_CHANGED=yes/no/unknown
TASK_ID=<task_id>
FINAL_STATUS=COMPLETE/FAILED/BLOCKED/REQUEST_CHANGES
CHECK_RESULT=pass/fail
TASK_STATUS=done/failed/unknown
FULL_LOOP_REPORT=<path>
REPORT_PATHS=...
WORKTREE_STATUS=clean/dirty/dirty_unknown
AUTO_CONTINUE_TO_NEXT_TASK=no
AUTO_GIT_BACKUP=no
HUMAN_REVIEW_REQUIRED=true
LOOP_STATUS=<status>
STOP_REASON=<reason>
NEXT_ACTION=review_real_task_execution_result
```

### RealCallRunOnceResult 数据结构

```python
@dataclass
class RealCallRunOnceResult:
    """Real-call run-once 结果（max_tasks=1 真实执行）。"""

    # 标识
    project: str
    run_id: str
    execution_mode: str                       # "real_call_run_once"
    real_call_requested: bool                 # True
    max_tasks: int                            # 1

    # 确认状态
    first_confirm_accepted: bool              # EXECUTE_PROJECT_LOOP
    real_confirm_accepted: bool               # EXECUTE_REAL_TASK_ONCE

    # 执行状态
    task_id: str | None
    command: str                              # 实际执行的命令描述
    function_call: str                        # 实际执行的函数调用
    real_task_execution: bool                 # 是否真实执行了任务
    run_project_task_full_called: str         # "yes"/"no"/"attempted"
    claude_code_called: str                   # "yes"/"no"/"unknown"
    business_code_changed: str                # "yes"/"no"/"unknown"

    # 结果
    final_status: str | None                  # FullTaskLoopResult.final_status
    check_result: str                         # "pass"/"fail"
    task_status: str                          # 执行后任务实际状态
    exception_message: str | None             # 异常时记录

    # 报告
    full_loop_report_path: str | None
    report_paths: list[str]

    # Workspace
    worktree_status: str                      # clean/dirty/dirty_unknown

    # 停止
    loop_status: str
    stop_reason: str | None
    human_review_required: bool               # 始终 True
    auto_continue: bool                       # 始终 False
    auto_git_backup: bool                     # 始终 False

    # 建议
    next_action: str
    message: str
```

## Timeout and Error Handling

### 超时

- MVP 阶段先不做函数调用超时
- Claude Code 内部已有 600s 超时
- 后续如需超时，可改用 subprocess 隔离或 threading.Timer

### 异常处理

```python
try:
    loop_result = run_project_task_full(project_path, task_id)
except Exception as e:
    return RealCallRunOnceResult(
        ...
        real_task_execution=True,
        run_project_task_full_called="attempted",
        check_result="fail",
        exception_message=str(e),
        stop_reason="execution_exception",
        ...
    )
```

### stdout/stderr

- 函数调用不需要处理 stdout/stderr
- `run_project_task_full()` 内部已有输出管理

### 编码

- 函数调用无编码问题
- 同进程执行，不需要处理 GBK/UTF-8

### Windows 兼容

- 所有路径使用 `pathlib.Path`
- 函数调用不依赖 shell
- `git status --short` 通过 `subprocess.run` 调用，已验证可工作

## Validation Plan

### 阶段 A：拒绝场景验证（不真实执行）

| # | 场景 | 命令/条件 | 预期结果 |
|---|------|----------|----------|
| 1 | 没有 --real-call-run-once | `--execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-dry-run` | 走 dry-run executor，不触发 run-once |
| 2 | 有 --real-call-run-once 但无 --real-confirm | `--execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-call-run-once` | 拒绝，REAL_TASK_EXECUTION=no |
| 3 | real-confirm 错误 | `--real-call --real-confirm yes --real-call-run-once` | 拒绝，real_confirm_rejected |
| 4 | max_tasks=0 | `--max-tasks 0 --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-run-once` | 拒绝，safety_gate_failed |
| 5 | max_tasks=2 | `--max-tasks 2 --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-run-once` | 拒绝，max_tasks_not_one |
| 6 | workspace dirty | 有未提交变更 | 拒绝，workspace_not_clean |
| 7 | planned_tasks 为空 | 无 pending 任务 | 拒绝，no_planned_tasks |
| 8 | --real-call-run-once + --real-call-dry-run | 同时传入 | 拒绝，mode_conflict |
| 9 | --real-call-run-once + --adapter-dry-run | 同时传入 | 拒绝，mode_conflict |
| 10 | --real-call-run-once + --real-call-stub | 同时传入 | 拒绝，mode_conflict |
| 11 | --real-call-run-once + --dry-run | 同时传入 | 拒绝，mode_conflict |

### 阶段 B：真实执行验证（需要 Claude Code 和子项目任务）

| # | 场景 | 条件 | 预期结果 |
|---|------|------|----------|
| 12 | child final_status=COMPLETE | 选择安全子项目任务真实执行 | CHECK_RESULT=pass, 停止等待人工确认 |
| 13 | child final_status=FAILED | 真实执行失败 | CHECK_RESULT=fail, 停止 |
| 14 | child 异常 | run_project_task_full 抛异常 | CHECK_RESULT=fail, execution_exception, 停止 |
| 15 | child 缺少 final_status | 返回值异常 | CHECK_RESULT=fail, missing_final_status, 停止 |
| 16 | child 产生 business code change | 真实执行后 git diff 有变化 | BUSINESS_CODE_CHANGED=yes/unknown, 停止 |
| 17 | child 产生 report only change | 只有报告变化 | BUSINESS_CODE_CHANGED=no, 停止 |
| 18 | child 后 workspace dirty_unknown | 有变化但无法分类 | WORKTREE_STATUS=dirty_unknown, 停止 |
| 19 | pass 后不自动进入下一任务 | final_status=COMPLETE | AUTO_CONTINUE_TO_NEXT_TASK=no |
| 20 | pass 后不自动 Git 备份 | final_status=COMPLETE | AUTO_GIT_BACKUP=no |
| 21 | CLAUDE_CODE_CALLED 输出 unknown | 真实执行后无法确认 | CLAUDE_CODE_CALLED=yes（有 Developer step success）或 unknown |

**注意**：阶段 B 验证需要选择一个安全的子项目任务并确认 Claude Code 可用。建议使用 G008 或新任务作为首次真实执行验证目标。

## Recommended Implementation Roadmap

| 任务 | 角色 | 内容 |
|------|------|------|
| T085 | Developer | 实现 real-call run-once safety shell（RealCallRunOnceResult 数据结构 + `run_project_loop_real_call_run_once()` 函数骨架 + preflight checks） |
| T086 | Developer | 实现 child command parser（FullTaskLoopResult 解析 + workspace 检测 + CLAUDE_CODE_CALLED/BUSINESS_CODE_CHANGED 推断），但真实调用部分仍用 simulated 结果 |
| T087 | Tester | 验证 real-call-run-once 拒绝场景（阶段 A 场景 1-11） |
| T088 | Tester | 验证 simulated child CHECK_RESULT=pass（阶段 B 部分，使用模拟数据） |
| T089 | Tester | 验证 simulated child CHECK_RESULT=fail（阶段 B 部分，使用模拟数据） |
| T090 | Developer | 实现真实调用（解除 simulated，连接真实 `run_project_task_full()`） |
| T091 | Tester | 验证真实执行（阶段 B 全部场景，需要 Claude Code 可用） |
| T092 | Reporter | 提交并推送 real-call run-once MVP |

### T085 详细说明

实现内容：

- `RealCallRunOnceResult` 数据结构（26+ 字段）
- `run_project_loop_real_call_run_once()` 函数骨架
- 复用 `validate_real_call_safety()` 做前置检查
- 额外 preflight（--real-call-dry-run 互斥等）
- runner.py 新增 `--real-call-run-once` 参数
- 拒绝场景全覆盖

不包含：

- 真实调用 `run_project_task_full()`
- 真实解析 `FullTaskLoopResult`
- 真实 workspace 变化检测

### T086 详细说明

实现内容：

- `_snapshot_workspace()` 函数
- `_classify_workspace_changes()` 函数
- `_infer_claude_code_called()` 函数
- `_infer_business_code_changed()` 函数
- 模拟 FullTaskLoopResult 输入解析

不包含：

- 真实调用 `run_project_task_full()`

### T087 验证范围

阶段 A 场景 1-11：全部拒绝场景，不涉及真实调用。

### T088-T089 验证范围

阶段 B 部分：使用模拟 FullTaskLoopResult 数据验证解析和推断逻辑。

### T090 真实调用

解除 simulated，连接真实 `run_project_task_full()`。

### T091 真实执行验证

需要 Claude Code 可用 + 安全子项目任务。

## Final Design Decision

| 决策项 | 结论 |
|--------|------|
| 外层命令 | `python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP --real-call --real-confirm EXECUTE_REAL_TASK_ONCE --real-call-run-once` |
| 内层调用方式 | Python 函数调用 `run_project_task_full(project_path, task_id)` |
| 是否真实执行 | 是，但 MVP 阶段通过 simulated → real 两步实现 |
| 首个真实调用范围 | max_tasks=1 单任务，函数调用 |
| 是否自动进入下一任务 | 否，无论 pass/fail 都停止等待人工确认 |
| 是否自动 Git 备份 | 否，需要人工确认 |
| CLAUDE_CODE_CALLED 默认值 | unknown（无法确认时输出 unknown，不写 no） |
| BUSINESS_CODE_CHANGED 默认值 | unknown（有变更但无法分类时输出 unknown） |
| 下一步任务 | T085：实现 real-call run-once safety shell |
