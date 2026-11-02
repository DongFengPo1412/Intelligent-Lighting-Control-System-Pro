#include "game_037_sprint_racer.h"
#include <cmath>
#include <cstdlib>
#include <algorithm>

namespace arcade {

static constexpr float PI = 3.1415926535f;

Game037SprintRacer::Game037SprintRacer()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(0),
      race_time_(0.0f),
      time_limit_(60.0f) {
}

void Game037SprintRacer::Init() {
    Reset();
}

void Game037SprintRacer::Reset() {
    state_ = STATE_RACING;
    state_timer_ = 0.0f;
    score_ = 0;
    race_time_ = 0.0f;
    time_limit_ = 60.0f;

    InitTrack();

    // Player starts on bottom straight at Finish Line facing East (angle = 0)
    player_.x = 8.0f;
    player_.y = 13.0f;
    player_.angle = 0.0f;
    player_.speed = 0.0f;
    player_.next_checkpoint = 1;
    player_.laps = 0;
    player_.spin_timer = 0.0f;

    // AI rival starts beside player
    ai_.x = 7.0f;
    ai_.y = 12.0f;
    ai_.angle = 0.0f;
    ai_.speed = 0.0f;
    ai_.next_checkpoint = 1;
    ai_.laps = 0;
    ai_.spin_timer = 0.0f;
}

void Game037SprintRacer::InitTrack() {
    // 0: Asphalt road, 1: Wall/Infield grass barrier
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            // Outer boundary
            if (x == 0 || x == 15 || y == 0 || y == 15) {
                track_map_[y][x] = 1;
            }
            // Infield island
            else if (x >= 5 && x <= 10 && y >= 5 && y <= 10) {
                track_map_[y][x] = 1;
            } else {
                track_map_[y][x] = 0; // Driveable asphalt
            }
        }
    }

    // Place 3 Oil Slicks at tricky corners
    oil_slicks_[0].x = 12.5f; oil_slicks_[0].y = 12.5f; oil_slicks_[0].active = true;
    oil_slicks_[1].x = 12.5f; oil_slicks_[1].y = 2.5f;  oil_slicks_[1].active = true;
    oil_slicks_[2].x = 2.5f;  oil_slicks_[2].y = 2.5f;  oil_slicks_[2].active = true;
}

bool Game037SprintRacer::IsOnTrack(float x, float y) const {
    int ix = static_cast<int>(std::round(x));
    int iy = static_cast<int>(std::round(y));
    if (ix < 0 || ix >= 16 || iy < 0 || iy >= 16) return false;
    return track_map_[iy][ix] == 0;
}

void Game037SprintRacer::UpdatePlayer(float dt, uint32_t buttons) {
    if (player_.spin_timer > 0.0f) {
        player_.spin_timer -= dt;
        player_.angle += 14.0f * dt; // Wild spinout
        player_.speed *= 0.95f;
    } else {
        // Steering
        const float steer_speed = 3.8f;
        if (buttons & KEY_LEFT)  player_.angle -= steer_speed * dt;
        if (buttons & KEY_RIGHT) player_.angle += steer_speed * dt;

        // Normalize angle
        while (player_.angle < 0.0f) player_.angle += 2.0f * PI;
        while (player_.angle >= 2.0f * PI) player_.angle -= 2.0f * PI;

        // Gas (KEY_A) and Brake (KEY_B)
        if (buttons & KEY_A) {
            player_.speed = std::min(7.5f, player_.speed + 12.0f * dt);
        } else if (buttons & KEY_B) {
            player_.speed = std::max(0.0f, player_.speed - 16.0f * dt);
        } else {
            player_.speed = std::max(0.0f, player_.speed - 3.5f * dt); // Rolling friction
        }
    }

    // Displace
    float next_x = player_.x + cosf(player_.angle) * player_.speed * dt;
    float next_y = player_.y + sinf(player_.angle) * player_.speed * dt;

    if (IsOnTrack(next_x, next_y)) {
        player_.x = next_x;
        player_.y = next_y;
    } else {
        // Barrier impact bounce
        player_.speed = -player_.speed * 0.35f;
    }

    CheckCheckpoints(player_, true);
    CheckOilCollisions(player_);
}

