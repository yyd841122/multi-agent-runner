# Tester Collision Check Protocol

## 1. 协议目标

定义 Tester Agent 如何检查 G007 玩家与平台基础碰撞逻辑，包括：

- 碰撞检测函数是否存在
- 碰撞逻辑是否在下落时执行
- 平台数据是否正确使用
- 玩家底部位置判断
- 水平范围重叠判断
- 从上方落到平台的判断
- 落到平台后 y 坐标修正
- 落到平台后垂直速度归零
- 防穿透检查
- 不越界实现平台滚动、随机平台和失败条件

本协议只做设计，不实现测试代码。

## 2. 为什么需要碰撞检测测试

G007 将引入玩家与平台基础碰撞逻辑，使玩家落到平台上时停止下落。

碰撞是游戏核心交互基础，后续平台滚动、游戏失败条件、关卡设计都依赖碰撞系统。

如果碰撞逻辑不正确（例如玩家穿透平台、侧面误判碰撞、速度未归零），后续所有功能都会受影响。

因此，在 G007 实现前，需要先定义碰撞测试协议，确保 Tester 可以独立验证碰撞逻辑。

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

### 3.3 重力行为检查

T047 的重力测试协议可以验证：

- 重力常量（`GRAVITY`）存在
- 垂直速度（`velocityY`）更新
- 玩家 `y` 坐标随时间增加
- 重力更新集成到 `gameLoop` 中

### 3.4 缺失的能力

当前 Tester 还不能验证：

- 玩家是否会在平台上停止下落
- 是否存在碰撞检测函数
- 碰撞逻辑是否检测玩家底部位置
- 碰撞逻辑是否检查水平范围重叠
- 碰撞逻辑是否只从上方触发
- 落到平台后 `y` 坐标是否修正
- 落到平台后垂直速度是否归零
- 玩家是否会穿透平台

G007 引入平台碰撞后，需要新增碰撞行为检查协议。

## 4. G007 测试范围

### 4.1 测试目标

G007 只测试玩家与平台基础碰撞：

- 玩家下落时能检测到平台
- 玩家落到平台上时停止下落
- 玩家不会穿过平台
- 玩家站在平台上时垂直速度归零或停止增加
- 碰撞逻辑集成到 `gameLoop` 中
- 平台数据来源于 G005 的固定平台布局

### 4.2 不测试什么

G007 不测试以下内容：

- 平台滚动
- 随机平台
- 游戏失败条件
- 游戏胜利条件
- 角色技能系统
- 复杂物理系统
- 微信小游戏 / 抖音小游戏适配

### 4.3 范围控制原则

- G007 只做玩家落到固定平台上停止，不做平台滚动
- G007 不引入随机平台生成
- G007 不引入游戏失败条件
- G007 不引入角色技能系统
- 如果 G007 实现中包含明显平台滚动、随机生成或失败条件，应视为越界

## 5. 不做什么

本协议明确不做以下事项：

- 不引入浏览器自动化
- 不测试平台滚动
- 不测试随机平台生成
- 不测试游戏失败条件
- 不测试游戏胜利条件
- 不测试角色技能系统
- 不修改小游戏业务代码

## 6. 碰撞状态检查项（C 组）

| 编号 | 测试项 | 检查目标 | 必需 |
|------|--------|----------|------|
| C-01 | 碰撞检测函数存在 | `checkPlatformCollision` / `detectPlatformCollision` / `handlePlatformCollision` | 是 |
| C-02 | 碰撞逻辑在下落时执行 | 碰撞检测和 `vy` / `velocityY` 结合 | 是 |
| C-03 | 存在站立状态或平台接触状态 | `isOnPlatform` / `onPlatform` / `currentPlatform` | 否 |

### C-01 碰撞检测函数存在

检查 `script.js` 中是否定义了碰撞检测函数。

关键词：

```text
checkPlatformCollision
detectPlatformCollision
handlePlatformCollision
checkCollision
collisionDetection
```

预期：至少匹配一个关键词。

### C-02 碰撞逻辑在下落时执行

检查 `script.js` 中碰撞检测是否与垂直速度（`vy` / `velocityY`）结合。

关键词模式：

