// game_085_lemmings_rescue.cpp —— 目标 #085 旅鼠拯救 核心实现
#include "game_085_lemmings_rescue.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>
#include <math.h>

namespace arcade {

static inline void SetPx85(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

Game085LemmingsRescue::Game085LemmingsRescue()
    : state_(STATE_TITLE),
      score_(0),
      high_score_(0),
      state_timer_(0.0f),
      anim_timer_(0.0f),
      stage_(1),
      spawned_count_(0),
      saved_count_(0),
      dead_count_(0),
      spawn_timer_(0.4f),
      stage_timer_(55.0f),
      hatch_x_(2),
      hatch_y_(2),
      exit_x_(13),
      exit_y_(13),
      cursor_x_(6),
      cursor_y_(4),
      selected_skill_(2),
      move_cooldown_(0.0f) {
    SetupMatch(STATE_TITLE);
}

void Game085LemmingsRescue::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

bool Game085LemmingsRescue::IsSolid(int x, int y) const {
    if (x < 0 || x >= 16 || y < 0 || y >= 16) return true;
    uint8_t t = terrain_[y][x];
    return (t == LEM_DIRT || t == LEM_STEEL || t == LEM_STAIR);
}

bool Game085LemmingsRescue::HasBlockerAt(int x, int y, int ignore_idx) const {
    for (int i = 0; i < kNumLemmings; ++i) {
        if (i == ignore_idx) continue;
        if (lemmings_[i].alive && lemmings_[i].state == LEM_STATE_BLOCKER) {
            if (lemmings_[i].x == x && (lemmings_[i].y == y || lemmings_[i].y == y - 1)) {
                return true;
            }
        }
    }
    return false;
}

void Game085LemmingsRescue::LoadStage(uint8_t stg) {
    stage_ = stg;
    spawned_count_ = 0;
    saved_count_ = 0;
    dead_count_ = 0;
    spawn_timer_ = 0.4f;
    stage_timer_ = TimeLimit();

    memset(terrain_, LEM_EMPTY, sizeof(terrain_));
    for (int y = 1; y <= 14; ++y) {
        terrain_[y][0] = LEM_STEEL;
        terrain_[y][15] = LEM_STEEL;
    }
    for (int x = 0; x < 16; ++x) {
        terrain_[15][x] = LEM_LAVA;
    }

    if (stg == 1) {
        hatch_x_ = 2; hatch_y_ = 2;
        exit_x_ = 13; exit_y_ = 13;
        cursor_x_ = 6; cursor_y_ = 4;
        selected_skill_ = 2; // DIGGER ready
        for (int x = 1; x <= 10; ++x) terrain_[5][x] = LEM_DIRT;
        for (int x = 4; x <= 9; ++x) terrain_[9][x] = LEM_DIRT;
        for (int x = 8; x <= 14; ++x) terrain_[14][x] = LEM_STEEL;
    } else if (stg == 2) {
        hatch_x_ = 2; hatch_y_ = 8;
        exit_x_ = 13; exit_y_ = 8;
        cursor_x_ = 7; cursor_y_ = 11;
        selected_skill_ = 1; // BUILDER ready
        for (int x = 1; x <= 7; ++x) terrain_[12][x] = LEM_STEEL;
        for (int x = 11; x <= 14; ++x) terrain_[9][x] = LEM_STEEL;
    } else {
        hatch_x_ = 4; hatch_y_ = 2;
        exit_x_ = 13; exit_y_ = 9;
        cursor_x_ = 6; cursor_y_ = 4;
        selected_skill_ = 2;
        for (int x = 2; x <= 8; ++x) terrain_[5][x] = LEM_DIRT;
        terrain_[3][8] = LEM_STEEL;
        terrain_[4][8] = LEM_STEEL;
        for (int x = 4; x <= 7; ++x) terrain_[10][x] = LEM_STEEL;
        terrain_[8][4] = LEM_STEEL;
        terrain_[9][4] = LEM_STEEL;
        for (int x = 11; x <= 14; ++x) terrain_[10][x] = LEM_STEEL;
    }

    for (int i = 0; i < kNumLemmings; ++i) {
        lemmings_[i] = {false, false, false, hatch_x_, hatch_y_, 1, LEM_STATE_FALLING, 0, 0, 0.0f, 0.0f};
    }
}

void Game085LemmingsRescue::SetupMatch(CartridgeState new_state) {
    state_ = new_state;
    score_ = 0;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    move_cooldown_ = 0.0f;
    LoadStage(1);
}

void Game085LemmingsRescue::Init() {
    Reset();
}

void Game085LemmingsRescue::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    SetupMatch(STATE_TITLE);
}

void Game085LemmingsRescue::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        SetupMatch(STATE_PLAYING);
    }
}

