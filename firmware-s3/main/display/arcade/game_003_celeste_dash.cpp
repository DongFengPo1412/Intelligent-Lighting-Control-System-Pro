// game_003_celeste_dash.cpp —— 目标 #003 空中冲刺 (Celeste Dash) 核心实现
#include "game_003_celeste_dash.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <math.h>
#include <string.h>

namespace arcade {

enum CelesteTile : uint8_t {
    CELESTE_AIR   = 0,
    CELESTE_SOLID = 1,
    CELESTE_SPIKE = 2,
};

static inline void SetPx003(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

Game003CelesteDash::Game003CelesteDash()
    : state_(STATE_TITLE),
      room_idx_(0),
      lives_(3),
      player_x_(1.0f),
      player_y_(13.0f),
      player_vx_(0.0f),
      player_vy_(0.0f),
      facing_x_(1),
      on_ground_(true),
      coyote_timer_(0.0f),
      dash_ready_(true),
      dash_timer_(0.0f),
      dash_vx_(0.0f),
      dash_vy_(0.0f),
      trail_spawn_acc_(0.0f),
      crystal_x_(-1),
      crystal_y_(-1),
      crystal_present_(false),
      crystal_cooldown_(0.0f),
      crystal_scored_(false),
      goal_x_(14),
      goal_y_(6),
      score_(0),
      high_score_(0),
      state_timer_(0.0f),
      anim_timer_(0.0f),
      grid_{},
      trails_{} {
}

void Game003CelesteDash::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

void Game003CelesteDash::RespawnInRoom() {
    player_x_ = 1.0f;
    player_y_ = 13.0f;
    player_vx_ = 0.0f;
    player_vy_ = 0.0f;
    facing_x_ = 1;
    on_ground_ = true;
    coyote_timer_ = 0.08f;
    dash_ready_ = true;
    dash_timer_ = 0.0f;
    dash_vx_ = 0.0f;
    dash_vy_ = 0.0f;
    trail_spawn_acc_ = 0.0f;
    crystal_cooldown_ = 0.0f;
    for (int i = 0; i < kMaxTrail; ++i) {
        trails_[i].active = false;
    }
}

void Game003CelesteDash::LoadRoom(int room_idx) {
    room_idx_ = room_idx;
    memset(grid_, CELESTE_AIR, sizeof(grid_));
    crystal_present_ = false;
    crystal_scored_ = false;
    crystal_x_ = -1;
    crystal_y_ = -1;

    // Starting snow ledge on bottom-left for all rooms
    for (int x = 0; x <= 3; ++x) {
        grid_[14][x] = CELESTE_SOLID;
        grid_[15][x] = CELESTE_SOLID;
    }
    for (int x = 4; x < 16; ++x) {
        grid_[15][x] = CELESTE_SPIKE;
    }

    if (room_idx == 0) {
        for (int x = 6; x <= 9; ++x) grid_[11][x] = CELESTE_SOLID;
        for (int x = 12; x <= 15; ++x) grid_[7][x] = CELESTE_SOLID;
        goal_x_ = 14;
        goal_y_ = 6;
    } else if (room_idx == 1) {
        crystal_present_ = true;
        crystal_x_ = 7;
        crystal_y_ = 9;
        for (int x = 10; x <= 15; ++x) grid_[6][x] = CELESTE_SOLID;
        goal_x_ = 13;
        goal_y_ = 5;
    } else {
        for (int x = 6; x <= 10; ++x) grid_[0][x] = CELESTE_SPIKE;
        for (int x = 7; x <= 10; ++x) grid_[11][x] = CELESTE_SOLID;
        crystal_present_ = true;
        crystal_x_ = 12;
        crystal_y_ = 7;
        for (int x = 7; x <= 10; ++x) grid_[5][x] = CELESTE_SOLID;
        for (int x = 1; x <= 4; ++x) grid_[3][x] = CELESTE_SOLID;
        goal_x_ = 2;
        goal_y_ = 2;
    }

    RespawnInRoom();
}

void Game003CelesteDash::Init() {
    Reset();
}

void Game003CelesteDash::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    score_ = 0;
    lives_ = 3;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    LoadRoom(0);
    state_ = STATE_TITLE;
}

void Game003CelesteDash::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        score_ = 0;
        lives_ = 3;
        state_timer_ = 0.0f;
        anim_timer_ = 0.0f;
        LoadRoom(0);
        state_ = STATE_PLAYING;
    }
}

