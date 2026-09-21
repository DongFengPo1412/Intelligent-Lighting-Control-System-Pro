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

    // 亮度与均光控制
    void SetGlobalBrightness(uint8_t brightness);
    uint8_t GetGlobalBrightness() const { return base_brightness_; }
    void SetCompensationEnabled(bool enable) { enable_compensation_ = enable; }
    bool IsCompensationEnabled() const { return enable_compensation_; }

    // 将显存数据推送到物理矩阵屏
    esp_err_t Show();

    // 坐标索引换算
    static inline int GetPixelIndex(int x, int y) {
        if (x < 0 || x >= MATRIX_WIDTH || y < 0 || y >= MATRIX_HEIGHT) return -1;
        int blockID = (y / 8) * 2 + (x / 8); 
        return blockID * 64 + (y % 8) * 8 + (x % 8);
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
    bool enable_compensation_;
    bool is_initialized_;
};
