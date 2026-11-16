# Intelligent Lighting Control System Pro — 第一轮整改与回归验证报告

**基线 Commit**：`cc3745ec842afd99d0385beb0526cded81f38876`（`main`）  
**整改分支**：`main`（直接落地，未创建分叉分支）  
**执行范围**：第一轮主链 Defects **F01–F13**、**F19**、**F20**；未执行 ESP32 烧录、手机 APK 安装、NVS 擦除或物理声学/光学实测。  
**原始日志归档**：会话工作缓存 `scratch/regression_logs/`、`scratch/esp_build.log`、`scratch/apk_out/`。

---

## 一、六大领域最终结论（严格口径）

| 领域 | 最终结论 | 核心依据与证据边界 |
| :--- | :---: | :--- |
| **1. ESP32 音频与固件编译 (`Audio HAL & Firmware Build`)** | **`SOFTWARE_PASS`** | F06/F19 修复经 `test_audio_alignment_native.py` 11 组与 `test_cpp_jetson_canvas.cpp` 18 项全通过，ESP-IDF v5.5.4 全量编译退出码 0 产出候选固件（`1,606,400` 字节）；尚未烧录实体板验证音质。 |
| **2. PC 对话抢占、语音锁与异常收口 (`Dialogue & Speech`)** | **`SOFTWARE_PASS`** | F08/F09/F10 修复经 `test_round1_rectification_regressions.py` (17/17)、`test_listener_lifecycle.py` (68/68)、`test_t03_bilingual.py` (60/60)、`test_audit_closure_defects.py` (21/21) 全部通过；真机全双工麦放待实机验收。 |
| **3. 手机热点零配置与分级安全 (`Hotspot Zero-Config & Security`)** | **`SOFTWARE_PASS`** | F01/F11/F13 修复经 `test_security_pairing_camera.py` (14/14)、`test_phase_a_network.py` (14/14)、`test_audio_discovery_alignment.py` (11/11)、`test_music_library.py` (18/18)、`test_final_wireless_default.py` (2/2) 全部通过，实机 Windows `ipconfig` 成功识别 `WLAN` 并过滤 `Radmin VPN`/`vEthernet (WSL)`；待真实手机热点验证。 |
| **4. Android 前摄桥接、健康发现与 APK (`Android Bridge & APK`)** | **`SOFTWARE_PASS`** | F02/F03/F12/F20 修复使 `build_apk.py` 顺利产出候选 APK（`2,861,537` 字节，v2/v3 签名校验通过），`test_phone_camera_requests.cjs` (12/12)、`AndroidRound1ContractsTest`、`WebViewCookieIsolationTest` 全通过；待真机安装与网络切换验收。 |
| **5. PC 视觉并发、源切换与校准绑定 (`PC Vision & Calibration`)** | **`SOFTWARE_PASS`** | F04/F05 修复经 `test_round1_rectification_regressions.py`、`test_audit_closure_defects.py` (21/21)、`test_vision_takeover_and_permission_closure.py` (7/7)、`test_final_vision_health.py` (1/1) 全通过；真实摄像头采集与校准精度待实机验收。 |
| **6. Jetson UART v2.3.1 / Mode 29 兼容 (`Jetson Interop`)** | **`SOFTWARE_PASS`** | `test_jetson_uart_protocol.py` (25/25)、`jetson-nano/tests/test_jetson_nano.py` (17/17)、`test_cpp_jetson_canvas.cpp` (18/18) 全部通过；注：历史 `tests/phase_a_core_test.cpp` 在 NVS 段无 F19 冲突，于第 64 行 `test_protocol()` 命中旧 `#101` (`game_id=101`) 断言漂移，记为 **F22** 递延。 |

> 以上 **6/6** 项软件结论均为 **`SOFTWARE_PASS`**，明确**不含 `HARDWARE_PASS`**；实体设备通过需完成第七节硬件检查清单。

