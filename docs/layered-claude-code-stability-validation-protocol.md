# Layered Claude Code Stability Validation Protocol

## Background

multi-agent-runner 项目使用 Claude Code CLI + 智谱代理（glm-5.1, `open.bigmodel.cn/api/anthropic`）作为 Developer Agent 执行引擎。

在 Stage 7 真实执行验证过程中，发现 Claude Code + 智谱代理的 tool-use 兼容性问题：

- **T100**：框架级真实任务，`run-project-task-full` 调用 Claude Code，600 秒超时
- **T102/G008**：极小 smoke task（只创建一个 marker 文件），同样 600 秒超时
- **T103**：系统化诊断，定位根因为 acceptEdits + tool-use 超时；text-only 路径正常
- **T104**：设计修复方案，推荐短期 B+A（可配置 permission mode）+ 中期 D（评估兼容性）
- **T105-T106**：设计并实现 configurable Claude permission mode
- **T107**：验证 default mode 最小文本调用正常
- **T108**：回归验证 acceptEdits + tool-use，**unexpected_pass**（超时不再复现）
- **T109**：评估智谱代理兼容性，text-only pass、tool-use unstable、full execution not_stable
- **T110**：决策路线 A（继续智谱代理 + 分层稳定性验证）

### 证据表

| Task | Scenario | Result | Meaning |
|------|----------|--------|---------|
| T100 | full run-project-task-full (框架级) | timeout (600s) | full real execution not stable |
| T102 | G008 smoke task (极小) | timeout (600s) | minimal full loop not stable |
| T103 | acceptEdits + tool-use | timeout (120s) | compatibility issue observed |
| T103 | default text-only | pass | text-only path OK |
| T103 | acceptEdits text-only | pass | text-only path OK |
| T107 | default text-only | pass | text-only path OK |
| T108 | default text-only | pass | text-only path OK |
| T108 | acceptEdits text-only | pass | text-only path OK |
| T108 | acceptEdits + tool-use | unexpected_pass | issue not deterministic |
| T109 | compatibility assessment | unstable | layered validation recommended |

## Goal

本协议定义恢复真实执行前的分层稳定性验证流程。通过 Layer 1-3 逐层验证 Claude Code + 智谱代理的稳定性，为 T116 人工决策提供科学依据。

## Non-goals

- 不直接恢复 `run-project-task-full`
- 不执行真实业务任务
- 不使用 `bypassPermissions`
- 不自动进入下一层
- 不自动 Git backup
- 不自动重试

## Validation Principles

1. **由低风险到高风险**：从 text-only 到 tool-use，从 CLI 直接到 runner 封装
2. **由单次到多次**：每层多次验证确认稳定性
3. **逐层通过**：只有前一层全部通过，才能进入下一层
4. **任何一层失败，立即停止并人工验收**
5. **不允许自动进入 run-project-task-full**
6. **不自动 Git backup**
7. **不自动重试**

### Layer 1-3 通过前

```text
NEXT_EXECUTION_ALLOWED=no
NEXT_REAL_TASK_ALLOWED=no
NEXT_SMOKE_TEST_ALLOWED=no
```

---

## Layer 1: Text-only Stability Validation

### 目标

验证 Claude Code 文本输出路径在连续多次调用中保持稳定，不触发 tool-use，不写文件，不修改项目。

### 前置条件

- workspace clean
- Claude Code CLI 可用（`claude --version` 正常返回）
- 智谱 API 可达

### 测试内容

| # | 测试 | 命令 | 次数 | 超时上限 |
|---|------|------|------|---------|
| 1 | default text-only | `claude --print "只回复 OK，不要解释，不要调用工具。"` | 连续 3 次 | 60 秒 |
| 2 | acceptEdits text-only | `claude --permission-mode acceptEdits --print "只回复 OK，不要解释，不要调用工具。"` | 连续 3 次 | 60 秒 |

### 通过标准

