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
