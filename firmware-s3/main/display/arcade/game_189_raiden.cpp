#include "game_189_raiden.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

static constexpr uint16_t BTN_UP    = 1 << 0;
static constexpr uint16_t BTN_DOWN  = 1 << 1;
static constexpr uint16_t BTN_LEFT  = 1 << 2;
static constexpr uint16_t BTN_RIGHT = 1 << 3;
static constexpr uint16_t BTN_A     = 1 << 4; // Fire
static constexpr uint16_t BTN_B     = 1 << 5; // Thermonuclear Bomb

Game189Raiden::Game189Raiden() {
    Init();
}

void Game189Raiden::Init() {
    Reset();
}

void Game189Raiden::Reset() {
    score_ = 0;
    lives_ = 3;
    stage_ = 1;
    weapon_type_ = WEAPON_VULCAN;
    bombs_ = 3;
    InitStage();
}

void Game189Raiden::InitStage() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    px_ = 7.5f;
    py_ = 13.0f;
    speed_ = 6.5f;

    for (int i = 0; i < MAX_BULLETS; ++i) bullets_[i].active = false;
    mega_bomb_.active = false;
    for (int i = 0; i < MAX_ENEMY_BULLETS; ++i) enemy_bullets_[i].active = false;

    enemy_shoot_timer_ = 1.0f;

    crystal_ = {8.0f, 5.0f, 1.2f, 0.8f, 0, 3.0f, true};

    enemies_[0] = {3.0f, 2.0f, 1.5f, 0.5f, 0, 2, true};
    enemies_[1] = {12.0f, 2.0f, -1.5f, 0.5f, 0, 2, true};
    enemies_[2] = {5.0f, 4.0f, 0.0f, 0.0f, 1, 4, true};
    enemies_[3] = {10.0f, 4.0f, 0.0f, 0.0f, 1, 4, true};
    enemies_[4] = {7.5f, 1.5f, 0.8f, 0.0f, 2, static_cast<int16_t>(15 + stage_ * 5), true};
}

