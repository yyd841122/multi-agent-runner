# Run Project Loop Real Task Execution Safety Design

## Background

Task execution bridge MVP（T070-T076）已完成：

- **T070**：task execution bridge 设计（14 个停止条件、安全输出字段）
- **T071**：adapter dry-run（TaskExecutionResult / ProjectLoopExecutionResult）
- **T072**：adapter 不真实执行验证（4 场景 PASS）
- **T073**：real-call stub（RealCallStubResult / run_project_loop_real_call_stub()）
- **T074**：CHECK_RESULT=pass 后停止验证（13 字段 PASS）
- **T075**：CHECK_RESULT=fail 后停止验证（三层验证 PASS）

当前系统状态：

```text
run-project-loop --execute --confirm EXECUTE_PROJECT_LOOP --real-call-stub
→ safety gate pass
→ 构造 run_project_task_full(project_path, task_id) 调用信息
→ 不执行
→ RealCallStubResult(check_result=pass, task_execution_performed=false)
→ 停止
```

已有 `run_project_task_full()` 函数（`tools/full_task_runner.py`），可执行单任务完整闭环：

- Developer → Basic Tester → Specialized Tester → Reviewer → Main Decision
- 返回 `FullTaskLoopResult`：project_path, task_id, final_status, steps, full_loop_report_path, next_action

**缺失环节**：从 real-call stub 升级到真实调用 `run_project_task_full()`。

## Goal

设计 `run-project-loop --real-call` 从 stub 升级到真实调用 `run_project_task_full()` 的安全协议。

核心问题：

1. 如何安全地从 stub 切换到真实调用
2. 如何引入第二重确认防止误调用
3. 如何捕获和解析 `FullTaskLoopResult`
4. 如何检查 workspace 变化
5. 如何判断执行结果并停止
6. 如何安全输出所有字段

## MVP Scope

| # | 能力 | 说明 |
|---|------|------|
| 1 | max_tasks=1 真实调用 | 只调用一个任务 |
| 2 | 双重确认 | EXECUTE_PROJECT_LOOP + EXECUTE_REAL_TASK_ONCE |
| 3 | 复用 safety gate | 9 项前置检查不变 |
| 4 | 直接函数调用 | 调用 `run_project_task_full()`，不是 subprocess |
| 5 | 收集 FullTaskLoopResult | 解析 final_status 和 steps |
| 6 | 检查 CHECK_RESULT | 基于 final_status 判断 pass/fail |
| 7 | 检查 workspace status | 执行前后比较 git status |
| 8 | 检查 Claude Code 调用 | 基于 final_status 和 steps 推断 |
| 9 | 生成 RealCallExecuteResult | 结构化输出 |
| 10 | 停止等待人工确认 | 执行后停止，不自动进入下一任务 |

## Non-goals

| # | 不做 | 原因 |
|---|------|------|
| 1 | max_tasks>1 真实连续执行 | MVP 先验证单任务 |
| 2 | 自动进入下一任务 | 第一次真实调用必须人工验收 |
| 3 | 自动 Git commit/push | push 需要人工确认 |
| 4 | 自动返工真实执行 | 返工需要人工确认 |
| 5 | 失败后继续执行 | 失败必须停止 |
| 6 | 自动部署 | 超出当前范围 |
| 7 | 跨仓库任务执行 | 超出当前范围 |
| 8 | 无人值守长循环 | MVP 不做 |
| 9 | 长期后台运行 | 超出当前范围 |
| 10 | subprocess 调用 | 当前直接函数调用更简单 |

## Confirmation Protocol

### 双重确认设计

真实调用需要两重确认：

**第一重确认**（已有）：进入 execute mode

```
--execute --confirm EXECUTE_PROJECT_LOOP
```

这是 T065 safety gate 的确认，允许进入 execute 模式。这一层确认不足以触发真实调用。

**第二重确认**（新增）：允许真实执行单任务

```
--real-call --real-confirm EXECUTE_REAL_TASK_ONCE
```

