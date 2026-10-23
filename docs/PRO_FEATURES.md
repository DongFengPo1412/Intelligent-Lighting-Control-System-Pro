# 高阶功能实现与运行接口

**简体中文** · [English](PRO_FEATURES.en.md) · [日本語](PRO_FEATURES.ja.md) · [项目首页](../README.md)

2026-10-23 代码版本。新增功能完成源码接入、离线检查与构建；**没有烧录、开摄像头、录音、发声或进行实机验收**。历史验收只适用于当时版本。

## 18 项需求对应关系

原始 [SRS](HIGH_STAGE_SYSTEM_SPEC_18.md) 中的品牌级形容词、性能指标和硬件假设不作为完成证明。下表说明当前工程如何实现各项功能，以及与原设计的差异。

| 项 | 当前实现与入口 | 范围与差异 |
| --- | --- | --- |
| 1 单 S3 | `firmware-s3/main/main.cc`，显示 Core 1，网络／音频 Core 0 | 单 S3 执行；大模型与视觉仍在 PC，不能称所有推理都在板端。 |
| 2 RMT DMA | `display/display_hal.cc`，矩阵启用 DMA | 沿用原生驱动；没有 CPU 零占用的测量结果。 |
| 3 缓冲与 Gamma | 绘图缓冲＋完成帧 PWM 快照；统一显示锁；`gamma` 可选 | 不是异步交换队列。Gamma 默认关闭以保护既有配色；没有稳定 60 FPS 的实测。 |
| 4 经典灯效 | 原 0–25（18 空缺），单块 16×16 逐行蛇形映射 | 保留现有高阶算法与坐标，不声称和 Mid 每帧相同。 |
| 5 本地 LLM | `Modelfile.kurisu`、`semantic_control.py`、Ollama | 角色配置基于 Qwen2.5；没有新训练模型或重新评测模型性能。 |
| 6 人格／长期记忆 | `memory_store.py`、`kurisu_agent.py`；SQLite、偏好记忆、资料分块、RAG | 默认为本地词汇哈希检索；配置 embedding 模型后可用本地语义向量。不是 Mem0 集成。 |
| 7 对话／MCP／小智 | 连续轮次；MCP HTTP/WS；独立小智 v1 Opus 适配；可选 Wi-Fi 双工／回声参考／打断 | 当前 Pro 固件仍是 **PC 声学唤醒**，没有移植板端 WakeNet。小智原生客户端可连接适配入口；不等于把 Pro 固件换成原生小智。双工路径尚未声学验收。 |
| 8 倒计时 | 专用 1–86400 秒命令、像素进度、结束动画与异步提示音 | 保留用户此前验收的进度显示；不是物理砂粒仿真。计时精度与提示音需以后实测。 |
| 9 世界线 | 模式 28：数字滚动后固定 `1.048596`，小数点与提示音序列 | 作品彩蛋，不是真实测量仪；声音是提示音，不是采样电流音效。 |
| 10 手势沙盒 | `multimodal_hub.py`、`interaction_engine.cc`；21 点、捏合抓取、释放投掷、相对 z 推动、重力反弹和波纹 | 单目相对深度，不是标定的米制 3D。没有 >60 FPS 实测。 |
| 11 视线／头姿 | 虹膜比值＋九点仿射校准、solvePnP 头姿、瞳孔偏移、离席环境微光 | 头姿内参为近似；训练点拟合误差不是独立视线准确率。 |
| 12 表情提示 | EAR、PERCLOS、嘴部／眉部几何；疲劳／皱眉提示、暖光关怀、持续微笑烟花 | 启发式互动信号，不是已验证的心理／医疗分类器。 |
| 13 桌宠生命周期 | 不同的待机／闭眼／口型帧，夜间闭眼、晚间哈欠、缺席与疲劳变暗、时钟上下文 | 原待机配色及用户四格肤色、两格熄灭、裤子同外套的覆盖保留。口型仍非音素同步。 |
| 14 无线音乐 | TCP 8889 双向 PCM；本地上传与 HTTP(S) 音频直链；接收／播放计数检查 | 统一 16 kHz/PCM16/单声道，传输未再有损压缩，但音乐预处理不等于原素材无损。 |
| 15 MIR 流体 | 能量、正向频谱通量、onset、节拍间隔／相位、频谱与阻尼波场 | 断流能量衰减；节奏估计是启发式，没有曲库准确率／音画同步实测。 |
| 16 体感游戏 | 手势／校准视线经停留防抖控制蛇与方块 | 同一摄像头所有者；手动选别的模式会暂停自动接管，重新启用视觉恢复。 |
| 17 DDA | 手动 0–1 难度、启用／关闭自适应、依据操作间隔和表情提示有界微调 | 蛇／方块速度有下限；不是已证明维持“心流”的研究结果。 |
| 18 跨端／3D | `/pro.html`、真实帧回读、像素编辑导入导出、原生 WebGL；Android 可配置主机与 DNS-SD 发现 | 可用真实 C++ WASM 引擎离线预览。曝光／光晕是屏幕可视化，不是光学数字孪生或物理漫反射求解。Android 未安装实测。 |