void Game085LemmingsRescue::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game085LemmingsRescue::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

void Game085LemmingsRescue::AssignSkillAtCursor() {
    int best_idx = -1;
    int best_dist_sq = 100;
    for (int i = 0; i < kNumLemmings; ++i) {
        if (!lemmings_[i].alive || lemmings_[i].saved) continue;
        if (lemmings_[i].state == LEM_STATE_FALLING || lemmings_[i].state == LEM_STATE_BLOCKER) continue;
        int dx = lemmings_[i].x - cursor_x_;
        int dy = lemmings_[i].y - cursor_y_;
        int d2 = dx * dx + dy * dy;
        if (d2 <= 6 && d2 < best_dist_sq) {
            best_dist_sq = d2;
            best_idx = i;
        }
    }
    if (best_idx < 0) return;

    SoundEvent(Sound::Action,selected_skill_);
    LemmingUnit& lm = lemmings_[best_idx];
    if (selected_skill_ == 0) {
        lm.state = LEM_STATE_BLOCKER;
        lm.skill_timer = 0.0f;
    } else if (selected_skill_ == 1) {
        lm.state = LEM_STATE_BUILDER;
        lm.bricks_left = 4;
        lm.skill_timer = 0.0f;
    } else if (selected_skill_ == 2) {
        lm.state = LEM_STATE_DIGGER;
        lm.skill_timer = 0.0f;
    }
}

