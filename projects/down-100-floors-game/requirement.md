# Project Requirement

## Project Metadata

项目名称：down-100-floors-game
项目代号：down-100-floors-game
项目类型：web_game
目标平台：browser
优先级：MVP
当前阶段：requirement_draft

## User Request

用户希望做一个类似经典下落类玩法的网页小游戏，用于验证 `multi-agent-runner` 是否可以自动完成项目需求拆解、任务生成、开发、测试、审查和报告。

该项目只是验证项目，不是 `multi-agent-runner` 主项目本身。

## Project Goal

开发一个最小可玩的网页小游戏 Demo，用于验证多 Agent 自动化 Vibe Coding 框架的真实业务执行能力。

## Background

用户希望最终实现：用户提出需求后，系统自动拆解任务、自动生成工作流、自动生成 Agent 提示词、自动调用 Claude Code、自动生成代码、自动测试、自动审查、自动返工和自动生成报告。

`down-100-floors-game` 是第一个业务验证样例。

## Target Users

- 框架开发者
- 自动化协作流程测试者
- 后续项目验收者

## Project Type

当前项目类型：web_game

## Tech Stack Constraints

技术栈约束：

- 前端：HTML / CSS / JavaScript
- 后端：不需要
- 数据库：不需要
- 运行环境：本地浏览器
- 禁止使用：复杂游戏引擎、复杂前端框架、外部付费素材

## Core Features

核心功能：

1. 玩家控制角色左右移动
2. 角色受重力影响不断下落
3. 平台向上滚动，模拟不断下降
4. 玩家需要踩到平台继续游戏
5. 掉出屏幕或碰到危险元素时游戏结束
6. 显示当前层数或分数
7. 支持开始和重新开始

## MVP Scope

第一版必须完成：

- 基础页面结构
- 游戏区域
- 玩家方块
- 平台生成
- 左右移动
- 简单重力
- 简单碰撞检测
- 游戏结束判定
- 层数或分数显示

## Out of Scope

第一版不做：

- 复杂美术
- 音效
- 排行榜
- 登录系统
- 后端服务
- 数据库
- 移动端适配
- 多关卡剧情
- 复杂道具系统

## Acceptance Criteria

验收标准：

- 可以在浏览器打开并运行
- 玩家可以左右移动
- 玩家会受重力影响
- 平台可以显示并参与碰撞
- 游戏可以开始和结束
- 有基础分数或层数显示
- 项目文件结构清晰
- 每个开发任务都有开发报告
- 每个测试任务都有测试报告
- 完成任务必须有完成证据

## Deliverables

最终输出物：

- index.html
- style.css
- script.js
- reports/dev/
- reports/test/
- reports/review/
- reports/final/

## Workflow Recommendation

建议 workflow：game_web_mvp

## Agent Recommendation

建议 Agent：

- Main Agent
- Planner Agent
- Developer Agent
- Tester Agent
- Reviewer Agent
- Reporter Agent

## Constraints

限制条件：

- 小游戏只是验证项目，不是主项目
- 不允许复刻原游戏名称、美术、素材、音效或关卡
- 所有任务必须服务于验证 multi-agent-runner
- 优先最小可运行版本
- 不允许一次性实现所有功能
- 每一步必须可验证
- 自动化是最终目标

## Notes

补充说明：

后续由 Planner Agent 根据本需求自动拆解开发任务。

---

## Long-term Vision

长期目标：

- 未来适配微信小游戏
- 未来适配抖音小游戏
- 未来支持多角色系统
- 未来每个角色可以拥有不同技能
- 角色灵感来自用户大学宿舍同学，用于表达青春回忆

## Current MVP Boundary

当前 MVP 只做：

- Web 浏览器 Demo
- 基础页面
- 基础游戏区域
- 后续可扩展结构

当前 MVP 不做：

- 微信小游戏发布
- 抖音小游戏发布
- 角色技能
- 真实人物形象
- 登录
- 排行榜
- 支付
- 广告
- 后端
- 数据库

## Platform Design Principle

平台适配原则：

- 游戏核心逻辑尽量独立
- 平台能力通过 adapter 适配
- 当前阶段只写说明，不实现 adapter 代码

## Character Design Principle

角色设计原则：

- 第一版不使用真实人物姓名、照片或明显身份特征
- 第一版只预留角色系统方向
- 后续如果使用真实同学原型，应先获得对方同意
- 第一版可以使用虚构角色占位
