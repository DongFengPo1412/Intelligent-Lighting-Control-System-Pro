// Temporary opt-in comparison: restore PRO_HAIR_CALIBRATION=OFF after use.
// Keep the complete character fixed and replace only the outer hair color.
#include "display_hal.h"
#include "kurisu_sprites.h"
#include <esp_log.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

static ColorRGB DriveColor(uint8_t r, uint8_t g, uint8_t b) {
    return ColorRGB((r * 255 + 19) / 20, (g * 255 + 19) / 20, (b * 255 + 19) / 20);
}

static bool SameColor(const ColorRGB& a, const ColorRGB& b) {
    return a.r == b.r && a.g == b.g && a.b == b.b;
}

extern "C" void app_main(void) {
    auto& hal = DisplayHAL::GetInstance();
    ESP_ERROR_CHECK(hal.Init(GPIO_NUM_17));
    hal.SetGlobalBrightness(20);
    const ColorRGB candidates[] = {DriveColor(3, 1, 0), DriveColor(5, 1, 0), DriveColor(7, 1, 0)};
    for (;;) {
        for (int profile = 0; profile < 3; ++profile) {
            ESP_LOGI("HairCalibration", "Profile %d: brown-border reference R=%d G=1 B=0; 8 seconds", profile + 1, 3 + profile * 2);
            hal.Clear();
            for (int y = 0; y < 16; ++y) {
                for (int x = 0; x < 16; ++x) {
                    const auto& source = KURISU_FRAME_IDLE[y][x];
                    hal.SetPixel(x, y, SameColor(source, KURISU_LED_HAIR_BORDER) ? candidates[profile] : source);
                }
            }
            // One/two/three dim red markers in the unused bottom-left background.
            for (int marker = 0; marker <= profile; ++marker) {
                hal.SetPixel(marker * 2, 15, DriveColor(1, 0, 0));
            }
            ESP_ERROR_CHECK(hal.Show());
            vTaskDelay(pdMS_TO_TICKS(8000));
        }
    }
}
