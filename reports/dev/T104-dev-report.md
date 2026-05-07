# T104 Dev Report

## Task

设计 Claude Code + 智谱代理 tool-use 兼容性修复方案。

## Scope

本轮只做设计，不修改代码，不执行真实任务。

## Changed Files

- docs/claude-zhipu-tool-use-fix-plan.md（new — 修复方案文档）
- reports/dev/T104-dev-report.md（new — 本文件）
- docs/tasks.md（modified — T104 状态更新、T105-T110 新增）
- memory/lessons.md（modified — T104 经验追加）
- memory/pitfalls.md（modified — T104 避坑追加）

## Diagnosis Basis

基于 T103 诊断结论：

| 测试场景 | 结果 | 说明 |
|----------|------|------|
| claude --print "OK" | pass | 秒级返回 |
| claude --acceptEdits --print "OK" | pass | 秒级返回 |
| claude --acceptEdits --print "创建文件" | timeout | 120 秒无响应 |
| claude --print "创建文件" | pass | 权限拒绝后正常返回 |

**诊断分类：C — acceptEdits + tool use 兼容性问题**

根因：Claude Code 在 acceptEdits 模式下执行工具后，将 tool_result 发回智谱 API 等待下一轮响应时卡住。

## Candidate Fix Options

比较了 6 个候选方案：

| 方案 | 核心思路 | 改动量 | 可行性 |
|------|---------|--------|--------|
| A | 去掉 acceptEdits，用默认权限 | 小 | 高（诊断用） |
| B | runner 调用模式参数可配置 | 中 | 高 |
| C | 改造子进程调用方式 | 小 | 低（非根因） |
| D | 更换智谱代理模型/兼容层 | 外部依赖 | 中 |
| E | runner 自执行 patch | 大 | 高（长期） |
| F | 切换官方 Claude 模型 | 小 | 高（过渡） |

## Recommended Strategy

- **短期**：方案 B + A（可配置 permission mode + 诊断验证）
- **中期**：方案 D（评估智谱 API tool_use 兼容性）
- **长期**：方案 E（runner 自执行 patch）
- **备用**：方案 F（切换官方 Claude）

## Next Tasks

| 任务 | 角色 | 目标 |
|------|------|------|
| T105 | Architect | 设计 configurable Claude permission mode |
| T106 | Developer | 实现 run_claude_code permission mode 配置 |
| T107 | Tester | 验证 default mode 最小 Claude Code 调用 |
| T108 | Tester | 验证 acceptEdits tool-use blocked 回归 |
| T109 | Researcher | 评估智谱代理 tool_use/tool_result 兼容性 |
| T110 | Decision | 决策真实执行路线 |

## Safety Result

| 检查项 | 结果 |
|--------|------|
| 是否调用 run-project-task-full | no |
| 是否执行真实任务 | no |
| 是否调用 Claude Code | no |
| 是否修改业务代码 | no |
| 是否修改框架代码 | no |
| 是否自动进入下一任务 | no |
| 是否自动 Git backup | no |

## Next

T105：设计 configurable Claude permission mode
