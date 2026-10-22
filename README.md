# Intelligent Lighting Control System — Pro

PC 本地语音智能体与单颗 ESP32-S3 协同的灯板、红莉栖桌宠和点阵游戏平台。

**简体中文** · [English](README_EN.md) · [日本語](README_JA.md)

**2026-10-23：高阶功能已扩展到代码与离线验证层，尚未上板验收。** [完整实现、18项需求差异与部署接口](docs/PRO_FEATURES.md)是当前说明；早期技术审计和实机记录保留为历史依据，不代表本轮新增功能的实测结果。

## 当前功能

| 模块 | 实现 |
| --- | --- |
| 灯板底座 | ESP-IDF RMT DMA、单块16×16逐行蛇形映射、显示状态锁、完成帧PWM快照、可选Gamma。 |
| 语音与语义 | PC声学KWS＋Whisper确认、经过校验的全模式语义计划、Ollama角色对话、GPT-SoVITS中日回复；默认支持回复后继续听取，空闲或结束语退出。 |
| 长期记忆 | SQLite持久偏好与对话、资料分块、可删除的RAG；默认词汇检索，可配置本地embedding模型。 |
| 具身交互 | 统一摄像头入口，指尖追踪、捏合抓投／重力／碰撞波纹、校准视线、近似头姿、离席／疲劳／微笑提示与桌宠昼夜状态。 |
| 显示与游戏 | 原有灯效、表情、蛇与方块；数字世界线、计时结束提示、像素画布、MIR流体、环境微光、体感游戏、手动／自适应难度。 |
| 协议与客户端 | UDP ACK控制、既有USB音频、可选Wi-Fi双向PCM；MCP HTTP/WS、小智v1 Opus适配；像素编辑、PWM回读WebGL预览、Android服务器配置与局域网发现。 |
| 无硬件预览 | 明确标注的模拟服务，可运行从正式C++源码编译的离线WASM引擎。 |

```mermaid
flowchart LR
    Input[板载麦克风] -->|USB或可选Wi-Fi PCM| Voice[PC KWS / Whisper]
    Voice --> Agent[语义计划 / 角色对话 / 持久记忆]
    Camera[按需启用的PC摄像头] --> Vision[统一视觉与控制仲裁]
    Web[Web / Android / MCP] --> Agent
    Agent -->|UDP命令与ACK| S3[单颗ESP32-S3]
    Vision -->|UDP命令与ACK| S3
    Agent --> TTS[角色语音合成]
    TTS -->|USB或可选Wi-Fi PCM| S3
    Music[音频文件或直链] --> MIR[PC解码与MIR]
    MIR --> S3
    S3 --> Matrix[16×16 WS2812B / 游戏 / 桌宠]
    S3 --> Speaker[I2S扬声器]
    S3 -->|完成帧回读| Preview[WebGL预览]
```

直接模式为0–31、排除18和25；25必须传倒计时时长。26–31分别为指尖、光球、世界线、画布、音乐流体和环境微光。桌宠原待机配色及用户指定局部覆盖保留。

## 运行与验证

- 安装控制／Web／视觉依赖：`python -m pip install -r pc-agent-vision/requirements-pro.txt`。ASR、KWS、角色语音和Ollama模型需按[当前部署说明](docs/PRO_FEATURES.md#服务模型与数据)另行准备。
- 只看模拟控制台：`python -B pc-agent-vision/web_server.py --simulate --no-audio --port 8086`，打开 `http://127.0.0.1:8086/pro.html`。按[预览步骤](docs/PRO_FEATURES.md#完全离线的预览)设置仓库外缓存；不连接设备、不加载模型、不发声。
- 真实动画模拟另需构建WASM引擎并设置 `KURISU_RENDERER_WASM`；未配置时只有有限静态样例。完整硬件服务仍用同一入口，启动可能连接设备和发声，本轮没有启动该路径。

本轮验证包含ESP-IDF完整编译、Python协议／服务／语音回归、真实C++引擎离线执行、真实Opus编解码、浏览器模拟控制台检查、Android编译及签名核验。**没有烧录、摄像头采集、录音、播放或Android安装实测。** 生成镜像、APK、日志和缓存均不提交源码仓库。

## 原设计差异与归属

[18项历史SRS](docs/HIGH_STAGE_SYSTEM_SPEC_18.md)中的原生板端WakeNet、物理砂粒、原音乐规格无损与物理光照仿真没有按原样实现。当前采用PC唤醒、像素进度计时、16kHz单声道音乐和WebGL可视化；小智适配入口与Pro的PCM入口相互独立。全双工／AEC、视线／情绪启发式及DDA需要后续实机调试。没有零CPU、稳定60FPS、端到端时延或识别准确率的新测量结论。

项目由 **刘超然 / Chaoran Liu** 维护；组员指尖模块已接入正式工程。ESP-IDF、Qwen、Whisper、Sherpa ONNX、GPT-SoVITS、MediaPipe、PyAV及角色素材分别按来源归属；集成不等于自训练或原创模型。仓库没有独立LICENSE，各依赖、图像、语音和权重遵循各自许可。

[当前实现与部署](docs/PRO_FEATURES.md) · [指尖接入](INTEGRATION.md) · [历史音频恢复](docs/VOICE_CONTROL_RECOVERY.md) · [历史面板验收](docs/MATRIX_16X16_VALIDATION.md) · [开发流程](docs/DEVELOPMENT_WORKFLOW.md)
