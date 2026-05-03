# Workflow Protocol

## 1. 协议目标

workflow 文件是项目自动化执行的总纲。它定义一个项目需要哪些 Agent、经历哪些阶段、每个阶段的输入输出和验收标准，以及执行策略和安全规则。

workflow 文件 **不是业务代码**，它是自动化协作协议。Main Agent / runner 通过读取 workflow 文件来理解项目如何执行。

当前第一版只创建协议文件和说明文档，不接入 runner.py。后续 T014 / T015 / T016 / T017 会逐步使用它。

## 2. workflow 基本信息

```yaml
workflow:
  id: <唯一标识>
  name: <显示名称>
  version: <语义版本号>
  description: <简要说明>
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `id` | 是 | 唯一标识，用于 runner 引用和日志记录 |
| `name` | 是 | 显示名称，用于报告和日志 |
| `version` | 是 | 语义版本号，便于后续迭代追踪 |
| `description` | 否 | 简要说明该工作流的适用场景 |

## 3. project_type 项目类型

```yaml
project_type:
  category: <项目类别>
  platform: <目标平台>
  stack:
    - <技术栈>
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `category` | 是 | 项目类别：game / web_app / api / mobile / desktop |
| `platform` | 是 | 目标平台：web / android / ios / windows / linux |
| `stack` | 是 | 技术栈列表，如 html / css / javascript / python / flutter |

扩展示例：

```yaml
# 前端项目
project_type:
  category: web_app
  platform: web
  stack:
    - react
    - typescript
    - tailwindcss

# 后端 API
project_type:
  category: api
  platform: server
  stack:
    - python
    - fastapi
    - sqlalchemy

# Flutter 移动端
project_type:
  category: mobile
  platform: android
  stack:
    - flutter
    - dart

# ERP 系统
project_type:
  category: web_app
  platform: web
  stack:
    - python
    - fastapi
    - react
    - postgresql
```

## 4. agents Agent 定义

```yaml
agents:
  - id: <Agent 标识>
    name: <显示名称>
    role: <角色描述>
    responsibility:
      - <职责列表>
    must_not:
      - <禁止事项列表>
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `id` | 是 | Agent 标识，与 stages 中引用一致 |
| `name` | 是 | 显示名称 |
| `role` | 是 | 角色描述（一句话） |
| `responsibility` | 是 | 职责列表 |
| `must_not` | 否 | 禁止事项，用于约束 Agent 行为 |

当前定义的 6 个标准 Agent 角色：

| Agent ID | 角色 | 核心职责 |
|----------|------|----------|
| `main` | 调度与决策 | 理解需求、选择工作流、分配任务、判断下一步 |
| `planner` | 任务规划 | 拆解需求为可执行任务、定义顺序和验收标准 |
| `developer` | 开发实现 | 修改代码、创建文件、生成开发报告 |
| `tester` | 测试验证 | 根据验收标准测试、输出测试报告 |
| `reviewer` | 审查评估 | 审查是否偏离需求、给出通过或返工建议 |
| `reporter` | 总结报告 | 汇总结果、记录经验和问题、生成最终报告 |

## 5. stages 阶段定义

```yaml
stages:
  - id: <阶段标识>
    name: <显示名称>
    agent: <执行的 Agent ID>
    input:
      - <输入文件或资源>
    output:
      - <输出文件或资源>
    acceptance:
      - <验收标准列表>
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `id` | 是 | 阶段标识，用于日志和追踪 |
| `name` | 是 | 显示名称 |
| `agent` | 是 | 执行该阶段的 Agent ID（引用 agents 定义） |
| `input` | 是 | 输入文件或资源列表 |
| `output` | 是 | 输出文件或资源列表 |
| `acceptance` | 是 | 验收标准列表 |

阶段之间按 stages 数组顺序执行。前一个阶段的 output 通常是后一个阶段的 input。

特殊路径占位符：

| 占位符 | 说明 |
|--------|------|
| `<task-id>` | 当前任务编号，如 T001 |
| `<stage>` | 当前阶段标识 |

当前定义的 6 个标准阶段：

