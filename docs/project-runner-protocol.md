# Project Runner Protocol

## 1. 协议目标

定义通用 project runner 的协议规范，使 `multi-agent-runner` 可以驱动任意子项目的自动化开发任务。

## 2. 为什么需要通用 project runner

第二阶段实现了 `run-game-next` 专用命令，成功驱动 `down-100-floors-game` 完成自动开发。但该命令硬编码了：

- 项目路径
- 任务文件路径
- 任务编号前缀
- 完成证据路径
- 报告保存路径

这些硬编码使得框架无法复用于其他项目。通用 project runner 通过参数化解决这一问题。

## 3. 当前 run-game-next 的局限

| 局限 | 通用 project runner 解决方式 |
|------|------------------------------|
| 硬编码 `projects/down-100-floors-game` | 通过 `--project` 参数指定 |
| 硬编码任务前缀 `G` | 通过 project.yaml 配置 |
| 硬编码报告路径 | 根据项目路径动态计算 |
| 只能执行游戏项目 | 可执行任意符合约定的项目 |
| 与 runner.py 强耦合 | 通过协议解耦 |

## 4. 目标命令形式

### 最小命令（T025 实现）

```bash
python runner.py run-project-next --project projects/down-100-floors-game
```

### 可选扩展（后续版本）

```bash
# 指定任务编号
python runner.py run-project-next --project projects/down-100-floors-game --task G003

# 试运行（只生成 prompt，不调用 Claude Code）
python runner.py run-project-next --project projects/down-100-floors-game --dry-run
```

### 兼容命令

`run-game-next` 保留为兼容命令，内部等价于：

```bash
python runner.py run-project-next --project projects/down-100-floors-game
```

## 5. 项目目录约定

一个可被 project runner 自动执行的子项目必须遵循以下标准结构：

```
projects/<project-name>/
├── project.yaml          # 项目配置（可选，协议设计阶段新增）
├── requirement.md        # 项目需求文档
├── index.html / app.py   # 项目入口文件（类型由 project.yaml 指定）
├── docs/
│   ├── tasks.md          # 子项目任务清单
│   └── workflow.md       # 工作流说明
├── reports/
│   ├── dev/              # Developer Agent 报告
│   ├── test/             # Tester Agent 报告
│   ├── review/           # Reviewer Agent 报告
│   └── final/            # 总结报告
└── memory/
    ├── lessons.md        # 经验沉淀
    └── pitfalls.md       # 踩坑记录
```

### 最小必要文件

project runner 执行时必须存在：

1. `<project-root>/docs/tasks.md` — 任务清单
2. `<project-root>/` — 项目根目录

project.yaml 为可选文件，缺失时使用默认约定。

## 6. 项目配置文件

项目配置文件路径：`<project-root>/project.yaml`

### 配置字段

```yaml
# ===== 项目基本信息 =====
project:
  id: <项目唯一标识>           # 必填，如 down-100-floors-game
  name: <项目显示名称>         # 必填，如 Down 100 Floors Game
  type: <项目类型>             # 必填，如 web_game / web_app / api / cli
  root: <项目根路径>           # 必填，如 projects/down-100-floors-game
  workflow: <工作流 ID>        # 可选，引用 workflows/ 下的 YAML

# ===== 任务配置 =====
tasks:
  file: docs/tasks.md          # 任务清单文件（相对于项目根路径）
  id_prefix: G                 # 任务编号前缀

# ===== 报告路径 =====
reports:
  dev: reports/dev              # Developer 报告目录
  test: reports/test            # Tester 报告目录
  review: reports/review        # Reviewer 报告目录
  final: reports/final          # 总结报告目录

# ===== Prompt 输出 =====
prompt:
  output: prompts/current_prompt.md  # Prompt 文件路径

# ===== 完成证据 =====
completion_evidence:
  developer: reports/dev/<task-id>-dev-report.md
  tester: reports/test/<task-id>-test-report.md
  reviewer: reports/review/<task-id>-review-report.md

# ===== 文件权限 =====
allowed_files:                  # Claude Code 允许修改的文件/目录
  - index.html
  - style.css
  - script.js
  - docs/
  - reports/
  - memory/

blocked_files:                  # Claude Code 禁止修改的文件
  - requirement.md
```

### 默认约定（project.yaml 缺失时）

当 project.yaml 不存在时，使用以下默认值：

