# Intelligent Lighting Control System Pro — 第一轮审查台账（F01～F22）

**基准 Commit**: `cc3745ec842afd99d0385beb0526cded81f38876`（`main`）  
**状态口径**：严格采用七类规范状态：`待核实` / `源码确认有问题` / `已修复待回归` / `软件验证通过` / `待当前版本实机验收` / `用户实机确认` / `可选增强/明确递延`。  
**说明**：本轮未执行 ESP32 烧录、手机 APK 安装或物理板端采音/亮灯实测，所有硬件关联项最高标定为 `待当前版本实机验收`。

---

## 台账总表（F01～F22）

| 编号 | 问题描述与影响链路 | 第一轮状态 | 涉及源码 / 测试文件 | 验证证据摘要 |
| :---: | :--- | :---: | :--- | :--- |
| **F01** | 热点免配对诉求与曲库/视觉 Token 拦截冲突 | **待当前版本实机验收** | `pc-agent-vision/access_control.py`, `advanced_api.py`, `web_app/app.js`, `android-app/.../FrontCameraBridge.java` | 局域网 `GET /api/pro/library`、`/api/pro/music`、`/api/pro/vision` 免手工 Token 放行；`/api/pro/memory` 等敏感路由保持 401；`/api/pro/camera/frame` 改用会话级 `X-Vision-Token`；`test_round1_rectification_regressions.py` + `test_security_pairing_camera.py` (14/14) 通过；待手机热点实测。 |
| **F02** | `MainActivity` 前摄 JS 桥在后台线程读取 `webView.getUrl()` 及 `CountDownLatch.await()` 阻塞 | **待当前版本实机验收** | `android-app/.../MainActivity.java`, `pc-agent-vision/web_app/app.js` | 新增异步 `requestFrontCamera(requestId, uploadUrl, mode, visionToken)`，`webView.getUrl()` 全部移入 UI 线程，删除 `CountDownLatch` 阻塞等待；APK 构建通过 + `test_phone_camera_requests.cjs` (12/12) 通过；待真机授权弹窗验证。 |
| **F03** | 手机前摄异步上传、旧会话迟到停止回调串扰及前端状态失真 | **待当前版本实机验收** | `android-app/.../FrontCameraBridge.java`, `pc-agent-vision/web_app/app.js`, `pc-agent-vision/advanced_api.py` | 引入单调 `sessionEpoch` 隔离旧回调/旧 `stop()`；透传五阶段诚实状态（`camera_opened` / `local_preview_ready` / `upload_accepted` / `observation_fresh` / `device_command_acknowledged`）；`AndroidRound1ContractsTest` + `test_phone_camera_requests.cjs` 通过；待真机推流实测。 |
| **F04** | 远程 MediaPipe 实例无互斥并发 `process()`/`close()` 竞态、网络与推理锁耦合及硬件 ACK 未传播 | **待当前版本实机验收** | `pc-agent-vision/multimodal_hub.py`, `pc-agent-vision/advanced_api.py` | 引入 `_RemoteMediaPipeHandle` 引用计数互斥保护 + 兼容 `_remote_hands`/`_remote_face` 注入、`MAX_REMOTE_PENDING_FRAMES=2` 限流、`device_command_acknowledged` 回传；`test_round1_rectification_regressions.py` + `test_audit_closure_defects.py` (21/21) 通过；待实机联调。 |
| **F05** | `GazeCalibration` 未绑定摄像头来源/旋转/镜像配置，跨设备切换误复用校准参数 | **待当前版本实机验收** | `pc-agent-vision/visual_features.py`, `pc-agent-vision/multimodal_hub.py` | `GazeCalibration` v2 绑定 `(source, camera_id, rotation, mirrored, aspect)`；切换来源或旋转自动失效并拒绝复用；`test_f05` 回归通过；待真机视线校准准确率验收。 |
| **F06** | `AudioHAL::PlayMonoPcm()` 每块调用 `ResetResampler16kTo24k()` 导致 16k->24k 重采样跨块咔哒/断点 | **待当前版本实机验收** | `firmware-s3/main/audio/audio_sample_format.h`, `audio_hal.h`, `audio_hal.cc`, `command_dispatcher.cc`, `tests/audio_alignment_native_test.cpp` | 抽出 `audio_pcm::PcmPlaybackPipeline` 跨块维持重采样状态、`FlushPcmStream()` 流末冲刷、抢占/打断/I²S 错误重置；主机 11 组全过 + ESP-IDF v5.5.4 编译通过；待实板烧录试听。 |
| **F07** | PC `music_engine` DSP 滤波器跨块置零、0.25 增益走旁路且低音量信号被异常抬升 | **待当前版本实机验收** | `pc-agent-vision/music_engine.py`, `web_server.py`, `web_app/index.html` | `SpeakerAudioProcessor` 跨块维持 105Hz 二阶 Butterworth HPF `zi`、统一 `DEFAULT_MUSIC_GAIN = 0.25`、移除 0.25 bypass 与超 gain 自动拉高并限定数字峰值天花板 `0.85`；`test_music_library.py` (18/18) + `test_round1` 通过；待实板外放试听。 |
| **F08** | `web_server.run_chat` 对话抢占时收音 `pause`/`resume` 归属判断失准 | **软件验证通过** | `pc-agent-vision/web_server.py` | 新增 `ChatPauseCoordinator` 按活跃轮次与 listener 实例管理归属，解决 A->B->C 抢占、异常/取消以及音乐暂停期间误恢复收音问题；`test_round1` + `test_listener_lifecycle.py` (68/68) 通过。 |
| **F09** | `KurisuAgent.chat()` 快捷分支与同步播报长期占用 `_chat_lock` | **软件验证通过** | `pc-agent-vision/kurisu_agent.py` | `_chat_lock` 收窄至仅保护快速历史/状态读写，语义规划与 `_execute_speech` 移出锁外并接入内部抢占取消事件；`test_f09` + 并发回归通过。 |
| **F10** | `KurisuAgent.chat()` 语义规划异常路径提前返回导致回退台词未播报 | **软件验证通过** | `pc-agent-vision/kurisu_agent.py` | 统一经 `_pending_speech` -> `_execute_speech` 收口，捕获规划与 TTS 异常并记录 `last_model_error`；`test_f10` 与 NACK/双语测试通过。 |
| **F11** | `AccessPolicy` 与 `wifi_gateway` 硬编码 `192.168.186.0/24` 导致通用手机热点失效 | **待当前版本实机验收** | `pc-agent-vision/access_control.py`, `pc-agent-vision/wifi_gateway.py` | 动态解析宿主活跃本地私网子网（Windows `ipconfig` / POSIX `ip addr`），过滤 Radmin/WireGuard/WSL/vEthernet 等虚拟网卡与 Loopback；`test_f11` 与全套网络测试通过；待真实手机热点验证。 |
| **F12** | Android UDP/NSD 发现恢复、PC 晚启动及切网后 `/api/health` 核验闭环不足 | **待当前版本实机验收** | `android-app/.../MainActivity.java`, `tests/java/org/fglab/kurisu/AndroidRound1ContractsTest.java` | 新增 `verifyServerHealth` (`/api/health`)、`ConnectivityManager.NetworkCallback` 切网监听、有界重试定时器与 `lastLoadedOrigin` 同源去重；APK 编译 + JVM 合同测试通过；待真机切网联调。 |
| **F13** | `service_discovery` 广播的 `pairing_required` 与 `AccessPolicy.trust_private` 默认值可能脱节 | **软件验证通过** | `pc-agent-vision/service_discovery.py`, `pc-agent-vision/web_server.py`, `pc-agent-vision/access_control.py` | 统一由 `resolve_trust_private()` 决定默认信任策略，并在启动广播时显式传入 `not access_policy.trust_private`；`test_f13` 回归通过。 |
| **F14** | `AGENTS.md` 等旧文档描述 60 FPS，而实装主显示循环为 33ms (~30 FPS) | **可选增强/明确递延** | `AGENTS.md` | 纯文档一致性问题，第一轮不动主渲染调度帧率，明确递延至后续文档同步。 |
| **F15** | 街机 100 款中部分卡带历史仅验证生命周期，缺完整玩法/音效与 RNG 差异 | **可选增强/明确递延** | `docs/PRO_FINAL_GAP_LIST.md`, `firmware-s3/main/display/arcade/*` | 依既有需求基线保持 P2 递延，不重启大规模街机改造。 |
| **F16** | 共享环境中 GPU/cuDNN 兼容与 LLM/TTS 预热耗时优化 | **可选增强/明确递延** | `pc-agent-vision/requirements-voice-constraints.txt` | 保留 `KURISU_ASR_DEVICE=cpu` 与 `KURISU_TTS_CUDNN=0` 已验证配置，递延至后续性能专项。 |
| **F17** | 复杂声学噪声环境下唤醒率/误报与实验性双工 AEC 调优 | **可选增强/明确递延** | `pc-agent-vision/voice_listener.py` | 依赖真实环境采音反馈，不阻塞本轮软件交付。 |
| **F18** | 极端长音频/多声道曲库解码峰值内存与损坏文件恢复体验 | **可选增强/明确递延** | `pc-agent-vision/music_engine.py` | 现有边界测试已覆盖基础负例，更深优化保持 P2 递延。 |
| **F19** | Windows 原生 C++ 测试桩 `nvs.h` 与 `jetson_uart.h` 存在 `ESP_FAIL`/`ESP_OK` 宏定义冲突 | **软件验证通过** | `tests/phase_a_stubs/nvs.h`, `firmware-s3/main/protocol/jetson_uart.h` | 修复为 ESP-IDF 一致取值（`ESP_OK=0`, `ESP_FAIL=-1`, `ESP_ERR_NVS_NOT_FOUND=1`）；`scripts/test_audio_alignment_native.py` 11 组全过（pre-fix 复现 `Save(-1)==ESP_FAIL` 失败 -> post-fix 全过）。 |
| **F20** | `tests/test_phone_camera_requests.cjs` 缺少 `location.hostname`/`isSecureContext` 桩导致安全上下文误判 | **软件验证通过** | `tests/test_phone_camera_requests.cjs` | 补齐 URL/Origin/SecureContext 模拟桩并新增 Tests 10–12（async `requestFrontCamera` 与 epoch 隔离）；pre-fix 在第 167 行复现失败 -> post-fix 12/12 全部通过。 |
| **F21** | 历史跟踪人脸数据（历史遗留资产）来源分类与隐私授权处置 | **可选增强/明确递延** | 历史受控资产目录（未触碰） | 本轮严格不删除/不迁移/不提交任何历史人脸资产，保留待用户分类授权。 |
| **F22** | 历史 `tests/phase_a_core_test.cpp` 第 64 行断言 `game_id=101` 非法与 `#101` 扩展协议存在基线漂移 | **可选增强/明确递延** | `tests/phase_a_core_test.cpp`, `firmware-s3/main/protocol/arcade_protocol.h` | 编译通过且 NVS/重构门禁通过后于 `test_protocol()` 命中历史 `101` 断言；本轮遵循禁改既有非 F19/F20 测试断言原则如实记录，后续按需同步测试。 |
