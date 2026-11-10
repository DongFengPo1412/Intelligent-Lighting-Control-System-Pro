# Intelligent Lighting Control System Pro — Jetson Nano 组员交接指南 (v2.3.1)

本指南专门面向负责 **Jetson Nano Linux 视觉计算上位机** 开发的组员。  
ESP32-S3 端底层固件已完成编译、验证与功能冻结。您只需要基于我们提供的独立轻量开发包 `jetson-nano.zip`，即可在 Linux 环境下完成全速 16×16 全彩画面推流与 AI 视觉模型对接，**无需编译或烧录 ESP32**。

---

## 一、物理接线指南 (40-Pin Header $\leftrightarrow$ ESP32-S3)

Jetson Nano J41 40-Pin 接线端子采用 3.3V TTL 电平，请使用 3 根母对母杜邦线连接：

| Jetson Nano (J41 端子) | 引脚功能 | 对应设备节点 | ESP32-S3 开发板引脚 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| **Pin 8** | UART2_TXD | `/dev/ttyTHS1` | **GPIO 8** (RXD) | Jetson 发送数据至 ESP32 |
| **Pin 10** | UART2_RXD | `/dev/ttyTHS1` | **GPIO 9** (TXD) | Jetson 接收 ESP32 回执与状态 |
| **Pin 6 / 9 / 14 / 20 / 39** | GND | - | **GND** | **双方必须共地** |

> [!IMPORTANT]
> 1. 电平标准：3.3V TTL，波特率 `115200`，数据位 8，停止位 1，无奇偶校验 (8N1)，无硬件流控。
> 2. 请确保 Jetson Nano 用户具有串口权限：`sudo usermod -aG dialout $USER`（执行后需重新登录生效）。

---

## 二、工程目录结构与依赖安装

解压 `jetson-nano.zip` 后的目录结构：

```text
jetson-nano/
├── config.json              # 默认配置文件（串口波特率、摄像头参数、手势映射）
├── protocol.py              # 通信协议序列化库（含二进制包打包与 CRC16）
├── uart_transport.py        # 健壮的后台异步串口通信驱动（自动线程、ACK匹配）
├── canvas_stream.py         # 16×16 全彩画布推流器（支持单包 768 字节满速推流）
├── camera_adapter.py        # 摄像头接入适配层（支持 CSI / USB 摄像头）
├── vision_mapping.py        # 视觉坐标/手势事件映射器（内置防抖、边沿触发与释键看门狗）
├── main.py                  # 统一命令行交互与演示入口
├── requirements.txt         # 核心 Python 依赖 (pyserial)
├── README_ZH.md             # 快速参考说明
└── tests/
    └── test_jetson_nano.py  # 客户端自测试套件
```

### 快速初始化环境：
```bash
# 1. 解压交付包
unzip jetson-nano.zip -d jetson-nano
cd jetson-nano

# 2. 创建 Python 虚拟环境
python3 -m venv venv
source venv/bin/activate

# 3. 安装依赖
pip3 install -r requirements.txt
```

---

## 三、快速开始与联调验证

### 1. 运行自检套件
```bash
python3 -m unittest discover -s tests -v
```
若全部显示 `OK`，说明本地协议库与算法发生器完全正常。

### 2. 交互式命令行控制台
```bash
python3 main.py interactive --port /dev/ttyTHS1
```
进入控制台后可直接输入指令：
- `ping`：验证双向串口连通性（返回 `{"status":"ok","pong":true}`）。
- `status`：查看 ESP32 当前运行状态与模式。
- `mode 29`：将点阵屏切入自由画布模式。
- `track 0.5 0.5`：发送手势跟随光标（处于屏幕正中央）。

### 3. 运行 16×16 全彩自由画布推流演示
```bash
# 运行极速二进制色彩波纹动画 (12 FPS)
python3 main.py canvas --pattern wave --protocol binary --fps 12 --port /dev/ttyTHS1

# 运行黑客帝国数字雨动画
python3 main.py canvas --pattern matrix --protocol binary --fps 12 --port /dev/ttyTHS1

# 运行壁炉火焰模拟
python3 main.py canvas --pattern fire --protocol binary --fps 12 --port /dev/ttyTHS1
```

---

## 四、组员 AI 视觉算法模型接入位置

在 `main.py` 的 `run_vision_demo` 函数中，我们已经封装好了会话维持、心跳守护与看门狗：

```python
# main.py (第 260 行左右)
while True:
    ret, frame = camera.read_frame()
    if not ret:
        time.sleep(0.03)
        continue

    # ==============================================================
    # 组员接入真实 AI 模型区域 (MediaPipe / TensorRT / YOLO / OpenCV)
    # ==============================================================
    # 示例: 
    # 1. landmarks = my_hand_detector.process(frame)
    # 2. x, y = landmarks.wrist.x, landmarks.wrist.y
    # 3. is_pinch = landmarks.is_pinching()
    # 4. 直接调用我们提供的映射器即可驱动 ESP32:
    mapper.handle_hand_frame(visible=True, x=x, y=y, pinch=is_pinch, mode="fingertip")
```

---

## 五、常见问题与排除方法

| 现象 | 可能原因 | 解决方法 |
| :--- | :--- | :--- |
| `PermissionError: [Errno 13] Permission denied: '/dev/ttyTHS1'` | Linux 用户未加入 `dialout` 用户组 | 执行 `sudo usermod -aG dialout $USER` 并注销重登。 |
| 发送指令后超时无响应 (`timeout`) | 1. 杜邦线未接对；<br>2. 双方未共地；<br>3. 端口占用。 | 检查 Pin 8 (TX) 接 ESP32 GPIO 8 (RX)，Pin 10 (RX) 接 ESP32 GPIO 9 (TX)，并确保 GND 紧密相连。 |
| 动画正常推送但屏幕显示用户模式 (`displayed: false`) | 手机 App 或 PC 端正在手动操作控制灯板 | 手机 App 释放控制或切回普通灯效后，Jetson 画面将自动恢复呈现。 |
| 运行程序报错 `Failed to open hardware camera` | 未插入摄像头或相机索引错误 | 若无实体摄像头需体验功能，请在命令行追加 `--simulate` 参数。 |

