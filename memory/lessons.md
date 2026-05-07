# Lessons

## 第一阶段经验总结

1. **自动化流程必须从最小闭环开始。** 先跑通"读任务 → 生成 prompt → 调用 Claude Code → 判断结果 → 更新状态"，再逐步增加能力。

2. **任务状态必须可机器读写。** `docs/tasks.md` 用固定格式（`状态：pending / in_progress / done`），runner.py 通过正则解析和更新，不需要数据库。

3. **生成 prompt、执行 prompt、判断结果、更新状态要拆成独立能力。** 每个能力独立函数，通过命令行组合，方便调试和复用。

4. **returncode=0 只能说明 Claude Code 进程成功，不代表任务完成。** Claude Code 可能只输出了建议代码而没有实际修改文件。

5. **必须检查完成证据。** 以 `reports/dev/<任务编号>-dev-report.md` 是否存在作为最小完成证据。没有证据不标记 done。

6. **retry-current 是处理 in_progress 卡住任务的必要能力。** 任务执行不完整时，可以重新生成 prompt 并重新调用 Claude Code，不需要手动干预。

7. **Claude Code 非交互执行必须允许自动编辑文件。** 调用时需要 `--permission-mode acceptEdits`，否则 Claude Code 只会输出建议代码而不是实际修改文件。

8. **runner.py 应作为最外层调度器。** Claude Code 是被调用的执行器，不应在 Claude Code 执行过程中嵌套调用 runner.py 的自动执行命令。

## T020.1 第一次子项目自动执行成功经验

### 成果

`multi-agent-runner` 已经第一次成功驱动 `projects/down-100-floors-game` 自动完成真实开发任务 G002。

### 成功链路

1. `runner.py run-game-next` 读取子项目任务文件。
2. 自动找到 G002 pending。
3. 自动将 G002 标记为 in_progress。
4. 自动生成 G002 执行提示词。
5. 自动调用 Claude Code。
6. Claude Code 自动修改子项目文件。
7. Claude Code 自动生成 `projects/down-100-floors-game/reports/dev/G002-dev-report.md`。
8. runner 检查完成证据。
9. G002 自动标记为 done。
10. index.html 可以在浏览器打开。

### 关键经验

- 子项目任务清单可以独立于主项目任务清单。
- 主框架可以通过专用命令驱动子项目任务。
- 完成证据检查对自动化判断非常关键。
- 验证项目应先从最小页面开始，不要一开始实现复杂玩法。
- 真实项目验证中发现的问题，应回写主框架。

## T022 第二阶段经验总结

### 核心经验

- 协议先行是必要的：Workflow / Agent Output / Requirement 三类协议为自动化提供了基础。
- 多模型适配器必须支持角色级模型配置，Reviewer 不应默认使用 Developer 同款模型。
- 真实验证项目比单纯框架自测更能暴露问题。
- 子项目自动执行应先用专用命令验证，再逐步泛化成通用 project runner。
- 完成证据检查仍然是自动化判断的核心。
- 重要节点必须先 Git 提交和 push，再继续下一阶段。

## T023 第三阶段规划经验

- 第三阶段应先提升框架通用性，再继续增加业务功能。
- `run-game-next` 已经证明子项目自动执行可行，但需要泛化为通用 project runner。
- 接入真实 Reviewer 模型前，必须保留 mock provider 回退。
- 测试链路要从最小静态检查开始，不要一开始引入复杂浏览器自动化。
- 小游戏功能开发应继续保持小任务，例如先做玩家显示和左右移动。
- 综合决策应先输出建议，不直接自动执行返工。

## T024 Project Runner 协议设计经验

- `run-game-next` 已证明子项目自动执行可行，但需要通过 project runner 泛化。
- 通用 project runner 必须先定义项目结构、任务文件、完成证据和安全边界。
- 子项目任务必须和主项目任务隔离（前缀隔离 + 路径隔离）。
- prompt 生成必须针对子项目，避免 Claude Code 误改主框架。
- 完成证据路径必须根据项目路径动态计算，不能硬编码。
- project.yaml 为可选配置，缺失时使用合理默认值，降低接入门槛。

## T025.1 通用 project runner 首次验证成功经验

### 成果

`multi-agent-runner` 已经通过通用命令：

```powershell
python runner.py run-project-next --project projects/down-100-floors-game
```

成功驱动 down-100-floors-game 自动完成 G003 实现玩家角色显示。

### 成功链路

1. `run-project-next` 接收 `--project` 项目路径参数
2. 自动读取 `<project>/docs/tasks.md`
3. 自动找到第一个 pending 子项目任务 G003
4. 自动将 G003 标记为 in_progress
5. 自动生成针对子项目的执行 prompt
6. 自动调用 Claude Code
7. Claude Code 自动修改子项目文件
8. Claude Code 自动生成 `<project>/reports/dev/G003-dev-report.md`
9. runner 检查完成证据
10. G003 自动标记为 done

### 关键经验

- `run-project-next` 证明了通用 project runner 方向可行。
- 子项目路径参数是从专用命令走向通用执行器的关键。
- 子项目完成证据必须基于项目路径动态计算。
- prompt 必须明确限制修改范围，避免误改主框架。
- 通用化应从一个已验证项目开始，而不是一开始支持所有项目类型。

## T028.1 DeepSeek Reviewer 首次真实审查成功经验

### 成果

`multi-agent-runner` 已经第一次完成真实模型分工链路：

- Developer：Claude Code + GLM
- Reviewer：DeepSeek API
- Runner：调度、保存报告、解析结构化结果

### 成功链路

1. G003 已由 `run-project-next` 自动开发完成。
2. G003 已生成 `projects/down-100-floors-game/reports/dev/G003-dev-report.md`。
3. `review-game-task G003` 读取任务要求、开发报告和项目文件快照。
4. 系统构造 Reviewer prompt。
5. `model_adapter` 调用 DeepSeek Reviewer。
6. DeepSeek 返回审查内容。
7. Reviewer 输出包含 `Machine Readable Result`。
8. runner 解析出 `Status=PASS`。
9. runner 解析出 `Decision=APPROVE`。
10. 审查报告保存为 `projects/down-100-floors-game/reports/review/G003-review-report.md`。

### 关键经验

