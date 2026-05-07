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

状态：done
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

状态：done
角色：Developer
目标：根据 Claude Code 输出、开发报告和任务验收标准，生成审查结论。

### 验收标准

- 创建 tools/reviewer_runner.py
- 可以读取 G002 任务要求
- 可以读取 G002 开发报告
- 可以读取小游戏项目文件摘要
- 可以通过 model_adapter 调用 reviewer 模型
- 当前默认使用 mock provider
- 可以生成 projects/down-100-floors-game/reports/review/G002-review-report.md
- 审查报告包含 PASS / FAIL / RETRY / BLOCKED 状态
- 不修改小游戏业务代码

---

## T022 第二阶段阶段总结

状态：done
角色：Reporter
目标：总结第二阶段成果、问题和下一阶段路线。

### 验收标准

- 生成第二阶段总结报告
- 更新 docs/workflow.md
- 更新 memory/lessons.md
- 更新 memory/pitfalls.md
- 明确第二阶段已完成能力
- 规划第三阶段方向

---

## T022.1 提交并推送第二阶段完整成果

状态：done
角色：Developer
目标：在进入第三阶段前，提交并推送第二阶段完整成果，完成远程备份。

### 验收标准

- git status 已检查
- 当前改动已提交
- commit message 清晰
- 已成功 push 到远程仓库
- push 后工作区 clean
- 生成提交记录报告

---

## T023 设计第三阶段路线

状态：done
角色：Planner
目标：基于第一阶段和第二阶段成果，设计第三阶段自动化能力扩展路线。

### 验收标准

- 创建第三阶段规划文档
- 明确第三阶段目标
- 明确下一批任务顺序
- 不偏离最终自动化目标
- 优先选择最小可验证改进
- 不新增功能代码

---

## T024 通用 project runner 协议设计

状态：done
角色：Architect
目标：设计如何把当前 run-game-next 泛化成通用项目执行器，定义项目路径参数、子项目任务文件路径、完成证据路径和 prompt 生成规则。

### 验收标准

- 定义通用 project runner 协议文档
- 明确项目路径参数规范
- 明确子项目任务文件路径规范
- 明确完成证据路径规范
- 明确 prompt 生成规则
- 不立即重写代码
- 不修改 runner.py

---

## T025 实现通用 run-project-next MVP

状态：done
角色：Developer
目标：实现通用 `python runner.py run-project-next --project projects/<project-name>` 命令，替代 run-game-next 的部分能力。

### 验收标准

- 支持 `--project` 参数指定项目路径
- 自动读取该项目的 docs/tasks.md
- 自动执行第一个 pending 任务
- 完成证据从项目路径下读取
- 可以成功执行 down-100-floors-game 项目
- 保留 run-game-next 作为兼容命令
- 不破坏已有命令

---

## T025.1 记录通用 project runner 首次验证成功经验

状态：done
角色：Reporter
目标：记录 run-project-next 首次成功驱动真实子项目自动完成 G003 任务的经验和注意事项。

### 验收标准

- 更新主项目 memory/lessons.md
- 更新主项目 memory/pitfalls.md
- 更新验证项目 memory/lessons.md
- 更新验证项目 memory/pitfalls.md
- 创建通用 project runner 首次成功总结报告
- 创建 T025.1 开发报告
- 不修改功能代码

---

## T025.2 提交并推送通用 project runner 成果

状态：done
角色：Developer
目标：在进入真实 Reviewer 模型接入前，提交并推送通用 project runner MVP 和 G003 自动执行成果。

### 验收标准

- git status 已检查
- 当前改动已提交
- commit message 清晰
- 已成功 push 到远程仓库
- push 后工作区 clean
- 生成提交记录报告

---

## T026 接入真实 Reviewer 模型配置

状态：done
角色：Developer
目标：选择一个真实 Reviewer 模型（DeepSeek / Qwen / Kimi），配置到 config.yaml 并验证连接可用。

### 验收标准

- config.yaml 中 reviewer provider 可以配置为 deepseek
- tools/model_adapter.py 实现 DeepSeek provider
- DeepSeek API Key 从 DEEPSEEK_API_KEY 环境变量读取
- 不写入真实 API Key
- 保留 mock provider 回退能力
- 可以运行本地 DeepSeek Reviewer 连接测试
- 可以保存 reports/model/deepseek-reviewer-test-output.md
- 不接入自动审查主流程

---

## T027 Reviewer 输出结构化解析 MVP

状态：done
角色：Developer
目标：让 Reviewer 输出可以被机器解析，提取 Status、Decision、Issues 等关键字段。

### 验收标准

- 定义 Reviewer 结构化输出格式
- 可以解析 Status
- 可以解析 Decision
- 可以解析 Issues
- 支持 APPROVE / REQUEST_CHANGES / RETRY / BLOCKED
- 不直接自动返工
- 不修改任务状态

---

## T028 Reviewer 自动审查接入真实模型

状态：done
角色：Developer
目标：让 review-game-task 或通用 review 命令可以调用真实 Reviewer 模型生成审查报告。

### 验收标准

- reviewer_runner.py 可切换使用真实模型
- 生成真实审查报告到 reports/review/
- 审查报告符合 Reviewer Agent 输出协议
- 保留 mock provider 回退能力
- 可通过 config.yaml 配置使用哪个模型
- 不直接自动返工
- 不修改小游戏业务代码

---

## T028.1 记录 DeepSeek Reviewer 首次真实审查成功经验

状态：done
角色：Reporter
目标：记录 DeepSeek Reviewer 首次真实审查 G003 并输出结构化 PASS / APPROVE 结果的经验和注意事项。

### 验收标准

- 更新主项目 memory/lessons.md
- 更新主项目 memory/pitfalls.md
- 更新验证项目 memory/lessons.md
- 更新验证项目 memory/pitfalls.md
- 创建 DeepSeek Reviewer 首次真实审查总结报告
- 创建 T028.1 开发报告
- 不修改功能代码

---

## T028.2 提交并推送真实 DeepSeek Reviewer 审查成果

状态：done
角色：Developer
目标：在进入 Tester Agent 前，提交并推送真实 DeepSeek Reviewer 审查成果。

### 验收标准

- git status 已检查
- 当前改动已提交
- commit message 清晰
- 已成功 push 到远程仓库
- push 后工作区 clean
- 生成提交记录报告

---

## T029 Tester Agent 最小测试协议

状态：done
角色：Architect
目标：定义 Tester Agent 对 Web MVP 项目的最小测试方式和测试报告格式。

### 验收标准

- 创建 docs/tester-protocol.md
- 创建 Tester 静态 Web 测试报告模板
- 明确 Web MVP 最小测试项
- 明确 PASS / FAIL 输出规则
- 明确测试报告完成证据路径
- 不实现测试代码
- 不修改小游戏业务代码

---

## T030 实现 Tester Agent 本地静态检查 MVP

状态：done
角色：Developer
目标：对 down-100-floors-game 做最小本地测试。

### 验收标准

- 创建 tools/tester_runner.py
- 检查 index.html / style.css / script.js 是否存在
- 检查 HTML 中是否包含 game area / start button / score display 等关键元素
- 检查 JS 是否无明显语法错误（如括号不匹配）
- 生成 reports/test/<task-id>-test-report.md
- 输出 PASS / FAIL 总结
- 测试报告符合 Tester Agent 输出协议
- 不修改小游戏业务代码

---

## T031 自动审查 + 测试结果综合决策 MVP

状态：done
角色：Developer
目标：Main Agent 综合 Developer / Tester / Reviewer 三方结果，决定下一步动作。

### 验收标准

- main_agent.py 新增综合决策规则
- 输入：Developer 完成证据、Tester PASS/FAIL、Reviewer APPROVE/REQUEST_CHANGES
- 输出：Main Decision（COMPLETE / RETRY / REQUEST_CHANGES / BLOCKED）
- 三方结果全部通过 → COMPLETE
- 任一方失败 → 对应 RETRY 或 REQUEST_CHANGES
- 生成综合决策报告到 reports/main/
- 不直接做复杂返工循环

---

## T031.1 记录三方证据链与 Main Agent 综合决策成功经验

状态：done
角色：Reporter
目标：记录 G003 第一次完成 Developer / Tester / Reviewer / Main Agent 四类证据闭环的经验和注意事项。

### 验收标准

- 更新主项目 memory/lessons.md
- 更新主项目 memory/pitfalls.md
- 更新验证项目 memory/lessons.md
- 更新验证项目 memory/pitfalls.md
- 创建 Main Agent 综合决策首次成功总结报告
- 创建 T031.1 开发报告
- 不修改功能代码

---

## T031.2 提交并推送 G003 完整闭环成果

状态：done
角色：Developer
目标：在进入 G004 玩家键盘左右移动前，提交并推送 G003 的开发、测试、审查和综合决策完整闭环成果。

### 验收标准

- git status 已检查
- 当前改动已提交
- commit message 清晰
- 已成功 push 到远程仓库
- push 后工作区 clean
- 生成提交记录报告

---

## T031.3 修正 T032 为 G004 玩家键盘左右移动

