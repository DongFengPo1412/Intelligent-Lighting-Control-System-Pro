# Pro最终软件功能审计（2026-11-05）

> 首验后状态：7034d35版已获用户对实际深蓝灯板的确认；其余系统仍逐组待验。46065a9完成USB/帧通信修复、统一游戏入口、100款控制说明核对及匹配构建，尚待新的App写入授权和手机安装确认。具体证据及范围见[最终收尾记录](PRO_FINAL_CLOSURE.md)，原R01–R12与51项能力继续保留，不重新开展全工程开发。

基线开发分支`arcade-100-audit-and-elevation / ccbc28f`。未发现独立Phase C.1提交；用户本轮明确改为直接整机审计，不补做大规模小游戏收尾。本报告以[最终需求](PRO_FINAL_REQUIREMENTS_BASELINE.md)为依据，不把README或Agent旧完成报告作为唯一事实。

**结论：READY_FOR_HARDWARE，仅指采用[已验证兼容运行配置](PRO_HARDWARE_READINESS.md)后，可以开始经授权的首次受控设备验证。不是当前全部默认环境可用、不是所有18项原SRS原样完成、不是最终产品或硬件验收通过。**

## 1. 原本要实现什么、现在是什么架构

用户原十点的核心是：现有电脑本地运行可定制的红莉栖角色模型、板载采音与同一角色中日回复、长期记忆和真语义控制；单S3承载灯效/显示/桌宠/音频/游戏，PC摄像头实现视觉联动和音乐分析；一个Wi-Fi Web/Android控制端替代Blinker。新增100款街机是其中一个模块。单S3不等于在S3执行LLM/MediaPipe。

当前采用独立Pro固件+PC Python Agent，并非原生小智固件；SQLite词汇哈希/可选embedding RAG不是Mem0；逐点倒计时不是砂粒物理；16kHz单声道PCM不是原曲规格无损；WebGL曝光/光晕不是物理光学仿真。现有用户原始表达与后续澄清允许这些必要能力的实现路线，未把旧Agent的品牌和性能宣传升级为上板门槛。原生WakeNet/AEC完整体验、LoRA、任意流媒体平台、米制3D与研究级识别准确率不能伪报完成。

## 2. 模式和职责边界

|运行方式|可以做|依赖/限制|
|---|---|---|
|仅ESP32+灯板/音频外设|固件灯效、桌宠帧/时钟上下文反馈、现有游戏、PWM/RMT、NVS|没有本地7B模型、Whisper或摄像头推理；桌宠PC提供的上下文不应假装板端智能|
|Android APK直连ESP32|100款街机及原生配对输入；本轮恢复基本模式、亮度、音量、倒计时/停止与桌宠模式；完成帧回读|新版APK与固件需匹配；没有Python自动兜底；AI/视觉/曲库、画布写入及旧游戏专用控制走PC增强API|
|PC增强模式+APK/浏览器|本地模型/记忆/中日TTS、板载Wi-Fi采音、视觉、曲库、MIR、MCP、画布、统一界面|PC保持运行，模型/包/校准与配对配置正确；摄像头默认不打开|
|显式模拟模式|真实HTTP/WS/业务逻辑与模拟控制器；可选C++WASM预览|不执行物理输出，不代表真实LLM、声学、手机或板卡通过|

## 3. 本轮确定性缺陷及修复

1. **APK基础功能链断裂**：`app.js`只放街机，Java又拒绝非arcade/frame/status，导致灯效/亮度/音量/倒计时无PC不能用。新增严格白名单的`nativeDeviceApi`和Java字段/范围校验；保留配对/boot nonce/序号/重试/生命周期，UDP状态补亮度且加显示锁读取。状态/帧转换、负回执拒绝和读写失败隔离有JS、JVM和真实file页面验证。没有开放任意UDP指令或私钥/配对读取。
2. **语音假健康**：`connect_audio=False`仍启动线程、健康为真；麦克风拒绝未阻止启动。现在完整回滚并保留`last_start_error`，状态接口可见，恢复后可显式重试；正常生命周期夹具改成已连接假设备，另保留独立断连/拒绝/异常负例。
3. **正式无线要求与默认值冲突**：正常音频默认改Wi-Fi，USB仅显式诊断，未知transport配置拒绝，不静默回退USB。对应U219–U222而非新功能。
4. **底层失败假成功**：I2S RX enable/部分资源初始化失败如实返回并释放部分资源；PCM/麦克风/UDP任务创建分别检查，缺音频时保留灯光/控制；无消费者ring回收；PCM监听失败退出可再次启动。仅源码审查、真实编译和现有策略回归，未做实板FreeRTOS/I2S故障注入。
5. **视觉依赖失败不可见**：CV导入移入捕获/清理路径，错误状态可见且清除running/旧脸缓存；不因此自动打开摄像头。
6. **真实语音环境冲突**：共享环境HF2.4与transformers4.46.3不兼容；任务隔离覆盖HF0.36后导入恢复。默认cuDNN推理真实导致native abort，保留失败日志；显式`KURISU_ASR_DEVICE=cpu`及`KURISU_TTS_CUDNN=0`已用当前生产构造器/权重实际生成双语PCM。未改全局包、CUDA DLL、模型权重、音色、信号处理或板端音量。

