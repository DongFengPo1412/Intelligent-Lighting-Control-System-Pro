#include "game_066_twinbee.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game066TwinBee::Game066TwinBee()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(6000),
      lives_(3),
      px_(7.5f),
      py_(13.0f),
      shoot_cooldown_(0.0f),
      bomb_cooldown_(0.0f),
      has_twin_gun_(false),
      has_shield_(false),
      has_option_clone_(false),
      has_arms_(true),
      ambulance_active_(false),
      amb_x_(7.5f),
      amb_y_(-2.0f),
      enemies_defeated_(0),
      cloud_timer_(2.0f) {
}

void Game066TwinBee::Init() {
    Reset();
}

void Game066TwinBee::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    lives_ = 3;
    InitStage();
}

void Game066TwinBee::InitStage() {
    px_ = 7.5f;
    py_ = 13.0f;
    shoot_cooldown_ = 0.0f;
    bomb_cooldown_ = 0.0f;
    has_twin_gun_ = false;
    has_shield_ = false;
    has_option_clone_ = false;
    has_arms_ = true;
    ambulance_active_ = false;
    amb_x_ = 7.5f;
    amb_y_ = -2.0f;
    enemies_defeated_ = 0;
    cloud_timer_ = 2.0f;

    for (int i = 0; i < MAX_SHOTS; ++i) shots_[i].active = false;
    for (int i = 0; i < MAX_BOMBS; ++i) bombs_[i].active = false;
    for (int i = 0; i < MAX_BELLS; ++i) bells_[i].active = false;

    // Initialize aerial enemies
    enemies_[0] = {2.0f, -2.0f, 2.0f, 2.5f, 0, 1, true};
    enemies_[1] = {12.0f, -5.0f, -2.0f, 2.2f, 0, 1, true};
    enemies_[2] = {6.0f, -9.0f, 1.5f, 2.0f, 1, 1, true};
    enemies_[3] = {9.0f, -12.0f, -1.8f, 2.0f, 1, 1, true};

    // Ground targets (Fruit and Gun Turret)
    ground_targets_[0] = {4.0f, 5.0f, 0, true};
    ground_targets_[1] = {11.0f, 2.0f, 1, true};
    ground_targets_[2] = {7.0f, -4.0f, 0, true};
}

void Game066TwinBee::SpawnBell(float x, float y) {
    for (int i = 0; i < MAX_BELLS; ++i) {
        if (!bells_[i].active) {
            bells_[i].active = true;
            bells_[i].x = x;
            bells_[i].y = y;
            bells_[i].vy = 1.0f;
            bells_[i].hit_count = 0;
            bells_[i].color_type = BELL_YELLOW;
            break;
        }
    }
}

void Game066TwinBee::ShootAir() {
    if (shoot_cooldown_ > 0.0f) return;

    if (has_twin_gun_) {
        // Fire dual parallel shots
        for (int dx = -1; dx <= 1; dx += 2) {
            for (int i = 0; i < MAX_SHOTS; ++i) {
                if (!shots_[i].active) {
                    shots_[i].active = true;
                    shots_[i].x = px_ + dx * 0.8f;
                    shots_[i].y = py_ - 1.0f;
                    shots_[i].vx = 0.0f;
                    shots_[i].vy = -16.0f;
                    break;
                }
            }
        }
    } else {
        // Single shot
        for (int i = 0; i < MAX_SHOTS; ++i) {
            if (!shots_[i].active) {
                shots_[i].active = true;
                shots_[i].x = px_;
                shots_[i].y = py_ - 1.0f;
                shots_[i].vx = 0.0f;
                shots_[i].vy = -16.0f;
                break;
            }
        }
    }

    if (has_option_clone_) {
        // Extra shot from shadow clone trailing to the left
        for (int i = 0; i < MAX_SHOTS; ++i) {
            if (!shots_[i].active) {
                shots_[i].active = true;
                shots_[i].x = px_ - 2.0f;
                shots_[i].y = py_ + 0.5f;
                shots_[i].vx = 0.0f;
                shots_[i].vy = -16.0f;
                break;
            }
        }
    }

    shoot_cooldown_ = 0.22f;
}

void Game066TwinBee::DropGroundBomb() {
    if (!has_arms_ || bomb_cooldown_ > 0.0f) return;

    for (int i = 0; i < MAX_BOMBS; ++i) {
        if (!bombs_[i].active) {
            bombs_[i].active = true;
            bombs_[i].x = px_;
            bombs_[i].y = py_ + 0.5f;
            bombs_[i].vx = 0.0f;
            bombs_[i].vy = 5.0f; // Drops forward toward ground targets
            break;
        }
    }

    bomb_cooldown_ = 0.40f;
}

