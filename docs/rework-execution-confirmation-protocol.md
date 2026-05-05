# Rework Execution Confirmation Protocol

## 1. 协议目标

定义自动返工执行前的人工确认协议。

核心原则：

- 返工 prompt 生成与返工执行必须严格分开
- 返工执行属于高风险写入操作，必须经过人工确认
- 确认必须使用严格格式，不接受模糊表达
- 最大返工次数为 3 轮，超过必须进入人工介入
- 本协议是 rework-protocol.md 和 full-task-loop-protocol.md 的补充

## 2. 背景

当前 multi-agent-runner 已具备以下返工基础：

- T040：自动返工协议设计
- T041：自动生成返工 prompt MVP
- `generate-rework-prompt` 命令可以基于 Tester/Reviewer/Main Agent 失败报告生成返工提示词
- 最大返工次数设计为 3 次

但当前系统只生成 rework prompt，不自动执行返工。用户需要手动将 rework prompt 提交给 Claude Code 执行。

T055 的目标是设计"自动返工执行前的人工确认协议"，为 T056 实现自动返工执行 MVP 做准备。

## 3. 当前返工能力

| 能力 | 状态 | 说明 |
|------|------|------|
| 生成 rework prompt | 已实现 | `generate-rework-prompt` |
| 读取失败报告 | 已实现 | Tester / Reviewer / Main Agent |
| 自动执行返工 | 未实现 | 当前需要人工操作 |
| 返工后重新测试 | 未实现 | 当前需要手动执行 |
| 返工轮次追踪 | 部分实现 | 通过任务编号后缀 R1/R2/R3 |
| 人工确认机制 | 未实现 | 本协议定义 |

## 4. 为什么不能直接自动返工

1. **返工执行是高风险写入操作。** 它会修改业务代码、覆盖文件，一旦出错难以回滚。
2. **模型可能理解错失败原因。** Tester FAIL 不一定代表代码错误，可能是 Tester 关键词匹配过窄（G007 碰撞测试已验证）。
3. **环境问题不应触发返工。** API Key 缺失、429 限额、网络超时属于环境阻塞，不是代码问题。
4. **用户需要知情权。** 返工会影响项目文件，用户应在执行前了解返工范围和风险。
5. **模糊表达容易导致误操作。** "继续""可以""试一下"不应被系统理解为确认执行。

## 5. 返工触发条件

### 5.1 可以触发返工候选

| 触发条件 | 来源 | 说明 |
|----------|------|------|
| Basic Tester FAIL | 基础静态测试报告 | 存在验收标准未通过 |
| Specialized Tester FAIL | 专项测试报告 | 碰撞/重力/行为等专项检查未通过 |
| Reviewer REQUEST_CHANGES | 审查报告 | DeepSeek Reviewer 建议修改 |
| Main Agent REQUEST_CHANGES | 综合决策报告 | 综合判断需要返工 |
| Main Agent BLOCKED 且原因可修复 | 综合决策报告 | 非环境阻塞的可修复问题 |
| Developer 完成证据与任务状态冲突 | 状态检查 | 状态不一致需要修复 |

### 5.2 不应触发返工

以下情况属于环境或执行阻塞，应进入 BLOCKED 或人工处理，而不是返工：

| 情况 | 原因 |
|------|------|
| API Key 缺失（DEEPSEEK_API_KEY 等） | 环境配置问题 |
| DeepSeek API 429 限额 | 模型调用限制 |
| Claude Code API 429 限额 | 模型调用限制 |
| 网络连接错误 | 基础设施问题 |
| .env 未加载 | 环境配置问题 |
| Reviewer 模型调用失败 | 外部依赖不可用 |
| Claude Code 超时但无代码改动证据 | 无法判断执行结果 |

## 6. 返工候选状态

### 6.1 定义

```
REWORK_CANDIDATE
```

含义：系统判断当前任务可能需要返工，但尚未得到用户确认，因此不得执行返工。

### 6.2 REWORK_CANDIDATE 允许做

| 操作 | 说明 |
|------|------|
| 生成 rework prompt | 基于失败证据自动生成 |
| 生成 rework summary | 汇总失败原因和建议范围 |
| 列出失败证据 | 展示 Tester/Reviewer/Main Agent 报告 |
| 列出建议返工范围 | 基于 project.yaml 的 allowed_files |
| 等待用户确认 | 进入等待状态 |
| 记录返工候选状态 | 写入返工轮次记录 |

