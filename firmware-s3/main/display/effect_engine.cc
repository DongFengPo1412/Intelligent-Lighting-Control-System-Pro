#include "effect_engine.h"
#include <math.h>
#include <string.h>

EffectEngine::EffectEngine()
    : g_hue_(0),
      last_hue_update_(0),
      next_blink_ms_(0),
      blink_start_ms_(0),
      is_blinking_(false),
      gaze_x_(0),
      next_gaze_ms_(0)
{
    memset(fire_heat_, 0, sizeof(fire_heat_));
    Reset();
}

void EffectEngine::Reset()
{
    g_hue_ = 0;
    last_hue_update_ = get_millis();

    // 1. 初始化赛博火焰热量场
    memset(fire_heat_, 0, sizeof(fire_heat_));

    // 2. 初始化黑客帝国代码雨 Pro
    for (int x = 0; x < MATRIX_WIDTH; x++) {
        rain_streams_[x].y = -(float)random8(16);
        rain_streams_[x].speed = 0.35f + (float)random8(45) / 100.0f; // 0.35 ~ 0.8 像素/帧
        rain_streams_[x].length = 5 + random8(6);                      // 5 ~ 10 格长拖尾
    }

    // 3. 初始化呼吸繁星
    for (int i = 0; i < 14; i++) {
        stars_[i].x = random8(16);
        stars_[i].y = random8(16);
        stars_[i].brightness = random8(200);
        stars_[i].step = (random8(2) == 0 ? 3 : -3);
        stars_[i].hue = random8();
    }

    // 4. 初始化灵动微表情状态机
    uint32_t now = get_millis();
    next_blink_ms_ = now + 3000 + (esp_random() % 2000);
    blink_start_ms_ = 0;
    is_blinking_ = false;
    gaze_x_ = 0;
    next_gaze_ms_ = now + 2500 + (esp_random() % 2000);
}

// =========================================================================
// 灵动微表情系统 (具备自然生理眨眼与眼神游移微动画)
// =========================================================================
void EffectEngine::DrawLivingFace(const ColorRGB& color, int type)
{
    DisplayHAL& hal = DisplayHAL::GetInstance();
    hal.Clear();

    uint32_t now = get_millis();

    // 1. 生理眨眼时间机 (每隔 3.5~5.5 秒自然眨动一次，持续 160ms)
    if (!is_blinking_ && now >= next_blink_ms_) {
        is_blinking_ = true;
        blink_start_ms_ = now;
        next_blink_ms_ = now + 3500 + (esp_random() % 2500);
    }

    uint32_t blink_elapsed = now - blink_start_ms_;
    if (is_blinking_ && blink_elapsed > 160) {
        is_blinking_ = false;
    }

    // 2. 眼神注视机 (每隔 2.5~4.5 秒随机切换：正视、左顾、右盼)
    if (now >= next_gaze_ms_) {
        int r = random8(3);
        gaze_x_ = (r == 0) ? -1 : ((r == 1) ? 0 : 1);
        next_gaze_ms_ = now + 2500 + (esp_random() % 2000);
    }

    // 3. 绘制外围脸部柔和圆环 (以 7.5, 7.5 为中心)
    for (int y = 0; y < 16; y++) {
        for (int x = 0; x < 16; x++) {
            float d = sqrtf((x - 7.5f) * (x - 7.5f) + (y - 7.5f) * (y - 7.5f));
            if (d < 7.4f && d > 6.2f) {
                hal.SetPixel(x, y, color);
            }
        }
    }

    // 4. 绘制灵动眼睛 (左眼基准: 5, 右眼基准: 10, 纵向: 5)
    int left_eye_x = 5 + gaze_x_;
    int right_eye_x = 10 + gaze_x_;

    if (is_blinking_) {
        if (blink_elapsed < 40 || blink_elapsed > 120) {
            // 半闭眼形态
            hal.SetPixel(left_eye_x, 5, color);
            hal.SetPixel(right_eye_x, 5, color);
        } else {
            // 全闭眼微弧线 (上睑与下睑完全合拢)
            hal.SetPixel(left_eye_x - 1, 5, color);
            hal.SetPixel(left_eye_x, 5, color);
            hal.SetPixel(left_eye_x + 1, 5, color);

            hal.SetPixel(right_eye_x - 1, 5, color);
            hal.SetPixel(right_eye_x, 5, color);
            hal.SetPixel(right_eye_x + 1, 5, color);
        }
    } else {
        // 睁眼状态：双像素灵动大眼，神采奕奕
        hal.SetPixel(left_eye_x, 4, color);
        hal.SetPixel(left_eye_x, 5, color);
        hal.SetPixel(right_eye_x, 4, color);
        hal.SetPixel(right_eye_x, 5, color);
    }

    // 5. 绘制富有表现力的嘴巴
    if (type == 1) {
        // 甜美笑脸 (嘴角上扬)
        hal.SetPixel(4, 10, color);
        hal.SetPixel(5, 11, color);
        for (int i = 6; i <= 9; i++) hal.SetPixel(i, 12, color);
        hal.SetPixel(10, 11, color);
        hal.SetPixel(11, 10, color);
    } else if (type == 2) {
        // 沮丧哭脸 (嘴角下耷，含眼泪)
        hal.SetPixel(4, 12, color);
        hal.SetPixel(5, 11, color);
        for (int i = 6; i <= 9; i++) hal.SetPixel(i, 10, color);
        hal.SetPixel(10, 11, color);
        hal.SetPixel(11, 12, color);

        // 蓝色彩滴落泪 (动态闪烁)
        if ((now / 250) % 2 == 0) {
            hal.SetPixel(left_eye_x, 7, ColorRGB::Cyan());
            hal.SetPixel(right_eye_x, 7, ColorRGB::Cyan());
        }
    } else {
        // 平静/思考 (微表情平直抿嘴)
        for (int i = 6; i <= 9; i++) hal.SetPixel(i, 11, color);
    }
}

