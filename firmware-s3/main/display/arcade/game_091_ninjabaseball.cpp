#include "game_091_ninjabaseball.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game091NinjaBaseball::Game091NinjaBaseball() {
    Init();
}

void Game091NinjaBaseball::Init() {
    ResetInning(true);
}

void Game091NinjaBaseball::Reset() {
    ResetInning(true);
}

void Game091NinjaBaseball::ResetInning(bool hard_reset) {
    if (hard_reset) {
        score_ = 0;
        lives_ = 3;
        inning_ = 1;
        home_runs_ = 0;
    }
    state_ = STATE_INNING;
    state_timer_ = 0.0f;
    thugs_defeated_ = 0;

    px_ = 3.0f;
    py_ = 12.0f;
    facing_ = 1;
    action_state_ = ACTION_IDLE;
    action_timer_ = 0.0f;

    for (int i = 0; i < MAX_THUGS; ++i) {
        thugs_[i].active = true;
        thugs_[i].x = 11.0f + i * 2.0f;
        thugs_[i].y = 9.0f + (i * 2.0f);
        thugs_[i].vx = -1.6f;
        thugs_[i].vy = 0.0f;
        thugs_[i].hp = 2;
        thugs_[i].is_airborne = false;
        thugs_[i].is_homerun_flying = false;
        thugs_[i].respawn_timer = 0.0f;
    }
}

void Game091NinjaBaseball::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_HERO_HIT) {
        if (state_timer_ > 1.8f) {
            lives_--;
            if (lives_ <= 0) {
                state_ = STATE_GAME_OVER;
                state_timer_ = 0.0f;
            } else {
                ResetInning(false);
            }
        }
        return;
    }

    if (state_ == STATE_STAGE_CLEAR) {
        if (state_timer_ > 2.0f) {
            inning_++;
            ResetInning(false);
        }
        return;
    }

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            ResetInning(true);
        }
        return;
    }

    UpdatePlayer(dt, buttons, prev_buttons);
    UpdateThugs(dt);
    CheckBatCombat();

    if (thugs_defeated_ >= 6) {
        state_ = STATE_STAGE_CLEAR;
        state_timer_ = 0.0f;
        score_ += 1000;
    }
}

void Game091NinjaBaseball::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (action_timer_ > 0.0f) {
        action_timer_ -= dt;
        if (action_state_ == ACTION_SLIDE) {
            px_ += facing_ * 8.5f * dt;
        }
        if (action_timer_ <= 0.0f) {
            action_state_ = ACTION_IDLE;
        }
    }

    // Directional movement when not locked in bat swing
    if (action_state_ == ACTION_IDLE) {
        float move_speed = 5.5f;
        if (buttons & BTN_LEFT) {
            px_ -= move_speed * dt;
            facing_ = -1;
        }
        if (buttons & BTN_RIGHT) {
            px_ += move_speed * dt;
            facing_ = 1;
        }
        if (buttons & BTN_UP) {
            py_ -= move_speed * 0.7f * dt;
        }
        if (buttons & BTN_DOWN) {
            py_ += move_speed * 0.7f * dt;
        }

        px_ = std::clamp(px_, 1.0f, 14.5f);
        py_ = std::clamp(py_, 8.0f, 14.0f);

        // Actions:
        // 1. Bat Bunt (Up + Button A)
        if ((buttons & BTN_UP) && (buttons & BTN_A) && !(prev_buttons & BTN_A)) {
            action_state_ = ACTION_BUNT;
            action_timer_ = 0.25f;
        }
        // 2. Bat Swing / Home Run (Button A alone)
        else if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
            // Check if there is an airborne enemy in reach -> Home Run!
            bool found_airborne = false;
            for (int i = 0; i < MAX_THUGS; ++i) {
                if (thugs_[i].active && thugs_[i].is_airborne && !thugs_[i].is_homerun_flying) {
                    float dx = (thugs_[i].x - px_) * facing_;
                    float dy = std::fabs(thugs_[i].y - py_);
                    if (dx > 0.0f && dx < 2.0f && dy < 2.5f) {
                        found_airborne = true;
                        break;
                    }
                }
            }

            if (found_airborne) {
                action_state_ = ACTION_HOMERUN;
                action_timer_ = 0.35f;
            } else {
                action_state_ = ACTION_SWING;
                action_timer_ = 0.22f;
            }
        }
        // 3. Slide Tackle (Button B)
        else if ((buttons & BTN_B) && !(prev_buttons & BTN_B)) {
            action_state_ = ACTION_SLIDE;
            action_timer_ = 0.35f;
            px_ += facing_ * 8.5f * dt;
        }
    }
}

