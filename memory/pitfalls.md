# Pitfalls

## 第一阶段踩坑记录

1. **不要在 Claude Code 会话内运行会再次调用 Claude Code 的命令。** 例如 `run-current`、`run-next`、`retry-current`、`run-loop`。这些命令会内部调用 Claude Code CLI，导致嵌套调用和长时间卡住。真实验收必须在普通 PowerShell 中执行。

2. **Windows 下 subprocess 读取 Claude Code 输出时要指定 `encoding="utf-8", errors="replace"`。** 默认使用 gbk 编码，Claude Code 输出包含中文字符时会导致 `UnicodeDecodeError`。

3. **PowerShell 查看 UTF-8 中文文件时要使用 `-Encoding UTF8`。** 直接 `cat` 或 `Get-Content` 可能显示乱码。

4. **Windows 下 Claude Code 可能需要 `CLAUDE_CODE_GIT_BASH_PATH`。** 如果 Claude Code CLI 报错找不到 bash，需要设置环境变量指向 git-bash 路径。

5. **Claude Code 非交互调用如果没有 `--permission-mode acceptEdits`，可能不会自动写文件。** 默认模式下 Claude Code 只输出建议代码，不会实际修改文件。

6. **不能只根据 Claude Code 退出码判断任务完成。** 退出码 0 只代表 Claude Code 进程正常结束，不代表它完成了预期工作（例如生成开发报告）。

7. **429 使用限额要被识别，并停止继续自动调用。** `analyze_claude_output` 要检测 stderr 中的 429 错误，避免在限额状态下继续自动调用导致浪费时间。检测范围应限定在 Stderr 段，避免 Stdout 中的代码内容误匹配。
