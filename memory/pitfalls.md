# Pitfalls

## 第一阶段踩坑记录

1. **不要在 Claude Code 会话内运行会再次调用 Claude Code 的命令。** 例如 `run-current`、`run-next`、`retry-current`、`run-loop`。这些命令会内部调用 Claude Code CLI，导致嵌套调用和长时间卡住。真实验收必须在普通 PowerShell 中执行。

2. **Windows 下 subprocess 读取 Claude Code 输出时要指定 `encoding="utf-8", errors="replace"`。** 默认使用 gbk 编码，Claude Code 输出包含中文字符时会导致 `UnicodeDecodeError`。

3. **PowerShell 查看 UTF-8 中文文件时要使用 `-Encoding UTF8`。** 直接 `cat` 或 `Get-Content` 可能显示乱码。

4. **Windows 下 Claude Code 可能需要 `CLAUDE_CODE_GIT_BASH_PATH`。** 如果 Claude Code CLI 报错找不到 bash，需要设置环境变量指向 git-bash 路径。

5. **Claude Code 非交互调用如果没有 `--permission-mode acceptEdits`，可能不会自动写文件。** 默认模式下 Claude Code 只输出建议代码，不会实际修改文件。

6. **不能只根据 Claude Code 退出码判断任务完成。** 退出码 0 只代表 Claude Code 进程正常结束，不代表它完成了预期工作（例如生成开发报告）。

7. **429 使用限额要被识别，并停止继续自动调用。** `analyze_claude_output` 要检测 stderr 中的 429 错误，避免在限额状态下继续自动调用导致浪费时间。检测范围应限定在 Stderr 段，避免 Stdout 中的代码内容误匹配。

## T020.1 子项目自动执行注意事项

1. **不要一开始把验证项目做复杂。** 先从最小页面开始，逐步增加能力。
2. **子项目任务应使用独立任务编号。** 例如 G001、G002，与主项目 T 编号区分。
3. **主项目任务和子项目任务不能混淆。** 主项目 tasks.md 用 T 前缀，子项目用 G 前缀。
4. **run-game-next 当前只服务 down-100-floors-game。** 不要误认为已经是通用多项目系统。
5. **子项目自动完成仍然必须依赖完成证据。** 例如 `projects/down-100-floors-game/reports/dev/G002-dev-report.md`。
6. **如果子项目任务执行成功但缺少完成证据，不能自动标记 done。** 与主项目规则一致。
7. **验证项目发现的框架问题，应记录到主项目 memory/。** 不要只留在子项目里。

## T022 第二阶段踩坑记录

1. **不要在协议还没稳定时直接做复杂平台功能。** 先把核心协议跑通，再考虑平台适配。
2. **不要一开始就接多个真实模型。** 先把一个模型跑通，再逐步扩展。
3. **不要把 mock 审查结果当成真实质量结论。** mock 只验证链路，不验证质量。
4. **不要把 down-100-floors-game 当成主项目。** 它只是验证项目。
5. **不要在 Web MVP 阶段提前做微信小游戏 / 抖音小游戏适配。** 等核心能力稳定后再适配。
6. **不要在第一版游戏中提前做角色技能和真实人物形象。** 等基础玩法完成后再引入。
7. **不要把 run-game-next 误认为已经是通用多项目执行器。** 它当前只服务 down-100-floors-game。

## T023 第三阶段规划避坑

1. **不要直接把 `run-game-next` 扩展成复杂平台，应先设计通用 project runner 协议。** 协议先行是第二阶段验证过的有效策略。
2. **不要一开始接多个真实模型，Reviewer 先接一个即可。** 多模型同时接入增加调试复杂度，一个跑通再扩展。
3. **不要把真实模型审查结果直接用于自动返工，先人工观察。** 真实模型输出格式可能不稳定，需要先验证解析可靠性。
4. **不要一开始做微信小游戏 / 抖音小游戏发布。** 等 Web MVP 核心能力稳定后再适配。
5. **不要提前实现角色技能系统。** 等基础玩法完成后再引入。
6. **不要把第三阶段变成"完整做游戏"，重点仍是验证框架自动化能力。** G003 只做玩家显示和移动。

## T024 Project Runner 协议设计避坑