```text
vy > 0
velocityY > 0
vy >= 0
velocityY >= 0
falling
isFalling
```

预期：碰撞检测应在玩家处于下落状态时执行。

### C-03 存在站立状态或平台接触状态

检查 `script.js` 中是否定义了站立状态或平台接触状态变量。

关键词：

```text
isOnPlatform
onPlatform
currentPlatform
grounded
isGrounded
standingOn
```

预期：此项为非必需，但建议存在。

## 7. 平台数据检查项（P 组）

| 编号 | 测试项 | 检查目标 | 必需 |
|------|--------|----------|------|
| P-01 | 平台数据存在 | `platforms` 或 `PLATFORM_LAYOUT` | 是 |
| P-02 | 平台有 x/y/width/height 信息 | `x` / `y` / `width` / `height` | 是 |
| P-03 | 碰撞逻辑遍历平台 | `for` / `forEach` / `some` / `find` 平台 | 是 |

### P-01 平台数据存在

检查 `script.js` 中是否存在平台数据定义。

关键词：

```text
platforms
PLATFORM_LAYOUT
platformData
platformList
```

预期：至少匹配一个关键词。

### P-02 平台有 x/y/width/height 信息

检查 `script.js` 中平台数据是否包含位置和尺寸信息。

关键词模式：

```text
platforms.*x
platforms.*y
platforms.*width
platforms.*height
platforms.*w
platforms.*h
```

预期：平台数据应至少包含 `x`、`y`、`width`、`height` 或缩写形式。

### P-03 碰撞逻辑遍历平台

检查 `script.js` 中碰撞检测函数是否遍历平台数组。

关键词模式：

```text
platforms.forEach
platforms.some
platforms.find
for.*platforms
for.*platform
```

预期：碰撞检测应对每个平台进行检测。

## 8. 玩家落到平台检查项（L 组）

| 编号 | 测试项 | 检查目标 | 必需 |
|------|--------|----------|------|
| L-01 | 判断玩家底部位置 | `playerBottom` / `playerState.y + playerHeight` | 是 |
| L-02 | 判断玩家水平范围重叠 | 玩家 `x` 范围与平台 `x` 范围比较 | 是 |
| L-03 | 判断从上方落到平台 | `previousY` / `previousBottom` / `vy >= 0` | 是 |

### L-01 判断玩家底部位置

检查 `script.js` 中碰撞检测是否计算玩家底部位置。

关键词模式：

```text
playerBottom
playerState.y + playerHeight
player.y + player.height
playerY + playerH
bottom
playerState.y + height
```

预期：碰撞检测应使用玩家底部位置与平台顶部比较。

### L-02 判断玩家水平范围重叠

检查 `script.js` 中碰撞检测是否检查玩家与平台的水平范围重叠。

关键词模式：

```text
playerState.x + playerWidth > platform.x
playerX + playerWidth > platform.x
playerRight > platform.x
playerState.x < platform.x + platform.width
overlap
horizontalOverlap
```

预期：碰撞检测应验证玩家水平范围与平台水平范围有重叠。

### L-03 判断从上方落到平台

检查 `script.js` 中碰撞检测是否只从上方触发。

关键词模式：

```text
previousY
previousBottom
lastY
vy >= 0
velocityY >= 0
vy > 0
velocityY > 0
fromAbove
```

预期：碰撞检测应确保玩家是从上方落到平台（下落方向），不是从下方或侧面。

## 9. 停止下落检查项（S 组）

| 编号 | 测试项 | 检查目标 | 必需 |
|------|--------|----------|------|
| S-01 | 落到平台后修正 y 坐标 | `playerState.y = platform.y - playerHeight` | 是 |
| S-02 | 落到平台后垂直速度归零 | `vy = 0` / `velocityY = 0` | 是 |
| S-03 | 更新玩家 DOM 位置 | `style.top` / `updatePlayerPosition()` | 是 |

### S-01 落到平台后修正 y 坐标

检查 `script.js` 中是否存在碰撞后修正玩家 `y` 坐标的逻辑。

关键词模式：

```text
playerState.y = platform.y - playerHeight
playerState.y = platform.y - height
playerY = platform.y - playerH
playerState.y = plat.y
snapTo
```