void Game037SprintRacer::UpdateAI(float dt) {
    if (ai_.spin_timer > 0.0f) {
        ai_.spin_timer -= dt;
        ai_.angle += 12.0f * dt;
        ai_.speed *= 0.95f;
    } else {
        // Target current checkpoint center
        float target_x = 8.0f, target_y = 12.5f;
        if (ai_.next_checkpoint == 1) { target_x = 12.5f; target_y = 8.0f; }
        else if (ai_.next_checkpoint == 2) { target_x = 8.0f; target_y = 2.5f; }
        else if (ai_.next_checkpoint == 3) { target_x = 2.5f; target_y = 8.0f; }

        float target_angle = atan2f(target_y - ai_.y, target_x - ai_.x);
        float diff = target_angle - ai_.angle;
        while (diff < -PI) diff += 2.0f * PI;
        while (diff > PI) diff -= 2.0f * PI;

        ai_.angle += diff * 4.0f * dt;
        ai_.speed = 5.2f; // Steady pace
    }

    float next_x = ai_.x + cosf(ai_.angle) * ai_.speed * dt;
    float next_y = ai_.y + sinf(ai_.angle) * ai_.speed * dt;

    if (IsOnTrack(next_x, next_y)) {
        ai_.x = next_x;
        ai_.y = next_y;
    } else {
        ai_.speed = 1.0f;
    }

    CheckCheckpoints(ai_, false);
    CheckOilCollisions(ai_);
}

void Game037SprintRacer::CheckCheckpoints(Car& car, bool is_player) {
    // CP 0: Start/Finish (x=8, y=11..14)
    // CP 1: Turn 1 (x=11..14, y=8)
    // CP 2: Back Straight (x=8, y=1..4)
    // CP 3: Turn 2 (x=1..4, y=8)

    if (car.next_checkpoint == 1) {
        if (car.x >= 11.0f && car.y >= 6.0f && car.y <= 10.0f) {
            car.next_checkpoint = 2;
        }
    } else if (car.next_checkpoint == 2) {
        if (car.y <= 4.0f && car.x >= 6.0f && car.x <= 10.0f) {
            car.next_checkpoint = 3;
        }
    } else if (car.next_checkpoint == 3) {
        if (car.x <= 4.0f && car.y >= 6.0f && car.y <= 10.0f) {
            car.next_checkpoint = 0;
        }
    } else if (car.next_checkpoint == 0) {
        if (car.y >= 11.0f && car.x >= 7.0f && car.x <= 10.0f) {
            car.laps++;
            car.next_checkpoint = 1;

            if (is_player) {
                score_ += 500;
                if (score_ > high_score_) high_score_ = score_;

                if (car.laps >= MAX_LAPS) {
                    state_ = STATE_VICTORY;
                    state_timer_ = 0.0f;
                    int time_bonus = static_cast<int>(std::max(0.0f, time_limit_ - race_time_)) * 20;
                    score_ += 1000 + time_bonus;
                    if (score_ > high_score_) high_score_ = score_;
                }
            }
        }
    }
}

void Game037SprintRacer::CheckOilCollisions(Car& car) {
    for (int i = 0; i < MAX_OIL_SLICKS; ++i) {
        if (oil_slicks_[i].active) {
            float dx = car.x - oil_slicks_[i].x;
            float dy = car.y - oil_slicks_[i].y;
            if (dx * dx + dy * dy <= 1.0f) {
                if (car.spin_timer <= 0.0f) {
                    car.spin_timer = 0.75f; // Spinout!
                }
            }
        }
    }
}