- 开发模型和审查模型分离是必要的。
- DeepSeek Reviewer 可以作为第一版独立审查模型。
- Reviewer 输出必须包含机器可解析块，不能只依赖自然语言。
- `Status / Decision / Issues` 是后续 Main Agent 综合决策的关键输入。
- 真实审查结果先人工观察，不应立即自动返工。

## T029 Tester Agent 协议设计经验

- Tester Agent 应从最小静态检查开始，不要一开始引入复杂浏览器自动化。
- 测试报告是自动化完成证据的一部分。
- Tester 的目标是验证验收标准，而不是修改代码。
- 测试结果必须能被 Main Agent 读取和综合判断。
- 对 Web MVP，先检查文件存在、关键 DOM、基础 CSS 和基础 JS 即可。
- 测试报告模板应与输出协议一致，减少实现时的格式歧义。
- PASS/FAIL 规则要简单明确：全部必需项通过 = PASS，任一失败 = FAIL。

## T031.1 三方证据链与 Main Agent 综合决策成功经验

### 成果

`multi-agent-runner` 已经第一次完成完整的任务验收闭环：

- Developer Agent：生成开发报告
- Tester Agent：生成测试报告并 PASS
- Reviewer Agent：生成审查报告并 APPROVE
- Main Agent：综合三方结果并输出 COMPLETE

### 成功链路

1. `run-project-next` 自动执行 G003。
2. Claude Code 修改子项目文件并生成 `G003-dev-report.md`。
3. `test-game-task G003` 执行本地静态测试。
4. Tester Agent 生成 `G003-test-report.md`。
5. Tester 结果为 `PASS`，16/16 测试项通过。
6. `review-game-task G003` 调用 DeepSeek Reviewer。
7. Reviewer 生成 `G003-review-report.md`。
8. Reviewer 结果为 `APPROVE`。
9. `decide-game-task G003` 综合 Developer / Tester / Reviewer 三方结果。
10. Main Agent 生成 `G003-main-decision.md`。
11. Main Decision 为 `COMPLETE`。

### 关键经验

- 完整闭环需要 Developer / Tester / Reviewer 三类证据，不能只依赖开发报告。
- Tester 和 Reviewer 是不同职责：Tester 验证事实，Reviewer 判断是否符合需求和边界。
- Main Agent 不做具体开发，只做综合判断和下一步决策。
- `COMPLETE` 应建立在多方证据一致通过的基础上。
- 这为后续自动返工和自动推进下一任务提供了基础。

## T032.1 G004 完整闭环成功经验

### 成果

`G004 实现玩家键盘左右移动` 已经完成完整闭环：

- Developer Agent：自动开发完成
- Tester Agent：静态测试 PASS
- Reviewer Agent：DeepSeek 审查 APPROVE
- Main Agent：综合决策 COMPLETE

### 成功链路

1. `run-project-next` 自动找到 G004 pending 任务。
2. G004 自动标记为 `in_progress`。
3. Claude Code 自动修改小游戏项目文件。
4. G004 开发报告生成：`G004-dev-report.md`。
5. G004 自动标记为 `done`。
6. `test-game-task G004` 生成测试报告。
7. Tester 结果为 `PASS`，16/16 项通过。
8. `review-game-task G004` 调用 DeepSeek Reviewer。
9. Reviewer 输出 `PASS / APPROVE / Issues=0`。
10. `decide-game-task G004` 综合三方结果。
11. Main Agent 输出 `COMPLETE`。

### 关键经验

- 小任务拆分有效：G003 只做玩家显示，G004 只做左右移动。
- 使用同一套 Developer / Tester / Reviewer / Main Agent 链路，可以连续验证游戏功能演进。
- Tester 当前仍是静态检查，能验证基础结构，但对移动行为的验证还需要后续增强。
- Reviewer 可以辅助判断任务边界是否被扩大。
- Main Agent 综合决策让任务完成状态更加可信。

## T033 第三阶段经验总结

### 核心经验

- 通用 `run-project-next` 是从单项目验证走向多项目复用的关键一步。
- DeepSeek Reviewer 接入后，开发模型和审查模型实现了职责分离。
- Reviewer 输出必须结构化，才能被 Main Agent 稳定使用。
- Tester Agent 即使先做静态检查，也能补齐"事实验证"环节。
- Main Agent 综合决策必须基于 Developer / Tester / Reviewer 多方证据。
- G003 / G004 连续闭环证明框架可以连续驱动真实项目迭代。
- 小步任务边界非常重要：G003 只做玩家显示，G004 只做左右移动。

## T035 Tester 行为检查协议设计经验

- 基础静态检查只能验证结构存在，不能充分证明交互行为正确。
- 对 G004 这类键盘移动任务，需要额外检查键盘事件、左右移动、边界限制和位置更新逻辑。
- 行为检查可以先从源码静态检查开始，暂时不引入浏览器自动化。
- 原始测试报告和行为测试报告应分开保存，便于 Main Agent 综合判断。
- Tester 能力应随着业务复杂度逐步增强。

## T040 自动返工协议设计经验

- 自动返工不能一开始就无人值守执行，必须先生成返工任务和返工 prompt。
- 返工必须基于 Tester / Reviewer / Main Agent 的失败证据，不能只凭一句错误描述。
- 返工任务应使用独立编号，例如 `G004-R1`，避免污染原任务。
- 返工完成后必须重新测试、审查和综合决策。
- project.yaml 中的 allowed_files / blocked_files 应用于返工 prompt。

## T043.2 G005 Developer 特殊完成经验

### 成果

G005 在执行 `run-project-next` 时出现了特殊情况：

- Claude Code 实际完成了 G005 开发
- 完成证据 `G005-dev-report.md` 已生成
- 子项目任务状态已更新为 `done`
- 但 Claude Code 最后返回 API 429，导致 runner 原本输出"执行失败"

### 关键经验

- 不应只依赖模型进程返回码判断任务是否完成。
- `returncode != 0` 但完成证据存在时，需要进一步检查任务状态。
- 完成证据和任务状态可以作为人工确认的重要依据。
- 429 / 限额错误可能发生在任务完成后的收尾阶段。
- runner 需要区分"真正失败"和"完成证据存在但模型返回错误"。
- T043.0 修复了超时异常处理，T043.1 修复了 returncode 与证据冲突判断，两个修复共同提升了框架稳定性。