预期：碰撞后玩家 `y` 坐标应修正为平台顶部减去玩家高度。

### S-02 落到平台后垂直速度归零

检查 `script.js` 中是否存在碰撞后垂直速度归零的逻辑。

关键词模式：

```text
velocityY = 0
vy = 0
velocityY = 0
speedY = 0
verticalSpeed = 0
```

预期：碰撞后垂直速度应设为 0，防止玩家继续下落。

### S-03 更新玩家 DOM 位置

检查 `script.js` 中碰撞后是否更新玩家 DOM 位置。

关键词模式：

```text
style.top
updatePlayerPosition
renderPlayer
drawPlayer
```

预期：碰撞后应更新玩家在页面上的实际位置。

## 10. 防穿透检查项（T 组）

| 编号 | 测试项 | 检查目标 | 必需 |
|------|--------|----------|------|
| T-01 | 使用上一帧位置或下落方向避免误判 | `previousY` / `lastY` / `vy > 0` | 是 |
| T-02 | 玩家不能直接穿过平台 | 有 `y` 修正逻辑 | 是 |
| T-03 | 碰撞只在下落时触发 | `vy >= 0` / `velocityY >= 0` | 是 |

### T-01 使用上一帧位置或下落方向避免误判

检查 `script.js` 中碰撞检测是否使用上一帧位置或下落方向来判断。

关键词模式：

```text
previousY
lastY
prevY
oldY
vy > 0
velocityY > 0
```

预期：碰撞检测应使用上一帧位置或下落方向，避免高速下落时穿越平台。

### T-02 玩家不能直接穿过平台

检查 `script.js` 中是否存在 `y` 坐标修正逻辑防止穿透。

关键词模式：

```text
playerState.y = platform.y - playerHeight
playerState.y = plat.y - h
snapToPlatform
clampY
```

预期：碰撞后必须有 `y` 坐标修正，确保玩家不会穿过平台。

### T-03 碰撞只在下落时触发

检查 `script.js` 中碰撞检测是否限制为只在下落时触发。

关键词模式：

```text
vy >= 0
velocityY >= 0
vy > 0
velocityY > 0
isFalling
falling
```

预期：碰撞检测应只在玩家下落时触发，跳起或上升时不触发。

## 11. 范围限制检查项（O 组）

| 编号 | 测试项 | 检查目标 | 必需 |
|------|--------|----------|------|
| O-01 | 不包含平台滚动逻辑 | 不应出现 `scrollPlatforms` / `platformScroll` | 是 |
| O-02 | 不包含随机平台生成 | 不应出现 `Math.random` 用于平台生成 | 是 |
| O-03 | 不包含游戏失败条件 | 不应出现 `gameOver` / `fail` 判定 | 是 |

### O-01 不包含平台滚动逻辑

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
- 如果只出现注释或占位符（如 `// TODO: scroll`），标记为 `PASS`，但备注建议移除

### O-02 不包含随机平台生成

检查 `script.js` 中是否包含随机平台生成逻辑。

范围控制关键词：

```text
Math.random
randomPlatform
generatePlatform
createRandomPlatform
```

判定规则：

- 如果出现使用 `Math.random` 生成平台的逻辑，标记为 `FAIL`
- 如果 `Math.random` 仅用于其他无关逻辑（如粒子效果），标记为 `PASS`
- 需要结合上下文判断

### O-03 不包含游戏失败条件

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

### O 组说明

O 组是范围控制检查，目的是防止 G007 越界实现。

如果出现明显平台滚动、随机平台生成、失败条件的完整实现，应判为 `FAIL` 或至少 `REQUEST_REVIEW`。

## 12. PASS / FAIL / BLOCKED 规则

### 12.1 判定规则

| 条件 | 结果 |
|------|------|
| 全部必需项通过 | `PASS` |
| 任一必需项失败 | `FAIL` |
| `script.js` 不存在或无法读取 | `BLOCKED` |
| 平台数据不存在 | `BLOCKED` |
| 范围越界实现明显存在（O 组 FAIL） | `FAIL` |

### 12.2 结果枚举

| 结果 | 含义 | 说明 |
|------|------|------|
| `PASS` | 全部必需项通过 | 碰撞逻辑测试通过 |
| `FAIL` | 至少一个必需项失败 | 碰撞逻辑测试失败 |
| `BLOCKED` | 无法执行测试 | 如 `script.js` 缺失或平台数据缺失 |

