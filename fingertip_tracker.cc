#include "fingertip_tracker.h"

#include <math.h>
#include <string.h>

namespace {

constexpr uint32_t kInputTimeoutMs = 500;
constexpr uint32_t kTrailLifetimeMs = 450;
constexpr uint32_t kTrailSampleMs = 35;
constexpr float kSnapDistancePx = 6.0f;
constexpr float kGridStep = 4.0f;

}  // namespace

FingertipTracker::FingertipTracker()
{
    Reset();
}

void FingertipTracker::Reset()
{
    portENTER_CRITICAL(&lock_);
    target_x_ = (MATRIX_WIDTH - 1) * 0.5f;
    target_y_ = (MATRIX_HEIGHT - 1) * 0.5f;
    target_visible_ = false;
    target_confidence_ = 1.0f;
    last_input_ms_ = 0;
    last_seen_ms_ = 0;
    has_seen_ = false;
    input_timeout_ms_ = kInputTimeoutMs;
    portEXIT_CRITICAL(&lock_);

    smooth_x_ = target_x_;
    smooth_y_ = target_y_;
    last_render_ms_ = get_millis();
    last_trail_ms_ = 0;
    trail_count_ = 0;
    memset(trail_, 0, sizeof(trail_));
}

void FingertipTracker::FeedTarget(float nx, float ny, bool visible, float confidence)
{
    const uint32_t now = get_millis();
    nx = Clamp01(nx);
    ny = Clamp01(ny);

    portENTER_CRITICAL(&lock_);

    float u = 0.5f;
    float v = 0.5f;
    const float x_span = input_x_max_ - input_x_min_;
    const float y_span = input_y_max_ - input_y_min_;
    if (x_span > 0.0001f) u = (nx - input_x_min_) / x_span;
    if (y_span > 0.0001f) v = (ny - input_y_min_) / y_span;

    u = Clamp01(u);
    v = Clamp01(v);
    if (invert_x_) u = 1.0f - u;
    if (invert_y_) v = 1.0f - v;

    if (visible) {
        target_x_ = u * (float)(MATRIX_WIDTH - 1);
        target_y_ = v * (float)(MATRIX_HEIGHT - 1);
        last_seen_ms_ = now;
        has_seen_ = true;
    }

    target_visible_ = visible;
    target_confidence_ = Clamp01(confidence);
    last_input_ms_ = now;

    portEXIT_CRITICAL(&lock_);
}

void FingertipTracker::SetInputWindow(float x_min, float y_min, float x_max, float y_max)
{
    portENTER_CRITICAL(&lock_);
    input_x_min_ = Clamp01(x_min);
    input_y_min_ = Clamp01(y_min);
    input_x_max_ = Clamp01(x_max);
    input_y_max_ = Clamp01(y_max);

    if (input_x_max_ <= input_x_min_ + 0.0001f) {
        input_x_min_ = 0.0f;
        input_x_max_ = 1.0f;
    }
    if (input_y_max_ <= input_y_min_ + 0.0001f) {
        input_y_min_ = 0.0f;
        input_y_max_ = 1.0f;
    }
    portEXIT_CRITICAL(&lock_);
}

void FingertipTracker::SetInvert(bool invert_x, bool invert_y)
{
    portENTER_CRITICAL(&lock_);
    invert_x_ = invert_x;
    invert_y_ = invert_y;
    portEXIT_CRITICAL(&lock_);
}

void FingertipTracker::SetSmoothing(float tau_seconds, float deadband_pixels)
{
    smoothing_tau_s_ = Clamp(tau_seconds, 0.01f, 0.50f);
    deadband_px_ = Clamp(deadband_pixels, 0.0f, 2.0f);
}

void FingertipTracker::SetTrailLength(uint8_t points)
{
    if (points > kMaxTrail) points = kMaxTrail;
    trail_limit_ = points;
}

void FingertipTracker::SetLostTimeout(uint32_t ms)
{
    lost_timeout_ms_ = (ms < 500) ? 500 : ((ms > 10000) ? 10000 : ms);
}

void FingertipTracker::SetColors(const ColorRGB& core, const ColorRGB& glow)
{
    core_color_ = core;
    glow_color_ = glow;
}

