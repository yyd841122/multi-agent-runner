# 工作流说明

## 第一阶段实际工作流（已验证）

```
用户 / 外层 runner
    ↓
runner.py 读取 docs/tasks.md
    ↓
找到 pending 任务
    ↓
生成 prompts/current_prompt.md
    ↓
调用 Claude Code（--permission-mode acceptEdits --print）
    ↓
Claude Code 修改文件并生成开发报告
    ↓
runner.py 保存 reports/claude/latest-output.md 和 history 报告
    ↓
runner.py 根据退出码判断结果
    ↓
runner.py 检查完成证据 reports/dev/<任务编号>-dev-report.md
    ↓
成功 + 有证据 → 标记 done
失败 或 缺少证据 → 保持 in_progress
    ↓
可通过 retry-current 重新执行当前任务
```

## runner.py 命令一览

| 命令 | 功能 |
|------|------|
| `python runner.py` | 显示下一个 pending 任务 |
| `python runner.py complete <T编号>` | 将任务状态改为 done |
| `python runner.py start <T编号>` | 将任务状态改为 in_progress |
| `python runner.py generate-prompt` | 生成下一个 pending 任务的提示词 |
| `python runner.py run-current` | 调用 Claude Code 执行当前提示词 |
| `python runner.py check-result` | 判断最新执行结果 |
| `python runner.py auto-complete-success` | 成功时自动完成当前 in_progress 任务 |
| `python runner.py run-next` | 单步自动闭环执行下一个 pending 任务 |
| `python runner.py retry-current` | 重新执行当前 in_progress 任务 |
| `python runner.py run-loop [最大轮数]` | 多任务自动执行循环（默认 10 轮） |

## 关键原则

1. **runner.py 是最外层执行器和调度中心。**
2. **Claude Code 是代码执行器，不是主调度器。** Claude Code 不能在自己的执行过程中再次调用 `runner.py run-current` / `run-next` / `retry-current` / `run-loop`。
3. **完成任务不能只看退出码，必须看完成证据。** 完成证据 = `reports/dev/<任务编号>-dev-report.md` 是否存在。
4. **retry-current 是处理 in_progress 卡住任务的必要能力。**

## 最终目标工作流

| 阶段 | Agent | 职责 |
|------|-------|------|
| 接收需求 | Main Agent | 接收用户需求，调度各子 Agent |
| 任务拆解 | Planner Agent | 将需求拆解为可执行任务 |
| 开发实现 | Developer Agent | 按任务生成代码 |
| 测试验证 | Tester Agent | 对生成代码进行测试 |
| 审查评估 | Reviewer Agent | 审查是否符合需求 |
| 总结报告 | Reporter Agent | 输出最终报告 |
