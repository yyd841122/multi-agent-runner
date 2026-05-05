# Lessons

## G006 简单重力下落完整闭环经验

### 成果

`G006 实现简单重力下落` 已完成：

- Developer：PASS
- Basic Tester：PASS，16/16
- Reviewer：PASS / APPROVE
- Main Agent：COMPLETE

### 实现内容

- 添加 `GRAVITY`
- 添加玩家垂直速度 `vy`
- 添加 `applyGravity()`
- 在游戏循环中调用重力更新
- 玩家 y 坐标随垂直速度变化
- 未实现平台碰撞、平台滚动、随机平台和游戏失败条件

### 经验

- G006 可以作为重力下落最小闭环任务。
- 重力逻辑应先独立于平台碰撞实现。
- full loop 首次执行中遇到 Reviewer 环境问题，但 Developer 和 Tester 阶段自动化已跑通。
- 后续应补 gravity tester，避免只靠基础静态测试和 Reviewer。

## G006 完整闭环与重力下落经验

### 成果

`G006 实现简单重力下落` 已完成完整闭环：

- Developer：done
- Basic Tester：PASS
- Reviewer：APPROVE
- Main Agent：COMPLETE

### 实现内容

- 玩家开始游戏后会随时间向下移动
- 存在 `GRAVITY`
- 存在玩家垂直速度 `vy`
- `applyGravity()` 更新 `vy` 和 `y`
- `gameLoop` 调用重力更新逻辑
- 玩家位置更新后页面显示正确
- 未实现平台碰撞、平台滚动、随机平台、失败条件和角色技能

### 经验

- 重力下落应独立于平台碰撞完成。
- G006 为后续 G007 平台碰撞奠定基础。
- G006 后续仍需要 gravity tester 做专项验证。

## G002 第一次自动开发任务成功经验

### 成果

`multi-agent-runner` 成功通过 `run-game-next` 自动完成 G002 实现基础游戏页面。

### 已完成内容

- 页面标题
- 游戏区域
- 开始按钮
- 层数或分数显示
- 状态提示
- 基础说明文字
- 开发报告

### 经验

- 第一版 Web MVP 先做基础页面是正确选择。
- 暂时不实现玩家、平台、重力、碰撞，可以降低复杂度。
- 先让页面可打开，可以快速建立验证信心。

## G003 通过通用 project runner 自动完成经验

### 成果

`G003 实现玩家角色显示` 已通过通用命令 `run-project-next` 自动完成。

### 已完成内容

- 页面中加入玩家角色元素
- 玩家角色显示在游戏区域内
- 玩家角色有明显样式
- 点击开始后显示玩家角色
- 生成 `G003-dev-report.md`
- G003 自动标记为 `done`

### 经验

- 先实现玩家显示，不做移动、平台、重力、碰撞，是正确的最小任务边界。
- G003 验证了通用 project runner 可以驱动真实游戏项目继续向前开发。
- 游戏功能应继续按小任务推进。

## G003 DeepSeek Reviewer 审查通过经验

### 成果

`G003 实现玩家角色显示` 已由 DeepSeek Reviewer 真实审查，并返回：

- Status：PASS
- Decision：APPROVE
- Issues：0

### 经验

- G003 的任务边界清楚，因此 Reviewer 更容易判断是否通过。
- 开发报告、任务要求和文件快照同时提供给 Reviewer，有助于提高审查质量。
- 审查报告应和开发报告一起保存，形成可追溯证据链。

## G003 完整证据链闭环成功经验

### 成果

`G003 实现玩家角色显示` 已经完成完整闭环：

- Developer：开发完成
- Tester：PASS（16/16 通过）
- Reviewer：APPROVE（DeepSeek 审查通过）
- Main Agent：COMPLETE

### 经验

- G003 任务边界清晰，因此自动开发、测试、审查和综合决策都能顺利完成。
- 玩家显示功能作为小任务适合验证完整闭环。
- 后续 G004 玩家左右移动应继续保持小任务边界。
- 完整闭环需要 Developer / Tester / Reviewer 三类证据，缺一不可。

## G004 玩家键盘左右移动完整闭环经验

### 成果

`G004 实现玩家键盘左右移动` 已完成：

- Developer：done
- Tester：PASS
- Reviewer：APPROVE
- Main Agent：COMPLETE

### 经验

- 左右移动作为独立任务是合理的，不应和重力、平台、碰撞放在同一任务中。
- 键盘移动是后续游戏玩法的基础能力。
- 每个游戏能力都应继续按小任务推进，并保留完整证据链。

## 第三阶段游戏验证经验总结

### 已完成

- G002：基础游戏页面
- G003：玩家角色显示
- G004：玩家键盘左右移动

### 经验

- 游戏功能应按最小能力逐步推进。
- 玩家显示和玩家移动拆成两个任务是正确的。
- 每个功能都保留 Developer / Tester / Reviewer / Main Agent 证据链，可以方便后续追踪。
- 后续可以继续做 G005 基础平台显示，但不应同时做重力和碰撞。

## G005 Developer 特殊完成经验

### 成果

`G005 实现基础平台显示` 已完成 Developer 阶段：

- index.html 已添加 5 个平台元素
- style.css 已添加平台样式（青绿色背景 + 深色边框 + 圆角）
- script.js 已添加固定平台布局（PLATFORM_LAYOUT）和 initPlatforms() / hidePlatforms() 逻辑
- G005-dev-report.md 已生成
- G005 状态为 done

### 特殊情况

Claude Code 在完成任务后返回 API 429，因此 runner 最初显示失败。实际应以完成证据和任务状态为准，后续继续执行 Tester 阶段。

### 平台布局

5 个平台分布在 y=120、200、280、360、440 的位置，宽度占游戏区域 45%-55%，左右错落排列。玩家初始位置 y=20px，不会被平台遮挡。

## G005 基础平台显示完整闭环经验

### 成果

`G005 实现基础平台显示` 已完成：

- Developer：done
- Tester：PASS（16/16 通过）
- Reviewer：APPROVE（DeepSeek 审查通过，Issues=0）
- Main Agent：COMPLETE

### 实现内容

- 游戏区域中已添加 5 个基础平台
- 平台有明显样式（青绿色背景 + 深色边框 + 圆角）
- 平台采用固定布局（PLATFORM_LAYOUT 数组）
- 平台显示在游戏区域内
- 平台不遮挡玩家初始位置
- 未实现重力、碰撞、滚动、随机生成和角色技能

### 经验

- 基础平台显示作为独立任务是合理的。
- 后续重力和碰撞必须拆成独立任务。
- 每个新增玩法能力都应继续保留完整证据链。
- 即使 Developer 阶段遇到 429，只要完成证据存在就应继续 Tester / Reviewer 闭环。

## 第四阶段游戏验证经验总结

### 已完成能力

- G002：基础游戏页面
- G003：玩家角色显示
- G004：玩家键盘左右移动
- G005：基础平台显示

### 经验

- 玩家显示、玩家移动、平台显示拆成独立任务是正确的。
- G005 只做基础平台显示，为后续重力和碰撞打基础。
- 每个游戏能力都应保留 Developer / Tester / Reviewer / Main Agent 证据链。
- 平台显示完成后，下一步适合做 G006 简单重力下落。
- 不应在平台显示阶段提前引入碰撞和滚动。
