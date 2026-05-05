# Full Task Loop Protocol

## 1. 协议目标

定义 `run-project-task-full` 命令的协议规范，将单个任务的 Developer / Tester / Specialized Tester / Reviewer / Main Agent 串成完整闭环。

本协议只做设计，不实现代码。

## 2. 为什么需要单任务完整闭环

### 2.1 当前状态

系统已经具备各 Agent 的单步能力：

- `run-project-next`：自动执行子项目下一个 Developer 任务
- `test-game-task`：执行基础 Tester 静态检查
- `test-game-behavior`：执行 G004 键盘移动行为检查
- `review-game-task`：调用 DeepSeek Reviewer
- `decide-game-task`：做 Main Agent 综合决策
- `generate-rework-prompt`：生成返工 prompt

但用户仍需手动依次执行：

```powershell
python runner.py run-project-next --project projects/down-100-floors-game
python runner.py test-game-task G006
python runner.py review-game-task G006
python runner.py decide-game-task G006
```

### 2.2 目标

单任务完整闭环是将半自动走向自动化落地的关键一步：

- 一次命令完成单个任务的全生命周期
- 减少用户手动操作
- 保留失败停止、返工限制和人工介入机制

### 2.3 不做什么

- 不做项目级连续循环（`run-loop` 留待后续）
- 不做无人值守全自动执行
- 不跳过人工介入边界

## 3. 命令格式

### 3.1 标准格式

```powershell
python runner.py run-project-task-full --project projects/down-100-floors-game --task G006
```

### 3.2 简化格式

```powershell
python runner.py run-project-task-full --project projects/down-100-floors-game
```

如果不传 `--task`，默认执行当前第一个 `pending` 任务。

### 3.3 第一版建议

优先要求显式传入 `--task`，避免误执行错误任务。

简化格式作为后续版本扩展。

## 4. 输入参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--project` | 是 | 子项目根路径 |
| `--task` | 第一版建议必填 | 任务编号 |
| `--dry-run` | 否 | 只输出执行计划，不实际执行 |
| `--skip-developer` | 否 | 跳过 Developer 阶段（任务已开发完成时） |
| `--max-retries` | 否 | 最大返工次数，默认 3 |

## 5. 输出结果

### 5.1 终端输出

```
[Full Task Loop] G006 简单重力下落
[1/5] Developer ... OK
[2/5] Basic Tester ... PASS
[3/5] Specialized Tester (gravity) ... PASS
[4/5] Reviewer ... APPROVE
[5/5] Main Decision ... COMPLETE
[Result] COMPLETE
```

### 5.2 完整闭环报告

保存路径：

```text
<project-root>/reports/final/<task-id>-full-loop-report.md
```

例如：

```text
projects/down-100-floors-game/reports/final/G006-full-loop-report.md
```

### 5.3 报告内容

```markdown
# <task-id> Full Loop Report

## Task

任务编号：<task-id>
任务名称：<任务名称>

## Developer Result

状态：done / failed / skipped
报告路径：<developer-report-path>

## Basic Tester Result

状态：PASS / FAIL / BLOCKED
报告路径：<basic-tester-report-path>

## Specialized Tester Result

类型：gravity / collision / none
状态：PASS / FAIL / BLOCKED / N/A
报告路径：<specialized-tester-report-path>

## Reviewer Result

状态：APPROVE / REQUEST_CHANGES / BLOCKED
报告路径：<reviewer-report-path>

## Main Decision

结果：COMPLETE / REQUEST_CHANGES / BLOCKED
报告路径：<main-decision-report-path>

## Rework

返工轮次：0 / 1 / 2 / 3
返工 prompt 路径：<rework-prompt-path>

## Final Status

COMPLETE / REQUEST_CHANGES / BLOCKED / MANUAL_INTERVENTION_REQUIRED

## Next Action

建议下一步：
```

## 6. 单任务完整闭环流程

