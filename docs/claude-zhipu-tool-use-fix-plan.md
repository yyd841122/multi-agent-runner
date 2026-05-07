# Claude Code + Zhipu Tool-use Compatibility Fix Plan

## Background

### T100 / G008 超时

- T100（框架级任务，矛盾 prompt）通过 `run-project-task-full` 调用 Claude Code，600 秒超时（returncode=124）
- G008（极小 smoke marker 任务，只创建一个文件，prompt 无歧义）通过 `run-project-task-full` 调用 Claude Code，600 秒超时（returncode=124）
- 两个任务复杂度差异巨大但都超时，说明根因不在任务大小或 prompt 质量

### T103 诊断结论

- Claude CLI 正常（2.1.104）
- 纯文本输出正常（默认模式和 acceptEdits 模式均秒级返回）
- acceptEdits + tool use（Write/Bash）→ 120 秒超时
- 默认模式 + tool use → 权限拒绝后正常返回
- 使用智谱云端直连（`open.bigmodel.cn/api/anthropic`），模型 glm-5.1

## Root Cause Summary

Claude Code 在 `--permission-mode acceptEdits` 模式下尝试调用工具（Write、Bash 等）时，与智谱 API 之间出现兼容性问题：

1. Claude Code 发送请求到智谱 API
2. 智谱 API 返回包含 `tool_use` 的响应
3. Claude Code 在本地执行工具（如 Write 文件）
4. Claude Code 将工具结果作为 `tool_result` 消息发送回 API
5. **在步骤 5 出现阻塞** — 智谱 API 可能未正确处理 `tool_result` 消息格式，或响应格式与 Claude Code 期望不兼容

关键证据：
- 纯文本回复不需要工具调用 → 秒级返回
- acceptEdits 模式下工具被实际执行 → 需要发回 tool_result 并等待下一轮响应 → 卡住
- 默认模式下工具被权限拒绝 → 不需要发回 tool_result → 正常返回

## Constraints

1. **当前主要使用智谱模型**（glm-5.1），用户有 API 额度和使用习惯
2. **不能继续盲目重跑真实任务**，每次超时消耗 600 秒和 API 额度
3. **不能马上无人值守执行**，需要先修复 tool use 兼容性
4. **不应直接大改框架**，修复应最小化、可回退
5. **修复前暂停真实任务执行**
6. **所有真实执行恢复前必须重新跑 smoke test**

## Candidate Fix Options

### 方案 A：去掉 acceptEdits，改用默认权限模式

**说明：** 让 Claude Code 不使用 `--permission-mode acceptEdits`，回到默认权限模式。

**优点：**
- 改动最小，只需去掉一个参数
- 已证明默认模式下工具调用被权限拒绝后能正常返回
- 风险极低，可立即验证

**缺点：**
- 无法自动写文件 — Claude Code 只会输出建议代码而不会实际修改文件
- 不符合最终无人值守自动化目标
- 工具调用被拒绝后 Claude Code 可能输出"需要你在提示时允许写入操作"

**适用场景：**
- 短期诊断验证
- 半自动模式（人工确认后手动应用变更）
- 确认问题确实出在 acceptEdits + tool use 而非其他环节

**验证命令：**
```bash
claude --print "在 /tmp 目录下创建一个名为 test.txt 的文件"
```

---

### 方案 B：新增 runner 调用模式参数（可配置 permission mode）

**说明：** 在 `run_claude_code()` 中新增可配置的 permission mode 参数，支持 default / acceptEdits / bypassPermissions 等模式切换。

**优点：**
- 不写死 acceptEdits，方便不同环境切换
- 可以在智谱代理环境下回退到 default 模式
- 后续可逐步测试 bypassPermissions 等模式
- 改动量可控（修改 run_claude_code 函数签名 + 配置）

**缺点：**
- 仍然不能保证智谱代理支持 tool use
- 需要修改框架代码（runner.py 或 claude_code_runner.py）
- default 模式下无法自动写文件

**适用场景：**
- 当前项目最小修复方向
- 为后续 mode 切换提供基础设施
- 与方案 A 配合使用：先可配置，再选择合适的 mode

