#include "game_049_balloon_fight.h"
#include <cmath>
#include <cstdlib>
#include <algorithm>

namespace arcade {

Game049BalloonFight::Game049BalloonFight()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(0),
      lives_(3),
      player_balloons_(2),
      enemies_defeated_(0),
      total_wave_enemies_(4),
      player_x_(7.5f),
      player_y_(9.0f),
      player_vx_(0.0f),
      player_vy_(0.0f),
      fish_timer_(0.0f),
      fish_leaping_(false),
      fish_x_(0.0f) {
}

void Game049BalloonFight::Init() {
    Reset();
}

void Game049BalloonFight::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    lives_ = 3;
    player_balloons_ = 2;
    enemies_defeated_ = 0;
    total_wave_enemies_ = 4;
    player_x_ = 7.5f;
    player_y_ = 9.0f;
    player_vx_ = 0.0f;
    player_vy_ = 0.0f;
    fish_timer_ = 0.0f;
    fish_leaping_ = false;
    fish_x_ = 0.0f;

    InitArena();
}

void Game049BalloonFight::InitArena() {
    // Clear platform grid
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            platform_grid_[y][x] = false;
        }
    }

    // Left Platform (y = 7, cols 2..5)
    for (int x = 2; x <= 5; ++x) platform_grid_[7][x] = true;
    // Right Platform (y = 6, cols 10..13)
    for (int x = 10; x <= 13; ++x) platform_grid_[6][x] = true;
    // Center Low Platform (y = 11, cols 6..9)
    for (int x = 6; x <= 9; ++x) platform_grid_[11][x] = true;

    // Spawn 3 Enemies
    enemies_[0] = {3.5f, 6.0f, 2.0f, 0.0f, 1, false, false, 0.0f, true};
    enemies_[1] = {11.5f, 5.0f, -2.2f, 0.0f, 1, false, false, 0.0f, true};
    enemies_[2] = {7.5f, 3.0f, 2.4f, 0.0f, 1, false, false, 0.0f, true};

    // Lightning Sparks
    sparks_[0] = {1.0f, 2.0f, 3.2f, 2.8f, true};
    sparks_[1] = {14.0f, 4.0f, -3.0f, 3.0f, true};
}

int Game049BalloonFight::GetEnemiesRemaining() const {
    return total_wave_enemies_ - enemies_defeated_;
}

void Game049BalloonFight::FlapWings(bool strong) {
    float impulse = strong ? -5.8f : -4.2f;
    if (player_balloons_ == 1) {
        impulse *= 0.78f; // Sluggish with 1 balloon
    }
    player_vy_ = impulse;
}

void Game049BalloonFight::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    const float gravity = 8.5f;
    const float air_accel = 6.0f;

    // Horizontal drift
    if (buttons & KEY_LEFT)  player_vx_ -= air_accel * dt;
    if (buttons & KEY_RIGHT) player_vx_ += air_accel * dt;

    player_vx_ *= std::max(0.0f, 1.0f - 1.2f * dt); // Air drag
    player_vx_ = std::max(-5.0f, std::min(5.0f, player_vx_));

    // Vertical flapping
    if ((buttons & KEY_A) && !(prev_buttons & KEY_A)) {
        FlapWings(true);
    } else if (buttons & KEY_B) {
        player_vy_ -= 12.0f * dt;
    }

    // Gravity
    player_vy_ += gravity * dt;
    player_vy_ = std::max(-7.0f, std::min(7.0f, player_vy_));

    player_x_ += player_vx_ * dt;
    player_y_ += player_vy_ * dt;

    // Screen wrap horizontally
    if (player_x_ < 0.0f) player_x_ += 16.0f;
    if (player_x_ >= 16.0f) player_x_ -= 16.0f;

    // Top ceiling clamp
    if (player_y_ < 0.5f) {
        player_y_ = 0.5f;
        player_vy_ = 0.5f; // Rebound down
    }

    // Platform solid landing
    int foot_x = static_cast<int>(std::round(player_x_));
    int foot_y = static_cast<int>(std::round(player_y_ + 0.6f));
    if (foot_x >= 0 && foot_x < 16 && foot_y >= 0 && foot_y < 16) {
        if (platform_grid_[foot_y][foot_x] && player_vy_ > 0.0f && player_y_ <= foot_y - 0.4f) {
            player_y_ = static_cast<float>(foot_y - 0.6f);
            player_vy_ = 0.0f;
        }
    }

    // Water surface check (row 15)
    if (player_y_ >= 14.5f) {
        // Splashed into water -> Death!
        lives_--;
        state_ = STATE_DEAD;
        state_timer_ = 0.0f;
        return;
    }

    // Giant Fish snap warning if skimming near water (y >= 13.0)
    if (player_y_ >= 13.0f) {
        fish_timer_ += dt;
        if (fish_timer_ >= 0.8f) {
            fish_leaping_ = true;
            fish_x_ = player_x_;
            // Swallowed by Giant Piranha Fish!
            lives_--;
            state_ = STATE_DEAD;
            state_timer_ = 0.0f;
            return;
        }
    } else {
        fish_timer_ = std::max(0.0f, fish_timer_ - dt);
    }
}