void Game189Raiden::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_STAGE_CLEAR) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            stage_++;
            bombs_ = std::min(static_cast<uint8_t>(5), static_cast<uint8_t>(bombs_ + 1));
            InitStage();
        }
        return;
    }

    if (state_ == STATE_SHIP_DESTROYED) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                px_ = 7.5f;
                py_ = 13.0f;
                for (int i = 0; i < MAX_BULLETS; ++i) bullets_[i].active = false;
                for (int i = 0; i < MAX_ENEMY_BULLETS; ++i) enemy_bullets_[i].active = false;
                mega_bomb_.active = false;
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

    // 8-Way move
    float dx = 0.0f, dy = 0.0f;
    if (buttons & BTN_LEFT)  dx -= 1.0f;
    if (buttons & BTN_RIGHT) dx += 1.0f;
    if (buttons & BTN_UP)    dy -= 1.0f;
    if (buttons & BTN_DOWN)  dy += 1.0f;

    if (dx != 0.0f || dy != 0.0f) {
        float inv = 1.0f / std::hypot(dx, dy);
        px_ += dx * inv * speed_ * dt;
        py_ += dy * inv * speed_ * dt;
    }

    px_ = std::max(1.0f, std::min(14.0f, px_));
    py_ = std::max(2.0f, std::min(14.0f, py_));

    uint16_t pressed = buttons & ~prev_buttons;

    // Fire A
    if (pressed & BTN_A) {
        if (weapon_type_ == WEAPON_VULCAN) {
            // 3-way
            int slot = 0;
            for (int i = 0; i < MAX_BULLETS && slot < 3; ++i) {
                if (!bullets_[i].active) {
                    if (slot == 0) bullets_[i] = {px_, py_ - 1.0f, 0.0f, -15.0f, false, 1, true};
                    else if (slot == 1) bullets_[i] = {px_ - 0.5f, py_ - 1.0f, -4.0f, -14.0f, false, 1, true};
                    else bullets_[i] = {px_ + 0.5f, py_ - 1.0f, 4.0f, -14.0f, false, 1, true};
                    slot++;
                }
            }
        } else {
            // Twin laser
            int slot = 0;
            for (int i = 0; i < MAX_BULLETS && slot < 2; ++i) {
                if (!bullets_[i].active) {
                    float ox = (slot == 0) ? -0.3f : 0.3f;
                    bullets_[i] = {px_ + ox, py_ - 1.0f, 0.0f, -20.0f, true, 3, true};
                    slot++;
                }
            }
        }
    }

    // Deploy bomb B
    if ((pressed & BTN_B) && bombs_ > 0 && !mega_bomb_.active) {
        bombs_--;
        mega_bomb_ = {px_, py_ - 2.0f, 0.45f, 1.0f, false, true};
    }

    // Bullets
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (!bullets_[i].active) continue;
        bullets_[i].x += bullets_[i].vx * dt;
        bullets_[i].y += bullets_[i].vy * dt;

        if (bullets_[i].x < 0.0f || bullets_[i].x > 15.0f || bullets_[i].y < 0.0f || bullets_[i].y > 15.0f) {
            bullets_[i].active = false;
            continue;
        }

        for (int j = 0; j < MAX_ENEMIES; ++j) {
            if (!enemies_[j].alive) continue;
            float r_hit = (enemies_[j].type == 2) ? 1.4f : 0.9f;
            if (std::hypot(enemies_[j].x - bullets_[i].x, enemies_[j].y - bullets_[i].y) < r_hit) {
                if (!bullets_[i].is_laser) {
                    bullets_[i].active = false;
                }
                enemies_[j].hp -= bullets_[i].damage;
                if (enemies_[j].hp <= 0) {
                    enemies_[j].alive = false;
                    score_ += (enemies_[j].type == 2) ? 5000 : (enemies_[j].type == 1 ? 300 : 150);
                }
                break;
            }
        }
    }

    // Mega-bomb
    if (mega_bomb_.active) {
        if (!mega_bomb_.exploding) {
            mega_bomb_.fuse -= dt;
            if (mega_bomb_.fuse <= 0.0f) {
                mega_bomb_.exploding = true;
                mega_bomb_.fuse = 0.5f;
            }
        } else {
            mega_bomb_.fuse -= dt;
            mega_bomb_.radius = std::min(6.5f, mega_bomb_.radius + 12.0f * dt);
            for (int k = 0; k < MAX_ENEMY_BULLETS; ++k) enemy_bullets_[k].active = false;

            for (int j = 0; j < MAX_ENEMIES; ++j) {
                if (enemies_[j].alive && std::hypot(enemies_[j].x - mega_bomb_.x, enemies_[j].y - mega_bomb_.y) < mega_bomb_.radius) {
                    enemies_[j].hp -= static_cast<int16_t>(8.0f * dt);
                    if (enemies_[j].hp <= 0) {
                        enemies_[j].alive = false;
                        score_ += (enemies_[j].type == 2) ? 5000 : 300;
                    }
                }
            }

            if (mega_bomb_.fuse <= 0.0f) {
                mega_bomb_.active = false;
            }
        }
    }

    // Crystal
    if (crystal_.active) {
        crystal_.x += crystal_.vx * dt;
        crystal_.y += crystal_.vy * dt;
        if (crystal_.x < 1.0f || crystal_.x > 14.5f) crystal_.vx = -crystal_.vx;
        if (crystal_.y < 3.0f || crystal_.y > 12.0f) crystal_.vy = -crystal_.vy;

        crystal_.swap_timer -= dt;
        if (crystal_.swap_timer <= 0.0f) {
            crystal_.swap_timer = 3.0f;
            crystal_.color = (crystal_.color == 0) ? 1 : 0;
        }

        if (std::hypot(crystal_.x - px_, crystal_.y - py_) < 1.2f) {
            weapon_type_ = (crystal_.color == 0) ? WEAPON_VULCAN : WEAPON_LASER;
            score_ += 500;
            crystal_.active = false;
        }
    }

    // Enemies
    for (int j = 0; j < MAX_ENEMIES; ++j) {
        if (!enemies_[j].alive) continue;
        enemies_[j].x += enemies_[j].vx * dt;
        enemies_[j].y += enemies_[j].vy * dt;

        if (enemies_[j].type == 0) {
            if (enemies_[j].x < 1.0f || enemies_[j].x > 14.5f) enemies_[j].vx = -enemies_[j].vx;
        } else if (enemies_[j].type == 2) {
            if (enemies_[j].x < 3.0f || enemies_[j].x > 12.0f) enemies_[j].vx = -enemies_[j].vx;
        }

        if (std::hypot(enemies_[j].x - px_, enemies_[j].y - py_) < 1.0f) {
            lives_--;
            state_ = STATE_SHIP_DESTROYED;
            state_timer_ = 1.0f;
            return;
        }
    }

    // Enemy bullets
    enemy_shoot_timer_ -= dt;
    if (enemy_shoot_timer_ <= 0.0f) {
        enemy_shoot_timer_ = std::max(0.5f, 1.4f - stage_ * 0.1f);
        for (int j = 0; j < MAX_ENEMIES; ++j) {
            if (enemies_[j].alive) {
                for (int b = 0; b < MAX_ENEMY_BULLETS; ++b) {
                    if (!enemy_bullets_[b].active) {
                        enemy_bullets_[b] = {enemies_[j].x, enemies_[j].y + 0.5f, 0.0f, 6.5f, true};
                        break;
                    }
                }
                break;
            }
        }
    }

    for (int b = 0; b < MAX_ENEMY_BULLETS; ++b) {
        if (!enemy_bullets_[b].active) continue;
        enemy_bullets_[b].y += enemy_bullets_[b].vy * dt;
        if (enemy_bullets_[b].y > 15.5f) {
            enemy_bullets_[b].active = false;
            continue;
        }

        if (std::hypot(enemy_bullets_[b].x - px_, enemy_bullets_[b].y - py_) < 0.8f) {
            enemy_bullets_[b].active = false;
            lives_--;
            state_ = STATE_SHIP_DESTROYED;
            state_timer_ = 1.0f;
            return;
        }
    }

    if (!enemies_[4].alive) { // Boss tank
        state_ = STATE_STAGE_CLEAR;
        state_timer_ = 2.0f;
        score_ += 5000;
    }
}