uint32_t FingertipTracker::RenderFrame()
{
    DisplayHAL& hal = DisplayHAL::GetInstance();
    const uint32_t now = get_millis();

    uint32_t dt_ms = now - last_render_ms_;
    if (dt_ms < 1) dt_ms = 1;
    if (dt_ms > 100) dt_ms = 100;
    last_render_ms_ = now;

    float target_x;
    float target_y;
    float confidence;
    bool target_visible;
    bool has_seen;
    uint32_t last_input_ms;
    uint32_t last_seen_ms;
    uint32_t timeout_ms;

    portENTER_CRITICAL(&lock_);
    target_x = target_x_;
    target_y = target_y_;
    confidence = target_confidence_;
    target_visible = target_visible_;
    has_seen = has_seen_;
    last_input_ms = last_input_ms_;
    last_seen_ms = last_seen_ms_;
    timeout_ms = input_timeout_ms_;
    portEXIT_CRITICAL(&lock_);

    const bool input_fresh =
        (last_input_ms != 0) && ((now - last_input_ms) <= timeout_ms);
    const bool active = target_visible && input_fresh;

    hal.Clear();
    DrawGrid();

    if (!has_seen) {
        DrawLostPulse(now, true, last_seen_ms);
        hal.Show();
        return 8;
    }

    if (!active) {
        DrawTrail(now, glow_color_);
        DrawLostPulse(now, false, last_seen_ms);
        hal.Show();
        return 8;
    }

    const float dx = target_x - smooth_x_;
    const float dy = target_y - smooth_y_;
    const float distance = sqrtf(dx * dx + dy * dy);

    if (distance > kSnapDistancePx) {
        // 手从画面另一侧重新出现时直接吸附，避免光点慢慢滑过整块屏幕。
        smooth_x_ = target_x;
        smooth_y_ = target_y;
    } else if (distance > deadband_px_) {
        // 快速移动时适当缩短时间常数，兼顾顺滑和跟手。
        float tau = smoothing_tau_s_ / (1.0f + distance * 0.35f);
        const float min_tau = smoothing_tau_s_ * 0.25f;
        if (tau < min_tau) tau = min_tau;

        const float dt_s = (float)dt_ms / 1000.0f;
        const float alpha = 1.0f - expf(-dt_s / tau);
        smooth_x_ += dx * alpha;
        smooth_y_ += dy * alpha;
    }

    smooth_x_ = Clamp(smooth_x_, 0.0f, (float)(MATRIX_WIDTH - 1));
    smooth_y_ = Clamp(smooth_y_, 0.0f, (float)(MATRIX_HEIGHT - 1));

    const float speed_px_s = distance / ((float)dt_ms / 1000.0f);
    const float heat = Clamp01(speed_px_s / 45.0f);
    const ColorRGB glow =
        ColorRGB::Lerp(glow_color_, ColorRGB(255, 45, 180), heat * 0.65f);
    const ColorRGB core =
        ColorRGB::Lerp(core_color_, ColorRGB::White(), 0.35f);
    const float intensity = 0.55f + 0.45f * Clamp01(confidence);

    if (now - last_trail_ms_ >= kTrailSampleMs) {
        PushTrail(smooth_x_, smooth_y_, now);
        last_trail_ms_ = now;
    }

    DrawTrail(now, glow);
    DrawTracker(smooth_x_, smooth_y_, core, glow, intensity);

    hal.Show();
    return 8;  // 与 RMT 刷新耗时叠加后约为 60 FPS
}

float FingertipTracker::Clamp01(float value)
{
    // 这个写法同时把 NaN 收敛到 0，避免异常检测值污染后续亮度计算。
    if (!(value > 0.0f)) return 0.0f;
    if (value > 1.0f) return 1.0f;
    return value;
}

float FingertipTracker::Clamp(float value, float low, float high)
{
    if (!(value >= low)) return low;
    if (value > high) return high;
    return value;
}

void FingertipTracker::AddPixel(DisplayHAL& hal, int x, int y, const ColorRGB& color)
{
    if (x < 0 || x >= MATRIX_WIDTH || y < 0 || y >= MATRIX_HEIGHT) return;
    ColorRGB pixel = hal.GetPixel(x, y);
    pixel += color;
    hal.SetPixel(x, y, pixel);
}

