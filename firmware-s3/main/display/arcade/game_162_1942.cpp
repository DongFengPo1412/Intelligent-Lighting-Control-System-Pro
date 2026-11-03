#include "game_162_1942.h"
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

Game162Roll1942::Game162Roll1942() {
    Reset();
}

void Game162Roll1942::Init() {
    Reset();
}

void Game162Roll1942::Reset() {
    state_ = STATE_PLAYING;
    score_ = 0;
    lives_ = 3;
    stage_ = 1;
    state_timer_ = 0.0f;
    enemy_spawn_timer_ = 0.5f;
    boss_active_ = false;

    for (int i = 0; i < MAX_PLAYER_BULLETS; ++i) player_bullets_[i].active = false;
    for (int i = 0; i < MAX_ENEMY_BULLETS; ++i) enemy_bullets_[i].active = false;
    for (int i = 0; i < MAX_ENEMIES; ++i) enemies_[i].active = false;
    for (int i = 0; i < MAX_POW; ++i) pow_items_[i].active = false;

    RespawnPlayer();
}

void Game162Roll1942::RespawnPlayer() {
    px_ = 8.0f;
    py_ = 13.0f;
    speed_ = 6.0f;
    loops_left_ = 3;
    is_looping_ = false;
    loop_timer_ = 0.0f;
    has_wingmen_ = false;
    fire_cooldown_ = 0.0f;
}

void Game162Roll1942::TriggerLoop() {
    if (loops_left_ > 0 && !is_looping_ && state_ == STATE_PLAYING) {
        loops_left_--;
        is_looping_ = true;
        loop_timer_ = 0.8f;
        score_ += 50;
    }
}

void Game162Roll1942::FireCannons() {
    if (fire_cooldown_ > 0.0f || is_looping_ || state_ != STATE_PLAYING) return;

    // Center bullet
    for (int i = 0; i < MAX_PLAYER_BULLETS; ++i) {
        if (!player_bullets_[i].active) {
            player_bullets_[i] = {px_, py_ - 0.8f, -14.0f, true};
            break;
        }
    }

    if (has_wingmen_) {
        for (int i = 0; i < MAX_PLAYER_BULLETS; ++i) {
            if (!player_bullets_[i].active) {
                player_bullets_[i] = {px_ - 1.5f, py_ - 0.4f, -14.0f, true};
                break;
            }
        }
        for (int i = 0; i < MAX_PLAYER_BULLETS; ++i) {
            if (!player_bullets_[i].active) {
                player_bullets_[i] = {px_ + 1.5f, py_ - 0.4f, -14.0f, true};
                break;
            }
        }
    }

    fire_cooldown_ = 0.18f;
}

void Game162Roll1942::SpawnRedFormation() {
    for (int i = 0; i < 4; ++i) {
        enemies_[i] = {static_cast<int8_t>(i), 3.0f + i * 3.0f, 1.0f + i * 1.2f, 0.0f, 3.0f, 1, true, false, true};
    }
    red_squadron_count_ = 4;
    red_squadron_killed_ = 0;
}

void Game162Roll1942::SpawnBoss() {
    boss_active_ = true;
    enemies_[0] = {99, 8.0f, 1.0f, 1.5f, 0.3f, 12, false, true, true};
}