这是新增的真实调用确认，与 stub 确认分离。

### 确认短语规则

| 确认短语 | 用途 | 说明 |
|----------|------|------|
| `EXECUTE_PROJECT_LOOP` | 第一重：进入 execute mode | 已有，不变 |
| `EXECUTE_REAL_TASK_ONCE` | 第二重：允许真实调用 | 新增 |

拒绝规则：

| 输入 | 结果 |
|------|------|
| 缺少 `--real-confirm` | 拒绝，提示需要 EXECUTE_REAL_TASK_ONCE |
| `yes` | 拒绝 |
| `ok` | 拒绝 |
| `确认` | 拒绝 |
| `EXECUTE_PROJECT_LOOP` | 拒绝（这是第一重确认，不能替代第二重） |
| `EXECUTE_REAL_TASK_ONCE` | 通过 |

### 为什么需要双重确认

1. `EXECUTE_PROJECT_LOOP` 只代表"我知道要执行"，不代表"我要真实调用 Claude Code"
2. `--real-call-stub` 也需要 `EXECUTE_PROJECT_LOOP`，但它不执行真实调用
3. 第二重确认 `EXECUTE_REAL_TASK_ONCE` 明确表示"我知道这会真实调用 Claude Code 并可能修改业务代码"
4. 两层确认分开，减少误操作风险

## CLI Design

### 方案 A：扩展现有 run-project-loop

```bash
python runner.py run-project-loop \
  --project . \
  --max-tasks 1 \
  --execute \
  --confirm EXECUTE_PROJECT_LOOP \
  --real-call \
  --real-confirm EXECUTE_REAL_TASK_ONCE
```

优点：
- 复用已有 planner / safety gate / max_tasks 限制
- 不新增命令，用户学习成本低
- 后续扩展 max_tasks>1 只需修改 `--max-tasks` 参数
- 与 `--adapter-dry-run` / `--real-call-stub` 参数风格一致
- n8n/API 接入只需拼参数，不需要新命令

缺点：
- 参数较多（7 个），但大部分有默认值
- 需要在 runner.py 中增加参数解析逻辑

### 方案 B：新增独立命令

```bash
python runner.py run-project-loop-real-once \
  --project . \
  --task <task_id> \
  --confirm EXECUTE_REAL_TASK_ONCE
```

优点：
- 命令简洁，参数少
- 职责更聚焦

缺点：
- 不复用 planner，需要自己读取任务列表和选择 pending task
- 不复用 execute safety gate，需要重新实现前置检查
- 不复用 max_tasks 限制
- 绕过了已有的分层安全机制
- 后续扩展 max_tasks>1 需要新命令或重写
- n8n/API 接入需要学习新命令

### 推荐方案：方案 A

理由：

1. **不绕过已有 planner**：方案 A 复用 `build_continuous_task_plan()` 选择任务
2. **不绕过 safety gate**：方案 A 先通过第一重确认，再通过第二重确认
3. **不绕过 max_tasks=1 限制**：方案 A 复用已有 max_tasks 检查
4. **参数互斥清晰**：`--adapter-dry-run` / `--real-call-stub` / `--real-call` 三者互斥
5. **后续扩展容易**：放开 max_tasks>1 时只需修改 `--max-tasks` 和内部逻辑
6. **n8n/API 友好**：只需拼参数，不需要新命令

### 参数互斥规则

```
--adapter-dry-run     → adapter dry-run 模式
--real-call-stub      → real-call stub 模式
--real-call            → 真实调用模式（新增）
（无上述参数）          → execute stub 模式（T066）
```

四个模式互斥，一次只能选一个。

## Preflight Checks

真实调用前必须同时满足以下检查：

