#include "game_067_snowbros.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game067SnowBros::Game067SnowBros()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(5500),
      lives_(3),
      px_(2.0f),
      py_(14.0f),
      pvy_(0.0f),
      on_ground_(true),
      facing_(1),
      shoot_cooldown_(0.0f),
      has_speed_potion_(false),
      has_power_potion_(false),
      has_range_potion_(false),
      enemies_defeated_(0) {
}

void Game067SnowBros::Init() {
    Reset();
}

void Game067SnowBros::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    lives_ = 3;
    InitStage();
}

void Game067SnowBros::InitStage() {
    px_ = 2.0f;
    py_ = 14.0f;
    pvy_ = 0.0f;
    on_ground_ = true;
    facing_ = 1;
    shoot_cooldown_ = 0.0f;
    has_speed_potion_ = false;
    has_power_potion_ = false;
    has_range_potion_ = false;
    enemies_defeated_ = 0;

    for (int i = 0; i < MAX_SHOTS; ++i) shots_[i].active = false;
    for (int i = 0; i < MAX_POTIONS; ++i) potions_[i].active = false;

    // Platform enemies: 2 on middle, 1 on upper, 1 on ground
    enemies_[0] = {12.0f, 14.0f, -2.5f, SNOW_NONE, false, 0.0f, 0.0f, true}; // Ground floor
    enemies_[1] = {3.0f, 9.0f, 2.5f, SNOW_NONE, false, 0.0f, 0.0f, true};   // Middle left
    enemies_[2] = {11.0f, 9.0f, -2.5f, SNOW_NONE, false, 0.0f, 0.0f, true};  // Middle right
    enemies_[3] = {7.0f, 4.0f, 2.2f, SNOW_NONE, false, 0.0f, 0.0f, true};   // Upper center
}

void Game067SnowBros::ThrowSnow() {
    if (shoot_cooldown_ > 0.0f) return;

    for (int i = 0; i < MAX_SHOTS; ++i) {
        if (!shots_[i].active) {
            shots_[i].active = true;
            shots_[i].x = px_ + facing_ * 0.8f;
            shots_[i].y = py_;
            shots_[i].vx = facing_ * (has_range_potion_ ? 16.0f : 11.0f);
            break;
        }
    }

    shoot_cooldown_ = 0.22f;
}

void Game067SnowBros::Jump() {
    if (on_ground_) {
        pvy_ = -9.2f;
        on_ground_ = false;
    }
}

static bool IsOnSolid(float x, float y) {
    int ix = int(std::round(x));
    int iy = int(std::round(y));

    // Ground floor
    if (iy == 14) return true;

    // Middle floor
    if (iy == 9 && ((ix >= 1 && ix <= 6) || (ix >= 9 && ix <= 14))) return true;

    // Upper floor
    if (iy == 4 && (ix >= 4 && ix <= 11)) return true;

    return false;
}

void Game067SnowBros::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_DEAD) {
        if (state_timer_ > 1.8f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                state_timer_ = 0.0f;
                InitStage();
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

    if (shoot_cooldown_ > 0.0f) shoot_cooldown_ -= dt;

    UpdatePlayer(dt, buttons, prev_buttons);
    UpdateProjectiles(dt);
    UpdateEnemies(dt);
    CheckCollisions();
}

void Game067SnowBros::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    float move_speed = has_speed_potion_ ? 7.5f : 5.0f;

    if (buttons & BUTTON_LEFT)  { px_ -= move_speed * dt; facing_ = -1; }
    if (buttons & BUTTON_RIGHT) { px_ += move_speed * dt; facing_ = 1; }

    px_ = std::max(0.5f, std::min(14.5f, px_));

    // Gravity & Vertical movement
    pvy_ += 24.0f * dt;
    py_ += pvy_ * dt;

    // Platform landing check
    on_ground_ = false;
    if (pvy_ >= 0.0f) {
        if (py_ >= 14.0f) {
            py_ = 14.0f;
            pvy_ = 0.0f;
            on_ground_ = true;
        } else if (py_ >= 9.0f && py_ <= 9.6f && ((px_ >= 0.8f && px_ <= 6.2f) || (px_ >= 8.8f && px_ <= 14.2f))) {
            py_ = 9.0f;
            pvy_ = 0.0f;
            on_ground_ = true;
        } else if (py_ >= 4.0f && py_ <= 4.6f && (px_ >= 3.8f && px_ <= 11.2f)) {
            py_ = 4.0f;
            pvy_ = 0.0f;
            on_ground_ = true;
        }
    }

    // Button A: Jump
    if ((buttons & BUTTON_A) && !(prev_buttons & BUTTON_A)) {
        Jump();
    }

    // Button B: Shoot Snow
    if ((buttons & BUTTON_B) && !(prev_buttons & BUTTON_B)) {
        ThrowSnow();
    }
}