void Game085LemmingsRescue::UpdateLemming(int idx, float dt) {
    LemmingUnit& lm = lemmings_[idx];
    if (!lm.alive || lm.saved) return;

    // Check exit door
    if (lm.x == exit_x_ && (lm.y == exit_y_ || lm.y == exit_y_ - 1)) {
        lm.saved = true;
        lm.alive = false;
        saved_count_++;
        AddScore(100);
        return;
    }

    // Check lava
    if (lm.y >= 15 || terrain_[lm.y][lm.x] == LEM_LAVA) {
        lm.alive = false;
        dead_count_++;
        return;
    }

    if (lm.state == LEM_STATE_FALLING) {
        if (IsSolid(lm.x, lm.y + 1)) {
            if (lm.fall_cells > 6) {
                lm.alive = false;
                dead_count_++;
                return;
            }
            lm.fall_cells = 0;
            lm.state = LEM_STATE_WALKING;
            lm.move_accum = 0.0f;
            return;
        }
        lm.move_accum += 8.0f * dt;
        while (lm.move_accum >= 1.0f) {
            lm.move_accum -= 1.0f;
            lm.y++;
            lm.fall_cells++;
            if (lm.y >= 15 || terrain_[lm.y][lm.x] == LEM_LAVA) {
                lm.alive = false;
                dead_count_++;
                return;
            }
            if (lm.x == exit_x_ && (lm.y == exit_y_ || lm.y == exit_y_ - 1) && lm.fall_cells <= 6) {
                lm.saved = true;
                lm.alive = false;
                saved_count_++;
                AddScore(100);
                return;
            }
            if (IsSolid(lm.x, lm.y + 1)) {
                if (lm.fall_cells > 6) {
                    lm.alive = false;
                    dead_count_++;
                } else {
                    lm.fall_cells = 0;
                    lm.state = LEM_STATE_WALKING;
                    lm.move_accum = 0.0f;
                }
                return;
            }
        }
        return;
    }

    // Ground support check for non-falling states
    if (!IsSolid(lm.x, lm.y + 1)) {
        lm.state = LEM_STATE_FALLING;
        lm.fall_cells = 0;
        lm.move_accum = 0.0f;
        return;
    }

    if (lm.state == LEM_STATE_BLOCKER) {
        return;
    }

    if (lm.state == LEM_STATE_BUILDER) {
        lm.skill_timer += dt;
        if (lm.skill_timer >= 0.28f) {
            lm.skill_timer -= 0.28f;
            int bx = lm.x + lm.dir;
            int by = lm.y;
            if (bx <= 0 || bx >= 15 || IsSolid(bx, by)) {
                lm.state = LEM_STATE_WALKING;
                lm.move_accum = 0.0f;
            } else {
                terrain_[by][bx] = LEM_STAIR;
                lm.bricks_left--;
                if (by - 1 >= 1 && !IsSolid(bx, by - 1)) {
                    lm.x = bx;
                    lm.y = by - 1;
                    if (lm.x == exit_x_ && (lm.y == exit_y_ || lm.y == exit_y_ - 1)) {
                        lm.saved = true;
                        lm.alive = false;
                        saved_count_++;
                        AddScore(100);
                        return;
                    }
                    if (lm.bricks_left <= 0) {
                        lm.state = LEM_STATE_WALKING;
                        lm.move_accum = 0.0f;
                    }
                } else {
                    lm.state = LEM_STATE_WALKING;
                    lm.move_accum = 0.0f;
                }
            }
        }
        return;
    }

    if (lm.state == LEM_STATE_DIGGER) {
        lm.skill_timer += dt;
        if (lm.skill_timer >= 0.30f) {
            lm.skill_timer -= 0.30f;
            if (lm.y + 1 >= 15 || terrain_[lm.y + 1][lm.x] == LEM_STEEL) {
                lm.state = LEM_STATE_WALKING;
                lm.move_accum = 0.0f;
            } else if (terrain_[lm.y + 1][lm.x] == LEM_DIRT || terrain_[lm.y + 1][lm.x] == LEM_STAIR) {
                terrain_[lm.y + 1][lm.x] = LEM_EMPTY;
                lm.y++;
                if (!IsSolid(lm.x, lm.y + 1)) {
                    lm.state = LEM_STATE_FALLING;
                    lm.fall_cells = 0;
                    lm.move_accum = 0.0f;
                }
            } else {
                lm.state = LEM_STATE_FALLING;
                lm.fall_cells = 0;
                lm.move_accum = 0.0f;
            }
        }
        return;
    }

    // Walking state
    lm.move_accum += 2.4f * dt;
    if (lm.move_accum >= 1.0f) {
        lm.move_accum -= 1.0f;
        int nx = lm.x + lm.dir;
        if (nx <= 0 || nx >= 15 || HasBlockerAt(nx, lm.y, idx)) {
            lm.dir = -lm.dir;
        } else if (!IsSolid(nx, lm.y)) {
            lm.x = nx;
            if (lm.x == exit_x_ && (lm.y == exit_y_ || lm.y == exit_y_ - 1)) {
                lm.saved = true;
                lm.alive = false;
                saved_count_++;
                AddScore(100);
                return;
            }
            if (!IsSolid(lm.x, lm.y + 1)) {
                lm.state = LEM_STATE_FALLING;
                lm.fall_cells = 0;
                lm.move_accum = 0.0f;
            }
        } else {
            // Solid cell ahead: check 1px step-up (stairs / low ledge)
            if (lm.y - 1 >= 1 && !IsSolid(nx, lm.y - 1) && !IsSolid(lm.x, lm.y - 1) && !HasBlockerAt(nx, lm.y - 1, idx)) {
                lm.x = nx;
                lm.y = lm.y - 1;
                if (lm.x == exit_x_ && (lm.y == exit_y_ || lm.y == exit_y_ - 1)) {
                    lm.saved = true;
                    lm.alive = false;
                    saved_count_++;
                    AddScore(100);
                    return;
                }
            } else {
                lm.dir = -lm.dir;
            }
        }
    }
}

