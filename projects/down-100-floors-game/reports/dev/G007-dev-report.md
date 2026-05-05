# G007 开发报告：实现玩家与平台基础碰撞

## 任务编号

G007

## 修改文件列表

| 文件 | 改动说明 |
|------|---------|
| `script.js` | 添加 `getPlatformBounds()` 和 `checkPlatformCollision()` 函数，集成到 gameLoop |
| `docs/tasks.md` | G007 状态从 in_progress 改为 done |

## 完成内容

### 1. 平台像素边界计算

添加 `getPlatformBounds()` 函数（第 116-127 行）：

```js
function getPlatformBounds(platform) {
    var areaWidth = gameArea.clientWidth;
    var leftPx = (platform.leftPct / 100) * areaWidth;
    var widthPx = (platform.widthPct / 100) * areaWidth;
    return {
        left: leftPx,
        top: platform.top,
        right: leftPx + widthPx,
        bottom: platform.top + 12
    };
}
```

- 将 G005 平台的百分比坐标（left、width）转换为像素值
- 每帧动态计算，确保窗口缩放时仍然正确
- 平台高度取 CSS 定义值 12px（border-box）

### 2. 碰撞检测函数

添加 `checkPlatformCollision()` 函数（第 129-152 行）：

```js
function checkPlatformCollision() {
    if (playerState.vy < 0) return;

    var playerBottom = playerState.y + playerState.height;
    var playerLeft = playerState.x;
    var playerRight = playerState.x + playerState.width;
    var prevBottom = playerBottom - playerState.vy;

    for (var i = 0; i < platforms.length; i++) {
        var bounds = getPlatformBounds(platforms[i]);

        if (playerBottom >= bounds.top && prevBottom <= bounds.top) {
            if (playerRight > bounds.left && playerLeft < bounds.right) {
                playerState.y = bounds.top - playerState.height;
                playerState.vy = 0;
                return;
            }
        }
    }
}
```

- **垂直判定**：当前帧玩家底部 >= 平台顶部，且上一帧玩家底部 <= 平台顶部（防止穿台）
- **水平判定**：玩家矩形与平台矩形有水平重叠
- **碰撞响应**：将玩家 y 坐标修正到平台顶部，垂直速度归零
- 仅在玩家下落（vy >= 0）时检测，向上移动时跳过

### 3. 集成到 gameLoop

在 `gameLoop` 中 `applyGravity()` 之后、`updatePlayerPosition()` 之前调用碰撞检测（第 158 行）：

```js
function gameLoop() {
    if (!isPlaying) return;
    handlePlayerMovement();
    applyGravity();
    checkPlatformCollision();  // G007: 碰撞检测
    updatePlayerPosition();
    animFrameId = requestAnimationFrame(gameLoop);
}
```

- 执行顺序：移动 → 重力 → 碰撞修正 → 渲染，保证位置正确

## 验收标准自查

| 验收标准 | 结果 |
|---------|------|
| 玩家下落时可以检测到平台 | ✅ 通过 — `checkPlatformCollision()` 遍历所有平台并检测碰撞 |
| 玩家落到平台上时停止下落 | ✅ 通过 — 碰撞时 `playerState.y` 修正到平台顶部 |
| 玩家不会穿过平台 | ✅ 通过 — `prevBottom <= bounds.top` 判定确保捕捉穿越帧 |
| 玩家站在平台上时垂直速度归零或停止增加 | ✅ 通过 — 碰撞时 `playerState.vy = 0`；每帧重力微增 0.3 后立即被碰撞修正重置 |
| 碰撞逻辑集成到 gameLoop 中 | ✅ 通过 — `checkPlatformCollision()` 在 gameLoop 中 `applyGravity()` 后调用 |
| 平台数据来源于 G005 的固定平台布局 | ✅ 通过 — 复用 `platforms` 数组，通过 `getPlatformBounds()` 计算像素坐标 |
| 玩家位置更新后页面显示正确 | ✅ 通过 — 碰撞修正后统一由 `updatePlayerPosition()` 渲染 |
| 不实现平台滚动 | ✅ 未实现 |
| 不实现随机平台生成 | ✅ 未实现 |
| 不实现游戏失败条件 | ✅ 未实现 |
| 不实现游戏胜利条件 | ✅ 未实现 |
| 不实现角色技能系统 | ✅ 未实现 |

## 是否完成

✅ 已完成
