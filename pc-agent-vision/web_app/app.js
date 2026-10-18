/**
 * 未来道具研究所 · 牧濑红莉栖具身交互中枢 Web App
 * Future Gadget Laboratory - Makise Kurisu Embodied Core
 * Steins;Gate Cyberpunk / Amadeus Interface Controller
 */

// ==========================================
// 1. 全局状态与网络通信
// ==========================================
let currentTab = 'comm';
let currentGame = null;
let currentMode = 11; // 默认微笑表情
let isListening = false;
let speechRecognizer = null;
let ws = null;
let matrixAnimId = null;
let countdownRemaining = 0;
let countdownTotal = 0;

// 游戏状态暂存 (用于本地拟真画布渲染)
let snakeState = {
    body: [{x: 8, y: 8}, {x: 8, y: 9}, {x: 8, y: 10}],
    dir: {x: 0, y: -1},
    food: {x: 4, y: 4}
};

// ==========================================
// 2. 初始化与生命周期
// ==========================================
window.addEventListener('DOMContentLoaded', () => {
    initNixieMeter();
    initWebSpeech();
    initMatrixCanvas();
    initWebSocket();
    fetchSystemStatus();

    // 绑定触摸震动反馈
    document.querySelectorAll('button').forEach(btn => {
        btn.addEventListener('pointerdown', () => {
            if (navigator.vibrate) navigator.vibrate(15);
        });
    });
});

// ==========================================
// 3. 标签页切换 (Tab Switching)
// ==========================================
function switchTab(tabId) {
    currentTab = tabId;
    const tabs = ['comm', 'matrix', 'arcade', 'system'];
    tabs.forEach(t => {
        const btn = document.getElementById(`tabBtn${capitalize(t)}`);
        const content = document.getElementById(`tabContent${capitalize(t)}`);
        if (btn) btn.classList.toggle('active', t === tabId);
        if (content) content.classList.toggle('active', t === tabId);
    });

    if (navigator.vibrate) navigator.vibrate(20);
}

function capitalize(s) {
    return s.charAt(0).toUpperCase() + s.slice(1);
}

// ==========================================
// 4. 世界线变动仪 (Nixie Tube Divergence Meter)
// ==========================================
function initNixieMeter() {
    const meter = document.getElementById('nixieMeter');
    if (!meter) return;
    meter.addEventListener('click', () => {
        triggerDivergenceShift();
    });
    // 初始轻微闪烁入场
    triggerDivergenceShift();
}

function triggerDivergenceShift() {
    const targetDigits = ['1', '0', '4', '8', '5', '9', '6'];
    const tubes = [
        document.getElementById('tube0'),
        document.getElementById('tube1'),
        document.getElementById('tube2'),
        document.getElementById('tube3'),
        document.getElementById('tube4'),
        document.getElementById('tube5'),
        document.getElementById('tube6')
    ];

    let ticks = 0;
    const maxTicks = 12;
    const interval = setInterval(() => {
        ticks++;
        tubes.forEach((t, idx) => {
            if (ticks < maxTicks) {
                t.textContent = Math.floor(Math.random() * 10);
                t.style.textShadow = '0 0 16px #ff2200, 0 0 32px #ff4400';
            } else {
                t.textContent = targetDigits[idx];
                t.style.textShadow = '';
            }
        });

        if (ticks >= maxTicks) {
            clearInterval(interval);
            updateAmadeusMood("“世界线变动率测量完毕。1.048596%——我们已经到达了命运石之门。”", "命运石之门线");
        }
    }, 60);
}

// ==========================================
// 5. 语音识别与文字对话 (COMM)
// ==========================================
function initWebSpeech() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
        speechRecognizer = new SpeechRecognition();
        speechRecognizer.lang = 'zh-CN';
        speechRecognizer.continuous = false;
        speechRecognizer.interimResults = false;

        speechRecognizer.onstart = () => {
            isListening = true;
            updateMicUI(true);
        };

        speechRecognizer.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            console.log("[语音识别得到]:", transcript);
            const input = document.getElementById('textInput');
            if (input) input.value = transcript;
            sendMessage(transcript);
        };

        speechRecognizer.onerror = (e) => {
            console.warn("[语音识别异常]:", e);
            updateMicUI(false);
        };

        speechRecognizer.onend = () => {
            isListening = false;
            updateMicUI(false);
        };
    } else {
        console.warn("当前浏览器未直接暴露 Web Speech API，可直接文字输入。");
    }
}

