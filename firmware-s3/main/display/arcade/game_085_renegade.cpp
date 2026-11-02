#include "game_085_renegade.h"
#include <algorithm>
#include <cmath>
#include <cstdlib>

namespace arcade {

Game085Renegade::Game085Renegade() {
    Reset();
}

void Game085Renegade::Init() {
    Reset();
}

void Game085Renegade::Reset() {
    state_ = STATE_FIGHT;
    state_timer_ = 0.0f;
    score_ = 0;
    lives_ = 3;
    hero_hp_ = 100;
    thugs_defeated_ = 0;
    ResetFight();
}

void Game085Renegade::ResetFight() {
    px_ = 4.0f;
    py_ = 10.0f;
    facing_ = 1;
    action_ = ACT_IDLE;
    act_timer_ = 0.0f;
    mounted_thug_idx_ = -1;

    for (int i = 0; i < MAX_THUGS; ++i) {
        thugs_[i].active = true;
        thugs_[i].x = 13.0f + i * 3.0f;
        thugs_[i].y = 8.0f + (i * 2.0f);
        thugs_[i].vx = -2.0f;
        thugs_[i].hp = 3;
        thugs_[i].is_down = false;
        thugs_[i].down_timer = 0.0f;
    }

    train_x_ = -30.0f;
}

void Game085Renegade::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_HERO_DEAD || state_ == STATE_VICTORY) {
        if (state_timer_ > 2.5f && (buttons & (BUTTON_A | BUTTON_B))) {
            Reset();
        }
        return;
    }

    // Train hazard update
    train_x_ += train_speed_ * dt;
    if (train_x_ > 40.0f) {
        train_x_ = -30.0f;
    }

    UpdatePlayer(dt, buttons, prev_buttons);
    UpdateThugs(dt);
    CheckCombat();

    // Check train crushing anyone on the track (y >= 13.8)
    if (train_x_ >= -2.0f && train_x_ <= 18.0f) {
        // Crushes thugs on track
        for (int i = 0; i < MAX_THUGS; ++i) {
            if (thugs_[i].active && thugs_[i].y >= 13.8f && std::abs(thugs_[i].x - train_x_) < 6.0f) {
                thugs_[i].active = false;
                thugs_defeated_++;
                score_ += 1000; // Platform push-off track kill bonus!
            }
        }
        // Crushes hero if on track
        if (py_ >= 13.8f && std::abs(px_ - train_x_) < 5.0f) {
            hero_hp_ = 0;
            lives_--;
            if (lives_ > 0) {
                hero_hp_ = 100;
                px_ = 4.0f;
                py_ = 10.0f;
            } else {
                state_ = STATE_HERO_DEAD;
                state_timer_ = 0.0f;
            }
        }
    }

    if (thugs_defeated_ >= 8) {
        state_ = STATE_VICTORY;
        state_timer_ = 0.0f;
        score_ += 8000;
    }
}

void Game085Renegade::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    float move_speed = 4.8f;

    if (act_timer_ > 0.0f) {
        act_timer_ -= dt;
        if (act_timer_ <= 0.0f) {
            action_ = ACT_IDLE;
            mounted_thug_idx_ = -1;
        }
        return;
    }

    // Check jump kick (A + B)
    if ((buttons & BUTTON_A) && (buttons & BUTTON_B) &&
        (!(prev_buttons & BUTTON_A) || !(prev_buttons & BUTTON_B))) {
        action_ = ACT_JUMP_KICK;
        act_timer_ = 0.35f;
        return;
    }

    // Check ground pound / front punch (Button A)
    if ((buttons & BUTTON_A) && !(prev_buttons & BUTTON_A)) {
        // Look for knocked-down thug to mount and pound!
        int target_down = -1;
        for (int i = 0; i < MAX_THUGS; ++i) {
            if (thugs_[i].active && thugs_[i].is_down && std::abs(thugs_[i].x - px_) < 1.4f && std::abs(thugs_[i].y - py_) < 1.2f) {
                target_down = i;
                break;
            }
        }

        if (target_down >= 0) {
            action_ = ACT_GROUND_POUND;
            act_timer_ = 0.5f;
            mounted_thug_idx_ = target_down;
            px_ = thugs_[target_down].x;
            py_ = thugs_[target_down].y;
            thugs_[target_down].hp -= 2;
            score_ += 300;
            if (thugs_[target_down].hp <= 0) {
                thugs_[target_down].active = false;
                thugs_[target_down].respawn_timer = 2.0f;
                thugs_defeated_++;
            }
            return;
        } else {
            action_ = ACT_FRONT_PUNCH;
            act_timer_ = 0.22f;
            return;
        }
    }

    // Backhand elbow strike (Button B)
    if ((buttons & BUTTON_B) && !(prev_buttons & BUTTON_B)) {
        action_ = ACT_BACK_ELBOW;
        act_timer_ = 0.25f;
        return;
    }

    // Walking
    if (buttons & BUTTON_LEFT)  { px_ -= move_speed * dt; facing_ = -1; }
    if (buttons & BUTTON_RIGHT) { px_ += move_speed * dt; facing_ = 1; }
    if (buttons & BUTTON_UP)    py_ -= (move_speed * 0.7f) * dt;
    if (buttons & BUTTON_DOWN)  py_ += (move_speed * 0.7f) * dt;

    px_ = std::max(1.0f, std::min(15.0f, px_));
    py_ = std::max(7.0f, std::min(14.2f, py_));
}

