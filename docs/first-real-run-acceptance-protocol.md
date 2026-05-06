# First Real Run Acceptance Protocol

## Background

Stage 6 已完成 real-call run-once safety shell 和 child command parser dry-run：

- **T084**：设计了真实调用最小实现协议（数据结构、workspace 检测、推断逻辑）
- **T085**：实现了 `run_project_loop_real_call_run_once_safety_shell()` + `RealCallRunOnceResult`（26 字段）
- **T086**：实现了 `parse_child_command_output()` + `ChildCommandParseResult`（20 字段）+ workspace 辅助函数
- **T087**：验证了 10 个拒绝场景 + 1 个对照场景，全部 PASS
- **T088**：验证了 simulated CHECK_RESULT=pass（CLI + 函数级 12 断言）
- **T089**：验证了 simulated CHECK_RESULT=fail（CLI + 函数级 12 断言）
- **T090**：生成 real-call run-once MVP 小结，确认 safety shell + parser dry-run MVP 完成

当前系统仍然**没有**真实调用 `run_project_task_full()`。所有验证均基于 safety shell 和 parser dry-run。

## Goal

本协议定义首次真实调用 `run_project_task_full()` 后如何验收：

1. 如何分类真实执行结果
2. 如何判断验收状态
3. 如何停止并等待人工确认
4. 如何处理未知字段

本协议为 T092（实现）和 T093（验证）提供设计依据。

## Scope

只覆盖：

| # | 范围 | 说明 |
|---|------|------|
| 1 | max_tasks=1 | 只执行一个 pending task |
| 2 | 单次真实调用 | 只调用一次 `run_project_task_full()` |
| 3 | Python 函数调用 | 同进程调用，不是 subprocess |
| 4 | 执行后立即停止 | 无论 pass/fail 都停止 |
| 5 | 等待人工验收 | 不自动进入下一任务 |
| 6 | 生成执行报告 | 必须生成验收结果 |

## Non-goals

| # | 不做 | 原因 |
|---|------|------|
| 1 | 连续执行多个任务 | 首次真实调用只验证单任务 |
| 2 | 自动修复失败 | 需要人工确认 |
| 3 | 自动返工 | 需要人工确认 |
| 4 | 自动 Git commit/push | 需要人工确认 workspace 变化 |
| 5 | 自动进入下一任务 | 首次真实调用必须人工验收 |
| 6 | 无人值守继续执行 | 首次真实调用必须人工验收 |
| 7 | 5 小时限额自动恢复 | 当前阶段不实现 |
| 8 | 外部触发自动执行 | 当前阶段不实现 |
| 9 | checkpoint / resume | 当前阶段不实现 |

## Acceptance Result Model

### FirstRealRunAcceptanceResult

```python
@dataclass
class FirstRealRunAcceptanceResult:
    """首次真实调用 run-project-task-full 后的验收结果。"""

    # 标识
    run_id: str                              # loop-YYYYMMDD-HHMMSS-<6hex>
    project: str                             # 项目路径
    task_id: str | None                      # 执行的任务编号
    execution_mode: str                      # "real_call_run_once"

    # 执行状态
    real_task_execution: str                 # "yes"
    run_project_task_full_called: str        # "yes" / "attempted" / "no"

    # 子调用结果
    child_exit_code: int | None              # 不使用（函数调用无 exit_code）
    child_check_result: str                  # "pass" / "fail" / "missing"
    child_task_status: str                   # "done" / "failed" / "unknown"

    # 解析状态
    parsed_stdout_status: str                # "not_applicable"（函数调用无 stdout 解析）
    parsed_stderr_status: str                # "not_applicable"（函数调用无 stderr 解析）

    # 推断字段
    claude_code_called: str                  # "yes" / "no" / "unknown"
    business_code_changed: str               # "yes" / "no" / "unknown"

    # Workspace
    workspace_status_before: str             # "clean"（执行前必须 clean）
    workspace_status_after: str              # "clean" / "dirty_reports_only" / "dirty_business_code" / "dirty_expected" / "dirty_unexpected" / "dirty_unknown"
    workspace_change_classification: str     # 同 workspace_status_after

    # 报告
    report_paths: list[str]                  # 生成的报告路径列表

    # 验收决策
    human_review_required: bool              # 始终 True
    auto_continue_to_next_task: bool         # 始终 False
    auto_git_backup: bool                    # 始终 False
    acceptance_status: str                   # "ready_for_human_review" / "blocked" / "failed_to_parse" / "unsafe_to_continue"
    acceptance_required_reason: str          # "first_real_execution_requires_review"
    stop_reason: str                         # 停止原因
    next_action: str                         # 建议下一步

    # 消息
    message: str                             # 人类可读消息
```

