# T106 Dev Report

## Task

实现 configurable Claude permission mode。

## Scope

本轮只实现 permission mode 参数与 dry-run 映射验证，不调用 Claude Code，不执行真实任务。

## Changed Files

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| tools/claude_code_runner.py | modified | 新增 build_claude_permission_args()、修改 run_claude_code() 签名 |
| tools/project_runner.py | modified | run_project_next() 新增 claude_permission_mode 参数并透传 |
| tools/full_task_runner.py | modified | run_developer_step() 和 run_project_task_full() 透传 |
| runner.py | modified | 新增 _parse_claude_permission_mode()、CLI 参数解析、claude-permission-mode-dry-run 命令 |
| reports/checks/T106-configurable-claude-permission-mode-check.md | new | 验证报告 |
| reports/dev/T106-dev-report.md | new | 本文件 |

## Implementation

### 1. build_claude_permission_args()

新增 `tools/claude_code_runner.py` 中的权限参数映射函数：

- `None` / `""` / `"acceptEdits"` → `["--permission-mode", "acceptEdits"]`
- `"default"` / `"none"` → `[]`（不传 --permission-mode）
- `"bypassPermissions"` → `["--permission-mode", "bypassPermissions"]`
- 非法值 → 抛出 `ValueError`

### 2. run_claude_code(permission_mode=...)

修改 `run_claude_code()` 签名：

```python
def run_claude_code(
    prompt: str,
    command: str = "claude",
    permission_mode: str | None = "acceptEdits",
) -> dict:
```

返回结果新增 `permission_mode` 和 `permission_args_passed` 字段。非法值时返回 `returncode=2` 的错误结果。

### 3. 调用链透传

- `runner.py` → `run_claude_code(prompt, permission_mode=mode)`（5 处调用全部修改）
- `runner.py` → `_handle_run_project_next(project_path, claude_permission_mode=mode)` → `run_project_next(project_path, claude_permission_mode=mode)` → `run_claude_code(prompt, permission_mode=mode)`
- `runner.py` → `run_project_task_full(project_path, task_id, claude_permission_mode=mode)` → `run_developer_step(project_path, task_id, claude_permission_mode=mode)` → `run_project_next(...)` → `run_claude_code(...)`

### 4. runner.py CLI

新增 `_parse_claude_permission_mode(args)` 辅助函数，从 args 中提取 `--claude-permission-mode` 值。

覆盖的命令：
- `run-current`
- `run-next`
- `retry-current`
- `run-loop`
- `run-game-next`
- `run-project-next`
- `run-project-task-full`

### 5. claude-permission-mode-dry-run

新增 CLI 命令，只输出参数映射，不调用 Claude Code。

```bash
python runner.py claude-permission-mode-dry-run
python runner.py claude-permission-mode-dry-run --mode acceptEdits
python runner.py claude-permission-mode-dry-run --mode default
python runner.py claude-permission-mode-dry-run --mode none
python runner.py claude-permission-mode-dry-run --mode bypassPermissions
python runner.py claude-permission-mode-dry-run --mode invalid
```

## Behavior

| Mode | Claude CLI 参数 | 行为 |
|------|----------------|------|
| `acceptEdits` | `--permission-mode acceptEdits` | 自动接受文件编辑（智谱代理下 tool-use 已知超时） |
| `default` | 无 | 不传 --permission-mode，Claude Code 使用默认权限行为 |
| `none` | 无 | 等价于 default |
| `bypassPermissions` | `--permission-mode bypassPermissions` | 绕过所有权限检查（高风险） |
| 非法值 | 拒绝 | ValueError / returncode=2 / CHECK_RESULT=fail |

## Compatibility

- 默认行为保持 `acceptEdits`，不破坏已有逻辑
- 所有历史调用都不传参，默认 acceptEdits 保证行为不变
- `_execute_one_task()` 和 `run_project_next()` 的默认值也是 `acceptEdits`

## Safety Result

| 检查项 | 结果 |
|--------|------|
| 是否调用 Claude Code | no |
| 是否运行 run-project-task-full 真实任务 | no |
| 是否修改业务代码 | no |
| 是否修改框架外文件 | no |
| 是否自动进入下一任务 | no |
| 是否自动 Git backup | no |

## Verification

36/36 验证场景全部 PASS。详见 reports/checks/T106-configurable-claude-permission-mode-check.md。

## Next

T107：验证 default mode 最小 Claude Code 调用
