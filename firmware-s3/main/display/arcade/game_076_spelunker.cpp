#include "game_076_spelunker.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game076Spelunker::Game076Spelunker()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(8500),
      lives_(3),
      px_(2.0f),
      py_(4.0f),
      pvy_(0.0f),
      fall_start_y_(4.0f),
      on_ground_(true),
      on_rope_(false),
      facing_(1),
      oxygen_(100.0f),
      flares_count_(3),
      treasures_collected_(0) {
}

void Game076Spelunker::Init() {
    Reset();
}

void Game076Spelunker::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    lives_ = 3;
    InitStage();
}

void Game076Spelunker::InitStage() {
    px_ = 2.0f;
    py_ = 4.0f;
    pvy_ = 0.0f;
    fall_start_y_ = 4.0f;
    on_ground_ = true;
    on_rope_ = false;
    facing_ = 1;
    oxygen_ = 100.0f;
    flares_count_ = 3;
    treasures_collected_ = 0;

    for (int i = 0; i < MAX_FLARES; ++i) flares_[i].active = false;

    // Ghosts
    ghosts_[0] = {14.0f, 10.0f, -1.2f, 0.5f, true};
    ghosts_[1] = {1.0f, 12.0f, 1.0f, -0.6f, false}; // Spawns later

    // Cavern Items (Idol, Oxygen, Key, Idol 2)
    items_[0] = {12.0f, 4.0f, 0, true};  // Gold Idol
    items_[1] = {6.0f, 9.0f, 1, true};   // Oxygen tank
    items_[2] = {13.0f, 9.0f, 2, true};  // Exit Key
    items_[3] = {8.0f, 14.0f, 0, true};  // Gold Idol 2
}

int Game076Spelunker::GetTreasuresRemaining() const {
    int count = 0;
    for (int i = 0; i < MAX_TREASURES; ++i) {
        if (items_[i].active) count++;
    }
    return count;
}

void Game076Spelunker::FireFlare() {
    if (flares_count_ <= 0) return;

    for (int i = 0; i < MAX_FLARES; ++i) {
        if (!flares_[i].active) {
            flares_[i].active = true;
            flares_[i].x = px_;
            flares_[i].y = py_ - 1.0f;
            flares_[i].vy = -14.0f;
            flares_[i].duration = 1.2f;
            flares_count_--;
            break;
        }
    }
}

void Game076Spelunker::Jump() {
    if (on_ground_) {
        pvy_ = -6.5f; // Small delicate jump
        fall_start_y_ = py_;
        on_ground_ = false;
        on_rope_ = false;
    } else if (on_rope_) {
        // Jump off rope horizontally
        pvy_ = -5.0f;
        fall_start_y_ = py_;
        px_ += facing_ * 1.0f;
        on_rope_ = false;
        on_ground_ = false;
    }
}

void Game076Spelunker::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_DEAD) {
        if (state_timer_ > 1.8f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                state_timer_ = 0.0f;
                px_ = 2.0f;
                py_ = 4.0f;
                pvy_ = 0.0f;
                fall_start_y_ = 4.0f;
                on_ground_ = true;
                on_rope_ = false;
                oxygen_ = 100.0f;
            } else {
                state_ = STATE_START;
            }
        }
        return;
    }

    if (state_ == STATE_VICTORY) {
        if (state_timer_ > 2.5f) {
            state_ = STATE_PLAYING;
            state_timer_ = 0.0f;
            InitStage();
        }
        return;
    }

    // Oxygen consumption
    oxygen_ -= 2.2f * dt;
    if (oxygen_ <= 0.0f) {
        lives_--;
        state_ = STATE_DEAD;
        state_timer_ = 0.0f;
        return;
    }

    UpdatePlayer(dt, buttons, prev_buttons);
    UpdateFlares(dt);
    UpdateGhosts(dt);
    CheckCollisions();
}