### 字段语义说明

| 字段 | 语义 |
|------|------|
| `real_task_execution` | 首次真实调用后始终为 `"yes"` |
| `run_project_task_full_called` | `"yes"` = 成功调用并返回结果，`"attempted"` = 调用但异常，`"no"` = 未调用 |
| `child_check_result` | 来自 `FullTaskLoopResult.final_status` 的映射：COMPLETE→pass，其他→fail，缺失→missing |
| `child_task_status` | 来自执行后重新读取 `tasks.md` 的任务实际状态 |
| `claude_code_called` | 基于 steps + workspace 推断：有 Developer step success→yes，无 steps→no，其他→unknown |
| `business_code_changed` | 基于 workspace 变化分类：clean→no，有业务代码变更→yes，无法分类→unknown |
| `acceptance_status` | `ready_for_human_review` = 可验收，`blocked` = 有问题需处理，`failed_to_parse` = 结果无法解析，`unsafe_to_continue` = 不安全 |

## Success Criteria

如果首次真实调用成功，必须**同时**满足以下所有条件：

| # | 条件 | 检查方式 |
|---|------|----------|
| 1 | `run_project_task_full_called=yes` 或 `attempted` | 调用结果 |
| 2 | `FullTaskLoopResult` 非 None | 返回值检查 |
| 3 | `final_status=COMPLETE` | 返回值检查 |
| 4 | `child_check_result=pass` | final_status 映射 |
| 5 | `child_task_status=done` 或 equivalent done status | 重新读取 tasks.md |
| 6 | workspace 变化可识别 | workspace 快照比较 |
| 7 | report_paths 非空 | 收集步骤报告路径 |
| 8 | `human_review_required=true` | 硬编码 |
| 9 | `auto_continue_to_next_task=false` | 硬编码 |
| 10 | `auto_git_backup=false` | 硬编码 |

成功后仍然必须停止，输出：

```
CHECK_RESULT=pass
ACCEPTANCE_STATUS=ready_for_human_review
STOP_REASON=first_real_execution_requires_review
NEXT_ACTION=review_real_task_execution_result
```

### 为什么 pass 后也停止

1. 第一次真实调用必须人工验收
2. 业务代码可能已变更，需要人工确认范围
3. Claude Code 是否调用需确认（可能输出 unknown）
4. Git 备份策略尚未自动化
5. 报告和代码是否一起提交需要人工决定
6. 这是首次真实执行的安全边界，不是长期限制

## Failure / Block Criteria

以下任一情况都必须视为失败或阻塞：