// 兼容接口
void EffectEngine::DrawFace(const ColorRGB& color, int type)
{
    DrawLivingFace(color, type);
}

// =========================================================================
// 特效 1: 真 2D 对角对流彩虹 (消除物理拼缝撕裂)
// =========================================================================
void EffectEngine::RenderRainbowWave()
{
    DisplayHAL& hal = DisplayHAL::GetInstance();
    for (int y = 0; y < 16; y++) {
        for (int x = 0; x < 16; x++) {
            // 45度空间对角向量连续流转，完美抹平板级接缝
            uint8_t hue = g_hue_ + (x + y) * 9;
            hal.SetPixel(x, y, hsv2rgb_fast(ColorHSV(hue, 245, 255)));
        }
    }
}

// =========================================================================
// 特效 2: 复合流光极光 (双波长正弦干涉场)
// =========================================================================
void EffectEngine::RenderAuroraBreathe()
{
    DisplayHAL& hal = DisplayHAL::GetInstance();
    uint8_t wave_a = beatsin8(11, 0, 50);
    uint8_t wave_b = beatsin8(17, 0, 40);

    for (int y = 0; y < 16; y++) {
        for (int x = 0; x < 16; x++) {
            // 正弦流体干涉计算
            uint8_t hue = g_hue_ + (x * 6) + (y * 5) + wave_a;
            float curtain = sinf((x * 0.45f) + (wave_b * 0.08f)) * 0.5f + 0.5f;
            uint8_t val = (uint8_t)(curtain * 175.0f + 70.0f);
            hal.SetPixel(x, y, hsv2rgb_fast(ColorHSV(hue, 215, val)));
        }
    }
}

// =========================================================================
// 特效 3: 双星交织流星划过 (带柔和渐隐拖尾)
// =========================================================================
void EffectEngine::RenderMeteorTrail()
{
    DisplayHAL& hal = DisplayHAL::GetInstance();
    hal.FadeToBlackBy(45); // 优雅丝滑的余晖衰减

    // 主流星 (明亮翡翠/紫金渐变)
    int x1 = beatsin8(13, 0, 15);
    int y1 = beatsin8(9, 0, 15);
    hal.SetPixel(x1, y1, hsv2rgb_fast(ColorHSV(g_hue_, 170, 255)));

    // 伴星 (反相位灵动追逐)
    int x2 = beatsin8(19, 0, 15);
    int y2 = beatsin8(12, 0, 15);
    hal.SetPixel(x2, y2, hsv2rgb_fast(ColorHSV(g_hue_ + 110, 210, 230)));
}

