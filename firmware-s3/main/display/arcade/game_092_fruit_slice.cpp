// game_092_fruit_slice.cpp —— 目标 #092 水果忍者 (Fruit Ninja) 核心实现
#include "game_092_fruit_slice.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>
#include <math.h>

namespace arcade {

static inline void SetPx092(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

Game092FruitSlice::Game092FruitSlice()
    : state_(STATE_TITLE),
      score_(0),
      high_score_(0),
      lives_(3),
      fruits_sliced_(0),
      rng_seed_(0x2010F92Au),
      state_timer_(0.0f),
      anim_timer_(0.0f),
      spawn_timer_(0.25f),
      blade_x_(7.5f),
      blade_y_(8.0f),
      slash_timer_(0.0f),
      slash_x0_(2.5f),
      slash_y0_(8.0f),
      slash_x1_(12.5f),
      slash_y1_(8.0f),
      last_combo_(0),
      exploded_(false) {
    memset(items_, 0, sizeof(items_));
    memset(drops_, 0, sizeof(drops_));
}

uint32_t Game092FruitSlice::NextRand() {
    rng_seed_ = rng_seed_ * 1103515245u + 12345u;
    return (rng_seed_ >> 16) & 0x7FFFu;
}

void Game092FruitSlice::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

void Game092FruitSlice::SetupMatch() {
    score_ = 0;
    lives_ = 3;
    fruits_sliced_ = 0;
    rng_seed_ = 0x2010F92Au;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    spawn_timer_ = 0.20f;
    blade_x_ = 7.5f;
    blade_y_ = 8.0f;
    slash_timer_ = 0.0f;
    last_combo_ = 0;
    exploded_ = false;
    for (int i = 0; i < kMaxItems; ++i) items_[i].active = false;
    for (int i = 0; i < kMaxDrops; ++i) drops_[i].active = false;
}

void Game092FruitSlice::Init() {
    Reset();
}

void Game092FruitSlice::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    state_ = STATE_TITLE;
    SetupMatch();
}

void Game092FruitSlice::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        SetupMatch();
        state_ = STATE_PLAYING;
        SpawnWave();
    }
}

void Game092FruitSlice::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game092FruitSlice::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

void Game092FruitSlice::SpawnWave() {
    int count = 1 + (int)(NextRand() % 3u);
    bool spawned_bomb = false;
    for (int n = 0; n < count; ++n) {
        int slot = -1;
        for (int i = 0; i < kMaxItems; ++i) {
            if (!items_[i].active) {
                slot = i;
                break;
            }
        }
        if (slot < 0) break;

        uint32_t r1 = NextRand();
        uint32_t r2 = NextRand();
        uint32_t r3 = NextRand();

        float start_x = 2.0f + (float)(r1 % 11u);
        bool make_bomb = (!spawned_bomb && count >= 2 && (r2 % 5u == 0u));
        if (make_bomb) spawned_bomb = true;

        items_[slot].active = true;
        items_[slot].is_bomb = make_bomb;
        items_[slot].kind = (uint8_t)(r3 % 4u);
        items_[slot].x = start_x;
        items_[slot].y = 15.6f;
        items_[slot].vx = (7.0f - start_x) * 0.35f + ((float)((int)(r2 % 5u) - 2) * 0.25f);
        items_[slot].vy = -15.8f - (float)(r1 % 35u) * 0.1f;
    }
}

void Game092FruitSlice::SpawnJuice(float cx, float cy, uint8_t kind, bool explosion) {
    uint8_t r = 240, g = 60, b = 70;
    if (explosion) {
        r = 255; g = 90; b = 30;
    } else if (kind == 0) {
        r = 245; g = 55; b = 65;   // Watermelon crimson juice
    } else if (kind == 1) {
        r = 255; g = 150; b = 25;  // Orange juice
    } else if (kind == 2) {
        r = 255; g = 235; b = 45;  // Banana splash
    } else {
        r = 80; g = 145; b = 255;  // Berry splash
    }

    int burst = explosion ? 8 : 4;
    for (int k = 0; k < burst; ++k) {
        int slot = -1;
        for (int i = 0; i < kMaxDrops; ++i) {
            if (!drops_[i].active) {
                slot = i;
                break;
            }
        }
        if (slot < 0) break;
        float ang = (float)k * (6.2831853f / (float)burst) + 0.35f;
        float spd = explosion ? 9.5f : 5.5f;
        drops_[slot].active = true;
        drops_[slot].x = cx;
        drops_[slot].y = cy;
        drops_[slot].vx = cosf(ang) * spd;
        drops_[slot].vy = sinf(ang) * spd - 2.0f;
        drops_[slot].life = explosion ? 0.55f : 0.42f;
        if (explosion && (k & 1)) {
            drops_[slot].r = 255; drops_[slot].g = 245; drops_[slot].b = 200;
        } else {
            drops_[slot].r = r; drops_[slot].g = g; drops_[slot].b = b;
        }
    }
}

