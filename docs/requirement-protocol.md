# Requirement Protocol

## 1. 协议目标

需求文件是用户原始需求进入自动化系统的标准入口。它定义一个统一格式，让 Main Agent / Planner Agent / runner.py 可以自动读取用户需求，并基于需求生成：

- workflow 选择
- Agent 组合
- 任务清单
- 验收标准
- 项目边界
- 输出要求

需求文件 **不是业务代码**，它是自动化协作的输入协议。

当前 T015 只创建协议和模板，不接入代码。后续 T017 会使用它做 Planner Agent 自动拆解任务。

## 2. 适用范围

本协议适用于所有通过 `multi-agent-runner` 自动化执行的项目需求输入：

| 场景 | 需求文件位置 |
|------|-------------|
| 主项目需求 | `docs/requirement.md` |
| 子项目需求 | `projects/<project-name>/requirement.md` |
| 模板参考 | `templates/requirement-template.md` |

## 3. 需求文件位置

| 位置 | 用途 |
|------|------|
| `docs/requirement.md` | 主项目（multi-agent-runner 自身）的需求 |
| `projects/<name>/requirement.md` | 子项目（如验证项目）的需求 |
| `templates/requirement-template.md` | 空白模板，用于新建项目时复制 |

Planner Agent 读取需求时，优先查找 `projects/<project-name>/requirement.md`，其次查找 `docs/requirement.md`。

## 4. 标准字段

需求文件包含以下标准字段：

| 字段 | 必填 | 说明 |
|------|------|------|
| `Project Metadata` | 是 | 项目元数据（名称、代号、类型、平台等） |
| `User Request` | 是 | 用户原始需求文字 |
| `Project Goal` | 是 | 项目目标（一句话） |
| `Background` | 否 | 背景说明 |
| `Target Users` | 否 | 目标用户 |
| `Project Type` | 是 | 项目类型枚举 |
| `Tech Stack Constraints` | 是 | 技术栈约束 |
| `Core Features` | 是 | 核心功能列表 |
| `MVP Scope` | 是 | 第一版必须完成的内容 |
| `Out of Scope` | 是 | 明确不做的事项 |
| `Acceptance Criteria` | 是 | 验收标准 |
| `Deliverables` | 是 | 最终输出物 |
| `Workflow Recommendation` | 否 | 建议 workflow |
| `Agent Recommendation` | 否 | 建议 Agent 列表 |
| `Constraints` | 否 | 限制条件 |
| `Notes` | 否 | 补充说明 |

## 5. 机器可读字段

以下字段设计为机器可读，Planner Agent 或 runner.py 可通过解析获取结构化信息：

| 字段 | 格式 | 解析方式 |
|------|------|----------|
| `项目名称` | 自由文本 | 直接读取 |
| `项目代号` | 小写英文 + 连字符 | 直接读取 |
| `项目类型` | 固定枚举值 | 精确匹配 |
| `目标平台` | 固定枚举值 | 精确匹配 |
| `优先级` | 固定枚举值 | 精确匹配 |
| `当前阶段` | 固定枚举值 | 精确匹配 |
| `Tech Stack` | 结构化列表 | 逐行解析 |
| `Core Features` | 编号列表 | 计数 + 逐项解析 |
| `MVP Scope` | 列表 | 逐项解析 |
| `Out of Scope` | 列表 | 逐项解析 |
| `Workflow Recommendation` | workflow ID | 精确匹配 |

## 6. 人工说明字段

以下字段允许自由文本，主要供人工阅读和 Planner Agent 理解上下文：

| 字段 | 说明 |
|------|------|
| `User Request` | 用户原始需求，可能包含口语化表达 |
| `Project Goal` | 一句话项目目标 |
| `Background` | 背景说明 |
| `Target Users` | 目标用户描述 |
| `Acceptance Criteria` | 验收标准描述 |
| `Constraints` | 限制条件 |
| `Notes` | 补充说明 |