---

## 二、修改与新增文件清单（共 27 项代码与文档变更）

| 分类 | 文件路径 | 关键改动说明 |
| :--- | :--- | :--- |
| **ESP32 固件 (F06, F19)** | `firmware-s3/main/audio/audio_sample_format.h` | 新增 `audio_pcm::PcmPlaybackPipeline`，跨块保持 16k->24k 重采样状态与流末尾 `Flush()` |
| | `firmware-s3/main/audio/audio_hal.h`, `audio_hal.cc` | 接入 `PcmPlaybackPipeline`、流代次切换与 `ResetPcmStream()`/`FlushPcmStream()`；移除每块 `ResetResampler16kTo24k()` |
| | `firmware-s3/main/protocol/command_dispatcher.cc` | 音频抢占调用 `ResetPcmStream()`；连续播报空隙 `>=150ms` 调用 `FlushPcmStream()` |
| | `firmware-s3/main/protocol/jetson_uart.h` | Windows 主机测试保护 `#ifndef ESP_OK` / `#ifndef ESP_FAIL` |
| **PC 语音/对话/音频 (F07–F10)** | `pc-agent-vision/music_engine.py` | 抽出 `SpeakerAudioProcessor` 保持跨块 Butterworth 105Hz HPF `zi`，统一 `DEFAULT_MUSIC_GAIN = 0.25`，移除 bypass 与超 gain 拉高 |
| | `pc-agent-vision/web_server.py` | `ChatPauseCoordinator` 修复并发抢占 pause/resume 归属；同步默认音乐增益与 `resolve_trust_private()`；`/ws` `mcp` 强制管理员鉴权 |
| | `pc-agent-vision/kurisu_agent.py` | `_chat_lock` 收窄至状态读写；快捷与语义分支及阻塞播报移出锁外并统一经 `_execute_speech` 收口 |
| | `pc-agent-vision/web_app/index.html` | 更新 `#musicBoost` 增益挡位，区分“数字前级增益”与“板载音量” |
| **网络与安全 (F01, F11, F13)** | `pc-agent-vision/access_control.py` | 动态解析活跃本地私网子网（过滤 VPN/Loopback）；曲库 GET 与基础音乐/视觉放行；新增 `issue_vision_capability` / `revoke_vision_capability` |
| | `pc-agent-vision/service_discovery.py` | 统一使用 `resolve_trust_private()` 对齐 `pairing_required` |
| | `pc-agent-vision/wifi_gateway.py` | 热点目标发现改用 `AccessPolicy.get_trusted_subnets()` 替代硬编码 `192.168.186` |
| **视觉与 Android (F02–F05, F12)** | `pc-agent-vision/visual_features.py` | `GazeCalibration` v2 绑定来源/摄像头 ID/旋转角度/镜像/宽高比元数据并识别不兼容旧校准 |
| | `pc-agent-vision/multimodal_hub.py` | `_RemoteMediaPipeHandle` 引用计数互斥推理与安全关闭；`MAX_REMOTE_PENDING_FRAMES=2`；`_record_device_command` 回传板端 ACK |
| | `pc-agent-vision/advanced_api.py` | 签发与撤销作用域 `vision_token`/`kurisu_vision_session`；返回 `upload_accepted`/`observation_fresh`/`device_command_acknowledged` |
| | `pc-agent-vision/web_app/app.js` | 适配异步 `requestFrontCamera`、`sessionEpoch` 回调隔离、五阶段诚实状态渲染及请求头传递 `X-Vision-Token` |
| | `android-app/src/org/fglab/kurisu/MainActivity.java` | 新增异步 `requestFrontCamera`，所有 `webView.getUrl()` 移至 UI 线程并移除 `CountDownLatch`；统一 `/api/health` 探针、`NetworkCallback`、重连退避与同源去重 |
| | `android-app/src/org/fglab/kurisu/FrontCameraBridge.java` | 引入 `sessionEpoch` 隔离旧会话事件，`X-Vision-Token`/`X-Vision-Session` 上传鉴权与错误遥测 |
| **测试与审计文档 (F19, F20)** | `tests/phase_a_stubs/nvs.h` | 修正 stub 宏 `ESP_OK=0`, `ESP_FAIL=-1`, `ESP_ERR_NVS_NOT_FOUND=1` |
| | `tests/test_phone_camera_requests.cjs` | 补齐 `location.hostname`、`isSecureContext` 与 `URL` 桩，新增异步前摄与 epoch 隔离测试 |
| | `tests/test_audio_discovery_alignment.py`, `tests/test_security_pairing_camera.py` | 同步去硬编码 `192.168.186` 断言并验证零配对与锁定模式 |
| | `tests/test_round1_rectification_regressions.py`, `tests/java/org/fglab/kurisu/AndroidRound1ContractsTest.java` | 新增第一轮 17 项 Pytest 集成回归与 JVM 合同测试 |
| | `docs/PRO_REVIEW_F01_F22_LEDGER.md`, `docs/PRO_ROUND1_VALIDATION.md` | 本轮审查台账与软件验证报告 |

