# Intelligent Lighting Control System Pro (高阶具身多模态智能光影交互系统)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![ESP-IDF](https://img.shields.io/badge/ESP--IDF-v5.x-blue.svg)](https://idf.espressif.com/)
[![CUDA](https://img.shields.io/badge/NVIDIA-RTX%204060%20Accelerated-green.svg)](https://developer.nvidia.com/cuda-zone)
[![XiaoZhi AI](https://img.shields.io/badge/XiaoZhi-Native%20ESP32--S3-purple.svg)](https://xiaozhi.dev/)

> 🎓 **通关式项目课程——大四高阶成果 (High-Stage Capstone Project)**  
> 对标日本顶级名校（东大/东工/京大）修士研究室（HCI 人机交互 / 嵌入式边缘智能 / 具身感知）及索尼、任天堂、日立等头部科技企业研发标准。

---

## 🌟 项目亮点与高阶进化 (Evolution from Mid-Stage)

本项目在**完全不增加额外硬件采购**的严格约束下，对大三中阶（`Intelligent-Lighting-Control-System-Mid`）进行了系统级重构与高阶跃迁：

| 维度 | 大三中阶 (Mid-Stage) | 大四高阶 (Pro-Stage) |
| :--- | :--- | :--- |
| **硬件架构** | 双芯片架构 (ESP32-S3 小智 + ESP32-WROOM-32 灯控)，软串口通信 | **单芯片融合架构**：彻底精简 WROOM-32，单一 ESP32-S3R16N8 统一调度网络、音频与光影渲染 |
| **灯控底层** | Arduino 框架 + FastLED 开源库，软件延时阻塞 | **ESP-IDF 原生 C++ 驱动**：硬件级 RMT (Remote Control) 外设 DMA 发送，**0% CPU 占用**，60FPS 无锁平滑混光 |
| **感知交互** | 基础离线语音与有限指令响应 | **多模态具身感知系统**：PC 端 RTX 4060 驱动 21 关节点三维手势空中光影追踪 + 视线注意力朝向估计 (Gaze Tracking) |
| **智能内核** | 云端小智固定服务器 | **本地化具身多模态 Agent**：本地私有化部署大模型，基于 MCP (Model Context Protocol) 协议与设备进行函数级双向工具调用 |
| **音频体验** | 小智内部固定提示音频 | **局域网流媒体 / 音频实时全双工随动**：支持 PC / 手机本地音频流实时推流，结合低时延 FFT 进行光影共振 |
| **移动控制** | 无独立移动客户端 | **跨平台轻量级控制 App**：自研移动端控制台，支持三维色彩拾取、虚拟手势映射与场景联动编排 |

---

## 🏗️ 系统整体架构 (System Architecture)

```
                       +---------------------------------------------+
                       |           PC Host (RTX 4060 8GB)            |
                       | - OpenCV + MediaPipe 3D Hand/Gaze Tracking  |
                       | - Local Multimodal LLM Agent (MCP Protocol) |
                       | - Real-time High-frequency WebSocket Server |
                       +----------------------+----------------------+
                                              |
                          Local Wi-Fi / WebSocket / BLE
                                              |
                                              v
                       +---------------------------------------------+
                       |           ESP32-S3R16N8 (Single MCU)        |
                       | - XiaoZhi AI Native Firmware (Voice Client) |
                       | - FreeRTOS Dual-Core Task Scheduling        |
                       | - Hardware RMT Peripheral WS2812B Engine    |
                       | - Double-buffered 16x16 Matrix Framebuffer  |
                       +----------------------+----------------------+
                                              |
                                   High-speed GPIO (RMT)
                                              |
                                              v
                       +---------------------------------------------+
                       |           16x16 WS2812B RGB Matrix          |
                       | (Fluid Dynamics, Gaze Focus, Particle Aura) |
                       +---------------------------------------------+
```

---

## 📁 代码目录结构 (Directory Structure)

```
Intelligent-Lighting-Control-System-Pro/
├── docs/                   # 硬件时序图、MCP 协议规范、交互设计文档
├── firmware-s3/            # ESP32-S3R16N8 原生固件 (ESP-IDF 5.x C++ / FreeRTOS)
│   ├── main/               # 系统入口与业务逻辑
│   ├── components/         # 自研组件 (rmt_ws2812b, audio_stream, mcp_client)
│   └── CMakeLists.txt
├── pc-agent-vision/        # PC 端视觉与多模态 Agent (Python + CUDA)
│   ├── vision_tracker/     # MediaPipe 3D 手势识别、视线检测引擎
│   ├── agent_core/         # 本地 MCP Agent 服务调度
│   └── tests/              # 视觉流水线与通信低时延单测
├── mobile-app/             # 跨平台自研移动控制端
└── README.md
```

---

## 🚀 快速开始与开发规划 (Roadmap)

- [ ] **Phase 1**: PC 端视觉追踪骨架构建 (MediaPipe 3D 手势空中追踪坐标映射与 WebSocket 广播)
- [ ] **Phase 2**: ESP32-S3 原生 ESP-IDF RMT 驱动与帧缓冲区双缓冲实现 (无 FastLED 依赖)
- [ ] **Phase 3**: XiaoZhi 协议与本地 MCP 工具集成 (小智语音与灯效函数呼叫)
- [ ] **Phase 4**: 跨平台移动 App 联动控制与音频流实时随动渲染
- [ ] **Phase 5**: 性能调优、学术级文档规范整理与演示视频制作

---

## 📄 开源许可证 (License)

本项目遵循 [MIT License](LICENSE) 开源协议。
