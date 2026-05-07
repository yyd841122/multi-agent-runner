# Real Execution Route Decision

## Background

multi-agent-runner 项目使用 Claude Code CLI + 智谱代理（glm-5.1, `open.bigmodel.cn/api/anthropic`）作为 Developer Agent 执行引擎。

在 Stage 7 真实执行验证过程中，发现了 Claude Code + 智谱代理的 tool-use 兼容性问题：

- **T100**：框架级真实任务，`run-project-task-full` 调用 Claude Code，600 秒超时
- **T102**：G008 极小 smoke task（只创建一个 marker 文件），同样 600 秒超时
- **T103**：系统化诊断，定位根因为 acceptEdits + tool-use 超时
- **T104**：设计修复方案，推荐短期 B+A（可配置 permission mode）+ 中期 D（评估兼容性）
- **T105-T106**：设计并实现 configurable Claude permission mode
- **T107**：验证 default mode 最小文本调用正常
- **T108**：回归验证 acceptEdits + tool-use，**unexpected_pass**（超时不再复现）
- **T109**：评估智谱代理兼容性，text-only pass、tool-use unstable、full execution not_stable

## Evidence Summary

| Task | Scenario | Result | Meaning |
|------|----------|--------|---------|
| T100 | full run-project-task-full (框架级) | timeout (600s) | full real execution not stable |
| T102 | G008 smoke task (极小) | timeout (600s) | minimal full loop not stable |
| T103 | acceptEdits + tool-use (创建文件) | timeout (120s) | compatibility issue observed |
| T103 | default text-only | pass | text-only path OK |
| T103 | acceptEdits text-only | pass | text-only path OK |
| T107 | default text-only | pass | text-only path OK |
| T108 | default text-only | pass | text-only path OK |
| T108 | acceptEdits text-only | pass | text-only path OK |
| T108 | acceptEdits + tool-use (创建文件) | unexpected_pass | issue not deterministic |
| T109 | compatibility assessment | unstable | layered validation recommended |

### 关键证据链

1. **text-only 链路稳定**：T103/T107/T108 三次验证，default 和 acceptEdits 模式下纯文本输出均秒级返回
2. **tool-use 兼容性不稳定**：T103 超时 vs T108 通过，相同测试场景不同结果
3. **full execution 未验证**：T100/T102 均超时，run-project-task-full 完整闭环仍未成功
4. **T108 单次 unexpected_pass 不具备统计意义**：不能当作兼容性已修复的证据

## Route Options

### 路线 A：继续智谱代理，先做分层稳定性验证

继续使用当前 Claude Code + 智谱代理环境，先不恢复 run-project-task-full，先执行 Layer 1-3 稳定性验证。

**优点：**
- 符合当前用户实际环境，不需要切换账号或模型
- 可以逐步定位稳定性
- 成本相对可控（智谱 API 费用较低）
- 如果验证通过，直接恢复真实任务执行

**缺点：**
- 仍有间歇性超时风险
- 可能再次触发 5 小时限制
- 需要更多诊断任务

**适用：**
- 当前最现实的短期路线
- 逐步积累证据

### 路线 B：切换官方 Claude Code 模型验证完整闭环

真实执行阶段临时切换官方 Anthropic Claude 模型，验证完整闭环。

**优点：**
- 最接近 Claude Code 原生能力
- tool-use 兼容性风险最低
- 最快验证系统架构是否正确

**缺点：**
- 用户当前主要使用智谱
- 可能有账号 / 成本 / 网络 / 可用性限制
- 不是长期方案

**适用：**
- 需要快速验证 multi-agent-runner 架构闭环时
- 作为路线 A 的对照实验

### 路线 C：runner 自执行 patch，模型只输出计划 / diff

不依赖 Claude Code tool-use 写文件，模型只输出结构化 patch / JSON plan / diff，runner 自己负责文件修改。

**优点：**
- 绕开 Claude Code + 智谱 tool-use 兼容性问题
- 长期更适合国内模型 API
- 更可控，更容易实现 checkpoint / resume

**缺点：**
- 架构改动大（需要 patch parser / sandbox / file writer / rollback 机制）
- 需要设计 prompt 模板让模型生成结构化 patch
- 短期不适合马上做

**适用：**
- 长期无人值守自动化方向

## Decision

```text
DECISION_OPTION=A
DECISION_NAME=Continue Zhipu proxy with layered stability validation
NEXT_EXECUTION_ALLOWED=no
NEXT_REAL_TASK_ALLOWED=no
NEXT_SMOKE_TEST_ALLOWED=no
```

### Reason

