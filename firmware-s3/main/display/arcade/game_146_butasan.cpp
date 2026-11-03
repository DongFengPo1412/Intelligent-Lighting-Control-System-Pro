#include "game_146_butasan.h"
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

Game146Butasan::Game146Butasan()
    : state_(STATE_PLAYING),
      state_timer_(0.0f),
      score_(0),
      lives_(3),
      level_(1),
      px_(7.5f),
      py_(12.0f),
      facing_x_(0.0f),
      facing_y_(-1.0f),
      held_bomb_idx_(-1) {
    Reset();
}

void Game146Butasan::Init() {
    Reset();
}

void Game146Butasan::Reset() {
    score_ = 0;
    lives_ = 3;
    level_ = 1;
    InitLevel();
}

void Game146Butasan::InitLevel() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    px_ = 7.5f;
    py_ = 12.0f;
    facing_x_ = 0.0f;
    facing_y_ = -1.0f;
    held_bomb_idx_ = -1;

    for (int i = 0; i < MAX_EXPLOSIONS; ++i) explosions_[i].timer = 0.0f;
    for (int i = 0; i < MAX_BOMBS; ++i) bombs_[i].active = false;

    bombs_[0] = {4.0f, 8.0f, 10.0f, 0, 0.0f, 0.0f, true};
    bombs_[1] = {11.0f, 8.0f, 10.0f, 0, 0.0f, 0.0f, true};
    bombs_[2] = {7.5f, 5.0f, 5.0f, 0, 0.0f, 0.0f, true};
    bombs_[3] = {7.5f, 10.0f, 15.0f, 0, 0.0f, 0.0f, true};

    enemies_[0] = {3.0f, 3.0f, 1.5f, 0.0f, true};
    enemies_[1] = {12.0f, 3.0f, -1.5f, 0.0f, true};
    enemies_[2] = {7.5f, 2.0f, 0.0f, 1.5f, true};
}

void Game146Butasan::LoseLife() {
    if (lives_ > 0) lives_--;
    state_ = STATE_PIG_BLASTED;
    state_timer_ = 0.0f;
}

void Game146Butasan::ExplodeBomb(float bx, float by) {
    int ix = static_cast<int>(std::round(bx));
    int iy = static_cast<int>(std::round(by));

    int offsets[5][2] = {{0, 0}, {1, 0}, {-1, 0}, {0, 1}, {0, -1}};
    for (int k = 0; k < 5; ++k) {
        int ex = ix + offsets[k][0];
        int ey = iy + offsets[k][1];
        if (ex >= 1 && ex <= 14 && ey >= 1 && ey <= 14) {
            for (int e = 0; e < MAX_EXPLOSIONS; ++e) {
                if (explosions_[e].timer <= 0.0f) {
                    explosions_[e].x = static_cast<int8_t>(ex);
                    explosions_[e].y = static_cast<int8_t>(ey);
                    explosions_[e].timer = 0.4f;
                    break;
                }
            }
        }
    }

    for (int i = 0; i < MAX_BOMBS; ++i) {
        if (bombs_[i].active && bombs_[i].state != 1) {
            if (std::abs(bombs_[i].x - bx) <= 1.4f && std::abs(bombs_[i].y - by) <= 1.4f) {
                bombs_[i].fuse = 0.05f;
            }
        }
    }
}

