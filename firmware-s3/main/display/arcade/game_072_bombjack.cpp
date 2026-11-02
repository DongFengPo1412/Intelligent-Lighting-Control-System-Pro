#include "game_072_bombjack.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game072BombJack::Game072BombJack()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(8500),
      lives_(3),
      px_(7.5f),
      py_(14.0f),
      pvy_(0.0f),
      on_ground_(true),
      is_gliding_(false),
      facing_(1),
      lit_bombs_collected_(0),
      combo_multiplier_(1),
      power_ball_spawned_(false),
      pb_x_(7.5f),
      pb_y_(-2.0f),
      pb_vy_(2.0f),
      power_ball_timer_(0.0f) {
}

void Game072BombJack::Init() {
    Reset();
}

void Game072BombJack::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    lives_ = 3;
    InitStage();
}

void Game072BombJack::InitStage() {
    px_ = 7.5f;
    py_ = 14.0f;
    pvy_ = 0.0f;
    on_ground_ = true;
    is_gliding_ = false;
    facing_ = 1;
    lit_bombs_collected_ = 0;
    combo_multiplier_ = 1;
    power_ball_spawned_ = false;
    power_ball_timer_ = 0.0f;

    // Distribute 8 bombs
    bombs_[0] = {3.0f, 10.0f, true, true};   // Initially lit!
    bombs_[1] = {12.0f, 10.0f, false, true};
    bombs_[2] = {2.5f, 5.0f, false, true};
    bombs_[3] = {12.5f, 5.0f, false, true};
    bombs_[4] = {7.0f, 3.0f, false, true};
    bombs_[5] = {8.5f, 3.0f, false, true};
    bombs_[6] = {4.0f, 14.0f, false, true};
    bombs_[7] = {11.0f, 14.0f, false, true};

    // Enemies
    enemies_[0] = {2.0f, 2.0f, 2.5f, 1.8f, 0, false, true};  // Flying bird
    enemies_[1] = {13.0f, 8.0f, -2.0f, 0.0f, 1, false, true}; // Mummy
    enemies_[2] = {7.0f, 9.0f, -1.8f, 2.0f, 2, false, true};  // Mech sphere
}

int Game072BombJack::GetBombsRemaining() const {
    int count = 0;
    for (int i = 0; i < MAX_BOMBS; ++i) {
        if (bombs_[i].active) count++;
    }
    return count;
}

void Game072BombJack::LightNextBomb() {
    // Light next available unlit bomb
    for (int i = 0; i < MAX_BOMBS; ++i) {
        if (bombs_[i].active && !bombs_[i].is_lit) {
            bombs_[i].is_lit = true;
            return;
        }
    }
}

void Game072BombJack::Jump() {
    if (on_ground_) {
        pvy_ = -12.5f; // Super high jump!
        on_ground_ = false;
        is_gliding_ = false;
    }
}

void Game072BombJack::GlideBrake() {
    if (!on_ground_) {
        // Wing flutter brake
        pvy_ = std::max(-3.0f, pvy_ * 0.4f - 2.0f);
        is_gliding_ = true;
    }
}

void Game072BombJack::DiveStomp() {
    if (!on_ground_) {
        pvy_ = 14.0f; // Rapid dive stomp!
        is_gliding_ = false;
    }
}

void Game072BombJack::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_DEAD) {
        if (state_timer_ > 1.8f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                state_timer_ = 0.0f;
                px_ = 7.5f;
                py_ = 14.0f;
                pvy_ = 0.0f;
                on_ground_ = true;
            } else {
                state_ = STATE_START;
            }
        }
        return;
    }

    if (state_ == STATE_VICTORY) {
        if (state_timer_ > 2.5f) {
            state_ = STATE_PLAYING;
            state_timer_ = 0.0f;
            InitStage();
        }
        return;
    }

    // Power Ball timer
    if (power_ball_timer_ > 0.0f) {
        power_ball_timer_ -= dt;
        if (power_ball_timer_ <= 0.0f) {
            for (int i = 0; i < MAX_ENEMIES; ++i) {
                enemies_[i].is_frozen = false;
            }
        }
    }

    UpdatePlayer(dt, buttons, prev_buttons);
    UpdateEnemies(dt);
    UpdatePowerBall(dt);
    CheckCollisions();
}