## T044.4 G005 完整闭环成功经验

### 成果

`G005 实现基础平台显示` 已完成完整闭环：

- Developer Agent：生成 `G005-dev-report.md`
- Tester Agent：生成 `G005-test-report.md`，结果 `PASS`，16/16 通过
- Reviewer Agent：生成 `G005-review-report.md`，结果 `PASS / APPROVE`
- Main Agent：生成 `G005-main-decision.md`，结果 `COMPLETE`

### 成功链路

1. `run-project-next` 自动执行 G005。
2. Claude Code 修改 `index.html` / `style.css` / `script.js`。
3. G005 生成开发报告。
4. G005 状态更新为 `done`。
5. `test-game-task G005` 生成基础测试报告。
6. Tester 结果为 `PASS`。
7. `review-game-task G005` 调用 DeepSeek Reviewer。
8. Reviewer 结果为 `APPROVE`。
9. `decide-game-task G005` 生成 Main Decision。
10. Main Agent 输出 `COMPLETE`。

### 关键经验

- G005 继续验证了 `project runner` 可以驱动真实游戏功能小步迭代。
- 平台显示任务应独立于重力、碰撞、滚动和随机生成。
- 即使 Claude Code 最后返回 429，也要优先检查完成证据和任务状态。
- Developer / Tester / Reviewer / Main Agent 四类证据可以帮助判断真实完成情况。
- 后续 G006 重力下落应继续保持小任务边界。

## T045 第四阶段经验总结

### 核心经验

- Tester 能力必须随着业务复杂度逐步增强，G004 键盘移动需要行为检查。
- project.yaml 是从路径约定走向项目配置驱动的重要一步。
- 自动返工必须先有安全限制，最大返工次数可以避免死循环。
- 返工 prompt 生成和返工执行必须分开，先人工确认再执行。
- 模型返回码不能作为唯一完成判断，必须结合完成证据和任务状态。
- 429 / 超时等模型异常必须被框架优雅处理。
- G005 基础平台显示继续证明小步功能闭环是可靠路线。

## T046 第五阶段规划经验

- 第五阶段应先设计重力和碰撞的 Tester 协议，再实现对应游戏功能。
- G006 只做简单重力下落，不应同时做碰撞和失败条件。
- G007 只做玩家与平台基础碰撞，不应同时做平台滚动和随机平台。
- 自动返工执行必须基于用户确认，不能直接无人值守循环。
- 每个游戏功能仍应保留 Developer / Tester / Reviewer / Main Agent 证据链。
- 重力和碰撞比前四阶段的功能更复杂，prompt 应明确已有代码上下文。
- Tester 静态检查对物理逻辑有局限性，后续可能需要浏览器自动化。
- 返工执行 MVP 应严格限制次数（3 次）和范围，不绕过用户确认。

## T047 重力下落测试协议设计经验

- G006 应先设计重力测试协议，再实现重力逻辑。
- 简单重力下落只需要验证玩家 y 坐标随时间增加，不应同时引入碰撞。
- 重力测试应检查 gravity、velocityY、playerState.y 和 gameLoop 集成。
- 范围限制检查很重要，防止 G006 一次性实现平台碰撞、滚动或失败条件。
- 重力行为测试可以先从源码静态检查开始，暂时不引入浏览器自动化。
- 5 组 15 个检查项覆盖了重力常量、速度更新、位置更新、循环集成和范围控制。
- 重力检查报告与基础静态检查报告、行为检查报告应分开保存，便于 Main Agent 综合判断。
- 测试协议设计应明确为后续 T050 实现提供方向，包括函数建议和命令建议。

## T049.3 run-project-task-full 首次验证经验

### 成果

`run-project-task-full` MVP 已完成首次真实验证：

- 自动执行 Developer 阶段
- 自动执行 Basic Tester 阶段
- 自动进入 Reviewer 阶段
- Reviewer 因缺少 `DEEPSEEK_API_KEY` 被正确 BLOCKED
- 系统没有错误继续 Main Decision
- 生成 `G006-full-loop-report.md`
- 补充 API Key 后，Reviewer 和 Main Agent 可继续完成闭环

### 关键经验

- 单任务完整闭环自动化已经从协议和代码进入真实验证阶段。
- full loop 遇到环境变量缺失时应停止，而不是继续错误决策。
- `.env` 适合用于本地密钥管理，但必须被 `.gitignore` 忽略。
- 当前 full loop 已能证明 Level 2 自动化初步落地。
- 下一步应补 `.env` 自动加载能力和 full loop resume 能力。

## T050.2 G006 完整闭环与 .env 自动加载经验

### 成果

G006 已完成完整闭环：

- Developer：PASS
- Basic Tester：PASS，16/16
- Reviewer：PASS / APPROVE，Issues=0
- Main Agent：COMPLETE

`.env` 自动加载能力已完成：

- `tools/env_loader.py` 支持读取项目根目录 `.env`
- `runner.py` 启动时自动加载 `.env`
- `.env` 被 `.gitignore` 忽略
- `.env.example` 可作为安全示例文件提交
- 不打印真实 API Key
- 默认不覆盖已有系统环境变量

### 关键经验

- 本地模型 API Key 适合放在 `.env` 中管理，但必须确保 `.env` 不被 Git 跟踪。
- `.env.example` 可以提交，用于说明需要哪些本地变量。
- full loop 第一次卡在 Reviewer 是环境配置问题，不是业务代码问题。
- `.env` 自动加载让 full loop 更接近真正自动化。
- G006 证明简单重力下落可以作为独立任务完成闭环。

## T049.0 单任务完整闭环自动化设计经验

- 当前系统已经具备各 Agent 的单步能力，但真正自动化需要 full task loop 编排。
- 单任务完整闭环是从半自动走向自动化落地的关键一步。
- full loop 必须先覆盖一个任务生命周期，再考虑项目连续循环。
- 自动化编排必须包含失败停止、返工 prompt、最大返工次数和人工介入边界。
- 不应直接从单步命令跳到无人值守项目级循环。
- 命令权限策略（A/B/C/D 四类）是安全自动化的基础，应随协议一起设计。
- 专项 Tester 选择映射应可配置，后续新增测试类型只需扩展映射表。
- full loop 第一版应只生成 rework prompt 不自动执行，验证闭环流程可靠后再开放自动返工。

