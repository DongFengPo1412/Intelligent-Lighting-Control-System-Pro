#include "display_hal.h"
#include "font_5x3.h"
#include <esp_log.h>
#include <string.h>

static const char* TAG = "DisplayHAL";

DisplayHAL& DisplayHAL::GetInstance()
{
    static DisplayHAL instance;
    return instance;
}

DisplayHAL::DisplayHAL()
    : led_strip_(nullptr),
      base_brightness_(20),
      enable_compensation_(true),
      is_initialized_(false)
{
    memset(buffer_, 0, sizeof(buffer_));
}

DisplayHAL::~DisplayHAL()
{
    if (led_strip_) {
        led_strip_del(led_strip_);
        led_strip_ = nullptr;
    }
}

esp_err_t DisplayHAL::Init(gpio_num_t gpio_pin)
{
    if (is_initialized_) return ESP_OK;

    ESP_LOGI(TAG, "Initializing RMT WS2812 driver on GPIO %d...", gpio_pin);

    led_strip_config_t strip_config = {
        .strip_gpio_num = gpio_pin,
        .max_leds = TOTAL_LEDS,
        .led_model = LED_MODEL_WS2812,
        .color_component_format = LED_STRIP_COLOR_COMPONENT_FMT_GRB,
        .flags = {
            .invert_out = false,
        }
    };

    led_strip_rmt_config_t rmt_config = {
        .clk_src = RMT_CLK_SRC_DEFAULT,
        .resolution_hz = 10 * 1000 * 1000, // 10MHz
        .flags = {
            .with_dma = false,
        }
    };

    esp_err_t ret = led_strip_new_rmt_device(&strip_config, &rmt_config, &led_strip_);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to create led_strip RMT device: %s", esp_err_to_name(ret));
        return ret;
    }

    Clear();
    Show();
    is_initialized_ = true;
    ESP_LOGI(TAG, "Display HAL initialized successfully.");
    return ESP_OK;
}

void DisplayHAL::Clear()
{
    memset(buffer_, 0, sizeof(buffer_));
}

void DisplayHAL::SetPixel(int x, int y, const ColorRGB& color)
{
    int idx = GetPixelIndex(x, y);
    if (idx >= 0 && idx < TOTAL_LEDS) {
        buffer_[idx] = color;
    }
}

void DisplayHAL::SetPixelByIndex(int index, const ColorRGB& color)
{
    if (index >= 0 && index < TOTAL_LEDS) {
        buffer_[index] = color;
    }
}

ColorRGB DisplayHAL::GetPixel(int x, int y) const
{
    int idx = GetPixelIndex(x, y);
    if (idx >= 0 && idx < TOTAL_LEDS) {
        return buffer_[idx];
    }
    return ColorRGB::Black();
}

void DisplayHAL::FillSolid(const ColorRGB& color)
{
    for (int i = 0; i < TOTAL_LEDS; i++) {
        buffer_[i] = color;
    }
}

void DisplayHAL::FadeToBlackBy(uint8_t fade_by)
{
    fade_to_black_by(buffer_, TOTAL_LEDS, fade_by);
}

void DisplayHAL::DrawDigit(int n, int x, int y, const ColorRGB& color)
{
    if (n < 0 || n > 9) return;
    for (int i = 0; i < 5; i++) {
        uint8_t row = numFont5x3[n][i];
        for (int j = 0; j < 3; j++) {
            if (row & (0x4 >> j)) {
                SetPixel(x + j, y + i, color);
            }
        }
    }
}

void DisplayHAL::SetGlobalBrightness(uint8_t brightness)
{
    base_brightness_ = brightness;
}

esp_err_t DisplayHAL::Show()
{
    if (!led_strip_) return ESP_ERR_INVALID_STATE;

    for (int i = 0; i < TOTAL_LEDS; i++) {
        // 1. 全局亮度缩放 (0 ~ 255)
        uint16_t r = (buffer_[i].r * base_brightness_) / 255;
        uint16_t g = (buffer_[i].g * base_brightness_) / 255;
        uint16_t b = (buffer_[i].b * base_brightness_) / 255;

        // 2. 4 块 8x8 级联板非线性压降梯级补偿
        if (enable_compensation_) {
            uint32_t panel = i / 64;
            uint32_t scale_percent;
            switch (panel) {
                case 0: scale_percent = 45;  break; // 第 1 块板
                case 1: scale_percent = 62;  break; // 第 2 块板
                case 2: scale_percent = 80;  break; // 第 3 块板
                default: scale_percent = 100; break; // 第 4 块板
            }
            r = (r * scale_percent) / 100;
            g = (g * scale_percent) / 100;
            b = (b * scale_percent) / 100;
        }

        led_strip_set_pixel(led_strip_, i, (uint32_t)r, (uint32_t)g, (uint32_t)b);
    }

    return led_strip_refresh(led_strip_);
}
