# Stage 7 No-Tool-Use Safe Execution Fallback Strategy

## Background

Stage 7 原目标是实现"真实单任务自动执行"：通过 `run-project-task-full` 调用 Claude Code，让 Claude Code 自动完成 Developer → Tester → Reviewer → Main Agent 完整闭环。

稳定性验证结果：

| Layer | 内容 | 结果 |
|-------|------|------|
| Layer 1 | text-only 6 次调用 | 6/6 pass |
| Layer 2 | acceptEdits + tool-use 3 次调用 | 0/3 pass（第 1 次 timeout） |
| Layer 3 | runner 封装调用 | 未执行（Layer 2 失败后按协议停止） |

结论：
- **text-only 链路稳定**：default 和 acceptEdits 模式纯文本输出均秒级返回
- **tool-use 链路不稳定**：acceptEdits + tool-use 触发 120s+ timeout
- **不能直接依赖 tool-use 进入真实执行**

历史证据链：
- T103：诊断 acceptEdits + tool-use 超时
- T108：acceptEdits + tool-use unexpected_pass（间歇性问题）
- T114：再次确认 acceptEdits + tool-use timeout

## Problem

当前问题：

1. **Claude Code text-only 稳定但 tool-use 不稳定**：智谱代理对 tool_use/tool_result 消息格式兼容性不稳定
2. **真实执行依赖 tool-use**：run-project-task-full 需要调用 `run_claude_code()` → Claude Code subprocess，Claude Code 执行任务时需要使用工具（Write、Edit、Bash 等）来修改文件
3. **tool-use 不稳定导致自动化闭环不可靠**：如果 tool-use 可能卡住、超时或无法返回，整个自动化流程无法闭环
4. **直接绕过风险高**：不能在 tool-use unstable 的情况下强行进入真实执行

## Decision

```text
Stage 7 不暂停
Stage 7 不跳过
Stage 7 不直接进入不稳定 tool-use 真实执行
Stage 7 改为优先设计 no-tool-use safe execution fallback
```

**核心决策**：将 Claude Code 从"直接执行者"转变为"结构化输出提供者"，runner 接管实际执行控制权。

## Core Strategy

### 模型角色转变

| 原方案 | 新方案 |
|--------|--------|
| Claude Code 通过 tool-use 直接写文件 | Claude Code 只输出 text-only structured proposal |
| Claude Code 直接执行命令 | runner 解析 proposal 后决定是否执行 |
| Claude Code 自主决策修改范围 | runner 控制所有修改范围 |
| Claude Code 生成并提交报告 | runner 根据 proposal 生成报告 |

### 核心原则

1. **Claude Code / 国内模型只负责 text-only 输出**：所有模型调用使用 default 模式或 text-only 路径，不依赖 tool-use
2. **runner 负责实际执行控制**：文件修改、命令执行、状态判断、报告生成全部由 runner 代码完成
3. **所有真实文件修改必须由 runner 审核后执行**：runner 解析 proposal 中的 patch，检查范围后应用
4. **所有命令执行必须由 runner 控制**：runner 只执行 allowlist 内的命令
5. **所有状态判断必须由 runner 记录**：runner 维护执行状态机
6. **所有 Git 操作必须后续由 dedicated git backup step 控制**：不自动 commit/push

## Proposed Execution Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Runner 控制流程                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. runner 选择一个真实单任务                                 │
│     ↓                                                       │
│  2. runner 生成结构化 prompt                                 │
│     包含：任务定义、现有代码上下文、输出格式要求              │
│     ↓                                                       │
│  3. Claude Code / 国内模型 返回 text-only proposal           │
│     使用 default 模式，不触发 tool-use                       │
│     ↓                                                       │
│  4. proposal 包含：                                          │
│     - target_files: 要修改的文件列表                         │
│     - intended_changes: 变更描述                             │
│     - patch_text: unified diff 格式的补丁                    │
│     - commands_to_run: 需要执行的命令列表                    │
│     - expected_results: 预期验证结果                         │
│     - safety_declarations: 安全声明                          │
│     ↓                                                       │
│  5. runner 解析 proposal                                     │
│     ↓                                                       │
│  6. runner 检查是否越权                                      │
│     - 文件范围检查                                           │
│     - 命令白名单检查                                         │
│     - 安全声明验证                                           │
│     ↓                                                       │
│  7. runner 进入 human review 或 controlled apply             │
│     ↓                                                       │
│  8. runner 应用允许范围内的 patch                             │
│     使用 Python 直接操作文件（非 Claude Code tool-use）       │
│     ↓                                                       │
│  9. runner 执行允许范围内的 test command                      │
│     ↓                                                       │
│  10. runner 生成 execution report                            │
│     ↓                                                       │
│  11. human review 后再决定是否进入下一步                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Allowed Model Output Types

