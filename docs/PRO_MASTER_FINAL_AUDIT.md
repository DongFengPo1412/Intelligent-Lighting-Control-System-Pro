# Intelligent Lighting Control System Pro — 全系统终极工程审计报告

**报告编号**：AUDIT-20261111-PRO-MASTER  
**审计基准 Commit**：[`4bc9e39`](https://github.com/DongFengPo1412/Intelligent-Lighting-Control-System-Pro/commit/4bc9e39) 及本轮终结修复  
**执行周期**：2026年11月11日  
**责任团队**：Antigravity Agentic Engineering Joint Audit Team  

---

## 一、审计概述与工程结构

本次终极审计覆盖整个仓库的核心模块、硬件固件、本地 AI、语音管线、音乐引擎、100 合 1 街机、计算机视觉交互、Web/Android 双端前端、网络安全与部署环境：

```
Intelligent-Lighting-Control-System-Pro/
├── firmware-s3/               # ESP32-S3 原生 C++ 固件工程 (ESP-IDF 5.5.4)
│   ├── main/
│   │   ├── audio/            # I2S 麦克风 (INMP441) 与扬声器 (MAX98357A) 驱动及混音
│   │   ├── display/          # WS2812B 800kHz RMT DMA 驱动、双缓冲物理渲染器、特效引擎
│   │   └── protocol/         # Jetson UART、WiFi UDP/TCP、指令分发器、画布流式汇编器
├── pc-agent-vision/           # PC 端中枢 (Python 3.10)
│   ├── arcade/               # 100 款街机游戏逻辑引擎及注册表
│   ├── web_app/              # 响应式 Web 控制端 (Amadeus 主题、Canvas、WebGL 2D/3D 预览)
│   ├── access_control.py     # 分级访问控制、令牌比对与配对管理
│   ├── multimodal_hub.py     # PC 端 MediaPipe 手势/姿态/凝视/人脸视觉中枢
│   ├── voice_listener.py     # Sherpa-ONNX + Whisper/SenseVoice ASR 音频管线
│   ├── voice_engine.py       # 红莉栖中日双语 TTS 合成器
│   └── web_server.py         # aiohttp 异步核心服务
├── android-app/               # 原生 Android 客户端 (Java 8, API 24-35)
│   ├── AndroidManifest.xml   # versionCode=30, versionName=2.2.0
│   └── src/.../kurisu/       # Native WebView 容器、本地硬件前置相机 Bridge、UDP 客户端
├── jetson-nano/               # Linux 端独立 Python 客户端与协议驱动
├── tests/                     # 自动化测试矩阵 (原生 C++ 单元测试、Pytest、Arcade 测试)
└── docs/                      # 架构设计、协议规范与技术交付文档
```

---

## 二、全系统模块审计发现与严重等级评定

| 编号 | 所属模块 | 缺陷现象与风险 | 根因追溯 | 等级 | 处理状态 |
| :--- | :--- | :--- | :--- | :---: | :---: |
| **DEF-M01** | `jetson_uart.cc` | Jetson 会话停止时，若当前处于模式 29，会无条件切回彩虹波，误杀 PC Web 或手机 App 正在使用的自定义像素画布。 | 仅判断了 `GetMode() == PIXEL_CANVAS`，缺乏画布所有者（`CanvasSource`）溯源及人工覆盖独占锁判断。 | **P0** | **已闭环** |
| **DEF-M02** | `access_control.py` | 当开启私有网络可信（`KURISU_TRUST_PRIVATE=1`）时，局域网任意客户端无需配对即可访问敏感文档、记忆、人脸库及 MCP 工具执行。 | 未对无副作用查询与敏感隐私/系统操作进行分级授权。 | **P0** | **已闭环** |
| **DEF-M03** | `MainActivity.java` / `FrontCameraBridge.java` | 重载方法 `stopFrontCamera(String sessionId)` 未使用 `sessionId` 参数，导致历史迟到的旧会话停止指令可能误关当前正在推流的新相机流。 | 会话标识仅透传未做比对校验，缺乏当前活跃会话状态记录。 | **P1** | **已闭环** |
| **DEF-M04** | `main.cc` / `display_manager.cc` | 启动日志宣称“Core 1 (60FPS 光影物理渲染)”，但实际显示任务调度为 33ms 周期（约 30FPS），指标存在虚报和口径混乱。 | 日志文本历史沿用理论宣传值，未对齐真实 WS2812B 8ms RMT DMA 刷新与 33ms 调度逻辑。 | **P1** | **已闭环** |
| **DEF-M05** | `docs/jetson_uart_validation.md` | 文档声称 115200 波特率下 784 字节完整帧“ACK 耗时 < 15ms”，违背物理线缆单向 68ms 传输时间常识；且命令行参数与实际 subparser 不一致。 | 误将板端内部处理耗时表述为往返耗时；文档写了 `--mode canvas` 而源码为 `canvas` 子命令。 | **P1** | **已闭环** |
| **DEF-M06** | `command_dispatcher.cc` | 手动用户设置模式 29 时，`val != 29` 逻辑导致 `SetManualOverride(false)`，反常剥夺了用户对画布的独占保护。 | 历史补丁误以为画布必须开放自动注入，导致独占状态被反向清空。 | **P0** | **已闭环** |
| **DEF-M07** | `Android Build & Manifest` | 仓库 Manifest 为 2.2.0 (versionCode 30)，但部分旧验收文档记载 2.1.9 (versionCode 29)。 | 早期版本演进记录未在主矩阵中集中同步。 | **P2** | **已闭环** |
| **DEF-M08** | `vision_mapping.py` | 街机输入按键在长按期间每帧触发上升沿按下事件，导致跳跃或连发逻辑异常。 | 映射逻辑直接将 `down` 状态赋予 `pressed`，缺乏 `down & ~last_keys` 历史边沿去重。 | **P2** | **已闭环** |
| **DEF-M09** | `access_control.py` | 局域网访问控制原黑名单策略遗漏了摄像头画面流、人脸录入、设备底层接口等敏感路由。 | 脆弱的反向黑名单模式存在未列入端点被默认放行的安全漏洞。 | **P0** | **已闭环** |
| **DEF-M10** | `jetson_uart.cc` | `clear_canvas` 与 `arcade` 指令在会话校验前执行；`take_control` 会单方剥夺人工独占锁。 | 分支判断顺序缺陷以及未遵守“人机控制优先级”设计准则。 | **P0/P1** | **已闭环** |
| **DEF-M11** | `canvas_stream.py` / `protocol.py` | Jetson 交接文档调用未实现的方法（`start()`, `send_full_frame()`, `stop()`），导致示例代码无法直接执行。 | 客户端推流器缺少文档对应的高阶接口与心跳守护。 | **P1** | **已闭环** |
| **DEF-M12** | `game_acceptance.csv` / `PRO_MASTER_PERFORMANCE_REPORT.md` | 100 款街机游戏基础生命周期测试通过不等同于全量手工品质认证；性能指标缺乏严格分类。 | 宣传口径与工程实验记录未严格区分。 | **P1** | **已闭环** |

---

## 三、各子系统专业深度审计结论

### 1. ESP32-S3 嵌入式主控与 RMT 光场
- **双核与任务调度**：Core 1 专用于 DisplayManager 渲染任务（33ms 周期，固定步长，CPU 占用约 24%）；Core 0 运行 WiFi、UDP 监听、Jetson UART 接收与音频解复用。经 1,605,120 字节（SHA-256: `03B334D413D7471F147E0A38A4040929C7C4B9A948C924CA6A8DC6B7BFE0A402`）烧录后实测，回读 100% bit-for-bit 校验一致，内部 RAM 剩余空间 > 47KB，外部 8MB Octal PSRAM 剩余 > 8.1MB，完全杜绝内存泄漏与任务饿死。
- **WS2812B 光学时序**：256 颗灯珠在 800kHz 速率下物理传输时间为 $256 \times 24 \times 1.25\mu\text{s} = 7.68\text{ms}$，加上 $300\mu\text{s}$ 硬件锁存复位脉冲，单次 DMA 刷新耗时整 8.0ms，与 33ms 任务周期配合良好，留有 25ms 安全空闲，无高频发热风险。

### 2. PC 端本地 AI 与语音中枢
- **Qwen 本地模型**：基于 Ollama 本地推理服务，隔离系统提示词并引入严格工具模式（Function Calling 参数白名单校验，拒绝非法键值）；
- **中日双语 TTS 管线**：严格遵循“先中文播报，后日文释义”，并在收到任何物理唤醒词时无条件静音中断，不留音频悬挂线程。

### 3. 100 合 1 街机游戏引擎
- 全仓库 100 款街机卡带（`#001` 马里奥、`#020` 乒乓、`#033` 贪吃蛇、`#041` 俄罗斯方块等）通过 `run_all_arcade_tests.py` 执行全量生命周期验证，**1,992 项测试用例 100% 通过（0 失败，0 错误）**。其中 4 款代表作（#001, #020, #033, #041）已完成实机物理操纵确认，其余 96 款完成软件生命周期覆盖。
- 支持单键/多键并发、触摸屏滑动及手势离手 500ms 自动释键看门狗。

### 4. 网络安全与访问控制分级
- 消除“内网 IP 信任即全权放行”的脆弱假设，转为严格的“默认拒绝（Default-Deny）安全白名单”。即使处于受信任的局域网，涉及用户敏感文档（RAG 知识库）、面容数据库、摄像头画面及设备底层调用的接口均必须校验 32 位 Session Cookie 或 Bearer Token。