void Game067SnowBros::UpdateProjectiles(float dt) {
    for (int i = 0; i < MAX_SHOTS; ++i) {
        if (!shots_[i].active) continue;
        shots_[i].x += shots_[i].vx * dt;
        if (shots_[i].x < 0.0f || shots_[i].x > 15.5f) {
            shots_[i].active = false;
        }
    }
}

void Game067SnowBros::UpdateEnemies(float dt) {
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;

        if (enemies_[i].is_rolling) {
            // Bowling ball rapid roll!
            enemies_[i].x += enemies_[i].roll_vx * dt;

            // Bounce off outer wall
            if (enemies_[i].x <= 1.0f) {
                enemies_[i].x = 1.0f;
                enemies_[i].roll_vx = std::abs(enemies_[i].roll_vx);
            } else if (enemies_[i].x >= 14.0f) {
                enemies_[i].x = 14.0f;
                enemies_[i].roll_vx = -std::abs(enemies_[i].roll_vx);
            }

            // Fall down if walked off platform
            if (!IsOnSolid(enemies_[i].x, enemies_[i].y)) {
                enemies_[i].y += 12.0f * dt;
                if (enemies_[i].y >= 14.0f) enemies_[i].y = 14.0f;
            }

            enemies_[i].melt_timer -= dt;
            if (enemies_[i].melt_timer <= 0.0f) {
                // Snowball bursts into flurry
                enemies_[i].active = false;
                enemies_defeated_++;
                score_ += 500;
                if (enemies_defeated_ >= 6) {
                    state_ = STATE_VICTORY;
                    state_timer_ = 0.0f;
                    score_ += 2500;
                    if (score_ > high_score_) high_score_ = score_;
                    return;
                }
            }
        } else if (enemies_[i].snow_stage == SNOW_FULL_BALL) {
            // Fully frozen in giant snowball: stationary, thaws slowly
            enemies_[i].melt_timer -= dt;
            if (enemies_[i].melt_timer <= 0.0f) {
                enemies_[i].snow_stage = SNOW_MEDIUM;
                enemies_[i].melt_timer = 2.0f;
            }
        } else {
            // Normal / slowed patrol
            float spd = (enemies_[i].snow_stage == SNOW_LIGHT) ? 1.2f : 2.6f;
            enemies_[i].x += (enemies_[i].vx > 0 ? spd : -spd) * dt;

            // Platform boundary patrol
            if (enemies_[i].x <= 1.0f) {
                enemies_[i].x = 1.0f;
                enemies_[i].vx = std::abs(enemies_[i].vx);
            } else if (enemies_[i].x >= 14.0f) {
                enemies_[i].x = 14.0f;
                enemies_[i].vx = -std::abs(enemies_[i].vx);
            }

            // Thawing if frosted
            if (enemies_[i].snow_stage > SNOW_NONE) {
                enemies_[i].melt_timer -= dt;
                if (enemies_[i].melt_timer <= 0.0f) {
                    enemies_[i].snow_stage--;
                    enemies_[i].melt_timer = 2.0f;
                }
            }
        }
    }
}

