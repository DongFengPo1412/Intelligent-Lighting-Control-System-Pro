#include "game_112_defender.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

static float WrapX(float x, float width = 48.0f) {
    while (x < 0.0f) x += width;
    while (x >= width) x -= width;
    return x;
}

static float WrapDistX(float x1, float x2, float width = 48.0f) {
    float dx = x1 - x2;
    while (dx > width * 0.5f) dx -= width;
    while (dx < -width * 0.5f) dx += width;
    return dx;
}

Game112Defender::Game112Defender() {
    Reset();
}

void Game112Defender::Init() {
    Reset();
}

void Game112Defender::Reset() {
    score_ = 0;
    lives_ = 3;
    smart_bombs_ = 2;
    wave_ = 1;
    InitWave();
}

void Game112Defender::InitWave() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    px_ = 8.0f;
    py_ = 7.0f;
    vx_ = 0.0f;
    vy_ = 0.0f;
    facing_dir_ = 1;
    carried_human_idx_ = -1;

    // Initialize Humanoids distributed on planet surface
    for (int i = 0; i < MAX_HUMANS; ++i) {
        humans_[i].x = 6.0f + static_cast<float>(i) * 11.0f;
        humans_[i].y = 14.0f;
        humans_[i].alive = true;
        humans_[i].being_abducted = false;
        humans_[i].is_falling = false;
        humans_[i].being_carried = false;
    }

    // Initialize Alien Landers
    int count = std::min(MAX_ALIENS, 3 + wave_);
    for (int i = 0; i < MAX_ALIENS; ++i) {
        if (i < count) {
            aliens_[i].x = WrapX(px_ + 12.0f + static_cast<float>(i) * 6.5f);
            aliens_[i].y = 2.0f + static_cast<float>(i % 3) * 1.5f;
            aliens_[i].vx = (i % 2 == 0) ? 2.5f : -2.5f;
            aliens_[i].vy = 0.0f;
            aliens_[i].active = true;
            aliens_[i].is_mutant = false;
            aliens_[i].abducted_human_idx = -1;
        } else {
            aliens_[i].active = false;
        }
    }

    for (int i = 0; i < MAX_LASERS; ++i) {
        lasers_[i].active = false;
    }
}

void Game112Defender::TriggerSmartBomb() {
    if (smart_bombs_ <= 0 || state_ != STATE_PLAYING) return;
    smart_bombs_--;

    for (int i = 0; i < MAX_ALIENS; ++i) {
        if (aliens_[i].active) {
            float dx = std::abs(WrapDistX(aliens_[i].x, px_));
            if (dx <= 8.5f) { // On-screen blast radius
                aliens_[i].active = false;
                score_ += 150;
                // If carrying human, drop human safely
                int h_idx = aliens_[i].abducted_human_idx;
                if (h_idx >= 0 && h_idx < MAX_HUMANS && humans_[h_idx].alive) {
                    humans_[h_idx].being_abducted = false;
                    humans_[h_idx].is_falling = true;
                }
            }
        }
    }
}

void Game112Defender::FireLaser() {
    for (int i = 0; i < MAX_LASERS; ++i) {
        if (!lasers_[i].active) {
            lasers_[i].x = px_ + static_cast<float>(facing_dir_) * 1.0f;
            lasers_[i].y = py_;
            lasers_[i].vx = static_cast<float>(facing_dir_) * 26.0f;
            lasers_[i].active = true;
            break;
        }
    }
}

void Game112Defender::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_PLAYER_DYING) {
        if (state_timer_ > 1.2f) {
            lives_--;
            if (lives_ <= 0) {
                state_ = STATE_GAME_OVER;
            } else {
                state_ = STATE_PLAYING;
                px_ = 8.0f;
                py_ = 7.0f;
                vx_ = 0.0f;
                vy_ = 0.0f;
                carried_human_idx_ = -1;
            }
        }
        return;
    }

    if (state_ == STATE_WAVE_CLEAR) {
        if (state_timer_ > 1.5f) {
            wave_++;
            if (smart_bombs_ < 3) smart_bombs_++;
            InitWave();
        }
        return;
    }

    // Input Handling
    if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
        FireLaser();
    }
    if ((buttons & BTN_B) && !(prev_buttons & BTN_B)) {
        TriggerSmartBomb();
    }

    UpdatePlayer(dt, buttons);
    UpdateAliens(dt);
    UpdateLasers(dt);
    UpdateHumans(dt);
    CheckCollisions();
    CheckWaveClear();
}

