# Tasks

## T001 初始化项目骨架

状态：done
角色：Developer
目标：创建 multi-agent-runner 最小目录结构。

### 验收标准

- 基础目录存在
- 基础文件存在
- runner.py 可以运行

---

## T002 读取任务清单并找到下一个 pending 任务

状态：done
角色：Developer
目标：让 runner.py 可以读取 docs/tasks.md，并找到第一个 pending 任务。

### 验收标准

- runner.py 可以读取 docs/tasks.md
- 可以解析任务编号、任务名称、状态、角色、目标
- 可以找到第一个状态为 pending 的任务
- 如果没有 pending 任务，可以给出明确提示

---

## T003 实现任务状态自动更新

状态：done
角色：Developer
目标：让 runner.py 可以通过命令自动修改 docs/tasks.md 中指定任务的状态。

### 验收标准

- 可以通过命令把指定任务状态改为 done
- 可以通过命令把指定任务状态改为 in_progress
- 修改后 docs/tasks.md 内容保持原有结构
- 如果任务编号不存在，给出明确提示
- 不需要手动修改任务状态

---

## T004 生成当前任务提示词

状态：done
角色：Developer
目标：根据下一个 pending 任务，生成 prompts/current_prompt.md。

### 验收标准

- runner.py 可以根据 pending 任务生成提示词
- prompts/current_prompt.md 内容包含任务编号、任务名称、角色、目标、验收标准
- 暂时不调用 Claude Code

---

## T005 自动调用 Claude Code 执行当前提示词

状态：done
角色：Developer
目标：让 runner.py 可以读取 prompts/current_prompt.md，并调用 Claude Code 执行。

### 验收标准

- runner.py 可以读取 prompts/current_prompt.md
- runner.py 可以调用 Claude Code CLI
- 可以保存 Claude Code 执行输出
- 暂时不做多轮自动循环

---

## T006 执行后自动保存结果并生成运行记录

状态：done
角色：Developer
目标：让 runner.py 在调用 Claude Code 后，自动保存执行结果、退出码、执行时间和日志路径。

### 验收标准

- 可以保存每次执行的 stdout
- 可以保存每次执行的 stderr
- 可以记录执行开始时间和结束时间
- 可以记录 Claude Code 的退出码
- 可以把执行摘要追加到 reports/run-log.md

---

## T007 根据执行结果判断任务是否完成

状态：done
角色：Developer
目标：让 runner.py 根据 Claude Code 执行结果，初步判断当前任务是否可以标记为完成。

### 验收标准

- 可以读取 Claude Code 最新执行结果
- 可以根据退出码判断执行是否成功
- 成功时给出建议：可以 complete 当前任务
- 失败时给出建议：需要修复或重新执行
- 暂时不自动修改任务状态

---

## T008 自动完成成功任务

状态：done
角色：Developer
目标：让 runner.py 在执行结果成功时，可以自动把当前任务标记为 done。

### 验收标准

- 可以识别当前 in_progress 任务
- 可以读取最近一次执行结果
- 如果退出码为 0，可以自动 complete 当前任务
- 如果退出码非 0，不自动 complete
- 暂时不进入下一轮自动循环

---

## T009 单步自动执行闭环

状态：done
角色：Developer
目标：让 runner.py 完成一次"生成提示词 → 调用 Claude Code → 判断结果 → 成功则完成任务"的单步自动闭环。

### 验收标准

- 可以自动找到下一个 pending 任务
- 可以自动生成 current_prompt.md
- 可以自动把该任务标记为 in_progress
- 可以自动调用 Claude Code
- 可以自动判断执行结果
- 成功时可以自动标记 done
- 暂时不做多任务循环

---

## T010 多任务自动执行循环

状态：done
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

状态：done
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

状态：done
角色：Developer
目标：让 claude_code_runner.py 调用 Claude Code 时使用 acceptEdits 模式，使 Claude Code 可以在非交互执行中自动编辑文件。