void Game072BombJack::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    float move_speed = 6.0f;

    if (buttons & BUTTON_LEFT)  { px_ -= move_speed * dt; facing_ = -1; }
    if (buttons & BUTTON_RIGHT) { px_ += move_speed * dt; facing_ = 1; }

    px_ = std::max(0.5f, std::min(15.0f, px_));

    // Gravity
    float grav = is_gliding_ ? 6.0f : 20.0f;
    pvy_ += grav * dt;
    py_ += pvy_ * dt;

    // Platform landing check
    on_ground_ = false;
    if (pvy_ >= 0.0f) {
        if (py_ >= 14.0f) {
            py_ = 14.0f;
            pvy_ = 0.0f;
            on_ground_ = true;
            is_gliding_ = false;
        } else if (py_ >= 10.0f && py_ <= 10.6f && ((px_ >= 1.8f && px_ <= 6.2f) || (px_ >= 8.8f && px_ <= 13.2f))) {
            py_ = 10.0f;
            pvy_ = 0.0f;
            on_ground_ = true;
            is_gliding_ = false;
        } else if (py_ >= 5.0f && py_ <= 5.6f && ((px_ >= 0.8f && px_ <= 4.2f) || (px_ >= 10.8f && px_ <= 14.2f))) {
            py_ = 5.0f;
            pvy_ = 0.0f;
            on_ground_ = true;
            is_gliding_ = false;
        } else if (py_ >= 3.0f && py_ <= 3.6f && (px_ >= 5.8f && px_ <= 9.2f)) {
            py_ = 3.0f;
            pvy_ = 0.0f;
            on_ground_ = true;
            is_gliding_ = false;
        }
    }

    // Button A: Jump / Glide Brake
    if ((buttons & BUTTON_A) && !(prev_buttons & BUTTON_A)) {
        if (on_ground_) Jump();
        else GlideBrake();
    }

    // Button B: Dive Stomp
    if ((buttons & BUTTON_B) && !(prev_buttons & BUTTON_B)) {
        DiveStomp();
    }
}

void Game072BombJack::UpdateEnemies(float dt) {
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;

        if (enemies_[i].is_frozen) {
            // Immobile coin bonus
            continue;
        }

        enemies_[i].x += enemies_[i].vx * dt;
        enemies_[i].y += enemies_[i].vy * dt;

        // Bouncing in arena bounds
        if (enemies_[i].x <= 1.0f) {
            enemies_[i].x = 1.0f;
            enemies_[i].vx = std::abs(enemies_[i].vx);
        } else if (enemies_[i].x >= 14.5f) {
            enemies_[i].x = 14.5f;
            enemies_[i].vx = -std::abs(enemies_[i].vx);
        }

        if (enemies_[i].y <= 1.0f) {
            enemies_[i].y = 1.0f;
            enemies_[i].vy = std::abs(enemies_[i].vy);
        } else if (enemies_[i].y >= 14.0f) {
            enemies_[i].y = 14.0f;
            enemies_[i].vy = -std::abs(enemies_[i].vy);
        }
    }
}

void Game072BombJack::UpdatePowerBall(float dt) {
    if (!power_ball_spawned_) return;

    pb_y_ += pb_vy_ * dt;
    if (pb_y_ > 15.5f) {
        power_ball_spawned_ = false;
    }
}

void Game072BombJack::CheckCollisions() {
    // 1. Bomb collections
    for (int i = 0; i < MAX_BOMBS; ++i) {
        if (!bombs_[i].active) continue;

        if (std::abs(px_ - bombs_[i].x) < 1.1f && std::abs(py_ - bombs_[i].y) < 1.1f) {
            bombs_[i].active = false;

            if (bombs_[i].is_lit) {
                // Lit fuse bomb bonus!
                score_ += 200 * combo_multiplier_;
                combo_multiplier_ = std::min(4, combo_multiplier_ + 1);
                lit_bombs_collected_++;
                LightNextBomb();

                // Spawn Power Ball on 3 lit bombs
                if (lit_bombs_collected_ == 3 && !power_ball_spawned_) {
                    power_ball_spawned_ = true;
                    pb_x_ = px_;
                    pb_y_ = 1.0f;
                    pb_vy_ = 2.5f;
                }
            } else {
                // Normal unlit bomb
                score_ += 100;
                combo_multiplier_ = 1;
            }

            if (GetBombsRemaining() == 0) {
                state_ = STATE_VICTORY;
                state_timer_ = 0.0f;
                score_ += 3500;
                if (score_ > high_score_) high_score_ = score_;
                return;
            }
        }
    }

    // 2. Power Ball collection
    if (power_ball_spawned_) {
        if (std::abs(px_ - pb_x_) < 1.2f && std::abs(py_ - pb_y_) < 1.2f) {
            power_ball_spawned_ = false;
            power_ball_timer_ = 5.0f;
            score_ += 1000;
            // Freeze all enemies into coins!
            for (int i = 0; i < MAX_ENEMIES; ++i) {
                enemies_[i].is_frozen = true;
            }
        }
    }

    // 3. Enemy collisions
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;

        if (std::abs(px_ - enemies_[i].x) < 1.0f && std::abs(py_ - enemies_[i].y) < 1.0f) {
            if (enemies_[i].is_frozen) {
                // Collect frozen coin enemy!
                enemies_[i].active = false;
                score_ += 500;
            } else {
                // Lethal collision!
                lives_--;
                state_ = STATE_DEAD;
                state_timer_ = 0.0f;
                return;
            }
        }
    }
}

