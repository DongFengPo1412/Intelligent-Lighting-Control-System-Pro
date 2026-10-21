> 交接状态：本文与根目录指尖源码是待集成参考资料，当前运行固件尚未接入模式 26 和 track 命令。本文描述的是接入方案，并非已实现功能。当前普通灯控已支持板端 Wi-Fi UDP 接收与确认；文末关于仅支持串口的描述属于旧状态。

# 指尖追踪灯光效果接入说明

这套代码分成两半：

- `pc/finger_tip_stream.py`：在 PC 上用 MediaPipe 找到食指指尖，持续把归一化坐标通过串口发给 ESP32-S3。
- `firmware/fingertip_tracker.h/.cc`：在 ESP32-S3 上把坐标映射到 16×16 灯板，负责平滑、拖尾、变色和丢失后的呼吸动画。

摄像头识别和灯效渲染是解耦的。以后换成别的手部检测模型，只要继续发送同样的 `track` JSON 即可。

## 1. 数据流

```text
USB 摄像头
   │
   ▼
MediaPipe Hands
   │  食指指尖 landmark[8]
   ▼
归一化坐标 (x, y) ∈ [0, 1]
   │
   ▼
{"cmd":"track","x":0.42,"y":0.63,"visible":true,"conf":0.98}
   │  USB-Serial-JTAG
   ▼
CommandDispatcher
   │
   ▼
DisplayManager::FeedFingertip()
   │
   ▼
FingertipTracker::FeedTarget()
   │  映射 + 平滑 + 拖尾
   ▼
DisplayHAL::SetPixel() -> RMT -> 16×16 WS2812
```

## 2. 固件接入步骤

### 2.1 增加显示模式

在 `firmware-s3/main/display/display_types.h` 的 `DisplayMode` 枚举末尾增加：

```cpp
    FINGERTIP_TRACKER = 26,     // 26: 摄像头指尖追踪光点
```

### 2.2 让 DisplayManager 持有追踪引擎

在 `display_manager.h` 中增加头文件和成员：

```cpp
#include "fingertip_tracker.h"

// public:
    void FeedFingertip(float nx, float ny, bool visible, float confidence = 1.0f);
    FingertipTracker& GetFingertipTracker() { return fingertip_tracker_; }

// private:
    FingertipTracker fingertip_tracker_;
```

在 `display_manager.cc` 的三处位置接入：

```cpp
// Init() 中，初始化其他引擎之后
fingertip_tracker_.Reset();

// DisplayTaskLoop() 的模式切换分支中
} else if (mode == DisplayMode::FINGERTIP_TRACKER) {
    fingertip_tracker_.Reset();
}

// DisplayTaskLoop() 的 switch 中
case DisplayMode::FINGERTIP_TRACKER:
    delay_ms = fingertip_tracker_.RenderFrame();
    break;
```

再增加两个转发方法：

```cpp
void DisplayManager::FeedFingertip(float nx, float ny, bool visible, float confidence)
{
    fingertip_tracker_.FeedTarget(nx, ny, visible, confidence);
}
```

### 2.3 解析串口坐标

在 `command_dispatcher.cc` 的 `ProcessJsonCommand()` 中增加 `track` 分支：

