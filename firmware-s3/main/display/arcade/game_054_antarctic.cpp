#include "game_054_antarctic.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game054Antarctic::Game054Antarctic()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(2500),
      penguin_lane_(0.0f),
      speed_(12.0f),
      is_jumping_(false),
      jump_timer_(0.0f),
      trip_stun_timer_(0.0f),
      distance_remaining_(100.0f),
      time_remaining_(45.0f),
      fish_collected_(0) {
}

void Game054Antarctic::Init() {
    Reset();
}

void Game054Antarctic::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    InitStage();
}

void Game054Antarctic::InitStage() {
    penguin_lane_ = 0.0f;
    speed_ = 14.0f;
    is_jumping_ = false;
    jump_timer_ = 0.0f;
    trip_stun_timer_ = 0.0f;
    distance_remaining_ = 100.0f;
    time_remaining_ = 45.0f;
    fish_collected_ = 0;

    crevasses_[0] = {30.0f, -0.4f, true};
    crevasses_[1] = {65.0f, 0.3f, true};
    crevasses_[2] = {95.0f, -0.2f, true};

    seals_[0] = {45.0f, 0.4f, true, true};
    seals_[1] = {80.0f, -0.5f, true, true};

    fishes_[0] = {20.0f, 0.0f, true};
    fishes_[1] = {75.0f, 0.2f, true};
}

void Game054Antarctic::TriggerJump() {
    if (!is_jumping_ && trip_stun_timer_ <= 0.0f) {
        is_jumping_ = true;
        jump_timer_ = 0.55f;
    }
}

