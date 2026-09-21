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

    // 绘制表情包辅助函数 (1:笑脸, 2:哭脸, 3:平静)
    void DrawFace(const ColorRGB& color, int type);

private:
    uint8_t g_hue_;
    uint32_t last_hue_update_;

    // 特效内部状态
    void RenderRainbowWave();
    void RenderAuroraBreathe();
    void RenderMeteorTrail();
    void RenderTwinkleStars();
    void RenderColorCycle();
    void RenderMatrixRain();
    void RenderCenterRipple();
    void RenderDynamicFace();
};
