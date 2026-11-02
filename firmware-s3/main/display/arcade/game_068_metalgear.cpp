#include "game_068_metalgear.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game068MetalGear::Game068MetalGear()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(6500),
      lives_(3),
      px_(2.0f),
      py_(13.0f),
      player_dir_(0),
      in_box_(false),
      is_moving_(false),
      dart_cooldown_(0.0f),
      has_keycard_(false),
      alert_level_(ALERT_NORMAL),
      alert_timer_(0.0f),
      guards_neutralized_(0) {
}

void Game068MetalGear::Init() {
    Reset();
}

void Game068MetalGear::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    lives_ = 3;
    InitStage();
}

void Game068MetalGear::InitStage() {
    px_ = 2.0f;
    py_ = 13.0f;
    player_dir_ = 0; // Up
    in_box_ = false;
    is_moving_ = false;
    dart_cooldown_ = 0.0f;
    has_keycard_ = false;
    alert_level_ = ALERT_NORMAL;
    alert_timer_ = 0.0f;
    guards_neutralized_ = 0;

    for (int i = 0; i < MAX_DARTS; ++i) darts_[i].active = false;

    // Patrolling guards
    guards_[0] = {6.0f, 5.0f, 1, 0.0f, false, true};  // Patrols hallway y=5
    guards_[1] = {9.0f, 9.0f, 2, 0.0f, false, true};  // Patrols vertical corridor x=9
    guards_[2] = {12.0f, 11.0f, 3, 0.0f, false, true}; // Guards keycard room
}

static bool IsWallOrCrate(int x, int y, bool door_open) {
    if (x <= 0 || x >= 15 || y <= 0 || y >= 15) return true;

    // Security door at (7, 2) and (8, 2)
    if ((x == 7 || x == 8) && y == 2) {
        return !door_open;
    }

    // Interior walls & crates
    if ((x == 4 || x == 5) && (y >= 4 && y <= 6)) return true;
    if ((x == 10 || x == 11) && (y >= 7 && y <= 9)) return true;
    if (y == 2 && x != 7 && x != 8) return true; // Security barrier wall

    return false;
}

void Game068MetalGear::ToggleCardboardBox() {
    in_box_ = !in_box_;
}

void Game068MetalGear::FireSilencedDart() {
    if (dart_cooldown_ > 0.0f || in_box_) return;

    for (int i = 0; i < MAX_DARTS; ++i) {
        if (!darts_[i].active) {
            darts_[i].active = true;
            darts_[i].x = px_;
            darts_[i].y = py_;

            float spd = 12.0f;
            if (player_dir_ == 0) { darts_[i].vx = 0.0f; darts_[i].vy = -spd; }
            else if (player_dir_ == 1) { darts_[i].vx = spd; darts_[i].vy = 0.0f; }
            else if (player_dir_ == 2) { darts_[i].vx = 0.0f; darts_[i].vy = spd; }
            else { darts_[i].vx = -spd; darts_[i].vy = 0.0f; }
            break;
        }
    }

    dart_cooldown_ = 0.35f;
}

void Game068MetalGear::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
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

    if (dart_cooldown_ > 0.0f) dart_cooldown_ -= dt;

    // Alert decay timer
    if (alert_level_ > ALERT_NORMAL) {
        alert_timer_ -= dt;
        if (alert_timer_ <= 0.0f) {
            alert_level_ = ALERT_NORMAL;
            for (int i = 0; i < MAX_GUARDS; ++i) guards_[i].alert = false;
        }
    }

    UpdatePlayer(dt, buttons, prev_buttons);
    UpdateGuards(dt);
    UpdateDarts(dt);
    CheckLineOfSight();
    CheckCollisions();
}

void Game068MetalGear::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    float move_speed = in_box_ ? 2.5f : 5.0f;
    float next_x = px_;
    float next_y = py_;
    is_moving_ = false;

    if (buttons & BUTTON_UP) {
        next_y -= move_speed * dt;
        player_dir_ = 0;
        is_moving_ = true;
    } else if (buttons & BUTTON_DOWN) {
        next_y += move_speed * dt;
        player_dir_ = 2;
        is_moving_ = true;
    } else if (buttons & BUTTON_LEFT) {
        next_x -= move_speed * dt;
        player_dir_ = 3;
        is_moving_ = true;
    } else if (buttons & BUTTON_RIGHT) {
        next_x += move_speed * dt;
        player_dir_ = 1;
        is_moving_ = true;
    }

    if (!IsWallOrCrate(int(std::round(next_x)), int(std::round(next_y)), has_keycard_)) {
        px_ = next_x;
        py_ = next_y;
    }

    px_ = std::max(1.0f, std::min(14.0f, px_));
    py_ = std::max(1.0f, std::min(14.0f, py_));

    // Button A: Fire Silenced Pistol Dart
    if ((buttons & BUTTON_A) && !(prev_buttons & BUTTON_A)) {
        FireSilencedDart();
    }

    // Button B: Toggle Cardboard Box
    if ((buttons & BUTTON_B) && !(prev_buttons & BUTTON_B)) {
        ToggleCardboardBox();
    }

    // Keycard pickup at (13, 13)
    if (!has_keycard_ && std::abs(px_ - 13.0f) < 0.9f && std::abs(py_ - 13.0f) < 0.9f) {
        has_keycard_ = true;
        score_ += 500;
    }

    // Objective / Terminal reached at (7..8, 1) through open security door!
    if (has_keycard_ && (std::abs(px_ - 7.5f) < 1.0f) && py_ <= 1.5f) {
        state_ = STATE_VICTORY;
        state_timer_ = 0.0f;
        score_ += 3000;
        if (score_ > high_score_) high_score_ = score_;
    }
}