状态：done
角色：Planner
目标：修正后续任务描述，将 T032 从继续开发 G003 调整为执行新的 G004 玩家键盘左右移动任务。

### 验收标准

- T032 任务名称已从 G003 调整为 G004
- T032 目标已调整为使用通用 project runner 自动执行 G004
- 子项目 docs/tasks.md 已追加 G004 pending 任务
- 不修改小游戏业务代码
- 不执行 G004

---

## T032 使用通用 project runner 自动执行 G004 玩家键盘左右移动

状态：done
角色：Developer
目标：使用通用 project runner 自动执行 G004，实现玩家角色的键盘左右移动能力。

### 验收标准

- 子项目 G004 已存在且状态为 pending
- 可以使用 run-project-next 自动执行 G004
- 玩家可以通过键盘左右方向键移动
- 玩家移动限制在游戏区域内
- 不实现重力
- 不实现平台生成
- 不实现碰撞检测
- 不实现角色技能系统
- G004 需要生成 Developer / Tester / Reviewer / Main Agent 证据链

---

## T032.1 记录 G004 完整闭环成功经验，并完成 T032

状态：done
角色：Reporter
目标：记录 G004 玩家键盘左右移动任务的 Developer / Tester / Reviewer / Main Agent 完整闭环经验，并完成 T032 收尾。

### 验收标准

- T032 已标记为 done
- 更新主项目 memory/lessons.md
- 更新主项目 memory/pitfalls.md
- 更新验证项目 memory/lessons.md
- 更新验证项目 memory/pitfalls.md
- 创建 G004 完整闭环总结报告
- 创建 T032.1 开发报告
- 不修改功能代码

---

## T033 第三阶段总结与 Git 备份

状态：done
角色：Reporter
目标：总结第三阶段成果，更新经验沉淀，提交并推送到远程仓库。

### 验收标准

- 生成第三阶段总结报告
- 更新 memory/lessons.md
- 更新 memory/pitfalls.md
- 更新 docs/phase-3-plan.md 验收标准
- git status 已检查
- 当前改动已提交
- commit message 清晰
- 已成功 push 到远程仓库
- push 后工作区 clean

---

## T034 设计第四阶段路线

状态：done
角色：Planner
目标：基于前三阶段成果，设计第四阶段任务路线。

### 验收标准

- 创建 docs/phase-4-plan.md
- 明确第四阶段目标
- 明确下一批任务顺序
- 继续服务最终自动化目标
- 优先选择最小可验证改进
- 不新增功能代码

---

## T034.1 提交并推送第四阶段路线规划

状态：done
角色：Developer
目标：在进入 Tester 行为检查增强前，提交并推送第四阶段路线规划成果。

### 验收标准

- git status 已检查
- 当前改动已提交
- commit message 清晰
- 已成功 push 到远程仓库
- push 后工作区 clean
- 生成提交记录报告

---

## T035 Tester 行为检查协议设计

状态：done
角色：Architect
目标：定义 Tester 如何检查键盘事件、边界移动、玩家位置更新等行为逻辑。

### 验收标准

- 明确 G004 当前静态测试的不足
- 明确行为检查范围
- 明确不引入浏览器自动化
- 明确 T036 实现方向

---

## T036 实现 Tester 键盘移动逻辑静态检查 MVP

状态：done
角色：Developer
目标：增强 Tester Agent，可以检查 G004 是否包含左右键监听、边界限制、位置更新函数。

### 验收标准

- 可以检查键盘事件监听逻辑
- 可以检查左右方向键处理逻辑
- 可以检查边界限制逻辑
- 可以检查玩家位置更新逻辑
- 不引入浏览器自动化
- 不修改小游戏业务代码

---

## T037 G004 增强测试与 Main Decision 复核

状态：done
角色：Developer
目标：用增强 Tester 重新测试 G004，并重新生成 Main Decision。

### 验收标准

- 生成增强版 G004 测试报告
- Main Agent 重新读取 Developer / Tester / Reviewer 结果
- 重新生成 G004 Main Decision
- 不自动返工

---

## T037.1 提交并推送 Tester 行为检查增强成果

状态：done
角色：Developer
目标：在进入 project.yaml 配置驱动前，提交并推送 Tester 行为检查增强成果。

### 验收标准

- git status 已检查
- 当前改动已提交
- commit message 清晰
- 已成功 push 到远程仓库
- push 后工作区 clean
- 生成提交记录报告

---

## T038 project.yaml 协议落地

状态：done
角色：Developer
目标：为 down-100-floors-game 创建真实 project.yaml。

### 验收标准

- 创建 projects/down-100-floors-game/project.yaml
- 字段遵循 T024 project runner 协议
- 不修改 runner 逻辑

---

## T039 project runner 读取 project.yaml MVP

状态：done
角色：Developer
目标：让 run-project-next 可以读取 project.yaml。

### 验收标准

- 如果存在 project.yaml，优先读取配置
- 如果不存在 project.yaml，回退路径约定
- 不破坏现有 run-project-next 命令

---

## T040 自动返工协议设计

状态：done
角色：Architect
目标：定义当 Tester FAIL 或 Reviewer REQUEST_CHANGES 时，如何生成返工任务。

### 验收标准

- 明确返工任务命名规则
- 明确返工 prompt 输入
- 明确返工完成证据
- 不自动执行返工

---

## T041 自动生成返工 prompt MVP

状态：done
角色：Developer
目标：当有失败报告时，生成返工 prompt。

### 验收标准

- 可以读取失败的 Tester / Reviewer 报告
- 可以生成 prompts/rework_prompt.md
- 不自动调用 Claude Code
- 人工确认后再执行

---

## T042 新增 G005 基础平台显示任务

状态：done
角色：Planner
目标：在子项目任务清单中添加 G005。

### 验收标准

- 子项目 tasks.md 追加 G005 pending
- G005 只做基础平台显示
- 不实现重力
- 不实现碰撞
- 不实现平台滚动

---

## T042.1 提交并推送 T038-T042 第四阶段中段成果

状态：done
角色：Developer
目标：在继续执行 G005 前，提交并推送 project.yaml、自动返工协议、返工 prompt 和 G005 任务规划成果。

### 验收标准

- git status 已检查
- current_prompt.md 临时改动已排除或恢复
- 当前改动已提交
- commit message 清晰
- 已成功 push 到远程仓库
- push 后工作区 clean
- 生成提交记录报告

---

## T043.0 修复 run-project-next 的 Claude Code 超时异常处理

状态：done
角色：Developer
目标：修复 run-project-next 调用 Claude Code 超时时 runner.py 直接崩溃的问题。

### 验收标准

- Claude Code 超时后 runner.py 不直接崩溃
- 超时结果可以转换为结构化执行结果
- 可以保存 latest-output.md
- 可以追加 run-log.md
- 可以输出清晰错误提示
- 任务状态保持 in_progress
- 不自动重试
- 不执行 G005

---

## T043.1 修复 run-project-next 返回码与完成证据冲突时的状态判断

状态：done
角色：Developer
目标：当 Claude Code 返回错误但完成证据已存在且任务已 done 时，runner 应识别为"完成证据存在但模型返回错误"，而不是简单失败。

### 验收标准

- 可以识别 returncode 非 0 但开发报告存在
- 可以识别任务状态已经 done
- 可以输出"完成证据存在但模型返回错误"
- 不把这种情况误判为普通失败
- 不自动重新执行任务
- 不修改小游戏业务代码

---

## T043.2 记录 G005 Developer 完成但模型返回 429 的特殊情况，并完成 T043

状态：done
角色：Reporter
目标：记录 G005 实际完成但 Claude Code 最后返回 429 的特殊情况，并完成 T043 收尾。

### 验收标准

- T043 已标记为 done
- 记录 G005 Developer 实际完成情况
- 记录 Claude Code 返回 429 的特殊情况
- 更新主项目 memory/lessons.md
- 更新主项目 memory/pitfalls.md
- 更新验证项目 memory/lessons.md
- 更新验证项目 memory/pitfalls.md
- 创建总结报告
- 创建 T043.2 开发报告
- 不重新执行 G005
- 不修改小游戏业务代码

---

## T043 使用 run-project-next 自动执行 G005

状态：done
角色：Developer
目标：自动实现基础平台显示。

### 验收标准

- Developer 生成 G005-dev-report
- G005 自动标记 done
- 不做重力
- 不做碰撞
- 不做平台滚动

---

## T044.4 记录 G005 完整闭环成功经验，并完成 T044

状态：done
角色：Reporter
目标：记录 G005 基础平台显示任务的 Developer / Tester / Reviewer / Main Agent 完整闭环经验，并完成 T044 收尾。

### 验收标准

- T044 已标记为 done
- 记录 G005 Developer / Tester / Reviewer / Main Agent 四类证据
- 记录 G005 开发阶段 429 特殊情况
- 更新主项目 memory/lessons.md
- 更新主项目 memory/pitfalls.md
- 更新验证项目 memory/lessons.md
- 更新验证项目 memory/pitfalls.md
- 创建 G005 完整闭环总结报告
- 创建 T044.4 开发报告
- 不执行测试、审查、综合决策命令
- 不修改小游戏业务代码