以上是功能层的实现映射。原生板端 WakeNet、物理沙粒、原音乐规格无损和物理光照仿真仍与原 SRS 有差异；不能将这些条款标为原样全部实现。性能与主观体验也不由编译结果推定。

## 服务、模型与数据

PC 3.10 环境安装 `pc-agent-vision/requirements-pro.txt`。它覆盖控制、Web、视觉、MIR、MCP 和 Opus 适配；现有 Whisper／KWS／Torch／GPT-SoVITS 的环境、模型和参考音频仍按 [语音恢复记录](VOICE_CONTROL_RECOVERY.md) 准备，不会由模拟模式自动下载。

运行入口仍为 `pc-agent-vision/web_server.py`，新增页面 `/pro.html`。新页面通过实际 API 操作，不使用原页面的独立动画代替硬件回读。

| 配置 | 默认／含义 |
| --- | --- |
| `KURISU_DATA_DIR` | `%LOCALAPPDATA%/KurisuPro`；持久记忆、登记人脸、视线校准和设备地址。不是仓库文件。 |
| `KURISU_CACHE_DIR` | `~/.codex/cache/tasks/kurisu-runtime-<pid>`；语音缓存和诊断。测试时显式使用本次任务缓存。 |
| `KURISU_CONTINUOUS` | `1`；回复后继续等下一句，空闲 10 秒或明确结束语退出。设 `0` 使用单轮。 |
| `KURISU_AUDIO_TRANSPORT` | `usb`；设为 `wifi` 才使用新增 TCP PCM。保留已验收 USB 音频转换、70% 板端音量与原处理基线。 |
| `KURISU_BARGE_IN` | 默认关闭；`1` 且 Wi-Fi 音频时启用实验性参考回声处理和唤醒打断。KWS 后仍需无提示 ASR 确认。 |
| `KURISU_ECHO_DELAY_MS` | `120`；只用于实验性软件回声参考对齐，不代表已标定声学延迟。 |
| `KURISU_AUTO_MEMORY` | `1`；明确的第一人称称呼／喜好／习惯句可保存为偏好。`记住：…` 手动保存；页面可查看、删单条或清空。设 `0` 关闭自动偏好抽取。 |
| `KURISU_EMBED_MODEL` | 不设时用词汇哈希；设为已安装的 Ollama embedding 模型后使用 `/api/embed`。切换表示时按记录重新生成向量。 |
| `OLLAMA_HOST` | embedding 服务默认 `http://127.0.0.1:11434`；聊天仍使用已有 `OPENAI_BASE_URL`。 |
| `KURISU_RENDERER_WASM` | 可选的已构建 `engine.wasm`，只在模拟模式使用。未配置时模拟器只提供有限静态样例，不能预览所有动态模式。 |
| `KURISU_NODE_EXE` | 默认 `node`；用于离线 C++ 渲染进程。 |

保存的记忆、资料、人脸和校准都在本机。检索结果只进入聊天参考上下文，不被解析成灯板控制计划。新模型、个人样本和运行数据均不提交 Git。

## 完全离线的预览

下列命令只启动模拟服务。不会扫描串口、发送 UDP、加载模型、开摄像头、录音或播放声音。服务仅绑定 `127.0.0.1`。

```powershell
$task = Join-Path $env:USERPROFILE ('.codex\cache\tasks\pro-preview-' + [guid]::NewGuid().ToString('N'))
$env:KURISU_DATA_DIR = Join-Path $task 'data'
$env:KURISU_CACHE_DIR = Join-Path $task 'cache'
python -B pc-agent-vision/web_server.py --simulate --no-audio --port 8086
```

访问 `http://127.0.0.1:8086/pro.html`。模拟聊天只执行明确字面灯效命令；不会伪装成本地模型已经理解任意语义。

如需预览真实 C++ 动画，先准备 Clang/WebAssembly 和相应 sysroot，生成到同一任务缓存，然后启动服务：

