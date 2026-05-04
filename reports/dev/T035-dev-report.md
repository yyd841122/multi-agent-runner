# T035 开发报告 — Tester 行为检查协议设计

## 任务信息

- 任务编号：T035
- 角色：Architect
- 状态：完成

## 修改文件列表

| 文件 | 改动说明 |
|------|----------|
| `docs/tasks.md` | T035 状态 pending → in_progress → done |
| `docs/tester-behavior-check-protocol.md` | 新建 — Tester 行为检查协议（13 章） |
| `docs/tester-protocol.md` | 追加行为检查扩展章节 |
| `templates/agent-output/tester-behavior-check-template.md` | 新建 — 行为检查报告模板（13 项检查） |
| `templates/agent-output/tester-static-web-test-template.md` | 追加 Behavior Check Extension 说明 |
| `memory/lessons.md` | 追加 T035 经验 |
| `memory/pitfalls.md` | 追加 T035 避坑 |
| `reports/final/T035-tester-behavior-check-protocol.md` | 新建 — 协议报告（9 章） |
| `reports/dev/T035-dev-report.md` | 新建 — 开发报告 |

## 完成内容

- 创建 Tester 行为检查协议文档，定义 4 组 13 项行为检查
- 创建行为检查报告模板
- 更新 tester-protocol.md 追加行为检查扩展章节
- 更新静态测试模板追加行为检查说明
- 定义 PASS / FAIL / BLOCKED 规则
- 定义完成证据路径规则
- 明确 T036 实现方向

## 验收标准自查

- [x] 创建 docs/tester-behavior-check-protocol.md
- [x] 创建 Tester 行为检查报告模板
- [x] 明确 G004 当前静态测试的不足
- [x] 明确键盘事件检查项（B-01 ~ B-03）
- [x] 明确左右移动逻辑检查项（M-01 ~ M-04）
- [x] 明确边界限制检查项（L-01 ~ L-03）
- [x] 明确玩家位置更新检查项（U-01 ~ U-03）
- [x] 明确 T036 实现方向
- [x] 不引入浏览器自动化
- [x] 不修改小游戏业务代码

## 限制遵守

- 未修改任何 Python 代码
- 未修改小游戏业务代码
- 未实现行为测试工具
- 未执行任何测试命令
- 未调用 DeepSeek API
- 未开始 T036
- 所有文档使用简体中文
- 文件名、路径、代码关键字保持英文

## 是否完成

是。