**改动范围：**
- `tools/claude_code_runner.py`：run_claude_code() 新增 permission_mode 参数
- `tools/full_task_runner.py`：传递 permission_mode
- `runner.py`：新增 --claude-permission-mode CLI 参数
- 配置文件可选：project.yaml 或 config.yaml

---

### 方案 C：改造子进程调用方式

**说明：** 改变 Claude Code subprocess 调用方式，例如使用 stdin 传递 prompt、使用临时 prompt 文件等。

**优点：**
- 解决长 prompt 命令行参数问题
- 日志更清晰
- 避免编码问题

**缺点：**
- **T103 已证明极短写文件 prompt 也会超时**（诊断测试 3 使用极简 prompt 仍然 120 秒超时）
- 这不是根因，只能作为辅助优化
- 不解决 acceptEdits + tool use 兼容性问题

**适用场景：**
- 后续稳定性优化
- 与方案 B/D 配合使用
- 不适合作为主要修复方向

---

### 方案 D：更换智谱代理模型 / API 兼容层

**说明：** 检查并修复智谱 API 对 Anthropic tool_use / tool_result 消息格式的兼容性。

**优点：**
- 可能从根上解决 tool-use 兼容性问题
- 修复后 acceptEdits 模式可正常使用
- 不需要修改框架逻辑

**缺点：**
- 需要外部调查（智谱 API 文档、兼容性报告、社区反馈）
- 不一定能在项目代码内解决
- 可能需要更换模型映射或代理层
- 需要智谱方面的配合或文档确认

**调查方向：**
1. 检查智谱 API 文档中 Anthropic 兼容层的 tool_use / tool_result 支持
2. 尝试不同模型（glm-4.7 vs glm-5.1）
3. 尝试不同 API endpoint
4. 检查智谱 API 是否有 tool_use 相关已知问题
5. 查看社区是否有类似报告

**适用场景：**
- 如果本地代码绕不过 tool_result 兼容问题
- 中期主要修复方向
- 需要先做兼容性评估（T109）

---

### 方案 E：真实执行层改用非 Claude Code 写文件机制

**说明：** 不依赖 Claude Code 的 Write/Bash 工具，改为模型只生成 patch / diff / JSON plan，由 runner 自己应用文件修改。

**优点：**
- 完全绕开 Claude Code tool-use，从根上消除兼容性问题
- runner 对文件修改有完全控制权
- 更适合国内模型 API（不依赖完整 tool_use 支持）
- 可实现更精细的权限控制和沙箱

**缺点：**
- 架构改动较大（需要实现 patch parser / file writer / sandbox）
- 需要设计 prompt 模板让模型生成结构化 patch
- 短期不适合马上实现
- 与当前 Claude Code agentic coding 路线方向不同

**适用场景：**
- 长期自动化增强路线
- 如果智谱 tool-use 兼容性短期无法解决
- 如果需要更可控的文件修改机制

**实现路线：**
1. 设计 patch 输出协议（模型生成标准格式 patch）
2. 实现 patch parser（解析模型输出为文件操作列表）
3. 实现 file writer（应用文件修改，含权限检查）
4. 实现 sandbox（限制修改范围）
5. 替换 run_claude_code 中的 tool-use 部分

---

### 方案 F：真实执行层暂时切换官方 Claude Code 模型

**说明：** 在真实执行阶段使用官方 Anthropic Claude 模型，规划/审查阶段继续使用智谱模型。

**优点：**
- 兼容性最好，Claude Code 原生支持
- 最快验证自动化闭环
- 不需要修改 tool-use 调用逻辑

**缺点：**
- 需要 Anthropic API Key 和网络访问
- 成本较高（官方 Claude API 计费）
- 用户当前主要使用智谱
- 网络可能受限（需要代理或 VPN）

**适用场景：**
- 如果智谱 tool-use 兼容性短期无法解决
- 需要尽快验证完整自动化闭环
- 作为过渡方案使用

**实现路线：**
1. 配置 ANTHROPIC_BASE_URL 指向官方 API
2. 配置 ANTHROPIC_AUTH_TOKEN 为官方 Key
3. 配置 ANTHROPIC_MODEL 为官方模型
4. 执行验证
5. 验证完成后切回智谱

---

## Recommended Strategy

### 短期（T105-T108）：方案 B + A — 可配置 permission mode + 诊断验证

