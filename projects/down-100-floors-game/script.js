// G002: 基础页面交互 — 按钮点击、状态切换、楼层显示
// G003: 玩家角色显示

(function () {
    const startBtn = document.getElementById('start-btn');
    const floorDisplay = document.getElementById('floor-display');
    const statusDisplay = document.getElementById('status-display');
    const gameArea = document.getElementById('game-area');
    const player = document.getElementById('player');

    // 玩家状态
    var playerState = {
        x: 0,
        y: 0,
        width: 30,
        height: 30
    };

    function setStatus(text, cssClass) {
        statusDisplay.textContent = text;
        statusDisplay.className = 'info-value ' + cssClass;
    }

    function initPlayer() {
        var areaWidth = gameArea.clientWidth;
        playerState.x = (areaWidth - playerState.width) / 2;
        playerState.y = 20;
        updatePlayerPosition();
        player.style.display = 'block';
    }

    function updatePlayerPosition() {
        player.style.left = playerState.x + 'px';
        player.style.top = playerState.y + 'px';
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
    }

    startBtn.addEventListener('click', function () {
        setStatus('游戏中', 'status-playing');
        startBtn.textContent = '游戏中...';
        startBtn.disabled = true;
        // 隐藏占位文字
        var placeholder = gameArea.querySelector('.placeholder-text');
        if (placeholder) placeholder.style.display = 'none';
        // 初始化并显示玩家角色
        initPlayer();
        console.log('Game started — player displayed at center top.');
    });

    resetUI();
})();