void Game066TwinBee::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
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
    if (bomb_cooldown_ > 0.0f) bomb_cooldown_ -= dt;

    // Periodic cloud passing releasing a bell
    cloud_timer_ -= dt;
    if (cloud_timer_ <= 0.0f) {
        cloud_timer_ = 5.0f;
        SpawnBell(3.0f + (rand() % 10), 1.0f);
    }

    UpdatePlayer(dt, buttons, prev_buttons);
    UpdateProjectiles(dt);
    UpdateBells(dt);
    UpdateEnemies(dt);
    UpdateAmbulance(dt);
    CheckCollisions();
}

void Game066TwinBee::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    float speed = has_twin_gun_ ? 8.0f : 6.5f; // Speed boost with white bell

    if (buttons & BUTTON_LEFT)  px_ -= speed * dt;
    if (buttons & BUTTON_RIGHT) px_ += speed * dt;
    if (buttons & BUTTON_UP)    py_ -= speed * dt;
    if (buttons & BUTTON_DOWN)  py_ += speed * dt;

    px_ = std::max(1.0f, std::min(14.0f, px_));
    py_ = std::max(2.0f, std::min(14.5f, py_));

    if ((buttons & BUTTON_A) && !(prev_buttons & BUTTON_A)) {
        ShootAir();
    }

    if ((buttons & BUTTON_B) && !(prev_buttons & BUTTON_B)) {
        DropGroundBomb();
    }
}

void Game066TwinBee::UpdateProjectiles(float dt) {
    for (int i = 0; i < MAX_SHOTS; ++i) {
        if (!shots_[i].active) continue;
        shots_[i].x += shots_[i].vx * dt;
        shots_[i].y += shots_[i].vy * dt;
        if (shots_[i].y < 0.0f) shots_[i].active = false;
    }

    for (int i = 0; i < MAX_BOMBS; ++i) {
        if (!bombs_[i].active) continue;
        bombs_[i].x += bombs_[i].vx * dt;
        bombs_[i].y += bombs_[i].vy * dt;
        if (bombs_[i].y > 15.5f) bombs_[i].active = false;
    }
}

void Game066TwinBee::UpdateBells(float dt) {
    for (int i = 0; i < MAX_BELLS; ++i) {
        if (!bells_[i].active) continue;

        bells_[i].y += bells_[i].vy * dt;
        // Gravity slowly pulls bell down
        bells_[i].vy = std::min(3.5f, bells_[i].vy + 8.0f * dt);

        if (bells_[i].y > 16.0f) {
            bells_[i].active = false;
        }
    }
}

void Game066TwinBee::UpdateEnemies(float dt) {
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;

        enemies_[i].y += enemies_[i].vy * dt;
        // Sinusoidal horizontal wave
        enemies_[i].x += std::sin(state_timer_ * 4.0f + i) * 3.0f * dt;

        if (enemies_[i].y > 16.0f) {
            // Loop from top
            enemies_[i].y = -2.0f;
            enemies_[i].x = 2.0f + (i * 3.5f);
        }
    }

    // Scroll ground targets
    for (int i = 0; i < MAX_GROUND_TARGETS; ++i) {
        if (!ground_targets_[i].active) continue;
        ground_targets_[i].y += 1.5f * dt;
        if (ground_targets_[i].y > 16.0f) {
            ground_targets_[i].y = -3.0f;
            ground_targets_[i].x = 3.0f + (rand() % 10);
            ground_targets_[i].active = true;
        }
    }
}

void Game066TwinBee::UpdateAmbulance(float dt) {
    if (!ambulance_active_) return;

    amb_y_ += 2.5f * dt;
    if (amb_y_ > 16.0f) {
        ambulance_active_ = false;
    }
}

