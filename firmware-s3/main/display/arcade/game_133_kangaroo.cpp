#include "game_133_kangaroo.h"
#include <cmath>
#include <cstdlib>
#include <cstring>

namespace arcade {

static constexpr float PLATFORM_Y[4] = {14.0f, 10.0f, 6.0f, 2.0f};

Game133Kangaroo::Game133Kangaroo() {
    Init();
}

void Game133Kangaroo::Init() {
    score_ = 0;
    lives_ = 3;
    level_ = 1;
    InitLevel();
}

void Game133Kangaroo::Reset() {
    Init();
}

void Game133Kangaroo::InitLevel() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;

    px_ = 2.0f;
    py_ = 14.0f;
    pvx_ = 0.0f;
    pvy_ = 0.0f;
    p_facing_ = 1; // Facing Right
    is_jumping_ = false;
    is_ducking_ = false;
    on_ladder_ = false;
    punch_timer_ = 0.0f;

    bell_rung_ = false;
    bell_ring_anim_ = 0.0f;

    // Fruits at platforms
    fruits_[0] = {5.0f, 13.0f, false};  // Ground
    fruits_[1] = {9.0f, 9.0f, false};   // Level 1
    fruits_[2] = {6.0f, 5.0f, false};   // Level 2
    fruits_[3] = {11.0f, 5.0f, false};  // Level 2 near bell

    // Monkeys
    monkeys_[0] = {8.0f, 10.0f, 2.0f, true};
    monkeys_[1] = {8.0f, 6.0f, 3.2f, true};
    monkeys_[2] = {10.0f, 2.0f, 1.5f, true};

    for (int i = 0; i < MAX_APPLES; ++i) {
        apples_[i].active = false;
    }
}

void Game133Kangaroo::RingBell() {
    bell_rung_ = true;
    bell_ring_anim_ = 0.6f;
    score_ += 100;
    // Respawns all fruits!
    for (int i = 0; i < NUM_FRUITS; ++i) {
        fruits_[i].collected = false;
    }
}

void Game133Kangaroo::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & 0x0030) && !(prev_buttons & 0x0030)) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_MOM_DOWN) {
        if (state_timer_ > 1.3f) {
            lives_--;
            if (lives_ == 0) {
                state_ = STATE_GAME_OVER;
            } else {
                state_ = STATE_PLAYING;
                px_ = 2.0f;
                py_ = 14.0f;
                pvx_ = 0.0f;
                pvy_ = 0.0f;
                p_facing_ = 1;
                is_jumping_ = false;
                on_ladder_ = false;
                punch_timer_ = 0.0f;
            }
        }
        return;
    }

    if (state_ == STATE_LEVEL_CLEAR) {
        if (state_timer_ > 1.6f) {
            level_++;
            score_ += 2000;
            InitLevel();
        }
        return;
    }

    if (bell_ring_anim_ > 0.0f) bell_ring_anim_ -= dt;

    UpdatePlayer(dt, buttons, prev_buttons);
    UpdateMonkeys(dt);
    UpdateApples(dt);
    CheckCollisions();

    // Check Joey Rescue
    if (py_ <= 2.5f && px_ <= 3.5f) {
        state_ = STATE_LEVEL_CLEAR;
        state_timer_ = 0.0f;
    }
}