## T050.3a Claude Code 安全命令自动执行经验

- 真正自动化不能每条低风险命令都等待人工确认。
- 自动化命令需要白名单，而不是完全放开权限。
- 只读检查命令、编译检查命令和状态查看命令可以自动执行。
- Git 提交推送可以在明确 Git 备份任务中自动执行。
- `.env` 和 API Key 必须始终排除在自动化输出之外。
- 权限策略应成为 full task loop 的基础安全协议。

## T051 碰撞检测测试协议设计经验

- G007 应先设计碰撞测试协议，再实现碰撞逻辑。
- 基础碰撞只验证玩家落到平台后停止，不应同时引入平台滚动和失败条件。
- 碰撞测试应检查平台数据、玩家底部、水平重叠、从上方落下和 y 坐标修正。
- 防穿透检查很重要，应考虑上一帧位置或下落方向。
- 范围限制检查可以避免 G007 一次性实现滚动、随机平台或失败条件。
- 6 组 18 个检查项覆盖了碰撞函数、平台数据、落到平台、停止下落、防穿透和范围控制。
- 碰撞检查报告与基础静态检查报告、行为检查报告、重力检查报告应分开保存，便于 Main Agent 综合判断。

## T051.1 Bash / PowerShell 命令差异经验

- Claude Code 在 Windows 项目中可能通过 Bash 执行命令。
- PowerShell 命令如 `Test-Path`、`Get-Content`、`Select-String` 不能直接在 Bash 中运行。
- 自动化提示词应优先使用 Bash 通用命令：`test -f`、`tail -n`、`grep -n`。
- 如果确实需要 PowerShell 命令，应明确指定 PowerShell 执行环境。
- 命令权限白名单必须同时区分 Bash 和 PowerShell 写法。

## T053.4 G007 完整闭环经验

- G007 通过自动化链路完成了 Developer、Basic Tester、Collision Tester、Reviewer、Main Agent 的完整闭环。
- Collision Tester 首次失败并不一定代表业务代码错误，可能是 Tester 关键词匹配过窄。
- T053.1 修正 Tester 后，G007 碰撞专项测试通过，说明专项 Tester 需要持续迭代。
- DeepSeek Reviewer 适合在 Tester 通过后做实现范围与代码质量审查。
- Main Agent 应基于 Developer / Tester / Reviewer 多方证据做最终决策。
- Reviewer 首次超时后重试成功，说明 API 调用需要合理的超时和重试策略。

## T054 G007 冗余闭环任务关闭经验

- 当原任务目标已被前置子任务完成时，不应重复执行相同测试、审查和决策。
- T054 的原始目标已由 T053.2 / T053.3 / T053.4 完成，因此 T054 只做关闭记录是合理的。
- 自动化项目中需要允许任务被前置完成后进行"记录关闭"，避免重复调用模型和重复执行 Developer。
- G007 证明 Claude Code Developer、Collision Tester、DeepSeek Reviewer、Main Agent 可以形成有效协作链路。

## T055 自动返工执行人工确认协议经验

- 自动化不能等于无限自动返工。返工执行是高风险写入操作，必须与 rework prompt 生成区分。
- Tester FAIL 或 Reviewer REQUEST_CHANGES 可以进入 REWORK_CANDIDATE，但不能直接执行返工。
- 严格人工确认格式（`确认执行 <task-id>-R<round> 返工` 或 `APPROVE_REWORK task=<id> round=<n>`）可以避免用户一句"继续"导致系统误执行。
- 最大 3 次返工限制是防止死循环的关键边界，超过 3 次必须生成人工介入报告。
- 环境阻塞（API Key 缺失、429、网络错误）不应触发返工，应直接进入 BLOCKED。
- 返工命令不得进入全局 allowlist，只能在满足全部前置条件时执行。
- REWORK_CANDIDATE 只允许生成证据和建议，不允许修改任何业务代码。

## T055.3 Git 备份命令逐条执行经验

- Git 备份任务可以自动执行，但应逐条执行命令。
- `cd && git add && git commit && git push` 会触发 Claude Code 安全确认（bare repository attack），不应加入白名单。
- 执行 Git 备份前应先用 `pwd` 确认当前目录。
- 如果当前目录不正确，应停止并报告，而不是用 `cd && git` 复合命令继续。
- 自动化要追求低风险命令自动执行，而不是把复合高风险命令全部放开。

## T056 execute-rework MVP 经验

- 返工执行必须先做安全外壳，再考虑真实执行。
- MVP 默认 dry-run，可以验证确认格式、轮次限制和 prompt 存在性。
- 未确认、确认错误、超过 3 轮都必须阻止执行。
- execute-rework 不应进入全局 allowlist。
- 确认格式校验应区分"格式错误"和"task/round 不匹配"两种场景。
- 中文和英文两种确认格式可以覆盖不同用户习惯。

## T056.2 confirmed rework execution stub 经验

- confirmed stub 在 dry-run 基础上增加了 real_execution_requested 和 execution_allowed 语义。
- 即使全部检查通过，real_execution_performed 始终为 false。
- 拒绝场景应区分 confirmation_status（missing / rejected）、round_status（invalid / exceeded）和 safety_status（fail）。
- 不带 --real-execution 时必须保持原有 dry-run 行为不变。

## T056.5 full loop resume stub 经验

- resume stub 复用 execute_confirmed_rework 的全部校验逻辑，避免重复造轮子。
- --resume 必须配合 --real-execution 和 --confirm 使用，单独使用应返回错误。
- resume_allowed=true 只代表"安全检查已全部通过"，不代表真实执行了返工。
- resume_target=NEXT_PENDING 为第六阶段调度器提供了接口。
- 不带 --resume 时保持 T056.2 原有行为不变。

## T057 第五阶段经验总结

### 核心经验