---

## 三、F06 / F08 修复前后关键对比证据

### 1. F06：音频重采样连续性（16kHz -> 24kHz）
- **修复前**：`AudioHAL::PlayMonoPcm()` 每次进入均调用 `ResetResampler16kTo24k()` 并独立处理单块 `<=480` 样本，导致分块边界插值相位归零并丢失跨块历史样本。
- **修复后**：`audio_pcm::PcmPlaybackPipeline` 跨块持有 `Resampler16kTo24k` 上下文直至 `stream_generation` 变更、抢占复位（`ResetPcmStream()`）或空隙 `>=150ms` 触发 `FlushPcmStream()`。`test_audio_alignment_native.py` 实测连续 4800 样本、480 样本分块、随机分片及奇数（4837）/ 偶数（4838）尾块输出完全对齐且故障可恢复。

### 2. F08 / F09 / F10：并发对话抢占与收音/播报闭环
- **修复前**：`web_server.py` 依赖旧单变量判断导致连续 `A -> B -> C` 对话抢占后过早 `listener.resume()` 或异常路径漏恢复；`KurisuAgent.chat()` 快捷路径持有 `_chat_lock` 同步 `voice.speak()`，且语义规划异常分支提前返回遗漏语音播报。
- **修复后**：`ChatPauseCoordinator` 在多轮抢占交错后仅当最后一轮活跃对话退出（且此前并非音乐暂停状态）才精确恢复 1 次收音；`_chat_lock` 仅包住内存历史更新，语义规划/硬件执行/TTS 均在锁外运行并受 `cancelled` 事件保护。

---

## 四、热点免配置与分级安全权限矩阵（F01 / F11 / F13）

| 客户端来源 | 普通状态/曲库 GET/基础灯控/音乐/对话/启动视觉 | `/api/pro/camera/frame` & `/vision/frame` | `/api/pro/memory`, `/documents`, `/enroll`, `/library`(POST), `/mcp`, `/ws`(mcp) |
| :--- | :---: | :---: | :---: |
| **本机 Loopback** | 允许 | 允许 | 允许 |
| **活跃私网子网**（`trust_private=True`，如手机热点 `172.20.10.x`） | **免手工 Token 放行** | **仅持有效活跃 `X-Vision-Token` + 匹配 `X-Vision-Session` 放行**，否则 `401` | **强制管理员 Bearer Token / 会话 Cookie**，否则 `401` |
| **未受信任远端 / VPN（Radmin/WireGuard）/ `trust_private=False`** | **拒绝 `401`**（需配对 Token） | **拒绝 `401`** | **拒绝 `401`** |
| **跨站 `Origin` / `Sec-Fetch-Site: cross-site`** | **拒绝 `403`** | **拒绝 `403`** | **拒绝 `403`** |

