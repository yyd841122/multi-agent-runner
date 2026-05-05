# Run Project Loop Execute Safety Design

## Background

Stage 6 MVP（T058-T063）已完成 dry-run 能力：

- `plan-project-loop`：读取 docs/tasks.md，识别 pending 任务，生成执行计划
- `run-project-loop --dry-run`：模拟连续任务推进，生成 TaskRunResult 和 ContinuousLoopRunResult
- `run-project-task-full`：单任务完整闭环（Developer → Tester → Reviewer → Main Decision）
- `execute-rework`：返工执行安全确认（dry-run / confirmed stub / resume stub）

当前 `run-project-loop --execute` 被明确拒绝（runner.py 输出 "ERROR：--execute 当前不支持"）。

## Goal

设计 `run-project-loop --execute` 的安全执行协议，使系统能够从 dry-run 进入真实执行模式，在受控条件下连续推进多个任务。

核心问题：

1. 何时允许进入 execute mode
2. 如何调用单任务闭环
3. 如何检查每任务结果
4. 什么时候继续下一个任务
5. 什么时候必须停止
6. 什么时候必须要求人工确认

## MVP Scope

execute mode MVP 只做：

| # | 能力 | 说明 |
|---|------|------|
| 1 | 显式确认后允许进入 execute mode | `--execute --confirm EXECUTE_PROJECT_LOOP` |
| 2 | 读取 planned_tasks | 复用 `build_continuous_task_plan()` |
| 3 | 按顺序调用已有单任务闭环 | 复用 `run_project_task_full()` |
| 4 | 每次只执行一个任务 | 顺序执行，不并行 |
| 5 | 每个任务完成后检查结果 | 工作区、报告、状态、非预期变化 |
| 6 | 满足 continue conditions 才进入下一个任务 | 全部条件满足才继续 |
| 7 | 达到 max_tasks 后停止 | max_tasks 硬限制 |
| 8 | 失败、dirty、rework、测试不通过时停止 | 任一不满足即停止 |
| 9 | 输出 execute run summary | 每任务结果 + 总体状态 |

## Non-goals

execute mode MVP 不做：

- 无人值守无限循环
- 跳过人工确认
- 真实自动多轮返工（rework candidate 出现时停止，不自动执行 execute-rework）
- 自动解决 merge conflict
- 自动修改 Git 历史
- 跨仓库推进
- 长期后台运行
- 失败后继续执行后续任务
- 自动部署
- 自动 Git push
- 自动调用 execute-rework
- max_tasks > 3（execute mode 硬限制为 3）

## Confirmation Protocol

### CLI 格式

```bash
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP
```

### 确认规则

| # | 规则 | 说明 |
|---|------|------|
| 1 | 默认没有 `--execute` 时只允许 dry-run | 不传 `--execute` 时行为与当前一致 |
| 2 | 有 `--execute` 但没有 `--confirm` 时拒绝 | 必须显式确认 |
| 3 | `--confirm` 值必须精确等于 `EXECUTE_PROJECT_LOOP` | 不接受任何其他值 |
| 4 | 以下值**必须拒绝**：yes、ok、y、确认、同意、continue、true、1 | 模糊确认不合法 |
| 5 | execute mode 下 max_tasks 默认建议为 1 | 最小化单次执行范围 |
| 6 | execute mode 下 max_tasks 硬限制为 3 | 不允许超过 3 |
| 7 | execute mode 第一个实现只允许 max_tasks=1 | MVP 最小范围 |
| 8 | max_tasks > 3 在 execute mode 下直接拒绝 | 不自动裁剪，要求用户明确修改 |

### 为什么 max_tasks 硬限制从 10 降到 3

1. dry-run 是模拟，失败代价为零，可以规划更多
2. execute mode 是真实执行，失败代价高（Claude Code 调用消耗、文件修改、状态变化）
3. 连续执行 3 个以上任务时，上下文偏离风险急剧增加
4. 后续经验积累后可以逐步提高上限