## 7. 项目类型规范

`Project Type` 字段使用以下枚举值：

| 值 | 说明 |
|-----|------|
| `web_game` | 网页游戏 |
| `web_page` | 静态网页 / 落地页 |
| `frontend_app` | 前端应用（SPA） |
| `backend_api` | 后端 API 服务 |
| `fullstack_app` | 全栈应用 |
| `flutter_app` | Flutter 移动应用 |
| `automation_script` | 自动化脚本 |
| `erp_module` | ERP 功能模块 |
| `other` | 其他类型 |

Planner Agent 根据 `Project Type` 选择对应的 workflow 文件。

## 8. 技术栈约束

`Tech Stack Constraints` 使用结构化子字段：

| 子字段 | 必填 | 说明 |
|--------|------|------|
| `前端` | 视项目类型 | 前端技术栈 |
| `后端` | 视项目类型 | 后端技术栈 |
| `数据库` | 视项目类型 | 数据库 |
| `运行环境` | 是 | 运行环境 |
| `禁止使用` | 否 | 明确禁止的技术 |

Planner Agent 根据技术栈约束决定每个任务的开发工具和验收方式。

## 9. 功能范围

功能范围通过三个字段控制边界：

| 字段 | 目的 |
|------|------|
| `Core Features` | 核心功能列表，Planner 必须为每项生成任务 |
| `MVP Scope` | 第一版必须完成的范围 |
| `Out of Scope` | 明确不做的事项 |

**原则：**

- `Core Features` 的数量控制任务总数
- `MVP Scope` 约束第一版范围，防止任务膨胀
- `Out of Scope` 是硬约束，Planner 不能为其生成任务
- 每个功能点应该是可独立验证的

## 10. 不做事项

`Out of Scope` 是项目边界的硬约束：

- Planner Agent 不能为 `Out of Scope` 中的项目生成任务
- Developer Agent 不能在开发过程中引入 `Out of Scope` 中的功能
- Reviewer Agent 应检查实现是否超出了 `MVP Scope`

## 11. 验收标准

`Acceptance Criteria` 定义项目整体验收标准：

- 每个 Criterion 应该是可验证的
- Planner Agent 在生成任务时，应将项目级验收标准拆解为任务级验收标准
- Reviewer Agent 在审查时，应对照项目级验收标准检查

## 12. 输出物要求

`Deliverables` 定义项目最终输出物：

- 可运行代码
- 开发报告
- 测试报告
- 审查报告
- 最终总结报告

Planner Agent 根据 `Deliverables` 确定需要哪些 Agent 参与以及各 Agent 的输出要求。

## 13. Planner Agent 使用方式

Planner Agent 读取需求文件的流程：

```
1. 读取 requirement.md
2. 解析机器可读字段（Project Type / Tech Stack / Core Features）
3. 选择对应的 workflow 文件
4. 根据 Core Features 和 MVP Scope 生成任务清单
5. 根据技术栈约束为每个任务指定验收标准
6. 检查任务不超出 Out of Scope 边界
7. 输出任务清单草案到文件
8. 等待人工确认后写入 docs/tasks.md
```

## 14. 后续接入 runner.py 的建议

| 后续任务 | 接入方式 |
|----------|----------|
| T017（Planner Agent） | 读取 requirement.md，解析机器可读字段，自动生成任务 |
| T018（Main Agent 决策） | 根据 Project Type 选择 workflow |
| T019（游戏项目初始化） | 使用已创建的 requirement.md 作为输入 |
| T020（自动执行验证） | 验证 Planner 能正确解析需求并生成任务 |

**解析建议：**

- 机器可读字段使用精确匹配或正则解析
- 列表类字段使用 `-` 前缀标记，逐行读取
- `Core Features` 使用编号列表，每个功能点对应一个或多个任务
- 当前阶段只做文件解析，不做自然语言理解
