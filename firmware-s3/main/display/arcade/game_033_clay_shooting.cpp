#include "game_033_clay_shooting.h"
#include <cmath>
#include <cstdlib>
#include <algorithm>

namespace arcade {

Game033ClayShooting::Game033ClayShooting()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(0),
      current_round_(1),
      total_hits_(0),
      round_hits_(0),
      ammo_(2),
      crosshair_x_(7.5f),
      crosshair_y_(7.5f),
      muzzle_flash_(0.0f) {
}

void Game033ClayShooting::Init() {
    Reset();
}

void Game033ClayShooting::Reset() {
    state_ = STATE_LAUNCHING;
    state_timer_ = 0.0f;
    score_ = 0;
    current_round_ = 1;
    total_hits_ = 0;
    crosshair_x_ = 7.5f;
    crosshair_y_ = 7.5f;
    muzzle_flash_ = 0.0f;

    LaunchRound();
}

void Game033ClayShooting::LaunchDoubleTrap() {
    ammo_ = 2;
    round_hits_ = 0;

    // Clay 0: Launch from Left Trap
    clays_[0].active = true;
    clays_[0].shattered = false;
    clays_[0].shatter_timer = 0.0f;
    clays_[0].x = 1.0f;
    clays_[0].y = 14.0f;
    clays_[0].vx = 4.2f + static_cast<float>(rand() % 15) / 10.0f;
    clays_[0].vy = -(11.5f + static_cast<float>(rand() % 20) / 10.0f);

    // Clay 1: Launch from Right Trap (Slightly staggered or simultaneous)
    clays_[1].active = true;
    clays_[1].shattered = false;
    clays_[1].shatter_timer = 0.0f;
    clays_[1].x = 14.0f;
    clays_[1].y = 14.0f;
    clays_[1].vx = -(4.2f + static_cast<float>(rand() % 15) / 10.0f);
    clays_[1].vy = -(11.5f + static_cast<float>(rand() % 20) / 10.0f);
}

void Game033ClayShooting::LaunchRound() {
    LaunchDoubleTrap();
}

bool Game033ClayShooting::PullTrigger() {
    if (ammo_ <= 0) return false;

    ammo_--;
    muzzle_flash_ = 0.08f;

    // Hit test against active clays
    for (int i = 0; i < MAX_CLAYS; ++i) {
        if (clays_[i].active && !clays_[i].shattered) {
            float dist = fabsf(crosshair_x_ - clays_[i].x) + fabsf(crosshair_y_ - clays_[i].y);
            if (dist <= 1.45f) {
                clays_[i].shattered = true;
                clays_[i].shatter_timer = 0.35f;
                round_hits_++;
                total_hits_++;

                // Apex altitude bonus
                int pts = (clays_[i].y <= 5.0f) ? 100 : 50;
                score_ += pts;

                // Double trap bonus
                if (round_hits_ == 2) {
                    score_ += 200; // Perfect Double!
                }

                if (score_ > high_score_) high_score_ = score_;
                return true;
            }
        }
    }
    return false;
}

void Game033ClayShooting::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_START) {
        if (buttons & (KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_GAMEOVER) {
        if (state_timer_ >= 2.0f && (buttons & (KEY_A | KEY_B))) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_ROUND_CLEAR) {
        if (state_timer_ >= 1.2f) {
            if (current_round_ < MAX_ROUNDS) {
                current_round_++;
                state_ = STATE_LAUNCHING;
                state_timer_ = 0.0f;
                LaunchRound();
            } else {
                state_ = STATE_GAMEOVER;
                state_timer_ = 0.0f;
            }
        }
        return;
    }

    // 1. Muzzle Flash Decay
    if (muzzle_flash_ > 0.0f) {
        muzzle_flash_ -= dt;
    }

    // 2. Crosshair Movement
    const float speed = 12.0f;
    if (buttons & KEY_LEFT)  crosshair_x_ = std::max(0.5f, crosshair_x_ - speed * dt);
    if (buttons & KEY_RIGHT) crosshair_x_ = std::min(14.5f, crosshair_x_ + speed * dt);
    if (buttons & KEY_UP)    crosshair_y_ = std::max(1.0f, crosshair_y_ - speed * dt);
    if (buttons & KEY_DOWN)  crosshair_y_ = std::min(14.5f, crosshair_y_ + speed * dt);

    // 3. Trigger Shotgun
    if ((buttons & KEY_A) && !(prev_buttons & KEY_A)) {
        PullTrigger();
    }

    UpdateClays(dt);
    CheckRoundProgression();
}

void Game033ClayShooting::UpdateClays(float dt) {
    const float gravity = 9.8f;

    for (int i = 0; i < MAX_CLAYS; ++i) {
        if (!clays_[i].active) continue;

        if (clays_[i].shattered) {
            clays_[i].shatter_timer -= dt;
            if (clays_[i].shatter_timer <= 0.0f) {
                clays_[i].active = false;
            }
            continue;
        }

        // Parabolic physics
        clays_[i].x += clays_[i].vx * dt;
        clays_[i].y += clays_[i].vy * dt;
        clays_[i].vy += gravity * dt;

        // Fall below grass
        if (clays_[i].y > 15.0f && clays_[i].vy > 0.0f) {
            clays_[i].active = false; // Missed
        }
        // Lateral escape
        if (clays_[i].x < -1.0f || clays_[i].x > 16.5f) {
            clays_[i].active = false;
        }
    }
}

void Game033ClayShooting::CheckRoundProgression() {
    bool any_active = false;
    for (int i = 0; i < MAX_CLAYS; ++i) {
        if (clays_[i].active) {
            any_active = true;
            break;
        }
    }

    if (!any_active) {
        state_ = STATE_ROUND_CLEAR;
        state_timer_ = 0.0f;
    }
}

void Game033ClayShooting::Render(uint8_t* fb) {
    // 1. Sky & Horizon
    // Top 13 rows are Sky Blue (#3498DB / #2980B9), Bottom 3 rows are Grass Green (#27AE60)
    for (int y = 0; y < 13; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            fb[idx + 0] = 52;  fb[idx + 1] = 152; fb[idx + 2] = 219;
        }
    }
    for (int y = 13; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            fb[idx + 0] = 39;  fb[idx + 1] = 174; fb[idx + 2] = 96;
        }
    }

    // 2. Shotgun Traps (Mechanical Launchers on left and right)
    fb[(14 * 16 + 0) * 3 + 0] = 80; fb[(14 * 16 + 0) * 3 + 1] = 80; fb[(14 * 16 + 0) * 3 + 2] = 80;
    fb[(14 * 16 + 15) * 3 + 0] = 80; fb[(14 * 16 + 15) * 3 + 1] = 80; fb[(14 * 16 + 15) * 3 + 2] = 80;

    // 3. HUD: Ammo Shells (Red cylinders on row 0)
    for (int a = 0; a < ammo_; ++a) {
        int idx = (0 * 16 + a) * 3;
        fb[idx + 0] = 231; fb[idx + 1] = 76; fb[idx + 2] = 60; // Red Shell
    }

    // Hits tally on row 0 right
    for (int h = 0; h < total_hits_ && h < 5; ++h) {
        int idx = (0 * 16 + (15 - h)) * 3;
        fb[idx + 0] = 241; fb[idx + 1] = 196; fb[idx + 2] = 15; // Gold star
    }

    // 4. Clays
    for (int i = 0; i < MAX_CLAYS; ++i) {
        if (!clays_[i].active) continue;

        int cx = static_cast<int>(std::round(clays_[i].x));
        int cy = static_cast<int>(std::round(clays_[i].y));

        if (cx >= 0 && cx < 16 && cy >= 0 && cy < 16) {
            int idx = (cy * 16 + cx) * 3;
            if (clays_[i].shattered) {
                // Shattered debris explosion (Yellow & White sparks)
                fb[idx + 0] = 255; fb[idx + 1] = 255; fb[idx + 2] = 255;
                if (cx > 0) {
                    int l_idx = (cy * 16 + (cx - 1)) * 3;
                    fb[l_idx + 0] = 241; fb[l_idx + 1] = 196; fb[l_idx + 2] = 15;
                }
                if (cx < 15) {
                    int r_idx = (cy * 16 + (cx + 1)) * 3;
                    fb[r_idx + 0] = 230; fb[r_idx + 1] = 126; fb[r_idx + 2] = 34;
                }
            } else {
                // Fluorescent Orange Clay Disc
                fb[idx + 0] = 230; fb[idx + 1] = 126; fb[idx + 2] = 34;
            }
        }
    }

    // 5. Crosshair (Laser Green #2ECC71 or Red Reticle, flashes White on shot)
    int hx = static_cast<int>(std::round(crosshair_x_));
    int hy = static_cast<int>(std::round(crosshair_y_));

    uint8_t cr = 46, cg = 204, cb = 113; // Green Reticle
    if (muzzle_flash_ > 0.0f) {
        cr = 255; cg = 255; cb = 255; // White Shotgun Blast
    }

    if (hx >= 0 && hx < 16 && hy >= 0 && hy < 16) {
        fb[(hy * 16 + hx) * 3 + 0] = cr;
        fb[(hy * 16 + hx) * 3 + 1] = cg;
        fb[(hy * 16 + hx) * 3 + 2] = cb;

        // 4 Crosshair spokes
        if (hx > 0) {
            fb[(hy * 16 + (hx - 1)) * 3 + 0] = cr;
            fb[(hy * 16 + (hx - 1)) * 3 + 1] = cg;
            fb[(hy * 16 + (hx - 1)) * 3 + 2] = cb;
        }
        if (hx < 15) {
            fb[(hy * 16 + (hx + 1)) * 3 + 0] = cr;
            fb[(hy * 16 + (hx + 1)) * 3 + 1] = cg;
            fb[(hy * 16 + (hx + 1)) * 3 + 2] = cb;
        }
        if (hy > 0) {
            fb[((hy - 1) * 16 + hx) * 3 + 0] = cr;
            fb[((hy - 1) * 16 + hx) * 3 + 1] = cg;
            fb[((hy - 1) * 16 + hx) * 3 + 2] = cb;
        }
        if (hy < 15) {
            fb[((hy + 1) * 16 + hx) * 3 + 0] = cr;
            fb[((hy + 1) * 16 + hx) * 3 + 1] = cg;
            fb[((hy + 1) * 16 + hx) * 3 + 2] = cb;
        }
    }
}

} // namespace arcade