## State Model

### ExecuteLoopState

```python
@dataclass
class ExecuteLoopState:
    """Execute mode 连续任务推进状态。"""
    run_id: str                         # 唯一标识，复用 _generate_run_id()
    project: str                        # 项目路径
    execution_mode: str                 # "execute"（始终）
    confirm_status: str                 # "confirmed" / "missing" / "invalid"
    max_tasks: int                      # 用户请求的 max_tasks
    hard_limit: int                     # execute mode 硬限制 = 3
    planned_tasks: list[str]            # 计划执行的任务 ID 列表
    current_task: str | None            # 当前正在执行的任务
    completed_tasks: list[str]          # 已成功完成的任务
    failed_tasks: list[str]             # 失败的任务
    stopped_task: str | None            # 导致停止的任务
    loop_status: str                    # 见下方枚举
    stop_reason: str | None             # 停止原因
    workspace_status: str               # "clean" / "dirty_expected" / "dirty_unexpected"
    task_execution_performed: bool      # 是否执行了真实任务
    claude_code_called: bool            # 是否调用了 Claude Code
    business_code_changed: bool         # 是否修改了业务代码
    git_backup_status: str              # "not_required" / "required" / "completed"
    human_review_required: bool         # 是否需要人工审查
    next_action: str                    # 建议下一步
    message: str                        # 详细消息
```

### loop_status 枚举

| 状态 | 含义 |
|------|------|
| `execute_confirmed` | 确认通过，准备开始 |
| `executing` | 正在执行某个任务 |
| `task_completed` | 当前任务完成，准备检查是否继续 |
| `stopped_on_failure` | 停止因为任务失败 |
| `stopped_on_dirty_worktree` | 停止因为工作区异常 |
| `stopped_on_max_tasks` | 停止因为达到 max_tasks |
| `stopped_on_no_pending` | 停止因为没有 pending 任务 |
| `stopped_on_rework_candidate` | 停止因为出现 rework candidate |
| `stopped_on_confirm_required` | 停止因为需要人工确认 |
| `stopped_on_git_backup_required` | 停止因为需要 Git 备份 |
| `execute_completed` | 全部计划任务正常完成 |
| `confirmation_rejected` | 确认短语缺失或不合法 |

### 关键字段说明

#### task_execution_performed

- 含义：本次 run-project-loop 是否执行了至少一个真实任务
- 值：execute mode 下为 `true`（只要有一个任务被执行），否则为 `false`
- 用途：判断本次运行是否产生了实际影响

#### claude_code_called

- 含义：本次 run-project-loop 是否调用了 Claude Code
- 值：execute mode 下为 `true`（通过 `run_project_task_full` 间接调用），否则为 `false`
- 用途：判断是否有模型调用消耗

#### business_code_changed

- 含义：本次 run-project-loop 是否修改了业务代码（.html/.css/.js 等）
- 值：取决于 Developer 任务的实际产出
- 用途：判断是否需要 Git 备份

#### human_review_required

- 含义：本次运行后是否需要人工介入
- 触发条件：rework candidate、非预期工作区变化、Git 备份需要
- 用途：决定 next_action 是否包含 "人工审查" 建议

## Preflight Checks

execute mode 启动前必须全部通过以下检查：

| # | 检查项 | 检查方式 | 失败处理 |
|---|--------|----------|----------|
| 1 | 工作区 clean | `git status --short` 无输出 | 停止，提示先提交或 stash |
| 2 | 确认短语正确 | `--confirm` 值 == `EXECUTE_PROJECT_LOOP` | 停止，提示正确格式 |
| 3 | max_tasks 合法 | 1 <= max_tasks <= 3（execute mode 硬限制） | 停止，提示合法范围 |
| 4 | planned_tasks 非空 | `build_continuous_task_plan()` 返回 planned 状态 | 停止，提示无 pending 任务 |
| 5 | NEXT_PENDING 可识别 | plan.next_pending 不为 None | 停止，检查 tasks.md |
| 6 | run-project-task-full 命令可用 | 检查 `run_project_task_full` 函数可导入 | 停止，提示框架问题 |
| 7 | 当前没有 pending rework | 检查无 `*-rework-prompt.md` 文件存在 | 停止，提示先处理返工 |
| 8 | 当前没有未提交总结 | 检查无遗留的 dev report（上一个任务） | 警告但允许继续 |
| 9 | 当前不在失败状态 | 检查无 in_progress 任务 | 停止，提示先处理 in_progress 任务 |

