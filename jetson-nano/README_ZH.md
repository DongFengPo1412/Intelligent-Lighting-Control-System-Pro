# Jetson Nano 与 ESP32-S3 全视觉互通开发指引

本工程为运行在 **Jetson Nano (Linux Ubuntu 18.04 / 20.04)** 上的独立 Python 交互套件。  
通过 GPIO 硬件串口（UART1）与 ESP32-S3 灯板主控进行全双工通信，支持：
1. **基础控制**：灯效模式切换、亮度调节、板载指示灯、状态查询。
2. **手势与指尖追踪**：实时指尖归一化坐标、可见性、置信度，驱动模式 26 指尖光点跟随。
3. **捏合与 3D 交互**：相对深度 `z`、捏合手势 `pinch`，驱动模式 27 光球抓取与波纹渲染。
4. **桌宠与表情联动**：人脸存在、视线偏角、疲劳检测、微笑放烟花联动模式 17 牧濑红莉栖桌宠。
5. **街机体感游戏**：手势控制正式 100 合 1 街机（#033 贪吃蛇、#041 俄罗斯方块等），具备**离手自动释键**安全机制。
6. **16×16 通用像素画布**：组员在 Jetson Linux 上用 Python 生成的任意新灯效动画，直接通过串口推送到模式 29 显示，**无需重新烧录 ESP32**！

---

## 一、 硬件接线说明

Jetson Nano J41 40-Pin 扩展排针与 ESP32-S3 连接方式：

| Jetson Nano (J41) | 功能 | ESP32-S3 引脚 | 说明 |
|---|---|---|---|
| **Pin 8 (UART1 TX)** | TXD 发送 | **GPIO 8 (RX)** | Jetson 发送数据至 ESP32 |
| **Pin 10 (UART1 RX)** | RXD 接收 | **GPIO 9 (TX)** | ESP32 回传 ACK/状态至 Jetson |
| **Pin 6 (GND)** | 地线 | **GND** | 必须共地！ |

> [!IMPORTANT]
> 1. 双方通信电平均为 **3.3V TTL**，严禁接 5V！
> 2. 默认波特率为 **115200 bps, 8N1**，无流控。
> 3. Jetson Linux 对应串口设备节点通常为 `/dev/ttyTHS1`。

---

## 二、 Linux 环境准备

### 1. 串口权限设置
在 Jetson Nano 终端中运行：
```bash
# 将当前用户加入 dialout 组以获得免 root 串口权限
sudo usermod -aG dialout $USER

# 若 /dev/ttyTHS1 被 nvgetty 系统服务占用，禁用该服务：
sudo systemctl stop nvgetty
sudo systemctl disable nvgetty
```
修改完成后请**注销并重新登录**（或重启 Jetson）。

### 2. Python 依赖
仅依赖标准库及 `pyserial`（若需要运行摄像头，安装 `opencv-python`）：
```bash
pip3 install pyserial
# 可选（如果有物理摄像头）：
# sudo apt-get install python3-opencv
```

---

## 三、 使用模式

所有功能均通过统一命令行入口 `main.py` 调用。

### 1. 交互式调试控制台 (Interactive)
```bash
python3 main.py interactive
```
支持输入以下命令并实时查看 ESP32 回包：
- `ping`：测试双向连通性与时延。
- `status`：查询当前显示模式、亮度、街机游戏与画布状态。
- `caps`：查询 ESP32 固件能力特性集与硬件分辨率（16×16）。
- `mode 1`：切换到红灯（或输入 `mode 17` 切换到桌宠）。
- `b 20`：调整亮度（0-60）。
- `arcade select 33`：选择贪吃蛇游戏。
- `arcade start`：启动游戏。
- `arcade in right`：发送右移手柄按键。
- `pixel 7 7 255 128 0`：在第 (7, 7) 坐标点亮一个橙色像素。
- `clear`：清空画布。

### 2. 动态像素动画演示 (Canvas Demo)
在 Jetson 上实时生成 16×16 动画并推送到 ESP32（模式 29）：
```bash
# 运行高帧率平滑色彩波浪动画 (默认二进制协议，约 12-15 FPS)
python3 main.py canvas --pattern wave --protocol binary

# 运行经典绿黑代码雨 (Matrix Rain)
python3 main.py canvas --pattern matrix --protocol binary

# 运行真实热对流火焰模拟 (Fire)
python3 main.py canvas --pattern fire --protocol binary

# 运行发光弹跳光球 (Ball)
python3 main.py canvas --pattern ball --protocol binary
```

### 3. 视觉识别与手势交互 (Vision Demo)
```bash
# 启动视觉识别演示 (若无物理摄像头，加上 --simulate 即可体验平滑模拟体感)
python3 main.py vision --simulate
```

### 4. 自动化连通性诊断自检 (Test)
```bash
python3 main.py test
```
自动逐项验证：PingPong、Status、Capabilities、Mode 17 切换、指尖追踪、手势捏合、桌宠上下文、按键安全释放、单像素点亮、两分块 CRC 校验重组、高速二进制整帧提交等 12 项指标。

---

## 四、 组员二次开发指南

组员只需编写 Python 代码即可实现自己的新功能：

### 1. 接入自己的视觉/手势模型
打开 [`vision_mapping.py`](file:///C:/workspace/Intelligent-Lighting-Control-System-Pro/jetson-nano/vision_mapping.py)，在 `handle_hand_frame` 或 `handle_gesture` 中接入你的模型推理输出：
```python
# 示例：检测到右手食指在 (x, y)
mapper.handle_hand_frame(visible=True, x=norm_x, y=norm_y, pinch=is_pinched, mode="fingertip")

# 示例：手移出画面或丢失，只需传入 visible=False，系统会自动触发按键安全释放：
mapper.handle_hand_frame(visible=False, mode="arcade")
```

### 2. 编写自己的全新像素动画
打开 [`canvas_stream.py`](file:///C:/workspace/Intelligent-Lighting-Control-System-Pro/jetson-nano/canvas_stream.py)，使用 `streamer.send_binary_frame(colors)`：
```python
from canvas_stream import CanvasStreamer
from uart_transport import JetsonUartTransport

transport = JetsonUartTransport(port="/dev/ttyTHS1")
transport.connect()
streamer = CanvasStreamer(transport)

# colors 为长度 256 的列表，每个元素为 (R, G, B) 元组 (0-255)
colors = [(255, 0, 0)] * 256  # 全红
streamer.send_binary_frame(colors, auto_mode=True)
```
无论是文字跑马灯、天气图表、雷达扫描还是音频频谱，全部在 Python 侧计算完成并直接在 ESP32 上显示，**彻底摆脱嵌入式 C++ 重新编译与烧录**！
