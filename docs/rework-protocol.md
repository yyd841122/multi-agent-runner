# Rework Protocol

## 1. 协议目标

Rework Protocol 定义当 Tester FAIL 或 Reviewer REQUEST_CHANGES 时，如何生成返工任务和返工 prompt。

核心原则：

- 返工必须基于失败证据，不能只凭一句错误描述
- 返工任务应独立编号，避免污染原任务
- 返工完成后必须重新走完整验证链路
- 第一版不自动执行返工，等待用户确认

## 2. 为什么需要返工协议

当前 G003 / G004 的完整闭环链路是：

```
Developer → Tester → Reviewer → Main Agent → COMPLETE
```

当 Tester FAIL 或 Reviewer REQUEST_CHANGES 时，Main Agent 输出 REQUEST_CHANGES，但没有自动返工能力。需要人工分析失败报告并手动修复。

返工协议的目标是让系统可以根据失败报告自动生成返工任务和返工 prompt，降低人工介入成本。

## 3. 当前不做什么

1. **不自动调用 Claude Code 修改代码** — 只生成返工 prompt，等待用户确认
2. **不自动修改任务状态** — 返工任务需要人工确认后才执行
3. **不做多轮自动返工循环** — 第一版只做单次返工
4. **不做环境问题修复** — API Key 缺失、模型限额等问题不应生成代码返工
5. **不做需求变更** — 返工只修复失败项，不新增功能

## 4. 返工触发条件

### 4.1 可以触发返工

| 触发条件 | 来源 |
|----------|------|
| Tester Result = FAIL | 基础静态测试报告 |
| Behavior Tester Result = FAIL | 行为测试报告 |
| Reviewer Decision = REQUEST_CHANGES | 审查报告 |
| Main Decision = REQUEST_CHANGES | 综合决策报告 |
| Main Decision = BLOCKED 且原因可修复 | 综合决策报告 |

### 4.2 不触发返工

| 情况 | 原因 |
|------|------|
| COMPLETE | 任务已完成 |
| PASS / APPROVE 且无问题 | 无需返工 |
| BLOCKED 原因是 API Key 缺失 | 环境问题，不是代码问题 |
| BLOCKED 原因是模型限额（429） | 环境问题，不是代码问题 |
| 用户明确选择暂不返工 | 人工决策 |

## 5. 返工输入来源

返工 prompt 应该读取以下报告：

| 输入 | 路径 | 说明 |
|------|------|------|
| 原始任务 | `docs/tasks.md` | 原任务编号、目标、验收标准 |
| Developer 报告 | `reports/dev/<task-id>-dev-report.md` | 开发内容和修改文件 |
| Tester 报告 | `reports/test/<task-id>-test-report.md` | 基础测试失败项 |
| Behavior Tester 报告 | `reports/test/<task-id>-behavior-test-report.md` | 行为测试失败项（可选） |
| Reviewer 报告 | `reports/review/<task-id>-review-report.md` | 审查 Issues |
| Main Decision 报告 | `reports/final/<task-id>-main-decision.md` | 综合决策原因 |
| project.yaml | `project.yaml` | allowed_files / blocked_files |

关键原则：返工 prompt 不能只依赖一句错误提示，必须包含失败证据和允许修改边界。

## 6. 返工任务命名规则

### 6.1 编号规则

| 类型 | 编号示例 | 说明 |
|------|----------|------|
| 原任务 | G004 | 原始开发任务 |
| 第一次返工 | G004-R1 | G004 的第一次返工 |
| 第二次返工 | G004-R2 | G004 的第二次返工 |

编号格式：`<原任务编号>-R<返工轮次>`

### 6.2 标题示例

```
G004-R1 修复玩家键盘左右移动边界问题
G004-R2 修复玩家移动后位置未更新问题
```

### 6.3 任务状态

与普通任务一致：`pending` → `in_progress` → `done`

### 6.4 写入位置

返工任务写入子项目 `docs/tasks.md`，但 T040 只设计协议，不实际写入。

## 7. 返工 prompt 生成规则

### 7.1 必须包含的内容

| 序号 | 内容 | 来源 |
|------|------|------|
| 1 | 当前项目路径 | project.yaml |
| 2 | 原任务编号 | docs/tasks.md |
| 3 | 返工任务编号 | 命名规则 |
| 4 | 原任务目标 | docs/tasks.md |
| 5 | 失败来源 | Main Decision |
| 6 | 失败项列表 | Tester / Reviewer |
| 7 | Reviewer Issues | Reviewer 报告 |
| 8 | Main Decision Reason | Main Decision 报告 |
| 9 | 允许修改文件 | project.yaml |
| 10 | 禁止修改文件 | project.yaml |
| 11 | 返工开发报告路径 | 证据规则 |
| 12 | 不扩大范围限制 | 固定 |

### 7.2 关键约束

返工 prompt 必须明确：

