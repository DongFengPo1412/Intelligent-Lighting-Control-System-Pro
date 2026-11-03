#include "game_160_ripoff.h"
#include <cstring>
#include <cmath>
#include <algorithm>

namespace arcade {

static constexpr uint16_t BTN_UP    = (1 << 0);
static constexpr uint16_t BTN_DOWN  = (1 << 1);
static constexpr uint16_t BTN_LEFT  = (1 << 2);
static constexpr uint16_t BTN_RIGHT = (1 << 3);
static constexpr uint16_t BTN_A     = (1 << 4);
static constexpr uint16_t BTN_B     = (1 << 5);

Game160RipOff::Game160RipOff() {
    Reset();
}

void Game160RipOff::Init() {
    Reset();
}

void Game160RipOff::Reset() {
    state_ = STATE_PLAYING;
    score_ = 0;
    wave_ = 1;

    player_x_ = 8.0f;
    player_y_ = 12.0f;
    player_vx_ = 0.0f;
    player_vy_ = 0.0f;
    facing_dx_ = 0.0f;
    facing_dy_ = -1.0f;
    player_alive_ = true;
    respawn_timer_ = 0.0f;
    fire_cooldown_ = 0.0f;

    // Initialize 4 fuel canisters at center
    canisters_[0] = {7.0f, 7.0f, 7.0f, 7.0f, 0, -1};
    canisters_[1] = {8.0f, 7.0f, 8.0f, 7.0f, 0, -1};
    canisters_[2] = {7.0f, 8.0f, 7.0f, 8.0f, 0, -1};
    canisters_[3] = {8.0f, 8.0f, 8.0f, 8.0f, 0, -1};

    for (int i = 0; i < MAX_BULLETS; ++i) {
        bullets_[i].active = false;
    }
    for (int i = 0; i < MAX_PIRATES; ++i) {
        pirates_[i].alive = false;
    }
    for (int i = 0; i < MAX_EXPLOSIONS; ++i) {
        explosions_[i].active = false;
    }

    pirates_killed_in_wave_ = 0;
    pirates_needed_for_wave_ = 6;
    spawn_timer_ = 0.5f;
    next_pirate_id_ = 0;
}

uint8_t Game160RipOff::GetRemainingFuel() const {
    uint8_t count = 0;
    for (int i = 0; i < NUM_CANISTERS; ++i) {
        if (canisters_[i].status != 3) { // 3: stolen
            count++;
        }
    }
    return count;
}

void Game160RipOff::FireBullet() {
    if (!player_alive_ || fire_cooldown_ > 0.0f) return;

    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (!bullets_[i].active) {
            bullets_[i].x = player_x_ + facing_dx_ * 0.8f;
            bullets_[i].y = player_y_ + facing_dy_ * 0.8f;
            bullets_[i].vx = facing_dx_ * 14.0f;
            bullets_[i].vy = facing_dy_ * 14.0f;
            bullets_[i].life = 1.2f;
            bullets_[i].active = true;
            fire_cooldown_ = 0.22f;
            break;
        }
    }
}

void Game160RipOff::MagnetRecoverCanisters() {
    for (int i = 0; i < NUM_CANISTERS; ++i) {
        if (canisters_[i].status == 2) { // dropped
            float dist = std::hypot(canisters_[i].x - player_x_, canisters_[i].y - player_y_);
            if (dist < 4.0f) {
                canisters_[i].x = canisters_[i].home_x;
                canisters_[i].y = canisters_[i].home_y;
                canisters_[i].status = 0; // at_base
                score_ += 25;
            }
        }
    }
}