// =========================================================================
// 特效 4: 呼吸繁星点点 (每个星芒独立亮暗生命周期)
// =========================================================================
void EffectEngine::RenderTwinkleStars()
{
    DisplayHAL& hal = DisplayHAL::GetInstance();
    hal.FadeToBlackBy(20);

    for (int i = 0; i < 14; i++) {
        int new_b = (int)stars_[i].brightness + stars_[i].step;
        if (new_b >= 255) {
            stars_[i].brightness = 255;
            stars_[i].step = -3 - random8(4);
        } else if (new_b <= 0) {
            stars_[i].brightness = 0;
            stars_[i].x = random8(16);
            stars_[i].y = random8(16);
            stars_[i].step = 3 + random8(4);
            stars_[i].hue = random8();
        } else {
            stars_[i].brightness = (uint8_t)new_b;
        }

        hal.SetPixel(stars_[i].x, stars_[i].y, hsv2rgb_fast(ColorHSV(stars_[i].hue, 140, stars_[i].brightness)));
    }
}

// =========================================================================
// 特效 5: 全屏温润色彩流转
// =========================================================================
void EffectEngine::RenderColorCycle()
{
    DisplayHAL& hal = DisplayHAL::GetInstance();
    hal.FillSolid(hsv2rgb_fast(ColorHSV(g_hue_, 250, 220)));
}

// =========================================================================
// 特效 6: 经典乱序雨滴
// =========================================================================
void EffectEngine::RenderMatrixRain()
{
    DisplayHAL& hal = DisplayHAL::GetInstance();
    hal.FadeToBlackBy(70);
    for (int i = 0; i < 3; i++) {
        int x = random8(16);
        int y = random8(16);
        hal.SetPixel(x, y, hsv2rgb_fast(ColorHSV(g_hue_ + random8(32), 220, 255)));
    }
}

// =========================================================================
// 特效 7: 抗锯齿双同心水波纹
// =========================================================================
void EffectEngine::RenderCenterRipple()
{
    DisplayHAL& hal = DisplayHAL::GetInstance();
    hal.Clear();

    uint32_t ms = get_millis();
    float r1 = fmodf((float)ms * 0.007f, 12.0f);
    float r2 = fmodf((float)(ms + 800) * 0.007f, 12.0f);

    for (int y = 0; y < 16; y++) {
        for (int x = 0; x < 16; x++) {
            float d = sqrtf((x - 7.5f) * (x - 7.5f) + (y - 7.5f) * (y - 7.5f));
            float dist1 = fabsf(d - r1);
            float dist2 = fabsf(d - r2);
            float b = 0.0f;

            if (dist1 < 1.2f) {
                b += (1.2f - dist1) / 1.2f * (1.0f - (r1 / 12.0f));
            }
            if (dist2 < 1.2f) {
                b += (1.2f - dist2) / 1.2f * (1.0f - (r2 / 12.0f));
            }

            if (b > 1.0f) b = 1.0f;
            if (b > 0.04f) {
                uint8_t val = (uint8_t)(b * 255.0f);
                hal.SetPixel(x, y, hsv2rgb_fast(ColorHSV(g_hue_ + (uint8_t)(d * 10), 240, val)));
            }
        }
    }
}

// =========================================================================
// 特效 8: 瞬息万变动态表情
// =========================================================================
void EffectEngine::RenderDynamicFace()
{
    ColorRGB c = hsv2rgb_fast(ColorHSV(g_hue_, 255, 255));
    int type = (g_hue_ % 128 > 64) ? 1 : 2;
    DrawLivingFace(c, type);
}

