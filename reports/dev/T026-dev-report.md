# T026 开发报告 — 接入真实 Reviewer 模型配置

## 任务信息

- 任务编号：T026
- 角色：Developer Agent
- 状态：完成

## 修改文件列表

| 文件 | 改动说明 |
|------|----------|
| `docs/tasks.md` | T026 状态从 pending → in_progress → done |
| `config.yaml` | reviewer.provider 改为 deepseek，新增 fallback_provider 和 timeout_seconds |
| `tools/model_adapter.py` | 实现 call_deepseek_provider 真实 API 调用 + save_model_test_output |
| `reports/model/deepseek-reviewer-test-output.md` | 新建 — 无 Key 测试结果 |
| `reports/dev/T026-dev-report.md` | 新建 — 开发报告 |

## 完成内容

### config.yaml 改动

- `reviewer.provider`: mock → deepseek
- `reviewer.model`: mock-reviewer → deepseek-chat
- `reviewer.fallback_provider`: mock（新增）
- `providers.deepseek.enabled`: false → true
- `providers.deepseek.timeout_seconds`: 60（新增）

### tools/model_adapter.py 改动

1. **call_deepseek_provider** — 从 NotImplementedError 桩改为完整实现：
   - 从环境变量 `DEEPSEEK_API_KEY` 读取 API Key
   - 使用 `urllib.request` 构建 POST 请求（无新依赖）
   - 请求 `https://api.deepseek.com/chat/completions`
   - 发送 OpenAI-compatible Chat Completions 格式
   - 解析 `choices[0].message.content` 作为响应内容
   - 三层错误处理：缺少 Key → HTTPError → URLError → 通用异常
   - 不让异常导致程序崩溃，统一返回 ModelResponse

2. **save_model_test_output** — 新增函数：
   - 接收 ModelResponse，输出到 markdown 文件
   - 自动创建父目录
   - 包含 provider / model / success / content / error / raw 字段

## 验收标准自查

- [x] config.yaml 中 reviewer provider 可以配置为 deepseek
- [x] tools/model_adapter.py 实现 DeepSeek provider
- [x] DeepSeek API Key 从 DEEPSEEK_API_KEY 环境变量读取
- [x] 不写入真实 API Key
- [x] 保留 mock provider 回退能力
- [x] 可以运行本地 DeepSeek Reviewer 连接测试
- [x] 可以保存 reports/model/deepseek-reviewer-test-output.md
- [x] 不接入自动审查主流程

## 本地无 API Key 测试结果

```
provider=deepseek
model=deepseek-chat
success=False
error=缺少环境变量 DEEPSEEK_API_KEY
```

验证通过：无 Key 时稳定返回失败信息，不崩溃。

## 真实 API Key 测试方式

用户在 PowerShell 中执行：

```powershell
$env:DEEPSEEK_API_KEY="你的 DeepSeek API Key"
python -c "from tools.model_adapter import ModelRequest, call_model, save_model_test_output; r=call_model(ModelRequest(agent='reviewer', prompt='请只回复：DeepSeek Reviewer 连接成功')); print(r); save_model_test_output(r, 'reports/model/deepseek-reviewer-test-output.md')"
```

预期结果：

```
success=True
provider=deepseek
model=deepseek-chat
content 中包含 "DeepSeek Reviewer 连接成功"
```

## 限制遵守

- 未写入真实 API Key
- 未接入自动审查主流程
- 未修改 reviewer_runner.py
- 未修改小游戏项目
- 未执行 run-project-next
- 未自动返工
- 未让 DeepSeek 修改代码
- 只实现 DeepSeek provider 和连接测试能力
- 保留 mock provider
- 所有文档使用简体中文
- 文件名、路径、代码关键字保持英文

## 是否完成

是。
