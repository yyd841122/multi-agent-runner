# Continuous Task Auto Advance Design

## Background

第五阶段已正式完成，系统已具备以下核心能力：

1. **单任务完整闭环**：`run-project-task-full` 自动执行 Developer → Tester → Reviewer → Main Agent
2. **返工执行安全确认**：`execute-rework` 支持 dry-run / confirmed stub / resume stub
3. **专项 Tester 映射**：根据任务编号自动选择 gravity / collision / behavior Tester
4. **命令权限策略**：A/B/C/D 四类命令分类

第五阶段遗留的关键缺失：系统只能单任务执行，无法自动连续推进多个任务。

## Stage 6 Goal

从"单任务完整闭环"升级为"连续任务自动推进"：

1. 读取任务列表，识别 next pending task
2. 自动执行一个任务闭环（复用 `run-project-task-full`）
3. 检查结果，决定是否继续下一个任务
4. 达到安全边界后停止
5. 输出 run summary

## MVP Scope

第六阶段 MVP 只做：

| # | 能力 | 说明 |
|---|------|------|
| 1 | 读取任务列表 | 从 `<project>/docs/tasks.md` 读取 |
| 2 | 识别 next pending | 找到第一个 pending 任务 |
| 3 | 连续推进 1-N 个任务 | 通过 `max_tasks` 参数控制上限 |
| 4 | 每任务走已有闭环 | 复用 `run-project_task_full` |
| 5 | 任务间安全检查 | 检查工作区、报告、状态 |
| 6 | 达到边界自动停止 | max_tasks / fail / dirty / rework |
| 7 | 输出 run summary | 包含每任务结果和总体状态 |
| 8 | 默认 dry-run | 不带 `--execute` 时只输出计划 |

## Non-goals

第六阶段 MVP 不做：

- 无人值守无限循环
- 真实自动返工多轮执行
- 跳过人工确认的危险操作
- 自动修改 Git 历史
- 自动处理 merge conflict
- 自动部署
- 跨仓库任务推进
- 长期后台运行
- 自动调用 `execute-rework`
- 自动调用 `git push`

## State Model

### 核心数据结构

```python
@dataclass
class ContinuousRunState:
    """连续任务自动推进状态。"""
    run_id: str                    # 运行唯一标识（时间戳 + 随机数）
    project: str                   # 子项目路径
    start_task: str | None         # 起始任务编号（None = 第一个 pending）
    current_task: str | None       # 当前执行任务
    next_task: str | None          # 下一个待执行任务
    max_tasks: int                 # 一次最多推进任务数（默认 3，上限 10）
    completed_count: int           # 已完成任务数
    failed_count: int              # 失败任务数
    skipped_count: int             # 跳过任务数
    stop_reason: str | None        # 停止原因
    loop_status: str               # 见下方状态枚举
    workspace_clean: bool          # 工作区是否 clean
    check_result: str              # pass / fail
    git_backup_required: bool      # 是否需要 Git 备份
    human_review_required: bool    # 是否需要人工审查
    next_action: str               # 建议下一步
    task_results: list[TaskRunResult]  # 每任务执行结果
```

### loop_status 枚举

| 状态 | 含义 |
|------|------|
| `not_started` | 初始状态，未开始执行 |
| `planning` | 正在规划执行计划（dry-run） |
| `running` | 正在执行某个任务 |
| `task_completed` | 当前任务完成，准备检查下一个 |
| `stopped_for_review` | 停止等待人工审查 |
| `stopped_on_failure` | 停止因为任务失败 |
| `stopped_on_dirty_worktree` | 停止因为工作区 dirty |
| `stopped_on_max_tasks` | 停止因为达到 max_tasks |
| `stopped_on_no_pending` | 停止因为没有 pending 任务 |
| `stopped_on_rework_candidate` | 停止因为出现 rework candidate |
| `completed` | 全部任务正常完成 |

### TaskRunResult

```python
@dataclass
class TaskRunResult:
    """单个任务在连续推进中的执行结果。"""
    task_id: str
    final_status: str              # COMPLETE / FAILED / BLOCKED / REQUEST_CHANGES
    check_result: str              # pass / fail
    workspace_clean_after: bool    # 任务执行后工作区是否 clean
    dev_report_exists: bool        # 开发报告是否存在
    step_summary: str              # 阶段结果摘要
    stop_reason: str | None        # 如果此任务导致停止，记录原因
```

## Continue Conditions

**允许自动进入下一个任务**必须同时满足以下全部条件：

