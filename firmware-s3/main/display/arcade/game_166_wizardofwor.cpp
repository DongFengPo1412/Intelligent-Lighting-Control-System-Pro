#include "game_166_wizardofwor.h"
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

Game166WizardOfWor::Game166WizardOfWor() {
    Reset();
}

void Game166WizardOfWor::Init() {
    Reset();
}

void Game166WizardOfWor::Reset() {
    score_ = 0;
    lives_ = 3;
    dungeon_ = 1;
    InitDungeon();
}

bool Game166WizardOfWor::IsWall(float x, float y) const {
    int ix = static_cast<int>(std::round(x));
    int iy = static_cast<int>(std::round(y));

    if (ix < 0 || ix > 15 || iy < 0 || iy > 14) return true;

    // Warp portals at (0, 7) and (15, 7)
    if (iy == 7 && (ix == 0 || ix == 15)) return false;

    // Outer border
    if (ix == 0 || ix == 15 || iy == 0 || iy == 14) return true;

    // Interior walls
    if ((iy == 4 || iy == 10) && (ix >= 3 && ix <= 12) && (ix != 7 && ix != 8)) return true;
    if ((ix == 4 || ix == 11) && (iy >= 5 && iy <= 9) && (iy != 7)) return true;

    return false;
}

bool Game166WizardOfWor::IsLineOfSight(float x, float y) const {
    return (std::abs(px_ - x) < 1.0f) || (std::abs(py_ - y) < 1.0f);
}

void Game166WizardOfWor::InitDungeon() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    px_ = 7.5f;
    py_ = 13.0f;
    facing_dx_ = 0.0f;
    facing_dy_ = -1.0f;
    speed_ = 4.8f;
    fire_cooldown_ = 0.0f;

    wizard_active_ = false;
    wizard_alive_ = false;
    wizard_teleport_count_ = 0;

    for (int i = 0; i < MAX_BULLETS; ++i) bullets_[i].active = false;

    monsters_[0] = {0, 0, 2.0f, 2.0f, 2.0f, 0.0f, false, true};  // Burwor
    monsters_[1] = {1, 1, 13.0f, 2.0f, -2.4f, 0.0f, true, true}; // Garwor
    monsters_[2] = {2, 2, 7.5f, 7.0f, 2.8f, 0.0f, true, true};  // Thorwor
}

void Game166WizardOfWor::SpawnWizard() {
    wizard_active_ = true;
    wizard_alive_ = true;
    wizard_x_ = 7.5f;
    wizard_y_ = 2.0f;
    wizard_teleport_timer_ = 2.0f;
}

void Game166WizardOfWor::FireBeam() {
    if (fire_cooldown_ > 0.0f || state_ != STATE_PLAYING) return;

    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (!bullets_[i].active) {
            bullets_[i].x = px_ + facing_dx_ * 0.8f;
            bullets_[i].y = py_ + facing_dy_ * 0.8f;
            bullets_[i].vx = facing_dx_ * 15.0f;
            bullets_[i].vy = facing_dy_ * 15.0f;
            bullets_[i].life = 1.0f;
            bullets_[i].active = true;
            fire_cooldown_ = 0.2f;
            break;
        }
    }
}