void Game091NinjaBaseball::UpdateThugs(float dt) {
    for (int i = 0; i < MAX_THUGS; ++i) {
        Thug& t = thugs_[i];
        if (!t.active) {
            if (t.respawn_timer > 0.0f) {
                t.respawn_timer -= dt;
            } else {
                t.active = true;
                t.hp = 2;
                t.x = 14.0f + (float)(rand() % 3);
                t.y = 8.5f + (float)(rand() % 5);
                t.vx = -1.6f;
                t.vy = 0.0f;
                t.is_airborne = false;
                t.is_homerun_flying = false;
            }
            continue;
        }

        // Home Run fly out of stadium
        if (t.is_homerun_flying) {
            t.x += t.vx * dt;
            t.y += t.vy * dt;
            t.vy += 8.0f * dt;
            if (t.x < -3.0f || t.x > 18.0f || t.y < -3.0f) {
                t.active = false;
                t.is_homerun_flying = false;
                t.respawn_timer = 2.0f;
            }
            continue;
        }

        // Airborne pop fly physics
        if (t.is_airborne) {
            t.y += t.vy * dt;
            t.vy += 14.0f * dt;
            if (t.vy >= 0.0f && t.y >= 12.0f) {
                t.y = 12.0f;
                t.vy = 0.0f;
                t.is_airborne = false;
            }
            continue;
        }

        // Ground walking AI
        float dx = px_ - t.x;
        float dy = py_ - t.y;
        t.x += (dx > 0.0f ? 1.0f : -1.0f) * 1.5f * dt;
        t.y += (dy > 0.0f ? 1.0f : -1.0f) * 0.8f * dt;
    }
}

void Game091NinjaBaseball::CheckBatCombat() {
    for (int i = 0; i < MAX_THUGS; ++i) {
        Thug& t = thugs_[i];
        if (!t.active || t.is_homerun_flying) continue;

        float dx = (t.x - px_) * facing_;
        float dy = std::fabs(t.y - py_);

        // 1. Home Run Execution
        if (action_state_ == ACTION_HOMERUN) {
            if (dx > 0.0f && dx < 2.0f && dy < 2.5f && t.is_airborne) {
                t.is_airborne = false;
                t.is_homerun_flying = true;
                t.vx = facing_ * 16.0f;
                t.vy = -7.5f;
                t.hp = 0;
                score_ += 500;
                home_runs_++;
                thugs_defeated_++;
                continue;
            }
        }

        // 2. Bat Bunt (Pops thug into air)
        if (action_state_ == ACTION_BUNT) {
            if (dx > 0.0f && dx < 1.6f && dy < 1.3f && !t.is_airborne) {
                t.is_airborne = true;
                t.vy = -6.5f;
                t.vx = facing_ * 0.8f;
                score_ += 50;
                continue;
            }
        }

        // 3. Bat Swing (Ground attack)
        if (action_state_ == ACTION_SWING) {
            if (dx > 0.0f && dx < 1.8f && dy < 1.2f && !t.is_airborne) {
                t.hp--;
                t.x += facing_ * 2.0f;
                score_ += 100;
                if (t.hp <= 0) {
                    t.active = false;
                    t.respawn_timer = 2.0f;
                    thugs_defeated_++;
                }
                continue;
            }
        }

        // 4. Slide Tackle
        if (action_state_ == ACTION_SLIDE) {
            if (dx > -0.5f && dx < 1.5f && dy < 1.0f) {
                t.hp--;
                t.x += facing_ * 1.5f;
                score_ += 120;
                if (t.hp <= 0) {
                    t.active = false;
                    t.respawn_timer = 2.0f;
                    thugs_defeated_++;
                }
                continue;
            }
        }

        // 5. Thug attacks Idle Batter
        if (action_state_ == ACTION_IDLE) {
            float dist = std::fabs(t.x - px_);
            if (dist < 0.9f && dy < 0.8f) {
                state_ = STATE_HERO_HIT;
                state_timer_ = 0.0f;
                break;
            }
        }
    }
}