void Game049BalloonFight::UpdateEnemies(float dt) {
    const float gravity = 7.5f;

    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;

        if (enemies_[i].is_pumping) {
            enemies_[i].pump_timer += dt;
            if (enemies_[i].pump_timer >= 3.5f) {
                // Fully re-inflated!
                enemies_[i].is_pumping = false;
                enemies_[i].balloons = 1;
                enemies_[i].vy = -3.5f;
            }
            continue; // Cannot move while pumping
        }

        if (enemies_[i].on_parachute) {
            // Slowly drifting down
            enemies_[i].y += 1.8f * dt;

            // Check landing on platform to start pumping
            int fx = static_cast<int>(std::round(enemies_[i].x));
            int fy = static_cast<int>(std::round(enemies_[i].y + 0.6f));
            if (fx >= 0 && fx < 16 && fy >= 0 && fy < 16) {
                if (platform_grid_[fy][fx]) {
                    enemies_[i].y = static_cast<float>(fy - 0.6f);
                    enemies_[i].on_parachute = false;
                    enemies_[i].is_pumping = true;
                    enemies_[i].pump_timer = 0.0f;
                    continue;
                }
            }

            // Fell into water
            if (enemies_[i].y >= 14.5f) {
                enemies_[i].active = false;
                enemies_defeated_++;
                score_ += 100;
                if (score_ > high_score_) high_score_ = score_;
            }
            continue;
        }

        // Active Flying AI
        enemies_[i].vy += gravity * dt;

        // Periodic flap upward towards player height
        if (enemies_[i].y > player_y_ + 0.5f || enemies_[i].vy > 2.0f) {
            enemies_[i].vy = -4.5f;
        }

        enemies_[i].x += enemies_[i].vx * dt;
        enemies_[i].y += enemies_[i].vy * dt;

        // Screen wrap
        if (enemies_[i].x < 0.0f) enemies_[i].x += 16.0f;
        if (enemies_[i].x >= 16.0f) enemies_[i].x -= 16.0f;

        // Ceiling clamp
        if (enemies_[i].y < 0.5f) {
            enemies_[i].y = 0.5f;
            enemies_[i].vy = 1.0f;
        }
    }
}

void Game049BalloonFight::UpdateSparks(float dt) {
    for (int i = 0; i < MAX_SPARKS; ++i) {
        if (!sparks_[i].active) continue;

        sparks_[i].x += sparks_[i].vx * dt;
        sparks_[i].y += sparks_[i].vy * dt;

        // Bounce on borders
        if (sparks_[i].x <= 0.0f) {
            sparks_[i].x = 0.0f;
            sparks_[i].vx = fabsf(sparks_[i].vx);
        } else if (sparks_[i].x >= 15.0f) {
            sparks_[i].x = 15.0f;
            sparks_[i].vx = -fabsf(sparks_[i].vx);
        }

        if (sparks_[i].y <= 0.5f) {
            sparks_[i].y = 0.5f;
            sparks_[i].vy = fabsf(sparks_[i].vy);
        } else if (sparks_[i].y >= 14.0f) {
            sparks_[i].y = 14.0f;
            sparks_[i].vy = -fabsf(sparks_[i].vy);
        }
    }
}

void Game049BalloonFight::CheckCollisions() {
    // 1. Player vs Enemies (Altitude Popping Rule)
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;

        float dist_x = fabsf(player_x_ - enemies_[i].x);
        float dist_y = player_y_ - enemies_[i].y;

        if (dist_x <= 0.85f && fabsf(dist_y) <= 0.85f) {
            // Player is higher (dist_y < -0.2f): Player pops enemy balloon!
            if (dist_y < -0.2f) {
                if (enemies_[i].balloons > 0) {
                    enemies_[i].balloons = 0;
                    enemies_[i].on_parachute = true;
                    player_vy_ = -3.5f; // Small rebound
                    score_ += 100;
                    if (score_ > high_score_) high_score_ = score_;
                } else if (enemies_[i].on_parachute || enemies_[i].is_pumping) {
                    // Kick off enemy into water!
                    enemies_[i].active = false;
                    enemies_defeated_++;
                    player_vy_ = -3.5f;
                    score_ += 200;
                    if (score_ > high_score_) high_score_ = score_;

                    if (enemies_defeated_ >= total_wave_enemies_) {
                        state_ = STATE_VICTORY;
                        state_timer_ = 0.0f;
                        score_ += 1000;
                        if (score_ > high_score_) high_score_ = score_;
                        return;
                    }
                }
            }
            // Enemy is higher (dist_y > 0.2f): Enemy pops player balloon!
            else if (dist_y > 0.2f) {
                player_balloons_--;
                enemies_[i].vy = -3.5f; // Enemy rebounds

                if (player_balloons_ <= 0) {
                    lives_--;
                    state_ = STATE_DEAD;
                    state_timer_ = 0.0f;
                    return;
                }
            }
        }
    }

    // 2. Player vs Lightning Sparks
    for (int s = 0; s < MAX_SPARKS; ++s) {
        if (!sparks_[s].active) continue;

        if (fabsf(player_x_ - sparks_[s].x) <= 0.75f &&
            fabsf(player_y_ - sparks_[s].y) <= 0.75f) {
            // Electrocuted!
            lives_--;
            state_ = STATE_DEAD;
            state_timer_ = 0.0f;
            return;
        }
    }
}

