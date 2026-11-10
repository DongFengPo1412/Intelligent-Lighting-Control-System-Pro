# Intelligent Lighting Control System Pro — ESP32-S3 × Jetson Nano 终极工程审计与缺陷闭环报告

**项目仓库**：DongFengPo1412/Intelligent-Lighting-Control-System-Pro  
**审计基线**：`89b6452`  
**固件协议版本**：v2.3.1  
**硬件平台**：ESP32-S3 (8MB Flash / 8MB Octal PSRAM) + Jetson Nano (40-Pin Header UART)  

---

## 一、审计背景与执行范围

为了实现 ESP32-S3 固件作为高可靠、免反复刷写的底层灯效/控制执行器，并使 Jetson Nano Linux 上位机具备持续迭代视觉算法和 16×16 全彩自由画布的能力，本轮对全系统源码进行了终极工程级逆向审计与端到端闭环验证。

### 审计文件清单：
1. **ESP32 协议与解析层**：
   - `firmware-s3/main/protocol/jetson_uart.h` / `jetson_uart.cc`
   - `firmware-s3/main/protocol/canvas_protocol.h` / `canvas_protocol.cc`
   - `firmware-s3/main/protocol/command_dispatcher.h` / `command_dispatcher.cc`
   - `firmware-s3/main/protocol/interaction_commands.h` / `interaction_commands.cc`
2. **ESP32 显示与仲裁层**：
   - `firmware-s3/main/display/display_manager.h` / `display_manager.cc`
   - `firmware-s3/main/display/display_types.h`
3. **Jetson Nano Linux 客户端与 SDK**：
   - `jetson-nano/protocol.py`
   - `jetson-nano/uart_transport.py`
   - `jetson-nano/canvas_stream.py`
   - `jetson-nano/camera_adapter.py`
   - `jetson-nano/vision_mapping.py`
   - `jetson-nano/main.py`
4. **自动化测试与交付包**：
   - `tests/test_cpp_jetson_canvas.cpp` (MSVC C++17 原生宿主机全套断言)
   - `tests/test_jetson_uart_protocol.py`
   - `jetson-nano/tests/test_jetson_nano.py`
   - `jetson-nano.zip` 独立交付压缩包

---

## 二、缺陷分类、根因与修复追溯矩阵 (P0 / P1 / P2)

