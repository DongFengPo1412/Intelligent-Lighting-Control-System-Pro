// game_083_tower_defense.cpp —— 目标 #083 路径塔防 核心实现
#include "game_083_tower_defense.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>
#include <math.h>

namespace arcade {

static const int kNumWaypoints = 6;
static const int kWaypoints[kNumWaypoints][2] = {
    {0, 2},
    {13, 2},
    {13, 7},
    {2, 7},
    {2, 13},
    {15, 13},
};

static const int kTowerCosts[3] = {25, 35, 45};
static const float kTowerRanges[3] = {3.6f, 3.3f, 3.8f};
static const float kTowerIntervals[3] = {0.40f, 0.65f, 0.95f};
static const float kTowerDamages[3] = {14.0f, 9.0f, 24.0f};

static inline void SetPx83(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

Game083TowerDefense::Game083TowerDefense()
    : state_(STATE_TITLE),
      score_(0),
      high_score_(0),
      state_timer_(0.0f),
      anim_timer_(0.0f),
      gold_(70),
      base_hp_(5),
      wave_(1),
      spawned_in_wave_(0),
      total_in_wave_(4),
      spawn_timer_(0.5f),
      wave_delay_(0.0f),
      cursor_x_(5),
      cursor_y_(4),
      selected_tower_type_(0),
      move_cooldown_(0.0f),
      num_towers_(0) {
    SetupMatch(STATE_TITLE);
}

void Game083TowerDefense::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

bool Game083TowerDefense::IsRoad(int x, int y) const {
    if (y == 2 && x >= 0 && x <= 13) return true;
    if (x == 13 && y >= 2 && y <= 7) return true;
    if (y == 7 && x >= 2 && x <= 13) return true;
    if (x == 2 && y >= 7 && y <= 13) return true;
    if (y == 13 && x >= 2 && x <= 15) return true;
    return false;
}

int Game083TowerDefense::FindTowerAt(int x, int y) const {
    for (int i = 0; i < num_towers_; ++i) {
        if (towers_[i].active && towers_[i].x == x && towers_[i].y == y) {
            return i;
        }
    }
    return -1;
}

void Game083TowerDefense::StartWave(uint8_t w) {
    wave_ = w;
    spawned_in_wave_ = 0;
    if (w == 1) total_in_wave_ = 4;
    else if (w == 2) total_in_wave_ = 6;
    else if (w == 3) total_in_wave_ = 7;
    else total_in_wave_ = 8;
    spawn_timer_ = 0.6f;
    wave_delay_ = 0.0f;
}

void Game083TowerDefense::SetupMatch(CartridgeState new_state) {
    state_ = new_state;
    score_ = 0;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    gold_ = 70;
    base_hp_ = 5;
    cursor_x_ = 5;
    cursor_y_ = 4;
    selected_tower_type_ = 0;
    move_cooldown_ = 0.0f;
    num_towers_ = 0;
    for (int i = 0; i < kMaxTowers; ++i) {
        towers_[i] = {false, 0, 0, 0, 1, 0.0f, 0.0f, 0.0f, 0.0f};
    }
    for (int i = 0; i < kMaxEnemies; ++i) {
        enemies_[i] = {false, 0.0f, 2.0f, 1, 0.0f, 1.0f, 0.0f, 0.0f, 0, false};
    }
    StartWave(1);
}

void Game083TowerDefense::Init() {
    Reset();
}

void Game083TowerDefense::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    SetupMatch(STATE_TITLE);
}

void Game083TowerDefense::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        SetupMatch(STATE_PLAYING);
    }
}

void Game083TowerDefense::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game083TowerDefense::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

void Game083TowerDefense::SpawnEnemy() {
    for (int i = 0; i < kMaxEnemies; ++i) {
        if (!enemies_[i].alive) {
            bool boss = (wave_ == 4 && spawned_in_wave_ == total_in_wave_ - 1);
            float base_hp = 28.0f;
            float spd = 2.6f;
            uint8_t rew = 12;
            if (wave_ == 2) { base_hp = 42.0f; spd = 3.0f; rew = 14; }
            else if (wave_ == 3) { base_hp = 60.0f; spd = 3.3f; rew = 16; }
            else if (wave_ >= 4) { base_hp = 80.0f; spd = 3.5f; rew = 20; }
            if (boss) {
                base_hp = 160.0f;
                spd = 2.4f;
                rew = 35;
            }
            enemies_[i].alive = true;
            enemies_[i].x = (float)kWaypoints[0][0];
            enemies_[i].y = (float)kWaypoints[0][1];
            enemies_[i].wp_idx = 1;
            enemies_[i].hp = base_hp;
            enemies_[i].max_hp = base_hp;
            enemies_[i].speed = spd;
            enemies_[i].slow_timer = 0.0f;
            enemies_[i].reward = rew;
            enemies_[i].is_boss = boss;
            spawned_in_wave_++;
            return;
        }
    }
}