void Game133Kangaroo::UpdatePlayer(float dt, uint16_t buttons, uint16_t prev_buttons) {
    // Punch (Button A)
    if (punch_timer_ > 0.0f) punch_timer_ -= dt;
    if ((buttons & 0x0010) && !(prev_buttons & 0x0010)) {
        punch_timer_ = 0.35f;
    }

    // Jump (Button B)
    if ((buttons & 0x0020) && !(prev_buttons & 0x0020)) {
        if (!is_jumping_ && !on_ladder_) {
            is_jumping_ = true;
            pvy_ = -7.5f;
        }
    }

    // Ladders locations:
    // Ladder 1: x = 12.0, between y in [10.0, 14.0]
    // Ladder 2: x = 3.0, between y in [6.0, 10.0]
    // Ladder 3: x = 5.0, between y in [2.0, 6.0]
    bool near_ladder = false;
    if (std::abs(px_ - 12.0f) < 0.8f && py_ >= 9.8f && py_ <= 14.2f) near_ladder = true;
    if (std::abs(px_ - 3.0f) < 0.8f && py_ >= 5.8f && py_ <= 10.2f) near_ladder = true;
    if (std::abs(px_ - 5.0f) < 0.8f && py_ >= 1.8f && py_ <= 6.2f) near_ladder = true;

    if (near_ladder && (buttons & (0x0001 | 0x0002))) {
        on_ladder_ = true;
        is_jumping_ = false;
        pvy_ = 0.0f;
    }

    if (on_ladder_) {
        float climb_speed = 3.5f;
        if (buttons & 0x0001) py_ -= climb_speed * dt; // Climb UP
        if (buttons & 0x0002) py_ += climb_speed * dt; // Climb DOWN

        // Reaching platform snap
        for (float plat : PLATFORM_Y) {
            if (std::abs(py_ - plat) < 0.3f && !(buttons & (0x0001 | 0x0002))) {
                py_ = plat;
                on_ladder_ = false;
                break;
            }
        }
        if (!near_ladder) on_ladder_ = false;
        return;
    }

    // Walking
    float walk_speed = 4.2f;
    if (buttons & 0x0004) { // LEFT
        px_ -= walk_speed * dt;
        p_facing_ = -1;
    }
    if (buttons & 0x0008) { // RIGHT
        px_ += walk_speed * dt;
        p_facing_ = 1;
    }

    if (px_ < 1.0f) px_ = 1.0f;
    if (px_ > 14.5f) px_ = 14.5f;

    // Gravity & Jump Physics
    if (is_jumping_) {
        pvy_ += 16.0f * dt;
        py_ += pvy_ * dt;

        // Check landing on platform when descending
        if (pvy_ > 0.0f) {
            for (float plat : PLATFORM_Y) {
                if (std::abs(py_ - plat) < 0.45f) {
                    py_ = plat;
                    pvy_ = 0.0f;
                    is_jumping_ = false;
                    break;
                }
            }
        }
    }

    // Bell hit by jump at (11.0, 4.5)
    if (std::abs(px_ - 11.0f) < 1.0f && std::abs(py_ - 4.5f) < 1.0f && is_jumping_) {
        RingBell();
    }
}

void Game133Kangaroo::UpdateMonkeys(float dt) {
    for (int i = 0; i < NUM_MONKEYS; ++i) {
        if (!monkeys_[i].alive) continue;

        monkeys_[i].throw_timer -= dt;
        if (monkeys_[i].throw_timer <= 0.0f) {
            monkeys_[i].throw_timer = 3.5f - level_ * 0.2f;
            if (monkeys_[i].throw_timer < 1.2f) monkeys_[i].throw_timer = 1.2f;

            // Throw apple downwards
            for (int a = 0; a < MAX_APPLES; ++a) {
                if (!apples_[a].active) {
                    apples_[a].active = true;
                    apples_[a].x = monkeys_[i].x;
                    apples_[a].y = monkeys_[i].y + 0.8f;
                    apples_[a].vy = 4.0f + level_ * 0.3f;
                    break;
                }
            }
        }
    }
}

void Game133Kangaroo::UpdateApples(float dt) {
    for (int i = 0; i < MAX_APPLES; ++i) {
        if (!apples_[i].active) continue;
        apples_[i].y += apples_[i].vy * dt;
        if (apples_[i].y > 15.0f) {
            apples_[i].active = false;
        }
    }
}

void Game133Kangaroo::CheckCollisions() {
    // 1. Collect Fruits
    for (int f = 0; f < NUM_FRUITS; ++f) {
        if (!fruits_[f].collected) {
            if (std::abs(px_ - fruits_[f].x) < 0.85f && std::abs(py_ - fruits_[f].y) < 1.0f) {
                fruits_[f].collected = true;
                score_ += 150;
            }
        }
    }

    // 2. Punch vs Monkeys & Falling Apples
    if (punch_timer_ > 0.0f) {
        float punch_x = px_ + (float)p_facing_ * 1.1f;
        float punch_y = py_;

        // vs Apples
        for (int a = 0; a < MAX_APPLES; ++a) {
            if (!apples_[a].active) continue;
            if (std::abs(punch_x - apples_[a].x) < 0.9f && std::abs(punch_y - apples_[a].y) < 0.9f) {
                apples_[a].active = false;
                score_ += 100; // Boxing glove punched apple out of mid-air!
            }
        }

        // vs Monkeys
        for (int m = 0; m < NUM_MONKEYS; ++m) {
            if (!monkeys_[m].alive) continue;
            if (std::abs(punch_x - monkeys_[m].x) < 1.0f && std::abs(punch_y - monkeys_[m].y) < 1.0f) {
                monkeys_[m].alive = false;
                score_ += 200; // Knockout!
            }
        }
    }

    // 3. Falling Apples vs Kangaroo
    for (int a = 0; a < MAX_APPLES; ++a) {
        if (!apples_[a].active) continue;
        if (std::abs(px_ - apples_[a].x) < 0.75f && std::abs(py_ - apples_[a].y) < 0.85f) {
            apples_[a].active = false;
            state_ = STATE_MOM_DOWN;
            state_timer_ = 0.0f;
            break;
        }
    }

    // 4. Monkeys touching Kangaroo
    for (int m = 0; m < NUM_MONKEYS; ++m) {
        if (!monkeys_[m].alive) continue;
        if (std::abs(px_ - monkeys_[m].x) < 0.75f && std::abs(py_ - monkeys_[m].y) < 0.85f) {
            state_ = STATE_MOM_DOWN;
            state_timer_ = 0.0f;
            break;
        }
    }
}