void Game092FruitSlice::PerformSlash(uint16_t keys_down, uint16_t keys_pressed) {
    uint16_t dir_mask = keys_down | keys_pressed;
    float dx = 0.0f;
    float dy = 0.0f;
    if (dir_mask & KEY_LEFT) dx -= 1.0f;
    if (dir_mask & KEY_RIGHT) dx += 1.0f;
    if (dir_mask & KEY_UP) dy -= 1.0f;
    if (dir_mask & KEY_DOWN) dy += 1.0f;

    if (dx == 0.0f && dy == 0.0f) {
        if (keys_pressed & KEY_B) {
            dx = 0.70710678f;
            dy = -0.70710678f;
        } else {
            dx = 1.0f;
            dy = 0.0f;
        }
    } else {
        float inv = 1.0f / sqrtf(dx * dx + dy * dy);
        dx *= inv;
        dy *= inv;
    }

    slash_x0_ = blade_x_ - dx * 5.0f;
    slash_y0_ = blade_y_ - dy * 5.0f;
    slash_x1_ = blade_x_ + dx * 5.0f;
    slash_y1_ = blade_y_ + dy * 5.0f;
    slash_timer_ = 0.18f;

    float sx = slash_x1_ - slash_x0_;
    float sy = slash_y1_ - slash_y0_;
    float seg_len_sq = sx * sx + sy * sy;
    if (seg_len_sq < 0.001f) seg_len_sq = 1.0f;

    uint8_t hit_fruits = 0;
    for (int i = 0; i < kMaxItems; ++i) {
        if (!items_[i].active) continue;
        float cx = items_[i].x + 1.0f;
        float cy = items_[i].y + 1.0f;
        float t = ((cx - slash_x0_) * sx + (cy - slash_y0_) * sy) / seg_len_sq;
        if (t < 0.0f) t = 0.0f;
        if (t > 1.0f) t = 1.0f;
        float qx = slash_x0_ + t * sx;
        float qy = slash_y0_ + t * sy;
        float dist = hypotf(cx - qx, cy - qy);
        if (dist <= 1.65f) {
            if (items_[i].is_bomb) {
                items_[i].active = false;
                exploded_ = true;
                lives_ = 0;
                SpawnJuice(cx, cy, 0, true);
                state_ = STATE_GAMEOVER;
                state_timer_ = 0.0f;
                return;
            } else {
                items_[i].active = false;
                hit_fruits++;
                fruits_sliced_++;
                SpawnJuice(cx, cy, items_[i].kind, false);
            }
        }
    }

    last_combo_ = hit_fruits;
    if (hit_fruits > 0) {
        uint32_t pts = (uint32_t)hit_fruits * 10u;
        if (hit_fruits >= 2) {
            pts += (uint32_t)hit_fruits * 20u;
        }
        AddScore(pts);
        if (fruits_sliced_ >= 40) {
            AddScore(100);
            state_ = STATE_VICTORY;
            state_timer_ = 0.0f;
        }
    }
}

