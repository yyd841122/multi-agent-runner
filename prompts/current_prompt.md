# T100：执行第一次真实 run-project-task-full 调用

你现在是 Developer Agent。

## 当前项目

当前项目是 `multi-agent-runner`。
项目路径：`E:\github_project\multi-agent-runner`

## 当前任务

T100：执行第一次真实 run-project-task-full 调用

## 任务目标

解除 simulated，连接真实 run_project_task_full()，执行第一次真实调用。

## 任务原始内容

状态：pending
角色：Developer
目标：解除 simulated，连接真实 run_project_task_full()，执行第一次真实调用。

### 验收标准

- 真实调用 run_project_task_full(project_path, task_id)
- 捕获 FullTaskLoopResult
- 构建 FirstRealRunAcceptanceResult
- workspace 前后检查
- 输出验收结果
- 停止等待人工确认

---

## 允许修改的文件

- `E:\github_project\multi-agent-runner/index.html`
- `E:\github_project\multi-agent-runner/style.css`
- `E:\github_project\multi-agent-runner/script.js`
- `E:\github_project\multi-agent-runner/docs/tasks.md`
- `E:\github_project\multi-agent-runner/reports/`
- `E:\github_project\multi-agent-runner/memory/`

## 禁止修改的文件

- `E:\github_project\multi-agent-runner/requirement.md`
- `E:\github_project\multi-agent-runner/project.yaml`
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
`E:\github_project\multi-agent-runner\reports\dev\T100-dev-report.md`

报告内容包含：
- 任务编号
- 修改文件列表
- 完成内容
- 验收标准自查
- 是否完成

请直接修改文件，不要只输出建议代码。

请开始执行 T100。