void Game067SnowBros::CheckCollisions() {
    // 1. Snow shots hit enemies
    for (int s = 0; s < MAX_SHOTS; ++s) {
        if (!shots_[s].active) continue;
        for (int e = 0; e < MAX_ENEMIES; ++e) {
            if (!enemies_[e].active || enemies_[e].is_rolling) continue;
            if (std::abs(shots_[s].x - enemies_[e].x) < 1.2f &&
                std::abs(shots_[s].y - enemies_[e].y) < 1.2f) {
                shots_[s].active = false;
                int boost = has_power_potion_ ? 2 : 1;
                enemies_[e].snow_stage = std::min(SNOW_FULL_BALL, enemies_[e].snow_stage + boost);
                enemies_[e].melt_timer = 3.5f;
                score_ += 50;
                break;
            }
        }
    }

    // 2. Rolling snowball sweeps enemies
    for (int r = 0; r < MAX_ENEMIES; ++r) {
        if (!enemies_[r].active || !enemies_[r].is_rolling) continue;
        for (int e = 0; e < MAX_ENEMIES; ++e) {
            if (e == r || !enemies_[e].active) continue;
            if (std::abs(enemies_[r].x - enemies_[e].x) < 1.4f &&
                std::abs(enemies_[r].y - enemies_[e].y) < 1.4f) {
                // Crushed by rolling snowball!
                enemies_[e].active = false;
                enemies_defeated_++;
                score_ += 300;

                // Chance to drop Potion
                for (int p = 0; p < MAX_POTIONS; ++p) {
                    if (!potions_[p].active) {
                        potions_[p].active = true;
                        potions_[p].x = enemies_[e].x;
                        potions_[p].y = enemies_[e].y;
                        potions_[p].type = (enemies_defeated_ % 3);
                        break;
                    }
                }

                if (enemies_defeated_ >= 6) {
                    state_ = STATE_VICTORY;
                    state_timer_ = 0.0f;
                    score_ += 2500;
                    if (score_ > high_score_) high_score_ = score_;
                    return;
                }
            }
        }
    }

    // 3. Player kicks giant snowball
    for (int e = 0; e < MAX_ENEMIES; ++e) {
        if (!enemies_[e].active || enemies_[e].is_rolling) continue;
        if (enemies_[e].snow_stage == SNOW_FULL_BALL) {
            if (std::abs(px_ - enemies_[e].x) < 1.4f &&
                std::abs(py_ - enemies_[e].y) < 1.4f) {
                // Kick snowball!
                enemies_[e].is_rolling = true;
                enemies_[e].roll_vx = (px_ < enemies_[e].x ? 12.0f : -12.0f);
                enemies_[e].melt_timer = 2.5f;
                score_ += 200;
            }
        }
    }

    // 4. Player collects Potion
    for (int p = 0; p < MAX_POTIONS; ++p) {
        if (!potions_[p].active) continue;
        if (std::abs(px_ - potions_[p].x) < 1.2f &&
            std::abs(py_ - potions_[p].y) < 1.2f) {
            potions_[p].active = false;
            if (potions_[p].type == 0) has_speed_potion_ = true;
            else if (potions_[p].type == 1) has_power_potion_ = true;
            else has_range_potion_ = true;
            score_ += 500;
            if (score_ > high_score_) high_score_ = score_;
        }
    }

    // 5. Unfrozen enemy hurts player
    for (int e = 0; e < MAX_ENEMIES; ++e) {
        if (!enemies_[e].active || enemies_[e].is_rolling || enemies_[e].snow_stage >= SNOW_MEDIUM) continue;
        if (std::abs(px_ - enemies_[e].x) < 0.9f &&
            std::abs(py_ - enemies_[e].y) < 0.9f) {
            lives_--;
            state_ = STATE_DEAD;
            state_timer_ = 0.0f;
            return;
        }
    }
}

