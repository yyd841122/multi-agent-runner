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