---

## T044 G005 Tester / Reviewer / Main Decision 完整闭环

状态：done
角色：Developer
目标：让 G005 完成测试、审查、综合决策。

### 验收标准

- 生成 G005-test-report
- 生成 G005-review-report
- 生成 G005-main-decision
- 如果失败，只记录，不自动返工

---

## T045 第四阶段阶段总结与 Git 备份

状态：done
角色：Reporter
目标：总结第四阶段成果并提交推送。

### 验收标准

- 创建第四阶段总结报告
- 更新 memory
- git commit
- git push
- 工作区 clean

---

## T046 设计第五阶段路线

状态：done
角色：Planner
目标：基于前四阶段成果，设计第五阶段任务路线。

### 验收标准

- 创建第五阶段规划文档
- 明确第五阶段目标
- 明确下一批任务顺序
- 优先设计重力和碰撞相关 Tester 协议
- 继续服务最终自动化目标
- 优先选择最小可验证改进
- 不新增功能代码

---

## T046.1 新增 CHANGELOG.md 并记录第一至第四阶段里程碑与第五阶段规划

状态：done
角色：Reporter
目标：新增根目录 CHANGELOG.md，集中记录项目阶段版本、核心成果、关键提交和第五阶段规划。

### 验收标准

- 创建 CHANGELOG.md
- 记录第一阶段 v0.1.0
- 记录第二阶段 v0.2.0
- 记录第三阶段 v0.3.0
- 记录第四阶段 v0.4.0
- 记录第五阶段 v0.5.0-plan
- 记录关键 commit
- 说明 README / CHANGELOG / docs/tasks / reports / memory 的分工
- 创建 T046.1 开发报告
- 不修改功能代码

---

## T046.2 提交并推送第五阶段规划与 CHANGELOG

状态：done
角色：Developer
目标：在进入重力下落测试协议设计前，提交并推送第五阶段规划与 CHANGELOG 版本记录成果。

### 验收标准

- git status 已检查
- 当前改动已提交
- commit message 清晰
- 已成功 push 到远程仓库
- push 后工作区 clean
- 生成提交记录报告

---

## T047 重力下落测试协议设计

状态：done
角色：Architect
目标：定义 Tester 如何检查简单重力下落逻辑。

### 验收标准

- 创建 docs/tester-gravity-check-protocol.md
- 创建 Tester 重力检查报告模板
- 明确 G006 简单重力下落的测试范围
- 明确重力状态检查项
- 明确垂直速度检查项
- 明确位置更新检查项
- 明确不测试平台碰撞
- 明确不测试平台滚动
- 明确不测试失败条件
- 明确 T050 实现方向
- 不修改小游戏业务代码

---

## T048 新增 G006 简单重力下落任务

状态：done
角色：Planner
目标：在子项目任务清单中添加 G006。

### 验收标准

- 子项目 tasks.md 追加 G006 pending
- G006 只做简单垂直下落
- 不实现碰撞
- 不实现平台滚动
- 不实现失败条件
- 不实现随机平台

---

## T048.1 提交并推送 T047-T048 重力协议与 G006 任务规划成果

状态：done
角色：Developer
目标：在重新处理 G006 执行前，提交并推送重力测试协议和 G006 任务规划成果。

### 验收标准

- git status 已检查
- G006 状态确认为 pending
- G006 失败执行日志未提交
- 当前改动已提交
- commit message 清晰
- 已成功 push 到远程仓库
- push 后工作区 clean
- 生成提交记录报告

---

## T049.0 设计单任务完整闭环自动化命令

状态：done
角色：Architect
目标：设计 run-project-task-full 命令，将 Developer / Tester / Reviewer / Main Agent 串成单任务完整闭环。

### 验收标准

- 创建 docs/full-task-loop-protocol.md
- 明确 run-project-task-full 命令格式
- 明确单任务完整闭环步骤
- 明确 Developer 执行规则
- 明确 Tester 执行规则
- 明确专项 Tester 选择规则
- 明确 Reviewer 执行规则
- 明确 Main Agent 决策规则
- 明确失败与返工 prompt 生成规则
- 明确最大返工次数限制
- 明确人工介入边界
- 不实现代码
- 不执行 G006

---

## T049.1 实现 run-project-task-full MVP

状态：done
角色：Developer
目标：实现单任务完整闭环命令 MVP，将 Developer / Tester / Reviewer / Main Agent 串起来。

### 验收标准

- 新增 tools/full_task_runner.py
- 新增 runner.py 命令 run-project-task-full
- 支持 --project 参数
- 支持 --task 参数
- 可以调用 Developer 阶段
- 可以调用 Basic Tester 阶段
- 可以调用 Reviewer 阶段
- 可以调用 Main Decision 阶段
- 可以生成 full-loop-report
- 任一阶段失败时停止后续阶段
- 不自动返工
- 不自动重试
- 不执行 G006

---

## T049.2 调整 T049 为使用 run-project-task-full 验证 G006

状态：done
角色：Planner
目标：将 T049 从旧的 run-project-next 单步执行调整为 run-project-task-full 单任务完整闭环验证。

### 验收标准

- T049 名称已调整为 run-project-task-full 验证
- T049 目标已调整为单任务完整闭环
- T049 验收标准包含 Developer / Tester / Reviewer / Main Agent
- T049 保持 pending
- 不执行 G006
- 不修改功能代码

---

## T049.3 记录 run-project-task-full 首次验证与 G006 完整闭环

状态：done
角色：Reporter
目标：记录 run-project-task-full 首次真实验证结果、Reviewer BLOCKED 情况、.env 安全忽略、补跑 Reviewer / Main Decision 成功，以及 G006 完整闭环。

### 验收标准

- T049 已标记为 done
- T049.3 已标记为 done
- 记录 run-project-task-full 首次验证结果
- 记录 Developer / Basic Tester / Specialized Tester / Reviewer 各阶段结果
- 记录 Reviewer 因缺少 DEEPSEEK_API_KEY 被 BLOCKED
- 记录 .env 已被 .gitignore 忽略
- 记录手动加载 .env 后 Reviewer 通过
- 记录 Main Agent 决策 COMPLETE
- 更新主项目 memory/lessons.md
- 更新主项目 memory/pitfalls.md
- 更新验证项目 memory/lessons.md
- 更新验证项目 memory/pitfalls.md
- 创建总结报告
- 创建开发报告
- 不重新执行 G006
- 不修改小游戏业务代码

---

## T049 使用 run-project-task-full 验证 G006 单任务完整闭环

状态：done
角色：Developer
目标：使用 run-project-task-full 命令验证 G006 的 Developer / Tester / Reviewer / Main Agent 单任务完整闭环。

### 验收标准

- 使用 run-project-task-full 执行 G006
- Developer 阶段可以自动执行 G006
- Basic Tester 阶段可以自动执行
- Reviewer 阶段可以自动执行
- Main Decision 阶段可以自动执行
- 可以生成 G006-full-loop-report.md
- 如果 Developer 超时，应停止在 Developer 阶段
- 如果 Tester FAIL，应停止并建议生成 rework prompt
- 如果 Reviewer REQUEST_CHANGES，应停止并建议生成 rework prompt
- 不自动执行返工
- 不无限循环
- 不跳过人工介入边界

---

## T050.1 添加 .env 自动加载能力

状态：done
角色：Developer
目标：让 runner.py 启动时自动读取项目根目录 .env，加载 DeepSeek 等本地环境变量，避免手动 PowerShell 加载。

### 验收标准

- 新增 tools/env_loader.py
- runner.py 启动时自动加载 .env
- 支持读取 DEEPSEEK_API_KEY
- 不覆盖已有系统环境变量
- 不打印真实 API Key
- 新增 .env.example
- 确认 .env 被 .gitignore 忽略
- 不调用 DeepSeek API
- 不执行 G006
- 不执行 full loop

---

## T050.2 记录 G006 完整闭环与 .env 自动加载能力，并完成 T050

状态：done
角色：Reporter
目标：记录 G006 完整闭环结果和 .env 自动加载能力，并完成 T050 收尾。

### 验收标准

- T050 已标记为 done
- T050.2 已标记为 done
- 记录 G006 Developer 结果
- 记录 G006 Basic Tester 结果
- 记录 G006 Reviewer 结果
- 记录 G006 Main Agent 结果
- 记录 run-project-task-full 首次验证结果
- 记录 .env 自动加载能力
- 记录 .env 已被 .gitignore 忽略
- 更新主项目 memory/lessons.md
- 更新主项目 memory/pitfalls.md
- 更新验证项目 memory/lessons.md
- 更新验证项目 memory/pitfalls.md
- 创建总结报告
- 创建开发报告
- 不重新执行 G006
- 不调用 DeepSeek API

---

## T050 G006 Tester / Reviewer / Main Decision 完整闭环

状态：done
角色：Developer
目标：让 G006 完成测试、审查、综合决策。

### 验收标准

- 生成 G006-test-report（基础测试）
- 生成 G006-behavior-test-report（重力行为测试）
- 生成 G006-review-report（DeepSeek 审查）
- 生成 G006-main-decision（综合决策）
- 如果失败，只记录，不自动返工
- 不跳过证据链

