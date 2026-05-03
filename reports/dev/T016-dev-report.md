# T016 开发报告 — 多模型 API 适配器 MVP

## 任务信息

- 任务编号：T016
- 角色：Developer Agent
- 状态：完成

## 修改文件列表

| 文件 | 改动说明 |
|------|----------|
| `docs/tasks.md` | T016 状态更新为 in_progress，更新验收标准 |
| `config.yaml` | 扩展模型配置，支持多 provider、多 Agent 独立配置 |
| `tools/model_adapter.py` | 完整实现多模型适配器（mock provider + 4 个预留 provider） |
| `docs/model-adapter-protocol.md` | 新建 — 模型适配器协议文档（10 个章节） |
| `reports/dev/T016-dev-report.md` | 新建 — 开发报告 |

## 完成内容

- 定义 `ModelRequest` / `ModelResponse` 数据结构
- 实现 `load_model_config()` — 读取 config.yaml 模型配置
- 实现 `get_agent_model_config()` — 根据 agent 名称查找模型配置
- 实现 `call_model()` — 统一模型调用入口，自动路由到对应 provider
- 实现 `call_mock_provider()` — 本地 mock，无需 API Key
- 预留 4 个 provider 函数：zhipu / deepseek / kimi / qwen
- 实现 `model_test()` — 本地测试函数
- 扩展 config.yaml：Agent 级别模型配置 + Provider 连接配置
- 明确 Reviewer 不默认使用 Developer 同款模型的设计原则

## 验收标准自查

- [x] 更新 config.yaml，支持不同 Agent 配置不同模型
- [x] 实现 tools/model_adapter.py 的统一接口
- [x] 至少支持 mock provider，用于本地无 API Key 测试
- [x] 预留 zhipu / deepseek / kimi / qwen provider 结构
- [x] 明确 Reviewer 不默认使用 Developer 同款模型
- [x] 创建 docs/model-adapter-protocol.md
- [x] 不接入 runner.py 主流程

## 本地测试结果

测试命令：

```python
from tools.model_adapter import ModelRequest, call_model
r = call_model(ModelRequest(agent='reviewer', prompt='测试 Reviewer 模型适配器'))
print(r)
```

预期：`success=True`，`provider='mock'`，`model='mock-reviewer'`

## 是否完成

是。