void Game068MetalGear::UpdateGuards(float dt) {
    for (int i = 0; i < MAX_GUARDS; ++i) {
        if (!guards_[i].active) continue;

        if (guards_[i].alert) {
            // Rush directly towards Snake
            float dx = px_ - guards_[i].x;
            float dy = py_ - guards_[i].y;
            float dist = std::sqrt(dx * dx + dy * dy);
            if (dist > 0.1f) {
                float spd = 4.0f;
                guards_[i].x += (dx / dist) * spd * dt;
                guards_[i].y += (dy / dist) * spd * dt;
            }
        } else {
            // Normal patrol
            guards_[i].patrol_timer += dt;
            if (guards_[i].patrol_timer > 2.2f) {
                guards_[i].patrol_timer = 0.0f;
                guards_[i].dir = (guards_[i].dir + 1) % 4; // Turn 90 degrees
            }

            float spd = 2.0f;
            float nx = guards_[i].x;
            float ny = guards_[i].y;
            if (guards_[i].dir == 0) ny -= spd * dt;
            else if (guards_[i].dir == 1) nx += spd * dt;
            else if (guards_[i].dir == 2) ny += spd * dt;
            else nx -= spd * dt;

            if (!IsWallOrCrate(int(std::round(nx)), int(std::round(ny)), has_keycard_)) {
                guards_[i].x = nx;
                guards_[i].y = ny;
            } else {
                guards_[i].dir = (guards_[i].dir + 2) % 4; // Turn around
            }
        }
    }
}

void Game068MetalGear::UpdateDarts(float dt) {
    for (int i = 0; i < MAX_DARTS; ++i) {
        if (!darts_[i].active) continue;
        darts_[i].x += darts_[i].vx * dt;
        darts_[i].y += darts_[i].vy * dt;

        if (IsWallOrCrate(int(std::round(darts_[i].x)), int(std::round(darts_[i].y)), has_keycard_)) {
            darts_[i].active = false;
        }
    }
}

void Game068MetalGear::CheckLineOfSight() {
    for (int i = 0; i < MAX_GUARDS; ++i) {
        if (!guards_[i].active || guards_[i].alert) continue;

        // Check if player is in guard's field of view
        float gx = guards_[i].x;
        float gy = guards_[i].y;
        float dx = px_ - gx;
        float dy = py_ - gy;

        bool in_sight_cone = false;
        if (guards_[i].dir == 0 && dy < 0.0f && std::abs(dx) <= 1.2f && std::abs(dy) <= 4.0f) in_sight_cone = true;
        if (guards_[i].dir == 1 && dx > 0.0f && std::abs(dy) <= 1.2f && std::abs(dx) <= 4.0f) in_sight_cone = true;
        if (guards_[i].dir == 2 && dy > 0.0f && std::abs(dx) <= 1.2f && std::abs(dy) <= 4.0f) in_sight_cone = true;
        if (guards_[i].dir == 3 && dx < 0.0f && std::abs(dy) <= 1.2f && std::abs(dx) <= 4.0f) in_sight_cone = true;

        if (in_sight_cone) {
            // Cardboard Box check: If in box AND stationary, guard ignores!
            if (in_box_ && !is_moving_) {
                // "Just a cardboard box..."
                continue;
            }

            // Spoke alert! "!" sound & trigger alert mode
            guards_[i].alert = true;
            alert_level_ = ALERT_EVASION;
            alert_timer_ = 8.0f;
            score_ = std::max(0, int(score_ - 100)); // Alert penalty
        }
    }
}