模型允许输出的内容类型：

| 类型 | 说明 | 示例 |
|------|------|------|
| structured plan | 结构化执行计划 | 包含步骤、目标文件、预期结果 |
| structured patch proposal | 结构化补丁提案 | unified diff 格式 |
| unified diff text | 统一差异文本 | 标准 `--- a/file +++ b/file @@ ...` |
| command proposal | 命令提案 | 需要执行的命令列表 |
| report draft | 报告草稿 | 开发报告、测试报告的文本内容 |
| status summary | 状态总结 | 任务完成情况说明 |
| analysis result | 分析结果 | 代码分析、问题诊断 |

## Forbidden Model Actions

模型禁止执行的动作：

| 禁止动作 | 原因 |
|----------|------|
| direct file write through tool-use | tool-use 不稳定 |
| direct git add/commit/push | 高风险操作必须由 runner 控制 |
| direct run-project-task-full invocation | 防止无限递归 |
| direct auto-continue | 每次执行后必须人工确认 |
| direct business code modification without runner approval | 所有修改必须经过范围检查 |
| direct bypass permissions | 权限控制是安全边界 |
| direct command execution | 命令必须经过白名单检查 |

## Runner Responsibilities

runner 在 no-tool-use 模式下的职责：

| 职责 | 说明 |
|------|------|
| task selection | 从任务列表选择下一个待执行任务 |
| prompt generation | 生成包含任务定义、代码上下文、输出格式要求的结构化 prompt |
| model invocation | 调用 Claude Code（text-only / default mode）或国内模型 API |
| proposal parsing | 解析模型返回的结构化 proposal |
| scope validation | 检查 proposal 中的文件和命令是否在允许范围内 |
| patch application | 使用 Python 代码直接应用 unified diff patch |
| command execution | 执行 allowlist 内的命令 |
| test result capture | 捕获命令输出和退出码 |
| report writing | 生成执行报告（开发报告、测试报告等） |
| state update | 更新任务状态 |
| human review gate | 每次执行后暂停等待人工确认 |
| error handling | 处理异常、超时、格式错误等 |

## Safety Gates

### 执行前安全门

| 安全门 | 检查内容 | 失败动作 |
|--------|---------|----------|
| clean worktree gate | git status --short 无输出 | 停止并报告 |
| single-task gate | 当前只有一个任务在执行 | 停止并报告 |
| allowed file scope gate | proposal 中所有文件路径在 allowed_files 内 | 停止并报告 |
| forbidden file scope gate | proposal 中无 blocked_files 文件 | 停止并报告 |

### Proposal 解析安全门

| 安全门 | 检查内容 | 失败动作 |
|--------|---------|----------|
| patch parse gate | unified diff 格式正确且可解析 | 停止并报告 |
| command allowlist gate | 所有命令在 allowlist 内 | 停止并报告 |

### 执行后安全门

| 安全门 | 检查内容 | 失败动作 |
|--------|---------|----------|
| business code change classification gate | workspace 变更分类为 dirty_expected | 停止并报告 |
| test result gate | 测试命令返回 pass | 记录并报告 |
| report existence gate | 执行报告已生成 | 停止并报告 |

### 全局安全门

| 安全门 | 检查内容 | 失败动作 |
|--------|---------|----------|
| human review gate | 每次执行后等待人工确认 | 不自动继续 |
| no auto-continue gate | 不自动进入下一任务 | 强制停止 |
| no auto-git-backup gate | 不自动 git commit/push | 强制停止 |

## Failure Handling

### 失败停止条件

| 条件 | 检测方式 | 停止等级 |
|------|---------|----------|
| model timeout | subprocess 超时 | hard stop |
| empty output | 模型返回空文本 | hard stop |
| invalid proposal format | JSON/结构解析失败 | hard stop |
| unsafe file path | 文件路径超出 allowed_files | hard stop |
| forbidden command | 命令不在 allowlist 内 | hard stop |
| dirty workspace before execution | 执行前 workspace 不 clean | hard stop |
| unexpected dirty workspace after execution | 执行后出现非预期文件变更 | hard stop |
| test failure | 测试命令返回非零 | soft stop（记录并报告） |
| missing report | 执行报告未生成 | soft stop（记录并报告） |
| ambiguous task status | 任务状态不明确 | soft stop（记录并报告） |

