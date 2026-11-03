#include "game_134_zookeeper.h"
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

static constexpr float TRACK_MIN = 1.0f;
static constexpr float TRACK_MAX = 14.0f;
static constexpr float CAGE_INNER_MIN = 2.5f;
static constexpr float CAGE_INNER_MAX = 12.5f;

Game134ZooKeeper::Game134ZooKeeper()
    : state_(STATE_PLAYING),
      state_timer_(0.0f),
      score_(0),
      lives_(3),
      level_(1),
      time_left_(30.0f),
      track_pos_(0.0f),
      px_(1.0f),
      py_(1.0f),
      is_jumping_(false),
      jump_timer_(0.0f),
      net_timer_(0.0f),
      net_spawned_(false),
      net_pos_(26.0f),
      net_respawn_timer_(10.0f) {
    Reset();
}

void Game134ZooKeeper::Init() {
    Reset();
}

void Game134ZooKeeper::Reset() {
    score_ = 0;
    lives_ = 3;
    level_ = 1;
    InitLevel();
}

void Game134ZooKeeper::InitWalls() {
    std::memset(walls_, 0, sizeof(walls_));

    for (int x = WALL_MIN; x <= WALL_MAX; ++x) {
        walls_[WALL_MIN][x] = true;
        walls_[WALL_MAX][x] = true;
    }
    for (int y = WALL_MIN; y <= WALL_MAX; ++y) {
        walls_[y][WALL_MIN] = true;
        walls_[y][WALL_MAX] = true;
    }
}

void Game134ZooKeeper::TrackPosToXY(float pos, float& x, float& y) {
    while (pos < 0.0f) pos += 52.0f;
    pos = std::fmod(pos, 52.0f);

    if (pos < 13.0f) {
        x = TRACK_MIN + pos;
        y = TRACK_MIN;
    } else if (pos < 26.0f) {
        x = TRACK_MAX;
        y = TRACK_MIN + (pos - 13.0f);
    } else if (pos < 39.0f) {
        x = TRACK_MAX - (pos - 26.0f);
        y = TRACK_MAX;
    } else {
        x = TRACK_MIN;
        y = TRACK_MAX - (pos - 39.0f);
    }
}

void Game134ZooKeeper::GetAdjacentWallCoord(float px, float py, int& wx, int& wy) {
    int ix = static_cast<int>(std::round(px));
    int iy = static_cast<int>(std::round(py));
    ix = std::max(1, std::min(14, ix));
    iy = std::max(1, std::min(14, iy));

    if (iy == 1) {
        wx = ix; wy = WALL_MIN;
    } else if (iy == 14) {
        wx = ix; wy = WALL_MAX;
    } else if (ix == 1) {
        wx = WALL_MIN; wy = iy;
    } else if (ix == 14) {
        wx = WALL_MAX; wy = iy;
    } else {
        wx = ix; wy = iy;
    }
}

void Game134ZooKeeper::InitLevel() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    time_left_ = 30.0f;

    track_pos_ = 0.0f;
    TrackPosToXY(track_pos_, px_, py_);
    is_jumping_ = false;
    jump_timer_ = 0.0f;
    net_timer_ = 0.0f;

    InitWalls();

    float base_speed = 3.5f + level_ * 0.4f;
    float dirs[NUM_ANIMALS][2] = {
        { base_speed * 0.7f,  base_speed * 0.7f},
        {-base_speed * 0.8f,  base_speed * 0.6f},
        { base_speed * 0.6f, -base_speed * 0.8f},
        {-base_speed * 0.7f, -base_speed * 0.7f}
    };
    uint8_t types[NUM_ANIMALS] = {0, 1, 0, 1};

    for (int i = 0; i < NUM_ANIMALS; ++i) {
        animals_[i].x = 5.0f + (i % 2) * 5.0f;
        animals_[i].y = 5.0f + (i / 2) * 5.0f;
        animals_[i].vx = dirs[i][0];
        animals_[i].vy = dirs[i][1];
        animals_[i].type = types[i];
        animals_[i].escaped = false;
        animals_[i].track_pos = 0.0f;
        animals_[i].track_dir = 1.0f;
    }

    net_spawned_ = true;
    net_pos_ = 26.0f;
    net_respawn_timer_ = 10.0f;
}