void Game068MetalGear::CheckCollisions() {
    // 1. Silenced darts hit guards
    for (int d = 0; d < MAX_DARTS; ++d) {
        if (!darts_[d].active) continue;
        for (int g = 0; g < MAX_GUARDS; ++g) {
            if (!guards_[g].active) continue;
            if (std::abs(darts_[d].x - guards_[g].x) < 1.2f &&
                std::abs(darts_[d].y - guards_[g].y) < 1.2f) {
                darts_[d].active = false;
                guards_[g].active = false;
                guards_neutralized_++;

                if (!guards_[g].alert) {
                    // Stealth silent takedown bonus!
                    score_ += 400;
                } else {
                    score_ += 150;
                }
                break;
            }
        }
    }

    // 2. Snake close quarters flanking takedown
    for (int g = 0; g < MAX_GUARDS; ++g) {
        if (!guards_[g].active || guards_[g].alert) continue;
        if (std::abs(px_ - guards_[g].x) < 1.0f &&
            std::abs(py_ - guards_[g].y) < 1.0f) {
            // CQC choke / silent takedown from behind/side
            guards_[g].active = false;
            guards_neutralized_++;
            score_ += 500;
            break;
        }
    }

    // 3. Alerted guard catches player
    for (int g = 0; g < MAX_GUARDS; ++g) {
        if (!guards_[g].active || !guards_[g].alert) continue;
        if (std::abs(px_ - guards_[g].x) < 0.9f &&
            std::abs(py_ - guards_[g].y) < 0.9f) {
            lives_--;
            state_ = STATE_DEAD;
            state_timer_ = 0.0f;
            return;
        }
    }
}

void Game068MetalGear::Render(uint8_t* fb) {
    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // 1. Compound Steel Floor
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            set_pixel(x, y, 35, 45, 50);
        }
    }

    // 2. Walls and Crates
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (IsWallOrCrate(x, y, has_keycard_)) {
                if ((x == 7 || x == 8) && y == 2) {
                    // Security door (Red locked / Green unlocked)
                    if (has_keycard_) {
                        set_pixel(x, y, 30, 220, 60);
                    } else {
                        set_pixel(x, y, 220, 30, 30);
                    }
                } else if ((x == 4 || x == 5) || (x == 10 || x == 11)) {
                    // Wooden crates
                    set_pixel(x, y, 140, 90, 40);
                } else {
                    // Military base concrete wall
                    set_pixel(x, y, 80, 90, 100);
                }
            }
        }
    }

    // 3. Goal Nuclear Terminal (y=1, x=7..8)
    set_pixel(7, 1, 40, 240, 255);
    set_pixel(8, 1, 40, 240, 255);

    // 4. Keycard item at (13, 13)
    if (!has_keycard_) {
        set_pixel(13, 13, 255, 215, 0); // Gold keycard
    }

    // 5. Guards & Vision Cones
    for (int g = 0; g < MAX_GUARDS; ++g) {
        if (!guards_[g].active) continue;
        int gx = int(std::round(guards_[g].x));
        int gy = int(std::round(guards_[g].y));

        // Guard body (Green military uniform)
        set_pixel(gx, gy, 40, 140, 50);
        set_pixel(gx, gy - 1, 220, 180, 140); // Helmet / head

        // Alert exclamation mark "!"
        if (guards_[g].alert) {
            set_pixel(gx, gy - 2, 255, 30, 30);
        } else {
            // Flash subtle vision direction dot
            int fx = gx, fy = gy;
            if (guards_[g].dir == 0) fy -= 2;
            else if (guards_[g].dir == 1) fx += 2;
            else if (guards_[g].dir == 2) fy += 2;
            else fx -= 2;
            set_pixel(fx, fy, 180, 180, 70);
        }
    }

    // 6. Projectiles (Silenced darts)
    for (int d = 0; d < MAX_DARTS; ++d) {
        if (!darts_[d].active) continue;
        set_pixel(int(std::round(darts_[d].x)), int(std::round(darts_[d].y)), 200, 255, 255);
    }

    // 7. Solid Snake
    if (state_ != STATE_DEAD) {
        int px = int(std::round(px_));
        int py = int(std::round(py_));

        if (in_box_) {
            // Cardboard Box disguise (Brown box with orange stripe)
            set_pixel(px, py, 190, 140, 60);
            set_pixel(px + 1, py, 170, 120, 45);
            set_pixel(px, py - 1, 190, 140, 60);
            set_pixel(px + 1, py - 1, 230, 100, 20); // Box tape
        } else {
            // Solid Snake: Bandana & Sneaking suit
            set_pixel(px, py, 60, 75, 90);           // Grey sneaking suit
            set_pixel(px, py - 1, 220, 180, 140);    // Face
            set_pixel(px, py - 2, 40, 40, 40);       // Dark bandana
        }
    } else {
        // Snake down
        int px = int(std::round(px_));
        int py = int(std::round(py_));
        set_pixel(px, py, 200, 40, 40);
    }

    // 8. HUD: Alert status banner (y=0)
    if (alert_level_ == ALERT_EVASION) {
        for (int x = 0; x < 16; ++x) {
            if ((int(state_timer_ * 10.0f) + x) % 2 == 0) {
                set_pixel(x, 0, 255, 20, 20); // Flashing RED ALERT!
            }
        }
    } else {
        // Keycard status
        if (has_keycard_) set_pixel(15, 0, 255, 215, 0);
    }
}

} // namespace arcade