### 失败恢复策略

| 场景 | 策略 |
|------|------|
| model timeout | 记录 timeout，不重试，等待人工确认 |
| invalid proposal | 记录原始输出和解析错误，等待人工确认 |
| unsafe scope | 记录违规文件/命令，等待人工确认 |
| dirty workspace | 不自动 clean，记录变更列表，等待人工确认 |
| test failure | 记录失败原因，不自动返工，等待人工确认 |

## Proposal Schema（设计草案）

```json
{
  "proposal_version": "1.0",
  "task_id": "G008",
  "task_title": "任务标题",
  "analysis": "对任务和现有代码的分析",
  "target_files": [
    {
      "path": "projects/down-100-floors-game/script.js",
      "action": "modify",
      "description": "修改说明"
    }
  ],
  "patches": [
    {
      "file": "projects/down-100-floors-game/script.js",
      "patch": "--- a/script.js\n+++ b/script.js\n@@ -10,3 +10,8 @@\n+// 新增代码\n"
    }
  ],
  "commands_to_run": [
    {
      "command": "python runner.py test-game-task G008",
      "purpose": "运行测试",
      "risk_level": "low"
    }
  ],
  "expected_results": "预期结果描述",
  "safety_declarations": {
    "no_framework_modification": true,
    "no_business_code_outside_scope": true,
    "no_git_operations": true,
    "no_env_modification": true
  }
}
```

注意：此 schema 是设计草案，T116 将正式定义完整 schema。

## Stage 7 Revised Path

### T116 以后建议任务拆解

| 任务 | 角色 | 目标 | 类型 |
|------|------|------|------|
| T116 | Architect | 设计 no-tool-use execution proposal schema | 设计 |
| T117 | Developer | 实现 proposal parser dry-run | 实现 |
| T118 | Developer | 实现 allowed scope validator dry-run | 实现 |
| T119 | Developer | 实现 controlled patch apply dry-run | 实现 |
| T120 | Tester | 执行 first no-tool-use real single-task dry-run | 验证 |
| T121 | Tester | 验证 first no-tool-use execution pass/fail 场景 | 验证 |
| T122 | Developer | 提交并推送 Stage 7 no-tool-use execution reports | 提交 |

### 任务依赖关系

```
T116 (schema 设计)
  ↓
T117 (proposal parser) ← 依赖 T116 schema
  ↓
T118 (scope validator) ← 依赖 T117 parser
  ↓
T119 (patch apply) ← 依赖 T118 validator
  ↓
T120 (first dry-run) ← 依赖 T119 patch apply
  ↓
T121 (pass/fail 验证) ← 依赖 T120 dry-run
  ↓
T122 (提交) ← 依赖 T121 验证
```

### 与原有任务的关系

原 T115（Layer 3 runner-level）和 T116（人工决策）已被重新定义：

- **原 T115**（Layer 3）→ 本策略文档替代。Layer 2 失败后不再继续 Layer 3 验证，改为 no-tool-use fallback
- **原 T116**（人工决策）→ 重新定义为 proposal schema 设计。人工决策点保留在每个执行步骤的 human review gate 中

## Decision Summary

```text
NO_TOOL_USE_FALLBACK_STRATEGY=designed
READY_FOR_DIRECT_TOOL_USE_REAL_EXECUTION=no
READY_FOR_NO_TOOL_USE_STAGE_7_CONTINUATION=yes
HUMAN_REVIEW_REQUIRED=yes
```

### 路线对比

| 路线 | 说明 | 当前状态 |
|------|------|---------|
| 路线 A | 继续智谱代理 + 分层验证 | Layer 2 失败，需要 fallback |
| 路线 B | 切换官方 Claude API | 备用，可作为对照实验 |
| 路线 C | runner 自执行 patch | **当前采用的方向**，不依赖 tool-use |
| 路线 A+C | 智谱 text-only + runner 执行 | **推荐组合** |

### 推荐执行路径

**短期（T116-T122）**：实现 no-tool-use execution pipeline
- 模型只输出 text-only structured proposal
- runner 解析、验证、应用、报告
- 全程 human review gate

**中期（T123+）**：验证并逐步放开
- 验证 no-tool-use pipeline 稳定性
- 考虑恢复 tool-use 对照实验
- 逐步提高自动化程度

**长期**：双模式支持
- tool-use 模式（当 tool-use 稳定时）
- no-tool-use 模式（当 tool-use 不稳定时）
- runner 自动选择模式