function toggleWebSpeech() {
    if (!speechRecognizer) {
        alert("浏览器未支持 Web Speech API，请直接在输入框打字发送！");
        return;
    }
    if (isListening) {
        speechRecognizer.stop();
    } else {
        try {
            speechRecognizer.start();
        } catch (e) {
            console.warn("启动语音识别失败:", e);
        }
    }
}

function updateMicUI(listening) {
    const micBtn = document.getElementById('micBtn');
    const micIcon = document.getElementById('micIcon');
    const micWave = document.getElementById('micWave');
    if (micBtn) micBtn.classList.toggle('listening', listening);
    if (micWave) micWave.classList.toggle('active', listening);
    if (micIcon) micIcon.textContent = listening ? '🔴' : '🎙️';
}

function handleInputKey(e) {
    if (e.key === 'Enter') {
        sendMessage();
    }
}

function sendQuickPrompt(text) {
    const input = document.getElementById('textInput');
    if (input) input.value = text;
    sendMessage(text);
}

async function sendMessage(explicitText = null) {
    const input = document.getElementById('textInput');
    const text = explicitText !== null ? explicitText : (input ? input.value.trim() : '');
    if (!text) return;
    if (input) input.value = '';

    // 1. 添加用户气泡
    appendChatBubble('user', '冈部伦太郎 (Hououin Kyouma)', text);

    // 2. 傲娇态度微调
    updateAmadeusMood("思考与具身推演中...", "演算中");

    try {
        const resp = await fetch('/api/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({message: text})
        });

        if (!resp.ok) throw new Error("HTTP " + resp.status);
        const data = await resp.json();

        // 3. 添加红莉栖回复气泡
        const reply = data.reply || "通信正常，但红莉栖正在观测脑波回路。";
        appendChatBubble('assistant', 'AMADEUS · 牧濑红莉栖', reply);

        // 4. 更新心情与语录
        let mood = "傲娇警戒中";
        if (text.includes("大海")) mood = "蔚蓝海洋心境";
        else if (text.includes("灯笼") || text.includes("火")) mood = "赛博烈焰";
        else if (text.includes("红灯") || text.includes("警戒")) mood = "真红警戒模式";
        else if (text.includes("倒计时") || text.includes("沙漏")) mood = "精密物理计量";
        else if (text.includes("笑")) mood = "微笑 (才没有呢)";
        else if (text.includes("助手") || text.includes("蒂娜")) mood = "极度气愤";

        updateAmadeusMood(`“${reply.slice(0, 48)}...”`, mood);

        // 如果识别到模式切换，同步更新当前模式号
        if (data.mode !== undefined) {
            currentMode = data.mode;
        }

    } catch (err) {
        console.error("对话请求失败:", err);
        appendChatBubble('assistant', 'AMADEUS 错误通道', `连接具身大脑失败: ${err.message}。请确保 PC 具身主控后台已在运行。`);
    }
}