### 12.3 与其他测试的关系

碰撞行为检查与基础静态检查、行为静态检查、重力行为检查独立判定：

- 基础静态检查（T030）：验证文件结构和关键元素
- 行为静态检查（T036）：验证键盘移动逻辑
- 重力行为检查（T047）：验证重力下落逻辑
- 碰撞行为检查（本协议）：验证玩家与平台碰撞逻辑

四类检查都 `PASS` 才能视为 Tester 整体 `PASS`。

## 13. 测试报告格式

碰撞行为测试报告使用以下格式：

```markdown
# Collision Check Test Report

## Agent

Tester Agent

## Task

任务编号：<task-id>
任务名称：<task名称>

## Status

PASS / FAIL / BLOCKED

## Project

项目路径：<project-root>

## Test Scope

- 碰撞函数 / 状态检查（C 组）
- 平台数据检查（P 组）
- 玩家落到平台检查（L 组）
- 停止下落检查（S 组）
- 防穿透检查（T 组）
- 范围限制检查（O 组）

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

- reports/test/<task-id>-collision-test-report.md

## Next Action

建议下一步：
```

报告模板文件：`templates/agent-output/tester-collision-check-template.md`

## 14. 完成证据路径

### 14.1 碰撞行为检查报告

碰撞行为检查报告保存路径：

```text
<project-root>/reports/test/<task-id>-collision-test-report.md
```

例如：

```text
projects/down-100-floors-game/reports/test/G007-collision-test-report.md
```

### 14.2 与其他测试报告的关系

- `G007-test-report.md`：基础静态检查报告
- `G007-behavior-test-report.md`：行为静态检查报告（如果存在）
- `G007-gravity-test-report.md`：重力行为检查报告
- `G007-collision-test-report.md`：碰撞行为检查报告

各报告独立生成，独立判定。

### 14.3 Main Agent 应读取的证据

后续 Main Agent 应同时读取以下报告：

| 报告 | 路径 | 作用 |
|------|------|------|
| 基础测试报告 | `reports/test/G007-test-report.md` | 验证文件结构和元素 |
| 碰撞测试报告 | `reports/test/G007-collision-test-report.md` | 验证碰撞逻辑 |
| 开发报告 | `reports/dev/G007-dev-report.md` | 记录开发内容 |
| 审查报告 | `reports/review/G007-review-report.md` | DeepSeek 审查结论 |
| 综合决策报告 | `reports/main/G007-main-decision.md` | Main Agent 综合决策 |

## 15. T054 实现建议

### 15.1 T054 应实现什么

T054 是 G007 Tester / Reviewer / Main Decision 完整闭环，应实现以下内容：

1. **运行基础静态检查** — 使用 T030 的 `test-game-task` 命令
2. **运行碰撞行为检查** — 基于本协议实现碰撞检查逻辑
3. **运行 Reviewer 审查** — 使用 DeepSeek Reviewer
4. **运行 Main Decision** — 综合所有报告生成决策

### 15.2 碰撞检查实现建议

碰撞行为检查建议在 `tools/tester_runner.py` 中新增函数：

- `check_collision_state(script_content)` — C 组检查
- `check_platform_data(script_content)` — P 组检查
- `check_landing_logic(script_content)` — L 组检查
- `check_stop_falling(script_content)` — S 组检查
- `check_anti_penetration(script_content)` — T 组检查
- `check_collision_scope_limit(script_content)` — O 组检查
- `run_collision_check(project_path, task_id)` — 主入口

### 15.3 新增命令建议

建议新增命令：

```text
python runner.py test-collision-check --project projects/down-100-floors-game --task G007
```

或者复用 `test-game-task` 命令，根据任务编号自动选择是否运行碰撞检查。

### 15.4 报告生成建议

碰撞检查报告应：

- 使用 `templates/agent-output/tester-collision-check-template.md` 模板
- 保存到 `<project-root>/reports/test/G007-collision-test-report.md`
- 包含所有 18 个检查项的结果
- 明确标注 `PASS` / `FAIL` / `BLOCKED`
