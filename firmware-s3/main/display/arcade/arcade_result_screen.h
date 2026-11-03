// arcade_result_screen.h —— 统一 16x16 街机结算与成绩展示层
#pragma once

#include "arcade_cartridge.h"
#include <stdint.h>

namespace arcade {

class ArcadeResultScreen {
public:
    static void RenderResult(uint8_t* fb_rgb24, bool is_victory, uint32_t score, uint32_t high_score, float anim_time);

    // 绘制 3x5 紧凑点阵数字 (0-9)
    static void DrawDigit3x5(uint8_t* fb_rgb24, int digit, int x, int y, uint8_t r, uint8_t g, uint8_t b);

    // 绘制数字串 (支持 1~4 位，自动居中)
    static void DrawScoreNumber(uint8_t* fb_rgb24, uint32_t score, int y, uint8_t r, uint8_t g, uint8_t b);

    // 绘制 3x5 紧凑大写英文字母 (G, O, W, I, N, S, C)
    static void DrawChar3x5(uint8_t* fb_rgb24, char ch, int x, int y, uint8_t r, uint8_t g, uint8_t b);
};

} // namespace arcade