| # | 失败条件 | 结果 |
|---|----------|------|
| 1 | `FullTaskLoopResult` 为 None | CHECK_RESULT=fail, ACCEPTANCE_STATUS=failed_to_parse |
| 2 | `final_status` 不是四种之一 | CHECK_RESULT=fail, ACCEPTANCE_STATUS=failed_to_parse |
| 3 | `final_status=FAILED` | CHECK_RESULT=fail, ACCEPTANCE_STATUS=blocked |
| 4 | `final_status=BLOCKED` | CHECK_RESULT=fail, ACCEPTANCE_STATUS=blocked |
| 5 | `final_status=REQUEST_CHANGES` | CHECK_RESULT=fail, ACCEPTANCE_STATUS=blocked |
| 6 | 调用抛出异常 | CHECK_RESULT=fail, ACCEPTANCE_STATUS=blocked |
| 7 | workspace `dirty_unknown` | CHECK_RESULT=fail, ACCEPTANCE_STATUS=unsafe_to_continue |
| 8 | workspace `dirty_unexpected` | CHECK_RESULT=fail, ACCEPTANCE_STATUS=unsafe_to_continue |
| 9 | `report_paths` 为空 | CHECK_RESULT=fail, ACCEPTANCE_STATUS=blocked |
| 10 | `claude_code_called=unknown` 且无法从报告确认 | ACCEPTANCE_STATUS=ready_for_human_review（降级，不阻塞） |
| 11 | `business_code_changed=unknown` 且无法从报告确认 | ACCEPTANCE_STATUS=ready_for_human_review（降级，不阻塞） |

失败后必须输出：

```
CHECK_RESULT=fail
ACCEPTANCE_STATUS=blocked 或 unsafe_to_continue
HUMAN_REVIEW_REQUIRED=true
AUTO_CONTINUE_TO_NEXT_TASK=false
AUTO_GIT_BACKUP=false
NEXT_ACTION=review_failure_before_continue
```

### 失败严重程度分类

| 严重程度 | 条件 | 验收状态 | 后续动作 |
|----------|------|----------|----------|
| 致命 | 异常、None 结果、无法解析 | failed_to_parse | 排查异常原因 |
| 严重 | FAILED、BLOCKED、dirty_unexpected | blocked | 人工审查并修复 |
| 中等 | REQUEST_CHANGES、report_paths 空 | blocked | 人工审查返工需求 |
| 低 | unknown 字段但结果可解析 | ready_for_human_review | 人工确认 |

## Human Review Checklist

首次真实调用后，用户必须人工检查以下 10 项：

### 验收清单

```
首次真实调用验收清单
====================

项目：_______________
任务：_______________
执行时间：_______________
验收人：_______________

[ ] 1. run-project-task-full 是否真的只运行了一次
       检查：RUN_PROJECT_TASK_FULL_CALLED=yes（不是 attempted 或 no）
       确认：日志中只出现一次调用记录

[ ] 2. 是否执行了正确的 task_id
       检查：TASK_ID 与计划执行的任务一致
       确认：任务描述与实际执行内容匹配

[ ] 3. CHECK_RESULT 是否可信
       检查：final_status=COMPLETE 对应 CHECK_RESULT=pass
       确认：不是所有情况都输出 pass

[ ] 4. 生成的 dev/test/check 报告是否存在
       检查：REPORT_PATHS 中每个路径都存在
       确认：报告内容非空，格式正确

[ ] 5. 是否调用 Claude Code
       检查：CLAUDE_CODE_CALLED=yes/no/unknown
       确认：如果 yes，确认调用记录存在
       确认：如果 unknown，说明无法确认的原因

[ ] 6. 是否修改业务代码
       检查：BUSINESS_CODE_CHANGED=yes/no/unknown
       确认：如果 yes，检查变更文件列表
       确认：如果 unknown，说明无法分类的原因

[ ] 7. 修改文件是否符合任务范围
       检查：git diff 列出所有变更文件
       确认：变更文件在预期范围内
       确认：没有修改框架代码、.env、配置文件

[ ] 8. git status 是否可解释
       检查：WORKSPACE_STATUS_AFTER 和 WORKSPACE_CHANGE_CLASSIFICATION
       确认：dirty 类型可以解释（如 dirty_reports_only）
       确认：没有 dirty_unexpected 或 dirty_unknown

[ ] 9. 是否需要 Git 备份
       检查：AUTO_GIT_BACKUP=false
       决策：是否手动执行 Git 提交
       确认：报告和代码是否一起提交

[ ] 10. 是否允许进入下一任务
       检查：ACCEPTANCE_STATUS=ready_for_human_review
       决策：通过验收后是否继续下一任务
       确认：未通过验收则不继续

验收结论：[ ] 通过  [ ] 不通过  [ ] 需要更多信息

备注：
_______________________________________________
```

