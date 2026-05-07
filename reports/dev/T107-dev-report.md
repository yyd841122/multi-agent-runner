# T107 Dev Report

## Task

验证 default mode 最小 Claude Code 调用。

## Scope

本轮只做最小文本调用诊断，不执行真实任务，不测试写文件 tool-use。

## Changed Files

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| reports/checks/T107-default-mode-minimal-claude-call-check.md | new | 验证报告 |
| reports/dev/T107-dev-report.md | new | 本文件 |
| docs/tasks.md | modified | T107 状态更新 |
| memory/lessons.md | modified | 追加 T107 经验 |
| memory/pitfalls.md | modified | 追加 T107 避坑记录 |

## Verification

### Dry-run Mapping

4/4 PASS。确认 `--claude-permission-mode default` 正确映射为不传 `--permission-mode`。

### Default Mode Minimal Claude Call

- 命令：`claude --print "只回复 OK，不要解释，不要调用工具。"`
- 结果：成功返回 "OK"，秒级响应
- 未传 `--permission-mode`
- 未触发工具调用
- 未写文件
- 未超时

### 对比 T103 诊断结论

| 模式 | 文本调用 | tool-use 调用 |
|------|---------|--------------|
| default（不传 --permission-mode） | PASS（本次验证） | 权限拒绝后正常返回（T103 已验证） |
| acceptEdits（--permission-mode acceptEdits） | PASS（T103 已验证） | TIMEOUT（T103 已验证） |

## Safety Result

| 检查项 | 结果 |
|--------|------|
| 是否运行 run-project-task-full | no |
| 是否执行真实任务 | no |
| 是否调用 Claude Code 写文件 | no |
| 是否修改业务代码 | no |
| 是否修改框架代码 | no |

## Next

T108：验证 acceptEdits tool-use blocked 回归
