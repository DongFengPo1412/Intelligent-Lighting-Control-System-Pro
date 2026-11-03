#include "game_191_finalfight.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

static constexpr uint16_t BTN_UP    = 1 << 0;
static constexpr uint16_t BTN_DOWN  = 1 << 1;
static constexpr uint16_t BTN_LEFT  = 1 << 2;
static constexpr uint16_t BTN_RIGHT = 1 << 3;
static constexpr uint16_t BTN_A     = 1 << 4; // Punch / Piledriver
static constexpr uint16_t BTN_B     = 1 << 5; // Desperation Clothesline

Game191FinalFight::Game191FinalFight() {
    Init();
}

void Game191FinalFight::Init() {
    Reset();
}

void Game191FinalFight::Reset() {
    score_ = 0;
    lives_ = 3;
    stage_ = 1;
    InitStage();
}

void Game191FinalFight::InitStage() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    px_ = 3.0f;
    py_ = 11.0f;
    facing_ = 1;
    speed_ = 5.0f;
    hp_ = 100.0f;
    max_hp_ = 100.0f;

    is_punching_ = false;
    punch_timer_ = 0.0f;
    is_spinning_ = false;
    spin_timer_ = 0.0f;

    grabbed_enemy_idx_ = -1;
    is_piledriving_ = false;
    piledrive_timer_ = 0.0f;
    piledrive_height_ = 0.0f;

    enemies_[0] = {8.0f, 10.0f, 25.0f, 25.0f, 0, true, 0, 0.0f};
    enemies_[1] = {12.0f, 12.0f, 25.0f, 25.0f, 0, true, 0, 0.0f};
    float boss_hp = 60.0f + stage_ * 20.0f;
    enemies_[2] = {14.0f, 10.5f, boss_hp, boss_hp, 1, true, 0, 0.0f};

    barrel_ = {6.0f, 12.0f, false, false, 6.0f, 12.0f};
}