void Game067SnowBros::Render(uint8_t* fb) {
    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // 1. Ice Castle Night Background
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            set_pixel(x, y, 10, 15, 35);
        }
    }

    // 2. Platforms (cyan icy blocks)
    // Ground floor y=15
    for (int x = 0; x < 16; ++x) {
        set_pixel(x, 15, 60, 140, 200);
    }
    // Middle floors y=10
    for (int x = 1; x <= 6; ++x)  set_pixel(x, 10, 60, 140, 200);
    for (int x = 9; x <= 14; ++x) set_pixel(x, 10, 60, 140, 200);
    // Upper floor y=5
    for (int x = 4; x <= 11; ++x) set_pixel(x, 5, 60, 140, 200);

    // 3. Potions
    for (int p = 0; p < MAX_POTIONS; ++p) {
        if (!potions_[p].active) continue;
        int px = int(std::round(potions_[p].x));
        int py = int(std::round(potions_[p].y));
        if (potions_[p].type == 0) {
            set_pixel(px, py, 255, 30, 30);   // Red
        } else if (potions_[p].type == 1) {
            set_pixel(px, py, 40, 80, 255);   // Blue
        } else {
            set_pixel(px, py, 255, 230, 20);  // Yellow
        }
    }

    // 4. Enemies
    for (int e = 0; e < MAX_ENEMIES; ++e) {
        if (!enemies_[e].active) continue;
        int ex = int(std::round(enemies_[e].x));
        int ey = int(std::round(enemies_[e].y));

        if (enemies_[e].is_rolling) {
            // Rolling giant snowball: 2x2 white/cyan ball
            for (int dy = -1; dy <= 0; ++dy) {
                for (int dx = -1; dx <= 0; ++dx) {
                    set_pixel(ex + dx, ey + dy, 240, 250, 255);
                }
            }
        } else if (enemies_[e].snow_stage == SNOW_FULL_BALL) {
            // Stationary giant snowball
            for (int dy = -1; dy <= 0; ++dy) {
                for (int dx = -1; dx <= 0; ++dx) {
                    set_pixel(ex + dx, ey + dy, 210, 240, 255);
                }
            }
        } else if (enemies_[e].snow_stage == SNOW_MEDIUM) {
            // Half encased
            set_pixel(ex, ey, 220, 240, 255);
            set_pixel(ex, ey - 1, 255, 60, 60); // Red demon head peeking out
        } else if (enemies_[e].snow_stage == SNOW_LIGHT) {
            // Frosted demon
            set_pixel(ex, ey, 255, 120, 120);
            set_pixel(ex, ey - 1, 255, 60, 60);
        } else {
            // Normal red demon
            set_pixel(ex, ey, 240, 30, 30);
            set_pixel(ex, ey - 1, 255, 80, 50);
        }
    }

    // 5. Projectiles (snowballs)
    for (int s = 0; s < MAX_SHOTS; ++s) {
        if (!shots_[s].active) continue;
        set_pixel(int(std::round(shots_[s].x)), int(std::round(shots_[s].y)), 255, 255, 255);
    }

    // 6. Player Snowman (Nick: Blue cap / white snowy body)
    if (state_ != STATE_DEAD) {
        int px = int(std::round(px_));
        int py = int(std::round(py_));

        set_pixel(px, py, 250, 250, 255);         // White snow body
        set_pixel(px, py - 1, 50, 120, 255);      // Blue beanie cap
        set_pixel(px + facing_, py, 255, 120, 40); // Carrot nose / mittens
    } else {
        // Melted puddle
        int px = int(std::round(px_));
        int py = int(std::round(py_));
        set_pixel(px - 1, py, 180, 220, 255);
        set_pixel(px,     py, 180, 220, 255);
        set_pixel(px + 1, py, 180, 220, 255);
    }
}

} // namespace arcade
