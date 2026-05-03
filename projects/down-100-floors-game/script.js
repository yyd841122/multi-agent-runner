// G002: 基础页面交互 — 按钮点击、状态切换、楼层显示

(function () {
    const startBtn = document.getElementById('start-btn');
    const floorDisplay = document.getElementById('floor-display');
    const statusDisplay = document.getElementById('status-display');
    const gameArea = document.getElementById('game-area');

    function setStatus(text, cssClass) {
        statusDisplay.textContent = text;
        statusDisplay.className = 'info-value ' + cssClass;
    }

    function resetUI() {
        floorDisplay.textContent = '0 / 100';
        setStatus('准备开始', 'status-ready');
        startBtn.textContent = '开始游戏';
        startBtn.disabled = false;
        // 显示占位文字
        const placeholder = gameArea.querySelector('.placeholder-text');
        if (placeholder) placeholder.style.display = '';
    }

    startBtn.addEventListener('click', function () {
        setStatus('游戏中', 'status-playing');
        startBtn.textContent = '游戏中...';
        startBtn.disabled = true;
        // 隐藏占位文字
        const placeholder = gameArea.querySelector('.placeholder-text');
        if (placeholder) placeholder.style.display = 'none';
        // 后续任务会在这里启动游戏循环
        console.log('Game started — waiting for game logic implementation.');
    });

    resetUI();
})();