void Game112Defender::UpdatePlayer(float dt, uint32_t buttons) {
    float accel = 20.0f;
    float drag = 0.90f;

    if (buttons & BTN_LEFT) {
        vx_ -= accel * dt;
        facing_dir_ = -1;
    }
    if (buttons & BTN_RIGHT) {
        vx_ += accel * dt;
        facing_dir_ = 1;
    }
    if (buttons & BTN_UP) {
        vy_ -= accel * dt;
    }
    if (buttons & BTN_DOWN) {
        vy_ += accel * dt;
    }

    vx_ *= drag;
    vy_ *= drag;

    px_ = WrapX(px_ + vx_ * dt);
    py_ += vy_ * dt;

    // Bounds limit
    if (py_ < 1.0f) { py_ = 1.0f; vy_ = 0.0f; }
    if (py_ > 14.0f) { py_ = 14.0f; vy_ = 0.0f; }

    // If carrying a human and touched ground (py >= 13.5), land human safely
    if (carried_human_idx_ >= 0) {
        int h = carried_human_idx_;
        if (py_ >= 13.5f) {
            humans_[h].being_carried = false;
            humans_[h].y = 14.0f;
            humans_[h].is_falling = false;
            carried_human_idx_ = -1;
            score_ += 500; // Safe landing bonus
        } else {
            humans_[h].x = px_;
            humans_[h].y = py_ + 1.0f;
        }
    }
}

void Game112Defender::UpdateAliens(float dt) {
    for (int i = 0; i < MAX_ALIENS; ++i) {
        if (!aliens_[i].active) continue;

        if (aliens_[i].is_mutant) {
            // Aggressive zig-zag pursuit of player
            float dx = WrapDistX(px_, aliens_[i].x);
            float dy = py_ - aliens_[i].y;
            aliens_[i].vx = (dx > 0) ? 6.5f : -6.5f;
            aliens_[i].vy = (dy > 0) ? 4.5f : -4.5f;
            aliens_[i].x = WrapX(aliens_[i].x + aliens_[i].vx * dt);
            aliens_[i].y += aliens_[i].vy * dt;
            if (aliens_[i].y < 1.0f) aliens_[i].y = 1.0f;
            if (aliens_[i].y > 14.0f) aliens_[i].y = 14.0f;
        } else if (aliens_[i].abducted_human_idx >= 0) {
            // Ascending into stratosphere with abducted human
            int h = aliens_[i].abducted_human_idx;
            aliens_[i].vy = -2.8f;
            aliens_[i].y += aliens_[i].vy * dt;
            aliens_[i].x = WrapX(aliens_[i].x + aliens_[i].vx * dt * 0.2f);

            if (h >= 0 && h < MAX_HUMANS && humans_[h].alive) {
                humans_[h].x = aliens_[i].x;
                humans_[h].y = aliens_[i].y + 0.8f;
            }

            // Reached top -> Human dies, Lander becomes Mutant!
            if (aliens_[i].y <= 1.2f) {
                if (h >= 0 && h < MAX_HUMANS) {
                    humans_[h].alive = false;
                    humans_[h].being_abducted = false;
                }
                aliens_[i].abducted_human_idx = -1;
                aliens_[i].is_mutant = true;
            }
        } else {
            // Normal Lander patrol / stalking humans
            aliens_[i].x = WrapX(aliens_[i].x + aliens_[i].vx * dt);

            // Seek closest living free humanoid
            int target_h = -1;
            float min_dist = 999.0f;
            for (int h = 0; h < MAX_HUMANS; ++h) {
                if (humans_[h].alive && !humans_[h].being_abducted && !humans_[h].being_carried) {
                    float dist = std::abs(WrapDistX(aliens_[i].x, humans_[h].x));
                    if (dist < min_dist) {
                        min_dist = dist;
                        target_h = h;
                    }
                }
            }

            if (target_h >= 0 && min_dist < 4.0f) {
                // Descend to capture
                aliens_[i].vy = 2.0f;
                aliens_[i].y += aliens_[i].vy * dt;

                if (aliens_[i].y >= 13.5f) {
                    // Abduct!
                    aliens_[i].abducted_human_idx = target_h;
                    humans_[target_h].being_abducted = true;
                }
            } else {
                // Gentle floating oscillation
                aliens_[i].y += std::sin(state_timer_ * 2.0f + i) * 1.5f * dt;
                if (aliens_[i].y < 2.0f) aliens_[i].y = 2.0f;
                if (aliens_[i].y > 10.0f) aliens_[i].y = 10.0f;
            }
        }
    }
}