| # | 检查项 | 检查方式 | 不满足时 |
|---|--------|----------|----------|
| 1 | workspace clean | `git status --short` | 拒绝 |
| 2 | execute safety gate pass | `validate_execute_loop_safety()` | 拒绝 |
| 3 | first confirm accepted | `EXECUTE_PROJECT_LOOP` 精确匹配 | 拒绝 |
| 4 | real confirm accepted | `EXECUTE_REAL_TASK_ONCE` 精确匹配 | 拒绝 |
| 5 | max_tasks=1 | 参数检查 | 拒绝 |
| 6 | planned_tasks 非空 | safety gate 返回 | 拒绝 |
| 7 | task_id 合法 | 前缀匹配（G → projects/down-100-floors-game 等） | 拒绝 |
| 8 | run_project_task_full 可调用 | 函数入口存在性检查 | 拒绝 |
| 9 | 当前任务不是 done | 重新读取 tasks.md | 拒绝 |
| 10 | 无 pending rework | 检查 rework_manager | 拒绝 |
| 11 | 无未提交报告 | 检查 reports/ 目录状态 | 拒绝 |
| 12 | 无未备份变更 | 检查 git status | 拒绝 |
| 13 | 无模式冲突 | `--adapter-dry-run` / `--real-call-stub` / `--real-call` 互斥 | 拒绝 |

任一不满足时必须输出：

```
REAL_TASK_EXECUTION=no
RUN_PROJECT_TASK_FULL_CALLED=no
CLAUDE_CODE_CALLED=no
BUSINESS_CODE_CHANGED=no
CHECK_RESULT=fail
HUMAN_REVIEW_REQUIRED=true
```

## Execution Method

### 推荐：Python 函数调用

```python
from tools.full_task_runner import run_project_task_full, FullTaskLoopResult

try:
    loop_result: FullTaskLoopResult = run_project_task_full(
        project_path=subproject_path,
        task_id=task_id,
    )
except Exception as e:
    # 捕获异常 → CHECK_RESULT=fail, stop_reason=execution_exception
```

### 为什么用函数调用而非 subprocess

1. **已有稳定入口**：`run_project_task_full()` 在 `tools/full_task_runner.py:415` 已实现
2. **结构化返回**：直接获得 `FullTaskLoopResult` 对象，不需要解析 stdout
3. **无环境问题**：同进程执行，不需要处理编码（GBK/UTF-8）、路径、环境变量
4. **无 shell 注入风险**：不经过 shell
5. **异常可直接捕获**：try/except 包裹，不需要解析退出码
6. **T070 设计文档已有结论**：直接函数调用更简单，后续如需隔离可再改为 subprocess

### 超时设计

虽然函数调用不使用 subprocess，但 `run_project_task_full()` 内部会调用 Claude Code，可能长时间运行：

```python
import signal

def _timeout_handler(signum, frame):
    raise TimeoutError("run_project_task_full 超时")

# 注意：Windows 不完全支持 signal.alarm
# MVP 可先不做超时，后续用 threading.Timer 或 subprocess 隔离
```

MVP 阶段建议：
- 先不做函数调用超时（Claude Code 内部已有 600s 超时）
- 后续如果需要超时，改用 subprocess 隔离

### Windows / bash 兼容

函数调用方式不存在 shell 兼容问题。所有路径使用 `pathlib.Path`，不依赖 shell。

## Output Parsing Rules

### 输入来源

`FullTaskLoopResult` 包含：

