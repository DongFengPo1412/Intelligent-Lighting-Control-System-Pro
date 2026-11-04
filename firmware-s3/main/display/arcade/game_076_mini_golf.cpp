// game_076_mini_golf.cpp —— 目标 #076 迷你高尔夫 (Mini Golf, 1987)
#include "game_076_mini_golf.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>
#include <math.h>

namespace arcade {

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

static const float kPowerSpeeds[3] = {6.5f, 10.5f, 14.5f};

static inline void SetPixel76(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

Game076MiniGolf::Game076MiniGolf()
    : state_(STATE_TITLE),
      hole_index_(0),
      hole_strokes_(0),
      total_strokes_(0),
      ball_x_(3.5f),
      ball_y_(12.5f),
      ball_vx_(0.0f),
      ball_vy_(0.0f),
      saved_x_(3.5f),
      saved_y_(12.5f),
      cup_x_(12.5f),
      cup_y_(3.5f),
      ball_moving_(false),
      aim_angle_(14),
      power_level_(1),
      splash_timer_(0.0f),
      sink_flash_timer_(0.0f),
      score_(0),
      high_score_(0),
      state_timer_(0.0f),
      anim_timer_(0.0f) {
    InitGameData();
}

void Game076MiniGolf::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

void Game076MiniGolf::LoadHole(int idx) {
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (x == 0 || x == 15 || y == 0 || y == 15) {
                tiles_[y][x] = GOLF_WALL;
            } else {
                tiles_[y][x] = GOLF_FAIRWAY;
            }
        }
    }

    hole_strokes_ = 0;
    ball_vx_ = 0.0f;
    ball_vy_ = 0.0f;
    ball_moving_ = false;

    if (idx == 0) {
        // Hole 1: Diagonal Par 2 with side sand bunker & pond
        ball_x_ = 3.5f; ball_y_ = 12.5f;
        cup_x_ = 12.5f; cup_y_ = 3.5f;
        aim_angle_ = 14;
        for (int y = 11; y <= 13; ++y) {
            for (int x = 8; x <= 11; ++x) tiles_[y][x] = GOLF_SAND;
        }
        for (int y = 4; y <= 6; ++y) {
            for (int x = 3; x <= 5; ++x) tiles_[y][x] = GOLF_WATER;
        }
    } else if (idx == 1) {
        // Hole 2: U-Bend wooden divider
        ball_x_ = 3.5f; ball_y_ = 12.5f;
        cup_x_ = 12.5f; cup_y_ = 12.5f;
        aim_angle_ = 12;
        for (int y = 6; y <= 14; ++y) {
            tiles_[y][7] = GOLF_WALL;
            tiles_[y][8] = GOLF_WALL;
        }
        tiles_[2][7] = GOLF_SAND;
        tiles_[2][8] = GOLF_SAND;
        tiles_[13][6] = GOLF_WATER;
        tiles_[14][6] = GOLF_WATER;
        tiles_[13][9] = GOLF_WATER;
        tiles_[14][9] = GOLF_WATER;
    } else if (idx == 2) {
        // Hole 3: Twin Lakes Island Bridge
        ball_x_ = 7.5f; ball_y_ = 13.5f;
        cup_x_ = 7.5f; cup_y_ = 2.5f;
        aim_angle_ = 12;
        for (int y = 5; y <= 10; ++y) {
            for (int x = 2; x <= 4; ++x) tiles_[y][x] = GOLF_WATER;
            for (int x = 11; x <= 13; ++x) tiles_[y][x] = GOLF_WATER;
        }
        tiles_[8][7] = GOLF_SAND;
        tiles_[8][8] = GOLF_SAND;
    } else {
        // Hole 4: Chicane Wooden Baffles
        ball_x_ = 3.5f; ball_y_ = 13.5f;
        cup_x_ = 12.5f; cup_y_ = 2.5f;
        aim_angle_ = 0;
        for (int x = 1; x <= 9; ++x) tiles_[9][x] = GOLF_WALL;
        for (int x = 6; x <= 14; ++x) tiles_[5][x] = GOLF_WALL;
        for (int y = 11; y <= 12; ++y) {
            for (int x = 12; x <= 13; ++x) tiles_[y][x] = GOLF_SAND;
        }
        for (int y = 2; y <= 3; ++y) {
            for (int x = 2; x <= 3; ++x) tiles_[y][x] = GOLF_WATER;
        }
    }

    saved_x_ = ball_x_;
    saved_y_ = ball_y_;
}

void Game076MiniGolf::InitGameData() {
    hole_index_ = 0;
    hole_strokes_ = 0;
    total_strokes_ = 0;
    power_level_ = 1;
    splash_timer_ = 0.0f;
    sink_flash_timer_ = 0.0f;
    score_ = 0;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    LoadHole(0);
}

void Game076MiniGolf::Init() {
    Reset();
}

void Game076MiniGolf::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    state_ = STATE_TITLE;
    InitGameData();
}

