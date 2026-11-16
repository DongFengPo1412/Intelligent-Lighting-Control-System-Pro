# Intelligent Lighting Control System Pro — 缺陷与整改审查台账（F01～F22 + R1-01～R1-05 + R3-01）

**当前分支**：`main`（Round 3 收口基于 `b3f8c4b9763b3b40f903fdb968a4eb1d263dafec`）  
**状态口径**：严格采用三类最终软件验收结论（`SOFTWARE_PASS` / `CONDITIONAL` / `FAIL`）与进度标签（`待当前版本实机验收` / `软件验证通过`）；禁用 `HARDWARE_PASS`。  
**说明**：
1. 严格保留原始交付基线的 **F01～F22** 编号与原始含义，不作覆盖或降级。
2. Round 1 独立复核新定位的问题独立编号为 **R1-01～R1-05**；Round 2 后独立复核定位的 PC 摄像头越权与会话劫持安全边界缺陷记为 **R3-01（New Security P1）**；历史旧测试兼容问题单独记为 **TC-01**。
3. 本轮未执行 ESP32 物理烧录（实体板内仍为早先烧录固件，尚未烧录 Round 1/3 候选包）、手机 APK 安装（真机尚未安装本轮候选包）或真实音频/相机/热点硬件验收；所有依赖实机硬件与真实网络环境的修复最高标定为 **`待当前版本实机验收`（软件层面 `SOFTWARE_PASS` / 总体 `CONDITIONAL`）**。

---

## 一、原始缺陷台账（F01～F22）