**任一检查不满足，必须停止并输出明确错误信息。**

## Continue Conditions

每个任务执行完成后，只有**同时满足以下全部条件**，才允许进入下一个任务：

| # | 条件 | 检查方式 | 说明 |
|---|------|----------|------|
| 1 | 任务 final_status=COMPLETE | `run_project_task_full` 返回值 | 不是 FAILED/BLOCKED/REQUEST_CHANGES |
| 2 | 任务状态已更新为 done | 重新读取 tasks.md 确认 | 状态不是 done 则停止 |
| 3 | 开发报告存在 | `reports/dev/<task_id>-dev-report.md` 存在性 | 缺失则停止 |
| 4 | 无非预期业务代码变化 | `git diff --name-only` 检查文件类型 | .py/.env 变化则停止 |
| 5 | 如有代码变更符合任务范围 | 变更文件在预期范围内 | 超出范围则停止 |
| 6 | 如需 Git 备份已提醒 | 检查是否有未提交变更 | 有变更则停止并提醒备份 |
| 7 | 没有 rework candidate | final_status != REQUEST_CHANGES | 有 rework 则停止 |
| 8 | human_review_required=false | 未标记需要人工审查 | 标记为 true 则停止 |
| 9 | 未超过 max_tasks | completed_count < max_tasks | 达到则停止 |
| 10 | next pending task 存在且合法 | 重新读取 tasks.md | 不存在则自然停止 |

**只要任一条件不满足，必须立即停止。**

### 条件 4 详细说明：工作区检查

| 变化类型 | 是否可接受 | 说明 |
|----------|-----------|------|
| `reports/dev/` 新增/修改 | 可接受 | 开发报告 |
| `reports/test/` 新增/修改 | 可接受 | 测试报告 |
| `reports/review/` 新增/修改 | 可接受 | 审查报告 |
| `reports/final/` 新增/修改 | 可接受 | 综合决策报告 |
| `docs/tasks.md` 修改 | 可接受 | 任务状态更新 |
| `index.html` / `style.css` / `script.js` 修改 | 可接受 | Developer 正常产出 |
| `*.py` 修改（非 reports/） | **不可接受** | 框架代码不应被任务修改 |
| `.env` 修改 | **不可接受** | 环境变量不应被修改 |

## Stop Conditions

以下任一条件触发时，必须立即停止：

| # | 停止条件 | stop_reason | loop_status |
|---|---------|-------------|-------------|
| 1 | 确认短语缺失或错误 | `confirmation_missing` / `confirmation_invalid` | `confirmation_rejected` |
| 2 | 工作区初始 dirty | `initial_worktree_dirty` | `confirmation_rejected` |
| 3 | max_tasks 非法 | `invalid_max_tasks` | `confirmation_rejected` |
| 4 | planned_tasks 为空 | `no_pending_tasks` | `stopped_on_no_pending` |
| 5 | 单任务执行失败（FAILED） | `task_failed` | `stopped_on_failure` |
| 6 | 单任务阻塞（BLOCKED） | `task_blocked` | `stopped_on_failure` |
| 7 | CHECK_RESULT=fail | `check_failed` | `stopped_on_failure` |
| 8 | 测试失败 | `test_failed` | `stopped_on_failure` |
| 9 | 报告缺失 | `report_missing` | `stopped_on_failure` |
| 10 | 出现 rework candidate | `rework_candidate` | `stopped_on_rework_candidate` |
| 11 | 超过 max rework rounds | `max_rework_exceeded` | `stopped_on_rework_candidate` |
| 12 | Git commit/push 失败 | `git_operation_failed` | `stopped_on_failure` |
| 13 | 出现非预期业务代码变化 | `unexpected_code_change` | `stopped_on_dirty_worktree` |
| 14 | 需要人工验收 | `human_review_required` | `stopped_on_confirm_required` |
| 15 | 达到 max_tasks | `max_tasks_reached` | `stopped_on_max_tasks` |
| 16 | 无更多 pending task | `no_pending_tasks` | `stopped_on_no_pending` |
| 17 | API 429 限流 | `api_rate_limited` | `stopped_on_failure` |
| 18 | Developer 超时 | `developer_timeout` | `stopped_on_failure` |
| 19 | 存在 in_progress 任务 | `existing_in_progress` | `confirmation_rejected` |