| 阶段 ID | 名称 | Agent | 核心输出 |
|---------|------|-------|----------|
| `requirement` | 需求确认 | main | docs/requirement.md |
| `planning` | 任务规划 | planner | docs/tasks.md |
| `development` | 开发实现 | developer | 项目文件 + 开发报告 |
| `testing` | 测试验证 | tester | 测试报告 |
| `review` | 审查评估 | reviewer | 审查报告 |
| `reporting` | 阶段总结 | reporter | 阶段总结报告 |

## 6. execution_policy 执行策略

```yaml
execution_policy:
  task_completion_rule:
    required:
      - <必要条件列表>
    completion_evidence:
      <agent_id>:
        - <证据文件路径>
  retry_policy:
    on_missing_evidence: <策略>
    on_failed_execution: <策略>
    max_retry_per_task: <次数>
  safety_rules:
    - <安全规则列表>
```

### 6.1 task_completion_rule 任务完成规则

定义任务何时可以标记为 done。

| 字段 | 说明 |
|------|------|
| `required` | 必须满足的条件列表 |
| `completion_evidence` | 每个 Agent 角色的完成证据文件路径 |

当前 required 条件：

| 条件 | 说明 |
|------|------|
| `process_returncode_zero` | 执行进程退出码为 0 |
| `completion_evidence_exists` | 对应 Agent 的完成证据文件存在 |

### 6.2 retry_policy 重试策略

| 字段 | 说明 |
|------|------|
| `on_missing_evidence` | 缺少完成证据时的策略 |
| `on_failed_execution` | 执行失败时的策略 |
| `max_retry_per_task` | 单个任务最大重试次数 |

当前策略值：

| 策略 | 说明 |
|------|------|
| `retry-current` | 重新执行当前任务 |
| `stop_and_report` | 停止执行并报告问题 |

### 6.3 safety_rules 安全规则

安全规则是硬约束，runner 和所有 Agent 都必须遵守。违反安全规则的行为应被阻止或告警。

当前安全规则：

1. runner.py 是最外层调度器
2. Claude Code 是代码执行器
3. 不允许嵌套调用自动执行命令
4. 任务完成不能只依赖 returncode=0
5. 自动完成任务前必须检查完成证据

## 7. 完成证据规则

完成证据是判断任务是否真正完成的核心机制。退出码为 0 只说明进程正常结束，不代表任务已完成。

每个 Agent 角色对应不同的完成证据文件：

| Agent | 完成证据文件 |
|-------|-------------|
| developer | `reports/dev/<task-id>-dev-report.md` |
| tester | `reports/test/<task-id>-test-report.md` |
| reviewer | `reports/review/<task-id>-review-report.md` |
| reporter | `reports/final/<stage>-summary.md` |

runner.py 在自动标记任务 done 前，必须检查对应 Agent 的完成证据文件是否存在。

## 8. 重试策略

| 场景 | 策略 | 说明 |
|------|------|------|
| 执行成功但缺少完成证据 | `retry-current` | 重新生成 prompt 并重新调用 |
| 执行失败（退出码非 0） | `stop_and_report` | 停止循环并报告问题 |
| 429 限额 | `stop_and_report` | 停止调用，避免浪费 |
| 达到最大重试次数 | `stop_and_report` | 停止重试并报告 |

## 9. 安全规则

安全规则来自第一阶段踩坑记录和实践经验：

1. **runner.py 是最外层调度器。** 所有自动化命令由 runner.py 发起。
2. **Claude Code 是代码执行器。** Claude Code 不做调度，只做执行。
3. **不允许嵌套调用。** Claude Code 执行过程中不能调用 run-current / run-next / retry-current / run-loop。
4. **退出码不等于任务完成。** returncode=0 只说明进程正常结束。
5. **完成证据是安全网。** 自动 done 前必须检查对应证据文件。

## 10. 后续扩展方向

当前第一版是最小可用协议，后续可以扩展：

1. **条件分支** — 根据测试或审查结果决定走不同路径（如返工）
2. **并行阶段** — 支持多个 Agent 并行执行独立任务
3. **环境配置** — 在 workflow 中定义环境变量、依赖安装等
4. **质量门禁** — 定义代码覆盖率、性能指标等自动检查条件
5. **多工作流组合** — 一个项目可以组合多个 workflow（如前端 + 后端）
6. **回滚策略** — 定义任务失败时的回滚机制
7. **自定义 Agent** — 支持用户定义新的 Agent 角色
8. **插件系统** — 支持通过插件扩展 workflow 能力
