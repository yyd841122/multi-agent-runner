# Configurable Claude Permission Mode Design

## Background

T100 / G008 通过 `run-project-task-full` 调用 Claude Code 时均 600 秒超时。T103 诊断确认根因为 acceptEdits + tool use 兼容性问题：Claude Code 在 acceptEdits 模式下执行工具后，将 tool_result 发回智谱 API 等待下一轮响应时卡住。

T104 修复方案推荐短期方案 B+A：让 run_claude_code 的 permission mode 可配置，并验证 default mode 是否可作为临时回退。

## Goal

设计 `run_claude_code()` 的 permission mode 可配置方案，为 T106 实现做准备。

## Non-goals

- 本轮不修复智谱代理 tool-use 兼容性
- 本轮不执行真实任务
- 本轮不修改 Claude 配置
- 本轮不修改任何代码

## Current Behavior

### 硬编码位置

`tools/claude_code_runner.py` 第 39 行：

```python
result = subprocess.run(
    [command, "--permission-mode", "acceptEdits", "--print", prompt],
    ...
)
```

### 调用链

1. `runner.py` → `run_claude_code(prompt)` （run-current, run-next, retry-current, run-loop, run-game-next）
2. `tools/project_runner.py` → `run_project_next()` → `run_developer_step()` → `run_claude_code(prompt)`
3. `tools/full_task_runner.py` → `run_project_task_full()` → `run_developer_step()` → `run_project_next()` → `run_claude_code(prompt)`

所有调用方只传 `(prompt)` — 无 permission_mode 参数。

### 需要改造的位置

| 文件 | 改动 | 说明 |
|------|------|------|
| tools/claude_code_runner.py | run_claude_code() 签名变更 | 新增 permission_mode 参数 |
| tools/project_runner.py | 传递 permission_mode | run_developer_step() 透传 |
| tools/full_task_runner.py | 传递 permission_mode | run_project_task_full() 透传 |
| tools/continuous_task_planner.py | 真实执行路径传递 | future: real-call 链路 |
| runner.py | CLI 参数解析 | 新增 --claude-permission-mode |

## Candidate Configuration Sources

### 方案 A：CLI 参数

```bash
python runner.py run-project-task-full --project . --task T102 --claude-permission-mode default
```

**优点：**
- 最直观，命令行可见
- 适合诊断和临时切换
- 不影响全局配置
- 易于在报告中记录

**缺点：**
- 命令较长
- 每次调用都要传参
- 需要向下传递参数（runner → project_runner → claude_code_runner）

### 方案 B：环境变量

```bash
CLAUDE_PERMISSION_MODE=default python runner.py run-project-task-full ...
```

**优点：**
- 适合本地长期配置
- 不需要改所有 CLI 命令
- 跨终端会话生效

**缺点：**
- 隐式行为，不容易从命令看出
- 容易被不同终端环境影响
- 调试困难

### 方案 C：项目配置文件

```yaml
# project.yaml
claude_permission_mode: default
```

**优点：**
- 项目级可控
- 适合不同项目使用不同策略
- 配置与代码分离

**缺点：**
- 需要扩展配置读取逻辑
- 可能影响 template 和 project_runner

### 方案 D：函数参数

```python
run_claude_code(prompt, permission_mode="acceptEdits")
```

**优点：**
- 实现清晰
- 便于单元测试
- 是底层必要改造
- 所有上层方案的基础

**缺点：**
- 需要上层 CLI / runner 传递
- 不能单独解决用户入口问题

## Recommended Design

### 短期实现：D + A（底层函数参数 + CLI 参数）

**理由：**
- D 是所有上层方案的基础，必须先做
- A 提供最直观的用户入口，适合诊断
- 两者组合覆盖最常见的使用场景
- 不引入隐式行为

### 中期扩展：B（环境变量）

**理由：**
- 在 D+A 稳定后，增加环境变量作为默认值来源
- 适合长期切换场景

### 长期扩展：C（项目配置）

**理由：**
- 在 B 稳定后，增加项目级配置
- 适合多项目场景

### 优先级

```
CLI 参数 > 环境变量 > 项目配置 > 内置默认值
```

**理由：**
- CLI 参数最显式，应优先级最高
- 环境变量次之，适合本地长期配置
- 项目配置适合团队共享默认值
- 内置默认值作为兜底

