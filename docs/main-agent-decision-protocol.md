# Main Agent Decision Protocol

## 1. 协议目标

Main Agent 是 `multi-agent-runner` 的调度和决策中心。它根据当前任务状态、执行结果和完成证据，决定下一步动作。

Main Agent **不直接写代码**。Developer Agent / Claude Code 才负责具体开发。

Main Agent 只做一件事：**看当前状态，决定下一步做什么。**

第一版使用规则判断，不接入真实模型。后续可以接入模型增强决策能力。

## 2. Main Agent 职责边界

| 做什么 | 不做什么 |
|--------|----------|
| 读取任务状态 | 不直接编写业务代码 |
| 读取执行结果 | 不直接修改项目文件 |
| 检查完成证据 | 不直接调用 Claude Code |
| 决定下一步动作 | 不解析代码内容 |
| 保存决策报告 | 不做代码质量分析 |
| 给出建议命令 | 不自动执行建议命令 |

## 3. Main Agent 不做什么

1. **不写代码** — 所有代码由 Developer Agent / Claude Code 生成
2. **不修改文件** — Main Agent 只读取和输出决策
3. **不调用 Claude Code** — Main Agent 只做决策，不做执行
4. **不自动执行建议** — 输出建议命令，但不自动运行
5. **不做复杂推理** — 第一版用简单规则，不做自然语言理解

## 4. 决策输入

| 输入 | 来源 | 说明 |
|------|------|------|
| `tasks` | `docs/tasks.md` | 当前所有任务及其状态 |
| `latest_result` | `reports/claude/latest-output.md` | 最近一次执行结果 |
| `evidence_exists` | `reports/dev/<task-id>-dev-report.md` | 当前任务完成证据是否存在 |

## 5. 决策输出

| 字段 | 类型 | 说明 |
|------|------|------|
| `decision` | 枚举值 | 决策结果 |
| `reason` | 文本 | 决策原因 |
| `task_id` | 可选 | 关联的任务编号 |
| `task_title` | 可选 | 关联的任务名称 |
| `assigned_agent` | 可选 | 建议分配的 Agent |
| `next_command` | 可选 | 建议执行的命令 |
| `evidence_required` | 可选 | 需要的完成证据 |
| `blocked` | 布尔 | 是否被阻塞 |

## 6. Decision 枚举

| 值 | 含义 | 触发条件 |
|-----|------|----------|
| `DEVELOP` | 进入开发阶段 | 有 pending 任务，无 in_progress 任务 |
| `RETRY` | 重试当前任务 | in_progress 任务需要重新执行 |
| `COMPLETE` | 完成当前任务 | in_progress 任务成功且有完成证据 |
| `TEST` | 进入测试阶段 | 预留，当前不使用 |
| `REVIEW` | 进入审查阶段 | 预留，当前不使用 |
| `PLAN` | 进入规划阶段 | 预留，当前不使用 |
| `STOP` | 停止执行 | 没有待处理任务 |
| `BLOCKED` | 被阻塞 | 429 限额或外部条件阻塞 |

## 7. 决策规则 MVP

```
输入：tasks, latest_result, evidence_exists

规则 1：如果存在 in_progress 任务
  如果 latest_result 为空（未执行过）：
    → RETRY: 需要重新执行当前任务
  如果 latest_result.is_rate_limited：
    → BLOCKED: API 限额，暂停执行
  如果 latest_result.success == False：
    → RETRY: 执行失败，需要重新执行
  如果 latest_result.success == True 且 evidence_exists == False：
    → RETRY: 执行成功但缺少完成证据
  如果 latest_result.success == True 且 evidence_exists == True：
    → COMPLETE: 执行成功且有完成证据，可以标记 done

规则 2：如果没有 in_progress，但存在 pending 任务
  → DEVELOP: 有待执行任务，建议 run-next

规则 3：如果没有 pending，也没有 in_progress
  → STOP: 所有任务已完成或当前没有可执行任务
```

## 8. 完成证据规则

Main Agent 检查完成证据时，使用与 runner.py 相同的逻辑：

| Agent | 完成证据文件 |
|-------|-------------|
| Developer | `reports/dev/<task-id>-dev-report.md` |
| Tester | `reports/test/<task-id>-test-report.md` |
| Reviewer | `reports/review/<task-id>-review-report.md` |
| Reporter | `reports/final/<stage>-summary.md` |

当前 MVP 只检查 Developer Agent 的完成证据。

## 9. 阻塞与重试规则

### 阻塞（BLOCKED）

触发条件：
- 429 API 限额
- 外部依赖缺失
- 配置错误

处理方式：
- 停止自动执行
- 输出阻塞原因
- 等待人工处理

### 重试（RETRY）

触发条件：
- 执行失败
- 执行成功但缺少完成证据
- in_progress 任务未执行过

处理方式：
- 建议执行 `retry-current`
- 保持 in_progress 状态
- 重新生成 prompt 并调用 Claude Code

## 10. 后续接入模型的方向

当前 MVP 使用规则判断。后续可以增强：

1. **读取 Planner 输出** — Main Agent 根据 Planner 的任务拆解决定执行顺序
2. **读取 Reviewer 结论** — 根据 APPROVE / REQUEST_CHANGES 决定是否进入下一任务
3. **读取 Tester 结果** — 根据 PASS / FAIL 决定是否需要返工
4. **接入模型 API** — 通过 `model_adapter` 调用 main 模型做更智能的决策
5. **工作流驱动** — 根据 workflow YAML 文件中的 stages 定义决策路径

## 11. 返工决策扩展

当 Main Agent 输出 `REQUEST_CHANGES` 时，后续可以进入 Rework Protocol。

Main Agent 不直接修改代码，而是输出：

- 失败原因（reason）
- 返工建议（next_action）
- 需要读取的报告
- 建议生成的返工任务编号

第一版不自动执行返工，只生成返工任务和返工 prompt，等待用户确认。

返工协议详见：`docs/rework-protocol.md`

## 12. Full Task Loop 中的 Main Agent

在 full task loop 中，Main Agent 是最终状态裁决者。

### 12.1 证据输入

Main Agent 必须基于以下所有证据进行判断：

| 证据 | 路径 | 必须 |
|------|------|------|
| Developer report | `reports/dev/<task-id>-dev-report.md` | 是 |
| Basic Tester report | `reports/test/<task-id>-test-report.md` | 是 |
| Specialized Tester report | `reports/test/<task-id>-<type>-test-report.md` | 如存在 |
| Reviewer report | `reports/review/<task-id>-review-report.md` | 是 |

### 12.2 判定规则

```
如果 Developer done AND Basic Tester PASS AND
   (无专项 Tester OR 专项 Tester PASS) AND
   Reviewer APPROVE:
    → COMPLETE

如果 Tester FAIL OR 专项 Tester FAIL:
    → REQUEST_CHANGES

如果 Reviewer REQUEST_CHANGES:
    → REQUEST_CHANGES

如果 模型限额 OR 超时 OR 缺报告:
    → BLOCKED
```

### 12.3 关键原则

- Main Agent 不能只依赖单一模型输出
- 必须综合 Developer / Tester / 专项 Tester / Reviewer 所有证据
- 不直接修改业务代码
- 不自动执行返工（只生成 rework prompt）

详细协议：`docs/full-task-loop-protocol.md`
