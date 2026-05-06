# Run Project Loop Task Execution Design

## Background

Stage 6 execute safety MVP（T064-T069）已完成：

- **T064**：execute mode 安全协议设计
- **T065**：execute mode safety gate（9 项前置检查，19 字段结果）
- **T066**：max_tasks=1 execute stub（模拟执行框架）
- **T067**：confirm 拒绝场景验证（8 场景全部 PASS）
- **T068**：max_tasks=1 execute stub 验证（3 场景全部 PASS）
- **T069**：execute safety MVP 小结

当前系统状态：

```text
execute_allowed=true
→ execute_stub_started=true
→ task_execution_performed=false（模拟）
→ stub_task=第一个 planned task
```

已有 `run_project_task_full()` 函数（`tools/full_task_runner.py`），可执行单任务完整闭环：

- Developer → Basic Tester → Specialized Tester → Reviewer → Main Decision
- 返回 `FullTaskLoopResult`：project_path, task_id, final_status, steps, full_loop_report_path, next_action

**缺失环节**：run-project-loop 如何安全调用 run-project-task-full，如何收集结果，如何判断继续/停止。

## Goal

设计 `run-project-loop --execute` 从 stub 升级到真实调用 `run_project_task_full()` 的安全协议。

核心问题：

1. 如何安全调用 `run_project_task_full()`
2. 如何收集和解析 `FullTaskLoopResult`
3. 如何判断单任务执行结果
4. 如何判断是否继续下一个任务
5. 何时必须停止并等待人工确认

## MVP Scope

| # | 能力 | 说明 |
|---|------|------|
| 1 | max_tasks=1 真实调用 | 只调用一个任务 |
| 2 | 复用 safety gate | 9 项前置检查不变 |
| 3 | 复用 confirm 协议 | EXECUTE_PROJECT_LOOP 精确匹配不变 |
| 4 | 直接函数调用 | 调用 `run_project_task_full()`，不是 subprocess |
| 5 | 收集 FullTaskLoopResult | 解析 final_status 和 steps |
| 6 | 检查 CHECK_RESULT | 基于 final_status 判断 pass/fail |
| 7 | 检查 workspace status | 执行后检查 git status |
| 8 | 生成 execute run summary | 结构化输出 |
| 9 | 停止等待人工确认 | 执行后停止，不自动进入下一任务 |

## Non-goals

| # | 不做 | 原因 |
|---|------|------|
| 1 | max_tasks>1 真实连续执行 | MVP 先验证单任务 |
| 2 | 失败后继续下一个任务 | 失败必须停止 |
| 3 | 自动返工真实执行 | 返工需要人工确认 |
| 4 | 自动 Git commit/push | push 需要人工确认 |
| 5 | 自动处理 merge conflict | 需要人工介入 |
| 6 | 无人值守长循环 | MVP 不做 |
| 7 | 跨仓库任务执行 | 超出当前范围 |
| 8 | 自动部署 | 超出当前范围 |
| 9 | subprocess 调用 | 当前直接函数调用更简单 |

## Command Design

### 外层命令

```bash
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP
```

外层 `run-project-loop` 负责：安全门、计划、调用和结果判断。

### 内层调用

```python
# 直接函数调用（非 subprocess）
from tools.full_task_runner import run_project_task_full

loop_result = run_project_task_full(
    project_path=project_path,  # 如 "projects/down-100-floors-game"
    task_id=task_id,             # 如 "G008"
)
```

内层 `run_project_task_full` 负责：单任务完整闭环（Developer → Tester → Reviewer → Main Decision）。

### 为什么不用 subprocess

1. `run_project_task_full()` 是同一进程内的 Python 函数，直接调用更简单
2. 避免启动新进程的开销和环境问题
3. 可以直接获得结构化 `FullTaskLoopResult`，不需要解析 stdout
4. 后续如果需要隔离执行，可以再改为 subprocess

## Responsibility Split

### run-project-loop（外层 loop）职责

