# Tester Gravity Check Protocol

## 1. 协议目标

定义 Tester Agent 如何检查 G006 简单重力下落逻辑，包括：

- 重力常量 / 状态是否存在
- 垂直速度是否正确更新
- 玩家垂直位置是否随时间向下移动
- 重力更新是否集成到游戏循环中
- 是否越界实现了碰撞、滚动或失败条件

本协议只做设计，不实现测试代码。

## 2. 为什么需要重力测试

G006 将引入简单重力下落逻辑，使玩家角色随时间向下移动。

重力是游戏核心物理基础，后续碰撞检测、平台滚动、失败条件都依赖重力系统。

如果重力逻辑不正确，后续所有功能都会受影响。

因此，在 G006 实现前，需要先定义重力测试协议，确保 Tester 可以独立验证重力逻辑。

## 3. 当前测试能力的不足

### 3.1 基础静态检查

T030 的基础静态检查可以验证：

- `index.html` / `style.css` / `script.js` 文件存在
- HTML 中关键元素（`#game-area`、`#player`、`#start-btn`）存在
- CSS 基础样式存在
- JS 初始化逻辑存在

### 3.2 行为静态检查

T036 的行为静态检查可以验证：

- 键盘事件监听逻辑
- 左右方向键处理逻辑
- 边界限制逻辑
- 玩家水平位置更新逻辑

### 3.3 缺失的能力

当前 Tester 还不能验证：

- 玩家是否会随时间向下移动
- 是否存在重力常量（`GRAVITY`）
- 是否存在垂直速度（`velocityY`）
- 是否存在重力更新逻辑（`applyGravity` / `updateGravity` / `handleGravity`）
- 重力更新是否在 `gameLoop` 中调用
- 玩家 `y` 坐标是否随时间增加

G006 引入重力后，需要新增重力行为检查协议。

## 4. G006 测试范围

### 4.1 测试目标

G006 只测试简单重力下落：

- 玩家随时间向下移动
- 存在 `GRAVITY` 重力值
- 存在 `velocityY` 垂直速度
- 存在 `applyGravity` / `updateGravity` / `handleGravity` 类似逻辑
- 在 `gameLoop` 中调用重力更新
- 玩家 `y` 坐标随时间增加

### 4.2 不测试什么

G006 不测试以下内容：

- 平台碰撞
- 站在平台上
- 平台滚动
- 随机平台
- 游戏失败
- 游戏胜利
- 角色技能系统
- 微信小游戏 / 抖音小游戏适配

### 4.3 范围控制原则

- G006 只做简单垂直下落，不做任何碰撞
- G006 不引入平台滚动
- G006 不引入游戏失败条件
- G006 不引入随机平台
- 如果 G006 实现中包含明显碰撞、滚动或失败条件逻辑，应视为越界

## 5. 不做什么

本协议明确不做以下事项：

- 不引入浏览器自动化
- 不测试平台碰撞
- 不测试平台滚动
- 不测试游戏失败条件
- 不测试游戏胜利条件
- 不测试随机平台
- 不测试角色技能系统
- 不修改小游戏业务代码

## 6. 重力状态检查项（G 组）

| 编号 | 测试项 | 检查目标 | 必需 |
|------|--------|----------|------|
| G-01 | 重力常量存在 | `GRAVITY` 或 `gravity` | 是 |
| G-02 | 玩家垂直速度存在 | `velocityY` 或 `vy` 或 `playerState.velocityY` | 是 |
| G-03 | 玩家 y 坐标状态存在 | `playerState.y` 或 `playerY` | 是 |

### G-01 重力常量存在

检查 `script.js` 中是否定义了重力常量。

关键词：

```text
GRAVITY
gravity
const GRAVITY
const gravity
let GRAVITY
let gravity
```

预期：至少匹配一个关键词。

### G-02 玩家垂直速度存在

检查 `script.js` 中是否定义了玩家垂直速度变量。

关键词：

```text
velocityY
vy
playerState.velocityY
verticalVelocity
speedY
```

预期：至少匹配一个关键词。

### G-03 玩家 y 坐标状态存在

检查 `script.js` 中是否定义了玩家 y 坐标状态变量。

关键词：

```text
playerState.y
playerY
player.y
top
```

预期：至少匹配一个关键词。

## 7. 垂直速度更新检查项（V 组）

| 编号 | 测试项 | 检查目标 | 必需 |
|------|--------|----------|------|
| V-01 | 重力影响速度 | `velocityY += GRAVITY` 或类似逻辑 | 是 |
| V-02 | 速度用于位置更新 | `playerState.y += velocityY` 或类似逻辑 | 是 |
| V-03 | 垂直速度有初始值 | `velocityY: 0` 或初始化赋值 | 是 |

### V-01 重力影响速度

检查 `script.js` 中是否存在重力影响垂直速度的逻辑。

关键词模式：

```text
velocityY += GRAVITY
velocityY += gravity
vy += GRAVITY
vy += gravity
velocityY = velocityY + GRAVITY
```

预期：至少匹配一个模式。

