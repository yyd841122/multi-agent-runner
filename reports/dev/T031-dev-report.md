# T031 开发报告 — 自动审查 + 测试结果综合决策 MVP

## 任务信息

- 任务编号：T031
- 角色：Developer Agent
- 状态：完成

## 修改文件列表

| 文件 | 改动说明 |
|------|----------|
| `docs/tasks.md` | T031 状态 pending → in_progress → done |
| `tools/main_agent.py` | 新增 CombinedDecision、parse_tester_report、parse_reviewer_report、decide_from_dev_test_review、save_combined_decision、run_combined_decision_for_game_task |
| `runner.py` | 新增 `decide-game-task` 命令，import run_combined_decision_for_game_task |
| `projects/down-100-floors-game/reports/final/G003-main-decision.md` | 新建 — G003 综合决策报告（Decision=COMPLETE） |
| `reports/dev/T031-dev-report.md` | 新建 — 开发报告 |

## 完成内容

### tools/main_agent.py 新增

**数据结构：**
- `CombinedDecision` — 综合决策结果（task_id, developer_report_exists, tester_status/result, reviewer_status/decision, decision, reason, next_action, blocked）

**解析函数：**
- `parse_tester_report()` — 解析测试报告中的 Status 和 Result（正则匹配 `## Status` 和 `## Result` 后的枚举值）
- `parse_reviewer_report()` — 解析审查报告中的 status 和 decision（优先解析 `## Parsed Result`，回退到 `## Machine Readable Result` 的 JSON 块）

**决策函数：**
- `decide_from_dev_test_review()` — 5 条规则的综合决策：
  - 规则 1：开发报告不存在 → BLOCKED
  - 规则 2：Tester 失败 → REQUEST_CHANGES
  - 规则 3：Reviewer 不批准 → REQUEST_CHANGES
  - 规则 4：三方都通过 → COMPLETE
  - 规则 5：解析失败 → BLOCKED

**报告与入口：**
- `save_combined_decision()` — 保存综合决策报告（8 段结构）
- `run_combined_decision_for_game_task()` — 对 down-100-floors-game 的入口函数

### runner.py 新增

- `decide-game-task` 命令（默认 G003）
- 输出综合决策报告路径 + Decision / Reason / Next Action 摘要

## 本地测试结果

```
python runner.py decide-game-task G003

综合决策：
  Decision：COMPLETE
  Reason：Developer / Tester / Reviewer 三方证据均通过
  Next Action：可以进入下一个任务
```

G003 综合决策详情：

| 证据来源 | 结果 |
|----------|------|
| Developer Report | exists |
| Tester Report | PASS |
| Reviewer Report | APPROVE |
| **Main Decision** | **COMPLETE** |

## 验收标准自查

- [x] Main Agent 可以读取 Developer 报告
- [x] Main Agent 可以读取 Tester 报告
- [x] Main Agent 可以读取 Reviewer 报告
- [x] 可以解析 Tester PASS / FAIL
- [x] 可以解析 Reviewer Status / Decision
- [x] 可以综合生成 Main Decision
- [x] 可以保存 G003-main-decision.md
- [x] 不自动返工
- [x] 不自动修改任务状态

## 限制遵守

- 未自动返工
- 未自动修改子项目任务状态
- 未调用 DeepSeek API
- 未调用 Claude Code
- 未执行 run-project-next
- 未修改小游戏业务代码
- 未修改 G003 dev/test/review 报告
- 所有文档使用简体中文
- 文件名、路径、代码关键字保持英文

## 是否完成

是。