void Game076Spelunker::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    float move_speed = 4.5f;

    // Check rope grabbing: Rope 1 at x=5 (y=4..14), Rope 2 at x=11 (y=4..9)
    bool near_rope1 = (std::abs(px_ - 5.0f) < 0.6f && py_ >= 4.0f && py_ <= 14.0f);
    bool near_rope2 = (std::abs(px_ - 11.0f) < 0.6f && py_ >= 4.0f && py_ <= 9.0f);

    if ((near_rope1 || near_rope2) && ((buttons & BUTTON_UP) || (buttons & BUTTON_DOWN))) {
        on_rope_ = true;
        px_ = near_rope1 ? 5.0f : 11.0f;
        pvy_ = 0.0f;
    }

    if (on_rope_) {
        float climb_speed = 3.5f;
        if (buttons & BUTTON_UP)   py_ -= climb_speed * dt;
        if (buttons & BUTTON_DOWN) py_ += climb_speed * dt;

        if (buttons & BUTTON_LEFT)  facing_ = -1;
        if (buttons & BUTTON_RIGHT) facing_ = 1;

        py_ = std::max(4.0f, std::min(14.0f, py_));
        fall_start_y_ = py_;
    } else {
        // Horizontal walk
        if (buttons & BUTTON_LEFT)  { px_ -= move_speed * dt; facing_ = -1; }
        if (buttons & BUTTON_RIGHT) { px_ += move_speed * dt; facing_ = 1; }

        px_ = std::max(0.5f, std::min(15.0f, px_));

        float prev_y = py_;
        // Gravity
        pvy_ += 22.0f * dt;
        py_ += pvy_ * dt;

        // Platform landing check
        on_ground_ = false;
        if (pvy_ >= 0.0f) {
            float landing_y = -1.0f;
            if (py_ >= 14.0f) {
                landing_y = 14.0f;
            } else if (prev_y <= 9.0f && py_ >= 9.0f && ((px_ >= 2.8f && px_ <= 8.2f) || (px_ >= 10.8f && px_ <= 15.2f))) {
                landing_y = 9.0f;
            } else if (prev_y <= 4.0f && py_ >= 4.0f && ((px_ >= 0.8f && px_ <= 5.2f) || (px_ >= 9.8f && px_ <= 14.2f))) {
                landing_y = 4.0f;
            }

            if (landing_y > 0.0f) {
                // Check delicate fall height! Fall > 2.2 blocks is fatal!
                if ((landing_y - fall_start_y_) > 2.2f) {
                    lives_--;
                    state_ = STATE_DEAD;
                    state_timer_ = 0.0f;
                    return;
                }

                py_ = landing_y;
                pvy_ = 0.0f;
                on_ground_ = true;
                fall_start_y_ = py_;
            }
        }
    }

    // Button A: Jump
    if ((buttons & BUTTON_A) && !(prev_buttons & BUTTON_A)) {
        Jump();
    }

    // Button B: Flare Gun
    if ((buttons & BUTTON_B) && !(prev_buttons & BUTTON_B)) {
        FireFlare();
    }
}

void Game076Spelunker::UpdateFlares(float dt) {
    for (int i = 0; i < MAX_FLARES; ++i) {
        if (!flares_[i].active) continue;

        flares_[i].y += flares_[i].vy * dt;
        flares_[i].duration -= dt;

        if (flares_[i].duration <= 0.0f || flares_[i].y < 0.0f) {
            flares_[i].active = false;
        }
    }
}

void Game076Spelunker::UpdateGhosts(float dt) {
    for (int i = 0; i < MAX_GHOSTS; ++i) {
        if (!ghosts_[i].active) continue;

        // Ghost floats towards player through walls
        float dx = px_ - ghosts_[i].x;
        float dy = py_ - ghosts_[i].y;
        float dist = std::sqrt(dx * dx + dy * dy);

        if (dist > 0.1f) {
            float spd = 1.4f;
            ghosts_[i].x += (dx / dist) * spd * dt;
            ghosts_[i].y += (dy / dist) * spd * dt;
        }
    }
}

void Game076Spelunker::CheckCollisions() {
    // 1. Flare vaporizes ghosts
    for (int f = 0; f < MAX_FLARES; ++f) {
        if (!flares_[f].active) continue;
        for (int g = 0; g < MAX_GHOSTS; ++g) {
            if (!ghosts_[g].active) continue;

            if (std::abs(flares_[f].x - ghosts_[g].x) < 3.0f &&
                std::abs(flares_[f].y - ghosts_[g].y) < 3.0f) {
                // Ghost vaporized in bright flare flash!
                ghosts_[g].active = false;
                score_ += 500;
                break;
            }
        }
    }

    // 2. Ghost touches Spelunker
    for (int g = 0; g < MAX_GHOSTS; ++g) {
        if (!ghosts_[g].active) continue;
        if (std::abs(px_ - ghosts_[g].x) < 0.9f && std::abs(py_ - ghosts_[g].y) < 0.9f) {
            lives_--;
            state_ = STATE_DEAD;
            state_timer_ = 0.0f;
            return;
        }
    }

    // 3. Item collections
    for (int i = 0; i < MAX_TREASURES; ++i) {
        if (!items_[i].active) continue;

        if (std::abs(px_ - items_[i].x) < 1.1f && std::abs(py_ - items_[i].y) < 1.1f) {
            items_[i].active = false;
            if (items_[i].type == 0) {
                score_ += 300;
            } else if (items_[i].type == 1) {
                oxygen_ = std::min(100.0f, oxygen_ + 35.0f);
                score_ += 150;
            } else {
                score_ += 500; // Key!
            }
            treasures_collected_++;
        }
    }

    // 4. Reach Cavern Exit (14, 14) with key (items_[2] collected)
    if (!items_[2].active && px_ >= 13.0f && py_ >= 13.5f) {
        state_ = STATE_VICTORY;
        state_timer_ = 0.0f;
        score_ += 4000;
        if (score_ > high_score_) high_score_ = score_;
    }
}