- 6/6 全部 pass
- 每次输出包含 "OK" 或等价确认
- 无 tool-use 触发
- 无文件变更
- 无超时
- 全部秒级返回（< 30 秒）

### 失败标准

- 任意一次 timeout
- 任意一次非 OK 输出
- 任意一次触发工具调用
- 任意一次产生文件变更
- 任意一次超过 30 秒

### 输出字段

```text
LAYER_1_STATUS=pass/fail/review_required
TEXT_ONLY_STABILITY=stable/unstable
DEFAULT_TEXT_PASS_COUNT=<0-3>
DEFAULT_TEXT_FAIL_COUNT=<0-3>
ACCEPTEDITS_TEXT_PASS_COUNT=<0-3>
ACCEPTEDITS_TEXT_FAIL_COUNT=<0-3>
```

### 失败处理

- 停止后续所有层
- 输出 `CHECK_RESULT=review_required` + `HUMAN_REVIEW_REQUIRED=yes`
- 智谱代理 text-only 也不稳定 → 考虑切换官方 Claude 或检查网络环境
- 进入路线决策（路线 B 或环境检查）

### 执行任务

T113：执行 Layer 1 text-only stability validation

---

## Layer 2: Controlled Single-file Tool-use Stability Validation

### 目标

验证受控 tool-use 写文件是否稳定，但不进入 run-project-task-full。只在安全路径下创建临时诊断文件。

### 前置条件

- Layer 1 全部通过
- workspace clean

### 测试内容

| # | 测试 | 命令 | 次数 | 超时上限 |
|---|------|------|------|---------|
| 1 | acceptEdits + 创建临时文件 | `claude --permission-mode acceptEdits --print "请在 reports/diagnostics/tool-use/ 目录下创建一个名为 T114-tool-use-check-01.txt 的文件，内容为 diagnostic ok。完成后只回复 DONE。"` | 最多 3 次 | 120 秒 |

**文件路径规则：**

```
reports/diagnostics/tool-use/T114-tool-use-check-01.txt
reports/diagnostics/tool-use/T114-tool-use-check-02.txt
reports/diagnostics/tool-use/T114-tool-use-check-03.txt
```

### 执行规则

1. 每次文件名唯一（递增编号）
2. 只在 `reports/diagnostics/tool-use/` 目录下创建
3. 不使用 `bypassPermissions`
4. 每次完成后人工确认文件内容和位置
5. 任何一次 timeout 立即停止，不再继续
6. 如果第一次就 timeout，记录为 Layer 2 fail
7. 每次测试前检查 workspace 是否 clean

### 通过标准

- 3/3 成功创建
- 文件内容正确（包含 "diagnostic ok" 或 "ok"）
- 无超时
- 无额外文件变更（只有预期的诊断文件）
- 无业务代码变更
- 无框架代码变更

### 失败标准

- 任意一次 timeout
- 创建了错误文件（不在预期路径）
- 修改了非预期文件
- Claude Code 无响应
- 产生了业务代码变更
- 产生了框架代码变更

### 输出字段

```text
LAYER_2_STATUS=pass/fail/review_required
TOOL_USE_STABILITY=stable/unstable
TOOL_USE_TEST_1=<pass/timeout/fail>
TOOL_USE_TEST_2=<pass/timeout/fail/skipped>
TOOL_USE_TEST_3=<pass/timeout/fail/skipped>
TOOL_USE_PASS_COUNT=<0-3>
TOOL_USE_FAIL_COUNT=<0-3>
```

### 失败处理

- 停止后续所有层
- 输出 `CHECK_RESULT=review_required` + `HUMAN_REVIEW_REQUIRED=yes`
- acceptEdits + tool-use 确认不稳定 → 考虑路线 B（切换官方 Claude）
- 也可以考虑路线 C（长期方案提前启动）
- 进入路线决策

### 清理策略

- 通过的临时文件可以保留作为证据，也可以人工清理
- 失败的临时文件如果有部分创建，保留用于诊断

