#include "game_135_pleiads.h"
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

Game135Pleiads::Game135Pleiads()
    : state_(STATE_PLAYING),
      state_timer_(0.0f),
      score_(0),
      lives_(3),
      level_(1),
      phase_(PHASE_RADAR),
      px_(7.5f),
      py_(14.0f),
      shields_left_(3),
      shield_active_(false),
      shield_timer_(0.0f),
      mothership_hp_(3),
      mothership_x_(7.5f),
      mothership_dir_(1.0f),
      mothership_destroyed_(false) {
    Reset();
}

void Game135Pleiads::Init() {
    Reset();
}

void Game135Pleiads::Reset() {
    score_ = 0;
    lives_ = 3;
    level_ = 1;
    InitLevel();
}

void Game135Pleiads::InitPhase0() {
    phase_ = PHASE_RADAR;
    for (int i = 0; i < NUM_ENEMIES; ++i) {
        enemies_[i].x = 2.5f + i * 3.5f;
        enemies_[i].y = 3.0f;
        enemies_[i].vx = 2.5f;
        enemies_[i].base_x = enemies_[i].x;
        enemies_[i].swoop_timer = 0.0f;
        enemies_[i].alive = true;
        enemies_[i].shoot_timer = 1.2f + i * 0.5f;
    }
    float bx[NUM_BARRIERS] = {3.0f, 6.5f, 10.0f, 13.5f};
    for (int i = 0; i < NUM_BARRIERS; ++i) {
        barriers_[i].x = bx[i];
        barriers_[i].y = 9.0f;
        barriers_[i].hp = 2;
    }
}

void Game135Pleiads::InitPhase1() {
    phase_ = PHASE_BIRDS;
    for (int i = 0; i < NUM_ENEMIES; ++i) {
        enemies_[i].base_x = 3.0f + i * 3.0f;
        enemies_[i].x = enemies_[i].base_x;
        enemies_[i].y = 2.0f;
        enemies_[i].swoop_timer = i * 0.7f;
        enemies_[i].alive = true;
        enemies_[i].shoot_timer = 1.5f + i * 0.6f;
    }
}

void Game135Pleiads::InitPhase2() {
    phase_ = PHASE_LANDING;
    mothership_hp_ = 3;
    mothership_x_ = 7.5f;
    mothership_dir_ = 1.0f;
    mothership_destroyed_ = false;
    for (int i = 0; i < NUM_ENEMIES; ++i) {
        enemies_[i].alive = false;
    }
}

void Game135Pleiads::InitLevel() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    px_ = 7.5f;
    py_ = 14.0f;
    shields_left_ = 3;
    shield_active_ = false;
    shield_timer_ = 0.0f;

    for (int i = 0; i < MAX_BULLETS; ++i) bullets_[i].active = false;
    for (int i = 0; i < MAX_ENEMY_BULLETS; ++i) enemy_bullets_[i].active = false;

    InitPhase0();
}

void Game135Pleiads::LoseLife() {
    if (lives_ > 0) lives_--;
    state_ = STATE_SHIP_HIT;
    state_timer_ = 0.0f;
}