1. **不要直接把 `run-game-next` 硬改成复杂通用逻辑，先设计协议。** 协议设计完成后再做最小实现。
2. **不要让子项目任务拥有无限文件修改权限。** 通过 allowed_files / blocked_files 控制。
3. **不要把子项目的 `docs/tasks.md` 和主项目的 `docs/tasks.md` 混用。** 路径隔离是基本原则。
4. **不要只用 returncode 判断子项目任务完成。** 必须检查完成证据文件。
5. **不要在 Claude Code 会话里执行会再次调用 Claude Code 的通用 project runner 命令。** 嵌套调用会卡住。

## T025.1 通用 project runner 注意事项

1. **不要把 `run-project-next` 一次性扩展成复杂平台。** 当前是 MVP，验证一个项目后逐步扩展。
2. **不要让子项目任务拥有无限文件修改权限。** prompt 中必须明确允许和禁止范围。
3. **不要混淆主项目 `docs/tasks.md` 和子项目 `docs/tasks.md`。** 路径隔离是基本原则。
4. **不要只根据 `returncode=0` 判断子项目任务完成。** 必须检查完成证据文件。
5. **子项目完成证据必须使用 `<project>/reports/dev/<task-id>-dev-report.md`。** 路径从项目根动态计算。
6. **通用 runner 验证要先从已知项目开始。** 例如 `down-100-floors-game`，不要一上来测试未知项目。
7. **不要在 Claude Code 会话内执行 `run-project-next`。** 嵌套调用会卡住。

## T028.1 DeepSeek Reviewer 真实审查注意事项

1. **不要把真实 Reviewer 模型的单次 PASS 直接视为最终质量保证。** 单次审查通过只说明当前任务边界内的验收标准满足，不代表整体质量。
2. **不要在没有 Tester Agent 的情况下直接进入自动返工闭环。** 综合决策需要 Developer / Tester / Reviewer 三方结果。
3. **不要让 Reviewer 自动修改代码，Reviewer 只给审查结论。** 审查和修改必须分离。
4. **不要把 DeepSeek API Key 写入代码或配置文件。** Key 只从环境变量读取。
5. **不要删除 mock provider，真实模型不可用时仍需回退或明确报错。** mock 是开发和调试的重要回退手段。
6. **不要只保存自然语言审查报告，必须保留结构化 `Machine Readable Result`。** 后续 Main Agent 只消费结构化结果。
7. **不要跳过人工观察阶段，真实 Reviewer 接入初期需要持续评估审查质量。** 模型输出格式可能不稳定。

## T029 Tester Agent 协议设计避坑

1. **不要一开始做复杂端到端测试。** 先做本地静态检查，后续再引入浏览器自动化。
2. **不要让 Tester Agent 修改业务代码。** Tester 只读不写，结果通过报告传递。
3. **不要把 Reviewer 审查当成 Tester 测试。** 审查是代码质量评估，测试是验收标准验证，两者职责不同。
4. **不要跳过测试报告完成证据。** 测试报告是 Main Agent 综合决策的输入之一。
5. **不要在 Web MVP 阶段测试微信小游戏或抖音小游戏平台能力。** 当前只测 Web MVP。
6. **不要测试尚未实现的游戏物理逻辑，例如重力、平台、碰撞。** 静态检查只验证当前任务边界。

## T031.1 三方证据链与综合决策避坑

1. **不要只凭 Developer 报告判定任务完成。** 必须有 Tester 和 Reviewer 的独立验证。
2. **不要把 Tester PASS 和 Reviewer APPROVE 混为一谈。** Tester 验证事实（元素是否存在），Reviewer 判断质量（是否符合需求和边界）。
3. **不要让 Main Agent 直接修改业务代码。** Main Agent 只做综合判断，不参与具体实现。
4. **不要在 Reviewer 或 Tester 缺失时直接 COMPLETE。** 三方证据缺一不可。
5. **不要在 Main Decision 阶段自动返工，初期应先人工观察。** 综合决策先输出建议，不直接触发返工。
6. **不要把单个任务的 COMPLETE 误认为整个项目完成。** COMPLETE 只代表当前任务闭环通过。
7. **不要跳过最终综合决策报告，报告是后续追溯的重要证据。** 综合决策报告应与开发、测试、审查报告一起保存。