```python
@dataclass
class FullTaskLoopResult:
    project_path: str           # 子项目路径
    task_id: str                # 任务 ID
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
| `BUSINESS_CODE_CHANGED` | git diff 比较 | 执行前后比较，有变更 → yes/unknown，无变更 → no |
| `CLAUDE_CODE_CALLED` | 推断 | final_status=COMPLETE 且 steps 含 Developer PASS → unknown（无法确认） |
| `REPORT_PATHS` | `loop_result.steps[*].report_path` | 收集所有非空 report_path |
| `WORKTREE_STATUS` | `git status --short` | 执行后检查 |
| `FULL_LOOP_REPORT` | `loop_result.full_loop_report_path` | 直接取值 |

### 缺失字段处理

| 缺失情况 | 处理 |
|----------|------|
| 缺少 `final_status` | CHECK_RESULT=fail, stop_reason=missing_final_status |
| 缺少 `full_loop_report_path` | 警告但继续，标记 report_missing |
| `final_status` 不是四种之一 | CHECK_RESULT=fail, stop_reason=unexpected_final_status |
| `steps` 为空 | CHECK_RESULT=fail, stop_reason=empty_steps |
| `CLAUDE_CODE_CALLED` 无法确认 | 输出 unknown，不写 no |

### final_status → CHECK_RESULT 映射

| final_status | CHECK_RESULT | 后续行为 |
|--------------|-------------|----------|
| COMPLETE | pass | 停止等待人工确认 |
| REQUEST_CHANGES | fail | 停止等待人工处理 |
| BLOCKED | fail | 停止等待人工处理 |
| FAILED | fail | 停止等待人工处理 |
| 异常 | fail | 停止等待人工处理 |

## Post Execution Stop Rules

### 无论 pass/fail 都停止

即使真实调用返回 CHECK_RESULT=pass（final_status=COMPLETE），本 MVP 也必须停止：

```
AUTO_CONTINUE_TO_NEXT_TASK=no
AUTO_GIT_BACKUP=no
HUMAN_REVIEW_REQUIRED=true
NEXT_ACTION=review_real_task_execution_result
```

### 停止原因

| final_status | 停止原因 | loop_status |
|--------------|----------|-------------|
| COMPLETE | real_task_execution_completed | task_execution_completed |
| REQUEST_CHANGES | rework_required | stopped_on_rework_required |
| BLOCKED | task_blocked | stopped_on_task_blocked |
| FAILED | task_failed | stopped_on_task_failed |
| 异常 | execution_exception | stopped_on_task_failed |

### 为什么 pass 后也停止

1. 第一个真实调用必须人工验收
2. 业务代码可能已变更，需要人工确认
3. Claude Code 是否调用需要确认（输出 unknown，不是确认值）
4. Git 备份策略尚未自动化
5. 这是 MVP 安全边界，不是长期限制

## Stop Conditions

必须停止的条件：

| # | 停止条件 | stop_reason | loop_status |
|---|---------|-------------|-------------|
| 1 | real confirm 缺失或错误 | real_confirm_rejected | real_confirm_failed |
| 2 | workspace dirty | workspace_not_clean | preflight_failed |
| 3 | max_tasks != 1 | max_tasks_not_one | preflight_failed |
| 4 | planned_tasks 为空 | no_planned_tasks | preflight_failed |
| 5 | task_id 不合法 | invalid_task_id | preflight_failed |
| 6 | run_project_task_full 不可调用 | runner_not_available | preflight_failed |
| 7 | 当前任务已是 done | task_already_done | preflight_failed |
| 8 | 有 pending rework | rework_pending | preflight_failed |
| 9 | 有未提交报告 | uncommitted_reports | preflight_failed |
| 10 | 有未备份变更 | uncommitted_changes | preflight_failed |
| 11 | 模式冲突 | mode_conflict | preflight_failed |
| 12 | 子调用抛出异常 | execution_exception | stopped_on_task_failed |
| 13 | 子调用 final_status=FAILED | task_failed | stopped_on_task_failed |
| 14 | 子调用 final_status=BLOCKED | task_blocked | stopped_on_task_blocked |
| 15 | 子调用 final_status=REQUEST_CHANGES | rework_required | stopped_on_rework_required |
| 16 | 缺少 CHECK_RESULT（final_status） | missing_final_status | stopped_on_check_fail |
| 17 | 任务状态未更新为 done | task_status_not_updated | stopped_on_check_fail |
| 18 | full_loop_report 缺失 | report_missing | stopped_on_check_fail |
| 19 | workspace 有非预期变更 | unexpected_code_change | stopped_on_dirty_worktree |
| 20 | 框架代码被修改 | framework_code_modified | stopped_on_dirty_worktree |
| 21 | 子调用成功完成（正常停止） | real_task_execution_completed | task_execution_completed |

## Safety Output Fields

真实调用后必须输出以下字段：

```
EXECUTION_MODE=real_call_execute
REAL_CALL_REQUESTED=true
REAL_TASK_EXECUTION=yes/no
RUN_PROJECT_TASK_FULL_CALLED=yes/no
CLAUDE_CODE_CALLED=yes/no/unknown
BUSINESS_CODE_CHANGED=yes/no/unknown
TASK_ID=<task_id>
FINAL_STATUS=COMPLETE/FAILED/BLOCKED/REQUEST_CHANGES
CHECK_RESULT=pass/fail
TASK_STATUS=done/failed/unknown
AUTO_CONTINUE_TO_NEXT_TASK=no
AUTO_GIT_BACKUP=no
HUMAN_REVIEW_REQUIRED=true
LOOP_STATUS=<status>
STOP_REASON=<reason>
NEXT_ACTION=review_real_task_execution_result
RUN_ID=<run_id>
MAX_TASKS=1
COMMAND=<command>
FULL_LOOP_REPORT=<path>
```

### 拒绝场景输出

当 preflight 不通过时：

```
EXECUTION_MODE=real_call_execute
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