### V-02 速度用于位置更新

检查 `script.js` 中是否存在垂直速度用于位置更新的逻辑。

关键词模式：

```text
playerState.y += velocityY
playerY += velocityY
playerY += vy
y += velocityY
y += vy
top += velocityY
```

预期：至少匹配一个模式。

### V-03 垂直速度有初始值

检查 `script.js` 中是否对垂直速度有初始化赋值。

关键词模式：

```text
velocityY: 0
velocityY = 0
vy: 0
vy = 0
verticalVelocity: 0
verticalVelocity = 0
```

预期：至少匹配一个模式。

## 8. 玩家垂直位置更新检查项（Y 组）

| 编号 | 测试项 | 检查目标 | 必需 |
|------|--------|----------|------|
| Y-01 | 玩家 top 更新存在 | `style.top` | 是 |
| Y-02 | 玩家 y 坐标会变化 | `playerState.y +=` 或 `playerY +=` | 是 |
| Y-03 | 下落方向正确 | y 值增加表示向下移动 | 是 |

### Y-01 玩家 top 更新存在

检查 `script.js` 中是否存在玩家 `style.top` 更新逻辑。

关键词：

```text
style.top
player.style.top
playerEl.style.top
```

预期：至少匹配一个关键词。

### Y-02 玩家 y 坐标会变化

检查 `script.js` 中是否存在玩家 y 坐标赋值或累加逻辑。

关键词模式：

```text
playerState.y +=
playerY +=
playerState.y =
playerY =
```

预期：至少匹配一个模式。

### Y-03 下落方向正确

检查 `script.js` 中 y 坐标增加逻辑是否表示向下移动。

在 Web 页面坐标系中，`top` 值增加表示向下移动。

验证逻辑：

- 如果存在 `playerState.y += velocityY` 或 `playerY += velocityY`，且 `velocityY` 受 `GRAVITY` 影响（正值），则方向正确
- 或者存在 `style.top = playerState.y + 'px'` 类似逻辑

预期：y 值增加方向应与 CSS top 值增加方向一致（向下）。

## 9. 游戏循环集成检查项（L 组）

| 编号 | 测试项 | 检查目标 | 必需 |
|------|--------|----------|------|
| L-01 | 游戏循环存在 | `gameLoop` 或 `requestAnimationFrame` | 是 |
| L-02 | 重力更新在循环中调用 | `applyGravity()` / `updateGravity()` / `handleGravity()` | 是 |
| L-03 | 位置更新在循环中调用 | `updatePlayerPosition()` | 是 |

### L-01 游戏循环存在

检查 `script.js` 中是否存在游戏循环。

关键词：

```text
gameLoop
requestAnimationFrame
function gameLoop
const gameLoop
```

预期：至少匹配一个关键词。

### L-02 重力更新在循环中调用

检查 `script.js` 中是否在游戏循环内调用了重力更新函数。

关键词模式：

```text
applyGravity
updateGravity
handleGravity
gravityUpdate
```

预期：至少匹配一个关键词，且该调用应在 `gameLoop` 或 `requestAnimationFrame` 回调中。

### L-03 位置更新在循环中调用

检查 `script.js` 中是否在游戏循环内调用了位置更新函数。

关键词模式：

```text
updatePlayerPosition
updatePosition
renderPlayer
drawPlayer
```

预期：至少匹配一个关键词，且该调用应在 `gameLoop` 或 `requestAnimationFrame` 回调中。

## 10. 范围限制与非目标检查项（S 组）

| 编号 | 测试项 | 检查目标 | 必需 |
|------|--------|----------|------|
| S-01 | 不包含平台碰撞逻辑 | 不应出现复杂 `collision` / `isOnPlatform` | 是 |
| S-02 | 不包含平台滚动逻辑 | 不应出现 `scrollPlatforms` 等逻辑 | 是 |
| S-03 | 不包含游戏失败条件 | 不应出现 `gameOver` / `fail` 判定 | 是 |

### S-01 不包含平台碰撞逻辑

检查 `script.js` 中是否包含复杂的平台碰撞检测逻辑。

范围控制关键词：

```text
isOnPlatform
checkCollision
platformCollision
detectCollision
```

判定规则：

- 如果出现简单的碰撞注释或占位符（如 `// TODO: collision`），标记为 `PASS`，但备注建议移除
- 如果出现完整的碰撞检测函数实现，标记为 `FAIL`
- 如果出现碰撞检测函数调用，标记为 `FAIL`

### S-02 不包含平台滚动逻辑

检查 `script.js` 中是否包含平台滚动逻辑。

范围控制关键词：

```text
scrollPlatforms
platformScroll
movePlatforms
scrollOffset
```

判定规则：

- 如果出现滚动相关函数实现，标记为 `FAIL`
- 如果只出现注释或占位符，标记为 `PASS`，但备注建议移除

### S-03 不包含游戏失败条件

检查 `script.js` 中是否包含游戏失败判定逻辑。

范围控制关键词：

```text
gameOver
isGameOver
checkFail
failCondition
```

判定规则：

