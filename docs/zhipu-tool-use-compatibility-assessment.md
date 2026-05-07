# Zhipu Tool-use Compatibility Assessment

## Background

multi-agent-runner 项目使用 Claude Code CLI + 智谱代理（glm-5.1, `open.bigmodel.cn/api/anthropic`）作为 Developer Agent 执行引擎。

在 Stage 7 真实执行验证过程中，发现了 Claude Code + 智谱代理的 tool-use 兼容性问题：

- **T100**：框架级真实任务，`run-project-task-full` 调用 Claude Code，600 秒超时
- **T102/G008**：极小 smoke task（只创建一个 marker 文件），同样 600 秒超时
- **T103**：系统化诊断，定位根因为 acceptEdits + tool-use 超时
- **T104**：设计修复方案，推荐短期 B+A（可配置 permission mode）+ 中期 D（评估兼容性）
- **T105-T106**：设计并实现 configurable Claude permission mode
- **T107**：验证 default mode 最小文本调用正常
- **T108**：回归验证 acceptEdits + tool-use，**unexpected_pass**（超时不再复现）

## Evidence Summary

| Task | Scenario | Result | Meaning |
|------|----------|--------|---------|
| T100 | run-project-task-full real task (框架级) | timeout (600s) | full loop not stable |
| T102/G008 | run-project-task-full minimal smoke | timeout (600s) | complexity not root cause |
| T103 | acceptEdits text-only | pass (秒级) | text path OK |
| T103 | acceptEdits + tool-use (创建文件) | **timeout (120s)** | compatibility issue found |
| T103 | default + tool-use (创建文件) | pass (权限拒绝后返回) | default mode workaround |
| T107 | default mode text-only | pass (秒级) | default text path OK |
| T108 | default text-only | pass (秒级) | text path still OK |
| T108 | acceptEdits text-only | pass (秒级) | text path still OK |
| T108 | acceptEdits + tool-use (创建文件) | **unexpected_pass** | issue not always reproducible |

### 关键证据链

1. **text-only 链路稳定**：T103/T107/T108 三次验证，default 和 acceptEdits 模式下纯文本输出均秒级返回
2. **tool-use 兼容性不稳定**：T103 超时 vs T108 通过，相同测试场景不同结果
3. **full execution 未验证**：T100/T102 均超时，run-project-task-full 完整闭环仍未成功

## Compatibility Assessment

### 1. Text-only 兼容性

| 维度 | 结论 |
|------|------|
| default text-only | pass（T107, T108 验证） |
| acceptEdits text-only | pass（T103, T108 验证） |
| 响应时间 | 秒级 |
| 稳定性 | 稳定（3 次验证均通过） |

**判断：文本输出链路基本可用。** 智谱代理对 Anthropic Messages API 的基础文本响应兼容性良好。

### 2. Tool-use 兼容性

| 维度 | 结论 |
|------|------|
| T103 acceptEdits + tool-use | timeout (120s) |
| T108 acceptEdits + tool-use | unexpected_pass |
| 测试次数 | 各 1 次 |
| 稳定性判断 | **unstable**（不稳定） |

**判断：tool-use 不是稳定不可用，但也不能判定稳定可用。** 单次 unexpected_pass 不代表兼容性问题已完全解决。

可能的解释：
1. 智谱代理的 tool_use/tool_result 兼容层存在间歇性问题
2. 智谱代理或 Claude Code CLI 版本在 T103 和 T108 之间发生了更新
3. T103 观察到的超时可能是暂时性的网络或服务端问题
4. 智谱 API 的负载状态可能影响 tool-use 请求的处理

### 3. 真实任务执行兼容性

| 维度 | 结论 |
|------|------|
| T100 run-project-task-full (框架级) | timeout (600s) |
| T102/G008 run-project-task-full (smoke) | timeout (600s) |
| 完整闭环成功次数 | 0 |
| 稳定性判断 | **not_stable** |

**判断：run-project-task-full 真实任务链路仍未稳定 pass。** 即使 T108 显示 tool-use 可能在某些时候通过，真实任务执行涉及更长 prompt、多轮工具调用、更复杂的 tool_result 交互，风险更高。

## Risk Assessment

### 继续真实任务执行的风险