### 执行任务

T114：执行 Layer 2 controlled single-file tool-use stability validation

---

## Layer 3: Runner-level Minimal Claude Call Validation

### 目标

验证 runner 封装层调用 Claude Code 的最小路径，但仍不进入 run-project-task-full。

### 前置条件

- Layer 1 全部通过
- Layer 2 全部通过
- workspace clean

### 测试内容

| # | 测试 | 说明 | 次数 | 超时上限 |
|---|------|------|------|---------|
| 1 | runner 调用 claude_code_runner | 通过 `run_claude_code()` 调用 Claude Code，prompt 极短，text-only | 1 次 | 60 秒 |
| 2 | runner 调用 claude_code_runner + tool-use | 通过 `run_claude_code()` 调用 Claude Code，创建一个临时文件 | 1 次 | 120 秒 |

### 测试命令

**测试 1：text-only（通过 runner 封装）**

```python
from tools.claude_code_runner import run_claude_code
result = run_claude_code(
    prompt="只回复 OK，不要解释，不要调用工具。",
    permission_mode="default"
)
```

**测试 2：controlled tool-use（通过 runner 封装）**

```python
from tools.claude_code_runner import run_claude_code
result = run_claude_code(
    prompt="在 reports/diagnostics/runner/ 目录下创建一个名为 T115-runner-check-01.txt 的文件，内容为 runner diagnostic ok。完成后只回复 DONE。",
    permission_mode="acceptEdits"
)
```

### 验证项

| # | 验证项 | 说明 |
|---|--------|------|
| 1 | runner 能调用 Claude Code | `run_claude_code()` 成功返回 |
| 2 | permission_mode 正确传递 | 检查返回的 `permission_mode` 字段 |
| 3 | 能捕获 stdout/stderr | 检查返回的 `stdout` 和 `stderr` 字段 |
| 4 | 能正确处理 returncode | 检查返回的 `returncode` 字段 |
| 5 | 能正确处理 timeout | 如果超时，`returncode=124` |
| 6 | 不会修改业务代码 | 检查 workspace 变更 |
| 7 | 不会修改框架代码 | 检查 workspace 变更 |

### 通过标准

- 2/2 全部 pass
- runner 封装调用正常
- permission_mode 正确传递
- stdout/stderr 正确捕获
- 无业务代码变更
- 无框架代码变更

### 失败标准

- runner wrapper 超时
- permission mode 未正确传递
- stdout/stderr 捕获异常
- 产生未知文件变更
- 产生了业务代码变更
- 产生了框架代码变更

### 输出字段

```text
LAYER_3_STATUS=pass/fail/review_required
RUNNER_LEVEL_CLAUDE_CALL=stable/unstable
RUNNER_TEXT_ONLY=<pass/fail/timeout>
RUNNER_TOOL_USE=<pass/fail/timeout>
RUNNER_PERMISSION_MODE_CORRECT=yes/no
RUNNER_STDOUT_CAPTURED=yes/no
RUNNER_STDERR_CAPTURED=yes/no
RUNNER_RETURN_CODE_CORRECT=yes/no
```

### 失败处理

- 停止后续所有层
- 输出 `CHECK_RESULT=review_required` + `HUMAN_REVIEW_REQUIRED=yes`
- runner 封装调用有问题 → 排查 runner → claude_code_runner → subprocess 链路
- 可能需要调整 runner 调用方式或参数
- 考虑路线 B（切换官方 Claude）或路线 C（长期方案提前启动）
- 进入路线决策

### 执行任务

T115：执行 Layer 3 runner-level minimal Claude call validation

---

## Layer 4: run-project-task-full Smoke Gate

**注意：Layer 4 不是马上执行，而是 T116 后人工决策才允许。**

### 目标

在 Layer 1-3 全部通过后，才允许恢复 G008/G009 run-project-task-full smoke test。

### 允许条件