void Game076Spelunker::Render(uint8_t* fb) {
    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // 1. Dark underground cavern rock
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            set_pixel(x, y, 15, 12, 10);
        }
    }

    // 2. Cavern Platforms
    for (int x = 0; x < 16; ++x) set_pixel(x, 15, 120, 80, 40); // Floor rock
    for (int x = 3; x <= 8; ++x)  set_pixel(x, 10, 130, 85, 45); // Mid-left
    for (int x = 11; x <= 15; ++x) set_pixel(x, 10, 130, 85, 45); // Mid-right
    for (int x = 1; x <= 5; ++x)  set_pixel(x, 5, 140, 90, 50);  // Upper-left
    for (int x = 10; x <= 14; ++x) set_pixel(x, 5, 140, 90, 50);  // Upper-right

    // 3. Vertical Ropes
    for (int y = 4; y <= 14; ++y) set_pixel(5, y, 200, 160, 60);  // Rope 1
    for (int y = 4; y <= 9; ++y)  set_pixel(11, y, 200, 160, 60); // Rope 2

    // 4. Exit Portal at (14, 14)
    bool has_key = !items_[2].active;
    set_pixel(14, 14, has_key ? 50 : 200, has_key ? 255 : 30, 40);
    set_pixel(15, 14, has_key ? 50 : 200, has_key ? 255 : 30, 40);

    // 5. Items
    for (int i = 0; i < MAX_TREASURES; ++i) {
        if (!items_[i].active) continue;
        int ix = int(std::round(items_[i].x));
        int iy = int(std::round(items_[i].y));
        if (items_[i].type == 0) {
            // Gold Idol
            set_pixel(ix, iy, 255, 215, 0);
            set_pixel(ix, iy - 1, 255, 180, 0);
        } else if (items_[i].type == 1) {
            // Oxygen Tank (Cyan)
            set_pixel(ix, iy, 40, 220, 255);
            set_pixel(ix, iy - 1, 255, 255, 255);
        } else {
            // Exit Key (Gold)
            set_pixel(ix, iy, 255, 220, 50);
            set_pixel(ix + 1, iy, 255, 220, 50);
        }
    }

    // 6. Flares
    for (int f = 0; f < MAX_FLARES; ++f) {
        if (!flares_[f].active) continue;
        int fx = int(std::round(flares_[f].x));
        int fy = int(std::round(flares_[f].y));
        set_pixel(fx, fy, 255, 255, 200);     // Magnesium white core
        set_pixel(fx, fy + 1, 255, 120, 0);   // Flame spark
        set_pixel(fx - 1, fy, 255, 200, 50);  // Radiance
        set_pixel(fx + 1, fy, 255, 200, 50);
    }

    // 7. Ghosts (Spooky floating phantoms)
    for (int g = 0; g < MAX_GHOSTS; ++g) {
        if (!ghosts_[g].active) continue;
        int gx = int(std::round(ghosts_[g].x));
        int gy = int(std::round(ghosts_[g].y));
        set_pixel(gx, gy, 230, 240, 255);     // Pale white
        set_pixel(gx, gy - 1, 200, 220, 255);
        set_pixel(gx - 1, gy, 180, 200, 255);
        set_pixel(gx + 1, gy, 180, 200, 255);
    }

    // 8. Spelunker Explorer
    if (state_ != STATE_DEAD) {
        int sx = int(std::round(px_));
        int sy = int(std::round(py_));

        set_pixel(sx, sy, 50, 120, 220);       // Blue explorer suit
        set_pixel(sx, sy - 1, 255, 200, 150);  // Face
        set_pixel(sx, sy - 2, 255, 220, 30);   // Yellow miner helmet
        set_pixel(sx + facing_, sy - 2, 255, 255, 255); // Headlamp beam
    } else {
        int sx = int(std::round(px_));
        int sy = int(std::round(py_));
        set_pixel(sx, sy, 220, 20, 20); // Spelunker tombstone / ghost
    }

    // 9. HUD (Oxygen bar on row 0)
    int o2_bars = int((oxygen_ / 100.0f) * 8.0f);
    for (int b = 0; b < o2_bars; ++b) {
        set_pixel(b, 0, 40, 220, 255);
    }
    // Flares remaining icons
    for (int f = 0; f < flares_count_; ++f) {
        set_pixel(15 - f, 0, 255, 100, 0);
    }
}

} // namespace arcade