当真实调用完成后：

```
EXECUTION_MODE=real_call_execute
REAL_CALL_REQUESTED=true
REAL_TASK_EXECUTION=yes
RUN_PROJECT_TASK_FULL_CALLED=yes
CLAUDE_CODE_CALLED=unknown
BUSINESS_CODE_CHANGED=<yes/no/unknown>
TASK_ID=<task_id>
FINAL_STATUS=<status>
CHECK_RESULT=<pass/fail>
TASK_STATUS=<done/failed/unknown>
AUTO_CONTINUE_TO_NEXT_TASK=no
AUTO_GIT_BACKUP=no
HUMAN_REVIEW_REQUIRED=true
LOOP_STATUS=<status>
STOP_REASON=<reason>
NEXT_ACTION=review_real_task_execution_result
```

### RealCallExecuteResult 数据结构

```python
@dataclass
class RealCallExecuteResult:
    """Real-call execute 结果（max_tasks=1 真实执行）。"""

    # 标识
    project: str
    run_id: str
    execution_mode: str                       # "real_call_execute"
    real_call_requested: bool                 # True
    max_tasks: int                            # 1

    # 确认状态
    first_confirm_accepted: bool              # EXECUTE_PROJECT_LOOP
    real_confirm_accepted: bool               # EXECUTE_REAL_TASK_ONCE

    # 执行状态
    task_id: str | None
    command: str
    real_task_execution: bool                 # 是否真实执行了任务
    run_project_task_full_called: bool        # 是否调用了 run_project_task_full
    claude_code_called: str                   # "yes"/"no"/"unknown"
    business_code_changed: str                # "yes"/"no"/"unknown"

    # 结果
    final_status: str | None                  # FullTaskLoopResult.final_status
    check_result: str                         # "pass"/"fail"
    task_status: str                          # 执行后任务实际状态
    exit_code: str                            # "success"/"failed"/"exception"/"not_executed"

    # 报告
    full_loop_report_path: str | None
    report_paths: list[str]

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

## Validation Plan

后续验证至少 15 个场景：

| # | 场景 | 命令/条件 | 预期结果 |
|---|------|----------|----------|
| 1 | 没有 --real-call | `--execute --confirm EXECUTE_PROJECT_LOOP` | 走 execute stub，不变 |
| 2 | 有 --real-call 但无 --real-confirm | `--execute --confirm EXECUTE_PROJECT_LOOP --real-call` | 拒绝，REAL_TASK_EXECUTION=no |
| 3 | --real-confirm yes | `--real-call --real-confirm yes` | 拒绝，real_confirm_rejected |
| 4 | --real-confirm EXECUTE_PROJECT_LOOP | `--real-call --real-confirm EXECUTE_PROJECT_LOOP` | 拒绝，这是第一重确认 |
| 5 | --real-confirm EXECUTE_REAL_TASK_ONCE + max_tasks=0 | `--real-call --real-confirm EXECUTE_REAL_TASK_ONCE --max-tasks 0` | 拒绝，safety_gate_failed |
| 6 | --real-confirm EXECUTE_REAL_TASK_ONCE + max_tasks=2 | `--real-call --real-confirm EXECUTE_REAL_TASK_ONCE --max-tasks 2` | 拒绝，max_tasks_not_one |
| 7 | workspace dirty | 有未提交变更 | 拒绝，workspace_not_clean |
| 8 | planned_tasks 为空 | 无 pending 任务 | 拒绝，no_planned_tasks |
| 9 | --real-call + --adapter-dry-run | 模式冲突 | 拒绝，mode_conflict |
| 10 | --real-call + --real-call-stub | 模式冲突 | 拒绝，mode_conflict |
| 11 | 子调用 final_status=COMPLETE | 真实执行成功 | CHECK_RESULT=pass, 停止等待人工确认 |
| 12 | 子调用 final_status=FAILED | 真实执行失败 | CHECK_RESULT=fail, 停止等待人工处理 |
| 13 | 子调用 final_status=BLOCKED | 真实执行阻塞 | CHECK_RESULT=fail, 停止 |
| 14 | 子调用抛出异常 | run_project_task_full 异常 | CHECK_RESULT=fail, execution_exception, 停止 |
| 15 | 子调用导致业务代码变化 | 真实执行后 git diff 有变化 | BUSINESS_CODE_CHANGED=yes/unknown, 停止 |
| 16 | pass 后不自动进入下一任务 | final_status=COMPLETE | AUTO_CONTINUE_TO_NEXT_TASK=no |
| 17 | pass 后不自动 Git 备份 | final_status=COMPLETE | AUTO_GIT_BACKUP=no |
| 18 | CLAUDE_CODE_CALLED 输出 unknown | 真实执行后无法确认 | CLAUDE_CODE_CALLED=unknown |

### 验证阶段划分

由于真实执行涉及 Claude Code 调用和业务代码修改，验证分两阶段：

**阶段 A：拒绝场景验证（不真实执行）**

场景 1-10 不涉及真实调用，可以安全验证。

**阶段 B：真实执行验证（需要 Claude Code）**

场景 11-18 涉及真实调用，需要：
1. 选择一个安全的子项目任务
2. 确认 Claude Code 可用
3. 确认有 DEEPSEEK_API_KEY
4. 人工观察执行过程
5. 验证后人工验收结果

**建议**：阶段 A 在 T080 实现，阶段 B 在 T081-T082 实现。

## Workspace Change Detection

### 执行前快照

```python
import subprocess

