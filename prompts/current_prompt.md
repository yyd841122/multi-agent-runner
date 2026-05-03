# 当前任务执行提示词

你现在是 Developer Agent。

## 当前任务

任务编号：T010
任务名称：多任务自动执行循环
状态：in_progress
角色：Developer

## 任务目标

让 runner.py 可以连续执行多个 pending 任务，直到没有 pending 任务或达到最大轮数。

## 任务原始内容

状态：in_progress
角色：Developer
目标：让 runner.py 可以连续执行多个 pending 任务，直到没有 pending 任务或达到最大轮数。

### 验收标准

- 可以连续查找 pending 任务
- 每轮可以自动生成提示词
- 每轮可以自动标记 in_progress
- 每轮可以自动调用 Claude Code
- 每轮可以自动判断执行结果
- 成功时自动 done
- 失败时停止循环并提示原因
- 支持最大轮数限制

---

## T009.1 修复 run-next 成功误判问题

状态：done
角色：Developer
目标：让 runner.py 在自动标记任务 done 前，检查任务完成证据，避免只根据退出码误判成功。

### 验收标准

- run-next 不再只根据 returncode=0 判断任务完成
- 自动 done 前必须检查 reports/dev/<任务编号>-dev-report.md 是否存在
- 如果执行成功但缺少开发报告，不自动标记 done
- 缺少完成证据时给出明确提示
- T010 不应被错误标记为 done

---

## T009.2 实现 retry-current 重新执行当前任务

状态：in_progress
角色：Developer
目标：让 runner.py 可以重新执行当前 in_progress 任务，用于任务执行不完整或缺少完成证据时的重试。

### 验收标准

- 可以识别当前第一个 in_progress 任务
- 可以根据该任务重新生成 prompts/current_prompt.md
- 可以重新调用 Claude Code
- 可以重新保存执行结果和历史报告
- 可以重新判断执行结果
- 成功且有完成证据时自动 done
- 成功但缺少完成证据时保持 in_progress
- 失败时保持 in_progress

---

## T009.3 修复 Claude Code 自动写文件权限

状态：in_progress
角色：Developer
目标：让 claude_code_runner.py 调用 Claude Code 时使用 acceptEdits 模式，使 Claude Code 可以在非交互执行中自动编辑文件。

### 验收标准

- run_claude_code() 调用 Claude Code 时包含 --permission-mode acceptEdits
- 保持原有 --print 调用方式
- 保持原有 stdout/stderr/returncode 返回结构
- 保持 encoding="utf-8", errors="replace"
- 不修改 T010 状态
- 不在 Claude Code 会话内执行 retry-current

## 工作要求

1. 只执行当前任务，不要提前实现后续任务。
2. 严格遵守任务验收标准。
3. 修改完成后输出修改文件列表。
4. 完成后生成对应开发报告。
5. 不要扩大需求范围。
6. 如果发现任务描述不清楚，先做最小合理假设，并在报告中说明。

请开始执行当前任务。