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

状态：in_progress
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

## T049 使用 run-project-next 自动执行 G006

状态：pending
角色：Developer
目标：自动实现简单重力下落。

### 验收标准

- Developer 生成 G006-dev-report
- 玩家可以随时间向下移动
- 重力下落逻辑清晰可测试
- 不做平台碰撞
- 不做平台滚动
- 不做失败条件
- 不做随机平台
- 不做角色技能系统

---

## T050 G006 Tester / Reviewer / Main Decision 完整闭环

状态：pending
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

## T051 碰撞检测测试协议设计

状态：pending
角色：Architect
目标：设计玩家与平台基础碰撞的测试协议。

### 验收标准

- 定义碰撞检测的测试检查项
- 明确只检测玩家落到平台上
- 明确不做复杂物理
- 明确不做平台滚动
- 明确不做失败条件
- 为 T053 实现 G007 做测试准备

---

## T052 新增 G007 玩家与平台基础碰撞任务

状态：pending
角色：Planner
目标：在子项目任务清单中添加 G007。

### 验收标准

- 子项目 tasks.md 追加 G007 pending
- G007 只做玩家落到平台时停止
- 不做平台滚动
- 不做随机平台
- 不做失败条件
- 不做角色技能系统

---

## T053 使用 run-project-next 自动执行 G007

状态：pending
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

## T054 G007 Tester / Reviewer / Main Decision 完整闭环

状态：pending
角色：Developer
目标：让 G007 完成测试、审查、综合决策。

### 验收标准

- 生成 G007-test-report（基础测试）
- 生成 G007-behavior-test-report（碰撞行为测试）
- 生成 G007-review-report（DeepSeek 审查）
- 生成 G007-main-decision（综合决策）
- 如果失败，只记录，不自动返工
- 不跳过证据链

---

## T055 自动返工执行人工确认协议设计

状态：pending
角色：Architect
目标：设计用户确认后执行返工的协议。

### 验收标准

- 定义人工确认入口
- 定义确认后的执行流程
- 定义最大返工次数仍为 3
- 定义人工介入条件
- 不做完全无人值守
- 不绕过用户确认

---

## T056 自动返工执行 MVP

状态：pending
角色：Developer
目标：在用户确认后执行已有 rework prompt。

### 验收标准

- 可以读取已生成的 rework prompt
- 用户确认后可以调用 Claude Code 执行返工
- 返工后可以重新运行 Tester
- 返工后可以重新运行 Reviewer
- 返工后可以重新生成 Main Decision
- 不自动无限循环
- 不绕过用户确认
- 不超过 3 次返工限制
- 不修改 project.yaml 或主框架文件

---

## T057 第五阶段阶段总结与 Git 备份

状态：pending
角色：Reporter
目标：总结第五阶段成果并提交推送。

### 验收标准

- 创建第五阶段总结报告
- 更新 docs/phase-5-plan.md 验收标准
- 更新主项目 memory/lessons.md
- 更新主项目 memory/pitfalls.md
- 更新验证项目 memory/lessons.md
- 更新验证项目 memory/pitfalls.md
- git status 已检查
- 当前改动已提交
- 已成功 push 到远程仓库
- push 后工作区 clean