## Workspace Classification Rules

真实调用后 workspace 分类规则：

| 分类 | 条件 | 验收动作 | BUSINESS_CODE_CHANGED |
|------|------|----------|----------------------|
| `clean` | before == after | 可验收，但仍停止 | no |
| `dirty_reports_only` | 变更只含 reports/ 路径 | 可验收，需确认是否提交报告 | no |
| `dirty_expected` | 变更含 reports/ + docs/tasks.md | 可验收，需确认变化符合任务范围 | no |
| `dirty_business_code` | 变更含 .html/.css/.js/.py 等（非 reports/ docs/） | 必须人工审查业务代码变化 | yes |
| `dirty_unexpected` | 变更含框架代码、.env 等 | 停止，不允许继续 | unknown |
| `dirty_unknown` | 无法分类 | 停止，不允许继续 | unknown |

### 分类优先级

1. 如果变更中有 `dirty_unexpected` → 优先标记 `dirty_unexpected`
2. 如果变更中有 `dirty_business_code` → 标记 `dirty_business_code`
3. 如果变更中有 `dirty_expected` 但无业务代码 → 标记 `dirty_expected`
4. 如果变更只有 reports/ → 标记 `dirty_reports_only`
5. 无变更 → `clean`

### 强制规则

- 执行前 workspace 必须 `clean`，否则 preflight 拒绝
- 执行后 workspace 任何分类都要求 `HUMAN_REVIEW_REQUIRED=true`
- 执行后 workspace 任何分类都要求 `AUTO_CONTINUE_TO_NEXT_TASK=false`
- 执行后 workspace 任何分类都要求 `AUTO_GIT_BACKUP=false`

## Claude Code Call Status Rules

真实执行后 `CLAUDE_CODE_CALLED` 必须如实输出：

| 值 | 条件 | 语义 |
|----|------|------|
| `yes` | `FullTaskLoopResult.steps` 中有 Developer step 且 `step.success=True` | 确认 Claude Code 被调用 |
| `no` | `FullTaskLoopResult.steps` 为空列表 | 确认未调用（未进入 Developer 阶段） |
| `unknown` | 有 steps 但无 Developer step success，或 workspace 有变化但无对应 step | 无法确认 |

### 强制规则

- **`unknown` 不能写成 `no`**。unknown 代表信息不足，no 代表确认未调用，语义不同。
- 如果 `CLAUDE_CODE_CALLED=unknown`，必须同时满足：
  - `HUMAN_REVIEW_REQUIRED=true`
  - `AUTO_CONTINUE_TO_NEXT_TASK=false`
  - 在 `message` 中说明为什么是 unknown

### 推断逻辑

```python
def infer_claude_code_called(
    loop_result: FullTaskLoopResult,
    workspace_status: str,
) -> str:
    # 无 steps → 未调用（确认）
    if not loop_result.steps:
        return "no"

    # 有 Developer step 且 success → 已调用（确认）
    for step in loop_result.steps:
        if step.name == "Developer" and step.success:
            return "yes"

    # 有变化但无法从 steps 确认 → unknown
    if workspace_status != "clean":
        return "unknown"

    # 默认 unknown（宁可多报告）
    return "unknown"
```

## Git Backup Rules

首次真实调用后：

```
AUTO_GIT_BACKUP=no
```

无论 pass/fail 都不能自动提交。

### 原因

1. 第一次真实执行需要人工确认执行结果
2. workspace 变化需要人工分类（reports only vs business code）
3. 业务代码变化需要人工审查
4. 报告和代码是否一起提交需要人工决定
5. 如果执行失败，可能需要 `git restore` 回退变更

### 后续规划

- T092-T094 完成后，可以设计人工确认后的 Git backup 流程
- 预计 T095/T096 之后，再考虑在验收通过后自动 Git backup
- 长期目标：验收通过后自动提交报告，人工确认后提交代码变更

### 人工 Git 备份流程建议