```
┌─────────────────────────────────────────────────────┐
│ run-project-task-full --project <path> --task <id>  │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
              ┌────────────────┐
              │ 读取 project.yaml │
              └────────┬───────┘
                       │
                       ▼
              ┌────────────────┐
              │ 读取 tasks.md   │
              └────────┬───────┘
                       │
                       ▼
              ┌────────────────┐
              │ 定位目标任务     │
              └────────┬───────┘
                       │
                       ▼
              ┌────────────────┐     ┌──────────────┐
              │ Developer 阶段  │────►│ 超时/失败？   │
              └────────┬───────┘     │ → STOP       │
                       │              └──────────────┘
                       ▼
              ┌────────────────┐
              │ Developer 报告？│
              │ 不存在 → STOP  │
              └────────┬───────┘
                       │
                       ▼
              ┌────────────────┐     ┌──────────────┐
              │ Basic Tester    │────►│ FAIL？       │
              └────────┬───────┘     │ → 生成 rework│
                       │              └──────────────┘
                       ▼
              ┌─────────────────┐    ┌──────────────┐
              │ Specialized      │───►│ FAIL？       │
              │ Tester（如需要） │    │ → 生成 rework│
              └────────┬────────┘    └──────────────┘
                       │
                       ▼
              ┌────────────────┐     ┌──────────────────┐
              │ Reviewer        │────►│ REQUEST_CHANGES？│
              └────────┬───────┘     │ → 生成 rework    │
                       │              └──────────────────┘
                       ▼
              ┌────────────────┐
              │ Main Decision   │
              └────────┬───────┘
                       │
            ┌──────────┼──────────┐
            │          │          │
            ▼          ▼          ▼
     ┌─────────┐ ┌──────────┐ ┌─────────┐
     │COMPLETE │ │REQUEST_   │ │BLOCKED  │
     │ → 结束  │ │CHANGES   │ │ → STOP  │
     └─────────┘ │→ rework  │ └─────────┘
                 └────┬─────┘
                      │
                      ▼
              ┌────────────────┐
              │ 返工轮次 < 3？  │
              │              │
              │ 是 → 执行返工  │
              │ 否 → 人工介入  │
              └────────────────┘
```

## 7. Developer 阶段规则

### 7.1 执行条件

| 任务状态 | Developer 报告 | 行为 |
|----------|---------------|------|
| `pending` | 不存在 | 执行 Developer |
| `done` | 存在 | 跳过 Developer |
| `in_progress` | 不存在 | 停止，提示用户确认 |
| `done` | 不存在 | 停止，状态冲突 |
| `in_progress` | 存在 | 跳过 Developer（可能是上轮返工） |

### 7.2 超时与失败处理

| 情况 | 处理 |
|------|------|
| Claude Code 超时 | 停止闭环，不进入 Tester |
| returncode 非 0，报告存在，任务已 done | 允许继续，记录 `completed_with_model_error=True` |
| returncode 非 0，报告不存在 | 停止闭环 |
| API 429 | 停止闭环，不重试 |

### 7.3 completed_with_model_error 处理

当 `completed_with_model_error=True` 时：

- 可以继续进入 Tester 阶段
- 但 full-loop-report 中必须记录模型异常
- 终端输出中必须标注 `[WARNING] completed with model error`

## 8. Tester 阶段规则

### 8.1 执行前提

- Developer 报告必须存在
- Developer 阶段未超时

### 8.2 基础 Tester

```powershell
# 用户手动方式
python runner.py test-game-task <task-id>

# full loop 中由内部函数调用
tester_runner.run_basic_test(project_path, task_id)
```

### 8.3 判定规则

| Tester 结果 | 后续行为 |
|------------|---------|
| PASS | 继续专项 Tester 或 Reviewer |
| FAIL | 停止，不进入 Reviewer，生成 rework prompt |
| BLOCKED | 停止，提示人工检查 |

## 9. 专项 Tester 选择规则

### 9.1 选择映射

根据任务编号或任务内容选择专项 Tester：

```python
special_tester_map = {
    "G004": "behavior",    # 键盘移动行为检查
    "G006": "gravity",     # 重力下落行为检查
    "G007": "collision",   # 碰撞检测行为检查
}
```

### 9.2 选择逻辑

1. 检查 `special_tester_map` 是否包含当前任务编号
2. 如果包含，执行对应专项 Tester
3. 如果不包含，跳过专项 Tester
4. 专项 Tester 与基础 Tester 独立判定