def _snapshot_workspace(project_root: Path) -> set[str]:
    """记录执行前 workspace 状态。"""
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=str(project_root),
        capture_output=True, text=True,
    )
    return set(result.stdout.strip().splitlines()) if result.stdout.strip() else set()
```

### 执行后比较

```python
def _detect_workspace_changes(
    project_root: Path, before: set[str], after: set[str]
) -> tuple[str, list[str]]:
    """比较执行前后 workspace 变化。

    Returns:
        (status, changed_files)
        status: "clean" / "dirty_expected" / "dirty_unexpected"
    """
    new_files = after - before
    if not new_files:
        return "clean", []

    changed = list(new_files)

    # 分类：预期 vs 非预期
    expected_prefixes = ("reports/", "docs/tasks.md")
    unexpected = [f for f in changed if not any(f.startswith(p) for p in expected_prefixes)]

    if unexpected:
        return "dirty_unexpected", changed
    return "dirty_expected", changed
```

### CLAUDE_CODE_CALLED 推断

```python
def _infer_claude_code_called(
    loop_result: FullTaskLoopResult,
    workspace_changes: tuple[str, list[str]],
) -> str:
    """推断 Claude Code 是否被调用。

    注意：外层无法精确判断，只能推断。
    """
    # 如果任务从未启动 → no
    if not loop_result.steps:
        return "no"

    # 如果有 Developer step 且状态为 PASS → 说明 Claude Code 被调用
    for step in loop_result.steps:
        if step.name == "Developer" and step.success:
            return "yes"

    # 如果 workspace 有变化 → unknown（可能是 Claude Code，也可能是其他原因）
    if workspace_changes[0] != "clean":
        return "unknown"

    # 默认 unknown（宁可多报告，不要漏报）
    return "unknown"