```bash
# 1. 查看执行结果
cat reports/dev/T092-real-execution-result.md

# 2. 查看工作区变更
git status --short
git diff --stat

# 3. 确认变更后手动提交
git add reports/
git commit -m "docs: add first real execution result"
```

## Required Output Fields

首次真实调用完成后必须输出以下字段：

```
EXECUTION_MODE=real_call_run_once
TASK_ID=<task_id>
REAL_TASK_EXECUTION=yes
RUN_PROJECT_TASK_FULL_CALLED=yes/attempted/no
CHILD_EXIT_CODE=not_applicable
CHILD_CHECK_RESULT=pass/fail/missing
CHILD_TASK_STATUS=done/failed/unknown
PARSE_CHECK_RESULT=not_applicable
CLAUDE_CODE_CALLED=yes/no/unknown
BUSINESS_CODE_CHANGED=yes/no/unknown
WORKSPACE_STATUS_BEFORE=clean
WORKSPACE_STATUS_AFTER=clean/dirty_reports_only/dirty_business_code/dirty_expected/dirty_unexpected/dirty_unknown
WORKSPACE_CHANGE_CLASSIFICATION=<same as WORKSPACE_STATUS_AFTER>
AUTO_CONTINUE_TO_NEXT_TASK=false
AUTO_GIT_BACKUP=false
HUMAN_REVIEW_REQUIRED=true
ACCEPTANCE_STATUS=ready_for_human_review/blocked/failed_to_parse/unsafe_to_continue
STOP_REASON=<reason>
NEXT_ACTION=<action>
CHECK_RESULT=pass/fail
```

### 字段来源映射

| 输出字段 | 来源 |
|----------|------|
| EXECUTION_MODE | 硬编码 `"real_call_run_once"` |
| TASK_ID | 从 planned_tasks 获取 |
| REAL_TASK_EXECUTION | 真实调用后 `"yes"` |
| RUN_PROJECT_TASK_FULL_CALLED | 调用结果：成功→`yes`，异常→`attempted`，未调用→`no` |
| CHILD_EXIT_CODE | 函数调用无 exit_code，固定 `"not_applicable"` |
| CHILD_CHECK_RESULT | `final_status` 映射：COMPLETE→pass，其他→fail，None→missing |
| CHILD_TASK_STATUS | 重新读取 tasks.md |
| PARSE_CHECK_RESULT | 函数调用无 stdout 解析，固定 `"not_applicable"` |
| CLAUDE_CODE_CALLED | steps + workspace 推断 |
| BUSINESS_CODE_CHANGED | workspace 变化分类推断 |
| WORKSPACE_STATUS_BEFORE | 执行前快照（必须 clean） |
| WORKSPACE_STATUS_AFTER | 执行后快照比较 |
| WORKSPACE_CHANGE_CLASSIFICATION | 同 WORKSPACE_STATUS_AFTER |
| AUTO_CONTINUE_TO_NEXT_TASK | 硬编码 `false` |
| AUTO_GIT_BACKUP | 硬编码 `false` |
| HUMAN_REVIEW_REQUIRED | 硬编码 `true` |
| ACCEPTANCE_STATUS | 综合判定 |
| STOP_REASON | 根据执行结果 |
| NEXT_ACTION | 根据验收状态 |
| CHECK_RESULT | pass/fail |

## Validation Plan

### 至少 20 个验证场景

#### 阶段 A：前置条件拒绝（不真实执行）

| # | 场景 | 条件 | 预期 |
|---|------|------|------|
| 1 | workspace dirty | 执行前有未提交变更 | 拒绝，REAL_TASK_EXECUTION=no |
| 2 | confirm 缺失 | 缺少 `--confirm EXECUTE_PROJECT_LOOP` | 拒绝，confirm_rejected |
| 3 | real confirm 缺失 | 缺少 `--real-confirm EXECUTE_REAL_TASK_ONCE` | 拒绝，real_confirm_missing |
| 4 | confirm 值错误 | `--confirm yes` | 拒绝，confirm_rejected |
| 5 | real confirm 值错误 | `--real-confirm yes` | 拒绝，real_confirm_rejected |
| 6 | max_tasks=2 | `--max-tasks 2` | 拒绝，max_tasks_not_one |
| 7 | max_tasks=0 | `--max-tasks 0` | 拒绝，invalid_max_tasks |
| 8 | 模式冲突：--real-call-dry-run | 同时传入 | 拒绝，mode_conflict |
| 9 | 模式冲突：--adapter-dry-run | 同时传入 | 拒绝，mode_conflict |
| 10 | 模式冲突：--real-call-stub | 同时传入 | 拒绝，mode_conflict |

