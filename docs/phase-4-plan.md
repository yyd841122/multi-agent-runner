# 第四阶段任务路线规划

## 1. 第四阶段目标

第四阶段目标是增强 Tester Agent 行为检查能力，继续推进 down-100-floors-game 的小步功能验证，并为自动返工和 project.yaml 配置驱动打基础。

具体目标：

1. **增强 Tester 行为检查** — 从静态结构检查扩展到行为逻辑检查（键盘事件、边界移动、位置更新）
2. **project.yaml 配置驱动** — 让 project runner 从路径约定走向项目配置驱动
3. **自动返工协议与 prompt** — 建立返工任务生成能力，但不自动执行
4. **继续小游戏验证** — G005 基础平台显示，保持小任务边界
5. **阶段总结** — 沉淀经验，Git 备份

**核心理念：第四阶段不是"快速做完整游戏"，而是继续用小游戏验证框架能力。**

## 2. 前置基础

### 第一阶段（已完成）

- 最小自动化执行闭环
- 完成证据检查机制
- retry-current / run-next / run-loop 雏形

### 第二阶段（已完成）

- Workflow / Agent Output / Requirement 三类协议
- 多模型 API 适配器 MVP（mock provider）
- Planner Agent 自动拆解链路
- Main Agent 决策协议（规则引擎）
- down-100-floors-game 验证项目（G001 / G002 已完成）
- Reviewer Agent 自动审查 MVP（mock provider）

### 第三阶段（已完成）

- 通用 run-project-next MVP
- DeepSeek Reviewer 真实模型接入
- Reviewer 输出结构化解析
- Tester Agent 本地静态检查
- Main Agent 综合决策
- G003 / G004 完整闭环验证

### 当前局限

1. Tester 主要是静态结构检查，无法验证行为逻辑（键盘事件、移动边界）
2. project runner 仍以路径约定运行，未读取 project.yaml
3. 没有 自动返工 链路，Tester 或 Reviewer 失败时无法生成返工 prompt
4. 游戏只有玩家显示和左右移动，还没有平台、重力、碰撞等核心玩法

## 3. 设计原则

1. **小步执行** — 每个任务小而明确，可独立验证
2. **先协议后实现** — 先设计协议文档，再做最小实现
3. **不一次性做完整游戏** — G005 只做平台显示，不做重力和碰撞
4. **不直接无人值守自动返工** — 先生成返工 prompt，人工确认后再执行
5. **每个功能保留完整证据链** — Developer / Tester / Reviewer / Main Agent
6. **保持 runner 稳定** — 新功能不破坏已有命令

## 4. 第四阶段任务路线

### 第一组：增强 Tester 行为检查能力（T035-T037）

| 任务 | 角色 | 目标 |
|------|------|------|
| T035 | Architect | Tester 行为检查协议设计 |
| T036 | Developer | 实现 Tester 键盘移动逻辑静态检查 MVP |
| T037 | Developer | G004 增强测试 + Main Decision 复核 |

### 第二组：project.yaml 配置驱动（T038-T039）

| 任务 | 角色 | 目标 |
|------|------|------|
| T038 | Developer | project.yaml 协议落地 |
| T039 | Developer | project runner 读取 project.yaml MVP |

### 第三组：自动返工协议与 prompt（T040-T041）

| 任务 | 角色 | 目标 |
|------|------|------|
| T040 | Architect | 自动返工协议设计 |
| T041 | Developer | 自动生成返工 prompt MVP |

### 第四组：G005 基础平台显示完整闭环（T042-T044）

| 任务 | 角色 | 目标 |
|------|------|------|
| T042 | Planner | 新增 G005 基础平台显示任务 |
| T043 | Developer | 使用 run-project-next 自动执行 G005 |
| T044 | Developer | G005 Tester / Reviewer / Main Decision 完整闭环 |

### 第五组：阶段总结（T045）

| 任务 | 角色 | 目标 |
|------|------|------|
| T045 | Reporter | 第四阶段阶段总结与 Git 备份 |

## 5. 推荐执行顺序

```
T035（Tester 行为检查协议）     ← 下一个 pending
        ↓
T036（Tester 键盘移动静态检查）  ←── 依赖 T035
        ↓
T037（G004 增强测试复核）        ←── 依赖 T036
        ↓
T038（project.yaml 协议落地）    ┐
T040（自动返工协议设计）         ├─ 可并行
        ┘
T039（project runner 读 yaml）   ←── 依赖 T038
T041（自动生成返工 prompt）      ←── 依赖 T040
        ↓
T042（新增 G005 任务）           ┐
        ↓                       │
T043（自动执行 G005）            ←── 依赖 T042
        ↓
T044（G005 完整闭环）            ←── 依赖 T043
        ↓
T045（阶段总结 + Git 备份）
```

串行关键路径：T035 → T036 → T037 → T038 → T039 → T042 → T043 → T044 → T045

可并行路径：T038 和 T040 可以并行；T039 和 T041 可以并行。

注意：实际执行中 runner.py 会按 tasks.md 中的顺序逐个执行。

## 6. 暂不做

1. **不做 Web UI 管理平台** — 保持 CLI 驱动
2. **不做数据库** — 继续使用文件系统
3. **不做微信小游戏 / 抖音小游戏发布** — 等 Web MVP 稳定后再适配
4. **不做角色技能系统** — 等基础玩法完成后再引入
5. **不做完全无人值守自动返工** — 先生成返工 prompt，人工确认后再执行
6. **不一次性实现平台、重力、碰撞、滚动** — G005 只做平台显示

## 7. 风险与注意事项

1. **行为静态检查局限性** — 源码静态分析可以验证逻辑存在，但无法验证运行时正确性
2. **project.yaml 向后兼容** — 必须保持"无 yaml 时回退路径约定"的能力
3. **返工 prompt 质量** — 自动生成的返工 prompt 需要人工审核，初期不直接执行
4. **G005 任务边界控制** — 只做平台显示，严格避免同时引入重力和碰撞
5. **Tester 增强不破坏已有检查** — 新增行为检查不能破坏已有的 16 项静态检查

## 8. 验收标准

第四阶段整体验收标准：

- [ ] Tester 行为检查协议设计完成
- [ ] Tester 可以检查键盘移动逻辑
- [ ] G004 增强测试复核完成
- [ ] project.yaml 已创建
- [ ] project runner 可以读取 project.yaml
- [ ] 自动返工协议设计完成
- [ ] 可生成返工 prompt
- [ ] G005 通过完整自动化链路完成
- [ ] 第四阶段总结报告完成
- [ ] 成果已提交推送到 GitHub
