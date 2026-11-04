#include <stdio.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <esp_log.h>
#include <esp_heap_caps.h>
#include "arcade_sound.h"
#include "display_manager.h"
#include "network_audio.h"
#include "board_led.h"
#include "command_dispatcher.h"
#include "audio_hal.h"
#include "arcade_audio_task.h"
#include "wifi_manager.h"
#include "arcade_manager.h"
#include "arcade_score_store.h"
#include "network_auth.h"
#include <nvs_flash.h>
#if __has_include("wifi_config.private.h")
#include "wifi_config.private.h"
#else
#include "wifi_config.example.h"
#endif

static const char* TAG = "MainApp";

// Low-rate serial-only diagnostics. No additional task, allocation or control endpoint.
static void LogRuntimeBudget() {
    ESP_LOGI("RuntimeBudget", "internal_free=%u internal_min=%u internal_largest=%u psram_free=%u psram_largest=%u",
        unsigned(heap_caps_get_free_size(MALLOC_CAP_INTERNAL|MALLOC_CAP_8BIT)),
        unsigned(heap_caps_get_minimum_free_size(MALLOC_CAP_INTERNAL|MALLOC_CAP_8BIT)),
        unsigned(heap_caps_get_largest_free_block(MALLOC_CAP_INTERNAL|MALLOC_CAP_8BIT)),
        unsigned(heap_caps_get_free_size(MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT)),
        unsigned(heap_caps_get_largest_free_block(MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT)));
    ESP_LOGI("RuntimeBudget", "stack_min_bytes main=%u display=%u sfx=%u pcm_play=%u",
        unsigned(uxTaskGetStackHighWaterMark(nullptr)),unsigned(DisplayManager::GetInstance().StackFreeBytes()),
        unsigned(ArcadeAudioStackFreeBytes()),unsigned(CommandDispatcher::GetInstance().AudioStackFree()));
    auto& bus=arcade::Sounds();
    ESP_LOGI("RuntimeBudget", "sfx queued=%u dropped=%u played=%u preempted=%u busy=%u short=%u late=%u faults=%u",
        unsigned(bus.queued.load()),unsigned(bus.dropped.load()),unsigned(bus.played.load()),
        unsigned(bus.preempted.load()),unsigned(bus.busy.load()),unsigned(bus.short_writes.load()),
        unsigned(bus.late.load()),unsigned(bus.faults.load()));
}

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
    // 0. 初始化 NVS 非易失性存储 (街机最高分持久化与 Wi-Fi 凭据)
    esp_err_t nvs_ret = nvs_flash_init();
    // Never silently erase scores, pairing keys, or Wi-Fi credentials.
    if (nvs_ret != ESP_OK) ESP_LOGE(TAG, "NVS unavailable: %s; back up/recover it explicitly", esp_err_to_name(nvs_ret));
    arcade::ArcadeScoreStore::SetReady(nvs_ret == ESP_OK);
    NetworkAuth::GetInstance().Init(nvs_ret == ESP_OK);

    // 显式在 NVS 就绪后初始化统一街机管理器
    arcade::ArcadeManager::GetInstance().Init();

    DisplayManager& display = DisplayManager::GetInstance();
    ESP_ERROR_CHECK(display.Init(GPIO_NUM_17));

    // 2. 初始化板载独立 RGB 指示灯 (GPIO 48，上电进入配对呼吸灯模式)
    BoardLed& board_led = BoardLed::GetInstance();
    ESP_ERROR_CHECK(board_led.Init(GPIO_NUM_48));

    // 2. 初始化 I2S 硬件音频驱动 (INMP441 麦克风 + MAX98357 扬声器，开机双音阶自检)
    AudioHAL& audio = AudioHAL::GetInstance();
    esp_err_t audio_ret = audio.Init(
        GPIO_NUM_4,  // mic_ws
        GPIO_NUM_5,  // mic_sck
        GPIO_NUM_6,  // mic_din
        GPIO_NUM_7,  // spk_dout
        GPIO_NUM_15, // spk_bclk
        GPIO_NUM_16  // spk_lrck
    );
    if (audio_ret != ESP_OK)
        ESP_LOGE(TAG, "Audio unavailable: %s; light/control operation remains available", esp_err_to_name(audio_ret));

    if(audio.IsInitialized() && !StartArcadeAudioTask())ESP_LOGW(TAG,"Arcade sound worker unavailable; games remain usable silently");

    // 3. 单块 16x16 蛇形灯板统一亮度，不再应用四块拼接板的梯级补偿。
    display.SetBrightness(20);

    // 4. 启动后台独立物理渲染引擎 (运行在 Core 1，优先级 5)
    ESP_ERROR_CHECK(display.StartTask(5, 1));

    // 5. 启动后台串口指令调度中枢 (运行在 Core 0，优先级 4，负责 USB 极速解析)
    CommandDispatcher& dispatcher = CommandDispatcher::GetInstance();
    ESP_ERROR_CHECK(dispatcher.StartSerialTask(4, 0));

    // 6. 启动全时无线 WiFi APSTA 双模共存与 UDP 8888 监听 (脱离 USB 数据线，外部电源供电依然100%互联！)
    WifiManager& wifi = WifiManager::GetInstance();
    esp_err_t wifi_ret = wifi.InitAndConnect(KURISU_WIFI_STA_SSID, KURISU_WIFI_STA_PASSWORD,
                        KURISU_WIFI_AP_SSID, KURISU_WIFI_AP_PASSWORD, 8888);
    if (wifi_ret != ESP_OK) ESP_LOGE(TAG,"Wi-Fi unavailable: %s; USB/display remain available",esp_err_to_name(wifi_ret));
    else if(audio.IsInitialized() && !NetworkAudio::GetInstance().Start())ESP_LOGE(TAG,"Wi-Fi PCM server failed to start");

    // 7. 初始默认展示：牧濑红莉栖桌宠伴侣 (同时保留模式 14 经典圆形变脸特效)
    display.SetMode(DisplayMode::KURISU_DESK_PET);

    ESP_LOGI(TAG, ">>> [中枢就绪]: 已就绪监听串口指令！可用命令示例：");
    ESP_LOGI(TAG, "    - 倒计时: 'countdown 60' 或 '{\"cmd\":\"countdown\",\"seconds\":60}'");
    ESP_LOGI(TAG, "    - 换灯效: 'fire', 'matrix', 'rainbow', 'aurora', 'mode 23' 等");
    ESP_LOGI(TAG, "    - 调亮度: 'brightness 25' 或 'b 30'");
    ESP_LOGI(TAG, "    - 查状态: 'status'");

    // 6. 主循环：进入极低功耗心跳监听 (不与渲染和串口争抢 CPU 资源)
    LogRuntimeBudget();
    uint32_t heartbeat_tick = 0;
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(5000));
        heartbeat_tick++;
        if(heartbeat_tick%6==0)LogRuntimeBudget();

        if (display.IsCountdownActive()) {
            ESP_LOGI(TAG, "[心跳 #%u]: 倒计时运行中，剩余 %u 秒",
                     (unsigned int)heartbeat_tick,
                     (unsigned int)display.GetCountdownRemainingSeconds());
        } else {
            ESP_LOGD(TAG, "[心跳 #%u]: 当前显示模式 %d", (unsigned int)heartbeat_tick, (int)display.GetMode());
        }
    }
}