---

## T050.3 Git 提交并推送 T047-T050 所有工作

状态：done
角色：Developer
目标：将 T047-T050 所有新增和修改文件提交并推送到远程仓库。

### 验收标准

- 所有 T047-T050 新增文件已提交
- 所有 T047-T050 修改文件已提交
- .env 不被提交（已在 .gitignore 中）
- git push 成功
- 工作区干净
- python runner.py 显示 T051 为下一个 pending

---

## T050.3a 配置 Claude Code 安全命令自动执行白名单

状态：done
角色：Safety Architect
目标：建立 Claude Code 安全命令自动执行白名单，减少低风险命令的人工确认，提高自动化程度。

### 验收标准

- 创建 docs/command-permission-policy.md
- 明确 A 类低风险自动执行命令
- 明确 B 类 Git 备份任务自动执行命令
- 明确 C 类需要人工确认命令
- 明确 D 类禁止自动执行命令
- 明确 Claude Code /permissions 配置建议
- 明确不得打印 API Key
- 明确不得提交 .env
- 明确不得自动执行危险删除命令
- 更新 docs/full-task-loop-protocol.md
- 更新 memory/lessons.md
- 更新 memory/pitfalls.md
- 创建总结报告
- 创建开发报告
- 不修改功能代码

---

## T050.3b 提交并推送命令权限白名单策略

状态：done
角色：Developer
目标：提交并推送 Claude Code 安全命令自动执行白名单策略文档。

### 验收标准

- git status 已检查
- `.env` 确认被 `.gitignore` 忽略
- 当前改动已提交
- commit message 清晰
- 已成功 push 到远程仓库
- push 后工作区 clean
- python runner.py 正常显示 T051
- 生成提交记录报告

---

## T051 碰撞检测测试协议设计

状态：done
角色：Architect
目标：设计玩家与平台基础碰撞的测试协议。

### 验收标准

- 创建 docs/tester-collision-check-protocol.md
- 创建 Tester 碰撞检查报告模板
- 明确 G007 玩家与平台基础碰撞测试范围
- 明确碰撞检测状态检查项
- 明确平台状态检查项
- 明确玩家落到平台上的检查项
- 明确玩家不穿透平台的检查项
- 明确不测试平台滚动
- 明确不测试随机平台
- 明确不测试游戏失败条件
- 明确不测试角色技能系统
- 明确 T054 实现方向
- 不修改小游戏业务代码

---

## T051.1 修正命令权限策略中的 Bash / PowerShell 命令差异

状态：done
角色：Safety Architect
目标：修正自动执行命令白名单中的 shell 差异，明确 Bash 与 PowerShell 的对应命令，避免 Claude Code 在 Bash 环境中执行 PowerShell 命令失败。

### 验收标准

- 更新 docs/command-permission-policy.md
- 明确 Bash 环境下的文件存在检查命令
- 明确 PowerShell 环境下的文件存在检查命令
- 明确 Bash 环境下的文件读取命令
- 明确 PowerShell 环境下的文件读取命令
- 明确 Bash 环境下的文本搜索命令
- 明确 PowerShell 环境下的文本搜索命令
- 移除 Bash 白名单中的 PowerShell 命令示例
- 更新 docs/full-task-loop-protocol.md
- 更新 memory/lessons.md
- 更新 memory/pitfalls.md
- 创建总结报告
- 创建开发报告
- 不修改功能代码

---

## T051.2 提交并推送 T051 碰撞测试协议与 shell 命令策略修正

状态：done
角色：Developer
目标：在进入 G007 任务规划前，提交并推送 T051 碰撞测试协议与 Bash / PowerShell 命令策略修正成果。

### 验收标准

- git status 已检查
- `.env` 确认被 `.gitignore` 忽略
- 当前改动已提交
- commit message 清晰
- 已成功 push 到远程仓库
- push 后工作区 clean
- python runner.py 正常显示 T052
- 生成提交记录报告

---

## T052 新增 G007 玩家与平台基础碰撞任务

状态：done
角色：Planner
目标：在子项目任务清单中添加 G007。

### 验收标准

- 子项目 tasks.md 追加 G007 pending
- G007 只做玩家与平台基础碰撞
- G007 基于 G005 固定平台和 G006 简单重力
- 明确后续由 Claude Code 执行 Developer
- 明确后续由 Tester 执行基础测试与碰撞专项测试
- 明确后续由 DeepSeek Reviewer 审查
- 明确后续由 Main Agent 综合决策
- 不实现平台滚动
- 不实现随机平台
- 不实现游戏失败条件
- 不实现角色技能系统
- 不修改小游戏业务代码

---

## T052.1 实现 G007 Collision Tester MVP

状态：done
角色：Developer
目标：实现 G007 碰撞专项 Tester MVP，让 run-project-task-full 在 G007 阶段可以执行 Collision Tester，而不是跳过专项测试。

### 验收标准

- 新增或扩展 Collision Tester 实现
- 新增 runner.py 命令 test-game-collision
- 支持命令 python runner.py test-game-collision G007
- 可以读取 G007 任务要求
- 可以读取 script.js
- 可以检查碰撞函数或碰撞处理逻辑
- 可以检查平台数据
- 可以检查玩家底部与平台顶部判断
- 可以检查水平范围重叠判断
- 可以检查落到平台后 y 坐标修正
- 可以检查垂直速度归零或停止增加
- 可以检查不包含平台滚动
- 可以检查不包含随机平台
- 可以检查不包含游戏失败条件
- 可以生成 G007-collision-test-report.md
- run-project-task-full 可以在 G007 时调用 Collision Tester
- 不执行 G007 Developer
- 不修改小游戏业务代码

---

## T052.2 提交并推送 G007 任务规划与 Collision Tester MVP

状态：done
角色：Developer
目标：在执行 G007 自动开发前，提交并推送 G007 任务规划与 Collision Tester MVP。

### 验收标准

- git status 已检查
- `.env` 确认被 `.gitignore` 忽略
- 当前改动已提交
- commit message 清晰
- 已成功 push 到远程仓库
- push 后工作区 clean
- python runner.py 正常显示 T053
- 生成提交记录报告

---

## T053 使用 run-project-next 自动执行 G007

状态：done
角色：Developer
目标：自动实现玩家与平台基础碰撞。

### 验收标准

- Developer 生成 G007-dev-report
- 玩家下落到平台时停止或站在平台上
- 不做平台滚动
- 不做随机平台
- 不做失败条件
- 不做角色技能系统

---

## T053.1 修正 Collision Tester 关键词匹配，兼容 G007 实际实现

状态：done
角色：Developer
目标：修正 G007 Collision Tester 关键词匹配，使其兼容 G007 实际实现中的 playerState.vy、prevBottom、bounds.top、playerState.height 等代码模式。

### 验收标准

- Collision Tester 支持 `playerState.vy`
- Collision Tester 支持 `prevBottom`
- Collision Tester 支持 `bounds.top`
- Collision Tester 支持 `playerState.height`
- Collision Tester 支持 `playerState.y = bounds.top - playerState.height`
- Collision Tester 支持 `playerState.vy < 0` 这类反向判断写法
- 重新运行 `python runner.py test-game-collision G007`
- G007 Collision Tester 误判项减少或通过
- 生成新的 G007-collision-test-report.md
- 创建 T053.1 开发报告
- 不修改 G007 业务代码
- 不调用 DeepSeek API
- 不执行 run-project-task-full

---

## T053.2 重新运行 G007 Collision Tester

状态：done
角色：Tester
目标：在修正 Collision Tester 匹配规则后，重新运行 G007 碰撞专项测试，确认误判已消除。

### 验收标准

- 重新执行 `python runner.py test-game-collision G007`
- G007 Collision Tester 结果为 PASS
- G007-collision-test-report.md 已更新
- 记录 Passed / Failed 数量
- 不修改 G007 业务代码
- 不调用 DeepSeek API
- 不执行 run-project-task-full

---

## T053.3 补跑 G007 Reviewer / Main Decision

状态：done
角色：Developer
目标：在 G007 Developer / Basic Tester / Collision Tester 均通过后，补跑 DeepSeek Reviewer 与 Main Agent 综合决策。

### 验收标准

- 执行 `python runner.py review-game-task G007`
- Reviewer 结果为 PASS / APPROVE
- 生成 G007-review-report.md
- 执行 `python runner.py decide-game-task G007`
- Main Agent 决策为 COMPLETE
- 生成 G007-main-decision.md
- 不重新执行 Developer
- 不执行 run-project-task-full

---

## T053.4 记录 G007 完整闭环

状态：done
角色：Reporter
目标：记录 G007 玩家与平台基础碰撞完整闭环结果，总结 Developer / Tester / Collision Tester / Reviewer / Main Agent 协作情况。

### 验收标准

- 记录 G007 Developer 结果
- 记录 G007 Basic Tester 结果
- 记录 G007 Collision Tester 结果
- 记录 G007 Reviewer 结果
- 记录 G007 Main Agent 结果
- 更新主项目 memory/lessons.md
- 更新主项目 memory/pitfalls.md
- 更新验证项目 memory/lessons.md
- 更新验证项目 memory/pitfalls.md
- 创建完整闭环总结报告
- 创建开发报告
- 不重新执行 G007
- 不修改小游戏业务代码

