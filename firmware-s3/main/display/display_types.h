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
    TETRIS_SCORE = 22,          // 22: 俄罗斯方块结算看板
    CYBER_FIRE = 23,            // 23: 赛博壁炉物理火焰
    MATRIX_RAIN_PRO = 24,       // 24: 黑客帝国代码雨 Pro
    COUNTDOWN_TIMER = 25        // 25: 智能高精度倒计时
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

    // 线性色彩混合插值 (t: 0.0f ~ 1.0f)
    static ColorRGB Lerp(const ColorRGB& c1, const ColorRGB& c2, float t) {
        if (t <= 0.0f) return c1;
        if (t >= 1.0f) return c2;
        uint8_t nr = (uint8_t)(c1.r + (c2.r - c1.r) * t);
        uint8_t ng = (uint8_t)(c1.g + (c2.g - c1.g) * t);
        uint8_t nb = (uint8_t)(c1.b + (c2.b - c1.b) * t);
        return ColorRGB(nr, ng, nb);
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

// 预计算的 Gamma 2.2 伽马色彩拟合查找表 (防止暗部截断为0，极度细腻温润)
static const uint8_t GAMMA_TABLE_22[256] = {
    0,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,
    1,   1,   1,   1,   1,   1,   1,   1,   1,   2,   2,   2,   2,   2,   2,   2,
    3,   3,   3,   3,   3,   4,   4,   4,   4,   5,   5,   5,   5,   6,   6,   6,
    6,   7,   7,   7,   8,   8,   8,   9,   9,   9,  10,  10,  11,  11,  11,  12,
   12,  13,  13,  13,  14,  14,  15,  15,  16,  16,  17,  17,  18,  18,  19,  19,
   20,  20,  21,  22,  22,  23,  23,  24,  25,  25,  26,  26,  27,  28,  28,  29,
   30,  30,  31,  32,  33,  33,  34,  35,  35,  36,  37,  38,  39,  39,  40,  41,
   42,  43,  43,  44,  45,  46,  47,  48,  49,  49,  50,  51,  52,  53,  54,  55,
   56,  57,  58,  59,  60,  61,  62,  63,  64,  65,  66,  67,  68,  69,  70,  71,
   73,  74,  75,  76,  77,  78,  79,  81,  82,  83,  84,  85,  87,  88,  89,  90,
   91,  93,  94,  95,  97,  98,  99, 100, 102, 103, 105, 106, 107, 109, 110, 111,
  113, 114, 116, 117, 119, 120, 121, 123, 124, 126, 127, 129, 130, 132, 133, 135,
  137, 138, 140, 141, 143, 145, 146, 148, 149, 151, 153, 154, 156, 158, 159, 161,
  163, 165, 166, 168, 170, 172, 173, 175, 177, 179, 181, 182, 184, 186, 188, 190,
  192, 194, 196, 197, 199, 201, 203, 205, 207, 209, 211, 213, 215, 217, 219, 221,
  223, 225, 227, 229, 231, 234, 236, 238, 240, 242, 244, 246, 248, 251, 253, 255
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