## CLI Design

### 方案 A：在 run-project-loop 上启用 --execute

```bash
python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP
```

优点：
- 复用已有命令入口，最小改动
- dry-run 和 execute 是同一命令的两种模式，语义清晰
- 内部逻辑已有基础（dry-run 分支），只需增加 execute 分支
- 后续接 n8n / API / UI 时只需切换 `--execute` 标志
- 用户已经熟悉 `run-project-loop` 命令

缺点：
- execute mode 和 dry-run mode 在同一入口，需要严格分支隔离
- max_tasks 硬限制不同（dry-run=10, execute=3），需要根据模式动态调整

### 方案 B：新增独立命令 execute-project-loop

```bash
python runner.py execute-project-loop --project . --max-tasks 1 --confirm EXECUTE_PROJECT_LOOP
```

优点：
- 命令名明确表示真实执行，减少误操作风险
- 可以独立实现安全检查逻辑，不干扰 dry-run 分支
- 权限控制可以独立配置

缺点：
- 新增命令入口，增加维护负担
- 与 dry-run 命令分离，用户需要记住两个命令
- 内部逻辑大量重复（计划生成、任务读取等）
- 后续接 n8n / API / UI 时需要知道用哪个命令

### 推荐方案

**推荐方案 A：在 run-project-loop 上启用 --execute**

推荐理由：

1. **最小改动**：只需修改 `runner.py` 的 `run-project-loop` 分支和 `tools/continuous_task_planner.py`
2. **复用 planner**：execute mode 复用 `build_continuous_task_plan()` 和 `run_project_loop_dry_run()` 的计划生成逻辑
3. **安全分离**：execute 分支在 preflight 检查后独立执行，不干扰 dry-run 分支
4. **用户熟悉**：用户已经在用 `run-project-loop`，只需加 `--execute --confirm`
5. **后续扩展**：n8n / API / UI 只需在调用时加 `--execute` 标志

### 参数设计

```
python runner.py run-project-loop --project <path> [--max-tasks N] [--execute] [--confirm <phrase>] [--dry-run]
```

| 参数 | 必填 | 默认值 | execute mode | dry-run mode |
|------|------|--------|-------------|-------------|
| `--project` | 是 | - | 相同 | 相同 |
| `--max-tasks` | 否 | 3 | 1-3（硬限制 3） | 1-10（硬限制 10） |
| `--execute` | 否 | False | 必须传入 | 不传或 `--dry-run` |
| `--confirm` | execute 时必填 | - | 必须为 `EXECUTE_PROJECT_LOOP` | 不需要 |
| `--dry-run` | 否 | True | 不可与 `--execute` 共存 | 默认 |

### --execute 和 --dry-run 互斥

- 不传任何标志 → dry-run（默认）
- `--dry-run` → dry-run（显式）
- `--execute` → execute mode（需配合 `--confirm`）
- `--execute --dry-run` → **报错**，互斥

## Execution Flow

### 完整流程