### 6.3 REWORK_CANDIDATE 禁止做

| 操作 | 原因 |
|------|------|
| 自动调用 Claude Code 执行返工 | 未经确认的高风险写入 |
| 自动修改业务代码 | 未经确认的文件修改 |
| 自动重新跑 Developer | 未经确认的重复执行 |
| 自动增加返工轮次 | 轮次只能由确认后的执行触发 |
| 自动覆盖原始报告 | 原始报告应保留 |
| 自动进入下一轮 full loop | 未确认不能继续 |

## 7. 人工确认原则

1. **确认必须使用严格格式。** 不接受模糊表达。
2. **确认必须在 rework prompt 生成后。** 先看证据，再做决定。
3. **确认必须包含任务编号和返工轮次。** 避免误确认其他任务的返工。
4. **确认是一次性的。** 每次返工执行都需要新的确认。
5. **确认不可委托。** 系统不能代替用户确认。

## 8. 人工确认格式

### 8.1 接受的确认格式

用户必须明确输入以下格式之一：

**格式一（中文）：**

```text
确认执行 <task-id>-R<round> 返工
```

示例：

```text
确认执行 G007-R1 返工
确认执行 G006-R2 返工
确认执行 G004-R3 返工
```

**格式二（英文）：**

```text
APPROVE_REWORK task=<task-id> round=<round>
```

示例：

```text
APPROVE_REWORK task=G007 round=1
APPROVE_REWORK task=G006 round=2
APPROVE_REWORK task=G004 round=3
```

### 8.2 不接受的模糊表达

以下表达不视为确认，只能触发再次确认提示：

```text
继续
可以
试一下
你看着办
自动处理
好的
OK
yes
go
do it
```

### 8.3 模糊表达的处理

当用户输入模糊表达时，系统应输出：

```text
[WARNING] 未识别为有效返工确认。
请使用以下格式之一：

  确认执行 <task-id>-R<round> 返工

  或：

  APPROVE_REWORK task=<task-id> round=<round>
```

## 9. 确认后的执行流程

### 9.1 前置检查

确认后，系统在执行返工前必须检查：

| 检查项 | 条件 |
|--------|------|
| 任务处于 REWORK_CANDIDATE | 状态文件中已记录 |
| rework prompt 已生成 | `prompts/rework_prompt.md` 存在 |
| 返工轮次未超过 R3 | `< 3` |
| 用户输入严格确认格式 | 格式匹配通过 |
| 工作区状态允许执行 | 无未提交的关键变更 |
| 无 API Key 泄露风险 | `.env` 不在工作区变更中 |

### 9.2 执行步骤

```
用户确认
    │
    ▼
前置检查（6 项全部通过）
    │
    ├── 任一不通过 → STOP + 输出原因
    │
    ▼
读取 rework prompt
    │
    ▼
调用 Claude Code 执行返工
    │
    ▼
检查返工完成证据
    │
    ├── 证据缺失 → STOP + 报告失败
    │
    ▼
重新执行 Tester
    │
    ├── FAIL → 评估是否进入下一轮返工候选
    │
    ▼
重新执行 Reviewer
    │
    ├── REQUEST_CHANGES → 评估是否进入下一轮返工候选
    │
    ▼
重新执行 Main Decision
    │
    ├── REQUEST_CHANGES → 评估是否进入下一轮返工候选
    │
    ▼
COMPLETE → 记录返工成功
```

### 9.3 返工轮次递增

返工轮次只在返工执行完成后递增：

```
执行前：R1（第一次返工）
执行后：如果仍然 FAIL，进入 R2 候选
执行前：R2（第二次返工）
执行后：如果仍然 FAIL，进入 R3 候选
执行前：R3（第三次返工）
执行后：如果仍然 FAIL，进入人工介入
```

## 10. 未确认时的系统行为

### 10.1 默认行为

当任务进入 REWORK_CANDIDATE 但用户未确认时：

```text
[Rework Candidate] G007-R1
[Trigger] Collision Tester FAIL
[Evidence] G007-collision-test-report.md
[Suggested Scope] script.js
[Files Allowed] index.html, style.css, script.js, docs/tasks.md, reports/, memory/
[Files Forbidden] project.yaml, requirement.md, docs/future-platform-plan.md
[Confirmation Required]
  确认执行 G007-R1 返工
  或：
  APPROVE_REWORK task=G007 round=1
[Status] Waiting for user confirmation...
```

