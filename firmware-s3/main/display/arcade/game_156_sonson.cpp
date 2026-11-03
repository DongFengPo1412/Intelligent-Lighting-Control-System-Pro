#include "game_156_sonson.h"
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

static const float LANES_Y[6] = {4.0f, 6.0f, 8.0f, 10.0f, 12.0f, 14.0f};

Game156SonSon::Game156SonSon() {
    Reset();
}

void Game156SonSon::Init() {
    Reset();
}

void Game156SonSon::Reset() {
    score_ = 0;
    lives_ = 3;
    level_ = 1;
    InitLevel();
}

void Game156SonSon::InitLevel() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    px_ = 3.0f;
    lane_idx_ = 3;
    py_ = LANES_Y[lane_idx_];
    distance_ = 0.0f;

    for (int i = 0; i < MAX_SHOTS; ++i) shots_[i].active = false;
    for (int i = 0; i < MAX_FRUITS; ++i) fruits_[i].active = false;

    enemies_[0] = {14.0f, 3, -3.5f, 0, 0.0f, true};
    enemies_[1] = {16.0f, 1, -3.0f, 1, 0.0f, true};
    enemies_[2] = {18.0f, 4, -2.8f, 2, 0.0f, true};
    enemies_[3] = {20.0f, 0, -3.2f, 0, 0.0f, true};
}

void Game156SonSon::LoseLife() {
    lives_--;
    state_ = STATE_PLAYER_HIT;
    state_timer_ = 0.0f;
}