void Game072BombJack::Render(uint8_t* fb) {
    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // 1. Pyramids of Giza Background
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (y >= 10) set_pixel(x, y, 160, 120, 50); // Desert sand
            else set_pixel(x, y, 30, 80, 160);          // Twilight blue sky
        }
    }

    // 2. Platforms
    for (int x = 0; x < 16; ++x) set_pixel(x, 15, 180, 140, 60);
    for (int x = 2; x <= 6; ++x) set_pixel(x, 11, 200, 180, 80);
    for (int x = 9; x <= 13; ++x) set_pixel(x, 11, 200, 180, 80);
    for (int x = 1; x <= 4; ++x) set_pixel(x, 6, 200, 180, 80);
    for (int x = 11; x <= 14; ++x) set_pixel(x, 6, 200, 180, 80);
    for (int x = 6; x <= 9; ++x) set_pixel(x, 4, 200, 180, 80);

    // 3. Bombs
    for (int i = 0; i < MAX_BOMBS; ++i) {
        if (!bombs_[i].active) continue;
        int bx = int(std::round(bombs_[i].x));
        int by = int(std::round(bombs_[i].y));

        // Black round bomb
        set_pixel(bx, by, 30, 30, 40);

        if (bombs_[i].is_lit) {
            // Sparking red/yellow fuse
            bool spark = (int(state_timer_ * 20.0f) % 2 == 0);
            set_pixel(bx, by - 1, spark ? 255 : 255, spark ? 50 : 220, 0);
        } else {
            set_pixel(bx, by - 1, 140, 100, 40); // Dull wick
        }
    }

    // 4. Power Ball "P"
    if (power_ball_spawned_) {
        int px = int(std::round(pb_x_));
        int py = int(std::round(pb_y_));
        set_pixel(px, py, 255, 215, 0);       // Gold
        set_pixel(px, py - 1, 255, 255, 255); // "P" glint
    }

    // 5. Enemies
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;
        int ex = int(std::round(enemies_[i].x));
        int ey = int(std::round(enemies_[i].y));

        if (enemies_[i].is_frozen) {
            // Gold smiling face coin
            set_pixel(ex, ey, 255, 220, 0);
            set_pixel(ex, ey - 1, 255, 255, 100);
        } else {
            if (enemies_[i].type == 0) {
                // Flying bird: Cyan/Red
                set_pixel(ex, ey, 40, 200, 220);
                set_pixel(ex - 1, ey, 220, 40, 40);
                set_pixel(ex + 1, ey, 220, 40, 40);
            } else if (enemies_[i].type == 1) {
                // Mummy: White bandage
                set_pixel(ex, ey, 220, 220, 200);
                set_pixel(ex, ey - 1, 255, 50, 50); // Red eyes
            } else {
                // Mech sphere: Metallic orange
                set_pixel(ex, ey, 240, 100, 30);
                set_pixel(ex, ey - 1, 255, 200, 50);
            }
        }
    }

    // 6. Jack (Blue superhero costume with red cape)
    if (state_ != STATE_DEAD) {
        int jx = int(std::round(px_));
        int jy = int(std::round(py_));

        set_pixel(jx, jy, 40, 100, 240);              // Blue bodysuit
        set_pixel(jx - facing_, jy, 220, 30, 30);     // Red cape fluttering
        set_pixel(jx, jy - 1, 255, 220, 160);         // Face
        set_pixel(jx, jy - 2, 240, 220, 40);          // Gold cowl/helmet
    } else {
        int jx = int(std::round(px_));
        int jy = int(std::round(py_));
        set_pixel(jx, jy, 255, 50, 50);
    }
}

} // namespace arcade
