# G002 Review Report

## Model Result

- provider: mock
- model: mock-reviewer
- success: True

## Reviewer Output

[MOCK MODEL RESPONSE]

agent: reviewer
provider: mock
model: mock-reviewer
temperature: 0.2

收到的 prompt 摘要：
你是 Reviewer Agent。

你的任务是审查 G002 的开发完成情况，判断是否符合任务验收标准。

## 输出格式要求

请严格按照以下格式输出：

# Reviewer Agent Output

## Agent

Reviewer Agent

## Task

任务编号：G002
任务名称：（从任务块中提取）

## Status

PASS / FAIL / RETRY / ...

system_prompt: 你是 Reviewer Agent，负责审查任务完成情况。输出必须严格遵循指定的 markdown 格式。

这是 mock 响应，不会调用真实 API。
要启用真实 API，请修改 config.yaml 中的 provider 配置。


## Source Files Reviewed

- index.html
- style.css
- script.js
- G002-dev-report.md
- docs/tasks.md