### 9.3 专项 Tester 结果处理

| 专项 Tester 结果 | 后续行为 |
|-----------------|---------|
| PASS | 继续 Reviewer |
| FAIL | 停止，不进入 Reviewer，生成 rework prompt |
| BLOCKED | 停止，提示人工检查 |
| N/A（无对应专项 Tester） | 继续 Reviewer |

### 9.4 第一版实现建议

- T049.1 可以先只设计 `special_tester_map` 接口，不一定立刻实现所有专项 Tester
- T050 再实现 G006 gravity tester
- G007 collision tester 留待第五阶段后续任务

## 10. Reviewer 阶段规则

### 10.1 执行前提

- 基础 Tester 必须通过（PASS）
- 如果有专项 Tester，专项 Tester 也必须通过（PASS）

### 10.2 执行规则

```powershell
# 用户手动方式
python runner.py review-game-task <task-id>

# full loop 中由内部函数调用
reviewer_runner.run_review(project_path, task_id)
```

### 10.3 判定规则

| Reviewer 结果 | 后续行为 |
|--------------|---------|
| APPROVE | 继续 Main Decision |
| REQUEST_CHANGES | 停止，生成 rework prompt |
| BLOCKED | 停止，不重试 |
| API 429 | 停止，状态为 BLOCKED |
| API 调用失败 | 停止，状态为 BLOCKED |

### 10.4 结构化解析

Reviewer 输出必须结构化解析，提取：

- `Status`：PASS / FAIL
- `Decision`：APPROVE / REQUEST_CHANGES / RETRY / BLOCKED
- `Issues`：问题列表

## 11. Main Agent 决策规则

### 11.1 证据输入

Main Agent 在 full loop 中应读取：

| 证据 | 路径 | 必须 |
|------|------|------|
| Developer report | `reports/dev/<task-id>-dev-report.md` | 是 |
| Basic Tester report | `reports/test/<task-id>-test-report.md` | 是 |
| Specialized Tester report | `reports/test/<task-id>-<type>-test-report.md` | 如存在 |
| Reviewer report | `reports/review/<task-id>-review-report.md` | 是 |

### 11.2 决策输出

| 结果 | 含义 | 后续 |
|------|------|------|
| `COMPLETE` | 所有证据通过 | 结束闭环 |
| `REQUEST_CHANGES` | 有证据失败或 Reviewer 不批准 | 生成 rework prompt |
| `BLOCKED` | 模型限额/超时/缺报告 | 停止闭环 |

### 11.3 判定规则

```
如果 Developer done AND Basic Tester PASS AND
   (无专项 Tester OR 专项 Tester PASS) AND
   Reviewer APPROVE:
    → COMPLETE

如果 Tester FAIL OR 专项 Tester FAIL:
    → REQUEST_CHANGES

如果 Reviewer REQUEST_CHANGES:
    → REQUEST_CHANGES

如果 模型限额 OR 超时 OR 缺报告:
    → BLOCKED
```

### 11.4 Main Agent 不做什么

- 不直接修改业务代码
- 不自动执行返工（只生成 rework prompt）
- 不跳过证据链

## 12. 失败处理与返工 prompt

### 12.1 生成条件

当以下任一情况发生时，生成返工 prompt：

- Basic Tester FAIL
- Specialized Tester FAIL
- Reviewer REQUEST_CHANGES
- Main Decision REQUEST_CHANGES

### 12.2 生成方式

```powershell
# 用户手动方式
python runner.py generate-rework-prompt <task-id> <round>

# full loop 中由内部函数调用
rework_generator.generate_rework_prompt(project_path, task_id, round_number)
```

### 12.3 返工 prompt 内容

返工 prompt 应包含：

- 原始任务要求和验收标准
- 失败的 Tester / Reviewer / Main Agent 报告内容
- 返工目标（针对失败项）
- 允许修改的文件范围
- 禁止修改的文件范围

### 12.4 第一版行为

第一版 full loop **只生成 rework prompt，不自动执行返工**。

返工 prompt 生成后，闭环结束，输出：