| 职责 | 说明 |
|------|------|
| 安全门 | 调用 `validate_execute_loop_safety()` |
| 计划生成 | 调用 `build_continuous_task_plan()` |
| 确认校验 | 校验 `--confirm EXECUTE_PROJECT_LOOP` |
| 任务选择 | 从 planned_tasks 中选择第一个 pending |
| 调用执行 | 调用 `run_project_task_full()` |
| 结果收集 | 解析 `FullTaskLoopResult` |
| 执行后检查 | 检查 workspace / report / status |
| 继续判断 | 决定是否继续下一个任务 |
| 停止决策 | 决定何时停止并等待人工确认 |
| Summary 输出 | 生成结构化 execute run summary |

### run-project-task-full（内层 full loop）职责

| 职责 | 说明 |
|------|------|
| Developer 执行 | 调用 Claude Code 修改业务代码 |
| Basic Tester | 执行基础静态测试 |
| Specialized Tester | 执行专项测试（如有） |
| Reviewer | 调用 DeepSeek Reviewer |
| Main Decision | 综合决策 |
| Full Loop Report | 生成完整闭环报告 |
| 返回结构化结果 | `FullTaskLoopResult` |

### 职责边界

```
run-project-loop（外层）
  ├── validate_execute_loop_safety()    ← 安全门
  ├── build_continuous_task_plan()      ← 计划生成
  ├── run_project_task_full(task_id)    ← 委托执行
  │   ├── Developer                     ← 内层
  │   ├── Tester                        ← 内层
  │   ├── Reviewer                      ← 内层
  │   └── Main Decision                 ← 内层
  ├── 解析 FullTaskLoopResult           ← 外层收集
  ├── 检查 workspace                    ← 外层检查
  └── 决定继续/停止                     ← 外层决策
```

## State Model

### TaskExecutionResult（新增）

```python
@dataclass
class TaskExecutionResult:
    """单任务真实执行结果（run-project-loop 视角）。"""

    task_id: str                            # 执行的任务 ID
    command: str                            # 调用命令描述
    execution_started: bool                 # 是否真正启动了执行
    execution_finished: bool                # 是否执行完成（无论成功失败）
    final_status: str                       # FullTaskLoopResult.final_status
    check_result: str                       # "pass" / "fail"
    task_status: str                        # 执行后任务的实际状态（done/in_progress 等）
    report_paths: list[str]                 # 生成的报告路径
    workspace_status: str                   # "clean" / "dirty_expected" / "dirty_unexpected"
    business_code_changed: bool             # 是否修改了业务代码
    rework_required: bool                   # 是否需要返工
    human_review_required: bool             # 是否需要人工审查
    next_action: str                        # 建议下一步
    message: str                            # 详细消息
```

### ProjectLoopExecutionResult（新增）

```python
@dataclass
class ProjectLoopExecutionResult:
    """run-project-loop 真实执行总结果。"""

    run_id: str                             # 唯一标识
    project: str                            # 项目路径
    execution_mode: str                     # "execute"
    max_tasks: int                          # 用户请求的 max_tasks
    started_task: str | None                # 启动执行的任务 ID
    completed_tasks: list[str]              # 成功完成的任务
    failed_tasks: list[str]                 # 失败的任务
    stopped_task: str | None                # 导致停止的任务
    task_results: list[TaskExecutionResult] # 每个任务的执行结果
    loop_status: str                        # 见下方枚举
    stop_reason: str | None                 # 停止原因
    workspace_status: str                   # "clean" / "dirty"
    git_backup_required: bool               # 是否需要 Git 备份
    human_review_required: bool             # 是否需要人工审查
    task_execution_performed: bool          # 是否执行了真实任务
    claude_code_called: str                 # "unknown" / "yes" / "no"
    business_code_changed: str              # "yes" / "no" / "unknown"
    next_action: str                        # 建议下一步
    message: str                            # 详细消息
```

### loop_status 枚举

| 状态 | 含义 |
|------|------|
| `execute_real_started` | 已启动真实执行 |
| `task_execution_completed` | 任务执行完成 |
| `stopped_on_task_failed` | 任务执行失败 |
| `stopped_on_task_blocked` | 任务被阻塞 |
| `stopped_on_rework_required` | 需要返工 |
| `stopped_on_dirty_worktree` | 执行后工作区异常 |
| `stopped_on_check_fail` | 执行后检查失败 |
| `stopped_on_git_backup_required` | 需要 Git 备份 |
| `stopped_on_human_review` | 需要人工审查 |
| `stopped_on_max_tasks` | 达到 max_tasks（MVP=1） |

### claude_code_called 三态说明