---

## 五、全量自动化回归统计（最终源码修改后执行）

### 1. Python Pytest（33 组套，435 通过 / 0 失败 / 1 跳过）
> 执行环境：`C:\Users\Liu\anaconda3\envs\ai_cv_env\python.exe -m pytest`（234 个 subtest 同步全通过，总耗时 `64.15s`）

- **第一轮新增整合回归**：`test_round1_rectification_regressions.py` — **17 passed**
- **语音/对话/双语核心**：`test_listener_lifecycle.py` (**68 passed**), `test_t03_bilingual.py` (**60 passed**), `test_audit_closure_defects.py` (**21 passed**), `test_final_voice_startup.py` (**17 passed**), `test_local_asr.py` (**2 passed**)
- **网络安全/热点/音乐**：`test_music_library.py` (**18 passed**), `test_phase_a_network.py` (**14 passed**), `test_security_pairing_camera.py` (**14 passed**), `test_audio_discovery_alignment.py` (**11 passed**), `test_music_follow.py` (**7 passed**), `test_final_wireless_default.py` (**2 passed**)
- **视觉/运行时/控制器**：`test_pro_runtime.py` (**37 passed, 1 skipped**，跳过的 `test_real_cpp_renderer_feeds_modes_canvas_and_games` 因未设置 `KURISU_RENDERER_WASM` 环境变量属环境前置可选跳过), `test_vision_voice_arcade.py` (**20 passed**), `test_controller_validation.py` (**10 passed**), `test_vision_takeover_and_permission_closure.py` (**7 passed**), `test_face_enrollment.py` (**6 passed**), `test_delivery_regressions.py` (**4 passed**), `test_final_closure.py` (**2 passed**), `test_final_vision_health.py` (**1 passed**)
- **Jetson 联调与协议**：`test_jetson_uart_protocol.py` (**25 passed**), `jetson-nano/tests/test_jetson_nano.py` (**17 passed**)
- **显示/功耗/街机回归**：`test_kurisu_palette.py` (**11 passed**), `test_mario_game.py` (**7 passed**), `test_power_limiter.py` (**6 passed**), `test_arcade_handoff.py` (**6 passed**), `test_arcade_result_screen.py` (**6 passed**), `test_arcade_lifecycle.py` (**5 passed**), `test_arcade_web_api.py` (**5 passed**), `test_arcade_continuous_simulation.py` (**3 passed**), `test_arcade_nvs_persistence.py` (**3 passed**), `test_arcade_partition_table.py` (**3 passed**)

### 2. Node.js / 原生 C++ / JVM 测试（全量通过）
- `tests/test_phone_camera_requests.cjs`：**12/12 PASSED**（pre-fix 第 167 行复现失败 -> 修复 F20 后全通过）
- `tests/final_closure.test.cjs`：**3 passed, 0 failed**
- `tests/final_device_transport.test.cjs`：**5 passed, 0 failed**
- `tests/phase_a1_pairing.test.cjs`：**4 passed, 0 failed**
- `tests/phase_a_transport.test.cjs`：**12 passed, 0 failed**
- `scripts/test_audio_alignment_native.py`：**11 组全 PASS（exit=0）**（pre-fix 在第 252 行复现 F19 失败 -> 修复 F06+F19 后全通过）
- `tests/test_cpp_jetson_canvas.cpp`（MSVC `/std:c++17`）：**18/18 ALL NATIVE C++ TESTS PASSED**
- `tests/java/org/fglab/kurisu/AndroidRound1ContractsTest.java`（JDK 17）：**PASS（exit=0）**
- `tests/java/org/fglab/kurisu/WebViewCookieIsolationTest.java`（JDK 17）：**SUCCESS（exit=0）**
- **已知历史基线限制（不隐瞒）**：`scripts/test_phase_a_native.py` 中 `tests/phase_a_core_test.cpp` 与 `tests/java/org/fglab/kurisu/DeviceUdpClientTest.java` 未计入通过：`phase_a_core_test.cpp` 已通过 F19 与 NVS 测试编译并在运行期 NVS 段后于第 64 行 `test_protocol()` 命中 `#101` 扩展前的旧 `game_id=101` 断言（单独记为 **TC-01**，不替代 `F22`）；`DeviceUdpClientTest.java` 依赖外部 `org.json:json:20240303` JAR 而未在本地直接运行。

