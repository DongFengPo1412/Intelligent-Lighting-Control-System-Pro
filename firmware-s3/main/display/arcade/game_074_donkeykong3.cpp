#include "game_074_donkeykong3.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game074DonkeyKong3::Game074DonkeyKong3()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(8000),
      lives_(3),
      px_(4.0f),
      py_(14.0f),
      pvy_(0.0f),
      on_ground_(true),
      spray_cooldown_(0.0f),
      has_super_spray_(false),
      super_spray_timer_(0.0f),
      dk_x_(7.5f),
      dk_y_(5.0f),
      dk_drop_speed_(0.6f),
      super_can_active_(false),
      super_can_x_(7.5f),
      super_can_y_(5.0f) {
}

void Game074DonkeyKong3::Init() {
    Reset();
}

void Game074DonkeyKong3::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    lives_ = 3;
    InitStage();
}

void Game074DonkeyKong3::InitStage() {
    px_ = 4.0f;
    py_ = 14.0f;
    pvy_ = 0.0f;
    on_ground_ = true;
    spray_cooldown_ = 0.0f;
    has_super_spray_ = false;
    super_spray_timer_ = 0.0f;

    dk_x_ = 7.5f;
    dk_y_ = 5.0f;
    dk_drop_speed_ = 0.6f;
    super_can_active_ = false;

    for (int i = 0; i < MAX_SPRAYS; ++i) sprays_[i].active = false;

    // 4 Flowers on garden floor
    flowers_[0] = {3.0f, 14.0f, true};
    flowers_[1] = {6.0f, 14.0f, true};
    flowers_[2] = {9.0f, 14.0f, true};
    flowers_[3] = {12.0f, 14.0f, true};

    // Bugs
    bugs_[0] = {2.0f, 2.0f, 2.5f, 1.5f, 0, false, true};
    bugs_[1] = {13.0f, 3.0f, -2.2f, 1.8f, 0, false, true};
    bugs_[2] = {4.0f, 1.0f, 2.0f, 2.0f, 1, false, true};
    bugs_[3] = {11.0f, 1.0f, -2.0f, 2.0f, 1, false, true};
}

int Game074DonkeyKong3::GetFlowersRemaining() const {
    int count = 0;
    for (int i = 0; i < MAX_FLOWERS; ++i) {
        if (flowers_[i].active) count++;
    }
    return count;
}

void Game074DonkeyKong3::SprayUpward() {
    if (spray_cooldown_ > 0.0f) return;

    for (int i = 0; i < MAX_SPRAYS; ++i) {
        if (!sprays_[i].active) {
            sprays_[i].active = true;
            sprays_[i].x = px_;
            sprays_[i].y = py_ - 1.2f;
            sprays_[i].vy = -16.0f;
            sprays_[i].is_super = has_super_spray_;
            break;
        }
    }

    spray_cooldown_ = 0.22f;
}

void Game074DonkeyKong3::Jump() {
    if (on_ground_) {
        pvy_ = -8.5f;
        on_ground_ = false;
    }
}

void Game074DonkeyKong3::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_DEAD) {
        if (state_timer_ > 1.8f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                state_timer_ = 0.0f;
                px_ = 4.0f;
                py_ = 14.0f;
                pvy_ = 0.0f;
                dk_y_ = 5.0f;
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

    if (spray_cooldown_ > 0.0f) spray_cooldown_ -= dt;

    if (super_spray_timer_ > 0.0f) {
        super_spray_timer_ -= dt;
        if (super_spray_timer_ <= 0.0f) {
            has_super_spray_ = false;
        }
    }

    UpdatePlayer(dt, buttons, prev_buttons);
    UpdateSprays(dt);
    UpdateDonkeyKong(dt);
    UpdateBugs(dt);
    CheckCollisions();
}

void Game074DonkeyKong3::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    float move_speed = 5.5f;

    if (buttons & BUTTON_LEFT)  px_ -= move_speed * dt;
    if (buttons & BUTTON_RIGHT) px_ += move_speed * dt;

    px_ = std::max(0.5f, std::min(15.0f, px_));

    // Gravity
    pvy_ += 22.0f * dt;
    py_ += pvy_ * dt;

    // Platform landing check
    on_ground_ = false;
    if (pvy_ >= 0.0f) {
        if (py_ >= 14.0f) {
            py_ = 14.0f;
            pvy_ = 0.0f;
            on_ground_ = true;
        } else if (py_ >= 10.0f && py_ <= 10.6f && ((px_ >= 1.8f && px_ <= 6.2f) || (px_ >= 8.8f && px_ <= 13.2f))) {
            py_ = 10.0f;
            pvy_ = 0.0f;
            on_ground_ = true;
        }
    }

    // Button A: Jump
    if ((buttons & BUTTON_A) && !(prev_buttons & BUTTON_A)) {
        Jump();
    }

    // Button B: Spray Upward
    if ((buttons & BUTTON_B) && !(prev_buttons & BUTTON_B)) {
        SprayUpward();
    }
}

