/* Shared arcade contract. Native mode never falls back to HTTP or simulation. */
"use strict";
(function (root) {
  const KEYS = Object.freeze({left:1,right:2,up:4,down:8,a:16,b:32,start:64,select:128});
  const IDS = new Set([1, 2, 3, 4, 5, 6, 9, 10, 14, 15, 16, 17, 18, 19, 20, 21, 22, 26, 27, 28, 29, 30, 31, 33, 34, 38, 40, 41, 42, 43, 44, 45, 51, 52, 53, 54, 55, 62, 63, 64, 65, 66, 67, 72, 73, 74, 75, 76, 83, 84, 85, 86, 87, 88, 92, 93, 94, 95, 97]);
  const ACTIONS = new Set(["select","start","pause","resume","reset","exit","input","heartbeat","status","frame","players","config"]);
  const requestId = () => "r_" + (root.crypto?.randomUUID?.() || Date.now().toString(36) + "_" + Math.random().toString(36).slice(2));

  function nativeExchange(bridge) {
    return (command, id, policy) => new Promise((resolve, reject) => {
      if (!bridge || typeof bridge.sendUdpAsync !== "function") return reject(Error("需要支持异步 UDP 的新版 APK"));
      const callbacks = root.__amadeusUdpCallbacks ||= Object.create(null);
      const timer = setTimeout(() => { delete callbacks[id]; reject(Error("设备离线或 UDP 回执超时")); }, policy.timeout * (policy.retries + 1) + 1800);
      callbacks[id] = (raw) => {
        delete callbacks[id]; clearTimeout(timer);
        try {
          const reply = JSON.parse(raw);
          if (!reply || reply.request_id !== id) throw Error("UDP 请求编号不匹配");
          if (reply.status !== "ok") throw Error(reply.error || "ESP32 拒绝操作");
          if (command.cmd === "frame" && !/^[0-9a-f]{1536}$/i.test(reply.pixels || "")) throw Error("不完整的灯板帧");
          if (command.cmd === "arcade" && (!reply.arcade || !Number.isInteger(reply.arcade.game_id) ||
              !Number.isInteger(reply.arcade.state))) throw Error("缺少有效街机状态");
          resolve({status:"ok", source:command.cmd === "frame" ? "hardware_pwm" : "esp32_hardware",
            simulated:false, request_id:id, mode:reply.mode, game_status:reply.arcade,
            hex:reply.pixels, frame_id:reply.frame_id, is_connected:true});
        } catch (error) { reject(error); }
      };
      try {
        // Host/token/boot nonce and sequence are owned by native settings, never a web page.
        bridge.sendUdpAsync(JSON.stringify({request_id:id, command:JSON.stringify(command)}), policy.timeout, policy.retries, id);
      } catch (error) { delete callbacks[id]; clearTimeout(timer); reject(error); }
    });
  }

  class ArcadeTransport {
    constructor(exchange) { this.exchange=exchange; this.down=0; this.tail=Promise.resolve(); this.pending=0; this.epoch=0; this.blocked=false; this.readBusy=false; this.revision=0; }
    call(path, data={}) {
      let action = path === "/api/arcade" ? data.action : path.replace("/api/arcade/", "");
      if (this.blocked && ["key","input","heartbeat"].includes(action)) return Promise.reject(Error("连接已中断，请明确继续或重新选卡"));
      if (action === "stop") action="exit";
      if (action === "key") {
        const bit=KEYS[data.key];
        if (!bit || typeof data.down !== "boolean") return Promise.reject(Error("无效手柄按键"));
        const pressed = data.down && !(this.down & bit) ? bit : 0;
        this.down = data.down ? this.down | bit : this.down & ~bit;
        data={down:this.down,pressed}; action="input";
      }
      if (!ACTIONS.has(action)) return Promise.reject(Error("未知街机操作"));
      // Readbacks are disposable: neither wait on controls nor hold up their queue.
      // Native/Python transports also use a separate authenticated replay identity.
      if (["frame","status"].includes(action)) {
        if (this.readBusy) return Promise.reject(Error("telemetry_busy"));
        this.readBusy=true;
        const epoch=this.epoch, revision=this.revision;
        const command=action==="frame"?{cmd:"frame"}:{cmd:"arcade",action:"status"};
        return Promise.resolve().then(()=>this.exchange(command,requestId(),{timeout:150,retries:0}))
          .then(reply=>{
            if(epoch!==this.epoch || revision!==this.revision) throw Error("stale_reply");
            return reply;
          }).finally(()=>{this.readBusy=false;});
      }
      if (action === "select" && !IDS.has(data.game_id)) return Promise.reject(Error("无效游戏编号"));
      if (action === "players" && ![1,2].includes(data.count)) return Promise.reject(Error("无效对战模式"));
      if (["select","reset","exit","pause","players"].includes(action)) { this.down=0; ++this.epoch; }
      if (this.blocked && ["input","heartbeat"].includes(action)) return Promise.reject(Error("连接已中断，请明确继续或重新选卡"));
      // Held state is periodically resynchronized, even if an earlier release was lost.
      if (action === "heartbeat" && this.down) { action="input"; data={down:this.down,pressed:0}; }
      const command = action === "frame" ? {cmd:"frame"} : {cmd:"arcade",action};
      if (action === "select") command.game_id=data.game_id;
      if (action === "config") {
        if(typeof data.sound_enabled!=="boolean" || !Number.isInteger(data.sound_volume) || data.sound_volume<0 || data.sound_volume>100 ||
           (data.difficulty!==undefined && (!Number.isInteger(data.difficulty)||data.difficulty<0||data.difficulty>2)))return Promise.reject(Error("无效街机设置"));
        command.sound_enabled=data.sound_enabled;command.sound_volume=data.sound_volume;
        if(data.difficulty!==undefined)command.difficulty=data.difficulty;
      }
      if (action === "players") {
        command.count=data.count;
      }
      if (action === "input") {
        if (![data.down,data.pressed].every(n => Number.isInteger(n) && n>=0 && n<=255)) return Promise.reject(Error("无效输入掩码"));
        command.down=data.down; command.pressed=data.pressed;
      }
      if (this.pending >= 64) { this.down=0; this.blocked=true; return Promise.reject(Error("输入队列已满，请重新继续游戏")); }
      const epoch=this.epoch, id=requestId();
      ++this.revision;
      const policy = ["input","heartbeat"].includes(action) ? {timeout:200,retries:1} : action === "frame" || action === "status" ? {timeout:400,retries:0} : {timeout:700,retries:2};
      ++this.pending;
      const result=this.tail.then(async () => {
        if (epoch !== this.epoch) throw Error("stale_request");
        if (this.blocked && ["input","heartbeat"].includes(action)) throw Error("连接已中断，请明确继续或重新选卡");
        if (["select","start","resume"].includes(action)) this.blocked=false;
        const reply=await this.exchange(command,id,policy);
        ++this.revision; // Also invalidate reads begun while this control was in flight.
        if (epoch !== this.epoch) throw Error("stale_reply");
        return reply;
      });
      this.tail=result.catch(() => {});
      return result.catch(error => {
        if (!/^stale_/.test(error.message) && epoch===this.epoch && !this.blocked) {
          this.down=0; this.blocked=true;
          // Best effort release/pause. Never resume automatically; board watchdog
          // remains the final safeguard if the control connection is truly gone.
          this.tail=this.tail.then(async()=>{
            if(epoch!==this.epoch || !this.blocked)return;
            for(const c of [{cmd:"arcade",action:"input",down:0,pressed:0},{cmd:"arcade",action:"pause"}]) {
              if(epoch!==this.epoch || !this.blocked)return;
              try { await this.exchange(c,requestId(),{timeout:150,retries:0}); } catch (_) {}
            }
          });
        }
        throw error;
      }).finally(() => { --this.pending; });
    }
    async suspend() {
      this.down=0;
      try { await this.call("/api/arcade",{action:"input",down:0,pressed:0}); } catch (_) {}
      try { await this.call("/api/arcade",{action:"pause"}); } catch (_) {}
      this.blocked=true;
    }
  }
  ArcadeTransport.registeredIds=Object.freeze([...IDS]);
  root.ArcadeTransport=ArcadeTransport;
  root.arcadeNativeExchange=nativeExchange;
  if (typeof module !== "undefined") module.exports={ArcadeTransport,nativeExchange};
})(typeof window !== "undefined" ? window : globalThis);
