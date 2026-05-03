# Agent Output Protocol

## 1. 协议目标

Agent 输出协议规定每个 Agent 的标准输出格式，让 runner.py / Main Agent 可以自动读取和判断结果：

- Planner 是否正确拆解任务
- Developer 是否真正完成开发
- Tester 是否给出 PASS / FAIL
- Reviewer 是否给出审查结论
- Reporter 是否完成总结
- Main Agent 是否给出下一步决策

Agent 输出协议 **不是业务代码**，它是自动化协作协议。

当前 T014 只创建协议文件和模板，不接入代码。后续 T017 / T018 / T021 会逐步使用这些协议。

## 2. 适用范围

本协议适用于 `multi-agent-runner` 框架中所有 Agent 角色的输出：

| Agent | 核心输出 |
|-------|----------|
| Main Agent | 决策结果、下一步动作 |
| Planner Agent | 任务清单、规划报告 |
| Developer Agent | 修改文件列表、开发报告 |
| Tester Agent | 测试报告、PASS / FAIL |
| Reviewer Agent | 审查结论、通过或返工 |
| Reporter Agent | 阶段总结报告 |

## 3. 通用输出原则

所有 Agent 输出都必须包含以下通用字段：

| 字段 | 必填 | 说明 |
|------|------|------|
| `Agent` | 是 | 当前 Agent 角色名称 |
| `Task` | 是 | 当前任务编号和名称 |
| `Status` | 是 | 当前任务状态 |
| `Summary` | 是 | 完成内容摘要 |
| `Outputs` | 是 | 输出文件或资源列表 |
| `Evidence` | 是 | 完成证据文件路径 |
| `Next Action` | 是 | 建议下一步动作 |

## 4. 机器可读字段规范

以下字段设计为机器可读，runner.py 或 Main Agent 可通过正则或标记解析：

| 字段 | 格式 | 解析方式 |
|------|------|----------|
| `Status` | 固定枚举值 | 精确匹配 |
| `Task` | `T<编号>` | 正则 `T\d+` |
| `Evidence` | 文件路径 | 文件存在性检查 |
| `Decision`（Reviewer） | 固定枚举值 | 精确匹配 |
| `Decision`（Main） | 固定枚举值 | 精确匹配 |
| `Result`（Tester） | PASS / FAIL | 精确匹配 |

**机器可读字段** 必须使用固定格式，不能包含自由文本。例如 `Status: PASS` 不能写成 `Status: 基本通过`。

**人工可读字段** 如 Summary、Issues、Fix Suggestions 等允许自由文本。

## 5. Main Agent 输出协议

**输出文件：** `reports/main/<task-id>-main-decision.md`

**核心字段：**

| 字段 | 必填 | 说明 |
|------|------|------|
| `Decision` | 是 | 下一步动作 |
| `Reason` | 是 | 决策原因 |
| `Assigned Agent` | 是 | 分配给的 Agent |
| `Required Input` | 是 | 下一步需要的输入 |
| `Expected Output` | 是 | 预期输出 |
| `Evidence Required` | 是 | 下一步的完成证据 |

**Decision 枚举值：**

| 值 | 说明 |
|-----|------|
| `PLAN` | 进入任务规划阶段 |
| `DEVELOP` | 进入开发实现阶段 |
| `TEST` | 进入测试验证阶段 |
| `REVIEW` | 进入审查评估阶段 |
| `RETRY` | 重试当前任务 |
| `COMPLETE` | 当前阶段完成 |
| `STOP` | 停止执行 |

## 6. Planner Agent 输出协议

**输出文件：** `docs/tasks.md`（任务清单）+ `reports/planner/<task-id>-planner-report.md`（规划报告）

**核心字段：**

| 字段 | 必填 | 说明 |
|------|------|------|
| `Status` | 是 | 任务状态 |
| `Plan Summary` | 是 | 规划摘要 |
| `Generated Tasks` | 是 | 生成的任务列表 |
| `Assumptions` | 否 | 规划假设 |
| `Risks` | 否 | 风险提示 |

**任务格式要求：** 每个任务必须包含编号（T<数字>）、标题、状态（pending）、角色、目标、验收标准。

**完成证据：** `docs/tasks.md` 更新记录 或 `reports/planner/<task-id>-planner-report.md`

## 7. Developer Agent 输出协议

**输出文件：** `reports/dev/<task-id>-dev-report.md`

**核心字段：**

| 字段 | 必填 | 说明 |
|------|------|------|
| `Status` | 是 | 任务状态 |
| `Summary` | 是 | 完成内容摘要 |
| `Modified Files` | 是 | 修改的文件列表 |
| `Created Files` | 否 | 新建的文件列表 |
| `Deleted Files` | 否 | 删除的文件列表 |
| `Verification` | 否 | 已执行的验证 |
| `Evidence` | 是 | 完成证据文件路径 |
| `Known Issues` | 否 | 已知问题 |

**Developer Agent 的最小完成证据：** `reports/dev/<task-id>-dev-report.md`

这是 runner.py 判断 Developer 任务是否完成的核心依据。

## 8. Tester Agent 输出协议

**输出文件：** `reports/test/<task-id>-test-report.md`

**核心字段：**