void Game074DonkeyKong3::UpdateSprays(float dt) {
    for (int i = 0; i < MAX_SPRAYS; ++i) {
        if (!sprays_[i].active) continue;
        sprays_[i].y += sprays_[i].vy * dt;
        if (sprays_[i].y < 1.0f) sprays_[i].active = false;
    }
}

void Game074DonkeyKong3::UpdateDonkeyKong(float dt) {
    // DK slowly crawls down ropes
    dk_y_ += dk_drop_speed_ * dt;

    if (dk_y_ >= 11.5f) {
        // DK reaches Stanley: squash!
        lives_--;
        state_ = STATE_DEAD;
        state_timer_ = 0.0f;
        return;
    }

    // Spawn Super Spray Can when DK pushed up past 3.5
    if (dk_y_ <= 3.5f && !super_can_active_ && !has_super_spray_) {
        super_can_active_ = true;
        super_can_x_ = dk_x_;
        super_can_y_ = dk_y_ + 1.5f;
    }

    if (super_can_active_) {
        super_can_y_ += 3.0f * dt;
        if (super_can_y_ > 14.5f) super_can_active_ = false;
    }
}

void Game074DonkeyKong3::UpdateBugs(float dt) {
    for (int i = 0; i < MAX_BUGS; ++i) {
        if (!bugs_[i].active) continue;

        if (bugs_[i].has_flower) {
            // Escape carrying flower upwards
            bugs_[i].y -= 3.0f * dt;
            if (bugs_[i].y < 0.0f) {
                // Bug successfully stole flower and escaped!
                bugs_[i].active = false;
            }
        } else {
            // Swoop towards flowers
            bugs_[i].x += bugs_[i].vx * dt;
            bugs_[i].y += bugs_[i].vy * dt;

            if (bugs_[i].x <= 1.0f) {
                bugs_[i].x = 1.0f;
                bugs_[i].vx = std::abs(bugs_[i].vx);
            } else if (bugs_[i].x >= 14.5f) {
                bugs_[i].x = 14.5f;
                bugs_[i].vx = -std::abs(bugs_[i].vx);
            }

            if (bugs_[i].y <= 1.0f) {
                bugs_[i].y = 1.0f;
                bugs_[i].vy = std::abs(bugs_[i].vy);
            } else if (bugs_[i].y >= 14.0f) {
                // Reached bottom, pick up flower if present
                for (int f = 0; f < MAX_FLOWERS; ++f) {
                    if (flowers_[f].active && std::abs(bugs_[i].x - flowers_[f].x) < 1.4f) {
                        flowers_[f].active = false;
                        bugs_[i].has_flower = true;
                        break;
                    }
                }
                bugs_[i].vy = -std::abs(bugs_[i].vy);
            }
        }
    }
}

void Game074DonkeyKong3::CheckCollisions() {
    // 1. Sprays hit Donkey Kong
    for (int s = 0; s < MAX_SPRAYS; ++s) {
        if (!sprays_[s].active) continue;

        if (std::abs(sprays_[s].x - dk_x_) < 2.0f &&
            sprays_[s].y <= dk_y_ + 1.8f && sprays_[s].y >= dk_y_ - 1.0f) {
            sprays_[s].active = false;
            // Push DK up!
            float push_amount = sprays_[s].is_super ? 1.6f : 0.8f;
            dk_y_ -= push_amount;
            score_ += sprays_[s].is_super ? 100 : 50;

            if (dk_y_ <= 1.5f) {
                // Pushed all the way into top beehive: VICTORY!
                state_ = STATE_VICTORY;
                state_timer_ = 0.0f;
                score_ += 3500;
                if (score_ > high_score_) high_score_ = score_;
                return;
            }
        }
    }

    // 2. Sprays hit bugs
    for (int s = 0; s < MAX_SPRAYS; ++s) {
        if (!sprays_[s].active) continue;
        for (int b = 0; b < MAX_BUGS; ++b) {
            if (!bugs_[b].active) continue;

            if (std::abs(sprays_[s].x - bugs_[b].x) < 1.3f &&
                std::abs(sprays_[s].y - bugs_[b].y) < 1.3f) {
                sprays_[s].active = false;
                bugs_[b].active = false;
                score_ += 200;

                // If bug was carrying flower, flower drops back safely!
                if (bugs_[b].has_flower) {
                    for (int f = 0; f < MAX_FLOWERS; ++f) {
                        if (!flowers_[f].active) {
                            flowers_[f].active = true;
                            flowers_[f].x = bugs_[b].x;
                            flowers_[f].y = 14.0f;
                            break;
                        }
                    }
                }
                break;
            }
        }
    }

    // 3. Stanley collects Super Spray Can
    if (super_can_active_) {
        if (std::abs(px_ - super_can_x_) < 1.2f && std::abs(py_ - super_can_y_) < 1.2f) {
            super_can_active_ = false;
            has_super_spray_ = true;
            super_spray_timer_ = 6.0f;
            score_ += 500;
        }
    }

    // 4. Bugs sting Stanley
    for (int b = 0; b < MAX_BUGS; ++b) {
        if (!bugs_[b].active) continue;
        if (std::abs(px_ - bugs_[b].x) < 0.9f && std::abs(py_ - bugs_[b].y) < 0.9f) {
            lives_--;
            state_ = STATE_DEAD;
            state_timer_ = 0.0f;
            return;
        }
    }
}