### 验收标准

- run_claude_code() 调用 Claude Code 时包含 --permission-mode acceptEdits
- 保持原有 --print 调用方式
- 保持原有 stdout/stderr/returncode 返回结构
- 保持 encoding="utf-8", errors="replace"
- 不修改 T010 状态
- 不在 Claude Code 会话内执行 retry-current

---

## T011 阶段总结与关键经验沉淀

状态：done
角色：Reporter
目标：总结第一阶段最小自动化闭环成果，沉淀关键经验、踩坑记录和后续开发约束。

### 验收标准

- 生成阶段总结报告
- 更新 docs/workflow.md
- 更新 memory/lessons.md
- 更新 memory/pitfalls.md
- 明确记录第一阶段已完成能力
- 明确记录后续开发必须遵守的自动化原则

---

## T012 设计第二阶段任务路线

状态：done
角色：Planner
目标：基于第一阶段闭环成果，设计第二阶段自动化能力扩展路线。

### 验收标准

- 明确第二阶段目标
- 明确下一批任务顺序
- 不偏离最终自动化目标
- 优先选择最小可验证改进

---

## T013 工作流协议规范化

状态：done
角色：Developer
目标：设计统一的 workflow YAML 文件格式，描述项目执行所需的 Agent、任务阶段、执行顺序和验收规则。

### 验收标准

- 定义 workflow YAML schema，至少包含：阶段名、Agent 角色、输入输出、执行顺序、验收规则
- 创建示例 workflow 文件 workflows/example.yaml
- tools/task_manager.py 或新模块能读取并解析 workflow 文件
- 不修改 runner.py 核心调度逻辑

---

## T014 Agent 输出协议规范化

状态：done
角色：Developer
目标：规定每个 Agent 的标准输出格式，确保多 Agent 协作时有统一的输入输出接口。

### 验收标准

- 定义每个 Agent 角色的输出格式规范
- Developer Agent：修改文件列表、开发报告
- Tester Agent：测试结果、通过率
- Reviewer Agent：审查结论、建议
- Reporter Agent：总结报告
- Planner Agent：任务清单
- 创建 agents/protocols.md 记录所有输出协议
- 协议格式以 markdown 为主，关键结构可辅以 JSON schema

---

## T015 项目需求输入规范化

状态：done
角色：Developer
目标：设计需求文档的标准格式，让用户需求可以被机器读取和解析。

### 验收标准

- 定义 requirement.md 标准格式，至少包含：项目名、目标、功能列表、技术约束、验收标准
- 创建示例需求文档 docs/requirement-template.md
- tools/task_manager.py 新增解析需求文档的函数
- 解析结果为结构化数据（dict 或 dataclass）

---

## T016 多模型 API 适配器 MVP

状态：done
角色：Developer
目标：设计统一的多模型 API 适配器，为 Planner / Reviewer / Main Agent 提供可配置的国内模型调用能力。

### 验收标准

- 更新 config.yaml，支持不同 Agent 配置不同模型
- 实现 tools/model_adapter.py 的统一接口
- 至少支持 mock provider，用于本地无 API Key 测试
- 预留 zhipu / deepseek / kimi / qwen provider 结构
- 明确 Reviewer 不默认使用 Developer 同款模型
- 创建 docs/model-adapter-protocol.md
- 不接入 runner.py 主流程

---

## T017 Planner Agent 自动拆解任务 MVP

状态：done
角色：Developer
目标：调用国内模型 API，根据需求文档自动生成任务清单草案。

### 验收标准

- 能读取 requirement.md
- 能调用国内模型 API 生成任务清单
- 生成的任务清单符合 tasks.md 格式
- 每个任务包含编号、标题、状态、角色、目标、验收标准
- 生成的任务清单输出到文件供人工审核
- 人工确认后才写入 docs/tasks.md

---

## T018 Main Agent 决策协议 MVP

状态：done
角色：Developer
目标：定义 Main Agent 如何根据任务状态、执行结果、测试结果决定下一步动作。

