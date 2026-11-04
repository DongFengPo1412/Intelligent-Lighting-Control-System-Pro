// game_004_gravity_flip.cpp —— 目标 #004 重力翻转 (VVVVVV Flip) 核心实现
#include "game_004_gravity_flip.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <math.h>
#include <string.h>

namespace arcade {

enum FlipTile : uint8_t {
    FLIP_AIR   = 0,
    FLIP_SOLID = 1,
    FLIP_SPIKE = 2,
};

static inline void SetPx004(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

Game004GravityFlip::Game004GravityFlip()
    : state_(STATE_TITLE),
      stage_idx_(0),
      lives_(3),
      player_x_(1.0f),
      player_y_(14.0f),
      player_vy_(0.0f),
      gravity_dir_(1),
      grounded_(true),
      drone_x_(8.0f),
      drone_y_(7.0f),
      drone_vx_(0.0f),
      drone_vy_(5.0f),
      drone_min_(5.0f),
      drone_max_(10.0f),
      exit_x_(14),
      exit_y_(14),
      score_(0),
      high_score_(0),
      state_timer_(0.0f),
      anim_timer_(0.0f),
      grid_{},
      orbs_{} {
}

void Game004GravityFlip::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

void Game004GravityFlip::RespawnPlayer() {
    player_x_ = 1.0f;
    player_y_ = 14.0f;
    player_vy_ = 0.0f;
    gravity_dir_ = 1;
    grounded_ = true;
}

void Game004GravityFlip::LoadStage(int stage_idx) {
    stage_idx_ = stage_idx;
    memset(grid_, FLIP_AIR, sizeof(grid_));

    for (int x = 0; x < 16; ++x) {
        grid_[0][x] = FLIP_SOLID;
        grid_[15][x] = FLIP_SOLID;
    }

    if (stage_idx == 0) {
        for (int x = 5; x <= 7; ++x) grid_[14][x] = FLIP_SPIKE;
        for (int x = 10; x <= 12; ++x) grid_[1][x] = FLIP_SPIKE;
        orbs_[0] = {6, 1, false};
        orbs_[1] = {11, 14, false};
        drone_x_ = 8.0f;
        drone_y_ = 7.0f;
        drone_vx_ = 0.0f;
        drone_vy_ = 5.0f;
        drone_min_ = 4.5f;
        drone_max_ = 10.5f;
        exit_x_ = 14;
        exit_y_ = 14;
    } else if (stage_idx == 1) {
        for (int x = 4; x <= 6; ++x) grid_[14][x] = FLIP_SPIKE;
        for (int x = 11; x <= 12; ++x) grid_[14][x] = FLIP_SPIKE;
        for (int x = 7; x <= 9; ++x) grid_[1][x] = FLIP_SPIKE;
        for (int x = 6; x <= 8; ++x) grid_[8][x] = FLIP_SOLID;
        orbs_[0] = {5, 1, false};
        orbs_[1] = {7, 7, false};
        drone_x_ = 10.0f;
        drone_y_ = 6.0f;
        drone_vx_ = 0.0f;
        drone_vy_ = 6.0f;
        drone_min_ = 4.0f;
        drone_max_ = 11.0f;
        exit_x_ = 14;
        exit_y_ = 1;
    } else {
        for (int x = 3; x <= 5; ++x) grid_[14][x] = FLIP_SPIKE;
        for (int x = 9; x <= 11; ++x) grid_[14][x] = FLIP_SPIKE;
        for (int x = 6; x <= 8; ++x) grid_[1][x] = FLIP_SPIKE;
        for (int x = 12; x <= 13; ++x) grid_[1][x] = FLIP_SPIKE;
        orbs_[0] = {4, 1, false};
        orbs_[1] = {10, 1, false};
        drone_x_ = 5.0f;
        drone_y_ = 7.5f;
        drone_vx_ = 6.5f;
        drone_vy_ = 0.0f;
        drone_min_ = 3.0f;
        drone_max_ = 12.0f;
        exit_x_ = 14;
        exit_y_ = 14;
    }

    RespawnPlayer();
}

void Game004GravityFlip::Init() {
    Reset();
}

void Game004GravityFlip::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    score_ = 0;
    lives_ = 3;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    LoadStage(0);
    state_ = STATE_TITLE;
}

void Game004GravityFlip::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        score_ = 0;
        lives_ = 3;
        state_timer_ = 0.0f;
        anim_timer_ = 0.0f;
        LoadStage(0);
        state_ = STATE_PLAYING;
    }
}

