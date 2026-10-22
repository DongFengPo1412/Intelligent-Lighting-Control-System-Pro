// Temporary opt-in comparison: restore PRO_HAIR_CALIBRATION=OFF after use.
// Keep the complete character fixed and replace only the outer hair color.
#include "display_hal.h"
#include "kurisu_sprites.h"
#include <esp_log.h>
#include <esp_timer.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

static ColorRGB OriginalPwm(const ColorRGB& color) {
    return ColorRGB(color.r * 20 / 255, color.g * 20 / 255, color.b * 20 / 255);
}

// Experimental quarter-step output, only for the hair border. Four consecutive
// phases average to q / 4 exactly. Stagger pixels to avoid whole-border flashes.
static uint8_t QuarterPwm(uint8_t q, unsigned phase) {
    return q / 4 + ((phase & 3) < q % 4 ? 1 : 0);
}

static bool SameColor(const ColorRGB& a, const ColorRGB& b) {
    return a.r == b.r && a.g == b.g && a.b == b.b;
}

extern "C" void app_main(void) {
    auto& hal = DisplayHAL::GetInstance();
    ESP_ERROR_CHECK(hal.Init(GPIO_NUM_17));
    // Other parts are converted once using exactly the normal brightness-20
    // integer scaling. Show at 255 then leaves these physical PWM bytes intact.
    hal.SetGlobalBrightness(255);
    const ColorRGB candidates_quarters[] = {{6, 2, 0}, {4, 1, 0}, {4, 1, 1}};
    for (;;) {
        for (int profile = 0; profile < 3; ++profile) {
            const auto& q = candidates_quarters[profile];
            ESP_LOGI("HairCalibration", "Profile %d: experimental average PWM R=%.2f G=%.2f B=%.2f; 8 seconds",
                     profile + 1, q.r / 4.0, q.g / 4.0, q.b / 4.0);
            hal.Clear();
            for (int y = 0; y < 16; ++y) {
                for (int x = 0; x < 16; ++x) {
                    const auto& source = KURISU_FRAME_IDLE[y][x];
                    hal.SetPixel(x, y, OriginalPwm(source));
                }
            }
            // One/two/three dim red markers in the unused bottom-left background.
            for (int marker = 0; marker <= profile; ++marker) {
                hal.SetPixel(marker * 2, 15, ColorRGB(1, 0, 0));
            }
            unsigned frames = 0;
            const int64_t started = esp_timer_get_time();
            do {
                for (int y = 0; y < 16; ++y) {
                    for (int x = 0; x < 16; ++x) {
                        if (!SameColor(KURISU_FRAME_IDLE[y][x], KURISU_LED_HAIR_BORDER)) continue;
                        const unsigned phase = frames + x + 3 * y;
                        hal.SetPixel(x, y, ColorRGB(QuarterPwm(q.r, phase),
                                                  QuarterPwm(q.g, phase),
                                                  QuarterPwm(q.b, phase)));
                    }
                }
                ESP_ERROR_CHECK(hal.Show());
                ++frames;
                if (frames % 64 == 0) vTaskDelay(1);
            } while (esp_timer_get_time() - started < 8000000);
            ESP_LOGI("HairCalibration", "Profile %d refresh %.1f Hz; check for visible shimmer",
                     profile + 1, frames * 1000000.0 / (esp_timer_get_time() - started));
        }
    }
}