## 4. 实际软件验证与不能扩大之处

- Python全发现包含语音/视觉/音乐/权限/游戏等，最终2190项：2189通过、1项条件跳过（未提供可选C++WASM产物）；原始计数及日志随交付报告保存。
- JS21项通过（原配对/按键16 + 基础设备5）；实际生产Java客户端UDP回环包含12类合法命令首ACK丢失重试、22类非法请求不上网、错误peer过滤/读写分离/生命周期中断。
- 生产C++主机测试：原B3 216局 + 额外51局、NVS host adapter、协议/重放/看门狗、音频短写/忙碌/优先策略。它们不是真实FreeRTOS/I2S/NVS验证。
- 100款真实HTTP/WS模拟集成、Chromium统一UI，以及独立真实file页面（假native设备边界）验证通过；不能替代Android安装/触控/Wi-Fi。
- 真实本地Ollama：非字面星光语义plan7、负ACK不说成功、隔离SQLite跨重启称呼回答、否定问句不控制。真实Sherpa KWS静音、缓存Whisper-Base CPU推理、现有GPT-SoVITS双语合成通过，不使用模拟回答或系统声线。
- 共同驻留链路实际执行了真实LLM→翻译→角色TTS→PCM/WAV，设备输出拦截、不开麦/不播放。该样例文本21.078秒、TTS12.281秒；包含当前冷/热状态与共同驻留条件，不是TTFT或稳定P95。**不能宣称达到中阶响应速度或已优化延迟。** 延迟/资源调优列P2，真实识别率、语气/双语等义、音质、传输及听感还需验收。
- ESP-IDF5.5.4完整构建；APK2.0.2(14)实际构建及v2/v3签名验证，网页资产与源码一致。没有安装/刷写/清NVS/迁移分区。

## 5. 51项独立状态

51项是审计能力拆分，不是声称用户原来列了51条。七级状态按用户定义；`INTEGRATION_VERIFIED`仅限所列真实软件组件联动范围。所有项目的当前硬件状态仍为NOT_TESTED。已有历史小场景验收只保留日期/条件，不外推本修订。

