# T028 开发报告 — Reviewer 自动审查接入真实模型

## 任务信息

- 任务编号：T028
- 角色：Developer Agent
- 状态：完成

## 修改文件列表

| 文件 | 改动说明 |
|------|----------|
| `docs/tasks.md` | T028 状态从 pending → in_progress → done |
| `tools/reviewer_runner.py` | 更新 prompt 要求输出 Machine Readable Result；run_reviewer_for_game_task 新增结构化解析和 Parsed Result 报告段 |
| `runner.py` | review-game-task 命令输出结构化审查结果摘要 |
| `projects/down-100-floors-game/reports/review/G003-review-report.md` | 新建 — G003 审查报告（无 Key 测试版） |
| `reports/dev/T028-dev-report.md` | 新建 — 开发报告 |

## 完成内容

### tools/reviewer_runner.py 改动

1. **build_reviewer_prompt** — prompt 中新增：
   - 明确要求输出 `## Machine Readable Result` 段落
   - 给出 JSON 模板（含双花括号转义）
   - 定义字段枚举规则（status 5 种 / decision 4 种）
   - 定义判断规则（全部满足→PASS/APPROVE / 有问题→FAIL/REQUEST_CHANGES / 缺文件→BLOCKED）

2. **run_reviewer_for_game_task** — 审查流程增强：
   - 调用 `parse_reviewer_output()` 解析 DeepSeek 返回内容
   - 报告新增 `## Parsed Result` 段（status / decision / issues / summary / next_action）
   - 解析失败时记录错误但不崩溃
   - 返回值从 `Path` 改为 `(Path, ReviewParseResult | None)` 元组

### runner.py 改动

- `review-game-task` 命令输出结构化结果摘要：
  - 解析成功：显示 Status / Decision / Issues 数量
  - 解析失败：显示错误原因
  - 模型调用失败：明确提示

## 验收标准自查

- [x] review-game-task 可以调用 DeepSeek Reviewer
- [x] Reviewer prompt 明确要求输出 Machine Readable Result
- [x] 可以保存 G003-review-report.md
- [x] 可以解析 Reviewer 的结构化输出
- [x] 可以输出 Status / Decision / Issues
- [x] 保留 mock provider 回退能力
- [x] 不自动返工
- [x] 不自动修改任务状态

## 无 Key 情况处理说明

在无 `DEEPSEEK_API_KEY` 环境变量时：

```
provider=deepseek, model=deepseek-chat, success=False
Error: 缺少环境变量 DEEPSEEK_API_KEY
Parsed Result: success=False, error=模型调用失败，无法解析
```

程序不崩溃，报告正确保存，结构化解析正确报告失败。

## 真实 DeepSeek 测试方式

用户在 PowerShell 中执行：

```powershell
$env:DEEPSEEK_API_KEY="你的 DeepSeek API Key"
python runner.py review-game-task G003
```

预期：

```
Reviewer 审查报告已生成：
  projects/down-100-floors-game/reports/review/G003-review-report.md

结构化审查结果：
  Status：PASS
  Decision：APPROVE
  Issues：0
```

然后查看报告：

```powershell
Get-Content projects\down-100-floors-game\reports\review\G003-review-report.md -Encoding UTF8
```

## 限制遵守

- 未自动返工
- 未自动修改任务状态
- 未修改小游戏业务代码
- 未修改 Developer 输出
- 未修改 config.yaml
- 未删除 mock provider
- 未接入多个真实模型
- 未执行 run-project-next
- 只实现 Reviewer 真实模型审查和结构化解析
- 所有文档使用简体中文
- 文件名、路径、代码关键字保持英文

## 是否完成

是。