- 单任务完整闭环（run-project-task-full）是从半自动走向自动化的关键一步。
- 专项 Tester 需要持续迭代，G007 Collision Tester 首次失败是关键词匹配过窄。
- 返工执行必须与返工 prompt 生成分离，REWORK_CANDIDATE 不等于返工执行。
- 严格确认格式可以避免用户一句"继续"导致系统误执行。
- 最大 3 次返工限制是防止死循环的关键边界。
- resume stub 为连续推进奠定基础，resume_target=NEXT_PENDING 为调度器提供了接口。
- A/B/C/D 命令权限策略是安全自动化的基础。
- .env 自动加载简化了 API Key 管理，但必须确保 .env 不被 Git 跟踪。

## T058-T062 第六阶段 MVP 经验

### 核心经验

- 连续任务推进应先实现 planner dry-run，再实现 loop dry-run，最后才考虑真实执行。
- `plan-project-loop` 和 `run-project-loop` 是两个独立能力：plan 只读不模拟，loop 才做模拟推进。
- max_tasks 必须有硬上限（10）和默认值（3），防止一次性规划过多任务。
- max_tasks=0 应明确拒绝，max_tasks>hard_limit 应自动裁剪，两者行为不同。
- LOOP_STATUS 需要区分 `stopped_on_max_tasks`（达到上限截断）和 `dry_run_completed`（自然结束）。
- RUN_ID 格式 `loop-YYYYMMDD-HHMMSS-<6hex>` 便于追溯和日志关联。
- 验证任务（T061/T062）也应独立提交，保持提交粒度一致。
- dry-run 输出的 TASK_EXECUTION_PERFORMED=false / CLAUDE_CODE_CALLED=false / BUSINESS_CODE_CHANGED=false 是安全保证的关键标志。
- 第六阶段从设计到实现到验证全部 dry-run，未执行任何真实任务，证明分阶段安全推进策略有效。

## T064 Execute Mode 安全设计经验

### 核心经验

- 从 dry-run 到 execute 必须单独设计 safety gate，不能复用 dry-run 的安全假设。
- execute mode 的 max_tasks 硬限制应该低于 dry-run（execute=3 vs dry-run=10），因为真实执行失败代价高。
- 不能把 dry-run 成功等同于允许真实执行，两者是独立的安全域。
- 确认短语必须精确匹配（EXECUTE_PROJECT_LOOP），yes/ok/确认等模糊确认必须拒绝。
- execute mode 需要独立的前置检查（preflight），比 dry-run 更严格（9 项 vs 2 项）。
- rework candidate 出现时应停止而不是自动执行 execute-rework，rework 需要人工确认。
- Git backup 应停止并提醒，不自动 push，push 需要人工确认。
- CLI 方案推荐复用 run-project-loop 加 --execute，而非新增独立命令，最小化改动和用户学习成本。
- execute mode MVP 只允许 max_tasks=1，逐步放开到 2、3，经验积累后再提高上限。

## T064-T069 Execute Safety MVP 经验

### 核心经验

- safety gate 和 execute stub 必须分开实现：safety gate 只做前置检查，stub 只做模拟执行，两者职责不同。
- confirm 拒绝场景必须单独验证（T067），不能只依赖代码逻辑审查。7 个拒绝场景 + 1 个互斥场景全覆盖。
- max_tasks=1 stub 验证必须在 clean workspace 下做（T068），dirty workspace 下只能做代码逻辑验证。
- 不能把 execute stub 误认为真实执行。EXECUTE_STUB_STARTED=true 不代表 TASK_EXECUTION_PERFORMED=true。
- execute mode 的三层检查结构有效：safety gate → stub max_tasks check → stub execution（模拟）。
- CHECK_RESULT 字段对自动化判断非常有用：pass = stub started，fail = stub 未启动。
- 验证任务和实现任务应保持独立提交粒度（T066→T067→T068），便于追溯和回退。

## T070 Task Execution Bridge 设计经验

### 核心经验

- 从 execute stub 到真实调用必须先设计 adapter。Adapter 负责 FullTaskLoopResult → TaskExecutionResult 的转换和 workspace 检查，不直接调用 run_project_task_full。
- 外层 loop 不能假设内层一定 pass。必须处理 COMPLETE / REQUEST_CHANGES / BLOCKED / FAILED 四种 final_status。
- 无法确认 Claude Code 是否调用时必须标记 CLAUDE_CODE_CALLED=unknown。外层不能在 task_execution_performed=true 时标记 CLAUDE_CODE_CALLED=no。
- 直接函数调用（非 subprocess）更简单，避免进程开销和环境问题。后续如需隔离可再改为 subprocess。
- MVP 执行完一个任务后必须停止等待人工确认，不自动进入下一任务。
- TaskExecutionResult 和 ProjectLoopExecutionResult 是两层抽象：前者是外层视角的单任务结果，后者是整个 loop 的总结果。
- 安全输出字段必须覆盖所有场景：safety gate 拒绝时 / 执行成功时 / 执行失败时 / 执行异常时，每个场景都应明确每个字段的值。
- adapter 应先 dry-run 验证调用链路，再接入真实执行。先验证不真实执行的路径，再验证真实执行路径。

## T070-T076 Task Execution Bridge MVP 经验

### 核心经验

- adapter dry-run 和 real-call stub 是两个不同阶段：adapter 只验证数据结构和调用链路，real-call stub 验证完整调用构造（含 preflight_status、exit_code、check_result）。
- 从 execute stub 到真实调用必须经过 adapter → real-call stub → real-call bridge 三步，不能跳过中间层。
- CHECK_RESULT=pass 和 CHECK_RESULT=fail 后都必须停止，等待人工确认。MVP 阶段不自动进入下一任务。
- 真实调用前必须确认 run_project_task_full 的输出契约（FullTaskLoopResult 的 final_status、report_paths 等）。
- 安全输出字段必须覆盖所有场景：safety gate 拒绝 / adapter dry-run / real-call stub pass / real-call stub fail。
- CLAUDE_CODE_CALLED 使用字符串类型（"no"/"unknown"/"yes"），不是布尔。task_execution_performed=true 时必须标记 unknown。
- TaskExecutionResult（14 字段）、ProjectLoopExecutionResult（19 字段）、RealCallStubResult（19 字段）是三层抽象，各层职责不同。
- 分阶段验证策略有效：设计 → adapter dry-run → adapter 验证 → real-call stub → pass 验证 → fail 验证 → 小结。