void Game074DonkeyKong3::Render(uint8_t* fb) {
    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // 1. Greenhouse Background
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            set_pixel(x, y, 15, 30, 20); // Greenhouse glass / vines
        }
    }

    // Top Beehive ceiling (y=1)
    for (int x = 6; x <= 9; ++x) {
        set_pixel(x, 1, 255, 200, 30); // Golden beehive
    }

    // 2. Ropes hanging from ceiling (x=6 and x=9)
    for (int y = 1; y < 13; ++y) {
        set_pixel(6, y, 180, 150, 80);
        set_pixel(9, y, 180, 150, 80);
    }

    // 3. Platforms
    for (int x = 0; x < 16; ++x) set_pixel(x, 15, 80, 140, 50); // Floor grass
    for (int x = 2; x <= 6; ++x) set_pixel(x, 10, 140, 90, 40);  // Left ledge
    for (int x = 9; x <= 13; ++x) set_pixel(x, 10, 140, 90, 40); // Right ledge

    // 4. Flowers
    for (int f = 0; f < MAX_FLOWERS; ++f) {
        if (!flowers_[f].active) continue;
        int fx = int(std::round(flowers_[f].x));
        int fy = int(std::round(flowers_[f].y));
        set_pixel(fx, fy, 255, 60, 60);       // Red petal
        set_pixel(fx, fy - 1, 255, 220, 40);  // Yellow pollen center
    }

    // 5. Super Spray Can
    if (super_can_active_) {
        int cx = int(std::round(super_can_x_));
        int cy = int(std::round(super_can_y_));
        set_pixel(cx, cy, 255, 215, 0);       // Gold can
        set_pixel(cx, cy - 1, 255, 50, 50);   // Red nozzle
    }

    // 6. Bugs (Buzzbees & Beespies)
    for (int b = 0; b < MAX_BUGS; ++b) {
        if (!bugs_[b].active) continue;
        int bx = int(std::round(bugs_[b].x));
        int by = int(std::round(bugs_[b].y));
        if (bugs_[b].type == 0) {
            // Buzzbee: Yellow/black stripes
            set_pixel(bx, by, 255, 220, 0);
            set_pixel(bx - 1, by, 40, 40, 40);
            set_pixel(bx + 1, by, 40, 40, 40);
        } else {
            // Beespies butterfly: Blue/magenta wings
            set_pixel(bx, by, 255, 50, 200);
            set_pixel(bx - 1, by, 50, 150, 255);
            set_pixel(bx + 1, by, 50, 150, 255);
        }
        if (bugs_[b].has_flower) {
            set_pixel(bx, by + 1, 255, 60, 60); // Carrying flower
        }
    }

    // 7. Donkey Kong (Giant Brown Ape on ropes)
    int dkx = int(std::round(dk_x_));
    int dky = int(std::round(dk_y_));
    for (int dy = -1; dy <= 1; ++dy) {
        for (int dx = -1; dx <= 1; ++dx) {
            set_pixel(dkx + dx, dky + dy, 140, 70, 20); // Brown fur body
        }
    }
    set_pixel(dkx, dky, 240, 180, 120);     // Peach face
    set_pixel(dkx - 1, dky, 255, 30, 30);   // Red tie
    set_pixel(dkx - 2, dky - 1, 140, 70, 20); // Left arm grasping rope
    set_pixel(dkx + 2, dky - 1, 140, 70, 20); // Right arm grasping rope

    // 8. Sprays
    for (int s = 0; s < MAX_SPRAYS; ++s) {
        if (!sprays_[s].active) continue;
        int sx = int(std::round(sprays_[s].x));
        int sy = int(std::round(sprays_[s].y));
        if (sprays_[s].is_super) {
            set_pixel(sx, sy, 255, 255, 50);  // High power yellow spray
            set_pixel(sx, sy - 1, 255, 200, 0);
        } else {
            set_pixel(sx, sy, 200, 240, 255); // White insecticide puff
            set_pixel(sx, sy - 1, 150, 220, 255);
        }
    }

    // 9. Stanley the Exterminator
    if (state_ != STATE_DEAD) {
        int sx = int(std::round(px_));
        int sy = int(std::round(py_));

        set_pixel(sx, sy, 40, 60, 180);       // Blue overalls
        set_pixel(sx, sy - 1, 255, 200, 160); // Face
        set_pixel(sx, sy - 2, 220, 30, 30);   // Red cap
        set_pixel(sx, sy - 3, 220, 220, 240); // Spray nozzle raised up
    } else {
        int sx = int(std::round(px_));
        int sy = int(std::round(py_));
        set_pixel(sx, sy, 220, 30, 30);
    }
}

} // namespace arcade