void Game092FruitSlice::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt < 0.0f) dt = 0.0f;
    if (dt > 0.05f) dt = 0.05f;
    state_timer_ += dt;
    anim_timer_ += dt;

    if (state_ == STATE_TITLE) {
        blade_x_ = 7.5f + cosf(anim_timer_ * 2.5f) * 3.0f;
        blade_y_ = 8.0f + sinf(anim_timer_ * 3.5f) * 2.0f;
        if (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)) {
            Start();
        }
        return;
    }

    if (state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        for (int i = 0; i < kMaxDrops; ++i) {
            if (!drops_[i].active) continue;
            drops_[i].vy += 16.0f * dt;
            drops_[i].x += drops_[i].vx * dt;
            drops_[i].y += drops_[i].vy * dt;
            drops_[i].life -= dt;
            if (drops_[i].life <= 0.0f) drops_[i].active = false;
        }
        if (state_timer_ > 0.5f && (keys_pressed & (KEY_START | KEY_A | KEY_B))) {
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

        const float blade_speed = 14.0f;
        if (keys_down & KEY_LEFT) blade_x_ -= blade_speed * dt;
        if (keys_down & KEY_RIGHT) blade_x_ += blade_speed * dt;
        if (keys_down & KEY_UP) blade_y_ -= blade_speed * dt;
        if (keys_down & KEY_DOWN) blade_y_ += blade_speed * dt;
        if (blade_x_ < 1.0f) blade_x_ = 1.0f;
        if (blade_x_ > 14.0f) blade_x_ = 14.0f;
        if (blade_y_ < 1.5f) blade_y_ = 1.5f;
        if (blade_y_ > 14.5f) blade_y_ = 14.5f;

        if (slash_timer_ > 0.0f) {
            slash_timer_ -= dt;
            if (slash_timer_ < 0.0f) slash_timer_ = 0.0f;
        }

        if (keys_pressed & (KEY_A | KEY_B)) {
            PerformSlash(keys_down, keys_pressed);
            if (state_ != STATE_PLAYING) return;
        }

        spawn_timer_ -= dt;
        if (spawn_timer_ <= 0.0f) {
            SpawnWave();
            float interval = 1.15f - (float)fruits_sliced_ * 0.01f;
            if (interval < 0.65f) interval = 0.65f;
            spawn_timer_ = interval;
        }

        const float gravity = 16.0f;
        for (int i = 0; i < kMaxItems; ++i) {
            if (!items_[i].active) continue;
            items_[i].vy += gravity * dt;
            items_[i].x += items_[i].vx * dt;
            items_[i].y += items_[i].vy * dt;

            if (items_[i].x < 0.5f) {
                items_[i].x = 0.5f;
                items_[i].vx = fabsf(items_[i].vx);
            } else if (items_[i].x > 13.5f) {
                items_[i].x = 13.5f;
                items_[i].vx = -fabsf(items_[i].vx);
            }

            if (items_[i].vy > 0.0f && items_[i].y > 16.2f) {
                bool was_bomb = items_[i].is_bomb;
                items_[i].active = false;
                if (!was_bomb) {
                    if (lives_ > 1) {
                        lives_--;
                    } else {
                        lives_ = 0;
                        state_ = STATE_GAMEOVER;
                        state_timer_ = 0.0f;
                        return;
                    }
                }
            }
        }

        for (int i = 0; i < kMaxDrops; ++i) {
            if (!drops_[i].active) continue;
            drops_[i].vy += 18.0f * dt;
            drops_[i].x += drops_[i].vx * dt;
            drops_[i].y += drops_[i].vy * dt;
            drops_[i].life -= dt;
            if (drops_[i].life <= 0.0f) drops_[i].active = false;
        }
    }
}