void Game085Renegade::UpdateThugs(float dt) {
    for (int i = 0; i < MAX_THUGS; ++i) {
        if (!thugs_[i].active) {
            if (thugs_[i].respawn_timer > 0.0f) {
                thugs_[i].respawn_timer -= dt;
                if (thugs_[i].respawn_timer <= 0.0f && thugs_defeated_ + i < 8) {
                    thugs_[i].active = true;
                    thugs_[i].x = 15.5f;
                    thugs_[i].y = 8.0f + (i * 2.0f);
                    thugs_[i].hp = 3;
                    thugs_[i].is_down = false;
                    thugs_[i].down_timer = 0.0f;
                }
            }
            continue;
        }

        if (thugs_[i].is_down) {
            thugs_[i].down_timer -= dt;
            if (thugs_[i].down_timer <= 0.0f) {
                thugs_[i].is_down = false; // Gets back up!
            }
            continue;
        }

        // Approach hero
        if (thugs_[i].x > px_ + 1.2f) {
            thugs_[i].x -= 2.2f * dt;
        } else if (thugs_[i].x < px_ - 1.2f) {
            thugs_[i].x += 2.2f * dt;
        }

        if (thugs_[i].y > py_ + 0.3f) {
            thugs_[i].y -= 1.3f * dt;
        } else if (thugs_[i].y < py_ - 0.3f) {
            thugs_[i].y += 1.3f * dt;
        }
    }
}

void Game085Renegade::CheckCombat() {
    // 1. Hero combat actions
    if (action_ == ACT_FRONT_PUNCH) {
        for (int i = 0; i < MAX_THUGS; ++i) {
            if (!thugs_[i].active || thugs_[i].is_down) continue;
            float dx = (thugs_[i].x - px_) * facing_;
            float dy = std::abs(thugs_[i].y - py_);

            if (dx > 0.0f && dx < 1.8f && dy < 1.2f) {
                thugs_[i].hp--;
                thugs_[i].x += facing_ * 1.5f;
                score_ += 150;
                if (thugs_[i].hp == 1) {
                    thugs_[i].is_down = true; // Knocked down to ground!
                    thugs_[i].down_timer = 2.5f;
                } else if (thugs_[i].hp <= 0) {
                    thugs_[i].active = false;
                    thugs_[i].respawn_timer = 2.0f;
                    thugs_defeated_++;
                }
            }
        }
    } else if (action_ == ACT_BACK_ELBOW) {
        for (int i = 0; i < MAX_THUGS; ++i) {
            if (!thugs_[i].active || thugs_[i].is_down) continue;
            float dx = (thugs_[i].x - px_) * (-facing_); // Behind hero!
            float dy = std::abs(thugs_[i].y - py_);

            if (dx > 0.0f && dx < 1.6f && dy < 1.2f) {
                thugs_[i].hp -= 2;
                thugs_[i].x -= facing_ * 2.0f; // Knocked backward!
                score_ += 250;
                if (thugs_[i].hp <= 0) {
                    thugs_[i].active = false;
                    thugs_[i].respawn_timer = 2.0f;
                    thugs_defeated_++;
                }
            }
        }
    } else if (action_ == ACT_JUMP_KICK) {
        for (int i = 0; i < MAX_THUGS; ++i) {
            if (!thugs_[i].active) continue;
            float dx = (thugs_[i].x - px_) * facing_;
            float dy = std::abs(thugs_[i].y - py_);

            if (dx > 0.0f && dx < 2.0f && dy < 1.4f) {
                thugs_[i].hp -= 2;
                // Massive knockback - pushes them toward tracks or off platform!
                thugs_[i].x += facing_ * 3.5f;
                thugs_[i].y += 1.0f; // Pushes down towards tracks
                thugs_[i].is_down = true;
                thugs_[i].down_timer = 2.0f;
                score_ += 350;
                if (thugs_[i].hp <= 0) {
                    thugs_[i].active = false;
                    thugs_[i].respawn_timer = 2.0f;
                    thugs_defeated_++;
                }
            }
        }
    }

    // 2. Thugs strike hero
    for (int i = 0; i < MAX_THUGS; ++i) {
        if (!thugs_[i].active || thugs_[i].is_down || action_ == ACT_GROUND_POUND) continue;
        if (std::abs(thugs_[i].x - px_) < 1.2f && std::abs(thugs_[i].y - py_) < 1.0f) {
            hero_hp_ -= 1;
            if (hero_hp_ <= 0) {
                lives_--;
                if (lives_ > 0) {
                    hero_hp_ = 100;
                    px_ = 4.0f;
                    py_ = 10.0f;
                } else {
                    state_ = STATE_HERO_DEAD;
                    state_timer_ = 0.0f;
                }
                return;
            }
        }
    }
}

