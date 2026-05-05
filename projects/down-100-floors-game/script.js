// G002: 基础页面交互 — 按钮点击、状态切换、楼层显示
// G003: 玩家角色显示
// G004: 玩家键盘左右移动
// G005: 基础平台显示
// G006: 简单重力下落
// G007: 玩家与平台基础碰撞

(function () {
    const startBtn = document.getElementById('start-btn');
    const floorDisplay = document.getElementById('floor-display');
    const statusDisplay = document.getElementById('status-display');
    const gameArea = document.getElementById('game-area');
    const player = document.getElementById('player');
    const platformEls = gameArea.querySelectorAll('.platform');

    var MOVE_SPEED = 4;
    var GRAVITY = 0.3;
    var isPlaying = false;
    var animFrameId = null;

    // 按键状态
    var keys = {
        ArrowLeft: false,
        ArrowRight: false
    };

    // 玩家状态
    var playerState = {
        x: 0,
        y: 0,
        width: 30,
        height: 30,
        vy: 0
    };

    // 平台固定布局：left(百分比), top(px), width(百分比)
    var PLATFORM_LAYOUT = [
        { left: 5,  top: 120, width: 55 },
        { left: 35, top: 200, width: 50 },
        { left: 10, top: 280, width: 45 },
        { left: 40, top: 360, width: 50 },
        { left: 5,  top: 440, width: 55 }
    ];

    // 平台状态
    var platforms = [];

    function setStatus(text, cssClass) {
        statusDisplay.textContent = text;
        statusDisplay.className = 'info-value ' + cssClass;
    }

    function initPlayer() {
        var areaWidth = gameArea.clientWidth;
        playerState.x = (areaWidth - playerState.width) / 2;
        playerState.y = 20;
        playerState.vy = 0;
        updatePlayerPosition();
        player.style.display = 'block';
    }

    function updatePlayerPosition() {
        player.style.left = playerState.x + 'px';
        player.style.top = playerState.y + 'px';
    }

    function initPlatforms() {
        platforms = [];
        for (var i = 0; i < PLATFORM_LAYOUT.length; i++) {
            var layout = PLATFORM_LAYOUT[i];
            platforms.push({
                leftPct: layout.left,
                top: layout.top,
                widthPct: layout.width,
                el: platformEls[i]
            });
        }
        for (var j = 0; j < platforms.length; j++) {
            var p = platforms[j];
            p.el.style.left = p.leftPct + '%';
            p.el.style.top = p.top + 'px';
            p.el.style.width = p.widthPct + '%';
            p.el.style.display = 'block';
        }
    }

    function hidePlatforms() {
        for (var i = 0; i < platformEls.length; i++) {
            platformEls[i].style.display = 'none';
        }
    }

    function handlePlayerMovement() {
        var areaWidth = gameArea.clientWidth;
        if (keys.ArrowLeft) {
            playerState.x -= MOVE_SPEED;
        }
        if (keys.ArrowRight) {
            playerState.x += MOVE_SPEED;
        }
        // 边界限制：左边界
        if (playerState.x < 0) {
            playerState.x = 0;
        }
        // 边界限制：右边界
        if (playerState.x > areaWidth - playerState.width) {
            playerState.x = areaWidth - playerState.width;
        }
    }

    function applyGravity() {
        playerState.vy += GRAVITY;
        playerState.y += playerState.vy;
    }

    // G007: 计算平台的像素边界（left/width 从百分比转换为像素）
    function getPlatformBounds(platform) {
        var areaWidth = gameArea.clientWidth;
        var leftPx = (platform.leftPct / 100) * areaWidth;
        var widthPx = (platform.widthPct / 100) * areaWidth;
        return {
            left: leftPx,
            top: platform.top,
            right: leftPx + widthPx,
            bottom: platform.top + 12  // platform height from CSS (border-box)
        };
    }

    // G007: 碰撞检测 — 玩家下落时检测是否落到平台顶面
    function checkPlatformCollision() {
        if (playerState.vy < 0) return; // 向上移动时不检测

        var playerBottom = playerState.y + playerState.height;
        var playerLeft = playerState.x;
        var playerRight = playerState.x + playerState.width;
        var prevBottom = playerBottom - playerState.vy; // 上一帧底部位置

        for (var i = 0; i < platforms.length; i++) {
            var bounds = getPlatformBounds(platforms[i]);

            // 垂直方向：玩家底部穿过或接触到平台顶部，且上一帧在平台上方
            if (playerBottom >= bounds.top && prevBottom <= bounds.top) {
                // 水平方向：玩家与平台有重叠
                if (playerRight > bounds.left && playerLeft < bounds.right) {
                    // 碰撞：将玩家放在平台顶部，垂直速度归零
                    playerState.y = bounds.top - playerState.height;
                    playerState.vy = 0;
                    return;
                }
            }
        }
    }

    function gameLoop() {
        if (!isPlaying) return;
        handlePlayerMovement();
        applyGravity();
        checkPlatformCollision();
        updatePlayerPosition();
        animFrameId = requestAnimationFrame(gameLoop);
    }

    function startGameLoop() {
        isPlaying = true;
        animFrameId = requestAnimationFrame(gameLoop);
    }

    function stopGameLoop() {
        isPlaying = false;
        if (animFrameId) {
            cancelAnimationFrame(animFrameId);
            animFrameId = null;
        }
    }

    function resetUI() {
        floorDisplay.textContent = '0 / 100';
        setStatus('准备开始', 'status-ready');
        startBtn.textContent = '开始游戏';
        startBtn.disabled = false;
        // 显示占位文字
        var placeholder = gameArea.querySelector('.placeholder-text');
        if (placeholder) placeholder.style.display = '';
        // 隐藏玩家角色
        player.style.display = 'none';
        // 隐藏平台
        hidePlatforms();
        // 重置按键状态
        keys.ArrowLeft = false;
        keys.ArrowRight = false;
    }

    // 键盘事件
    document.addEventListener('keydown', function (e) {
        if (!isPlaying) return;
        if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
            e.preventDefault();
            keys[e.key] = true;
        }
    });

    document.addEventListener('keyup', function (e) {
        if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
            keys[e.key] = false;
        }
    });

    startBtn.addEventListener('click', function () {
        setStatus('游戏中', 'status-playing');
        startBtn.textContent = '游戏中...';
        startBtn.disabled = true;
        // 隐藏占位文字
        var placeholder = gameArea.querySelector('.placeholder-text');
        if (placeholder) placeholder.style.display = 'none';
        // 初始化并显示平台
        initPlatforms();
        // 初始化并显示玩家角色
        initPlayer();
        // 启动游戏循环
        startGameLoop();
        console.log('Game started — platforms and player displayed, keyboard movement enabled.');
    });

    resetUI();
})();
