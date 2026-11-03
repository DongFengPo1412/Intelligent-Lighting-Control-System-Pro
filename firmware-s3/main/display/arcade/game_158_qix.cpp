#include "game_158_qix.h"
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

Game158Qix::Game158Qix() {
    Reset();
}

void Game158Qix::Init() {
    Reset();
}

void Game158Qix::Reset() {
    score_ = 0;
    lives_ = 3;
    level_ = 1;
    InitLevel();
}

void Game158Qix::InitLevel() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    px_ = 7;
    py_ = 15;
    is_drawing_ = false;
    draw_slow_ = false;
    draw_path_len_ = 0;
    percent_claimed_ = 0.0f;

    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (x == 0 || x == 15 || y == 0 || y == 15) {
                grid_[y][x] = CELL_BORDER;
            } else {
                grid_[y][x] = CELL_EMPTY;
            }
        }
    }

    qx_ = 7.5f;
    qy_ = 7.5f;
    qvx_ = 2.4f + (level_ * 0.3f);
    qvy_ = 1.8f + (level_ * 0.2f);

    sparx_[0] = {0.0f, 0.0f, 1};
    sparx_[1] = {15.0f, 0.0f, -1};
}

float Game158Qix::CalcPercent() const {
    int total_internal = 14 * 14;
    int claimed = 0;
    for (int y = 1; y < 15; ++y) {
        for (int x = 1; x < 15; ++x) {
            if (grid_[y][x] == CELL_CLAIMED) claimed++;
        }
    }
    return (static_cast<float>(claimed) / total_internal) * 100.0f;
}

void Game158Qix::LoseLife() {
    lives_--;
    state_ = STATE_PLAYER_HIT;
    state_timer_ = 0.0f;
}

void Game158Qix::ClaimTerritory() {
    for (int i = 0; i < draw_path_len_; ++i) {
        grid_[draw_path_y_[i]][draw_path_x_[i]] = CELL_BORDER;
    }

    // Flood fill from Qix position
    bool visited[16][16];
    std::memset(visited, 0, sizeof(visited));

    int q_start_x = std::max(1, std::min(14, static_cast<int>(std::round(qx_))));
    int q_start_y = std::max(1, std::min(14, static_cast<int>(std::round(qy_))));

    int queue_x[256];
    int queue_y[256];
    int head = 0, tail = 0;

    queue_x[tail] = q_start_x;
    queue_y[tail] = q_start_y;
    tail++;
    visited[q_start_y][q_start_x] = true;

    static const int offsets[4][2] = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};

    while (head < tail) {
        int cx = queue_x[head];
        int cy = queue_y[head];
        head++;

        for (int o = 0; o < 4; ++o) {
            int nx = cx + offsets[o][0];
            int ny = cy + offsets[o][1];
            if (nx >= 0 && nx < 16 && ny >= 0 && ny < 16) {
                if (!visited[ny][nx] && grid_[ny][nx] == CELL_EMPTY) {
                    visited[ny][nx] = true;
                    queue_x[tail] = nx;
                    queue_y[tail] = ny;
                    tail++;
                }
            }
        }
    }

    int newly_claimed = 0;
    for (int y = 1; y < 15; ++y) {
        for (int x = 1; x < 15; ++x) {
            if (grid_[y][x] == CELL_EMPTY && !visited[y][x]) {
                grid_[y][x] = CELL_CLAIMED;
                newly_claimed++;
            }
        }
    }

    uint32_t mult = draw_slow_ ? 2 : 1;
    score_ += newly_claimed * 10 * mult;

    draw_path_len_ = 0;
    is_drawing_ = false;

    percent_claimed_ = CalcPercent();
    if (percent_claimed_ >= WIN_PERCENTAGE) {
        score_ += 3000;
        state_ = STATE_STAGE_CLEAR;
        state_timer_ = 0.0f;
    }
}

