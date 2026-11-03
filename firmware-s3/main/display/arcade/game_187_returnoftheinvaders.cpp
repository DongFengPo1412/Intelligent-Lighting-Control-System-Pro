#include "game_187_returnoftheinvaders.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

static constexpr uint16_t BTN_LEFT  = 1 << 2;
static constexpr uint16_t BTN_RIGHT = 1 << 3;
static constexpr uint16_t BTN_A     = 1 << 4; // Dual laser
static constexpr uint16_t BTN_B     = 1 << 5; // Boomerang cutter

Game187ReturnOfTheInvaders::Game187ReturnOfTheInvaders() {
    Init();
}

void Game187ReturnOfTheInvaders::Init() {
    Reset();
}

void Game187ReturnOfTheInvaders::Reset() {
    score_ = 0;
    lives_ = 3;
    stage_ = 1;
    InitStage();
}

void Game187ReturnOfTheInvaders::InitStage() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    px_ = 7.5f;
    py_ = 14.0f;
    speed_ = 7.0f;

    for (int i = 0; i < MAX_LASERS; ++i) lasers_[i].active = false;
    boomerang_.active = false;
    for (int i = 0; i < MAX_BOMBS; ++i) bombs_[i].active = false;

    ufo_active_ = false;
    ufo_timer_ = 5.0f;
    alien_dir_ = 1.0f;
    bomb_timer_ = 0.8f;

    for (int i = 0; i < MAX_ALIENS; ++i) aliens_[i].alive = false;

    // Row 1: Splitters
    for (int col = 0; col < 5; ++col) {
        aliens_[col] = {
            3.0f + col * 2.2f,
            3.0f,
            1.2f,
            0.0f,
            1, // splitter
            2,
            true
        };
    }
    // Row 2: Normals
    for (int col = 0; col < 6; ++col) {
        aliens_[5 + col] = {
            2.0f + col * 2.2f,
            5.0f,
            1.2f,
            0.0f,
            0, // normal
            1,
            true
        };
    }
}

void Game187ReturnOfTheInvaders::SplitAlien(float x, float y) {
    int spawned = 0;
    for (int i = 0; i < MAX_ALIENS && spawned < 2; ++i) {
        if (!aliens_[i].alive) {
            float vx = (spawned == 0) ? -4.0f : 4.0f;
            float spawn_x = (spawned == 0) ? std::max(1.0f, x - 0.8f) : std::min(14.0f, x + 0.8f);
            aliens_[i] = {spawn_x, y, vx, 0.0f, 2, 1, true};
            spawned++;
        }
    }
}

