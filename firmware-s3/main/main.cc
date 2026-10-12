#include <stdio.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <esp_log.h>
#include "display_manager.h"
#include "command_dispatcher.h"

static const char* TAG = "MainApp";

extern "C" void app_main(void)
{
    ESP_LOGI(TAG, "===============================================================");
    ESP_LOGI(TAG, ">>> [智光魔方 Pro]: ESP32-S3 单板高阶多模态中枢正式启动");
    ESP_LOGI(TAG, ">>> [双核架构]: Core 1 (60FPS 光影物理渲染) | Core 0 (实时指令与通信中枢)");
    ESP_LOGI(TAG, ">>> [硬件外设]: GPIO 17 硬件 RMT 直驱 16x16 矩阵屏 (FastLED 线性色阶)");
    ESP_LOGI(TAG, ">>> [协议支持]: 纯文本极速短语 (countdown/mode/...) + 工业级 cJSON + 频谱流");
    ESP_LOGI(TAG, "===============================================================");

    // 1. 初始化显示引擎 (挂载至 GPIO 17)
    DisplayManager& display = DisplayManager::GetInstance();
    ESP_ERROR_CHECK(display.Init(GPIO_NUM_17));

    // 2. 开启 4 块板硬件压降梯级均光校准 (FastLED 纯线性色阶通透管线)
    display.SetCompensation(true);
    display.SetBrightness(20);

    // 3. 启动后台独立物理渲染引擎 (运行在 Core 1，优先级 5)
    ESP_ERROR_CHECK(display.StartTask(5, 1));

    // 4. 启动后台串口指令调度中枢 (运行在 Core 0，优先级 4，负责 USB 极速解析)
    CommandDispatcher& dispatcher = CommandDispatcher::GetInstance();
    ESP_ERROR_CHECK(dispatcher.StartSerialTask(4, 0));

    // 5. 初始默认展示：灵动微表情桌面伴侣 (具备自然生理眨眼与眼神注视)
    display.SetMode(DisplayMode::FACE_SMILE);

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
