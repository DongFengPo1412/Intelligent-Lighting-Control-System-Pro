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

    // 2. 开启 4 块板硬件压降梯级均光校准 (彻底解决 3V3 下前亮后暗)
    display.SetCompensation(true);
    display.SetBrightness(20);

    // 3. 启动后台独立渲染任务 (运行在 Core 1，优先级 5)
    ESP_ERROR_CHECK(display.StartTask(5, 1));

    ESP_LOGI(TAG, ">>> [系统就绪]: 进入高阶模式自动巡检演示循环...");

    int demo_cycle = 0;
    while (1) {
        ESP_LOGI(TAG, "\n========== 演示轮次 %d ==========", ++demo_cycle);

        // 1. 幻彩霓虹 (模式 4)
        ESP_LOGI(TAG, ">>> [演示 1/8]: 模式 4 - 幻彩霓虹 (Rainbow Wave)");
        display.SetMode(DisplayMode::RAINBOW_WAVE);
        vTaskDelay(pdMS_TO_TICKS(3000));

        // 2. 呼吸极光 (模式 5)
        ESP_LOGI(TAG, ">>> [演示 2/8]: 模式 5 - 呼吸极光 (Aurora Breathe)");
        display.SetMode(DisplayMode::AURORA_BREATHE);
        vTaskDelay(pdMS_TO_TICKS(3000));

        // 3. 流星划过 (模式 6)
        ESP_LOGI(TAG, ">>> [演示 3/8]: 模式 6 - 流星划过 (Meteor Trail)");
        display.SetMode(DisplayMode::METEOR_TRAIL);
        vTaskDelay(pdMS_TO_TICKS(3000));

        // 4. 中心波纹 (模式 10)
        ESP_LOGI(TAG, ">>> [演示 4/8]: 模式 10 - 中心波纹 (Center Ripple)");
        display.SetMode(DisplayMode::CENTER_RIPPLE);
        vTaskDelay(pdMS_TO_TICKS(3000));

        // 5. 经典表情包全家桶 (模式 11, 12, 13, 14)
        ESP_LOGI(TAG, ">>> [演示 5/8]: 表情包矩阵 - 笑脸 -> 哭脸 -> 平静 -> 动态变换");
        display.SetMode(DisplayMode::FACE_SMILE);
        vTaskDelay(pdMS_TO_TICKS(1500));
        display.SetMode(DisplayMode::FACE_CRY);
        vTaskDelay(pdMS_TO_TICKS(1500));
        display.SetMode(DisplayMode::FACE_NEUTRAL);
        vTaskDelay(pdMS_TO_TICKS(1500));
        display.SetMode(DisplayMode::FACE_DYNAMIC);
        vTaskDelay(pdMS_TO_TICKS(2500));

        // 6. 俄罗斯方块游戏演示 (模式 21)
        ESP_LOGI(TAG, ">>> [演示 6/8]: 模式 21 - 俄罗斯方块经典游戏");
        display.SetMode(DisplayMode::TETRIS_GAME);
        for (int step = 0; step < 8; step++) {
            vTaskDelay(pdMS_TO_TICKS(500));
            if (step % 3 == 0) display.TetrisMove(-1);
            else if (step % 3 == 1) display.TetrisRotate();
            else display.TetrisMove(1);
        }

        // 7. 贪吃蛇游戏演示 (模式 19)
        ESP_LOGI(TAG, ">>> [演示 7/8]: 模式 19 - 贪吃蛇经典游戏");
        display.SetMode(DisplayMode::SNAKE_GAME);
        for (int step = 0; step < 8; step++) {
            vTaskDelay(pdMS_TO_TICKS(400));
            if (step == 2) display.SnakeMove(0, 1);
            else if (step == 4) display.SnakeMove(-1, 0);
            else if (step == 6) display.SnakeMove(0, -1);
        }

        // 8. 音律随动模拟测试 (模式 15)
        ESP_LOGI(TAG, ">>> [演示 8/8]: 模式 15 - 16频段重力音律随动引擎 (重力跌落+鼓点叠加)");
        display.SetMode(DisplayMode::AUDIO_SPECTRUM);
        for (int frame = 0; frame < 80; frame++) {
            int simulated_bands[16];
            int beat = (frame % 16 == 0) ? 1 : 0;
            for (int b = 0; b < 16; b++) {
                // 模拟多频段声浪起伏
                int val = (int)(fabsf(sinf(frame * 0.2f + b * 0.4f)) * 14.0f) + random8(3);
                simulated_bands[b] = (val > 15) ? 15 : val;
            }
            display.FeedSpectrum(beat, simulated_bands);
            vTaskDelay(pdMS_TO_TICKS(50));
        }
    }
}