```
run-project-loop --execute --confirm EXECUTE_PROJECT_LOOP --max-tasks 1
    │
    ├── 1. Preflight（9 项检查）
    │   ├── 1a. 解析参数（execute, confirm, max_tasks）
    │   ├── 1b. 检查确认短语（必须精确匹配）
    │   ├── 1c. 检查 max_tasks（1-3 范围）
    │   ├── 1d. 检查工作区 clean
    │   ├── 1e. 检查无 in_progress 任务
    │   ├── 1f. 检查无 pending rework
    │   ├── 1g. 检查 run_project_task_full 可用
    │   ├── 1h. 生成计划（build_continuous_task_plan）
    │   └── 1i. 确认 planned_tasks 非空
    │
    ├── 2. Build Execute State
    │   ├── 生成 run_id
    │   ├── 初始化 ExecuteLoopState
    │   └── loop_status = execute_confirmed
    │
    ├── 3. Confirm Execute
    │   ├── 输出即将执行的计划摘要
    │   ├── 输出 RUN_ID
    │   └── 输出 EXECUTION_MODE=execute
    │
    ├── 4. Execute One Task（循环）
    │   │
    │   ├── 4a. 读取任务列表，找到下一个 pending
    │   │   ├── 无 pending → stop(no_pending_tasks)
    │   │   └── completed_count >= max_tasks → stop(max_tasks_reached)
    │   │
    │   ├── 4b. 调用 run_project_task_full(current_task)
    │   │   ├── 返回 COMPLETE → 继续
    │   │   ├── 返回 FAILED → stop(task_failed)
    │   │   ├── 返回 BLOCKED → stop(task_blocked)
    │   │   └── 返回 REQUEST_CHANGES → stop(rework_candidate)
    │   │
    │   ├── 4c. Collect Result
    │   │   ├── 检查任务状态（重新读取 tasks.md）
    │   │   ├── 检查报告存在
    │   │   ├── 检查工作区变更
    │   │   └── 检查无非预期变化
    │   │
    │   ├── 4d. Decide Continue / Stop
    │   │   ├── 全部 continue conditions 满足 → 继续
    │   │   └── 任一不满足 → stop（附带原因）
    │   │
    │   └── 4e. 回到 4a 继续下一个任务
    │
    ├── 5. Write Summary
    │   ├── 更新 ExecuteLoopState
    │   ├── 生成 execute run summary
    │   └── 保存到 reports/ 目录（可选）
    │
    └── 6. Output
        ├── RUN_ID
        ├── EXECUTION_MODE=execute
        ├── LOOP_STATUS
        ├── STOP_REASON
        ├── COMPLETED_TASKS
        ├── FAILED_TASKS
        ├── TASK_EXECUTION_PERFORMED
        ├── CLAUDE_CODE_CALLED
        ├── BUSINESS_CODE_CHANGED
        ├── GIT_BACKUP_STATUS
        ├── HUMAN_REVIEW_REQUIRED
        ├── NEXT_ACTION
        └── Message
```

### 停止后的处理

停止后，系统输出：

```
[Execute Run Summary]
RUN_ID: loop-20260506-xxxx
EXECUTION_MODE: execute
PROJECT: .
LOOP_STATUS: stopped_on_failure
STOP_REASON: task_failed
MAX_TASKS: 1
COMPLETED: 0 / 1
FAILED: 1 (T065)
TASK_EXECUTION_PERFORMED: true
CLAUDE_CODE_CALLED: true
BUSINESS_CODE_CHANGED: false
GIT_BACKUP_STATUS: not_required
HUMAN_REVIEW_REQUIRED: false
NEXT_ACTION: 检查失败任务报告，确认是否继续
```

## Validation Plan

至少 14 个后续验证场景：