| 字段 | 默认值 |
|------|--------|
| `project.id` | 目录名 |
| `project.type` | `web_app` |
| `tasks.file` | `docs/tasks.md` |
| `tasks.id_prefix` | `T` |
| `reports.dev` | `reports/dev` |
| `reports.test` | `reports/test` |
| `reports.review` | `reports/review` |
| `reports.final` | `reports/final` |
| `prompt.output` | `prompts/current_prompt.md` |
| `completion_evidence.developer` | `reports/dev/<task-id>-dev-report.md` |
| `allowed_files` | 全部允许 |
| `blocked_files` | `requirement.md` |

## 7. 子项目任务文件规范

子项目任务文件路径：`<project-root>/docs/tasks.md`

格式与主项目 `docs/tasks.md` 完全一致：

```markdown
## G001 初始化项目结构

状态：pending
角色：Developer
目标：创建项目基础文件。

### 验收标准

- index.html 存在
- style.css 存在
- script.js 存在
```

### 关键规则

- 任务编号前缀由 `project.yaml` 中的 `tasks.id_prefix` 决定
- 子项目任务与主项目任务完全隔离，不可互相引用
- 子项目任务格式必须与主项目一致（编号、标题、状态、角色、目标、验收标准）

## 8. 任务编号前缀规则

| 项目 | 前缀 | 示例 |
|------|------|------|
| 主框架 multi-agent-runner | T | T024, T025 |
| down-100-floors-game | G | G001, G002 |
| 未来新项目 | 自定义 | P001, A001 等 |

前缀在 `project.yaml` 的 `tasks.id_prefix` 中定义。project runner 根据前缀解析任务。

## 9. Prompt 生成规则

通用 project runner 生成 prompt 时，必须包含以下信息：

### 必须包含的内容

1. **当前项目路径** — 告诉 Claude Code 在哪个项目目录下工作
2. **当前任务编号** — 如 G003
3. **当前任务名称** — 如 玩家显示与左右移动
4. **当前任务目标** — 任务目标描述
5. **当前任务验收标准** — 具体验收条目
6. **允许修改文件范围** — 来自 project.yaml 的 allowed_files
7. **禁止修改文件范围** — 来自 project.yaml 的 blocked_files
8. **不允许扩大任务范围** — 只做当前任务要求的工作
9. **完成证据路径** — 开发报告保存路径
10. **必须直接修改文件** — 不要只输出建议代码

### Prompt 模板结构

```markdown
# <任务编号>：<任务名称>

你现在是 <角色> Agent。

## 项目背景

当前项目是 `<项目名称>`。
项目路径：`<项目根路径>`
项目类型：<项目类型>

## 当前任务

<任务编号>：<任务名称>

目标：<任务目标>

## 验收标准

<验收标准列表>

## 允许修改的文件

<allowed_files 列表>

## 禁止修改的文件

<blocked_files 列表>

## 完成证据

完成后必须生成开发报告：
<项目根路径>/reports/dev/<任务编号>-dev-report.md

## 限制要求

- 必须直接修改文件，不要只输出建议代码
- 不允许扩大任务范围
- 不允许修改主框架代码
- 所有文档使用简体中文
- 文件名、路径、命令保持英文

## 验收方式

完成后运行：
python <验证命令>
```

### 关键约束

- prompt 必须明确指向子项目，而不是主框架
- prompt 必须包含文件修改权限边界
- prompt 必须包含完成证据路径
- prompt 不允许 Claude Code 再次调用 runner 命令

## 10. 完成证据规则

### 证据类型

| Agent | 证据路径（相对于项目根） | 说明 |
|-------|--------------------------|------|
| Developer | `reports/dev/<task-id>-dev-report.md` | 开发报告 |
| Tester | `reports/test/<task-id>-test-report.md` | 测试报告 |
| Reviewer | `reports/review/<task-id>-review-report.md` | 审查报告 |

### 证据路径计算

完整路径 = `<project-root>` + 证据相对路径

例如：
- 项目路径：`projects/down-100-floors-game`
- 任务编号：`G003`
- Developer 证据：`projects/down-100-floors-game/reports/dev/G003-dev-report.md`

### 证据检查规则

任务不能只根据 `returncode=0` 自动标记 done。必须满足以下全部条件：

1. Claude Code 执行成功（`returncode == 0`）
2. 完成证据文件存在
3. 任务状态更新成功

缺一不可。缺少任一条件时，任务保持 `in_progress`。

## 11. 报告保存规则

### 路径规则

所有报告保存在子项目目录下，与主框架报告隔离。