void Game135Pleiads::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_PLAYING) {
        // Shield
        if ((buttons & BTN_B) && !(prev_buttons & BTN_B)) {
            if (shields_left_ > 0 && !shield_active_) {
                shield_active_ = true;
                shield_timer_ = 1.5f;
                shields_left_--;
            }
        }
        if (shield_active_) {
            shield_timer_ -= dt;
            if (shield_timer_ <= 0.0f) {
                shield_active_ = false;
                shield_timer_ = 0.0f;
            }
        }

        // Horizontal movement
        float move_speed = 8.0f;
        if (buttons & BTN_LEFT)  px_ = std::max(1.0f, px_ - move_speed * dt);
        if (buttons & BTN_RIGHT) px_ = std::min(14.0f, px_ + move_speed * dt);

        // Vertical movement in Phase 2 for landing
        if (phase_ == PHASE_LANDING && mothership_destroyed_) {
            if (buttons & BTN_UP)   py_ = std::max(1.0f, py_ - move_speed * 0.8f * dt);
            if (buttons & BTN_DOWN) py_ = std::min(14.0f, py_ + move_speed * 0.8f * dt);

            if (py_ <= 2.2f) {
                if (px_ >= 5.0f && px_ <= 10.0f) {
                    score_ += 500;
                    state_ = STATE_STAGE_CLEAR;
                    state_timer_ = 0.0f;
                    return;
                } else {
                    LoseLife();
                    return;
                }
            }
        }

        // Fire Laser
        if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
            if (!(phase_ == PHASE_LANDING && mothership_destroyed_)) {
                for (int i = 0; i < MAX_BULLETS; ++i) {
                    if (!bullets_[i].active) {
                        bullets_[i].x = px_;
                        bullets_[i].y = py_ - 1.0f;
                        bullets_[i].active = true;
                        break;
                    }
                }
            }
        }

        // Bullets update
        for (int i = 0; i < MAX_BULLETS; ++i) {
            if (bullets_[i].active) {
                bullets_[i].y -= 16.0f * dt;
                if (bullets_[i].y < 0.0f) {
                    bullets_[i].active = false;
                    continue;
                }

                // Phase 0 barrier collisions
                if (phase_ == PHASE_RADAR) {
                    for (int k = 0; k < NUM_BARRIERS; ++k) {
                        if (barriers_[k].hp > 0) {
                            if (std::abs(bullets_[i].x - barriers_[k].x) < 1.0f &&
                                std::abs(bullets_[i].y - barriers_[k].y) < 0.8f) {
                                barriers_[k].hp--;
                                bullets_[i].active = false;
                                break;
                            }
                        }
                    }
                }

                // Enemy collisions
                if (bullets_[i].active && (phase_ == PHASE_RADAR || phase_ == PHASE_BIRDS)) {
                    for (int k = 0; k < NUM_ENEMIES; ++k) {
                        if (enemies_[k].alive) {
                            if (std::abs(bullets_[i].x - enemies_[k].x) < 1.0f &&
                                std::abs(bullets_[i].y - enemies_[k].y) < 1.0f) {
                                enemies_[k].alive = false;
                                bullets_[i].active = false;
                                score_ += 100;
                                break;
                            }
                        }
                    }
                }

                // Phase 2 mothership collision
                if (bullets_[i].active && phase_ == PHASE_LANDING && !mothership_destroyed_) {
                    if (std::abs(bullets_[i].x - mothership_x_) < 2.0f && bullets_[i].y <= 3.0f) {
                        bullets_[i].active = false;
                        mothership_hp_--;
                        if (mothership_hp_ <= 0) {
                            mothership_destroyed_ = true;
                            score_ += 600;
                        }
                    }
                }
            }
        }

        // Phase specific enemy logic
        if (phase_ == PHASE_RADAR) {
            int alive_count = 0;
            for (int k = 0; k < NUM_ENEMIES; ++k) {
                if (enemies_[k].alive) {
                    alive_count++;
                    enemies_[k].x += enemies_[k].vx * dt;
                    if (enemies_[k].x <= 1.5f || enemies_[k].x >= 13.5f) {
                        enemies_[k].vx = -enemies_[k].vx;
                    }
                    enemies_[k].shoot_timer -= dt;
                    if (enemies_[k].shoot_timer <= 0.0f) {
                        enemies_[k].shoot_timer = 2.0f;
                        for (int b = 0; b < MAX_ENEMY_BULLETS; ++b) {
                            if (!enemy_bullets_[b].active) {
                                enemy_bullets_[b].x = enemies_[k].x;
                                enemy_bullets_[b].y = enemies_[k].y + 0.5f;
                                enemy_bullets_[b].active = true;
                                break;
                            }
                        }
                    }
                }
            }
            if (alive_count == 0) {
                score_ += 300;
                InitPhase1();
            }
        } else if (phase_ == PHASE_BIRDS) {
            int alive_count = 0;
            for (int k = 0; k < NUM_ENEMIES; ++k) {
                if (enemies_[k].alive) {
                    alive_count++;
                    enemies_[k].swoop_timer += dt;
                    if (enemies_[k].swoop_timer > 1.5f) {
                        enemies_[k].y += 4.5f * dt;
                        enemies_[k].x = enemies_[k].base_x + std::sin(enemies_[k].y * 1.5f) * 3.0f;
                        if (enemies_[k].y >= 15.0f) {
                            enemies_[k].y = 2.0f;
                            enemies_[k].swoop_timer = 0.0f;
                        }
                    } else {
                        enemies_[k].x = enemies_[k].base_x;
                    }

                    enemies_[k].shoot_timer -= dt;
                    if (enemies_[k].shoot_timer <= 0.0f) {
                        enemies_[k].shoot_timer = 2.2f;
                        for (int b = 0; b < MAX_ENEMY_BULLETS; ++b) {
                            if (!enemy_bullets_[b].active) {
                                enemy_bullets_[b].x = enemies_[k].x;
                                enemy_bullets_[b].y = enemies_[k].y + 0.5f;
                                enemy_bullets_[b].active = true;
                                break;
                            }
                        }
                    }

                    if (std::abs(enemies_[k].x - px_) < 1.0f && std::abs(enemies_[k].y - py_) < 1.0f) {
                        if (!shield_active_) {
                            LoseLife();
                            return;
                        }
                    }
                }
            }
            if (alive_count == 0) {
                score_ += 400;
                InitPhase2();
            }
        } else if (phase_ == PHASE_LANDING) {
            if (!mothership_destroyed_) {
                mothership_x_ += mothership_dir_ * 3.5f * dt;
                if (mothership_x_ <= 3.0f) {
                    mothership_x_ = 3.0f;
                    mothership_dir_ = 1.0f;
                } else if (mothership_x_ >= 12.0f) {
                    mothership_x_ = 12.0f;
                    mothership_dir_ = -1.0f;
                }
            }
        }

        // Enemy bullets
        for (int b = 0; b < MAX_ENEMY_BULLETS; ++b) {
            if (enemy_bullets_[b].active) {
                enemy_bullets_[b].y += 6.5f * dt;
                if (enemy_bullets_[b].y >= 15.5f) {
                    enemy_bullets_[b].active = false;
                    continue;
                }

                if (phase_ == PHASE_RADAR) {
                    for (int k = 0; k < NUM_BARRIERS; ++k) {
                        if (barriers_[k].hp > 0) {
                            if (std::abs(enemy_bullets_[b].x - barriers_[k].x) < 1.0f &&
                                std::abs(enemy_bullets_[b].y - barriers_[k].y) < 0.8f) {
                                enemy_bullets_[b].active = false;
                                break;
                            }
                        }
                    }
                }

                if (enemy_bullets_[b].active) {
                    if (std::abs(enemy_bullets_[b].x - px_) < 0.9f && std::abs(enemy_bullets_[b].y - py_) < 0.9f) {
                        enemy_bullets_[b].active = false;
                        if (!shield_active_) {
                            LoseLife();
                            return;
                        }
                    }
                }
            }
        }
    } else if (state_ == STATE_STAGE_CLEAR || state_ == STATE_SHIP_HIT) {
        state_timer_ += dt;
        if (state_timer_ >= 1.5f) {
            if (state_ == STATE_STAGE_CLEAR) {
                level_++;
                InitLevel();
            } else if (state_ == STATE_SHIP_HIT) {
                if (lives_ > 0) {
                    px_ = 7.5f;
                    py_ = 14.0f;
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

void Game135Pleiads::Render(uint8_t* fb) {
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

    // Barriers
    if (phase_ == PHASE_RADAR) {
        for (int i = 0; i < NUM_BARRIERS; ++i) {
            if (barriers_[i].hp > 0) {
                int bx = static_cast<int>(std::round(barriers_[i].x));
                int by = static_cast<int>(std::round(barriers_[i].y));
                uint8_t c = (barriers_[i].hp == 2) ? 220 : 120;
                set_pixel(bx, by, 30, c, 220);
                set_pixel(bx - 1, by, 20, c / 2, 160);
            }
        }
    }

    // Enemies
    for (int i = 0; i < NUM_ENEMIES; ++i) {
        if (enemies_[i].alive) {
            int ex = static_cast<int>(std::round(enemies_[i].x));
            int ey = static_cast<int>(std::round(enemies_[i].y));
            if (phase_ == PHASE_RADAR) {
                set_pixel(ex, ey, 220, 200, 30);
                set_pixel(ex, ey - 1, 180, 140, 20);
            } else if (phase_ == PHASE_BIRDS) {
                set_pixel(ex, ey, 255, 60, 160);
                set_pixel(ex - 1, ey, 60, 220, 255);
                set_pixel(ex + 1, ey, 60, 220, 255);
            }
        }
    }

    // Mothership / Runway
    if (phase_ == PHASE_LANDING) {
        if (!mothership_destroyed_) {
            int mx = static_cast<int>(std::round(mothership_x_));
            for (int ox = -2; ox <= 2; ++ox) {
                set_pixel(mx + ox, 2, 220, 50, 50);
            }
            set_pixel(mx, 1, 255, 200, 50);
        } else {
            for (int y = 0; y < 4; ++y) {
                set_pixel(4, y, 50, 220, 50);
                set_pixel(11, y, 50, 220, 50);
            }
            set_pixel(7, 1, 240, 240, 60);
            set_pixel(8, 1, 240, 240, 60);
        }
    }

    // Bullets
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (bullets_[i].active) {
            set_pixel(static_cast<int>(std::round(bullets_[i].x)),
                      static_cast<int>(std::round(bullets_[i].y)), 255, 255, 255);
        }
    }
    for (int i = 0; i < MAX_ENEMY_BULLETS; ++i) {
        if (enemy_bullets_[i].active) {
            set_pixel(static_cast<int>(std::round(enemy_bullets_[i].x)),
                      static_cast<int>(std::round(enemy_bullets_[i].y)), 255, 60, 40);
        }
    }

    // Player
    int px = static_cast<int>(std::round(px_));
    int py = static_cast<int>(std::round(py_));
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        if (shield_active_) {
            set_pixel(px, py, 100, 220, 255);
            set_pixel(px - 1, py, 60, 180, 255);
            set_pixel(px + 1, py, 60, 180, 255);
            set_pixel(px, py - 1, 200, 255, 255);
        } else {
            set_pixel(px, py, 60, 140, 255);
            set_pixel(px - 1, py, 40, 80, 200);
            set_pixel(px + 1, py, 40, 80, 200);
            set_pixel(px, py - 1, 255, 200, 50);
        }
    } else if (state_ == STATE_SHIP_HIT) {
        set_pixel(px, py, 255, 220, 60);
        set_pixel(px - 1, py - 1, 255, 60, 20);
        set_pixel(px + 1, py + 1, 255, 60, 20);
    }

    // Shields indicator
    for (int s = 0; s < std::min(static_cast<int>(shields_left_), 3); ++s) {
        set_pixel(s * 2, 15, 60, 180, 255);
    }
}

} // namespace arcade
