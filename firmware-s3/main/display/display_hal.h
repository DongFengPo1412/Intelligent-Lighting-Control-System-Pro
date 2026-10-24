#pragma once

#include "display_types.h"
#include "led_strip.h"
#include <esp_err.h>

class DisplayHAL {
public:
    static DisplayHAL& GetInstance();

    // 初始化硬件 RMT 驱动
    esp_err_t Init(gpio_num_t gpio_pin = GPIO_NUM_17);

    // 显存操作
    void Clear();
    void SetPixel(int x, int y, const ColorRGB& color);
    void SetPixelByIndex(int index, const ColorRGB& color);
    ColorRGB GetPixel(int x, int y) const;
    void FillSolid(const ColorRGB& color);
    void FadeToBlackBy(uint8_t fade_by);
    void DrawDigit(int n, int x, int y, const ColorRGB& color);

    // 整板统一亮度控制
    void SetGlobalBrightness(uint8_t brightness);
    uint8_t GetGlobalBrightness() const { return base_brightness_; }

    // 将显存数据推送到物理矩阵屏
    // sRGB conversion is opt-in for image content; existing effects keep raw RGB.
    esp_err_t Show(uint8_t brightness_percent = 100, bool srgb_image = false);

    // 左上角为原点；当前实物每行同向，蛇形板可通过编译选项选择。
    static constexpr int GetPixelIndex(int x, int y) {
        return MatrixLayout::PixelIndex(x, y);
    }

    ColorRGB* GetBuffer() { return buffer_; }
    // Completed front frame, in actual PWM bytes. Call under DisplayManager lock.
    const ColorRGB* GetFrontBuffer() const { return front_buffer_; }
    uint32_t GetFrameId() const { return frame_id_; }
    void SetGammaEnabled(bool enabled) { gamma_enabled_ = enabled; }

private:
    DisplayHAL();
    ~DisplayHAL();

    DisplayHAL(const DisplayHAL&) = delete;
    DisplayHAL& operator=(const DisplayHAL&) = delete;

    led_strip_handle_t led_strip_;
    ColorRGB buffer_[TOTAL_LEDS];
    ColorRGB front_buffer_[TOTAL_LEDS] = {};
    uint32_t frame_id_ = 0;
    bool gamma_enabled_ = false;
    uint8_t base_brightness_;
    bool is_initialized_;
};