void Game092FruitSlice::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    // Wooden dojo backdrop
    for (int y = 0; y < 16; ++y) {
        uint8_t r = (y % 4 == 0) ? 30 : 22;
        uint8_t g = (y % 4 == 0) ? 19 : 13;
        uint8_t b = (y % 4 == 0) ? 11 : 8;
        for (int x = 0; x < 16; ++x) {
            SetPx092(fb_rgb24, x, y, r, g, b);
        }
    }

    // Bomb explosion flash during early GAMEOVER
    if (state_ == STATE_GAMEOVER && exploded_ && state_timer_ < 0.45f) {
        for (int y = 0; y < 16; ++y) {
            for (int x = 0; x < 16; ++x) {
                if (((x + y) & 1) == 0) {
                    SetPx092(fb_rgb24, x, y, 255, 70, 50);
                } else {
                    SetPx092(fb_rgb24, x, y, 255, 220, 180);
                }
            }
        }
    }

    if (state_ == STATE_TITLE) {
        // Decorative watermelon & katana slash on title screen
        SetPx092(fb_rgb24, 4, 6, 240, 50, 60);
        SetPx092(fb_rgb24, 5, 6, 240, 50, 60);
        SetPx092(fb_rgb24, 4, 7, 40, 200, 70);
        SetPx092(fb_rgb24, 5, 7, 40, 200, 70);

        SetPx092(fb_rgb24, 10, 5, 255, 150, 25);
        SetPx092(fb_rgb24, 11, 5, 255, 200, 60);
        SetPx092(fb_rgb24, 10, 6, 255, 140, 20);
        SetPx092(fb_rgb24, 11, 6, 255, 150, 25);

        for (int s = -4; s <= 4; ++s) {
            SetPx092(fb_rgb24, 8 + s, 8 - s / 2, 190, 250, 255);
        }
    }

    // Juice particles
    for (int i = 0; i < kMaxDrops; ++i) {
        if (!drops_[i].active) continue;
        SetPx092(fb_rgb24, (int)roundf(drops_[i].x), (int)roundf(drops_[i].y),
                 drops_[i].r, drops_[i].g, drops_[i].b);
    }

    // Tossed 2x2 fruits & bombs
    bool pulse = (((int)(anim_timer_ * 10.0f)) & 1) != 0;
    for (int i = 0; i < kMaxItems; ++i) {
        if (!items_[i].active) continue;
        int ix = (int)roundf(items_[i].x);
        int iy = (int)roundf(items_[i].y);
        if (items_[i].is_bomb) {
            uint8_t br = pulse ? 210 : 55;
            uint8_t bg = pulse ? 30 : 20;
            uint8_t bb = pulse ? 35 : 28;
            SetPx092(fb_rgb24, ix, iy, br, bg, bb);
            SetPx092(fb_rgb24, ix + 1, iy, 40, 15, 20);
            SetPx092(fb_rgb24, ix, iy + 1, 40, 15, 20);
            SetPx092(fb_rgb24, ix + 1, iy + 1, br, bg, bb);
            // Blinking fuse spark above bomb
            if (pulse) {
                SetPx092(fb_rgb24, ix + 1, iy - 1, 255, 245, 90);
            } else {
                SetPx092(fb_rgb24, ix + 1, iy - 1, 255, 120, 20);
            }
        } else if (items_[i].kind == 0) {
            // Watermelon: red flesh top, green rind bottom
            SetPx092(fb_rgb24, ix, iy, 245, 50, 65);
            SetPx092(fb_rgb24, ix + 1, iy, 245, 50, 65);
            SetPx092(fb_rgb24, ix, iy + 1, 40, 205, 70);
            SetPx092(fb_rgb24, ix + 1, iy + 1, 40, 205, 70);
        } else if (items_[i].kind == 1) {
            // Orange
            SetPx092(fb_rgb24, ix, iy, 255, 195, 65);
            SetPx092(fb_rgb24, ix + 1, iy, 255, 145, 20);
            SetPx092(fb_rgb24, ix, iy + 1, 255, 145, 20);
            SetPx092(fb_rgb24, ix + 1, iy + 1, 225, 110, 10);
        } else if (items_[i].kind == 2) {
            // Banana
            SetPx092(fb_rgb24, ix, iy, 255, 240, 55);
            SetPx092(fb_rgb24, ix + 1, iy, 255, 230, 35);
            SetPx092(fb_rgb24, ix, iy + 1, 235, 195, 20);
            SetPx092(fb_rgb24, ix + 1, iy + 1, 255, 240, 55);
        } else {
            // Berry
            SetPx092(fb_rgb24, ix, iy, 150, 205, 255);
            SetPx092(fb_rgb24, ix + 1, iy, 65, 130, 255);
            SetPx092(fb_rgb24, ix, iy + 1, 65, 130, 255);
            SetPx092(fb_rgb24, ix + 1, iy + 1, 45, 95, 220);
        }
    }

    // Active 10-pixel katana slash stroke
    if (slash_timer_ > 0.0f) {
        bool blitz = (last_combo_ >= 2);
        for (int step = 0; step <= 10; ++step) {
            float t = (float)step / 10.0f;
            int sx = (int)roundf(slash_x0_ + (slash_x1_ - slash_x0_) * t);
            int sy = (int)roundf(slash_y0_ + (slash_y1_ - slash_y0_) * t);
            if (blitz) {
                SetPx092(fb_rgb24, sx, sy, 255, 245, 130);
            } else if (step >= 3 && step <= 7) {
                SetPx092(fb_rgb24, sx, sy, 255, 255, 255);
            } else {
                SetPx092(fb_rgb24, sx, sy, 110, 245, 255);
            }
        }
    }

    // Katana cursor locus
    int bx = (int)roundf(blade_x_);
    int by = (int)roundf(blade_y_);
    SetPx092(fb_rgb24, bx, by, 180, 250, 255);

    // Lives HUD at top right
    for (int i = 0; i < (int)lives_ && i < 3; ++i) {
        SetPx092(fb_rgb24, 15 - i * 2, 0, 46, 215, 95);
    }

    if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPx092(fb_rgb24, 6, y, 250, 250, 250);
            SetPx092(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game092FruitSlice::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = lives_;
    st.state = (uint8_t)state_;
    uint32_t prog = ((uint32_t)fruits_sliced_ * 100u) / 40u;
    st.progress = (uint8_t)(prog > 100u ? 100u : prog);
    return st;
}

static_assert(sizeof(Game092FruitSlice) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