### 验收标准

- 定义决策规则：成功做什么、失败做什么、需返工做什么
- 定义决策输入：任务状态、执行结果、测试结果、审查结果
- 定义决策输出：下一个动作（执行下一任务 / 重试 / 停止等）
- 以配置文件或代码逻辑形式实现
- 不接入 LLM，先用规则引擎

---

## T018.1 提交并推送当前框架成果

状态：done
角色：Developer
目标：在进入验证项目之前，提交并推送当前 multi-agent-runner 框架成果，完成远程备份。

### 验收标准

- git status 已检查
- 当前改动已提交
- commit message 清晰
- 已成功 push 到远程仓库
- push 后工作区 clean
- 生成提交记录报告

---

## T019 down-100-floors-game 验证项目初始化

状态：done
角色：Developer
目标：在 projects/down-100-floors-game 中生成验证项目需求和基础目录，并补充未来微信小游戏 / 抖音小游戏 / 角色系统方向，但第一版仍只做 Web MVP。

### 验收标准

- projects/down-100-floors-game 基础目录存在
- requirement.md 已补充长期方向和当前 MVP 边界
- README.md 存在
- index.html / style.css / script.js 存在
- docs/tasks.md 存在
- docs/workflow.md 存在
- docs/future-platform-plan.md 存在
- docs/character-system-plan.md 存在
- reports/dev、reports/test、reports/review、reports/final 存在
- memory/lessons.md 和 memory/pitfalls.md 存在
- 不实现完整游戏功能
- 不实现微信小游戏 / 抖音小游戏发布功能
- 不实现角色技能系统

---

## T020 使用 runner 自动执行小游戏第一个开发任务

状态：done
角色：Developer
目标：用已有 runner 自动执行小游戏项目的第一个开发任务，验证框架能服务真实业务项目。

### 验收标准

- 在 docs/tasks.md 中创建小游戏项目的第一个开发任务
- 使用 run-next 自动执行
- 验证 runner 能正确处理项目级任务
- 验证完成证据检查正常工作
- 验证任务状态正确流转
- 不在 Claude Code 会话内执行 run-next

---

## T020.1 记录验证项目第一次自动执行成功经验

状态：done
角色：Reporter
目标：记录 multi-agent-runner 第一次成功驱动 down-100-floors-game 子项目自动完成开发任务的经验和注意事项。

### 验收标准

- 更新主项目 memory/lessons.md
- 更新主项目 memory/pitfalls.md
- 更新验证项目 memory/lessons.md
- 更新验证项目 memory/pitfalls.md
- 创建第一次子项目自动执行总结报告
- 创建 T020.1 开发报告
- 不修改功能代码

---

## T020.2 提交并推送第一次验证项目成果

状态：in_progress
角色：Developer
目标：在进入 Reviewer Agent 自动审查前，提交并推送当前框架和第一次真实子项目自动执行成果。

### 验收标准

- git status 已检查
- 当前改动已提交
- commit message 清晰
- 已成功 push 到远程仓库
- push 后工作区 clean
- 生成提交记录报告

---

## T021 Reviewer Agent 自动审查 MVP

状态：pending
角色：Developer
目标：根据开发输出和任务验收标准，自动生成审查结论。

### 验收标准

- 能读取任务验收标准
- 能读取开发报告和修改文件列表
- 能调用模型或规则引擎生成审查结论
- 审查结论包含：通过/不通过、具体问题、建议修改
- 审查结果写入 reports/review/
- 不需要复杂的代码质量分析

---

## T022 第二阶段阶段总结

状态：pending
角色：Reporter
目标：总结第二阶段成果、问题和下一阶段路线。

### 验收标准

- 生成第二阶段总结报告
- 更新 docs/workflow.md
- 更新 memory/lessons.md
- 更新 memory/pitfalls.md
- 明确第二阶段已完成能力
- 规划第三阶段方向