void Game160RipOff::SpawnPirate() {
    for (int i = 0; i < MAX_PIRATES; ++i) {
        if (!pirates_[i].alive) {
            int side = next_pirate_id_ % 4;
            float px = 0.0f, py = 0.0f;
            if (side == 0) {
                px = 4.0f + static_cast<float>((next_pirate_id_ * 3) % 8);
                py = 0.0f;
            } else if (side == 1) {
                px = 15.0f;
                py = 4.0f + static_cast<float>((next_pirate_id_ * 3) % 8);
            } else if (side == 2) {
                px = 4.0f + static_cast<float>((next_pirate_id_ * 3) % 8);
                py = 15.0f;
            } else {
                px = 0.0f;
                py = 4.0f + static_cast<float>((next_pirate_id_ * 3) % 8);
            }

            pirates_[i].id = next_pirate_id_++;
            pirates_[i].x = px;
            pirates_[i].y = py;
            pirates_[i].speed = 2.2f + static_cast<float>(wave_) * 0.35f;
            pirates_[i].towing_canister = -1;
            pirates_[i].alive = true;
            break;
        }
    }
}

void Game160RipOff::AddExplosion(float x, float y, float duration) {
    for (int i = 0; i < MAX_EXPLOSIONS; ++i) {
        if (!explosions_[i].active) {
            explosions_[i].x = x;
            explosions_[i].y = y;
            explosions_[i].timer = duration;
            explosions_[i].active = true;
            break;
        }
    }
}