void Game083TowerDefense::HandleBuildOrUpgrade() {
    if (cursor_y_ < 1 || IsRoad(cursor_x_, cursor_y_)) {
        return;
    }
    int idx = FindTowerAt(cursor_x_, cursor_y_);
    if (idx >= 0) {
        if (towers_[idx].level < 3) {
            int upg_cost = 20 * (int)towers_[idx].level;
            if (gold_ >= upg_cost) {
                gold_ -= upg_cost;
                towers_[idx].level++;
            }
        }
    } else if (num_towers_ < kMaxTowers) {
        int cost = kTowerCosts[selected_tower_type_];
        if (gold_ >= cost) {
            gold_ -= cost;
            towers_[num_towers_] = {
                true,
                cursor_x_,
                cursor_y_,
                selected_tower_type_,
                1,
                0.0f,
                0.0f,
                (float)cursor_x_,
                (float)cursor_y_
            };
            num_towers_++;
        }
    }
}

void Game083TowerDefense::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt > 0.05f) dt = 0.05f;

    if (state_ == STATE_PAUSED) {
        if (keys_pressed & KEY_START) {
            state_ = STATE_PLAYING;
        }
        return;
    }

    state_timer_ += dt;
    anim_timer_ += dt;

    if (state_ == STATE_TITLE) {
        if (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)) {
            Start();
        }
        return;
    }

    if (state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        if (state_timer_ > 0.5f && (keys_pressed & (KEY_START | KEY_A | KEY_B))) {
            Start();
        }
        return;
    }

    if (keys_pressed & KEY_START) {
        state_ = STATE_PAUSED;
        return;
    }

    // Cursor movement
    if (move_cooldown_ > 0.0f) {
        move_cooldown_ -= dt;
    }
    uint16_t dpad_trigger = keys_pressed & (KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN);
    if (!dpad_trigger && move_cooldown_ <= 0.0f && (keys_down & (KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN))) {
        dpad_trigger = keys_down & (KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN);
        move_cooldown_ = 0.14f;
    } else if (dpad_trigger) {
        move_cooldown_ = 0.18f;
    }

    if (dpad_trigger & KEY_LEFT) {
        if (cursor_x_ > 0) cursor_x_--;
    } else if (dpad_trigger & KEY_RIGHT) {
        if (cursor_x_ < 15) cursor_x_++;
    } else if (dpad_trigger & KEY_UP) {
        if (cursor_y_ > 1) cursor_y_--;
    } else if (dpad_trigger & KEY_DOWN) {
        if (cursor_y_ < 15) cursor_y_++;
    }

    if (keys_pressed & KEY_B) {
        selected_tower_type_ = (uint8_t)((selected_tower_type_ + 1) % 3);
    }
    if (keys_pressed & KEY_A) {
        HandleBuildOrUpgrade();
    }

    // Wave spawning
    if (spawned_in_wave_ < total_in_wave_) {
        spawn_timer_ -= dt;
        if (spawn_timer_ <= 0.0f) {
            SpawnEnemy();
            float interval = 1.10f - (float)(wave_ - 1) * 0.10f;
            if (interval < 0.75f) interval = 0.75f;
            spawn_timer_ = interval;
        }
    }

    // Update enemies
    for (int i = 0; i < kMaxEnemies; ++i) {
        if (!enemies_[i].alive) continue;
        if (enemies_[i].slow_timer > 0.0f) {
            enemies_[i].slow_timer -= dt;
            if (enemies_[i].slow_timer < 0.0f) enemies_[i].slow_timer = 0.0f;
        }
        float spd = enemies_[i].speed * ((enemies_[i].slow_timer > 0.0f) ? 0.5f : 1.0f);
        float move_rem = spd * dt;

        while (move_rem > 0.0f && enemies_[i].wp_idx < kNumWaypoints) {
            float tx = (float)kWaypoints[enemies_[i].wp_idx][0];
            float ty = (float)kWaypoints[enemies_[i].wp_idx][1];
            float dx = tx - enemies_[i].x;
            float dy = ty - enemies_[i].y;
            float dist = sqrtf(dx * dx + dy * dy);
            if (dist <= move_rem) {
                enemies_[i].x = tx;
                enemies_[i].y = ty;
                move_rem -= dist;
                enemies_[i].wp_idx++;
            } else {
                enemies_[i].x += (dx / dist) * move_rem;
                enemies_[i].y += (dy / dist) * move_rem;
                move_rem = 0.0f;
            }
        }

        if (enemies_[i].wp_idx >= kNumWaypoints) {
            enemies_[i].alive = false;
            if (base_hp_ > 1) {
                base_hp_--;
            } else {
                base_hp_ = 0;
                state_ = STATE_GAMEOVER;
                state_timer_ = 0.0f;
                return;
            }
        }
    }

    // Update towers & firing
    for (int t = 0; t < num_towers_; ++t) {
        if (!towers_[t].active) continue;
        if (towers_[t].beam_timer > 0.0f) {
            towers_[t].beam_timer -= dt;
        }
        if (towers_[t].cooldown > 0.0f) {
            towers_[t].cooldown -= dt;
        }
        if (towers_[t].cooldown > 0.0f) continue;

        float range = kTowerRanges[towers_[t].type] + (float)(towers_[t].level - 1) * 0.4f;
        int best_e = -1;
        float best_prog = -1.0f;
        for (int e = 0; e < kMaxEnemies; ++e) {
            if (!enemies_[e].alive) continue;
            float dx = enemies_[e].x - (float)towers_[t].x;
            float dy = enemies_[e].y - (float)towers_[t].y;
            if (dx * dx + dy * dy <= range * range) {
                float prog = (float)enemies_[e].wp_idx * 20.0f;
                if (enemies_[e].wp_idx < kNumWaypoints) {
                    float wx = (float)kWaypoints[enemies_[e].wp_idx][0] - enemies_[e].x;
                    float wy = (float)kWaypoints[enemies_[e].wp_idx][1] - enemies_[e].y;
                    prog -= sqrtf(wx * wx + wy * wy);
                }
                if (prog > best_prog) {
                    best_prog = prog;
                    best_e = e;
                }
            }
        }

        if (best_e >= 0) {
            float dmg_mult = 1.0f + 0.5f * (float)(towers_[t].level - 1);
            float dmg = kTowerDamages[towers_[t].type] * dmg_mult;
            float cd = kTowerIntervals[towers_[t].type] * (1.0f - 0.12f * (float)(towers_[t].level - 1));
            towers_[t].cooldown = cd;
            towers_[t].beam_timer = 0.14f;
            towers_[t].target_x = enemies_[best_e].x;
            towers_[t].target_y = enemies_[best_e].y;

            if (towers_[t].type == 1) {
                // Frost slow
                enemies_[best_e].slow_timer = 2.0f;
            }

            if (towers_[t].type == 2) {
                // Cannon AoE splash
                float cx = enemies_[best_e].x;
                float cy = enemies_[best_e].y;
                for (int e = 0; e < kMaxEnemies; ++e) {
                    if (!enemies_[e].alive) continue;
                    float sx = enemies_[e].x - cx;
                    float sy = enemies_[e].y - cy;
                    if (e == best_e) {
                        enemies_[e].hp -= dmg;
                    } else if (sx * sx + sy * sy <= 1.8f * 1.8f) {
                        enemies_[e].hp -= dmg * 0.65f;
                    }
                    if (enemies_[e].hp <= 0.0f) {
                        enemies_[e].alive = false;
                        gold_ += enemies_[e].reward;
                        AddScore(20);
                    }
                }
            } else {
                enemies_[best_e].hp -= dmg;
                if (enemies_[best_e].hp <= 0.0f) {
                    enemies_[best_e].alive = false;
                    gold_ += enemies_[best_e].reward;
                    AddScore(20);
                }
            }
        }
    }

    // Check wave completion
    if (spawned_in_wave_ >= total_in_wave_) {
        bool any_alive = false;
        for (int e = 0; e < kMaxEnemies; ++e) {
            if (enemies_[e].alive) {
                any_alive = true;
                break;
            }
        }
        if (!any_alive) {
            if (wave_ >= 4) {
                AddScore(100);
                state_ = STATE_VICTORY;
                state_timer_ = 0.0f;
                return;
            } else {
                wave_delay_ += dt;
                if (wave_delay_ >= 1.2f) {
                    gold_ += 15;
                    StartWave((uint8_t)(wave_ + 1));
                }
            }
        }
    }
}