void Game037SprintRacer::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_START) {
        if (buttons & (KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_VICTORY || state_ == STATE_TIMEOUT) {
        if (state_timer_ >= 2.0f && (buttons & (KEY_A | KEY_B))) {
            Reset();
        }
        return;
    }

    race_time_ += dt;
    if (race_time_ >= time_limit_) {
        state_ = STATE_TIMEOUT;
        state_timer_ = 0.0f;
        return;
    }

    UpdatePlayer(dt, buttons);
    UpdateAI(dt);
}

void Game037SprintRacer::Render(uint8_t* fb) {
    // 1. Draw Track & Infield
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            if (track_map_[y][x] == 1) {
                // Outer wall or infield grass
                if (x == 0 || x == 15 || y == 0 || y == 15) {
                    fb[idx + 0] = 120; fb[idx + 1] = 120; fb[idx + 2] = 120; // Guard rail
                } else {
                    fb[idx + 0] = 39; fb[idx + 1] = 174; fb[idx + 2] = 96;  // Grass Infield
                }
            } else {
                // Asphalt track
                fb[idx + 0] = 35; fb[idx + 1] = 40; fb[idx + 2] = 45;
            }
        }
    }

    // 2. Start/Finish Line (Checkered pattern at x=8, y=11..14)
    for (int y = 11; y <= 14; ++y) {
        int idx = (y * 16 + 8) * 3;
        if (y % 2 == 0) {
            fb[idx + 0] = 255; fb[idx + 1] = 255; fb[idx + 2] = 255;
        } else {
            fb[idx + 0] = 20; fb[idx + 1] = 20; fb[idx + 2] = 20;
        }
    }

    // 3. Oil Slicks (Pitch Black with Purple sheen)
    for (int i = 0; i < MAX_OIL_SLICKS; ++i) {
        int ox = static_cast<int>(std::round(oil_slicks_[i].x));
        int oy = static_cast<int>(std::round(oil_slicks_[i].y));
        if (ox >= 0 && ox < 16 && oy >= 0 && oy < 16) {
            int idx = (oy * 16 + ox) * 3;
            fb[idx + 0] = 10; fb[idx + 1] = 10; fb[idx + 2] = 20;
        }
    }

    // 4. AI Rival Car (Pure White #ECF0F1)
    int ax = static_cast<int>(std::round(ai_.x));
    int ay = static_cast<int>(std::round(ai_.y));
    if (ax >= 0 && ax < 16 && ay >= 0 && ay < 16) {
        int idx = (ay * 16 + ax) * 3;
        fb[idx + 0] = 236; fb[idx + 1] = 240; fb[idx + 2] = 241;
    }

    // 5. Player Sprint Car (Bright Racing Yellow #F1C40F or Amber, with Red Tail)
    int px = static_cast<int>(std::round(player_.x));
    int py = static_cast<int>(std::round(player_.y));
    if (px >= 0 && px < 16 && py >= 0 && py < 16) {
        int idx = (py * 16 + px) * 3;
        fb[idx + 0] = 241; fb[idx + 1] = 196; fb[idx + 2] = 15; // Golden body
    }

    // 6. HUD on top row: Lap count dots
    for (int l = 0; l < player_.laps && l < MAX_LAPS; ++l) {
        int idx = (0 * 16 + (l + 1)) * 3;
        fb[idx + 0] = 46; fb[idx + 1] = 204; fb[idx + 2] = 113; // Green lap dot
    }

    // Victory celebration flash
    if (state_ == STATE_VICTORY) {
        if (static_cast<int>(state_timer_ * 6.0f) % 2 == 0) {
            for (int x = 0; x < 16; ++x) {
                fb[(0 * 16 + x) * 3 + 0] = 241;
                fb[(0 * 16 + x) * 3 + 1] = 196;
                fb[(0 * 16 + x) * 3 + 2] = 15;
            }
        }
    }
}

} // namespace arcade