void Game166WizardOfWor::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (state_ == STATE_DUNGEON_CLEAR) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            dungeon_++;
            InitDungeon();
        }
        return;
    }

    if (state_ == STATE_WORRIOR_DIED) {
        state_timer_ -= dt;
        if (state_timer_ <= 0.0f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                px_ = 7.5f;
                py_ = 13.0f;
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

    float dx = 0.0f, dy = 0.0f;
    if (buttons & BTN_LEFT)  { dx -= 1.0f; facing_dx_ = -1.0f; facing_dy_ = 0.0f; }
    else if (buttons & BTN_RIGHT) { dx += 1.0f; facing_dx_ = 1.0f; facing_dy_ = 0.0f; }
    else if (buttons & BTN_UP)    { dy -= 1.0f; facing_dx_ = 0.0f; facing_dy_ = -1.0f; }
    else if (buttons & BTN_DOWN)  { dy += 1.0f; facing_dx_ = 0.0f; facing_dy_ = 1.0f; }

    if (dx != 0.0f || dy != 0.0f) {
        float new_px = px_ + dx * speed_ * dt;
        float new_py = py_ + dy * speed_ * dt;

        if (std::abs(py_ - 7.0f) < 0.8f) {
            if (new_px <= 0.2f) new_px = 14.8f;
            else if (new_px >= 14.8f) new_px = 0.2f;
        }

        if (!IsWall(new_px, py_)) px_ = new_px;
        if (!IsWall(px_, new_py)) py_ = new_py;
    }

    if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
        FireBeam();
    }

    // Bullets
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (!bullets_[i].active) continue;

        bullets_[i].x += bullets_[i].vx * dt;
        bullets_[i].y += bullets_[i].vy * dt;
        bullets_[i].life -= dt;

        if (IsWall(bullets_[i].x, bullets_[i].y) || bullets_[i].life <= 0.0f) {
            bullets_[i].active = false;
            continue;
        }

        bool hit = false;
        for (int m = 0; m < NUM_MONSTERS; ++m) {
            if (monsters_[m].alive && std::hypot(monsters_[m].x - bullets_[i].x, monsters_[m].y - bullets_[i].y) < 1.0f) {
                monsters_[m].alive = false;
                score_ += (monsters_[m].type == 0) ? 200 : ((monsters_[m].type == 1) ? 500 : 1000);
                bullets_[i].active = false;
                hit = true;
                break;
            }
        }
        if (hit) continue;

        if (wizard_alive_ && std::hypot(wizard_x_ - bullets_[i].x, wizard_y_ - bullets_[i].y) < 1.1f) {
            wizard_alive_ = false;
            score_ += 2500;
            bullets_[i].active = false;
            state_ = STATE_DUNGEON_CLEAR;
            state_timer_ = 2.0f;
            continue;
        }
    }

    // Monsters patrol
    int alive_monsters = 0;
    for (int m = 0; m < NUM_MONSTERS; ++m) {
        if (!monsters_[m].alive) continue;
        alive_monsters++;

        float new_mx = monsters_[m].x + monsters_[m].vx * dt;
        float new_my = monsters_[m].y + monsters_[m].vy * dt;

        if (std::abs(monsters_[m].y - 7.0f) < 0.8f) {
            if (new_mx <= 0.2f) new_mx = 14.8f;
            else if (new_mx >= 14.8f) new_mx = 0.2f;
        }

        if (IsWall(new_mx, new_my)) {
            monsters_[m].vx = -monsters_[m].vx;
        } else {
            monsters_[m].x = new_mx;
            monsters_[m].y = new_my;
        }

        if (std::hypot(monsters_[m].x - px_, monsters_[m].y - py_) < 0.8f) {
            lives_--;
            state_ = STATE_WORRIOR_DIED;
            state_timer_ = 1.0f;
            return;
        }
    }

    if (alive_monsters == 0 && !wizard_active_) {
        SpawnWizard();
    }

    if (wizard_alive_) {
        wizard_teleport_timer_ -= dt;
        if (wizard_teleport_timer_ <= 0.0f) {
            static const float spots[5][2] = {
                {2.0f, 7.0f}, {13.0f, 7.0f}, {7.5f, 12.0f}, {5.0f, 2.0f}, {7.5f, 2.0f}
            };
            wizard_teleport_count_++;
            int idx = wizard_teleport_count_ % 5;
            wizard_x_ = spots[idx][0];
            wizard_y_ = spots[idx][1];
            wizard_teleport_timer_ = 2.0f;
        }

        if (std::hypot(wizard_x_ - px_, wizard_y_ - py_) < 0.9f) {
            lives_--;
            state_ = STATE_WORRIOR_DIED;
            state_timer_ = 1.0f;
            return;
        }
    }
}

void Game166WizardOfWor::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx]     = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Walls
    for (int y = 0; y < 15; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (IsWall(static_cast<float>(x), static_cast<float>(y))) {
                set_pixel(x, y, 0, 80, 220);
            }
        }
    }

    // Warp portals
    set_pixel(0, 7, 255, 255, 0);
    set_pixel(15, 7, 255, 255, 0);

    // Monsters
    for (int m = 0; m < NUM_MONSTERS; ++m) {
        if (monsters_[m].alive) {
            int mx = static_cast<int>(std::round(monsters_[m].x));
            int my = static_cast<int>(std::round(monsters_[m].y));
            if (!monsters_[m].is_cloaked || IsLineOfSight(monsters_[m].x, monsters_[m].y)) {
                if (monsters_[m].type == 0) set_pixel(mx, my, 0, 150, 255);
                else if (monsters_[m].type == 1) set_pixel(mx, my, 255, 220, 0);
                else set_pixel(mx, my, 255, 40, 40);
            }
        }
    }

    // Wizard
    if (wizard_alive_) {
        int wx = static_cast<int>(std::round(wizard_x_));
        int wy = static_cast<int>(std::round(wizard_y_));
        set_pixel(wx, wy, 255, 0, 255);
        set_pixel(wx, wy - 1, 255, 255, 255);
    }

    // Bullets
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (bullets_[i].active) {
            int bx = static_cast<int>(std::round(bullets_[i].x));
            int by = static_cast<int>(std::round(bullets_[i].y));
            set_pixel(bx, by, 255, 255, 200);
        }
    }

    // Worrior
    int px = static_cast<int>(std::round(px_));
    int py = static_cast<int>(std::round(py_));
    if (state_ == STATE_PLAYING || state_ == STATE_DUNGEON_CLEAR) {
        set_pixel(px, py, 255, 255, 0);
        set_pixel(px, py - 1, 255, 200, 100);
    } else if (state_ == STATE_WORRIOR_DIED) {
        set_pixel(px, py, 255, 60, 0);
    }

    // Bottom Radar Scanner (y=15)
    for (int m = 0; m < NUM_MONSTERS; ++m) {
        if (monsters_[m].alive) {
            int rx = static_cast<int>(std::round(monsters_[m].x));
            set_pixel(rx, 15, 0, 255, 120);
        }
    }
    if (wizard_alive_) {
        int rx = static_cast<int>(std::round(wizard_x_));
        set_pixel(rx, 15, 255, 0, 255);
    }
}

} // namespace arcade