## T032.1 G004 完整闭环注意事项

1. **不要把 G004 的 COMPLETE 误认为游戏玩法完整。** G004 只实现了左右移动，游戏还需要重力、平台、碰撞等核心玩法。
2. **当前 Tester 仍以静态检查为主，尚不能完全替代真实交互测试。** 键盘移动行为需要在浏览器中人工验证。
3. **后续如果继续做重力、平台、碰撞，需要增强 Tester 测试能力。** 静态检查无法验证动态行为。
4. **不要在 G004 阶段提前引入角色技能系统。** 角色系统是后续长期目标。
5. **不要提前进入微信小游戏 / 抖音小游戏适配。** 当前只做 Web MVP。
6. **不要跳过 Reviewer 和 Main Decision，尤其是功能开始复杂后。** 多方验证的价值随复杂度增加而提升。

## T033 第三阶段踩坑记录

### 注意事项

- 不要把静态测试结果当成完整交互测试结果。
- 不要在没有行为测试能力前快速推进复杂玩法。
- 不要让 Reviewer 替代 Tester，二者职责不同。
- 不要让 Main Agent 跳过证据链直接 COMPLETE。
- 不要一次性实现平台、重力、碰撞、角色技能等多个能力。
- 不要在 Web MVP 未稳定时进入微信小游戏 / 抖音小游戏适配。
- 不要忘记重要节点 Git 备份。

## T035 Tester 行为检查协议设计避坑

- 不要把 G004 的基础静态测试 PASS 当成完整交互测试 PASS。
- 不要一开始引入复杂浏览器自动化，先用源码静态检查补强。
- 不要让行为检查修改业务代码。
- 不要把基础测试报告和行为测试报告混在一个文件里。
- 不要跳过边界限制检查，玩家移动最容易出现越界问题。

## T040 自动返工协议设计避坑

- 不要在 Tester 或 Reviewer 失败后立即自动修改代码。
- 不要让返工任务扩大原始需求范围。
- 不要覆盖原始开发报告，返工报告应单独保存。
- 不要跳过返工后的测试和审查。
- 不要在环境问题或 API 限额问题上生成代码返工任务。
- 不要让返工任务修改 project.yaml 或主框架文件。

## T043.2 G005 Developer 特殊完成避坑

### 避坑记录

1. 不要看到 `returncode=1` 就立即判定任务失败。
2. 不要在完成证据已经存在时盲目重新执行同一个任务。
3. 不要忽略 `G005-dev-report.md` 和子项目任务状态。
4. 不要在 API 429 限额期间反复调用 Claude Code。
5. 不要把"模型返回错误"与"业务代码未完成"混为一谈。
6. 遇到状态冲突时，应先检查报告、任务状态和实际文件改动。
7. T043.0 修复的超时处理和 T043.1 修复的证据冲突判断，避免了未来同类问题。

## T044.4 G005 完整闭环注意事项

### 避坑记录

1. 不要把基础平台显示和重力、碰撞、平台滚动放在同一任务中。
2. 不要在 Claude Code 返回 429 后盲目重复执行同一任务。
3. 不要只看 returncode，要结合开发报告、任务状态和实际文件改动判断。
4. 不要跳过 Tester / Reviewer / Main Agent 证据链。
5. 不要在 Web MVP 未稳定前进入微信小游戏 / 抖音小游戏适配。
6. 不要在 G005 阶段引入角色技能系统。

## T045 第四阶段踩坑总结

### 注意事项

- 不要把静态检查误认为完整交互测试。
- 不要在没有次数限制的情况下设计自动返工。
- 不要在 Claude Code 返回错误时立刻重复执行任务。
- 不要只看 returncode，要结合完成证据、任务状态和实际文件改动。
- 不要把平台显示、重力、碰撞、滚动合并到一个任务。
- 不要在 Web MVP 未稳定时进入微信小游戏 / 抖音小游戏适配。
- 不要在没有人工确认机制前启用完全自动返工。

## T046 第五阶段规划避坑

