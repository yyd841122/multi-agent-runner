# Planner Agent 自动拆解输出

## 调用信息

- provider: mock
- model: mock-planner
- agent: planner
- success: True
- timestamp: 2026-05-03T19:55:19.390608

## 模型响应内容

[MOCK MODEL RESPONSE]

agent: planner
provider: mock
model: mock-planner
temperature: 0.2

收到的 prompt 摘要：
你是 Planner Agent。

你的任务是根据以下项目需求，生成一份任务拆解草案。

## 输出格式要求

请严格按照以下格式输出：

# Planner Agent Output

## Agent

Planner Agent

## Task

任务：根据项目需求生成任务清单草案

## Status

PASS / FAIL / RETRY / BLOCKED / INFO

## ...

system_prompt: 你是 Planner Agent，负责根据项目需求生成任务清单草案。输出必须严格遵循指定的 markdown 格式。

这是 mock 响应，不会调用真实 API。
要启用真实 API，请修改 config.yaml 中的 provider 配置。