### 10.2 禁止行为

未确认时，系统不得：

1. 调用 Claude Code 执行返工
2. 修改业务代码
3. 覆盖原始报告
4. 增加返工轮次
5. 自动进入下一轮 full loop
6. 自动重试 Developer

### 10.3 用户可以做的

1. 查看失败证据
2. 修改 rework prompt 后再确认
3. 手动修复后跳过返工
4. 选择不返工，进入 BLOCKED
5. 请求人工介入

## 11. 最大返工次数限制

### 11.1 限制规则

| 轮次 | 编号 | 行为 |
|------|------|------|
| 第 1 次返工 | R1 | 允许生成 prompt + 确认后执行 |
| 第 2 次返工 | R2 | 允许生成 prompt + 确认后执行 |
| 第 3 次返工 | R3 | 允许生成 prompt + 确认后执行 |
| 第 4 次请求 | R4+ | 不生成执行型 prompt，生成人工介入报告 |

### 11.2 返工轮次记录

返工轮次通过以下方式追踪：

1. 任务编号后缀：`G007-R1`、`G007-R2`、`G007-R3`
2. 返工记录文件：`reports/rework/<task-id>-R<round>-rework-summary.md`
3. 子项目 `docs/tasks.md` 中的返工任务条目

### 11.3 超限处理

当返工轮次达到 3 次后仍然 FAIL 时：

```text
[Result] MANUAL_INTERVENTION_REQUIRED
[Reason] 已达到最大返工次数（3次）
[Rounds] R1 → FAIL, R2 → FAIL, R3 → FAIL
[Action] 需要人工检查任务要求、代码质量和模型输出
[Report] <project-root>/reports/final/<task-id>-manual-intervention-report.md
```

系统生成人工介入报告，不得继续生成执行型返工 prompt。

## 12. 人工介入规则

### 12.1 触发条件

| 条件 | 说明 |
|------|------|
| 返工轮次达到 R3 后仍然 FAIL | 代码可能存在根本问题 |
| 连续 3 次不同原因 FAIL | 问题可能不在代码层面 |
| 任务状态与证据严重冲突 | 无法自动判断 |
| API Key 或环境持续不可用 | 非代码问题 |
| 用户主动请求人工介入 | 用户判断 |

### 12.2 人工介入报告

路径：

```text
<project-root>/reports/final/<task-id>-manual-intervention-report.md
```

内容：

```markdown
# <task-id> Manual Intervention Report

## Trigger

触发原因：

## Task Status

当前任务状态：

## Rework History

| Round | Trigger | Result | Report |
|-------|---------|--------|--------|
| R1 | ... | FAIL | ... |
| R2 | ... | FAIL | ... |
| R3 | ... | FAIL | ... |

## Evidence Summary

- Developer Report:
- Tester Report:
- Reviewer Report:
- Main Decision:

## Suggested Actions

1.
2.
3.

## System Recommendation

系统建议：
```

### 12.3 人工介入后的处理

人工介入后，用户可以选择：

1. 手动修复代码，然后重新执行 Tester
2. 修改任务要求或验收标准
3. 跳过当前任务，标记为 BLOCKED
4. 重置返工轮次（清零 R 计数）
5. 放弃当前任务

## 13. 与 run-project-task-full 的衔接

### 13.1 当前行为

`run-project-task-full` 遇到失败时：

- 停止 full loop
- 生成或建议生成 rework prompt
- 输出失败证据
- 结束闭环，不自动重试

### 13.2 T056 实现后的行为

T056 实现后，`run-project-task-full` 可以增加 `--allow-rework` 参数：

```bash
python runner.py run-project-task-full --project <path> --task <id> --allow-rework
```

行为：

1. 遇到失败时，自动进入 REWORK_CANDIDATE
2. 自动生成 rework prompt
3. 输出确认提示，等待用户输入
4. 用户确认后，执行返工
5. 返工后重新运行 Tester / Reviewer / Main Decision
6. 如果仍然 FAIL，进入下一轮 REWORK_CANDIDATE
7. 超过 3 次进入人工介入

### 13.3 不带 --allow-rework 的行为

不带 `--allow-rework` 时，行为与当前一致：