```text
LAYER_1_STATUS=pass
LAYER_2_STATUS=pass
LAYER_3_STATUS=pass
WORKTREE_STATUS=clean
NEXT_EXECUTION_ALLOWED=human_approved
```

### 执行范围

- max one smoke task
- 只执行 G008 或 G009（由 T116 人工决定）
- 不自动重试
- 不自动进入下一任务
- 不自动 Git backup
- 执行后人工验收

### 超时设置

- Claude Code timeout: 600 秒
- 如 600 秒超时，判定为 Layer 4 fail

### 通过标准

- smoke task 成功完成
- smoke marker 文件已创建
- 无额外文件变更
- 业务代码未修改
- 框架代码未修改

### 失败标准

- smoke task 超时
- smoke marker 未创建
- 产生了非预期文件变更

### 输出字段

```text
LAYER_4_STATUS=pass/fail/review_required
FULL_LOOP_SMOKE=pass/fail/timeout
SMOKE_TASK_ID=G008 或 G009
SMOKE_MARKER_CREATED=yes/no
FULL_LOOP_STABILITY=stable/unstable
```

### 失败处理

- 输出 `CHECK_RESULT=review_required` + `HUMAN_REVIEW_REQUIRED=yes`
- 进入路线决策（路线 B 或路线 C）

### 决策任务

T116：人工决策是否恢复 G008/G009 run-project-task-full smoke test

---

## Stop Rules

任何层出现以下情况必须停止：

| # | 停止条件 | 说明 |
|---|---------|------|
| 1 | timeout | 任何测试超时 |
| 2 | unexpected file modification | 产生非预期文件变更 |
| 3 | business code changed | 业务代码被修改 |
| 4 | framework code changed | 框架代码被修改 |
| 5 | Claude Code no response | Claude Code 完全无响应 |
| 6 | API 429 / 5 hour limit | 触发 API 使用限额 |
| 7 | permission mode mismatch | permission mode 未正确传递 |
| 8 | tool-use unexpected behavior | 工具调用行为异常 |
| 9 | dirty_unknown workspace | workspace 出现无法解释的变更 |

### 停止后输出

```text
CHECK_RESULT=review_required
HUMAN_REVIEW_REQUIRED=yes
AUTO_CONTINUE_TO_NEXT_TASK=no
AUTO_GIT_BACKUP=no
NEXT_EXECUTION_ALLOWED=no
STOP_REASON=<具体停止原因>
STOP_LAYER=<1/2/3/4>
```

---

## Report Structure

每层验证报告应包含以下章节：

1. **Goal**：本层验证目标
2. **Commands**：实际执行的命令
3. **Expected Result**：预期结果
4. **Actual Result**：实际结果
5. **Timeout Settings**：超时设置
6. **Permission Mode**：使用的权限模式
7. **Stdout/Stderr Summary**：输出摘要
8. **Changed Files**：变更文件列表
9. **Safety Check**：安全检查项
10. **Check Result**：验证结论
11. **Next Action**：下一步行动

### 报告路径

| Layer | 报告路径 |
|-------|---------|
| Layer 1 | `reports/checks/T113-layer-1-text-only-stability-check.md` |
| Layer 2 | `reports/checks/T114-layer-2-tool-use-stability-check.md` |
| Layer 3 | `reports/checks/T115-layer-3-runner-level-claude-call-check.md` |
| Layer 4 Decision | `reports/checks/T116-layered-stability-human-decision.md` |

---

## Safety Rules

1. **不自动进入下一层**：每层通过后必须人工确认才能进入下一层
2. **不自动 Git backup**：验证产生的临时文件需要人工分类
3. **不自动重试**：任何失败立即停止，不自动重试
4. **任何异常都人工验收**：unknown 字段、unexpected_pass、unexpected file 都需要人工确认
5. **不修改业务代码**：Layer 1-3 不修改 `projects/**` 下的文件
6. **不修改框架代码**：Layer 1-3 不修改 `runner.py`、`tools/*.py`
7. **不使用 bypassPermissions**：只使用 default 和 acceptEdits
8. **不执行 run-project-task-full**：Layer 1-3 不调用 run-project-task-full
9. **Layer 4 需要人工决策**：不能自动从 Layer 3 进入 Layer 4

