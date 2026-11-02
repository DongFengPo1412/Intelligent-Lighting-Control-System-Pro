#include "game_058_paperboy.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game058Paperboy::Game058Paperboy()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(2500),
      lives_(3),
      player_x_(8.0f),
      player_y_(12.5f),
      speed_(6.0f),
      papers_remaining_(10),
      delivered_count_(0),
      route_progress_(0.0f) {
}

void Game058Paperboy::Init() {
    Reset();
}

void Game058Paperboy::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    lives_ = 3;
    InitRoute();
}

void Game058Paperboy::InitRoute() {
    player_x_ = 8.0f;
    player_y_ = 12.5f;
    speed_ = 6.0f;
    papers_remaining_ = 10;
    delivered_count_ = 0;
    route_progress_ = 0.0f;

    for (int i = 0; i < MAX_PAPERS; ++i) papers_[i].active = false;

    // Suburban Houses along the street
    houses_[0] = {-5.0f, true, 4.0f, 2.0f, false, false};   // Subscriber house
    houses_[1] = {-20.0f, false, 4.0f, 2.0f, false, false}; // Non-subscriber
    houses_[2] = {-35.0f, true, 4.0f, 2.0f, false, false};  // Subscriber house

    // Suburban hazards
    hazards_[0] = {6.0f, -10.0f, 1.5f, 2.0f, 0, true}; // Barking dog
    hazards_[1] = {11.0f, -25.0f, -1.0f, 2.5f, 1, true}; // Lawnmower
    hazards_[2] = {8.0f, -40.0f, 0.0f, 4.0f, 2, true}; // Skateboarder
}

void Game058Paperboy::ThrowPaper() {
    if (papers_remaining_ <= 0) return;

    for (int i = 0; i < MAX_PAPERS; ++i) {
        if (!papers_[i].active) {
            papers_[i].active = true;
            papers_[i].x = player_x_ - 1.0f;
            papers_[i].y = player_y_;
            papers_[i].vx = -12.0f;
            papers_[i].vy = -3.0f;
            papers_remaining_--;
            break;
        }
    }
}

void Game058Paperboy::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_DEAD) {
        if (state_timer_ > 1.5f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                state_timer_ = 0.0f;
                InitRoute();
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
            InitRoute();
        }
        return;
    }

    UpdateBicycle(dt, buttons, prev_buttons);
    UpdatePapers(dt);
    UpdateHazards(dt);
    CheckCollisions();

    // Check Daily Route Completion
    if (route_progress_ >= 45.0f) {
        state_ = STATE_VICTORY;
        state_timer_ = 0.0f;
        score_ += 1000 + delivered_count_ * 200;
        if (score_ > high_score_) high_score_ = score_;
    }
}

void Game058Paperboy::UpdateBicycle(float dt, uint32_t buttons, uint32_t prev_buttons) {
    // Speed control
    if (buttons & BUTTON_UP) {
        speed_ = std::min(9.0f, speed_ + 8.0f * dt);
    } else if (buttons & BUTTON_DOWN) {
        speed_ = std::max(3.5f, speed_ - 10.0f * dt);
    } else {
        if (speed_ < 6.0f) speed_ += 4.0f * dt;
        if (speed_ > 6.0f) speed_ -= 4.0f * dt;
    }

    // Steering
    if (buttons & BUTTON_LEFT)  player_x_ -= 6.0f * dt;
    if (buttons & BUTTON_RIGHT) player_x_ += 6.0f * dt;

    // Road/Sidewalk bounds
    if (player_x_ < 5.0f) player_x_ = 5.0f; // Edge of sidewalk
    if (player_x_ > 14.5f) player_x_ = 14.5f;

    // Throw Paper: Button A
    if ((buttons & BUTTON_A) && !(prev_buttons & BUTTON_A)) {
        ThrowPaper();
    }

    // Bunny Hop curb: Button B
    // (Bicycle bunny hop could dodge ground cracks)

    // Advance street scroll
    route_progress_ += speed_ * dt;
    score_ += static_cast<int>(speed_ * dt * 2.0f);
}