| # | 条件 | 检查方式 |
|---|------|----------|
| 1 | 当前任务 `final_status=COMPLETE` | `run_project_task_full` 返回值 |
| 2 | 当前任务状态已写入 `docs/tasks.md` | 重新读取 tasks.md 确认 |
| 3 | 开发报告存在 | `reports/dev/<task_id>-dev-report.md` 存在性 |
| 4 | 无非预期业务代码变化 | 工作区只有 docs/ 和 reports/ 变化 |
| 5 | 工作区可接受 | 只有报告和任务文件变化，无 .py/.js/.html/.css 变化 |
| 6 | 无 pending rework | `final_status != REQUEST_CHANGES` |
| 7 | `human_review_required=false` | 未标记需要人工审查 |
| 8 | 未超过 `max_tasks` | `completed_count < max_tasks` |
| 9 | 下一个 pending task 存在 | 重新读取 tasks.md 找到 |

**只要任一条件不满足，必须立即停止。**

### 条件 4 详细说明：工作区检查

任务执行后，工作区可能包含：

| 变化类型 | 是否可接受 | 说明 |
|----------|-----------|------|
| `reports/dev/` 新增/修改 | 可接受 | 开发报告 |
| `reports/test/` 新增/修改 | 可接受 | 测试报告 |
| `reports/review/` 新增/修改 | 可接受 | 审查报告 |
| `reports/final/` 新增/修改 | 可接受 | 综合决策报告 |
| `docs/tasks.md` 修改 | 可接受 | 任务状态更新 |
| `index.html` 修改 | 需确认 | Developer 正常产出 |
| `style.css` 修改 | 需确认 | Developer 正常产出 |
| `script.js` 修改 | 需确认 | Developer 正常产出 |
| `*.py` 修改（非 reports/） | 不可接受 | 框架代码不应被修改 |
| `.env` 修改 | 不可接受 | 环境变量不应被修改 |

第六阶段 MVP 的策略：

- Developer 正常修改 `index.html` / `style.css` / `script.js` 是预期行为
- 只要 `.py` 文件和 `.env` 没有变化，视为工作区可接受
- 如果出现 `.py` 或 `.env` 变化，立即停止

## Stop Conditions

以下任一条件触发时，必须立即停止：

| # | 停止条件 | stop_reason |
|---|---------|-------------|
| 1 | `run_project_task_full` 返回 FAILED | `task_failed` |
| 2 | `run_project_task_full` 返回 BLOCKED | `task_blocked` |
| 3 | `run_project_task_full` 返回 REQUEST_CHANGES | `rework_candidate` |
| 4 | 工作区出现 `.py` 或 `.env` 变化 | `dirty_worktree_unexpected` |
| 5 | 任务状态无法从 tasks.md 读取 | `task_status_unknown` |
| 6 | 下一个 pending task 不存在 | `no_pending_tasks` |
| 7 | `completed_count >= max_tasks` | `max_tasks_reached` |
| 8 | Developer 超时 | `developer_timeout` |
| 9 | 模型 API 429 | `api_rate_limited` |
| 10 | 检测到 `.env` 变化 | `env_file_changed` |

## CLI Design

### 方案 A：新增 `run-project-loop`

```bash
python runner.py run-project-loop --project projects/down-100-floors-game --max-tasks 3 --dry-run
```

优点：
- 语义清晰，与 `run-project-next` / `run-project-task-full` 形成系列
- 内部复用 `run_project_task_full`，不重复造轮子
- 状态管理在一个命令内完成
- `--dry-run` 默认安全，只输出计划
- 后续容易接 n8n / API / UI
- `--max-tasks` 有硬上限（10）

缺点：
- 新增命令入口
- 需要新增一个工具模块

### 方案 B：外部多次调用 `run-project-task-full`

```bash
# 外部脚本循环调用
for task in G008 G009 G010; do
    python runner.py run-project-task-full --project projects/down-100-floors-game --task $task
    if [ $? -ne 0 ]; then break; fi
done
```

优点：
- 不需要新增命令
- 每次调用独立，无状态管理负担

缺点：
- 没有统一的状态跟踪
- 没有统一的 run summary
- 没有任务间安全检查
- max_tasks 控制在外部脚本
- 不方便后续接 n8n / API / UI
- 无法生成 dry-run 计划

### 推荐方案

**推荐方案 A：新增 `run-project-loop`**

推荐理由：