```

### BUSINESS_CODE_CHANGED 推断

```python
def _infer_business_code_changed(
    workspace_changes: tuple[str, list[str]],
    project_root: Path,
) -> str:
    """推断业务代码是否变化。"""
    status, changed = workspace_changes

    if status == "clean":
        return "no"

    # 检查变更文件是否属于业务代码
    business_extensions = (".html", ".css", ".js", ".py", ".yaml", ".json")
    business_files = [
        f for f in changed
        if any(f.strip().endswith(ext) for ext in business_extensions)
        # 排除 reports/ 和 docs/
        and not f.strip().startswith(("reports/", "docs/"))
    ]

    if business_files:
        return "yes"

    # 有变更但不是明确的业务文件
    return "unknown"
```

## Recommended Implementation Roadmap

| 任务 | 角色 | 内容 |
|------|------|------|
| T078 | Developer | 实现 real-call double-confirm safety gate |
| T079 | Developer | 实现 max_tasks=1 real-call dry-run executor |
| T080 | Tester | 验证 real confirm 拒绝场景（场景 1-10） |
| T081 | Tester | 验证 simulated CHECK_RESULT=pass（场景 11, 16-17） |
| T082 | Tester | 验证 simulated CHECK_RESULT=fail（场景 12-15, 18） |
| T083 | Reporter | 提交并推送 real-call safety MVP |

### T078 详细说明

实现内容：
- `RealCallExecuteResult` 数据结构
- `validate_real_call_confirm()` 第二重确认校验
- preflight 检查（13 项）
- runner.py 新增 `--real-call` 和 `--real-confirm` 参数
- 模式互斥检查
- 拒绝场景全覆盖

不包含：
- 真实调用 `run_project_task_full()`
- 真实解析 `FullTaskLoopResult`
- 真实检查 workspace 变化

### T079 详细说明

实现内容：
- `run_project_loop_real_call_execute()` 函数
- 真实调用 `run_project_task_full()`
- 捕获 `FullTaskLoopResult`
- workspace 变化检测
- CLAUDE_CODE_CALLED 推断
- BUSINESS_CODE_CHANGED 推断
- `RealCallExecuteResult` 组装
- 安全输出字段

不包含：
- max_tasks>1 支持
- 自动继续下一任务
- 自动 Git 备份

### T080 验证范围

场景 1-10：全部拒绝场景，不涉及真实调用。安全验证。

### T081 验证范围

场景 11（COMPLETE → pass）+ 场景 16-17（pass 后不自动继续/不自动备份）。
需要选择一个安全的子项目任务真实执行。

### T082 验证范围

场景 12-15, 18：各种 fail 和 unknown 场景。
可能需要模拟 fail，或选择可能失败的任务。

## Final Design Decision

| 决策项 | 结论 |
|--------|------|
| 推荐 CLI | 方案 A：扩展现有 `run-project-loop`，新增 `--real-call` + `--real-confirm` |
| real confirm phrase | `EXECUTE_REAL_TASK_ONCE` |
| 首个真实调用范围 | max_tasks=1 单任务，函数调用 `run_project_task_full()` |
| 是否自动进入下一任务 | 否，无论 pass/fail 都停止等待人工确认 |
| 是否自动 Git 备份 | 否，需要人工确认 |
| CLAUDE_CODE_CALLED 默认值 | unknown（无法确认时输出 unknown，不写 no） |
| BUSINESS_CODE_CHANGED 默认值 | unknown（有变更但无法分类时输出 unknown） |
| 下一步任务 | T078：实现 real-call double-confirm safety gate |