| 编号 | 原始问题描述 | 当前状态 | 涉及源码 / 测试与说明 |
| :---: | :--- | :---: | :--- |
| **F01** | 热点免配对诉求与敏感接口/曲库/视觉 Token 拦截冲突 | **待当前版本实机验收** | `pc-agent-vision/access_control.py`, `advanced_api.py`, `web_app/app.js`, `FrontCameraBridge.java`；普通灯控/曲库 GET/基础视觉免管理员 Token，相机帧改用会话级 `X-Vision-Token`（GET 单帧遗漏已于 `R1-02` 补齐）；待真热点实测。 |
| **F02** | Android 前摄 `@JavascriptInterface` 后台读 `webView.getUrl()` 与 `CountDownLatch.await()` 阻塞 | **待当前版本实机验收** | `android-app/.../MainActivity.java`, `app.js`；异步 `requestFrontCamera` 已落地（按需权限补强见 `R1-05`），待真机安装验收。 |
| **F03** | 手机前摄异步上传、旧会话迟到停止回调串扰及前端状态失真 | **待当前版本实机验收** | `FrontCameraBridge.java`, `app.js`, `advanced_api.py`；单调 `sessionEpoch` + 五阶段诚实状态；待真机推流验收。 |
| **F04** | 远程 MediaPipe 并发 `process()`/`close()` 竞态、推理锁耦合与设备 ACK 传播 | **待当前版本实机验收** | `multimodal_hub.py`, `advanced_api.py`；`_RemoteMediaPipeHandle` 引用计数保护 + 跨帧 ACK 误报已于 `R1-01` 修复；待真机联调。 |
| **F05** | `GazeCalibration` 未绑定摄像头来源/旋转/镜像配置导致跨源误复用 | **待当前版本实机验收** | `visual_features.py`, `multimodal_hub.py`；校准 v2 元数据绑定 + 镜像硬编码错误已于 `R1-04` 修复；待真机视线准确率实测。 |
| **F06** | ESP32 `AudioHAL::PlayMonoPcm()` 每块重置 16k→24k 重采样器 | **待当前版本实机验收** | `audio_sample_format.h`, `audio_hal.h`, `audio_hal.cc`, `command_dispatcher.cc`；第一轮已修复并通过 ESP-IDF 编译与 11 组 C++ 原生测试（Round 2 未改 ESP32 源码，待授权烧录听音）。 |
| **F07** | PC `music_engine` 滤波器跨块置零、0.25 旁路与低音量抬升失真 | **待当前版本实机验收** | `music_engine.py`, `web_server.py`, `web_app/index.html`；连续 105Hz HPF `zi` 与 `DEFAULT_MUSIC_GAIN=0.25` 已落地，待实板听音。 |
| **F08** | `web_server.run_chat` 并发抢占收音 `pause`/`resume` 归属错乱 | **软件验证通过** | `pc-agent-vision/web_server.py`；第一轮 `ChatPauseCoordinator` 与 Round 2 `R1-03` 释放-抢占竞争窗口补丁均已通过精确线程 Barrier/Event 测试。 |
| **F09** | `KurisuAgent.chat()` 快捷分支与同步播报长期持有 `_chat_lock` | **软件验证通过** | `pc-agent-vision/kurisu_agent.py`；锁范围已收窄至历史/状态读写，TTS 移出锁外并支持抢占取消，第一轮回归通过。 |
| **F10** | `KurisuAgent.chat()` 语义规划异常路径提前返回导致漏播报 | **软件验证通过** | `pc-agent-vision/kurisu_agent.py`；统一经 `_pending_speech` → `_execute_speech` 收口，规划/TTS 异常与 NACK 回归通过。 |
| **F11** | `access_control` / `wifi_gateway` 硬编码 `192.168.186.0/24` 无法适配通用手机热点 | **待当前版本实机验收** | `access_control.py`, `wifi_gateway.py`；已改动态读取活跃私网子网并过滤虚拟网卡，待真实热点验收。 |
| **F12** | Android UDP/NSD 服务发现恢复与 `/api/health` 存活核验闭环不足 | **待当前版本实机验收** | `MainActivity.java`, `AndroidRound1ContractsTest.java`；健康探测、`NetworkCallback` 与同源防重已落地，待真机切网恢复实测。 |
| **F13** | `service_discovery` 广播 `pairing_required` 与 `AccessPolicy.trust_private` 默认值可能脱节 | **软件验证通过** | `service_discovery.py`, `web_server.py`, `access_control.py`；已统一 `resolve_trust_private()` 并在启动同步注入。 |
| **F14** | Android `WebStorage` 清理导致前端主题/用户偏好丢失 | **待当前版本实机验收** (`SOFTWARE_PASS`) | `android-app/.../MainActivity.java`, `web_app/app.js`；新增 `@JavascriptInterface` `getThemePreference`/`setThemePreference` 与 `SharedPreferences("config")["ui_theme"]`，仅持久化非敏感 `day`/`night` 主题并在 `onPageFinished()` 回填；`WebStorage.deleteAllData()` 仍全清配对 Token/Cookie，经 `AndroidRound1ContractsTest` 验证。 |
| **F15** | 日间 HUD 与动态状态颜色对比度不足 | **软件验证通过** (`SOFTWARE_PASS`) | `web_app/index.html`, `style.css`, `app.js`；移除 `#ffd23f`/`#f59e0b`/`#94a3b8` 与 JS 内联 `stateColors`，改用日/夜 CSS 变量与 `state-code-0..4`；经无头 Edge CDP (`tests/test_ui_contrast_f15.cjs`) 实测 `360/390/768/1280` 宽度无溢出，日/夜 HUD 对比度均 `>= 5.02:1`（WCAG AA `>= 4.5:1`）。 |
| **F16** | 语义规划 Schema 仍限制 `game_id <= 100` 及提示词遗漏 `#101` | **软件验证通过** (`SOFTWARE_PASS`) | `pc-agent-vision/semantic_control.py`, `light_tools.py`, `web_app/index.html`；Schema `game_id.maximum = 101`、Prompt 与 `from_wire` 更新至 `1..101`（显式拒绝 `True`/越界）、新增“打开微光纪元”少样本与 `#101` 直达解析；`exact_plan`、Mock Ollama HTTP 及板端 NACK 诚实报错回归通过。 |
| **F17** | `#101《微光纪元》` 缺失完整挖掘、建造、战斗等实际沙盒机制 | **待当前版本实机验收** (`SOFTWARE_PASS`) | `firmware-s3/main/display/arcade/game_101_microlight.h/.cpp`, `pc-agent-vision/arcade/game_101_microlight.py`；对称重构 30 种方块与掉落、真实 `PutTile`/`put_tile` 世界修改、256 槽有界编辑缓存、资源扣减与实体阻挡建造、4 敌人追击/击退/掉落、宝箱与冰/仙人掌/熔岩环境机制，经 C++ & Python 回归与 36,000 步压测，待实体 ESP32 屏幕手玩验收。 |
| **F18** | `#101` 跳跃、群落位掩码、负坐标等玩法/逻辑不一致 | **软件验证通过** (`SOFTWARE_PASS`) | `game_101_microlight.h/.cpp`, `game_101_microlight.py`；分离 `KEY_UP` 跳跃/上浮与 `KEY_A` 挖掘无冲突、实现数学 `FloorDiv`/`FloorMod`（`-80..80`）、7-bit `VisitedBiomeCount()`  popcount 计群落并修复单高位 `bitmask >= 4` 误判胜利；C++ 与 Python 同种子 180 帧像素校验和精确一致（`1362504820`）。 |
| **F19** | Windows 原生 C++ 测试桩 `nvs.h` 与 `jetson_uart.h` 存在 `ESP_FAIL`/`ESP_OK` 宏定义冲突 | **软件验证通过** (`SOFTWARE_PASS`) | `tests/phase_a_stubs/nvs.h`, `jetson_uart.h`；`scripts/test_audio_alignment_native.py` 11 组与 `test_cpp_jetson_canvas.cpp` 18 项及 `phase_a_core_test.cpp` 全通过。 |
| **F20** | `tests/test_phone_camera_requests.cjs` 测试桩缺少 `location.hostname`/`isSecureContext` 触发误报 | **软件验证通过** (`SOFTWARE_PASS`) | `tests/test_phone_camera_requests.cjs`；安全上下文桩与 12/12 项生命周期测试全部通过。 |
| **F21** | 私人音乐库测试夹具与集成测试未彻底隔离（含历史隐私资产隔离约束） | **软件验证通过** (`SOFTWARE_PASS`) | `tests/test_audio_discovery_alignment.py`；`VoiceMusicCommandE2ETests` 改为 `TemporaryDirectory` 合成 `.wav` 夹具，新增暂停/恢复/切歌/停止/空目录/损坏 WAV/非音频后缀/无效路径测试；真实私人目录测试改由 `KURISU_REAL_MUSIC_DIR` 显式门控，无私人资产入库。 |
| **F22** | 验收文档、版本标识、FPS 描述（60 FPS vs 30 FPS）与发布证据不一致 | **软件验证通过** (`SOFTWARE_PASS`) | `AGENTS.md`（同步写明 Core 1 实际主循环 `~30 FPS / 33ms` 与理论峰值 `60 FPS`）、`docs/PRO_FINAL_REQUIREMENTS_BASELINE.md`（更新当前正式分支为 `main`）、`docs/ARCADE_101_MICROLIGHT_INTEGRATION.md`（补齐原型对照与硬件裁剪披露矩阵）及本台账/验证报告。 |