void Game004GravityFlip::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game004GravityFlip::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

bool Game004GravityFlip::IsSolid(int tx, int ty) const {
    if (tx < 0 || tx >= 16 || ty < 0 || ty >= 16) return false;
    return grid_[ty][tx] == FLIP_SOLID;
}

bool Game004GravityFlip::IsSpike(int tx, int ty) const {
    if (tx < 0 || tx >= 16 || ty < 0 || ty >= 16) return false;
    return grid_[ty][tx] == FLIP_SPIKE;
}

void Game004GravityFlip::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt > 0.05f) dt = 0.05f;
    state_timer_ += dt;
    anim_timer_ += dt;

    if (state_ == STATE_TITLE) {
        if (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN)) {
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

        // Update patrolling obstacle drone
        if (drone_vx_ != 0.0f) {
            drone_x_ += drone_vx_ * dt;
            if (drone_x_ <= drone_min_) {
                drone_x_ = drone_min_;
                drone_vx_ = fabsf(drone_vx_);
            } else if (drone_x_ >= drone_max_) {
                drone_x_ = drone_max_;
                drone_vx_ = -fabsf(drone_vx_);
            }
        }
        if (drone_vy_ != 0.0f) {
            drone_y_ += drone_vy_ * dt;
            if (drone_y_ <= drone_min_) {
                drone_y_ = drone_min_;
                drone_vy_ = fabsf(drone_vy_);
            } else if (drone_y_ >= drone_max_) {
                drone_y_ = drone_max_;
                drone_vy_ = -fabsf(drone_vy_);
            }
        }

        // STRICT ANTI-DUPLICATION RULE:
        // NO normal jump! Gravity flips ONLY when standing on floor or ceiling (grounded_ == true).
        const uint16_t flip_mask = KEY_A | KEY_B | KEY_UP | KEY_DOWN;
        if (grounded_ && (keys_pressed & flip_mask)) {
            gravity_dir_ = -gravity_dir_;
            grounded_ = false;
            player_vy_ = (float)gravity_dir_ * 2.5f;
        }

        // Horizontal movement
        const float move_speed = 7.5f;
        float vx = 0.0f;
        if (keys_down & KEY_LEFT) vx = -move_speed;
        else if (keys_down & KEY_RIGHT) vx = move_speed;

        float next_x = player_x_ + vx * dt;
        if (next_x < 0.0f) next_x = 0.0f;
        if (next_x > 15.0f) next_x = 15.0f;

        int cur_ty = (int)roundf(player_y_);
        if (vx > 0.0f && IsSolid((int)floorf(next_x + 0.85f), cur_ty)) {
            next_x = floorf(next_x + 0.85f) - 0.86f;
        } else if (vx < 0.0f && IsSolid((int)floorf(next_x + 0.1f), cur_ty)) {
            next_x = floorf(next_x + 0.1f) + 1.0f;
        }
        player_x_ = next_x;

        // Vertical gravity acceleration & surface landing
        int left_tx = (int)floorf(player_x_ + 0.15f);
        int right_tx = (int)floorf(player_x_ + 0.80f);

        if (grounded_) {
            int support_ty = (gravity_dir_ > 0) ? ((int)roundf(player_y_) + 1) : ((int)roundf(player_y_) - 1);
            if (!IsSolid(left_tx, support_ty) && !IsSolid(right_tx, support_ty)) {
                grounded_ = false;
            }
        }

        if (!grounded_) {
            const float grav_accel = 38.0f;
            player_vy_ += (float)gravity_dir_ * grav_accel * dt;
            if (player_vy_ > 14.0f) player_vy_ = 14.0f;
            if (player_vy_ < -14.0f) player_vy_ = -14.0f;

            float next_y = player_y_ + player_vy_ * dt;
            if (gravity_dir_ > 0 && player_vy_ >= 0.0f) {
                int foot_ty = (int)floorf(next_y + 0.95f);
                if (IsSolid(left_tx, foot_ty) || IsSolid(right_tx, foot_ty)) {
                    next_y = (float)foot_ty - 1.0f;
                    player_vy_ = 0.0f;
                    grounded_ = true;
                }
            } else if (gravity_dir_ < 0 && player_vy_ <= 0.0f) {
                int head_ty = (int)floorf(next_y + 0.05f);
                if (IsSolid(left_tx, head_ty) || IsSolid(right_tx, head_ty)) {
                    next_y = (float)(head_ty + 1);
                    player_vy_ = 0.0f;
                    grounded_ = true;
                }
            }
            player_y_ = next_y;
        }

        // Collectible energy orbs
        for (int i = 0; i < kMaxOrbs; ++i) {
            if (!orbs_[i].collected) {
                float odx = (player_x_ + 0.5f) - ((float)orbs_[i].x + 0.5f);
                float ody = (player_y_ + 0.5f) - ((float)orbs_[i].y + 0.5f);
                if (odx * odx + ody * ody <= 1.2f) {
                    orbs_[i].collected = true;
                    AddScore(50);
                }
            }
        }

        // Hazard check (red spikes + moving drone)
        int cx = (int)roundf(player_x_);
        int cy = (int)roundf(player_y_);
        float ddx = player_x_ - drone_x_;
        float ddy = player_y_ - drone_y_;
        bool hit_drone = (ddx * ddx + ddy * ddy <= 0.65f);
        bool hit_spike = IsSpike(cx, cy) || IsSpike(left_tx, cy) || IsSpike(right_tx, cy);

        if (hit_spike || hit_drone) {
            if (lives_ > 1) {
                lives_--;
                RespawnPlayer();
            } else {
                lives_ = 0;
                state_ = STATE_GAMEOVER;
                state_timer_ = 0.0f;
            }
            return;
        }

        // Checkpoint / Stage exit check
        float edx = (player_x_ + 0.5f) - ((float)exit_x_ + 0.5f);
        float edy = (player_y_ + 0.5f) - ((float)exit_y_ + 0.5f);
        if (edx * edx + edy * edy <= 1.6f) {
            AddScore(100);
            if (stage_idx_ + 1 < kNumStages) {
                LoadStage(stage_idx_ + 1);
            } else {
                AddScore(200);
                state_ = STATE_VICTORY;
                state_timer_ = 0.0f;
            }
        }
    }
}

