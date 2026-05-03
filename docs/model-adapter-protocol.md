# Model Adapter Protocol

## 1. 协议目标

多模型 API 适配器为 Planner / Reviewer / Main Agent 等"大脑型" Agent 提供统一的模型调用接口。

- Developer Agent 继续使用 Claude Code（可能使用 GLM）执行代码
- Planner / Reviewer / Main 等 Agent 通过 model_adapter 调用国内模型 API
- 不同 Agent 可以配置不同模型，避免单一模型风险

## 2. 为什么需要多模型

单一模型存在以下问题：

1. **自己审自己** — 如果 Developer 和 Reviewer 使用同一模型，审查缺乏独立性
2. **单点故障** — 一个模型 API 挂了，整个流程阻塞
3. **能力差异** — 不同模型在不同任务上各有优势（如 DeepSeek 擅长推理，Qwen 擅长中文）
4. **限额分摊** — 多模型可以分摊 API 调用量，避免单一模型限额

## 3. 模型角色分离原则

| Agent | 用途 | 模型要求 | 当前配置 |
|-------|------|----------|----------|
| Developer | 代码执行 | 强编码能力 | Claude Code（GLM） |
| Planner | 任务拆解 | 强规划能力 | 可配置（mock / zhipu / deepseek） |
| Reviewer | 代码审查 | 强推理 + 独立于 Developer | **不应与 Developer 同模型** |
| Main | 调度决策 | 轻量推理 | 可配置（mock） |
| Tester | 测试生成 | 逻辑推理 | 可配置（mock） |
| Reporter | 总结报告 | 中文生成 | 可配置（mock） |

## 4. Developer / Reviewer 模型分离

**核心原则：Reviewer 不应默认使用与 Developer 执行器相同的模型。**

原因：

1. 审查的独立性 — 如果 Developer 代码有系统性偏差，同模型审查可能无法发现
2. 视角多样性 — 不同模型对同一代码有不同的理解和判断
3. 避免共犯 — 同一模型的训练数据和方法可能导致相同的盲点

**建议配置：**

| Developer 模型 | 建议 Reviewer 模型 |
|----------------|-------------------|
| Claude Code (GLM) | DeepSeek / Qwen / Kimi |
| DeepSeek | Qwen / Kimi / GLM |
| Qwen | DeepSeek / Kimi / GLM |

## 5. 配置结构

config.yaml 中的模型配置分为三层：

```yaml
models:           # 第一层：Agent 到模型的映射
  default_provider: mock
  planner:
    provider: mock
    model: mock-planner
  reviewer:
    provider: mock
    model: mock-reviewer

providers:        # 第二层：Provider 连接配置
  mock:
    enabled: true
  deepseek:
    enabled: false
    api_key_env: DEEPSEEK_API_KEY
    base_url: "https://api.deepseek.com"
    default_model: "deepseek-chat"
```

**查找优先级：**

1. `models.<agent>.provider` — Agent 级别指定 provider
2. `models.default_provider` — 默认 provider
3. `mock` — 最终兜底

## 6. Agent 到模型的映射规则

```
call_model(ModelRequest(agent="reviewer", prompt="..."))
    ↓
读取 config.yaml
    ↓
查找 models.reviewer → provider: mock, model: mock-reviewer
    ↓
查找 providers.mock → enabled: true
    ↓
路由到 call_mock_provider()
    ↓
返回 ModelResponse
```

**错误处理：**

| 场景 | 处理 |
|------|------|
| Agent 未配置 | 使用 default_provider |
| Provider 不存在 | 返回 success=False，error="未知 provider" |
| Provider 未启用 | 返回 success=False，error="未启用" |
| Provider 未实现 | 返回 success=False，error="NotImplementedError" |

## 7. Provider 设计

| Provider | 状态 | API 格式 | 说明 |
|----------|------|----------|------|
| `mock` | 已实现 | 无 | 本地测试用，不调用外部 API |
| `zhipu` | 预留 | OpenAI 兼容 | 智谱 GLM 系列 |
| `deepseek` | 预留 | OpenAI 兼容 | DeepSeek 系列 |
| `kimi` | 预留 | OpenAI 兼容 | Moonshot 系列 |
| `qwen` | 预留 | OpenAI 兼容 | 通义千问系列 |

所有国内模型 Provider 都使用 OpenAI 兼容格式（`/v1/chat/completions`），实现时可用 `openai` 库或直接 `requests` 调用。

**Provider 函数签名：**

```python
def call_<provider>_provider(
    request: ModelRequest,
    provider_config: dict,
    model_config: dict,
) -> ModelResponse
```

## 8. API Key 管理规则

1. **API Key 不写入任何文件** — 只从环境变量读取
2. **config.yaml 中只记录环境变量名** — 如 `api_key_env: DEEPSEEK_API_KEY`
3. **运行时从 `os.environ` 读取** — 如 `os.environ.get("DEEPSEEK_API_KEY")`
4. **API Key 缺失时给出明确错误** — 不静默失败

## 9. Mock Provider 的作用

Mock Provider 在以下场景中使用：

1. **本地开发测试** — 无需真实 API Key 即可验证流程
2. **CI/CD 环境** — 不依赖外部服务
3. **新 Agent 开发** — 先用 mock 验证接口，再接入真实模型
4. **演示和文档** — 展示调用流程而不产生费用

Mock Provider 的返回内容包含：

- agent 名称
- provider 和 model 信息
- prompt 摘要
- 明确标注"这是 mock 响应"

## 10. 后续真实 API 接入计划

| 阶段 | 任务 | Provider | 说明 |
|------|------|----------|------|
| T016（当前） | 多模型适配器 MVP | mock | 接口设计 + mock 实现 |
| T017 | Planner Agent 自动拆解 | zhipu 或 deepseek | 第一个真实 API 调用 |
| T021 | Reviewer Agent 自动审查 | deepseek 或 qwen | Reviewer 使用不同模型 |
| 后续 | 真实 API provider 实现 | 全部 | 逐个实现各 provider 的真实调用 |