void Game085LemmingsRescue::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
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

    if (move_cooldown_ > 0.0f) {
        move_cooldown_ -= dt;
    }
    uint16_t dpad_mask = KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN;
    uint16_t dpad_trig = keys_pressed & dpad_mask;
    if (!dpad_trig && move_cooldown_ <= 0.0f && (keys_down & dpad_mask)) {
        dpad_trig = keys_down & dpad_mask;
        move_cooldown_ = 0.14f;
    } else if (dpad_trig) {
        move_cooldown_ = 0.18f;
    }

    if (dpad_trig & KEY_LEFT) {
        if (cursor_x_ > 1) cursor_x_--;
    } else if (dpad_trig & KEY_RIGHT) {
        if (cursor_x_ < 14) cursor_x_++;
    } else if (dpad_trig & KEY_UP) {
        if (cursor_y_ > 1) cursor_y_--;
    } else if (dpad_trig & KEY_DOWN) {
        if (cursor_y_ < 14) cursor_y_++;
    }

    if (keys_pressed & KEY_B) {
        selected_skill_ = (uint8_t)((selected_skill_ + 1) % 3);
    }
    if (keys_pressed & KEY_A) {
        AssignSkillAtCursor();
    }

    // Release 5 lemmings from hatch
    if (spawned_count_ < kNumLemmings) {
        spawn_timer_ -= dt;
        if (spawn_timer_ <= 0.0f) {
            int idx = spawned_count_;
            lemmings_[idx].spawned = true;
            lemmings_[idx].alive = true;
            lemmings_[idx].saved = false;
            lemmings_[idx].x = hatch_x_;
            lemmings_[idx].y = hatch_y_;
            lemmings_[idx].dir = 1;
            lemmings_[idx].state = LEM_STATE_FALLING;
            lemmings_[idx].fall_cells = 0;
            lemmings_[idx].move_accum = 0.0f;
            lemmings_[idx].skill_timer = 0.0f;
            spawned_count_++;
            spawn_timer_ = 1.45f;
        }
    }

    for (int i = 0; i < kNumLemmings; ++i) {
        UpdateLemming(i, dt);
    }

    // Too many lost (> 2 dead means < 3 can be saved)
    if (dead_count_ > kNumLemmings-RequiredSaved()) {
        state_ = STATE_GAMEOVER;
        state_timer_ = 0.0f;
        return;
    }

    stage_timer_ -= dt;
    if (stage_timer_ <= 0.0f) {
        if (saved_count_ >= RequiredSaved()) {
            if (stage_ >= 3) {
                state_ = STATE_VICTORY;
                state_timer_ = 0.0f;
            } else {
                LoadStage((uint8_t)(stage_ + 1));
            }
        } else {
            state_ = STATE_GAMEOVER;
            state_timer_ = 0.0f;
        }
        return;
    }

    if (spawned_count_ >= kNumLemmings) {
        int active_mobile = 0;
        for (int i = 0; i < kNumLemmings; ++i) {
            if (lemmings_[i].alive && lemmings_[i].state != LEM_STATE_BLOCKER) {
                active_mobile++;
            }
        }
        if (active_mobile == 0) {
            if (saved_count_ >= RequiredSaved()) {
                if (stage_ >= 3) {
                    state_ = STATE_VICTORY;
                    state_timer_ = 0.0f;
                } else {
                    LoadStage((uint8_t)(stage_ + 1));
                }
            } else {
                state_ = STATE_GAMEOVER;
                state_timer_ = 0.0f;
            }
        }
    }
}

