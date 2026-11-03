// arcade_result_screen.cpp — 统一 16x16 街机结算与高分展示屏
#include "arcade_result_screen.h"
#include <string.h>
#include <stdio.h>
#include <math.h>

namespace arcade {

// 3x5 点阵字模 (每个数字 3 bit，占 5 行)
static const uint8_t kFontDigits3x5[10][5] = {
    {0b111, 0b101, 0b101, 0b101, 0b111}, // 0
    {0b010, 0b110, 0b010, 0b010, 0b111}, // 1
    {0b111, 0b001, 0b111, 0b100, 0b111}, // 2
    {0b111, 0b001, 0b111, 0b001, 0b111}, // 3
    {0b101, 0b101, 0b111, 0b001, 0b001}, // 4
    {0b111, 0b100, 0b111, 0b001, 0b111}, // 5
    {0b111, 0b100, 0b111, 0b101, 0b111}, // 6
    {0b111, 0b001, 0b010, 0b010, 0b010}, // 7
    {0b111, 0b101, 0b111, 0b101, 0b111}, // 8
    {0b111, 0b101, 0b111, 0b001, 0b111}, // 9
};

static void SetPixelDirect(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b)
{
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

void ArcadeResultScreen::DrawDigit3x5(uint8_t* fb, int digit, int x, int y, uint8_t r, uint8_t g, uint8_t b)
{
    if (digit < 0 || digit > 9) return;
    for (int row = 0; row < 5; ++row) {
        uint8_t bits = kFontDigits3x5[digit][row];
        for (int col = 0; col < 3; ++col) {
            if (bits & (0b100 >> col)) {
                SetPixelDirect(fb, x + col, y + row, r, g, b);
            }
        }
    }
}

void ArcadeResultScreen::DrawChar3x5(uint8_t* fb, char ch, int x, int y, uint8_t r, uint8_t g, uint8_t b)
{
    static const uint8_t kChar_G[5] = {0b111, 0b100, 0b101, 0b101, 0b111};
    static const uint8_t kChar_O[5] = {0b111, 0b101, 0b101, 0b101, 0b111};
    static const uint8_t kChar_W[5] = {0b101, 0b101, 0b101, 0b111, 0b101};
    static const uint8_t kChar_I[5] = {0b111, 0b010, 0b010, 0b010, 0b111};
    static const uint8_t kChar_N[5] = {0b101, 0b111, 0b111, 0b101, 0b101};
    static const uint8_t kChar_S[5] = {0b111, 0b100, 0b111, 0b001, 0b111};
    static const uint8_t kChar_C[5] = {0b111, 0b100, 0b100, 0b100, 0b111};
    static const uint8_t kChar_A[5] = {0b010, 0b101, 0b111, 0b101, 0b101};
    static const uint8_t kChar_H[5] = {0b101, 0b101, 0b111, 0b101, 0b101};
    static const uint8_t kChar_E[5] = {0b111, 0b100, 0b111, 0b100, 0b111};

    const uint8_t* pattern = nullptr;
    switch (ch) {
        case 'G': pattern = kChar_G; break;
        case 'O': pattern = kChar_O; break;
        case 'W': pattern = kChar_W; break;
        case 'I': pattern = kChar_I; break;
        case 'N': pattern = kChar_N; break;
        case 'S': pattern = kChar_S; break;
        case 'C': pattern = kChar_C; break;
        case 'A': pattern = kChar_A; break;
        case 'H': pattern = kChar_H; break;
        case 'E': pattern = kChar_E; break;
        default: return;
    }

    for (int row = 0; row < 5; ++row) {
        uint8_t bits = pattern[row];
        for (int col = 0; col < 3; ++col) {
            if (bits & (0b100 >> col)) {
                SetPixelDirect(fb, x + col, y + row, r, g, b);
            }
        }
    }
}

void ArcadeResultScreen::DrawScoreNumber(uint8_t* fb, uint32_t score, int y, uint8_t r, uint8_t g, uint8_t b, float anim_time)
{
    char buf[12];
    int len = snprintf(buf, sizeof(buf), "%u", (unsigned int)score);
    if (len <= 0) return;

    if (len <= 4) {
        // 1~4 位数字直接居中展示 (每个数字宽 3，间隙 1)
        int total_w = len * 3 + (len - 1);
        int start_x = (16 - total_w) / 2;
        for (int i = 0; i < len; ++i) {
            DrawDigit3x5(fb, buf[i] - '0', start_x + i * 4, y, r, g, b);
        }
    } else {
        // >4 位数字 (如 12500、100000) 采用跑马灯平滑滚动，绝不发生截断
        int total_w = len * 4 - 1;
        int scroll_range = total_w - 15;
        float cycle = 2.5f;
        float t = fmodf(anim_time, cycle);
        int offset = 0;
        if (t < 0.6f) {
            offset = 0; // 停留在最高有效位
        } else if (t < 1.9f) {
            float frac = (t - 0.6f) / 1.3f;
            offset = (int)(frac * (scroll_range + 1));
            if (offset > scroll_range) offset = scroll_range;
        } else {
            offset = scroll_range; // 停留在末位数字
        }
        int start_x = -offset;
        for (int i = 0; i < len; ++i) {
            DrawDigit3x5(fb, buf[i] - '0', start_x + i * 4, y, r, g, b);
        }
    }
}

void ArcadeResultScreen::RenderResult(uint8_t* fb, bool is_victory, uint32_t score, uint32_t high_score, float anim_time)
{
    memset(fb, 0, kFrameBufferSize);

    // 自动分页轮播：每 2.2 秒在【当前本局得分】与【历史最高分】之间平滑交替
    int phase = ((int)(anim_time / 2.2f)) % 2;

    if (phase == 0) {
        // Phase 0: 本局结果与当前得分
        // 1. 顶部标题 (Row 1-5)
        if (is_victory) {
            // 胜利 "WIN" 纯金黄 (W at x=2, I at x=6, N at x=10)
            DrawChar3x5(fb, 'W', 2, 1, 255, 215, 0);
            DrawChar3x5(fb, 'I', 6, 1, 255, 215, 0);
            DrawChar3x5(fb, 'N', 10, 1, 255, 215, 0);
        } else {
            // 失败 "G O" 亮鲜红 (G at x=4, O at x=9)
            DrawChar3x5(fb, 'G', 4, 1, 255, 30, 30);
            DrawChar3x5(fb, 'O', 9, 1, 255, 30, 30);
        }

        // 2. 当前得分展示 (Row 7-11)
        DrawScoreNumber(fb, score, 7, 255, 190, 20, anim_time);
    } else {
        // Phase 1: 历史纪录与最高分 (High Score)
        // 1. 顶部标头 "HI" (H at x=4, I at x=9)
        bool is_new_record = (score >= high_score && score > 0);
        if (is_new_record) {
            // 新纪录闪烁金色
            float flash = (sinf(anim_time * 6.28f * 3.0f) + 1.0f) * 0.5f;
            uint8_t g_val = (uint8_t)(flash * 100.0f + 155.0f);
            DrawChar3x5(fb, 'H', 4, 1, 255, g_val, 0);
            DrawChar3x5(fb, 'I', 9, 1, 255, g_val, 0);
        } else {
            // 经典天青色 HI 标头
            DrawChar3x5(fb, 'H', 4, 1, 0, 220, 255);
            DrawChar3x5(fb, 'I', 9, 1, 0, 220, 255);
        }

        // 2. 最高分展示 (Row 7-11)
        DrawScoreNumber(fb, high_score, 7, 255, 215, 0, anim_time);
    }

    // 3. 底部重新开局呼吸提示 (Row 14-15)
    float pulse = (sinf(anim_time * 6.28f * 1.5f) + 1.0f) * 0.5f;
    uint8_t b_val = (uint8_t)(pulse * 180.0f + 60.0f);

    // 提示指示点与微型按键符号
    DrawChar3x5(fb, 'A', 1, 11, 70, 70, 80);
    SetPixelDirect(fb, 7, 14, 0, b_val, (uint8_t)(b_val * 0.8f));
    SetPixelDirect(fb, 8, 14, 0, b_val, (uint8_t)(b_val * 0.8f));
}

} // namespace arcade
