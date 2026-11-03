#include "game_186_championbaseball.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

static constexpr uint16_t BTN_UP    = 1 << 0;
static constexpr uint16_t BTN_DOWN  = 1 << 1;
static constexpr uint16_t BTN_LEFT  = 1 << 2;
static constexpr uint16_t BTN_RIGHT = 1 << 3;
static constexpr uint16_t BTN_A     = 1 << 4; // Swing
static constexpr uint16_t BTN_B     = 1 << 5; // Bunt

Game186ChampionBaseball::Game186ChampionBaseball() {
    Init();
}

void Game186ChampionBaseball::Init() {
    Reset();
}

void Game186ChampionBaseball::Reset() {
    score_ = 0;
    inning_ = 1;
    outs_ = 0;
    strikes_ = 0;
    balls_ = 0;
    bases_[0] = false;
    bases_[1] = false;
    bases_[2] = false;
    InitAtBat();
}

void Game186ChampionBaseball::InitAtBat() {
    state_ = STATE_PITCHING;
    state_timer_ = 0.0f;
    batter_x_ = 7.5f;
    batter_y_ = 13.0f;
    is_swinging_ = false;
    swing_timer_ = 0.0f;

    pitcher_x_ = 7.5f;
    pitcher_y_ = 4.0f;
    ball_x_ = pitcher_x_;
    ball_y_ = pitcher_y_;
    ball_vx_ = 0.0f;
    ball_vy_ = 0.0f;
    ball_active_ = false;
    is_hit_ = false;
    pitch_cooldown_ = 0.6f;
}

void Game186ChampionBaseball::PitchBall() {
    ball_active_ = true;
    ball_x_ = pitcher_x_;
    ball_y_ = pitcher_y_;
    float curve = (static_cast<float>((strikes_ * 3 + balls_ * 7) % 5) - 2.0f) * 0.4f;
    ball_vx_ = curve;
    ball_vy_ = 12.0f + static_cast<float>(inning_ % 3) * 1.5f;
}

void Game186ChampionBaseball::AdvanceRunners(int bases_hit) {
    int runs = 0;
    for (int b = 2; b >= 0; --b) {
        if (bases_[b]) {
            bases_[b] = false;
            int target = b + bases_hit;
            if (target >= 3) {
                runs++;
            } else {
                bases_[target] = true;
            }
        }
    }

    if (bases_hit >= 4) {
        runs++;
    } else {
        bases_[bases_hit - 1] = true;
    }

    score_ += runs * 1000 + bases_hit * 200;
}

