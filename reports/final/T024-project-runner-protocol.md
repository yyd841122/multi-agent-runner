# T024 通用 Project Runner 协议设计报告

## 任务信息

- 任务编号：T024
- 角色：Architect Agent
- 日期：2026-05-04

## 1. 设计背景

第二阶段实现的 `run-game-next` 专用命令已成功驱动 `down-100-floors-game` 完成自动开发（G002），验证了子项目自动执行的可行性。但该命令存在以下硬编码问题：

- 项目路径：`projects/down-100-floors-game`
- 任务前缀：`G`
- 报告路径：硬编码在 runner.py 中

这些硬编码使得框架无法复用于其他子项目。

## 2. 设计目标

设计通用 project runner 协议，使框架可以通过一条命令驱动任意符合约定的子项目：

```bash
python runner.py run-project-next --project projects/<any-project>
```

## 3. 协议核心要素

### 3.1 项目目录约定

定义了子项目标准目录结构，包含 `project.yaml`、`requirement.md`、`docs/tasks.md`、`reports/`、`memory/` 等必需目录。

### 3.2 项目配置文件

设计了 `project.yaml` 配置格式，包含：
- 项目基本信息（id / name / type / root / workflow）
- 任务配置（file / id_prefix）
- 报告路径（dev / test / review / final）
- 完成证据路径（developer / tester / reviewer）
- 文件权限（allowed_files / blocked_files）

### 3.3 命令形式

- 最小命令：`python runner.py run-project-next --project <path>`
- 可选扩展：`--task <id>` / `--dry-run`
- 兼容命令：`run-game-next` 保留

### 3.4 Prompt 生成规则

定义了 prompt 必须包含的 10 项内容：项目路径、任务编号、名称、目标、验收标准、文件权限、证据路径等。

### 3.5 完成证据规则

完成证据路径根据项目根路径动态计算。任务完成需同时满足：执行成功 + 证据存在 + 状态更新成功。

### 3.6 安全规则

8 条安全规则，涵盖嵌套调用禁止、文件权限控制、任务隔离、Git 备份等。

## 4. 交付物

| 交付物 | 路径 | 说明 |
|--------|------|------|
| 协议文档 | `docs/project-runner-protocol.md` | 15 章完整协议 |
| 配置模板 | `templates/project-runner/project-config-template.yaml` | 带注释的项目配置模板 |
| 协议报告 | `reports/final/T024-project-runner-protocol.md` | 本报告 |

## 5. T025 实现建议

T024 只做协议设计，不实现 run-project-next。

T025 实现建议：
1. 新增 `tools/project_runner.py` 封装通用执行逻辑
2. `runner.py` 新增 `run-project-next` 命令
3. `run-game-next` 内部调用 project_runner
4. 复用 `tools/task_manager.py` 的解析函数

## 6. 验收标准自查

- [x] 创建 docs/project-runner-protocol.md
- [x] 创建 templates/project-runner/project-config-template.yaml
- [x] 明确 project runner 的命令形式
- [x] 明确项目路径参数
- [x] 明确子项目任务文件路径
- [x] 明确任务编号前缀规则
- [x] 明确完成证据路径
- [x] 明确 prompt 生成规则
- [x] 明确报告保存规则
- [x] 明确失败处理规则
- [x] 不修改 Python 执行逻辑
