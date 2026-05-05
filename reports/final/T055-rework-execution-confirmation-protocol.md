# T055 自动返工执行人工确认协议报告

## 1. 背景

当前 multi-agent-runner 已具备返工 prompt 自动生成能力（T040/T041），但返工执行仍需人工操作。T055 的目标是设计"自动返工执行前的人工确认协议"，为 T056 实现自动返工执行 MVP 提供协议基础。

## 2. 当前返工能力

| 能力 | 状态 |
|------|------|
| 生成 rework prompt | 已实现 |
| 读取失败报告 | 已实现 |
| 自动执行返工 | 未实现（T056） |
| 人工确认机制 | 本协议定义 |
| 返工轮次追踪 | 部分实现 |

## 3. 协议目标

- 将返工 prompt 生成与返工执行严格分开
- 定义 REWORK_CANDIDATE 状态
- 定义严格人工确认格式
- 限制最大返工次数为 3 轮
- 定义人工介入规则
- 与 run-project-task-full 衔接

## 4. 返工触发条件

### 4.1 可以触发返工候选

- Basic Tester FAIL
- Specialized Tester FAIL
- Reviewer REQUEST_CHANGES
- Main Agent REQUEST_CHANGES
- Main Agent BLOCKED 且原因可修复
- Developer 完成证据与任务状态冲突

### 4.2 不触发返工

- API Key 缺失
- DeepSeek API 429
- Claude Code API 429
- 网络错误
- .env 未加载
- Reviewer 模型调用失败
- Claude Code 超时但无代码改动证据

## 5. REWORK_CANDIDATE 状态

REWORK_CANDIDATE 表示"建议返工"，不表示"立即执行返工"。

允许：生成 rework prompt、列出失败证据、等待用户确认。

禁止：自动执行返工、修改业务代码、增加返工轮次、覆盖原始报告。

## 6. 人工确认格式

### 接受的格式

```text
确认执行 <task-id>-R<round> 返工

或：

APPROVE_REWORK task=<task-id> round=<round>
```

### 不接受的模糊表达

继续、可以、试一下、你看着办、自动处理、好的、OK、yes、go、do it

## 7. 最大返工次数

- 同一任务最多 3 轮返工：R1 / R2 / R3
- 第 4 次请求必须停止
- 系统生成人工介入报告
- 不得继续生成执行型返工 prompt

## 8. 人工介入规则

触发条件：返工 3 次后仍 FAIL、连续 3 次不同原因 FAIL、任务状态与证据严重冲突、API/环境持续不可用、用户主动请求。

人工介入报告路径：`<project-root>/reports/final/<task-id>-manual-intervention-report.md`

## 9. 与 full task loop 的衔接

### 当前行为

`run-project-task-full` 失败后只生成 rework prompt，不自动执行返工。

### T056 实现后

增加 `--allow-rework` 参数，失败后进入 REWORK_CANDIDATE，等待用户确认后执行返工。

不带 `--allow-rework` 时行为不变。

## 10. 命令权限边界

返工命令属于 C 类（需要人工确认或任务显式授权），不得加入全局 allowlist。

执行条件：REWORK_CANDIDATE + rework prompt 存在 + 严格确认格式 + 轮次 <= 3 + 无 API Key 泄露风险。

## 11. T056 实现建议

1. 新增 `tools/rework_executor.py`
2. 新增 `execute-rework` 命令
3. 实现确认格式解析
4. 实现前置检查
5. 实现返工后重新测试链路
6. 集成到 `run-project-task-full --allow-rework`

## 12. 是否完成

T055 已完成。

创建了以下文件：

- `docs/rework-execution-confirmation-protocol.md`（20 章节完整协议）
- `templates/rework/rework-execution-confirmation-template.md`（确认模板）
- `reports/final/T055-rework-execution-confirmation-protocol.md`（总结报告）
- `reports/dev/T055-dev-report.md`（开发报告）

更新了以下文件：

- `docs/tasks.md`（T055 状态 in_progress → done）
- `docs/rework-protocol.md`（追加返工执行人工确认章节）
- `docs/full-task-loop-protocol.md`（追加 Rework Execution Confirmation 章节）
- `docs/command-permission-policy.md`（追加 Rework Command Permission Boundary 章节）
- `memory/lessons.md`（追加 T055 经验）
- `memory/pitfalls.md`（追加 T055 避坑）

未实现自动返工执行代码（T056 职责）。