1. **T105**：设计 configurable Claude permission mode
2. **T106**：实现 run_claude_code permission mode 配置
3. **T107**：验证 default mode 下最小 Claude Code 调用行为
4. **T108**：验证 acceptEdits 仍然 blocked，形成兼容性记录

短期目标：让 permission mode 可配置，确认 default mode 是否可以作为临时回退。

### 中期（T109）：方案 D — 评估智谱 API tool_use/tool_result 兼容性

5. **T109**：评估智谱代理 tool_use/tool_result 兼容性

中期目标：搞清楚智谱 API 是否支持 tool_use，如果不支持则确定替代方案。

### 长期（T110）：决策 — 确定真实执行路线

6. **T110**：决策真实执行路线

三种可能结论：
- **路线 1**：智谱修复 tool-use → 继续使用 acceptEdits + 智谱
- **路线 2**：智谱不支持 → 切换官方 Claude（方案 F）或实现 runner 自执行 patch（方案 E）
- **路线 3**：混合模式 → 规划/审查用智谱，执行用官方 Claude

### 备用：方案 F — 切换官方 Claude 模型

如果中期评估确认智谱短期无法修复 tool-use 兼容性，可使用方案 F 作为过渡。

### 未来增强：方案 E — runner 自执行 patch

长期自动化增强方向，不依赖 Claude Code tool-use。

## Immediate Next Tasks

| 任务 | 角色 | 目标 | 依赖 |
|------|------|------|------|
| T105 | Architect | 设计 configurable Claude permission mode | T104 完成 |
| T106 | Developer | 实现 run_claude_code permission mode 配置 | T105 完成 |
| T107 | Tester | 验证 default mode 最小 Claude Code 调用 | T106 完成 |
| T108 | Tester | 验证 acceptEdits tool-use blocked 回归 | T107 完成 |
| T109 | Researcher | 评估智谱代理 tool_use/tool_result 兼容性 | T108 完成 |
| T110 | Decision | 决策真实执行路线 | T109 完成 |

**关键约束：**
- T105/T106 先不改变默认行为（保持 acceptEdits），避免破坏已有逻辑
- T107 只做诊断验证，不跑真实大任务
- T108 明确记录 acceptEdits 当前是 blocked
- T110 形成正式路线决策文档

## Safety Rules

1. **修复前暂停真实任务执行** — 不执行 run-project-task-full
2. **只允许最小诊断命令** — 不执行复杂自动化
3. **不允许继续 acceptEdits 写文件测试** — 已确认会超时
4. **不允许自动进入真实执行** — 需人工确认
5. **所有真实执行恢复前必须重新跑 smoke test** — 验证修复有效
6. **不允许修改 runner.py / tools/*.py** — T105/T106 才修改
7. **不允许修改 .claude/settings.json** — 不修改 Claude 配置

## Decision Needed Later

以下问题需要在 T110 或之前由人工决策：

1. **是否继续用智谱做 Claude Code tool-use？**
   - 取决于 T109 兼容性评估结果
   - 如果智谱确认支持但需要配置调整 → 继续用智谱
   - 如果智谱确认不支持 → 考虑方案 E 或 F

2. **是否切换官方 Claude Code？**
   - 取决于网络条件、成本预算和 API Key 可用性
   - 官方模型兼容性最好，但有成本和网络限制

3. **是否让 runner 自己应用 patch？**
   - 取决于长期自动化规划
   - 方案 E 改动大但自主性高
   - 适合长期投入但不适合短期修复

4. **是否继续追求无人值守真实执行？**
   - 当前框架已支持 dry-run 和 safety shell
   - 真实执行需要 tool-use 兼容性
   - 如果无法解决，可以降级为半自动模式（人工确认后应用变更）

5. **方案 B 的 default mode 是否作为长期模式使用？**
   - default mode 无法自动写文件
   - 但可以配合方案 E（模型生成 patch + runner 应用）形成新路线

## Final Status

```text
T104_FIX_PLAN_STATUS=done
RECOMMENDED_SHORT_TERM=B_PLUS_A
RECOMMENDED_MID_TERM=D
RECOMMENDED_LONG_TERM=E
REAL_TASK_EXECUTION=no
RUN_PROJECT_TASK_FULL_CALLED=no
CLAUDE_CODE_CALLED=no
NEXT_PENDING=T105
```