---

## T053.5 提交并推送 G007 自动化完整闭环成果

状态：done
角色：Developer
目标：在处理 T054 前，提交并推送 G007 自动化完整闭环成果。

### 验收标准

- git status 已检查
- `.env` 确认被 `.gitignore` 忽略
- 当前改动已提交
- commit message 清晰
- 已成功 push 到远程仓库
- push 后工作区 clean
- python runner.py 正常显示 T054
- 生成提交记录报告

---

## T054 G007 Tester / Reviewer / Main Decision 完整闭环

状态：done
角色：Developer
目标：让 G007 完成测试、审查、综合决策。

### 验收标准

- 生成 G007-test-report（基础测试）
- 生成 G007-behavior-test-report（碰撞行为测试）
- 生成 G007-review-report（DeepSeek 审查）
- 生成 G007-main-decision（综合决策）
- 如果失败，只记录，不自动返工
- 不跳过证据链

### 完成说明

T054 原始目标已经由以下任务前置完成：

- T053.2：重新运行 G007 Collision Tester，结果 PASS（17/18）
- T053.3：补跑 G007 Reviewer / Main Decision，Reviewer APPROVE，Main Decision COMPLETE
- T053.4：记录 G007 完整闭环

因此 T054 不重复执行测试、审查、决策，只做冗余任务关闭记录。

---

## T054.1 提交并推送 T054 G007 闭环关闭记录

状态：done
角色：Developer
目标：提交并推送 T054 G007 完整闭环冗余任务关闭记录。

### 验收标准

- git status 已检查
- `.env` 确认被 `.gitignore` 忽略
- 当前改动已提交
- commit message 清晰
- 已成功 push 到远程仓库
- push 后工作区 clean
- python runner.py 正常显示 T055
- 生成提交记录报告

---

## T055 自动返工执行人工确认协议设计

状态：done
角色：Architect
目标：设计用户确认后执行返工的协议。

### 验收标准

- 创建 docs/rework-execution-confirmation-protocol.md
- 创建 rework execution confirmation 模板
- 明确返工触发条件
- 明确返工候选状态
- 明确人工确认格式
- 明确确认后才允许执行返工
- 明确未确认时只生成 rework prompt
- 明确最大返工次数为 3
- 明确超过 3 次进入人工介入
- 明确禁止无限循环
- 明确禁止自动重复执行返工
- 明确如何记录返工轮次
- 明确如何与 run-project-task-full 衔接
- 更新 docs/rework-protocol.md
- 更新 docs/full-task-loop-protocol.md
- 更新 docs/command-permission-policy.md
- 更新 memory/lessons.md
- 更新 memory/pitfalls.md
- 创建总结报告
- 创建开发报告
- 不实现自动返工执行代码

---

## T055.1 提交并推送自动返工执行人工确认协议

状态：done
角色：Developer
目标：提交并推送 T055 自动返工执行人工确认协议成果。

### 验收标准

- git status 已检查
- `.env` 确认被 `.gitignore` 忽略
- 当前改动已提交
- commit message 清晰
- 已成功 push 到远程仓库
- push 后工作区 clean
- python runner.py 正常显示 T056
- 生成提交记录报告

---

## T055.3 补充 Git 备份命令逐条执行规则，禁止 cd + git 复合命令

状态：done
角色：Safety Architect
目标：补充 Git 备份命令执行规则，明确低风险命令可自动执行、Git 备份命令可逐条自动执行，但禁止 cd + git 复合命令。

### 验收标准

- 更新 docs/command-permission-policy.md
- 更新 docs/full-task-loop-protocol.md
- 明确单条低风险命令可以自动执行
- 明确 Git 备份命令在 Git 备份任务中可以自动执行
- 明确 Git 备份命令必须逐条执行
- 明确禁止 `cd && git ...` 复合命令
- 明确不在项目目录时应停止并报告
- 更新 memory/lessons.md
- 更新 memory/pitfalls.md
- 创建总结报告
- 创建开发报告
- 不修改功能代码

---

## T056 自动返工执行 MVP

状态：done
角色：Developer
目标：在用户确认后执行已有 rework prompt。

### 验收标准

- 新增 execute-rework 命令入口
- 支持 project / task / round 参数
- 支持 confirm 参数
- 未提供 confirm 时必须 BLOCKED
- confirm 格式错误时必须 BLOCKED
- confirm 与 task / round 不匹配时必须 BLOCKED
- round 小于 1 时必须 BLOCKED
- round 大于 3 时必须进入人工介入或 BLOCKED
- 环境类错误不得触发返工执行
- 默认不调用 Claude Code 执行真实返工
- 默认不修改业务代码
- 支持 dry-run 或 ready 状态输出
- 可以生成返工执行检查报告
- 不把 execute-rework 加入全局 allowlist
- 更新相关协议文档
- 创建总结报告
- 创建开发报告

---

## T056.2 实现 confirmed rework execution

状态：done
角色：Developer
目标：在 dry-run safety gate 基础上实现 confirmed rework execution stub。

### 验收标准

- 新增 ReworkConfirmedExecutionResult 数据结构
- 新增 execute_confirmed_rework 函数
- 新增 --real-execution 命令参数
- 无 --real-execution 时保持原有 dry-run 行为
- 有 --real-execution 且全部检查通过时进入 confirmed stub
- execution_allowed=True 且 real_execution_performed=False
- 拒绝场景全覆盖（缺少确认、模糊确认、round 错误、prompt 不存在）
- 不调用 Claude Code
- 不修改业务代码

---

## T056.3 验证一次返工候选流程

状态：done
角色：Developer
目标：验证一次 rework candidate flow 的 dry-run 和 confirmed stub。

### 验收标准

- 选择安全候选任务（G007-R1）
- 执行 dry-run candidate flow 验证
- 执行 confirmed stub candidate flow 验证
- 确认不调用 Claude Code
- 确认不修改业务代码
- 生成验证报告

---

## T056.4 设计 full loop resume

状态：done
角色：Architect
目标：设计 confirmed rework execution stub 通过后，如何安全恢复主流程继续调度下一个 pending task。

### 验收标准

- 创建 docs/full-loop-resume-design.md
- 明确 resume 状态模型
- 明确 CLI 方案（推荐复用 execute-rework + --resume）
- 明确安全规则
- 明确验证场景（至少 10 个）
- 明确 T056.5 实现范围
- 不实现代码
- 不修改 runner.py
- 不修改 tools/rework_manager.py

---

## T056.5 实现 full loop resume

状态：done
角色：Developer
目标：实现 full loop resume stub，让 confirmed rework execution 通过后可以安全恢复主流程。

### 验收标准

- 新增 ReworkResumeResult 数据结构
- 新增 prepare_full_loop_resume 函数
- 新增 --resume 命令参数
- --resume 必须配合 --real-execution 和 --confirm 使用
- 全部检查通过时 resume_allowed=true, resume_target=NEXT_PENDING
- 拒绝场景全覆盖（参数缺失、confirm 错误、round 错误、prompt 不存在）
- 不调用 Claude Code
- 不修改业务代码
- 不带 --resume 时保持原有行为

---

## T057 第五阶段阶段总结与 Git 备份

状态：done
角色：Reporter
目标：总结第五阶段成果并提交推送。

### 验收标准

- 创建第五阶段总结报告
- 更新主项目 memory/lessons.md
- 更新主项目 memory/pitfalls.md
- 更新验证项目 memory/lessons.md
- 更新验证项目 memory/pitfalls.md
- git status 已检查
- 当前改动已提交
- 已成功 push 到远程仓库
- push 后工作区 clean

---

## T058 设计连续任务自动推进协议

状态：done
角色：Architect
目标：设计从单任务闭环升级为连续任务自动推进的协议。

### 验收标准

- 创建 docs/continuous-task-auto-advance-design.md
- 明确第六阶段 MVP 边界
- 明确核心状态模型（ContinuousRunState）
- 明确 continue / stop 条件
- 明确 CLI 设计（推荐 run-project-loop）
- 明确执行流程（dry-run + execute）
- 明确安全规则
- 至少 14 个验证场景
- 不实现代码

---

## T059 实现 continuous task planner

状态：done
角色：Developer
目标：实现 `tools/continuous_task_planner.py`，包含 dry-run 计划生成逻辑。

### 验收标准

- 新增 tools/continuous_task_planner.py
- 新增 PlannedTask 和 ContinuousTaskPlan 数据结构
- 实现 dry-run 计划生成（读取任务列表、列出 pending 任务）
- runner.py 新增 plan-project-loop 命令
- 不调用 Claude Code
- 不修改业务代码

---

## T060 实现 run-project-loop 命令

状态：done
角色：Developer
目标：实现 `run-project-loop` dry-run 命令，复用 continuous_task_planner 模拟连续任务推进。

### 验收标准