| # | 场景 | 验证方式 | 预期结果 |
|---|------|----------|----------|
| 1 | 不带 `--execute` | `run-project-loop --max-tasks 1` | 仍然 dry-run |
| 2 | 带 `--execute` 但缺少 `--confirm` | `run-project-loop --execute --max-tasks 1` | 拒绝，提示需要 `--confirm` |
| 3 | `--confirm yes` | `run-project-loop --execute --confirm yes --max-tasks 1` | 拒绝，确认短语不合法 |
| 4 | `--confirm ok` | `run-project-loop --execute --confirm ok --max-tasks 1` | 拒绝 |
| 5 | `--confirm 确认` | `run-project-loop --execute --confirm 确认 --max-tasks 1` | 拒绝 |
| 6 | confirm 正确但 max_tasks=0 | `run-project-loop --execute --confirm EXECUTE_PROJECT_LOOP --max-tasks 0` | 拒绝 |
| 7 | confirm 正确但 max_tasks=4 | `run-project-loop --execute --confirm EXECUTE_PROJECT_LOOP --max-tasks 4` | 拒绝（超过 execute 硬限制 3） |
| 8 | 工作区 dirty | 修改文件后运行 execute | 拒绝，提示先提交 |
| 9 | planned_tasks 为空 | 所有任务 done 后运行 execute | 停止，no_pending_tasks |
| 10 | max_tasks=1 execute stub | `run-project-loop --execute --confirm EXECUTE_PROJECT_LOOP --max-tasks 1` | 只执行 1 个任务后停止 |
| 11 | 单任务 CHECK_RESULT=fail | 模拟任务失败 | 停止，stopped_on_failure |
| 12 | 出现 rework candidate | 任务返回 REQUEST_CHANGES | 停止，stopped_on_rework_candidate |
| 13 | Git backup required | 任务完成后有未提交变更 | 停止并提醒备份 |
| 14 | 全部通过但达到 max_tasks | max_tasks=1 且任务成功 | 停止并输出 summary |
| 15 | `--execute --dry-run` 同时传入 | 互斥参数 | 报错 |
| 16 | 不调用未知命令 | 检查代码引用 | 只调用 run_project_task_full |
| 17 | 不允许无限循环 | max_tasks 硬限制 3 | 循环上限有保障 |

## Recommended Implementation Roadmap

| 任务 | 目标 | 说明 |
|------|------|------|
| T065 | 实现 execute mode safety gate | 在 runner.py 和 continuous_task_planner.py 中增加 preflight 检查、确认协议、execute 硬限制 |
| T066 | 实现 max_tasks=1 execute stub | execute mode 下 max_tasks=1 的最小实现（只走一个任务的 stub） |
| T067 | 验证 execute confirm 拒绝场景 | 验证所有确认拒绝场景（场景 1-9, 15） |
| T068 | 验证 max_tasks=1 execute stub | 验证单任务执行和停止行为（场景 10-14, 16-17） |
| T069 | 提交并推送 execute mode safety MVP | Git 备份 |

### 建议修改文件

| 文件 | 修改内容 |
|------|----------|
| `tools/continuous_task_planner.py` | 新增 ExecuteLoopState、preflight 检查函数、execute 硬限制逻辑 |
| `runner.py` | 修改 `run-project-loop` 分支，增加 execute mode 支持 |

### 不修改的文件

- `tools/full_task_runner.py`（复用，不修改）
- `tools/rework_manager.py`（复用，不修改）
- 业务代码（index.html / style.css / script.js）

## Final Design Decision

| 决策项 | 结论 |
|--------|------|
| 推荐 CLI | `python runner.py run-project-loop --project . --max-tasks 1 --execute --confirm EXECUTE_PROJECT_LOOP` |
| 默认模式 | dry-run（不传 `--execute` 时行为不变） |
| execute mode 确认短语 | `EXECUTE_PROJECT_LOOP`（精确匹配，不接受任何变体） |
| execute mode 默认 max_tasks | 1（最小化单次执行范围） |
| execute mode 硬限制 | 3（dry-run 硬限制仍为 10，execute 独立限制） |
| execute mode MVP max_tasks | 只允许 1（后续逐步放开到 2、3） |
| 下一步任务 | T065：实现 execute mode safety gate |
