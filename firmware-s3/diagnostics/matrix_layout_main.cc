// Opt-in wiring test, built with -DPRO_MATRIX_DIAGNOSTIC=ON.
// Uses the production HAL; never starts Wi-Fi, the microphone or the speaker.
#include "display_hal.h"
#include <esp_log.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

static void ShowFor(DisplayHAL& hal, uint32_t milliseconds) {
    ESP_ERROR_CHECK(hal.Show());
    vTaskDelay(pdMS_TO_TICKS(milliseconds));
}

extern "C" void app_main(void) {
    auto& hal = DisplayHAL::GetInstance();
    ESP_ERROR_CHECK(hal.Init(GPIO_NUM_17));
    hal.SetGlobalBrightness(20);  // 20/255, sparse patterns only.

    for (;;) {
        ESP_LOGI("MatrixTest", "CORNERS: top-left RED, top-right GREEN, bottom-left BLUE, bottom-right YELLOW");
        hal.Clear();
        for (int dy = 0; dy < 2; ++dy) {
            for (int dx = 0; dx < 2; ++dx) {
                hal.SetPixel(dx, dy, ColorRGB::Red());
                hal.SetPixel(14 + dx, dy, ColorRGB::Green());
                hal.SetPixel(dx, 14 + dy, ColorRGB::Blue());
                hal.SetPixel(14 + dx, 14 + dy, ColorRGB::Yellow());
            }
        }
        ShowFor(hal, 5000);

        ESP_LOGI("MatrixTest", "ROWS: white dot moves left-to-right in EVERY row, rows top-to-bottom");
        for (int y = 0; y < 16; ++y) {
            for (int x = 0; x < 16; ++x) {
                hal.Clear();
                hal.SetPixel(x, y, ColorRGB::White());
                ShowFor(hal, 25);
            }
        }

        ESP_LOGI("MatrixTest", "BARS: cyan staircase, height increases from LEFT to RIGHT, grows from BOTTOM");
        hal.Clear();
        for (int x = 0; x < 16; ++x) {
            for (int height = 0; height <= x; ++height) {
                hal.SetPixel(x, 15 - height, ColorRGB::Cyan());
            }
        }
        ShowFor(hal, 7000);
    }
}