|ID|目标|状态|实现/证据|关键限制|
|---|---|---|---|---|
|SYS01|单ESP32-S3加PC算力中枢|SOURCE_IMPLEMENTED|firmware-s3/main/main.cc; display_manager.cc; wifi_manager.cc; ESP-IDF5.5.4 full build; code task ownership review|FreeRTOS actual startup/stack not executed on this revision|
|SYS02|PSRAM与内存/任务资源可观测|SOURCE_IMPLEMENTED|sdkconfig.defaults; main.cc LogRuntimeBudget; IDF rename/Kconfig actual configuration; final size log|Link size is not runtime heap; low-memory failure injection hardware pending|
|SYS03|NVS高分延迟初始化及失败保护|SOFTWARE_VERIFIED|arcade_score_store.cpp; main.cc; production C++ constructors/failure/reopen host adapter|Host adapter is not Flash power-cycle acceptance|
|SYS04|16MB双OTA和可恢复部署|SOURCE_IMPLEMENTED|partitions_16mb.csv; sdkconfig.defaults; Actual build fits6MiB app; migration guide review|No OTA update/rollback executed; do not flash app alone onto unknown layout|
|LED01|保留灯效与0..31既有编号|SOFTWARE_VERIFIED|display_types.h; effect_engine.cc; display_manager.cc; semantic_control.py; mode/schema contracts and firmware build|18 unused;25 countdown only;32 arcade lifecycle; not Mid pixel-identical proof|
|LED02|原生RMT DMA/完成帧/显示锁|SOURCE_IMPLEMENTED|display_hal.cc; display_manager.cc; SDK full build; frame/protocol/bounds tests|Not 0% CPU or measured60FPS; raw draw buffer plus completed PWM snapshot, not full async swap chain|
|LED03|统一亮度和功耗软件限制|SOFTWARE_VERIFIED|display_hal.cc; command_dispatcher.cc; brightness0..60 validation; JS/JVM negative cases; build|Limiter does not certify current/voltage/thermal safety; default20 unchanged|
|LED04|可选Gamma/固定配色和布线|SOFTWARE_VERIFIED|display_hal.cc; kurisu_sprites.h; existing palette/matrix tests; build|Gamma default retained; no temporal dithering, physical appearance pending|
|LED05|指定秒数逐点倒计时|SOFTWARE_VERIFIED|display_manager.cc StartCountdown; command_dispatcher.cc; schema/time boundary tests; native UI60sec/stop; firmware build|Proportional pixel countdown; not physical sand; precise physical duration/sound pending|
|LED06|世界线1.048596彩蛋|SOFTWARE_VERIFIED|interaction_engine.cc; semantic_control.py; existing renderer/protocol contracts; firmware build|Fictional visual effect; not measuring instrument; electrical sample sound not implemented|
|PET01|保留用户确认的16x16形象/覆盖|SOFTWARE_VERIFIED|kurisu_sprites.h; effect_engine.cc; palette/sRGB/mapping regression|No redesign; historical physical hue approval not extended to this firmware|
|PET02|昼夜/待机/眨眼/口型/疲劳状态|SOFTWARE_VERIFIED|advanced_api.py life_loop; effect_engine.cc FeedPet; pet lifecycle/context unit contracts|Not phoneme-level lip sync or scientifically validated emotion|
|PET03|手动显示优先于视觉自动切换|SOFTWARE_VERIFIED|light_controller.py; multimodal_hub.py process; test_pro_runtime manual-mode latch and re-enable cases|Physical gestures not re-tested|
|AI01|板载麦克风而非PC麦克风|SOURCE_IMPLEMENTED|audio_hal.cc; command_dispatcher.cc; network_audio.cc; voice_listener.py; PCM framing/priority/negative startup contracts; firmware build|No physical capture this task; CPU ASR profile avoids local cuDNN native crash|
|AI02|独立声学唤醒门加ASR确认|SOFTWARE_VERIFIED|wake_detector.py; voice_listener.py; real Sherpa model+silence; startup4+existing lifecycle29|No current human wake accuracy/FAR/FRR measurement; no board WakeNet|
|AI03|ASR/VAD/完整轮次与连续对话|SOFTWARE_VERIFIED|voice_listener.py; conversation_session.py; real cached Whisper-Base CPU load/silence; VAD/session/lifecycle tests|Silence is not speech accuracy; noise/latency/user barge-in physical pending|
|AI04|原角色模型先中后日并失败静音|INTEGRATION_VERIFIED|voice_engine.py; bilingual_guard.py; real VoiceEngine role weights->bilingual PCM/WAV without playback; T03 regression|Default local GPU/cuDNN path abort reproduced; explicit compatible profile only; voice quality not listened|
|AI05|本地开源LLM与可定制人格|INTEGRATION_VERIFIED|kurisu_agent.py; kurisu_prompt.py; Modelfile.kurisu; data/kurisu_lore_v1.json; actual Ollama kurisu semantic/chat/memory limited integration|Persona naturalness/source facts require human review; LoRA/pretraining not required|
|AI06|真实语义规划及结构化验证|INTEGRATION_VERIFIED|semantic_control.py; light_tools.py; pro_tools.py; actual semantic stars plan7; schema/negative/question regression|Not every utterance is accurate; malformed/conflicting plan fails closed|
|AI07|板端确认前不得宣称操作成功|INTEGRATION_VERIFIED|kurisu_agent.py; wifi_gateway.py; light_tools.py; actual Agent negative ACK boundary; production UDP retry/ID loopback|Device boundary intercepted in model test; actual LED execution not verified|
|AI08|超时/关停/资源恢复/准确健康|SOFTWARE_VERIFIED|web_server.py run_chat/cleanup; voice_listener.py start/is_healthy; lifecycle29; new failed-connect/mic-reject/restart4; real HTTP|Manual retry via authenticated /api/retry_warmup after device recovery; no claim killing native threads|
|AI09|动态双语等义和翻译失败可见|SOFTWARE_VERIFIED|bilingual_guard.py; voice_engine.py; web_server.py; T03 contracts; limited real translation samples|Deterministic guards do not prove arbitrary semantic equivalence; human bilingual review still pending|
|MEM01|用户本名/称呼/偏好持久化|INTEGRATION_VERIFIED|memory_store.py; kurisu_agent.py; actual isolated SQLite close/reopen+Ollama nickname answer; correction tests|No real personal database accessed; nickname translation style not fully certified|
|MEM02|精确更正/遗忘/资料及他人保护|SOFTWARE_VERIFIED|memory_store.py; advanced_api.py memory/documents; property-domain/document/lore/third-party regression; management cases|Single local user model, not multi-tenant authorization|
|MEM03|RAG参考资料不变成硬件指令|SOFTWARE_VERIFIED|memory_store.py search; kurisu_agent.py _converse; retrieval/source/alias/tool-safety contracts|Not Mem0; unverified lore excluded; raw original-game corpus not claimed complete|
|TOOL01|全功能工具参数/权限与失败回传|SOFTWARE_VERIFIED|mcp_server.py; pro_tools.py; web_server.py; advanced_api.py; JSON-RPC/WS/schema/rate/access tests|Tests are host/software; arbitrary extension/plugin execution not enabled|
|TOOL02|可选小智Opus兼容入口|SOFTWARE_VERIFIED|xiaozhi_bridge.py (OpusCodec/XiaoZhiConnection); real Opus codec round-trip and fake ASR/Agent protocol tests|Not native WakeNet firmware or verified acoustic duplex|
|VIS01|单一摄像头所有者与退出释放|SOFTWARE_VERIFIED|multimodal_hub.py; advanced_api.py; capture lifecycle/face freshness/copy contracts; missing-import error test|No camera opened; actual capture driver/recognition pending|
|VIS02|21点指尖/捏合抓投/相对深度|SOFTWARE_VERIFIED|visual_features.py; multimodal_hub.py; interaction_engine.cc; fingertip_tracker.cc; geometry/command/timeout/software contracts; firmware build|Monocular relative depth, not calibrated metric3D; >60FPS not measured|
|VIS03|凝视校准与头部姿态|SOFTWARE_VERIFIED|visual_features.py; app.js calibration; multimodal_hub.py; rank/finite calibration; uncalibrated gaze refuses game control|Training fit not independent gaze accuracy|
|VIS04|人脸登记/身份问候及失效保护|SOFTWARE_VERIFIED|identity_store.py; multimodal_hub.py; face enrollment6; stale/missing/stopped sample protection|Not security authentication; enrolled real faces not inspected/published|
|VIS05|表情/疲劳/离席联动|SOFTWARE_VERIFIED|visual_features.py; multimodal_hub.py; advanced_api.py; synthetic geometry/event/manual-priority contracts|No medical/emotion accuracy certification; optional scene refinement is P2|
|VIS06|蛇/方块手势或视线体感|SOFTWARE_VERIFIED|multimodal_hub.py; game_engine.cc; calibration gate/dwell/manual override tests; firmware build|Distinct from arcade Target IDs33/41; no new camera test|
|MUS01|本地曲库/语音点歌/队列切歌|SOFTWARE_VERIFIED|music_library.py; music_commands.py; advanced_api.py; music library scan/path/id/queue/cancel/persistence API regression|No real user library read or speaker playback; decode-before-stop usability P2|
|MUS02|上传/直接网络音源解码播放|SOFTWARE_VERIFIED|music_engine.py; advanced_api.py; generated audio decode/limits/negative routes regression|Not arbitrary DRM/account platforms; long multichannel decode memory budget P2|
|MUS03|16频带FFT/RMS/flux/onset/节拍灯光|SOFTWARE_VERIFIED|music_engine.py; spectrum_engine.cc; interaction_engine.cc; 7 synthetic/timing tests; real production renderer/firmware build|Beat heuristic; no objective board sound-to-light latency measurement|
|MUS04|WiFi PCM双向音频与麦克风优先|SOFTWARE_VERIFIED|network_audio.py; network_audio.cc; audio_hal.cc; command_dispatcher.cc; network audio protocol/error/cancel tests; bounded PCM/SFX native policy; build|Actual WiFi audio not re-tested; not original-format lossless transport|
|MUS05|TTS/音乐/麦克风/游戏音效不争用|SOFTWARE_VERIFIED|audio_hal.cc; arcade_audio_task.cc; arcade_sound.h; music_engine.py; production bounded short-write/busy/dedup/priority host tests|DMA/listening/load tests pending; no long blocking writes added|
|APP01|一套统一Web和可安装APK|INTEGRATION_VERIFIED|web_app/index.html/app.js; MainActivity.java; build_apk.py; APK2.0.2(14) v2/v3 signature; identical assets; browser tests|APK not installed; Chromium is not WebView hardware acceptance|
|APP02|无PC基本灯控/倒计时/桌宠模式|INTEGRATION_VERIFIED|app.js; arcade_transport.js nativeDeviceApi; DeviceUdpClient.java; wifi_manager.cc; production file UI fake bridge;21 JS tests; real JVM UDP12 valid/22 invalid|Hardware not tested; PC AI/music/vision routes intentionally not converted|
|APP03|100款街机直连/多键/释键/状态|INTEGRATION_VERIFIED|arcade_transport.js; DeviceUdpClient.java; arcade_manager.cpp; 100 HTTP;21 JS; JVM loopback; Chromium2 multitouch mappings|Physical touch-to-LED latency/phone not verified; telemetry failure isolated|
|APP04|完成帧回读/像素画布/WebGL预览|SOFTWARE_VERIFIED|app.js; display_manager.cc SnapshotFrame; advanced_api.py; full-frame validation/canvas contracts; native frame UI|Not optical digital twin; independent canvas writes/legacy gamepad still use PC enhanced API|
|APP05|断线错误/配对/版本兼容提示|INTEGRATION_VERIFIED|paired_http.js; arcade_transport.js; MainActivity.java; 401 one-shot retry; unconfirmed ACK failure; request IDs; browser|No silent simulator fallback; older firmware lacks brightness ACK and is visibly rejected|
|NET01|UDP配对/nonce/序号/幂等请求|INTEGRATION_VERIFIED|network_auth.cc; udp_request_guard.h; wifi_gateway.py; DeviceUdpClient.java; production guard/native/JVM actual loopback/ID collision tests|Plain UDP not encryption; token sniffing on hostile LAN remains risk|
|NET02|HTTP/WS权限/Origin/负载/速率|INTEGRATION_VERIFIED|access_control.py; web_server.py; mcp_server.py; access middleware/WS rate1008/loopback default tests|Default127.0.0.1; remote phone PC enhanced needs explicit configuration|
|NET03|USB供电不改变无线通信选择|SOFTWARE_VERIFIED|light_controller.py default wifi; explicit usb diagnostic; new2 transport configuration negatives; network ACK tests|Power connector does not select audio transport; no automatic USB fallback|
|GAME01|100正式ID保留注册及基础生命周期|INTEGRATION_VERIFIED|games_100_manifest.json; registered_games.json; CMake; arcade_manager.cpp; 100 registry/source tests; production native rounds;100 HTTP/browser|56 success/goal paths,44 pending; not100 product-quality certification|
|GAME02|难度/动作音效/计分与持久化|PARTIALLY_IMPLEMENTED|game_acceptance.csv; docs/ARCADE_PHASE_C.md; 216 B3+51 extra input rounds; sound/NVS adapter contracts|45 three-tier certified;55 generic-only action sounds;4 RNG initial-state differences; physical scores pending|
|DEP01|首次部署备份/分区核对/USB恢复|READY_FOR_HARDWARE|docs/PRO_HARDWARE_READINESS.md; ARCADE_PHASE_C_HARDWARE_READINESS.md; partition/build/config review; no hardware actions|Ready to begin controlled validation only; not permission to flash or erase|
|DEP02|可复现兼容语音运行配置|INTEGRATION_VERIFIED|requirements-voice-constraints.txt; pro_deployment_preflight.py; voice runtime flags; configuration preflight passed; real production VoiceListener/VoiceEngine silent inference|Stock env HF2.4 incompatible; default cuDNN native abort; compatible profile required, not globally repaired|
|DEP03|私人数据隔离与可追溯文档|SOFTWARE_VERIFIED|pro_paths.py; .gitignore; final source docs; test data dirs isolated; inherited hashes preserved; tracked-file inventory|36 historical tracked face files need owner classification; no deletion/history rewrite authorized|

## 6. 必要功能、部分实现与剩余问题

必备主链的真实源码已具备，没有以空接口代替模型/音频/视觉执行路径；受控软件验证覆盖其主要逻辑，但并非所有链路都连接了实物。100款游戏已注册，56款成功路径、45款三档证据；55款动作音效/44款成功认证/4款随机初态是未完成品质项，不能改写成全产品完成，也不按最新用户决策无限阻止整机继续。

必要部署修复是新版APK/固件匹配、正确Python及隔离语音兼容profile、真实配对/私有网络配置；均有明确方案。共享GPU库的根本修复、联合驻留延迟、长歌曲内存预算、坏切歌体验、额外关卡/原作风格和所有性能指标可暂缓；不能把真实crash忽略，必须先采用已验证profile。

详见[差距分级](PRO_FINAL_GAP_LIST.md)、[验收CSV](PRO_FINAL_ACCEPTANCE_MATRIX.csv)与[上板闸门](PRO_HARDWARE_READINESS.md)。达到首次受控验证条件后停止软件扩展，不自动开启新阶段。
