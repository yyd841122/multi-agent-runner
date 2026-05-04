# T040 自动返工协议报告

## 1. 背景

当前 G003 / G004 的完整闭环链路是 Developer → Tester → Reviewer → Main Agent → COMPLETE。当 Tester FAIL 或 Reviewer REQUEST_CHANGES 时，Main Agent 输出 REQUEST_CHANGES，但没有自动返工能力。

需要设计返工协议，让系统可以根据失败报告自动生成返工任务和返工 prompt。

## 2. 协议目标

设计自动返工协议，使系统可以：

1. 根据失败报告生成返工任务
2. 根据失败证据生成返工 prompt
3. 保持与现有验证链路的一致性
4. 明确人工确认边界

## 3. 返工触发条件

| 触发条件 | 来源 |
|----------|------|
| Tester Result = FAIL | 基础静态测试报告 |
| Behavior Tester Result = FAIL | 行为测试报告 |
| Reviewer Decision = REQUEST_CHANGES | 审查报告 |
| Main Decision = REQUEST_CHANGES | 综合决策报告 |
| Main Decision = BLOCKED 且原因可修复 | 综合决策报告 |

不触发返工：COMPLETE、PASS / APPROVE、环境问题（API Key、429）、用户选择暂不返工。

## 4. 返工输入来源

| 输入 | 说明 |
|------|------|
| 原始任务 | 原任务编号、目标、验收标准 |
| Developer 报告 | 开发内容和修改文件 |
| Tester 报告 | 基础测试失败项 |
| Behavior Tester 报告 | 行为测试失败项（可选） |
| Reviewer 报告 | 审查 Issues |
| Main Decision 报告 | 综合决策原因 |
| project.yaml | allowed_files / blocked_files |

## 5. 返工任务命名规则

| 类型 | 编号示例 |
|------|----------|
| 原任务 | G004 |
| 第一次返工 | G004-R1 |
| 第二次返工 | G004-R2 |

返工报告路径：`reports/dev/G004-R1-dev-report.md`

返工后验证链路与原任务一致。

## 6. 返工 prompt 规则

必须包含：

- 项目路径、原任务编号、返工任务编号
- 失败来源、失败项列表、Reviewer Issues
- Main Decision Reason
- 允许修改文件、禁止修改文件
- 返工开发报告路径
- 不扩大范围限制

关键约束：只修复失败项，不新增无关功能。

## 7. 返工完成证据

返工完成后必须重新走完整验证链路：

Developer → Tester → Behavior Tester → Reviewer → Main Agent → COMPLETE 或 REQUEST_CHANGES

## 8. 人工确认边界

第一版只自动生成返工任务和返工 prompt，是否执行需要用户确认。

系统不自动调用 Claude Code 修改代码。

## 9. T041 实现建议

1. 新增 `tools/rework_runner.py`
2. 读取失败报告（Tester / Reviewer / Main Decision）
3. 生成返工任务描述和返工 prompt
4. 保存到 `prompts/rework_prompt.md`
5. 不自动调用 Claude Code
6. 命令：`python runner.py generate-rework-prompt G004`

## 10. 是否完成

是。T040 只做协议设计，T041 才实现自动生成返工 prompt MVP。
