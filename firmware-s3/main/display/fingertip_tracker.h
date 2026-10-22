#pragma once

#include "display_types.h"
#include "display_hal.h"
#include <freertos/FreeRTOS.h>

/**
 * FingertipTracker
 *
 * 把上位机（PC / MediaPipe）送来的归一化指尖坐标映射到 16x16 灯板，
 * 并渲染一个带平滑跟随、速度变色、拖尾和丢失回落动画的光点追踪器。
 *
 * 坐标约定：
 *   nx, ny 均为 0.0f ~ 1.0f，原点在摄像头画面左上角；
 *   nx 向右增大，ny 向下增大。
 *   如果摄像头画面已经做过水平镜像（cv2.flip(frame, 1)），直接送入即可。
 *
 * 线程约定：
 *   FeedTarget() 可以在串口/网络接收任务中调用；
 *   RenderFrame() 只能在 DisplayManager 的渲染任务中调用。
 *   内部用临界区保护输入状态，配置接口建议在开始推流前调用一次。
 */
class FingertipTracker {
public:
    FingertipTracker();
    ~FingertipTracker() = default;

    FingertipTracker(const FingertipTracker&) = delete;
    FingertipTracker& operator=(const FingertipTracker&) = delete;

    // 清空目标、拖尾和动画状态。切换显示模式时调用。
    void Reset();

    /**
     * 输入一帧指尖位置。
     *
     * @param nx         归一化 x 坐标，0.0f ~ 1.0f
     * @param ny         归一化 y 坐标，0.0f ~ 1.0f
     * @param visible    当前是否检测到目标；false 时保留最后位置并播放回落动画
     * @param confidence 检测置信度，0.0f ~ 1.0f，用于调节亮度
     */
    void FeedTarget(float nx, float ny, bool visible = true, float confidence = 1.0f);

    /**
     * 把摄像头画面中的一个矩形区域映射到整块灯板。
     * 默认是整幅画面 (0, 0, 1, 1)。如果摄像头是 16:9，而灯板是正方形，
     * 可以只取画面中央的正方形，避免横向拉伸。
     */
    void SetInputWindow(float x_min, float y_min, float x_max, float y_max);

    // 坐标方向反转。默认不反转；摄像头未做镜像时可反转 x。
    void SetInvert(bool invert_x, bool invert_y);

    // tau_seconds 越大越平滑但越滞后；deadband_pixels 用于压住微小抖动。
    void SetSmoothing(float tau_seconds, float deadband_pixels = 0.04f);

    // 拖尾点数，0 表示关闭拖尾，最大 10。
    void SetTrailLength(uint8_t points);

    // 目标丢失后，呼吸提示保持多久再完全淡出。
    void SetLostTimeout(uint32_t ms);

    // 自定义核心色与光晕色。
    void SetColors(const ColorRGB& core, const ColorRGB& glow);

    // 渲染一帧并推送到 WS2812 矩阵，返回建议的下一帧延迟（毫秒）。
    uint32_t RenderFrame();

private:
    static constexpr int kMaxTrail = 10;

    struct TrailPoint {
        float x;
        float y;
        uint32_t stamp_ms;
    };

    static float Clamp01(float value);
    static float Clamp(float value, float low, float high);

    static void AddPixel(DisplayHAL& hal, int x, int y, const ColorRGB& color);
    static ColorRGB ScaleColor(const ColorRGB& color, float factor);

    void PushTrail(float x, float y, uint32_t now);
    void DrawGrid();
    void DrawTrail(uint32_t now, const ColorRGB& glow);
    void DrawSoftPoint(float cx, float cy, const ColorRGB& color,
                       float intensity, float radius);
    void DrawTracker(float cx, float cy, const ColorRGB& core,
                     const ColorRGB& glow, float intensity);
    void DrawLostPulse(uint32_t now, bool waiting, uint32_t last_seen_ms);

    portMUX_TYPE lock_ = portMUX_INITIALIZER_UNLOCKED;

    // ---- 输入状态：由接收任务写入，渲染任务读取 ----
    float input_x_min_ = 0.0f;
    float input_y_min_ = 0.0f;
    float input_x_max_ = 1.0f;
    float input_y_max_ = 1.0f;
    bool invert_x_ = false;
    bool invert_y_ = false;

    float target_x_ = 7.5f;
    float target_y_ = 7.5f;
    bool target_visible_ = false;
    float target_confidence_ = 1.0f;
    uint32_t last_input_ms_ = 0;
    uint32_t last_seen_ms_ = 0;
    bool has_seen_ = false;

    // ---- 渲染状态：只由渲染任务修改 ----
    float smooth_x_ = 7.5f;
    float smooth_y_ = 7.5f;
    uint32_t last_render_ms_ = 0;
    uint32_t last_trail_ms_ = 0;

    float smoothing_tau_s_ = 0.07f;
    float deadband_px_ = 0.04f;
    uint32_t input_timeout_ms_ = 500;
    uint32_t lost_timeout_ms_ = 4000;

    ColorRGB core_color_ = ColorRGB(230, 255, 255);
    ColorRGB glow_color_ = ColorRGB(0, 190, 255);

    TrailPoint trail_[kMaxTrail];
    int trail_count_ = 0;
    volatile int trail_limit_ = 9;
};