| 风险 | 严重程度 | 说明 |
|------|---------|------|
| 再次超时 | 高 | T100/T102 均超时，T108 只通过一次最小测试 |
| 浪费额度 | 中 | 每次超时消耗 600 秒和 API 额度 |
| 触发 5 小时限制 | 中 | 智谱 API 可能有日限额，连续重跑可能触发 |
| 误判兼容性已修复 | 高 | 单次 unexpected_pass 不能作为恢复依据 |

### 不能把 T108 单次 unexpected_pass 当作彻底修复的理由

1. 只有一次测试，不具备统计意义
2. 最小测试（创建一个文件）与真实任务（多轮工具调用）复杂度差距大
3. T103 和 T108 结果不一致，说明可能存在间歇性因素
4. 智谱代理的兼容性可能受服务端状态、负载、版本等因素影响

## Stability Validation Layers

为科学评估 tool-use 兼容性，建议分层验证。以下只设计不执行。

### Layer 1：Text-only Stability（文本输出稳定性）

**目标**：确认文本输出链路在连续多次调用中保持稳定。

| 测试 | 命令 | 次数 | 预期 |
|------|------|------|------|
| default text-only | `claude --print "只回复 OK"` | 连续 3 次 | 全部秒级返回 |
| acceptEdits text-only | `claude --permission-mode acceptEdits --print "只回复 OK"` | 连续 3 次 | 全部秒级返回 |

**通过标准**：6/6 全部通过
**风险**：极低（纯文本，无副作用）
**预计耗时**：< 1 分钟

### Layer 2：Single-file Tool-use Stability（单文件工具调用稳定性）

**目标**：确认 acceptEdits + tool-use 在多次调用中是否稳定通过。

| 测试 | 命令 | 次数 | 预期 |
|------|------|------|------|
| acceptEdits + 创建临时文件 | `claude --permission-mode acceptEdits --print "创建 _diag_N.txt，内容 ok"` | 最多 3 次 | 记录 pass/timeout/fail |

**规则**：
- 使用临时文件名（`_diag_stability_1.txt` 等），不覆盖已有文件
- 每次测试后检查文件是否创建
- 每次测试后人工清理临时文件
- 任何一次 timeout 立即停止，不再继续
- 如果第一次就 timeout，记录为 Layer 2 fail

**通过标准**：3/3 全部通过
**风险**：低（创建临时文件，可控清理）
**预计耗时**：3-6 分钟（假设不超时）

**结果记录格式**：

```text
LAYER2_TEST_1=<pass/timeout/fail>
LAYER2_TEST_2=<pass/timeout/fail> 或 skipped
LAYER2_TEST_3=<pass/timeout/fail> 或 skipped
LAYER2_RESULT=<pass/fail/incomplete>
```

### Layer 3：Runner-level Smoke（Runner 封装调用测试）

**目标**：用 runner 封装调用 Claude Code，但不进入完整 multi-agent loop。

| 测试 | 说明 | 次数 |
|------|------|------|
| run_claude_code 极小 task | 通过 runner 调用 claude，prompt 极小，不进入 full loop | 1 次 |

**规则**：
- 不使用 run-project-task-full
- 不进入 Developer → Tester → Reviewer → Decision 完整闭环
- 只验证 runner → claude_code_runner → subprocess 链路
- 任务内容极小（如创建一个临时文件）

**通过标准**：1/1 通过
**风险**：低
**预计耗时**：< 5 分钟

### Layer 4：run-project-task-full Smoke（完整闭环冒烟测试）

**目标**：重新执行类似 G008 的 smoke task。

| 测试 | 说明 | 次数 |
|------|------|------|
| run-project-task-full smoke | 新建 G009 或重用 G008，只创建一个 marker 文件 | 1 次 |

**规则**：
- 必须通过 Layer 1-3 才能执行
- 只允许一次
- 使用 acceptEdits 权限模式
- 超时设置合理（600 秒）

**通过标准**：1/1 通过
**风险**：中（涉及完整闭环）
**预计耗时**：10-15 分钟

### 分层依赖关系

```
Layer 1 (text-only stability)
    ↓ 全部通过
Layer 2 (single-file tool-use stability)
    ↓ 全部通过
Layer 3 (runner-level smoke)
    ↓ 通过
Layer 4 (run-project-task-full smoke)
    ↓ 通过
恢复真实任务执行
```