| 值 | 含义 | 何时使用 |
|----|------|----------|
| `"unknown"` | 无法确认是否调用 | `run_project_task_full` 内部 Developer 调用了 Claude Code，但外层无法直接感知调用结果 |
| `"yes"` | 确认调用了 Claude Code | 通过 FullTaskLoopResult 的 Developer 步骤状态推断（非 SKIPPED/BLOCKED） |
| `"no"` | 确认未调用 | 安全门未通过、计划为空等未触达执行的情况 |

**关键规则**：当 `task_execution_performed=true` 时，`claude_code_called` 必须为 `"unknown"` 或 `"yes"`，不允许为 `"no"`。因为真实执行中 Developer 可能调用 Claude Code，外层无法精确判断。

### business_code_changed 三态说明

| 值 | 含义 | 何时使用 |
|----|------|----------|
| `"unknown"` | 执行了任务但未检查变更 | 理论上不应出现，应为 yes 或 no |
| `"yes"` | 检测到业务代码变更 | `git diff --name-only` 检测到业务文件变化 |
| `"no"` | 未检测到业务代码变更 | `git diff --name-only` 无业务文件变化 |

## Preflight Checks

真实调用前必须检查（与 T065 safety gate 相同）：

| # | 检查项 | 检查方式 | 失败处理 |
|---|--------|----------|----------|
| 1 | 确认短语正确 | `--confirm == EXECUTE_PROJECT_LOOP` | 拒绝 |
| 2 | max_tasks 合法 | 1 <= max_tasks <= 3 | 拒绝 |
| 3 | max_tasks=1 | MVP 只支持 1 | 拒绝 |
| 4 | 工作区 clean | `git status --short` 无输出 | 拒绝 |
| 5 | 无 in_progress 任务 | 读取 tasks.md | 拒绝 |
| 6 | 无 pending rework | 检查无 rework prompt 文件 | 拒绝 |
| 7 | planned_tasks 非空 | `build_continuous_task_plan()` | 拒绝 |
| 8 | task_id 合法 | planned_tasks[0] 存在 | 拒绝 |
| 9 | `run_project_task_full` 可导入 | Python import 检查 | 拒绝 |

**全部检查通过后，才调用 `run_project_task_full()`。**

## Child Command Execution

### 调用方式

```python
# 1. 确定 task_id
task_id = planned_tasks[0]

# 2. 确定 project_path
project_path = "projects/down-100-floors-game"  # 从 plan 或参数获取

# 3. 直接调用
loop_result = run_project_task_full(
    project_path=project_path,
    task_id=task_id,
)

# 4. loop_result 是 FullTaskLoopResult
#    .project_path  -> 项目路径
#    .task_id       -> 任务 ID
#    .final_status  -> COMPLETE / REQUEST_CHANGES / BLOCKED / FAILED
#    .steps         -> 各阶段结果列表
#    .full_loop_report_path -> 完整闭环报告路径
#    .next_action   -> 下一步建议
```

### 结果解析

```python
def parse_execution_result(loop_result: FullTaskLoopResult) -> TaskExecutionResult:
    """将 FullTaskLoopResult 转换为 TaskExecutionResult。"""

    # final_status → check_result
    check_result = "pass" if loop_result.final_status == "COMPLETE" else "fail"

    # steps → report_paths
    report_paths = [
        step.report_path
        for step in loop_result.steps
        if step.report_path
    ]

    # final_status → rework_required
    rework_required = loop_result.final_status == "REQUEST_CHANGES"

    # full_loop_report_path 追加
    if loop_result.full_loop_report_path:
        report_paths.append(loop_result.full_loop_report_path)

    return TaskExecutionResult(
        task_id=loop_result.task_id,
        command=f"run_project_task_full(project={loop_result.project_path}, task={loop_result.task_id})",
        execution_started=True,
        execution_finished=True,
        final_status=loop_result.final_status,
        check_result=check_result,
        task_status="unknown",  # 需要执行后重新读取 tasks.md
        report_paths=report_paths,
        workspace_status="unknown",  # 需要执行后检查
        business_code_changed=False,  # 需要执行后检查
        rework_required=rework_required,
        human_review_required=rework_required or loop_result.final_status in ("BLOCKED", "FAILED"),
        next_action=_determine_next_action(loop_result),
        message=_build_result_message(loop_result),
    )
```