void Game133Kangaroo::Render(uint8_t* fb) {
    if (!fb) return;
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // 1. Tree trunk platforms
    // Ground
    for (int x = 0; x < 16; ++x) set_pixel(x, 15, 60, 140, 40);
    // Plat 1 (y=11)
    for (int x = 2; x <= 13; ++x) set_pixel(x, 11, 140, 80, 30);
    // Plat 2 (y=7)
    for (int x = 2; x <= 13; ++x) set_pixel(x, 7, 140, 80, 30);
    // Plat 3 canopy (y=3)
    for (int x = 1; x <= 6; ++x) set_pixel(x, 3, 30, 160, 40);

    // Ladders (yellow dots)
    // Ladder 1 (x=12, y in [11, 14])
    for (int y = 11; y <= 14; ++y) set_pixel(12, y, 220, 200, 50);
    // Ladder 2 (x=3, y in [7, 10])
    for (int y = 7; y <= 10; ++y) set_pixel(3, y, 220, 200, 50);
    // Ladder 3 (x=5, y in [3, 6])
    for (int y = 3; y <= 6; ++y) set_pixel(5, y, 220, 200, 50);

    // 2. Fruit Bell at (11, 4)
    if (bell_ring_anim_ > 0.0f) {
        set_pixel(11, 4, 255, 255, 255); // Ringing flash
    } else {
        set_pixel(11, 4, 255, 215, 0);   // Golden bell
    }

    // 3. Fruits (Red cherries / apples)
    for (int f = 0; f < NUM_FRUITS; ++f) {
        if (!fruits_[f].collected) {
            set_pixel((int)fruits_[f].x, (int)fruits_[f].y, 255, 40, 50);
        }
    }

    // 4. Monkeys (Brown furry sprite)
    for (int m = 0; m < NUM_MONKEYS; ++m) {
        if (!monkeys_[m].alive) continue;
        int mx = (int)std::round(monkeys_[m].x);
        int my = (int)std::round(monkeys_[m].y);
        set_pixel(mx, my, 160, 90, 40);
        set_pixel(mx, my - 1, 200, 130, 60);
    }

    // 5. Falling Apples
    for (int a = 0; a < MAX_APPLES; ++a) {
        if (!apples_[a].active) continue;
        int ax = (int)std::round(apples_[a].x);
        int ay = (int)std::round(apples_[a].y);
        set_pixel(ax, ay, 255, 50, 40);
    }

    // 6. Joey Kangaroo at (2, 2)
    set_pixel(2, 2, 255, 180, 80); // Little joey
    set_pixel(2, 1, 255, 255, 255);

    // 7. Mother Kangaroo
    int kx = (int)std::round(px_);
    int ky = (int)std::round(py_);

    if (state_ == STATE_PLAYING || state_ == STATE_LEVEL_CLEAR) {
        set_pixel(kx, ky, 220, 140, 40);     // Brown fur
        set_pixel(kx, ky - 1, 240, 160, 60); // Ears / head
        set_pixel(kx - p_facing_, ky, 180, 100, 30); // Tail
        // Boxing Glove
        if (punch_timer_ > 0.0f) {
            set_pixel(kx + p_facing_ * 2, ky - 1, 255, 20, 20); // Extended red boxing glove punch
        } else {
            set_pixel(kx + p_facing_, ky - 1, 220, 30, 30);
        }
    } else if (state_ == STATE_MOM_DOWN) {
        set_pixel(kx, ky, 255, 200, 50);
        set_pixel(kx - 1, ky, 255, 40, 20);
        set_pixel(kx + 1, ky, 255, 40, 20);
    }

    // 8. Lives
    for (int l = 0; l < lives_ && l < 3; ++l) {
        set_pixel(l * 2, 0, 220, 140, 40);
    }
}

} // namespace arcade
