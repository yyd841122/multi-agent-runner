# G004 开发报告：实现玩家键盘左右移动

## 任务编号

G004

## 任务目标

让玩家角色可以通过键盘左右方向键在游戏区域内移动，为后续重力和平台玩法做准备。

## 修改文件列表

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| `script.js` | 修改 | 添加键盘事件监听、游戏循环、玩家移动逻辑、边界检测 |

## 完成内容

### 1. 键盘事件监听

- 添加 `keydown` 和 `keyup` 事件监听器
- 跟踪 `ArrowLeft` 和 `ArrowRight` 按键状态
- 仅在游戏进行中（`isPlaying === true`）时响应按键
- 调用 `e.preventDefault()` 防止方向键触发页面滚动

### 2. 游戏循环

- 使用 `requestAnimationFrame` 实现游戏主循环
- 每帧执行：移动处理 → 位置更新 → 渲染
- 提供 `startGameLoop()` 和 `stopGameLoop()` 控制循环生命周期
- 点击"开始游戏"时启动循环

### 3. 玩家移动逻辑

- `MOVE_SPEED = 4`：每帧移动 4 像素
- 左方向键按下时 `x -= MOVE_SPEED`
- 右方向键按下时 `x += MOVE_SPEED`
- 支持同时按住左右键（互相抵消效果）

### 4. 边界检测

- 左边界：`playerState.x < 0` 时重置为 `0`
- 右边界：`playerState.x > areaWidth - playerState.width` 时限制
- 每帧读取 `gameArea.clientWidth` 确保边界值准确

### 5. 状态管理

- 新增 `isPlaying` 标志控制游戏循环和键盘响应
- 新增 `animFrameId` 管理动画帧
- `resetUI()` 中重置按键状态

## 验收标准自查

| 验收标准 | 状态 | 说明 |
|---------|------|------|
| 玩家可以通过键盘左方向键向左移动 | PASS | keydown 监听 ArrowLeft，x 递减 |
| 玩家可以通过键盘右方向键向右移动 | PASS | keydown 监听 ArrowRight，x 递增 |
| 玩家不能移出游戏区域左边界 | PASS | playerState.x < 0 时 clamp 到 0 |
| 玩家不能移出游戏区域右边界 | PASS | playerState.x > areaWidth - width 时 clamp |
| 玩家位置更新后页面显示正确 | PASS | gameLoop 每帧调用 updatePlayerPosition |
| 不实现重力 | PASS | 未添加任何重力逻辑 |
| 不实现平台生成 | PASS | 未添加平台相关代码 |
| 不实现碰撞检测 | PASS | 未添加碰撞检测逻辑 |
| 不实现角色技能系统 | PASS | 未添加技能相关代码 |

## 技术实现说明

- 使用按键状态表（`keys` 对象）而非单次按键事件，实现持续平滑移动
- `requestAnimationFrame` 保证与浏览器刷新率同步，避免卡顿
- 每帧重新读取 `gameArea.clientWidth`，确保窗口大小变化时边界检测仍然准确
- 移动逻辑与渲染分离，便于后续扩展（重力、碰撞等）

## 是否完成

已完成