1. **MVP 可控**：`--dry-run` 默认只输出计划，不执行任何任务
2. **状态清晰**：`ContinuousRunState` 统一管理运行状态
3. **不破坏单任务闭环**：内部调用 `run_project_task_full`，不修改其逻辑
4. **方便后续扩展**：后续接 n8n / API / UI 时，只需调用一个命令
5. **安全边界明确**：`max_tasks` 硬上限 10，默认 3

### 参数设计

```
python runner.py run-project-loop --project <path> [--max-tasks N] [--start-task <id>] [--dry-run] [--execute]
```

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--project` | 是 | - | 子项目路径 |
| `--max-tasks` | 否 | 3 | 一次最多推进任务数（1-10） |
| `--start-task` | 否 | None | 指定起始任务（None = 第一个 pending） |
| `--dry-run` | 否 | True | 只输出计划，不执行（默认） |
| `--execute` | 否 | False | 真实执行任务（需显式传入） |

### 安全约束

- `--execute` 和 `--dry-run` 互斥
- 不传 `--execute` 时，只输出计划（dry-run）
- `max_tasks` 硬上限 10，超出自动修正为 10
- 每次 `run-project-loop` 执行前必须检查工作区 clean

## Execution Flow

### dry-run 模式（默认）

```
run-project-loop --project <path> --max-tasks 3
    │
    ├── 1. 校验参数
    │   - project 路径存在
    │   - max_tasks 在 1-10 范围
    │
    ├── 2. 检查工作区
    │   - git status 必须是 clean
    │   - 不 clean → 停止，提示先提交
    │
    ├── 3. 读取任务列表
    │   - <project>/docs/tasks.md
    │   - 找到所有 pending 任务
    │
    ├── 4. 生成执行计划
    │   - 列出前 max_tasks 个 pending 任务
    │   - 输出每个任务的计划信息
    │   - 不执行任何任务
    │
    └── 5. 输出 dry-run 计划
        - run_id
        - 计划任务列表
        - 预计执行顺序
        - next_action=使用 --execute 开始执行
```

### execute 模式

```
run-project-loop --project <path> --max-tasks 3 --execute
    │
    ├── 1. 校验参数 + 检查工作区
    │
    ├── 2. 创建 ContinuousRunState（run_id, max_tasks）
    │
    ├── 3. 循环执行任务
    │   │
    │   ├── 3a. 读取任务列表，找到下一个 pending
    │   │   - 无 pending → stop(no_pending_tasks)
    │   │   - completed_count >= max_tasks → stop(max_tasks_reached)
    │   │
    │   ├── 3b. 调用 run_project_task_full(current_task)
    │   │   - 返回 COMPLETE → 继续
    │   │   - 返回 FAILED → stop(task_failed)
    │   │   - 返回 BLOCKED → stop(task_blocked)
    │   │   - 返回 REQUEST_CHANGES → stop(rework_candidate)
    │   │
    │   ├── 3c. 检查任务执行后工作区
    │   │   - .py 或 .env 变化 → stop(dirty_worktree_unexpected)
    │   │   - 只有 docs/reports 变化 → 继续
    │   │   - 有 index.html/css/js 变化 → 正常（Developer 产出）
    │   │
    │   ├── 3d. 确认任务状态
    │   │   - 重新读取 tasks.md
    │   │   - 任务状态应为 done
    │   │   - 状态不是 done → stop(task_status_unknown)
    │   │
    │   ├── 3e. 记录 TaskRunResult
    │   │   - 更新 completed_count / failed_count
    │   │
    │   └── 3f. 回到 3a 继续下一个任务
    │
    └── 4. 输出 run summary
        - 生成 run summary 报告
        - 输出 stop_reason
        - 输出 next_action