void Game186ChampionBaseball::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_INNING_END) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            inning_++;
            if (inning_ > 9) {
                state_ = STATE_GAME_OVER;
            } else {
                outs_ = 0;
                strikes_ = 0;
                balls_ = 0;
                bases_[0] = false;
                bases_[1] = false;
                bases_[2] = false;
                InitAtBat();
            }
        }
        return;
    }

    if (state_ == STATE_GAME_OVER) {
        if (((buttons & BTN_A) && !(prev_buttons & BTN_A)) ||
            ((buttons & BTN_B) && !(prev_buttons & BTN_B))) {
            Reset();
        }
        return;
    }

    // Stance left/right
    if (buttons & BTN_LEFT) {
        batter_x_ = std::max(5.0f, batter_x_ - 6.0f * dt);
    }
    if (buttons & BTN_RIGHT) {
        batter_x_ = std::min(10.0f, batter_x_ + 6.0f * dt);
    }

    uint16_t pressed = buttons & ~prev_buttons;
    int swing_type = 0;
    if ((pressed & BTN_A) && !is_swinging_) {
        is_swinging_ = true;
        swing_timer_ = 0.22f;
        swing_type = 1;
    } else if ((pressed & BTN_B) && !is_swinging_) {
        is_swinging_ = true;
        swing_timer_ = 0.35f;
        swing_type = 2;
    }

    if (is_swinging_) {
        swing_timer_ -= dt;
        if (swing_timer_ <= 0.0f) {
            is_swinging_ = false;
        }
    }

    if (state_ == STATE_PITCHING) {
        if (!ball_active_) {
            pitch_cooldown_ -= dt;
            if (pitch_cooldown_ <= 0.0f) {
                PitchBall();
            }
        } else {
            ball_x_ += ball_vx_ * dt;
            ball_y_ += ball_vy_ * dt;

            // Bat contact
            if (is_swinging_ && (ball_y_ >= 12.0f && ball_y_ <= 13.8f)) {
                float dist = std::abs(ball_x_ - batter_x_);
                if (dist <= 1.5f) {
                    is_hit_ = true;
                    state_ = STATE_BALL_IN_PLAY;
                    float offset = ball_x_ - batter_x_;
                    if (swing_type == 2) { // Bunt
                        ball_vx_ = offset * 2.0f;
                        ball_vy_ = -4.0f;
                        ball_air_timer_ = 0.8f;
                    } else { // Full swing
                        ball_vx_ = offset * 8.0f;
                        ball_vy_ = -14.0f;
                        ball_air_timer_ = (dist < 0.6f) ? 1.4f : 0.9f;
                    }
                    return;
                }
            }

            // Crosses plate
            if (ball_y_ >= 14.5f) {
                ball_active_ = false;
                if (ball_x_ >= 6.0f && ball_x_ <= 9.0f) {
                    strikes_++;
                    if (strikes_ >= 3) {
                        outs_++;
                        strikes_ = 0;
                        balls_ = 0;
                        if (outs_ >= 3) {
                            state_ = STATE_INNING_END;
                            state_timer_ = 1.5f;
                        } else {
                            InitAtBat();
                        }
                    } else {
                        InitAtBat();
                    }
                } else {
                    balls_++;
                    if (balls_ >= 4) {
                        strikes_ = 0;
                        balls_ = 0;
                        AdvanceRunners(1);
                        InitAtBat();
                    } else {
                        InitAtBat();
                    }
                }
            }
        }
    } else if (state_ == STATE_BALL_IN_PLAY) {
        ball_air_timer_ -= dt;
        ball_x_ += ball_vx_ * dt;
        ball_y_ += ball_vy_ * dt;

        if (ball_air_timer_ <= 0.0f) {
            if (ball_y_ < 2.0f) {
                AdvanceRunners(4); // Home Run
            } else if (ball_y_ < 5.0f) {
                AdvanceRunners(2); // Double
            } else if (ball_y_ < 9.0f) {
                AdvanceRunners(1); // Single
            } else {
                outs_++;
                if (outs_ >= 3) {
                    state_ = STATE_INNING_END;
                    state_timer_ = 1.5f;
                    return;
                }
            }
            strikes_ = 0;
            balls_ = 0;
            InitAtBat();
        }
    }
}

void Game186ChampionBaseball::Render(uint8_t* fb) {
    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx]     = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Field background
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (y <= 5) {
                set_pixel(x, y, 30, 110, 40);
            } else if (y >= 6 && y <= 11) {
                if (x >= 4 && x <= 11) {
                    set_pixel(x, y, 160, 100, 50);
                } else {
                    set_pixel(x, y, 30, 110, 40);
                }
            } else {
                set_pixel(x, y, 140, 90, 40);
            }
        }
    }

    // Bases
    set_pixel(7, 13, 255, 255, 255);
    set_pixel(12, 9, 255, 255, bases_[0] ? 0 : 255);
    set_pixel(7, 6, 255, 255, bases_[1] ? 0 : 255);
    set_pixel(2, 9, 255, 255, bases_[2] ? 0 : 255);

    // Pitcher
    int px = static_cast<int>(std::round(pitcher_x_));
    int py = static_cast<int>(std::round(pitcher_y_));
    set_pixel(px, py, 40, 100, 220);
    set_pixel(px, py + 1, 230, 230, 230);

    // Batter
    int bx = static_cast<int>(std::round(batter_x_));
    int by = static_cast<int>(std::round(batter_y_));
    set_pixel(bx, by, 220, 40, 40);
    set_pixel(bx, by + 1, 240, 240, 240);
    if (is_swinging_) {
        set_pixel(bx - 1, by, 200, 150, 60);
        set_pixel(bx + 1, by, 200, 150, 60);
    } else {
        set_pixel(bx + 1, by - 1, 200, 150, 60);
    }

    // Ball
    if (ball_active_ || state_ == STATE_BALL_IN_PLAY) {
        int b_x = static_cast<int>(std::round(ball_x_));
        int b_y = static_cast<int>(std::round(ball_y_));
        set_pixel(b_x, b_y, 255, 255, 255);
    }

    // Scoreboard counts
    for (int s = 0; s < strikes_; ++s) {
        set_pixel(s, 0, 255, 50, 50);
    }
    for (int bl = 0; bl < balls_; ++bl) {
        set_pixel(15 - bl, 0, 50, 255, 50);
    }
    for (int o = 0; o < outs_; ++o) {
        set_pixel(o, 1, 255, 140, 0);
    }
}

} // namespace arcade
