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
    [19, "贪吃蛇", "再来一局", "interactive", "⌁"],
    [20, "蛇的结算", "游戏结算画面", "interactive", "⚑"],
    [21, "俄罗斯方块", "方块落下的瞬间", "interactive", "▦"],
    [22, "方块结算", "游戏结算画面", "interactive", "⚑"],
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
    (n === 25 ? "专注倒计时" : "尚未读取");
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
  const arcadeTransport = new window.ArcadeTransport(nativeMode ? window.arcadeNativeExchange(window.AmadeusNative) :
    async (command, id, policy) => {
      const path = command.cmd === "frame" ? "/api/arcade/frame" : "/api/arcade";
      const data = command.cmd === "frame" ? undefined : {...command};
      const reply = await httpApi(path,data,data ? "POST" : "GET",3000);
      if (!reply || reply.status === "error") throw Error(reply?.error || "无效服务回执");
      return reply;
    });
  async function api(path, data, method = "POST", timeout = 15000) {
    if (path === "/api/arcade" || path.startsWith("/api/arcade/")) return arcadeTransport.call(path,data);
    if (nativeMode) {
      if (path === "/api/status") {
        const r=await window.arcadeNativeExchange(window.AmadeusNative)({cmd:"status"},"status_"+Date.now(),{timeout:400,retries:0});
        return {...r,status:"online",is_connected:true,simulated:false};
      }
      throw Error("此功能需要电脑服务；街机可直接连接灯板");
    }
    return httpApi(path,data,method,timeout);
  }
  const pairedHttp = window.createPairedHttp({
    fetch: (...args) => fetch(...args), storage: sessionStorage,
    prompt: () => window.prompt("请输入电脑服务的配对令牌（见电脑端 web-access-token 文件）")
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
      setTimeout(() => launchMarioGame(), 80);
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
    state.online = !!s;
    state.simulated = !!s?.simulated;
    state.board = !!s?.is_connected;
    const text = !s
      ? "电脑服务未连接"
      : s.simulated
        ? "离线模拟 · 无实物输出"
        : s.is_connected
          ? "设备已连接"
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
      ? "当前为模拟服务：可预览操作流程，不会控制灯板、播放声音或打开摄像头。"
      : state.online
        ? "电脑服务在线，灯板尚未连接。请检查灯板电源与 Wi-Fi。"
        : "电脑服务未连接，请在连接设置中检查地址和网络。";
    $("serverStatus").textContent = state.online ? "服务在线" : "离线";
    $("serverAddress").textContent =
      location.protocol === "file:" ? "尚未设置" : location.origin;
    $("boardConnection").textContent = s?.simulated
      ? "模拟设备"
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
      ? "模拟服务，不进行真实语音识别"
      : wakeReady
        ? "对板载麦克风说“助手”即可开始"
        : "可发送文字；板载语音状态见设置";
    $("sendChat").disabled = !state.online || !!state.ownChat;
    markHardware();
    if (!state.board) {
      for (const id of ["previousMusic", "nextMusic", "stopMusic"])
        $(id).disabled = true;
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
      ? "模拟帧"
      : f.frame_source === "board"
        ? "灯板回读"
        : f.frame_source || "设备回读";
    $("frameTag").textContent = state.simulated ? "模拟预览" : "实时回读";
    $("homeFrameEmpty").hidden = $("lightFrameEmpty").hidden = true;
    $("frameSource").textContent = `${source} · 帧 ${f.frame_id ?? "—"}`;
    $("modeName").textContent = $("currentModeLabel").textContent = modeName(
      f.mode,
    );
    $$("[data-mode]").forEach((b) => {
      b.classList.toggle("active", Number(b.dataset.mode) === f.mode);
      b.setAttribute("aria-pressed", String(Number(b.dataset.mode) === f.mode));
    });
    if (state.arcadeActive) state.game = "arcade";
    else if ([19, 20].includes(f.mode)) state.game = "snake";
    else if ([21, 22].includes(f.mode)) state.game = "tetris";
    else if (state.game === "mario") {
      /* 马里奥处于主动运行状态，不因底层环境模式上报而被动停止 */
    } else {
      state.game = null;
    }
    $("gameState").textContent = state.game
      ? state.game === "arcade"
        ? ARCADE_TITLE_MAP[state.arcadeGid] || "街机"
        : state.game === "snake"
        ? "贪吃蛇"
        : state.game === "tetris"
          ? "俄罗斯方块"
          : "超级马里奥"
      : "选择游戏开始";
    $$("[data-game]").forEach((b) =>
      b.classList.toggle("active", state.arcadeActive ? Number(b.dataset.arcadeId)===state.arcadeGid : b.dataset.game === state.game),
    );
    if ($("marioContainer")) {
      $("marioContainer").style.display = state.arcadeActive || state.game === "mario" ? "flex" : "none";
    }
    if ($("gamepad")) {
      $("gamepad").style.display = state.arcadeActive || state.game === "mario" ? "none" : "flex";
    }
    if (f.brightness != null) syncRange("brightness", f.brightness, " / 60");
    $("countdownState").textContent =
      f.mode === 25 ? "计时画面显示中" : "尚未开始 / 已结束";
  }
  async function setMode(mode) {
    if (state.arcadeActive) {
      await api("/api/arcade", {action:"exit"});
      state.arcadeActive=false;state.game=null;
      clearInterval(arcadeHeartbeatTimer);
      if ($("marioContainer")) $("marioContainer").style.display="none";
    }
    if (state.game === "mario") {
      await api("/api/game", { game: "mario", action: "stop" }).catch(() => {});
      state.game = null;
      if ($("marioContainer")) $("marioContainer").style.display = "none";
      if ($("gamepad")) $("gamepad").style.display = "flex";
    }
    await api("/api/mode", { mode });
    notice(
      `${modeName(mode)} · ${state.simulated ? "模拟操作已提交" : "设备已确认"}`,
    );
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
        if (v.type === "mario_frame") {
          if ($("marioCanvas") && v.hex) {
            drawMarioFrame($("marioCanvas"), v.hex);
          }
          if (v.status) {
            updateMarioHud(v.status);
          }
        }
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
      : current
        ? "PLAYBACK STOPPED"
        : "READY WHEN YOU ARE";
    document
      .querySelector(".music-player")
      .classList.toggle("playing", !!m.running);
    $("musicProgress").max = Math.max(1, m.duration || 0);
    $("musicProgress").value = m.position || 0;
    $("musicTime").textContent = time(m.position) + " / " + time(m.duration);
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
    $("stopMusic").disabled = !state.board || !m.running;
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
  const MARIO_STATES = ["标题画面", "准备中", "游戏中", "已暂停", "死亡", "结束", "通关"];

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

  function updateMarioHud(st) {
    if (!st) return;
    if ($("marioStateTag")) $("marioStateTag").textContent = MARIO_STATES[st.state] || `State ${st.state}`;
    if ($("marioScoreStat")) $("marioScoreStat").textContent = "得分: " + String(st.score || 0).padStart(5, "0");
    if ($("marioLivesStat")) $("marioLivesStat").textContent = "❤️ ×" + (st.lives ?? 3);
    if ($("marioCoinsStat")) $("marioCoinsStat").textContent = "🪙 ×" + String(st.coins || 0).padStart(2, "0");
    if ($("marioProgressStat")) $("marioProgressStat").textContent = "🏁 " + (st.progress ?? 0) + "%";
    if ($("marioProgFill")) $("marioProgFill").style.width = Math.min(100, Math.max(0, st.progress ?? 0)) + "%";
    if ($("marioSyncBadge")) {
      $("marioSyncBadge").textContent = state.board ? "🟢 实时同步中 (静音)" : "📱 触屏本地模式";
      $("marioSyncBadge").style.color = state.board ? "#35c759" : "#ffd23f";
    }
    if ($("marioStartBtn")) {
      if (st.state === 0) {
        $("marioStartBtn").innerHTML = "▶ <strong>点击开始游戏</strong>";
        $("marioStartBtn").classList.add("primary");
      } else if (st.state === 1) {
        $("marioStartBtn").innerHTML = "⏳ 关卡载入中...";
        $("marioStartBtn").classList.remove("primary");
      } else if (st.state === 2) {
        $("marioStartBtn").innerHTML = "⏸ 暂停游戏";
        $("marioStartBtn").classList.remove("primary");
      } else if (st.state === 3) {
        $("marioStartBtn").innerHTML = "▶ 继续游戏";
        $("marioStartBtn").classList.add("primary");
      } else if (st.state === 4 || st.state === 5) {
        $("marioStartBtn").innerHTML = "↺ 重新开始";
        $("marioStartBtn").classList.add("primary");
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
      btn.title=available?"已接入软件，实机待验":"计划项目，尚未接入";
      btn.dataset.available=String(available);
      const matchCat = cat === "all" || btn.dataset.arcadeCat === cat;
      const hay = `${btn.dataset.arcadeId} ${gid} ${item ? item[2] + " " + item[3] : btn.textContent}`.toLowerCase();
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
    const specificHelp={
      ...Object.fromEntries(Object.entries(window.ARCADE_B3_RULES||{}).map(([id,v])=>[id,v.help])),
      35:"方向键挖土、收集8颗青色宝石，再进入右下出口；可水平推石，提防头顶落石。三档改变落石速度和限时。",
      55:"方向键移动光标，A 旋转镜面并进入安全预览；B 确认发射/停止。只有发射才会充能或引爆炸弹；暂停与重新开局使用上方按钮。共四关。",
      57:"A 选择下一辆车，B 上一辆；白点标示当前车辆。横车用左右，竖车用上下；让红车到达右侧出口。移动次数有限。",
      58:"先编程：↑追加前进，←追加左转，→追加右转，↓追加等待；A 执行，B 撤销末条（执行时中止）。踩黄开关打开红门，再到绿出口。顶行显示指令，白点为执行位置。",
      81:"沿蓝色安全区移动；A 开启画线，再进入空白区并回到安全区闭合。粉色敌人碰到黄线或自己折返碰线会失败；圈占50/60/70%获胜。",
      98:"左右旋转，A 或 ↑ 喷气；黄色顶条是燃料。缓慢、近乎竖直地落在绿色平台，岩地或高速接触会坠毁。支持转向与喷气同时按住。",
      17:"四轨对应 1/2/3/4 或 ←/↓/↑/→；在下方判定线击中音符。三拍预滚，完成64音符；乱按会扣容错。音效会让路于语音/音乐/收音。",
      85:"方向键移动光标，A 给附近行走旅鼠分配技能，B 按 阻挡→搭桥→挖掘 循环；默认挖掘。顶端亮点提示所选技能；三关均须达到救援目标。",
      92:"方向键移动刀光，A/B 挥刀，也可在灯板预览上划动；挥刀存在短冷却。切够40个水果，避开红色脉冲炸弹。",
      95:"左右绕核心移动白点，穿过墙壁缺口；通过30道墙或存活45秒获胜。"
    };
    if(help)help.textContent=specificHelp[gNum] || (gNum===20
      ? "P1 使用 ↑/↓；本地双人模式的 P2 使用 A/B（键盘 J/K）。AI/双人切换保留比分与暂停状态。"
      : gNum===1
        ? "手机支持多点触控：左右移动、A 跳跃、B 加速；电脑使用方向键、空格和 Shift。"
        : "按当前卡带的手柄操作；支持多点触控和独立松键。电脑可使用方向键、J/K 与空格。");

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
      if (keyUp) keyUp.style.visibility = "hidden";
      if (keyDown) keyDown.style.visibility = "hidden";
      if (actions) actions.style.display = "none";
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
    const b3=window.ARCADE_B3_RULES?.[gNum];
    if(b3 && ct===3){if(btnA_sub)btnA_sub.textContent=b3.a||"确认";if(btnB_sub)btnB_sub.textContent=b3.b||"";if(keyB)keyB.style.display=b3.b?"inline-flex":"none";}
    if(b3 && ct===0 && tapBtn)tapBtn.textContent=b3.a;

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
      notice("卡带设置已确认"+ (reply.simulated?"（模拟模式无实体声音）":""));
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
      $("arcadeSettingsStatus").textContent=(status.difficulty_supported?"此卡带支持三档实际难度；待机或结算时调整。":"此卡带尚未接入统一难度。")+
        (status.simulated?" 模拟模式仅记录音效事件。":" 语音、音乐、收音优先，游戏声音可能保持静音。");
    }
    if (status.game_id===20 && [1,2].includes(status.player_count)) {
      state.pongPlayers=status.player_count;
      const toggle=$("pongAiToggleBtn");
      if(toggle)toggle.textContent=status.player_count===1?"单人 AI · 切为双人":"本地双人 · 切为 AI";
    }
    const stateLabels = {
      0: "TITLE 待机",
      1: "PLAYING 游玩中",
      2: "PAUSED 已暂停",
      3: "GAMEOVER 结算",
      4: "VICTORY 胜利",
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
        0: "CTRL_TAP_SINGLE",
        1: "CTRL_TWO_BUTTON",
        2: "CTRL_DPAD_4WAY",
        3: "CTRL_ARCADE_AB",
        4: "CTRL_MULTI_TRACK",
        5: "CTRL_VERSUS_DUAL"
      };
      $("arcadeControlStat").textContent = ctNames[cType] || `TYPE_${cType}`;
    }

    updateGamepadLayout(status.control_type, status.game_id || state.arcadeGid);

    if ($("arcadePauseBtn")) {
      $("arcadePauseBtn").textContent = stCode === 2 ? "▶ 继续游戏" : "⏸ 暂停游戏";
    }
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
    if ($("arcadeGameTitle")) $("arcadeGameTitle").textContent = gameTitle;
    if ($("gameState")) $("gameState").textContent = gameTitle;

    if ($("marioContainer")) {
      $("marioContainer").style.display = "flex";
      try { $("marioContainer").scrollIntoView({ behavior: "smooth", block: "nearest" }); } catch (_) {}
    }
    if ($("gamepad")) $("gamepad").style.display = "none";

    $$("[data-arcade-id]").forEach((btn) => {
      btn.classList.toggle("active", parseInt(btn.dataset.arcadeId, 10) === gid);
    });
    $$("[data-game]").forEach((btn) => {
      btn.classList.toggle("active", idMap[btn.dataset.game] === gid);
    });

    try {
      const res = await api("/api/arcade", { action: "select", game_id: gid });
      if (res && res.status === "ok") {
        state.arcadeActive = true;
        state.arcadeGid = gid;
        state.game = "arcade";

        const badge = $("marioSyncBadge");
        if (badge) {
          if (res.source === "esp32_hardware") {
            badge.textContent = "🟢 ESP32 硬件模式 (唯一权威)";
            badge.style.backgroundColor = "rgba(34, 197, 94, 0.2)";
            badge.style.color = "#22c55e";
          } else {
            badge.textContent = "🟡 本地模拟器测试模式";
            badge.style.backgroundColor = "rgba(234, 179, 8, 0.2)";
            badge.style.color = "#eab308";
          }
        }
        updateArcadeHud(res.game_status);
        startArcadeHeartbeat();
        notice(`已成功载入街机卡带 #${String(gid).padStart(3, "0")}`);
      } else {
        throw new Error(res?.message || res?.error || "载入游戏失败");
      }
    } catch (e) {
      notice(`街机选卡失败: ${e.message}`);
      const badge = $("marioSyncBadge");
      if (badge) {
        badge.textContent = "🔴 设备离线 / 选卡失败";
        badge.style.backgroundColor = "rgba(239, 68, 68, 0.2)";
        badge.style.color = "#ef4444";
      }
    }
  }

  function startArcadeHeartbeat() {
    if (arcadeHeartbeatTimer) clearInterval(arcadeHeartbeatTimer);
    arcadeHeartbeatTimer = setInterval(async () => {
      if (!state.arcadeActive) {
        clearInterval(arcadeHeartbeatTimer);
        return;
      }
      try {
        const hb = await api("/api/arcade", { action: "heartbeat" });
        if (hb && hb.game_status) {
          updateArcadeHud(hb.game_status);
        }
      } catch (err) {
        const badge = $("marioSyncBadge");
        if (badge && state.arcadeActive) {
          badge.textContent = "⚠️ 连接抖动 / 自动安全暂停";
          badge.style.backgroundColor = "rgba(239, 68, 68, 0.2)";
          badge.style.color = "#ef4444";
        }
      }
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
    return arcadeTransport.suspend();
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
      if (navigator.vibrate) try { navigator.vibrate(12); } catch (_) {}
      if (arcadeHeartbeatTimer) clearInterval(arcadeHeartbeatTimer);
      await api("/api/arcade", { action: "stop" }).catch(() => {});
      state.arcadeActive = false;
      state.game = null;
      if ($("gameState")) $("gameState").textContent = "选择游戏开始";
      if ($("marioContainer")) $("marioContainer").style.display = "none";
      if ($("gamepad")) $("gamepad").style.display = "flex";
      $$("[data-arcade-id]").forEach((btn) => btn.classList.remove("active"));
      $$("[data-game]").forEach((btn) => btn.classList.remove("active"));
      notice("已安全退出街机系统");
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

  // 15 FPS 实时画布回读与 HUD 同步 (严密对齐硬件帧源)
  let arcadeFrameBusy=false;
  setInterval(async () => {
    if (!arcadeFrameBusy && !document.hidden && state.arcadeActive && $("marioCanvas") && $("marioContainer")?.style.display !== "none") {
      try {
        arcadeFrameBusy=true;
        const res = await api("/api/arcade/frame", undefined, "GET", 1500);
        if (res && res.hex && $("marioCanvas")) {
          drawMarioFrame($("marioCanvas"), res.hex);
        }
        if (res?.game_status || (res?.status && typeof res.status === "object")) updateArcadeHud(res.game_status || res.status);
      } catch (_) {} finally { arcadeFrameBusy=false; }
    }
  }, 100);
  $("difficulty").oninput = () => {
    $("difficultyValue").textContent =
      Number($("difficulty").value) < 0.35
        ? "轻松"
        : Number($("difficulty").value) > 0.7
          ? "挑战"
          : "中等";
  };
  bind("setDifficulty", async () => {
    if(state.arcadeActive)throw Error("当前街机卡带尚未接入此全局难度设置，需后续逐款实现");
    await api("/api/pro/difficulty", {
      level: Number($("difficulty").value),
      adaptive: $("adaptive").checked,
    });
    notice("难度已更新");
  });
  bind("visionStart", async () => {
    const res = await api("/api/pro/vision", {
      enabled: true,
      mode: $("visionMode").value,
      camera: Number($("camera").value),
    });
    if (res && res.error) {
      notice("摄像头启动提示: " + res.error);
    } else {
      notice(
        state.simulated
          ? "模拟视觉流程已提交，不启用摄像头"
          : "已请求启用电脑摄像头，正在接入观测流",
      );
    }
    lastPro = 0;
    setTimeout(() => poll(), 500);
  });
  bind("visionStop", async () => {
    await api("/api/pro/vision", { enabled: false });
    cancelCalibration();
    lastPro = 0;
  });
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
      : "校准拟合完成；独立定位精度需实际验证";
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
      throw Error("当前没有新鲜的人脸／虹膜观测");
    samples.push([o.iris_x, o.iris_y, ...targets[samples.length]]);
    if (samples.length === 9) {
      const r = await api("/api/pro/calibrate", { samples });
      notice(
        `拟合误差 ${Number(r.rms_training_error).toFixed(4)}；独立精度尚未测量`,
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
      notice("草稿已导入，尚未应用到灯板");
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
      if (nativeMode) { $("status").textContent="APK 直连 ESP32；语音、音乐和视觉需要电脑服务"; return; }
      stage = "features";
      if (now - lastPro > 1500) {
        const p = await api("/api/pro/status", undefined, "GET", 6000);
        state.vision = p.vision;
        $("status").textContent = JSON.stringify(p, null, 2);
        $("visionStatus").textContent = JSON.stringify(p.vision, null, 2);
        $("visionBadge").textContent = p.vision?.running ? "运行中" : "未启用";
        $("visionSummary").textContent =
          p.vision?.error ||
          (p.vision?.running
            ? `互动方式：${p.vision.mode}${p.vision.fresh === false ? " · 暂无新鲜观测" : ""}`
            : "摄像头未启用");
        updateMusic(p.music);
        lastPro = now;
        if (state.page === "music" && libraryDirty) await loadLibrary();
      }
      stage = "frame";
      if (state.board && state.page !== "settings") {
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
        connection({ ...state.general, is_connected: false });
        $("frameSource").textContent = "帧回读失败：" + error.message;
        lastGeneral = 0;
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
