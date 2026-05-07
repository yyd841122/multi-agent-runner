# G008：Smoke Test Marker

你现在是 Developer Agent。

## 当前项目

当前项目是 `down-100-floors-game`。
项目路径：`E:\github_project\multi-agent-runner\projects\down-100-floors-game`

## 当前任务

G008：Smoke Test Marker

## 任务目标

创建一个极简 smoke marker 文件，验证 run-project-task-full 可以执行一个极小真实任务。

## 任务原始内容

状态：pending
角色：Developer
目标：创建一个极简 smoke marker 文件，验证 run-project-task-full 可以执行一个极小真实任务。

### 验收标准

- 创建文件 reports/smoke/G008-smoke-marker.md
- 文件内容包含标题和验证说明
- 不修改任何其他文件
- 不修改游戏源文件（index.html / style.css / script.js）
- 不重构
- 不优化
- 不运行无关任务

## 允许修改的文件

- `E:\github_project\multi-agent-runner\projects\down-100-floors-game/index.html`
- `E:\github_project\multi-agent-runner\projects\down-100-floors-game/style.css`
- `E:\github_project\multi-agent-runner\projects\down-100-floors-game/script.js`
- `E:\github_project\multi-agent-runner\projects\down-100-floors-game/docs/tasks.md`
- `E:\github_project\multi-agent-runner\projects\down-100-floors-game/reports/`
- `E:\github_project\multi-agent-runner\projects\down-100-floors-game/memory/`

## 禁止修改的文件

- `E:\github_project\multi-agent-runner\projects\down-100-floors-game/requirement.md`
- `E:\github_project\multi-agent-runner\projects\down-100-floors-game/docs/future-platform-plan.md`
- `E:\github_project\multi-agent-runner\projects\down-100-floors-game/docs/character-system-plan.md`
- `E:\github_project\multi-agent-runner\projects\down-100-floors-game/project.yaml`
- multi-agent-runner 主框架代码
- runner.py
- tools/*.py
- config.yaml

## 限制要求

- 必须直接修改文件，不要只输出建议代码
- 不允许扩大任务范围
- 不允许修改主框架代码
- 不允许修改 project.yaml
- 所有文档使用简体中文
- 文件名、路径、命令保持英文

## 完成证据

完成后必须生成开发报告：
`E:\github_project\multi-agent-runner\projects\down-100-floors-game\reports\dev\G008-dev-report.md`

报告内容包含：
- 任务编号
- 修改文件列表
- 完成内容
- 验收标准自查
- 是否完成

请直接修改文件，不要只输出建议代码。

请开始执行 G008。