## T077 Real Task Execution Safety Design 经验

### 核心经验

- 真实调用必须使用双重确认：EXECUTE_PROJECT_LOOP（进入 execute mode）+ EXECUTE_REAL_TASK_ONCE（允许真实调用），一层确认不够。
- 真实调用推荐复用已有 `run-project-loop` 命令加 `--real-call --real-confirm`，不新增独立命令。复用 planner / safety gate / max_tasks 限制。
- 真实调用推荐 Python 函数调用 `run_project_task_full()`，不是 subprocess。同进程直接获得 `FullTaskLoopResult`，无编码和环境问题。
- 无法确认 Claude Code 是否被调用时必须输出 unknown，不能写 no。unknown 代表信息不足，不是确认。
- 无法确认业务代码是否变化时也必须输出 unknown。
- 第一次真实调用 pass 后也必须停止等待人工验收。AUTO_CONTINUE_TO_NEXT_TASK=no 是 MVP 硬约束。
- workspace 变化检测应使用执行前后快照比较（git status --short），不是执行后单次检查。
- 验证应分两阶段：拒绝场景（不真实执行）先验证，真实执行场景后验证。

## T078 Real-Call Double-Confirm Safety Gate 实现经验

### 核心经验

- 双重确认安全门分层检查有效：execute safety gate → real_confirm 短语 → max_tasks → 模式互斥 → workspace → 全部通过。每一层独立拒绝，不跳过。
- RealCallSafetyResult 使用 20 个字段覆盖所有安全输出需求，与 RealCallStubResult 字段命名保持一致性。
- validate_real_call_safety() 复用 validate_execute_loop_safety() 作为第一重检查，避免重复实现。第二重检查（real_confirm + max_tasks + 模式互斥）是新增逻辑。
- CLI 层互斥检查和函数层互斥检查双重覆盖：CLI 先做参数互斥，函数再验证语义互斥。
- workspace dirty 时函数级验证可以覆盖大部分拒绝路径。clean workspace 下的完整 E2E 验证需要提交后做（T080）。
- 拒绝路径必须全部验证到 stop_reason，不能只看 check_result。不同拒绝原因对应不同 next_action。

## T077-T082 Real-call Safety MVP 经验

### 核心经验

- 双重确认是进入真实调用前的必要边界：EXECUTE_PROJECT_LOOP（execute mode）+ EXECUTE_REAL_TASK_ONCE（real-call），一层不够。
- real-call dry-run executor 不等于真实执行。它只构造 command/function_call 字符串，TASK_EXECUTION_PERFORMED 始终 False。
- pass 后必须停止，fail 后也必须停止。MVP 阶段无论结果如何都不自动进入下一任务。
- fail-stop 设计约束验证可以通过证据链推导：代码逻辑（return 终止）+ 设计规则（所有 fail 路径停止）+ pass-stop 推导（pass 已停止，fail 更不可能继续）。
- 从 execute stub 到真实调用应分步推进：safety gate → dry-run executor → 拒绝验证 → pass 验证 → fail 验证 → 小结，每步独立提交。
- 下一步真实调用前仍然需要单独设计实现协议（T084），不能直接跳到真实执行。

## T084 真实调用最小实现设计经验

### 核心经验

- 第一次真实调用必须 run-once：max_tasks=1，执行一次就停止，不自动继续。
- 子命令输出必须结构化：`FullTaskLoopResult` 已包含 final_status / steps / report_paths，直接函数调用比 subprocess 解析 stdout 更可靠。
- 无法确认字段必须用 unknown：真实执行后 CLAUDE_CODE_CALLED 和 BUSINESS_CODE_CHANGED 可能无法确认，必须输出 unknown 而不是 no。
- pass 后也不能自动继续：即使 final_status=COMPLETE，第一次真实调用也必须停止等待人工验收。
- 真实调用推荐 Python 函数调用而非 subprocess：已有稳定函数入口 `run_project_task_full()`，避免编码/路径/环境问题。
- 真实调用实现应分步推进：safety shell（拒绝场景）→ parser（解析逻辑）→ 拒绝验证 → pass 模拟 → fail 模拟 → 真实调用 → 真实验证 → 小结。
- workspace 变化检测应使用执行前后快照比较，不是执行后单次检查。

## T085 Real-Call Run-Once Safety Shell 实现经验

### 核心经验

- run-once safety shell 是真实调用前的最后一层安全外壳，只构造 command/function_call 但不执行，确保安全后才进入 T086 parser 和 T090 真实调用。
- RealCallRunOnceResult 字段应统一使用字符串类型（"no"/"false"/"true"），与 T079 RealCallDryRunExecutorResult 的布尔字段形成对比改进，便于后续统一输出。
- 模式互斥检查应在 CLI 层和函数层双重覆盖：CLI 层更早、更清晰，函数层在函数被其他入口调用时仍然有效。
- 复用 validate_real_call_safety() 可避免重复实现双重确认、max_tasks 检查和 workspace 检查。run-once safety shell 只需额外添加与其他模式的互斥检查。
- dirty workspace 下无法实测 pass 路径，可通过函数级验证确认数据结构和字段值。clean workspace 下的完整 E2E 验证留给 T087。

## T086 Child Command Parser Dry-Run 实现经验

### 核心经验

- KEY=value 格式解析应使用白名单机制（_PARSER_KNOWN_KEYS），只识别已知 key，避免解析无关行。
- 缺失必需字段（CHECK_RESULT）和缺失可选字段应分开处理：必需字段缺失 → parse_failed，可选字段缺失 → parsed_with_missing_fields + unknown 值。
- unknown 字段不能降级为 no。unknown 代表信息不足，no 代表确认未发生，语义不同。
- git status --short 输出行有前缀（如 `A  `、`M  `），分类变更时必须先剥离前 3 字符再检查文件路径。
- workspace 分类应区分 dirty_business_code（有 .html/.css/.js/.py 等变更）和 dirty_unexpected（有未知变更）和 dirty_expected（只有 reports/ docs/ 变更）。
- parser dry-run CLI 内置样例字符串是低风险、高效率的验证方式，适合在 dirty workspace 下验证解析逻辑。

## T090 Real-call Run-once MVP 小结经验

### 核心经验