- 失败后只生成 rework prompt
- 不自动执行返工
- 不进入 REWORK_CANDIDATE 等待循环

## 14. 与 generate-rework-prompt 的衔接

### 14.1 当前命令

```bash
python runner.py generate-rework-prompt <task-id>
```

### 14.2 T056 新增命令

```bash
python runner.py execute-rework --project <path> --task <task-id> --round <n> --confirmed
```

参数：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--project` | 是 | 子项目根路径 |
| `--task` | 是 | 任务编号 |
| `--round` | 是 | 返工轮次（1/2/3） |
| `--confirmed` | 是 | 确认标志，必须显式传入 |

### 14.3 执行流程

```
execute-rework
    │
    ▼
前置检查
    ├── rework prompt 是否存在？
    ├── 返工轮次是否 <= 3？
    ├── confirmed 参数是否传入？
    ├── 工作区状态是否允许？
    │
    ├── 任一不通过 → STOP + 输出原因
    │
    ▼
读取 rework prompt
    │
    ▼
调用 Claude Code 执行返工
    │
    ▼
检查返工完成证据
    │
    ▼
返回执行结果
```

## 15. 返工记录文件

### 15.1 路径规则

| 文件 | 路径 | 说明 |
|------|------|------|
| 返工 prompt | `<project-root>/prompts/rework_prompt.md` | 当前返工提示词 |
| 返工历史 prompt | `<project-root>/prompts/rework-prompt-R<round>.md` | 历史返工提示词 |
| 返工总结 | `<project-root>/reports/rework/<task-id>-R<round>-rework-summary.md` | 每轮返工总结 |
| 人工介入报告 | `<project-root>/reports/final/<task-id>-manual-intervention-report.md` | 超限时生成 |

### 15.2 示例路径

```text
projects/down-100-floors-game/prompts/rework_prompt.md
projects/down-100-floors-game/prompts/rework-prompt-R1.md
projects/down-100-floors-game/reports/rework/G007-R1-rework-summary.md
projects/down-100-floors-game/reports/rework/G007-R2-rework-summary.md
projects/down-100-floors-game/reports/rework/G007-R3-rework-summary.md
projects/down-100-floors-game/reports/final/G007-manual-intervention-report.md
```

### 15.3 返工总结内容

```markdown
# <task-id>-R<round> Rework Summary

## Task

原任务编号：
返工轮次：R<round>

## Trigger

触发原因：
失败来源：

## Failure Evidence

- Tester Report:
- Reviewer Report:
- Main Decision:

## Rework Scope

允许修改文件：
禁止修改文件：

## Execution

是否确认执行：
确认时间：
执行结果：

## Result

返工后 Tester 结果：
返工后 Reviewer 结果：
返工后 Main Decision：

## Next Action

下一步建议：
```

## 16. 命令权限边界

### 16.1 返工命令分类

返工执行属于高风险写入操作，不属于 A 类低风险自动执行命令。

| 命令 | 分类 | 说明 |
|------|------|------|
| `generate-rework-prompt` | A 类 | 只生成文件，不修改业务代码 |
| `execute-rework --confirmed` | C 类 | 需要人工确认 + 任务显式授权 |
| `run-project-task-full --allow-rework` | C 类 | 需要人工确认 + 参数显式传入 |

### 16.2 不得加入全局 allowlist 的命令

```bash
python runner.py execute-rework *
python runner.py run-project-task-full --allow-rework *
```

### 16.3 执行条件

返工相关命令只能在以下条件**全部满足**时执行：

1. 任务已经进入 REWORK_CANDIDATE
2. 已生成 rework prompt
3. 用户输入严格确认格式
4. 未超过最大返工次数 3
5. 没有 API Key 泄露风险
6. 工作区状态允许执行

## 17. PASS / REQUEST_CHANGES / BLOCKED 处理

### 17.1 返工后 PASS

```text
[Result] PASS → COMPLETE
[Rework Round] R<round>
[Action] 返工成功，任务完成
```

### 17.2 返工后 REQUEST_CHANGES

```text
[Result] REQUEST_CHANGES
[Rework Round] R<round>
[Action] 进入下一轮 REWORK_CANDIDATE（如果 R<round> < 3）
         或进入人工介入（如果 R<round> >= 3）