void Game187ReturnOfTheInvaders::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_STAGE_CLEAR) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            stage_++;
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
                for (int i = 0; i < MAX_LASERS; ++i) lasers_[i].active = false;
                boomerang_.active = false;
                for (int i = 0; i < MAX_BOMBS; ++i) bombs_[i].active = false;
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

    // Ship move
    if (buttons & BTN_LEFT)  px_ = std::max(1.0f, px_ - speed_ * dt);
    if (buttons & BTN_RIGHT) px_ = std::min(14.0f, px_ + speed_ * dt);

    uint16_t pressed = buttons & ~prev_buttons;

    // Fire laser (A)
    if (pressed & BTN_A) {
        for (int i = 0; i < MAX_LASERS; ++i) {
            if (!lasers_[i].active) {
                lasers_[i] = {px_, py_ - 1.0f, -16.0f, true};
                break;
            }
        }
    }

    // Launch boomerang (B)
    if ((pressed & BTN_B) && !boomerang_.active) {
        boomerang_ = {px_, py_ - 1.0f, 0.0f, -12.0f, 0, true};
    }

    // Update lasers
    for (int i = 0; i < MAX_LASERS; ++i) {
        if (!lasers_[i].active) continue;
        lasers_[i].y += lasers_[i].vy * dt;
        if (lasers_[i].y < 0.0f) {
            lasers_[i].active = false;
            continue;
        }

        // Alien hits
        for (int j = 0; j < MAX_ALIENS; ++j) {
            if (aliens_[j].alive && std::hypot(aliens_[j].x - lasers_[i].x, aliens_[j].y - lasers_[i].y) < 0.9f) {
                lasers_[i].active = false;
                aliens_[j].hp--;
                if (aliens_[j].hp <= 0) {
                    aliens_[j].alive = false;
                    score_ += (aliens_[j].type == 1) ? 150 : 80;
                    if (aliens_[j].type == 1) {
                        SplitAlien(aliens_[j].x, aliens_[j].y);
                    }
                }
                break;
            }
        }

        // UFO hit
        if (ufo_active_ && std::hypot(ufo_x_ - lasers_[i].x, 1.0f - lasers_[i].y) < 1.2f) {
            lasers_[i].active = false;
            ufo_active_ = false;
            score_ += 1000;
            for (int k = 0; k < MAX_BOMBS; ++k) bombs_[k].active = false;
        }
    }

    // Update boomerang
    if (boomerang_.active) {
        if (boomerang_.state == 0) { // Ascending
            boomerang_.y += boomerang_.vy * dt;
            if (boomerang_.y <= 4.0f) {
                boomerang_.state = 1; // Returning
            }
        } else { // Returning
            float dx = px_ - boomerang_.x;
            boomerang_.x += dx * 6.0f * dt;
            boomerang_.y += 10.0f * dt;
            if (boomerang_.y >= py_) {
                boomerang_.active = false;
            }
        }

        if (boomerang_.active) {
            for (int j = 0; j < MAX_ALIENS; ++j) {
                if (aliens_[j].alive && std::hypot(aliens_[j].x - boomerang_.x, aliens_[j].y - boomerang_.y) < 1.0f) {
                    aliens_[j].hp -= 2;
                    if (aliens_[j].hp <= 0) {
                        aliens_[j].alive = false;
                        score_ += (aliens_[j].type == 1) ? 150 : 80;
                        if (aliens_[j].type == 1) {
                            SplitAlien(aliens_[j].x, aliens_[j].y);
                        }
                    }
                }
            }

            if (ufo_active_ && std::hypot(ufo_x_ - boomerang_.x, 1.0f - boomerang_.y) < 1.4f) {
                ufo_active_ = false;
                score_ += 1000;
                for (int k = 0; k < MAX_BOMBS; ++k) bombs_[k].active = false;
            }
        }
    }

    // Update aliens march
    int alive_count = 0;
    bool hit_edge = false;
    for (int i = 0; i < MAX_ALIENS; ++i) {
        if (aliens_[i].alive) alive_count++;
    }

    if (alive_count == 0) {
        state_ = STATE_STAGE_CLEAR;
        state_timer_ = 1.8f;
        score_ += 2000;
        return;
    }

    float inv_speed = 1.0f + (11.0f - alive_count) * 0.15f;
    for (int i = 0; i < MAX_ALIENS; ++i) {
        if (!aliens_[i].alive) continue;
        if (aliens_[i].type == 2) { // Mini
            aliens_[i].x += aliens_[i].vx * dt;
            if (aliens_[i].x < 1.0f || aliens_[i].x > 14.5f) {
                aliens_[i].vx = -aliens_[i].vx;
            }
        } else {
            aliens_[i].x += alien_dir_ * inv_speed * dt;
            if ((alien_dir_ > 0.0f && aliens_[i].x >= 14.0f) || (alien_dir_ < 0.0f && aliens_[i].x <= 1.0f)) {
                hit_edge = true;
            }
        }
    }

    if (hit_edge) {
        alien_dir_ = -alien_dir_;
        for (int i = 0; i < MAX_ALIENS; ++i) {
            if (aliens_[i].alive && aliens_[i].type != 2) {
                aliens_[i].y += 0.8f;
            }
        }
    }

    for (int i = 0; i < MAX_ALIENS; ++i) {
        if (aliens_[i].alive && aliens_[i].y >= 13.5f) {
            lives_ = 0;
            state_ = STATE_GAME_OVER;
            return;
        }
    }

    // Bombs
    bomb_timer_ -= dt;
    if (bomb_timer_ <= 0.0f && alive_count > 0) {
        bomb_timer_ = std::max(0.4f, 1.2f - stage_ * 0.1f);
        for (int i = 0; i < MAX_ALIENS; ++i) {
            if (aliens_[i].alive) {
                for (int b = 0; b < MAX_BOMBS; ++b) {
                    if (!bombs_[b].active) {
                        bombs_[b] = {aliens_[i].x, aliens_[i].y + 0.5f, 7.0f, true};
                        break;
                    }
                }
                break;
            }
        }
    }

    for (int b = 0; b < MAX_BOMBS; ++b) {
        if (!bombs_[b].active) continue;
        bombs_[b].y += bombs_[b].vy * dt;
        if (bombs_[b].y > 15.5f) {
            bombs_[b].active = false;
            continue;
        }

        if (std::hypot(bombs_[b].x - px_, bombs_[b].y - py_) < 0.8f) {
            bombs_[b].active = false;
            lives_--;
            state_ = STATE_SHIP_DESTROYED;
            state_timer_ = 1.0f;
            return;
        }
    }

    // UFO
    if (!ufo_active_) {
        ufo_timer_ -= dt;
        if (ufo_timer_ <= 0.0f) {
            ufo_active_ = true;
            ufo_x_ = 0.0f;
            ufo_timer_ = 8.0f;
        }
    } else {
        ufo_x_ += 4.5f * dt;
        if (ufo_x_ > 16.0f) {
            ufo_active_ = false;
        }
    }
}

