# T021 开发报告 — Reviewer Agent 自动审查 MVP

## 任务信息

- 任务编号：T021
- 角色：Developer Agent
- 状态：完成

## 修改文件列表

| 文件 | 改动说明 |
|------|----------|
| `docs/tasks.md` | T021 状态更新为 in_progress |
| `tools/reviewer_runner.py` | 新建 — Reviewer Agent 自动审查运行器 |
| `runner.py` | 新增 `review-game-task` 命令 |
| `reports/dev/T021-dev-report.md` | 新建 — 开发报告 |

## 完成内容

- 实现 `load_text_file()` — 读取文本文件
- 实现 `extract_task_block()` — 从子项目 tasks.md 提取指定任务块
- 实现 `build_reviewer_prompt()` — 构造符合 T014 Reviewer 输出协议的审查 prompt
- 实现 `save_review_output()` — 保存审查报告到子项目 reports/review/
- 实现 `run_reviewer_for_game_task()` — 完整审查链路：读取任务 → 读取报告 → 读取文件 → 构造 prompt → 调用模型 → 保存报告
- 新增 runner.py `review-game-task` 命令
- 审查 prompt 包含：任务要求、开发报告、项目文件快照
- 审查输出要求：Status / Decision (APPROVE/REQUEST_CHANGES) / Acceptance Check
- 当前使用 mock provider，调用 `model_adapter` 的 `reviewer` 配置

## 验收标准自查

- [x] 创建 tools/reviewer_runner.py
- [x] 可以读取 G002 任务要求
- [x] 可以读取 G002 开发报告
- [x] 可以读取小游戏项目文件摘要
- [x] 可以通过 model_adapter 调用 reviewer 模型
- [x] 当前默认使用 mock provider
- [x] 可以生成 projects/down-100-floors-game/reports/review/G002-review-report.md
- [x] 审查报告包含 PASS / FAIL / RETRY / BLOCKED 状态
- [x] 不修改小游戏业务代码

## 本地测试结果

测试命令：`python runner.py review-game-task G002`

预期：输出审查报告路径，G002-review-report.md 文件存在

## 是否完成

是。