---

## 六、候选构建产物（未烧录板卡 / 未安装手机）

| 构建对象 | 工具链 | 输出路径（仓库外隔离缓存） | 文件大小 | SHA-256 |
| :--- | :--- | :--- | :---: | :--- |
| **ESP32-S3 候选固件 (`s3_led_matrix_test.bin`)** | ESP-IDF `v5.5.4` | `scratch/esp_build/s3_led_matrix_test.bin` | `1,606,400` B（`0x188300`，分区余量 `74%`） | `4EA2F1E7F6410FAB706061E79A6DCE385CECFAFE3D8A95E074D1FCE7A5BE70B7` |
| **Android 候选调试包 (`Kurisu_Amadeus_Pro_round1_candidate.apk`)** | Android SDK Build-Tools `35.0.0` + JDK 17 | `scratch/apk_out/Kurisu_Amadeus_Pro_round1_candidate.apk` | `2,861,537` B（v2/v3 签名校验 `true`；`versionCode=30`, `versionName=2.2.0`） | `66927EEA69E64C839AB29C4B4AF9E53F12F634A5346226F73F0512ADE4EAF865` |

---

## 七、后续人工实机验收检查清单（授权前禁止自动执行）

1. **固件与 APK 受控部署**（需用户明确授权并先回读/核对当前板卡 OTA 分区备份）：使用独立 `esptool` / `idf.py` 写 app 分区（不动 NVS / Jetson UART 接口），手动安装 `Kurisu_Amadeus_Pro_round1_candidate.apk`。
2. **手机热点零配置与切网恢复**：手机开启个人热点连接 PC 与 ESP32，确认 Android 端零 Token 自动发现并可稳定点歌、查状态、发起对话及开启视觉；验证 PC 晚于 App 启动、或手机从家庭 Wi-Fi 切到热点后的 `/api/health` 自动重连，并核实敏感路径 `/api/pro/memory` 仍被 401 拦截。
3. **手机前摄推流与视觉联动**：在 Android WebView 点击开启前置相机（`pet` / `fingertip` / `sandbox` / `gaze_game`），确认无弹窗卡死、5 阶段真实进度反馈正常、快速停止/切换来源不崩溃，且在 `gaze_game` 下切换摄像头或旋转角度后要求重新校准。
4. **连续对话与音质听感**：连续发送多轮语音对话并发起打断，核查 ESP32 扬声器 16k->24k TTS 无分块咔哒声、PC 音乐不同增益挡位（`0.25`–`0.75`）无破音且听感单调递进、打断收尾后麦克风仅恢复一次。
5. **Jetson UART 共存冒烟**：确认实板 `v2.3.1` 协议下 `ping` / `status` / `caps` 及模式 29 自定义画布与 PC/App 人工覆盖锁定逻辑仍 100% 正常工作。

---

## 八、Round 2 定向补丁与回归补充（基于 `36cf142` 独立复核）