void Game191FinalFight::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_STAGE_CLEAR) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            stage_++;
            InitStage();
        }
        return;
    }

    if (state_ == STATE_HAGGAR_KO) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                px_ = 3.0f;
                py_ = 11.0f;
                hp_ = 100.0f;
                is_punching_ = false;
                is_spinning_ = false;
                grabbed_enemy_idx_ = -1;
                is_piledriving_ = false;
            } else {
                state_ = STATE_GAME_OVER;
            }
        }
        return;
    }

    if (state_ == STATE_GAME_OVER) {
        if (((buttons & BTN_A) && !(prev_buttons & BTN_A)) ||
            ((buttons & BTN_B) && !(prev_buttons & BTN_B))) {
            Reset();
        }
        return;
    }

    // Check Haggar KO
    if (hp_ <= 0.0f) {
        hp_ = 0.0f;
        lives_--;
        state_ = STATE_HAGGAR_KO;
        state_timer_ = 1.5f;
        return;
    }

    // 1. Piledriver Update
    if (is_piledriving_) {
        piledrive_timer_ -= dt;
        if (piledrive_timer_ > 0.2f) {
            piledrive_height_ = std::min(3.0f, piledrive_height_ + 15.0f * dt);
        } else {
            piledrive_height_ = std::max(0.0f, piledrive_height_ - 25.0f * dt);
        }

        if (piledrive_timer_ <= 0.0f) {
            is_piledriving_ = false;
            piledrive_height_ = 0.0f;
            if (grabbed_enemy_idx_ >= 0 && grabbed_enemy_idx_ < MAX_ENEMIES) {
                auto& victim = enemies_[grabbed_enemy_idx_];
                victim.hp -= 40.0f;
                victim.state = 1; // knockdown
                victim.kd_timer = 1.0f;
                victim.x = px_ + facing_ * 0.8f;
                victim.y = py_;
                score_ += 1500;
                if (victim.hp <= 0.0f) {
                    victim.alive = false;
                    score_ += (victim.type == 1) ? 3000 : 1000;
                }

                for (int i = 0; i < MAX_ENEMIES; ++i) {
                    if (i != grabbed_enemy_idx_ && enemies_[i].alive && std::hypot(enemies_[i].x - px_, enemies_[i].y - py_) < 2.0f) {
                        enemies_[i].hp -= 15.0f;
                        enemies_[i].state = 1;
                        enemies_[i].kd_timer = 0.8f;
                        if (enemies_[i].hp <= 0.0f) {
                            enemies_[i].alive = false;
                        }
                    }
                }
            }
            grabbed_enemy_idx_ = -1;
        }
        return;
    }

    // 2. Spinning Clothesline Update
    if (is_spinning_) {
        spin_timer_ -= dt;
        for (int i = 0; i < MAX_ENEMIES; ++i) {
            if (enemies_[i].alive && enemies_[i].state == 0 && std::hypot(enemies_[i].x - px_, enemies_[i].y - py_) < 2.2f) {
                enemies_[i].hp -= 18.0f;
                enemies_[i].state = 1; // knockdown
                enemies_[i].kd_timer = 1.0f;
                enemies_[i].x += (enemies_[i].x > px_) ? 1.5f : -1.5f;
                score_ += 500;
                if (enemies_[i].hp <= 0.0f) {
                    enemies_[i].alive = false;
                    score_ += (enemies_[i].type == 1) ? 3000 : 1000;
                }
            }
        }

        if (spin_timer_ <= 0.0f) {
            is_spinning_ = false;
        }
    }

    // 3. Punch timer
    if (is_punching_) {
        punch_timer_ -= dt;
        if (punch_timer_ <= 0.0f) is_punching_ = false;
    }

    // 4. Movement
    if (!is_spinning_ && !is_punching_) {
        float dx = 0.0f, dy = 0.0f;
        if (buttons & BTN_LEFT)  { dx -= 1.0f; facing_ = -1; }
        if (buttons & BTN_RIGHT) { dx += 1.0f; facing_ = 1; }
        if (buttons & BTN_UP)    dy -= 1.0f;
        if (buttons & BTN_DOWN)  dy += 1.0f;

        if (dx != 0.0f || dy != 0.0f) {
            float inv = 1.0f / std::hypot(dx, dy);
            px_ += dx * inv * speed_ * dt;
            py_ += dy * inv * speed_ * dt;
        }

        px_ = std::max(1.0f, std::min(14.5f, px_));
        py_ = std::max(8.0f, std::min(14.0f, py_));
    }

    // 5. Check Grapple Catch
    if (grabbed_enemy_idx_ < 0 && !is_spinning_ && !is_punching_) {
        for (int i = 0; i < MAX_ENEMIES; ++i) {
            if (enemies_[i].alive && enemies_[i].state == 0 && std::hypot(enemies_[i].x - px_, enemies_[i].y - py_) < 0.6f) {
                grabbed_enemy_idx_ = i;
                enemies_[i].state = 2; // grabbed
                break;
            }
        }
    }

    uint16_t pressed = buttons & ~prev_buttons;

    // 6. Button A: Punch / Piledriver
    if (pressed & BTN_A) {
        if (grabbed_enemy_idx_ >= 0) {
            is_piledriving_ = true;
            piledrive_timer_ = 0.45f;
            piledrive_height_ = 0.0f;
        } else if (!is_punching_ && !is_spinning_) {
            is_punching_ = true;
            punch_timer_ = 0.2f;
            float hit_x = px_ + facing_ * 1.0f;
            float hit_y = py_;
            for (int i = 0; i < MAX_ENEMIES; ++i) {
                if (enemies_[i].alive && enemies_[i].state == 0 && std::hypot(enemies_[i].x - hit_x, enemies_[i].y - hit_y) < 1.0f) {
                    enemies_[i].hp -= 10.0f;
                    score_ += 200;
                    if (enemies_[i].hp <= 0.0f) {
                        enemies_[i].alive = false;
                        enemies_[i].state = 1;
                        score_ += (enemies_[i].type == 1) ? 3000 : 1000;
                    }
                    break;
                }
            }

            if (!barrel_.broken && std::hypot(barrel_.x - hit_x, barrel_.y - hit_y) < 1.2f) {
                barrel_.broken = true;
                barrel_.item_active = true;
                barrel_.item_x = barrel_.x + facing_ * 1.5f;
                barrel_.item_y = barrel_.y;
                score_ += 300;
            }
        }
    }

    // 7. Button B: Desperation Clothesline
    if ((pressed & BTN_B) && !is_spinning_ && !is_piledriving_) {
        if (hp_ > 8.0f) {
            hp_ -= 8.0f;
            is_spinning_ = true;
            spin_timer_ = 0.4f;
            if (grabbed_enemy_idx_ >= 0) {
                enemies_[grabbed_enemy_idx_].state = 0;
                grabbed_enemy_idx_ = -1;
            }

            for (int i = 0; i < MAX_ENEMIES; ++i) {
                if (enemies_[i].alive && enemies_[i].state == 0 && std::hypot(enemies_[i].x - px_, enemies_[i].y - py_) < 2.2f) {
                    enemies_[i].hp -= 18.0f;
                    enemies_[i].state = 1; // knockdown
                    enemies_[i].kd_timer = 1.0f;
                    enemies_[i].x += (enemies_[i].x > px_) ? 1.5f : -1.5f;
                    score_ += 500;
                    if (enemies_[i].hp <= 0.0f) {
                        enemies_[i].alive = false;
                        score_ += (enemies_[i].type == 1) ? 3000 : 1000;
                    }
                }
            }
        }
    }

    // 8. Item collection
    if (barrel_.item_active) {
        if (std::hypot(barrel_.item_x - px_, barrel_.item_y - py_) < 0.9f) {
            barrel_.item_active = false;
            hp_ = std::min(max_hp_, hp_ + 35.0f);
            score_ += 1000;
        }
    }

    // 9. Enemies AI
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].alive) continue;
        if (enemies_[i].state == 1) { // knockdown
            enemies_[i].kd_timer -= dt;
            if (enemies_[i].kd_timer <= 0.0f) enemies_[i].state = 0;
            continue;
        }
        if (enemies_[i].state == 2) { // grabbed
            enemies_[i].x = px_ + facing_ * 0.6f;
            enemies_[i].y = py_;
            continue;
        }

        float edx = px_ - enemies_[i].x;
        float edy = py_ - enemies_[i].y;
        float d = std::hypot(edx, edy);
        if (d > 0.8f) {
            float spd = (enemies_[i].type == 0) ? 2.5f : 3.5f;
            enemies_[i].x += (edx / d) * spd * dt;
            enemies_[i].y += (edy / d) * spd * dt;
        } else {
            if (!is_spinning_ && !is_piledriving_) {
                hp_ -= 15.0f * dt;
                if (hp_ <= 0.0f) {
                    hp_ = 0.0f;
                    lives_--;
                    state_ = STATE_HAGGAR_KO;
                    state_timer_ = 1.5f;
                    return;
                }
            }
        }
    }

    if (!enemies_[2].alive) { // Boss
        state_ = STATE_STAGE_CLEAR;
        state_timer_ = 2.0f;
        score_ += 10000;
    }
}