void Game162Roll1942::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_STAGE_CLEAR) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            stage_++;
            state_ = STATE_PLAYING;
            for (int i = 0; i < MAX_ENEMIES; ++i) enemies_[i].active = false;
            for (int i = 0; i < MAX_ENEMY_BULLETS; ++i) enemy_bullets_[i].active = false;
        }
        return;
    }

    if (state_ == STATE_PLAYER_EXPLODING) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                RespawnPlayer();
            } else {
                state_ = STATE_GAME_OVER;
            }
        }
        return;
    }

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            Reset();
        }
        return;
    }

    if (fire_cooldown_ > 0.0f) fire_cooldown_ -= dt;

    if (is_looping_) {
        loop_timer_ -= dt;
        if (loop_timer_ <= 0.0f) {
            is_looping_ = false;
        }
    } else {
        float dx = 0.0f, dy = 0.0f;
        if (buttons & BTN_LEFT)  dx -= 1.0f;
        if (buttons & BTN_RIGHT) dx += 1.0f;
        if (buttons & BTN_UP)    dy -= 1.0f;
        if (buttons & BTN_DOWN)  dy += 1.0f;

        if (dx != 0.0f || dy != 0.0f) {
            float len = std::hypot(dx, dy);
            px_ += (dx / len) * speed_ * dt;
            py_ += (dy / len) * speed_ * dt;
        }

        px_ = std::max(1.5f, std::min(14.5f, px_));
        py_ = std::max(2.0f, std::min(14.5f, py_));
    }

    if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
        FireCannons();
    }
    if ((buttons & BTN_B) && !(prev_buttons & BTN_B)) {
        TriggerLoop();
    }

    // Player bullets update
    for (int i = 0; i < MAX_PLAYER_BULLETS; ++i) {
        if (!player_bullets_[i].active) continue;

        player_bullets_[i].y += player_bullets_[i].vy * dt;
        if (player_bullets_[i].y < -1.0f) {
            player_bullets_[i].active = false;
            continue;
        }

        for (int e = 0; e < MAX_ENEMIES; ++e) {
            if (enemies_[e].active) {
                float hit_r = enemies_[e].is_boss ? 1.8f : 1.1f;
                if (std::hypot(enemies_[e].x - player_bullets_[i].x, enemies_[e].y - player_bullets_[i].y) < hit_r) {
                    enemies_[e].hp--;
                    player_bullets_[i].active = false;

                    if (enemies_[e].hp <= 0) {
                        enemies_[e].active = false;
                        score_ += enemies_[e].is_boss ? 500 : 100;
                        if (enemies_[e].is_red) {
                            red_squadron_killed_++;
                            if (red_squadron_killed_ >= red_squadron_count_) {
                                for (int p = 0; p < MAX_POW; ++p) {
                                    if (!pow_items_[p].active) {
                                        pow_items_[p] = {enemies_[e].x, enemies_[e].y, 1.5f, true};
                                        break;
                                    }
                                }
                                score_ += 1000;
                            }
                        }
                        if (enemies_[e].is_boss) {
                            boss_active_ = false;
                            state_ = STATE_STAGE_CLEAR;
                            state_timer_ = 2.0f;
                            score_ += 3000;
                        }
                    }
                    break;
                }
            }
        }
    }

    // Enemy bullets update
    for (int i = 0; i < MAX_ENEMY_BULLETS; ++i) {
        if (!enemy_bullets_[i].active) continue;

        enemy_bullets_[i].y += enemy_bullets_[i].vy * dt;
        if (enemy_bullets_[i].y > 16.0f) {
            enemy_bullets_[i].active = false;
            continue;
        }

        if (!is_looping_ && std::hypot(enemy_bullets_[i].x - px_, enemy_bullets_[i].y - py_) < 0.9f) {
            enemy_bullets_[i].active = false;
            if (has_wingmen_) {
                has_wingmen_ = false;
            } else {
                lives_--;
                state_ = STATE_PLAYER_EXPLODING;
                state_timer_ = 1.0f;
                return;
            }
        }
    }

    // POW items update
    for (int i = 0; i < MAX_POW; ++i) {
        if (!pow_items_[i].active) continue;

        pow_items_[i].y += pow_items_[i].vy * dt;
        if (pow_items_[i].y > 16.0f) {
            pow_items_[i].active = false;
            continue;
        }

        if (std::hypot(pow_items_[i].x - px_, pow_items_[i].y - py_) < 1.2f) {
            pow_items_[i].active = false;
            has_wingmen_ = true;
            if (loops_left_ < 3) loops_left_++;
            score_ += 500;
        }
    }

    // Spawn enemies
    if (!boss_active_) {
        enemy_spawn_timer_ -= dt;
        if (enemy_spawn_timer_ <= 0.0f) {
            bool has_active = false;
            for (int e = 0; e < MAX_ENEMIES; ++e) {
                if (enemies_[e].active) { has_active = true; break; }
            }

            if (!has_active && (stage_ % 2 == 1)) {
                SpawnRedFormation();
                enemy_spawn_timer_ = 4.0f;
            } else if (!has_active && (stage_ % 2 == 0)) {
                SpawnBoss();
                enemy_spawn_timer_ = 10.0f;
            } else {
                for (int e = 0; e < MAX_ENEMIES; ++e) {
                    if (!enemies_[e].active) {
                        enemies_[e] = {static_cast<int8_t>(e), 2.0f + (e * 4.0f), 0.0f, 0.0f, 3.2f, 1, false, false, true};
                        break;
                    }
                }
                enemy_spawn_timer_ = 1.2f;
            }
        }
    }

    // Update enemies
    for (int e = 0; e < MAX_ENEMIES; ++e) {
        if (!enemies_[e].active) continue;

        enemies_[e].x += enemies_[e].vx * dt;
        enemies_[e].y += enemies_[e].vy * dt;

        if (enemies_[e].is_boss) {
            if (enemies_[e].x <= 3.0f || enemies_[e].x >= 13.0f) {
                enemies_[e].vx = -enemies_[e].vx;
            }
            if (static_cast<int>(enemies_[e].y * 10.0f) % 25 == 0) {
                for (int b = 0; b < MAX_ENEMY_BULLETS; ++b) {
                    if (!enemy_bullets_[b].active) {
                        enemy_bullets_[b] = {enemies_[e].x, enemies_[e].y + 1.2f, 5.0f, true};
                        break;
                    }
                }
            }
        } else {
            if (enemies_[e].y > 16.5f) {
                enemies_[e].active = false;
                continue;
            }
        }

        if (!is_looping_ && std::hypot(enemies_[e].x - px_, enemies_[e].y - py_) < 1.0f) {
            enemies_[e].active = false;
            if (has_wingmen_) {
                has_wingmen_ = false;
            } else {
                lives_--;
                state_ = STATE_PLAYER_EXPLODING;
                state_timer_ = 1.0f;
                return;
            }
        }
    }
}

