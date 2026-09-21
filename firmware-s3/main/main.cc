#include <stdio.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <esp_log.h>
#include "display_manager.h"

static const char* TAG = "MainApp";

extern "C" void app_main(void)
{
    ESP_LOGI(TAG, "===============================================================");
    ESP_LOGI(TAG, ">>> [智光魔方 Pro]: ESP32-S3 单板高阶灯效系统正式启动");
    ESP_LOGI(TAG, ">>> [硬件引脚]: GPIO 17 硬件 RMT 直驱 16x16 矩阵屏 (3V3 + 均光校准)");
    ESP_LOGI(TAG, ">>> [架构模式]: C++ 面向对象封装 + FreeRTOS 独立多核渲染引擎");
    ESP_LOGI(TAG, "===============================================================");

    // 1. 初始化显示引擎 (挂载至 GPIO 17)
    DisplayManager& display = DisplayManager::GetInstance();
    ESP_ERROR_CHECK(display.Init(GPIO_NUM_17));

    // 2. 开启 4 块板硬件压降梯级均光校准 (FastLED 线性色阶通透管线)
    display.SetCompensation(true);
    display.SetBrightness(20);

    // 3. 启动后台独立渲染任务 (运行在 Core 1，优先级 5)
    ESP_ERROR_CHECK(display.StartTask(5, 1));

    ESP_LOGI(TAG, ">>> [系统就绪]: 进入高阶灯效审美重构与倒计时系统自动巡检演示循环...");

    int demo_cycle = 0;
    while (1) {
        ESP_LOGI(TAG, "\n========== 演示轮次 %d ==========", ++demo_cycle);

        // 1. 真 2D 对角对流彩虹 (模式 4)
        ESP_LOGI(TAG, ">>> [演示 1/9]: 模式 4 - 真 2D 对角对流彩虹 (True 2D Rainbow Field，零接缝断层)");
        display.SetMode(DisplayMode::RAINBOW_WAVE);
        vTaskDelay(pdMS_TO_TICKS(3500));

        // 2. 复合流光极光 (模式 5)
        ESP_LOGI(TAG, ">>> [演示 2/9]: 模式 5 - 复合流光极光 (Aurora Symphony，双波长正弦干涉场)");
        display.SetMode(DisplayMode::AURORA_BREATHE);
        vTaskDelay(pdMS_TO_TICKS(3500));

        // 3. 赛博壁炉物理火焰 (模式 23)
        ESP_LOGI(TAG, ">>> [演示 3/9]: 模式 23 - 赛博物理火焰模拟 (Perlin Cyber Flame，热量对流与黑体辐射)");
        display.SetMode(DisplayMode::CYBER_FIRE);
        vTaskDelay(pdMS_TO_TICKS(4000));

        // 4. 黑客帝国代码雨 Pro (模式 24)
        ESP_LOGI(TAG, ">>> [演示 4/9]: 模式 24 - 黑客帝国代码雨 Pro (Matrix Code Rain 2.0，16列独立长尾流)");
        display.SetMode(DisplayMode::MATRIX_RAIN_PRO);
        vTaskDelay(pdMS_TO_TICKS(4000));

        // 5. 抗锯齿中心波纹 (模式 10)
        ESP_LOGI(TAG, ">>> [演示 5/9]: 模式 10 - 抗锯齿双同心波纹 (Center Ripple)");
        display.SetMode(DisplayMode::CENTER_RIPPLE);
        vTaskDelay(pdMS_TO_TICKS(3500));

        // 6. AI 灵动微表情系统 (模式 11, 12, 13, 14: 自然生理眨眼 + 眼神游移)
        ESP_LOGI(TAG, ">>> [演示 6/9]: AI 灵动微表情系统 (生理眨眼 + 眼神张望 + 情绪呼吸)");
        display.SetMode(DisplayMode::FACE_SMILE);
        vTaskDelay(pdMS_TO_TICKS(2500));
        display.SetMode(DisplayMode::FACE_CRY);
        vTaskDelay(pdMS_TO_TICKS(2500));
        display.SetMode(DisplayMode::FACE_NEUTRAL);
        vTaskDelay(pdMS_TO_TICKS(2500));
        display.SetMode(DisplayMode::FACE_DYNAMIC);
        vTaskDelay(pdMS_TO_TICKS(2500));

        // 7. 经典游戏复刻 (俄罗斯方块与贪吃蛇)
        ESP_LOGI(TAG, ">>> [演示 7/9]: 经典游戏矩阵 - 俄罗斯方块 & 贪吃蛇");
        display.SetMode(DisplayMode::TETRIS_GAME);
        for (int step = 0; step < 6; step++) {
            vTaskDelay(pdMS_TO_TICKS(400));
            if (step % 2 == 0) display.TetrisMove(-1);
            else display.TetrisRotate();
        }
        display.SetMode(DisplayMode::SNAKE_GAME);
        for (int step = 0; step < 6; step++) {
            vTaskDelay(pdMS_TO_TICKS(350));
            if (step == 2) display.SnakeMove(0, 1);
            else if (step == 4) display.SnakeMove(-1, 0);
        }

        // 8. 专业调音台级音律随动 (模式 15: 峰值悬停顶针 + 重力自由落体)
        ESP_LOGI(TAG, ">>> [演示 8/9]: 模式 15 - 专业音律随动 (带 Peak-Hold 峰值悬停顶针与重力跌落)");
        display.SetMode(DisplayMode::AUDIO_SPECTRUM);
        for (int frame = 0; frame < 70; frame++) {
            int simulated_bands[16];
            int beat = (frame % 16 == 0) ? 1 : 0;
            for (int b = 0; b < 16; b++) {
                int val = (int)(fabsf(sinf(frame * 0.22f + b * 0.45f)) * 14.0f) + random8(3);
                simulated_bands[b] = (val > 15) ? 15 : val;
            }
            display.FeedSpectrum(beat, simulated_bands);
            vTaskDelay(pdMS_TO_TICKS(50));
        }

        // 9. 智能倒计时系统 (模式 25: 精确等比逐颗熄灭，动态情感色彩流变)
        ESP_LOGI(TAG, ">>> [演示 9/9]: 模式 25 - 智能高精度倒计时 (演示 8 秒倒计时，256 灯珠逐颗渐次熄灭)");
        display.StartCountdown(8); // 演示 8 秒倒计时
        while (display.IsCountdownActive()) {
            uint32_t rem = display.GetCountdownRemainingSeconds();
            ESP_LOGI(TAG, "    [倒计时中]: 剩余 %u 秒...", (unsigned int)rem);
            vTaskDelay(pdMS_TO_TICKS(1000));
        }
        vTaskDelay(pdMS_TO_TICKS(1500)); // 留白呼吸感
    }
}