```
[Result] REQUEST_CHANGES
[Rework] R1 prompt generated: <rework-prompt-path>
[Next] 用户确认后可执行返工
```

## 13. 最大返工次数限制

### 13.1 限制规则

继承 T041 返工协议的规则：

- 最大返工次数：3
- R1-R3：允许生成返工 prompt
- R4+：不生成 prompt，生成人工介入报告

### 13.2 返工轮次记录

返工轮次通过任务编号后缀追踪：

```
G006    → 原始任务
G006-R1 → 第一次返工
G006-R2 → 第二次返工
G006-R3 → 第三次返工
G006-R4+ → 不自动生成，人工介入
```

### 13.3 超限处理

当返工轮次达到 3 次时：

```
[Result] MANUAL_INTERVENTION_REQUIRED
[Reason] 已达到最大返工次数（3次）
[Action] 需要人工检查任务要求、代码质量和模型输出
```

## 14. 人工介入边界

### 14.1 必须停止并人工介入的情况

| 情况 | 原因 |
|------|------|
| Claude Code 超时 | 无法确认任务是否完成 |
| Reviewer API 429 | 模型限额，无法自动恢复 |
| DeepSeek API 调用失败 | 外部依赖不可用 |
| Developer 报告缺失 | 无法判断开发是否完成 |
| Tester BLOCKED | 无法执行测试 |
| Main Agent BLOCKED | 无法做综合决策 |
| 超过最大返工次数 | 自动返工已无意义 |
| 任务状态与证据冲突 | 无法自动判断真实状态 |
| `script.js` 等关键文件不存在 | 无法执行测试 |

### 14.2 人工介入报告

当触发人工介入时，生成：

```text
<project-root>/reports/final/<task-id>-manual-intervention.md
```

内容包括：

- 触发原因
- 当前任务状态
- 各阶段结果
- 建议的下一步操作

## 15. 安全停止条件

### 15.1 自动停止条件

full loop 在以下条件自动停止：

1. 任何阶段出现 BLOCKED
2. Developer 超时或失败
3. Tester FAIL（不继续 Reviewer）
4. 专项 Tester FAIL（不继续 Reviewer）
5. Reviewer API 429 或调用失败
6. 超过最大返工次数
7. 任务状态与证据冲突

### 15.2 永不自动执行的操作

full loop 永不自动执行以下操作：

1. 删除文件
2. 重置 Git
3. 推送代码
4. 调用 `run-project-next` 执行下一个任务
5. 无限循环返工

## 16. 命令权限策略

### 16.1 设计原则

真正可控的自动化应该是：

- 低风险命令自动执行
- 明确授权命令自动执行
- 高风险命令人工确认
- 危险命令禁止执行

### 16.2 A 类命令：允许自动执行，不需要用户确认

以下命令属于低风险读取、检查、验证命令，可以在 full task loop 中自动执行：

```powershell
git status
git status --short
git diff --stat
git log --oneline -5
git branch --show-current
git remote -v
python runner.py
python -m py_compile runner.py
python -m py_compile tools/project_runner.py
python -m py_compile tools/tester_runner.py
python -m py_compile tools/main_agent.py
Test-Path <path>
Get-Content <path> -Encoding UTF8 -Tail 80
Select-String -Path <path> -Pattern "<pattern>"
```

用途：

- 检查工作区状态
- 检查当前 pending 任务
- 检查完成证据
- 检查报告内容
- 检查源码是否包含关键逻辑
- 编译验证 Python 文件

### 16.3 B 类命令：仅在明确 Git 备份任务中允许自动执行

以下命令会改变 Git 历史或远程仓库，仅在明确的 Git 备份任务中允许自动执行：

```powershell
git add .
git commit -m "<message>"
git push
```

**允许场景：**

- `Txxx.1 提交并推送...` 类任务
- `阶段总结与 Git 备份` 类任务
- 明确写有 `git commit / git push` 验收标准的任务

**不允许场景：**

- 普通开发任务
- Tester 任务
- Reviewer 任务
- Main Decision 任务
- 返工 prompt 生成任务

### 16.4 C 类命令：需要人工确认或任务显式授权