void Game146Butasan::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_PLAYING) {
        float move_speed = (held_bomb_idx_ == -1) ? 5.5f : 4.2f;
        float dx = 0.0f;
        float dy = 0.0f;
        if (buttons & BTN_LEFT) {
            dx -= move_speed;
            facing_x_ = -1.0f; facing_y_ = 0.0f;
        } else if (buttons & BTN_RIGHT) {
            dx += move_speed;
            facing_x_ = 1.0f; facing_y_ = 0.0f;
        } else if (buttons & BTN_UP) {
            dy -= move_speed;
            facing_x_ = 0.0f; facing_y_ = -1.0f;
        } else if (buttons & BTN_DOWN) {
            dy += move_speed;
            facing_x_ = 0.0f; facing_y_ = 1.0f;
        }

        px_ = std::max(1.5f, std::min(13.5f, px_ + dx * dt));
        py_ = std::max(1.5f, std::min(13.5f, py_ + dy * dt));

        // Pick up or throw bomb (BTN_A)
        if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
            if (held_bomb_idx_ == -1) {
                float min_d = 1.3f;
                int best = -1;
                for (int i = 0; i < MAX_BOMBS; ++i) {
                    if (bombs_[i].active && (bombs_[i].state == 0 || bombs_[i].state == 3)) {
                        float d = std::hypot(bombs_[i].x - px_, bombs_[i].y - py_);
                        if (d < min_d) { min_d = d; best = i; }
                    }
                }
                if (best != -1) {
                    bombs_[best].state = 1;
                    held_bomb_idx_ = best;
                }
            } else {
                bombs_[held_bomb_idx_].state = 2;
                bombs_[held_bomb_idx_].x = px_ + facing_x_ * 0.8f;
                bombs_[held_bomb_idx_].y = py_ + facing_y_ * 0.8f;
                bombs_[held_bomb_idx_].vx = facing_x_ * 12.0f;
                bombs_[held_bomb_idx_].vy = facing_y_ * 12.0f;
                held_bomb_idx_ = -1;
            }
        }

        // Kick bomb (BTN_B)
        if ((buttons & BTN_B) && !(prev_buttons & BTN_B)) {
            if (held_bomb_idx_ == -1) {
                for (int i = 0; i < MAX_BOMBS; ++i) {
                    if (bombs_[i].active && (bombs_[i].state == 0 || bombs_[i].state == 3)) {
                        if (std::abs(bombs_[i].x - px_) < 1.3f && std::abs(bombs_[i].y - py_) < 1.3f) {
                            bombs_[i].state = 3;
                            bombs_[i].vx = facing_x_ * 14.0f;
                            bombs_[i].vy = facing_y_ * 14.0f;
                            break;
                        }
                    }
                }
            }
        }

        // Update held bomb pos
        if (held_bomb_idx_ != -1) {
            bombs_[held_bomb_idx_].x = px_;
            bombs_[held_bomb_idx_].y = py_ - 0.8f;
        }

        // Update bombs
        for (int i = 0; i < MAX_BOMBS; ++i) {
            if (!bombs_[i].active) continue;

            bombs_[i].fuse -= dt;
            if (bombs_[i].fuse <= 0.0f) {
                bombs_[i].active = false;
                if (held_bomb_idx_ == i) {
                    held_bomb_idx_ = -1;
                    LoseLife();
                    return;
                }
                ExplodeBomb(bombs_[i].x, bombs_[i].y);
                continue;
            }

            if (bombs_[i].state == 2 || bombs_[i].state == 3) {
                bombs_[i].x += bombs_[i].vx * dt;
                bombs_[i].y += bombs_[i].vy * dt;

                if (bombs_[i].x <= 1.5f) {
                    bombs_[i].x = 1.5f; bombs_[i].vx = -bombs_[i].vx * 0.7f; bombs_[i].state = 0;
                } else if (bombs_[i].x >= 13.5f) {
                    bombs_[i].x = 13.5f; bombs_[i].vx = -bombs_[i].vx * 0.7f; bombs_[i].state = 0;
                }
                if (bombs_[i].y <= 1.5f) {
                    bombs_[i].y = 1.5f; bombs_[i].vy = -bombs_[i].vy * 0.7f; bombs_[i].state = 0;
                } else if (bombs_[i].y >= 13.5f) {
                    bombs_[i].y = 13.5f; bombs_[i].vy = -bombs_[i].vy * 0.7f; bombs_[i].state = 0;
                }

                for (int k = 0; k < NUM_ENEMIES; ++k) {
                    if (enemies_[k].alive) {
                        if (std::abs(bombs_[i].x - enemies_[k].x) < 1.0f &&
                            std::abs(bombs_[i].y - enemies_[k].y) < 1.0f) {
                            bombs_[i].active = false;
                            score_ += 250;
                            ExplodeBomb(bombs_[i].x, bombs_[i].y);
                            break;
                        }
                    }
                }
            }
        }

        // Update explosions
        for (int i = 0; i < MAX_EXPLOSIONS; ++i) {
            if (explosions_[i].timer > 0.0f) {
                explosions_[i].timer -= dt;
                if (std::abs(px_ - explosions_[i].x) < 0.8f && std::abs(py_ - explosions_[i].y) < 0.8f) {
                    LoseLife();
                    return;
                }

                for (int k = 0; k < NUM_ENEMIES; ++k) {
                    if (enemies_[k].alive) {
                        if (std::abs(enemies_[k].x - explosions_[i].x) < 0.8f &&
                            std::abs(enemies_[k].y - explosions_[i].y) < 0.8f) {
                            enemies_[k].alive = false;
                            score_ += 200;
                        }
                    }
                }
            }
        }

        // Update enemies
        bool all_dead = true;
        for (int k = 0; k < NUM_ENEMIES; ++k) {
            if (!enemies_[k].alive) continue;
            all_dead = false;

            enemies_[k].x += enemies_[k].vx * dt;
            enemies_[k].y += enemies_[k].vy * dt;

            if (enemies_[k].x <= 2.0f || enemies_[k].x >= 13.0f) enemies_[k].vx = -enemies_[k].vx;
            if (enemies_[k].y <= 2.0f || enemies_[k].y >= 13.0f) enemies_[k].vy = -enemies_[k].vy;

            if (std::abs(px_ - enemies_[k].x) < 0.8f && std::abs(py_ - enemies_[k].y) < 0.8f) {
                LoseLife();
                return;
            }
        }

        if (all_dead) {
            score_ += 1000;
            state_ = STATE_STAGE_CLEAR;
            state_timer_ = 0.0f;
        }
    } else if (state_ == STATE_STAGE_CLEAR || state_ == STATE_PIG_BLASTED) {
        state_timer_ += dt;
        if (state_timer_ >= 1.5f) {
            if (state_ == STATE_STAGE_CLEAR) {
                level_++;
                InitLevel();
            } else if (state_ == STATE_PIG_BLASTED) {
                if (lives_ > 0) {
                    px_ = 7.5f;
                    py_ = 12.0f;
                    held_bomb_idx_ = -1;
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

void Game146Butasan::Render(uint8_t* fb) {
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

    // Fences
    for (int x = 0; x < 16; ++x) {
        set_pixel(x, 0, 100, 60, 40);
        set_pixel(x, 15, 100, 60, 40);
    }
    for (int y = 0; y < 16; ++y) {
        set_pixel(0, y, 100, 60, 40);
        set_pixel(15, y, 100, 60, 40);
    }

    // Bombs
    for (int i = 0; i < MAX_BOMBS; ++i) {
        if (bombs_[i].active) {
            int bx = static_cast<int>(std::round(bombs_[i].x));
            int by = static_cast<int>(std::round(bombs_[i].y));
            if (bombs_[i].fuse < 3.0f) {
                int flash = static_cast<int>(bombs_[i].fuse * 10.0f) % 2;
                if (flash == 0) set_pixel(bx, by, 255, 30, 20);
                else set_pixel(bx, by, 255, 240, 40);
            } else {
                set_pixel(bx, by, 40, 40, 40);
                set_pixel(bx, by - 1, 255, 220, 50);
            }
        }
    }

    // Explosions
    for (int i = 0; i < MAX_EXPLOSIONS; ++i) {
        if (explosions_[i].timer > 0.0f) {
            set_pixel(explosions_[i].x, explosions_[i].y, 255, 160, 30);
        }
    }

    // Enemies
    for (int k = 0; k < NUM_ENEMIES; ++k) {
        if (enemies_[k].alive) {
            int ex = static_cast<int>(std::round(enemies_[k].x));
            int ey = static_cast<int>(std::round(enemies_[k].y));
            set_pixel(ex, ey, 140, 80, 50);
            set_pixel(ex, ey - 1, 240, 160, 140);
        }
    }

    // Player
    int px = static_cast<int>(std::round(px_));
    int py = static_cast<int>(std::round(py_));
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        set_pixel(px, py, 255, 160, 180);
        set_pixel(px, py - 1, 255, 120, 150);
        if (held_bomb_idx_ != -1) set_pixel(px, py - 2, 255, 40, 40);
    } else if (state_ == STATE_PIG_BLASTED) {
        set_pixel(px, py, 255, 60, 30);
    }

    // Lives
    for (int l = 0; l < std::min(static_cast<int>(lives_), 3); ++l) {
        set_pixel(1 + l * 2, 0, 255, 160, 180);
    }
}

} // namespace arcade
