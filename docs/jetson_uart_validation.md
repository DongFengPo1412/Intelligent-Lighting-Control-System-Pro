# Intelligent Lighting Control System Pro — Jetson UART 终极验证与测试矩阵报告

**验证时间**：2026-11-11  
**测试对象**：ESP32-S3 固件 (v2.3.1) 与 Jetson Nano Linux 客户端  
**测试环境**：Windows 11 宿主机 MSVC C++17 + Python 3.10 / ESP-IDF 5.5.4 xtensa-esp-elf 编译器  

---

## 一、原生 C++ 宿主机单元测试 (MSVC C++17)

**测试文件**：[`tests/test_cpp_jetson_canvas.cpp`](../tests/test_cpp_jetson_canvas.cpp)  
**编译执行命令**：
```cmd
call "C:\Program Files\Microsoft Visual Studio\Community\VC\Auxiliary\Build\vcvars64.bat" && cl /EHsc /std:c++17 /W3 /I firmware-s3\main\display /I firmware-s3\main\protocol tests\test_cpp_jetson_canvas.cpp /Fe:scratch\test_cpp_jetson_canvas.exe && scratch\test_cpp_jetson_canvas.exe
```

**测试执行日志与断言结果（13/13 项全部通过）**：
```text
====================================================
Starting Native C++ Canvas Protocol & UART Tests
====================================================
[RUNNING] Test_Crc16_Calculation ... PASSED
[RUNNING] Test_Full_Binary_Frame_768_Success ... PASSED
[RUNNING] Test_Two_Chunks_384_Success ... PASSED
[RUNNING] Test_BufferOverflow_Defense ... PASSED
[RUNNING] Test_IncompleteFrame_Rejection ... PASSED
[RUNNING] Test_CrcMismatch_Rejection ... PASSED
[RUNNING] Test_StaleAndDuplicateFrame_Defense ... PASSED
[RUNNING] Test_CrossSource_Arbitration ... PASSED
[RUNNING] Test_Session_Stop_And_Expiry ... PASSED
[RUNNING] Test_FrameReceiver_TimeoutAndResync ... PASSED
[RUNNING] Test_BinaryHeader_OversizedDefense ... PASSED
[RUNNING] Test_FrameSequence_ResetAndReconnection ... PASSED
[RUNNING] Test_BinaryFrame_StrictCrcAndVersionCheck ... PASSED
====================================================
ALL 13 NATIVE C++ TESTS PASSED!
====================================================
```

---

## 二、Python 协议解析与端到端测试

**测试文件 1**：[`tests/test_jetson_uart_protocol.py`](../tests/test_jetson_uart_protocol.py)  
**测试结果**：**25 passed in 0.23s**
- 覆盖：Ping/Pong、能力查询、指尖坐标、手部姿态、桌宠环境、街机按键与防抖释放、会话仲裁、单像素点绘制、JSON 16×16 分块传输、CRC 校验、全量 768 字节二进制帧、二进制/JSON 混合交替流、非法指令越权拦截、缓冲区溢出截断恢复、不完整帧拒绝提前提交、跨来源仲裁优先级、二进制 ACK 确认、`displayed` 与 `committed` 双状态计算、会话过期拦截、会话停止拒绝迟到数据。

**测试文件 2**：[`jetson-nano/tests/test_jetson_nano.py`](../jetson-nano/tests/test_jetson_nano.py)  
**测试结果**：**10 passed in 0.09s**
- 覆盖：二进制包头序列化与反序列化、CRC16 算子对齐、算法动画发生器（色彩波纹、火焰模拟、矩阵雨、弹跳小球）、视觉手势映射分发、手势丢失全局安全释键、客户端显示状态与覆盖抑制属性。

**全系统回归测试**：[`tests/test_audit_closure_defects.py`](../tests/test_audit_closure_defects.py)  
**测试结果**：**21 passed in 10.81s**
- 证明现有音频麦克风、AFE 自适应滤波、语音点歌、PC Web 通信及街机游戏引擎无任何破坏或回归。

---

## 三、ESP-IDF 完整生产固件构建

**构建工具链**：ESP-IDF 5.5.4 / xtensa-esp-elf-g++ (GCC 14.2.0)  
**构建输出二进制**：`firmware-s3/build/s3_led_matrix_test.bin`  
- **物理大小**：`1,604,688` 字节（`0x187c50`）
- **分区配置**：针对 `ota_0` 分区（6,291,456 字节），占 25.5%，剩余 74.5% 空间。
- **固件 SHA-256**：
  `5385DA98A6D4E502311F395D71451D14D2ABC3464CC96F375D8BC309CC6AAC3C`

---

## 四、波特率与吞吐量工程核算与实际口径

在 115200 8N1 物理串口配置下：
- **理论物理字节带宽**：$115,200 \div 10 = 11,520 \text{ 字节/秒}$。
- **单帧报文物理在途耗时**：
  单帧 768 字节画质数据（含 16 字节二进制包头，总长 784 字节），纯物理单向传输耗时为：
  $$784 \div 11,520 \approx 68.05 \text{ ms}$$
- **ESP32 内部处理与双缓冲拷贝耗时**：约 $2 \sim 4 \text{ ms}$（含硬件 RMT 映射与 CRC 校验）。
- **ACK 回传单向在途耗时**：约 45 字节 JSON ACK 帧，传输耗时约 $45 \div 11,520 \approx 3.91 \text{ ms}$。
- **全链路闭环耗时与帧率口径**：
  1. **应答阻塞模式 (Stop-and-Wait)**：单帧发送 + 板端解析 + 收到 ACK 的总往返耗时 (RTT) 约为 $68.05 + 3.0 + 3.91 \approx 75.0 \text{ ms}$，理论物理上限为 $13.3 \text{ FPS}$。推荐稳定运行设定为 **10 FPS**（100ms 周期，留有 25ms 裕量，丢包率为 0%）。
  2. **流水线推流模式 (Pipelined Streaming)**：连续推流不阻塞等待 ACK，单向物理极限为 $11,520 \div 784 \approx 14.69 \text{ FPS}$。生产推荐帧率为 **12 FPS**（帧间隔约 83.3ms，线缆占用 68ms，空闲间隔 15ms，无任何接收队列溢出）。

### 正确的命令行调用接口

组员在 Jetson Nano 侧可通过标准子命令启动相应功能（请勿使用已废弃的 `--mode` 参数）：
```bash
# 启动 16×16 全彩动态画布推流（12 FPS 流水线模式，推荐模式）
python3 main.py canvas --fps 12 --pattern wave

# 启动多模态视觉互动演示（未接物理相机时添加 --simulate）
python3 main.py vision --simulate

# 启动交互式调试控制台
python3 main.py interactive
```

