// game_010_stack.cpp —— 目标 #010 堆叠大师 16 核心实现
#include "game_010_stack.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>
#include <math.h>

namespace arcade {

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

Game010Stack::Game010Stack()
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
      state_timer_(0.0f),
      anim_timer_(0.0f) {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    for (int i = 0; i < kMaxDebris; ++i) {
        debris_[i].active = false;
    }
}

void Game010Stack::GetLayerColor(int layer_idx, uint8_t& r, uint8_t& g, uint8_t& b) {
    float hue = fmodf(layer_idx * 14.0f, 360.0f);
    HsvToRgb(hue, 0.85f, 0.95f, r, g, b);
}

void Game010Stack::Init() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    Reset();
}

void Game010Stack::Reset() {
    state_ = STATE_TITLE;
    score_ = 0;
    perfect_combo_ = 0;
    perfect_flash_ = 0.0f;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    current_row_ = 14;

    for (int i = 0; i < kMaxDebris; ++i) {
        debris_[i].active = false;
    }

    layer_count_ = 1;
    layers_[0].x = 3.5f;
    layers_[0].w = 9.0f;
    GetLayerColor(0, layers_[0].r, layers_[0].g, layers_[0].b);

    active_x_ = 0.0f;
    active_w_ = 9.0f;
    active_vx_ = 7.5f;
}

void Game010Stack::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER) {
        state_ = STATE_PLAYING;
        score_ = 0;
        perfect_combo_ = 0;
        perfect_flash_ = 0.0f;
        state_timer_ = 0.0f;
        anim_timer_ = 0.0f;
        current_row_ = 14;
        layer_count_ = 1;
        layers_[0].x = 3.5f;
        layers_[0].w = 9.0f;
        GetLayerColor(0, layers_[0].r, layers_[0].g, layers_[0].b);
        active_x_ = 0.0f;
        active_w_ = 9.0f;
        active_vx_ = 7.5f;
        for (int i = 0; i < kMaxDebris; ++i) debris_[i].active = false;
    }
}

void Game010Stack::Pause() {
    if (state_ == STATE_PLAYING) state_ = STATE_PAUSED;
}

void Game010Stack::Resume() {
    if (state_ == STATE_PAUSED) state_ = STATE_PLAYING;
}

void Game010Stack::PlaceBlock() {
    int base_idx = layer_count_ - 1;
    float base_x = layers_[base_idx].x;
    float base_w = layers_[base_idx].w;

    float act_left = active_x_;
    float act_right = active_x_ + active_w_;
    float base_left = base_x;
    float base_right = base_x + base_w;

    if (fabsf(act_left - base_left) < 0.42f) {
        active_x_ = base_x;
        perfect_combo_++;
        perfect_flash_ = 0.2f;

        if (perfect_combo_ >= 3 && active_w_ < 9.0f) {
            active_w_ += 1.0f;
            if (active_x_ > 0.0f) active_x_ -= 0.5f;
        }
    } else {
        perfect_combo_ = 0;

        float overlap_left = fmaxf(act_left, base_left);
        float overlap_right = fminf(act_right, base_right);
        float overlap_w = overlap_right - overlap_left;

        if (overlap_w <= 0.3f) {
            state_ = STATE_GAMEOVER;
            state_timer_ = 0.0f;
            if (score_ > high_score_) {
                high_score_ = score_;
                ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
            }
            return;
        }

        float cut_x = 0.0f, cut_w = 0.0f;
        if (act_left < base_left) {
            cut_x = act_left;
            cut_w = base_left - act_left;
        } else {
            cut_x = base_right;
            cut_w = act_right - base_right;
        }

        for (int i = 0; i < kMaxDebris; ++i) {
            if (!debris_[i].active) {
                debris_[i].active = true;
                debris_[i].x = cut_x;
                debris_[i].y = (float)current_row_;
                debris_[i].w = cut_w;
                debris_[i].vy = 2.0f;
                GetLayerColor(layer_count_, debris_[i].r, debris_[i].g, debris_[i].b);
                break;
            }
        }

        active_x_ = overlap_left;
        active_w_ = overlap_w;
    }

    score_++;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }

    if (layer_count_ < kMaxVisibleLayers) {
        int idx = layer_count_;
        layers_[idx].x = active_x_;
        layers_[idx].w = active_w_;
        GetLayerColor(layer_count_, layers_[idx].r, layers_[idx].g, layers_[idx].b);
        layer_count_++;
    } else {
        for (int i = 0; i < kMaxVisibleLayers - 1; ++i) {
            layers_[i] = layers_[i + 1];
        }
        layers_[kMaxVisibleLayers - 1].x = active_x_;
        layers_[kMaxVisibleLayers - 1].w = active_w_;
        GetLayerColor(score_, layers_[kMaxVisibleLayers - 1].r, layers_[kMaxVisibleLayers - 1].g, layers_[kMaxVisibleLayers - 1].b);
    }

    if (current_row_ > 2) {
        current_row_--;
    }

    if (active_vx_ > 0) {
        active_x_ = 16.0f - active_w_;
        active_vx_ = -(7.5f + (float)score_ * 0.28f);
    } else {
        active_x_ = 0.0f;
        active_vx_ = (7.5f + (float)score_ * 0.28f);
    }
    if (fabsf(active_vx_) > 16.0f) active_vx_ = (active_vx_ > 0) ? 16.0f : -16.0f;
}