- run-once safety shell 不等于真实执行。safety shell 只构造 command/function_call 字符串，RUN_PROJECT_TASK_FULL_CALLED 始终为 no。真实调用需要单独设计验收协议。
- child parser 只解决输出解析问题，不解决执行问题。parse_child_command_output() 可以正确解析 CHECK_RESULT=pass/fail，但 parser 本身不会触发任何执行。
- pass 后也必须停止。AUTO_CONTINUE_TO_NEXT_TASK 和 AUTO_GIT_BACKUP 在 continuous_task_planner.py 中硬编码为 false，这是 MVP 安全边界。
- fail 后也必须停止。四种 fail 类型（REQUEST_CHANGES/BLOCKED/FAILED/异常）都设计为停止并等待人工处理。
- 从 safety shell + parser dry-run 到真实执行之间，仍需要单独设计首次执行验收协议，确认环境、任务选择、预期结果和回退策略。
- 分步推进策略在 Stage 6 继续有效：设计 → safety shell → parser → 拒绝验证 → pass 模拟 → fail 模拟 → 小结，每步独立提交。

## T091 首次真实调用验收协议设计经验

### 核心经验

- 第一次真实调用 pass 后也必须人工验收。即使 final_status=COMPLETE，也需要通过 10 项验收清单逐项确认，不能自动进入下一任务。
- unknown 字段不能写成 no。CLAUDE_CODE_CALLED=unknown 代表信息不足，CLAUDE_CODE_CALLED=no 代表确认未调用，两者语义完全不同。unknown 时必须设置 HUMAN_REVIEW_REQUIRED=true 和 AUTO_CONTINUE_TO_NEXT_TASK=false。
- 首次真实调用后不能自动 Git backup。workspace 变化需要人工分类（reports only vs business code），报告和代码是否一起提交需要人工决定。
- 验收状态分为 4 种：ready_for_human_review（可验收）、blocked（有问题需处理）、failed_to_parse（结果无法解析）、unsafe_to_continue（不安全）。unknown 字段不阻塞验收，只降级为 ready_for_human_review。
- 5 小时限额恢复机制是未来需求。checkpoint、run state 持久化、reset time 检测、resume_allowed 判断和恢复后自动继续，等首次真实调用跑通后单独设计。
- 首次真实调用使用 Python 函数调用（非 subprocess），无 exit_code 和 stdout/stderr，需要用 FullTaskLoopResult.final_status 判断结果。

## T095 首次真实执行开关设计经验

### 核心经验

- 真实执行需要三重确认：EXECUTE_PROJECT_LOOP（第一重）+ EXECUTE_REAL_TASK_ONCE（第二重）+ EXECUTE_REAL_RUN_ONCE（第三重）。双重确认用于 safety shell，三重确认才允许真实执行。
- `--real-call-run-once` 不是执行开关，只进入 safety shell。`--real-execute-once` 才是执行请求，配合 `--real-execute-confirm EXECUTE_REAL_RUN_ONCE` 才允许真实执行。
- 三个确认短语不能互相替代：EXECUTE_PROJECT_LOOP 只能用于 --confirm，EXECUTE_REAL_TASK_ONCE 只能用于 --real-confirm，EXECUTE_REAL_RUN_ONCE 只能用于 --real-execute-confirm。
- API 429 / 5 小时限制当前阶段只 stop and report，不自动恢复。checkpoint / resume 等能力等首次真实调用跑通后单独设计。
- 首次真实执行后无论 pass/fail 都不自动继续、不自动 Git backup、不自动返工，必须等待人工验收。

## T100 第一次真实 run-project-task-full 调用经验

### 核心经验

