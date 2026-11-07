/* One responsive client for browser and Android; all live pixels come from frame readback. */
"use strict";
(() => {
  const $ = (id) => document.getElementById(id);
  const $$ = (selector) => [...document.querySelectorAll(selector)];
  const names = {
    overview: "概览",
    lights: "灯光",
    music: "音乐",
    interaction: "互动",
    settings: "设置",
  };
  const state = {
    page: "overview",
    online: false,
    board: false,
    simulated: false,
    mode: null,
    frame: null,
    game: null,
    libraryOffset: 0,
    libraryQuery: "",
    libraryTotal: 0,
    libraryRequest: 0,
    music: {},
    socket: null,
    ownChat: null,
  };
  const modes = [
    [0, "关闭灯光", "安静，留给夜晚", "solid", "○"],
    [1, "绯红", "一抹坚定的红", "solid", "●"],
    [2, "深蓝", "沉入一片蓝", "solid", "●"],
    [3, "青绿", "清新一点", "solid", "●"],
    [4, "彩虹漫游", "缓缓流动的色彩", "ambient", "◒"],
    [5, "极光", "把北境带到桌面", "ambient", "≋"],
    [6, "流星", "留住一瞬的光", "ambient", "↗"],
    [7, "满天繁星", "属于你的星空", "ambient", "✦"],
    [8, "色彩呼吸", "让颜色慢慢变化", "ambient", "◉"],
    [9, "雨滴", "听见落雨的节奏", "ambient", "⋮"],
    [10, "水面波纹", "一圈圈荡开", "ambient", "◎"],
    [11, "微笑", "今天也要开心", "character", "⌣"],
    [12, "难过", "也允许低落一会儿", "character", "⌢"],
    [13, "平静", "给思绪留白", "character", "—"],
    [14, "表情轮换", "每一种心情", "character", "☺"],
    [15, "16 列频谱", "看见音乐的频率", "ambient", "▥"],
    [16, "助手反馈", "对话时的光", "interactive", "◈"],
    [17, "牧濑红莉栖", "一直在你身边", "character", "✧"],
    [23, "篝火", "一点暖意", "ambient", "♨"],
    [24, "代码雨", "实验室的另一面", "ambient", "⠿"],
    [26, "指尖追踪", "光跟着手指走", "interactive", "⌖"],
    [27, "光球抓投", "捏住，然后放开", "interactive", "◌"],
    [28, "世界线", "熟悉的彩蛋数字", "interactive", "％"],
    [29, "像素画布", "把灵感画下来", "interactive", "▦"],
    [30, "音乐光环", "声音在光里绽放", "ambient", "◉"],
    [31, "环境微光", "让房间柔和一点", "ambient", "☼"],
  ];
  const modeName = (n) =>
    modes.find((m) => m[0] === n)?.[1] ||
    (n === 25 ? "专注倒计时" : n === 32 ? "街机" : "尚未读取");
  const colors = {
    5: ["#273831", "#9bc6b0"],
    7: ["#292b40", "#a5a9e2"],
    10: ["#24343e", "#87bdcf"],
    17: ["#3e2826", "#e9a18b"],
    1: ["#402626", "#ed8064"],
    2: ["#25304b", "#99afec"],
    3: ["#243b32", "#8dc9a3"],
    23: ["#422d23", "#dcb18b"],
  };
  let toastTimer,
    matrix3d,
    pollTimer,
    lastGeneral = 0,
    lastPro = 0,
    polling = false,
    lastError = "",
    lastMusicError = "",
    libraryDirty = true;
  function notice(message) {
    $("toast").textContent = message;
    $("toast").hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => ($("toast").hidden = true), 6500);
  }
  const nativeMode = location.protocol === "file:";
  const deviceHealth = new window.DeviceHealth();
  const nativeDevice = nativeMode ? window.nativeDeviceApi(window.arcadeNativeExchange(window.AmadeusNative)) : null;
  const arcadeTransport = new window.ArcadeTransport(nativeMode ? window.arcadeNativeExchange(window.AmadeusNative) :
    async (command, id, policy) => {
      const path = command.cmd === "frame" ? "/api/arcade/frame" : "/api/arcade";
      const data = command.cmd === "frame" ? undefined : {...command};
      const reply = await httpApi(path,data,data ? "POST" : "GET",3000);
      if (!reply || reply.status === "error") throw Error(reply?.error || "请求失败");
      return reply;
    });
  async function api(path, data, method = "POST", timeout = 15000) {
    if (path === "/api/arcade" || path.startsWith("/api/arcade/")) return arcadeTransport.call(path,data);
    if (nativeMode) {
      return nativeDevice(path,data,method);
    }
    return httpApi(path,data,method,timeout);
  }
  try {
    const params = new URLSearchParams(location.search);
    const pairFromQuery = (params.get("pair") || "").trim();
    if (pairFromQuery) {
      sessionStorage.setItem("kurisu_access_token", pairFromQuery);
      try { localStorage.setItem("kurisu_access_token", pairFromQuery); } catch (_) {}
      params.delete("pair");
      const cleanQuery = params.toString();
      history.replaceState(null, "", location.pathname + (cleanQuery ? "?" + cleanQuery : "") + location.hash);
    } else if (!sessionStorage.getItem("kurisu_access_token")) {
      const savedToken = localStorage.getItem("kurisu_access_token");
      if (savedToken) sessionStorage.setItem("kurisu_access_token", savedToken);
    }
  } catch (_) {}
  const pairStorage = {
    getItem: (k) => {
      try { return sessionStorage.getItem(k) || localStorage.getItem(k); } catch (_) { return sessionStorage.getItem(k); }
    },
    setItem: (k, v) => {
      sessionStorage.setItem(k, v);
      try { localStorage.setItem(k, v); } catch (_) {}
    }
  };
  function getAccessToken() {
    try {
      return (
        (typeof pairStorage !== "undefined" && pairStorage.getItem("kurisu_access_token")) ||
        localStorage.getItem("kurisu_access_token") ||
        sessionStorage.getItem("kurisu_access_token") ||
        state.token ||
        ""
      );
    } catch (_) {
      return state.token || "";
    }
  }
  function promptPairingToken() {
    const dialog = $("pairDialog"), form = $("pairForm"), input = $("pairTokenInput");
    if (!dialog || typeof dialog.showModal !== "function" || !form || !input) {
      return window.prompt("请输入电脑服务的配对令牌（见电脑端 web-access-token 文件）");
    }
    return new Promise((resolve) => {
      const finish = (val) => {
        form.onsubmit = null;
        if ($("closePairDialog")) $("closePairDialog").onclick = null;
        if ($("cancelPairBtn")) $("cancelPairBtn").onclick = null;
        dialog.oncancel = null;
        if (dialog.open) dialog.close();
        resolve(val);
      };
      input.value = pairStorage.getItem("kurisu_access_token") || "";
      form.onsubmit = (e) => { e.preventDefault(); finish(input.value.trim()); };
      if ($("closePairDialog")) $("closePairDialog").onclick = () => finish("");
      if ($("cancelPairBtn")) $("cancelPairBtn").onclick = () => finish("");
      dialog.oncancel = () => finish("");
      dialog.showModal();
      setTimeout(() => input.focus(), 30);
    });
  }
  const pairedHttp = window.createPairedHttp({
    fetch: (...args) => fetch(...args), storage: pairStorage,
    prompt: promptPairingToken
  });
  const httpApi = (path,data,method="POST",timeout=15000) =>
    pairedHttp(path,{method,body:data===undefined?undefined:JSON.stringify(data),
      headers:data===undefined?{}:{"Content-Type":"application/json"}},timeout);
  function bind(id, fn) {
    $(id).addEventListener("click", async (e) => {
      const b = e.currentTarget;
      if (b.disabled || b.dataset.busy) return;
      b.dataset.busy = "1";
      b.disabled = true;
      try {
        await fn(e);
      } catch (error) {
        notice(error.message);
      } finally {
        delete b.dataset.busy;
        b.disabled = b.hasAttribute("data-hardware") && !state.board;
      }
    });
  }
  function markHardware() {
    $$("[data-hardware]").forEach((b) => {
      b.disabled = !state.board || b.dataset.busy === "1";
    });
  }
  function navigate(page, anchor) {
    if (!names[page]) page = "overview";
    if (state.arcadeActive && page !== "interaction") releaseArcadeControls();
    state.page = page;
    $$(".page").forEach((p) => {
      p.hidden = p.id !== "page-" + page;
      p.classList.toggle("active", !p.hidden);
    });
    $$("[data-page]").forEach((b) => {
      b.classList.toggle("active", b.dataset.page === page);
      if (b.dataset.page === page) b.setAttribute("aria-current", "page");
      else b.removeAttribute("aria-current");
    });
    $("pageTitle").textContent = names[page];
    document.title = `${names[page]} · Amadeus 光影实验室`;
    if (location.hash !== "#" + page)
      history.replaceState(null, "", "#" + page);
    window.scrollTo({ top: 0, behavior: "instant" });
    if (anchor) $(anchor)?.scrollIntoView({ block: "start" });
    if (page === "music" && state.online && libraryDirty)
      loadLibrary().catch((e) => notice(e.message));
    if (page === "lights" && state.frame) renderFrame(state.frame);
  }
  function route() {
    const hash = location.hash.slice(1);
    const aliases = {
      musicLibrary: "music",
      comm: "overview",
      matrix: "lights",
      arcade: "interaction",
      system: "settings",
      mario: "interaction",
      marioContainer: "interaction",
    };
    navigate(aliases[hash] || hash);
    if (hash === "mario" || hash === "marioContainer") {
      setTimeout(() => launchArcadeGame(1), 80);
    }
  }
  $$("[data-page]").forEach(
    (b) => (b.onclick = () => navigate(b.dataset.page)),
  );
  $$("[data-go]").forEach(
    (b) => (b.onclick = () => navigate(b.dataset.go, b.dataset.anchor)),
  );
  window.addEventListener("hashchange", route);
  $("todayLabel").textContent = new Intl.DateTimeFormat("zh-CN", {
    month: "long",
    day: "numeric",
    weekday: "long",
  }).format(new Date());
  function connection(s) {
    s=deviceHealth.observe(s);
    state.online = !!s;
    state.simulated = !!s?.simulated;
    state.board = !!s?.is_connected;
    const text = !s
      ? (nativeMode ? "灯板未连接" : "电脑服务未连接")
      : s.simulated
        ? "演示模式"
        : s.is_connected
          ? (s.control_retrying ? "正在重连设备" : "设备已连接")
          : "服务在线 · 灯板离线";
    $("connectionText").textContent = text;
    $$("[data-connection]").forEach((e) => (e.textContent = text));
    document.body.classList.toggle("connected", state.board);
    $("connectionPill").classList.toggle(
      "offline",
      !state.board || state.simulated,
    );
    $("offlineBanner").hidden = state.board && !state.simulated;
    $("offlineText").textContent = state.simulated
      ? "当前处于演示模式。"
      : state.online
        ? "电脑服务在线，灯板尚未连接。请检查灯板电源与 Wi-Fi。"
        : (nativeMode ? "正在搜寻并连接灯板或电脑服务…" : "电脑服务未连接，请在连接设置中检查地址和网络。");
    $("serverStatus").textContent = state.online ? "服务在线" : "离线";
    $("serverAddress").textContent =
      nativeMode
        ? "手机直连灯板"
        : (s?.lan_url || location.origin);
    $("boardConnection").textContent = s?.simulated
      ? "演示模式"
      : s?.is_connected
        ? "Wi-Fi 已连接"
        : "未连接";
    const wakeReady = Boolean(s?.wake_detector_ready && s?.listener_healthy !== false);
    $("wakeState").textContent = wakeReady
      ? "唤醒检测器就绪"
      : (s?.listener_listening === false && s?.model_ready)
        ? "监听异常 / 未就绪"
        : "未就绪";
    $("audioTransport").textContent = s?.audio_transport
      ? s.audio_transport === "wifi"
        ? "Wi-Fi PCM"
        : s.audio_transport
      : "由电脑服务配置";
    $("voiceState").textContent = s?.simulated
      ? "可直接输入文字体验对话"
      : wakeReady
        ? "对板载麦克风说“助手”即可开始"
        : "可发送文字；板载语音状态见设置";
    if(nativeMode)$("voiceState").textContent="灯光和街机可直连；AI对话需连接电脑服务";
    $("sendChat").disabled = nativeMode || !state.online || !!state.ownChat;
    markHardware();
    if (!state.board) {
      for (const id of ["previousMusic", "pauseResumeMusic", "nextMusic", "stopMusic"])
        if ($(id)) $(id).disabled = true;
      $$(".play-track").forEach((b) => (b.disabled = true));
    }
    if (!state.board) {
      $("homeFrameEmpty").hidden = $("lightFrameEmpty").hidden = false;
      $("homeFrameEmpty").textContent = $("lightFrameEmpty").textContent =
        "灯板未连接 · 预览暂停";
      $("frameTag").textContent = "预览暂停";
    }
    if (s) {
      const c = s.wifi?.last_command || {};
      const brightness = c.brightness ?? c.state?.brightness;
      syncRange("brightness", brightness, " / 60");
      syncRange("volume", s.volume ?? c.volume, "%");
      syncRange("musicVolume", s.volume ?? c.volume, "%");
    }
  }
  function syncRange(id, value, suffix = "") {
    if (!Number.isFinite(Number(value)) || value == null) return;
    const el = $(id);
    if (el && document.activeElement !== el && el.dataset.busy !== "1") {
      el.value = String(value);
      const valEl = $(id + "Value");
      if (valEl) valEl.textContent = value + suffix;
    }
  }
  function matrix2d(canvas, hex) {
    const c = canvas.getContext("2d"),
      size = canvas.width / 16;
    c.clearRect(0, 0, canvas.width, canvas.height);
    c.fillStyle = "#101217";
    c.fillRect(0, 0, canvas.width, canvas.height);
    for (let i = 0; i < 256; i++) {
      const rgb = [0, 1, 2].map((k) =>
        parseInt(hex?.slice(i * 6 + k * 2, i * 6 + k * 2 + 2) || "00", 16),
      );
      const view = rgb.map((v) =>
        v === 0
          ? 0
          : Math.round(255 * Math.pow(Math.min(1, (v * 3) / 255), 1 / 2.2)),
      );
      const x = (i % 16) * size + size / 2,
        y = Math.floor(i / 16) * size + size / 2;
      c.fillStyle = rgb.some((v) => v > 0)
        ? `rgb(${view.join(",")})`
        : "#22262e";
      c.shadowColor = c.fillStyle;
      c.shadowBlur = rgb.some((v) => v > 0) ? size * 0.45 : 0;
      c.beginPath();
      c.arc(x, y, size * 0.24, 0, Math.PI * 2);
      c.fill();
    }
    c.shadowBlur = 0;
  }
  function renderFrame(f) {
    if (!/^[0-9a-f]{1536}$/i.test(f.pixels || "")) return;
    state.frame = f;
    state.mode = f.mode;
    matrix2d($("homeMatrix"), f.pixels);
    if (state.page === "lights") {
      matrix2d($("matrixCanvas"), f.pixels);
      if (matrix3d && !$("view").hidden) matrix3d.update(f.pixels);
    }
    const source = state.simulated
      ? "演示画面"
      : "实时画面";
    $("frameTag").textContent = state.simulated ? "演示画面" : "实时同步";
    $("homeFrameEmpty").hidden = $("lightFrameEmpty").hidden = true;
    $("frameSource").textContent = `${source} · 帧 ${f.frame_id ?? "—"}`;
    $("modeName").textContent = $("currentModeLabel").textContent = modeName(
      f.mode,
    );
    $$("[data-mode]").forEach((b) => {
      b.classList.toggle("active", Number(b.dataset.mode) === f.mode);
      b.setAttribute("aria-pressed", String(Number(b.dataset.mode) === f.mode));
    });
    state.game=state.arcadeActive ? "arcade" : null;
    $("gameState").textContent=state.arcadeActive ? ARCADE_TITLE_MAP[state.arcadeGid] || "街机" : "选择游戏开始";
    $$("[data-game]").forEach((b) =>
      b.classList.toggle("active", state.arcadeActive ? Number(b.dataset.arcadeId)===state.arcadeGid : b.dataset.game === state.game),
    );
    if ($("marioContainer")) {
      $("marioContainer").style.display = state.arcadeActive ? "flex" : "none";
    }
    if (f.brightness != null) syncRange("brightness", f.brightness, " / 60");
    $("countdownState").textContent =
      f.mode === 25 ? "计时画面显示中" : "尚未开始 / 已结束";
  }
  async function setMode(mode) {
    if([19,20,21,22].includes(mode))return launchArcadeGame(mode<21?33:41);
    if (state.arcadeActive) {
      await api("/api/arcade", {action:"exit"});
      state.arcadeActive=false;state.game=null;
      clearInterval(arcadeHeartbeatTimer);
      if ($("marioContainer")) $("marioContainer").style.display="none";
    }
    await api("/api/mode", { mode });
    notice(`已切换至：${modeName(mode)}`);
    lastPro = 0;
  }
  function modeClick(e) {
    const b = e.currentTarget;
    if (b.disabled || b.dataset.busy) return;
    b.dataset.busy = "1";
    b.disabled = true;
    setMode(Number(b.dataset.mode))
      .catch((e) => notice(e.message))
      .finally(() => {
        delete b.dataset.busy;
        markHardware();
      });
  }
  function renderEffects() {
    const category = $("effectCategory").value;
    $("effectGrid").replaceChildren();
    for (const m of modes.filter(
      (m) => category === "all" || m[3] === category,
    )) {
      const b = document.createElement("button");
      b.className = "effect-card";
      b.dataset.mode = m[0];
      b.setAttribute("data-hardware", "");
      const [bg, fg] = colors[m[0]] || ["#302b33", "#c8a3b4"];
      b.style.setProperty("--scene-bg", bg);
      b.style.setProperty("--scene-color", fg);
      const icon = document.createElement("span");
      icon.className = "effect-icon";
      icon.textContent = m[4];
      const title = document.createElement("strong");
      title.textContent = m[1];
      const sub = document.createElement("small");
      sub.textContent = m[2];
      b.append(icon, title, sub);
      b.addEventListener("click", modeClick);
      b.classList.toggle("active", state.mode === m[0]);
      $("effectGrid").append(b);
    }
    markHardware();
  }
  for (const n of [7, 5, 10, 17]) {
    const m = modes.find((m) => m[0] === n),
      b = document.createElement("button");
    b.className = "scene-card";
    b.dataset.mode = n;
    b.setAttribute("data-hardware", "");
    const [bg, fg] = colors[n];
    b.style.setProperty("--scene-bg", bg);
    b.style.setProperty("--scene-color", fg);
    const icon = document.createElement("span");
    icon.className = "scene-icon";
    icon.textContent = m[4];
    const copy = document.createElement("span"),
      title = document.createElement("strong"),
      sub = document.createElement("small"),
      arrow = document.createElement("span");
    title.textContent = m[1];
    sub.textContent = m[2];
    arrow.className = "scene-arrow";
    arrow.textContent = "↗";
    copy.append(title, sub);
    b.append(icon, copy, arrow);
    $("quickScenes").append(b);
  }
  $$("[data-mode]").forEach((b) => b.addEventListener("click", modeClick));
  $("effectCategory").onchange = renderEffects;
  renderEffects();
  let volumeDebounce = null;
  function handleVolumeInput(val) {
    const num = Number(val);
    if (!Number.isFinite(num)) return;
    const vEl = $("volume");
    if (vEl) vEl.value = String(num);
    const vvEl = $("volumeValue");
    if (vvEl) vvEl.textContent = num + "%";
    const mvEl = $("musicVolume");
    if (mvEl) mvEl.value = String(num);
    const mvvEl = $("musicVolumeValue");
    if (mvvEl) mvvEl.textContent = num + "%";

    clearTimeout(volumeDebounce);
    volumeDebounce = setTimeout(async () => {
      try {
        await api("/api/volume", { volume: num });
      } catch (_) {}
    }, 70);
  }

  async function handleVolumeCommit(val) {
    const num = Number(val);
    if (!Number.isFinite(num)) return;
    clearTimeout(volumeDebounce);
    try {
      await api("/api/volume", { volume: num });
      notice("扬声器音量已确认 (" + num + "%)");
    } catch (error) {
      notice(error.message);
    } finally {
      lastGeneral = 0;
    }
  }

  $("brightness").oninput = () =>
    ($("brightnessValue").textContent = $("brightness").value + " / 60");
  $("brightness").onchange = async () => {
    const e = $("brightness");
    e.dataset.busy = "1";
    try {
      await api("/api/cmd", { cmd: "brightness", val: Number(e.value) });
      notice("灯光亮度已确认");
    } catch (error) {
      notice(error.message);
    } finally {
      delete e.dataset.busy;
      lastGeneral = 0;
    }
  };

  for (const volId of ["volume", "musicVolume"]) {
    const el = $(volId);
    if (el) {
      el.oninput = (e) => handleVolumeInput(e.target.value);
      el.onchange = (e) => handleVolumeCommit(e.target.value);
    }
  }
  async function timer(seconds) {
    if (!Number.isInteger(seconds) || seconds < 1 || seconds > 86400)
      throw Error("计时范围为 1–86400 秒");
    await api("/api/cmd", { cmd: "countdown", seconds });
    notice("倒计时已确认");
  }
  $$("[data-timer]").forEach(
    (b) =>
      (b.onclick = () =>
        timer(Number(b.dataset.timer)).catch((e) => notice(e.message))),
  );
  $("timerForm").onsubmit = (e) => {
    e.preventDefault();
    if (state.board)
      timer(Number($("seconds").value)).catch((e) => notice(e.message));
  };
  bind("stopTimer", async () => {
    await api("/api/cmd", { cmd: "stop_countdown" });
    notice("已停止倒计时");
  });
  $$("[data-preview]").forEach(
    (b) =>
      (b.onclick = () => {
        try {
          const three = b.dataset.preview === "3d";
          if (three && !matrix3d) matrix3d = new Matrix3D($("view"));
          $("view").hidden = !three;
          $("matrixCanvas").hidden = three;
          $("exposureControl").hidden = !three;
          $$("[data-preview]").forEach((x) => {
            x.classList.toggle("active", x === b);
            x.setAttribute("aria-pressed", String(x === b));
          });
          if (state.frame) renderFrame(state.frame);
        } catch (e) {
          notice(e.message);
        }
      }),
  );
  $("previewExposure").oninput = () => {
    if (matrix3d) {
      matrix3d.exposure = Number($("previewExposure").value);
      matrix3d.draw();
    }
  };
  function addMessage(role, text) {
    const d = document.createElement("div");
    d.className = "chat-message " + role;
    const name = document.createElement("span"),
      p = document.createElement("p");
    name.textContent = role === "user" ? "你" : "红莉栖";
    p.textContent = text;
    d.append(name, p);
    $("chatLog").append(d);
    while ($("chatLog").children.length > 80)
      $("chatLog").firstElementChild.remove();
    $("chatLog").scrollTop = $("chatLog").scrollHeight;
  }
  $("startConversation").onclick = () => {
    $("conversationCard").scrollIntoView({
      behavior: "smooth",
      block: "center",
    });
    $("chatInput").focus({ preventScroll: true });
  };
  $$("[data-prompt]").forEach(
    (b) =>
      (b.onclick = () => {
        $("chatInput").value = b.dataset.prompt;
        $("chatInput").focus();
      }),
  );
  $("chatForm").onsubmit = async (e) => {
    e.preventDefault();
    const message = $("chatInput").value.trim();
    if (!message || state.ownChat || !state.online) return;
    state.ownChat = message;
    $("sendChat").disabled = true;
    $("chatInput").value = "";
    addMessage("user", message);
    $("chatStatus").textContent = "正在处理，请稍候…";
    try {
      const r = await api("/api/chat", { message }, "POST", 120000);
      addMessage("assistant", r.reply || "暂时没有收到回复");
      if (r.model_error) {
        $("chatStatus").textContent = "模型状态：" + r.model_error;
      } else if (r.translation_error) {
        $("chatStatus").textContent = "翻译状态：" + r.translation_error;
      } else if (r.tts_error) {
        $("chatStatus").textContent = "语音合成状态：" + r.tts_error;
      } else {
        $("chatStatus").textContent = "回复已收到";
      }
    } catch (error) {
      $("chatStatus").textContent = error.message;
      notice(error.message);
    } finally {
      state.ownChat = null;
      $("sendChat").disabled = !state.online;
      lastPro = 0;
    }
  };
  // Optional browser dictation remains separate from the validated board microphone.
  const Speech = window.SpeechRecognition || window.webkitSpeechRecognition;
  let dictation;
  if (
    Speech &&
    window.isSecureContext &&
    !navigator.userAgent.includes("AmadeusAndroid")
  ) {
    $("browserMic").hidden = false;
    $("browserMic").onclick = () => {
      if (dictation) {
        dictation.stop();
        return;
      }
      dictation = new Speech();
      dictation.lang = "zh-CN";
      dictation.interimResults = false;
      dictation.onresult = (e) => {
        $("chatInput").value = e.results[0][0].transcript;
        $("chatStatus").textContent = "语音已填入，点击发送才会执行。";
      };
      dictation.onerror = (e) => {
        $("chatStatus").textContent = "浏览器语音输入不可用：" + e.error;
      };
      dictation.onend = () => {
        dictation = null;
        $("browserMic").setAttribute("aria-pressed", "false");
      };
      try {
        dictation.start();
        $("browserMic").setAttribute("aria-pressed", "true");
        $("chatStatus").textContent =
          "浏览器语音输入中；识别服务由浏览器提供。";
      } catch (error) {
        dictation = null;
        notice(error.message);
      }
    };
  }
  function openSocket() {
    if (location.protocol === "file:" || state.socket) return;
    const ws = new WebSocket(
      (location.protocol === "https:" ? "wss:" : "ws:") +
        "//" +
        location.host +
        "/ws",
    );
    state.socket = ws;
    ws.onmessage = (e) => {
      try {
        const v = JSON.parse(e.data);
        if (v.type === "chat_reply" && v.user !== state.ownChat) {
          if (v.user) addMessage("user", v.user);
          addMessage("assistant", v.text || "");
        }
        if (["mode_changed", "countdown_started"].includes(v.type)) lastPro = 0;
      } catch (_) {
        /* Ignore malformed telemetry. */
      }
    };
    ws.onerror = () => ws.close();
    ws.onclose = () => {
      if (state.socket === ws) state.socket = null;
    };
  }
  const time = (s) =>
    `${String(Math.floor(Math.max(0, s || 0) / 60)).padStart(2, "0")}:${String(Math.floor(Math.max(0, s || 0) % 60)).padStart(2, "0")}`;
  function updateMusic(m = {}) {
    state.music = m;
    $$(".track-row").forEach((row) => {
      row.classList.toggle("active", row.dataset.track === m.current?.id);
      row.querySelector("button").disabled = !state.board;
    });
    const current = m.current;
    $("nowPlaying").textContent =
      current?.title || (m.running ? "临时音源" : "选一首喜欢的歌");
    $("nowArtist").textContent = current
      ? current.artist || current.filename || "本地曲库"
      : "由板载扬声器播放，灯光随音乐律动";
    $("playerState").textContent = m.running
      ? state.simulated
        ? "SIMULATED PLAYBACK"
        : "NOW PLAYING"
      : m.paused
        ? "PAUSED"
        : current
          ? "PLAYBACK STOPPED"
          : "READY WHEN YOU ARE";
    document
      .querySelector(".music-player")
      .classList.toggle("playing", !!m.running);
    $("musicProgress").max = Math.max(1, m.duration || 0);
    if (!state.seekingMusic) {
      $("musicProgress").value = m.position || 0;
      $("musicTime").textContent = time(m.position) + " / " + time(m.duration);
    }
    for (const [id, value] of [
      ["musicOrder", m.order],
      ["musicRepeat", m.repeat],
    ])
      if (value && document.activeElement !== $(id)) $(id).value = value;
    if (m.gain && $("musicBoost") && document.activeElement !== $("musicBoost")) {
      const match = Array.from($("musicBoost").options).find((o) => Math.abs(Number(o.value) - Number(m.gain)) < 0.01);
      if (match) $("musicBoost").value = match.value;
    }
    $("previousMusic").disabled = $("nextMusic").disabled =
      !state.board || !m.queue_count;
    if ($("pauseResumeMusic")) {
      $("pauseResumeMusic").disabled = !state.board || (!m.running && !m.paused && !m.current);
      const icon = $("pauseResumeIcon");
      if (icon) icon.setAttribute("href", m.running ? "#i-pause" : "#i-play");
      $("pauseResumeMusic").setAttribute("aria-label", m.running ? "暂停音乐" : "继续播放");
    }
    $("stopMusic").disabled = !state.board || (!m.running && !m.paused);
    $("musicVoiceHint").textContent = m.running
      ? m.voice_wake
        ? "播放中先说“助手”，音乐停止后可说“下一首”或继续点歌。"
        : "播放中可通过网页切歌；当前没有启用音乐唤醒监听。"
      : "对板子说“助手”，再说“播放＋歌名”“播放某位歌手的歌”或“单曲循环”。";
    const l = m.library || {};
    $("libraryCount").textContent = l.count ?? "—";
    $("librarySettingsCount").textContent = l.root
      ? `${l.count || 0} 首`
      : "未配置";
    const message =
      l.error ||
      (l.scanning
        ? "正在扫描曲库…"
        : l.root
          ? `共 ${l.count || 0} 首 · 音乐原文件保持原位`
          : "尚未配置曲库，请到设置中添加电脑上的音乐文件夹");
    $("libraryState").textContent = $("librarySettingsState").textContent =
      message;
    if (document.activeElement !== $("libraryRoot") && l.root)
      $("libraryRoot").value = l.root;
    if (m.error && m.error !== lastMusicError) notice(m.error);
    lastMusicError = m.error || "";
  }
  async function loadLibrary() {
    const serial = ++state.libraryRequest,
      query = state.libraryQuery,
      offset = state.libraryOffset;
    $("libraryPageState").textContent = "正在读取…";
    const r = await api(
      "/api/pro/library?" +
        new URLSearchParams({ q: query, offset: String(offset), limit: "30" }),
      undefined,
      "GET",
    );
    if (serial !== state.libraryRequest) return;
    state.libraryTotal = r.total;
    libraryDirty = !!r.scanning;
    $("libraryTracks").replaceChildren();
    for (const [index, t] of r.items.entries()) {
      const row = document.createElement("div");
      row.className = "track-row";
      row.dataset.track = t.id;
      row.classList.toggle("active", state.music.current?.id === t.id);
      const number = document.createElement("span");
      number.className = "track-index";
      number.textContent = String(offset + index + 1).padStart(2, "0");
      const meta = document.createElement("div");
      meta.className = "track-meta";
      const title = document.createElement("strong"),
        artist = document.createElement("small");
      title.textContent = t.title;
      artist.textContent = t.artist || t.filename || "本地音乐";
      meta.append(title, artist);
      const b = document.createElement("button");
      b.className = "play-track";
      b.setAttribute(
        "aria-label",
        "播放 " + (t.artist ? t.artist + " — " : "") + t.title,
      );
      b.innerHTML = '<svg><use href="#i-play"/></svg>';
      b.disabled = !state.board;
      b.onclick = async () => {
        b.disabled = true;
        try {
          await api("/api/pro/music", {
            track_id: t.id,
            visual: $("musicVisual").value,
            scope: query,
          });
          notice(state.simulated ? "模拟点播已提交" : "已开始播放：" + t.title);
          lastPro = 0;
        } catch (e) {
          notice(e.message);
        } finally {
          b.disabled = !state.board;
        }
      };
      row.append(number, meta, b);
      $("libraryTracks").append(row);
    }
    if (!r.items.length) {
      const empty = document.createElement("p");
      empty.className = "empty-state";
      empty.textContent = r.scanning
        ? "曲库正在扫描，请稍候刷新"
        : r.error ||
          (!r.root
            ? "先到设置添加你的电脑音乐文件夹"
            : "没有找到匹配的歌曲，试试歌名或歌手的一部分");
      $("libraryTracks").append(empty);
    }
    $("libraryCount").textContent = r.count ?? 0;
    $("libraryPageState").textContent =
      `匹配 ${r.total} 首${r.total ? " · " + (offset + 1) + "–" + (offset + r.items.length) : ""}`;
    $("libraryPreviousPage").disabled = offset === 0;
    $("libraryNextPage").disabled = offset + 30 >= r.total;
    if (document.activeElement !== $("libraryRoot"))
      $("libraryRoot").value = r.root || "";
  }
  $("librarySearchForm").onsubmit = (e) => {
    e.preventDefault();
    state.libraryQuery = $("libraryQuery").value.trim();
    state.libraryOffset = 0;
    loadLibrary().catch((e) => notice(e.message));
  };
  bind("clearLibrarySearch", () => {
    state.libraryQuery = "";
    state.libraryOffset = 0;
    $("libraryQuery").value = "";
    return loadLibrary();
  });
  bind("libraryPreviousPage", () => {
    state.libraryOffset = Math.max(0, state.libraryOffset - 30);
    return loadLibrary();
  });
  bind("libraryNextPage", () => {
    state.libraryOffset += 30;
    return loadLibrary();
  });
  async function scanLibrary(configure = false) {
    const r = await api(
      "/api/pro/library",
      configure
        ? { action: "configure", root: $("libraryRoot").value.trim() }
        : { action: "scan" },
      "POST",
      60000,
    );
    if (r.error) throw Error(r.error);
    state.libraryOffset = 0;
    await loadLibrary();
    notice(`曲库已更新，共 ${r.count || 0} 首`);
    lastPro = 0;
  }
  bind("configureLibrary", () => scanLibrary(true));
  bind("rescanLibrary", () => scanLibrary());
  bind("rescanLibrarySettings", () => scanLibrary());
  for (const [id, action] of [
    ["previousMusic", "previous"],
    ["nextMusic", "next"],
    ["stopMusic", "stop"],
  ])
    bind(id, async () => {
      await api("/api/pro/music", { action });
      lastPro = 0;
    });
  if ($("pauseResumeMusic")) {
    bind("pauseResumeMusic", async () => {
      const action = state.music.running ? "pause" : "resume";
      await api("/api/pro/music", { action });
      notice(action === "pause" ? "音乐已暂停" : "已恢复播放");
      lastPro = 0;
    });
  }
  const progEl = $("musicProgress");
  if (progEl) {
    const calcSeekSeconds = (e) => {
      const dur = Number(state.music?.duration || 0);
      if (!dur || dur <= 0) return null;
      const rect = progEl.getBoundingClientRect();
      if (!rect.width) return null;
      const clientX = e.touches?.[0]?.clientX ?? e.changedTouches?.[0]?.clientX ?? e.clientX;
      const ratio = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
      return Math.round(ratio * dur * 10) / 10;
    };
    progEl.addEventListener("pointerdown", (e) => {
      if (!state.board || !(state.music?.duration > 0)) return;
      state.seekingMusic = true;
      try { progEl.setPointerCapture(e.pointerId); } catch (_) {}
      const sec = calcSeekSeconds(e);
      if (sec !== null) {
        progEl.value = sec;
        $("musicTime").textContent = time(sec) + " / " + time(state.music.duration);
      }
    });
    progEl.addEventListener("pointermove", (e) => {
      if (!state.seekingMusic) return;
      const sec = calcSeekSeconds(e);
      if (sec !== null) {
        progEl.value = sec;
        $("musicTime").textContent = time(sec) + " / " + time(state.music.duration);
      }
    });
    const finishSeek = async (e) => {
      if (!state.seekingMusic) return;
      state.seekingMusic = false;
      const sec = calcSeekSeconds(e);
      if (sec === null) return;
      try {
        await api("/api/pro/music", { action: "seek", position: sec });
        notice("已跳转至 " + time(sec));
        lastPro = 0;
      } catch (err) {
        notice(err.message);
      }
    };
    progEl.addEventListener("pointerup", finishSeek);
    progEl.addEventListener("pointercancel", () => { state.seekingMusic = false; });
  }
  for (const id of ["musicOrder", "musicRepeat"])
    $(id).onchange = () =>
      api("/api/pro/music", {
        action: "options",
        order: $("musicOrder").value,
        repeat: $("musicRepeat").value,
      }).catch((e) => notice(e.message));
  if ($("musicBoost")) {
    $("musicBoost").onchange = () => {
      const val = Number($("musicBoost").value);
      api("/api/pro/music", { action: "gain", gain: val })
        .then(() => notice("已切换响度档位: " + val + "x"))
        .catch((e) => notice(e.message));
    };
  }
  $("musicVisual").onchange = async () => {
    try {
      if (state.music.running)
        await api("/api/mode", {
          mode: $("musicVisual").value === "fluid" ? 30 : 15,
        });
    } catch (e) {
      notice(e.message);
    }
  };
  bind("playUrl", async () => {
    const url = new URL($("musicUrl").value);
    if (!["http:", "https:"].includes(url.protocol))
      throw Error("请输入 HTTP(S) 音频直链");
    await api("/api/pro/music", {
      url: url.href,
      visual: $("musicVisual").value,
    });
    notice("音源已提交");
    lastPro = 0;
  });
  $("musicFile").onchange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    try {
      if (!state.board) throw Error("请先连接灯板");
      if (file.size > 20 * 1024 * 1024) throw Error("临时上传不能超过 20 MiB");
      await pairedHttp("/api/pro/music-upload?visual="+
        encodeURIComponent($("musicVisual").value),{method:"POST",body:file});
      notice(state.simulated ? "模拟音源已提交" : "音乐已开始");
      lastPro = 0;
    } catch (error) {
      notice(error.message);
    } finally {
      e.target.value = "";
    }
  };
  function drawMarioFrame(canvas, hex) {
    if (!canvas || !hex || hex.length < 1536) return;
    const ctx = canvas.getContext("2d");
    const sz = canvas.width / 16;
    ctx.fillStyle = "#0c1017";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    for (let i = 0; i < 256; i++) {
      const r = parseInt(hex.slice(i * 6, i * 6 + 2), 16) || 0;
      const g = parseInt(hex.slice(i * 6 + 2, i * 6 + 4), 16) || 0;
      const b = parseInt(hex.slice(i * 6 + 4, i * 6 + 6), 16) || 0;
      const x = (i % 16) * sz;
      const y = Math.floor(i / 16) * sz;
      if (r === 0 && g === 0 && b === 0) {
        ctx.fillStyle = "#121822";
        ctx.fillRect(x + 1, y + 1, sz - 2, sz - 2);
      } else {
        ctx.fillStyle = `rgb(${r},${g},${b})`;
        ctx.fillRect(x + 1, y + 1, sz - 2, sz - 2);
      }
    }
  }

  // =========================================================================
  // 统一 100 款点阵街机游戏核心控制器 (ESP32 唯一权威来源，全链路响应式联动)
  // =========================================================================
  const ARCADE_CATALOG_100 = [
    [1, "A", "超级马里奥", "Super Mario Bros."],
    [2, "A", "涂鸦跳跃", "Doodle Jump"],
    [3, "A", "空中冲刺", "Celeste Dash"],
    [4, "A", "重力翻转", "VVVVVV Flip"],
    [5, "A", "挖洞夺金", "Lode Runner"],
    [6, "A", "泡泡捕敌", "Bubble Bobble"],
    [7, "A", "深井射击", "Downwell"],
    [8, "A", "蓄力跳跃", "Jump King"],
    [9, "B", "飞翔小鸟", "Flappy Bird 16"],
    [10, "B", "堆叠大师", "Stack Master"],
    [11, "B", "恐龙跑酷", "Dino Runner"],
    [12, "B", "旋盘投刀", "Knife Hit"],
    [13, "B", "摆锤投球", "Pendulum Drop"],
    [14, "B", "轨道跃迁", "Orbit Hop"],
    [15, "C", "闪灯记忆", "Simon Says"],
    [16, "C", "打地鼠", "Whack-A-Mole"],
    [17, "C", "四轨节奏", "Rhythm Lanes"],
    [18, "C", "红灯绿灯", "Red Light Green"],
    [19, "C", "猜球杯", "Shell Shuffle"],
    [20, "D", "双人乒乓", "Pong 1972"],
    [21, "D", "经典打砖块", "Breakout 1976"],
    [22, "D", "迷你弹珠台", "Mini Pinball"],
    [23, "D", "空气曲棍球", "Air Hockey"],
    [24, "D", "弹珠撞靶", "Peggle Bounce"],
    [25, "D", "滚珠平衡迷宫", "Tilt Labyrinth"],
    [26, "E", "太空侵略者", "Space Invaders 1978"],
    [27, "E", "小行星", "Asteroids"],
    [28, "E", "导弹指挥官", "Missile Command"],
    [29, "E", "百足蜈蚣", "Centipede"],
    [30, "E", "打鸭子", "Duck Hunt"],
    [31, "E", "双向射击", "Robotron 2084"],
    [32, "E", "横向防卫", "Defender"],
    [33, "F", "经典贪吃蛇", "Classic Snake"],
    [34, "F", "吃豆人", "Pac-Man 1980"],
    [35, "F", "落石夺宝", "Boulder Dash"],
    [36, "F", "地下充气战", "Dig Dug"],
    [37, "F", "染色跳格", "Q*bert"],
    [38, "F", "炸弹人", "Bomberman 1983"],
    [39, "F", "迷雾探索迷宫", "Fog Maze"],
    [40, "F", "镜像双人迷宫", "Mirror Twins"],
    [41, "G", "俄罗斯方块", "Tetris"],
    [42, "G", "彩球连锁", "Puyo Puyo"],
    [43, "G", "2048滑块", "Neon 2048"],
    [44, "G", "宝石迷阵", "Bejeweled"],
    [45, "G", "同色消块", "SameGame"],
    [46, "G", "合成大西瓜", "Suika Merge"],
    [47, "G", "九宫拼块", "Blockudoku"],
    [48, "G", "三合镇", "Triple Town"],
    [49, "H", "灭灯谜题", "Lights Out"],
    [50, "H", "四色迷你数独", "Color Sudoku"],
    [51, "H", "同色连线", "Flow Free"],
    [52, "H", "管道旋转接水", "Pipe Connect"],
    [53, "H", "汉诺塔", "Tower of Hanoi"],
    [54, "I", "推箱子", "Sokoban 1982"],
    [55, "I", "镜面激光", "Mirror Laser"],
    [56, "I", "数字华容道", "15 Sliding Puzzle"],
    [57, "I", "移车出库", "Rush Hour"],
    [58, "I", "编程机器人", "Robo Programmer"],
    [59, "I", "割绳子", "Cut the Rope"],
    [60, "I", "传送门谜题", "Portal Grid"],
    [61, "J", "四子棋", "Connect Four"],
    [62, "J", "黑白棋", "Reversi"],
    [63, "J", "五子棋", "Gomoku"],
    [64, "J", "西洋跳棋", "Checkers"],
    [65, "J", "点格棋", "Dots and Boxes"],
    [66, "J", "海战棋", "Battleship"],
    [67, "J", "围墙棋", "Quoridor"],
    [68, "K", "颜色密码", "Mastermind"],
    [69, "K", "Nim取石子", "Nim Strategy"],
    [70, "K", "连通染色", "Flood-It"],
    [71, "K", "单人孔明棋", "Peg Solitaire"],
    [72, "K", "Hex连通棋", "Hex Connection"],
    [73, "K", "飞行棋", "Ludo Race"],
    [74, "L", "变道赛车", "Highway Racer 1979"],
    [75, "L", "滑雪绕旗", "Alpine Slalom"],
    [76, "L", "迷你高尔夫", "Mini Golf"],
    [77, "L", "保龄球", "Ten-Pin Bowling"],
    [78, "L", "棒球击打", "Home Run Derby"],
    [79, "L", "足球点球", "Penalty Shootout"],
    [80, "M", "Tron光线摩托", "Tron Light Cycles"],
    [81, "M", "Qix圈地", "Qix Territory"],
    [82, "M", "坦克抛物线对轰", "Tank Artillery"],
    [83, "M", "路径塔防", "Path Tower Defense"],
    [84, "M", "节点征服", "Node Conquest"],
    [85, "M", "旅鼠拯救", "Lemmings Rescue"],
    [86, "N", "小农场", "Tiny Harvest"],
    [87, "N", "交通灯管理", "Traffic Control"],
    [88, "N", "机场降落引导", "Flight Control"],
    [89, "N", "消防灭火", "Fire Brigade"],
    [90, "N", "传送带工厂", "Conveyor Factory"],
    [91, "O", "电线迷宫", "Steady Wire Loop"],
    [92, "O", "水果忍者", "Fruit Ninja"],
    [93, "O", "黑洞吞噬", "Hole.io"],
    [94, "O", "钩爪摆荡", "Grapple Swing"],
    [95, "O", "旋转避壁", "Super Hexagon"],
    [96, "O", "冰面滑行迷宫", "Ice Slide Maze"],
    [97, "P", "青蛙过河", "Frogger 1981"],
    [98, "P", "月球着陆", "Lunar Lander"],
    [99, "P", "自动攻击生存", "Pixel Survivor"],
    [100, "P", "翻牌配对", "Memory Match"]
  ];
  const ARCADE_TITLE_MAP = Object.fromEntries(ARCADE_CATALOG_100.map(([id, , zh, en]) => [id, `[#${String(id).padStart(3, "0")}] ${zh} (${en})`]));
  let arcadeHeartbeatTimer = null;
  let activeControlType = 3;

  function filterArcadeCatalog() {
    const cat = $("arcadeCategoryFilter")?.value || "all";
    const q = ($("arcadeSearchInput")?.value || "").trim().toLowerCase();
    let visible = 0;
    $$("#arcadeGameGrid [data-arcade-id]").forEach((btn) => {
      const gid = parseInt(btn.dataset.arcadeId, 10);
      const item = ARCADE_CATALOG_100[gid - 1];
      const available=ArcadeTransport.registeredIds.includes(gid);
      btn.disabled=!available;
      const guide=window.ARCADE_GAME_GUIDES?.[gid];
      btn.title=guide?.help || "游玩说明尚未加载";
      if(!btn.querySelector(".arcade-game-description")){
        const name=document.createElement("strong");name.textContent=btn.textContent;
        const description=document.createElement("span");description.className="arcade-game-description";
        description.textContent=guide?.help || "游玩说明尚未加载";
        btn.replaceChildren(name,description);
      }
      btn.dataset.available=String(available);
      const matchCat = cat === "all" || btn.dataset.arcadeCat === cat;
      const hay = `${btn.dataset.arcadeId} ${gid} ${item ? item[2] + " " + item[3] : btn.textContent} ${guide?.help||""}`.toLowerCase();
      const show = matchCat && (!q || hay.includes(q));
      btn.hidden = !show;
      if (show) visible++;
    });
    if ($("arcadeVisibleCount")) {
      $("arcadeVisibleCount").textContent = `${visible} / 100 目录 · ${ArcadeTransport.registeredIds.length} 已接入（实机待验）`;
    }
  }
  if ($("arcadeCategoryFilter")) $("arcadeCategoryFilter").onchange = filterArcadeCatalog;
  if ($("arcadeSearchInput")) $("arcadeSearchInput").oninput = filterArcadeCatalog;
  filterArcadeCatalog();

  function updateGamepadLayout(controlType, gid) {
    const tapStage = $("arcadeTapStage");
    const dpad = $("arcadeDpad");
    const actions = $("arcadeActions");
    const trackStage = $("arcadeTrackStage");
    const versus = $("arcadeVersusStage");
    const keyUp = $("marioKeyUp");
    const keyDown = $("marioKeyDown");
    const keyLeft = $("marioKeyLeft");
    const keyRight = $("marioKeyRight");
    const keyB = $("marioKeyB");
    const btnA_sub = document.querySelector("#marioKeyA .btn-sub");
    const btnB_sub = document.querySelector("#marioKeyB .btn-sub");
    const tapBtn = $("arcadeTapBig");

    if (tapStage) tapStage.style.display = "none";
    if (dpad) dpad.style.display = "grid";
    if (actions) actions.style.display = "flex";
    if (trackStage) trackStage.style.display = "none";
    if (versus) versus.style.display = "none";
    if (keyUp) keyUp.style.visibility = "visible";
    if (keyDown) keyDown.style.visibility = "visible";
    if (keyLeft) keyLeft.style.visibility = "visible";
    if (keyRight) keyRight.style.visibility = "visible";
    if (keyB) keyB.style.display = "inline-flex";

    const ct = Number(controlType !== undefined ? controlType : 3);
    activeControlType = ct;
    const gNum = Number(gid || state.arcadeGid || 1);
    const help=document.querySelector(".mario-help");
    const selectedGuide=window.ARCADE_GAME_GUIDES?.[gNum];
    if(help)help.textContent=selectedGuide?.help || "游玩说明尚未加载，请刷新页面。";

    if (ct === 0) {
      // CTRL_TAP_SINGLE (#009 Flappy, #010 Stack, #012 Knife Hit, #013 Pendulum, #014 Orbit Hop, #018 Red/Green Light)
      if (tapStage) tapStage.style.display = "flex";
      if (dpad) dpad.style.display = "none";
      if (actions) actions.style.display = "none";
      if (tapBtn) {
        const tapLabels = {
          9: "🕊️ 拍翅轻点 (TAP)",
          10: "🧱 切削放置 (TAP)",
          12: "🗡️ 投掷飞刀 (TAP)",
          13: "🎯 释放摆球 (TAP)",
          14: "🪐 切换轨道 (TAP)",
          18: "🚦 按住前进 · 松开急停 (HOLD)"
        };
        tapBtn.textContent = tapLabels[gNum] || "👆 单键触控 (TAP)";
      }
    } else if (ct === 1) {
      // CTRL_TWO_BUTTON (#002 Doodle Jump, #021 Breakout, #074 Highway Racer, #075 Slalom Ski, #095 Super Hexagon)
      if (keyUp) keyUp.style.visibility = gNum===74 ? "visible" : "hidden";
      if (keyDown) keyDown.style.visibility = gNum===74 ? "visible" : "hidden";
      if (actions) actions.style.display = selectedGuide?.a ? "flex" : "none";
    } else if (ct === 2) {
      // CTRL_DPAD_4WAY
      if (actions) actions.style.display = "none";
    } else if (ct === 3) {
      // CTRL_ARCADE_AB
      if (gNum === 41 || gNum === 42) {
        if (btnA_sub) btnA_sub.textContent = "旋转";
        if (btnB_sub) btnB_sub.textContent = "快降";
      } else if(gNum===55) {
        if(btnA_sub)btnA_sub.textContent="旋转/预览";
        if(btnB_sub)btnB_sub.textContent="发射/停止";
      } else if(gNum===57) {
        if(btnA_sub)btnA_sub.textContent="下一辆";
        if(btnB_sub)btnB_sub.textContent="上一辆";
      } else if(gNum===58) {
        if(btnA_sub)btnA_sub.textContent="执行程序";
        if(btnB_sub)btnB_sub.textContent="撤销/中止";
      } else if(gNum===81) {
        if(btnA_sub)btnA_sub.textContent="开/关画线";
        if(keyB)keyB.style.display="none";
      } else if(gNum===98) {
        if(btnA_sub)btnA_sub.textContent="喷气";
        if(keyB)keyB.style.display="none";
      } else if(gNum===85) {
        if(btnA_sub)btnA_sub.textContent="分配技能";
        if(btnB_sub)btnB_sub.textContent="切换技能";
      } else if(gNum===92) {
        if(btnA_sub)btnA_sub.textContent="挥刀";
        if(btnB_sub)btnB_sub.textContent="斜挥刀";
      } else if (gNum === 38) {
        if (btnA_sub) btnA_sub.textContent = "炸弹";
        if (btnB_sub) btnB_sub.textContent = "动作";
      } else if (gNum === 22) {
        if (btnA_sub) btnA_sub.textContent = "左挡";
        if (btnB_sub) btnB_sub.textContent = "右挡";
      } else if (gNum === 92) {
        if (btnA_sub) btnA_sub.textContent = "挥刀";
        if (btnB_sub) btnB_sub.textContent = "旋斩";
      } else if ([26, 27, 28, 29, 30, 31, 32].includes(gNum)) {
        if (btnA_sub) btnA_sub.textContent = "开火";
        if (btnB_sub) btnB_sub.textContent = "副武";
      } else {
        if (btnA_sub) btnA_sub.textContent = "确认/A";
        if (btnB_sub) btnB_sub.textContent = "切换/B";
      }
    } else if (ct === 4) {
      // CTRL_MULTI_TRACK (#015 Simon, #017 Rhythm Lanes, #070 Flood-It)
      if (dpad) dpad.style.display = "none";
      if (actions) actions.style.display = "none";
      if (trackStage) trackStage.style.display = "grid";
      const t1 = $("arcadeTrack1"), t2 = $("arcadeTrack2"), t3 = $("arcadeTrack3"), t4 = $("arcadeTrack4");
      if (gNum === 17) {
        if (t1) t1.textContent = "轨 1";
        if (t2) t2.textContent = "轨 2";
        if (t3) t3.textContent = "轨 3";
        if (t4) t4.textContent = "轨 4";
      } else {
        if (t1) t1.textContent = "1 · 红";
        if (t2) t2.textContent = "2 · 绿";
        if (t3) t3.textContent = "3 · 蓝";
        if (t4) t4.textContent = "4 · 黄";
      }
    } else if (ct === 5) {
      // CTRL_VERSUS_DUAL (#020 Pong)
      if (dpad) dpad.style.display = "none";
      if (actions) actions.style.display = "none";
      if (versus) versus.style.display = "flex";
    }
    const b3=selectedGuide;
    if(b3 && [1,3].includes(ct)){if(btnA_sub)btnA_sub.textContent=b3.a||"确认";if(btnB_sub)btnB_sub.textContent=b3.b||"";if(keyB)keyB.style.display=b3.b?"inline-flex":"none";}
    if(b3 && ct===0 && tapBtn && b3.a)tapBtn.textContent=b3.a;

  }

  function updateFsGamepadLayout(controlType, gid) {
    const gNum = Number(gid || state.arcadeGid || 1);
    const ct = Number(controlType !== undefined ? controlType : 3);
    const dpad = $("fsDpad");
    const lrStage = $("fsLrStage");
    const tapLeft = $("fsTapLeft");
    const tapRight = $("fsTapRight");
    const actions = $("fsActions");
    const tracks = $("fsTracks");
    const pongP1 = $("fsPongP1");
    const pongP2 = $("fsPongP2");
    const guide = window.ARCADE_GAME_GUIDES?.[gNum];
    const tip = $("fsGuideText");
    if (tip) tip.textContent = guide?.help || "按键操控灯板";

    const keyASub = $("fsKeyASub");
    const keyBSub = $("fsKeyBSub");
    const btnB = $("fsKeyB");

    if (dpad) dpad.style.display = "none";
    if (lrStage) lrStage.style.display = "none";
    if (tapLeft) tapLeft.style.display = "none";
    if (tapRight) tapRight.style.display = "none";
    if (actions) actions.style.display = "none";
    if (tracks) tracks.style.display = "none";
    if (pongP1) pongP1.style.display = "none";
    if (pongP2) pongP2.style.display = "none";

    if (ct === 0) {
      if (tapLeft) tapLeft.style.display = "flex";
      if (tapRight) tapRight.style.display = "flex";
      const tapBigL = $("fsTapBigLeft");
      const tapBigR = $("fsTapBigRight");
      const label = guide?.a || "👆 点击控制";
      if (tapBigL) tapBigL.textContent = label;
      if (tapBigR) tapBigR.textContent = label;
    } else if (ct === 1) {
      if (lrStage) lrStage.style.display = "flex";
      if (guide?.a) {
        if (actions) actions.style.display = "flex";
        if (btnB) btnB.style.display = "none";
        if (keyASub) keyASub.textContent = guide.a;
      }
    } else if (ct === 2) {
      if (dpad) dpad.style.display = "grid";
    } else if (ct === 4) {
      if (tracks) tracks.style.display = "flex";
    } else if (ct === 5) {
      if (pongP1) pongP1.style.display = "flex";
      if (pongP2) pongP2.style.display = "flex";
    } else {
      if (dpad) dpad.style.display = "grid";
      if (actions) actions.style.display = "flex";
      if (btnB) btnB.style.display = "flex";
      if (keyASub) keyASub.textContent = guide?.a || "跳跃";
      if (keyBSub) keyBSub.textContent = guide?.b || "加速";
    }
  }

  let arcadeSettingsDirty=false;
  for(const id of ["arcadeDifficulty","arcadeSoundEnabled","arcadeSoundVolume"])
    $(id)?.addEventListener("input",()=>{arcadeSettingsDirty=true;});
  if($("arcadeApplySettings"))$("arcadeApplySettings").onclick=async()=>{
    const button=$("arcadeApplySettings");button.disabled=true;
    try {
      const data={action:"config",sound_enabled:$("arcadeSoundEnabled").checked,sound_volume:Number($("arcadeSoundVolume").value)};
      if(!$("arcadeDifficulty").disabled)data.difficulty=Number($("arcadeDifficulty").value);
      const reply=await api("/api/arcade",data);arcadeSettingsDirty=false;updateArcadeHud(reply.game_status);
      notice("设置已保存");
    } catch(error){notice(error.message);}finally{button.disabled=false;}
  };

  function updateArcadeHud(status) {
    if (!status) return;
    const difficulty=$("arcadeDifficulty");
    if(difficulty) {
      difficulty.disabled=!status.difficulty_supported || [1,2].includes(status.state);
      if(!arcadeSettingsDirty) {
        difficulty.value=String(status.difficulty??1);
        $("arcadeSoundEnabled").checked=status.sound_enabled===true;
        $("arcadeSoundVolume").value=String(status.sound_volume??25);
      }
      $("arcadeSettingsStatus").textContent = status.difficulty_supported
        ? "可在待机或结算画面切换游戏难度。"
        : "当前游戏采用固定标准难度。";
    }
    if (status.game_id===20 && [1,2].includes(status.player_count)) {
      state.pongPlayers=status.player_count;
      const toggle=$("pongAiToggleBtn");
      if(toggle)toggle.textContent=status.player_count===1?"单人 AI · 切为双人":"本地双人 · 切为 AI";
    }
    const stateLabels = {
      0: "待机",
      1: "游戏中",
      2: "已暂停",
      3: "游戏结束",
      4: "通关胜利",
    };
    const stateColors = {
      0: "#64748b",
      1: "#22c55e",
      2: "#eab308",
      3: "#ef4444",
      4: "#f59e0b",
    };
    const stCode = Number(status.state !== undefined ? status.state : 0);
    const tag = $("marioStateTag");
    if (tag) {
      tag.textContent = status.state_name || stateLabels[stCode] || "待机";
      tag.style.backgroundColor = stateColors[stCode] || "#64748b";
    }

    if ($("marioScoreStat")) {
      const s = String(status.score || 0).padStart(5, "0");
      $("marioScoreStat").textContent = `得分: ${s}`;
    }
    if ($("arcadeHighScoreStat")) {
      const hs = String(status.high_score || 0).padStart(5, "0");
      $("arcadeHighScoreStat").textContent = `最高: ${hs}`;
    }
    if ($("marioLivesStat")) {
      const lives = status.lives !== undefined ? status.lives : 3;
      $("marioLivesStat").textContent = `❤️ ×${lives}`;
    }
    if ($("marioProgressStat")) {
      $("marioProgressStat").textContent = `🏁 ${status.progress || 0}%`;
    }
    if ($("marioProgFill")) {
      $("marioProgFill").style.width = `${Math.min(100, Math.max(0, status.progress || 0))}%`;
    }
    if ($("arcadeControlStat")) {
      const cType = Number(status.control_type !== undefined ? status.control_type : 3);
      const ctNames = {
        0: "单键点按",
        1: "双键控制",
        2: "四向十字键",
        3: "十字键 + A/B",
        4: "四轨按键",
        5: "双人同屏"
      };
      $("arcadeControlStat").textContent = ctNames[cType] || `模式 ${cType}`;
    }

    updateGamepadLayout(status.control_type, status.game_id || state.arcadeGid);

    if ($("arcadePauseBtn")) {
      $("arcadePauseBtn").textContent = stCode === 2 ? "▶ 继续游戏" : "⏸ 暂停游戏";
    }
    const badge = $("marioSyncBadge");
    if (badge && state.arcadeActive && status.source === "esp32_hardware") {
      badge.textContent = "🟢 灯板已连接";
      badge.style.backgroundColor = "rgba(34, 197, 94, 0.2)";
      badge.style.color = "#22c55e";
    }

    // 全屏横屏手柄 HUD 同步
    if ($("fsGameTitle")) {
      $("fsGameTitle").textContent = ARCADE_TITLE_MAP[status.game_id || state.arcadeGid] || `街机 #${status.game_id || state.arcadeGid || 1}`;
    }
    if ($("fsStateStat")) {
      $("fsStateStat").textContent = stCode === 2 ? "⏸ 暂停" : (stCode === 1 ? "🟢 游玩中" : "待机");
    }
    if ($("fsScoreStat")) {
      $("fsScoreStat").textContent = `得分: ${String(status.score || 0).padStart(5, "0")}`;
    }
    if ($("fsHighScoreStat")) {
      $("fsHighScoreStat").textContent = `最高: ${String(status.high_score || 0).padStart(5, "0")}`;
    }
    if ($("fsLivesStat")) {
      $("fsLivesStat").textContent = `❤️ ×${status.lives !== undefined ? status.lives : 3}`;
    }
    if ($("fsProgressStat")) {
      $("fsProgressStat").textContent = `🏁 ${status.progress || 0}%`;
    }
    if ($("fsPauseBtn")) {
      $("fsPauseBtn").textContent = stCode === 2 ? "▶ 继续" : "⏸ 暂停";
    }
    if ($("fsSyncBadge")) {
      if (status.source === "esp32_hardware") {
        $("fsSyncBadge").textContent = "🟢 灯板同步";
        $("fsSyncBadge").style.backgroundColor = "rgba(34, 197, 94, 0.18)";
        $("fsSyncBadge").style.color = "#22c55e";
      } else {
        $("fsSyncBadge").textContent = "🟡 离线模式";
        $("fsSyncBadge").style.backgroundColor = "rgba(234, 179, 8, 0.18)";
        $("fsSyncBadge").style.color = "#eab308";
      }
    }
    updateFsGamepadLayout(status.control_type, status.game_id || state.arcadeGid);
  }

  async function launchArcadeGame(gameId) {
    const idMap = {
      mario: 1, flappy: 9, stack: 10, pong: 20, breakout: 21,
      space_invaders: 26, snake: 33, pacman: 34, bomberman: 38,
      tetris: 41, sokoban: 54, highway: 74, frogger: 97,
      "001": 1, "033": 33, "041": 41,
      1: 1, 33: 33, 41: 41
    };
    const gid = idMap[gameId] || parseInt(gameId, 10);
    if (!ArcadeTransport.registeredIds.includes(gid)) {
      notice("此目标游戏尚未接入当前固件");
      return;
    }

    arcadeSettingsDirty=false;
    const gameTitle = ARCADE_TITLE_MAP[gid] || `街机游戏 #${gid}`;
    navigate("interaction");

    try {
      const res = await api("/api/arcade", { action: "select", game_id: gid });
      if (res && res.status === "ok") {
        state.arcadeActive = true;
        state.arcadeGid = gid;
        state.game = "arcade";
        $("arcadeGameTitle").textContent=gameTitle;
        $("gameState").textContent=gameTitle;
        $("marioContainer").style.display="flex";
        $$("[data-arcade-id]").forEach(btn=>btn.classList.toggle("active",Number(btn.dataset.arcadeId)===gid));

        const badge = $("marioSyncBadge");
        if (badge) {
          if (res.source === "esp32_hardware") {
            badge.textContent = "🟢 灯板已连接";
            badge.style.backgroundColor = "rgba(34, 197, 94, 0.2)";
            badge.style.color = "#22c55e";
          } else {
            badge.textContent = "🟡 离线演示";
            badge.style.backgroundColor = "rgba(234, 179, 8, 0.2)";
            badge.style.color = "#eab308";
          }
        }
        updateArcadeHud(res.game_status);
        startArcadeHeartbeat();
        notice(`已载入 ${gameTitle}`);
      } else {
        throw new Error(res?.message || res?.error || "载入游戏失败");
      }
    } catch (e) {
      notice(`街机选卡失败: ${e.message}`);
      const badge = $("marioSyncBadge");
      if (badge) {
        badge.textContent = "🔴 灯板未连接";
        badge.style.backgroundColor = "rgba(239, 68, 68, 0.2)";
        badge.style.color = "#ef4444";
      }
    }
  }

  function startArcadeHeartbeat() {
    if (arcadeHeartbeatTimer) clearInterval(arcadeHeartbeatTimer);
    let busy=false;
    arcadeHeartbeatTimer = setInterval(async () => {
      if(busy || document.hidden || state.page!=="interaction")return;
      if (!state.arcadeActive) {
        clearInterval(arcadeHeartbeatTimer);
        return;
      }
      try {
        busy=true;
        const hb = await api("/api/arcade", { action: "heartbeat" });
        if (hb && hb.game_status) {
          updateArcadeHud(hb.game_status);
        }
      } catch (err) {
        if(/^stale_/.test(err.message) || state.page!=="interaction")return;
        const badge = $("marioSyncBadge");
        if (badge && state.arcadeActive) {
          badge.textContent = "⚠️ 连接波动 · 已自动暂停";
          badge.style.backgroundColor = "rgba(239, 68, 68, 0.2)";
          badge.style.color = "#ef4444";
        }
      } finally {busy=false;}
    }, 300);
  }

  $$("[data-arcade-id]").forEach((btn) => {
    btn.onclick = (e) => {
      e.preventDefault();
      launchArcadeGame(btn.dataset.arcadeId);
    };
  });

  $$("[data-game]").forEach((b) => {
    if (b.hasAttribute("data-arcade-id")) return;
    b.onclick = (e) => {
      e.preventDefault();
      launchArcadeGame(b.dataset.game);
    };
  });

  if ($("btnMarioGame")) {
    $("btnMarioGame").onclick = (e) => {
      e.preventDefault();
      launchArcadeGame("001");
    };
  }

  if ($("heroPlayMario")) {
    $("heroPlayMario").onclick = (e) => {
      e.preventDefault();
      navigate("interaction");
      launchArcadeGame("001");
    };
  }

  // 手机触屏手柄按键绑定
  const resetArcadeButtons=[];
  function releaseArcadeControls() {
    resetArcadeButtons.forEach(reset=>reset());
    clearInterval(arcadeHeartbeatTimer);
    if(state.arcadeStopping)return Promise.resolve();
    return arcadeTransport.suspend().then(reply=>{
      if(reply?.game_status)updateArcadeHud(reply.game_status);
    });
  }
  function bindArcadeTouchKey(btn, keyName) {
    if (!btn) return;
    const pointers=new Set();
    resetArcadeButtons.push(()=>{pointers.clear();btn.classList.remove("pressed","active");});
    btn.style.touchAction="none";
    btn.addEventListener("pointerdown",e=>{
      e.preventDefault();
      if(pointers.has(e.pointerId))return;
      pointers.add(e.pointerId);btn.setPointerCapture(e.pointerId);
      if(pointers.size!==1)return;
      btn.classList.add("pressed","active");
      if(navigator.vibrate)navigator.vibrate(10);
      api("/api/arcade",{action:"key",key:keyName,down:true}).catch(error=>{
        pointers.clear();btn.classList.remove("pressed","active");notice(error.message);
      });
    });
    const release=e=>{
      e.preventDefault();
      if(!pointers.delete(e.pointerId)||pointers.size)return;
      btn.classList.remove("pressed","active");
      api("/api/arcade",{action:"key",key:keyName,down:false}).catch(error=>notice(error.message));
    };
    btn.addEventListener("pointerup",release);
    btn.addEventListener("pointercancel",release);
    btn.addEventListener("lostpointercapture",release);
  }

  $$("[data-mario-key]").forEach((btn) => {
    bindArcadeTouchKey(btn, btn.dataset.marioKey);
  });

  // #092 水果忍者 (Fruit Ninja) 手机屏幕滑动切割手势直映射
  const arcadeScreenCanvas = $("marioCanvas");
  if (arcadeScreenCanvas) {
    let swipeOrigin = null;
    arcadeScreenCanvas.style.touchAction = "none";
    arcadeScreenCanvas.addEventListener("pointerdown", (e) => {
      if (!state.arcadeActive || state.arcadeGid !== 92) return;
      swipeOrigin = { x: e.clientX, y: e.clientY, id: e.pointerId, fired: false };
      try { arcadeScreenCanvas.setPointerCapture(e.pointerId); } catch (_) {}
    });
    arcadeScreenCanvas.addEventListener("pointermove", (e) => {
      if (!swipeOrigin || swipeOrigin.id !== e.pointerId || swipeOrigin.fired || state.arcadeGid !== 92) return;
      const dx = e.clientX - swipeOrigin.x;
      const dy = e.clientY - swipeOrigin.y;
      if (Math.hypot(dx, dy) >= 16) {
        swipeOrigin.fired = true;
        let mask = 16; // KEY_A slash
        if (Math.abs(dx) > 8) mask |= dx > 0 ? 2 : 1;
        if (Math.abs(dy) > 8) mask |= dy > 0 ? 8 : 4;
        api("/api/arcade", { action: "input", down: mask, pressed: mask }).catch(() => {});
        setTimeout(() => {
          if (state.arcadeActive && state.arcadeGid === 92) {
            api("/api/arcade", { action: "input", down: 0, pressed: 0 }).catch(() => {});
          }
        }, 90);
      }
    });
    const clearSwipe = () => { swipeOrigin = null; };
    arcadeScreenCanvas.addEventListener("pointerup", clearSwipe);
    arcadeScreenCanvas.addEventListener("pointercancel", clearSwipe);
  }

  if ($("pongAiToggleBtn")) {
    $("pongAiToggleBtn").onclick = async (e) => {
      e.preventDefault();
      try {
        resetArcadeButtons.forEach(reset => reset());
        const reply=await api("/api/arcade",{action:"players",count:state.pongPlayers===2?1:2});
        updateArcadeHud(reply.game_status);
        notice(state.pongPlayers===2?"已选择本地双人：P1 ↑/↓，P2 A/B":"已选择单人 AI");
      } catch (err) {
        notice("Pong 模式切换失败: " + err.message);
      }
    };
  }

  if ($("marioStartBtn")) {
    $("marioStartBtn").onclick = async (e) => {
      e.preventDefault();
      if (navigator.vibrate) try { navigator.vibrate(12); } catch (_) {}
      try {
        const res = await api("/api/arcade", { action: "start" });
        if (res && res.game_status) updateArcadeHud(res.game_status);
        notice("街机已开始游玩");
        startArcadeHeartbeat();
      } catch (err) {
        notice(`启动失败: ${err.message}`);
      }
    };
  }

  if ($("arcadePauseBtn")) {
    $("arcadePauseBtn").onclick = async (e) => {
      e.preventDefault();
      if (navigator.vibrate) try { navigator.vibrate(12); } catch (_) {}
      try {
        const curTag = $("marioStateTag")?.textContent || "";
        const isPaused = curTag.includes("PAUSED") || curTag.includes("暂停");
        const act = isPaused ? "resume" : "pause";
        const res = await api("/api/arcade", { action: act });
        if (res && res.game_status) updateArcadeHud(res.game_status);
        notice(isPaused ? "游戏已恢复继续" : "游戏已暂停");
        startArcadeHeartbeat();
      } catch (err) {
        notice(`操作失败: ${err.message}`);
      }
    };
  }

  if ($("marioResetBtn")) {
    $("marioResetBtn").onclick = async (e) => {
      e.preventDefault();
      if (navigator.vibrate) try { navigator.vibrate(12); } catch (_) {}
      try {
        const res = await api("/api/arcade", { action: "reset" });
        if (res && res.game_status) updateArcadeHud(res.game_status);
        notice("街机已重新开局");
      } catch (err) {
        notice(`重开失败: ${err.message}`);
      }
    };
  }

  if ($("marioStopBtn")) {
    $("marioStopBtn").onclick = async (e) => {
      e.preventDefault();
      if(state.arcadeStopping)return;
      state.arcadeStopping=true;
      if (navigator.vibrate) try { navigator.vibrate(12); } catch (_) {}
      if (arcadeHeartbeatTimer) clearInterval(arcadeHeartbeatTimer);
      try {await api("/api/arcade", { action: "stop" });}
      catch(error){resetArcadeButtons.forEach(reset=>reset());notice("本地按键已清除，设备退出未确认，请检查连接后重试。" + error.message);return;}
      finally {state.arcadeStopping=false;}
      resetArcadeButtons.forEach(reset=>reset());
      state.arcadeActive = false;
      state.game = null;
      if ($("gameState")) $("gameState").textContent = "选择游戏开始";
      if ($("marioContainer")) $("marioContainer").style.display = "none";
      exitFullscreenGamepad();

      $$("[data-arcade-id]").forEach((btn) => btn.classList.remove("active"));
      $$("[data-game]").forEach((btn) => btn.classList.remove("active"));
      notice("已安全退出街机系统");
    };
  }

  function enterFullscreenGamepad() {
    const overlay = $("fullscreenGamepadOverlay");
    if (!overlay) return;
    overlay.style.display = "flex";
    overlay.setAttribute("aria-hidden", "false");
    document.body.classList.add("fs-gamepad-active");
    if (navigator.vibrate) try { navigator.vibrate(20); } catch (_) {}
    try {
      const el = document.documentElement;
      if (el.requestFullscreen) {
        el.requestFullscreen().catch(() => {});
      } else if (el.webkitRequestFullscreen) {
        el.webkitRequestFullscreen();
      }
    } catch (_) {}
    try {
      if (screen.orientation && screen.orientation.lock) {
        screen.orientation.lock("landscape").catch(() => {});
      }
    } catch (_) {}
    updateFsGamepadLayout(activeControlType, state.arcadeGid);
  }

  function exitFullscreenGamepad() {
    const overlay = $("fullscreenGamepadOverlay");
    if (!overlay) return;
    overlay.style.display = "none";
    overlay.setAttribute("aria-hidden", "true");
    document.body.classList.remove("fs-gamepad-active");
    if (navigator.vibrate) try { navigator.vibrate(10); } catch (_) {}
    try {
      if (document.fullscreenElement && document.exitFullscreen) {
        document.exitFullscreen().catch(() => {});
      }
    } catch (_) {}
    try {
      if (screen.orientation && screen.orientation.unlock) {
        screen.orientation.unlock();
      }
    } catch (_) {}
  }

  if ($("enterFullscreenPadBtn")) {
    $("enterFullscreenPadBtn").onclick = (e) => {
      e.preventDefault();
      enterFullscreenGamepad();
    };
  }
  if ($("fsExitPadBtn")) {
    $("fsExitPadBtn").onclick = (e) => {
      e.preventDefault();
      exitFullscreenGamepad();
    };
  }
  if ($("fsStartBtn")) {
    $("fsStartBtn").onclick = async (e) => {
      e.preventDefault();
      if (navigator.vibrate) try { navigator.vibrate(12); } catch (_) {}
      try {
        const res = await api("/api/arcade", { action: "start" });
        if (res && res.game_status) updateArcadeHud(res.game_status);
        notice("街机已开始游玩");
        startArcadeHeartbeat();
      } catch (err) {
        notice(`启动失败: ${err.message}`);
      }
    };
  }
  if ($("fsPauseBtn")) {
    $("fsPauseBtn").onclick = async (e) => {
      e.preventDefault();
      if (navigator.vibrate) try { navigator.vibrate(12); } catch (_) {}
      try {
        const curTag = $("marioStateTag")?.textContent || $("fsStateStat")?.textContent || "";
        const isPaused = curTag.includes("PAUSED") || curTag.includes("暂停");
        const act = isPaused ? "resume" : "pause";
        const res = await api("/api/arcade", { action: act });
        if (res && res.game_status) updateArcadeHud(res.game_status);
        notice(isPaused ? "游戏已恢复继续" : "游戏已暂停");
        startArcadeHeartbeat();
      } catch (err) {
        notice(`操作失败: ${err.message}`);
      }
    };
  }
  if ($("fsResetBtn")) {
    $("fsResetBtn").onclick = async (e) => {
      e.preventDefault();
      if (navigator.vibrate) try { navigator.vibrate(12); } catch (_) {}
      try {
        const res = await api("/api/arcade", { action: "reset" });
        if (res && res.game_status) updateArcadeHud(res.game_status);
        notice("街机已重新开局");
      } catch (err) {
        notice(`重开失败: ${err.message}`);
      }
    };
  }

  // 键盘事件全局适配 (WASD / 十字键 / 1-4 四轨键 / 空格 / Shift / Enter / R)
  window.addEventListener("keydown", (e) => {
    if (!state.arcadeActive || document.activeElement?.tagName === "INPUT" || document.activeElement?.tagName === "TEXTAREA" || document.activeElement?.tagName === "SELECT") return;
    const trackKeyMap = activeControlType === 4 ? { "1": "left", "2": "down", "3": "up", "4": "right" } : {};
    const keyMap = {
      ...trackKeyMap,
      ArrowLeft: "left", a: "left", A: "left",
      ArrowRight: "right", d: "right", D: "right",
      ArrowUp: "up", w: "up", W: "up",
      ArrowDown: "down", s: "down", S: "down",
      " ": "a", j: "a", J: "a",
      Shift: "b", k: "b", K: "b",
      Enter: "start",
      r: "reset", R: "reset",
      p: "pause", P: "pause"
    };
    const k = keyMap[e.key];
    if (k) {
      e.preventDefault();
      if (e.repeat) return;
      if (k === "reset") {
        api("/api/arcade", { action: "reset" }).catch(() => {});
      } else if (k === "pause") {
        api("/api/arcade", { action: "pause" }).catch(() => {});
      } else if (k === "start") {
        api("/api/arcade", { action: "start" }).catch(() => {});
      } else {
        api("/api/arcade", { action: "key", key: k, down: true }).catch(() => {});
      }
    }
  });

  window.addEventListener("keyup", (e) => {
    if (!state.arcadeActive || document.activeElement?.tagName === "INPUT" || document.activeElement?.tagName === "TEXTAREA" || document.activeElement?.tagName === "SELECT") return;
    const trackKeyMap = activeControlType === 4 ? { "1": "left", "2": "down", "3": "up", "4": "right" } : {};
    const keyMap = {
      ...trackKeyMap,
      ArrowLeft: "left", a: "left", A: "left",
      ArrowRight: "right", d: "right", D: "right",
      ArrowUp: "up", w: "up", W: "up",
      ArrowDown: "down", s: "down", S: "down",
      " ": "a", j: "a", J: "a",
      Shift: "b", k: "b", K: "b"
    };
    const k = keyMap[e.key];
    if (k) {
      api("/api/arcade", { action: "key", key: k, down: false }).catch(() => {});
    }
  });

  // Disposable 4 Hz preview: prioritize commands over full-frame telemetry.
  let arcadeFrameBusy=false;
  setInterval(async () => {
    if (!arcadeFrameBusy && !document.hidden && state.arcadeActive && $("marioCanvas") && $("marioContainer")?.style.display !== "none") {
      try {
        arcadeFrameBusy=true;
        const res = await api("/api/arcade/frame", undefined, "GET", 1500);
        if (res && res.hex) {
          if ($("marioCanvas")) {
            drawMarioFrame($("marioCanvas"), res.hex);
            $("arcadePreviewStatus").textContent="实时画面 · 帧 "+(res.frame_id??"—");
          }
          if ($("fsMiniCanvas") && $("fullscreenGamepadOverlay")?.style.display !== "none") {
            drawMarioFrame($("fsMiniCanvas"), res.hex);
          }
        }
        if (res?.game_status || (res?.status && typeof res.status === "object")) updateArcadeHud(res.game_status || res.status);
      } catch (error) {
        if(!/^stale_|telemetry_busy/.test(error.message))$("arcadePreviewStatus").textContent="画面同步中…";
      } finally { arcadeFrameBusy=false; }
    }
  }, 250);

  let phoneStream = null;
  let phoneUploadTimer = null;
  let phoneUploading = false;

  function stopPhoneCamera() {
    if (window.AmadeusNative && window.AmadeusNative.stopFrontCamera) {
      try { window.AmadeusNative.stopFrontCamera(); } catch(e) {}
    }
    if (phoneUploadTimer) {
      clearInterval(phoneUploadTimer);
      phoneUploadTimer = null;
    }
    phoneUploading = false;
    if (phoneStream && phoneStream.getTracks) {
      try {
        phoneStream.getTracks().forEach((t) => t.stop());
      } catch (e) {}
    }
    phoneStream = null;
    const video = $("phoneCameraVideo");
    if (video) { video.srcObject = null; video.style.display = "none"; }
    const img = $("phoneCameraImg");
    if (img) { img.src = ""; img.style.display = "none"; }
    const wrapper = $("phoneCameraWrapper");
    if (wrapper) wrapper.style.display = "none";
    const overlay = $("phoneCameraOverlay");
    if (overlay) {
      const ctx = overlay.getContext("2d");
      ctx.clearRect(0, 0, overlay.width, overlay.height);
    }
  }

  async function startPhoneCamera() {
    stopPhoneCamera();
    const wrapper = $("phoneCameraWrapper");
    const video = $("phoneCameraVideo");
    const img = $("phoneCameraImg");
    const overlay = $("phoneCameraOverlay");
    const info = $("phoneDetectionInfo");
    const mode = $("visionMode") ? $("visionMode").value : "fingertip";
    const tok = getAccessToken();
    state.token = tok;

    // 1. Android APK native hardware camera bridge
    if (window.AmadeusNative && window.AmadeusNative.hasNativeCamera && window.AmadeusNative.hasNativeCamera()) {
      if (video) video.style.display = "none";
      if (img) img.style.display = "block";
      if (wrapper) wrapper.style.display = "block";

      window.onNativeCameraFrame = function(b64) {
        if (img) img.src = "data:image/jpeg;base64," + b64;
      };

      window.onNativeCameraObservation = function(res) {
        const obs = res.observation || {};
        if (overlay && img) {
          overlay.width = img.clientWidth || 320;
          overlay.height = img.clientHeight || 240;
          const octx = overlay.getContext("2d");
          octx.clearRect(0, 0, overlay.width, overlay.height);

          if (obs.hand) {
            const h = obs.hand;
            const hx = (1 - h.x) * overlay.width;
            const hy = h.y * overlay.height;
            octx.beginPath();
            octx.arc(hx, hy, 16, 0, Math.PI * 2);
            octx.fillStyle = h.pinch
              ? "rgba(255, 235, 59, 0.9)"
              : "rgba(76, 175, 80, 0.9)";
            octx.fill();
            octx.lineWidth = 3;
            octx.strokeStyle = "#fff";
            octx.stroke();

            if (info) {
              info.textContent = h.pinch ? "✋ 捏合抓取" : "👆 食指追踪中";
            }
          } else if (obs.present) {
            if (info) {
              info.textContent = obs.identity
                ? `👤 识别: ${obs.identity}`
                : "👤 人脸就绪";
            }
          } else {
            if (info) info.textContent = "正在捕捉手势/人脸...";
          }
        }
      };

      let serverBase = state.serverOrigin || window.location.origin;
      if (!serverBase || serverBase.startsWith("file:")) {
        const savedUrl = localStorage.getItem("server_url") || "";
        serverBase = savedUrl || "http://192.168.186.90:8080";
      }
      serverBase = serverBase.replace(/\/+$/, "");
      const uploadUrl = `${serverBase}/api/pro/camera/frame?token=${encodeURIComponent(tok)}&mode=${encodeURIComponent(mode)}`;

      const started = window.AmadeusNative.startFrontCamera(uploadUrl, mode);
      if (!started) {
        throw Error("硬件前置摄像头无法打开，请确认已授予相机权限");
      }
      phoneStream = { isNative: true };
      return;
    }

    // 2. WebRTC getUserMedia for secure browser contexts
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw Error("当前浏览器运行环境未开放 WebRTC 权限，请使用最新版 APK 或选择【电脑摄像头】");
    }
    if (img) img.style.display = "none";
    if (video) video.style.display = "block";

    const canvas = $("phoneCameraHidden") || document.createElement("canvas");
    const stream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: "user",
        width: { ideal: 480 },
        height: { ideal: 480 },
      },
      audio: false,
    });
    phoneStream = stream;
    video.srcObject = stream;
    await video.play().catch(() => {});
    if (wrapper) wrapper.style.display = "block";

    canvas.width = 256;
    canvas.height = 256;
    const ctx = canvas.getContext("2d");

    phoneUploadTimer = setInterval(async () => {
      if (phoneUploading || !phoneStream || video.readyState < 2) return;
      phoneUploading = true;
      try {
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        const blob = await new Promise((res) =>
          canvas.toBlob(res, "image/jpeg", 0.65)
        );
        if (!blob) return;

        const currentMode = $("visionMode") ? $("visionMode").value : "fingertip";
        const url = `/api/pro/camera/frame?token=${encodeURIComponent(tok)}&mode=${encodeURIComponent(currentMode)}`;

        const response = await fetch(url, {
          method: "POST",
          headers: {
            "Content-Type": "image/jpeg",
            "X-Vision-Mode": currentMode,
            ...(tok ? { "Authorization": "Bearer " + tok, "X-Access-Token": tok } : {}),
          },
          body: blob,
        });

        if (response.ok) {
          const res = await response.json();
          const obs = res.observation || {};

          if (overlay) {
            overlay.width = video.videoWidth || 320;
            overlay.height = video.videoHeight || 240;
            const octx = overlay.getContext("2d");
            octx.clearRect(0, 0, overlay.width, overlay.height);

            if (obs.hand) {
              const h = obs.hand;
              const hx = (1 - h.x) * overlay.width;
              const hy = h.y * overlay.height;
              octx.beginPath();
              octx.arc(hx, hy, 16, 0, Math.PI * 2);
              octx.fillStyle = h.pinch
                ? "rgba(255, 235, 59, 0.9)"
                : "rgba(76, 175, 80, 0.9)";
              octx.fill();
              octx.lineWidth = 3;
              octx.strokeStyle = "#fff";
              octx.stroke();

              if (info) {
                info.textContent = h.pinch ? "✋ 捏合抓取" : "👆 食指追踪中";
              }
            } else if (obs.present) {
              if (info) {
                info.textContent = obs.identity
                  ? `👤 识别: ${obs.identity}`
                  : "👤 人脸就绪";
              }
            } else {
              if (info) info.textContent = "正在捕捉手势/人脸...";
            }
          }
        }
      } catch (err) {
      } finally {
        phoneUploading = false;
      }
    }, 65);
  }

  if ($("cameraSource")) {
    $("cameraSource").addEventListener("change", () => {
      const src = $("cameraSource").value;
      if ($("pcCameraConfig")) {
        $("pcCameraConfig").style.display = src === "pc" ? "block" : "none";
      }
    });
  }

  bind("cameraDetectBtn", async () => {
    try {
      const r = await api("/api/pro/camera/devices", undefined, "GET");
      if (r && r.devices && r.devices.length) {
        notice(`已检测到 ${r.devices.length} 个可用摄像头: ` + r.devices.map(d => `${d.name}`).join(", "));
        $("camera").value = r.devices[0].id;
      } else {
        notice("未探测到额外摄像头，保持默认 0");
      }
    } catch (e) {
      notice("摄像头探测: " + e.message);
    }
  });

  bind("visionStart", async () => {
    const src = $("cameraSource") ? $("cameraSource").value : "phone";
    if (src === "phone") {
      try {
        if ($("cameraStreamWrapper")) $("cameraStreamWrapper").style.display = "none";
        await startPhoneCamera();
        notice("手机前置摄像头已开启，正在向灯板同步");
        $("visionBadge").textContent = "运行中";
        $("visionSummary").textContent = `手机前置互动：${$("visionMode").value} · 实时传输中`;
      } catch (err) {
        notice("前置摄像头启动提示: " + err.message);
      }
    } else {
      stopPhoneCamera();
      const res = await api("/api/pro/vision", {
        enabled: true,
        mode: $("visionMode").value,
        camera: Number($("camera").value),
      });
      if (res && res.error) {
        notice("摄像头启动提示: " + res.error);
      } else {
        notice("已开启电脑摄像头互动");
        if ($("cameraStreamWrapper")) {
          $("cameraStreamWrapper").style.display = "block";
          const tok = getAccessToken();
          state.token = tok;
          $("cameraStreamImg").src = `/api/pro/camera/feed?token=${encodeURIComponent(tok)}&t=${Date.now()}`;
        }
      }
    }
    lastPro = 0;
    setTimeout(() => poll(), 500);
  });
  bind("visionStop", async () => {
    stopPhoneCamera();
    await api("/api/pro/vision", { enabled: false });
    if ($("cameraStreamWrapper")) {
      $("cameraStreamWrapper").style.display = "none";
      $("cameraStreamImg").src = "";
    }
    cancelCalibration();
    lastPro = 0;
    $("visionBadge").textContent = "未启用";
    $("visionSummary").textContent = "摄像头未启用";
  });
  let currentPhoneRotation = 90;
  if ($("rotatePhoneCameraBtn")) {
    $("rotatePhoneCameraBtn").addEventListener("click", (e) => {
      e.stopPropagation();
      e.preventDefault();
      currentPhoneRotation = (currentPhoneRotation + 90) % 360;
      if (window.AmadeusNative && window.AmadeusNative.setCameraRotation) {
        window.AmadeusNative.setCameraRotation(currentPhoneRotation);
      }
      notice(`已顺时针旋转至: ${currentPhoneRotation}°`);
    });
  }
  bind("enroll", async () => {
    const name = $("identity").value.trim();
    if (!name) throw Error("请填写登记名称");
    await api("/api/pro/enroll", { name });
    notice("当前人脸已登记到电脑本地");
  });
  const targets = [
    [0.1, 0.1],
    [0.5, 0.1],
    [0.9, 0.1],
    [0.1, 0.5],
    [0.5, 0.5],
    [0.9, 0.5],
    [0.1, 0.9],
    [0.5, 0.9],
    [0.9, 0.9],
  ];
  let samples = [],
    targetDot = null;
  function cancelCalibration() {
    targetDot?.remove();
    targetDot = null;
  }
  function calibrationText() {
    cancelCalibration();
    const target = targets[samples.length];
    $("calibration").textContent = target
      ? `注视橙色圆点，点击采集或按空格 (${samples.length}/9)`
      : "九点视线校准已完成";
    if (target) {
      targetDot = document.createElement("div");
      targetDot.className = "calibration-dot";
      targetDot.style.left = target[0] * 100 + "%";
      targetDot.style.top = target[1] * 100 + "%";
      document.body.append(targetDot);
    }
  }
  bind("calibrate", () => {
    if (!state.vision?.running) throw Error("请先启用视觉");
    samples = [];
    calibrationText();
  });
  bind("sampleGaze", async () => {
    if (!targetDot) throw Error("请先开始九点校准");
    const s = await api("/api/pro/status", undefined, "GET"),
      v = s.vision,
      o = v.observation;
    if (
      !v.running ||
      v.fresh === false ||
      !o?.present ||
      o.iris_x === undefined
    )
      throw Error("请正对摄像头以识别人脸与视线");
    samples.push([o.iris_x, o.iris_y, ...targets[samples.length]]);
    if (samples.length === 9) {
      const r = await api("/api/pro/calibrate", { samples });
      notice(
        `视线校准已完成（误差 ${Number(r.rms_training_error).toFixed(4)}）`,
      );
    }
    calibrationText();
  });
  document.addEventListener("keydown", (e) => {
    if (
      e.code === "Space" &&
      targetDot &&
      !["INPUT", "TEXTAREA", "SELECT", "BUTTON"].includes(
        document.activeElement.tagName,
      )
    ) {
      e.preventDefault();
      $("sampleGaze").click();
    }
  });
  async function listMemory() {
    const list = await api("/api/pro/memory", undefined, "GET");
    $("memories").replaceChildren();
    for (const item of list) {
      const p = document.createElement("p"),
        text = document.createElement("span"),
        b = document.createElement("button");
      text.textContent = item.text;
      b.textContent = "删除";
      b.className = "quiet";
      b.onclick = async () => {
        try {
          await api("/api/pro/memory", { id: item.id }, "DELETE");
          await listMemory();
        } catch (e) {
          notice(e.message);
        }
      };
      p.append(text, b);
      $("memories").append(p);
    }
    if (!list.length) $("memories").textContent = "还没有保存的记忆。";
  }
  bind("listMemory", listMemory);
  bind("addMemory", async () => {
    const text = $("memoryText").value.trim();
    if (!text) throw Error("先写下想记住的内容");
    await api("/api/pro/memory", { text });
    $("memoryText").value = "";
    await listMemory();
    notice("记忆已保存");
  });
  bind("addDocument", async () => {
    const text = $("memoryText").value.trim();
    if (!text) throw Error("先填写参考资料");
    const r = await api("/api/pro/documents", { text });
    notice(`已导入 ${r.chunks} 段资料`);
  });
  const draft = new Uint8Array(768),
    editor = $("editor"),
    draftContext = editor.getContext("2d");
  let drawing = false;
  function drawDraft() {
    draftContext.fillStyle = "#111316";
    draftContext.fillRect(0, 0, 320, 320);
    for (let i = 0; i < 256; i++) {
      draftContext.fillStyle = `rgb(${draft.slice(i * 3, i * 3 + 3).join(",")})`;
      draftContext.fillRect((i % 16) * 20, Math.floor(i / 16) * 20, 19, 19);
    }
  }
  function paint(e) {
    const r = editor.getBoundingClientRect(),
      x = Math.floor(((e.clientX - r.left) / r.width) * 16),
      y = Math.floor(((e.clientY - r.top) / r.height) * 16);
    if (x < 0 || x > 15 || y < 0 || y > 15) return;
    for (let k = 0; k < 3; k++)
      draft[(y * 16 + x) * 3 + k] = parseInt(
        $("color").value.slice(1 + k * 2, 3 + k * 2),
        16,
      );
    drawDraft();
  }
  editor.onpointerdown = (e) => {
    drawing = true;
    editor.setPointerCapture(e.pointerId);
    paint(e);
  };
  editor.onpointermove = (e) => {
    if (drawing) paint(e);
  };
  editor.onpointerup = editor.onpointercancel = () => (drawing = false);
  const draftHex = () =>
    Array.from(draft, (v) => v.toString(16).padStart(2, "0")).join("");
  bind("clearCanvas", () => {
    draft.fill(0);
    drawDraft();
  });
  bind("sendCanvas", async () => {
    await api("/api/pro/canvas", { hex: draftHex() });
    notice("画布已确认");
  });
  bind("saveCanvas", () => {
    if (navigator.userAgent.includes("AmadeusAndroid")) {
      location.href = "amadeus://export?hex=" + draftHex();
      return;
    }
    const url = URL.createObjectURL(
      new Blob([JSON.stringify({ width: 16, height: 16, hex: draftHex() })], {
        type: "application/json",
      }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = "amadeus-canvas.json";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 3000);
  });
  $("loadCanvas").onchange = async (e) => {
    try {
      const file = e.target.files[0];
      if (!file) return;
      if (file.size > 16384) throw Error("画布文件过大");
      const d = JSON.parse(await file.text());
      if (d.width !== 16 || d.height !== 16 || !/^[0-9a-f]{1536}$/i.test(d.hex))
        throw Error("需要 16×16 RGB JSON 画布");
      for (let i = 0; i < 768; i++)
        draft[i] = parseInt(d.hex.slice(i * 2, i * 2 + 2), 16);
      drawDraft();
      notice("画布已导入，点击“应用到灯板”即可显示");
    } catch (error) {
      notice(error.message);
    } finally {
      e.target.value = "";
    }
  };
  function openConnection() {
    if (navigator.userAgent.includes("AmadeusAndroid")) {
      location.href = "amadeus://settings";
      return;
    }
    $("serverUrl").value = location.protocol === "file:" ? "" : location.origin;
    $("connectionDialog").showModal();
  }
  bind("openConnection", openConnection);
  bind("connectionSettings", openConnection);
  bind("closeConnection", () => $("connectionDialog").close());
  $("serverForm").onsubmit = (e) => {
    e.preventDefault();
    try {
      const url = new URL($("serverUrl").value.trim());
      if (
        !["http:", "https:"].includes(url.protocol) ||
        url.username ||
        url.password
      )
        throw Error("请输入完整的 HTTP(S) 服务地址");
      location.assign(url.origin + "/");
    } catch (error) {
      notice(error.message);
    }
  };
  bind("runCeremony", async () => {
    await api("/api/ceremony", {});
    notice("已请求播放连接自检提示");
  });
  bind("refreshStatus", () => {
    lastGeneral = lastPro = 0;
    return poll();
  });
  bind("retryConnection", () => {
    pairedHttp.resetPairing();
    lastGeneral = lastPro = 0;
    return poll();
  });
  async function poll() {
    if (polling || document.hidden) return;
    polling = true;
    let stage = "service";
    try {
      const now = Date.now();
      if (!state.online || now - lastGeneral > 4000) {
        const s = await api("/api/status", undefined, "GET", 5000);
        state.general = s;
        connection(s);
        lastGeneral = now;
        if (!nativeMode) openSocket();
      }
      if (nativeMode) {
        $("status").textContent="APK 直连 ESP32：灯效、亮度、音量、倒计时和街机；AI、音乐和视觉需要电脑服务";
        if(state.board && state.page!=="settings" && !state.arcadeActive){
          stage="frame";renderFrame(await api("/api/pro/frame",undefined,"GET"));
        }
        lastError="";return;
      }
      stage = "features";
      if (now - lastPro > 1500) {
        const p = await api("/api/pro/status", undefined, "GET", 6000);
        state.vision = p.vision;
        $("status").textContent = JSON.stringify(p, null, 2);
        $("visionStatus").textContent = JSON.stringify(p.vision, null, 2);
        const running = p.vision?.running || phoneStream !== null;
        $("visionBadge").textContent = running ? "运行中" : "未启用";
        if (phoneStream) {
          $("visionSummary").textContent = `手机前置互动：${$("visionMode").value} · 实时传输中`;
        } else {
          $("visionSummary").textContent =
            p.vision?.error ||
            (p.vision?.running
              ? `互动方式：${p.vision.mode}${p.vision.fresh === false ? " · 暂无新鲜观测" : ""}`
              : "摄像头未启用");
        }
        if (!phoneStream && $("cameraStreamWrapper")) {
          if (p.vision?.running) {
            $("cameraStreamWrapper").style.display = "block";
            const img = $("cameraStreamImg");
            if (!img.src || img.src.indexOf("/api/pro/camera/feed") === -1) {
              const tok = getAccessToken();
          state.token = tok;
              img.src = `/api/pro/camera/feed?token=${encodeURIComponent(tok)}&t=${Date.now()}`;
            }
            if ($("cameraDetectionInfo")) {
              const obs = p.vision?.observation || {};
              if (obs.hand) {
                $("cameraDetectionInfo").textContent = obs.hand.pinch ? "✋ 捏合抓取" : "👆 食指追踪";
              } else if (obs.present) {
                $("cameraDetectionInfo").textContent = obs.identity ? `👤 识别: ${obs.identity}` : "👤 人脸就绪";
              } else {
                $("cameraDetectionInfo").textContent = "正在捕捉手势/人脸...";
              }
            }
          } else {
            $("cameraStreamWrapper").style.display = "none";
            $("cameraStreamImg").src = "";
          }
        }
        updateMusic(p.music);
        lastPro = now;
        if (state.page === "music" && libraryDirty) await loadLibrary();
      }
      stage = "frame";
      if (state.board && state.page !== "settings" && !state.arcadeActive) {
        const f = await api("/api/pro/frame", undefined, "GET", 6000);
        renderFrame(f);
      }
      lastError = "";
    } catch (error) {
      if (error.message !== lastError) {
        lastError = error.message;
      }
      $("chatStatus").textContent = error.message;
      if (stage === "service") {
        connection(null);
        state.socket?.close();
      } else if (stage === "frame") {
        if(error.message==="telemetry_busy")return;
        $("frameTag").textContent = "同步中";
        $("frameSource").textContent = "正在同步灯板画面…";
      } else {
        $("status").textContent = "功能状态暂不可用：" + error.message;
      }
    } finally {
      polling = false;
      clearTimeout(pollTimer);
      pollTimer = setTimeout(
        poll,
        state.online ? (state.page === "lights" ? 500 : 1000) : 4000,
      );
    }
  }
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      if (state.arcadeActive) releaseArcadeControls();
      clearInterval(arcadeHeartbeatTimer);
      clearTimeout(pollTimer);
      state.socket?.close();
    } else {
      lastGeneral = lastPro = 0;
      if (state.arcadeActive) startArcadeHeartbeat();
      poll();
    }
  });
  window.addEventListener("blur", () => { if (state.arcadeActive) releaseArcadeControls(); });
  window.addEventListener("pagehide", () => {
    if (state.arcadeActive) releaseArcadeControls();
    clearInterval(arcadeHeartbeatTimer);
    clearTimeout(pollTimer);
    state.socket?.close();
    cancelCalibration();
    dictation?.abort();
  });
  matrix2d($("homeMatrix"));
  matrix2d($("matrixCanvas"));
  drawDraft();
  route();
  connection(null);
  poll();
})();