- 如果出现失败判定函数实现，标记为 `FAIL`
- 如果只出现注释或占位符，标记为 `PASS`，但备注建议移除

### S 组说明

S 组是范围控制检查，目的是防止 G006 越界实现。

如果出现明显平台碰撞、滚动、失败条件的完整实现，应判为 `FAIL` 或至少 `REQUEST_REVIEW`。

## 11. PASS / FAIL / BLOCKED 规则

### 11.1 判定规则

| 条件 | 结果 |
|------|------|
| 全部必需项通过 | `PASS` |
| 任一必需项失败 | `FAIL` |
| `script.js` 不存在或无法读取 | `BLOCKED` |
| 范围越界实现明显存在（S 组 FAIL） | `FAIL` |

### 11.2 结果枚举

| 结果 | 含义 | 说明 |
|------|------|------|
| `PASS` | 全部必需项通过 | 重力逻辑测试通过 |
| `FAIL` | 至少一个必需项失败 | 重力逻辑测试失败 |
| `BLOCKED` | 无法执行测试 | 如 `script.js` 缺失 |

### 11.3 与其他测试的关系

重力行为检查与基础静态检查、行为静态检查独立判定：

- 基础静态检查（T030）：验证文件结构和关键元素
- 行为静态检查（T036）：验证键盘移动逻辑
- 重力行为检查（本协议）：验证重力下落逻辑

三者都 `PASS` 才能视为 Tester 整体 `PASS`。

## 12. 测试报告格式

重力行为测试报告使用以下格式：

```markdown
# Gravity Check Test Report

## Agent

Tester Agent

## Task

任务编号：<task-id>
任务名称：<任务名称>

## Status

PASS / FAIL / BLOCKED

## Project

项目路径：<project-root>

## Test Scope

- 重力状态检查
- 垂直速度检查
- 玩家垂直位置更新检查
- 游戏循环集成检查
- 范围限制检查

## Test Cases

| 编号 | 测试项 | 必需 | 结果 | 说明 |
|------|--------|------|------|------|

## Result

PASS / FAIL / BLOCKED

## Failed Items

- （无失败项则留空）

## Out-of-Scope Findings

- （记录越界实现发现，无则留空）

## Fix Suggestions

- （无建议则留空）

## Evidence

- reports/test/<task-id>-gravity-test-report.md

## Next Action

建议下一步：
```

报告模板文件：`templates/agent-output/tester-gravity-check-template.md`

## 13. 完成证据路径

### 13.1 重力行为检查报告

重力行为检查报告保存路径：

```text
<project-root>/reports/test/<task-id>-gravity-test-report.md
```

例如：

```text
projects/down-100-floors-game/reports/test/G006-gravity-test-report.md
```

### 13.2 基础静态检查与重力行为检查的关系

- `G006-test-report.md`：基础静态检查报告
- `G006-gravity-test-report.md`：重力行为检查报告

两个报告独立生成，独立判定。

### 13.3 Main Agent 应读取的证据

后续 Main Agent 应同时读取以下报告：

| 报告 | 路径 | 作用 |
|------|------|------|
| 基础测试报告 | `reports/test/G006-test-report.md` | 验证文件结构和元素 |
| 重力测试报告 | `reports/test/G006-gravity-test-report.md` | 验证重力下落逻辑 |
| 开发报告 | `reports/dev/G006-dev-report.md` | 记录开发内容 |
| 审查报告 | `reports/review/G006-review-report.md` | DeepSeek 审查结论 |
| 综合决策报告 | `reports/main/G006-main-decision.md` | Main Agent 综合决策 |

## 14. T050 实现建议

### 14.1 T050 应实现什么

T050 是 G006 Tester / Reviewer / Main Decision 完整闭环，应实现以下内容：

1. **运行基础静态检查** — 使用 T030 的 `test-game-task` 命令
2. **运行重力行为检查** — 基于本协议实现重力检查逻辑
3. **运行 Reviewer 审查** — 使用 DeepSeek Reviewer
4. **运行 Main Decision** — 综合所有报告生成决策

### 14.2 重力检查实现建议

重力行为检查建议在 `tools/tester_runner.py` 中新增函数：

- `check_gravity_state(script_content)` — G 组检查
- `check_velocity_update(script_content)` — V 组检查
- `check_y_position_update(script_content)` — Y 组检查
- `check_game_loop_integration(script_content)` — L 组检查
- `check_scope_limit(script_content)` — S 组检查
- `run_gravity_check(project_path, task_id)` — 主入口

### 14.3 新增命令建议

建议新增命令：

```text
python runner.py test-gravity-check --project projects/down-100-floors-game --task G006
```

或者复用 `test-game-task` 命令，根据任务编号自动选择是否运行重力检查。

### 14.4 报告生成建议

重力检查报告应：

- 使用 `templates/agent-output/tester-gravity-check-template.md` 模板
- 保存到 `<project-root>/reports/test/G006-gravity-test-report.md`
- 包含所有 15 个检查项的结果
- 明确标注 `PASS` / `FAIL` / `BLOCKED`