void Game160RipOff::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_GAME_OVER) {
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            Reset();
        }
        return;
    }

    // Particle explosions
    for (int i = 0; i < MAX_EXPLOSIONS; ++i) {
        if (explosions_[i].active) {
            explosions_[i].timer -= dt;
            if (explosions_[i].timer <= 0.0f) {
                explosions_[i].active = false;
            }
        }
    }

    if (fire_cooldown_ > 0.0f) fire_cooldown_ -= dt;

    // Player inputs & respawn
    if (!player_alive_) {
        respawn_timer_ -= dt;
        if (respawn_timer_ <= 0.0f) {
            if (GetRemainingFuel() > 0) {
                player_alive_ = true;
                player_x_ = 8.0f;
                player_y_ = 12.0f;
                player_vx_ = 0.0f;
                player_vy_ = 0.0f;
            } else {
                state_ = STATE_GAME_OVER;
                return;
            }
        }
    } else {
        float speed = 5.5f;
        if (buttons & BTN_UP) {
            player_vx_ = 0.0f; player_vy_ = -speed;
            facing_dx_ = 0.0f; facing_dy_ = -1.0f;
        } else if (buttons & BTN_DOWN) {
            player_vx_ = 0.0f; player_vy_ = speed;
            facing_dx_ = 0.0f; facing_dy_ = 1.0f;
        } else if (buttons & BTN_LEFT) {
            player_vx_ = -speed; player_vy_ = 0.0f;
            facing_dx_ = -1.0f; facing_dy_ = 0.0f;
        } else if (buttons & BTN_RIGHT) {
            player_vx_ = speed; player_vy_ = 0.0f;
            facing_dx_ = 1.0f; facing_dy_ = 0.0f;
        } else {
            player_vx_ = 0.0f; player_vy_ = 0.0f;
        }

        if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
            FireBullet();
        }
        if ((buttons & BTN_B) && !(prev_buttons & BTN_B)) {
            MagnetRecoverCanisters();
        }

        player_x_ += player_vx_ * dt;
        player_y_ += player_vy_ * dt;
        player_x_ = std::max(0.0f, std::min(15.0f, player_x_));
        player_y_ = std::max(0.0f, std::min(15.0f, player_y_));

        // Touch dropped canister
        for (int i = 0; i < NUM_CANISTERS; ++i) {
            if (canisters_[i].status == 2) {
                if (std::hypot(canisters_[i].x - player_x_, canisters_[i].y - player_y_) < 1.0f) {
                    canisters_[i].x = canisters_[i].home_x;
                    canisters_[i].y = canisters_[i].home_y;
                    canisters_[i].status = 0;
                    score_ += 50;
                }
            }
        }
    }

    // Update bullets
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (!bullets_[i].active) continue;

        bullets_[i].x += bullets_[i].vx * dt;
        bullets_[i].y += bullets_[i].vy * dt;
        bullets_[i].life -= dt;

        if (bullets_[i].life <= 0.0f || bullets_[i].x < 0.0f || bullets_[i].x > 15.0f ||
            bullets_[i].y < 0.0f || bullets_[i].y > 15.0f) {
            bullets_[i].active = false;
            continue;
        }

        for (int p = 0; p < MAX_PIRATES; ++p) {
            if (pirates_[p].alive && std::hypot(pirates_[p].x - bullets_[i].x, pirates_[p].y - bullets_[i].y) < 1.1f) {
                pirates_[p].alive = false;
                bullets_[i].active = false;
                score_ += 100;
                pirates_killed_in_wave_++;
                AddExplosion(pirates_[p].x, pirates_[p].y, 0.3f);

                if (pirates_[p].towing_canister != -1) {
                    int8_t cid = pirates_[p].towing_canister;
                    canisters_[cid].status = 2; // dropped
                    canisters_[cid].carrier_id = -1;
                    pirates_[p].towing_canister = -1;
                }
                break;
            }
        }
    }

    // Spawn pirates
    int active_pirates = 0;
    for (int p = 0; p < MAX_PIRATES; ++p) {
        if (pirates_[p].alive) active_pirates++;
    }

    if (active_pirates < MAX_PIRATES && pirates_killed_in_wave_ < pirates_needed_for_wave_) {
        spawn_timer_ -= dt;
        if (spawn_timer_ <= 0.0f) {
            SpawnPirate();
            spawn_timer_ = 1.0f;
        }
    }

    // Update pirates
    for (int p = 0; p < MAX_PIRATES; ++p) {
        if (!pirates_[p].alive) continue;

        // Collision with player
        if (player_alive_ && std::hypot(pirates_[p].x - player_x_, pirates_[p].y - player_y_) < 1.0f) {
            player_alive_ = false;
            respawn_timer_ = 1.0f;
            pirates_[p].alive = false;
            AddExplosion(player_x_, player_y_, 0.4f);
            AddExplosion(pirates_[p].x, pirates_[p].y, 0.4f);

            if (pirates_[p].towing_canister != -1) {
                int8_t cid = pirates_[p].towing_canister;
                canisters_[cid].status = 2;
                canisters_[cid].carrier_id = -1;
            }
            if (GetRemainingFuel() == 0) {
                state_ = STATE_GAME_OVER;
            }
            continue;
        }

        // Pirate AI
        if (pirates_[p].towing_canister == -1) {
            int target_idx = -1;
            float min_dist = 999.0f;
            for (int i = 0; i < NUM_CANISTERS; ++i) {
                if (canisters_[i].status == 0 || canisters_[i].status == 2) {
                    float d = std::hypot(canisters_[i].x - pirates_[p].x, canisters_[i].y - pirates_[p].y);
                    if (d < min_dist) {
                        min_dist = d;
                        target_idx = i;
                    }
                }
            }

            if (target_idx != -1) {
                float dx = canisters_[target_idx].x - pirates_[p].x;
                float dy = canisters_[target_idx].y - pirates_[p].y;
                float dist = std::hypot(dx, dy);
                if (dist > 0.4f) {
                    pirates_[p].x += (dx / dist) * pirates_[p].speed * dt;
                    pirates_[p].y += (dy / dist) * pirates_[p].speed * dt;
                } else {
                    pirates_[p].towing_canister = target_idx;
                    canisters_[target_idx].status = 1; // towed
                    canisters_[target_idx].carrier_id = pirates_[p].id;
                }
            } else if (player_alive_) {
                float dx = player_x_ - pirates_[p].x;
                float dy = player_y_ - pirates_[p].y;
                float dist = std::hypot(dx, dy);
                if (dist > 0.1f) {
                    pirates_[p].x += (dx / dist) * pirates_[p].speed * dt;
                    pirates_[p].y += (dy / dist) * pirates_[p].speed * dt;
                }
            }
        } else {
            int8_t cid = pirates_[p].towing_canister;
            float d_left = pirates_[p].x;
            float d_right = 15.0f - pirates_[p].x;
            float d_top = pirates_[p].y;
            float d_bottom = 15.0f - pirates_[p].y;
            float min_d = std::min({d_left, d_right, d_top, d_bottom});

            float esc_dx = 0.0f, esc_dy = 0.0f;
            if (min_d == d_left) esc_dx = -1.0f;
            else if (min_d == d_right) esc_dx = 1.0f;
            else if (min_d == d_top) esc_dy = -1.0f;
            else esc_dy = 1.0f;

            pirates_[p].x += esc_dx * pirates_[p].speed * dt;
            pirates_[p].y += esc_dy * pirates_[p].speed * dt;

            canisters_[cid].x = pirates_[p].x - esc_dx * 0.8f;
            canisters_[cid].y = pirates_[p].y - esc_dy * 0.8f;

            if (pirates_[p].x <= -0.5f || pirates_[p].x >= 15.5f ||
                pirates_[p].y <= -0.5f || pirates_[p].y >= 15.5f) {
                canisters_[cid].status = 3; // stolen
                canisters_[cid].carrier_id = -1;
                pirates_[p].alive = false;

                if (GetRemainingFuel() == 0) {
                    state_ = STATE_GAME_OVER;
                }
                continue;
            }
        }
    }

    // Wave progression
    active_pirates = 0;
    for (int p = 0; p < MAX_PIRATES; ++p) {
        if (pirates_[p].alive) active_pirates++;
    }

    if (pirates_killed_in_wave_ >= pirates_needed_for_wave_ && active_pirates == 0) {
        wave_++;
        pirates_killed_in_wave_ = 0;
        pirates_needed_for_wave_ = 6 + wave_ * 2;
        score_ += 500 * GetRemainingFuel();

        for (int i = 0; i < NUM_CANISTERS; ++i) {
            if (canisters_[i].status == 2) {
                canisters_[i].x = canisters_[i].home_x;
                canisters_[i].y = canisters_[i].home_y;
                canisters_[i].status = 0;
            }
        }
    }
}