| 报告类型 | 保存路径 |
|----------|----------|
| 开发报告 | `<project-root>/reports/dev/<task-id>-dev-report.md` |
| 测试报告 | `<project-root>/reports/test/<task-id>-test-report.md` |
| 审查报告 | `<project-root>/reports/review/<task-id>-review-report.md` |
| 总结报告 | `<project-root>/reports/final/<task-id>-<title>.md` |
| Prompt 文件 | `<project-root>/prompts/current_prompt.md` |

### 报告格式

所有报告必须符合 Agent Output Protocol（`docs/agent-output-protocol.md`）。

### 主框架日志

每次 project runner 执行后，追加一条摘要到主框架 `reports/run-log.md`：

```
[时间] run-project-next --project <project-path> | 任务: <task-id> | 结果: <success/fail> | 证据: <found/missing>
```

## 12. 状态更新规则

### 状态流转

```
pending → in_progress → done
                    ↘ 保持 in_progress（失败/缺证据）
```

### 规则

| 条件 | 操作 |
|------|------|
| 开始执行前 | 标记为 `in_progress` |
| 执行成功 + 证据存在 | 标记为 `done` |
| 执行成功 + 证据缺失 | 保持 `in_progress` |
| 执行失败 | 保持 `in_progress` |
| 429 限额 | 保持 `in_progress`，停止后续执行 |
| 修改了禁止文件 | 保持 `in_progress`，记录警告 |

### 扩展状态（未来）

| 状态 | 含义 |
|------|------|
| `blocked` | 任务被阻塞，需要外部干预 |

当前版本不实现 `blocked` 状态。

## 13. 失败处理规则

### 失败场景

| 场景 | 错误码 | 处理方式 |
|------|--------|----------|
| 无 pending 任务 | NO_PENDING | 输出提示，正常退出 |
| 项目路径不存在 | INVALID_PROJECT | 输出错误，退出码 1 |
| tasks.md 不存在 | NO_TASKS_FILE | 输出错误，退出码 1 |
| 任务解析失败 | PARSE_ERROR | 输出错误，退出码 1 |
| Claude Code 执行失败 | EXEC_FAILED | 保持 in_progress，输出错误 |
| 缺少完成证据 | NO_EVIDENCE | 保持 in_progress，输出警告 |
| 429 限额 | RATE_LIMITED | 保持 in_progress，停止后续 |
| 修改了禁止文件 | FILE_VIOLATION | 保持 in_progress，记录警告 |

### 第一版处理原则

1. 停止执行，不继续下一个任务
2. 保持任务 `in_progress`（已开始执行）或 `pending`（未开始执行）
3. 输出明确的错误信息
4. 保存执行报告
5. 不自动进入下一个任务
6. 用户可通过 `retry-current` 重试

## 14. 安全规则

1. **runner.py 是最外层调度器。** Claude Code 是被调用的执行器。
2. **不允许 Claude Code 在自身执行过程中再次调用 `run-project-next`。** 避免嵌套调用。
3. **不允许子项目任务修改主框架代码。** 通过 prompt 和文件权限控制。
4. **不允许跳过完成证据检查。** 没有证据不标记 done。
5. **不允许子项目任务和主项目任务混淆。** 前缀隔离，路径隔离。
6. **不允许随意修改需求文件。** `requirement.md` 默认在 `blocked_files` 中。
7. **进入新阶段前必须 Git 备份。** 重要变更前先 commit + push。
8. **真实项目路径校验。** `--project` 参数必须在 `projects/` 目录下。

## 15. T025 实现建议

### 最小实现路径

1. `runner.py` 新增 `run-project-next` 命令，接受 `--project` 参数
2. 读取 `<project-root>/docs/tasks.md`，使用 `tasks.id_prefix` 解析任务
3. 找到第一个 `pending` 任务，标记 `in_progress`
4. 根据 prompt 生成规则生成 `current_prompt.md`
5. 调用 Claude Code 执行
6. 检查完成证据
7. 成功 + 证据存在 → 标记 `done`

### 代码组织建议

- 新增 `tools/project_runner.py`，封装通用项目执行逻辑
- `run-game-next` 保留为兼容命令，内部调用 `project_runner`
- 复用现有 `tools/task_manager.py` 的解析函数，通过 `id_prefix` 参数扩展

### 验证步骤

1. `python runner.py run-project-next --project projects/down-100-floors-game` 能找到 G003（如果存在）
2. 已完成的 G002 不被重新执行
3. 完成证据路径正确解析
4. 主框架命令不受影响
