# Pro 技术说明

**简体中文** · [English](technical-notes.en.md) · [日本語](technical-notes.ja.md) · [项目首页](../README.md)

[源码](#source-map) · [驱动](#driver) · [显示与游戏](#display) · [语音与智能体](#voice-agent) · [通信](#transport) · [独立实验](#vision-audio) · [状态与证据](#implementation-status)

审计基线为 `d548868`。以当前源代码、构建配置和能找到的记录为依据；[18 项规格](HIGH_STAGE_SYSTEM_SPEC_18.md)作为历史需求，不作为完成证明。

<a id="source-map"></a>

## 核心模块与源码对应

| 入口／模块 | 文件 | 实际职责 |
| :--- | :--- | :--- |
| 固件入口 | [main.cc](../firmware-s3/main/main.cc)、[CMake](../firmware-s3/main/CMakeLists.txt) | 初始化显示、板载 LED、I2S、USB 与 APSTA/UDP，默认桌宠17；可显式选择独立诊断入口。 |
| 像素输出 | [display_hal.cc](../firmware-s3/main/display/display_hal.cc)、[matrix_layout.h](../firmware-s3/main/display/matrix_layout.h) | 一个256像素应用缓冲、蛇形地址、全局亮度、RMT DMA与刷新。 |
| 模式与图形 | [display_manager.cc](../firmware-s3/main/display/display_manager.cc)、[effect_engine.cc](../firmware-s3/main/display/effect_engine.cc) | 模式初始化、任务调度、计时、灯效、表情与桌宠。 |
| 游戏／频谱 | [game_engine.cc](../firmware-s3/main/display/game_engine.cc)、[spectrum_engine.cc](../firmware-s3/main/display/spectrum_engine.cc) | 两种游戏、结算、频带绘制与峰值保持。 |
| 命令／网络 | [command_dispatcher.cc](../firmware-s3/main/protocol/command_dispatcher.cc)、[wifi_manager.cc](../firmware-s3/main/protocol/wifi_manager.cc) | USB文本／PCM分流、音频环形缓冲、JSON/文本命令、UDP请求回执缓存。 |
| I2S | [audio_hal.cc](../firmware-s3/main/audio/audio_hal.cc) | INMP441输入、MAX98357A输出、PCM转换、播放互斥与空闲停钟。 |
| PC服务 | [web_server.py](../pc-agent-vision/web_server.py)、[light_controller.py](../pc-agent-vision/light_controller.py)、[wifi_gateway.py](../pc-agent-vision/wifi_gateway.py) | HTTP/WS、串行聊天、USB音频与UDP确认。 |
| 语音／计划 | [voice_listener.py](../pc-agent-vision/voice_listener.py)、[wake_detector.py](../pc-agent-vision/wake_detector.py)、[semantic_control.py](../pc-agent-vision/semantic_control.py) | VAD、KWS、Whisper、语义模式目录与参数校验。 |
| 对话／合成 | [kurisu_agent.py](../pc-agent-vision/kurisu_agent.py)、[voice_engine.py](../pc-agent-vision/voice_engine.py)、[light_tools.py](../pc-agent-vision/light_tools.py) | 短期会话、工具执行、双语回复、GPT-SoVITS及缓存。 |
| 客户端 | [Web JS](../pc-agent-vision/web_app/app.js)、[Android Activity](../android-app/src/org/fglab/kurisu/MainActivity.java) | 页面控制、独立Canvas动画与WebView封装。 |

Web服务不会自动启动 `vision_gesture.py`、`vision_face.py`、`vision_tracker.py` 或 `audio_visualizer.py`。根目录 `fingertip_tracker.*` 未被正式CMake列入，命令解析与枚举也没有26/track；[INTEGRATION](../INTEGRATION.md)是待实施接入方案。

<a id="driver"></a>

## 单块面板、RMT与调度

当前为单块16×16、正视左上DIN、偶数行向右／奇数行向左；越界返回-1，所有二维绘图共用：

```math
i(x,y)=16y+\begin{cases}x,&y\bmod2=0\\15-x,&y\bmod2=1\end{cases},\qquad 0\le x,y<16
```

GPIO17输出GRB的WS2812数据。`led_strip_new_rmt_device`配置10 MHz分辨率、128符号内存、`with_dma=true`，分配258个输出位置：256实体像素后附加2个黑色位置。它们是发送数据裕量，不是多了2颗实体LED；复位脉宽由实际库实现决定，不能从注释认定已测得280 μs。

显示任务优先级5、Core1；USB命令及音频任务在Core0，UDP任务也在Core0。大多数引擎刷新后返回33 ms任务延时，频谱20 ms、结算100 ms，另加绘图、刷新、板载指示灯和调度开销。原生DMA并不代表CPU零占用，`led_strip_refresh`也不能直接当成无等待帧交换。没有Front/Back交换队列，不能称应用双缓冲或稳定60 FPS。

启动亮度20，协议亮度0–60，实际通道缩放约为RGB×brightness/255。没有Mid的FastLED5 V/1200 mA估算器，亮度上限不等于物理电流限制。板载GPIO48是另一个RMT设备、`with_dma=false`，显示连接／听取／思考／播放状态；不能把所有LED都称DMA驱动。

模式设置有互斥锁，但游戏和频带共享数据并未全部封装为同一个任务消息队列，当前ACK不是全系统原子快照。

<a id="display"></a>

## 灯效、桌宠、计时和游戏

### 模式目录

枚举为0–25去掉18，共25个编号，包含关灯和结算画面，不是25种动态灯效。

| 编号 | 实现 |
| :--- | :--- |
| 0；1/2/3 | 关灯；纯红／蓝／绿。 |
| 4–10 | 对角HSV彩虹、空间正弦极光、双流星、14个生命周期星点、全屏变色、随机雨滴、双径向波纹。 |
| 11–14 | 笑、哭、平静及三表情轮换，加入预设眨眼／视线游移动画；不是追踪用户视线。 |
| 15；16/17 | 频谱；16与17均调用同一个桌宠绘制函数。 |
| 19/20；21/22 | 贪吃蛇／结算；俄罗斯方块／结算。 |
| 23/24/25 | 随机冷却与邻域传播火焰；按列速度／长度变化的代码雨；按时长计时。 |

效果并非Mid逐像素复刻：彩虹、极光、星点、波纹和表情都有当前独立实现。火焰代码没有Perlin噪声采样，代码雨也没有绘制可识别的数字字符；应按具体热量数组和像素条带描述。

### 桌宠图像和色彩状态

四帧为待机、闭眼、两张口型。扬声器启用时口型每140 ms交替，否则按随机间隔眨眼约160 ms。I2S空闲约800 ms才停钟，因此口型可能在语音结束后继续；没有音素、音量包络或语音时间戳对齐，也无昼夜／打哈欠／睡眠模型。

[生成脚本](../scripts/update_kurisu_sprites.py)保留源图RGB、部位标签、显示覆盖、LED参考PWM，再生成[固件帧](../firmware-s3/main/display/kurisu_sprites.h)。参考全局亮度B=20，为目标通道q反算驱动值：

```math
c=\left\lceil\frac{255q}{20}\right\rceil,\qquad p=\left\lfloor\frac{cB}{255}\right\rfloor
```

它保证指定参考档位的整数数字输出，不保证物理色度、亮度或屏幕色一致。当前桌宠系数100%，`Show`未开启sRGB二次解码。`srgb_transfer.h`保留为可选转换，旧Gamma表不意味着正式输出都经过Gamma校正。

原图256格独立基准见[fixture](../tests/fixtures/kurisu_design_hex.txt)。四格肤色、两格熄灭、裤子同外套是用户要求的显示覆盖，不能写成原图完全未变。深棕外框仍偏橙；四相暗部实验有可见闪烁已弃用，详情见[配色迭代记录](KURISU_VISUAL_TUNING.md)。

### 计时和世界线演出

计时命令时长1–86400秒，用`get_millis()`差值而非重复sleep累加，剩余像素按比例计算：

```math
N_{\mathrm{on}}=\left\lfloor256\max\left(0,1-\frac{t-t_0}{T}\right)\right\rfloor
```

再加边界像素羽化与绿／橙／红进度色。达到时长后进入约1500 ms全屏提示，随后关灯；没有实测计时误差、物理砂粒或专属结束提示音。只设模式25不会重置计时起点，应调用`countdown`。

“世界线”实际是PC依次发送fire→meteor→matrix→dynamic，间隔0.35/0.35/1.2 s；网页显示固定1.048596%。没有板上数字仪表、随机数锁定或独立电流音效，不能把角色设定当测量结果。

### 游戏机制与边界

贪吃蛇为256长度坐标数组、初长3、16×16穿墙与自碰撞。食物随机位置不排除身体，增长槽位没有显式复制旧尾。速度按分数变化；公式先检查旧速度再赋新值，可能出现75 ms后回80 ms，不应写成严格80 ms下限。反向判断直接比头颈坐标，跨边界时仍需测试。

俄罗斯方块使用7形状×4朝向，16×16存储、x=3..12十列场地，碰撞、下移、旋转、固化、消行和得分；初800 ms、每行减30 ms，条件式会短暂到80 ms再回100 ms。`drop`只向下一格，没有硬降或墙踢。没有反应时间或表情驱动DDA。得分十位超出0–9时被字模拒绝，不宜声称任意多位成绩完整显示。

<a id="voice-agent"></a>

## 本地音频入口与语义计划

### 唤醒与单轮状态机

板端I2S_RX16 kHz单声道32位槽，`ReadMic`右移16位得到PCM16，经USB到PC。PC以30 ms/480采样帧去直流、WebRTC VAD模式2与自适应RMS门限分句；实际连续2帧语音启动，待命/指令静音门限16/36帧，并对短片段尝试Silero复核。源码注释中的3帧不是当前条件。

待命语音先过Sherpa ONNX Zipformer KWS（阈值0.50），再用无唤醒提示的Whisper确认；仅接受句首配置名称，声学证据缺失不能由Whisper文字唤醒。Whisper优先CUDA float16，失败回CPU int8；KWS缺失会关闭自动唤醒。唤醒后10 s无指令回待命；处理、排队和正在说话时不按空闲超时丢弃。

名字与命令同句可以直接执行；名字单独说会应答后等待一条命令。不完整“我想看”等前缀跨分句暂存。执行及播报期间暂停采音上传，结束恢复监听并将`is_awake=False`。因此不是连续会话或回声抵消的全双工。

### 计划校验与对话

`semantic_control.py`提供效果名目录、JSON Schema、完整字面命令快速路径、明确数值分句提取、计划校验及最多一次模型修正。模型给出效果名，再由程序映射编号；拒绝非法参数、非控制意图夹带操作、同时启停计时，多种竞争显示要求转澄清，最多4动作。

`kurisu_agent.py`只在控制计划中执行工具，普通聊天不从人格回复里提取硬件动作；一轮内同工具同参数去重。执行成功依赖板端ACK。聊天历史仅在内存中保留近期完整轮次（约12轮），没有Mem0、持久化向量库或独立长期记忆。`Modelfile.kurisu`以`qwen2.5:7b`加角色提示和采样参数，不是LLM训练脚本。

`light_tools.py`虽使用MCP命名与函数Schema，但当前执行是Python本地调用，没有完整MCP JSON-RPC发现／会话服务，也没有在S3继续运行Mid的小智客户端。不能写“板载小智MCP双向协议已集成”。

### 语音合成与PCM播放

`voice_engine.py`加载外部GPT-SoVITS v2Pro角色权重、BERT/HuBERT与参考音频；没有本项目训练流程。中日分段合成，双段成功时插180 ms静音，经滤波／可选noisereduce／均衡／归一化，保存32 kHz WAV并以`resample_poly`降为16 kHz PCM。合成缺依赖或权重时不改用系统合成音；板端USB不可用时存在Windows本机播放路径，不保证所有平台自动降级。

板端PCM16转两个相同32位I2S槽，音量映射为平方律（数字映射，不是声压测量）：

```math
g=\left\lfloor65536(V/100)^2\right\rfloor,\qquad s_{32}=\mathrm{clip}_{32}(s_{16}g)
```

PC按累计字节与单调时钟节流，目标预送120 ms：

```math
t_{\mathrm{send}}=t_0+\frac{B_{\mathrm{sent}}}{2\times16000}-0.120
```

32 KiB环形缓冲由8192字节栈播放任务消费；PC前后查询`audio_rx/audio_played/audio_dropped/audio_errors`，要求采样增量一致且无丢弃／错误。`audio_played`是完整写入I2S的采样计数，不代表扬声器的声学质量。没有输入／输出同时工作的AEC保证，也不是原始素材的无损播放。

<a id="transport"></a>

## USB、Wi-Fi与控制页面

USB上行麦克风帧为`55 AA len_hi len_lo PCM16LE`；下行为`AA 55 len_hi len_lo PCM16LE`，长度字段大端、负载小端。固件下行帧最大2048字节，没有CRC或包超时恢复。USB也能解析文本／JSON，但PC普通控制强制经UDP8888。

UDP封套`{"request_id":"...","command":"..."}`；默认PC超时0.6 s、重试2次。S3按发送IP和ID缓存16条、30 s内可复用，同ID不同命令返回冲突。缓存有界，不是无限期恰好一次；ACK表示解析／处理结果，不是光学或声学验收。STA+SoftAP、约2 s信标用于发现，断线重连由定时器调度。

HTTP8080提供`/api/chat`、`mode`、`volume`、`cmd`、`game`、`status`和`ceremony`，WebSocket`/ws`广播聊天／模式事件。浏览器Canvas用自己的函数和时间生成像素，频谱／游戏／桌宠并不从板端读回。世界线数字同样是页面演出，不是Three.js、WebGL或数字孪生。

Android是Java WebView，优先加载配置的PC地址，失败转内置页面；本地assets与Web源JS已有差异，且相对`/api`在file页面不能自动找到PC。Activity内置地址、SDK工具路径都与作者机器相关；不能宣称任意手机安装APK即可独立控制S3。现有HTTP/UDP路径没有用户认证，按本地实验网络条件使用。

<a id="vision-audio"></a>

## 独立视觉与音频程序

| 程序 | 实际实现 | 边界 |
| :--- | :--- | :--- |
| [vision_gesture.py](../pc-agent-vision/vision_gesture.py) | MediaPipe单手关键点x/y阈值；0关灯、1红、2/胜利桌宠、3火、4代码雨、5彩虹。 | 改变结果且距上次触发>0.6 s才发送，不是保持同一姿势0.6 s验证。仍用USB连接标志作为发送门槛；无3D抓投。 |
| [vision_face.py](../pc-agent-vision/vision_face.py) | Haar+100×100灰度LBPH，S保存、T重训；ylk红、zzc蓝、其他登记名笑脸，问候冷却15 s。 | 无活体或安全认证评测；语音合成同步调用可能阻塞GUI；不是在线增量学习。 |
| [vision_tracker.py](../pc-agent-vision/vision_tracker.py) | Face Mesh嘴宽／嘴高>2.8触发笑脸，按时间恢复动态图案，记录有人状态。 | 几何启发式，不是情绪分类、头姿／注视点、疲劳检测；无人时未实现自动节能。 |
| [audio_visualizer.py](../pc-agent-vision/audio_visualizer.py) | PyAudio默认输入16 kHz、512点Hann+rFFT、16带平均、峰值归一化、幅度对数压缩、低频突增。 | 默认PC音频输入，不是自动手机/系统播放捕获；不随Web服务自动启动，也不是MIR流体。 |

独立频谱程序边界数组沿用Mid，但采样率和阈值不同：P初值0.05、每窗衰减0.96、下限0.01。设a_i为频带平均：

```math
P_t=\max(0.96P_{t-1},\max_i a_i,0.01),\qquad
b_i=\left\lfloor15\frac{\ln(1+9a_i/P_t)}{\ln10}\right\rfloor
```

13–15号再乘0.7，钳0–15；beat用频点1–3幅值和，相比前值1.35倍、幅值>0.12、RMS>0.02。16 kHz时窗32 ms、bin31.25 Hz，使用1–199号bin。S3接收16带，经验衰减并加峰值白点；`last_feed_time_`没有真正实现超时清空，输入停止仍保留旧目标值。

视觉／频谱脚本中的旧`b 150`超出固件0–60范围，恢复命令会被拒绝；不要照其打印文字认定设置成功。三种视觉程序争用相机，可能覆盖语音／网页模式，没有统一输入仲裁。根目录指尖引擎仍未编译接入，不能用它补齐上述功能。

<a id="implementation-status"></a>

## 验证、未完成内容和后续工作

本轮重新执行的是22交互回归、6语义单元、11配色检查、两个C++静态断言文件和两份JS语法检查。回归使用AST抽取与替身，未加载CUDA/TTS或打开硬件。没有重新运行真实模型、固件完整构建、烧录、录音和播放。

既有[语音修复](VOICE_CONTROL_RECOVERY.md)记录固定30例语义、两条用户确认语音和223360采样写入检查；这些分别对应语义用例、完整语音场景与静音播放统计，不能合并为识别率或听感指标。[单块面板](MATRIX_16X16_VALIDATION.md)记录诊断图和多模式用户确认；73/74硬件检查次数含可变状态轮询，不是相同固定基准。

最新配色记录对应873920字节固件，本地二进制SHA256与`pants_match_coat_validation`记录一致，能核对构建、写入日志及亮度20／模式17／停止采音ACK。这不是本轮重新测量；深棕目标仍未通过，当前图形静态方案也不等于精确色彩校准。

| 状态 | 内容 |
| :--- | :--- |
| 当前可追踪主线 | 单板驱动、灯效／桌宠／游戏／计时、UDP ACK、单轮语音和Web控制。 |
| 独立、缺少统一验收 | 三种视觉程序、PyAudio频谱、Android打包与脱机页面、未接入指尖源。 |
| 未来目标 | 连续对话、MCP协议服务、持久记忆、视线／姿态／疲劳、抓投、体感游戏、DDA、无线音频、MIR、3D数字孪生。 |
| 已知问题 | 旧b150、Web模拟与板状态差异、模式25缺时间入口、游戏增长／食物／速度／得分边界、共享数据与相机仲裁、无流超时清空。 |

当前依赖未完整锁定，私有模型不随Git分发，Python路径含原作者环境。旧README中的缺失目录、MIT文件链接、85%CPU与延迟／TTFT目标已移除或降为计划。源码和既有历史报告本轮保持不变，仅为规格书添加“设计目标”提示。个人维护身份不等于所有框架／模型／素材的作者身份。
