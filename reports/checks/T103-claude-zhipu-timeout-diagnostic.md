# T103 Claude Code + Zhipu Timeout Diagnostic

## Goal

诊断 T100 / G008 均 600 秒超时的根因。

## Background

- T100（框架级任务，矛盾 prompt）通过 `run-project-task-full` 调用 Claude Code，600 秒超时（returncode=124）
- G008（极小 smoke marker 任务，只创建一个文件，prompt 无歧义）通过 `run-project-task-full` 调用 Claude Code，600 秒超时（returncode=124）
- 当前使用 Claude Code CLI 2.1.104 + 智谱模型代理（glm-5.1）

## Environment Checks

### Claude CLI

| 检查项 | 结果 |
|--------|------|
| where claude | `C:\Users\Administrator\.local\bin\claude.exe` |
| claude --version | 2.1.104 (Claude Code) |
| CLAUDE_CLI_FOUND | yes |

### 环境变量

| 变量 | 值 |
|------|-----|
| ANTHROPIC_BASE_URL | https://open.bigmodel.cn/api/anthropic |
| ANTHROPIC_MODEL | glm-5.1 |
| ANTHROPIC_AUTH_TOKEN | present（masked） |
| HTTP_PROXY | 未设置 |
| HTTPS_PROXY | 未设置 |
| ALL_PROXY | 未设置 |
| NO_PROXY | 未设置 |

关键发现：**直接走智谱云端 API**（`open.bigmodel.cn`），不是本地代理。

### settings.json 摘要

| 检查项 | 结果 |
|--------|------|
| ANTHROPIC_BASE_URL | https://open.bigmodel.cn/api/anthropic |
| ANTHROPIC_MODEL | glm-5.1 |
| API_TIMEOUT_MS | 3000000（50 分钟） |
| ENABLE_TOOL_SEARCH | 0 |
| 多层代理配置 | 无 |
| 异常 base_url | 无 |

### 项目级配置

| 检查项 | 结果 |
|--------|------|
| .claude/settings.local.json | 存在，只有权限列表 |
| .mcp.json | 不存在 |
| 额外代理配置 | 无 |

## Minimal Claude Tests

### 测试 1：最小文本输出（默认模式）

```
claude --print "只回复 OK，不要解释，不要调用工具。"
```

| 检查项 | 结果 |
|--------|------|
| MINIMAL_PRINT_STATUS | pass |
| 输出 | "好的" |
| 耗时 | 秒级 |

### 测试 2：最小文本输出（acceptEdits 模式）

```
claude --permission-mode acceptEdits --print "只回复 OK，不要修改文件，不要调用工具。"
```

| 检查项 | 结果 |
|--------|------|
| ACCEPT_EDITS_PRINT_STATUS | pass |
| 输出 | "好的" |
| 耗时 | 秒级 |

### 测试 3：acceptEdits + 工具调用（写文件）

```
claude --permission-mode acceptEdits --print "在 /tmp 目录下创建一个名为 claude-diag-test.txt 的文件..."
```

| 检查项 | 结果 |
|--------|------|
| TOOL_USE_ACCEPT_EDITS_STATUS | **timeout** |
| 超时时间 | 120 秒 |
| 输出 | 无 |
| 行为 | 完全无响应 |

### 测试 4：默认模式 + 工具调用（写文件）

```
claude --print "请在当前目录创建一个名为 _diag_test.txt 的文件..."
```

| 检查项 | 结果 |
|--------|------|
| DEFAULT_TOOL_USE_STATUS | pass（权限拒绝后返回） |
| 输出 | "写入权限被拒绝，需要你在提示时允许写入操作..." |
| 耗时 | 秒级 |
| 行为 | 尝试调用工具，被权限拒绝后正常返回 |

## Diagnosis

### 诊断分类：C

**Claude CLI 可启动，普通 --print 正常，acceptEdits 普通文本输出正常，但 acceptEdits + tool use / 写文件场景超时。**

| 测试场景 | 结果 | 说明 |
|----------|------|------|
| claude --print "OK" | pass | 秒级返回 |
| claude --acceptEdits --print "OK" | pass | 秒级返回 |
| claude --acceptEdits --print "创建文件" | **timeout** | 120 秒无响应 |
| claude --print "创建文件" | pass | 权限拒绝后正常返回 |

### 根因分析

当 Claude Code 在 `--permission-mode acceptEdits` 模式下尝试调用工具（Write、Bash 等）时，与智谱 API 之间出现兼容性问题：

1. Claude Code 发送请求到智谱 API
2. 智谱 API 返回包含 `tool_use` 的响应
3. Claude Code 在本地执行工具（如 Write 文件）
4. Claude Code 将工具结果发送回 API
5. **在这一步出现阻塞** — 智谱 API 可能未正确处理 `tool_result` 消息格式，或响应格式与 Claude Code 期望不兼容

关键证据：
- 默认模式下，工具调用被权限拒绝后能正常返回（不需要等待 API 响应 tool_result）
- acceptEdits 模式下，工具调用被执行后，需要将结果发回 API 等待下一轮响应，此时卡住
- 纯文本回复不需要工具调用，所以秒级返回

### 与 T100 / G008 的关联

`run-project-task-full` → `run_developer_step()` → `run_claude_code()` 调用 Claude Code 时使用 `--permission-mode acceptEdits`。

G008 的 prompt 要求创建一个文件，Claude Code 会尝试调用 Write 工具。在 acceptEdits 模式下，工具调用执行后需要与 API 交互，而智谱代理对 `tool_result` 消息的处理可能存在兼容性问题，导致无限等待。

## Risk

- 当前不适合继续真实任务执行，所有需要工具调用的任务都会在 acceptEdits 模式下超时
- 继续重跑会消耗 API 调用额度
- 可能触发智谱 API 限流
- 需要先修复 Claude Code + 智谱代理的 tool use 兼容性

## Recommended Fix Path

按优先级排序：

1. **先修复最小 tool use 测试**：验证 `claude --permission-mode acceptEdits --print "创建文件"` 能否通过修复配置或调整调用方式恢复正常
2. **候选修复方向**：
   - A. 尝试不用 `--permission-mode acceptEdits`，改为默认权限模式或 `bypassPermissions` 模式
   - B. 检查智谱 API 是否支持 Anthropic tool use / tool_result 消息格式
   - C. 尝试更换模型（如 glm-4.7）或更换代理/API 兼容层
   - D. 调整 run_claude_code() 的调用参数（如 `--max-turns`、stdin 传 prompt 等）
   - E. 如果智谱代理无法稳定支持 tool use，考虑将 Claude Code 真实执行层切换回官方模型或其他兼容性更好的代理
3. **验证修复后的完整链路**：先验证 acceptEdits + tool use → 再验证 G008 → 最后恢复 run-project-task-full
4. 在修复完成前暂停真实自动化任务执行

## Check Result

```text
CHECK_RESULT=review_required
```

原因：诊断已定位根因为 acceptEdits + tool use 兼容性问题，但尚未修复，需要进入 T104 设计修复方案。

## Next

T104：设计 Claude Code + 智谱代理 tool-use 兼容性修复方案
