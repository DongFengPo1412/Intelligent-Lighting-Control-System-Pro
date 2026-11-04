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
  async function api(path, data, method = "POST", timeout = 15000) {
  let activeKeyMask = 0;

  function dispatchNativeUdp(host, port, message, timeoutMs) {
    if (window.AmadeusNative && typeof window.AmadeusNative.sendUdpAsync === "function") {
      return new Promise((resolve, reject) => {
        const cbId = "cb_" + Date.now() + "_" + Math.floor(Math.random() * 1000000);
        if (!window.__amadeusUdpCallbacks) window.__amadeusUdpCallbacks = {};
        const timer = setTimeout(() => {
          delete window.__amadeusUdpCallbacks[cbId];
          reject(new Error("ESP32 UDP 响应超时 (1500ms)"));
        }, timeoutMs + 300);
        window.__amadeusUdpCallbacks[cbId] = (replyStr) => {
          clearTimeout(timer);
          try {
            const parsed = JSON.parse(replyStr);
            resolve(parsed);
          } catch (e) {
            reject(new Error("ESP32 UDP 报文解析失败: " + e.message));
          }
        };
        try {
          window.AmadeusNative.sendUdpAsync(host, port, message, timeoutMs, cbId);
        } catch (e) {
          clearTimeout(timer);
          delete window.__amadeusUdpCallbacks[cbId];
          reject(e);
        }
      });
    } else if (window.AmadeusNative && typeof window.AmadeusNative.sendUdp === "function") {
      return new Promise((resolve, reject) => {
        try {
          const replyStr = window.AmadeusNative.sendUdp(host, port, message, timeoutMs);
          const parsed = JSON.parse(replyStr);
          resolve(parsed);
        } catch (e) {
          reject(new Error("ESP32 UDP 同步请求失败: " + e.message));
        }
      });
    }
    return Promise.reject(new Error("未检测到原生 UDP 支持"));
  }

  async function api(path, data, method = "POST", timeout = 15000) {
    if (location.protocol === "file:") {
      if (window.AmadeusNative && path.startsWith("/api/arcade")) {
        const host = localStorage.getItem("esp32_ip") || "192.168.4.1";
        const port = 8888;
        const reqId = "req_" + Date.now() + "_" + Math.floor(Math.random() * 10000);
        let cmd = null;

        // 统一解析 path-based 与 action-based 请求
        let action = "";
        let gameId = undefined;
        let keyName = undefined;
        let isDown = false;

        if (path === "/api/arcade" && data && data.action) {
          action = String(data.action).toLowerCase();
          gameId = data.game_id;
          keyName = data.key;
          isDown = data.down !== undefined ? Boolean(data.down) : Boolean(data.is_down);
        } else if (path.startsWith("/api/arcade/")) {
          action = path.replace("/api/arcade/", "").toLowerCase();
          if (data) {
            gameId = data.game_id;
            keyName = data.key;
            isDown = data.down !== undefined ? Boolean(data.down) : Boolean(data.is_down);
          }
        }

        if (action === "select") {
          cmd = { cmd: "arcade", action: "select", game_id: Number(gameId) };
        } else if (action === "start") {
          cmd = { cmd: "arcade", action: "start" };
        } else if (action === "pause") {
          cmd = { cmd: "arcade", action: "pause" };
        } else if (action === "resume") {
          cmd = { cmd: "arcade", action: "resume" };
        } else if (action === "reset") {
          cmd = { cmd: "arcade", action: "reset" };
        } else if (action === "stop" || action === "exit") {
          activeKeyMask = 0;
          cmd = { cmd: "arcade", action: "exit" };
        } else if (action === "key" || action === "input") {
          const KEY_BITS = { left: 1, right: 2, up: 4, down: 8, a: 16, b: 32, start: 64, select: 128 };
          const mask = KEY_BITS[(keyName || "").toLowerCase()] || 0;
          if (isDown) {
            activeKeyMask |= mask;
          } else {
            activeKeyMask &= ~mask;
          }
          cmd = { cmd: "arcade", action: "input", down: activeKeyMask, pressed: isDown ? mask : 0 };
        } else if (action === "heartbeat" || action === "status") {
          cmd = { cmd: "arcade", action: "heartbeat" };
        } else if (action === "frame") {
          cmd = { cmd: "frame" };
        }

        if (cmd) {
          const envelope = { request_id: reqId, command: JSON.stringify(cmd) };
          const rawReply = await dispatchNativeUdp(host, port, JSON.stringify(envelope), 1500);

          if (!rawReply || typeof rawReply !== "object") {
            throw new Error("ESP32 UDP 返回了空数据或非 JSON 格式");
          }
          if (rawReply.status === "error") {
            throw new Error(rawReply.error || "ESP32 硬件响应错误");
          }

          // 结构转换：使 Web 界面 HUD 和渲染引擎真实获取 ESP32 状态
          const result = {
            status: "ok",
            source: "esp32_hardware",
            request_id: rawReply.request_id || reqId,
            mode: rawReply.mode,
          };

          if (rawReply.arcade) {
            result.game_status = {
              active: Boolean(rawReply.arcade.active),
              game_id: Number(rawReply.arcade.game_id),
              name: String(rawReply.arcade.name || ""),
              state: Number(rawReply.arcade.state),
              score: Number(rawReply.arcade.score),
              high_score: Number(rawReply.arcade.high_score),
              lives: Number(rawReply.arcade.lives),
              progress: Number(rawReply.arcade.progress),
              control_type: Number(rawReply.arcade.control_type),
            };
            result.arcade = rawReply.arcade;
          }

          if (rawReply.pixels || rawReply.hex) {
            result.hex = rawReply.hex || rawReply.pixels;
            result.pixels = rawReply.pixels || rawReply.hex;
            result.frame_id = rawReply.frame_id;
            result.source = rawReply.frame_source || "esp32_hardware";
          }

          return result;
        }
      }
      throw Error("尚未连接电脑服务，请打开连接设置");
    }
    const abort = new AbortController(),
      timer = setTimeout(() => abort.abort(), timeout);
    try {
      const r = await fetch(path, {
        method,
        headers:
          data === undefined ? {} : { "Content-Type": "application/json" },
        body: data === undefined ? undefined : JSON.stringify(data),
        signal: abort.signal,
        cache: "no-store",
      });
      const v = await r.json();
      if (!r.ok || v.status === "error")
        throw Error(v.error || v.message || `请求失败 (${r.status})`);
      return v;
    } catch (e) {
      if (e.name === "AbortError")
        throw Error(
          method === "GET"
            ? "连接超时，请检查电脑服务"
            : "等待回执超时；操作可能已执行，请查看设备状态后再操作",
        );
      throw e;
    } finally {
      clearTimeout(timer);
    }
  }
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
    if ([19, 20].includes(f.mode)) state.game = "snake";
    else if ([21, 22].includes(f.mode)) state.game = "tetris";
    else if (state.game === "mario") {
      /* 马里奥处于主动运行状态，不因底层环境模式上报而被动停止 */
    } else {
      state.game = null;
    }
    $("gameState").textContent = state.game
      ? state.game === "snake"
        ? "贪吃蛇"
        : state.game === "tetris"
          ? "俄罗斯方块"
          : "超级马里奥"
      : "选择游戏开始";
    $$("[data-game]").forEach((b) =>
      b.classList.toggle("active", b.dataset.game === state.game),
    );
    if ($("marioContainer")) {
      $("marioContainer").style.display = state.game === "mario" ? "flex" : "none";
    }
    if ($("gamepad")) {
      $("gamepad").style.display = state.game === "mario" ? "none" : "flex";
    }
    if (f.brightness != null) syncRange("brightness", f.brightness, " / 60");
    $("countdownState").textContent =
      f.mode === 25 ? "计时画面显示中" : "尚未开始 / 已结束";
  }
  async function setMode(mode) {
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
      const r = await fetch(
        "/api/pro/music-upload?visual=" +
          encodeURIComponent($("musicVisual").value),
        { method: "POST", body: file },
      );
      const v = await r.json();
      if (!r.ok) throw Error(v.error || "上传失败");
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
  let arcadeHeartbeatTimer = null;

  function updateGamepadLayout(controlType, gid) {
    const tapStage = $("arcadeTapStage");
    const dpad = $("arcadeDpad");
    const actions = $("arcadeActions");
    const versus = $("arcadeVersusStage");
    const keyUp = $("marioKeyUp");
    const keyDown = $("marioKeyDown");
    const keyLeft = $("marioKeyLeft");
    const keyRight = $("marioKeyRight");
    const keyB = $("marioKeyB");
    const btnA_sub = document.querySelector("#marioKeyA .btn-sub");
    const btnB_sub = document.querySelector("#marioKeyB .btn-sub");
    const tapBtn = $("arcadeTapBig");

    // 重置所有区域可见性
    if (tapStage) tapStage.style.display = "none";
    if (dpad) dpad.style.display = "grid";
    if (actions) actions.style.display = "flex";
    if (versus) versus.style.display = "none";
    if (keyUp) keyUp.style.visibility = "visible";
    if (keyDown) keyDown.style.visibility = "visible";
    if (keyLeft) keyLeft.style.visibility = "visible";
    if (keyRight) keyRight.style.visibility = "visible";
    if (keyB) keyB.style.display = "inline-flex";

    const ct = Number(controlType !== undefined ? controlType : 3);
    const gNum = Number(gid || state.arcadeGid || 1);

    if (ct === 0) {
      // CTRL_TAP_SINGLE (Flappy Bird #009, Stack #010)
      if (tapStage) tapStage.style.display = "flex";
      if (dpad) dpad.style.display = "none";
      if (actions) actions.style.display = "none";
      if (tapBtn) {
        tapBtn.textContent = gNum === 9 ? "🕊️ 拍翅轻点 (TAP)" : "🧱 切削放置 (TAP)";
      }
    } else if (ct === 1) {
      // CTRL_TWO_BUTTON (Breakout #021, Highway Racer #074, Doodle Jump #002)
      if (keyUp) keyUp.style.visibility = "hidden";
      if (keyDown) keyDown.style.visibility = "hidden";
      if (actions) actions.style.display = "none";
    } else if (ct === 2) {
      // CTRL_DPAD_4WAY (Snake #033, Pacman #034, Sokoban #054, Frogger #097)
      if (actions) actions.style.display = "none";
    } else if (ct === 3) {
      // CTRL_ARCADE_AB (Mario #001, Space Invaders #026, Bomberman #038, Tetris #041)
      if (gNum === 41) {
        if (btnA_sub) btnA_sub.textContent = "旋转";
        if (btnB_sub) btnB_sub.textContent = "软降";
      } else if (gNum === 38) {
        if (btnA_sub) btnA_sub.textContent = "炸弹";
        if (btnB_sub) btnB_sub.textContent = "引爆";
      } else if (gNum === 26) {
        if (btnA_sub) btnA_sub.textContent = "激光";
        if (btnB_sub) btnB_sub.textContent = "防御";
      } else {
        if (btnA_sub) btnA_sub.textContent = "跳跃";
        if (btnB_sub) btnB_sub.textContent = "冲刺";
      }
    } else if (ct === 5) {
      // CTRL_VERSUS_DUAL (Pong #020)
      if (dpad) dpad.style.display = "none";
      if (actions) actions.style.display = "none";
      if (versus) versus.style.display = "flex";
    }
  }

  function updateArcadeHud(status) {
    if (!status) return;
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
      const cType = Number(status.control_type || 3);
      const ctNames = { 0: "CTRL_TAP_SINGLE", 1: "CTRL_TWO_BUTTON", 2: "CTRL_DPAD_4WAY", 3: "CTRL_ARCADE_AB", 5: "CTRL_VERSUS_DUAL" };
      $("arcadeControlStat").textContent = ctNames[cType] || `TYPE_${cType}`;
    }

    // 专属动态手柄布局适配
    updateGamepadLayout(status.control_type, status.game_id || state.arcadeGid);

    // 暂停按钮文本动态更新
    if ($("arcadePauseBtn")) {
      $("arcadePauseBtn").textContent = stCode === 2 ? "▶ 继续游戏" : "⏸ 暂停游戏";
    }
  }

  async function launchArcadeGame(gameId) {
    const idMap = {
      mario: 1, snake: 33, tetris: 41,
      "001": 1, "033": 33, "041": 41,
      1: 1, 33: 33, 41: 41
    };
    const gid = idMap[gameId] || parseInt(gameId, 10);
    if (!gid) {
      notice("未知的街机游戏编号");
      return;
    }

    const titleMap = {
      1: "[#001] 超级马里奥 (Super Mario Bros.)",
      9: "[#009] 飞翔小鸟 (Flappy Bird 16)",
      10: "[#010] 堆叠大师 (Stack Master)",
      20: "[#020] 双人乒乓 (Pong 1972)",
      21: "[#021] 经典打砖块 (Breakout 1976)",
      26: "[#026] 太空侵略者 (Space Invaders 1978)",
      33: "[#033] 经典贪吃蛇 (Classic Snake)",
      34: "[#034] 吃豆人 (Pac-Man 1980)",
      38: "[#038] 炸弹人 (Bomberman 1983)",
      41: "[#041] 俄罗斯方块 (Tetris)",
      54: "[#054] 推箱子 (Sokoban 1982)",
      74: "[#074] 变道赛车 (Highway Racer 1979)",
      97: "[#097] 青蛙过河 (Frogger 1981)",
    };

    if ($("arcadeGameTitle")) $("arcadeGameTitle").textContent = titleMap[gid] || `街机游戏 #${gid}`;
    if ($("gameState")) $("gameState").textContent = titleMap[gid] || `街机 #${gid}`;

    // 展现统一街机容器
    if ($("marioContainer")) {
      $("marioContainer").style.display = "flex";
      try { $("marioContainer").scrollIntoView({ behavior: "smooth", block: "nearest" }); } catch (_) {}
    }
    if ($("gamepad")) $("gamepad").style.display = "none";

    // 选卡按钮高亮
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

  // 绑定专属街机选卡按钮
  $$("[data-arcade-id]").forEach((btn) => {
    btn.onclick = (e) => {
      e.preventDefault();
      launchArcadeGame(btn.dataset.arcadeId);
    };
  });

  // 兼容旧版 data-game 选择按钮
  $$("[data-game]").forEach((b) => {
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
  function bindArcadeTouchKey(btn, keyName) {
    if (!btn) return;
    let isPressed = false;

    const press = (e) => {
      e?.preventDefault?.();
      if (isPressed) return;
      isPressed = true;
      btn.classList.add("pressed", "active");
      if (navigator.vibrate) {
        try { navigator.vibrate(10); } catch (_) {}
      }
      api("/api/arcade", { action: "key", key: keyName, down: true }).catch(() => {});
    };

    const release = (e) => {
      e?.preventDefault?.();
      if (!isPressed) return;
      isPressed = false;
      btn.classList.remove("pressed", "active");
      api("/api/arcade", { action: "key", key: keyName, down: false }).catch(() => {});
    };

    btn.addEventListener("touchstart", press, { passive: false });
    btn.addEventListener("touchend", release, { passive: false });
    btn.addEventListener("touchcancel", release, { passive: false });
    btn.addEventListener("mousedown", press);
    btn.addEventListener("mouseup", release);
    btn.addEventListener("mouseleave", release);
  }

  $$("[data-mario-key]").forEach((btn) => {
    bindArcadeTouchKey(btn, btn.dataset.marioKey);
  });

  if ($("pongAiToggleBtn")) {
    $("pongAiToggleBtn").onclick = async (e) => {
      e.preventDefault();
      try {
        await api("/api/arcade", { action: "key", key: "start", down: true });
        setTimeout(() => api("/api/arcade", { action: "key", key: "start", down: false }).catch(() => {}), 80);
        notice("已切换 Pong 对战模式 (单人 AI / 本地双人)");
      } catch (err) {
        notice("Pong 模式切换失败: " + err.message);
      }
    };
  }

  // 顶部与操作栏功能按键
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

  // 键盘事件全局适配 (WASD / 十字键 / 空格 / Shift / Enter / R)
  window.addEventListener("keydown", (e) => {
    if (!state.arcadeActive || document.activeElement?.tagName === "INPUT" || document.activeElement?.tagName === "TEXTAREA") return;
    const keyMap = {
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
    if (!state.arcadeActive || document.activeElement?.tagName === "INPUT" || document.activeElement?.tagName === "TEXTAREA") return;
    const keyMap = {
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
  setInterval(async () => {
    if (state.arcadeActive && $("marioCanvas") && $("marioContainer")?.style.display !== "none") {
      try {
        const res = await api("/api/arcade/frame", undefined, "GET", 1500);
        if (res && res.hex && $("marioCanvas")) {
          drawMarioFrame($("marioCanvas"), res.hex);
        }
        if (res && res.status) {
          updateArcadeHud(res.status);
        }
      } catch (_) {}
    }
  }, 66);
  $("difficulty").oninput = () => {
    $("difficultyValue").textContent =
      Number($("difficulty").value) < 0.35
        ? "轻松"
        : Number($("difficulty").value) > 0.7
          ? "挑战"
          : "中等";
  };
  bind("setDifficulty", async () => {
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
        openSocket();
      }
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
      clearTimeout(pollTimer);
      state.socket?.close();
    } else {
      lastGeneral = lastPro = 0;
      poll();
    }
  });
  window.addEventListener("pagehide", () => {
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