| 编号 | 等级 | 缺陷现象与风险 | 根本原因定位 | 修复方案与代码变更 | 覆盖测试依据 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DEF-01** | **P0** | 会话停止后，迟到数据可绕过过期检查并继续执行。 | `StopSession()` 后调用 `ClearSession()` 将 `session_id_` 清空，而数据校验逻辑为 `ju.session_id_[0] != '\0' && !ju.IsSessionActive()`。清空后 `!= '\0'` 评估为假，绕过了检查。 | 引入四态状态机 `SessionState` (`IDLE`, `ACTIVE`, `STOPPED`, `EXPIRED`)。`StopSession()` 置 `session_state_ = STOPPED`，所有视觉数据与画布指令在 `STOPPED`/`EXPIRED` 态一律报错拒绝。 | C++ 测试 9；Python 测试 25 (`test_25_session_stop_and_late_data_rejection`) |
| **DEF-02** | **P0** | 会话停止时灯板处于模式 29，未主动脱离画布模式。 | 会话停止逻辑仅标记内部状态，未通知 `DisplayManager` 恢复普通显示模式，造成旧画面冻结残留。 | 在 `StopSession()` 中判断：若当前显示模式为 `PIXEL_CANVAS` (29)，安全回退至基础灯效 `RAINBOW_WAVE` (1)。 | C++ 测试 9；Python 测试 25 |
| **DEF-03** | **P0** | Jetson Python 重启后，新实例帧号从 0 开始被 ESP32 当作旧帧拒绝。 | `CanvasAssembler::Reset()` 仅清空当前组装缓冲，保留了 `last_committed_frame_id_`，且无重置序号接口。重传小序号帧触发 `stale_frame_id`。 | 新增 `ResetSequence(initial_seq)`，引入 `has_committed_any_frame_` 标志。新会话首帧无论序号大小必定接纳，后续帧严格按 16 位回绕环形差值防重放。 | C++ 测试 12 (`Test_FrameSequence_ResetAndReconnection`) |
| **DEF-04** | **P0** | PC/手机手动选择模式 29 时，未建立人工控制保护，Jetson 可覆盖用户画面。 | `command_dispatcher.cc` 中设置模式时编写了 `dm.SetManualOverride(val != 29)`，误将 29 排除在人工覆盖之外。 | 修正为 `if (is_manual_user) { dm.SetManualOverride(true); }`。只要是用户手动触发，无论切换至何种模式均锁定独占控制。 | C++ 测试 8；Python 测试 19 |
| **DEF-05** | **P0** | Jetson `session start` 携带模式可强制夺取用户控制权。 | `jetson_uart.cc` 收到带 `mode` 的 `session start` 时无条件调用 `SetManualOverride(false)`。 | 调整为仅当显式附带 `take_control: true` 时才允许接管；若人工覆盖处于激活状态且未授权接管，拒绝切换显示模式。 | C++ 测试 8；Python 测试 22 |
| **DEF-06** | **P1** | Jetson 视觉演示无周期心跳，运行约 15 秒后必然超时失效。 | `main.py` 的 `run_vision_demo` 仅在启动前发一次 `session start`，主循环中没有心跳维持。 | 在 `main.py` 主循环加入 3.0 秒非阻塞心跳逻辑；`finally` 块中加入完整的 `release_input` 与 `session stop` 清理。 | Python 客户端测试与超时看门狗测试 |
| **DEF-07** | **P1** | Canvas 演示程序缺少会话生命周期与心跳。 | `run_canvas_demo` 未接入 `session start` / `session stop`，可能在旧会话冲突下推流。 | `run_canvas_demo` 统一接入会话启动、3.0 秒周期心跳、序号初始化与异常退出优雅停止。 | Python 客户端测试 |
| **DEF-08** | **P1** | 二进制帧 CRC 字段为 0 时跳过了校验，存在假阳性隐患。 | 校验条件为 `if (header.crc16 != 0)`，导致合法的 CRC=0x0000 数据包未被校验。 | 引入 `FLAG_SKIP_CRC = (1 << 2)` 显式免检标志。除非头标志指明免检，否则即使 `crc16 == 0` 也必须严格通过校验。 | C++ 测试 13 (`Test_BinaryFrame_StrictCrcAndVersionCheck`) |
| **DEF-09** | **P1** | 二进制帧未核对协议版本与头长度边界。 | `ProcessBinaryFrame` 未检查 `header.version == 1` 及各类帧类型的有效载荷边界。 | 增加 `header.version != 1` 拦截；对全量帧 (768)、单像素 (5)、清屏 (0/3) 及分块实施强类型校验。 | C++ 测试 11、13 |
| **DEF-10** | **P1** | 硬件摄像头失败时，客户端悄悄降级为模拟模式冒充真实视觉。 | `camera_adapter.py` 在 OpenCV 缺失或硬件相机打开失败时自动将 `self.simulate` 置为 `True`。 | 移除自动降级逻辑。硬件相机初始化失败必须明确抛出错误，仅在命令行显式提供 `--simulate` 时才运行模拟数据。 | Python 单元测试 |
| **DEF-11** | **P2** | 街机输入未区分边沿触发；表情识别频繁触发庆祝。 | `vision_mapping.py` 将 `down` 直接赋值给 `pressed`，导致每一帧重复触发上升沿；笑容识别无冷却。 | 增加上升沿计算 `pressed = down & ~last_keys`；为 `celebrate()` 增加 4.0 秒冷却时间防抖。 | Python 单元测试 |
| **DEF-12** | **P2** | 固件与客户端协议版本标识不一致。 | 固件历史常量仍为 `2.3.0`，而文档与交付物称为 `2.3.1`。 | 全工程统一同步版本号常量至 `2.3.1`。 | C++ / Python 测试 |

