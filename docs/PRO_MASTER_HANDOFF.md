# Intelligent Lighting Control System Pro — Jetson 组员独立开发与交接手册

**文档编号**：HANDOFF-20261111-PRO-MASTER  
**版本标识**：Pro v2.3.1 冻结交付版  
**交接对象**：Jetson Nano 视觉与端侧算法开发组员  

---

## 一、 系统工程分工与状态冻结说明

经过四轮严格的代码审计、缺陷闭环与物理芯片烧录验证，**ESP32-S3 固件已正式达到生产级终极冻结状态**。

```
+-------------------------------------------------------------+
|                     系统工程架构与权限边界                   |
+-------------------------------------------------------------+
|                                                             |
|  [ESP32-S3 硬件主控]  =======> 【彻底冻结 (FROZEN)】         |
|  - 256 WS2812B 硬件 DMA 渲染 (30 FPS)                       |
|  - 100 款完整街机游戏引擎                                   |
|  - I2S 音频与双向 WiFi 通信                                 |
|  - 16x16 通用全彩像素画布接收引擎                           |
|  * 组员在后续开发中【无需、也严禁】重新烧录 ESP32 固件！      |
|                                                             |
|  [PC 端上位机中枢]   =======> 【基础核心冻结】               |
|  - 本地 Qwen 大模型推理、中日双语 TTS、Web/APK 管理          |
|                                                             |
|  [Jetson Nano 端]    =======> 【完全交由组员独立自主开发】   |
|  - 组员可使用纯 Python 自由编写视觉检测模型与手势识别        |
|  - 组员可使用纯 Python 自由开发 16x16 原创像素动画推流      |
+-------------------------------------------------------------+
```

---

## 二、 物理硬件引脚连接指南

Jetson Nano J41 40-Pin 排针与 ESP32-S3 之间的连接极其简单，只需 3 根杜邦线：

```
Jetson Nano (J41)                       ESP32-S3-N16R8 开发板
+-----------------------+               +-----------------------+
| Pin 8  (UART1 TXD)    | ------------> | GPIO 8 (UART RX)      |
| Pin 10 (UART1 RXD)    | <------------ | GPIO 9 (UART TX)      |
| Pin 6  (GND 地线)     | ============= | GND   (公共地)        |
+-----------------------+               +-----------------------+
```

> [!CAUTION]
> **切记务必共地 (Pin 6 连接 ESP32 GND)**！如果不接公共地线，两块开发板的地电位不同将导致串口误码率激增甚至无法识别帧头。

---

## 三、 Jetson 端快速上手与环境初始化

### 1. 解压交付包
从仓库根目录拷贝 `jetson-nano.zip` 至 Jetson Nano Linux 桌面或工作目录并解压：
```bash
unzip jetson-nano.zip -d jetson-nano
cd jetson-nano
```

### 2. 串口免 Root 权限与系统服务排查
```bash
# 加入 dialout 用户组
sudo usermod -aG dialout $USER

# 禁用占用 /dev/ttyTHS1 的默认串口终端服务
sudo systemctl stop nvgetty
sudo systemctl disable nvgetty
```
修改完成后**注销并重新登录**。

### 3. 安装依赖
```bash
pip3 install pyserial
```

---

## 四、 组员核心任务与 Python 开发接口

组员在 Jetson 上的全部工作均被封装在纯 Python 层，无需触碰底层 C/C++。

### 1. 推送原创 16×16 像素动画（无需重烧 ESP32！）
组员可以使用 `canvas_stream.py` 中的 `CanvasStreamer` 直接将任意 numpy / PIL 画面发送给灯板：

```python
import time
from uart_transport import UartTransport
from canvas_stream import CanvasStreamer

# 1. 建立串口连接并开启会话 (自动完成心跳守护与序列号同步)
transport = UartTransport(port="/dev/ttyTHS1", baudrate=115200)
streamer = CanvasStreamer(transport)
streamer.start()

# 2. 连续推送 16×16 RGB 像素画面 (768 字节)
try:
    while True:
        # 组员在此处自行生成 256 颗 RGB 像素 (768 字节的 bytes 对象)
        rgb_data = bytes([255, 0, 0] * 256) # 示例：全屏纯红
        
        # 以 12 FPS 流水线模式推送
        streamer.send_full_frame(rgb_data, auto_mode=True)
        time.sleep(1.0 / 12)
finally:
    streamer.stop() # 退出时自动安全切回彩虹波
    transport.close()
```

### 2. 接入真实视觉模型（摄像头与 MediaPipe/YOLO）
在 `main.py` 的 `run_vision_demo` 函数中，组员只需替换相机帧推理部分：
* 将食指尖物理坐标归一化到 `0.0 ~ 1.0`，调用 `builder.fingertip(x, y, visible=True)` 驱动灯板光点跟随；
* 检测到双手捏合动作，调用 `builder.hand(x, y, z, pinch=True)` 驱动光球抓取与波纹特效；
* 检测到人脸笑容，调用 `builder.celebrate()` 触发全屏礼花特效。

---

## 五、 常见问题与联调排障

| 异常现象 | 可能原因 | 解决办法 |
| :--- | :--- | :--- |
| 发送指令后串口超时无应答 (`timeout`) | 1. 串口引脚反接；<br>2. 双方未共地；<br>3. `nvgetty` 占用了端口。 | 检查 Pin 8 接 GPIO 8，Pin 10 接 GPIO 9，Pin 6 接 GND；确认已执行 `sudo systemctl stop nvgetty`。 |
| 动画正常推送但灯板不显示画面 (`displayed: false`) | 手机 App 或 PC 端正在手动操作控制灯板（人工独占锁激活） | 手机端释放手动操作或切回自动灯效后，Jetson 画面将自动恢复呈现。 |
| 重新启动 Python 脚本后报 `stale_frame_id` | 旧版未同步序列号（已在此版本彻底修复） | 本版固件支持客户端每次启动自动重置 `initial_seq=0`，直接正常运行。 |
| 物理摄像头打不开报错 | 摄像头未正确挂载到 `/dev/video0` | 检查 USB/CSI 相机排线；若仅需测试灯效与协议链路，在命令行添加 `--simulate` 参数即可启动高质量体感仿真。 |

