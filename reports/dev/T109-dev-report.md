# T109 Dev Report

## Task

评估智谱代理 tool_use/tool_result 兼容性与稳定性。

## Scope

本轮只做评估，不调用 Claude Code，不执行真实任务，不修改代码。

## Changed Files

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| docs/zhipu-tool-use-compatibility-assessment.md | new | 智谱 tool-use 兼容性评估文档 |
| reports/dev/T109-dev-report.md | new | 本文件 |
| docs/tasks.md | modified | T109 状态更新 |
| memory/lessons.md | modified | 追加 T109 经验 |
| memory/pitfalls.md | modified | 追加 T109 避坑记录 |

## Evidence Summary

### T103 证明了什么

- acceptEdits + tool-use 存在兼容性问题（120 秒超时）
- text-only 链路正常（default 和 acceptEdits 均秒级返回）
- default + tool-use 被权限拒绝后正常返回
- 问题出在 acceptEdits 模式下工具执行后等待 API 响应 tool_result 的环节

### T107 证明了什么

- default mode text-only 正常返回
- configurable permission mode 实现正确（4/4 dry-run 映射通过）
- default/none 不传 --permission-mode，可作为安全对照

### T108 证明了什么

- T103 的 acceptEdits + tool-use 超时问题**不再复现**
- 最小 tool-use 测试（创建一个文件）成功通过
- 兼容性状态发生变化，可能由代理更新或环境变化导致

### 目前仍未证明什么

1. tool-use 兼容性是否稳定（只有 T108 一次 unexpected_pass）
2. run-project-task-full 是否能完成真实任务（T100/T102 均超时）
3. T103 到 T108 之间什么发生了变化（代理版本？CLI 版本？网络状态？）
4. 真实任务的多轮工具调用是否稳定

## Assessment

### Text-only Compatibility

| 测试 | T103 | T107 | T108 | 结论 |
|------|------|------|------|------|
| default text-only | pass | pass | pass | **稳定可用** |
| acceptEdits text-only | pass | - | pass | **稳定可用** |

智谱代理对 Anthropic Messages API 的基础文本响应兼容性良好。

### Tool-use Compatibility

| 测试 | T103 | T108 | 结论 |
|------|------|------|------|
| acceptEdits + tool-use | timeout | unexpected_pass | **不稳定** |

单次 unexpected_pass 不代表兼容性问题已修复。可能存在间歇性因素。

### Full Execution Compatibility

| 测试 | 结果 | 结论 |
|------|------|------|
| T100 run-project-task-full | timeout | **not_stable** |
| T102/G008 run-project-task-full | timeout | **not_stable** |

run-project-task-full 真实任务链路仍未成功完成。

## Recommendation

### 推荐路线

- **短期**：路线 A — 继续智谱代理，先做 Layer 1-4 分层稳定性验证
- **备用**：路线 B — 切换官方 Claude 验证闭环
- **长期**：路线 C — Runner 自执行 Patch

### 分层验证设计

- Layer 1：text-only stability（连续 3 次 default + 3 次 acceptEdits）
- Layer 2：single-file tool-use stability（最多 3 次 acceptEdits + 创建临时文件）
- Layer 3：runner-level smoke（runner 封装调用 Claude Code，不进入 full loop）
- Layer 4：run-project-task-full smoke（完整闭环冒烟测试）

任何一层失败，停止后续验证，进入路线决策。

## Safety Result

| 检查项 | 结果 |
|--------|------|
| 是否运行 run-project-task-full | no |
| 是否调用 Claude Code | no |
| 是否执行真实任务 | no |
| 是否修改业务代码 | no |
| 是否修改框架代码 | no |

## Next

T110：决策真实执行路线