void Game066TwinBee::CheckCollisions() {
    // 1. Air shots hit Bells (Juggling and color changing!)
    for (int s = 0; s < MAX_SHOTS; ++s) {
        if (!shots_[s].active) continue;
        for (int b = 0; b < MAX_BELLS; ++b) {
            if (!bells_[b].active) continue;
            if (std::abs(shots_[s].x - bells_[b].x) < 1.2f &&
                std::abs(shots_[s].y - bells_[b].y) < 1.2f) {
                shots_[s].active = false;
                // Juggle bell upward!
                bells_[b].vy = -4.5f;
                bells_[b].hit_count++;
                score_ += 20;

                // Color morph cycle: Yellow -> White -> Blue -> Red
                if (bells_[b].hit_count >= 15) {
                    bells_[b].color_type = BELL_RED;    // Clone
                } else if (bells_[b].hit_count >= 10) {
                    bells_[b].color_type = BELL_BLUE;   // Shield
                } else if (bells_[b].hit_count >= 5) {
                    bells_[b].color_type = BELL_WHITE;  // Twin gun
                } else {
                    bells_[b].color_type = BELL_YELLOW; // Bonus
                }
                break;
            }
        }
    }

    // 2. Air shots hit Aerial enemies
    for (int s = 0; s < MAX_SHOTS; ++s) {
        if (!shots_[s].active) continue;
        for (int e = 0; e < MAX_ENEMIES; ++e) {
            if (!enemies_[e].active) continue;
            if (std::abs(shots_[s].x - enemies_[e].x) < 1.2f &&
                std::abs(shots_[s].y - enemies_[e].y) < 1.2f) {
                shots_[s].active = false;
                enemies_[e].active = false;
                enemies_defeated_++;
                score_ += 150;

                if (enemies_defeated_ >= 8) {
                    state_ = STATE_VICTORY;
                    state_timer_ = 0.0f;
                    score_ += 2500;
                    if (score_ > high_score_) high_score_ = score_;
                    return;
                }
                break;
            }
        }
    }

    // 3. Ground bombs hit Ground Targets
    for (int b = 0; b < MAX_BOMBS; ++b) {
        if (!bombs_[b].active) continue;
        for (int g = 0; g < MAX_GROUND_TARGETS; ++g) {
            if (!ground_targets_[g].active) continue;
            if (std::abs(bombs_[b].x - ground_targets_[g].x) < 1.4f &&
                std::abs(bombs_[b].y - ground_targets_[g].y) < 1.4f) {
                bombs_[b].active = false;
                ground_targets_[g].active = false;
                score_ += 300;
                break;
            }
        }
    }

    // 4. Player collects Bell
    for (int b = 0; b < MAX_BELLS; ++b) {
        if (!bells_[b].active) continue;
        if (std::abs(px_ - bells_[b].x) < 1.3f &&
            std::abs(py_ - bells_[b].y) < 1.3f) {
            bells_[b].active = false;

            if (bells_[b].color_type == BELL_YELLOW) {
                score_ += 500;
            } else if (bells_[b].color_type == BELL_WHITE) {
                has_twin_gun_ = true;
                score_ += 1000;
            } else if (bells_[b].color_type == BELL_BLUE) {
                has_shield_ = true;
                score_ += 1000;
            } else if (bells_[b].color_type == BELL_RED) {
                has_option_clone_ = true;
                score_ += 1000;
            }
            if (score_ > high_score_) high_score_ = score_;
            break;
        }
    }

    // 5. Player touches Ambulance Angel
    if (ambulance_active_) {
        if (std::abs(px_ - amb_x_) < 1.4f && std::abs(py_ - amb_y_) < 1.4f) {
            ambulance_active_ = false;
            has_arms_ = true; // Arms repaired!
            score_ += 500;
        }
    }

    // 6. Player collides with Aerial Enemy
    for (int e = 0; e < MAX_ENEMIES; ++e) {
        if (!enemies_[e].active) continue;
        if (std::abs(px_ - enemies_[e].x) < 1.1f &&
            std::abs(py_ - enemies_[e].y) < 1.1f) {
            enemies_[e].active = false;

            if (has_shield_) {
                has_shield_ = false; // Shield breaks
            } else if (has_arms_) {
                has_arms_ = false;   // Arm damage!
                ambulance_active_ = true;
                amb_x_ = px_;
                amb_y_ = 0.0f;
            } else {
                // Fatal hit!
                lives_--;
                state_ = STATE_DEAD;
                state_timer_ = 0.0f;
                return;
            }
            break;
        }
    }
}