### 异常处理

```python
try:
    loop_result = run_project_task_full(project_path, task_id)
except Exception as e:
    # 执行异常 → 标记失败，停止
    return ProjectLoopExecutionResult(
        ...
        loop_status="stopped_on_task_failed",
        stop_reason=f"run_project_task_full 异常：{e}",
        task_execution_performed=True,
        claude_code_called="unknown",
        business_code_changed="unknown",
        ...
    )
```

## Post Execution Checks

`run_project_task_full` 返回后必须检查：

| # | 检查项 | 检查方式 | 通过条件 | 失败处理 |
|---|--------|----------|----------|----------|
| 1 | final_status | `loop_result.final_status` | == "COMPLETE" | 按 final_status 分类停止 |
| 2 | Full Loop Report 存在 | `Path(loop_result.full_loop_report_path).exists()` | 存在 | 停止，标记 report_missing |
| 3 | 任务状态更新 | 重新读取 tasks.md | 任务状态为 done | 停止，标记 task_status_not_updated |
| 4 | Dev Report 存在 | `reports/dev/<task_id>-dev-report.md` | 存在 | 停止，标记 dev_report_missing |
| 5 | Workspace 状态 | `git status --short` | 可分类（预期变更 vs 非预期变更） | 停止，标记 dirty_unexpected |
| 6 | 业务代码变更 | `git diff --name-only` | 只有预期文件变更 | 如有非预期变更则停止 |
| 7 | 无 rework candidate | `final_status != REQUEST_CHANGES` | 无 rework | 停止等待返工确认 |
| 8 | 无 BLOCKED | `final_status != BLOCKED` | 无阻塞 | 停止等待人工处理 |

### final_status 分类处理

| final_status | 含义 | 外层处理 |
|--------------|------|----------|
| `COMPLETE` | 全部通过 | 检查 workspace → 生成 summary → 停止等待确认 |
| `REQUEST_CHANGES` | 需要返工 | 停止，输出 rework_required=true |
| `BLOCKED` | 被阻塞 | 停止，输出 human_review_required=true |
| `FAILED` | 执行失败 | 停止，输出 task_failed |

### Workspace 检查详细规则

执行后 workspace 可能有以下变更：

| 变更类型 | 是否可接受 | 说明 |
|----------|-----------|------|
| `reports/dev/` 新增/修改 | 可接受 | 开发报告 |
| `reports/test/` 新增/修改 | 可接受 | 测试报告 |
| `reports/review/` 新增/修改 | 可接受 | 审查报告 |
| `reports/final/` 新增/修改 | 可接受 | 综合决策报告 |
| `docs/tasks.md` 修改（子项目） | 可接受 | 任务状态更新 |
| `index.html` / `style.css` / `script.js` 修改（子项目） | 可接受 | Developer 正常产出 |
| `*.py` 修改（非 reports/） | **不可接受** | 框架代码不应被任务修改 |
| `.env` 修改 | **不可接受** | 环境变量不应被修改 |
| `runner.py` / `tools/*.py` 修改 | **不可接受** | 框架不应被任务修改 |

## Stop Conditions

| # | 停止条件 | stop_reason | loop_status |
|---|---------|-------------|-------------|
| 1 | safety gate 不通过 | 继承 safety gate 的 stop_reason | 继承 safety gate 的 loop_status |
| 2 | max_tasks != 1 | max_tasks_gt_1_not_supported | stopped_on_max_tasks |
| 3 | planned_tasks 为空 | no_pending_tasks | stopped_on_no_pending |
| 4 | `run_project_task_full` 抛出异常 | execution_exception | stopped_on_task_failed |
| 5 | final_status=FAILED | task_failed | stopped_on_task_failed |
| 6 | final_status=BLOCKED | task_blocked | stopped_on_task_blocked |
| 7 | final_status=REQUEST_CHANGES | rework_required | stopped_on_rework_required |
| 8 | Full Loop Report 缺失 | report_missing | stopped_on_check_fail |
| 9 | 任务状态未更新为 done | task_status_not_updated | stopped_on_check_fail |
| 10 | Dev Report 缺失 | dev_report_missing | stopped_on_check_fail |
| 11 | workspace 有非预期变更 | unexpected_code_change | stopped_on_dirty_worktree |
| 12 | 框架代码被修改 | framework_code_modified | stopped_on_dirty_worktree |
| 13 | 达到 max_tasks=1 | max_tasks_reached（正常停止） | stopped_on_max_tasks |
| 14 | 任务成功执行完成 | task_completed（正常停止） | task_execution_completed |