// =========================================================================
// 高阶全新特效 1: 赛博物理火焰模拟 (Perlin Cyber Flame)
// =========================================================================
void EffectEngine::RenderCyberFire()
{
    DisplayHAL& hal = DisplayHAL::GetInstance();

    // 1. 随机冷却：每格热量随时间自然散失
    for (int x = 0; x < MATRIX_WIDTH; x++) {
        for (int y = 0; y < MATRIX_HEIGHT; y++) {
            uint8_t cool = random8(12, 28);
            fire_heat_[x][y] = (fire_heat_[x][y] > cool) ? fire_heat_[x][y] - cool : 0;
        }
    }

    // 2. 对流与水平热传导：热气自然上升并左右扩散
    for (int y = 0; y < MATRIX_HEIGHT - 1; y++) {
        for (int x = 0; x < MATRIX_WIDTH; x++) {
            int left_x = (x > 0) ? (x - 1) : 0;
            int right_x = (x < MATRIX_WIDTH - 1) ? (x + 1) : (MATRIX_WIDTH - 1);

            uint16_t heat_sum = fire_heat_[left_x][y + 1] +
                                2 * fire_heat_[x][y + 1] +
                                fire_heat_[right_x][y + 1];
            fire_heat_[x][y] = (uint8_t)(heat_sum / 4);
        }
    }

    // 3. 底部热源引燃：在最下层随机注入炽热燃料
    for (int x = 0; x < MATRIX_WIDTH; x++) {
        if (random8() < 160) {
            fire_heat_[x][MATRIX_HEIGHT - 1] = random8(180, 255);
        }
    }

    // 4. 将物理热量值映射到黑体辐射火焰色系
    for (int y = 0; y < MATRIX_HEIGHT; y++) {
        for (int x = 0; x < MATRIX_WIDTH; x++) {
            uint8_t heat = fire_heat_[x][y];
            ColorRGB color = ColorRGB::Black();

            if (heat > 0) {
                if (heat < 80) {
                    // 暗红至炽红阶段
                    color = ColorRGB(heat * 3, 0, 0);
                } else if (heat < 180) {
                    // 炽红至暖橙金黄阶段
                    color = ColorRGB(255, (heat - 80) * 2, 0);
                } else {
                    // 耀眼金黄至白热阶段
                    uint8_t white_boost = (heat - 180) * 2;
                    color = ColorRGB(255, 200 + (heat - 180) / 2, white_boost);
                }
            }
            hal.SetPixel(x, y, color);
        }
    }
}

// =========================================================================
// 高阶全新特效 2: 黑客帝国数字代码雨 Pro (Matrix Code Rain 2.0)
// =========================================================================
void EffectEngine::RenderMatrixRainPro()
{
    DisplayHAL& hal = DisplayHAL::GetInstance();
    hal.Clear();

    for (int x = 0; x < MATRIX_WIDTH; x++) {
        rain_streams_[x].y += rain_streams_[x].speed;

        // 如果整条流已经完全滑出屏幕下方，重置到顶部上方
        if (rain_streams_[x].y - rain_streams_[x].length > (float)MATRIX_HEIGHT) {
            rain_streams_[x].y = -(float)random8(6);
            rain_streams_[x].speed = 0.35f + (float)random8(45) / 100.0f;
            rain_streams_[x].length = 5 + random8(6);
        }

        int head_y = (int)rain_streams_[x].y;

        // 沿纵向绘制光柱拖尾
        for (int i = 0; i <= rain_streams_[x].length; i++) {
            int py = head_y - i;
            if (py >= 0 && py < MATRIX_HEIGHT) {
                if (i == 0) {
                    // 头部：极亮青白光子脉冲
                    hal.SetPixel(x, py, ColorRGB(220, 255, 240));
                } else {
                    // 尾部：荧光霓虹绿向深邃墨绿优雅渐隐
                    float fade = 1.0f - ((float)i / (float)rain_streams_[x].length);
                    uint8_t g = (uint8_t)(fade * 255.0f);
                    uint8_t r = (uint8_t)(fade * 15.0f);
                    uint8_t b = (uint8_t)(fade * 30.0f);
                    hal.SetPixel(x, py, ColorRGB(r, g, b));
                }
            }
        }
    }
}

// =========================================================================
// 统一模式渲染分发中心
// =========================================================================
uint32_t EffectEngine::RenderFrame(DisplayMode mode)
{
    DisplayHAL& hal = DisplayHAL::GetInstance();

    // 更新全局流动色相
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
            DrawLivingFace(ColorRGB::Yellow(), 1);
            break;
        case DisplayMode::FACE_CRY:
            DrawLivingFace(ColorRGB::Blue(), 2);
            break;
        case DisplayMode::FACE_NEUTRAL:
            DrawLivingFace(ColorRGB::Green(), 3);
            break;
        case DisplayMode::FACE_DYNAMIC:
            RenderDynamicFace();
            break;
        case DisplayMode::AI_FEEDBACK:
            DrawLivingFace(ColorRGB::Yellow(), 1);
            break;
        case DisplayMode::CYBER_FIRE:
            RenderCyberFire();
            break;
        case DisplayMode::MATRIX_RAIN_PRO:
            RenderMatrixRainPro();
            break;
        default:
            hal.Clear();
            break;
    }

    hal.Show();
    return 33; // 约 30 FPS 刷新
}