- **改动范围**：`pc-agent-vision/multimodal_hub.py`、`pc-agent-vision/advanced_api.py`、`pc-agent-vision/access_control.py`、`pc-agent-vision/web_server.py`、`android-app/src/org/fglab/kurisu/MainActivity.java`、`tests/test_round1_rectification_regressions.py`、`tests/java/org/fglab/kurisu/AndroidRound1ContractsTest.java`、`docs/PRO_REVIEW_F01_F22_LEDGER.md`、`docs/PRO_ROUND1_VALIDATION.md`。
- **ESP32 生产代码变化**：**无变更**（沿用 Round 1 已验证的 `s3_led_matrix_test.bin`，`1,606,400` B，SHA-256: `4EA2F1E7F6410FAB706061E79A6DCE385CECFAFE3D8A95E074D1FCE7A5BE70B7`；注意当前实体 ESP32 板内仍为早先烧录固件，尚未烧录此候选包）。
- **Android Round 2 候选 APK**：已重新编译与 v2/v3 签名校验通过，输出 `scratch/apk_out/Kurisu_Amadeus_Pro_round2_candidate.apk`（`2,861,537` B，SHA-256: `2ADB03D4A375F48134C9121AB44548671F0E9CFFBFC2F78594BC27E2B86A3948`，尚未安装真机）。
- **Round 2 复测统计（最终修改后执行）**：
  - Python Pytest（22 组核心与 Round 2 新增测试）：**383 passed, 1 skipped, 0 failed**（`116 subtests passed`；含 `test_round1_rectification_regressions.py` **20 passed**——验证 `R1-01` 跨帧 ACK 隔离与多指令失败聚合、`R1-02` `GET /api/pro/camera/frame` 作用域凭据、`R1-03` `ChatPauseCoordinator` 释放-抢占两阶段线程 Barrier 竞争窗口、`R1-04` F05 `mirrored=false` 与 90/180 旋转及切源失效；跳过项仍为需 `KURISU_RENDERER_WASM` 的 `test_real_cpp_renderer_feeds_modes_canvas_and_games`）。
  - Node.js & JVM 回归：`test_phone_camera_requests.cjs` (12/12)、`final_closure.test.cjs` (3/3)、`final_device_transport.test.cjs` (5/5)、`phase_a1_pairing.test.cjs` (4/4)、`phase_a_transport.test.cjs` (12/12)、`AndroidRound1ContractsTest`（含 `R1-05` `MainActivity.onCreate` 无主动权限弹窗源码检查与 `onRequestPermissionsResult` 懒授权流程校验）与 `WebViewCookieIsolationTest` 全部退出码 `0` 通过。
  - 既有台账恢复：**F14～F22** 已在 `docs/PRO_REVIEW_F01_F22_LEDGER.md` 完整恢复原始编号与正式需求状态（`F16～F18` 保持正式后续待办需求，未降级）。

---

## 九、Round 3 最终功能收口、安全补强与构建验收（基于 `b3f8c4b`）

### 1. 本轮覆盖项与严格结论（`SOFTWARE_PASS` / `CONDITIONAL` / `FAIL`）