**MVP 中，无论任务成功还是失败，执行完一个任务后都必须停止。不自动进入下一个任务。**

## Safety Output Fields

真实执行后，必须明确输出以下安全字段：

```
TASK_EXECUTION_PERFORMED=true
RUN_PROJECT_TASK_FULL_CALLED=true
CLAUDE_CODE_CALLED=unknown/yes/no
BUSINESS_CODE_CHANGED=yes/no/unknown
GIT_BACKUP_REQUIRED=yes/no
HUMAN_REVIEW_REQUIRED=yes/no
CHECK_RESULT=pass/fail
LOOP_STATUS=<status>
STOP_REASON=<reason>
NEXT_ACTION=<action>
```

### 字段详细规则

| 字段 | 安全门未通过时 | 执行成功时 | 执行失败时 | 执行异常时 |
|------|--------------|-----------|-----------|-----------|
| `TASK_EXECUTION_PERFORMED` | false | true | true | true |
| `RUN_PROJECT_TASK_FULL_CALLED` | false | true | true | unknown |
| `CLAUDE_CODE_CALLED` | no | unknown | unknown | unknown |
| `BUSINESS_CODE_CHANGED` | no | yes/no | unknown | unknown |
| `GIT_BACKUP_REQUIRED` | no | yes/no | no | no |
| `HUMAN_REVIEW_REQUIRED` | false | false/true | true | true |
| `CHECK_RESULT` | fail | pass | fail | fail |

### CLAUDE_CODE_CALLED 推断规则

```python
def infer_claude_code_called(
    execution_performed: bool,
    loop_result: FullTaskLoopResult | None,
) -> str:
    """推断 Claude Code 是否被调用。"""
    if not execution_performed:
        return "no"
    if loop_result is None:
        return "unknown"
    # 检查 Developer 步骤是否实际执行
    for step in loop_result.steps:
        if step.name == "Developer" and step.status not in ("SKIPPED", "BLOCKED"):
            return "unknown"  # Developer 非跳过/阻塞，可能调用了 Claude Code
    return "no"  # Developer 被跳过或阻塞，未调用 Claude Code
```

**关键规则**：外层不能假设 `CLAUDE_CODE_CALLED=no`。只有明确未触达执行时才能标记 `no`，否则必须标记 `unknown`。

## Validation Plan

### 后续验证场景（至少 15 个）

| # | 场景 | 验证方式 | 预期结果 |
|---|------|----------|----------|
| 1 | safety gate fail（confirm 错误） | `--execute --confirm yes` | 不调用 run-project-task-full |
| 2 | safety gate fail（max_tasks>1） | `--execute --confirm EXECUTE_PROJECT_LOOP --max-tasks 2` | 不调用 run-project-task-full |
| 3 | safety gate fail（workspace dirty） | 修改文件后执行 | 不调用 run-project-task-full |
| 4 | safety gate fail（planned_tasks 为空） | 所有任务 done 后执行 | 不调用 run-project-task-full |
| 5 | safety gate fail（task_id 不合法） | 手动构造异常 | 不调用 run-project-task-full |
| 6 | run-project-task-full 返回 COMPLETE | 正常执行 | CHECK_RESULT=pass, 停止等待确认 |
| 7 | run-project-task-full 返回 FAILED | 模拟失败 | CHECK_RESULT=fail, 停止 |
| 8 | run-project-task-full 返回 REQUEST_CHANGES | 模拟 Tester/Reviewer 拒绝 | CHECK_RESULT=fail, rework_required=true |
| 9 | run-project-task-full 返回 BLOCKED | 模拟 API 阻塞 | CHECK_RESULT=fail, human_review_required=true |
| 10 | run-project-task-full 执行后 workspace dirty（预期变更） | 正常执行 | dirty_expected, GIT_BACKUP_REQUIRED=true |
| 11 | run-project-task-full 执行后 workspace dirty（非预期变更） | 模拟修改 .py | dirty_unexpected, 停止 |
| 12 | run-project-task-full 抛出异常 | 模拟异常 | execution_exception, 停止 |
| 13 | max_tasks=1 成功执行后不自动进入下一任务 | 成功执行 | 停止，输出 NEXT_ACTION |
| 14 | 所有输出包含真实执行标记 | 成功执行 | TASK_EXECUTION_PERFORMED=true |
| 15 | 安全输出字段完整性 | 所有场景 | 每个场景都输出全部安全字段 |

