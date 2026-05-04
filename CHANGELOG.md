# CHANGELOG

本文件记录 `multi-agent-runner` 的重要阶段、版本里程碑、核心能力变化和关键提交。

## 文档分工

- `README.md`：说明项目是什么、如何运行、当前能力概览。
- `CHANGELOG.md`：记录版本变化、阶段里程碑和关键提交。
- `docs/tasks.md`：记录任务清单和任务状态。
- `reports/dev/`：记录每个开发任务的详细执行报告。
- `reports/final/`：记录阶段总结和里程碑总结。
- `memory/lessons.md`：记录可复用经验。
- `memory/pitfalls.md`：记录踩坑和注意事项。

---

## v0.5.0-plan - 第五阶段规划：重力、碰撞与人工确认返工

### 状态

规划完成，待执行。

### 对应任务

- T046：设计第五阶段路线

### 规划方向

- G006：简单重力下落
- G007：玩家与平台基础碰撞
- 重力下落 Tester 协议
- 碰撞检测 Tester 协议
- 人工确认后的返工执行链路
- 继续保持 Developer / Tester / Reviewer / Main Agent 完整证据链

### 暂不做

- 完整游戏
- 微信小游戏 / 抖音小游戏发布
- 角色技能系统
- Web UI 管理平台
- 数据库
- 完全无人值守返工

---

## v0.4.0 - 第四阶段：自动化安全机制增强

### 状态

已完成。

### 核心成果

- Tester 行为检查增强
- G004 键盘移动行为测试 13/13 PASS
- `project.yaml` 配置驱动
- `project runner` 读取 `project.yaml`
- 自动返工协议设计
- 自动生成返工 prompt MVP
- 最大返工次数限制：3
- 超过 R3 后生成 manual intervention report
- Claude Code 超时异常处理
- returncode 与完成证据冲突判断修复
- G005 基础平台显示完整闭环

### 游戏验证成果

- G005：基础平台显示
  - Developer：done
  - Tester：PASS，16/16
  - Reviewer：APPROVE，Issues=0
  - Main Agent：COMPLETE

### 关键任务

- T035-T037：Tester 行为检查增强
- T038-T039：`project.yaml` 配置驱动
- T040-T041：自动返工协议与 prompt
- T043.0-T043.2：异常处理修复与特殊情况记录
- T044：G005 完整闭环
- T045：第四阶段总结与 Git 备份

### 关键提交

- `34f4eaf` docs: mark T037.1 as done
- `1952d2a` docs: mark T042.1 as done
- `5174106` docs: complete phase 4 automation safety milestone

---

## v0.3.0 - 第三阶段：通用 project runner 与完整证据链

### 状态

已完成。

### 核心成果

- 通用 `project runner` 协议
- 通用 `run-project-next` MVP
- DeepSeek Reviewer 真实模型接入
- Reviewer 输出结构化解析
- Tester Agent 本地静态检查
- Main Agent 综合决策
- G003 玩家角色显示完整闭环
- G004 玩家键盘左右移动完整闭环

### 游戏验证成果

- G003：玩家角色显示
  - Developer：done
  - Tester：PASS
  - Reviewer：APPROVE
  - Main Agent：COMPLETE
- G004：玩家键盘左右移动
  - Developer：done
  - Tester：PASS
  - Reviewer：APPROVE
  - Main Agent：COMPLETE

### 关键任务

- T023-T025：通用 project runner
- T026-T028：DeepSeek Reviewer 与结构化审查
- T029-T031：Tester / Reviewer / Main Agent 三方证据链
- T032：G004 完整闭环
- T033：第三阶段总结与 Git 备份

### 关键提交

- `af3f5b6` feat: add generic project runner MVP with G003 auto-execution
- `9afe86b` feat: integrate real DeepSeek reviewer with structured review pipeline
- `c6b29e4` feat: complete G003 validation evidence loop with Tester, Reviewer and Main Agent
- `31068d5` docs: add T033 phase 3 summary and dev report

---

## v0.2.0 - 第二阶段：协议化与验证项目初始化

### 状态

已完成。

### 核心成果

- Workflow 协议规范化
- Agent 输出协议规范化
- 项目需求输入规范化
- 多模型 API 适配器 MVP
- Planner Agent 自动拆解任务 MVP
- Main Agent 决策协议 MVP
- `down-100-floors-game` 验证项目初始化
- G002 基础游戏页面自动开发
- DeepSeek Reviewer 接入前的 Reviewer MVP

### 游戏验证成果

- G002：基础游戏页面
  - 自动开发完成
  - 页面可打开
  - 包含游戏区域、开始按钮、楼层/状态显示

### 关键任务

- T013-T015：协议规范化
- T016：多模型 API 适配器
- T017：Planner Agent 自动拆解任务 MVP
- T018：Main Agent 决策协议 MVP
- T019：down-100-floors-game 初始化
- T020：自动执行小游戏第一个开发任务
- T021：Reviewer Agent 自动审查 MVP
- T022：第二阶段总结

### 关键提交

- `bbb1798` feat: complete multi-agent runner MVP framework
- `486a00d` feat: validate first project auto-run
- `072c203` docs: complete phase 2 multi-agent runner milestone

---

## v0.1.0 - 第一阶段：runner 最小自动化闭环

### 状态

已完成。

### 核心成果

- 初始化 `multi-agent-runner`
- 读取 `docs/tasks.md`
- 解析 pending / in_progress / done 状态
- 自动生成 Claude Code prompt
- 调用 Claude Code
- 保存 `reports/claude/latest-output.md`
- 记录 `reports/run-log.md`
- 检查完成证据
- 根据完成证据自动标记任务 done
- 形成第一版最小自动化闭环

### 关键经验

- 完成证据比模型退出码更可靠。
- runner.py 是调度中心，Claude Code 是执行器。
- 主 Agent 只负责调度和决策，不做具体开发。
- 每个任务都必须有可追溯报告。

---

## 当前总体进展

截至 v0.5.0-plan，`multi-agent-runner` 已经具备：

- 多阶段任务管理
- 子项目自动执行
- 多模型 Reviewer
- Tester 静态检查
- Tester 行为检查
- Main Agent 综合决策
- project.yaml 配置读取
- 自动返工 prompt 生成
- 最大返工次数限制
- 异常处理与人工介入机制

`down-100-floors-game` 当前已完成：

- G002：基础游戏页面
- G003：玩家角色显示
- G004：玩家键盘左右移动
- G005：基础平台显示