```powershell
python -B scripts/build_offline_renderer.py --clang <clang.exe> --sysroot <wasm-sysroot> --output-dir "$task\engine"
node pc-agent-vision/offline_renderer.js "$task\engine\engine.wasm" --test
$env:KURISU_RENDERER_WASM = "$task\engine\engine.wasm"
python -B pc-agent-vision/web_server.py --simulate --no-audio --port 8086
```

此模块编译正式 Effect/Game/Spectrum/Interaction/Fingertip 引擎，替换时钟、LED HAL 和音频状态；不是 ESP32 调度器、I2S、网络或电源仿真。模拟倒计时另用进度样例，不冒充真实计时任务。WASM 模块不随 Git 分发。

## 显示、视觉、音乐与游戏

- 直接模式为 **0–31，排除 18、25**；25 必须通过倒计时命令传入时长。新增 26 指尖、27 光球、28 世界线、29 画布、30 MIR 流体、31 环境微光。
- 指尖组员源码已加入正式 CMake、枚举、命令解析、显示锁与模式调度。独立入口见 [接入说明](../INTEGRATION.md)；日常推荐使用统一 Web 视觉入口，避免多个程序争用摄像头。
- 在页面启用视觉才打开摄像头；默认不启用。先选择游戏 19／21，再选择手势／视线游戏；视线游戏需要九点校准，注视橙色点后按空格采样。改变摄像头索引前先停止。
- 用户选择其他显示模式／倒计时后，自动视觉切模暂停；重新启用相应视觉功能恢复。人脸登记是本地 LBPH 问候，不是身份安全认证。 登记要求摄像头运行、当前检测到人脸且样本年龄不超过 1 秒；无人／空裁剪／停止／采集失败会失效缓存，并在锁内使用图像副本。6 项离线回归通过，不代表识别精度验证。
- 上传音频或提供能直接返回音频的 HTTP(S) 地址；最大 20 MiB、最长 30 分钟。并非接入所有需要账户、DRM 或跳转解析的音乐平台。播放和特征发送失败会在状态中显示；停止音乐会中断推送。
- DDA 的操作间隔、面部几何只是调节提示；可关闭自适应并手动设置。原有游戏规则和结算保留。

## 协议

### HTTP／WebSocket

原有 `/api/chat`、`mode`、`volume`、`cmd`、`game`、`status`、`ceremony` 与 `/ws` 保留。新增：

| 路由 | 用途 |
| --- | --- |
| `GET /api/pro/frame` | 完成帧，`pixels` 为 1536 个十六进制字符，逻辑行优先；`frame_source` 明确区分硬件 PWM 和模拟。 |
| `POST /api/pro/canvas` | `{"hex":"<256 RGB pixels>"}`；整帧验证后原子提交，再切模式 29。 |
| `GET /api/pro/status` | 视觉、音乐、连续轮次和小智连接状态。 |
| `GET/POST/DELETE /api/pro/memory` | 记忆列表、保存、按 id 删除；POST `{"clear":true}` 清空。 |
| `POST /api/pro/documents` | `{"text":"..."}` 分块导入参考资料，最多 100000 字符。 |
| `POST /api/pro/vision` | `{"enabled":true,"mode":"pet","camera":0}`；mode 可选 pet/fingertip/sandbox/gesture_game/gaze_game/identity。 |
| `POST /api/pro/calibrate` | 至少 5 个非共线 `[iris_x,iris_y,target_x,target_y]` 样本，保存校准。 |
| `POST /api/pro/enroll` | `{"name":"..."}` 登记当前检测到的脸。 |
| `POST /api/pro/track-calibrate` | 指尖输入窗口 x0/y0/x1/y1 及 invert_x/invert_y。 |
| `POST /api/pro/difficulty` | `{"level":0.5,"adaptive":true}`。 |
| `POST /api/pro/music-upload` | 请求体为音频文件字节，不是 multipart。 |
| `POST /api/pro/music` | `{"url":"..."}` 或 `{"stop":true}`。 |
| `POST /api/pro/observations` | 仅模拟环境：合成观察输入，用于离线流程测试。 |
| `POST /api/pro/device-tool` | 调用已连接原生小智设备实际广播的 MCP 工具；name/arguments 按该设备 schema 校验。 |

### MCP

HTTP `/mcp` 支持 initialize、ping、tools/list、tools/call 和会话删除。初始化返回 `Mcp-Session-Id`，后续带回该头；通知返回 202。支持协议 2024-11-05、2025-03-26、2025-06-18 的 JSON 响应子集，不提供 SSE 流。`/ws` 也接受 `{"type":"mcp","payload":{...JSON-RPC...}}`。