## Default Strategy

### 内置默认值：acceptEdits

**理由：**
1. 保持当前行为兼容 — 所有历史调用都不传参，默认 acceptEdits 保证行为不变
2. 避免已有测试突然变化
3. 后续 T107 显式传 `default` 做诊断

### 重要说明

当前智谱代理下 acceptEdits + tool-use **已知会超时**。因此：
- 真实任务执行时不应继续默认使用 acceptEdits
- 需要显式测试 `default` mode
- T107 验证 default mode 行为
- T108 确认 acceptEdits 仍然 blocked

## CLI Design

### 新增参数

```
--claude-permission-mode <mode>
```

### 允许值

| 值 | 映射到 Claude CLI 参数 | 说明 |
|----|----------------------|------|
| `default` | （不传 --permission-mode） | 使用 Claude Code 默认权限行为 |
| `none` | （不传 --permission-mode） | 等价于 default |
| `acceptEdits` | `--permission-mode acceptEdits` | 自动接受文件编辑 |
| `bypassPermissions` | `--permission-mode bypassPermissions` | 绕过所有权限检查 |

### 验证规则

- 未知值 → 拒绝，输出错误信息，CHECK_RESULT=fail
- 大小写不敏感 → 统一转小写处理
- 空字符串 → 等价于 default

### 需要覆盖的命令

| 命令 | 说明 |
|------|------|
| `run-project-task-full` | 单任务完整闭环 |
| `run-project-next` | 单步执行 |
| `run-current` | 执行当前提示词 |
| `run-next` | 单步自动闭环 |
| `retry-current` | 重新执行当前任务 |
| `run-loop` | 多任务循环 |
| `run-game-next` | 小游戏单步执行 |
| `run-project-loop` 真实执行路径 | 连续任务真实执行 |

**本轮只设计，不实现。**

## Function Design

### run_claude_code() 签名变更

```python
def run_claude_code(
    prompt: str,
    command: str = "claude",
    permission_mode: str = "acceptEdits",
) -> dict:
```

### 内部逻辑

```python
# 构造命令参数
cmd_args = [command]
if permission_mode in ("default", "none", ""):
    pass  # 不传 --permission-mode
elif permission_mode == "acceptEdits":
    cmd_args.extend(["--permission-mode", "acceptEdits"])
elif permission_mode == "bypassPermissions":
    cmd_args.extend(["--permission-mode", "bypassPermissions"])
else:
    # 未知模式 — 仍然尝试传递，由 Claude CLI 报错
    cmd_args.extend(["--permission-mode", permission_mode])
cmd_args.extend(["--print", prompt])
```

### 调用方传递规则

1. `runner.py` CLI 解析 `--claude-permission-mode` → 传递给 `run_claude_code(prompt, permission_mode=mode)`
2. `tools/project_runner.py` 的 `run_project_next()` 接收 `permission_mode` 参数 → 传递给 `run_claude_code()`
3. `tools/full_task_runner.py` 的 `run_project_task_full()` 接收 `permission_mode` 参数 → 传递给 `run_project_next()`

## Mode Mapping

| 配置值 | Claude CLI 参数 | 行为描述 |
|--------|----------------|---------|
| `default` | 无 | 不传 permission-mode，Claude Code 使用默认权限行为（工具调用需要用户确认） |
| `none` | 无 | 等价于 default |
| `acceptEdits` | `--permission-mode acceptEdits` | 自动接受文件编辑（**智谱代理下 tool-use 已知超时**） |
| `bypassPermissions` | `--permission-mode bypassPermissions` | 绕过所有权限检查（**高风险，只用于受控环境**） |

## Output Fields

后续执行报告中必须包含以下字段：

| 字段 | 说明 | 示例 |
|------|------|------|
| `CLAUDE_PERMISSION_MODE` | 实际使用的 permission mode | `default` / `acceptEdits` / `bypassPermissions` |
| `CLAUDE_PERMISSION_MODE_SOURCE` | 配置来源 | `cli` / `env` / `project` / `default` |
| `CLAUDE_PERMISSION_ARG_PASSED` | 是否传递了 --permission-mode 给 Claude CLI | `yes` / `no` |
| `CLAUDE_COMMAND_PREVIEW` | 命令摘要（masked） | `claude --print <prompt>` |

