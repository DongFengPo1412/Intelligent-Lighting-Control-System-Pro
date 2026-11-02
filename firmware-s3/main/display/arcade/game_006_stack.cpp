// game_006_stack.cpp —— 堆叠大师 16 核心实现
#include "game_006_stack.h"
#include <string.h>
#include <math.h>

namespace arcade {

// 将彩虹 HSV 色环转换为 RGB888
static void HsvToRgb(float h, float s, float v, uint8_t& r, uint8_t& g, uint8_t& b) {
    float c = v * s;
    float h_prime = fmodf(h / 60.0f, 6.0f);
    float x = c * (1.0f - fabsf(fmodf(h_prime, 2.0f) - 1.0f));
    float m = v - c;
    float r1 = 0, g1 = 0, b1 = 0;

    if (h_prime >= 0 && h_prime < 1) { r1 = c; g1 = x; }
    else if (h_prime >= 1 && h_prime < 2) { r1 = x; g1 = c; }
    else if (h_prime >= 2 && h_prime < 3) { g1 = c; b1 = x; }
    else if (h_prime >= 3 && h_prime < 4) { g1 = x; b1 = c; }
    else if (h_prime >= 4 && h_prime < 5) { r1 = x; b1 = c; }
    else { r1 = c; b1 = x; }

    r = (uint8_t)((r1 + m) * 255.0f);
    g = (uint8_t)((g1 + m) * 255.0f);
    b = (uint8_t)((b1 + m) * 255.0f);
}

Game006Stack::Game006Stack()
    : state_(STATE_TITLE),
      current_row_(14),
      active_x_(0.0f),
      active_w_(9.0f),
      active_vx_(7.0f),
      layer_count_(1),
      score_(0),
      high_score_(0),
      perfect_combo_(0),
      perfect_flash_(0.0f),
      state_timer_(0.0f) {
    for (int i = 0; i < kMaxDebris; ++i) {
        debris_[i].active = false;
    }
}

void Game006Stack::GetLayerColor(int layer_idx, uint8_t& r, uint8_t& g, uint8_t& b) {
    // 随层数循环流动色环：每层色相步进 14 度
    float hue = fmodf(layer_idx * 14.0f, 360.0f);
    HsvToRgb(hue, 0.85f, 0.95f, r, g, b);
}

void Game006Stack::Init() {
    Reset();
}

void Game006Stack::Reset() {
    state_ = STATE_PLAYING;
    score_ = 0;
    perfect_combo_ = 0;
    perfect_flash_ = 0.0f;
    state_timer_ = 0.0f;
    current_row_ = 14;

    // 清空坠落碎片
    for (int i = 0; i < kMaxDebris; ++i) {
        debris_[i].active = false;
    }

    // 初始化底部第 0 层基座 (y = 15，宽度 9，居中放置在 x = 3.5)
    layer_count_ = 1;
    layers_[0].x = 3.5f;
    layers_[0].w = 9.0f;
    GetLayerColor(0, layers_[0].r, layers_[0].g, layers_[0].b);

    // 活动方块初始化 (从最左端平移入场)
    active_x_ = 0.0f;
    active_w_ = 9.0f;
    active_vx_ = 7.5f;
}

void Game006Stack::PlaceBlock() {
    // 基座层为当前层正下方的一层
    int base_idx = layer_count_ - 1;
    float base_x = layers_[base_idx].x;
    float base_w = layers_[base_idx].w;

    float act_left = active_x_;
    float act_right = active_x_ + active_w_;
    float base_left = base_x;
    float base_right = base_x + base_w;

    // 1. 完美吸附判定 (当偏差小于 0.4 像素时判定为完美叠合)
    if (fabsf(act_left - base_left) < 0.42f) {
        active_x_ = base_x;
        perfect_combo_++;
        perfect_flash_ = 0.2f;

        // 连击奖励：连续 3 次完美对齐，方块略微恢复加宽 1 像素 (最大不超过初始 9)
        if (perfect_combo_ >= 3 && active_w_ < 9.0f) {
            active_w_ += 1.0f;
            if (active_x_ > 0.0f) active_x_ -= 0.5f;
        }
    } else {
        perfect_combo_ = 0;

        // 2. 切除计算
        float overlap_left = (act_left > base_left) ? act_left : base_left;
        float overlap_right = (act_right < base_right) ? act_right : base_right;
        float overlap_w = overlap_right - overlap_left;

        // 完全悬空未命中基座 -> 游戏结束
        if (overlap_w <= 0.0f) {
            state_ = STATE_GAMEOVER;
            state_timer_ = 0.0f;

            // 整个活动方块作为碎片坠落
            for (int i = 0; i < kMaxDebris; ++i) {
                if (!debris_[i].active) {
                    debris_[i].x = active_x_;
                    debris_[i].y = (float)current_row_;
                    debris_[i].w = active_w_;
                    debris_[i].vy = 2.0f;
                    GetLayerColor(layer_count_, debris_[i].r, debris_[i].g, debris_[i].b);
                    debris_[i].active = true;
                    break;
                }
            }
            return;
        }

        // 生成被切除悬空碎片的掉落
        float cut_x = 0.0f;
        float cut_w = 0.0f;
        if (act_left < base_left) {
            // 切除左侧多余部分
            cut_x = act_left;
            cut_w = base_left - act_left;
        } else if (act_right > base_right) {
            // 切除右侧多余部分
            cut_x = base_right;
            cut_w = act_right - base_right;
        }

        if (cut_w > 0.0f) {
            for (int i = 0; i < kMaxDebris; ++i) {
                if (!debris_[i].active) {
                    debris_[i].x = cut_x;
                    debris_[i].y = (float)current_row_;
                    debris_[i].w = cut_w;
                    debris_[i].vy = 1.5f;
                    GetLayerColor(layer_count_, debris_[i].r, debris_[i].g, debris_[i].b);
                    debris_[i].active = true;
                    break;
                }
            }
        }

        // 留下重叠部分成为新层基座
        active_x_ = overlap_left;
        active_w_ = overlap_w;
    }

    // 成功安置新层
    score_++;
    if (score_ > high_score_) high_score_ = score_;

    // 记录到层数组
    int new_idx = layer_count_;
    if (new_idx >= kMaxVisibleLayers) new_idx = kMaxVisibleLayers - 1;

    layers_[new_idx].x = active_x_;
    layers_[new_idx].w = active_w_;
    GetLayerColor(layer_count_, layers_[new_idx].r, layers_[new_idx].g, layers_[new_idx].b);
    layer_count_++;

    // 摄像机/画幅向下卷轴：当堆叠高度超过屏幕第 5 行 (y < 5) 时，全局下沉 1 格
    if (current_row_ > 5) {
        current_row_--;
    } else {
        // 下沉一层以腾出顶部空间
        for (int i = 0; i < layer_count_ - 1; ++i) {
            layers_[i] = layers_[i + 1];
        }
        layer_count_--;
    }

    // 准备下一个从对面飞来的活动方块
    active_vx_ = (active_vx_ > 0.0f) ? -(7.5f + score_ * 0.15f) : (7.5f + score_ * 0.15f);
    if (active_vx_ > 14.0f) active_vx_ = 14.0f;
    if (active_vx_ < -14.0f) active_vx_ = -14.0f;

    active_x_ = (active_vx_ > 0.0f) ? -active_w_ : 16.0f;
}

void Game006Stack::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt > 0.05f) dt = 0.05f;
    state_timer_ += dt;

    if (perfect_flash_ > 0.0f) {
        perfect_flash_ -= dt;
        if (perfect_flash_ < 0.0f) perfect_flash_ = 0.0f;
    }

    // 碎片重力掉落更新
    for (int i = 0; i < kMaxDebris; ++i) {
        if (debris_[i].active) {
            debris_[i].vy += 32.0f * dt;
            debris_[i].y += debris_[i].vy * dt;
            if (debris_[i].y > 16.5f) {
                debris_[i].active = false;
            }
        }
    }

    if (state_ == STATE_TITLE) {
        // 标题画面演示流动方块
        active_x_ += 7.0f * dt;
        if (active_x_ > 16.0f) active_x_ = -6.0f;
        if (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN)) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_GAMEOVER) {
        if (state_timer_ > 0.4f && (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_SELECT))) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_PAUSED) {
        if (keys_pressed & KEY_START) {
            state_ = STATE_PLAYING;
        }
        return;
    }

    if (state_ == STATE_PLAYING) {
        // 暂停判断
        if (keys_pressed & KEY_START) {
            state_ = STATE_PAUSED;
            return;
        }

        // 单键轻触放置方块：任何动作键按下均触发放置
        const uint16_t tap_mask = KEY_A | KEY_UP | KEY_B | KEY_DOWN | KEY_LEFT | KEY_RIGHT | KEY_SELECT;
        if (keys_pressed & tap_mask) {
            PlaceBlock();
            return;
        }

        // 活动方块左右往返巡逻
        active_x_ += active_vx_ * dt;
        if (active_vx_ > 0.0f && active_x_ > 16.0f) {
            active_vx_ = -active_vx_;
            active_x_ = 16.0f;
        } else if (active_vx_ < 0.0f && active_x_ + active_w_ < 0.0f) {
            active_vx_ = -active_vx_;
            active_x_ = -active_w_;
        }
    }
}