工具包含既有灯效／音量／计时、`self.matrix.set_canvas/get_frame`、`self.game.set_difficulty`、`self.memory.remember/search` 和 `self.sensors.get_context`。结构化视觉／音乐上下文也提供给角色聊天，带有启用状态、时效和模拟标记，不把旧观测当成正在看见。Schema 校验和设备 ACK 都参与结果判断；调用出错返回 isError，不能把它播报为成功。

### 两种无线音频入口

**Pro PCM**：PC 配置 `KURISU_AUDIO_TRANSPORT=wifi`，连接 S3 TCP 8889。帧头 `KAP1 + kind(u8) + length(u16BE)`；负载最多 2048 字节，PCM16LE/16000/mono。kind 4 握手串 `pcm16le/16000/mono/v1`，1 下行音频，2 上行麦克风，5 心跳。控制仍走 UDP ACK，播放结果核对 I2S 采样计数。

**原生小智 Opus 适配**：启动前配置 `KURISU_XIAOZHI_BRIDGE=1`，原生客户端连接 `ws://<PC-IP>:8080/xiaozhi/v1/`，`Protocol-Version: 1`，hello 指定 Opus/16000/mono、20/40/60 ms。适配 listen/start/stop、abort、STT/LLM/TTS、Opus 帧和双向 MCP 工具发现。此模式不再同时启动 Pro 的 PC 麦克风监听器，避免两个语音入口争用。

可用 `KURISU_XIAOZHI_TOKEN` 要求客户端发送 Bearer token。ASR 通过已有本地 Whisper 资源懒加载，默认 CPU int8；配置 `KURISU_ASR_MODEL` 和 `KURISU_ASR_DEVICE` 改变模型／设备。语音合成沿用角色模型。这是服务器适配，不会改写、构建或烧录外部小智工程；未做真实原生客户端联调。

原生小智 Opus 与 Pro KAP1 PCM **不可互换**。当前 HTTP／UDP／PCM 部署面向受信任实验局域网，不建议直接公网开放。

## Android 与构建

Android 首次运行输入 PC 地址，或发现 `_kurisupro._tcp` 服务并选择连接；地址持久保存。不能连接时显示明确提示，不把离线页面当作仍可控制设备。PC 通过可选 zeroconf 发布 DNS-SD；防火墙与局域网环境需以后实测。

构建脚本不再覆盖 MainActivity、Manifest、资源或仓库内 assets；产物与临时 debug 密钥写到显式的外部目录。需要项目原有 aapt2/R8、JDK、android.jar 和 SDK Build Tools（含 zipalign/apksigner）：

```powershell
python -B android-app/build_apk.py --work-dir "$task\android-build-new" --output "$task\Kurisu-Pro-debug.apk" --build-tools <SDK-build-tools-dir> --java-home <JDK-dir> --android-jar <android.jar>
```

构建目录与输出均必须是新路径。APK 为独立测试签名，仓库里的旧 v1.0 APK 不代表本轮源码；本轮不覆盖旧 APK、不安装到手机。

ESP32 构建继续使用 ESP-IDF 5.5.4。正式入口关闭 `PRO_MATRIX_DIAGNOSTIC` 和 `PRO_HAIR_CALIBRATION`；离线构建使用隔离源码副本和公开 Wi-Fi 示例，私有配置不复制到产物。**本轮不运行 flash／monitor。**

## 离线验证与后续实机项目

测试入口 `tests/test_pro_runtime.py`、`tests/test_controller_validation.py`、`tests/test_face_enrollment.py`、`scripts/test_interaction_regressions.py`、`scripts/test_semantic_control.py`、`tests/test_kurisu_palette.py`、`tests/test_display_engines.py` 和离线渲染器 `--test`。测试时设置 `KURISU_TEST_TMP` 为独立任务缓存；可用 `KURISU_TEST_RENDERER_WASM` 启用真实 C++ 渲染联通检查。不要运行名称相似的历史上板测试脚本。

需要以后实测的内容包括：无线音频断线／丢包与音质，AEC／误打断，连续语音，视觉阈值和校准独立误差，灯光亮度与 Gamma，提示音，刷新率／CPU／栈余量，Android 安装／服务发现与长时间运行。源代码和模拟器提供实现依据，不替代这些结果。

协议参考：[小智 WebSocket](https://xiaozhi.dev/docs/development/websocket/)、[小智 MCP](https://xiaozhi.dev/docs/development/mcp/protocol/)、[Ollama embeddings](https://docs.ollama.com/api/embed)、[Android apksigner](https://developer.android.com/tools/apksigner)。同时参考了本机小智 2.2.4 的 WebSocket v1 实现。