void Game058Paperboy::UpdatePapers(float dt) {
    for (int i = 0; i < MAX_PAPERS; ++i) {
        if (!papers_[i].active) continue;

        papers_[i].x += papers_[i].vx * dt;
        papers_[i].y += papers_[i].vy * dt;

        if (papers_[i].x < 0.0f || papers_[i].y < 0.0f || papers_[i].y > 15.0f) {
            papers_[i].active = false;
        }
    }
}

void Game058Paperboy::UpdateHazards(float dt) {
    float dy = speed_ * dt;

    // Scroll houses down
    for (int i = 0; i < MAX_HOUSES; ++i) {
        houses_[i].y += dy;
        if (houses_[i].y > 18.0f) {
            houses_[i].y = -15.0f;
            houses_[i].delivered = false;
            houses_[i].window_broken = false;
        }
    }

    // Scroll & move hazards
    for (int i = 0; i < MAX_HAZARDS; ++i) {
        if (!hazards_[i].active) continue;

        hazards_[i].y += dy + hazards_[i].vy * dt;
        hazards_[i].x += hazards_[i].vx * dt;

        if (hazards_[i].x < 5.0f) {
            hazards_[i].x = 5.0f;
            hazards_[i].vx = std::abs(hazards_[i].vx);
        } else if (hazards_[i].x > 14.0f) {
            hazards_[i].x = 14.0f;
            hazards_[i].vx = -std::abs(hazards_[i].vx);
        }

        if (hazards_[i].y > 18.0f) {
            hazards_[i].y = -15.0f - (i * 10.0f);
        }
    }
}

void Game058Paperboy::CheckCollisions() {
    // Check newspaper delivery into mailboxes or window vandalism
    for (int p = 0; p < MAX_PAPERS; ++p) {
        if (!papers_[p].active) continue;

        for (int h = 0; h < MAX_HOUSES; ++h) {
            // Check mailbox hit (x approx 4.0)
            if (std::abs(papers_[p].x - houses_[h].mailbox_x) < 1.3f &&
                std::abs(papers_[p].y - houses_[h].y) < 1.5f) {
                papers_[p].active = false;

                if (houses_[h].is_subscriber && !houses_[h].delivered) {
                    houses_[h].delivered = true;
                    delivered_count_++;
                    score_ += 250;
                }
                break;
            }

            // Check window vandalism (x approx 2.0)
            if (std::abs(papers_[p].x - houses_[h].window_x) < 1.3f &&
                std::abs(papers_[p].y - houses_[h].y) < 1.5f) {
                papers_[p].active = false;

                if (!houses_[h].is_subscriber && !houses_[h].window_broken) {
                    houses_[h].window_broken = true;
                    score_ += 150; // Vandalism bonus points!
                }
                break;
            }
        }
    }

    // Check bike crash into suburban hazards
    for (int i = 0; i < MAX_HAZARDS; ++i) {
        if (!hazards_[i].active) continue;
        if (std::abs(player_x_ - hazards_[i].x) < 0.9f &&
            std::abs(player_y_ - hazards_[i].y) < 0.9f) {
            lives_--;
            state_ = STATE_DEAD;
            state_timer_ = 0.0f;
            return;
        }
    }
}