| 领域 / 编号 | 最终软件结论 | 实体硬件状态 | 关键代码与验证摘要 |
| :--- | :---: | :---: | :--- |
| **New Security P1 (`R3-01` PC 摄像头鉴权与会话所有权)** | **`SOFTWARE_PASS`** | `CONDITIONAL`（待真热点/手机实测） | `access_control.py`, `advanced_api.py`, `app.js`；普通灯控/音乐/手机前摄（`remote`）保持热点免手工 Token；未经管理员鉴权开启/关闭 `camera` 或套取/劫持他人会话在业务判断前即拦截返回 `401`（`PcWebcamAuthAndSessionOwnershipTests` 实测）。 |
| **F16（`#101` 语义规划 Schema / Prompt / NACK）** | **`SOFTWARE_PASS`** | `CONDITIONAL`（待真实语音联调） | `semantic_control.py`, `light_tools.py`, `web_app/index.html`；`WIRE_SCHEMA` 上限 `101`、`from_wire` 严格校型、`exact_plan` + Mock Ollama + 板端 NACK 诚实失败响应全通过。 |
| **F17 / F18（`#101《微光纪元》` C++/Python 对称沙盒迁移）** | **`SOFTWARE_PASS`** | `CONDITIONAL`（待实体 ESP32 板屏实测） | `game_101_microlight.h/.cpp`, `game_101_microlight.py`；原型差异对照与裁剪边界见 `docs/ARCADE_101_MICROLIGHT_INTEGRATION.md`。实现 `KEY_UP` 跳跃与 `KEY_A` 挖掘无冲突、负坐标 `FloorDiv`/`FloorMod`、popcount `VisitedBiomeCount() >= 4`、30 方块、`PutTile`/`put_tile` 有界 256 槽、4 敌人战斗与生态机制；C++/Python 同种子 180 帧像素校验和精确一致（`1362504820`）。 |
| **F14（Android 主题偏好持久化与凭据隔离）** | **`SOFTWARE_PASS`** | `CONDITIONAL`（待真机 APK 安装实测） | `MainActivity.java`, `app.js`；非敏感 `ui_theme`（`day`/`night`）独立存入 `SharedPreferences("config")` 并在 `onPageFinished()` 回填；`WebStorage.deleteAllData()` 仍全清 Token/Cookie（`AndroidRound1ContractsTest` 通过）。 |
| **F15（日间 HUD 与动态状态 WCAG AA 对比度）** | **`SOFTWARE_PASS`** | 已无头 Edge 实测 | `index.html`, `style.css`, `app.js`；移除硬编码亮色与 JS 内联色值，`test_ui_contrast_f15.cjs` 实测 `360x800`/`390x844`/`768x1024`/`1280x800` 零横向溢出，日/夜 HUD 对比度实测 `[day PLAY] 6.43:1~14.85:1` / `[night PLAY] 5.02:1~11.70:1`。 |
| **F21 / TC-01 / F22（测试隔离、历史断言与文档一致性）** | **`SOFTWARE_PASS`** | 适用 | `test_audio_discovery_alignment.py`（全隔离开源合成 `.wav` 夹具、`KURISU_REAL_MUSIC_DIR` 门控）、`phase_a_core_test.cpp`（`game_id=1..101` 合法、`>=102`/负/浮点/布尔/字符串拒绝）、`AGENTS.md`（写明 `~30 FPS / 33ms` 主循环与 `60 FPS` 理论峰值）及 `PRO_FINAL_REQUIREMENTS_BASELINE.md`（同步当前分支 `main`）。 |

### 2. Round 3 候选构建产物（重要：尚未烧录实体板 / 尚未安装真机）

| 构建对象 | 工具链 | 输出路径（仓库外隔离缓存） | 文件大小 | SHA-256 | 实体部署说明 |
| :--- | :--- | :--- | :---: | :--- | :--- |
| **ESP32-S3 Round 3 候选固件** | ESP-IDF `v5.5.4` | `scratch/esp_build_r3/s3_led_matrix_test.bin` | `1,618,912` B（`0x18b3e0`，分区余量 `74%`） | `C2FE815BD1D2EFA95591F5D6105ABA61E54BEFCA499C9056369B1A5BE39829A4` | **实体 ESP32 板内仍为早先烧录固件**，本轮未执行任何烧录 |
| **Android Round 3 候选 APK** | Android SDK `35.0.0` + JDK 17 | `scratch/apk_out/Kurisu_Amadeus_Pro_round3_candidate.apk` | `2,861,537` B（v2/v3 签名校验 `true`） | `C3526C8AFB1CADC4352AD90314508225ABB64149468EA6EDECAC38BACB3248B5` | **测试手机尚未安装此候选包**，待手动安装验收 |

### 3. Round 3 最终代码修改后实跑回归统计