void Game076MiniGolf::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        InitGameData();
        state_ = STATE_PLAYING;
    }
}

void Game076MiniGolf::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game076MiniGolf::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

bool Game076MiniGolf::IsWallAt(float px, float py) const {
    int gx = (int)floorf(px);
    int gy = (int)floorf(py);
    if (gx < 0 || gx >= 16 || gy < 0 || gy >= 16) return true;
    return tiles_[gy][gx] == GOLF_WALL;
}

void Game076MiniGolf::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    (void)keys_down;
    if (dt > 0.05f) dt = 0.05f;

    if (state_ == STATE_PAUSED) {
        if (keys_pressed & KEY_START) {
            state_ = STATE_PLAYING;
        }
        return;
    }

    state_timer_ += dt;
    anim_timer_ += dt;
    if (splash_timer_ > 0.0f) splash_timer_ = fmaxf(0.0f, splash_timer_ - dt);
    if (sink_flash_timer_ > 0.0f) sink_flash_timer_ = fmaxf(0.0f, sink_flash_timer_ - dt);

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

    if (state_ == STATE_PLAYING) {
        if (keys_pressed & KEY_START) {
            state_ = STATE_PAUSED;
            return;
        }

        if (!ball_moving_) {
            if (keys_pressed & KEY_LEFT) {
                aim_angle_ = (aim_angle_ + 15) % 16;
            }
            if (keys_pressed & KEY_RIGHT) {
                aim_angle_ = (aim_angle_ + 1) % 16;
            }
            if (keys_pressed & (KEY_UP | KEY_B)) {
                power_level_ = (power_level_ + 1) % 3;
            }
            if (keys_pressed & KEY_DOWN) {
                power_level_ = (power_level_ + 2) % 3;
            }

            if (keys_pressed & KEY_A) {
                saved_x_ = ball_x_;
                saved_y_ = ball_y_;
                hole_strokes_++;
                total_strokes_++;
                float rad = (float)aim_angle_ * ((float)M_PI / 8.0f);
                float spd = kPowerSpeeds[power_level_];
                ball_vx_ = cosf(rad) * spd;
                ball_vy_ = sinf(rad) * spd;
                ball_moving_ = true;
            }
        } else {
            const int kSubSteps = 4;
            float sub_dt = dt / (float)kSubSteps;

            for (int s = 0; s < kSubSteps; ++s) {
                float nx = ball_x_ + ball_vx_ * sub_dt;
                if (IsWallAt(nx, ball_y_)) {
                    ball_vx_ = -ball_vx_ * 0.82f;
                } else {
                    ball_x_ = nx;
                }

                float ny = ball_y_ + ball_vy_ * sub_dt;
                if (IsWallAt(ball_x_, ny)) {
                    ball_vy_ = -ball_vy_ * 0.82f;
                } else {
                    ball_y_ = ny;
                }

                int gx = (int)floorf(ball_x_);
                int gy = (int)floorf(ball_y_);
                if (gx < 0) gx = 0;
                if (gx > 15) gx = 15;
                if (gy < 0) gy = 0;
                if (gy > 15) gy = 15;

                // Water hazard: 1-stroke penalty + reset to pre-shot spot
                if (tiles_[gy][gx] == GOLF_WATER) {
                    hole_strokes_++;
                    total_strokes_++;
                    ball_x_ = saved_x_;
                    ball_y_ = saved_y_;
                    ball_vx_ = 0.0f;
                    ball_vy_ = 0.0f;
                    ball_moving_ = false;
                    splash_timer_ = 0.30f;

                    if (total_strokes_ >= kMaxTotalStrokes) {
                        state_ = STATE_GAMEOVER;
                        state_timer_ = 0.0f;
                    }
                    return;
                }

                // Cup check
                float dx_cup = ball_x_ - cup_x_;
                float dy_cup = ball_y_ - cup_y_;
                float dist_cup = sqrtf(dx_cup * dx_cup + dy_cup * dy_cup);
                float spd = sqrtf(ball_vx_ * ball_vx_ + ball_vy_ * ball_vy_);

                if (dist_cup < 0.72f) {
                    if (spd <= 12.8f) {
                        // Sinks into cup!
                        int raw_pts = 150 - hole_strokes_ * 20;
                        uint32_t pts = (raw_pts > 20) ? (uint32_t)raw_pts : 20u;
                        AddScore(pts);
                        sink_flash_timer_ = 0.30f;
                        ball_moving_ = false;
                        ball_vx_ = 0.0f;
                        ball_vy_ = 0.0f;
                        hole_index_++;

                        if (hole_index_ >= kTotalHoles) {
                            if (total_strokes_ <= kMaxTotalStrokes) {
                                state_ = STATE_VICTORY;
                            } else {
                                state_ = STATE_GAMEOVER;
                            }
                            state_timer_ = 0.0f;
                            return;
                        }

                        if (total_strokes_ >= kMaxTotalStrokes) {
                            state_ = STATE_GAMEOVER;
                            state_timer_ = 0.0f;
                            return;
                        }

                        LoadHole(hole_index_);
                        return;
                    } else {
                        // Lip-out if speed is excessive
                        ball_vx_ *= 0.55f;
                        ball_vy_ *= 0.55f;
                    }
                }

                // Surface friction damping (high friction in sand bunkers!)
                float decel = (tiles_[gy][gx] == GOLF_SAND) ? 22.0f : 6.0f;
                if (spd > 0.0f) {
                    float new_spd = spd - decel * sub_dt;
                    if (new_spd <= 0.30f) {
                        ball_vx_ = 0.0f;
                        ball_vy_ = 0.0f;
                        ball_moving_ = false;
                        if (total_strokes_ >= kMaxTotalStrokes) {
                            state_ = STATE_GAMEOVER;
                            state_timer_ = 0.0f;
                        }
                        return;
                    } else {
                        float ratio = new_spd / spd;
                        ball_vx_ *= ratio;
                        ball_vy_ *= ratio;
                    }
                }
            }
        }
    }
}