- `run_project_task_full()` → `run_developer_step()` → `run_project_next()` → `run_claude_code()` → subprocess 链路已验证可达。第一次真实调用证明端到端链路正确。
- Claude Code subprocess 超时（600 秒）后系统正确 BLOCKED：returncode=124, Developer 阶段停止，Tester/Reviewer/Decision 未启动。
- 真实执行后必须人工验收。T100 的 10 项验收清单全部 PASS，但 child execution 超时，整体判定为 review_required。
- 首次真实执行任务不宜为框架级任务。T100 要求"解除 simulated，连接真实 run_project_task_full()"，属于框架开发任务，不适合作为首次验证。
- Prompt 存在矛盾会导致超时。T100 的 prompt 要求修改框架代码但禁止修改列表包含 runner.py 和 tools/*.py，Claude Code 因矛盾指令卡住。
- 600 秒 timeout 对复杂任务不足。`CLAUDE_CODE_TIMEOUT_SECONDS=600` 是硬编码值，复杂框架任务需要更长时间，但不应盲目增加。
- 下一步应使用更小的 smoke task 验证完整闭环。降低任务复杂度，验证一次可完成的真实调用。

## T101 人工验收第一次真实调用结果经验

### 核心经验

- 人工验收是真实执行后不可跳过的环节。10 项验收清单覆盖了只执行一次、正确 task_id、Claude Code 启动、正确捕获结果、停止后续阶段、不自动继续、不自动 backup、不修改业务代码、变更可解释、策略调整。
- 验收通过不等于任务 pass。T100 验收清单 10/10 PASS，但 child execution 超时，最终判定 review_required。
- 变更文件检查是安全验收的核心。必须确认无 runner.py、tools/*.py、projects/**、业务代码变更，所有变更必须在预期路径内。
- 验收应包含下一步策略建议。比较多个方案并给出推荐，帮助决策者快速行动。
- 推荐策略：新增更小的 smoke task 验证首次完整闭环，而非增加 timeout 或改进框架。

## T102 first real-run smoke test 经验

### 核心经验

- G008 是极小 smoke task（只创建一个 marker 文件），prompt 无歧义，但仍然 600 秒超时。这说明问题不在任务复杂度或 prompt 矛盾。
- T100（框架级任务，矛盾 prompt）和 G008（极小任务，清晰 prompt）都超时，说明根因在 Claude Code CLI / 模型 API / 网络 / subprocess 执行链路。
- 后续不要继续盲目重跑真实任务，应先进行 Claude Code 连接诊断（T103）。
- Claude Code 通过 `echo hello | claude --print` 方式可以秒级响应，但通过 subprocess 传递长 prompt 参数时可能行为不同。需要对比两种调用方式。
- Safety gate 机制在 dirty workspace 下正确阻止执行。通过 stash → gate → pop 流程可以临时绕过，但需注意执行后恢复。

## T103 Claude Code + 智谱代理超时诊断经验

### 核心经验

- **acceptEdits + tool use 是超时的根因。** `claude --print "OK"` 秒级返回，`claude --acceptEdits --print "OK"` 秒级返回，但 `claude --acceptEdits --print "创建文件..."` 120 秒无响应。
- 默认模式下请求工具调用（如创建文件），权限被拒绝后能正常返回。但在 acceptEdits 模式下，工具被实际执行后，需要将 tool_result 发回 API 等待下一轮响应，此时卡住。
- **诊断分类 C：CLI 正常、文本正常、acceptEdits 文本正常，但 acceptEdits + tool use 超时。** 这说明问题出在智谱 API 对 Claude Code tool_result 消息的兼容性上。
- 当前使用智谱云端直连（`open.bigmodel.cn/api/anthropic`），不是本地代理。ANHTROPIC_MODEL=glm-5.1。
- 后续必须先验证最小 tool use 测试，再验证 acceptEdits，再恢复 run-project-task-full。不要继续盲目重跑真实任务。
- 修复方向包括：更换权限模式、调整调用参数、检查智谱 API tool use 兼容性、更换模型或代理。

## T104 Claude Code + 智谱代理 tool-use 兼容性修复方案设计经验

### 核心经验

- **修复方案设计应先比较多个方向，再选择最小可行方案。** T104 比较了 6 个候选方案（A-F），推荐短期 B+A（可配置 permission mode + 诊断验证），中期 D（评估智谱 API 兼容性），长期 E（runner 自执行 patch）。
- **短期不要继续真实任务执行。** 应先让 run_claude_code 的 permission mode 可配置，再验证 default/acceptEdits/bypass 等模式在不同环境下的行为。
- **方案 B（可配置 permission mode）是当前最小改动方向。** 只需修改 run_claude_code() 函数签名和调用方，不改变默认行为，风险低。
- **方案 A（去掉 acceptEdits）只能作为诊断手段。** 默认模式下 Claude Code 无法自动写文件，不符合最终自动化目标。
- **方案 D（评估智谱 API 兼容性）是中期关键任务。** 需要确认智谱 API 是否支持 Anthropic tool_use/tool_result，如果不支持则需要选择替代路线。
- **方案 E（runner 自执行 patch）是长期方向。** 绕开 Claude Code tool-use，让 runner 自己应用模型生成的 patch，更适合国内模型 API。
- **方案 F（切换官方 Claude）是备用方案。** 兼容性最好但有成本和网络限制。
- **修复验证应分层：最小 tool use 测试 → acceptEdits 测试 → G008 smoke test → 完整闭环。** 不要跳步。

## T105 configurable Claude permission mode 设计经验

### 核心经验

- **permission mode 必须可配置。** 当前 `run_claude_code()` 在 `tools/claude_code_runner.py:39` 硬编码 `--permission-mode acceptEdits`，无法切换到 default 或其他模式。
- **短期采用底层函数参数 + CLI 参数方案（D+A）。** 先改 `run_claude_code()` 签名增加 `permission_mode` 参数，再在 `runner.py` 增加 `--claude-permission-mode` CLI 参数。
- **默认值先保持 acceptEdits 以兼容历史行为。** 不传参时行为与改动前完全一致，避免破坏已有逻辑。真实任务诊断时显式传 `default`。
- **配置优先级：CLI 参数 > 环境变量 > 项目配置 > 内置默认值。** CLI 参数最显式应优先级最高，环境变量适合本地长期配置，项目配置适合多项目场景。
- **调用链需要全链路透传：** runner.py → project_runner.py → claude_code_runner.py，每个环节都需要接收和传递 permission_mode。
- **支持 4 种模式：default / none / acceptEdits / bypassPermissions。** default 和 none 等价（不传 --permission-mode），bypassPermissions 标记为 high-risk。
- **default mode 下 Claude Code 无法自动写文件。** 工具调用会被权限拒绝，只能输出建议代码。这符合当前诊断需求，但不适合无人值守自动化。
- **20 个验证场景覆盖默认行为、显式传参、非法值、优先级和安全约束。**

### T106 实现 permission mode 可配置经验

- **默认值必须保持 acceptEdits 以兼容历史行为。** 所有历史调用都不传参，默认 acceptEdits 保证行为不变。`_execute_one_task()`、`run_project_next()`、`run_project_task_full()` 的默认值也必须是 acceptEdits。
- **default / none 只是不传 --permission-mode，不代表修复 tool-use。** default mode 下 Claude Code 无法自动写文件，工具调用被权限拒绝。真实任务恢复前必须先做最小 Claude Code 调用验证（T107）。
- **全链路透传需要同步修改 4 个文件：** claude_code_runner.py（底层函数）→ project_runner.py（透传）→ full_task_runner.py（透传）→ runner.py（CLI 解析）。
- **CLI 参数解析和 mode 校验不能用 lower() 统一小写。** acceptEdits 本身是 mixed-case，`"acceptEdits".lower()` → `"acceptedits"`，与 valid_modes 不匹配。应保持原始值比较。
- **dry-run 命令是安全验证的最佳方式。** `claude-permission-mode-dry-run` 只输出参数映射，不调用 Claude Code，可以安全验证所有 mode 的正确性。

### T107 验证 default mode 最小文本调用经验

- **default mode 最小文本调用正常返回。** `claude --print "只回复 OK"` 在不传 `--permission-mode` 时秒级返回 "OK"，确认 default mode 文本输出链路正常。
- **default/none 模式不传 --permission-mode，可作为 acceptEdits tool-use 卡死问题的安全对照。** T103 已确认 acceptEdits + tool-use 超时，而 default mode 文本调用正常，两者对比说明问题在 acceptEdits 的 tool-use 路径上。
- **只允许做只读文本测试，不允许写文件 tool-use。** T107 只验证最小文本返回，写文件测试留给后续任务。
- **dry-run 映射验证是调用 Claude Code 前的必要前置检查。** 4/4 dry-run 通过后才执行最小 Claude Code 调用。