void Game049BalloonFight::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_START) {
        if (buttons & (KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_DEAD) {
        if (state_timer_ >= 1.5f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                state_timer_ = 0.0f;
                player_balloons_ = 2;
                player_x_ = 7.5f;
                player_y_ = 9.0f;
                player_vx_ = 0.0f;
                player_vy_ = 0.0f;
            }
        }
        return;
    }

    if (state_ == STATE_VICTORY) {
        if (state_timer_ >= 2.5f && (buttons & (KEY_A | KEY_B))) {
            Reset();
        }
        return;
    }

    UpdatePlayer(dt, buttons, prev_buttons);
    UpdateEnemies(dt);
    UpdateSparks(dt);
    CheckCollisions();
}

void Game049BalloonFight::Render(uint8_t* fb) {
    // 1. Midnight Starry Sky (#060814)
    for (int i = 0; i < 256 * 3; ++i) {
        fb[i] = 8;
    }

    // 2. Floating Grass Platforms
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (platform_grid_[y][x]) {
                int idx = (y * 16 + x) * 3;
                fb[idx + 0] = 46;  fb[idx + 1] = 204; fb[idx + 2] = 113; // Emerald grass
            }
        }
    }

    // 3. Deep Water Ocean (row 15)
    for (int x = 0; x < 16; ++x) {
        int idx = (15 * 16 + x) * 3;
        fb[idx + 0] = 26;  fb[idx + 1] = 82;  fb[idx + 2] = 118; // Royal Blue Water
    }

    // 4. Lightning Sparks (Flashing White/Cyan)
    for (int s = 0; s < MAX_SPARKS; ++s) {
        if (!sparks_[s].active) continue;

        int sx = static_cast<int>(std::round(sparks_[s].x));
        int sy = static_cast<int>(std::round(sparks_[s].y));
        if (sx >= 0 && sx < 16 && sy >= 0 && sy < 16) {
            int idx = (sy * 16 + sx) * 3;
            fb[idx + 0] = 0; fb[idx + 1] = 255; fb[idx + 2] = 255;
        }
    }

    // 5. Enemies (Golden Yellow Balloons over Magenta Body)
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;

        int ex = static_cast<int>(std::round(enemies_[i].x));
        int ey = static_cast<int>(std::round(enemies_[i].y));

        if (ex >= 0 && ex < 16 && ey >= 0 && ey < 16) {
            int idx = (ey * 16 + ex) * 3;
            if (enemies_[i].balloons > 0) {
                fb[idx + 0] = 241; fb[idx + 1] = 196; fb[idx + 2] = 15; // Yellow Balloon
            } else if (enemies_[i].on_parachute) {
                fb[idx + 0] = 255; fb[idx + 1] = 255; fb[idx + 2] = 255; // White Chute
            } else {
                fb[idx + 0] = 155; fb[idx + 1] = 89;  fb[idx + 2] = 182; // Pumping Thug
            }
        }
    }

    // 6. Player Balloon Fighter (Scarlet Balloons over Cyan Pilot)
    int px = static_cast<int>(std::round(player_x_));
    int py = static_cast<int>(std::round(player_y_));
    if (px >= 0 && px < 16 && py >= 0 && py < 16) {
        int idx = (py * 16 + px) * 3;
        if (player_balloons_ >= 2) {
            fb[idx + 0] = 231; fb[idx + 1] = 76; fb[idx + 2] = 60; // Scarlet Double Balloon
        } else if (player_balloons_ == 1) {
            fb[idx + 0] = 230; fb[idx + 1] = 126; fb[idx + 2] = 34; // Orange Single Balloon
        } else {
            fb[idx + 0] = 100; fb[idx + 1] = 100; fb[idx + 2] = 100; // Popped
        }
    }

    // 7. Giant Fish Snap (if leaping)
    if (fish_leaping_) {
        int fx = static_cast<int>(std::round(fish_x_));
        if (fx >= 0 && fx < 16) {
            int idx = (14 * 16 + fx) * 3;
            fb[idx + 0] = 243; fb[idx + 1] = 156; fb[idx + 2] = 18; // Giant Fish Maw
        }
    }
}

} // namespace arcade