void Game054Antarctic::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_DEAD) {
        if (state_timer_ > 2.0f) {
            state_ = STATE_START;
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

    time_remaining_ -= dt;
    if (time_remaining_ <= 0.0f) {
        time_remaining_ = 0.0f;
        state_ = STATE_DEAD;
        state_timer_ = 0.0f;
        return;
    }

    UpdatePenguin(dt, buttons, prev_buttons);
    UpdateHazards(dt);
    CheckCollisions();

    // Check Victory
    if (distance_remaining_ <= 0.0f) {
        distance_remaining_ = 0.0f;
        state_ = STATE_VICTORY;
        state_timer_ = 0.0f;
        score_ += 1000 + static_cast<int>(time_remaining_ * 30.0f);
        if (score_ > high_score_) high_score_ = score_;
    }
}

void Game054Antarctic::UpdatePenguin(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (trip_stun_timer_ > 0.0f) {
        trip_stun_timer_ -= dt;
        speed_ = std::max(0.0f, speed_ - 20.0f * dt);
        return;
    }

    // Acceleration & Braking
    if (buttons & BUTTON_UP) {
        speed_ = std::min(24.0f, speed_ + 10.0f * dt);
    } else if (buttons & BUTTON_DOWN) {
        speed_ = std::max(8.0f, speed_ - 15.0f * dt);
    } else {
        // Natural cruising speed
        if (speed_ < 14.0f) speed_ += 5.0f * dt;
    }

    // Steering left / right
    if (buttons & BUTTON_LEFT) {
        penguin_lane_ -= 2.2f * dt;
    } else if (buttons & BUTTON_RIGHT) {
        penguin_lane_ += 2.2f * dt;
    }
    penguin_lane_ = std::max(-1.0f, std::min(1.0f, penguin_lane_));

    // Jump trigger
    if ((buttons & BUTTON_A) && !(prev_buttons & BUTTON_A)) {
        TriggerJump();
    }

    if (is_jumping_) {
        jump_timer_ -= dt;
        if (jump_timer_ <= 0.0f) {
            is_jumping_ = false;
        }
    }

    // Advance distance
    distance_remaining_ -= (speed_ * 0.15f) * dt;
    score_ += static_cast<int32_t>(speed_ * dt * 2.0f);
}

void Game054Antarctic::UpdateHazards(float dt) {
    float dz = speed_ * dt * 2.5f;

    // Advance crevasses
    for (int i = 0; i < MAX_CREVASSES; ++i) {
        if (!crevasses_[i].active) continue;
        crevasses_[i].z -= dz;
        if (crevasses_[i].z < -5.0f) {
            crevasses_[i].z = 100.0f + (i * 20.0f);
            crevasses_[i].lane = ((i % 2 == 0) ? -0.4f : 0.4f);
        }
    }

    // Advance seals
    for (int i = 0; i < MAX_SEALS; ++i) {
        if (!seals_[i].active) continue;
        seals_[i].z -= dz;
        if (seals_[i].z < -5.0f) {
            seals_[i].z = 90.0f + (i * 35.0f);
            seals_[i].lane = ((i % 2 == 0) ? 0.5f : -0.5f);
        }
    }

    // Advance fish
    for (int i = 0; i < MAX_FISH; ++i) {
        if (!fishes_[i].active) continue;
        fishes_[i].z -= dz;
        if (fishes_[i].z < -5.0f) {
            fishes_[i].z = 80.0f + (i * 40.0f);
            fishes_[i].lane = (i == 0 ? -0.1f : 0.1f);
        }
    }
}

void Game054Antarctic::CheckCollisions() {
    // Check crevasse trip
    for (int i = 0; i < MAX_CREVASSES; ++i) {
        if (!crevasses_[i].active) continue;
        if (crevasses_[i].z >= -1.0f && crevasses_[i].z <= 3.0f) {
            if (std::abs(penguin_lane_ - crevasses_[i].lane) < 0.6f) {
                if (!is_jumping_) {
                    trip_stun_timer_ = 1.2f;
                    speed_ = 0.0f;
                    crevasses_[i].z = -6.0f; // Pass it behind
                    return;
                }
            }
        }
    }

    // Check seal bump
    for (int i = 0; i < MAX_SEALS; ++i) {
        if (!seals_[i].active) continue;
        if (seals_[i].z >= -1.0f && seals_[i].z <= 3.0f) {
            if (std::abs(penguin_lane_ - seals_[i].lane) < 0.5f) {
                trip_stun_timer_ = 1.0f;
                speed_ = 0.0f;
                seals_[i].z = -6.0f;
                return;
            }
        }
    }

    // Check fish collection
    for (int i = 0; i < MAX_FISH; ++i) {
        if (!fishes_[i].active) continue;
        if (fishes_[i].z >= -1.5f && fishes_[i].z <= 3.5f) {
            if (std::abs(penguin_lane_ - fishes_[i].lane) < 0.55f) {
                fishes_[i].active = false;
                fish_collected_++;
                score_ += 200;
                time_remaining_ = std::min(60.0f, time_remaining_ + 3.0f);
                speed_ = std::min(26.0f, speed_ + 4.0f); // Fish burst!
            }
        }
    }
}

void Game054Antarctic::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    // Horizon at y=4
    // Sky: Dark Antarctic dusk / aurora (Deep blue / cyan)
    for (int y = 0; y < 4; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = 10;
            fb[idx + 1] = 20;
            fb[idx + 2] = 50 + y * 15;
        }
    }

    // Ice ground: y=4 to 15 (White with cyan snowbanks)
    for (int y = 4; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            // Ice plain
            fb[idx] = 180 + (y * 5);
            fb[idx + 1] = 210 + (y * 3);
            fb[idx + 2] = 245;

            // Perspective road borders
            float road_width = 2.0f + (y - 4.0f) * 1.0f;
            float center_x = 7.5f;
            if (std::abs(x - center_x) > road_width) {
                // Snow dunes
                fb[idx] = 140;
                fb[idx + 1] = 170;
                fb[idx + 2] = 200;
            }
        }
    }

    // Render Crevasses (Dark blue ice fissures)
    for (int i = 0; i < MAX_CREVASSES; ++i) {
        if (!crevasses_[i].active) continue;
        if (crevasses_[i].z > 0.0f && crevasses_[i].z < 100.0f) {
            float t = (100.0f - crevasses_[i].z) / 100.0f;
            int cy = 4 + static_cast<int>(t * 10.0f);
            float road_w = 2.0f + (cy - 4.0f) * 1.0f;
            int cx = static_cast<int>(std::round(7.5f + crevasses_[i].lane * road_w));
            if (cy >= 4 && cy < 16) {
                for (int dx = -1; dx <= 1; ++dx) {
                    int px = cx + dx;
                    if (px >= 0 && px < 16) {
                        int idx = (cy * 16 + px) * 3;
                        fb[idx] = 0;
                        fb[idx + 1] = 30;
                        fb[idx + 2] = 80; // Deep water fissure
                    }
                }
            }
        }
    }

    // Render Seals (Grey/white cute popping seal)
    for (int i = 0; i < MAX_SEALS; ++i) {
        if (!seals_[i].active) continue;
        if (seals_[i].z > 0.0f && seals_[i].z < 100.0f) {
            float t = (100.0f - seals_[i].z) / 100.0f;
            int sy = 4 + static_cast<int>(t * 10.0f);
            float road_w = 2.0f + (sy - 4.0f) * 1.0f;
            int sx = static_cast<int>(std::round(7.5f + seals_[i].lane * road_w));
            if (sx >= 0 && sx < 16 && sy >= 4 && sy < 16) {
                int idx = (sy * 16 + sx) * 3;
                fb[idx] = 120;
                fb[idx + 1] = 130;
                fb[idx + 2] = 140; // Seal grey
            }
        }
    }

    // Render Leaping Fish (Orange fish sparkling)
    for (int i = 0; i < MAX_FISH; ++i) {
        if (!fishes_[i].active) continue;
        if (fishes_[i].z > 0.0f && fishes_[i].z < 100.0f) {
            float t = (100.0f - fishes_[i].z) / 100.0f;
            int fy = 4 + static_cast<int>(t * 10.0f);
            float road_w = 2.0f + (fy - 4.0f) * 1.0f;
            int fx = static_cast<int>(std::round(7.5f + fishes_[i].lane * road_w));
            if (fx >= 0 && fx < 16 && fy >= 4 && fy < 16) {
                int idx = (fy * 16 + fx) * 3;
                fb[idx] = 255;
                fb[idx + 1] = 140;
                fb[idx + 2] = 0; // Orange fish
            }
        }
    }

    // Render Penguin (Penta: Tuxedo black & white with yellow beak)
    int py = is_jumping_ ? 11 : 13;
    float road_w = 2.0f + (13.0f - 4.0f) * 1.0f;
    int px = static_cast<int>(std::round(7.5f + penguin_lane_ * road_w));

    if (px >= 0 && px < 16 && py >= 0 && py < 16) {
        int idx = (py * 16 + px) * 3;
        if (trip_stun_timer_ > 0.0f) {
            // Spinning yellow stars when stunned
            fb[idx] = 255;
            fb[idx + 1] = 255;
            fb[idx + 2] = 0;
        } else {
            fb[idx] = 20;
            fb[idx + 1] = 20;
            fb[idx + 2] = 25; // Black penguin body
            // White belly
            if (py > 0) {
                int belly_idx = ((py - 1) * 16 + px) * 3;
                fb[belly_idx] = 255;
                fb[belly_idx + 1] = 255;
                fb[belly_idx + 2] = 255;
            }
        }
    }

    // HUD: Timer & Distance progress bar on row 0
    int time_bars = static_cast<int>((time_remaining_ / 45.0f) * 8.0f);
    for (int t = 0; t < time_bars && t < 8; ++t) {
        int idx = t * 3;
        fb[idx] = 0;
        fb[idx + 1] = 255;
        fb[idx + 2] = 0;
    }

    int dist_bars = static_cast<int>((1.0f - distance_remaining_ / 100.0f) * 7.0f);
    for (int d = 0; d < dist_bars && d < 7; ++d) {
        int idx = (15 - d) * 3;
        fb[idx] = 255;
        fb[idx + 1] = 100;
        fb[idx + 2] = 0;
    }
}

} // namespace arcade
