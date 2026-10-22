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
    esp_err_t Show();

    // 左上角为原点，16x16 整板逐行蛇形走线。
    static constexpr int GetPixelIndex(int x, int y) {
        return MatrixLayout::PixelIndex(x, y);
    }

    ColorRGB* GetBuffer() { return buffer_; }

private:
    DisplayHAL();
    ~DisplayHAL();

    DisplayHAL(const DisplayHAL&) = delete;
    DisplayHAL& operator=(const DisplayHAL&) = delete;

    led_strip_handle_t led_strip_;
    ColorRGB buffer_[TOTAL_LEDS];
    uint8_t base_brightness_;
    bool is_initialized_;
};