void Game091NinjaBaseball::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Outfield Green Grass
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            set_pixel(x, y, 25, 95, 30);
        }
    }

    // Infield Brown Dirt Diamond
    for (int y = 7; y <= 15; ++y) {
        for (int x = 1; x <= 14; ++x) {
            if ((x + y >= 11) && (y - x <= 11)) {
                set_pixel(x, y, 165, 115, 60);
            }
        }
    }

    // Home Base White Pentagon
    set_pixel(3, 13, 255, 255, 255);
    set_pixel(2, 13, 240, 240, 240);

    // Render Thugs
    for (int i = 0; i < MAX_THUGS; ++i) {
        const Thug& t = thugs_[i];
        if (!t.active) continue;

        int tx = (int)std::round(t.x);
        int ty = (int)std::round(t.y);

        if (t.is_homerun_flying) {
            // Spinning baseball flying out!
            set_pixel(tx, ty, 255, 255, 255);
            set_pixel(tx + 1, ty, 255, 60, 60); // Red stitches
            set_pixel(tx, ty - 1, 255, 220, 0); // Speed flash
        } else if (t.is_airborne) {
            // High in air popped thug
            set_pixel(tx, ty, 40, 100, 180);
            set_pixel(tx, ty - 1, 255, 255, 255); // baseball head
        } else {
            // Ground catcher thug
            set_pixel(tx, ty, 40, 90, 160);       // Blue armor
            set_pixel(tx, ty - 1, 240, 240, 240); // Baseball head
            set_pixel(tx - 1, ty - 1, 160, 90, 30); // Leather glove
        }
    }

    // Render Batter (Captain Jose)
    int px = (int)std::round(px_);
    int py = (int)std::round(py_);

    if (state_ == STATE_HERO_HIT) {
        set_pixel(px, py, 255, 50, 0);
        set_pixel(px, py - 1, 255, 220, 0);
    } else {
        if (action_state_ == ACTION_SLIDE) {
            // Dirt-sliding ninja
            set_pixel(px, py, 220, 30, 30);            // Red ninja suit
            set_pixel(px + facing_, py, 240, 190, 140);
            set_pixel(px - facing_, py, 200, 150, 80);  // Dirt plume
        } else if (action_state_ == ACTION_HOMERUN) {
            // Full golden 360-degree home run swing!
            set_pixel(px, py, 220, 30, 30);
            set_pixel(px, py - 1, 240, 190, 140);
            set_pixel(px + facing_, py - 1, 255, 230, 0); // Golden bat
            set_pixel(px + facing_ * 2, py - 1, 255, 255, 180); // Swing spark
            set_pixel(px + facing_, py - 2, 255, 200, 0);
        } else if (action_state_ == ACTION_BUNT) {
            // Short horizontal bunt bat held forward
            set_pixel(px, py, 220, 30, 30);
            set_pixel(px, py - 1, 240, 190, 140);
            set_pixel(px + facing_, py - 1, 200, 140, 50); // Wooden bat
        } else if (action_state_ == ACTION_SWING) {
            // Standard bat swing
            set_pixel(px, py, 220, 30, 30);
            set_pixel(px, py - 1, 240, 190, 140);
            set_pixel(px + facing_, py - 1, 220, 160, 60);
        } else {
            // Bat ready batting stance
            set_pixel(px, py, 220, 30, 30);        // Red ninja legs
            set_pixel(px, py - 1, 240, 190, 140);   // Face
            set_pixel(px, py - 2, 200, 20, 20);     // Red ninja cap
            set_pixel(px - facing_, py - 2, 200, 140, 50); // Bat resting on shoulder
        }
    }

    // Top HUD: Lives on left, Home Run star icons on right
    for (int l = 0; l < lives_ && l < 3; ++l) {
        set_pixel(l, 0, 255, 50, 50);
    }
    for (int hr = 0; hr < home_runs_ && hr < 4; ++hr) {
        set_pixel(15 - hr, 0, 255, 220, 0);
    }
}

} // namespace arcade
