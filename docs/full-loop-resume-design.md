# Full Loop Resume Design

## Background

T056 实现了 `execute-rework` 命令的 dry-run 安全检查。

T056.2 实现了 confirmed rework execution stub（`--real-execution`），当全部安全检查通过时：
- `execution_allowed=True`
- `real_execution_performed=False`
- `EXECUTION_MODE=confirmed_rework_execution_stub`

T056.3 验证了一次完整的 rework candidate flow，确认 dry-run 和 confirmed stub 均按预期工作。

当前问题：confirmed stub 通过后，系统停留在返工检查点，没有能力"恢复主流程"继续调度下一个任务。

## Goal

full loop resume 解决：当 rework candidate 已验证、confirmed stub 已通过后，系统如何安全地标记本轮返工检查完成，并恢复到主流程的下一个 pending task。

具体目标：

1. 明确 resume 的最小状态模型
2. 设计 CLI 形态
3. 定义安全规则
4. 定义验证场景
5. 为 T056.5 实现提供清晰范围

## Non-goals

本阶段（T056.4 设计 + T056.5 实现）不解决：

- 自动连续执行多个任务
- 自动调用 Claude Code 执行真实返工
- 自动修改业务代码
- 无限循环调度
- 失败自动多轮返工
- 第六阶段连续任务自动推进
- run-project-task-full 内部集成 resume

## State Model

### 状态字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `task_id` | str | 当前返工任务编号（如 G007） |
| `rework_round` | int | 返工轮次（1-3） |
| `candidate_status` | str | validated / missing / failed |
| `execution_mode` | str | resume_stub / dry_run / confirmed_rework_execution_stub |
| `execution_allowed` | bool | 是否允许执行 |
| `real_execution_performed` | bool | 是否已真实执行 |
| `resume_allowed` | bool | 是否允许恢复主流程 |
| `resume_target` | str | 恢复目标（NEXT_PENDING / MANUAL_INTERVENTION / BLOCKED） |
| `resume_reason` | str | 恢复原因或拒绝原因 |
| `loop_status` | str | resume_stub_ready / rework_in_progress / resume_blocked |
| `next_action` | str | 建议的下一步操作 |
| `safety_status` | str | pass / fail |

### resume_allowed=true 条件

`resume_allowed=true` 必须在以下条件**全部**满足时出现：

1. `candidate_status=validated`（confirmed stub 已通过）
2. `execution_allowed=true`（执行被允许）
3. `real_execution_performed` 可以是 `false` 或 `true`（当前 MVP 阶段为 `false`）
4. `safety_status=pass`（安全检查通过）

### 当前 MVP 约束

由于真实返工执行仍未发生（`real_execution_performed=false`），resume stub 阶段的语义为：

- `resume_allowed=true`：表示"安全检查已全部通过，系统可以安全恢复主流程"
- `resume_target=NEXT_PENDING`：表示主流程应继续到下一个 pending task
- `loop_status=resume_stub_ready`：表示 resume stub 已就绪，等待用户触发下一步

## CLI Design

### 方案一：复用 `execute-rework` + `--resume`

```bash
python runner.py execute-rework \
  --project projects/down-100-floors-game \
  --task G007 --round 1 \
  --confirm "APPROVE_REWORK task=G007 round=1" \
  --real-execution \
  --resume
```

优点：
- 复用现有命令，减少代码量
- 所有返工相关操作在一个入口
- 用户只需记住一个命令族
- `--resume` 是渐进增强，不影响现有参数

缺点：
- `execute-rework` 承载的职责增加
- 参数组合变多（`--real-execution` + `--resume` + `--confirm`）
- 需要明确 `--resume` 与 `--real-execution` 的依赖关系

依赖关系：
- `--resume` 必须与 `--real-execution` 同时使用
- `--resume` 必须与 `--confirm` 同时使用
- 单独使用 `--resume` 应返回错误提示

### 方案二：新增 `resume-loop` 命令

```bash
python runner.py resume-loop \
  --project projects/down-100-floors-game \
  --task G007 --round 1
```