ColorRGB FingertipTracker::ScaleColor(const ColorRGB& color, float factor)
{
    return ColorRGB::Lerp(ColorRGB::Black(), color, Clamp01(factor));
}

void FingertipTracker::PushTrail(float x, float y, uint32_t now)
{
    const int limit = trail_limit_;
    if (limit <= 0) return;

    if (trail_count_ > 0) {
        const float dx = x - trail_[trail_count_ - 1].x;
        const float dy = y - trail_[trail_count_ - 1].y;
        // 指尖停住时不要反复叠加同一个点，否则拖尾会变成一团常亮光斑。
        if (dx * dx + dy * dy < 0.04f) return;
    }

    if (trail_count_ >= limit) {
        const int keep = limit - 1;
        if (keep > 0) {
            const int start = trail_count_ - keep;
            memmove(&trail_[0], &trail_[start], sizeof(TrailPoint) * keep);
        }
        trail_count_ = keep;
    }

    if (trail_count_ < kMaxTrail) {
        trail_[trail_count_].x = x;
        trail_[trail_count_].y = y;
        trail_[trail_count_].stamp_ms = now;
        trail_count_++;
    }
}

void FingertipTracker::DrawGrid()
{
    DisplayHAL& hal = DisplayHAL::GetInstance();

    // 很暗的 4x4 网格，用来提示摄像头画面与灯阵的映射关系。
    for (int i = (int)kGridStep; i < MATRIX_WIDTH; i += (int)kGridStep) {
        for (int y = 0; y < MATRIX_HEIGHT; y++) {
            AddPixel(hal, i, y, ColorRGB(0, 0, 18));
        }
    }
    for (int i = (int)kGridStep; i < MATRIX_HEIGHT; i += (int)kGridStep) {
        for (int x = 0; x < MATRIX_WIDTH; x++) {
            AddPixel(hal, x, i, ColorRGB(0, 0, 18));
        }
    }
}

void FingertipTracker::DrawTrail(uint32_t now, const ColorRGB& glow)
{
    int count = trail_count_;
    int start = 0;
    const int limit = trail_limit_;
    if (count > limit) {
        start = count - limit;
        count = limit;
    }

    for (int n = 0; n < count; n++) {
        const int i = start + n;
        const uint32_t age = now - trail_[i].stamp_ms;
        if (age >= kTrailLifetimeMs) continue;

        const float fade = 1.0f - (float)age / (float)kTrailLifetimeMs;
        DrawSoftPoint(trail_[i].x, trail_[i].y, glow,
                      0.28f * fade * fade, 1.8f);
    }
}

void FingertipTracker::DrawSoftPoint(float cx, float cy, const ColorRGB& color,
                                     float intensity, float radius)
{
    DisplayHAL& hal = DisplayHAL::GetInstance();
    intensity = Clamp01(intensity);
    if (intensity <= 0.0f || radius <= 0.0f) return;

    int x0 = (int)floorf(cx - radius);
    int x1 = (int)ceilf(cx + radius);
    int y0 = (int)floorf(cy - radius);
    int y1 = (int)ceilf(cy + radius);
    if (x0 < 0) x0 = 0;
    if (y0 < 0) y0 = 0;
    if (x1 >= MATRIX_WIDTH) x1 = MATRIX_WIDTH - 1;
    if (y1 >= MATRIX_HEIGHT) y1 = MATRIX_HEIGHT - 1;

    for (int y = y0; y <= y1; y++) {
        for (int x = x0; x <= x1; x++) {
            const float dx = (float)x - cx;
            const float dy = (float)y - cy;
            const float d = sqrtf(dx * dx + dy * dy);
            if (d >= radius) continue;

            float falloff = 1.0f - d / radius;
            falloff *= falloff;
            AddPixel(hal, x, y, ScaleColor(color, intensity * falloff));
        }
    }
}