#### 阶段 B：真实执行结果验收（使用模拟 FullTaskLoopResult）

| # | 场景 | 条件 | 预期 |
|---|------|------|------|
| 11 | final_status=COMPLETE + workspace clean | 正常成功执行 | ready_for_human_review, 停止 |
| 12 | final_status=COMPLETE + dirty_reports_only | 成功，只有报告变更 | ready_for_human_review, 停止 |
| 13 | final_status=FAILED | 任务失败 | blocked, 停止 |
| 14 | final_status=BLOCKED | 任务被阻塞 | blocked, 停止 |
| 15 | final_status=REQUEST_CHANGES | 需要返工 | blocked, 停止 |
| 16 | 调用抛出异常 | run_project_task_full 异常 | blocked, execution_exception, 停止 |
| 17 | FullTaskLoopResult 为 None | 返回值异常 | failed_to_parse, 停止 |
| 18 | final_status 不是四种之一 | 返回值格式错误 | failed_to_parse, unexpected_final_status, 停止 |
| 19 | 缺少 final_status | 字段缺失 | failed_to_parse, missing_final_status, 停止 |

#### 阶段 C：推断和验收规则

| # | 场景 | 条件 | 预期 |
|---|------|------|------|
| 20 | CLAUDE_CODE_CALLED 推断：有 Developer step success | steps 包含 Developer success | claude_code_called=yes |
| 21 | CLAUDE_CODE_CALLED 推断：无 steps | steps 为空 | claude_code_called=no |
| 22 | CLAUDE_CODE_CALLED 推断：有变化但无 Developer success | workspace dirty 但无对应 step | claude_code_called=unknown |
| 23 | BUSINESS_CODE_CHANGED 推断：有 .py/.html 变更 | 业务代码文件变更 | business_code_changed=yes |
| 24 | BUSINESS_CODE_CHANGED 推断：只有 reports/ 变更 | 非业务代码文件变更 | business_code_changed=no |
| 25 | workspace dirty_business_code | 有业务代码变更 | dirty_business_code, 停止 |
| 26 | workspace dirty_unexpected | 有框架代码或 .env 变更 | dirty_unexpected, unsafe_to_continue, 停止 |
| 27 | workspace dirty_unknown | 无法分类变更 | dirty_unknown, unsafe_to_continue, 停止 |

#### 阶段 D：停止和后备行为

| # | 场景 | 条件 | 预期 |
|---|------|------|------|
| 28 | pass 后不自动进入下一任务 | final_status=COMPLETE | AUTO_CONTINUE_TO_NEXT_TASK=false |
| 29 | pass 后不自动 Git backup | final_status=COMPLETE | AUTO_GIT_BACKUP=false |
| 30 | fail 后不自动返工 | final_status=FAILED | 不触发 execute-rework |
| 31 | unknown 字段不得写成 no | CLAUDE_CODE_CALLED 无法确认 | 输出 unknown，不输出 no |
| 32 | report_paths 缺失 | 无报告生成 | blocked, 停止 |
| 33 | task_status=unknown | tasks.md 中状态无法确认 | 降级为 ready_for_human_review |

## Recommended Implementation Roadmap

### T092-T097 建议任务路线