void Game083TowerDefense::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    memset(fb_rgb24, 0, 16 * 16 * 3);

    // Terrain & S-shaped road
    for (int y = 1; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (IsRoad(x, y)) {
                if (((x + y) & 1) == 0) {
                    SetPx83(fb_rgb24, x, y, 125, 88, 46);
                } else {
                    SetPx83(fb_rgb24, x, y, 108, 76, 40);
                }
            } else {
                SetPx83(fb_rgb24, x, y, 18, 46, 22);
            }
        }
    }

    // Spawn portal at (0, 2) and Cyan Base crystal at (15, 13)
    SetPx83(fb_rgb24, 0, 2, 190, 55, 225);
    int pulse = (int)((sinf(anim_timer_ * 5.0f) + 1.0f) * 35.0f);
    SetPx83(fb_rgb24, 15, 13, 0, (uint8_t)(180 + pulse), 255);

    // Towers & firing beams
    for (int i = 0; i < num_towers_; ++i) {
        if (!towers_[i].active) continue;
        uint8_t tr = 0, tg = 235, tb = 255;
        if (towers_[i].type == 1) { tr = 65; tg = 135; tb = 255; }
        else if (towers_[i].type == 2) { tr = 255; tg = 135; tb = 20; }
        if (towers_[i].level >= 2) {
            tr = (uint8_t)(tr + (255 - tr) / 3);
            tg = (uint8_t)(tg + (255 - tg) / 3);
            tb = (uint8_t)(tb + (255 - tb) / 3);
        }
        SetPx83(fb_rgb24, towers_[i].x, towers_[i].y, tr, tg, tb);

        if (towers_[i].beam_timer > 0.0f) {
            int mx = (int)roundf(((float)towers_[i].x + towers_[i].target_x) * 0.5f);
            int my = (int)roundf(((float)towers_[i].y + towers_[i].target_y) * 0.5f);
            SetPx83(fb_rgb24, mx, my, tr, tg, tb);
        }
    }

    // Enemies
    for (int i = 0; i < kMaxEnemies; ++i) {
        if (!enemies_[i].alive) continue;
        int ex = (int)roundf(enemies_[i].x);
        int ey = (int)roundf(enemies_[i].y);
        if (enemies_[i].is_boss) {
            SetPx83(fb_rgb24, ex, ey, 255, 40, 200);
        } else if (enemies_[i].slow_timer > 0.0f) {
            SetPx83(fb_rgb24, ex, ey, 110, 200, 255);
        } else {
            SetPx83(fb_rgb24, ex, ey, 240, 50, 45);
        }
    }

    // Build cursor
    if (state_ == STATE_PLAYING || state_ == STATE_TITLE) {
        bool blink = (((int)(anim_timer_ * 6.0f)) % 2) == 0;
        if (blink) {
            if (IsRoad(cursor_x_, cursor_y_)) {
                SetPx83(fb_rgb24, cursor_x_, cursor_y_, 220, 40, 40);
            } else {
                SetPx83(fb_rgb24, cursor_x_, cursor_y_, 255, 255, 255);
            }
        }
    }

    // Row 0 HUD: Base HP (0..4), Gold (6..11), Wave (12..13), Selected Tower Type (15)
    for (int h = 0; h < 5; ++h) {
        if (h < (int)base_hp_) {
            SetPx83(fb_rgb24, h, 0, 0, 225, 240);
        } else {
            SetPx83(fb_rgb24, h, 0, 55, 20, 20);
        }
    }
    int gold_pips = gold_ / 15;
    if (gold_pips > 6) gold_pips = 6;
    for (int g = 0; g < 6; ++g) {
        if (g < gold_pips) {
            SetPx83(fb_rgb24, 6 + g, 0, 255, 205, 20);
        } else {
            SetPx83(fb_rgb24, 6 + g, 0, 45, 38, 12);
        }
    }
    SetPx83(fb_rgb24, 13, 0, (uint8_t)(60 * wave_), 180, 90);
    if (selected_tower_type_ == 0) SetPx83(fb_rgb24, 15, 0, 0, 235, 255);
    else if (selected_tower_type_ == 1) SetPx83(fb_rgb24, 15, 0, 65, 135, 255);
    else SetPx83(fb_rgb24, 15, 0, 255, 135, 20);

    if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPx83(fb_rgb24, 6, y, 250, 250, 250);
            SetPx83(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game083TowerDefense::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = base_hp_;
    st.state = (uint8_t)state_;
    st.progress = (uint8_t)((wave_ - 1) * 25 + (spawned_in_wave_ * 25) / (total_in_wave_ > 0 ? total_in_wave_ : 1));
    return st;
}

static_assert(sizeof(Game083TowerDefense) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
