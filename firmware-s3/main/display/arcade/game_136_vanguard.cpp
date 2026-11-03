#include "game_136_vanguard.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

static constexpr uint16_t BTN_UP    = (1 << 0);
static constexpr uint16_t BTN_DOWN  = (1 << 1);
static constexpr uint16_t BTN_LEFT  = (1 << 2);
static constexpr uint16_t BTN_RIGHT = (1 << 3);
static constexpr uint16_t BTN_A     = (1 << 4);
static constexpr uint16_t BTN_B     = (1 << 5);

Game136Vanguard::Game136Vanguard()
    : state_(STATE_PLAYING),
      state_timer_(0.0f),
      score_(0),
      lives_(3),
      level_(1),
      fuel_(100.0f),
      zone_(ZONE_MOUNTAIN),
      px_(2.0f),
      py_(7.5f),
      heading_x_(1.0f),
      heading_y_(0.0f),
      invulnerable_timer_(0.0f),
      has_energy_pod_(false),
      gond_hp_(3),
      gond_shield_angle_(0.0f) {
    Reset();
}

void Game136Vanguard::Init() {
    Reset();
}

void Game136Vanguard::Reset() {
    score_ = 0;
    lives_ = 3;
    level_ = 1;
    InitLevel();
}

void Game136Vanguard::InitZoneMountain() {
    zone_ = ZONE_MOUNTAIN;
    for (int i = 0; i < 16; ++i) {
        top_walls_[i] = 2.0f + std::sin(i * 0.5f) * 1.0f;
        bot_walls_[i] = 13.0f - std::sin(i * 0.5f) * 1.0f;
    }

    float ex[NUM_ENEMIES] = {10.0f, 13.0f, 15.0f};
    float ey[NUM_ENEMIES] = {5.0f, 9.0f, 7.0f};
    float evx[NUM_ENEMIES] = {-2.0f, -2.5f, -3.0f};
    float evy[NUM_ENEMIES] = {0.5f, -0.6f, 0.0f};

    for (int i = 0; i < NUM_ENEMIES; ++i) {
        enemies_[i].x = ex[i];
        enemies_[i].y = ey[i];
        enemies_[i].vx = evx[i];
        enemies_[i].vy = evy[i];
        enemies_[i].alive = true;
    }

    energy_pod_.x = 14.0f;
    energy_pod_.y = 7.5f;
    energy_pod_.collected = false;
    has_energy_pod_ = true;
}

void Game136Vanguard::InitZoneStripe() {
    zone_ = ZONE_STRIPE;
    px_ = 7.5f;
    py_ = 13.0f;
    heading_x_ = 0.0f;
    heading_y_ = -1.0f;

    for (int i = 0; i < 16; ++i) {
        top_walls_[i] = 2.0f;
        bot_walls_[i] = 13.0f;
    }

    float ex[NUM_ENEMIES] = {6.0f, 9.0f, 7.5f};
    float ey[NUM_ENEMIES] = {2.0f, 4.0f, 1.0f};
    float evx[NUM_ENEMIES] = {1.0f, -1.2f, 0.0f};
    float evy[NUM_ENEMIES] = {1.5f, 1.2f, 2.0f};

    for (int i = 0; i < NUM_ENEMIES; ++i) {
        enemies_[i].x = ex[i];
        enemies_[i].y = ey[i];
        enemies_[i].vx = evx[i];
        enemies_[i].vy = evy[i];
        enemies_[i].alive = true;
    }

    energy_pod_.x = 7.5f;
    energy_pod_.y = 3.0f;
    energy_pod_.collected = false;
    has_energy_pod_ = true;
}

void Game136Vanguard::InitZoneGond() {
    zone_ = ZONE_GOND;
    px_ = 7.5f;
    py_ = 13.5f;
    heading_x_ = 0.0f;
    heading_y_ = -1.0f;
    gond_hp_ = 3;
    gond_shield_angle_ = 0.0f;

    for (int i = 0; i < NUM_ENEMIES; ++i) {
        enemies_[i].alive = false;
    }
    has_energy_pod_ = false;
}