void Game003CelesteDash::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game003CelesteDash::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

bool Game003CelesteDash::IsSolidTile(int tx, int ty) const {
    if (tx < 0 || tx >= 16 || ty < 0 || ty >= 16) return false;
    return grid_[ty][tx] == CELESTE_SOLID;
}

bool Game003CelesteDash::IsSpikeTile(int tx, int ty) const {
    if (tx < 0 || tx >= 16 || ty < 0 || ty >= 16) return false;
    return grid_[ty][tx] == CELESTE_SPIKE;
}

void Game003CelesteDash::SpawnTrail(bool pink) {
    for (int i = 0; i < kMaxTrail; ++i) {
        if (!trails_[i].active) {
            trails_[i].active = true;
            trails_[i].x = player_x_;
            trails_[i].y = player_y_;
            trails_[i].timer = 0.22f;
            trails_[i].pink = pink;
            return;
        }
    }
    trails_[0].active = true;
    trails_[0].x = player_x_;
    trails_[0].y = player_y_;
    trails_[0].timer = 0.22f;
    trails_[0].pink = pink;
}

void Game003CelesteDash::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt > 0.05f) dt = 0.05f;
    state_timer_ += dt;
    anim_timer_ += dt;

    for (int i = 0; i < kMaxTrail; ++i) {
        if (trails_[i].active) {
            trails_[i].timer -= dt;
            if (trails_[i].timer <= 0.0f) trails_[i].active = false;
        }
    }

    if (state_ == STATE_TITLE) {
        if (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP)) {
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

        if (crystal_cooldown_ > 0.0f) {
            crystal_cooldown_ -= dt;
            if (crystal_cooldown_ < 0.0f) crystal_cooldown_ = 0.0f;
        }

        if (keys_down & KEY_LEFT) facing_x_ = -1;
        else if (keys_down & KEY_RIGHT) facing_x_ = 1;

        if (on_ground_) {
            coyote_timer_ = 0.08f;
            if (dash_timer_ <= 0.0f) {
                dash_ready_ = true;
            }
        } else if (coyote_timer_ > 0.0f) {
            coyote_timer_ -= dt;
        }

        // Jump on KEY_A
        if ((keys_pressed & KEY_A) && (on_ground_ || coyote_timer_ > 0.0f) && dash_timer_ <= 0.0f) {
            player_vy_ = -11.5f;
            on_ground_ = false;
            coyote_timer_ = 0.0f;
        }

        // 8-way mid-air / ground Dash on KEY_B
        if ((keys_pressed & KEY_B) && dash_ready_ && dash_timer_ <= 0.0f) {
            int ix = ((keys_down & KEY_RIGHT) ? 1 : 0) - ((keys_down & KEY_LEFT) ? 1 : 0);
            int iy = ((keys_down & KEY_DOWN) ? 1 : 0) - ((keys_down & KEY_UP) ? 1 : 0);
            if (ix == 0 && iy == 0) {
                ix = facing_x_;
                iy = -1;
            }
            float norm = (ix != 0 && iy != 0) ? 0.70710678f : 1.0f;
            const float dash_speed = 28.0f;
            dash_vx_ = (float)ix * norm * dash_speed;
            dash_vy_ = (float)iy * norm * dash_speed;
            dash_timer_ = 0.14f;
            dash_ready_ = false;
            on_ground_ = false;
            coyote_timer_ = 0.0f;
            trail_spawn_acc_ = 0.0f;
            SpawnTrail(true);
        }

        if (dash_timer_ > 0.0f) {
            // Zero gravity during dash!
            dash_timer_ -= dt;
            trail_spawn_acc_ += dt;
            if (trail_spawn_acc_ >= 0.035f) {
                trail_spawn_acc_ -= 0.035f;
                SpawnTrail(dash_timer_ > 0.07f);
            }
            player_vx_ = dash_vx_;
            player_vy_ = dash_vy_;
            if (dash_timer_ <= 0.0f) {
                dash_timer_ = 0.0f;
                player_vx_ = dash_vx_ * 0.35f;
                player_vy_ = dash_vy_ * 0.35f;
            }
        } else {
            const float move_speed = 7.5f;
            if (keys_down & KEY_LEFT) player_vx_ = -move_speed;
            else if (keys_down & KEY_RIGHT) player_vx_ = move_speed;
            else player_vx_ = 0.0f;

            const float gravity = 32.0f;
            player_vy_ += gravity * dt;
            if (player_vy_ > 14.0f) player_vy_ = 14.0f;
        }

        // Horizontal movement + tile collision
        float next_x = player_x_ + player_vx_ * dt;
        if (next_x < 0.0f) {
            next_x = 0.0f;
            player_vx_ = 0.0f;
        } else if (next_x > 15.0f) {
            next_x = 15.0f;
            player_vx_ = 0.0f;
        }
        int check_y = (int)roundf(player_y_);
        if (player_vx_ > 0.0f && IsSolidTile((int)floorf(next_x + 0.85f), check_y)) {
            next_x = floorf(next_x + 0.85f) - 0.86f;
            player_vx_ = 0.0f;
        } else if (player_vx_ < 0.0f && IsSolidTile((int)floorf(next_x + 0.1f), check_y)) {
            next_x = floorf(next_x + 0.1f) + 1.0f;
            player_vx_ = 0.0f;
        }
        player_x_ = next_x;

        // Vertical movement + tile collision
        float old_y = player_y_;
        float next_y = player_y_ + player_vy_ * dt;
        on_ground_ = false;

        int left_tx = (int)floorf(player_x_ + 0.15f);
        int right_tx = (int)floorf(player_x_ + 0.80f);

        if (player_vy_ >= 0.0f) {
            int foot_ty = (int)floorf(next_y + 0.95f);
            if ((IsSolidTile(left_tx, foot_ty) || IsSolidTile(right_tx, foot_ty)) &&
                old_y + 0.95f <= (float)foot_ty + 0.35f) {
                next_y = (float)foot_ty - 1.0f;
                player_vy_ = 0.0f;
                on_ground_ = true;
                if (dash_timer_ <= 0.0f) {
                    dash_ready_ = true;
                }
            }
        } else {
            int head_ty = (int)floorf(next_y + 0.05f);
            if (next_y < 0.0f) {
                next_y = 0.0f;
                player_vy_ = 0.0f;
            } else if (IsSolidTile(left_tx, head_ty) || IsSolidTile(right_tx, head_ty)) {
                next_y = (float)(head_ty + 1);
                player_vy_ = 0.0f;
            }
        }
        player_y_ = next_y;

        // Dash crystal recharge check
        if (crystal_present_ && crystal_cooldown_ <= 0.0f) {
            float dx = (player_x_ + 0.5f) - ((float)crystal_x_ + 0.5f);
            float dy = (player_y_ + 0.5f) - ((float)crystal_y_ + 0.5f);
            if (dx * dx + dy * dy <= 1.85f) {
                dash_ready_ = true;
                crystal_cooldown_ = 2.5f;
                if (!crystal_scored_) {
                    crystal_scored_ = true;
                    AddScore(25);
                }
            }
        }

        // Spike / pit hazard check
        int cx = (int)roundf(player_x_);
        int cy = (int)roundf(player_y_);
        if (player_y_ > 15.1f || IsSpikeTile(cx, cy) ||
            IsSpikeTile(left_tx, (int)floorf(player_y_ + 0.85f)) ||
            IsSpikeTile(right_tx, (int)floorf(player_y_ + 0.85f))) {
            if (lives_ > 1) {
                lives_--;
                RespawnInRoom();
            } else {
                lives_ = 0;
                state_ = STATE_GAMEOVER;
                state_timer_ = 0.0f;
            }
            return;
        }

        // Golden strawberry / room goal flag check
        float gdx = (player_x_ + 0.5f) - ((float)goal_x_ + 0.5f);
        float gdy = (player_y_ + 0.5f) - ((float)goal_y_ + 0.5f);
        if (gdx * gdx + gdy * gdy <= 1.5f) {
            AddScore(100);
            if (room_idx_ + 1 < kNumRooms) {
                LoadRoom(room_idx_ + 1);
            } else {
                AddScore(200);
                state_ = STATE_VICTORY;
                state_timer_ = 0.0f;
            }
        }
    }
}