### 安全检查项

| # | 检查项 | Layer 1 | Layer 2 | Layer 3 |
|---|--------|---------|---------|---------|
| 1 | 是否运行 run-project-task-full | no | no | no |
| 2 | 是否调用 Claude Code | yes (text-only) | yes (tool-use) | yes (via runner) |
| 3 | 是否执行真实任务 | no | no | no |
| 4 | 是否修改业务代码 | no | no | no |
| 5 | 是否修改框架代码 | no | no | no |
| 6 | 是否使用 bypassPermissions | no | no | no |
| 7 | 是否自动 Git backup | no | no | no |

---

## Task Roadmap

| Task | 角色 | 目标 | 依赖 |
|------|------|------|------|
| T111 | Architect | 设计 layered Claude Code stability validation protocol | T110 |
| T112 | Developer | 实现 text-only stability check dry-run/report skeleton | T111 |
| T113 | Tester | 执行 Layer 1 text-only stability validation | T112 |
| T114 | Tester | 执行 Layer 2 controlled single-file tool-use stability validation | T113 |
| T115 | Tester | 执行 Layer 3 runner-level minimal Claude call validation | T114 |
| T116 | Human | 人工决策是否恢复 G008/G009 run-project-task-full smoke test | T115 |

### 任务说明

- **T111**：设计分层稳定性验证的详细协议（本文件）
- **T112**：实现 text-only 稳定性验证的 dry-run 和报告生成（不调用 Claude Code）
- **T113**：执行 Layer 1 文本输出稳定性验证（6 次调用，全部秒级返回）
- **T114**：执行 Layer 2 单文件 tool-use 稳定性验证（最多 3 次，记录 pass/timeout/fail）
- **T115**：执行 Layer 3 runner 封装最小调用验证（text-only + controlled tool-use）
- **T116**：人工决策点，基于 Layer 1-3 结果决定是否恢复 full loop smoke test

### 任务约束

- T112 可以实现辅助命令，但不能调用 Claude Code
- T113 才允许调用 text-only Claude Code
- T114 才允许一次或最多三次受控 tool-use
- T115 才允许 runner-level minimal Claude call
- T116 只做人工决策，不直接跑 smoke task

---

## Later Decision Points

### 如果 Layer 1 失败

- 智谱代理 text-only 也不稳定 → 考虑切换官方 Claude 或检查网络环境
- 这是最低层，失败意味着基础链路有问题
- 排查方向：网络连接、API Key、智谱 API 状态

### 如果 Layer 2 失败

- acceptEdits + tool-use 确认不稳定 → 考虑路线 B（切换官方 Claude 验证闭环）
- 也可以考虑路线 C（长期方案提前启动）
- 失败类型分析：
  - 全部 timeout → tool-use 基本不可用
  - 部分通过部分超时 → 间歇性问题
  - 通过但文件内容错误 → 兼容性部分问题

### 如果 Layer 3 失败

- runner 封装调用有问题 → 排查 runner → claude_code_runner → subprocess 链路
- 可能需要调整 runner 调用方式或参数
- 考虑路线 B 或路线 C

### 如果 Layer 1-3 全部通过

- 进入 Layer 4（run-project-task-full smoke）需要人工决策（T116）
- Layer 4 通过后，恢复真实任务执行
- 但仍需要逐步放开：先 smoke → 再单个真实任务 → 最后连续循环

---

## Final Status

```text
T111_PROTOCOL_STATUS=done
NEXT_EXECUTION_ALLOWED=no
NEXT_REAL_TASK_ALLOWED=no
NEXT_SMOKE_TEST_ALLOWED=no
NEXT_PENDING=T112
NEXT_STAGE=Stage 7
```