优点：
- 职责分离，语义清晰
- 参数简洁
- 后续扩展空间大

缺点：
- 新增命令入口，增加维护成本
- `resume-loop` 需要重新做一轮 safety check 或读取之前的 check 结果
- 可能与 `execute-rework` 的安全检查重复
- 对于 MVP 来说过度设计

### 推荐方案

**推荐方案一：复用 `execute-rework` + `--resume`**

推荐理由：

1. MVP 最小修改：只需在 `execute_confirmed_rework()` 中增加 resume 分支
2. 不重复造轮子：复用已有的 round/confirm/prompt 检查逻辑
3. 安全 gate 不绕过：`--resume` 必须经过 `execute-rework` 的全部安全检查
4. 后续第六阶段容易扩展：可以在 `--resume` 基础上增加 `--auto-continue` 参数

## Safety Rules

### 必须满足的安全规则

| # | 规则 | 违反结果 |
|---|------|----------|
| 1 | 没有 validated candidate，不允许 resume | `resume_allowed=false` |
| 2 | 没有通过 confirmed execution stub，不允许 resume | `resume_allowed=false` |
| 3 | round 非法（<1 或 >3），不允许 resume | `resume_allowed=false` |
| 4 | 超过 max rounds（>3），不允许 resume | `resume_allowed=false` |
| 5 | task_id 无效（格式不匹配），不允许 resume | `resume_allowed=false` |
| 6 | resume 不能自动调用 Claude Code | 永远 true |
| 7 | resume 不能自动修改业务代码 | 永远 true |
| 8 | resume 不能自动进入无限循环 | 永远 true |
| 9 | resume 必须输出 `next_action` | 必须 |
| 10 | `--resume` 不能单独使用，必须配合 `--real-execution` 和 `--confirm` | 返回错误提示 |

### resume 永不执行的操作

1. 调用 Claude Code
2. 修改业务代码（index.html / style.css / script.js）
3. 自动执行下一个 pending task
4. 自动修改任务状态
5. 自动进入 run-project-task-full
6. 无限循环调度

## Resume Flow

### 正常流程

```
execute-rework --confirm "..." --real-execution --resume
    │
    ├── 1. 校验参数完整性
    │   - --resume 必须配合 --real-execution
    │   - --resume 必须配合 --confirm
    │   - 缺少任一 → resume_status=param_missing, resume_allowed=false
    │
    ├── 2. 校验 round（复用已有逻辑）
    │   - round < 1 → round_status=invalid, resume_allowed=false
    │   - round > 3 → round_status=exceeded, resume_allowed=false
    │
    ├── 3. 校验 confirm（复用已有逻辑）
    │   - confirm 缺失 → confirmation_status=missing, resume_allowed=false
    │   - confirm 格式错误 → confirmation_status=rejected, resume_allowed=false
    │   - confirm 与 task/round 不匹配 → confirmation_status=rejected, resume_allowed=false
    │
    ├── 4. 检查 rework prompt（复用已有逻辑）
    │   - prompt 不存在 → safety_status=fail, resume_allowed=false
    │
    ├── 5. 全部检查通过
    │   → candidate_status=validated
    │   → execution_allowed=true
    │   → real_execution_performed=false
    │   → safety_status=pass
    │
    └── 6. resume stub 输出
        → resume_allowed=true
        → resume_target=NEXT_PENDING
        → loop_status=resume_stub_ready
        → next_action=ready_for_next_pending_task
```

### 参数校验流程

```
--resume 存在？
├── 没有 → 走原有 execute_confirmed_rework 逻辑
└── 有
    ├── --real-execution 存在？
    │   ├── 没有 → 错误：--resume requires --real-execution
    │   └── 有
    │       ├── --confirm 存在？
    │       │   ├── 没有 → 错误：--resume requires --confirm
    │       │   └── 有 → 继续 resume 逻辑
    │       └── 
    └── 
```

### 输出格式

```
resume_allowed=True
resume_target=NEXT_PENDING
resume_reason=all safety checks passed
loop_status=resume_stub_ready
execution_mode=confirmed_rework_execution_stub
candidate_status=validated
execution_allowed=True
real_execution_performed=False
safety_status=pass
next_action=ready_for_next_pending_task
```