void Game189Raiden::Render(uint8_t* fb) {
    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx]     = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Background terrain
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (x >= 6 && x <= 9) {
                set_pixel(x, y, 20, 60, 140);
            } else {
                set_pixel(x, y, 50, 90, 40);
            }
        }
    }

    // Enemies
    for (int j = 0; j < MAX_ENEMIES; ++j) {
        if (!enemies_[j].alive) continue;
        int ex = static_cast<int>(std::round(enemies_[j].x));
        int ey = static_cast<int>(std::round(enemies_[j].y));
        if (enemies_[j].type == 2) {
            for (int bx = ex - 2; bx <= ex + 2; ++bx) {
                for (int by = ey - 1; by <= ey + 1; ++by) {
                    set_pixel(bx, by, 120, 80, 50);
                }
            }
            set_pixel(ex, ey, 220, 60, 60);
        } else if (enemies_[j].type == 1) {
            set_pixel(ex, ey, 90, 90, 90);
            set_pixel(ex, ey - 1, 140, 140, 140);
        } else {
            set_pixel(ex, ey, 200, 180, 50);
            set_pixel(ex - 1, ey, 140, 120, 30);
            set_pixel(ex + 1, ey, 140, 120, 30);
        }
    }

    // Enemy bullets
    for (int b = 0; b < MAX_ENEMY_BULLETS; ++b) {
        if (!enemy_bullets_[b].active) continue;
        set_pixel(static_cast<int>(std::round(enemy_bullets_[b].x)), static_cast<int>(std::round(enemy_bullets_[b].y)), 255, 120, 40);
    }

    // Crystal
    if (crystal_.active) {
        int cx = static_cast<int>(std::round(crystal_.x));
        int cy = static_cast<int>(std::round(crystal_.y));
        if (crystal_.color == 0) {
            set_pixel(cx, cy, 255, 40, 40);
        } else {
            set_pixel(cx, cy, 40, 140, 255);
        }
    }

    // Bomb
    if (mega_bomb_.active) {
        int bx = static_cast<int>(std::round(mega_bomb_.x));
        int by = static_cast<int>(std::round(mega_bomb_.y));
        if (!mega_bomb_.exploding) {
            set_pixel(bx, by, 255, 200, 40);
        } else {
            int rad = static_cast<int>(std::round(mega_bomb_.radius));
            for (int dy = -rad; dy <= rad; ++dy) {
                for (int dx = -rad; dx <= rad; ++dx) {
                    float d = std::hypot(dx, dy);
                    if (d >= 1.0f && d <= mega_bomb_.radius) {
                        set_pixel(bx + dx, by + dy, 255, 100, 20);
                    }
                }
            }
        }
    }

    // Player bullets
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (!bullets_[i].active) continue;
        int bx = static_cast<int>(std::round(bullets_[i].x));
        int by = static_cast<int>(std::round(bullets_[i].y));
        if (bullets_[i].is_laser) {
            set_pixel(bx, by, 60, 180, 255);
        } else {
            set_pixel(bx, by, 255, 220, 80);
        }
    }

    // Fighter
    int px = static_cast<int>(std::round(px_));
    int py = static_cast<int>(std::round(py_));
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        set_pixel(px, py, 220, 40, 40);
        set_pixel(px - 1, py, 200, 200, 220);
        set_pixel(px + 1, py, 200, 200, 220);
        set_pixel(px, py - 1, 255, 255, 255);
    } else if (state_ == STATE_SHIP_DESTROYED) {
        set_pixel(px, py, 255, 60, 0);
    }
}

} // namespace arcade
