#pragma once

#include <stdint.h>
#include <stdlib.h>
#include <math.h>
#include <esp_random.h>
#include <esp_timer.h>

#define MATRIX_WIDTH   16
#define MATRIX_HEIGHT  16
#define TOTAL_LEDS     (MATRIX_WIDTH * MATRIX_HEIGHT) // 256

// 预定义模式枚举 (对齐中阶模式定义)
enum class DisplayMode : int {
    OFF = 0,                    // 0: 清屏关灯
    SOLID_RED = 1,              // 1: 纯红模式
    SOLID_BLUE = 2,             // 2: 纯蓝模式
    SOLID_GREEN = 3,            // 3: 纯绿模式
    RAINBOW_WAVE = 4,           // 4: 幻彩霓虹
    AURORA_BREATHE = 5,         // 5: 呼吸极光
    METEOR_TRAIL = 6,           // 6: 流星划过
    TWINKLE_STARS = 7,          // 7: 繁星点点
    COLOR_CYCLE = 8,            // 8: 全屏色彩
    MATRIX_RAIN = 9,            // 9: 乱序雨滴
    CENTER_RIPPLE = 10,         // 10: 中心波纹
    FACE_SMILE = 11,            // 11: 笑脸盈盈
    FACE_CRY = 12,              // 12: 垂头丧气
    FACE_NEUTRAL = 13,          // 13: 面无表情
    FACE_DYNAMIC = 14,          // 14: 瞬息万变
    AUDIO_SPECTRUM = 15,        // 15: 音乐随动
    AI_FEEDBACK = 16,           // 16: AI 对话唤醒反馈
    SNAKE_GAME = 19,            // 19: 贪吃蛇游戏
    SNAKE_SCORE = 20,           // 20: 贪吃蛇结算看板
    TETRIS_GAME = 21,           // 21: 俄罗斯方块游戏
    TETRIS_SCORE = 22           // 22: 俄罗斯方块结算看板
};

struct ColorRGB {
    uint8_t r;
    uint8_t g;
    uint8_t b;

    constexpr ColorRGB() : r(0), g(0), b(0) {}
    constexpr ColorRGB(uint8_t red, uint8_t green, uint8_t blue) : r(red), g(green), b(blue) {}

    ColorRGB& operator+=(const ColorRGB& rhs) {
        r = (r + rhs.r > 255) ? 255 : (r + rhs.r);
        g = (g + rhs.g > 255) ? 255 : (g + rhs.g);
        b = (b + rhs.b > 255) ? 255 : (b + rhs.b);
        return *this;
    }

    ColorRGB scale(uint8_t scale_percent) const {
        return ColorRGB((r * scale_percent) / 100, (g * scale_percent) / 100, (b * scale_percent) / 100);
    }

    // 常用常量色
    static constexpr ColorRGB Black()   { return ColorRGB(0, 0, 0); }
    static constexpr ColorRGB White()   { return ColorRGB(255, 255, 255); }
    static constexpr ColorRGB Red()     { return ColorRGB(255, 0, 0); }
    static constexpr ColorRGB Green()   { return ColorRGB(0, 255, 0); }
    static constexpr ColorRGB Blue()    { return ColorRGB(0, 0, 255); }
    static constexpr ColorRGB Yellow()  { return ColorRGB(255, 255, 0); }
    static constexpr ColorRGB Cyan()    { return ColorRGB(0, 255, 255); }
    static constexpr ColorRGB Purple()  { return ColorRGB(180, 0, 255); }
    static constexpr ColorRGB Orange()  { return ColorRGB(255, 128, 0); }
    static constexpr ColorRGB Lime()    { return ColorRGB(50, 255, 0); }
    static constexpr ColorRGB Gray()    { return ColorRGB(128, 128, 128); }
};

struct ColorHSV {
    uint8_t h; // 0 ~ 255
    uint8_t s; // 0 ~ 255
    uint8_t v; // 0 ~ 255

    constexpr ColorHSV() : h(0), s(0), v(0) {}
    constexpr ColorHSV(uint8_t hue, uint8_t sat, uint8_t val) : h(hue), s(sat), v(val) {}
};

// 极速免浮点 HSV 转 RGB 算法 (复现 FastLED 彩虹色盘特性)
static inline ColorRGB hsv2rgb_fast(const ColorHSV& hsv)
{
    if (hsv.s == 0) {
        return ColorRGB(hsv.v, hsv.v, hsv.v);
    }

    uint8_t region = hsv.h / 43;
    uint8_t remainder = (hsv.h - (region * 43)) * 6;

    uint8_t p = (hsv.v * (255 - hsv.s)) >> 8;
    uint8_t q = (hsv.v * (255 - ((hsv.s * remainder) >> 8))) >> 8;
    uint8_t t = (hsv.v * (255 - ((hsv.s * (255 - remainder)) >> 8))) >> 8;

    switch (region) {
        case 0:  return ColorRGB(hsv.v, t, p);
        case 1:  return ColorRGB(q, hsv.v, p);
        case 2:  return ColorRGB(p, hsv.v, t);
        case 3:  return ColorRGB(p, q, hsv.v);
        case 4:  return ColorRGB(t, p, hsv.v);
        default: return ColorRGB(hsv.v, p, q);
    }
}

// 快速随机数 0 ~ 255
static inline uint8_t random8()
{
    return (uint8_t)(esp_random() & 0xFF);
}

static inline uint8_t random8(uint8_t max_val)
{
    if (max_val == 0) return 0;
    return (uint8_t)((esp_random() & 0xFFFF) % max_val);
}

static inline uint8_t random8(uint8_t min_val, uint8_t max_val)
{
    if (min_val >= max_val) return min_val;
    return min_val + random8(max_val - min_val);
}

// 获取毫秒时间戳
static inline uint32_t get_millis()
{
    return (uint32_t)(esp_timer_get_time() / 1000ULL);
}

// 模拟 FastLED beatsin8 函数：基于当前时间生成周期性正弦波数值 [low, high]
static inline uint8_t beatsin8(uint8_t beats_per_minute, uint8_t lowest = 0, uint8_t highest = 255)
{
    uint32_t ms = get_millis();
    // 周期以毫秒计：60000 / BPM
    float period_ms = 60000.0f / (beats_per_minute > 0 ? beats_per_minute : 1);
    float angle = (float)fmod(ms, period_ms) / period_ms * 2.0f * (float)M_PI;
    float sin_val = (sinf(angle) + 1.0f) * 0.5f; // 0.0 ~ 1.0
    return lowest + (uint8_t)(sin_val * (highest - lowest));
}

// 颜色按比例渐暗淡出 (fadeToBlackBy)
static inline void fade_to_black_by(ColorRGB* leds, uint32_t count, uint8_t fade_by)
{
    uint16_t keep = 255 - fade_by;
    for (uint32_t i = 0; i < count; i++) {
        leds[i].r = (leds[i].r * keep) >> 8;
        leds[i].g = (leds[i].g * keep) >> 8;
        leds[i].b = (leds[i].b * keep) >> 8;
    }
}