- 新增 run-project-loop 命令入口
- 支持 --project / --max-tasks / --start-task / --dry-run / --execute 参数
- --dry-run 默认 true，只输出计划
- --execute 时调用 run-project-task-full 执行任务
- 任务间安全检查
- 生成 run summary
- 不自动 git push
- 不自动 execute-rework

---

## T061 验证 max_tasks=1 dry-run

状态：done
角色：Developer
目标：验证单任务 dry-run 计划输出，确认 max_tasks=1 只规划 1 个任务并在达到上限后停止。

### 验收标准

- max_tasks=1 dry-run 只输出 1 个任务的计划
- 不调用 Claude Code
- 不修改业务代码
- 输出 run_id / loop_status / next_action

---

## T062 验证 max_tasks=3 dry-run

状态：done
角色：Developer
目标：验证多任务 dry-run 计划输出和停止条件，确认 max_tasks=3 最多模拟 3 个任务。

### 验收标准

- max_tasks=3 dry-run 输出 3 个任务的计划
- 验证无 pending 时停止
- 验证 max_tasks 超上限自动修正
- 不调用 Claude Code
- 不修改业务代码

---

## T063 第六阶段 MVP 汇总检查与阶段小结

状态：done
角色：Developer
目标：汇总检查第六阶段 MVP 成果，生成阶段小结报告，更新 memory。

### 验收标准

- 汇总检查所有第六阶段任务（T058-T062）
- 生成 stage-6-mvp-summary.md
- 复核 plan-project-loop 和 run-project-loop 命令
- 更新 memory/lessons.md 和 memory/pitfalls.md
- 不实现新功能

---

## T064 设计 run-project-loop execute mode 安全协议

状态：done
角色：Architect
目标：设计 `run-project-loop --execute` 的安全执行协议，定义真实执行任务时的安全边界、状态管理和人工介入条件。

### 验收标准

- 定义 execute mode 的安全协议 ✓
- 定义任务间状态管理和失败处理 ✓
- 定义人工介入边界 ✓
- 不直接实现代码 ✓

---

## T065 实现 execute mode safety gate

状态：done
角色：Developer
目标：在 runner.py 和 continuous_task_planner.py 中实现 execute mode 的前置检查、确认协议和 execute 硬限制。

### 验收标准

- 实现 preflight 检查（9 项）✓
- 实现确认短语校验（精确匹配 EXECUTE_PROJECT_LOOP）✓
- 实现 execute mode max_tasks 硬限制（3）✓
- 实现 --execute 和 --dry-run 互斥检查 ✓
- 不实现真实任务执行（只做 safety gate）✓

---

## T066 实现 max_tasks=1 execute stub

状态：done
角色：Developer
目标：实现 execute mode 下 max_tasks=1 的最小 stub 执行，只走一个任务闭环。

### 验收标准

- 实现 ExecuteLoopState 数据结构
- 实现 max_tasks=1 的 execute 流程
- 调用 run_project_task_full 执行单任务
- 实现任务后结果检查（continue conditions）
- 实现停止条件判断

---

## T067 验证 execute confirm 拒绝场景

状态：done
角色：Tester
目标：验证所有确认拒绝场景（不带 execute、缺 confirm、模糊确认、max_tasks 非法、dirty 工作区等）。

### 验收标准

- 验证场景 1-9 和 15（共 10 个拒绝场景）
- 每个场景记录输入和预期输出
- 不执行真实任务

---

## T068 验证 max_tasks=1 execute stub

状态：done
角色：Tester
目标：验证 max_tasks=1 execute stub 的执行和停止行为。

### 验收标准

- 验证场景 10-14, 16-17（共 7 个场景）
- 记录每场景的输入、输出和行为
- 确认安全边界有效

---

## T069 提交并推送 execute mode safety MVP

状态：done
角色：Stage Summary
目标：execute mode safety MVP 小结与提交确认。

### 验收标准

- execute safety MVP 小结已生成
- 复核验证全部通过
- 安全边界确认有效

---

## T070 设计 run-project-loop 调用 run-project-task-full 的安全协议

状态：done
角色：Designer
目标：设计从 execute stub 到真实调用 run-project-task-full 的安全协议。

### 验收标准

- 设计单任务真实执行的安全边界 ✓
- 设计执行结果检查协议 ✓
- 设计继续/停止条件 ✓
- 设计失败/返工/dirty 恢复策略 ✓
- 设计 max_tasks 逐步放开策略（1→2→3） ✓

---

## T071 实现 run-project-task-full adapter dry-run

状态：done
角色：Developer
目标：实现 adapter 数据结构和调用链路验证，但不调用真实 run-project-task-full。

### 验收标准

- 新增 TaskExecutionResult 数据结构 ✓
- 新增 ProjectLoopExecutionResult 数据结构 ✓
- 实现 adapter 函数（FullTaskLoopResult → TaskExecutionResult） ✓
- 实现 workspace 检查函数
- 实现 CLAUDE_CODE_CALLED 推断函数
- dry-run 模式不调用真实 run-project-task-full
- 不调用 Claude Code
- 不修改业务代码

---

## T072 验证 adapter 不真实执行

状态：done
角色：Tester
目标：验证 adapter dry-run 所有路径都不调用真实执行。

### 验收标准

- 验证 adapter dry-run 不调用 run-project-task-full ✓
- 验证 adapter dry-run 不调用 Claude Code ✓
- 验证 adapter dry-run 不修改业务代码 ✓
- 验证所有拒绝路径正确返回 ✓

---

## T073 实现 max_tasks=1 real-call stub

状态：done
角色：Developer
目标：在 adapter 基础上实现 real-call stub，构造真实调用信息但不执行，支持 max_tasks=1。

### 验收标准

- 实现 RealCallStubResult 数据结构 ✓
- 实现 run_project_loop_real_call_stub() 函数 ✓
- 扩展 run-project-loop --real-call-stub 参数 ✓
- 构造未来 run-project-task-full 调用信息 ✓
- 不真实调用 run-project-task-full ✓
- 不调用 Claude Code ✓
- 不修改业务代码 ✓
- 不推进任务状态 ✓

---

## T074 验证 CHECK_RESULT=pass 后停止

状态：done
角色：Tester
目标：验证任务成功执行后系统正确停止并等待人工确认。

### 验收标准

- ✓ 验证 CHECK_RESULT=pass 后 loop 停止
- ✓ 验证输出包含 TASK_EXECUTION_PERFORMED=false（real-call stub 不执行任务）
- ✓ 验证不自动进入下一任务
- ✓ 验证安全输出字段完整

<!-- NEXT_PENDING=T075 -->
<!-- NEXT_STAGE=Stage 6 -->

---

## T075 验证 CHECK_RESULT=fail 后停止

状态：done
角色：Tester
目标：验证任务失败后系统正确停止并报告失败原因。

### 验收标准

- ✓ 验证 CHECK_RESULT=fail 后 loop 停止（设计约束 + 代码逻辑 + CLI 实测）
- ✓ 验证 fail 后不自动进入下一任务
- ✓ 验证 human_review_required 正确标记（True）
- ✓ 验证安全输出字段完整

<!-- NEXT_PENDING=T076 -->
<!-- NEXT_STAGE=Stage 6 -->

---

## T076 提交并推送 task execution bridge MVP

状态：done
角色：Developer
目标：提交并推送 task execution bridge MVP 成果。

### 验收标准

- git status 已检查
- 当前改动已提交
- commit message 清晰
- 已成功 push 到远程仓库
- push 后工作区 clean

<!-- NEXT_PENDING=T077 -->
<!-- NEXT_STAGE=Stage 6 -->

---

## T077 设计 max_tasks=1 真实调用 run-project-task-full 安全协议

状态：done
角色：Architect
目标：设计从 real-call stub 到真实调用 run_project_task_full 的安全协议。

### 验收标准

- 设计 real-call bridge 安全协议 ✓
- 设计真实执行后的 workspace 检查规则 ✓
- 设计真实执行后的结果验证规则 ✓
- 设计真实执行的安全边界和人工确认机制 ✓
- 不直接实现代码 ✓

<!-- NEXT_PENDING=T078 -->
<!-- NEXT_STAGE=Stage 6 -->

---

## T078 实现 real-call double-confirm safety gate

状态：done
角色：Developer
目标：实现真实调用的双重确认安全门，包含 RealCallSafetyResult 数据结构和 preflight 检查。

### 验收标准

- ✓ 新增 RealCallSafetyResult 数据结构（20 字段）
- ✓ 新增 validate_real_call_safety() 双重确认校验
- ✓ 实现 preflight 检查（9 层级）
- ✓ runner.py 新增 --real-call 和 --real-confirm 参数
- ✓ 模式互斥检查（--adapter-dry-run / --real-call-stub / --real-call）
- ✓ 拒绝场景全覆盖（12 场景验证）
- ✓ 不真实调用 run_project_task_full

<!-- NEXT_PENDING=T079 -->
<!-- NEXT_STAGE=Stage 6 -->

---

## T079 实现 max_tasks=1 real-call dry-run executor

状态：done
角色：Developer
目标：实现 max_tasks=1 真实调用 run_project_task_full 的执行器，捕获 FullTaskLoopResult 并输出 RealCallExecuteResult。