以下命令可能改变或删除文件，默认需要人工确认：

```powershell
git restore <file>
git checkout -- <file>
Remove-Item <file>
Move-Item <file>
Copy-Item <source> <target>
```

**允许示例：**

- 恢复 `projects/down-100-floors-game/prompts/current_prompt.md`
- 删除明确指定的失败临时日志
- 清理明确指定的临时文件

**禁止泛化为删除整个目录。**

### 16.5 D 类命令：禁止自动执行

以下命令在任何自动化流程中禁止执行：

```powershell
git reset --hard
git clean -fd
Remove-Item -Recurse
rm -rf
del /s
rmdir /s
```

同时禁止：

- 删除 `.git/`
- 删除 `reports/`
- 删除 `memory/`
- 删除 `projects/`
- 删除 `docs/`
- 打印或提交 API Key
- 修改 secrets
- 批量删除未明确授权的文件

### 16.6 full task loop 中的默认行为

在 `run-project-task-full` 中，系统可以自动执行：

- 状态检查命令（A 类）
- Python 编译检查（A 类）
- 完成证据检查（A 类）
- 测试命令（A 类）
- Reviewer 命令（A 类）
- Main Decision 命令（A 类）
- 返工 prompt 生成命令（A 类）

但遇到以下情况必须停止并提示用户：

- 需要删除文件（C 类）
- 需要恢复文件（C 类）
- 需要重置 Git（D 类）
- 需要 push 非备份任务的改动（B 类）
- 检测到 API Key 或疑似 secret
- 出现超时、429、模型调用失败

## 17. 报告与证据路径

### 17.1 Full Loop 完整闭环报告

```text
<project-root>/reports/final/<task-id>-full-loop-report.md
```

### 17.2 人工介入报告

```text
<project-root>/reports/final/<task-id>-manual-intervention.md
```

### 17.3 各阶段报告

| 阶段 | 报告路径 |
|------|----------|
| Developer | `<project-root>/reports/dev/<task-id>-dev-report.md` |
| Basic Tester | `<project-root>/reports/test/<task-id>-test-report.md` |
| Specialized Tester | `<project-root>/reports/test/<task-id>-<type>-test-report.md` |
| Reviewer | `<project-root>/reports/review/<task-id>-review-report.md` |
| Main Decision | `<project-root>/reports/main/<task-id>-main-decision.md` |

### 17.4 返工 Prompt

```text
<project-root>/prompts/rework-prompt-<round>.md
```

## 18. T049.1 实现建议

### 18.1 代码组织

建议在 `tools/` 下新增 `full_task_loop.py`：

```python
class FullTaskLoop:
    def __init__(self, project_path, task_id, config):
        self.project_path = project_path
        self.task_id = task_id
        self.config = config
        self.rework_round = 0
        self.max_retries = 3

    def run(self):
        """执行完整闭环"""
        # 1. Developer 阶段
        # 2. Basic Tester 阶段
        # 3. Specialized Tester 阶段
        # 4. Reviewer 阶段
        # 5. Main Decision 阶段
        # 6. 生成 full-loop-report
        pass
```

### 18.2 runner.py 集成

```python
# runner.py 新增命令
elif command == "run-project-task-full":
    project = get_arg(args, "--project")
    task = get_arg(args, "--task")
    full_task_loop.run(project, task)
```

### 18.3 实现优先级

1. 先实现 Developer → Basic Tester → Reviewer → Main Decision 主线
2. 再集成 Specialized Tester 选择逻辑
3. 最后集成 rework prompt 生成和返工循环

### 18.4 验证步骤

1. 用已完成的 G005 验证 full loop 不会重复执行
2. 用 G006 验证完整闭环
3. 验证失败停止逻辑
4. 验证 rework prompt 生成

---

## Command Permission Policy

`run-project-task-full` 和后续自动化命令必须遵守 `docs/command-permission-policy.md`。

核心原则：

- 低风险命令自动执行
- Git 备份任务中允许 Git 提交推送
- 文件恢复和删除需要人工确认或任务显式授权
- 危险命令禁止执行
- `.env` 和 API Key 永远不能提交或打印