```

### 停止后的处理

停止后，系统输出：

```
[Run Summary]
run_id: 20260505-xxxx
project: projects/down-100-floors-game
loop_status: stopped_on_failure
stop_reason: task_failed
completed: 2 / 3
failed: 1
skipped: 0
next_action: 检查失败任务报告，确认是否继续
```

## Safety Rules

### 永不自动执行

| # | 操作 | 原因 |
|---|------|------|
| 1 | 自动 `git push` | 推送需要人工确认 |
| 2 | 自动 `execute-rework` | 返工需要严格确认 |
| 3 | 自动删除文件 | 高风险操作 |
| 4 | 自动修改 `.py` 文件 | 框架代码不应被任务修改 |
| 5 | 自动修改 `.env` | 环境变量不应被任务修改 |
| 6 | 无限循环 | `max_tasks` 硬上限 10 |
| 7 | 跳过 Tester / Reviewer | 每任务仍走完整闭环 |
| 8 | 跨仓库操作 | 当前只支持单项目 |

### 任务间安全检查

每个任务执行完成后，进入下一个任务前，必须检查：

1. `final_status == COMPLETE`（不是 FAIL / BLOCKED / REQUEST_CHANGES）
2. 任务状态已更新为 `done`
3. 开发报告存在
4. 无 `.py` / `.env` 非预期变化
5. `completed_count < max_tasks`
6. 下一个 pending 任务存在

### 默认安全模式

| 设置 | 默认值 | 说明 |
|------|--------|------|
| `--dry-run` | True | 默认只输出计划 |
| `--max-tasks` | 3 | 默认最多 3 个任务 |
| `max_tasks` 上限 | 10 | 硬上限，不可超过 |
| 工作区检查 | 每任务后检查 | 必须通过才继续 |
| Git push | 不自动执行 | 需要人工触发 |

## Validation Plan

后续实现需要验证以下场景：

| # | 场景 | 验证方式 | 预期 |
|---|------|----------|------|
| 1 | 没有 pending task | `--project <已完成项目> --dry-run` | 停止，`stop_reason=no_pending_tasks` |
| 2 | dry-run 计划输出 | `--dry-run` | 只输出计划，不执行任务 |
| 3 | max_tasks=1 | `--max-tasks 1 --execute` | 完成 1 个任务后停止 |
| 4 | max_tasks=3 | `--max-tasks 3 --dry-run` | 计划列出 3 个 pending 任务 |
| 5 | 任务失败 | 模拟 fail | 立即停止，`stop_reason=task_failed` |
| 6 | 工作区初始 dirty | 修改文件后运行 | 停止，提示先提交 |
| 7 | 出现 rework candidate | 任务返回 REQUEST_CHANGES | 停止，`stop_reason=rework_candidate` |
| 8 | next task 不合法 | 无 | 停止，`stop_reason=no_pending_tasks` |
| 9 | Git backup required | 多个任务完成后 | 输出提示，不自动 push |
| 10 | 全部条件满足 | `--execute --max-tasks 1` | 输出 `next_action=run_summary` |
| 11 | 达到 max_tasks | `--max-tasks 2` 且有 3+ pending | 完成 2 个后停止 |
| 12 | dry-run 不调用 Claude Code | `--dry-run` | `real_execution_performed=false` |
| 13 | 工作区出现 .py 变化 | 模拟 | 停止，`stop_reason=dirty_worktree_unexpected` |
| 14 | max_tasks 超上限 | `--max-tasks 100` | 自动修正为 10 |

## Recommended Implementation Roadmap

| 任务 | 目标 | 说明 |
|------|------|------|
| T058 | 设计连续任务自动推进协议 | 本文档 |
| T059 | 实现 continuous task planner | `tools/continuous_runner.py` + dry-run 逻辑 |
| T060 | 实现 `run-project-loop` 命令 | runner.py 集成 + execute 分支 |
| T061 | 验证 max_tasks=1 dry-run | 单任务 dry-run 验证 |
| T062 | 验证 max_tasks=3 dry-run | 多任务 dry-run 验证 |
| T063 | 提交并推送第六阶段 MVP | Git 备份 |

### 建议修改文件

| 文件 | 修改内容 |
|------|----------|
| `tools/continuous_runner.py` | 新增，核心逻辑 |
| `runner.py` | 新增 `run-project-loop` 命令 |
| `docs/tasks.md` | 追加任务记录 |
| `reports/dev/T059-dev-report.md` | 开发报告 |

### 不修改的文件

- `tools/full_task_runner.py`（复用，不修改）
- `tools/rework_manager.py`（复用，不修改）
- 业务代码（index.html / style.css / script.js）

## Final Design Decision

| 决策项 | 结论 |
|--------|------|
| 推荐命令 | `python runner.py run-project-loop --project <path> [--max-tasks N] [--dry-run] [--execute]` |
| 默认模式 | dry-run（只输出计划，不执行） |
| 最大任务数策略 | 默认 3，硬上限 10 |
| 是否允许真实执行 | 只在显式传入 `--execute` 时执行，且每个任务仍走完整闭环 |
| 何时停止 | 任务失败 / BLOCKED / rework candidate / 工作区异常 / 达到 max_tasks / 无 pending |
| 下一步任务 | T059：实现 continuous task planner dry-run |