void Game066TwinBee::Render(uint8_t* fb) {
    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // 1. Pastoral Green island / Sky background
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (x >= 3 && x <= 12) {
                // Green land
                set_pixel(x, y, 30, 140, 50);
            } else {
                // Blue sky/ocean borders
                set_pixel(x, y, 20, 80, 180);
            }
        }
    }

    // Ground targets
    for (int g = 0; g < MAX_GROUND_TARGETS; ++g) {
        if (!ground_targets_[g].active) continue;
        int gx = int(std::round(ground_targets_[g].x));
        int gy = int(std::round(ground_targets_[g].y));
        if (ground_targets_[g].type == 0) {
            // Ground fruit (Apple/Strawberry: red/green stem)
            set_pixel(gx, gy, 230, 30, 30);
            set_pixel(gx, gy - 1, 30, 200, 30);
        } else {
            // Turret Gun (grey)
            set_pixel(gx, gy, 120, 120, 130);
            set_pixel(gx, gy - 1, 200, 200, 50);
        }
    }

    // Bells
    for (int b = 0; b < MAX_BELLS; ++b) {
        if (!bells_[b].active) continue;
        int bx = int(std::round(bells_[b].x));
        int by = int(std::round(bells_[b].y));

        uint8_t br = 255, bg = 215, bb = 0;
        if (bells_[b].color_type == BELL_WHITE) {
            br = 255; bg = 255; bb = 255;
        } else if (bells_[b].color_type == BELL_BLUE) {
            br = 50; bg = 120; bb = 255;
        } else if (bells_[b].color_type == BELL_RED) {
            br = 255; bg = 40; bb = 40;
        }
        set_pixel(bx, by, br, bg, bb);
        set_pixel(bx - 1, by + 1, br - 40, bg - 40, bb);
        set_pixel(bx + 1, by + 1, br - 40, bg - 40, bb);
    }

    // Aerial Enemies
    for (int e = 0; e < MAX_ENEMIES; ++e) {
        if (!enemies_[e].active) continue;
        int ex = int(std::round(enemies_[e].x));
        int ey = int(std::round(enemies_[e].y));
        if (enemies_[e].type == 0) {
            // Flying Strawberry
            set_pixel(ex, ey, 255, 60, 80);
            set_pixel(ex, ey - 1, 40, 220, 40);
        } else {
            // Saucer
            set_pixel(ex, ey, 220, 180, 40);
            set_pixel(ex - 1, ey, 180, 140, 30);
            set_pixel(ex + 1, ey, 180, 140, 30);
        }
    }

    // Ambulance Angel
    if (ambulance_active_) {
        int ax = int(std::round(amb_x_));
        int ay = int(std::round(amb_y_));
        set_pixel(ax, ay, 255, 255, 255); // White robe
        set_pixel(ax, ay - 1, 255, 220, 0); // Angel halo
        set_pixel(ax - 1, ay, 255, 50, 50); // Red cross
        set_pixel(ax + 1, ay, 255, 50, 50);
    }

    // Projectiles
    for (int s = 0; s < MAX_SHOTS; ++s) {
        if (!shots_[s].active) continue;
        set_pixel(int(std::round(shots_[s].x)), int(std::round(shots_[s].y)), 255, 255, 100);
    }

    for (int b = 0; b < MAX_BOMBS; ++b) {
        if (!bombs_[b].active) continue;
        set_pixel(int(std::round(bombs_[b].x)), int(std::round(bombs_[b].y)), 255, 120, 0);
    }

    // Player TwinBee
    if (state_ != STATE_DEAD) {
        int px = int(std::round(px_));
        int py = int(std::round(py_));

        // Shield aura
        if (has_shield_) {
            set_pixel(px - 1, py - 2, 80, 180, 255);
            set_pixel(px + 1, py - 2, 80, 180, 255);
            set_pixel(px - 2, py,     80, 180, 255);
            set_pixel(px + 2, py,     80, 180, 255);
        }

        // Hull (blue sphere)
        set_pixel(px, py, 40, 100, 240);
        set_pixel(px, py - 1, 255, 220, 50); // Cockpit canopy (yellow)

        // Boxing glove arms
        if (has_arms_) {
            set_pixel(px - 1, py, 255, 255, 255); // Left white glove
            set_pixel(px + 1, py, 255, 255, 255); // Right white glove
        }

        // Shadow clone
        if (has_option_clone_) {
            set_pixel(px - 2, py + 1, 150, 60, 200);
        }
    } else {
        // Explosion
        int px = int(std::round(px_));
        int py = int(std::round(py_));
        for (int dy = -1; dy <= 1; ++dy) {
            for (int dx = -1; dx <= 1; ++dx) {
                set_pixel(px + dx, py + dy, 255, 150, 30);
            }
        }
    }
}

} // namespace arcade
