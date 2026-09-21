#pragma once

#include "display_types.h"
#include "display_hal.h"

class EffectEngine {
public:
    EffectEngine();
    ~EffectEngine() = default;

    // 重置特效状态
    void Reset();

    // 更新并渲染指定的模式帧 (返回值: 建议下一帧的延迟毫秒数，如 33ms 对应 30FPS)
    uint32_t RenderFrame(DisplayMode mode);

    // 绘制灵动微表情辅助函数 (1:笑脸, 2:哭脸, 3:平静, 具备自然眨眼与眼神游移)
    void DrawLivingFace(const ColorRGB& color, int type);
    void DrawFace(const ColorRGB& color, int type);

private:
    uint8_t g_hue_;
    uint32_t last_hue_update_;

    // 1. 经典视觉特效 (重构为真 2D 空间场)
    void RenderRainbowWave();
    void RenderAuroraBreathe();
    void RenderMeteorTrail();
    void RenderTwinkleStars();
    void RenderColorCycle();
    void RenderMatrixRain();
    void RenderCenterRipple();
    void RenderDynamicFace();

    // 2. 高阶新增特效
    void RenderCyberFire();
    void RenderMatrixRainPro();

    // 赛博物理火焰热量场 (16x16)
    uint8_t fire_heat_[MATRIX_WIDTH][MATRIX_HEIGHT];

    // 黑客帝国代码雨 Pro (16列独立下落流)
    struct RainStream {
        float y;
        float speed;
        int length;
    } rain_streams_[MATRIX_WIDTH];

    // 呼吸繁星结构体
    struct Star {
        int8_t x;
        int8_t y;
        uint8_t brightness;
        int8_t step;
        uint8_t hue;
    } stars_[14];

    // 灵动微表情状态机 (自然生理眨眼与凝视追踪)
    uint32_t next_blink_ms_;
    uint32_t blink_start_ms_;
    bool is_blinking_;
    int gaze_x_; // -1: 左看, 0: 正视, +1: 右看
    uint32_t next_gaze_ms_;
};