void Game134ZooKeeper::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_PLAYING) {
        time_left_ -= dt;
        if (time_left_ <= 0.0f) {
            time_left_ = 0.0f;
            score_ += 1000;
            state_ = STATE_LEVEL_CLEAR;
            state_timer_ = 0.0f;
            return;
        }

        // Jump
        if (is_jumping_) {
            jump_timer_ -= dt;
            if (jump_timer_ <= 0.0f) {
                is_jumping_ = false;
                jump_timer_ = 0.0f;
            }
        } else {
            if ((buttons & BTN_B) && !(prev_buttons & BTN_B)) {
                is_jumping_ = true;
                jump_timer_ = 0.5f;
            }
        }

        // Net timer
        if (net_timer_ > 0.0f) {
            net_timer_ -= dt;
            if (net_timer_ < 0.0f) net_timer_ = 0.0f;
        }

        // Move around perimeter
        float move_speed = 7.0f;
        float delta_pos = 0.0f;
        float pos = std::fmod(track_pos_, 52.0f);
        if (pos < 0.0f) pos += 52.0f;

        if (pos < 13.0f || pos == 52.0f) {
            if (buttons & BTN_RIGHT) delta_pos += move_speed * dt;
            if (buttons & BTN_LEFT)  delta_pos -= move_speed * dt;
            if (pos <= 0.5f && (buttons & BTN_DOWN)) delta_pos -= move_speed * dt;
            else if (pos >= 12.5f && (buttons & BTN_DOWN)) delta_pos += move_speed * dt;
        } else if (pos < 26.0f) {
            if (buttons & BTN_DOWN) delta_pos += move_speed * dt;
            if (buttons & BTN_UP)   delta_pos -= move_speed * dt;
            if (pos <= 13.5f && (buttons & BTN_LEFT)) delta_pos -= move_speed * dt;
            else if (pos >= 25.5f && (buttons & BTN_LEFT)) delta_pos += move_speed * dt;
        } else if (pos < 39.0f) {
            if (buttons & BTN_LEFT)  delta_pos += move_speed * dt;
            if (buttons & BTN_RIGHT) delta_pos -= move_speed * dt;
            if (pos <= 26.5f && (buttons & BTN_UP)) delta_pos -= move_speed * dt;
            else if (pos >= 38.5f && (buttons & BTN_UP)) delta_pos += move_speed * dt;
        } else {
            if (buttons & BTN_UP)   delta_pos += move_speed * dt;
            if (buttons & BTN_DOWN) delta_pos -= move_speed * dt;
            if (pos <= 39.5f && (buttons & BTN_RIGHT)) delta_pos -= move_speed * dt;
            else if (pos >= 51.5f && (buttons & BTN_RIGHT)) delta_pos += move_speed * dt;
        }

        track_pos_ = std::fmod(track_pos_ + delta_pos, 52.0f);
        if (track_pos_ < 0.0f) track_pos_ += 52.0f;
        TrackPosToXY(track_pos_, px_, py_);

        // Brick building with BTN_A
        if (buttons & BTN_A) {
            int wx = 0, wy = 0;
            GetAdjacentWallCoord(px_, py_, wx, wy);
            if (wx >= 0 && wx < 16 && wy >= 0 && wy < 16) {
                if (!walls_[wy][wx]) {
                    walls_[wy][wx] = true;
                    score_ += 15;
                }
            }
        }

        // Net respawn & collection
        if (!net_spawned_ && net_timer_ <= 0.0f) {
            net_respawn_timer_ -= dt;
            if (net_respawn_timer_ <= 0.0f) {
                net_spawned_ = true;
                net_pos_ = std::fmod(track_pos_ + 26.0f, 52.0f);
                net_respawn_timer_ = 12.0f;
            }
        }

        if (net_spawned_) {
            float dist_to_net = std::abs(track_pos_ - net_pos_);
            if (dist_to_net > 26.0f) dist_to_net = 52.0f - dist_to_net;
            if (dist_to_net < 1.2f) {
                net_spawned_ = false;
                net_timer_ = 6.0f;
                score_ += 100;
            }
        }

        // Animals update
        for (int i = 0; i < NUM_ANIMALS; ++i) {
            Animal& a = animals_[i];
            if (!a.escaped) {
                float nx = a.x + a.vx * dt;
                float ny = a.y + a.vy * dt;

                if (ny <= CAGE_INNER_MIN) {
                    int ix = std::max(WALL_MIN, std::min(WALL_MAX, static_cast<int>(std::round(a.x))));
                    if (walls_[WALL_MIN][ix]) {
                        a.vy = std::abs(a.vy);
                        walls_[WALL_MIN][ix] = false;
                    } else {
                        a.escaped = true;
                        a.track_pos = std::fmod(static_cast<float>(ix - 1), 52.0f);
                        a.track_dir = (a.vx >= 0.0f) ? 1.0f : -1.0f;
                    }
                } else if (ny >= CAGE_INNER_MAX) {
                    int ix = std::max(WALL_MIN, std::min(WALL_MAX, static_cast<int>(std::round(a.x))));
                    if (walls_[WALL_MAX][ix]) {
                        a.vy = -std::abs(a.vy);
                        walls_[WALL_MAX][ix] = false;
                    } else {
                        a.escaped = true;
                        a.track_pos = std::fmod(26.0f + (14.0f - ix), 52.0f);
                        a.track_dir = (a.vx <= 0.0f) ? 1.0f : -1.0f;
                    }
                } else if (nx <= CAGE_INNER_MIN) {
                    int iy = std::max(WALL_MIN, std::min(WALL_MAX, static_cast<int>(std::round(a.y))));
                    if (walls_[iy][WALL_MIN]) {
                        a.vx = std::abs(a.vx);
                        walls_[iy][WALL_MIN] = false;
                    } else {
                        a.escaped = true;
                        a.track_pos = std::fmod(39.0f + (14.0f - iy), 52.0f);
                        a.track_dir = (a.vy <= 0.0f) ? 1.0f : -1.0f;
                    }
                } else if (nx >= CAGE_INNER_MAX) {
                    int iy = std::max(WALL_MIN, std::min(WALL_MAX, static_cast<int>(std::round(a.y))));
                    if (walls_[iy][WALL_MAX]) {
                        a.vx = -std::abs(a.vx);
                        walls_[iy][WALL_MAX] = false;
                    } else {
                        a.escaped = true;
                        a.track_pos = std::fmod(13.0f + (iy - 1.0f), 52.0f);
                        a.track_dir = (a.vy >= 0.0f) ? 1.0f : -1.0f;
                    }
                } else {
                    a.x = nx;
                    a.y = ny;
                }
            } else {
                float escape_speed = 5.0f;
                a.track_pos = std::fmod(a.track_pos + a.track_dir * escape_speed * dt, 52.0f);
                if (a.track_pos < 0.0f) a.track_pos += 52.0f;
                TrackPosToXY(a.track_pos, a.x, a.y);

                float dist = std::hypot(px_ - a.x, py_ - a.y);
                if (dist < 1.1f) {
                    if (net_timer_ > 0.0f) {
                        a.escaped = false;
                        a.x = 7.5f;
                        a.y = 7.5f;
                        a.vx = (a.track_dir > 0.0f) ? 3.5f : -3.5f;
                        a.vy = 3.0f;
                        score_ += 250;
                    } else if (!is_jumping_) {
                        if (lives_ > 0) lives_--;
                        state_ = STATE_CAUGHT;
                        state_timer_ = 0.0f;
                        return;
                    } else {
                        score_ += 50;
                    }
                }
            }
        }
    } else if (state_ == STATE_LEVEL_CLEAR || state_ == STATE_CAUGHT) {
        state_timer_ += dt;
        if (state_timer_ >= 1.5f) {
            if (state_ == STATE_LEVEL_CLEAR) {
                level_++;
                InitLevel();
            } else if (state_ == STATE_CAUGHT) {
                if (lives_ > 0) {
                    InitLevel();
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

void Game134ZooKeeper::Render(uint8_t* fb) {
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

    // Track boundary
    for (int x = 1; x <= 14; ++x) {
        set_pixel(x, 1, 15, 25, 20);
        set_pixel(x, 14, 15, 25, 20);
    }
    for (int y = 1; y <= 14; ++y) {
        set_pixel(1, y, 15, 25, 20);
        set_pixel(14, y, 15, 25, 20);
    }

    // Brick walls
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (walls_[y][x]) {
                set_pixel(x, y, 200, 110, 40);
            }
        }
    }

    // Net bonus
    if (net_spawned_) {
        float nx = 0.0f, ny = 0.0f;
        TrackPosToXY(net_pos_, nx, ny);
        set_pixel(static_cast<int>(std::round(nx)), static_cast<int>(std::round(ny)), 255, 255, 60);
    }

    // Animals
    for (int i = 0; i < NUM_ANIMALS; ++i) {
        int ax = static_cast<int>(std::round(animals_[i].x));
        int ay = static_cast<int>(std::round(animals_[i].y));
        if (animals_[i].escaped) {
            set_pixel(ax, ay, 255, 60, 30);
        } else {
            if (animals_[i].type == 0) {
                set_pixel(ax, ay, 240, 150, 20);
            } else {
                set_pixel(ax, ay, 180, 50, 220);
            }
        }
    }

    // Zeke player
    int zx = static_cast<int>(std::round(px_));
    int zy = static_cast<int>(std::round(py_));
    if (is_jumping_) {
        set_pixel(zx, zy, 200, 255, 255);
    } else if (net_timer_ > 0.0f) {
        set_pixel(zx, zy, 255, 240, 50);
    } else {
        set_pixel(zx, zy, 40, 160, 255);
    }

    // State flashes
    if (state_ == STATE_CAUGHT) {
        int flash = static_cast<int>(state_timer_ * 10.0f) % 2;
        if (flash == 0) {
            for (int x = 0; x < 16; ++x) {
                set_pixel(x, 0, 220, 30, 30);
                set_pixel(x, 15, 220, 30, 30);
            }
        }
    } else if (state_ == STATE_LEVEL_CLEAR) {
        int flash = static_cast<int>(state_timer_ * 10.0f) % 2;
        if (flash == 0) {
            for (int x = 0; x < 16; ++x) {
                set_pixel(x, 0, 30, 220, 60);
                set_pixel(x, 15, 30, 220, 60);
            }
        }
    }
}

} // namespace arcade