void Game112Defender::UpdateLasers(float dt) {
    for (int i = 0; i < MAX_LASERS; ++i) {
        if (!lasers_[i].active) continue;

        lasers_[i].x = WrapX(lasers_[i].x + lasers_[i].vx * dt);
        // Expiration check: if it travels further than half screen width
        float dist = std::abs(WrapDistX(lasers_[i].x, px_));
        if (dist > 9.0f) {
            lasers_[i].active = false;
        }
    }
}

void Game112Defender::UpdateHumans(float dt) {
    for (int i = 0; i < MAX_HUMANS; ++i) {
        if (!humans_[i].alive) continue;

        if (humans_[i].is_falling) {
            humans_[i].y += 4.5f * dt; // Fall gravity

            // Mid-air catch by player
            float dist_p = std::abs(WrapDistX(humans_[i].x, px_));
            if (dist_p < 1.1f && std::abs(humans_[i].y - py_) < 1.1f && carried_human_idx_ == -1) {
                humans_[i].is_falling = false;
                humans_[i].being_carried = true;
                carried_human_idx_ = i;
                score_ += 500; // Catch bonus!
            } else if (humans_[i].y >= 14.0f) {
                // Fatal crash splat on planet surface
                humans_[i].alive = false;
                humans_[i].is_falling = false;
            }
        }
    }
}

void Game112Defender::CheckCollisions() {
    // Laser vs Alien collisions
    for (int l = 0; l < MAX_LASERS; ++l) {
        if (!lasers_[l].active) continue;

        for (int a = 0; a < MAX_ALIENS; ++a) {
            if (!aliens_[a].active) continue;

            float dx = std::abs(WrapDistX(lasers_[l].x, aliens_[a].x));
            float dy = std::abs(lasers_[l].y - aliens_[a].y);

            if (dx < 0.9f && dy < 0.9f) {
                lasers_[l].active = false;
                aliens_[a].active = false;
                score_ += (aliens_[a].is_mutant ? 200 : 150);

                // If lander was abducting a human, release human into freefall!
                int h = aliens_[a].abducted_human_idx;
                if (h >= 0 && h < MAX_HUMANS && humans_[h].alive) {
                    humans_[h].being_abducted = false;
                    humans_[h].is_falling = true;
                }
                break;
            }
        }
    }

    // Alien vs Player collision
    for (int a = 0; a < MAX_ALIENS; ++a) {
        if (!aliens_[a].active) continue;

        float dx = std::abs(WrapDistX(px_, aliens_[a].x));
        float dy = std::abs(py_ - aliens_[a].y);

        if (dx < 0.8f && dy < 0.8f) {
            // Player destroyed
            state_ = STATE_PLAYER_DYING;
            state_timer_ = 0.0f;
            if (carried_human_idx_ >= 0) {
                humans_[carried_human_idx_].being_carried = false;
                humans_[carried_human_idx_].is_falling = true;
                carried_human_idx_ = -1;
            }
            break;
        }
    }
}

void Game112Defender::CheckWaveClear() {
    bool any_alien = false;
    for (int i = 0; i < MAX_ALIENS; ++i) {
        if (aliens_[i].active) {
            any_alien = true;
            break;
        }
    }

    if (!any_alien) {
        state_ = STATE_WAVE_CLEAR;
        state_timer_ = 0.0f;
        score_ += 1000;
    }
}

