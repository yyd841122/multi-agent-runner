# T056 自动返工执行 MVP 总结

## 1. 背景

T055 设计了返工执行人工确认协议，定义了 REWORK_CANDIDATE 状态、严格确认格式、最大返工次数限制和人工介入规则。T056 在此基础上实现 `execute-rework` 命令的 MVP 安全外壳。

## 2. MVP 目标

实现 `execute-rework` 命令入口，只做执行前安全检查，不执行真实返工。

## 3. 实现内容

### 3.1 新增数据结构

- `ReworkExecutionCheckResult`：返工执行前安全检查结果（status / reason / confirmed / report_path）

### 3.2 新增函数

| 函数 | 功能 |
|------|------|
| `validate_rework_confirmation()` | 校验严格确认格式 |
| `validate_rework_round()` | 校验返工轮次 |
| `prepare_rework_execution()` | 执行前安全检查主函数 |
| `_save_execution_check_report()` | 生成执行检查报告 |

### 3.3 runner.py 集成

新增 `execute-rework` 命令入口，支持 `--project` / `--task` / `--round` / `--confirm` / `--no-dry-run` 参数。

## 4. 安全边界

- MVP 默认 `dry_run=True`
- 不调用 Claude Code
- 不修改业务代码
- 只校验 task / round / confirm / prompt
- 生成 execution check report

## 5. 确认格式校验

### 接受的格式

```text
确认执行 <task-id>-R<round> 返工
APPROVE_REWORK task=<task-id> round=<round>
```

### 拒绝的格式

继续、可以、试一下、你看着办、自动处理、好的、OK、yes、go、do it

### 拒绝不匹配

当确认文本中的 task/round 与请求参数不一致时，返回 BLOCKED。

## 6. 最大返工次数

- round < 1 → BLOCKED
- round 1/2/3 → 允许进入安全检查
- round > 3 → MANUAL_INTERVENTION

## 7. dry-run 行为

MVP 阶段所有 `execute-rework` 执行均为 dry-run：

- 即使确认通过、prompt 存在、轮次合法，也只返回 READY_TO_EXECUTE
- 不调用 Claude Code
- 不修改任何文件（除了生成检查报告）

## 8. 本地验证结果

| 场景 | 命令 | 预期 | 实际 |
|------|------|------|------|
| 未确认 | `--round 1`（无 --confirm） | BLOCKED | PASS |
| 模糊确认 | `--confirm "继续"` | BLOCKED | PASS |
| round 不匹配 | `--confirm "APPROVE_REWORK task=G007 round=2"` | BLOCKED | PASS |
| round > 3 | `--round 4 --confirm "APPROVE_REWORK task=G007 round=4"` | MANUAL_INTERVENTION | PASS |
| round < 1 | `--round 0 --confirm "确认执行 G007-R0 返工"` | BLOCKED | PASS |
| 正确确认 + prompt 存在 | `--confirm "APPROVE_REWORK task=G007 round=1"` | READY_TO_EXECUTE | PASS |

全部 6 个验证场景通过。

## 9. 未实现内容

- 真实返工执行（调用 Claude Code 修改业务代码）
- 返工后重新运行 Tester / Reviewer / Main Decision
- `run-project-task-full --allow-rework` 集成
- `--no-dry-run` 真实执行模式

## 10. 后续建议

- 在真实 FAIL 场景下验证 `execute-rework` 完整链路
- 实现 `--no-dry-run` 模式，在严格确认后调用 Claude Code
- 集成到 `run-project-task-full --allow-rework`
- 实现返工后自动重新测试和审查
- 增加返工轮次自动检测（基于已有 R1/R2/R3 编号）

## 11. 是否完成

T056 已完成。

实现了 `execute-rework` 命令的安全外壳，包含确认格式校验、轮次限制和 prompt 存在性检查。

MVP 不执行真实返工，所有操作均为 dry-run 安全检查。
