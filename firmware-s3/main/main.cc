#include <stdio.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <esp_log.h>
#include "display_manager.h"
#include "board_led.h"
#include "command_dispatcher.h"
#include "audio_hal.h"
#include "wifi_manager.h"
#if __has_include("wifi_config.private.h")
#include "wifi_config.private.h"
#else
#include "wifi_config.example.h"
#endif

static const char* TAG = "MainApp";

extern "C" void app_main(void)
{
    ESP_LOGI(TAG, "===============================================================");
    ESP_LOGI(TAG, ">>> [智光魔方 Pro]: ESP32-S3 单板高阶多模态中枢正式启动");
    ESP_LOGI(TAG, ">>> [双核架构]: Core 1 (60FPS 光影物理渲染) | Core 0 (实时指令与通信中枢)");
    ESP_LOGI(TAG, ">>> [声学外设]: I2S INMP441 麦克风 (GPIO 4,5,6) + MAX98357A 扬声器 (GPIO 7,15,16)");
    ESP_LOGI(TAG, ">>> [光场外设]: GPIO 17 硬件 RMT 直驱 16x16 矩阵屏 (FastLED 线性色阶)");
    ESP_LOGI(TAG, ">>> [板载指示]: GPIO 48 硬件 RMT 板载 RGB 指示灯 (开机搜寻呼吸 / 配对常亮绿)");
    ESP_LOGI(TAG, ">>> [通信架构]: USB-Serial-JTAG 物理串口 + 局域网 WiFi UDP 8888 双通道自适应");
    ESP_LOGI(TAG, "===============================================================");

    // 1. 初始化显示引擎 (挂载至 GPIO 17，优先获取 RMT Channel 0 与硬件 GDMA)
    DisplayManager& display = DisplayManager::GetInstance();
    ESP_ERROR_CHECK(display.Init(GPIO_NUM_17));

    // 2. 初始化板载独立 RGB 指示灯 (GPIO 48，上电进入配对呼吸灯模式)
    BoardLed& board_led = BoardLed::GetInstance();
    ESP_ERROR_CHECK(board_led.Init(GPIO_NUM_48));

    // 2. 初始化 I2S 硬件音频驱动 (INMP441 麦克风 + MAX98357 扬声器，开机双音阶自检)
    AudioHAL& audio = AudioHAL::GetInstance();
    ESP_ERROR_CHECK(audio.Init(
        GPIO_NUM_4,  // mic_ws
        GPIO_NUM_5,  // mic_sck
        GPIO_NUM_6,  // mic_din
        GPIO_NUM_7,  // spk_dout
        GPIO_NUM_15, // spk_bclk
        GPIO_NUM_16  // spk_lrck
    ));

    // 3. 单块 16x16 蛇形灯板统一亮度，不再应用四块拼接板的梯级补偿。
    display.SetBrightness(20);

    // 4. 启动后台独立物理渲染引擎 (运行在 Core 1，优先级 5)
    ESP_ERROR_CHECK(display.StartTask(5, 1));

    // 5. 启动后台串口指令调度中枢 (运行在 Core 0，优先级 4，负责 USB 极速解析)
    CommandDispatcher& dispatcher = CommandDispatcher::GetInstance();
    ESP_ERROR_CHECK(dispatcher.StartSerialTask(4, 0));

    // 6. 启动全时无线 WiFi APSTA 双模共存与 UDP 8888 监听 (脱离 USB 数据线，外部电源供电依然100%互联！)
    WifiManager& wifi = WifiManager::GetInstance();
    wifi.InitAndConnect(KURISU_WIFI_STA_SSID, KURISU_WIFI_STA_PASSWORD,
                        KURISU_WIFI_AP_SSID, KURISU_WIFI_AP_PASSWORD, 8888);

    // 7. 初始默认展示：牧濑红莉栖桌宠伴侣 (同时保留模式 14 经典圆形变脸特效)
    display.SetMode(DisplayMode::KURISU_DESK_PET);

    ESP_LOGI(TAG, ">>> [中枢就绪]: 已就绪监听串口指令！可用命令示例：");
    ESP_LOGI(TAG, "    - 倒计时: 'countdown 60' 或 '{\"cmd\":\"countdown\",\"seconds\":60}'");
    ESP_LOGI(TAG, "    - 换灯效: 'fire', 'matrix', 'rainbow', 'aurora', 'mode 23' 等");
    ESP_LOGI(TAG, "    - 调亮度: 'brightness 25' 或 'b 30'");
    ESP_LOGI(TAG, "    - 查状态: 'status'");

    // 6. 主循环：进入极低功耗心跳监听 (不与渲染和串口争抢 CPU 资源)
    uint32_t heartbeat_tick = 0;
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(5000));
        heartbeat_tick++;

        if (display.IsCountdownActive()) {
            ESP_LOGI(TAG, "[心跳 #%u]: 倒计时运行中，剩余 %u 秒",
                     (unsigned int)heartbeat_tick,
                     (unsigned int)display.GetCountdownRemainingSeconds());
        } else {
            ESP_LOGD(TAG, "[心跳 #%u]: 当前显示模式 %d", (unsigned int)heartbeat_tick, (int)display.GetMode());
        }
    }
}