### 验收标准

- ✓ 实现 RealCallDryRunExecutorResult 数据结构（24 字段）
- ✓ 实现 run_project_loop_real_call_dry_run_executor() 函数
- ✓ 复用 validate_real_call_safety() 双重确认
- ✓ 构造未来调用 command 和 function_call
- ✓ runner.py 新增 --real-call-dry-run 参数
- ✓ 不真实调用 run_project_task_full
- ✓ 不调用 Claude Code
- ✓ 不修改业务代码
- ✓ 11 个验证场景覆盖

<!-- NEXT_PENDING=T084 -->
<!-- NEXT_STAGE=Stage 6 -->

---

## T080 验证 real confirm 拒绝场景 ✅

状态：done
角色：Tester
目标：验证真实调用拒绝场景（场景 1-10），确认不涉及真实调用。

### 验收标准

- ✅ 验证场景 1-10 全部拒绝（7 个拒绝场景 + 2 个区别验证场景）
- ✅ 每个场景记录输入、预期和实际输出
- ✅ REAL_TASK_EXECUTION=no
- ✅ RUN_PROJECT_TASK_FULL_CALLED=no
- ✅ 不真实调用 run_project_task_full

---

## T081 验证 simulated CHECK_RESULT=pass ✅

状态：done
角色：Tester
目标：验证真实执行成功场景（场景 11, 16-17），确认 pass 后停止等待人工确认。

### 验收标准

- ✅ 验证外层 CHECK_RESULT=pass（real-call dry-run executor）
- ✅ 验证 pass 后不自动进入下一任务
- ✅ 验证 pass 后不自动 Git 备份
- ✅ 验证 HUMAN_REVIEW_REQUIRED=true
- ✅ 17 个字段全部符合预期
- ✅ 未执行真实任务，未调用 run-project-task-full

---

## T082 验证 simulated CHECK_RESULT=fail ✅

状态：done
角色：Tester
目标：验证真实执行失败场景（场景 12-15, 18），确认 fail 后正确停止。

### 验收标准

- ✅ fail-stop 设计约束验证通过（8 项约束全部 PASS）
- ✅ T075 fail-stop 验证报告作为依据
- ✅ T077 设计文档 final_status→CHECK_RESULT 映射确认
- ✅ 当前 dry-run executor 12 个字段全部符合预期
- ✅ 未执行真实任务，未调用 run-project-task-full

---

## T083 real-call safety MVP 小结与提交确认 ✅

状态：done
角色：Stage Summary Agent + Real Call Safety MVP Release Check Architect
目标：生成 real-call safety MVP 小结报告，更新 memory 和 tasks.md。

### 验收标准

- ✅ 生成 reports/stage-6-real-call-safety-mvp-summary.md
- ✅ 生成 reports/dev/T083-dev-report.md
- ✅ 更新 memory/lessons.md（real-call safety MVP 经验）
- ✅ 更新 memory/pitfalls.md（real-call safety MVP 避坑）
- ✅ 更新 docs/tasks.md（T083 状态更新）
- ✅ 复核命令验证通过（错误拒绝 + 正确双确认）
- ✅ 未实现新功能，未修改代码文件

---

## T084 设计真实调用 run-project-task-full 的最小实现协议 ✅

状态：done
角色：Designer
目标：设计从 real-call dry-run executor 升级到真实调用 run-project-task-full 的最小实现协议。

### 验收标准

- ✅ 设计 RealCallRunOnceResult 数据结构（26+ 字段）
- ✅ 设计 workspace 变化检测机制（前后快照比较 + 分类）
- ✅ 设计 CLAUDE_CODE_CALLED 和 BUSINESS_CODE_CHANGED 推断逻辑
- ✅ 设计真实执行后的验证方案（21 个场景，分阶段 A/B）
- ✅ 保持 max_tasks=1 限制
- ✅ 保持双重确认要求
- ✅ 推荐 Python 函数调用（非 subprocess）
- ✅ 新增 --real-call-run-once 参数

<!-- NEXT_PENDING=T086 -->
<!-- NEXT_STAGE=Stage 6 -->
---

## T085 实现 real-call run-once safety shell ✅

状态：done
角色：Developer
目标：实现 RealCallRunOnceResult 数据结构和 `run_project_loop_real_call_run_once()` 函数骨架，包含 preflight checks 和拒绝场景全覆盖。

### 验收标准

- ✅ 新增 RealCallRunOnceResult 数据结构（26 字段）
- ✅ 新增 run_project_loop_real_call_run_once_safety_shell() 函数
- ✅ 复用 validate_real_call_safety() 做前置检查
- ✅ 额外 preflight（--real-call-dry-run / --adapter-dry-run / --real-call-stub / --dry-run 互斥）
- ✅ runner.py 新增 --real-call-run-once 参数
- ✅ 拒绝场景全覆盖（12 个验证场景全部 PASS）
- ✅ 不真实调用 run_project_task_full
- ✅ 不调用 Claude Code
- ✅ 不修改业务代码

<!-- NEXT_PENDING=T086 -->
<!-- NEXT_STAGE=Stage 6 -->

---

## T086 实现 child command parser ✅

状态：done
角色：Developer
目标：实现 FullTaskLoopResult 解析、workspace 检测、CLAUDE_CODE_CALLED 和 BUSINESS_CODE_CHANGED 推断函数。

### 验收标准

- ✅ 实现 _snapshot_workspace() 函数
- ✅ 实现 _classify_workspace_changes() 函数
- ✅ 实现 _infer_claude_code_called() 函数
- ✅ 实现 _infer_business_code_changed() 函数
- ✅ 实现 ChildCommandParseResult 数据结构
- ✅ 实现 parse_child_command_output() 函数
- ✅ 新增 parse-child-output-dry-run CLI
- ✅ 10 个验证场景全部 PASS
- ✅ 不真实调用 run_project_task_full
- ✅ 不调用 Claude Code
- ✅ 不修改业务代码

<!-- NEXT_PENDING=T087 -->
<!-- NEXT_STAGE=Stage 6 -->

---

## T087 验证 real-call-run-once 拒绝场景 ✅

状态：done
角色：Tester
目标：验证 real-call-run-once 的 11 个拒绝场景（阶段 A）。

### 验收标准

- ✅ 验证阶段 A 场景 1-10 全部拒绝（10 拒绝 + 1 对照）
- ✅ 每个场景记录输入、预期和实际输出
- ✅ REAL_TASK_EXECUTION=no
- ✅ RUN_PROJECT_TASK_FULL_CALLED=no
- ✅ 不真实调用 run_project_task_full

<!-- NEXT_PENDING=T088 -->
<!-- NEXT_STAGE=Stage 6 -->

---

## T088 验证 simulated child CHECK_RESULT=pass

状态：done ✅
角色：Tester
目标：验证使用模拟 FullTaskLoopResult 数据时，final_status=COMPLETE 的解析和输出。

### 验收标准

- ✅ 验证 CHECK_RESULT=pass 映射正确
- ✅ 验证 AUTO_CONTINUE_TO_NEXT_TASK=no
- ✅ 验证 AUTO_GIT_BACKUP=no
- ✅ 验证 HUMAN_REVIEW_REQUIRED=true
- ✅ 验证 workspace 检测和推断逻辑
- ✅ 不真实调用 run_project_task_full

<!-- NEXT_PENDING=T089 -->
<!-- NEXT_STAGE=Stage 6 -->

---

## T089 验证 simulated child CHECK_RESULT=fail

状态：done ✅
角色：Tester
目标：验证使用模拟 FullTaskLoopResult 数据时，final_status=FAILED/BLOCKED/REQUEST_CHANGES 的解析和输出。

### 验收标准

- ✅ 验证 CHECK_RESULT=fail 映射正确
- ✅ 验证 fail 后不自动继续
- ✅ 验证 fail 后不自动 Git 备份
- ✅ 验证 fail 后不自动返工
- ✅ 验证异常处理
- ✅ 不真实调用 run_project_task_full

<!-- NEXT_PENDING=T090 -->
<!-- NEXT_STAGE=Stage 6 -->

---

## T090 real-call run-once MVP 小结与提交确认 ✅

状态：done ✅
角色：Stage Summary Agent + Real-call Run-once MVP Release Check Architect
目标：生成 real-call run-once MVP 小结报告，更新 memory 和 tasks.md。

### 验收标准

- ✅ 生成 reports/stage-6-real-call-run-once-mvp-summary.md
- ✅ 生成 reports/dev/T090-dev-report.md
- ✅ 更新 memory/lessons.md（real-call run-once MVP 经验）
- ✅ 更新 memory/pitfalls.md（real-call run-once MVP 避坑）
- ✅ 更新 docs/tasks.md（T090 状态更新）
- ✅ 复核命令验证通过（safety shell + parser pass/fail）
- ✅ 未实现新功能，未修改代码文件

<!-- NEXT_PENDING=T091 -->
<!-- NEXT_STAGE=Stage 7 -->

---

## T091 设计首次真实调用 run-project-task-full 的验收协议 ✅