```cpp
else if (strcasecmp(cmd, "track") == 0) {
    cJSON* x_item = cJSON_GetObjectItem(root, "x");
    cJSON* y_item = cJSON_GetObjectItem(root, "y");

    // 没有 x/y 时只切换模式，方便发送 {"cmd":"track"}
    if (!x_item || !y_item) {
        dm.SetMode(DisplayMode::FINGERTIP_TRACKER);
        cJSON_Delete(root);
        return true;
    }
    if (!cJSON_IsNumber(x_item) || !cJSON_IsNumber(y_item)) {
        cJSON_Delete(root);
        return false;
    }

    bool visible = true;
    cJSON* vis_item = cJSON_GetObjectItem(root, "visible");
    if (vis_item && cJSON_IsBool(vis_item)) {
        visible = cJSON_IsTrue(vis_item);
    }

    float confidence = 1.0f;
    cJSON* conf_item = cJSON_GetObjectItem(root, "conf");
    if (conf_item && cJSON_IsNumber(conf_item)) {
        confidence = (float)conf_item->valuedouble;
    }

    dm.FeedFingertip((float)x_item->valuedouble,
                     (float)y_item->valuedouble,
                     visible, confidence);
    cJSON_Delete(root);
    return true;
}
else if (strcasecmp(cmd, "track_cal") == 0) {
    cJSON* x0 = cJSON_GetObjectItem(root, "x0");
    cJSON* y0 = cJSON_GetObjectItem(root, "y0");
    cJSON* x1 = cJSON_GetObjectItem(root, "x1");
    cJSON* y1 = cJSON_GetObjectItem(root, "y1");

    const float x_min = (x0 && cJSON_IsNumber(x0)) ? (float)x0->valuedouble : 0.0f;
    const float y_min = (y0 && cJSON_IsNumber(y0)) ? (float)y0->valuedouble : 0.0f;
    const float x_max = (x1 && cJSON_IsNumber(x1)) ? (float)x1->valuedouble : 1.0f;
    const float y_max = (y1 && cJSON_IsNumber(y1)) ? (float)y1->valuedouble : 1.0f;

    cJSON* ix = cJSON_GetObjectItem(root, "invert_x");
    cJSON* iy = cJSON_GetObjectItem(root, "invert_y");
    const bool invert_x = (ix && cJSON_IsBool(ix)) ? cJSON_IsTrue(ix) : false;
    const bool invert_y = (iy && cJSON_IsBool(iy)) ? cJSON_IsTrue(iy) : false;

    dm.GetFingertipTracker().SetInputWindow(x_min, y_min, x_max, y_max);
    dm.GetFingertipTracker().SetInvert(invert_x, invert_y);
    cJSON_Delete(root);
    return true;
}
```

### 2.4 高频坐标包不要回 ACK

现有 `ProcessLine()` 会对每条成功指令回一条 `{"status":"ok"}`，并且会用 `ESP_LOGI` 打印整条指令。跟踪坐标每秒 30～60 包，如果每包都回 ACK、都打日志，会明显浪费串口带宽并增加延迟。

建议在 `CommandDispatcher` 中增加一个 `bool suppress_reply_` 成员（构造函数里初始化为 `false`），并在 `ProcessLine()` 里这样处理：

```cpp
suppress_reply_ = false;   // 每次解析新行前重置

if (*line == '{') {
    if (ProcessJsonCommand(line)) {
        if (!suppress_reply_) {
            SendReply("{\"status\":\"ok\"}\r\n");
        }
        return;
    }
}
```

在 `track` 分支成功调用 `dm.FeedFingertip(...)` 后加上：

```cpp
suppress_reply_ = true;
```

同时把高频坐标包的日志关掉。可以在 `ProcessLine()` 打印日志之前加：

```cpp
const bool is_track_stream =
    (strstr(line, "\"cmd\":\"track\"") != nullptr) ||
    (strncmp(line, "track ", 6) == 0);

if (!is_track_stream) {
    ESP_LOGI(TAG, ">>> [收到外部指令]: %s", line);
}
```

`track_cal` 不是高频指令，仍然会正常打印和回复。

纯文本模式可以再加一条：

```cpp
if (strcasecmp(text_str, "track") == 0 ||
    strcasecmp(text_str, "fingertip") == 0) {
    dm.SetMode(DisplayMode::FINGERTIP_TRACKER);
    return true;
}
```

### 2.5 加入编译

在 `firmware-s3/main/CMakeLists.txt` 的 `SRCS` 中加入：

```cmake
"display/fingertip_tracker.cc"
```

## 3. 协议