| 任务 | 角色 | 内容 |
|------|------|------|
| T092 | Developer | 实现 `FirstRealRunAcceptanceResult` 数据结构 + 验收状态判定函数 |
| T093 | Developer | 实现 simulated first real-run acceptance parser（使用模拟 FullTaskLoopResult 验证判定逻辑） |
| T094 | Tester | 验证 first real-run acceptance pass/fail 场景（阶段 B+C 模拟数据） |
| T095 | Architect | 设计首次真实调用 `run-project-task-full` 的执行开关（从 safety shell 升级到真实执行） |
| T096 | Developer | 执行第一次真实 `run_project_task_full()` 调用（解除 safety shell，连接真实执行） |
| T097 | Human | 人工验收第一次真实调用结果（使用本协议的验收清单） |

### T092 详细说明

实现内容：

- `FirstRealRunAcceptanceResult` 数据结构
- `classify_acceptance_status()` 函数（综合判定验收状态）
- `build_first_real_run_result()` 函数（构建完整结果）
- 复用 `_snapshot_workspace()`, `_classify_workspace_changes()`, `_infer_claude_code_called()`, `_infer_business_code_changed()`

不包含：

- 真实调用 `run_project_task_full()`

### T093 详细说明

实现内容：

- 模拟 `FullTaskLoopResult` 输入的验收结果判定
- simulated pass/fail/blocked/exception 场景覆盖
- 验证所有 ACCEPTANCE_STATUS 值正确

不包含：

- 真实调用 `run_project_task_full()`

### T094 详细说明

验证阶段 B+C+D 的模拟场景，确认判定逻辑正确。

### T095 详细说明

设计从 safety shell 到真实执行的切换机制：

- 如何将 `run_project_loop_real_call_run_once_safety_shell()` 升级为真实执行
- 保留所有 preflight 检查
- 新增 `--real-execution` 参数或复用已有参数
- 异常处理和回退策略

### T096 详细说明

执行第一次真实调用：

- 选择一个安全的子项目 pending 任务
- 执行 `run_project_task_full(project_path, task_id)`
- 捕获 `FullTaskLoopResult`
- 构建 `FirstRealRunAcceptanceResult`
- 输出验收结果
- 停止等待人工确认

### T097 详细说明

人工验收：

- 使用本协议的 10 项验收清单
- 逐项确认或标记问题
- 决定是否继续下一任务
- 决定是否执行 Git 提交

## Future Requirement

### Rate Limit Recovery / Checkpoint Resume

当 Claude Code / 模型 API 达到 5 小时限制或 API 429 时，未来需要支持：

1. **checkpoint**：保存当前执行状态（已完成的步骤、剩余步骤）
2. **run state 持久化**：将 `FirstRealRunAcceptanceResult` 保存到文件
3. **reset time 检测**：检测 API 限额重置时间
4. **resume_allowed 判断**：判断是否可以恢复执行
5. **恢复后自动继续**：从 checkpoint 处继续

**当前阶段不实现**，等首次真实调用跑通后单独设计。

### 需要记录的关键问题

- 函数调用无 `exit_code`（同进程执行），需要用 `final_status` 判断结果
- 函数调用无 `stdout`/`stderr`（同进程执行），解析逻辑不适用
- 函数调用异常需要 `try/except` 捕获
- 5 小时 API 限额是 Claude Code 的限制，不是框架限制
- 429 错误处理已在 T043.0 中部分实现（超时处理），但尚未实现自动恢复

## Final Decision

| 决策项 | 结论 |
|--------|------|
| 首次真实调用范围 | max_tasks=1，单任务，Python 函数调用，执行后停止 |
| 是否自动进入下一任务 | 否，无论 pass/fail 都停止等待人工验收 |
| 是否自动 Git 备份 | 否，首次真实执行后需要人工确认 workspace 变化 |
| 是否需要人工验收 | 是，必须通过 10 项验收清单 |
| CLAUDE_CODE_CALLED 默认值 | unknown（无法确认时输出 unknown，不写 no） |
| BUSINESS_CODE_CHANGED 默认值 | unknown（有变更但无法分类时输出 unknown） |
| 验收状态分类 | ready_for_human_review / blocked / failed_to_parse / unsafe_to_continue |
| 下一步任务 | T092：实现 first real-run acceptance result model |