1. T108 出现 unexpected_pass，说明 tool-use 不一定完全不可用，不能判定为"不可修复"
2. 但 T100/T102 真实任务仍未稳定通过，不能直接恢复 run-project-task-full
3. T103/T108 结果不一致，说明兼容性存在间歇性，需要多次验证确认稳定性
4. 路线 A 符合当前用户实际环境，成本最低，可以逐步积累证据
5. 分层验证可以科学评估 tool-use 兼容性，避免再次盲目超时浪费额度

### 为什么不选择路线 B

- 用户当前主要使用智谱代理，切换到官方 Claude 需要解决网络和成本问题
- 路线 B 适合作为备用方案：如果路线 A 在 Layer 2 就失败，再考虑切换官方 Claude
- 路线 B 的价值在于"验证系统架构闭环"，而非"解决智谱兼容性"

### 为什么不选择路线 C

- 路线 C 架构改动大，短期不适合
- 但路线 C 是长期方向，可以在路线 A/B 验证通过后并行推进

## Safety Rules

1. **不直接恢复 run-project-task-full**
   - 必须先通过 Layer 1-3 稳定性验证
   - Layer 4 (full loop smoke) 需要人工决策

2. **不继续盲目真实任务执行**
   - 不执行 T100/T102 级别的真实任务
   - 不使用 bypassPermissions

3. **不自动进入 smoke task**
   - Layer 1-3 通过后，Layer 4 需要人工决策（T116）

4. **不自动 Git backup**
   - 稳定性验证产生的临时文件需要人工清理

5. **不使用 bypassPermissions**
   - 稳定性验证使用 default / acceptEdits 模式

6. **先做 Layer 1-3**
   - Layer 1：text-only stability（连续 3 次 default + 3 次 acceptEdits）
   - Layer 2：single-file tool-use stability（最多 3 次 acceptEdits + 创建临时文件）
   - Layer 3：runner-level smoke（runner 封装调用 Claude Code，不进入 full loop）

7. **任何一层失败，停止后续验证，进入路线决策**
   - 如果路线 A 在 Layer 2 就失败 → 考虑路线 B
   - 如果路线 A 在 Layer 3 失败 → 考虑路线 B 或路线 C

## Next Task Roadmap

| Task | 角色 | 目标 | 依赖 |
|------|------|------|------|
| T111 | Architect | 设计 layered Claude Code stability validation protocol | T110 |
| T112 | Developer | 实现 text-only stability check dry-run/report | T111 |
| T113 | Tester | 执行 Layer 1 text-only stability validation | T112 |
| T114 | Tester | 执行 Layer 2 controlled single-file tool-use stability validation | T113 |
| T115 | Tester | 执行 Layer 3 runner-level minimal Claude call validation | T114 |
| T116 | Human | 人工决策是否恢复 G008/G009 run-project-task-full smoke test | T115 |

### 任务说明

- **T111**：设计分层稳定性验证的详细协议，包括每层的测试命令、通过标准、失败处理
- **T112**：实现 text-only 稳定性验证的 dry-run 和报告生成
- **T113**：执行 Layer 1 文本输出稳定性验证（6 次调用，全部秒级返回）
- **T114**：执行 Layer 2 单文件 tool-use 稳定性验证（最多 3 次，记录 pass/timeout/fail）
- **T115**：执行 Layer 3 runner 封装最小调用验证
- **T116**：人工决策点，基于 Layer 1-3 结果决定是否恢复 full loop smoke test

## Later Decision Points

### 如果 Layer 1 失败

- 智谱代理 text-only 也不稳定 → 考虑切换官方 Claude 或检查网络环境
- 这是最低层，失败意味着基础链路有问题

### 如果 Layer 2 失败

- acceptEdits + tool-use 确认不稳定 → 考虑路线 B（切换官方 Claude 验证闭环）
- 也可以考虑路线 C（长期方案提前启动）

### 如果 Layer 3 失败

- runner 封装调用有问题 → 排查 runner → claude_code_runner → subprocess 链路
- 可能需要调整 runner 调用方式或参数

### 如果 Layer 1-3 全部通过

- 进入 Layer 4（run-project-task-full smoke）需要人工决策
- Layer 4 通过后，恢复真实任务执行

## Final Status

```text
T110_DECISION_STATUS=done
DECISION_OPTION=A
DECISION_NAME=Continue Zhipu proxy with layered stability validation
NEXT_EXECUTION_ALLOWED=no
NEXT_REAL_TASK_ALLOWED=no
NEXT_SMOKE_TEST_ALLOWED=no
NEXT_PENDING=T111
NEXT_STAGE=Stage 7
```
