# T017 开发报告 — Planner Agent 自动拆解任务 MVP

## 任务信息

- 任务编号：T017
- 角色：Developer Agent
- 状态：完成

## 修改文件列表

| 文件 | 改动说明 |
|------|----------|
| `docs/tasks.md` | T017 状态更新为 in_progress |
| `tools/planner_runner.py` | 新建 — Planner Agent 自动拆解任务运行器 |
| `runner.py` | 新增 `plan-project` 命令 |
| `reports/dev/T017-dev-report.md` | 新建 — 开发报告 |

## 完成内容

- 实现 `load_requirement()` — 读取项目需求文件
- 实现 `build_planner_prompt()` — 根据需求内容构造符合 T014 输出协议的 Planner prompt
- 实现 `save_planner_output()` — 保存 Planner 输出到 reports/planner/
- 实现 `run_planner()` — 完整的 Planner 执行链路：读取需求 → 构造 prompt → 调用模型 → 保存输出
- 在 runner.py 新增 `plan-project` 命令，调用 run_planner()
- 当前默认使用 mock provider，不接真实 API
- Planner 输出不直接覆盖 docs/tasks.md，只生成草案报告

## 验收标准自查

- [x] 可以读取 projects/down-100-floors-game/requirement.md
- [x] 可以构造 Planner Agent prompt
- [x] 可以通过 model_adapter 调用 planner 模型
- [x] 可以保存 Planner 输出到 reports/planner/
- [x] 当前默认使用 mock provider
- [x] 不直接覆盖 docs/tasks.md
- [x] 不实现真实 API 调用

## 本地测试结果

测试命令：`python runner.py plan-project`

预期输出：
- 已读取需求文件
- 已构造 Planner prompt
- 模型调用完成：provider=mock, model=mock-planner, success=True
- Planner 输出已保存：reports/planner/T017-planner-output.md

## 是否完成

是。
