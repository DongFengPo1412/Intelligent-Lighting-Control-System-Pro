// arcade_result_screen.cpp —— 统一 16x16 街机结算与成绩展示层
#include "arcade_result_screen.h"
#include <string.h>
#include <stdio.h>
#include <math.h>

namespace arcade {

// 3x5 点阵字体数据 (每行 3 bit，占 5 行)
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
    // 自定义 3x5 大写英文字母
    static const uint8_t kChar_G[5] = {0b111, 0b100, 0b101, 0b101, 0b111};
    static const uint8_t kChar_O[5] = {0b111, 0b101, 0b101, 0b101, 0b111};
    static const uint8_t kChar_W[5] = {0b101, 0b101, 0b101, 0b111, 0b101};
    static const uint8_t kChar_I[5] = {0b111, 0b010, 0b010, 0b010, 0b111};
    static const uint8_t kChar_N[5] = {0b101, 0b111, 0b111, 0b101, 0b101};
    static const uint8_t kChar_S[5] = {0b111, 0b100, 0b111, 0b001, 0b111};
    static const uint8_t kChar_C[5] = {0b111, 0b100, 0b100, 0b100, 0b111};
    static const uint8_t kChar_A[5] = {0b010, 0b101, 0b111, 0b101, 0b101};

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

void ArcadeResultScreen::DrawScoreNumber(uint8_t* fb, uint32_t score, int y, uint8_t r, uint8_t g, uint8_t b)
{
    char buf[12];
    int len = snprintf(buf, sizeof(buf), "%u", (unsigned int)score);
    if (len <= 0) return;

    if (len <= 3) {
        // 1~3 位数字直接居中展示 (每个字宽 3，间隙 1)
        int total_w = len * 3 + (len - 1);
        int start_x = (16 - total_w) / 2;
        for (int i = 0; i < len; ++i) {
            DrawDigit3x5(fb, buf[i] - '0', start_x + i * 4, y, r, g, b);
        }
    } else {
        // 4 位数字紧凑排列 (间隙 1: 4*3+3=15 像素，完美塞满 16 列)
        int start_x = 0;
        for (int i = 0; i < len && i < 4; ++i) {
            DrawDigit3x5(fb, buf[i] - '0', start_x + i * 4, y, r, g, b);
        }
    }
}

void ArcadeResultScreen::RenderResult(uint8_t* fb, bool is_victory, uint32_t score, uint32_t high_score, float anim_time)
{
    memset(fb, 0, kFrameBufferSize);

    // 1. 顶层标题 (Row 1-5)
    if (is_victory) {
        // 胜利 "WIN" 金黄色居中 (W at x=2, I at x=6, N at x=10)
        DrawChar3x5(fb, 'W', 2, 1, 255, 215, 0);
        DrawChar3x5(fb, 'I', 6, 1, 255, 215, 0);
        DrawChar3x5(fb, 'N', 10, 1, 255, 215, 0);
    } else {
        // 失败 "G O" 烈焰红色居中 (G at x=4, O at x=9)
        DrawChar3x5(fb, 'G', 4, 1, 255, 30, 30);
        DrawChar3x5(fb, 'O', 9, 1, 255, 30, 30);
    }

    // 2. 分数展示 (Row 8-12)
    // 采用琥珀金/青碧高可读色
    DrawScoreNumber(fb, score, 8, 255, 190, 20);

    // 3. 底部重新开始提示 (Row 14-15)
    // 呼吸脉冲指示灯：提醒玩家按 A 或 手机端重开
    float pulse = (sinf(anim_time * 6.28f * 1.5f) + 1.0f) * 0.5f; // 1.5Hz 呼吸
    uint8_t b_val = (uint8_t)(pulse * 180.0f + 60.0f);

    // 绘制微型 "A" 标志与呼吸点
    DrawChar3x5(fb, 'A', 2, 11, 80, 80, 90);
    SetPixelDirect(fb, 7, 14, 0, b_val, (uint8_t)(b_val * 0.8f));
    SetPixelDirect(fb, 8, 14, 0, b_val, (uint8_t)(b_val * 0.8f));
}

} // namespace arcade