| 字段 | 必填 | 说明 |
|------|------|------|
| `Status` | 是 | 任务状态 |
| `Test Scope` | 是 | 测试范围 |
| `Test Cases` | 是 | 测试用例表格 |
| `Result` | 是 | 最终结果 PASS / FAIL |
| `Failed Items` | 否 | 失败项列表 |
| `Fix Suggestions` | 否 | 修复建议 |

**完成证据：** `reports/test/<task-id>-test-report.md`

## 9. Reviewer Agent 输出协议

**输出文件：** `reports/review/<task-id>-review-report.md`

**核心字段：**

| 字段 | 必填 | 说明 |
|------|------|------|
| `Status` | 是 | 任务状态 |
| `Review Scope` | 是 | 审查范围 |
| `Requirement Match` | 是 | 是否符合原始需求 |
| `Acceptance Check` | 是 | 验收标准逐项检查 |
| `Issues` | 否 | 发现的问题 |
| `Decision` | 是 | 审查结论 |

**Decision 枚举值：**

| 值 | 说明 |
|-----|------|
| `APPROVE` | 审查通过，可进入下一任务 |
| `REQUEST_CHANGES` | 需要返工修改 |
| `RETRY` | 建议重新执行 |
| `BLOCKED` | 被外部条件阻塞 |

**完成证据：** `reports/review/<task-id>-review-report.md`

## 10. Reporter Agent 输出协议

**输出文件：** `reports/final/<stage>-summary.md`

**核心字段：**

| 字段 | 必填 | 说明 |
|------|------|------|
| `Status` | 是 | 任务状态 |
| `Summary` | 是 | 总结 |
| `Completed Tasks` | 是 | 已完成任务列表 |
| `Key Results` | 是 | 关键成果 |
| `Lessons` | 否 | 经验总结 |
| `Pitfalls` | 否 | 踩坑记录 |

**完成证据：** `reports/final/<stage>-summary.md`

## 11. 完成证据规则

任务完成必须同时满足三个条件：

1. **执行成功** — 进程退出码为 0
2. **完成证据存在** — 对应 Agent 的证据文件存在
3. **输出协议符合要求** — 关键字段已正确填写

| Agent | 完成证据文件 |
|-------|-------------|
| Main Agent | `reports/main/<task-id>-main-decision.md` |
| Planner Agent | `reports/planner/<task-id>-planner-report.md` 或 `docs/tasks.md` 更新 |
| Developer Agent | `reports/dev/<task-id>-dev-report.md` |
| Tester Agent | `reports/test/<task-id>-test-report.md` |
| Reviewer Agent | `reports/review/<task-id>-review-report.md` |
| Reporter Agent | `reports/final/<stage>-summary.md` |

**重要说明：**

- `returncode=0` 只能说明进程成功退出，不能单独证明任务完成
- 完成证据文件存在 ≠ 任务一定完成，但文件不存在 = 任务一定未完成
- 当前阶段只检查文件是否存在，后续可以增加内容解析检查

## 12. PASS / FAIL / RETRY / BLOCKED / INFO 状态规范

| 状态 | 含义 | runner.py 行为 |
|------|------|----------------|
| `PASS` | 当前任务或检查通过 | 标记 done，进入下一任务 |
| `FAIL` | 当前任务失败 | 保持 in_progress，等待人工处理 |
| `RETRY` | 建议重试 | 执行 retry-current |
| `BLOCKED` | 被外部条件阻塞 | 停止执行，报告原因 |
| `INFO` | 仅信息记录 | 不改变任务状态 |

**使用规则：**

- 每个输出只能有一个 Status
- Status 必须使用上述固定值，不能自创
- BLOCKED 应附带阻塞原因（如 API 限额、缺少依赖文件）

## 13. 文件命名规范

| 类型 | 路径模板 | 示例 |
|------|----------|------|
| 开发报告 | `reports/dev/<task-id>-dev-report.md` | `reports/dev/T001-dev-report.md` |
| 测试报告 | `reports/test/<task-id>-test-report.md` | `reports/test/T001-test-report.md` |
| 审查报告 | `reports/review/<task-id>-review-report.md` | `reports/review/T001-review-report.md` |
| 规划报告 | `reports/planner/<task-id>-planner-report.md` | `reports/planner/T001-planner-report.md` |
| 决策记录 | `reports/main/<task-id>-main-decision.md` | `reports/main/T001-main-decision.md` |
| 阶段总结 | `reports/final/<stage>-summary.md` | `reports/final/T011-stage-summary.md` |

**命名规则：**

- task-id 格式：`T<数字>` 或 `T<数字>.<子编号>`，如 `T001`、`T009.1`
- stage 格式：自由命名，建议用任务编号或阶段标识
- 文件名全部使用小写英文和连字符

## 14. 后续接入 runner.py 的建议

当前 T014 只创建协议和模板，不修改代码。后续任务接入建议：

| 后续任务 | 接入方式 |
|----------|----------|
| T017（Planner Agent） | 读取 Planner 输出模板，验证任务清单格式 |
| T018（Main Agent 决策） | 解析 Decision 字段，驱动下一步动作 |
| T020（自动执行验证） | 使用 Developer 输出模板格式检查完成证据 |
| T021（Reviewer Agent） | 生成符合 Reviewer 输出协议的审查报告 |

**解析建议：**

- 机器可读字段（Status、Decision、Result）使用精确匹配或正则
- 人工可读字段（Summary、Issues）当前不解析，仅存储
- 完成证据检查当前只验证文件存在性
- 后续可增加内容格式校验（如检查必填字段是否存在）