void Game162Roll1942::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx]     = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Ocean waves
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if ((x + y * 3) % 19 == 0) {
                set_pixel(x, y, 10, 40, 110);
            }
        }
    }

    // POW
    for (int i = 0; i < MAX_POW; ++i) {
        if (pow_items_[i].active) {
            int px = static_cast<int>(std::round(pow_items_[i].x));
            int py = static_cast<int>(std::round(pow_items_[i].y));
            set_pixel(px, py, 255, 120, 0);
            set_pixel(px, py - 1, 255, 220, 0);
        }
    }

    // Enemies
    for (int e = 0; e < MAX_ENEMIES; ++e) {
        if (enemies_[e].active) {
            int ex = static_cast<int>(std::round(enemies_[e].x));
            int ey = static_cast<int>(std::round(enemies_[e].y));
            if (enemies_[e].is_boss) {
                for (int bx = -2; bx <= 2; ++bx) {
                    set_pixel(ex + bx, ey, 90, 110, 90);
                    set_pixel(ex + bx, ey - 1, 120, 140, 120);
                }
            } else if (enemies_[e].is_red) {
                set_pixel(ex, ey, 255, 30, 30);
            } else {
                set_pixel(ex, ey, 140, 150, 160);
            }
        }
    }

    // Enemy bullets
    for (int i = 0; i < MAX_ENEMY_BULLETS; ++i) {
        if (enemy_bullets_[i].active) {
            int bx = static_cast<int>(std::round(enemy_bullets_[i].x));
            int by = static_cast<int>(std::round(enemy_bullets_[i].y));
            set_pixel(bx, by, 255, 60, 60);
        }
    }

    // Player bullets
    for (int i = 0; i < MAX_PLAYER_BULLETS; ++i) {
        if (player_bullets_[i].active) {
            int bx = static_cast<int>(std::round(player_bullets_[i].x));
            int by = static_cast<int>(std::round(player_bullets_[i].y));
            set_pixel(bx, by, 255, 255, 100);
        }
    }

    // Player P-38
    int px = static_cast<int>(std::round(px_));
    int py = static_cast<int>(std::round(py_));
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        if (is_looping_) {
            set_pixel(px, py, 255, 255, 255);
            set_pixel(px - 1, py, 255, 215, 0);
            set_pixel(px + 1, py, 255, 215, 0);
        } else {
            set_pixel(px, py, 0, 220, 255);
            set_pixel(px, py - 1, 240, 240, 240);
            set_pixel(px - 1, py, 0, 150, 220);
            set_pixel(px + 1, py, 0, 150, 220);

            if (has_wingmen_) {
                set_pixel(px - 2, py + 1, 0, 255, 140);
                set_pixel(px + 2, py + 1, 0, 255, 140);
            }
        }
    } else if (state_ == STATE_PLAYER_EXPLODING) {
        set_pixel(px, py, 255, 80, 0);
        set_pixel(px - 1, py, 255, 200, 0);
        set_pixel(px + 1, py, 255, 200, 0);
    }
}

} // namespace arcade