### 安全约束

- 不输出 ANTHROPIC_AUTH_TOKEN 或任何密钥
- 不输出完整超长 prompt（截断到 200 字符）
- 只输出命令摘要

## Validation Plan

### 验证场景（20 个）

| # | 场景 | 预期行为 |
|---|------|---------|
| 1 | 未传 --claude-permission-mode | 保持 acceptEdits 默认行为 |
| 2 | --claude-permission-mode acceptEdits | 传 --permission-mode acceptEdits 给 Claude CLI |
| 3 | --claude-permission-mode default | 不传 --permission-mode 给 Claude CLI |
| 4 | --claude-permission-mode none | 不传 --permission-mode 给 Claude CLI |
| 5 | --claude-permission-mode bypassPermissions | 传 --permission-mode bypassPermissions 给 Claude CLI |
| 6 | --claude-permission-mode unknown_value | 拒绝，CHECK_RESULT=fail |
| 7 | --claude-permission-mode "" (空字符串) | 等价于 default |
| 8 | CLI 参数优先于环境变量 | CLI 传 default + 环境变量 acceptEdits → 使用 default |
| 9 | 环境变量优先于项目配置 | 环境变量 default + 项目配置 acceptEdits → 使用 default |
| 10 | 项目配置优先于内置默认 | 项目配置 default → 使用 default |
| 11 | run-project-task-full 能接收该参数 | 命令正常解析 |
| 12 | run-project-next 能接收该参数 | 命令正常解析 |
| 13 | run-project-loop 未来真实路径能向下传递 | 透传到 run_claude_code() |
| 14 | default mode 不会自动写文件 | 工具调用被权限拒绝 |
| 15 | acceptEdits 在智谱代理下标记为 known-risk | 报告中标注 |
| 16 | bypassPermissions 标记为 high-risk | 报告中标注 |
| 17 | 输出字段包含 mode/source/arg passed | 报告包含 4 个必需字段 |
| 18 | 不泄露 token | 命令预览中无密钥 |
| 19 | 缺省行为兼容历史测试 | 不传参时行为与改动前完全一致 |
| 20 | 与已有 T096/T098 safety gate 不冲突 | safety gate 不关心 permission mode |

## Risk Control

### default mode

- **行为**：工具调用需要用户确认，非交互模式下被权限拒绝
- **影响**：Claude Code 无法自动写文件，只能输出建议代码
- **适用**：诊断验证、半自动模式
- **不适合**：无人值守自动化

### acceptEdits

- **行为**：自动接受文件编辑
- **智谱代理下已知问题**：tool-use 调用后 tool_result 回传 API 卡住
- **标记**：`KNOWN_RISK=tool_use_timeout_with_zhipu`
- **适用**：官方 Claude 模型或兼容 tool-use 的 API
- **不适合**：当前智谱代理环境下的真实任务执行

### bypassPermissions

- **行为**：绕过所有权限检查
- **标记**：`HIGH_RISK=all_permissions_bypassed`
- **适用**：只用于受控环境（如沙箱、CI）
- **不适合**：生产环境

### 通用风险

1. permission mode 可配置**不等于修复智谱 tool_use**
2. 真实任务恢复前**必须重新跑最小 smoke test**
3. 所有真实执行**必须显式指定 permission mode**，不能依赖默认值
4. default mode 下的任务完成标准需要重新定义（无文件写入 ≠ 任务失败）

## Recommended Implementation Roadmap

| 任务 | 角色 | 目标 | 依赖 |
|------|------|------|------|
| T106 | Developer | 实现 configurable Claude permission mode | T105 |
| T107 | Tester | 验证 default mode 最小 Claude Code 调用 | T106 |
| T108 | Tester | 验证 acceptEdits tool-use blocked 回归 | T107 |
| T109 | Researcher | 评估智谱代理 tool_use/tool_result 兼容性 | T108 |
| T110 | Decision | 决策真实执行路线 | T109 |

## Final Status

```text
T105_DESIGN_STATUS=done
RECOMMENDED_SHORT_TERM=D_PLUS_A
DEFAULT_PERMISSION_MODE=acceptEdits
NEXT_PENDING=T106
```