void Game058Paperboy::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    // Diagonal Isometric Suburban Street:
    // Left x=0..4: Green Front Lawn & Houses
    // Mid x=5..8: Grey Concrete Sidewalk
    // Right x=9..15: Dark Grey Asphalt Road
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            if (x < 5) {
                // Front lawn
                fb[idx] = 40;
                fb[idx + 1] = 160;
                fb[idx + 2] = 40; // Green grass
            } else if (x < 9) {
                // Sidewalk concrete
                fb[idx] = 160;
                fb[idx + 1] = 160;
                fb[idx + 2] = 160;
                if ((y + static_cast<int>(route_progress_)) % 4 == 0) {
                    // Concrete expansion crack
                    fb[idx] = 120;
                    fb[idx + 1] = 120;
                    fb[idx + 2] = 120;
                }
            } else {
                // Asphalt street
                fb[idx] = 50;
                fb[idx + 1] = 50;
                fb[idx + 2] = 55;
            }
        }
    }

    // Render Houses (Porch / Mailbox / Window)
    for (int h = 0; h < MAX_HOUSES; ++h) {
        int hy = static_cast<int>(std::round(houses_[h].y));
        if (hy >= 0 && hy < 16) {
            // House wall
            for (int wx = 0; wx <= 2; ++wx) {
                int idx = (hy * 16 + wx) * 3;
                if (houses_[h].is_subscriber) {
                    fb[idx] = 200;
                    fb[idx + 1] = 180;
                    fb[idx + 2] = 50; // Yellow warm subscriber house
                } else {
                    fb[idx] = 100;
                    fb[idx + 1] = 50;
                    fb[idx + 2] = 50; // Dark non-subscriber house
                }
            }

            // Mailbox (x=4)
            int mb_idx = (hy * 16 + 4) * 3;
            if (houses_[h].delivered) {
                fb[mb_idx] = 0;
                fb[mb_idx + 1] = 255;
                fb[mb_idx + 2] = 0; // Green delivered flag!
            } else {
                fb[mb_idx] = 220;
                fb[mb_idx + 1] = 30;
                fb[mb_idx + 2] = 30; // Red mailbox
            }

            // Window (x=2)
            if (houses_[h].window_broken) {
                int win_idx = (hy * 16 + 2) * 3;
                fb[win_idx] = 255;
                fb[win_idx + 1] = 255;
                fb[win_idx + 2] = 255; // White broken glass
            }
        }
    }

    // Render Hazards
    for (int i = 0; i < MAX_HAZARDS; ++i) {
        if (!hazards_[i].active) continue;
        int hx = static_cast<int>(std::round(hazards_[i].x));
        int hy = static_cast<int>(std::round(hazards_[i].y));
        if (hx >= 0 && hx < 16 && hy >= 0 && hy < 16) {
            int idx = (hy * 16 + hx) * 3;
            if (hazards_[i].type == 0) {
                fb[idx] = 160;
                fb[idx + 1] = 82;
                fb[idx + 2] = 45; // Brown dog
            } else if (hazards_[i].type == 1) {
                fb[idx] = 255;
                fb[idx + 1] = 100;
                fb[idx + 2] = 0; // Orange lawnmower
            } else {
                fb[idx] = 0;
                fb[idx + 1] = 220;
                fb[idx + 2] = 255; // Cyan skateboarder
            }
        }
    }

    // Render Flying Newspapers
    for (int p = 0; p < MAX_PAPERS; ++p) {
        if (!papers_[p].active) continue;
        int px = static_cast<int>(std::round(papers_[p].x));
        int py = static_cast<int>(std::round(papers_[p].y));
        if (px >= 0 && px < 16 && py >= 0 && py < 16) {
            int idx = (py * 16 + px) * 3;
            fb[idx] = 255;
            fb[idx + 1] = 255;
            fb[idx + 2] = 255; // White paper roll
        }
    }

    // Render Paperboy on Bicycle
    int bx = static_cast<int>(std::round(player_x_));
    int by = static_cast<int>(std::round(player_y_));
    if (bx >= 0 && bx < 16 && by >= 0 && by < 16) {
        int idx = (by * 16 + bx) * 3;
        fb[idx] = 50;
        fb[idx + 1] = 100;
        fb[idx + 2] = 255; // Blue paperboy cap

        // Bicycle wheels front and back
        if (by > 0) {
            int f_idx = ((by - 1) * 16 + bx) * 3;
            fb[f_idx] = 200;
            fb[f_idx + 1] = 200;
            fb[f_idx + 2] = 200; // Front wheel
        }
        if (by < 15) {
            int r_idx = ((by + 1) * 16 + bx) * 3;
            fb[r_idx] = 200;
            fb[r_idx + 1] = 200;
            fb[r_idx + 2] = 200; // Rear wheel
        }
    }

    // HUD: Papers remaining pips on row 0
    for (int p = 0; p < papers_remaining_ && p < 10; ++p) {
        int idx = p * 3;
        fb[idx] = 255;
        fb[idx + 1] = 255;
        fb[idx + 2] = 255; // White paper icon
    }

    for (int l = 0; l < lives_ && l < 3; ++l) {
        int idx = (15 - l) * 3;
        fb[idx] = 255;
        fb[idx + 1] = 0;
        fb[idx + 2] = 0;
    }
}

} // namespace arcade