void Game006Stack::Render(uint8_t* fb_rgb24) {
    // 1. 深邃雅致黑灰背景 (带有微微渐变与完美对齐闪白)
    uint8_t bg_flash = (uint8_t)(perfect_flash_ * 180.0f);
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            fb_rgb24[idx + 0] = 12 + bg_flash;
            fb_rgb24[idx + 1] = 15 + bg_flash;
            fb_rgb24[idx + 2] = 22 + bg_flash;
        }
    }

    // 2. 绘制已稳定堆叠的历史基座层
    // 屏幕行号与层对应的关系：最底下一层为 y = 15，往上依次 y = 15 - i
    for (int i = 0; i < layer_count_; ++i) {
        int row = 15 - i;
        if (row < 0 || row >= 16) continue;

        int start_x = (int)roundf(layers_[i].x);
        int end_x = (int)roundf(layers_[i].x + layers_[i].w);

        for (int x = start_x; x < end_x; ++x) {
            if (x >= 0 && x < 16) {
                int idx = (row * 16 + x) * 3;
                fb_rgb24[idx + 0] = layers_[i].r;
                fb_rgb24[idx + 1] = layers_[i].g;
                fb_rgb24[idx + 2] = layers_[i].b;
            }
        }
    }

    // 3. 绘制正在平移中的活动方块 (位于 current_row_)
    if (state_ == STATE_PLAYING || state_ == STATE_TITLE) {
        uint8_t ar, ag, ab;
        GetLayerColor(score_ + 1, ar, ag, ab);

        int row = current_row_;
        if (row >= 0 && row < 16) {
            int start_x = (int)roundf(active_x_);
            int end_x = (int)roundf(active_x_ + active_w_);

            for (int x = start_x; x < end_x; ++x) {
                if (x >= 0 && x < 16) {
                    int idx = (row * 16 + x) * 3;
                    fb_rgb24[idx + 0] = ar;
                    fb_rgb24[idx + 1] = ag;
                    fb_rgb24[idx + 2] = ab;
                }
            }
        }
    }

    // 4. 绘制受重力下落的切除多余碎片
    for (int i = 0; i < kMaxDebris; ++i) {
        if (debris_[i].active) {
            int dy = (int)roundf(debris_[i].y);
            if (dy >= 0 && dy < 16) {
                int start_x = (int)roundf(debris_[i].x);
                int end_x = (int)roundf(debris_[i].x + debris_[i].w);
                for (int x = start_x; x < end_x; ++x) {
                    if (x >= 0 && x < 16) {
                        int idx = (dy * 16 + x) * 3;
                        // 略微半透明变暗
                        fb_rgb24[idx + 0] = debris_[i].r >> 1;
                        fb_rgb24[idx + 1] = debris_[i].g >> 1;
                        fb_rgb24[idx + 2] = debris_[i].b >> 1;
                    }
                }
            }
        }
    }

    // 5. 游戏结束或暂停特效
    if (state_ == STATE_GAMEOVER) {
        // 全屏边缘红光示警
        for (int x = 0; x < 16; ++x) {
            int top = (0 * 16 + x) * 3;
            int bot = (15 * 16 + x) * 3;
            fb_rgb24[top + 0] = 231; fb_rgb24[top + 1] = 76; fb_rgb24[top + 2] = 60;
            fb_rgb24[bot + 0] = 231; fb_rgb24[bot + 1] = 76; fb_rgb24[bot + 2] = 60;
        }
    } else if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            int idx1 = (y * 16 + 6) * 3;
            int idx2 = (y * 16 + 9) * 3;
            fb_rgb24[idx1 + 0] = fb_rgb24[idx1 + 1] = fb_rgb24[idx1 + 2] = 245;
            fb_rgb24[idx2 + 0] = fb_rgb24[idx2 + 1] = fb_rgb24[idx2 + 2] = 245;
        }
    }
}

CartridgeStatus Game006Stack::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.lives = (state_ == STATE_GAMEOVER) ? 0 : 1;
    st.state = (uint8_t)state_;
    st.progress = (uint8_t)(score_ > 255 ? 255 : score_);
    return st;
}

} // namespace arcade

