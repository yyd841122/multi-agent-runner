# T039 开发报告 — project runner 读取 project.yaml MVP

## 任务信息

- 任务编号：T039
- 角色：Developer
- 状态：完成

## 修改文件列表

| 文件 | 改动说明 |
|------|----------|
| `docs/tasks.md` | T039 状态 pending → in_progress → done |
| `tools/project_runner.py` | 新增 ProjectRunnerConfig、YAML 解析、config 驱动执行 |
| `reports/dev/T039-dev-report.md` | 新建 — 开发报告 |

## 完成内容

- 新增 ProjectRunnerConfig 数据类
- 新增 load_project_runner_config 读取 project.yaml 或回退路径约定
- 新增 _parse_simple_yaml_value / _parse_simple_yaml_list_block 最小 YAML 解析
- 修改 build_project_task_prompt 使用 config 的 allowed_files / blocked_files
- 修改 run_project_next 使用 config 的 tasks_file / developer_evidence_pattern
- prompt 中加入 project.yaml 到禁止修改列表
- 保持 run-project-next 命令完全兼容

## 验收标准自查

| 验收标准 | 结果 |
|----------|------|
| 如果存在 project.yaml，优先读取配置 | PASS |
| 如果不存在 project.yaml，回退路径约定 | PASS |
| 可以读取 tasks.file | PASS |
| 可以读取 reports.dev | PASS |
| 可以读取 completion_evidence.developer | PASS |
| 可以读取 allowed_files | PASS |
| 可以读取 blocked_files | PASS |
| 不破坏现有 run-project-next 命令 | PASS |

## 本地测试

```
python -c "from tools.project_runner import load_project_runner_config; ..."

loaded_from_yaml=True
tasks_file=.../docs/tasks.md
dev_reports_dir=.../reports/dev
allowed_files=['index.html', 'style.css', ...]
blocked_files=['requirement.md', 'docs/future-platform-plan.md', ...]
```

回退测试（无 project.yaml）：`loaded_from_yaml=False`

## 限制遵守

- 未执行 run-project-next
- 未调用 Claude Code 执行业务开发
- 未修改 runner.py
- 未修改小游戏业务代码
- 未修改子项目 tasks.md
- 未调用 DeepSeek API
- 未新增第三方依赖
- 未开始 T040
- 所有文档使用简体中文
- 文件名、路径、命令保持英文

## 是否完成

是。