---

## 二、Round 1 独立复核新增项（R1-01～R1-05）及测试兼容记录（TC-01）

| 编号 | 复核定位问题 | Round 2 状态 | 涉及源码 / 测试与验证说明 |
| :---: | :--- | :---: | :--- |
| **R1-01** | 视觉 ACK 跨帧误报：`upload_frame()` 直接读取全局 `last_device_command_*`，导致未发指令帧继承上一帧 `True` | **待当前版本实机验收** | `pc-agent-vision/multimodal_hub.py`, `pc-agent-vision/advanced_api.py`；为每帧建立含 `session_id`/`epoch`/`frame_seq`/`attempted`/`command_count`/`acknowledged` 的线程隔离上下文，`pet` 等 0 指令帧明确返回 `attempted=False, acknowledged=None`；真实 HTTP + `process_remote_frame` 回归通过，待实机联调。 |
| **R1-02** | `access_control.py` 定义了 `SCOPED_VISION_FEED_PATHS` 却漏掉 `GET /api/pro/camera/frame` 视觉会话授权分支 | **待当前版本实机验收** | `pc-agent-vision/access_control.py`；改用 `norm_path in SCOPED_VISION_FEED_PATHS and method == "GET"`，远程会话强制校验匹配 `session_id` 与对端 IP；真实 `aiohttp` 中间件路由正反例回归通过，待真机热点验证。 |
| **R1-03** | `ChatPauseCoordinator.release()` 锁外调用 `resume()` 与新轮次 `prepare_pause()` 间存在提前恢复收音竞争窗口，且 `_released_turns` 无上限增长 | **软件验证通过** | `pc-agent-vision/web_server.py`；新增 `_resume_pending` / `_resume_in_progress` 状态标记、`_hw_lock` 硬件串行锁（严格遵循 `_hw_lock -> _lock` 加锁顺序防死锁）及 `MAX_RETIRED_TURNS=256` 淘汰机制；经 `threading.Event` 精确构造交错窗口验证通过。 |
| **R1-04** | `multimodal_hub.py` 中 `mirrored=bool(is_flipped or True)` 恒为 `True`，未真实区分手机/PC 镜像与旋转几何 | **待当前版本实机验收** | `pc-agent-vision/multimodal_hub.py`；按 `raw_mirrored`、`apply_flip` 与 `source` 推导真实 `effective_mirrored`，补全 `apply_rotation` 几何旋转，校验 `mirrored=False/True`、90/180/270 旋转及 PC/手机切源失效与重校准测试，全部通过。 |
| **R1-05** | Android `MainActivity.onCreate()` 首次启动即主动弹窗请求 `CAMERA` 权限 | **待当前版本实机验收** | `android-app/.../MainActivity.java`；移除 `onCreate()` 中主动权限请求，改为用户点击开启前摄时按需请求，并通过 `onRequestPermissionsResult()` 与瞬态 `onPause()` 保护无缝衔接原异步授权流；重新编译候选 APK 与 JVM 合同测试通过，待真机实测。 |
| **TC-01** | 历史 `tests/phase_a_core_test.cpp` 第 64 行旧断言 `{"action":"select","game_id":101}` 非法与 `#101` 协议扩展冲突 | **软件验证通过** (`SOFTWARE_PASS`) | `tests/phase_a_core_test.cpp`；Round 3 随 `#101` 全链路升级，将 `game_id=1..101` 纳入合法契约并严格拒绝 `102`/`0`/`-1`/`1.5`/`true`/`"101"`，`scripts/test_phase_a_native.py` 退出码 `0` 全通过。 |
| **R3-01** | **New Security P1**：受信任热点局域网客户端可免管理员 Token 通过 `POST /api/pro/vision` 启动/停止 PC 本机摄像头并套取 `vision_token`，或停掉他人已开启视觉会话 | **待当前版本实机验收** (`SOFTWARE_PASS`) | `pc-agent-vision/access_control.py`, `advanced_api.py`, `web_app/app.js`；普通灯控/音乐/手机前摄（`source="remote"`）仍对热点免配对；`source="camera"` 或缺省/伪造来源以及停止 `camera` 会话在鉴权前置阶段即被 `401 (pc_camera_requires_admin_auth)` 拦截，且非所有者不得停掉他人会话（`is_vision_session_owner`）；经 `PcWebcamAuthAndSessionOwnershipTests` 验证，待真热点与 PC 本机互访复测。 |