### 切换模式

```json
{"cmd":"mode","val":26}
```

或者纯文本：

```text
mode 26
fingertip
track
```

### 推送坐标

```json
{"cmd":"track","x":0.42,"y":0.63,"visible":true,"conf":0.98}
```

- `x`、`y`：0.0～1.0，原点在摄像头画面左上角，`y` 向下增大。
- `visible`：是否检测到手；`false` 时保留最后位置并播放呼吸回落。
- `conf`：可选，默认 1.0；会轻微影响光点亮度。

没有手时建议继续低频发送：

```json
{"cmd":"track","x":0.5,"y":0.5,"visible":false,"conf":0.0}
```

### 校准映射区域

如果不想在 Python 端裁成正方形，也可以让固件只取画面中央区域：

```json
{"cmd":"track_cal","x0":0.21875,"y0":0.0,"x1":0.78125,"y1":1.0}
```

上面的数值对应 16:9 画面中央的正方形区域。`track_cal` 还支持：

```json
{"cmd":"track_cal","invert_x":true,"invert_y":false}
```

实际解析时，`invert_x` / `invert_y` 缺省为 `false`。如果摄像头没有镜像，可以反转 `x`。

## 4. 参数调节

在 `DisplayManager::Init()` 里可以统一配置：

```cpp
fingertip_tracker_.SetSmoothing(0.07f, 0.04f); // 时间常数 / 死区
fingertip_tracker_.SetTrailLength(9);          // 0 关闭拖尾，最大 10
fingertip_tracker_.SetLostTimeout(4000);       // 丢失后呼吸提示 4 秒
fingertip_tracker_.SetColors(ColorRGB(230, 255, 255),
                             ColorRGB(0, 190, 255));
```

调参建议：

- 光点明显滞后：把 `0.07f` 降到 `0.04f` 左右。
- 光点抖动：把时间常数加到 `0.10f`～`0.15f`，或增大死区。
- 拖尾太短：把拖尾点数加到 10；想更干净就降到 4～6。
- 边缘总差一点：检查 `SetInputWindow()` 的裁剪范围，或调整 Python 的 `--square-crop`。

## 5. 运行

先把固件烧录好，确认 PC 能通过 `light_controller.py` 连接 ESP32-S3。把 `pc/finger_tip_stream.py` 复制到项目的 `pc-agent-vision/` 目录（和 `light_controller.py` 放在一起），然后：

```bash
cd pc-agent-vision
python finger_tip_stream.py --camera 0 --rate 40
```

常用选项：

```text
--no-preview        无窗口运行
--no-mirror         不镜像摄像头
--no-square-crop    使用完整画面而不是中央正方形
--camera 1          切换摄像头
--rate 30           降低串口发送频率
```

## 6. 视觉说明

灯板上会显示：

- 很暗的 4×4 网格，用于提示摄像头画面与灯阵的对应关系；
- 一个青色光晕、亮白核心和短刻度的追踪器；
- 快速移动时颜色会从青色偏向品红；
- 身后有 450ms 左右的渐隐拖尾；
- 手离开画面后，最后位置会播放一个扩散呼吸环，4 秒后淡出。

默认跟踪食指指尖（MediaPipe landmark `8`）。如果要跟踪其他手指，改 `finger_tip_stream.py` 里的 `INDEX_FINGER_TIP`：拇指 `4`、中指 `12`、无名指 `16`、小指 `20`。

## 7. 关于 Wi-Fi

当前固件的命令入口是 USB-Serial-JTAG，`LightController.send_json()` 走的是串口。仓库里的 `wifi_gateway.py` 只是 PC 端 UDP 发送器，固件端还没有对应的 UDP 接收任务。如果要走 Wi-Fi，需要在 S3 侧增加 UDP/WebSocket 接收，并把收到的同一份 `track` JSON 交给 `CommandDispatcher::ProcessLine()`；灯效引擎本身不需要改动。