void Game158Qix::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_PLAYING) {
        int dx = 0;
        int dy = 0;
        if ((buttons & BTN_LEFT) && !(prev_buttons & BTN_LEFT))   dx = -1;
        else if ((buttons & BTN_RIGHT) && !(prev_buttons & BTN_RIGHT)) dx = 1;
        else if ((buttons & BTN_UP) && !(prev_buttons & BTN_UP))     dy = -1;
        else if ((buttons & BTN_DOWN) && !(prev_buttons & BTN_DOWN)) dy = 1;

        if (dx != 0 || dy != 0) {
            int nx = px_ + dx;
            int ny = py_ + dy;
            if (nx >= 0 && nx < 16 && ny >= 0 && ny < 16) {
                uint8_t target = grid_[ny][nx];
                if (!is_drawing_) {
                    if (target == CELL_BORDER || target == CELL_CLAIMED) {
                        px_ = nx; py_ = ny;
                    } else if (target == CELL_EMPTY) {
                        if ((buttons & (BTN_A | BTN_B))) {
                            is_drawing_ = true;
                            draw_slow_ = (buttons & BTN_A) != 0;
                            px_ = nx; py_ = ny;
                            grid_[ny][nx] = CELL_DRAWING;
                            if (draw_path_len_ < MAX_DRAW_PATH) {
                                draw_path_x_[draw_path_len_] = nx;
                                draw_path_y_[draw_path_len_] = ny;
                                draw_path_len_++;
                            }
                        }
                    }
                } else {
                    if (target == CELL_EMPTY) {
                        px_ = nx; py_ = ny;
                        grid_[ny][nx] = CELL_DRAWING;
                        if (draw_path_len_ < MAX_DRAW_PATH) {
                            draw_path_x_[draw_path_len_] = nx;
                            draw_path_y_[draw_path_len_] = ny;
                            draw_path_len_++;
                        }
                    } else if (target == CELL_BORDER || target == CELL_CLAIMED) {
                        px_ = nx; py_ = ny;
                        ClaimTerritory();
                    }
                }
            }
        }

        // 2. Qix
        qx_ += qvx_ * dt;
        qy_ += qvy_ * dt;

        int iqx = static_cast<int>(std::round(qx_));
        int iqy = static_cast<int>(std::round(qy_));

        if (iqx <= 1 || iqx >= 14 || grid_[iqy][iqx] == CELL_BORDER || grid_[iqy][iqx] == CELL_CLAIMED) {
            qvx_ = -qvx_;
            qx_ = std::max(1.5f, std::min(13.5f, qx_));
        }
        if (iqy <= 1 || iqy >= 14 || grid_[iqy][iqx] == CELL_BORDER || grid_[iqy][iqx] == CELL_CLAIMED) {
            qvy_ = -qvy_;
            qy_ = std::max(1.5f, std::min(13.5f, qy_));
        }

        if (is_drawing_) {
            for (int i = 0; i < draw_path_len_; ++i) {
                if (std::abs(qx_ - draw_path_x_[i]) < 0.9f && std::abs(qy_ - draw_path_y_[i]) < 0.9f) {
                    LoseLife();
                    return;
                }
            }
        }

        // 3. Sparx
        float sparx_speed = 3.5f;
        for (int s = 0; s < NUM_SPARX; ++s) {
            auto& sp = sparx_[s];
            if (sp.dir == 1) {
                if (sp.y == 0.0f && sp.x < 15.0f) sp.x += sparx_speed * dt;
                else if (sp.x >= 15.0f && sp.y < 15.0f) sp.y += sparx_speed * dt;
                else if (sp.y >= 15.0f && sp.x > 0.0f) sp.x -= sparx_speed * dt;
                else if (sp.x <= 0.0f && sp.y > 0.0f) sp.y -= sparx_speed * dt;
            } else {
                if (sp.y == 0.0f && sp.x > 0.0f) sp.x -= sparx_speed * dt;
                else if (sp.x <= 0.0f && sp.y < 15.0f) sp.y += sparx_speed * dt;
                else if (sp.y >= 15.0f && sp.x < 15.0f) sp.x += sparx_speed * dt;
                else if (sp.x >= 15.0f && sp.y > 0.0f) sp.y -= sparx_speed * dt;
            }

            sp.x = std::max(0.0f, std::min(15.0f, sp.x));
            sp.y = std::max(0.0f, std::min(15.0f, sp.y));

            if (!is_drawing_ && std::abs(px_ - sp.x) < 0.8f && std::abs(py_ - sp.y) < 0.8f) {
                LoseLife();
                return;
            }
        }

    } else if (state_ == STATE_STAGE_CLEAR || state_ == STATE_PLAYER_HIT) {
        state_timer_ += dt;
        if (state_timer_ >= 1.5f) {
            if (state_ == STATE_STAGE_CLEAR) {
                level_++;
                InitLevel();
            } else {
                if (lives_ > 0) {
                    for (int i = 0; i < draw_path_len_; ++i) {
                        grid_[draw_path_y_[i]][draw_path_x_[i]] = CELL_EMPTY;
                    }
                    draw_path_len_ = 0;
                    is_drawing_ = false;
                    px_ = 7; py_ = 15;
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

void Game158Qix::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // 1. Grid
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            uint8_t c = grid_[y][x];
            if (c == CELL_CLAIMED) set_pixel(x, y, 40, 100, 200);
            else if (c == CELL_BORDER) set_pixel(x, y, 120, 120, 140);
            else if (c == CELL_DRAWING) set_pixel(x, y, 255, 230, draw_slow_ ? 40 : 80);
        }
    }

    // 2. Qix Helix
    int iqx = static_cast<int>(std::round(qx_));
    int iqy = static_cast<int>(std::round(qy_));
    set_pixel(iqx, iqy, 255, 40, 180);
    if (iqx + 1 < 16) set_pixel(iqx + 1, iqy, 40, 255, 200);
    if (iqy - 1 >= 0) set_pixel(iqx, iqy - 1, 255, 220, 40);
    if (iqx - 1 >= 0) set_pixel(iqx - 1, iqy, 255, 80, 40);

    // 3. Sparx
    for (int s = 0; s < NUM_SPARX; ++s) {
        set_pixel(static_cast<int>(std::round(sparx_[s].x)),
                  static_cast<int>(std::round(sparx_[s].y)), 255, 255, 100);
    }

    // 4. Player
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        set_pixel(px_, py_, 255, 50, 50);
    } else if (state_ == STATE_PLAYER_HIT) {
        set_pixel(px_, py_, 255, 255, 255);
    }

    // 5. Percent gauge
    int pct_dots = static_cast<int>((percent_claimed_ / 100.0f) * 8.0f);
    for (int i = 0; i < pct_dots; ++i) set_pixel(8 + i, 0, 40, 255, 120);
    for (int l = 0; l < std::min((int)lives_, 3); ++l) set_pixel(l * 2, 0, 255, 50, 50);
}

} // namespace arcade
