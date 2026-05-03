# T011 阶段总结：第一阶段最小自动化闭环

## 1. 阶段目标

构建 `multi-agent-runner` 最小自动化闭环：runner.py 能自动读取任务、生成提示词、调用 Claude Code、判断结果、更新状态。

## 2. 已完成能力

| 任务 | 能力 | 状态 |
|------|------|------|
| T001 | 初始化项目骨架 | done |
| T002 | 读取 tasks.md 并找到 pending 任务 | done |
| T003 | 自动更新任务状态（complete / start） | done |
| T004 | 自动生成 current_prompt.md | done |
| T005 | 自动调用 Claude Code 执行当前提示词 | done |
| T006 | 保存执行结果与运行日志 | done |
| T007 | 根据执行结果判断成功 / 失败 | done |
| T008 | 成功后自动完成当前任务 | done |
| T009 | 单步自动执行闭环（run-next） | done |
| T009.1 | 修复成功误判：增加完成证据检查 | done |
| T009.2 | 实现 retry-current 重试当前任务 | done |
| T009.3 | 修复 Claude Code 非交互自动写文件权限 | done |
| T010 | 多任务自动执行循环（run-loop） | done |

## 3. 当前自动化闭环

```
run-next / run-loop
  ↓
读取 docs/tasks.md → 找到 pending 任务
  ↓
标记 in_progress → 生成 prompts/current_prompt.md
  ↓
调用 Claude Code（--permission-mode acceptEdits --print）
  ↓
保存 reports/claude/latest-output.md + history 报告
  ↓
判断结果：成功 + 有完成证据 → done
           成功 + 无证据 → 保持 in_progress（可 retry-current）
           失败 → 保持 in_progress
```

## 4. 关键修复

| 问题 | 修复 |
|------|------|
| Windows subprocess 中文乱码 | 增加 `encoding="utf-8", errors="replace"` |
| 只看退出码误判任务完成 | 增加 `has_completion_evidence` 检查开发报告 |
| Claude Code 不自动写文件 | 增加 `--permission-mode acceptEdits` |
| 任务卡在 in_progress 无法重试 | 新增 `retry-current` 命令 |
| 429 限额检测误匹配 stdout 代码 | 限定检测范围到 Stderr 段 |

## 5. 重要经验

1. 从最小闭环开始，逐步增加能力。
2. 任务状态可机器读写是自动化的基础。
3. 退出码 ≠ 任务完成，必须有完成证据。
4. runner.py 是调度中心，Claude Code 是执行器。
5. 非交互调用 Claude Code 必须开启自动编辑权限。

## 6. 踩坑记录

详见 `memory/pitfalls.md`。

关键要点：
- 不要在 Claude Code 内嵌套调用自动执行命令
- Windows 编码问题需要显式处理
- 完成证据是自动化的安全网

## 7. 当前项目状态

```
multi-agent-runner/
├─ runner.py              # 入口，支持 10 个命令
├─ config.yaml            # 基础配置
├─ docs/
│  ├─ tasks.md            # 任务清单（T001-T012）
│  ├─ requirement.md      # 需求说明
│  └─ workflow.md         # 工作流说明（已更新为实际工作流）
├─ agents/                # Agent 角色定义（6 个）
├─ prompts/               # 提示词（自动生成）
├─ reports/
│  ├─ run-log.md          # 运行日志
│  ├─ dev/                # 开发报告（按任务编号）
│  ├─ claude/             # Claude Code 执行输出
│  │  ├─ latest-output.md
│  │  └─ history/
│  └─ final/              # 阶段总结报告
├─ memory/                # 经验和踩坑记录
├─ projects/              # 验证项目
└─ tools/
   ├─ task_manager.py     # 任务解析和状态管理
   ├─ workflow_manager.py # 提示词生成
   ├─ claude_code_runner.py # Claude Code 调用
   └─ report_manager.py   # 报告生成和结果分析
```

## 8. 下一阶段建议

第二阶段建议从以下方向开始，仍然保持小步验证：

1. **工作流协议规范化** — 定义 Agent 间通信格式（输入/输出 JSON schema），让多 Agent 协作有统一协议。
2. **模型适配器接入国内模型 API** — 实现 `tools/model_adapter.py`，支持智谱、DeepSeek 等国内模型，用于 Planner / Reviewer 等不需要写代码的 Agent。
3. **Planner Agent 自动任务拆解** — 让 Planner 根据用户需求自动生成 tasks.md 中的任务列表。
4. **验证项目落地** — 用 `projects/down-100-floors-game/` 验证完整流程。
