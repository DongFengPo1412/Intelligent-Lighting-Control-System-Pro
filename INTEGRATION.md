# 指尖追踪模块：当前正式接入

2026-10-23：组员提供的指尖模块已接入源码与正式构建，并完成离线编译／C++测试；没有烧录或摄像头到灯板的实机验证。总体部署与18项范围见 [PRO_FEATURES](docs/PRO_FEATURES.md)。

- PC：`pc-agent-vision/finger_tip_stream.py`，或统一视觉入口 `multimodal_hub.py`。
- 固件：`firmware-s3/main/display/fingertip_tracker.h/.cc`，已列入 CMake。
- 模式26、`track`、`track_cal`、输入校验、DisplayManager显示锁、正式任务路由及PC模式目录均已接入。

数据流：摄像头 → MediaPipe食指尖点8 → 默认镜像与中央正方形裁剪 → Wi-Fi UDP请求／板端ACK → 平滑／拖尾／丢失动画 → RMT矩阵。

```json
{"cmd":"mode","val":26}
{"cmd":"track","x":0.42,"y":0.63,"visible":true,"conf":0.98}
{"cmd":"track_cal","x0":0.0,"y0":0.0,"x1":1.0,"y1":1.0,"invert_x":false,"invert_y":false}
```

坐标原点左上，x向右、y向下，范围0–1。`visible`为布尔；`conf`可选，缺省1。`track_cal`字段缺省为上例值，输入窗口须有正面积；它不会自动切换模式。部分字段更新也按其余默认值处理，不保留上一次未传入的参数。

独立脚本在未来实际运行时：

```powershell
python pc-agent-vision/finger_tip_stream.py --camera 0 --rate 30
```

该命令会打开摄像头并尝试控制设备，本轮没有执行。`--no-preview`不显示窗口，`--no-mirror`取消镜像，`--no-square-crop`保留完整画面。不要同时运行独立脚本和统一Web视觉入口争用摄像头。

脚本检查Wi-Fi控制状态，拒绝未获回执的模式／坐标请求；不再以USB音频连接作为灯光控制门槛。默认方案逐帧使用现有ACK契约，发送频率只是上限，实际吞吐取决于请求往返。没有声称60FPS或测得端到端延迟。

独立脚本的`conf`来自MediaPipe左右手分类分数，**不是指尖定位置信度**；统一视觉入口只把它当显示权重。单目相对z也不代表米制深度。

可在无设备条件下运行构建出的真实C++离线引擎，选择模式26并注入模拟观察；入口与边界见当前部署指南。