- 不要因为 G005 完成就一次性实现重力、碰撞、失败条件。
- 不要在没有重力测试协议前实现 G006。
- 不要在没有碰撞测试协议前实现 G007。
- 不要让自动返工绕过用户确认。
- 不要超过最大返工次数限制。
- 不要在 Web MVP 未稳定前进入微信小游戏 / 抖音小游戏适配。
- 不要把静态测试结果当成物理逻辑的完整验证。
- 不要在 prompt 中省略已有代码上下文，重力和碰撞需要准确坐标信息。

## T047 重力下落测试协议设计避坑

- 不要在 G006 中同时实现碰撞检测。
- 不要在 G006 中实现平台滚动。
- 不要在 G006 中实现游戏失败条件。
- 不要只靠 Reviewer 判断重力是否正确，Tester 需要有专门检查项。
- 不要一开始引入复杂物理系统。
- 不要跳过范围控制检查，S 组检查防止越界实现。
- 不要把重力检查报告和基础静态检查报告混在一个文件里。
- 不要在重力测试中引入浏览器自动化，先从源码静态检查开始。

## T049.0 单任务完整闭环自动化设计避坑

- 不要误以为单个 Agent 能自动执行就等于全自动。
- 不要让 full loop 在 Tester FAIL 后继续 Reviewer。
- 不要在 Reviewer 429 或 Claude Code 超时时自动重试。
- 不要跳过 Main Agent 综合决策。
- 不要让返工自动无限循环。
- 不要在没有 full task loop 的情况下直接做项目级 run-loop。
- 不要让 full loop 自动执行 git push、文件删除等高风险操作。
- 不要忽略命令权限策略，自动化必须有安全边界。

## T049.3 run-project-task-full 首次验证避坑

- 不要把 Reviewer BLOCKED 当作业务代码失败。
- 缺少 `DEEPSEEK_API_KEY` 属于环境配置问题。
- `.env` 必须确认被 `.gitignore` 忽略，避免泄露 API Key。
- full loop 被阻塞后，不应盲目重新执行 Developer。
- 当前 full loop 还没有 resume 机制，后续需要支持从 Reviewer 阶段恢复。
- Specialized Tester 当前对 G006 仍为 SKIPPED，后续 T050 需要补 gravity tester。

## T050.2 G006 与 .env 自动加载避坑

- 不要提交 `.env` 到 GitHub。
- 不要在日志中打印真实 API Key。
- 不要把 `.env` 加载失败误判为业务代码失败。
- 不要在 Reviewer 缺少 API Key 时继续 Main Decision。
- 不要重复执行已经完成的 G006 Developer 阶段。
- 不要把 G006 的重力下落与平台碰撞混在一起。
- `.env` 自动加载后仍需要检查 `DEEPSEEK_API_KEY` 是否真实可用。

## T050.3a Claude Code 命令权限避坑

- 不要为了省事开启无边界自动执行。
- 不要把 Git 备份权限扩展到普通开发任务。
- 不要让 Claude Code 自动执行 `git reset --hard` 或 `git clean -fd`。
- 不要让 Claude Code 打印 `.env` 内容。
- 不要把 `.env` 加入 Git。
- 不要把删除文件命令加入低风险白名单。
- 不要跳过提交前的 `git status --short` 检查。

## T051 碰撞检测测试协议设计避坑

- 不要在 G007 中同时实现平台滚动。
- 不要在 G007 中实现随机平台生成。
- 不要在 G007 中实现游戏失败条件。
- 不要只检测 y 坐标，不检测水平范围重叠。
- 不要忽略从上方落下这一条件，否则可能出现侧面或底部误判。
- 不要在没有专项 Tester 的情况下只依赖 Reviewer 判断碰撞是否正确。
- 不要在碰撞检查中引入浏览器自动化，先从源码静态检查开始。
- 不要把碰撞检查报告和基础静态检查报告混在一个文件里。

## T051.1 Bash / PowerShell 命令差异避坑

- 不要在 `Bash(...)` 中使用 `Test-Path`。
- 不要在 `Bash(...)` 中使用 `Get-Content`。
- 不要在 `Bash(...)` 中使用 `Select-String`。
- 不要把 PowerShell 命令加入 Bash 白名单。
- 自动验收命令应优先使用 Bash 兼容写法。

## T053.4 G007 完整闭环避坑