void FingertipTracker::DrawTracker(float cx, float cy, const ColorRGB& core,
                                   const ColorRGB& glow, float intensity)
{
    DisplayHAL& hal = DisplayHAL::GetInstance();
    intensity = Clamp01(intensity);
    if (intensity <= 0.0f) return;

    // 1. 柔和外晕
    DrawSoftPoint(cx, cy, glow, intensity * 0.45f, 3.2f);

    // 2. 半径约 2 像素的追踪环
    int x0 = (int)floorf(cx - 3.0f);
    int x1 = (int)ceilf(cx + 3.0f);
    int y0 = (int)floorf(cy - 3.0f);
    int y1 = (int)ceilf(cy + 3.0f);
    if (x0 < 0) x0 = 0;
    if (y0 < 0) y0 = 0;
    if (x1 >= MATRIX_WIDTH) x1 = MATRIX_WIDTH - 1;
    if (y1 >= MATRIX_HEIGHT) y1 = MATRIX_HEIGHT - 1;

    for (int y = y0; y <= y1; y++) {
        for (int x = x0; x <= x1; x++) {
            const float dx = (float)x - cx;
            const float dy = (float)y - cy;
            const float d = sqrtf(dx * dx + dy * dy);
            const float ring = fabsf(d - 2.0f);
            if (ring < 0.55f) {
                const float fade = 1.0f - ring / 0.55f;
                AddPixel(hal, x, y, ScaleColor(glow, intensity * 0.55f * fade));
            }
        }
    }

    // 3. 四向短刻度，让追踪器在 16x16 上仍然有明确的中心感
    const int ix = (int)lroundf(cx);
    const int iy = (int)lroundf(cy);
    const float arm_intensity = 0.43f * intensity;
    AddPixel(hal, ix - 3, iy, ScaleColor(glow, arm_intensity));
    AddPixel(hal, ix + 3, iy, ScaleColor(glow, arm_intensity));
    AddPixel(hal, ix, iy - 3, ScaleColor(glow, arm_intensity));
    AddPixel(hal, ix, iy + 3, ScaleColor(glow, arm_intensity));

    // 4. 高亮核心
    DrawSoftPoint(cx, cy, core, intensity, 1.15f);
}

void FingertipTracker::DrawLostPulse(uint32_t now, bool waiting, uint32_t last_seen_ms)
{
    DisplayHAL& hal = DisplayHAL::GetInstance();

    float cx = (MATRIX_WIDTH - 1) * 0.5f;
    float cy = (MATRIX_HEIGHT - 1) * 0.5f;
    float fade = 1.0f;

    if (!waiting) {
        cx = smooth_x_;
        cy = smooth_y_;
        const uint32_t age = now - last_seen_ms;
        fade = 1.0f - (float)age / (float)lost_timeout_ms_;
        fade = Clamp01(fade);
    }

    if (fade <= 0.0f) return;

    const float phase = (float)(now % 1600) / 1600.0f;
    const float radius = waiting ? (1.0f + phase * 3.0f) : (0.8f + phase * 3.8f);
    const float ring_intensity = (1.0f - phase) * 0.32f * fade;

    int x0 = (int)floorf(cx - radius - 1.0f);
    int x1 = (int)ceilf(cx + radius + 1.0f);
    int y0 = (int)floorf(cy - radius - 1.0f);
    int y1 = (int)ceilf(cy + radius + 1.0f);
    if (x0 < 0) x0 = 0;
    if (y0 < 0) y0 = 0;
    if (x1 >= MATRIX_WIDTH) x1 = MATRIX_WIDTH - 1;
    if (y1 >= MATRIX_HEIGHT) y1 = MATRIX_HEIGHT - 1;

    for (int y = y0; y <= y1; y++) {
        for (int x = x0; x <= x1; x++) {
            const float dx = (float)x - cx;
            const float dy = (float)y - cy;
            const float d = sqrtf(dx * dx + dy * dy);
            const float ring = fabsf(d - radius);
            if (ring < 0.7f) {
                const float falloff = 1.0f - ring / 0.7f;
                AddPixel(hal, x, y,
                         ScaleColor(glow_color_, ring_intensity * falloff));
            }
        }
    }

    DrawSoftPoint(cx, cy, glow_color_, 0.12f * fade, 0.9f);
}
