#include "effect_engine.h"
#include <math.h>

EffectEngine::EffectEngine()
    : g_hue_(0),
      last_hue_update_(0)
{
}

void EffectEngine::Reset()
{
    g_hue_ = 0;
    last_hue_update_ = get_millis();
}

void EffectEngine::DrawFace(const ColorRGB& color, int type)
{
    DisplayHAL& hal = DisplayHAL::GetInstance();
    hal.Clear();

    // 绘制脸部圆形轮廓 (以 7.5, 7.5 为圆心)
    for (int y = 0; y < 16; y++) {
        for (int x = 0; x < 16; x++) {
            float d = sqrtf(powf(x - 7.5f, 2.0f) + powf(y - 7.5f, 2.0f));
            if (d < 7.5f && d > 6.5f) {
                hal.SetPixel(x, y, color);
            }
        }
    }

    // 绘制眼睛 (5, 5) 和 (10, 5)
    hal.SetPixel(5, 5, color);
    hal.SetPixel(10, 5, color);

    // 绘制嘴巴
    if (type == 1) { // 笑脸 (Smiling)
        hal.SetPixel(5, 11, color);
        hal.SetPixel(10, 11, color);
        for (int i = 6; i <= 9; i++) hal.SetPixel(i, 12, color);
    } else if (type == 2) { // 哭脸 (Crying)
        hal.SetPixel(5, 12, color);
        hal.SetPixel(10, 12, color);
        for (int i = 6; i <= 9; i++) hal.SetPixel(i, 11, color);
    } else { // 平静 (Neutral)
        for (int i = 6; i <= 9; i++) hal.SetPixel(i, 11, color);
    }
}

void EffectEngine::RenderRainbowWave()
{
    DisplayHAL& hal = DisplayHAL::GetInstance();
    for (int i = 0; i < TOTAL_LEDS; i++) {
        uint8_t hue = g_hue_ + i * 7;
        hal.SetPixelByIndex(i, hsv2rgb_fast(ColorHSV(hue, 240, 255)));
    }
}

void EffectEngine::RenderAuroraBreathe()
{
    DisplayHAL& hal = DisplayHAL::GetInstance();
    uint8_t br = beatsin8(15, 30, 255); // 呼吸亮度正弦振荡
    for (int i = 0; i < TOTAL_LEDS; i++) {
        uint8_t hue = g_hue_ + i * 4;
        hal.SetPixelByIndex(i, hsv2rgb_fast(ColorHSV(hue, 220, br)));
    }
}

void EffectEngine::RenderMeteorTrail()
{
    DisplayHAL& hal = DisplayHAL::GetInstance();
    hal.FadeToBlackBy(40); // 拖尾淡出
    int x = beatsin8(13, 0, 15);
    int y = beatsin8(8, 0, 15);
    hal.SetPixel(x, y, hsv2rgb_fast(ColorHSV(g_hue_, 200, 255)));
}

void EffectEngine::RenderTwinkleStars()
{
    DisplayHAL& hal = DisplayHAL::GetInstance();
    hal.FadeToBlackBy(15);
    if (random8() < 25) {
        int x = random8(16);
        int y = random8(16);
        hal.SetPixel(x, y, ColorRGB::White());
    }
}

void EffectEngine::RenderColorCycle()
{
    DisplayHAL& hal = DisplayHAL::GetInstance();
    hal.FillSolid(hsv2rgb_fast(ColorHSV(g_hue_, 255, 220)));
}

void EffectEngine::RenderMatrixRain()
{
    DisplayHAL& hal = DisplayHAL::GetInstance();
    hal.FadeToBlackBy(80);
    for (int i = 0; i < 3; i++) {
        int x = random8(16);
        int y = random8(16);
        hal.SetPixel(x, y, hsv2rgb_fast(ColorHSV(g_hue_ + random8(32), 200, 255)));
    }
}

void EffectEngine::RenderCenterRipple()
{
    DisplayHAL& hal = DisplayHAL::GetInstance();
    hal.Clear();
    float r = (float)(get_millis() % 1500) / 100.0f; // 0 ~ 15
    for (int y = 0; y < 16; y++) {
        for (int x = 0; x < 16; x++) {
            float d = sqrtf(powf(x - 7.5f, 2.0f) + powf(y - 7.5f, 2.0f));
            if (fabsf(d - r) < 1.0f) {
                hal.SetPixel(x, y, hsv2rgb_fast(ColorHSV(g_hue_, 255, 255)));
            }
        }
    }
}

void EffectEngine::RenderDynamicFace()
{
    ColorRGB c = hsv2rgb_fast(ColorHSV(g_hue_, 255, 255));
    int type = (g_hue_ % 128 > 64) ? 1 : 2;
    DrawFace(c, type);
}

uint32_t EffectEngine::RenderFrame(DisplayMode mode)
{
    DisplayHAL& hal = DisplayHAL::GetInstance();

    // 更新全局色彩色相
    uint32_t now = get_millis();
    if (now - last_hue_update_ >= 20) {
        g_hue_++;
        last_hue_update_ = now;
    }

    switch (mode) {
        case DisplayMode::OFF:
            hal.Clear();
            break;
        case DisplayMode::SOLID_RED:
            hal.FillSolid(ColorRGB::Red());
            break;
        case DisplayMode::SOLID_BLUE:
            hal.FillSolid(ColorRGB::Blue());
            break;
        case DisplayMode::SOLID_GREEN:
            hal.FillSolid(ColorRGB::Green());
            break;
        case DisplayMode::RAINBOW_WAVE:
            RenderRainbowWave();
            break;
        case DisplayMode::AURORA_BREATHE:
            RenderAuroraBreathe();
            break;
        case DisplayMode::METEOR_TRAIL:
            RenderMeteorTrail();
            break;
        case DisplayMode::TWINKLE_STARS:
            RenderTwinkleStars();
            break;
        case DisplayMode::COLOR_CYCLE:
            RenderColorCycle();
            break;
        case DisplayMode::MATRIX_RAIN:
            RenderMatrixRain();
            break;
        case DisplayMode::CENTER_RIPPLE:
            RenderCenterRipple();
            break;
        case DisplayMode::FACE_SMILE:
            DrawFace(ColorRGB::Yellow(), 1);
            break;
        case DisplayMode::FACE_CRY:
            DrawFace(ColorRGB::Blue(), 2);
            break;
        case DisplayMode::FACE_NEUTRAL:
            DrawFace(ColorRGB::Green(), 3);
            break;
        case DisplayMode::FACE_DYNAMIC:
            RenderDynamicFace();
            break;
        case DisplayMode::AI_FEEDBACK:
            DrawFace(ColorRGB::Yellow(), 1);
            break;
        default:
            hal.Clear();
            break;
    }

    hal.Show();
    return 33; // 约 30 FPS 刷新
}