void Game191FinalFight::Render(uint8_t* fb) {
    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx]     = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Background street
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (y <= 7) {
                set_pixel(x, y, 120, 50, 40);
            } else {
                set_pixel(x, y, 70, 70, 75);
            }
        }
    }

    // Barrel / Item
    if (!barrel_.broken) {
        int bx = static_cast<int>(std::round(barrel_.x));
        int by = static_cast<int>(std::round(barrel_.y));
        set_pixel(bx, by, 140, 80, 30);
        set_pixel(bx, by - 1, 110, 60, 20);
    } else if (barrel_.item_active) {
        int ix = static_cast<int>(std::round(barrel_.item_x));
        int iy = static_cast<int>(std::round(barrel_.item_y));
        set_pixel(ix, iy, 255, 160, 40);
        set_pixel(ix + 1, iy, 255, 230, 180);
    }

    // Enemies
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].alive) continue;
        int ex = static_cast<int>(std::round(enemies_[i].x));
        int ey = static_cast<int>(std::round(enemies_[i].y));
        if (enemies_[i].state == 1) {
            set_pixel(ex, ey, 100, 100, 100);
        } else if (enemies_[i].type == 1) { // Boss Damnd
            set_pixel(ex, ey, 240, 40, 40);
            set_pixel(ex, ey - 1, 230, 210, 50);
            set_pixel(ex, ey + 1, 40, 40, 120);
        } else {
            set_pixel(ex, ey, 220, 140, 40);
            set_pixel(ex, ey - 1, 220, 180, 140);
            set_pixel(ex, ey + 1, 50, 90, 50);
        }
    }

    // Haggar
    int hx = static_cast<int>(std::round(px_));
    int hy = static_cast<int>(std::round(py_ - piledrive_height_));
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        if (is_spinning_) {
            set_pixel(hx, hy, 160, 100, 50);
            set_pixel(hx - 1, hy, 255, 255, 100);
            set_pixel(hx + 1, hy, 255, 255, 100);
            set_pixel(hx, hy - 1, 60, 40, 20);
        } else if (is_piledriving_) {
            set_pixel(hx, hy, 160, 100, 50);
            set_pixel(hx, hy - 1, 160, 100, 50);
            set_pixel(hx, hy + 1, 200, 160, 40);
        } else {
            set_pixel(hx, hy, 180, 120, 70);
            set_pixel(hx, hy - 1, 90, 60, 30);
            set_pixel(hx, hy + 1, 40, 90, 40);
            if (is_punching_) {
                set_pixel(hx + facing_, hy, 255, 220, 80);
            }
        }
    } else if (state_ == STATE_HAGGAR_KO) {
        set_pixel(hx, hy, 255, 50, 0);
    }

    // Health bar at top
    int hp_px = static_cast<int>(std::round((hp_ / max_hp_) * 14.0f));
    for (int x = 0; x < hp_px; ++x) {
        set_pixel(x + 1, 0, 40, 220, 40);
    }
}

} // namespace arcade