void Game003CelesteDash::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    // Mountain night sky
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            SetPx003(fb_rgb24, x, y, 14, 18, 38);
        }
    }

    // Tiles
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (grid_[y][x] == CELESTE_SOLID) {
                bool snow_top = (y > 0 && grid_[y - 1][x] == CELESTE_AIR);
                if (snow_top) {
                    SetPx003(fb_rgb24, x, y, 190, 225, 255);
                } else {
                    SetPx003(fb_rgb24, x, y, 68, 88, 128);
                }
            } else if (grid_[y][x] == CELESTE_SPIKE) {
                SetPx003(fb_rgb24, x, y, 235, 55, 65);
            }
        }
    }

    // Dash crystal
    if (crystal_present_) {
        if (crystal_cooldown_ <= 0.0f) {
            SetPx003(fb_rgb24, crystal_x_, crystal_y_, 80, 255, 160);
        } else {
            SetPx003(fb_rgb24, crystal_x_, crystal_y_, 35, 70, 60);
        }
    }

    // Golden strawberry / summit flag
    uint8_t pulse = (uint8_t)(200 + (int)(sinf(anim_timer_ * 8.0f) * 45.0f));
    SetPx003(fb_rgb24, goal_x_, goal_y_, 255, pulse, 20);

    // Dash trail
    for (int i = 0; i < kMaxTrail; ++i) {
        if (trails_[i].active) {
            int tx = (int)roundf(trails_[i].x);
            int ty = (int)roundf(trails_[i].y);
            if (trails_[i].pink) {
                SetPx003(fb_rgb24, tx, ty, 255, 105, 180);
            } else {
                SetPx003(fb_rgb24, tx, ty, 0, 220, 255);
            }
        }
    }

    // Player (bright cyan/pink when dash_ready_, dim blue when spent)
    int px = (int)roundf(player_x_);
    int py = (int)roundf(player_y_);
    if (dash_ready_) {
        SetPx003(fb_rgb24, px, py, 0, 245, 255);
    } else {
        SetPx003(fb_rgb24, px, py, 65, 115, 200);
    }

    // HUD: Lives at top-left (x=0..2, y=0), Room indicator at top-right (x=13..15)
    for (int i = 0; i < (int)lives_ && i < 3; ++i) {
        SetPx003(fb_rgb24, i, 0, 255, 90, 120);
    }
    for (int r = 0; r <= room_idx_ && r < kNumRooms; ++r) {
        SetPx003(fb_rgb24, 15 - r, 0, 255, 215, 0);
    }

    if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPx003(fb_rgb24, 6, y, 250, 250, 250);
            SetPx003(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game003CelesteDash::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = lives_;
    st.state = (uint8_t)state_;
    if (state_ == STATE_VICTORY) {
        st.progress = 100;
    } else {
        st.progress = (uint8_t)((room_idx_ * 100) / kNumRooms);
    }
    return st;
}

static_assert(sizeof(Game003CelesteDash) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