void Game076MiniGolf::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    // Course terrain
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            uint8_t t = tiles_[y][x];
            if (t == GOLF_WALL) {
                uint8_t wr = ((x + y) % 2 == 0) ? 145 : 120;
                SetPixel76(fb_rgb24, x, y, wr, 78, 32);
            } else if (t == GOLF_SAND) {
                SetPixel76(fb_rgb24, x, y, 235, 200, 85);
            } else if (t == GOLF_WATER) {
                uint8_t wb = (((int)(anim_timer_ * 4.0f) + x + y) % 2 == 0) ? 235 : 195;
                SetPixel76(fb_rgb24, x, y, 25, 115, wb);
            } else {
                uint8_t fg = ((x + y) % 2 == 0) ? 155 : 138;
                if (sink_flash_timer_ > 0.0f) fg = 210;
                SetPixel76(fb_rgb24, x, y, 32, fg, 55);
            }
        }
    }

    // Cup & red flagstick
    int cx = (int)floorf(cup_x_);
    int cy = (int)floorf(cup_y_);
    SetPixel76(fb_rgb24, cx, cy, 15, 20, 15);
    SetPixel76(fb_rgb24, cx, cy - 1, 245, 45, 45);

    // Dotted aim line when ball is at rest
    if (state_ == STATE_PLAYING && !ball_moving_) {
        float rad = (float)aim_angle_ * ((float)M_PI / 8.0f);
        int dots = 2 + power_level_;
        uint8_t ar = (power_level_ == 0) ? 80 : ((power_level_ == 1) ? 255 : 255);
        uint8_t ag = (power_level_ == 0) ? 230 : ((power_level_ == 1) ? 220 : 85);
        uint8_t ab = (power_level_ == 0) ? 255 : ((power_level_ == 1) ? 40 : 30);

        for (int d = 1; d <= dots; ++d) {
            int ax = (int)floorf(ball_x_ + cosf(rad) * (float)d * 1.15f);
            int ay = (int)floorf(ball_y_ + sinf(rad) * (float)d * 1.15f);
            if (ax > 0 && ax < 15 && ay > 0 && ay < 15 && tiles_[ay][ax] != GOLF_WALL) {
                SetPixel76(fb_rgb24, ax, ay, ar, ag, ab);
            } else {
                break;
            }
        }
    }

    // Golf ball
    int bx = (int)floorf(ball_x_);
    int by = (int)floorf(ball_y_);
    if (splash_timer_ > 0.0f) {
        SetPixel76(fb_rgb24, bx, by, 140, 220, 255);
    } else {
        SetPixel76(fb_rgb24, bx, by, 255, 255, 255);
    }

    // Top wall HUD: hole progress on left (gold), remaining stroke budget on right (cyan)
    for (int h = 0; h < kTotalHoles; ++h) {
        if (h < hole_index_) {
            SetPixel76(fb_rgb24, 1 + h, 0, 46, 230, 113);
        } else if (h == hole_index_) {
            SetPixel76(fb_rgb24, 1 + h, 0, 255, 215, 0);
        }
    }
    int rem = kMaxTotalStrokes - total_strokes_;
    if (rem < 0) rem = 0;
    int bars = (rem + 2) / 3;
    for (int b = 0; b < bars && b < 6; ++b) {
        SetPixel76(fb_rgb24, 14 - b, 0, 0, 215, 255);
    }

    if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPixel76(fb_rgb24, 6, y, 250, 250, 250);
            SetPixel76(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game076MiniGolf::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    int rem = kMaxTotalStrokes - total_strokes_;
    st.lives = (state_ == STATE_GAMEOVER || rem <= 0) ? 0 : (uint8_t)rem;
    st.state = (uint8_t)state_;
    int prog = (hole_index_ * 100) / kTotalHoles;
    if (prog > 100) prog = 100;
    st.progress = (uint8_t)prog;
    return st;
}

static_assert(sizeof(Game076MiniGolf) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