**任何一层失败，停止后续验证，进入路线决策。**

## Route Options

### 路线 A：继续智谱代理，但先做稳定性验证

**说明**：保持当前环境（智谱代理 glm-5.1），但先做 Layer 1-4 分层稳定性验证。

**优点**：
- 符合当前用户环境和习惯
- 成本可控（智谱 API 费用较低）
- 可以逐步验证，风险递增
- 如果验证通过，直接恢复真实任务执行

**缺点**：
- 不稳定风险仍在，可能再次超时
- 即使 Layer 1-3 通过，Layer 4 仍可能超时
- 智谱代理的兼容性可能随时变化

**适合**：
- 短期继续推进
- 逐步积累证据
- 如果兼容性问题确实是间歇性的，可以逐步恢复信心

### 路线 B：切换官方 Claude Code 模型验证闭环

**说明**：在真实执行阶段临时使用官方 Anthropic Claude 模型，验证完整闭环。

**优点**：
- 最接近 Claude Code 原生能力
- tool-use 兼容性风险最低
- 最快验证自动化闭环
- 可以用最少的时间证明系统设计可行

**缺点**：
- 需要 Anthropic API Key 和网络访问
- 官方 Claude API 成本较高
- 用户当前主要使用智谱
- 网络可能受限（需要代理或 VPN）
- 不是长期方案

**适合**：
- 需要快速证明系统闭环时
- 作为路线 A 的对照实验
- 确认问题确实在智谱代理而非系统本身

### 路线 C：改造 runner，让模型只输出 patch，由 runner 自己写文件

**说明**：不依赖 Claude Code 的 Write/Bash 工具，改为模型只生成 patch/diff/JSON plan，由 runner 自己应用文件修改。

**优点**：
- 完全绕开 Claude Code tool-use 兼容问题
- 更适配国内模型 API
- 长期更可控，不依赖第三方兼容性
- 可实现更精细的权限控制和沙箱

**缺点**：
- 架构改动大（需要实现 patch parser / file writer / sandbox）
- 需要设计 prompt 模板让模型生成结构化 patch
- 短期不适合作为下一步
- 与当前 Claude Code agentic coding 路线方向不同

**适合**：
- 长期自动化增强方向
- 如果智谱 tool-use 兼容性短期无法解决
- 需要更可控的文件修改机制

## Recommended Strategy

```text
SHORT_TERM=A_WITH_LAYERED_STABILITY_VALIDATION
BACKUP=B_OFFICIAL_CLAUDE_FOR_LOOP_PROOF
LONG_TERM=C_RUNNER_APPLIES_PATCH
```

### 短期：路线 A — 分层稳定性验证

1. 执行 Layer 1-4，逐步验证 tool-use 兼容性
2. 每层通过后才进入下一层
3. 任何一层失败，停止并进入路线决策

### 备用：路线 B — 官方 Claude 验证闭环

- 如果路线 A 在 Layer 2 就失败，考虑路线 B
- 临时切换官方 Claude，执行一次完整闭环
- 验证系统设计可行，再决定长期方向
- 不需要长期使用官方 Claude，只用于验证

### 长期：路线 C — Runner 自执行 Patch

- 无论短期选择哪条路线，长期都应考虑路线 C
- 绕开 tool-use 依赖，让系统更自主
- 可以在路线 A/B 验证通过后，并行推进路线 C

## Decision Needed

T110 应该是路线决策任务，不直接执行真实任务。

T110 应输出：

```text
DECISION_OPTION=A/B/C
REASON=<reason>
NEXT_EXECUTION_ALLOWED=yes/no
NEXT_SMOKE_TEST_PLAN=<plan>
```

## Final Status

```text
T109_ASSESSMENT_STATUS=done
ZHIPU_TEXT_ONLY_COMPATIBILITY=pass
ZHIPU_TOOL_USE_COMPATIBILITY=unstable
FULL_RUN_PROJECT_TASK_FULL_COMPATIBILITY=not_stable
RECOMMENDED_SHORT_TERM=A_WITH_LAYERED_STABILITY_VALIDATION
RECOMMENDED_BACKUP=B_OFFICIAL_CLAUDE_FOR_LOOP_PROOF
RECOMMENDED_LONG_TERM=C_RUNNER_APPLIES_PATCH
NEXT_PENDING=T110
```