void Game136Vanguard::InitLevel() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    fuel_ = 100.0f;
    px_ = 2.0f;
    py_ = 7.5f;
    heading_x_ = 1.0f;
    heading_y_ = 0.0f;
    invulnerable_timer_ = 0.0f;

    for (int i = 0; i < MAX_BULLETS; ++i) {
        bullets_[i].active = false;
    }

    InitZoneMountain();
}

void Game136Vanguard::CrashShip() {
    if (lives_ > 0) lives_--;
    state_ = STATE_SHIP_CRASH;
    state_timer_ = 0.0f;
}

void Game136Vanguard::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_PLAYING) {
        fuel_ -= 2.5f * dt;
        if (fuel_ <= 0.0f) {
            fuel_ = 0.0f;
            CrashShip();
            return;
        }

        if (invulnerable_timer_ > 0.0f) {
            invulnerable_timer_ -= dt;
            if (invulnerable_timer_ < 0.0f) invulnerable_timer_ = 0.0f;
        }

        float move_speed = 7.0f;
        float vx = 0.0f;
        float vy = 0.0f;
        if (buttons & BTN_LEFT)  vx -= move_speed;
        if (buttons & BTN_RIGHT) vx += move_speed;
        if (buttons & BTN_UP)    vy -= move_speed;
        if (buttons & BTN_DOWN)  vy += move_speed;

        if (vx != 0.0f || vy != 0.0f) {
            float mag = std::hypot(vx, vy);
            heading_x_ = vx / mag;
            heading_y_ = vy / mag;
        }

        px_ += vx * dt;
        py_ += vy * dt;

        if (zone_ == ZONE_MOUNTAIN) {
            px_ = std::max(0.5f, std::min(14.5f, px_));
            int c_idx = std::max(0, std::min(15, static_cast<int>(std::round(px_))));
            float top_b = top_walls_[c_idx];
            float bot_b = bot_walls_[c_idx];

            if ((py_ <= top_b || py_ >= bot_b) && invulnerable_timer_ <= 0.0f) {
                CrashShip();
                return;
            }
            py_ = std::max(top_b + 0.2f, std::min(bot_b - 0.2f, py_));
        } else {
            px_ = std::max(2.5f, std::min(12.5f, px_));
            py_ = std::max(0.5f, std::min(14.5f, py_));
        }

        // Fire cannon forward (BTN_A)
        if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
            for (int i = 0; i < MAX_BULLETS; ++i) {
                if (!bullets_[i].active) {
                    bullets_[i].x = px_ + heading_x_ * 0.8f;
                    bullets_[i].y = py_ + heading_y_ * 0.8f;
                    bullets_[i].vx = heading_x_ * 15.0f;
                    bullets_[i].vy = heading_y_ * 15.0f;
                    bullets_[i].active = true;
                    break;
                }
            }
        }
        // Fire cannon reverse (BTN_B)
        if ((buttons & BTN_B) && !(prev_buttons & BTN_B)) {
            for (int i = 0; i < MAX_BULLETS; ++i) {
                if (!bullets_[i].active) {
                    bullets_[i].x = px_ - heading_x_ * 0.8f;
                    bullets_[i].y = py_ - heading_y_ * 0.8f;
                    bullets_[i].vx = -heading_x_ * 15.0f;
                    bullets_[i].vy = -heading_y_ * 15.0f;
                    bullets_[i].active = true;
                    break;
                }
            }
        }

        // Bullets update
        for (int i = 0; i < MAX_BULLETS; ++i) {
            if (bullets_[i].active) {
                bullets_[i].x += bullets_[i].vx * dt;
                bullets_[i].y += bullets_[i].vy * dt;
                if (bullets_[i].x < 0.0f || bullets_[i].x >= 16.0f ||
                    bullets_[i].y < 0.0f || bullets_[i].y >= 16.0f) {
                    bullets_[i].active = false;
                    continue;
                }

                // Enemy collision
                for (int k = 0; k < NUM_ENEMIES; ++k) {
                    if (enemies_[k].alive) {
                        if (std::abs(bullets_[i].x - enemies_[k].x) < 1.0f &&
                            std::abs(bullets_[i].y - enemies_[k].y) < 1.0f) {
                            enemies_[k].alive = false;
                            bullets_[i].active = false;
                            score_ += 100;
                            fuel_ = std::min(100.0f, fuel_ + 15.0f);
                            break;
                        }
                    }
                }

                // Gond Boss
                if (bullets_[i].active && zone_ == ZONE_GOND && gond_hp_ > 0) {
                    if (std::abs(bullets_[i].x - 7.5f) < 1.2f && std::abs(bullets_[i].y - 3.5f) < 1.2f) {
                        float norm_angle = std::fmod(gond_shield_angle_, 2.0f * 3.14159265f);
                        if (norm_angle < 0.0f) norm_angle += 2.0f * 3.14159265f;
                        if (norm_angle > 0.8f && norm_angle < 2.5f) {
                            bullets_[i].active = false;
                            gond_hp_--;
                            score_ += 300;
                            if (gond_hp_ <= 0) {
                                score_ += 1000;
                                state_ = STATE_STAGE_CLEAR;
                                state_timer_ = 0.0f;
                                return;
                            }
                        } else {
                            bullets_[i].active = false;
                        }
                    }
                }
            }
        }

        // Energy pod pickup
        if (has_energy_pod_ && !energy_pod_.collected) {
            if (std::abs(px_ - energy_pod_.x) < 1.2f && std::abs(py_ - energy_pod_.y) < 1.2f) {
                energy_pod_.collected = true;
                invulnerable_timer_ = 6.0f;
                fuel_ = 100.0f;
                score_ += 200;
            }
        }

        // Enemies collision
        bool all_dead = true;
        for (int k = 0; k < NUM_ENEMIES; ++k) {
            if (enemies_[k].alive) {
                all_dead = false;
                enemies_[k].x += enemies_[k].vx * dt;
                enemies_[k].y += enemies_[k].vy * dt;

                if (zone_ == ZONE_MOUNTAIN && enemies_[k].x <= 0.0f) {
                    enemies_[k].x = 15.5f;
                } else if (zone_ == ZONE_STRIPE && enemies_[k].y >= 16.0f) {
                    enemies_[k].y = 0.5f;
                }

                if (std::abs(px_ - enemies_[k].x) < 0.9f && std::abs(py_ - enemies_[k].y) < 0.9f) {
                    if (invulnerable_timer_ > 0.0f) {
                        enemies_[k].alive = false;
                        score_ += 200;
                    } else {
                        CrashShip();
                        return;
                    }
                }
            }
        }

        if (zone_ == ZONE_MOUNTAIN && all_dead) {
            score_ += 300;
            InitZoneStripe();
        } else if (zone_ == ZONE_STRIPE && all_dead) {
            score_ += 400;
            InitZoneGond();
        } else if (zone_ == ZONE_GOND) {
            gond_shield_angle_ += 3.0f * dt;
        }
    } else if (state_ == STATE_STAGE_CLEAR || state_ == STATE_SHIP_CRASH) {
        state_timer_ += dt;
        if (state_timer_ >= 1.5f) {
            if (state_ == STATE_STAGE_CLEAR) {
                level_++;
                InitLevel();
            } else if (state_ == STATE_SHIP_CRASH) {
                if (lives_ > 0) {
                    fuel_ = 100.0f;
                    px_ = (zone_ == ZONE_MOUNTAIN) ? 2.0f : 7.5f;
                    py_ = (zone_ == ZONE_MOUNTAIN) ? 7.5f : 13.0f;
                    state_ = STATE_PLAYING;
                    state_timer_ = 0.0f;
                } else {
                    state_ = STATE_GAME_OVER;
                    state_timer_ = 0.0f;
                }
            }
        }
    } else if (state_ == STATE_GAME_OVER) {
        state_timer_ += dt;
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            Reset();
        }
    }
}