### 验证策略

| 阶段 | 任务 | 说明 |
|------|------|------|
| Adapter dry-run | T071 | 实现 adapter 但不真实执行，只验证调用链路 |
| Adapter 验证 | T072 | 验证 adapter 不真实执行 |
| Real-call stub | T073 | 实现 max_tasks=1 真实调用，但使用 mock Developer |
| CHECK_RESULT=pass | T074 | 验证成功后停止 |
| CHECK_RESULT=fail | T075 | 验证失败后停止 |
| Git 备份 | T076 | 提交并推送 task execution bridge MVP |

### 为什么先做 Adapter dry-run

从 stub 到真实调用必须先设计 adapter 层：

1. Adapter 负责 `FullTaskLoopResult` → `TaskExecutionResult` 的转换
2. Adapter 负责 workspace 检查
3. Adapter 可以在 dry-run 模式下验证整个调用链路
4. Adapter 通过后，才接入真实 `run_project_task_full`

## Recommended Implementation Roadmap

| 任务 | 目标 | 说明 |
|------|------|------|
| **T071** | 实现 run-project-task-full adapter dry-run | 实现 TaskExecutionResult / ProjectLoopExecutionResult 数据结构和 adapter 函数，但不调用真实 run_project_task_full |
| **T072** | 验证 adapter 不真实执行 | 验证 adapter dry-run 所有路径都不调用真实执行 |
| **T073** | 实现 max_tasks=1 real-call | 在 adapter 基础上接入真实 `run_project_task_full()`，支持 max_tasks=1 |
| **T074** | 验证 CHECK_RESULT=pass 后停止 | 模拟成功执行，验证停止行为和输出 |
| **T075** | 验证 CHECK_RESULT=fail 后停止 | 模拟失败执行，验证停止行为和输出 |
| **T076** | 提交并推送 task execution bridge MVP | Git 备份 |

### 建议修改文件

| 文件 | 修改内容 |
|------|----------|
| `tools/continuous_task_planner.py` | 新增 TaskExecutionResult、ProjectLoopExecutionResult、adapter 函数 |
| `runner.py` | 修改 run-project-loop execute 分支，使用 adapter 替代 stub |

### 不修改的文件

- `tools/full_task_runner.py`（复用，不修改）
- `tools/rework_manager.py`（复用，不修改）
- `tools/project_runner.py`（复用，不修改）
- 业务代码（index.html / style.css / script.js）

## max_tasks 逐步放开策略

| 阶段 | max_tasks | 前提条件 | 说明 |
|------|-----------|----------|------|
| MVP | 1 | adapter 验证通过 | 单任务执行后停止 |
| Phase 2 | 2 | max_tasks=1 真实执行 3+ 次无异常 | 连续执行 2 个任务 |
| Phase 3 | 3 | max_tasks=2 真实执行 3+ 次无异常 | 连续执行 3 个任务 |

每次放开的验证要求：

1. 上一级别真实执行至少 3 次无异常
2. 每次执行后 workspace 检查全部通过
3. 每次执行后 CHECK_RESULT 与实际一致
4. 没有出现框架代码被修改的情况
5. 没有出现非预期业务代码变更

## Final Design Decision

| 决策项 | 结论 |
|--------|------|
| 外层命令 | `python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP` |
| 内层调用 | `run_project_task_full(project_path, task_id)` — 直接函数调用 |
| 首个真实调用范围 | max_tasks=1，单任务执行后停止 |
| 是否自动进入下一任务 | 否，执行完一个任务后必须停止等待人工确认 |
| 是否自动 Git 备份 | 否，输出 GIT_BACKUP_REQUIRED=true 提醒用户 |
| CLAUDE_CODE_CALLED 默认值 | unknown（不能假设 no） |
| 下一步任务 | T071：实现 run-project-task-full adapter dry-run |