void Game160RipOff::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx]     = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Fuel canisters
    for (int i = 0; i < NUM_CANISTERS; ++i) {
        int cx = static_cast<int>(std::round(canisters_[i].x));
        int cy = static_cast<int>(std::round(canisters_[i].y));
        if (canisters_[i].status == 0) {
            set_pixel(cx, cy, 0, 220, 255); // Cyan
        } else if (canisters_[i].status == 1) {
            set_pixel(cx, cy, 255, 255, 0); // Yellow (towed)
        } else if (canisters_[i].status == 2) {
            set_pixel(cx, cy, 255, 180, 0); // Orange (dropped)
        }
    }

    // Pirates
    for (int p = 0; p < MAX_PIRATES; ++p) {
        if (pirates_[p].alive) {
            int px = static_cast<int>(std::round(pirates_[p].x));
            int py = static_cast<int>(std::round(pirates_[p].y));
            if (pirates_[p].towing_canister == -1) {
                set_pixel(px, py, 255, 30, 80);
            } else {
                set_pixel(px, py, 255, 80, 20);
            }
        }
    }

    // Player
    if (player_alive_) {
        int px = static_cast<int>(std::round(player_x_));
        int py = static_cast<int>(std::round(player_y_));
        set_pixel(px, py, 0, 255, 120);
    }

    // Bullets
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (bullets_[i].active) {
            int bx = static_cast<int>(std::round(bullets_[i].x));
            int by = static_cast<int>(std::round(bullets_[i].y));
            set_pixel(bx, by, 255, 255, 255);
        }
    }

    // Explosions
    for (int i = 0; i < MAX_EXPLOSIONS; ++i) {
        if (explosions_[i].active) {
            int ex = static_cast<int>(std::round(explosions_[i].x));
            int ey = static_cast<int>(std::round(explosions_[i].y));
            set_pixel(ex, ey, 255, 200, 50);
        }
    }
}

} // namespace arcade

