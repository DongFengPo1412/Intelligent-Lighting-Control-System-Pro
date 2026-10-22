# Pro 部署与操作

**简体中文** · [English](setup.en.md) · [日本語](setup.ja.md) · [项目首页](../README.md)

[结构](#structure) · [硬件](#hardware) · [固件](#firmware) · [PC与模型](#pc) · [运行](#operation) · [检查与排查](#verification)

ESP-IDF 5.5.4在隔离副本完整编译通过，使用公开示例网络配置，镜像874800字节；11项真实C++显示引擎用例及9项Python控制/资源释放用例通过。C++测试使用假时钟/LED HAL，Python测试不连接串口、UDP、麦克风或模型。没有烧录、录音、发声或新的实机验收；历史听感和硬件记录不视为本修订版实测。

<a id="structure"></a>

## 仓库结构与外部文件

```text
.
├── firmware-s3/
│   ├── CMakeLists.txt
│   ├── sdkconfig.defaults
│   ├── diagnostics/
│   └── main/
│       ├── main.cc
│       ├── CMakeLists.txt
│       ├── idf_component.yml
│       ├── wifi_config.example.h
│       ├── audio/
│       ├── display/
│       └── protocol/
├── pc-agent-vision/
│   ├── web_server.py
│   ├── kurisu_agent.py
│   ├── semantic_control.py
│   ├── voice_listener.py
│   ├── voice_engine.py
│   ├── wake_detector.py
│   ├── light_controller.py
│   ├── wifi_gateway.py
│   ├── Modelfile.kurisu
│   ├── requirements-wake.txt
│   ├── web_app/
│   └── faces/
├── android-app/
├── scripts/
├── tests/
├── docs/
└── INTEGRATION.md
```

这是主要目录，独立视觉／频谱脚本也位于`pc-agent-vision`。模型、私有配置、`.runtime_deps`、缓存、诊断录音和构建产物不随源码交付。当前已有脸图是历史跟踪资源，不代表任意用户已有可用人脸库；新增采样应留在本地，本轮没有增删这些资源。

<a id="hardware"></a>

## 硬件与连接

| 部件 | 当前源码配置 | 核对事项 |
| :--- | :--- | :--- |
| 主控 | ESP32-S3，USB Serial/JTAG、Wi-Fi APSTA。 | 具体模组型号不能由旧目录名推断；默认8 MB Flash配置也不是实体型号证明。 |
| 灯板 | 单块16×16 WS2812B、256灯、GRB，GPIO17→DIN。 | 正视左上DIN，偶数行向右；代码额外发2个黑数据不代表258实体灯。 |
| INMP441 | WS=4、SCK=5、DIN=6，I2S_NUM_1，16 kHz。 | 麦克风与所选声道、供电及地按实体模块核对。 |
| MAX98357A与扬声器 | DOUT=7、BCLK=15、LRCK=16，I2S_NUM_0，16 kHz双32位槽。 | 模块负责功放，扬声器阻抗和电源能力不能从代码推定。 |
| 板载RGB | GPIO48，独立RMT设备、无DMA。 | 核对实际开发板是否有此灯。 |
| PC USB | 原生USB Serial/JTAG，自动找VID/PID 303A:1001，否则回退COM9。 | 本机端口可能不同；音频需要数据线，不只是USB供电。 |
| Wi-Fi | UDP8888，S3同时STA与SoftAP。 | 同一可达网络；私有参数自行配置，使用日志中的实际地址。 |

矩阵电源、电平转换、线径、压降和整机电流没有完整受控记录。默认亮度20和协议上限60不构成5 V/1.2 A限流。按实体板和灯板资料设计供电、共地及数据电平，不把程序亮度当作供电容量保证。

<a id="firmware"></a>

## 固件配置与构建

主组件宣告ESP-IDF>=5.0、`espressif/led_strip:^3.0.2`；最近可核对的构建使用ESP-IDF **v5.5.4**。没有验证所有满足下限的版本均能构建。`sdkconfig.defaults`设ESP32-S3、8 MB Flash与Octal PSRAM，必须按实际硬件检查；本地sdkconfig和依赖锁被忽略。

复制 [wifi_config.example.h](../firmware-s3/main/wifi_config.example.h)为同目录`wifi_config.private.h`，只在本地填写STA和AP配置。`.gitignore`已排除私有头；不要把原电脑的网络参数复制到公共文档。

在已激活ESP-IDF的终端从仓库根进入：

```powershell
cd firmware-s3
idf.py --version
idf.py menuconfig
idf.py -DPRO_MATRIX_DIAGNOSTIC=OFF -DPRO_HAIR_CALIBRATION=OFF build
idf.py -p COMx flash monitor
```

新配置如果尚未选择ESP32-S3，先备份既有配置再运行`idf.py set-target esp32s3`。`COMx`替换为实际端口，烧录时关闭占用串口的PC服务。启动会把灯板置模式17、亮度20、板载音量70。

`PRO_MATRIX_DIAGNOSTIC=ON`替换为无网络／音频的走线诊断；`PRO_HAIR_CALIBRATION=ON`是已因闪烁被否决的独立配色实验。两者不能同时开，日常服务必须均OFF。不要为普通复现运行历史调色实验或重新生成帧。

<a id="pc"></a>

## PC环境、模型与依赖

当前本机环境是Windows、Python **3.10.20**；ASR有CPU回退，GPT-SoVITS配置使用CUDA。仓库没有一份覆盖全部组件的锁定requirements，不能保证新环境一次安装即可运行。

| 功能 | 依赖／文件 | 来源和范围 |
| :--- | :--- | :--- |
| 控制／Web | pyserial、NumPy、aiohttp；入口还导入Torch与语音模块。 | Web入口不是完全隔离模型依赖的轻量控制服务器。 |
| ASR／VAD | Torch、faster-whisper、webrtcvad、Whisper `base`资源。 | 初次模型获取可能需联网，后续本地推理不等于全部资源都已打包。 |
| 声学唤醒 | `sherpa-onnx==1.13.8`及`sherpa-onnx-core==1.13.8`，`models/wake_kws`。 | 参考[唤醒记录](VOICE_CONTROL_RECOVERY.md)，模型和私有依赖未跟踪。 |
| 语言模型 | Ollama、`qwen2.5:7b`与`Modelfile.kurisu`。 | 本地角色提示配置，不是自训练LLM。 |
| TTS | NumPy、SciPy、GPT-SoVITS环境、BERT/HuBERT、角色权重及参照音频，可选noisereduce。 | 需兼容Torch/CUDA环境，外部模型不随仓库分发。 |
| 可选视觉 | OpenCV contrib、MediaPipe的`solutions`接口、Torch。 | 各脚本单独启动，核对API版本，不混装多份OpenCV包。 |
| 可选输入频谱 | PyAudio、NumPy及可打开的音频输入。 | 不是自动系统回环或手机音乐输入。 |

语言模型准备命令（会下载模型，不会训练）：

```powershell
ollama pull qwen2.5:7b
ollama create kurisu -f pc-agent-vision/Modelfile.kurisu
ollama list
```

确认Ollama服务可达`http://localhost:11434`。Agent默认`OPENAI_BASE_URL`为`http://localhost:11434/v1`；语义规划仍明确要求Ollama端点，改为其他兼容接口并不保证整条路径可用。

唤醒依赖按现有隔离方式装入目标目录，模型另行准备：

```powershell
python -m pip install --target pc-agent-vision/.runtime_deps -r pc-agent-vision/requirements-wake.txt
```

`wake_kws`需要`tokens.txt`与epoch-12 INT8 encoder/decoder/joiner（文件命名后缀见`wake_detector.py`）；初始化会生成关键词文件。目录缺失或模型不匹配会关闭自动唤醒，不退回自由转写猜唤醒。

TTS实际查找`models/GPT-SoVITS`、`models/pretrained_models/chinese-roberta-wwm-ext-large`、`chinese-hubert-base`及`models/kurisu_tts/{kurisu-e15.ckpt,kurisu_e4_s972.pth,prompt_shy.wav}`。源码根部另一个`GPT_SoVITS`目录不能自动代替这些路径。按模型来源确认资源和依赖；没有权重时不要声称已复现合成。

<a id="operation"></a>

## 启动与分功能操作

运行前确认USB端口和UDP8888没有被另一个服务占用；仅启动一个主要入口。启动Web服务会初始化模型、连接设备、准备缓存并可能播放配对提示音。

```powershell
python pc-agent-vision/web_server.py
```

PC打开`http://localhost:8080`；手机与PC网络互通后打开启动日志显示的PC地址。查看`/api/status`中的`wifi.wifi_online`、`audio_usb_connected`、`board_audio_recent`、`wake_detector_ready`及错误字段。Web服务在线不等于板端和音频都在线，页面初始动画／标签也不是硬件证明。

基本路径是：说唤醒词→必要时等待应答→说一条完整命令→板端确认→中日回复→回待命。可尝试红／蓝／绿、星空／波纹、倒计时和亮度／音量设置；下一轮仍需再唤醒。播放时暂停上传麦克风，不做同时听说。

Web按钮支持模式、原始亮度、音量、计时及游戏方向。推荐参数和协议范围不同：固件亮度0–60、PC封装夹到1–60、语义百分比按最大60换算；亮度20不是20%。计时用明确秒数，不能只点模式25后期待完整计时。游戏S/drop为下移一格。

Android APK与源码在[android-app](../android-app)，是WebView客户端；需按源码配置PC地址。构建脚本含作者机器的JDK17／Android35工具路径，必须自行匹配。内置assets可能过时，离线页面不能独立替代PC模型与S3通信，不默认运行重打包脚本。

以下程序单独占用摄像头／音频或触发硬件，分别运行并先停止竞争程序：

```powershell
python pc-agent-vision/vision_gesture.py
python pc-agent-vision/vision_face.py
python pc-agent-vision/vision_tracker.py
python pc-agent-vision/audio_visualizer.py
```

不要一次执行整个代码块启动全部功能。手势q/Esc、人脸S/T/Q、后台视觉与频谱Ctrl+C退出。人脸问候可能发声；频谱需PC输入设备。现有脚本`b 150`不符合固件范围，参照[已知问题](technical-notes.zh-CN.md#vision-audio)，不要根据退出打印认定恢复成功。根目录指尖脚本尚不能作为正式模式使用。

<a id="verification"></a>

## 检查与排查

以下离线检查不打开硬件或加载完整模型；应在有NumPy／SciPy的兼容环境运行：

```powershell
python scripts/test_interaction_regressions.py
python scripts/test_semantic_control.py
python -m unittest discover -s tests -p test_kurisu_palette.py
node --check pc-agent-vision/web_app/app.js
node --check android-app/assets/www/app.js
xtensa-esp32s3-elf-g++ -std=c++14 -fsyntax-only tests/matrix_layout_test.cpp
xtensa-esp32s3-elf-g++ -std=c++14 -fsyntax-only tests/srgb_transfer_test.cpp
```

`test_semantic_control.py --live`仅调用本地Ollama，不驱动灯板；`test_board_ack.py --silent`仍会操作实体灯板。其他综合测试可能开模型、麦克风、改模式或发声，不要批量运行。历史烧录／声光验收与本轮离线结果分别见[技术说明](technical-notes.zh-CN.md#implementation-status)。

| 现象 | 核对内容 |
| :--- | :--- |
| 网页能开但灯不变 | UDP可达地址、信标、ACK与`request_id`；HTTP成功不代替板端确认。 |
| Wi-Fi在线但无语音 | USB数据口、PCM帧、最近板载音频、KWS／Whisper／TTS资源。 |
| 模型说成功但无动作 | 查看结构化计划与工具回执；旧脚本／展示文案可能不匹配当前协议。 |
| 指令后必须再唤醒 | 当前既定单轮策略，不是持续对话故障已修复。 |
| 网页与灯图不同 | Canvas是独立模拟，无逐像素回读，桌宠源图也不同。 |
| 颜色仍不符合目标 | 查部位配方和实物反馈；自动生成检查不能替代色彩验收。 |
| 采音／播放互相影响 | 核对暂停归属、样本计数、丢弃／错误与栈余量，不能只看PC发送完成。 |


倒计时只能使用带1–86400整数秒的专用命令，直接模式选择为0–24、18除外；25不再接受为无时长切模。PC控制器、工具Schema和固件一致拒绝该用法。独立手势/频谱脚本改用Wi-Fi控制就绪状态，恢复亮度为合法值20；USB音频连接不再是这些控制动作的前置条件。仍是独立程序，没有统一摄像头或模式仲裁。

ESP-IDF 5.5.4在隔离副本完整编译通过，使用公开示例网络配置，镜像874800字节；11项真实C++显示引擎用例及9项Python控制/资源释放用例通过。C++测试使用假时钟/LED HAL，Python测试不连接串口、UDP、麦克风或模型。没有烧录、录音、发声或新的实机验收；历史听感和硬件记录不视为本修订版实测。

`requirements-control.txt` 固定pyserial 3.5，仅覆盖控制客户端；不能据此启动完整Web/视觉/语音栈。完整依赖仍未锁定，外部模型与原机器路径仍需配置。维护修复不改变历史记录，也不代表个人原创了所有框架、模型和素材。

```shell
python -m pip install -r pc-agent-vision/requirements-control.txt
```
