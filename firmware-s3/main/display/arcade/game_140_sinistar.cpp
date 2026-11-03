#include "game_140_sinistar.h"
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

Game140Sinistar::Game140Sinistar()
    : state_(STATE_PLAYING),
      state_timer_(0.0f),
      score_(0),
      lives_(3),
      level_(1),
      px_(7.5f),
      py_(7.5f),
      vx_(0.0f),
      vy_(0.0f),
      angle_(-1.5707963f),
      sinibombs_(3),
      sinistar_alive_(false),
      sinistar_pieces_(0),
      sinistar_hp_(5),
      sinistar_x_(7.5f),
      sinistar_y_(1.0f) {
    Reset();
}

void Game140Sinistar::Init() {
    Reset();
}

void Game140Sinistar::Reset() {
    score_ = 0;
    lives_ = 3;
    level_ = 1;
    InitLevel();
}

void Game140Sinistar::InitLevel() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    px_ = 7.5f;
    py_ = 7.5f;
    vx_ = 0.0f;
    vy_ = 0.0f;
    angle_ = -1.5707963f;
    sinibombs_ = 3;

    for (int i = 0; i < MAX_BULLETS; ++i) bullets_[i].active = false;
    for (int i = 0; i < MAX_BOMBS; ++i) active_bombs_[i].active = false;
    for (int i = 0; i < MAX_CRYSTALS; ++i) crystals_[i].active = false;

    sinistar_alive_ = false;
    sinistar_pieces_ = 0;
    sinistar_hp_ = 5;
    sinistar_x_ = 7.5f;
    sinistar_y_ = 1.0f;

    asteroids_[0] = {3.0f, 4.0f, 4};
    asteroids_[1] = {12.0f, 4.0f, 4};
    asteroids_[2] = {4.0f, 12.0f, 4};
    asteroids_[3] = {12.0f, 12.0f, 4};

    workers_[0] = {2.0f, 2.0f, 1.2f, 0.8f, false, true, 0.0f};
    workers_[1] = {13.0f, 13.0f, -1.2f, -0.8f, false, true, 0.0f};
}