void Game112Defender::Render(uint8_t* fb) {
    if (!fb) return;
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // 1. Radar Minimap (Top Row y = 0)
    for (int rx = 0; rx < 16; ++rx) {
        set_pixel(rx, 0, 10, 20, 40); // Radar background wire
    }
    // Radar Blips
    for (int h = 0; h < MAX_HUMANS; ++h) {
        if (humans_[h].alive) {
            int rx = static_cast<int>(humans_[h].x / 48.0f * 16.0f);
            set_pixel(rx, 0, 0, 255, 100); // Green human blip
        }
    }
    for (int a = 0; a < MAX_ALIENS; ++a) {
        if (aliens_[a].active) {
            int rx = static_cast<int>(aliens_[a].x / 48.0f * 16.0f);
            set_pixel(rx, 0, aliens_[a].is_mutant ? 255 : 220, aliens_[a].is_mutant ? 30 : 180, 0);
        }
    }
    // Radar Defender blip
    int r_px = static_cast<int>(px_ / 48.0f * 16.0f);
    set_pixel(r_px, 0, 255, 255, 255);

    // 2. Rugged Martian Terrain at y = 15
    for (int sx = 0; sx < 16; ++sx) {
        float world_x = WrapX(px_ - 7.5f + static_cast<float>(sx));
        int height_variant = static_cast<int>(std::sin(world_x * 0.4f) * 1.2f);
        set_pixel(sx, 15, 180, 50, 20); // Martian red rock
        if (height_variant > 0) {
            set_pixel(sx, 14, 140, 40, 15);
        }
    }

    // Camera transform: screen_x = WrapDistX(entity_x, px_) + 7.5f
    // 3. Humanoids
    for (int h = 0; h < MAX_HUMANS; ++h) {
        if (!humans_[h].alive) continue;
        float sx = WrapDistX(humans_[h].x, px_) + 7.5f;
        int isx = static_cast<int>(std::round(sx));
        int isy = static_cast<int>(std::round(humans_[h].y));
        if (isx >= 0 && isx < 16 && isy >= 1 && isy < 16) {
            // Humanoid: Cyan body + flesh head
            set_pixel(isx, isy, 0, 220, 255);
            set_pixel(isx, isy - 1, 255, 200, 160);
        }
    }

    // 4. Aliens
    for (int a = 0; a < MAX_ALIENS; ++a) {
        if (!aliens_[a].active) continue;
        float sx = WrapDistX(aliens_[a].x, px_) + 7.5f;
        int isx = static_cast<int>(std::round(sx));
        int isy = static_cast<int>(std::round(aliens_[a].y));
        if (isx >= 0 && isx < 16 && isy >= 1 && isy < 15) {
            if (aliens_[a].is_mutant) {
                // Mutant: Fierce flashing magenta/orange
                set_pixel(isx, isy, 255, 40, 200);
                set_pixel(isx - 1, isy, 255, 120, 0);
                set_pixel(isx + 1, isy, 255, 120, 0);
            } else {
                // Lander: Lime green saucer
                set_pixel(isx, isy, 100, 255, 40);
                set_pixel(isx, isy - 1, 220, 255, 120);
                set_pixel(isx - 1, isy, 50, 180, 30);
                set_pixel(isx + 1, isy, 50, 180, 30);
            }
        }
    }

    // 5. Lasers
    for (int l = 0; l < MAX_LASERS; ++l) {
        if (!lasers_[l].active) continue;
        float sx = WrapDistX(lasers_[l].x, px_) + 7.5f;
        int isx = static_cast<int>(std::round(sx));
        int isy = static_cast<int>(std::round(lasers_[l].y));
        if (isx >= 0 && isx < 16 && isy >= 1 && isy < 15) {
            set_pixel(isx, isy, 255, 240, 50); // Radiant gold laser pulse
            set_pixel(isx - 1, isy, 255, 100, 0);
        }
    }

    // 6. Defender Ship at center (screen x = 7..8)
    if (state_ == STATE_PLAYING) {
        int sx = 8;
        int sy = static_cast<int>(std::round(py_));
        // Sleek supersonic jet cockpit & delta wings
        set_pixel(sx, sy, 255, 255, 255); // Cockpit
        set_pixel(sx - facing_dir_, sy, 40, 120, 255); // Hull
        set_pixel(sx - facing_dir_ * 2, sy, 255, 100, 20); // Engine jet fire
        set_pixel(sx, sy - 1, 80, 160, 255); // Upper wing fin
    } else if (state_ == STATE_PLAYER_DYING) {
        int sx = 8;
        int sy = static_cast<int>(std::round(py_));
        // Explosion particle shards
        set_pixel(sx, sy, 255, 200, 50);
        set_pixel(sx - 1, sy - 1, 255, 40, 20);
        set_pixel(sx + 1, sy + 1, 255, 80, 0);
        set_pixel(sx + 1, sy - 1, 255, 255, 0);
    }

    // 7. HUD Indicators (Lives & Smart Bombs on top corners)
    for (int l = 0; l < lives_; ++l) {
        set_pixel(l, 1, 0, 255, 255);
    }
    for (int b = 0; b < smart_bombs_; ++b) {
        set_pixel(15 - b, 1, 255, 220, 0);
    }
}

} // namespace arcade