function appendChatBubble(role, sender, text) {
    const vp = document.getElementById('chatViewport');
    if (!vp) return;

    const div = document.createElement('div');
    div.className = `chat-bubble ${role}`;

    const now = new Date();
    const timeStr = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}:${String(now.getSeconds()).padStart(2,'0')}`;

    div.innerHTML = `
        <div class="bubble-sender">${sender}</div>
        <div class="bubble-body">${escapeHTML(text)}</div>
        <div class="bubble-time">${timeStr}</div>
    `;

    vp.appendChild(div);
    vp.scrollTop = vp.scrollHeight;
}

function escapeHTML(str) {
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function updateAmadeusMood(quote, tag) {
    const qEl = document.getElementById('amadeusQuote');
    const tEl = document.getElementById('emotionTag');
    if (qEl) qEl.textContent = quote;
    if (tEl) tEl.textContent = tag;
}

// ==========================================
// 6. 音量与硬件设置
// ==========================================
async function changeVolume(val) {
    const valText = document.getElementById('volValText');
    if (valText) valText.textContent = `${val}%`;

    try {
        await fetch('/api/volume', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({volume: parseInt(val)})
        });
    } catch (e) {
        console.warn("调节音量失败:", e);
    }
}

async function changeBrightness(val) {
    const bVal = document.getElementById('brightVal');
    if (bVal) bVal.textContent = val;

    try {
        await fetch('/api/cmd', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({cmd: 'bright', val: parseInt(val)})
        });
    } catch (e) {
        console.warn("调节亮度失败:", e);
    }
}

// ==========================================
// 7. 光场模式与物理沙漏控制 (MATRIX)
// ==========================================
async function setMode(modeNum) {
    currentMode = parseInt(modeNum);
    console.log(`[光场指令] 切换模式 -> ${modeNum}`);
    
    // 如果离开游戏模式，重置游戏标记
    if (currentMode !== 19 && currentMode !== 21) {
        currentGame = null;
        updateGameIndicator(null);
    }

    try {
        await fetch('/api/mode', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({mode: currentMode})
        });
    } catch (e) {
        console.warn("切换光场模式失败:", e);
    }
}

async function setCountdown(sec) {
    countdownTotal = sec;
    countdownRemaining = sec;
    currentMode = 25; // 物理沙漏模式
    console.log(`[物理沙漏] 启动倒计时 ${sec} 秒`);

    try {
        await fetch('/api/cmd', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({cmd: 'countdown', seconds: sec})
        });
        appendChatBubble('assistant', 'AMADEUS · 物理沙漏', `物理沙漏已设定: ${sec} 秒倒计时开始，256 颗灯珠呈等比线性衰减！`);
    } catch (e) {
        console.warn("倒计时启动失败:", e);
    }
}

function setCustomCountdown() {
    const input = document.getElementById('customCdSec');
    const sec = parseInt(input.value);
    if (!sec || sec <= 0) {
        alert("请输入有效的倒计时秒数 (1~3600)！");
        return;
    }
    setCountdown(sec);
}

async function stopCountdown() {
    countdownRemaining = 0;
    try {
        await fetch('/api/cmd', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({cmd: 'stop_countdown'})
        });
        setMode(11); // 恢复微笑表情
    } catch (e) {
        console.warn("停止倒计时失败:", e);
    }
}

// ==========================================
// 8. 掌上街机手柄 (ARCADE CONTROLLER)
// ==========================================
function startGame(gameName) {
    currentGame = gameName;
    updateGameIndicator(gameName);

    if (gameName === 'snake') {
        setMode(19);
        snakeState = {
            body: [{x: 8, y: 8}, {x: 8, y: 9}, {x: 8, y: 10}],
            dir: {x: 0, y: -1},
            food: {x: 4, y: 4}
        };
    } else if (gameName === 'tetris') {
        setMode(21);
    }

    switchTab('arcade');
    if (navigator.vibrate) navigator.vibrate([30, 50, 30]);
}

function updateGameIndicator(gameName) {
    const el = document.getElementById('gameIndicator');
    if (!el) return;
    if (!gameName) {
        el.textContent = "当前未运行游戏";
        el.classList.remove('running');
    } else if (gameName === 'snake') {
        el.textContent = "● 贪吃蛇运行中 (Mode 19)";
        el.classList.add('running');
    } else if (gameName === 'tetris') {
        el.textContent = "● 俄罗斯方块运行中 (Mode 21)";
        el.classList.add('running');
    }
}

async function sendGameKey(direction, event) {
    if (event) event.preventDefault();
    if (navigator.vibrate) navigator.vibrate(20);

    if (currentGame === 'snake' || currentMode === 19) {
        let dx = 0, dy = 0;
        if (direction === 'up') { dx = 0; dy = -1; }
        else if (direction === 'down') { dx = 0; dy = 1; }
        else if (direction === 'left') { dx = -1; dy = 0; }
        else if (direction === 'right') { dx = 1; dy = 0; }

        snakeState.dir = {x: dx, y: dy};

        try {
            await fetch('/api/game', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({game: 'snake', dx: dx, dy: dy})
            });
        } catch (e) {
            console.warn("发送贪吃蛇按键失败:", e);
        }
    } else if (currentGame === 'tetris' || currentMode === 21) {
        let act = direction;
        if (direction === 'up') act = 'rot';
        else if (direction === 'down') act = 'drop';

        try {
            await fetch('/api/game', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({game: 'tetris', action: act})
            });
        } catch (e) {
            console.warn("发送俄罗斯方块动作失败:", e);
        }
    } else {
        // 未启动游戏时默认切入贪吃蛇
        startGame('snake');
    }
}

async function sendGameAction(action, event) {
    if (event) event.preventDefault();
    if (navigator.vibrate) navigator.vibrate(35);

    try {
        await fetch('/api/game', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({game: 'tetris', action: action})
        });
    } catch (e) {
        console.warn("发送街机动作按键失败:", e);
    }
}

// ==========================================
// 9. 16x16 LED 光场实时拟真画布 (MATRIX CANVAS)
// ==========================================
function initMatrixCanvas() {
    const canvas = document.getElementById('matrixCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let frame = 0;

    function renderLoop() {
        frame++;
        renderMatrixFrame(ctx, frame);
        matrixAnimId = requestAnimationFrame(renderLoop);
    }
    renderLoop();
}

function renderMatrixFrame(ctx, frame) {
    const size = 16;
    const ledGap = 2;
    const ledRadius = 6;
    const step = 256 / size;

    // 清屏黑色暗底
    ctx.fillStyle = '#060a0f';
    ctx.fillRect(0, 0, 256, 256);

    for (let y = 0; y < size; y++) {
        for (let x = 0; x < size; x++) {
            const color = getLedColorForMode(currentMode, x, y, frame);

            const cx = x * step + step / 2;
            const cy = y * step + step / 2;

            // 绘制 LED 圆珠
            ctx.beginPath();
            ctx.arc(cx, cy, ledRadius, 0, Math.PI * 2);
            ctx.fillStyle = color;
            ctx.fill();

            // 绘制微微发光光晕
            if (color !== '#111720') {
                ctx.beginPath();
                ctx.arc(cx, cy, ledRadius + 2, 0, Math.PI * 2);
                ctx.fillStyle = color + '33'; // 20% alpha
                ctx.fill();
            }
        }
    }
}

function getLedColorForMode(mode, x, y, frame) {
    switch(mode) {
        case 0: // 关灯
            return '#111720';

        case 1: // 纯红警戒
            return '#ff1122';

        case 2: // 纯蓝
            return '#0088ff';

        case 3: // 纯绿
            return '#00ff66';

        case 4: // 幻彩霓虹 (Rainbow)
            const hue = (x * 12 + y * 12 + frame * 3) % 360;
            return `hsl(${hue}, 100%, 50%)`;

        case 5: // 极光呼吸 (Aurora)
            const bri = 40 + Math.sin(frame * 0.05 + x * 0.2) * 30;
            return `hsl(170, 90%, ${bri}%)`;

        case 6: // 流星 (Meteor)
            const my = (frame * 0.4 + x * 2) % 24;
            const dist = Math.abs(y - my);
            if (dist < 3) {
                const alpha = 1.0 - dist * 0.3;
                return `rgba(255, 200, 100, ${alpha})`;
            }
            return '#111720';

        case 7: // 繁星闪烁 (Stars)
            const noise = Math.sin(x * 17.1 + y * 83.3 + frame * 0.1);
            return noise > 0.6 ? '#ffffff' : (noise > 0.4 ? '#4488ff' : '#111720');

        case 10: // 中心水波 (Ripple)
            const dx = x - 7.5;
            const dy = y - 7.5;
            const r = Math.sqrt(dx * dx + dy * dy);
            const wave = Math.sin(r * 0.8 - frame * 0.15);
            return wave > 0 ? '#00bfff' : '#002244';

        case 11: // 微笑表情 (Smile)
            // 眼睛 (3,4) (12,4)
            if ((x === 4 || x === 5) && (y === 4 || y === 5)) return '#00ffcc';
            if ((x === 10 || x === 11) && (y === 4 || y === 5)) return '#00ffcc';
            // 嘴巴
            if (y === 11 && x >= 4 && x <= 11) return '#ffaa00';
            if ((y === 10) && (x === 3 || x === 12)) return '#ffaa00';
            if ((y === 9) && (x === 2 || x === 13)) return '#ffaa00';
            return '#111720';

        case 19: // 贪吃蛇 (Snake)
            // 食物
            if (x === 4 && y === 4) return '#ff0055';
            // 蛇身
            for (let seg of snakeState.body) {
                if (seg.x === x && seg.y === y) return '#00ff88';
            }
            return '#111720';

        case 21: // 俄罗斯方块 (Tetris)
            if (y >= 14) return '#ff9900';
            if (x >= 6 && x <= 9 && y >= 7 && y <= 8) return '#00ccff';
            return '#111720';

        case 23: // 赛博烈焰 (Fire)
            const fy = (15 - y);
            const flicker = Math.sin(x * 1.5 + frame * 0.3) * 2;
            if (fy < 6 + flicker) return '#ff3300';
            if (fy < 10 + flicker) return '#ff8800';
            if (fy < 13 + flicker) return '#ffee00';
            return '#111720';

        case 24: // 代码雨 (Matrix Code Rain)
            const dropY = (frame * 0.3 + (x * 7) % 16) % 18;
            if (Math.abs(y - dropY) < 1) return '#aaffcc';
            if (y < dropY && y > dropY - 4) return '#00ff44';
            return '#111720';

        case 25: // 物理沙漏 (Countdown)
            // 256 颗灯等比熄灭
            const ledIdx = y * 16 + x;
            const progress = (frame * 2) % 256;
            return ledIdx >= progress ? '#ffaa00' : '#111720';

        default:
            return '#223344';
    }
}

// ==========================================
// 10. WebSocket 实时双向流与连接状态
// ==========================================
function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    try {
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log("[WebSocket] 已成功连接具身大脑！");
            updateConnectionUI(true);
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                handleServerEvent(data);
            } catch (err) {
                console.log("[WebSocket 原始数据]:", event.data);
            }
        };

        ws.onclose = () => {
            console.warn("[WebSocket] 连接断开，3秒后重连...");
            updateConnectionUI(false);
            setTimeout(initWebSocket, 3000);
        };

        ws.onerror = () => {
            updateConnectionUI(false);
        };
    } catch (e) {
        console.warn("WebSocket 创建失败:", e);
        updateConnectionUI(false);
    }
}

function updateConnectionUI(connected) {
    const badge = document.getElementById('connBadge');
    const text = document.getElementById('connText');
    if (badge) badge.classList.toggle('offline', !connected);
    if (text) text.textContent = connected ? 'WiFi 在线' : '重连中...';
}

function handleServerEvent(event) {
    if (event.type === 'mode_changed') {
        currentMode = event.mode;
        const wBadge = document.getElementById('wakeStatusBadge');
        if (wBadge) {
            if (event.mode === 3) {
                wBadge.textContent = '🟢 常亮绿 (待唤醒)';
                wBadge.style.color = '#00ff88';
                wBadge.style.borderColor = '#00ff88';
            } else if (event.mode === 5) {
                wBadge.textContent = '⚡ 呼吸灯 (配对中...)';
                wBadge.style.color = '#00d2ff';
                wBadge.style.borderColor = '#00d2ff';
            } else {
                wBadge.textContent = '🔴 交互中 (微表情灵动)';
                wBadge.style.color = '#ffaa00';
                wBadge.style.borderColor = '#ffaa00';
            }
        }
    } else if (event.type === 'chat_reply') {
        appendChatBubble('assistant', 'AMADEUS · 牧濑红莉栖', event.text);
        const wBadge = document.getElementById('wakeStatusBadge');
        if (wBadge) {
            wBadge.textContent = '🔴 交互中 (微表情灵动)';
            wBadge.style.color = '#ffaa00';
            wBadge.style.borderColor = '#ffaa00';
            clearTimeout(window._wakeResetTimer);
            window._wakeResetTimer = setTimeout(() => {
                if (wBadge) {
                    wBadge.textContent = '🟢 常亮绿 (待唤醒)';
                    wBadge.style.color = '#00ff88';
                    wBadge.style.borderColor = '#00ff88';
                }
            }, 30000);
        }
    } else if (event.type === 'status') {
        if (event.volume !== undefined) {
            const slider = document.getElementById('volSlider');
            const txt = document.getElementById('volValText');
            if (slider) slider.value = event.volume;
            if (txt) txt.textContent = `${event.volume}%`;
        }
    }
}

// ==========================================
// 11. 系统状态探针
// ==========================================
async function fetchSystemStatus() {
    try {
        const resp = await fetch('/api/status');
        if (resp.ok) {
            const data = await resp.json();
            const ipEl = document.getElementById('sysIp');
            if (ipEl && data.host_ip) {
                ipEl.textContent = `http://${data.host_ip}:8080`;
            }
        }
    } catch (e) {
        console.warn("获取状态失败:", e);
    }
}

// ==========================================
// 12. 上电握手与配对正向反馈仪式触发
// ==========================================
async function triggerBootCeremony() {
    showNotification("⚡ 正在执行脑波同步握手与配对自检仪式...", "info");
    try {
        const resp = await fetch('/api/ceremony', { method: 'POST' });
        const data = await resp.json();
        if (data.status === 'ok') {
            showNotification("✅ 配对握手自检完成！牧濑红莉栖系统已就绪！", "success");
        }
    } catch (e) {
        showNotification("触发仪式异常: " + e.message, "error");
    }
}
