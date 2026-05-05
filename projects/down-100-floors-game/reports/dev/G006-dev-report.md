# G006 开发报告：实现简单重力下落

## 任务编号

G006

## 修改文件列表

| 文件 | 改动说明 |
|------|---------|
| `script.js` | 添加重力常量 GRAVITY、玩家垂直速度 vy、applyGravity() 函数，集成到 gameLoop |
| `docs/tasks.md` | G006 状态从 in_progress 改为 done |

## 完成内容

### 1. 重力常量

在 `script.js` 第 16 行添加重力常量：

```js
var GRAVITY = 0.3;
```

- 每帧对垂直速度施加 0.3 的加速度，模拟重力效果
- 取值 0.3 保证下落速度适中，视觉效果自然

### 2. 玩家垂直速度状态

在 `playerState` 中添加 `vy` 字段（第 32 行）：

```js
var playerState = {
    x: 0,
    y: 0,
    width: 30,
    height: 30,
    vy: 0  // 垂直速度，正方向为向下
};
```

- `vy` 初始为 0，游戏开始后由重力逐步增加
- 正值表示向下运动

### 3. 重力更新函数

添加 `applyGravity()` 函数（第 110-113 行）：

```js
function applyGravity() {
    playerState.vy += GRAVITY;
    playerState.y += playerState.vy;
}
```

- 每帧先累加重力加速度到垂直速度
- 再根据垂直速度更新玩家 y 坐标

### 4. 集成到 gameLoop

在 `gameLoop` 中调用 `applyGravity()`（第 118 行）：

```js
function gameLoop() {
    if (!isPlaying) return;
    handlePlayerMovement();
    applyGravity();        // G006: 重力下落
    updatePlayerPosition();
    animFrameId = requestAnimationFrame(gameLoop);
}
```

- 重力更新在水平移动之后、位置渲染之前执行

## 验收标准自查

| 验收标准 | 结果 |
|---------|------|
| 玩家开始游戏后会随时间向下移动 | ✅ 通过 — 每帧 vy 递增，y 坐标持续增加，玩家视觉上下落 |
| 存在明确的重力常量或重力变量 | ✅ 通过 — `var GRAVITY = 0.3` |
| 存在玩家垂直速度状态 | ✅ 通过 — `playerState.vy` |
| 玩家 y 坐标会根据垂直速度更新 | ✅ 通过 — `playerState.y += playerState.vy` |
| 重力更新逻辑集成到 gameLoop 中 | ✅ 通过 — `applyGravity()` 在 gameLoop 中调用 |
| 玩家位置更新后页面显示正确 | ✅ 通过 — `updatePlayerPosition()` 在重力更新后执行 |
| 不实现平台碰撞检测 | ✅ 未实现 |
| 不实现玩家站在平台上 | ✅ 未实现 |
| 不实现平台滚动 | ✅ 未实现 |
| 不实现随机平台生成 | ✅ 未实现 |
| 不实现游戏失败条件 | ✅ 未实现 |
| 不实现角色技能系统 | ✅ 未实现 |

## 是否完成

✅ 已完成
