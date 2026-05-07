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

## T064 Execute Mode 安全设计避坑

- 不要把 dry-run 的安全假设直接用于 execute mode，execute 需要独立的前置检查和停止条件。
- 不要让 execute mode 复用 dry-run 的 max_tasks 硬限制（10），execute 应该更低（3）。
- 不要把 dry-run 成功视为 execute 安全的充分条件，dry-run 不执行任务。
- 不要接受模糊确认（yes/ok/确认/同意），execute 确认必须精确匹配 EXECUTE_PROJECT_LOOP。
- 不要在 execute mode 中自动执行 execute-rework，rework 需要人工确认。
- 不要在 execute mode 中自动 git push，push 需要人工确认。
- 不要在 execute mode MVP 中允许 max_tasks > 1，MVP 先验证单任务执行。
- 不要让 --execute 和 --dry-run 同时传入，两者互斥。

## T065-T069 Execute Safety MVP 避坑

- 不要把 EXECUTE_STUB_STARTED=true 误认为真实执行已发生。stub 只是模拟，TASK_EXECUTION_PERFORMED 始终为 false。
- 不要把 safety gate 通过（EXECUTE_ALLOWED=true）等同于可以执行。safety gate 通过后还有 stub 层的 max_tasks 检查。
- 不要在 dirty workspace 下验证 max_tasks=1 stub 启动场景。dirty workspace 会先被 safety gate 拒绝，无法触达 stub 逻辑。
- 不要跳过 confirm 拒绝场景的单独验证。代码审查不能替代运行时验证，尤其是 confirm 值的边界。
- 不要把 NEXT_ACTION=ready_for_T067_validation 误认为系统建议重做 T067。这是 T066 实现时的遗留命名。
- 不要在 execute mode 验证中修改代码文件。验证任务只运行命令和记录结果。

## T070 Task Execution Bridge 设计避坑

- 不要在 task_execution_performed=true 时标记 CLAUDE_CODE_CALLED=no。外层无法精确判断 Claude Code 是否被调用，必须标记 unknown。
- 不要假设 run_project_task_full 一定返回 COMPLETE。四种 final_status（COMPLETE/REQUEST_CHANGES/BLOCKED/FAILED）每种都要处理。
- 不要在 MVP 阶段自动进入下一个任务。max_tasks=1 执行完后必须停止等待人工确认。
- 不要用 subprocess 调用 run_project_task_full。当前是同进程函数调用，subprocess 会增加不必要的复杂度。
- 不要跳过 adapter dry-run 阶段。从 stub 直接跳到真实执行，中间缺少 adapter 验证会导致问题难以定位。
- 不要忽略执行后的 workspace 检查。真实执行可能修改文件，必须检查是否有非预期变更（尤其是框架代码）。
- 不要在 CLAUDE_CODE_CALLED=unknown 时偷偷改成 no。unknown 就是 unknown，代表信息不足。

## T071-T075 Task Execution Bridge 实现避坑

- 不要把 adapter dry-run 和 real-call stub 混为一谈。adapter 只构造调用信息，real-call stub 进入完整调用占位流程。
- 不要在 real-call stub 中设置 task_execution_performed=true。stub 只是占位，不执行任何真实操作。
- 不要假设 CHECK_RESULT 只有 pass。所有 fail 路径也必须验证（safety gate 拒绝、max_tasks 错误、无 planned task）。
- 不要在 fail 路径中继续执行。所有 fail 路径必须通过 return 终止函数。
- 不要把 NEXT_ACTION=ready_for_T07x_validation 误认为系统建议重做该任务。这是实现时的遗留命名。
- 不要跳过 adapter dry-run 阶段直接实现 real-call stub。中间缺少验证会导致问题难以定位。
- 不要在验证任务中修改代码文件。验证只运行命令和记录结果。

## T077 Real Task Execution Safety Design 避坑

- 不要只用 EXECUTE_PROJECT_LOOP 一层确认就允许真实调用。stub 也需要这个确认，无法区分 stub 和真实执行。
- 不要在 CLAUDE_CODE_CALLED 无法确认时输出 no。no 代表确认未调用，unknown 代表无法确认，两者含义不同。
- 不要在 BUSINESS_CODE_CHANGED 无法分类时输出 no。同上。
- 不要用 subprocess 调用 run_project_task_full。已有稳定函数入口，subprocess 增加编码/环境/路径问题。
- 不要在第一次真实调用 pass 后自动进入下一任务。必须人工验收。
- 不要把验证场景 11-18（真实执行）和场景 1-10（拒绝）混在一起。拒绝场景不需要真实调用，可以安全先做。
- 不要新增独立命令（如 run-project-loop-real-once），应复用已有 run-project-loop 加参数。独立命令会绕过 planner / safety gate / max_tasks 限制。