void Game187ReturnOfTheInvaders::Render(uint8_t* fb) {
    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx]     = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // UFO
    if (ufo_active_) {
        int ux = static_cast<int>(std::round(ufo_x_));
        set_pixel(ux, 1, 255, 60, 60);
        set_pixel(ux - 1, 1, 200, 30, 30);
        set_pixel(ux + 1, 1, 200, 30, 30);
        set_pixel(ux, 0, 255, 255, 100);
    }

    // Aliens
    for (int i = 0; i < MAX_ALIENS; ++i) {
        if (!aliens_[i].alive) continue;
        int ax = static_cast<int>(std::round(aliens_[i].x));
        int ay = static_cast<int>(std::round(aliens_[i].y));
        if (aliens_[i].type == 1) { // Splitter
            set_pixel(ax, ay, 220, 50, 220);
            set_pixel(ax - 1, ay, 180, 40, 180);
            set_pixel(ax + 1, ay, 180, 40, 180);
        } else if (aliens_[i].type == 2) { // Mini
            set_pixel(ax, ay, 50, 255, 200);
        } else {
            set_pixel(ax, ay, 50, 220, 50);
            set_pixel(ax - 1, ay, 40, 160, 40);
            set_pixel(ax + 1, ay, 40, 160, 40);
        }
    }

    // Bombs
    for (int b = 0; b < MAX_BOMBS; ++b) {
        if (!bombs_[b].active) continue;
        set_pixel(static_cast<int>(std::round(bombs_[b].x)), static_cast<int>(std::round(bombs_[b].y)), 255, 200, 40);
    }

    // Lasers
    for (int i = 0; i < MAX_LASERS; ++i) {
        if (!lasers_[i].active) continue;
        set_pixel(static_cast<int>(std::round(lasers_[i].x)), static_cast<int>(std::round(lasers_[i].y)), 100, 220, 255);
    }

    // Boomerang
    if (boomerang_.active) {
        int bx = static_cast<int>(std::round(boomerang_.x));
        int by = static_cast<int>(std::round(boomerang_.y));
        set_pixel(bx, by, 255, 255, 50);
        set_pixel(bx - 1, by, 255, 140, 0);
        set_pixel(bx + 1, by, 255, 140, 0);
    }

    // Ship
    int px = static_cast<int>(std::round(px_));
    int py = static_cast<int>(std::round(py_));
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        set_pixel(px, py, 255, 255, 255);
        set_pixel(px - 1, py, 40, 120, 240);
        set_pixel(px + 1, py, 40, 120, 240);
        set_pixel(px, py - 1, 255, 100, 50);
    } else if (state_ == STATE_SHIP_DESTROYED) {
        set_pixel(px, py, 255, 50, 0);
    }
}

} // namespace arcade
