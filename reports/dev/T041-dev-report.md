# T041 开发报告 — 自动生成返工 prompt MVP

## 任务信息

- 任务编号：T041
- 角色：Developer
- 状态：完成

## 修改文件列表

| 文件 | 改动说明 |
|------|----------|
| `docs/tasks.md` | T041 状态 pending → in_progress → done |
| `tools/rework_manager.py` | 新建 — 返工 prompt 生成器 + 人工介入报告 |
| `runner.py` | 新增 generate-rework-prompt 命令 |
| `projects/.../prompts/rework_prompt.md` | 新建 — G004-R1 返工 prompt（验证样例） |
| `projects/.../G004-manual-intervention-report.md` | 新建 — G004 人工介入报告（R4 超限验证） |
| `reports/dev/T041-dev-report.md` | 新建 — 开发报告 |

## 完成内容

- 新增 tools/rework_manager.py 返工 prompt 生成器
- 支持读取子项目任务块、project.yaml 配置、4 类报告
- 支持生成 G004-R1/R2/R3 返工 prompt
- 支持最大返工次数限制（MAX_REWORK_ROUNDS = 3）
- 超过 3 次时生成人工介入报告，不生成 R4 prompt
- 新增 generate-rework-prompt 命令
- 不自动调用 Claude Code

## 验收标准自查

| 验收标准 | 结果 |
|----------|------|
| 创建 tools/rework_manager.py | PASS |
| 可以读取子项目任务文件 | PASS |
| 可以读取 project.yaml | PASS |
| 可以读取相关报告 | PASS |
| 可以生成 rework_prompt.md | PASS |
| prompt 包含原任务、失败来源、允许/禁止文件 | PASS |
| 支持最大返工次数限制 | PASS |
| 最大返工次数为 3 | PASS |
| 超过 3 次不生成 R4 prompt | PASS |
| 超过 3 次生成人工介入报告 | PASS |
| 不自动调用 Claude Code | PASS |
| 不自动修改业务代码 | PASS |

## 本地测试

```
python runner.py generate-rework-prompt G004 1
→ 返工 prompt 已生成：G004-R1，轮次 1/3

python runner.py generate-rework-prompt G004 4
→ 已达到最大返工次数限制：3
→ 人工介入报告已生成
```

## 是否防止无限返工循环

是。同一任务最多允许 3 次返工，超过后生成 manual intervention report，要求人工介入。

## 限制遵守

- 未调用 Claude Code
- 未执行返工
- 未修改小游戏业务代码
- 未调用 DeepSeek API
- 未执行测试、审查、综合决策命令
- 未修改 G004 状态
- 未创建真实 G004-R1 任务到 tasks.md
- 未生成 G004-R4 prompt
- 未新增第三方依赖
- 所有文档使用简体中文

## 是否完成

是。