void Game085LemmingsRescue::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    // Cavern dark blue-purple backdrop
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            SetPx85(fb_rgb24, x, y, 12, 10, 24);
        }
    }

    // Terrain
    for (int y = 1; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            uint8_t t = terrain_[y][x];
            if (t == LEM_DIRT) {
                if (((x + y) & 1) == 0) SetPx85(fb_rgb24, x, y, 150, 95, 45);
                else SetPx85(fb_rgb24, x, y, 128, 78, 36);
            } else if (t == LEM_STEEL) {
                SetPx85(fb_rgb24, x, y, 95, 105, 120);
            } else if (t == LEM_STAIR) {
                SetPx85(fb_rgb24, x, y, 245, 200, 45);
            } else if (t == LEM_LAVA) {
                uint8_t flick = (uint8_t)(120 + (((int)(anim_timer_ * 8.0f) + x) % 2) * 80);
                SetPx85(fb_rgb24, x, y, 255, (uint8_t)(flick / 2), 15);
            }
        }
    }

    // Entry Hatch (top-left) & Exit Door (bottom-right)
    SetPx85(fb_rgb24, hatch_x_, hatch_y_ - 1, 210, 120, 255);
    SetPx85(fb_rgb24, hatch_x_, hatch_y_, 140, 70, 190);

    SetPx85(fb_rgb24, exit_x_, exit_y_ - 1, 255, 215, 40);
    SetPx85(fb_rgb24, exit_x_, exit_y_, 40, 235, 220);

    // Lemmings (green-haired / bright green-cyan sprites, orange if blocker)
    for (int i = 0; i < kNumLemmings; ++i) {
        if (!lemmings_[i].alive || lemmings_[i].saved) continue;
        if (lemmings_[i].state == LEM_STATE_BLOCKER) {
            SetPx85(fb_rgb24, lemmings_[i].x, lemmings_[i].y, 255, 95, 35);
        } else if (lemmings_[i].state == LEM_STATE_BUILDER) {
            SetPx85(fb_rgb24, lemmings_[i].x, lemmings_[i].y, 120, 255, 90);
        } else if (lemmings_[i].state == LEM_STATE_DIGGER) {
            SetPx85(fb_rgb24, lemmings_[i].x, lemmings_[i].y, 50, 245, 255);
        } else {
            SetPx85(fb_rgb24, lemmings_[i].x, lemmings_[i].y, 60, 245, 85);
        }
    }

    // Cursor
    if (state_ == STATE_PLAYING || state_ == STATE_TITLE) {
        if ((((int)(anim_timer_ * 6.0f)) % 2) == 0) {
            SetPx85(fb_rgb24, cursor_x_, cursor_y_, 255, 255, 255);
        }
    }

    // HUD Row 0: Saved count (0..4), Stage (8..10), Selected Skill (14..15)
    for (int s = 0; s < 5; ++s) {
        if (s < (int)saved_count_) {
            SetPx85(fb_rgb24, s, 0, 50, 245, 90);
        } else if (s >= 5 - (int)dead_count_) {
            SetPx85(fb_rgb24, s, 0, 180, 35, 35);
        } else {
            SetPx85(fb_rgb24, s, 0, 35, 50, 40);
        }
    }
    for (int k = 0; k < 3; ++k) {
        if (k < (int)stage_) SetPx85(fb_rgb24, 8 + k, 0, 220, 190, 60);
    }
    if (selected_skill_ == 0) {
        SetPx85(fb_rgb24, 14, 0, 255, 90, 30);
        SetPx85(fb_rgb24, 15, 0, 255, 90, 30);
    } else if (selected_skill_ == 1) {
        SetPx85(fb_rgb24, 14, 0, 250, 205, 35);
        SetPx85(fb_rgb24, 15, 0, 250, 205, 35);
    } else {
        SetPx85(fb_rgb24, 14, 0, 0, 230, 255);
        SetPx85(fb_rgb24, 15, 0, 0, 230, 255);
    }

    if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPx85(fb_rgb24, 6, y, 250, 250, 250);
            SetPx85(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game085LemmingsRescue::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = (uint8_t)(kNumLemmings > dead_count_ ? (kNumLemmings - dead_count_) : 0);
    st.state = (uint8_t)state_;
    st.progress = (uint8_t)(((stage_ - 1) * 33) + (saved_count_ * 34) / 3);
    if (st.progress > 100) st.progress = 100;
    return st;
}

static_assert(sizeof(Game085LemmingsRescue) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