- **只修复失败项，不新增无关功能**
- 不修改主框架文件
- 不修改 project.yaml
- 不扩大任务范围
- 修改后写清楚修复内容和验证建议

## 8. 返工允许修改范围

与原任务一致，从 `project.yaml` 的 `allowed_files` 读取。

默认：

- `index.html`
- `style.css`
- `script.js`
- `docs/tasks.md`
- `reports/`
- `memory/`

## 9. 返工禁止修改范围

与原任务一致，从 `project.yaml` 的 `blocked_files` 读取。

默认：

- `requirement.md`
- `docs/future-platform-plan.md`
- `docs/character-system-plan.md`
- `project.yaml`
- 主框架代码

## 10. 返工完成证据规则

### 10.1 返工报告路径

| Agent | 报告路径 |
|-------|----------|
| Developer | `reports/dev/<rework-id>-dev-report.md` |
| Tester | `reports/test/<rework-id>-test-report.md` |
| Behavior Tester | `reports/test/<rework-id>-behavior-test-report.md` |
| Reviewer | `reports/review/<rework-id>-review-report.md` |
| Main Decision | `reports/final/<rework-id>-main-decision.md` |

例如 G004-R1：

- `reports/dev/G004-R1-dev-report.md`
- `reports/test/G004-R1-test-report.md`
- `reports/test/G004-R1-behavior-test-report.md`
- `reports/review/G004-R1-review-report.md`
- `reports/final/G004-R1-main-decision.md`

### 10.2 返工报告内容

返工开发报告必须包含：

- 返工任务编号
- 原任务编号
- 失败项列表
- 修复内容
- 修改文件列表
- 验证建议

## 11. 返工后的验证链路

返工完成后必须重新走完整验证链路：

```
Developer Rework
    ↓
Tester（基础静态测试）
    ↓
Behavior Tester（如果任务涉及行为）
    ↓
Reviewer
    ↓
Main Agent
    ↓
COMPLETE 或 REQUEST_CHANGES（再次返工）
```

不能只改完就标记 COMPLETE。返工后的验证标准与原任务一致。

## 12. 人工确认边界

### 12.1 第一版（当前）

| 步骤 | 自动/人工 |
|------|-----------|
| 发现失败 | 自动 |
| 读取失败报告 | 自动 |
| 生成返工任务 | 自动 |
| 生成返工 prompt | 自动 |
| **确认是否执行返工** | **人工** |
| 执行返工 | 人工触发 |
| 返工后验证 | 人工触发 |

### 12.2 后续扩展

| 步骤 | 当前 | 未来 |
|------|------|------|
| 确认执行返工 | 人工 | 可选自动 |
| 返工后验证 | 人工触发 | 可选自动 |
| 多轮返工限制 | 无 | 最多 N 轮 |
| 失败后 blocked | 无 | 自动 blocked |

## 13. 与 Main Agent 的关系

当 Main Agent 输出 `REQUEST_CHANGES` 时，后续进入 Rework Protocol。

Main Agent 不直接修改代码，而是输出：

- 失败原因（reason）
- 返工建议（next_action）
- 需要读取的报告
- 建议生成的返工任务编号

返工任务由 Rework Protocol 接管，与 Main Agent 的决策链路解耦。

## 14. T041 实现建议

### 14.1 实现方向

T041 应在 `tools/` 中新增返工 prompt 生成工具：

1. 新增 `tools/rework_runner.py`
2. 读取失败报告（Tester / Reviewer / Main Decision）
3. 生成返工任务描述和返工 prompt
4. 保存到 `prompts/rework_prompt.md`
5. 不自动调用 Claude Code

### 14.2 命令建议

```bash
python runner.py generate-rework-prompt G004
```

功能：

- 读取 G004 相关失败报告
- 生成返工任务描述
- 生成返工 prompt
- 保存到 `prompts/rework_prompt.md`
- 输出摘要，等待用户确认

### 14.3 返工轮次自动检测

- 检查 `docs/tasks.md` 中是否已有 `G004-R1`
- 如果没有，使用 `G004-R1`
- 如果已有，使用下一个编号 `G004-R2`

## 15. 返工执行人工确认

自动返工分为两个阶段：

1. 返工 prompt 生成
2. 返工执行

当前系统允许自动生成 rework prompt，但不允许自动执行返工。

返工执行必须满足：

- 任务处于 REWORK_CANDIDATE
- 已生成 rework prompt
- 返工轮次不超过 R3
- 用户输入严格确认格式
- 工作区状态允许执行

严格确认格式包括：

```text
确认执行 <task-id>-R<round> 返工

或：

APPROVE_REWORK task=<task-id> round=<round>
```

未确认时，系统只能输出建议，不得调用 Claude Code 执行返工。

不接受模糊表达（"继续""可以""试一下""你看着办""自动处理"）作为确认。

详细协议见 `docs/rework-execution-confirmation-protocol.md`。