void Game156SonSon::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_PLAYING) {
        // 1. Lane Switch
        if ((buttons & BTN_UP) && !(prev_buttons & BTN_UP)) {
            if (lane_idx_ > 0) lane_idx_--;
        } else if ((buttons & BTN_DOWN) && !(prev_buttons & BTN_DOWN)) {
            if (lane_idx_ < NUM_LANES - 1) lane_idx_++;
        }

        float target_y = LANES_Y[lane_idx_];
        py_ += (target_y - py_) * std::min(1.0f, dt * 20.0f);

        // 2. Horizontal run & scroll
        float speed = 4.5f;
        float dx = 0.0f;
        if (buttons & BTN_LEFT)  dx -= speed;
        if (buttons & BTN_RIGHT) dx += speed;

        px_ = std::max(1.5f, std::min(14.0f, px_ + dx * dt));

        float scroll_speed = 3.0f;
        distance_ += scroll_speed * dt;

        // 3. Fire shot
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            for (int i = 0; i < MAX_SHOTS; ++i) {
                if (!shots_[i].active) {
                    shots_[i] = {px_ + 0.8f, py_, lane_idx_, 14.0f, true};
                    break;
                }
            }
        }

        // 4. Update shots
        for (int i = 0; i < MAX_SHOTS; ++i) {
            if (!shots_[i].active) continue;
            shots_[i].x += shots_[i].vx * dt;
            if (shots_[i].x > 15.5f) {
                shots_[i].active = false;
                continue;
            }

            for (int e = 0; e < MAX_ENEMIES; ++e) {
                if (enemies_[e].alive && enemies_[e].lane == shots_[i].lane) {
                    if (std::abs(shots_[i].x - enemies_[e].x) < 1.0f) {
                        enemies_[e].alive = false;
                        enemies_[e].respawn_timer = 2.0f;
                        shots_[i].active = false;
                        score_ += 150;

                        // Spawn fruit
                        for (int f = 0; f < MAX_FRUITS; ++f) {
                            if (!fruits_[f].active) {
                                fruits_[f] = {enemies_[e].x, enemies_[e].lane, (enemies_[e].lane % 2 == 1), true};
                                break;
                            }
                        }
                        break;
                    }
                }
            }
        }

        // 5. Update fruits
        for (int f = 0; f < MAX_FRUITS; ++f) {
            if (!fruits_[f].active) continue;
            fruits_[f].x -= scroll_speed * 0.5f * dt;
            if (fruits_[f].lane == lane_idx_ && std::abs(px_ - fruits_[f].x) < 0.9f) {
                fruits_[f].active = false;
                score_ += fruits_[f].is_melon ? 500 : 300;
            }
            if (fruits_[f].x < 0.5f) fruits_[f].active = false;
        }

        // 6. Update enemies
        for (int e = 0; e < MAX_ENEMIES; ++e) {
            if (!enemies_[e].alive) {
                enemies_[e].respawn_timer -= dt;
                if (enemies_[e].respawn_timer <= 0.0f) {
                    enemies_[e].x = 16.5f + (e * 2.0f);
                    enemies_[e].lane = (lane_idx_ + (static_cast<int>(distance_) % 4)) % NUM_LANES;
                    enemies_[e].alive = true;
                }
                continue;
            }

            enemies_[e].x += enemies_[e].vx * dt;

            if (enemies_[e].lane == lane_idx_ && std::abs(px_ - enemies_[e].x) < 0.8f) {
                LoseLife();
                return;
            }

            if (enemies_[e].x < -1.0f) {
                enemies_[e].x = 16.5f + (e * 2.0f);
                enemies_[e].lane = (lane_idx_ + (static_cast<int>(distance_) % 4)) % NUM_LANES;
                enemies_[e].alive = true;
            }
        }

        // 7. Finish
        if (distance_ >= MAX_DISTANCE) {
            score_ += 2500;
            state_ = STATE_STAGE_CLEAR;
            state_timer_ = 0.0f;
        }

    } else if (state_ == STATE_STAGE_CLEAR || state_ == STATE_PLAYER_HIT) {
        state_timer_ += dt;
        if (state_timer_ >= 1.5f) {
            if (state_ == STATE_STAGE_CLEAR) {
                level_++;
                InitLevel();
            } else {
                if (lives_ > 0) {
                    px_ = 3.0f;
                    lane_idx_ = 3;
                    py_ = LANES_Y[lane_idx_];
                    for (int i = 0; i < MAX_SHOTS; ++i) shots_[i].active = false;
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

void Game156SonSon::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // 1. Bamboo platforms
    for (int l = 0; l < NUM_LANES; ++l) {
        int floor_y = static_cast<int>(LANES_Y[l]) + 1;
        if (floor_y < 16) {
            for (int x = 0; x < 16; ++x) set_pixel(x, floor_y, 40, 140, 70);
        }
    }

    // 2. Pagoda Gate
    if (distance_ >= MAX_DISTANCE - 10.0f) {
        int gx = static_cast<int>(std::round(15.0f - (MAX_DISTANCE - distance_)));
        if (gx >= 0 && gx < 16) {
            for (int y = 2; y <= 14; ++y) set_pixel(gx, y, 240, 200, 40);
        }
    }

    // 3. Fruits
    for (int f = 0; f < MAX_FRUITS; ++f) {
        if (!fruits_[f].active) continue;
        int fx = static_cast<int>(std::round(fruits_[f].x));
        int fy = static_cast<int>(std::round(LANES_Y[fruits_[f].lane]));
        if (!fruits_[f].is_melon) set_pixel(fx, fy, 255, 120, 160);
        else set_pixel(fx, fy, 255, 180, 30);
    }

    // 4. Enemies
    for (int e = 0; e < MAX_ENEMIES; ++e) {
        if (!enemies_[e].alive) continue;
        int ex = static_cast<int>(std::round(enemies_[e].x));
        int ey = static_cast<int>(std::round(LANES_Y[enemies_[e].lane]));
        if (enemies_[e].type == 0) set_pixel(ex, ey, 180, 50, 220);
        else if (enemies_[e].type == 1) set_pixel(ex, ey, 40, 140, 240);
        else set_pixel(ex, ey, 240, 60, 40);
    }

    // 5. Shots
    for (int i = 0; i < MAX_SHOTS; ++i) {
        if (shots_[i].active) {
            int sx = static_cast<int>(std::round(shots_[i].x));
            int sy = static_cast<int>(std::round(shots_[i].y));
            set_pixel(sx, sy, 255, 240, 80);
            if (sx - 1 >= 0) set_pixel(sx - 1, sy, 255, 160, 40);
        }
    }

    // 6. SonSon
    int px = static_cast<int>(std::round(px_));
    int py = static_cast<int>(std::round(py_));
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        set_pixel(px, py, 240, 170, 40);
        if (py - 1 >= 0) set_pixel(px, py - 1, 240, 60, 40);
        if (px + 1 < 16) set_pixel(px + 1, py, 255, 220, 50);
    } else if (state_ == STATE_PLAYER_HIT) {
        set_pixel(px, py, 255, 50, 50);
    }

    // 7. Progress & Lives
    int prog_dots = static_cast<int>((distance_ / MAX_DISTANCE) * 8.0f);
    for (int i = 0; i < prog_dots; ++i) set_pixel(8 + i, 0, 240, 200, 40);
    for (int l = 0; l < std::min((int)lives_, 3); ++l) set_pixel(l * 2, 0, 240, 60, 40);
}

} // namespace arcade