## T078 Real-Call Double-Confirm Safety Gate 避坑

- 不要把 RealCallSafetyResult 和 RealCallExecuteResult 混为一谈。Safety gate 只做前置检查，不执行任何真实操作。Execute result 才是 T079 的内容。
- 不要在 validate_real_call_safety() 中跳过 execute safety gate 直接检查 real_confirm。两层检查是分层设计，第一层不通过就不应进入第二层。
- 不要在 workspace dirty 时期望能验证 real_confirm 拒绝路径。dirty workspace 会被 execute safety gate 先拦截，需要在 clean workspace 下验证（T080）。
- 不要把 CLI 层互斥检查和函数层互斥检查当作重复逻辑。CLI 层做参数级互斥（更早、更清晰的错误提示），函数层做语义级互斥（函数被其他入口调用时仍然有效）。

## T077-T082 Real-call Safety MVP 避坑

- 不要把 real-call dry-run executor 的 CHECK_RESULT=pass 误认为真实执行成功。dry-run executor 不执行任务，pass 只代表 safety gate 通过和 command 构造成功。
- 不要跳过 fail-stop 设计约束验证。即使当前 dry-run executor 不产生真实 fail，也要通过代码逻辑和设计规则验证所有 fail 路径都正确停止。
- 不要在下一步直接实现真实调用。从 dry-run executor 到真实执行之间需要单独设计实现协议（RealCallExecuteResult、workspace 变化检测、CLAUDE_CODE_CALLED 推断等）。
- 不要把 dry-run executor 的 CLAUDE_CODE_CALLED=no 和真实执行后的推断混为一谈。真实执行后应输出 unknown（无法确认），不是 no。

## T084 真实调用最小实现设计避坑

- 不要在真实调用后把 CLAUDE_CODE_CALLED 写成 no。真实执行后无法精确确认，必须输出 unknown。
- 不要在真实调用后把 BUSINESS_CODE_CHANGED 写成 no。有变更但无法分类时必须输出 unknown。
- 不要跳过 simulated 阶段直接实现真实调用。应先用模拟数据验证解析和推断逻辑，再连接真实执行。
- 不要把 `--real-call-run-once` 和 `--real-call-dry-run` 设计为可以同时使用，两者互斥。
- 不要在第一次真实调用 pass 后自动进入下一任务。MVP 硬约束：无论 pass/fail 都停止。
- 不要用 subprocess 调用 `run_project_task_full()`。Python 函数调用更简单，避免编码和环境问题。
- 不要假设 `FullTaskLoopResult` 一定有 final_status。必须处理 None 和异常值。

## T085 Real-Call Run-Once Safety Shell 避坑

- 不要把 run-once safety shell 的 CHECK_RESULT=pass 误认为真实执行成功。safety shell 只构造 command/function_call，不执行任何真实操作。
- 不要跳过 CLI 层互斥检查直接依赖函数层。CLI 层提供更清晰的错误提示（ERROR: ...），函数层在函数被其他入口调用时仍然有效。
- 不要在 dirty workspace 下期望能验证 pass 路径。dirty workspace 会被 safety gate 先拦截，函数级验证是 dirty 状态下的补充手段。
- 不要把 --real-call-run-once 和 --real-call-dry-run 设计为可以同时使用。run-once 是 T079 dry-run executor 的升级路径，两者互斥。
- 不要在 run-once safety shell 中调用 run_project_task_full。safety shell 的职责是"检查通过 + 构造调用信息"，真实调用是 T090。

## T086 Child Command Parser Dry-Run 避坑