void Game140Sinistar::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_PLAYING) {
        float turn_speed = 4.5f;
        if (buttons & BTN_LEFT)  angle_ -= turn_speed * dt;
        if (buttons & BTN_RIGHT) angle_ += turn_speed * dt;

        float thrust = 10.0f;
        if (buttons & BTN_UP) {
            vx_ += std::cos(angle_) * thrust * dt;
            vy_ += std::sin(angle_) * thrust * dt;
        }

        vx_ *= 0.96f;
        vy_ *= 0.96f;

        px_ = std::fmod(px_ + vx_ * dt, 16.0f);
        if (px_ < 0.0f) px_ += 16.0f;
        py_ = std::fmod(py_ + vy_ * dt, 16.0f);
        if (py_ < 0.0f) py_ += 16.0f;

        // Fire Laser (BTN_A)
        if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
            for (int i = 0; i < MAX_BULLETS; ++i) {
                if (!bullets_[i].active) {
                    bullets_[i].x = px_ + std::cos(angle_) * 0.8f;
                    bullets_[i].y = py_ + std::sin(angle_) * 0.8f;
                    bullets_[i].vx = std::cos(angle_) * 16.0f;
                    bullets_[i].vy = std::sin(angle_) * 16.0f;
                    bullets_[i].active = true;
                    break;
                }
            }
        }

        // Fire Sinibomb (BTN_B)
        if ((buttons & BTN_B) && !(prev_buttons & BTN_B)) {
            if (sinibombs_ > 0) {
                for (int i = 0; i < MAX_BOMBS; ++i) {
                    if (!active_bombs_[i].active) {
                        sinibombs_--;
                        active_bombs_[i].x = px_;
                        active_bombs_[i].y = py_;
                        active_bombs_[i].vx = std::cos(angle_) * 10.0f;
                        active_bombs_[i].vy = std::sin(angle_) * 10.0f;
                        active_bombs_[i].active = true;
                        break;
                    }
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

                for (int k = 0; k < NUM_ASTEROIDS; ++k) {
                    if (asteroids_[k].hp > 0 &&
                        std::abs(bullets_[i].x - asteroids_[k].x) < 1.1f &&
                        std::abs(bullets_[i].y - asteroids_[k].y) < 1.1f) {
                        bullets_[i].active = false;
                        asteroids_[k].hp--;
                        score_ += 20;

                        for (int c = 0; c < MAX_CRYSTALS; ++c) {
                            if (!crystals_[c].active) {
                                crystals_[c].x = asteroids_[k].x + (bullets_[i].vx / 16.0f) * 0.8f;
                                crystals_[c].y = asteroids_[k].y + (bullets_[i].vy / 16.0f) * 0.8f;
                                crystals_[c].active = true;
                                break;
                            }
                        }
                        break;
                    }
                }

                if (bullets_[i].active) {
                    for (int w = 0; w < NUM_WORKERS; ++w) {
                        if (workers_[w].alive &&
                            std::abs(bullets_[i].x - workers_[w].x) < 0.9f &&
                            std::abs(bullets_[i].y - workers_[w].y) < 0.9f) {
                            workers_[w].alive = false;
                            workers_[w].respawn_timer = 3.0f;
                            bullets_[i].active = false;
                            score_ += 150;
                            break;
                        }
                    }
                }
            }
        }

        // Crystals collection
        for (int c = 0; c < MAX_CRYSTALS; ++c) {
            if (crystals_[c].active &&
                std::abs(px_ - crystals_[c].x) < 1.0f &&
                std::abs(py_ - crystals_[c].y) < 1.0f) {
                crystals_[c].active = false;
                if (sinibombs_ < 20) sinibombs_++;
                score_ += 100;
            }
        }

        // Workers
        for (int w = 0; w < NUM_WORKERS; ++w) {
            if (!workers_[w].alive) {
                workers_[w].respawn_timer -= dt;
                if (workers_[w].respawn_timer <= 0.0f) {
                    workers_[w].x = 0.5f;
                    workers_[w].y = 0.5f;
                    workers_[w].alive = true;
                    workers_[w].has_crystal = false;
                }
                continue;
            }

            if (!workers_[w].has_crystal) {
                int target_c = -1;
                float min_d = 999.0f;
                for (int c = 0; c < MAX_CRYSTALS; ++c) {
                    if (crystals_[c].active) {
                        float d = std::hypot(crystals_[c].x - workers_[w].x, crystals_[c].y - workers_[w].y);
                        if (d < min_d) { min_d = d; target_c = c; }
                    }
                }
                if (target_c != -1) {
                    float ang = std::atan2(crystals_[target_c].y - workers_[w].y,
                                           crystals_[target_c].x - workers_[w].x);
                    workers_[w].vx = std::cos(ang) * 2.5f;
                    workers_[w].vy = std::sin(ang) * 2.5f;
                    if (min_d < 0.6f) {
                        crystals_[target_c].active = false;
                        workers_[w].has_crystal = true;
                    }
                }
            } else {
                float ang = std::atan2(sinistar_y_ - workers_[w].y, sinistar_x_ - workers_[w].x);
                workers_[w].vx = std::cos(ang) * 2.5f;
                workers_[w].vy = std::sin(ang) * 2.5f;
                if (std::hypot(sinistar_x_ - workers_[w].x, sinistar_y_ - workers_[w].y) < 1.0f) {
                    workers_[w].has_crystal = false;
                    sinistar_pieces_++;
                    if (sinistar_pieces_ >= 6 && !sinistar_alive_) {
                        sinistar_alive_ = true;
                    }
                }
            }

            workers_[w].x = std::fmod(workers_[w].x + workers_[w].vx * dt, 16.0f);
            if (workers_[w].x < 0.0f) workers_[w].x += 16.0f;
            workers_[w].y = std::fmod(workers_[w].y + workers_[w].vy * dt, 16.0f);
            if (workers_[w].y < 0.0f) workers_[w].y += 16.0f;
        }

        // Sinistar Boss
        if (sinistar_alive_) {
            float s_speed = 3.5f;
            float ang = std::atan2(py_ - sinistar_y_, px_ - sinistar_x_);
            sinistar_x_ += std::cos(ang) * s_speed * dt;
            sinistar_y_ += std::sin(ang) * s_speed * dt;

            if (std::abs(px_ - sinistar_x_) < 1.2f && std::abs(py_ - sinistar_y_) < 1.2f) {
                if (lives_ > 0) lives_--;
                state_ = STATE_SHIP_DEVOURED;
                state_timer_ = 0.0f;
                return;
            }
        }

        // Sinibombs
        for (int i = 0; i < MAX_BOMBS; ++i) {
            if (active_bombs_[i].active) {
                if (sinistar_alive_) {
                    float ang = std::atan2(sinistar_y_ - active_bombs_[i].y,
                                           sinistar_x_ - active_bombs_[i].x);
                    active_bombs_[i].vx = std::cos(ang) * 14.0f;
                    active_bombs_[i].vy = std::sin(ang) * 14.0f;
                }
                active_bombs_[i].x += active_bombs_[i].vx * dt;
                active_bombs_[i].y += active_bombs_[i].vy * dt;

                if (active_bombs_[i].x < 0.0f || active_bombs_[i].x >= 16.0f ||
                    active_bombs_[i].y < 0.0f || active_bombs_[i].y >= 16.0f) {
                    active_bombs_[i].active = false;
                    continue;
                }

                if (sinistar_alive_ &&
                    std::abs(active_bombs_[i].x - sinistar_x_) < 1.5f &&
                    std::abs(active_bombs_[i].y - sinistar_y_) < 1.5f) {
                    active_bombs_[i].active = false;
                    sinistar_hp_--;
                    score_ += 400;
                    if (sinistar_hp_ <= 0) {
                        sinistar_alive_ = false;
                        score_ += 2000;
                        state_ = STATE_STAGE_CLEAR;
                        state_timer_ = 0.0f;
                        return;
                    }
                }
            }
        }
    } else if (state_ == STATE_STAGE_CLEAR || state_ == STATE_SHIP_DEVOURED) {
        state_timer_ += dt;
        if (state_timer_ >= 1.5f) {
            if (state_ == STATE_STAGE_CLEAR) {
                level_++;
                InitLevel();
            } else if (state_ == STATE_SHIP_DEVOURED) {
                if (lives_ > 0) {
                    px_ = 7.5f;
                    py_ = 7.5f;
                    vx_ = 0.0f;
                    vy_ = 0.0f;
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

void Game140Sinistar::Render(uint8_t* fb) {
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

    // Asteroids
    for (int i = 0; i < NUM_ASTEROIDS; ++i) {
        if (asteroids_[i].hp > 0) {
            int ax = static_cast<int>(std::round(asteroids_[i].x));
            int ay = static_cast<int>(std::round(asteroids_[i].y));
            set_pixel(ax, ay, 140, 110, 80);
            set_pixel(ax + 1, ay, 100, 80, 50);
            set_pixel(ax, ay + 1, 100, 80, 50);
        }
    }

    // Crystals
    for (int i = 0; i < MAX_CRYSTALS; ++i) {
        if (crystals_[i].active) {
            set_pixel(static_cast<int>(std::round(crystals_[i].x)),
                      static_cast<int>(std::round(crystals_[i].y)), 180, 255, 255);
        }
    }

    // Workers
    for (int i = 0; i < NUM_WORKERS; ++i) {
        if (workers_[i].alive) {
            int wx = static_cast<int>(std::round(workers_[i].x));
            int wy = static_cast<int>(std::round(workers_[i].y));
            set_pixel(wx, wy, 255, 100, 30);
            if (workers_[i].has_crystal) set_pixel(wx, wy - 1, 255, 255, 255);
        }
    }

    // Sinistar
    if (sinistar_alive_) {
        int sx = static_cast<int>(std::round(sinistar_x_));
        int sy = static_cast<int>(std::round(sinistar_y_));
        for (int ox = -1; ox <= 1; ++ox) {
            for (int oy = -1; oy <= 1; ++oy) {
                set_pixel(sx + ox, sy + oy, 160, 160, 180);
            }
        }
        set_pixel(sx - 1, sy - 1, 255, 20, 20);
        set_pixel(sx + 1, sy - 1, 255, 20, 20);
        set_pixel(sx, sy + 1, 40, 0, 0);
    } else if (sinistar_pieces_ > 0) {
        int sx = static_cast<int>(std::round(sinistar_x_));
        int sy = static_cast<int>(std::round(sinistar_y_));
        for (int p = 0; p < std::min(static_cast<int>(sinistar_pieces_), 6); ++p) {
            set_pixel(sx + (p % 3) - 1, sy + (p / 3) - 1, 90, 90, 110);
        }
    }

    // Bullets
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (bullets_[i].active) {
            set_pixel(static_cast<int>(std::round(bullets_[i].x)),
                      static_cast<int>(std::round(bullets_[i].y)), 255, 255, 100);
        }
    }

    // Sinibombs
    for (int i = 0; i < MAX_BOMBS; ++i) {
        if (active_bombs_[i].active) {
            set_pixel(static_cast<int>(std::round(active_bombs_[i].x)),
                      static_cast<int>(std::round(active_bombs_[i].y)), 255, 40, 220);
        }
    }

    // Player
    int px = static_cast<int>(std::round(px_));
    int py = static_cast<int>(std::round(py_));
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        set_pixel(px, py, 50, 180, 255);
        int nx = static_cast<int>(std::round(px_ + std::cos(angle_) * 1.1f));
        int ny = static_cast<int>(std::round(py_ + std::sin(angle_) * 1.1f));
        set_pixel(nx, ny, 255, 255, 255);
    } else if (state_ == STATE_SHIP_DEVOURED) {
        set_pixel(px, py, 255, 50, 20);
        set_pixel(px - 1, py, 255, 150, 20);
        set_pixel(px + 1, py, 255, 150, 20);
    }

    // Bombs count on row 15
    for (int b = 0; b < std::min(static_cast<int>(sinibombs_), 5); ++b) {
        set_pixel(b * 2, 15, 255, 60, 240);
    }
}

} // namespace arcade