状态：done ✅
角色：Architect
目标：设计从 safety shell + parser dry-run 升级到首次真实调用 run_project_task_full 的验收协议，确认环境、任务选择、预期结果和回退策略。

### 验收标准

- ✅ 定义首次真实调用的前置条件
- ✅ 定义候选任务选择规则
- ✅ 定义预期结果和回退策略
- ✅ 定义安全边界和人工介入条件
- ✅ 定义验收状态模型（FirstRealRunAcceptanceResult）
- ✅ 定义成功验收标准（10 个条件）
- ✅ 定义失败/阻塞标准（4 种严重程度）
- ✅ 定义人工验收清单（10 项）
- ✅ 定义 workspace 分类规则（6 种分类）
- ✅ 定义 Claude Code 调用状态规则（yes/no/unknown）
- ✅ 定义 Git 备份规则（不自动 backup）
- ✅ 设计验证场景（33 个）
- ✅ 不实现代码
- ✅ 不修改 runner.py
- ✅ 不执行真实任务

<!-- NEXT_PENDING=T092 -->
<!-- NEXT_STAGE=Stage 7 -->

---

## T092 实现 first real-run acceptance result model ✅

状态：done ✅
角色：Developer
目标：实现 FirstRealRunAcceptanceResult 数据结构和验收状态判定函数。

### 验收标准

- ✅ 新增 FirstRealRunAcceptanceResult 数据结构（26 字段）
- ✅ 新增 evaluate_first_real_run_acceptance() 函数
- ✅ 新增 first-real-run-acceptance-dry-run CLI（5 个样例）
- ✅ 复用 parse_child_command_output + workspace 辅助函数
- ✅ 49/49 函数级断言全部 PASS
- ✅ 不真实调用 run_project_task_full
- ✅ 不调用 Claude Code
- ✅ 不修改业务代码

<!-- NEXT_PENDING=T093 -->
<!-- NEXT_STAGE=Stage 7 -->

---

## T093 实现 simulated first real-run acceptance parser ✅

状态：done ✅
角色：Developer
目标：使用模拟 FullTaskLoopResult 数据验证验收判定逻辑。

### 验收标准

- ✅ 模拟 final_status=COMPLETE 的验收判定
- ✅ 模拟 final_status=FAILED 的验收判定
- ✅ 模拟 final_status=BLOCKED 的验收判定
- ✅ 模拟 final_status=REQUEST_CHANGES 的验收判定
- ✅ 模拟异常的验收判定
- ✅ 验证所有 ACCEPTANCE_STATUS 值正确
- ✅ 不真实调用 run_project_task_full
- ✅ 不调用 Claude Code

<!-- NEXT_PENDING=T094 -->
<!-- NEXT_STAGE=Stage 7 -->

---

## T094 验证 first real-run acceptance pass/fail 场景 ✅

状态：done ✅
角色：Tester
目标：验证验收协议的 pass/fail/blocked/unsafe 场景（阶段 B+C+D 模拟数据）。

### 验收标准

- ✅ 验证 pass 后 ready_for_human_review（2 个 pass 场景）
- ✅ 验证 fail 后 blocked（4 个 blocked 场景）
- ✅ 验证异常后 failed_to_parse（1 个场景）
- ✅ 验证 dirty_unexpected 后 unsafe_to_continue（1 个场景）
- ✅ 验证 unknown 字段导致 blocked（不降级为 no）
- ✅ 验证 pass 后不自动继续（auto_continue=false）
- ✅ 验证 fail 后不自动返工（auto_continue=false）
- ✅ 不真实调用 run_project_task_full

<!-- NEXT_PENDING=T096 -->
<!-- NEXT_STAGE=Stage 7 -->

---

## T095 设计首次真实调用 run-project-task-full 执行开关 ✅

状态：done ✅
角色：Architect
目标：设计从 safety shell 升级到真实执行的切换机制，保留所有 preflight 检查。

### 验收标准

- ✅ 设计执行开关机制（--real-execute-once + --real-execute-confirm EXECUTE_REAL_RUN_ONCE）
- ✅ 设计异常处理和回退策略
- ✅ 保留所有 preflight 检查（19 项）
- ✅ 不实现代码

### 产出文件

- ✅ docs/first-real-run-execution-switch-design.md
- ✅ reports/dev/T095-dev-report.md
- ✅ memory/lessons.md（追加经验）
- ✅ memory/pitfalls.md（追加避坑记录）

---

## T096 实现 first real-run execute-once safety gate ✅

状态：done ✅
角色：Developer
目标：实现 first real-run execute-once safety gate（第三重确认 + 新参数 + preflight 扩展），不真实调用 run-project-task-full。

### 验收标准

- ✅ 新增 FirstRealRunExecuteOnceSafetyResult 数据结构（25 字段）
- ✅ 新增 REAL_EXECUTE_CONFIRM_PHRASE = "EXECUTE_REAL_RUN_ONCE"
- ✅ 新增 validate_first_real_run_execute_once_safety() 函数
- ✅ 复用 validate_real_call_safety() 做双重确认前置检查
- ✅ 新增第三重确认检查（missing / rejected / accepted）
- ✅ 新增 max_tasks=1 only 检查
- ✅ runner.py 新增 --real-execute-once 参数
- ✅ runner.py 新增 --real-execute-confirm 参数
- ✅ 不带 --real-execute-once 时保持 T085 行为不变
- ✅ 16 个验证场景全部 PASS
- ✅ 不真实调用 run_project_task_full
- ✅ 不调用 Claude Code
- ✅ 不修改业务代码

### 产出文件

- ✅ tools/continuous_task_planner.py（新增 FirstRealRunExecuteOnceSafetyResult + validate_first_real_run_execute_once_safety）
- ✅ runner.py（新增 --real-execute-once + --real-execute-confirm CLI）
- ✅ reports/checks/T096-first-real-run-execute-once-safety-gate-check.md
- ✅ reports/dev/T096-dev-report.md

<!-- NEXT_PENDING=T099 -->
<!-- NEXT_STAGE=Stage 7 -->

---

## T097 验证 execute-once 拒绝场景

状态：done
角色：Tester
目标：在 clean workspace 下验证 --real-execute-once 在前置条件不满足时必须拒绝，正确三重确认只进入 safety gate 不真实执行。

### 验收标准

- [x] 16 个拒绝场景全部验证通过
- [x] 正确三重确认对照验证 REAL_EXECUTE_ALLOWED=true
- [x] 第三重确认精确匹配（只有 EXECUTE_REAL_RUN_ONCE accepted）
- [x] 未执行真实任务、未调用 run-project-task-full、未调用 Claude Code
- [x] 工作区保持 clean

### 输出文件

- reports/checks/T097-execute-once-rejection-check.md
- reports/dev/T097-dev-report.md

---

## T098 实现 first real-run executor simulated child call

状态：done
角色：Developer
目标：实现模拟 FullTaskLoopResult 输入的执行链路验证，不真实调用 run_project_task_full。

### 验收标准

- [x] 模拟 FullTaskLoopResult 输入（pass / fail / missing-check-result / dirty-unexpected / unsafe-unknown / missing-report-paths）
- [x] 模拟 workspace 变化
- [x] 复用 parse_child_command_output() + evaluate_first_real_run_acceptance()
- [x] 验证执行流程完整（safety gate → simulated stdout → parser → acceptance）
- [x] 不真实调用 run_project_task_full

### 输出文件

- tools/continuous_task_planner.py（新增 FirstRealRunExecutorSimulatedResult + run_first_real_run_executor_simulated_child_call + _SIMULATED_CHILD_SAMPLES）
- runner.py（新增 --simulate-child + --child-sample CLI）
- reports/checks/T098-first-real-run-executor-simulated-child-call-check.md
- reports/dev/T098-dev-report.md

---

## T099 验证 simulated real execution pass/fail

状态：done
角色：Tester
目标：验证模拟执行链路在 pass/fail 场景下的行为正确性。

### 验收标准

- [x] 验证 simulated pass → ready_for_human_review
- [x] 验证 simulated fail → blocked
- [x] 验证 simulated exception → blocked / failed_to_parse / unsafe_to_continue
- [x] 验证所有场景停止等待人工验收
- [x] 不真实调用 run_project_task_full

### 输出文件

- reports/checks/T099-simulated-real-execution-pass-fail-check.md
- reports/dev/T099-dev-report.md

<!-- NEXT_PENDING=T100 -->
<!-- NEXT_STAGE=Stage 7 -->

---

## T100 执行第一次真实 run-project-task-full 调用

状态：pending
角色：Developer
目标：解除 simulated，连接真实 run_project_task_full()，执行第一次真实调用。

### 验收标准

- 真实调用 run_project_task_full(project_path, task_id)
- 捕获 FullTaskLoopResult
- 构建 FirstRealRunAcceptanceResult
- workspace 前后检查
- 输出验收结果
- 停止等待人工确认

---

## T101 人工验收第一次真实调用结果

状态：pending
角色：Human
目标：使用 10 项验收清单人工验收第一次真实调用结果。

### 验收标准

- 使用验收清单逐项确认
- 确认执行结果可信
- 决定是否继续下一任务