- 不要在 _classify_workspace_changes 中直接用 git status 行做 startswith 检查。行格式是 `XY filename`（前 3 字符为状态标记），必须先剥离前缀再检查文件路径，否则 `A  reports/xxx.md` 不会匹配 `reports/`。
- 不要把缺失可选字段的值默认为 no 或空字符串。CLAUDE_CODE_CALLED 和 BUSINESS_CODE_CHANGED 缺失时必须为 unknown，与确认的 no 语义不同。
- 不要把 parse_check_result=pass 和 CHECK_RESULT=pass 混为一谈。parse_check_result 代表解析是否成功，CHECK_RESULT 代表子命令执行结果。
- 不要假设 REPORT_PATHS 只有一个路径。应使用逗号分隔解析为 list。
- 不要在 parser 中忽略 exit_code 非 0 的情况。虽然 parser 本身不处理 exit_code，但应在 message 中说明，供后续执行层决策。

## T090 Real-call Run-once MVP 小结避坑

- 不要把 run-once safety shell 的 CHECK_RESULT=pass 误认为真实执行成功。safety shell 只构造调用信息，不执行任何真实操作。
- 不要把 child parser 能解析样例输出误认为可以处理真实执行结果。parser 验证的是解析逻辑，不是执行链路。
- 不要把 pass 后停止误认为是 bug。MVP 阶段无论 pass/fail 都停止等待人工确认，这是安全边界，不是长期限制。
- 不要在下一步直接实现真实调用。从 safety shell + parser 到真实执行之间，需要先设计首次执行验收协议。
- 不要把 T090 小结的 REAL_CALL_RUN_ONCE_MVP_STATUS=done 误解为真实执行已完成。done 代表 safety shell + parser MVP 完成，不代表真实调用。

## T091 首次真实调用验收协议设计避坑

- 不要把首次真实调用 pass 后的 ready_for_human_review 当成可以自动继续。ready_for_human_review 只代表结果可验收，不代表验收已通过。
- 不要在 CLAUDE_CODE_CALLED 无法确认时输出 no。no 代表确认未调用，unknown 代表信息不足，两者含义不同。
- 不要在 BUSINESS_CODE_CHANGED 无法分类时输出 no。同上，unknown 和 no 语义不同。
- 不要在首次真实调用后自动 Git backup。workspace 变化需要人工分类，报告和代码是否一起提交需要人工决定。
- 不要把 5 小时限额恢复机制在当前阶段实现。checkpoint / resume 等能力等首次真实调用跑通后单独设计。
- 不要假设首次真实调用一定成功。需要同时设计成功和失败的验收标准，以及异常处理流程。
- 不要在 unknown 字段出现时直接阻塞验收。unknown 字段只降级为 ready_for_human_review，不阻塞，但必须设置 HUMAN_REVIEW_REQUIRED=true。

## T095 首次真实执行开关设计避坑

- 不要把 `--real-call-run-once` 当成执行开关。它只进入 safety shell，构造 command/function_call 但不执行。`--real-execute-once` 才是真实执行请求。
- 不要把第二重确认短语 `EXECUTE_REAL_TASK_ONCE` 用于第三重确认。三个确认短语不能互相替代，任何错位都必须拒绝。
- 不要接受 yes/ok/确认 作为第三重确认。必须精确等于 `EXECUTE_REAL_RUN_ONCE`。
- 不要在首次真实执行 pass 后自动进入下一任务。三重确认只允许执行一次，执行后必须停止等待人工验收。
- 不要在当前阶段实现 API 429 / 5 小时限额自动恢复。当前只 stop and report，未来单独设计 checkpoint resume。

## T100 第一次真实 run-project-task-full 调用避坑