```

### 17.3 返工后 BLOCKED

```text
[Result] BLOCKED
[Action] 停止返工循环，不增加返工轮次
[Reason] 环境/基础设施问题，不是代码问题
[Next] 人工检查环境配置
```

BLOCKED 不消耗返工轮次，因为它不是代码问题。

## 18. 禁止事项

### 18.1 系统禁止行为

1. **禁止未确认时执行返工**
2. **禁止接受模糊表达作为确认**
3. **禁止超过 3 次返工**
4. **禁止自动无限循环返工**
5. **禁止返工中修改禁止文件**（project.yaml、主框架代码、.env 等）
6. **禁止返工命令进入全局 allowlist**
7. **禁止返工时打印 API Key**
8. **禁止覆盖原始报告**（应另存为返工报告）
9. **禁止在环境阻塞时生成返工任务**
10. **禁止自动跳过人工介入**

### 18.2 用户禁止行为

1. 不要一次确认多个任务的返工
2. 不要在未查看失败证据时确认返工
3. 不要在 API Key 缺失时要求返工
4. 不要在 429 限额期间要求返工
5. 不要要求系统绕过确认机制

## 19. T056 实现建议

### 19.1 代码组织

建议在 `tools/` 下新增 `rework_executor.py`：

```python
class ReworkExecutor:
    def __init__(self, project_path, task_id, round_number, config):
        self.project_path = project_path
        self.task_id = task_id
        self.round_number = round_number
        self.config = config
        self.max_retries = 3

    def check_prerequisites(self):
        """前置检查"""
        # 1. 检查 rework prompt 是否存在
        # 2. 检查返工轮次是否 <= 3
        # 3. 检查工作区状态
        # 4. 检查 API Key 安全
        pass

    def execute(self, confirmed=False):
        """执行返工"""
        if not confirmed:
            return "ERROR: 返工执行需要用户确认"
        if not self.check_prerequisites():
            return "ERROR: 前置检查未通过"
        # 读取 rework prompt
        # 调用 Claude Code 执行
        # 检查完成证据
        pass

    def re_test(self):
        """返工后重新测试"""
        # 重新执行 Tester
        # 重新执行 Reviewer
        # 重新执行 Main Decision
        pass
```

### 19.2 runner.py 集成

```python
elif command == "execute-rework":
    project = get_arg(args, "--project")
    task = get_arg(args, "--task")
    round_num = get_arg(args, "--round")
    confirmed = "--confirmed" in args
    rework_executor.execute(project, task, round_num, confirmed)
```

### 19.3 确认格式解析

```python
import re

def parse_rework_confirmation(user_input):
    """解析返工确认格式"""
    # 格式一：确认执行 <task-id>-R<round> 返工
    pattern1 = r"^确认执行\s+([A-Z]\d+)-R(\d+)\s+返工$"
    match1 = re.match(pattern1, user_input.strip())

    # 格式二：APPROVE_REWORK task=<task-id> round=<round>
    pattern2 = r"^APPROVE_REWORK\s+task=([A-Z]\d+)\s+round=(\d+)$"
    match2 = re.match(pattern2, user_input.strip())

    if match1:
        return {"task_id": match1.group(1), "round": int(match1.group(2))}
    elif match2:
        return {"task_id": match2.group(1), "round": int(match2.group(2))}
    else:
        return None  # 未识别为有效确认
```

### 19.4 实现优先级

1. 先实现 `execute-rework` 命令（前置检查 + Claude Code 调用）
2. 再实现返工后重新测试链路
3. 最后集成到 `run-project-task-full --allow-rework`

### 19.5 验证步骤

1. 用一个已知 FAIL 的场景验证 rework prompt 生成
2. 用严格确认格式验证 execute-rework 执行
3. 用模糊表达验证拒绝逻辑
4. 用 R4+ 验证人工介入触发
5. 验证返工后重新测试链路

## 20. 后续扩展方向

1. **可视化确认界面**：将终端确认升级为 Web UI 确认
2. **条件自动确认**：对特定类型的 FAIL（如 Tester 关键词误判），支持用户预设自动确认规则
3. **返工策略模板**：不同类型的 FAIL 使用不同的返工策略
4. **返工成本估算**：在确认前提示本次返工预估的 API 调用次数和耗时
5. **返工历史分析**：汇总返工成功率、常见失败原因、模型表现等
6. **智能返工建议**：基于历史数据，建议是否值得继续返工或直接人工介入