void Game085Renegade::Render(uint8_t* fb) {
    auto set_pixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // 1. Subway Station Tiled Wall (y: 0..6)
    for (int y = 0; y < 7; ++y) {
        for (int x = 0; x < 16; ++x) {
            set_pixel(x, y, 40, 50, 60);
        }
    }
    // Subway Station Sign
    for (int x = 4; x < 12; ++x) set_pixel(x, 2, 20, 100, 200);

    // 2. Concrete Station Platform (y: 7..13)
    for (int y = 7; y < 14; ++y) {
        for (int x = 0; x < 16; ++x) {
            set_pixel(x, y, 90, 90, 95);
        }
    }
    // Yellow Platform Safety Line (y: 13)
    for (int x = 0; x < 16; ++x) {
        set_pixel(x, 13, 255, 220, 0);
    }

    // 3. Train Track & Train (y: 14..15)
    for (int y = 14; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            set_pixel(x, y, 25, 20, 20); // Dark rails & ties
        }
    }

    // Express Train rushing past
    int tx = static_cast<int>(std::round(train_x_));
    for (int dx = -5; dx <= 5; ++dx) {
        set_pixel(tx + dx, 14, 200, 40, 40); // Silver & red express cars
        set_pixel(tx + dx, 15, 180, 180, 190);
    }

    // 4. Thugs (Red & Green mohawk gang members)
    for (int i = 0; i < MAX_THUGS; ++i) {
        if (!thugs_[i].active) continue;
        int ex = static_cast<int>(std::round(thugs_[i].x));
        int ey = static_cast<int>(std::round(thugs_[i].y));

        if (thugs_[i].is_down) {
            // Prone on ground
            set_pixel(ex, ey, 200, 40, 50);
            set_pixel(ex + 1, ey, 240, 180, 140);
        } else {
            set_pixel(ex, ey, 200, 40, 50);      // Leather jacket
            set_pixel(ex, ey - 1, 240, 180, 140); // Head
            set_pixel(ex, ey - 2, 50, 220, 80);   // Green Mohawk hair
        }
    }

    // 5. Hero Kunio (White uniform gakuran)
    int px = static_cast<int>(std::round(px_));
    int py = static_cast<int>(std::round(py_));

    if (action_ == ACT_GROUND_POUND) {
        // Straddling thug, punching down
        set_pixel(px, py, 250, 250, 250);
        set_pixel(px, py - 1, 240, 180, 140);
        set_pixel(px, py + 1, 255, 120, 0); // Fists slamming!
    } else {
        set_pixel(px, py, 250, 250, 250);     // White jacket
        set_pixel(px, py - 1, 240, 180, 140); // Face
        set_pixel(px, py - 2, 20, 20, 20);    // Black hair

        if (action_ == ACT_FRONT_PUNCH) {
            set_pixel(px + facing_, py, 255, 200, 150); // Straight punch
        } else if (action_ == ACT_BACK_ELBOW) {
            set_pixel(px - facing_, py, 255, 200, 150); // Back elbow
        } else if (action_ == ACT_JUMP_KICK) {
            set_pixel(px + facing_ * 2, py - 1, 255, 255, 255); // Flying kick
        }
    }

    // 6. HUD (y = 0)
    int hp_bars = std::max(0, std::min(8, hero_hp_ / 12));
    for (int b = 0; b < hp_bars; ++b) {
        set_pixel(b, 0, 50, 220, 50);
    }
    for (int l = 0; l < lives_; ++l) {
        set_pixel(15 - l * 2, 0, 250, 250, 250);
    }
}

} // namespace arcade