- 不要在 Collision Tester FAIL 后直接判定 Developer 失败，应先判断是否为 Tester 误判。
- 不要为了让测试通过而放宽范围限制检查。
- 不要在 G007 中同时加入平台滚动、随机平台或失败条件。
- 不要跳过 Collision Tester 直接进入 Reviewer。
- 不要重复执行已经完成的 Developer 阶段。
- Reviewer API 超时后可以重试一次，但如果持续超时应停止并报告。

## T054 G007 冗余任务关闭避坑

- 不要因为任务列表里还有 T054 pending，就重复执行已经完成的 G007 Reviewer / Main Decision。
- 不要重复执行已经完成的 G007 Developer。
- 不要在证据链完整时再次调用 DeepSeek，避免浪费 API 和引入不一致结果。
- 对于已由子任务完成的目标，应创建关闭记录，而不是重复执行。

## T055 自动返工执行避坑

- 不要把网络错误、API Key 缺失、API 429 误判为代码返工。这些属于环境阻塞，应进入 BLOCKED。
- 不要在未确认时执行返工。REWORK_CANDIDATE 不等于返工执行。
- 不要接受"继续""可以""你看着办"作为返工确认。必须使用严格格式。
- 不要超过 3 次返工。R4+ 必须生成人工介入报告。
- 不要让返工命令进入全局 allowlist。返工是 C 类命令。
- 不要在返工中修改禁止文件（project.yaml、主框架代码、.env）。
- 不要在返工执行前跳过前置检查（6 项全部通过才能执行）。
- 不要覆盖原始报告，返工报告应单独保存。

## T055.3 Git 复合命令避坑

- 不要把 `cd && git ...` 加入 allowlist。
- 不要把多个 Git 写入命令合并成一行执行。
- 不要在未确认当前目录时执行 `git add` / `git commit` / `git push`。
- 不要为了减少确认次数而放开复合命令。
- Git 备份任务应逐条执行，便于定位失败点和控制风险。

## T056 execute-rework MVP 避坑

- 不要在 MVP 中直接调用 Claude Code 执行返工。
- 不要把 `execute-rework` 加入全局自动执行白名单。
- 不要接受模糊确认语句（"继续""可以""试一下"等）。
- 不要超过 3 轮返工。R4+ 必须进入人工介入。
- 不要把环境错误（API Key 缺失、429）误判为代码返工。
- 不要跳过 rework prompt 存在性检查。

## T056.2 confirmed rework execution stub 避坑

- 不要在 confirmed stub 中设置 real_execution_performed=true。
- 不要让 --real-execution 绕过 dry-run 的任何安全检查。
- 不要把 confirmed stub 的 execution_allowed=true 误认为真实执行已发生。

## T056.5 full loop resume stub 避坑

- 不要让 --resume 单独使用，必须配合 --real-execution 和 --confirm。
- 不要在 resume stub 中自动执行下一个 pending task。
- 不要把 resume_allowed=true 误认为连续任务自动推进已实现。
- 不要让 resume 绕过 execute-rework 的任何安全检查。

## T057 第五阶段避坑总结

- 不要在 Tester FAIL 后继续 Reviewer，应立即停止闭环。
- 不要把环境阻塞（API Key 缺失、429）误判为代码返工。
- 不要在未确认时执行返工，REWORK_CANDIDATE 不等于返工执行。
- 不要把静态检查结果当成物理逻辑的完整验证。
- 不要在第六阶段直接实现无人值守循环，应先设计连续推进协议。

## T058-T062 第六阶段 MVP 避坑

- 不要把 dry-run 输出误认为真实自动化。dry-run 只模拟推进，不执行任何任务。
- 不要让 --execute 在未设计安全协议前可用。T060 明确拒绝 --execute。
- 不要把 LOOP_STATUS=dry_run_completed 和 stopped_on_max_tasks 混淆。前者是自然结束，后者是达到上限截断。
- 不要在 planner 和 loop 中重复实现任务读取逻辑，应复用 task_manager。
- 不要在验证任务中修改代码文件，验证只运行命令和记录结果。
- 不要跳过 max_tasks=0 和 max_tasks>10 的边界测试，这些是安全边界。
- 不要把 NEXT_TASK=NONE 误认为系统错误，可能只是所有 pending 任务都已 planned。