void Game136Vanguard::Render(uint8_t* fb) {
    if (!fb) return;
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Cavern / Walls
    if (zone_ == ZONE_MOUNTAIN) {
        for (int x = 0; x < 16; ++x) {
            int top_y = static_cast<int>(std::round(top_walls_[x]));
            int bot_y = static_cast<int>(std::round(bot_walls_[x]));
            for (int y = 0; y <= top_y; ++y) set_pixel(x, y, 100, 50, 20);
            for (int y = bot_y; y < 16; ++y) set_pixel(x, y, 100, 50, 20);
        }
    } else {
        for (int y = 0; y < 16; ++y) {
            set_pixel(1, y, 40, 60, 120);
            set_pixel(2, y, 70, 90, 160);
            set_pixel(13, y, 70, 90, 160);
            set_pixel(14, y, 40, 60, 120);
        }
    }

    // Energy Pod
    if (has_energy_pod_ && !energy_pod_.collected) {
        int epx = static_cast<int>(std::round(energy_pod_.x));
        int epy = static_cast<int>(std::round(energy_pod_.y));
        set_pixel(epx, epy, 255, 240, 50);
        set_pixel(epx + 1, epy, 255, 120, 30);
    }

    // Enemies
    for (int i = 0; i < NUM_ENEMIES; ++i) {
        if (enemies_[i].alive) {
            int ex = static_cast<int>(std::round(enemies_[i].x));
            int ey = static_cast<int>(std::round(enemies_[i].y));
            set_pixel(ex, ey, 240, 50, 40);
            set_pixel(ex, ey - 1, 255, 120, 60);
        }
    }

    // Gond Boss
    if (zone_ == ZONE_GOND && gond_hp_ > 0) {
        set_pixel(7, 3, 255, 255, 255);
        set_pixel(8, 3, 255, 255, 255);
        set_pixel(7, 4, 255, 30, 30);
        set_pixel(8, 4, 255, 30, 30);

        for (int a = 0; a < 4; ++a) {
            float rad = gond_shield_angle_ + a * 0.4f;
            int sx = static_cast<int>(std::round(7.5f + std::cos(rad) * 2.5f));
            int sy = static_cast<int>(std::round(3.5f + std::sin(rad) * 2.5f));
            set_pixel(sx, sy, 50, 220, 255);
        }
    }

    // Bullets
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (bullets_[i].active) {
            set_pixel(static_cast<int>(std::round(bullets_[i].x)),
                      static_cast<int>(std::round(bullets_[i].y)), 255, 255, 180);
        }
    }

    // Player
    int px = static_cast<int>(std::round(px_));
    int py = static_cast<int>(std::round(py_));
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        if (invulnerable_timer_ > 0.0f) {
            int flash = static_cast<int>(invulnerable_timer_ * 15.0f) % 3;
            uint8_t cr[3] = {255, 255, 50};
            uint8_t cg[3] = {255, 220, 255};
            uint8_t cb[3] = {255, 50, 220};
            set_pixel(px, py, cr[flash], cg[flash], cb[flash]);
            set_pixel(px - 1, py, cr[flash], cg[flash], cb[flash]);
            set_pixel(px + 1, py, cr[flash], cg[flash], cb[flash]);
        } else {
            set_pixel(px, py, 60, 200, 255);
            set_pixel(px - 1, py, 40, 120, 220);
            set_pixel(px, py - 1, 255, 255, 255);
        }
    } else if (state_ == STATE_SHIP_CRASH) {
        set_pixel(px, py, 255, 120, 30);
        set_pixel(px - 1, py, 255, 40, 20);
        set_pixel(px + 1, py, 255, 40, 20);
    }

    // Fuel gauge
    int fuel_pixels = static_cast<int>(std::round((fuel_ / 100.0f) * 15.0f));
    for (int x = 0; x <= fuel_pixels && x < 16; ++x) {
        set_pixel(x, 15, 50, 220, 60);
    }
}

} // namespace arcade