- **Python Pytest**：
  - `tests/test_round3_closure.py` + `tests/test_audio_discovery_alignment.py`：**21 passed, 1 skipped**（跳过项为环境未设 `KURISU_REAL_MUSIC_DIR` 时的可选私人曲库测试）
  - `tests/test_pro_runtime.py` + 全部 `tests/test_arcade*.py`：**2022 passed, 1 skipped, 101 subtests passed**（跳过项为未设 `KURISU_RENDERER_WASM` 时的 WASM 渲染可选测试）
  - `test_local_asr.py`, `test_vision_voice_arcade.py`, `test_controller_validation.py`, `test_face_enrollment.py`, `test_delivery_regressions.py`, `test_final_closure.py`, `test_kurisu_palette.py`, `test_mario_game.py`, `test_power_limiter.py`：**68 passed, 17 subtests passed**
  - 核心与 Jetson 合集（`test_round1_rectification_regressions.py`, `test_music_library.py`, `test_music_follow.py`, `test_listener_lifecycle.py`, `test_audit_closure_defects.py`, `test_t03_bilingual.py`, `test_security_pairing_camera.py`, `test_phase_a_network.py`, `test_vision_takeover_and_permission_closure.py`, `test_final_vision_health.py`, `test_final_voice_startup.py`, `test_final_wireless_default.py`, `test_jetson_uart_protocol.py`, `jetson-nano/tests/test_jetson_nano.py`）：同进程合跑 **290 passed, 1 failed, 116 subtests passed**（唯一失败为紧随 `test_round1_rectification_regressions.py` 后运行 `test_listener_lifecycle.py::test_7i_shutdown_during_preparation_stage` 时触发的 Python 3.10 模块级 `web_server.chat_lock` 跨事件循环绑定报错）；独立进程运行 `tests/test_listener_lifecycle.py`：**68 passed, 8 subtests passed**。
- **原生 C++ / MSVC / ESP-IDF 验证**：
  - `scripts/test_phase_a_native.py`（含更新后 `phase_a_core_test.cpp` 与全套 `001`～`101` C++ 卡带 + JVM `BridgePolicy`）：**PASS (exit=0)**
  - `tests/test_cpp_101_microlight.cpp`（MSVC `/std:c++17`）：**PASS (exit=0)**，并与 Python 输出 `fb_csum=1362504820` 逐像素一致
  - `scripts/test_audio_alignment_native.py`：**11 组全 PASS (exit=0)**
  - `tests/test_cpp_jetson_canvas.cpp`：**18/18 ALL NATIVE C++ TESTS PASSED**
- **Node.js / 无头浏览器 / JVM**：
  - `final_closure.test.cjs` (**3/3**)、`final_device_transport.test.cjs` (**5/5**)、`phase_a1_pairing.test.cjs` (**4/4**)、`phase_a_transport.test.cjs` (**12/12**)、`test_phone_camera_requests.cjs` (**12/12**)、`test_ui_contrast_f15.cjs` (**PASS**, Edge headless 360/390/768/1280px `>= 5.02:1`)
  - `AndroidRound1ContractsTest`（含 F14 状态机与源码契约）、`WebViewCookieIsolationTest`：**PASS (exit=0)**；`DeviceUdpClientTest.java` 因需外部 `org.json` JAR 未在本地运行。

### 4. Round 3 新增真机/实板验收清单
1. 备份当前 ESP32 分区后烧录 `s3_led_matrix_test.bin`（`C2FE815B...`），在 `16×16` LED 灯板上启动 `#101《微光纪元》`，实操验证 `UP` 跳跃与 `A` 挖掘不冲突、`B` 攻击/建造耗材与夜敌刷新正常。
2. 手机手动安装 `Kurisu_Amadeus_Pro_round3_candidate.apk`（`C3526C8A...`），切换日间主题后断网恢复/冷重启，核实日间主题持久保留且 `WebStorage` 清理不残留旧配对凭据；在热点局域网内尝试免认证访问 `POST /api/pro/vision {"source":"camera"}` 应获 `401`，而手机前摄 `source="remote"` 免手工输入正常拉流。