void Game010Stack::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt > 0.05f) dt = 0.05f;
    state_timer_ += dt;
    anim_timer_ += dt;

    if (perfect_flash_ > 0.0f) {
        perfect_flash_ -= dt;
    }

    for (int i = 0; i < kMaxDebris; ++i) {
        if (debris_[i].active) {
            debris_[i].vy += 30.0f * dt;
            debris_[i].y += debris_[i].vy * dt;
            if (debris_[i].y > 16.0f) {
                debris_[i].active = false;
            }
        }
    }

    if (state_ == STATE_TITLE) {
        active_x_ += active_vx_ * dt;
        if (active_x_ + active_w_ >= 16.0f) {
            active_x_ = 16.0f - active_w_;
            active_vx_ = -fabsf(active_vx_);
        } else if (active_x_ <= 0.0f) {
            active_x_ = 0.0f;
            active_vx_ = fabsf(active_vx_);
        }
        if (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN)) {
            Start();
        }
        return;
    }

    if (state_ == STATE_GAMEOVER) {
        if (state_timer_ > 0.6f && (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP))) {
            Start();
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
        if (keys_pressed & KEY_START) {
            state_ = STATE_PAUSED;
            return;
        }

        active_x_ += active_vx_ * dt;
        if (active_x_ + active_w_ >= 16.0f) {
            active_x_ = 16.0f - active_w_;
            active_vx_ = -fabsf(active_vx_);
        } else if (active_x_ <= 0.0f) {
            active_x_ = 0.0f;
            active_vx_ = fabsf(active_vx_);
        }

        const uint16_t tap_mask = KEY_A | KEY_UP | KEY_B | KEY_SELECT | KEY_LEFT | KEY_RIGHT | KEY_DOWN;
        if (keys_pressed & tap_mask) {
            PlaceBlock();
        }
    }
}

void Game010Stack::Render(uint8_t* fb_rgb24) {
    if (state_ == STATE_GAMEOVER && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, false, score_, high_score_, anim_timer_);
        return;
    }

    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            fb_rgb24[idx + 0] = 12;
            fb_rgb24[idx + 1] = 12;
            fb_rgb24[idx + 2] = 20;
        }
    }

    for (int i = 0; i < layer_count_; ++i) {
        int screen_y = 15 - i;
        if (screen_y < 0) continue;

        int lx1 = (int)roundf(layers_[i].x);
        int lx2 = (int)roundf(layers_[i].x + layers_[i].w);
        if (lx1 < 0) lx1 = 0;
        if (lx2 > 16) lx2 = 16;

        uint8_t r = layers_[i].r;
        uint8_t g = layers_[i].g;
        uint8_t b = layers_[i].b;

        for (int x = lx1; x < lx2; ++x) {
            int idx = (screen_y * 16 + x) * 3;
            fb_rgb24[idx + 0] = r;
            fb_rgb24[idx + 1] = g;
            fb_rgb24[idx + 2] = b;
        }
    }

    if (state_ == STATE_PLAYING || state_ == STATE_TITLE || state_ == STATE_PAUSED) {
        int ax1 = (int)roundf(active_x_);
        int ax2 = (int)roundf(active_x_ + active_w_);
        if (ax1 < 0) ax1 = 0;
        if (ax2 > 16) ax2 = 16;

        uint8_t ar, ag, ab;
        GetLayerColor(layer_count_, ar, ag, ab);

        if (perfect_flash_ > 0.0f) {
            ar = ag = ab = 255;
        }

        for (int x = ax1; x < ax2; ++x) {
            int idx = (current_row_ * 16 + x) * 3;
            fb_rgb24[idx + 0] = ar;
            fb_rgb24[idx + 1] = ag;
            fb_rgb24[idx + 2] = ab;
        }
    }

    for (int i = 0; i < kMaxDebris; ++i) {
        if (debris_[i].active) {
            int dy = (int)roundf(debris_[i].y);
            int dx1 = (int)roundf(debris_[i].x);
            int dx2 = (int)roundf(debris_[i].x + debris_[i].w);
            if (dy >= 0 && dy < 16) {
                if (dx1 < 0) dx1 = 0;
                if (dx2 > 16) dx2 = 16;
                for (int x = dx1; x < dx2; ++x) {
                    int idx = (dy * 16 + x) * 3;
                    fb_rgb24[idx + 0] = debris_[i].r / 2;
                    fb_rgb24[idx + 1] = debris_[i].g / 2;
                    fb_rgb24[idx + 2] = debris_[i].b / 2;
                }
            }
        }
    }

    if (state_ == STATE_PAUSED) {
        for (int y = 6; y <= 9; ++y) {
            int idx1 = (y * 16 + 6) * 3;
            int idx2 = (y * 16 + 9) * 3;
            fb_rgb24[idx1 + 0] = fb_rgb24[idx1 + 1] = fb_rgb24[idx1 + 2] = 250;
            fb_rgb24[idx2 + 0] = fb_rgb24[idx2 + 1] = fb_rgb24[idx2 + 2] = 250;
        }
    }
}

CartridgeStatus Game010Stack::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = (state_ == STATE_GAMEOVER) ? 0 : 1;
    st.state = (uint8_t)state_;
    st.progress = (uint8_t)(score_ > 255 ? 255 : score_);
    return st;
}

} // namespace arcade