拒绝时：

```
resume_allowed=False
resume_target=BLOCKED
resume_reason=<具体原因>
loop_status=resume_blocked
next_action=<修正建议>
```

## Validation Plan

T056.5 需要验证以下场景：

| # | 场景 | 命令 | 预期 |
|---|------|------|------|
| 1 | `--resume` 缺少 `--real-execution` | `--resume`（无 `--real-execution`） | resume_allowed=false, 参数缺失提示 |
| 2 | `--resume` 缺少 `--confirm` | `--real-execution --resume`（无 `--confirm`） | resume_allowed=false, 参数缺失提示 |
| 3 | confirm 缺失 | `--real-execution --resume`（无 `--confirm`） | resume_allowed=false, confirmation_status=missing |
| 4 | confirm 格式错误 | `--confirm "继续" --real-execution --resume` | resume_allowed=false, confirmation_status=rejected |
| 5 | round 无效（<1） | `--round 0 --real-execution --resume` | resume_allowed=false, round_status=invalid |
| 6 | round 超限（>3） | `--round 4 --real-execution --resume` | resume_allowed=false, round_status=exceeded |
| 7 | 全部通过 | `--confirm "APPROVE_REWORK..." --real-execution --resume` | resume_allowed=true, resume_target=NEXT_PENDING |
| 8 | resume 不调用 Claude Code | 验证执行前后文件无变化 | real_execution_performed=false, 业务代码未变 |
| 9 | 不带 `--resume` 时保持原有行为 | `--real-execution`（无 `--resume`） | 走原有 confirmed stub，无 resume 字段 |
| 10 | 带安全检查通过但 `--resume` 时 safety gate fail | prompt 不存在 + `--resume` | resume_allowed=false, safety_status=fail |

## Recommended Implementation Scope for T056.5

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `tools/rework_manager.py` | 新增 `ReworkResumeResult` dataclass + `prepare_resume()` 函数 |
| `runner.py` | 新增 `--resume` 参数解析 + resume 输出分支 |
| `docs/tasks.md` | 追加 T056.5 记录 |
| `reports/dev/T056.5-dev-report.md` | 新增开发报告 |

### 不修改的文件

- 业务代码（index.html / style.css / script.js）
- tools/full_task_runner.py（第六阶段再集成）
- docs/full-task-loop-protocol.md（第六阶段再更新）

### 代码结构建议

```python
# tools/rework_manager.py

@dataclass
class ReworkResumeResult:
    """full loop resume 结果。"""
    task_id: str
    rework_round: int
    candidate_status: str       # validated / missing / failed
    execution_mode: str         # resume_stub
    execution_allowed: bool
    real_execution_performed: bool
    resume_allowed: bool
    resume_target: str          # NEXT_PENDING / BLOCKED
    resume_reason: str
    loop_status: str            # resume_stub_ready / resume_blocked
    safety_status: str          # pass / fail
    next_action: str


def prepare_resume(
    project_root: Path,
    task_id: str,
    round_number: int,
    confirm: str | None = None,
    real_execution: bool = False,
    resume: bool = False,
) -> ReworkResumeResult:
    """full loop resume stub。

    必须配合 --real-execution 和 --confirm 使用。
    复用 execute_confirmed_rework 的全部安全检查逻辑。
    不调用 Claude Code，不修改业务代码。
    """
    ...
```

### runner.py 参数解析扩展

在现有 `execute-rework` 命令解析中增加：

```python
elif args[i] == "--resume":
    resume = True
    i += 1
```

增加 `resume` 参数后的输出分支：

```python
if resume:
    result = prepare_resume(...)
    # 输出 resume 相关字段
    print(f"resume_allowed={result.resume_allowed}")
    print(f"resume_target={result.resume_target}")
    print(f"resume_reason={result.resume_reason}")
    print(f"loop_status={result.loop_status}")
    ...
```

## Next

T056.5 实现 full loop resume
