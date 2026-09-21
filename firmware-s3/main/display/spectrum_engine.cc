#include "spectrum_engine.h"
#include <stdio.h>
#include <string.h>

SpectrumEngine::SpectrumEngine()
    : is_beat_(0),
      last_feed_time_(0)
{
    Reset();
}

void SpectrumEngine::Reset()
{
    is_beat_ = 0;
    for (int i = 0; i < 16; i++) {
        bands_[i] = 0;
        fall_bands_[i] = 0.0f;
    }
}

void SpectrumEngine::FeedBands(int beat, const int bands[16])
{
    is_beat_ = beat;
    for (int i = 0; i < 16; i++) {
        bands_[i] = bands[i];
    }

    // 最左列低频补偿与鼓点爆发 (复刻中阶调优逻辑)
    if (bands_[0] <= 1) {
        bands_[0] = bands_[1] + 1;
    }
    if (is_beat_ == 1) {
        bands_[0] = 15; // 鼓点爆发，低音冲顶
    }

    last_feed_time_ = get_millis();
}

void SpectrumEngine::ParseSerialCommand(const char* cmd)
{
    if (!cmd || strncmp(cmd, "f,", 2) != 0) return;

    int beat = 0;
    int b[16] = {0};
    int parsed = sscanf(cmd, "f,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d",
                        &beat,
                        &b[0], &b[1], &b[2], &b[3],
                        &b[4], &b[5], &b[6], &b[7],
                        &b[8], &b[9], &b[10], &b[11],
                        &b[12], &b[13], &b[14], &b[15]);

    if (parsed == 17) {
        FeedBands(beat, b);
    }
}

uint32_t SpectrumEngine::RenderFrame()
{
    DisplayHAL& hal = DisplayHAL::GetInstance();

    // 1. 整体渐暗：保留拖尾余晖 (复刻中阶 fadeToBlackBy 160)
    hal.FadeToBlackBy(160);

    // 2. 遍历横向 16 列音轨
    for (int x = 0; x < MATRIX_WIDTH; x++) {
        // 重力加速度衰减
        if ((float)bands_[x] >= fall_bands_[x]) {
            fall_bands_[x] = (float)bands_[x]; // 瞬间上升
        } else {
            // 固定步长 + 比例衰减
            fall_bands_[x] -= (0.4f + fall_bands_[x] * 0.05f);

            // 触底归零
            if (fall_bands_[x] < (float)bands_[x] + 0.2f && bands_[x] <= 2) {
                fall_bands_[x] = (float)bands_[x];
            }
            if (fall_bands_[x] < 0.0f) fall_bands_[x] = 0.0f;
        }

        int current_height = (int)fall_bands_[x];
        if (current_height > 15) current_height = 15;

        // 3. 纵向绘制：15 - y 倒算物理坐标，从底部面板向上生长
        for (int y = 0; y <= current_height; y++) {
            int target_physical_y = 15 - y;
            if (target_physical_y < 0) target_physical_y = 0;

            // 色彩渐变：暖色(红橙)在底，冷色(蓝紫)冲顶
            ColorRGB pixel_color = hsv2rgb_fast(ColorHSV(y * 14 + 140, 245, 255));
            hal.SetPixel(x, target_physical_y, pixel_color);
        }
    }

    // 4. 鼓点微光叠加
    if (is_beat_ == 1) {
        ColorRGB beat_glow(0, 25, 25);
        for (int i = 0; i < TOTAL_LEDS; i++) {
            hal.GetBuffer()[i] += beat_glow;
        }
        is_beat_ = 0; // 消费瞬态鼓点
    }

    hal.Show();
    return 20; // 约 50 FPS 高频刷新
}