void Game004GravityFlip::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    // Deep sci-fi corridor background
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            uint8_t bg_b = (uint8_t)(24 + ((x + y) & 1) * 6);
            SetPx004(fb_rgb24, x, y, 8, 12, bg_b);
        }
    }

    // Walls & Spikes
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (grid_[y][x] == FLIP_SOLID) {
                SetPx004(fb_rgb24, x, y, 45, 110, 175);
            } else if (grid_[y][x] == FLIP_SPIKE) {
                SetPx004(fb_rgb24, x, y, 235, 50, 55);
            }
        }
    }

    // Collectible energy orbs
    for (int i = 0; i < kMaxOrbs; ++i) {
        if (!orbs_[i].collected) {
            SetPx004(fb_rgb24, orbs_[i].x, orbs_[i].y, 255, 230, 40);
        }
    }

    // Moving plasma drone
    SetPx004(fb_rgb24, (int)roundf(drone_x_), (int)roundf(drone_y_), 255, 90, 210);

    // Exit teleporter (2px tall beacon)
    int beam_y2 = (exit_y_ <= 2) ? (exit_y_ + 1) : (exit_y_ - 1);
    SetPx004(fb_rgb24, exit_x_, exit_y_, 46, 255, 130);
    SetPx004(fb_rgb24, exit_x_, beam_y2, 20, 180, 95);

    // Captain Viridian (cyan when gravity down, neon violet-cyan when inverted)
    int px = (int)roundf(player_x_);
    int py = (int)roundf(player_y_);
    if (gravity_dir_ > 0) {
        SetPx004(fb_rgb24, px, py, 90, 245, 255);
    } else {
        SetPx004(fb_rgb24, px, py, 160, 255, 220);
    }

    // Lives HUD on top wall (x=0..2, y=0)
    for (int i = 0; i < (int)lives_ && i < 3; ++i) {
        SetPx004(fb_rgb24, i, 0, 255, 255, 255);
    }

    if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPx004(fb_rgb24, 6, y, 250, 250, 250);
            SetPx004(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game004GravityFlip::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = lives_;
    st.state = (uint8_t)state_;
    if (state_ == STATE_VICTORY) {
        st.progress = 100;
    } else {
        st.progress = (uint8_t)((stage_idx_ * 100) / kNumStages);
    }
    return st;
}

static_assert(sizeof(Game004GravityFlip) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