- 不要用框架级任务做首次真实执行验证。T100 是"执行第一次真实 run-project-task-full 调用"，属于框架开发任务，不适合作为首次验证目标。
- 不要在 prompt 中设置矛盾指令。T100 的 prompt 要求"连接真实 run_project_task_full()"（暗示修改框架代码），但禁止修改列表包含 runner.py 和 tools/*.py，导致 Claude Code 因矛盾卡住超时。
- 不要盲目增加 timeout。600 秒超时的根因是任务过大和 prompt 矛盾，不是 timeout 本身不足。应先降低任务复杂度。
- 不要把真实调用链路验证成功等同于任务完成。T100 证明链路可达，但 child execution 超时，任务未实际完成。
- 不要跳过执行后 workspace 检查。真实执行可能修改非预期文件，必须逐一确认变更是否可解释。
- 不要在 `run-project-task-full` 命令中期望三重确认。该命令是独立入口，不经过 `run-project-loop` 的三重确认流程。

## T101 人工验收第一次真实调用结果避坑

- 不要跳过人工验收直接进入下一任务。真实执行后必须通过验收清单逐项确认，即使调用链路看起来正常。
- 不要把验收清单 PASS 等同于任务 pass。10/10 PASS 只代表安全约束满足，不代表业务目标达成。
- 不要忽略 prompt 分析。超时的根因往往在 prompt 设计中（任务过大、矛盾指令、范围不清）。
- 不要只给一个策略选项。应比较多个方案（增加 timeout / 更换任务 / 改进框架），让决策者选择。
- 不要在验收报告中隐瞒风险。T100 的 prompt 矛盾和 5 小时额度风险必须如实记录。

## T102 first real-run smoke test 避坑

- 不要在 Claude Code 超时问题未诊断前继续重跑真实任务。T100 和 G008 都超时，盲目重跑只会消耗额度。
- 不要假设"任务越小越不会超时"。G008 是极小任务仍然超时，说明根因不在任务大小。
- 不要忽略 Claude Code subprocess 调用方式差异。`echo hello | claude --print` 秒级响应，但 subprocess 传递长 prompt 参数可能行为完全不同。
- Safety gate 在 dirty workspace 下会阻止执行。如果需要临时绕过（如 stash → gate → pop），必须确保 pop 后再执行真实调用。
- 不要把 T102 标记为 done。smoke task 未成功完成，应标记为 review_required。

## T103 Claude Code + 智谱代理超时诊断避坑

- 不要在 acceptEdits + tool use 兼容性问题未修复前继续重跑真实任务。根因已定位：acceptEdits 模式下工具调用后等待 API 响应 tool_result 时卡住。
- 不要只测 `claude --print "OK"` 就判断 Claude Code 正常。纯文本回复和工具调用是完全不同的代码路径，必须单独测试 tool use 场景。
- 不要忽略默认模式和 acceptEdits 模式的行为差异。默认模式下工具调用被权限拒绝后能正常返回（不需要等 API 响应），但 acceptEdits 模式下工具被执行后需要等 API 响应。
- 不要假设智谱 API 完全兼容 Anthropic API。tool_use / tool_result 消息格式可能存在细微差异，导致 Claude Code 无限等待。
- 诊断时应该分层测试：CLI 基础 → 文本输出 → acceptEdits 文本 → acceptEdits + tool use，逐步缩小问题范围。

## T104 Claude Code + 智谱代理 tool-use 修复方案设计避坑

- 不要只设计一个修复方案就动手实现。应先比较多个方向（至少 5 个），评估改动量、可行性和风险，再选择最小可行方案。
- 不要跳过可配置 permission mode 步骤直接修改 acceptEdits。先让模式可配置，再验证不同模式的行为，避免破坏已有逻辑。
- 不要在 permission mode 可配置之前就跑真实任务。default mode 下 Claude Code 无法自动写文件，可能导致任务执行不完整。
- 不要假设 bypassPermissions 模式不会有同样的问题。bypassPermissions 和 acceptEdits 的区别只在权限确认环节，tool_result 回传 API 的流程可能一样。
- 不要把方案 E（runner 自执行 patch）当作短期修复方向。架构改动大，适合长期增强但不适合当前阶段。
- 不要在 T109（智谱 API 兼容性评估）完成前做路线决策。需要先搞清楚智谱 API 是否支持 tool_use，再决定是修复还是绕开。

## T105 configurable Claude permission mode 设计避坑

- 不要在 T106 实现时改变默认行为。默认值必须保持 acceptEdits，所有历史调用不传参时行为与改动前完全一致。
- 不要只改 run_claude_code() 不改调用链。需要 runner.py → project_runner.py → claude_code_runner.py 全链路透传 permission_mode。
- 不要忽略 CLI 参数验证。未知 permission mode 值必须拒绝并输出错误信息，不能静默忽略或回退到默认值。
- 不要在命令预览中输出密钥或完整 prompt。CLAUDE_COMMAND_PREVIEW 只输出命令摘要，prompt 截断到 200 字符。
- 不要假设 default mode 能完成需要文件写入的任务。default mode 下工具调用被权限拒绝，Claude Code 只输出建议代码。
- 不要假设 bypassPermissions 没有同样的问题。bypassPermissions 绕过权限但不影响 tool_result 回传 API 的流程，可能同样卡住。
- 不要跳过 T107（default mode 验证）直接跑真实任务。需要先确认 default mode 下的最小行为。

### T106 实现避坑

- 不要用 `mode.lower()` 统一小写后再与 `{"acceptEdits", ...}` 比较。`"acceptEdits".lower()` → `"acceptedits"`，与 valid_modes 不匹配导致合法值被误判为非法。
- 不要只验证合法 mode，必须也验证非法值（如 `invalid`）是否正确拒绝。
- 不要在验证 CLI 参数时触发真实 Claude Code 调用。使用 `claude-permission-mode-dry-run` 命令做安全验证。
- 不要修改业务代码（projects/ 下的文件）或框架外文件。T106 只改 claude_code_runner.py、project_runner.py、full_task_runner.py、runner.py。

## T107 验证 default mode 最小文本调用避坑

- 不要在 dry-run 映射验证未通过前直接调用 Claude Code。dry-run 是安全前置检查。
- 不要在验证任务中测试写文件 tool-use。T107 只验证最小只读文本返回。
- 不要使用 acceptEdits 模式测试写文件。T107 的目标是验证 default mode。
- 不要运行 run-project-task-full。T107 只做最小文本调用诊断。
- 不要修改任何代码文件。验证任务只运行命令和记录结果。

## T108 回归验证 acceptEdits + tool-use 避坑

- 不要假设历史诊断结论永远成立。T103 的 acceptEdits + tool-use 超时在 T108 回归时变为 unexpected_pass。
- 不要在 unexpected_pass 后立即进入真实任务执行。单次测试不足以确信稳定性。
- 不要在回归验证中删除意外创建的诊断文件。保留为 unexpected artifact，等待人工决定。
- 不要使用 bypassPermissions 作为 tool-use 测试的替代方案。T108 只验证 acceptEdits。
- 不要运行 run-project-task-full。T108 只做最小 tool-use 回归诊断。

## T109 智谱代理兼容性评估避坑

- 不要把 T108 单次 unexpected_pass 当作智谱 tool-use 兼容性已修复的证据。单次通过不具备统计意义。
- 不要跳过分层验证直接恢复 run-project-task-full。Layer 1-4 必须逐层通过。
- 不要在兼容性评估中调用 Claude Code 或执行真实任务。T109 只做评估和文档。
- 不要忽略 T103 和 T108 结果不一致的风险。间歇性问题比持续性问题更难定位和复现。
- 不要假设路线 C（runner 自执行 patch）可以短期内替代路线 A。路线 C 是长期方向，短期应优先路线 A。

## T110 真实执行路线决策避坑

- 不要在 Layer 1-3 未通过前恢复 run-project-task-full。即使 T108 通过了一次最小 tool-use 测试，真实任务风险更高。
- 不要把路线 A 的决策当作"继续照旧"。路线 A 是"继续用智谱但先做稳定性验证"，不是"跳过验证直接恢复执行"。
- 不要在 Layer 2 失败时仍然坚持路线 A。Layer 2 失败说明 tool-use 确认不稳定，应切换路线 B 或启动路线 C。
- 不要在 T116 之前自动进入 Layer 4 (run-project-task-full smoke)。Layer 4 需要人工决策。
- 不要忽略路线 B 的对照实验价值。如果路线 A 在 Layer 3 失败，路线 B 可以快速确认问题是否在智谱代理。

## T111 分层稳定性验证协议设计避坑

- 不要在 Layer 1 失败时仍然尝试 Layer 2。Layer 1 是基础，text-only 不稳定说明 API 基础链路有问题。
- 不要把 Layer 1-3 通过等同于可以恢复真实任务。Layer 1-3 通过后还需要 T116 人工决策才能进入 Layer 4。
- 不要在 Layer 2 测试中使用 bypassPermissions。只使用 default 和 acceptEdits，bypassPermissions 风险过高。
- 不要在 Layer 2 测试中让 Claude Code 在非预期路径创建文件。文件范围限制在 `reports/diagnostics/tool-use/`。
- 不要忽略 Layer 3 runner 封装验证。即使 CLI 直接调用通过，runner 封装层可能引入额外问题（permission mode 传递、stdout/stderr 捕获等）。
- 不要自动重试失败的测试。任何一次失败立即停止，记录结果，等待人工验收。
