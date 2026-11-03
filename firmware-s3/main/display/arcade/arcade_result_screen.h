// arcade_result_screen.h — 统一 16x16 街机结算与高分展示屏
#pragma once

#include "arcade_cartridge.h"
#include <stdint.h>

namespace arcade {

class ArcadeResultScreen {
public:
    // 渲染结算界面 (自动分页展示当前得分与历史高分，支持 >4 位大数字平滑滚动，不发生截断)
    static void RenderResult(uint8_t* fb_rgb24, bool is_victory, uint32_t score, uint32_t high_score, float anim_time);

    // 绘制 3x5 微型数字 (0-9)
    static void DrawDigit3x5(uint8_t* fb_rgb24, int digit, int x, int y, uint8_t r, uint8_t g, uint8_t b);

    // 绘制分数字符串 (支持 1~4 位居中显示与 >4 位大数字跑马灯平滑滚动)
    static void DrawScoreNumber(uint8_t* fb_rgb24, uint32_t score, int y, uint8_t r, uint8_t g, uint8_t b, float anim_time);

    // 绘制 3x5 大写英文字母 (G, O, W, I, N, S, C, A, H, E)
    static void DrawChar3x5(uint8_t* fb_rgb24, char ch, int x, int y, uint8_t r, uint8_t g, uint8_t b);
};

} // namespace arcade
