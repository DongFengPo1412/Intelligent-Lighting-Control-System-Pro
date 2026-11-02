#include "game_043_centipede.h"
#include <cmath>
#include <cstdlib>
#include <algorithm>

namespace arcade {

Game043Centipede::Game043Centipede()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(0),
      lives_(3),
      player_x_(7.5f),
      player_y_(14.0f),
      fire_cooldown_(0.0f),
      centipede_step_timer_(0.0f),
      centipede_step_interval_(0.14f),
      spider_spawn_timer_(4.0f) {
}

void Game043Centipede::Init() {
    Reset();
}

void Game043Centipede::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    lives_ = 3;
    player_x_ = 7.5f;
    player_y_ = 14.0f;
    fire_cooldown_ = 0.0f;
    centipede_step_timer_ = 0.0f;
    centipede_step_interval_ = 0.14f;
    spider_spawn_timer_ = 4.0f;

    for (int i = 0; i < MAX_BULLETS; ++i) {
        bullets_[i].active = false;
    }

    spider_.active = false;

    InitArena();
}

void Game043Centipede::InitArena() {
    // 1. Clear and spawn random mushroom field in middle rows (y = 2 to 10)
    for (int i = 0; i < MAX_MUSHROOMS; ++i) {
        mushrooms_[i].active = false;
    }

    // Pre-seeded mushrooms for consistent gameplay
    static const int seed_mushrooms[][2] = {
        {2, 3}, {7, 3}, {12, 4}, {4, 6}, {9, 6}, {14, 7},
        {1, 8}, {6, 9}, {11, 9}, {3, 11}, {8, 11}, {13, 12}
    };
    int num_seeds = sizeof(seed_mushrooms) / sizeof(seed_mushrooms[0]);
    for (int i = 0; i < num_seeds && i < MAX_MUSHROOMS; ++i) {
        mushrooms_[i].x = seed_mushrooms[i][0];
        mushrooms_[i].y = seed_mushrooms[i][1];
        mushrooms_[i].health = 2;
        mushrooms_[i].active = true;
    }

    // 2. Initialize 8-segment centipede along top row (y = 0)
    for (int i = 0; i < MAX_SEGMENTS; ++i) {
        if (i < 8) {
            segments_[i].x = static_cast<float>(7 - i); // Head at x=7, tail at x=0
            segments_[i].y = 0.0f;
            segments_[i].dir_x = 1; // Moving right
            segments_[i].is_head = (i == 0);
            segments_[i].active = true;
        } else {
            segments_[i].active = false;
        }
    }
}

int Game043Centipede::GetActiveSegmentCount() const {
    int count = 0;
    for (int i = 0; i < MAX_SEGMENTS; ++i) {
        if (segments_[i].active) count++;
    }
    return count;
}

void Game043Centipede::SpawnMushroom(int x, int y) {
    if (x < 0 || x >= 16 || y < 0 || y >= 16) return;

    // Check if mushroom already exists at location
    for (int i = 0; i < MAX_MUSHROOMS; ++i) {
        if (mushrooms_[i].active && mushrooms_[i].x == x && mushrooms_[i].y == y) {
            return;
        }
    }

    // Find free slot
    for (int i = 0; i < MAX_MUSHROOMS; ++i) {
        if (!mushrooms_[i].active) {
            mushrooms_[i].x = x;
            mushrooms_[i].y = y;
            mushrooms_[i].health = 2;
            mushrooms_[i].active = true;
            break;
        }
    }
}

void Game043Centipede::HitCentipedeSegment(int seg_idx) {
    if (seg_idx < 0 || seg_idx >= MAX_SEGMENTS || !segments_[seg_idx].active) return;

    segments_[seg_idx].active = false;
    int mx = static_cast<int>(std::round(segments_[seg_idx].x));
    int my = static_cast<int>(std::round(segments_[seg_idx].y));
    SpawnMushroom(mx, my);

    if (segments_[seg_idx].is_head) {
        score_ += 100;
    } else {
        score_ += 10;
    }

    // Fission: Next segment in line becomes a new head!
    if (seg_idx + 1 < MAX_SEGMENTS && segments_[seg_idx + 1].active) {
        segments_[seg_idx + 1].is_head = true;
    }

    if (score_ > high_score_) high_score_ = score_;

    if (GetActiveSegmentCount() == 0) {
        state_ = STATE_VICTORY;
        state_timer_ = 0.0f;
        score_ += 1000;
        if (score_ > high_score_) high_score_ = score_;
    }
}

void Game043Centipede::FireBullet() {
    if (fire_cooldown_ > 0.0f) return;

    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (!bullets_[i].active) {
            bullets_[i].x = player_x_;
            bullets_[i].y = player_y_ - 0.5f;
            bullets_[i].active = true;
            fire_cooldown_ = 0.2f;
            break;
        }
    }
}

void Game043Centipede::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    const float speed = 8.0f;

    if (buttons & KEY_LEFT) player_x_ -= speed * dt;
    if (buttons & KEY_RIGHT) player_x_ += speed * dt;
    if (buttons & KEY_UP) player_y_ -= speed * dt;
    if (buttons & KEY_DOWN) player_y_ += speed * dt;

    // Player zone constraint: bottom 5 rows (y: 11..15)
    player_x_ = std::max(0.0f, std::min(15.0f, player_x_));
    player_y_ = std::max(11.0f, std::min(15.0f, player_y_));

    // Fire laser (KEY_A)
    if (buttons & KEY_A) {
        FireBullet();
    }
}

void Game043Centipede::UpdateBullets(float dt) {
    const float bullet_speed = 18.0f;

    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (!bullets_[i].active) continue;

        bullets_[i].y -= bullet_speed * dt;
        if (bullets_[i].y < 0.0f) {
            bullets_[i].active = false;
        }
    }
}

void Game043Centipede::UpdateSpider(float dt) {
    if (!spider_.active) {
        spider_spawn_timer_ -= dt;
        if (spider_spawn_timer_ <= 0.0f) {
            spider_.active = true;
            spider_.x = (rand() % 2 == 0) ? 0.0f : 15.0f;
            spider_.y = 12.0f;
            spider_.vx = (spider_.x < 8.0f) ? 3.5f : -3.5f;
            spider_.vy = (rand() % 2 == 0) ? 2.5f : -2.5f;
            spider_spawn_timer_ = 6.0f;
        }
        return;
    }

    spider_.x += spider_.vx * dt;
    spider_.y += spider_.vy * dt;

    // Bounce vertically within player zone (y: 10..15)
    if (spider_.y <= 10.0f) {
        spider_.y = 10.0f;
        spider_.vy = fabsf(spider_.vy);
    } else if (spider_.y >= 15.0f) {
        spider_.y = 15.0f;
        spider_.vy = -fabsf(spider_.vy);
    }

    // Leave screen horizontally
    if (spider_.x < -1.0f || spider_.x > 16.0f) {
        spider_.active = false;
        spider_spawn_timer_ = 5.0f;
    }
}

void Game043Centipede::UpdateCentipede(float dt) {
    centipede_step_timer_ += dt;
    if (centipede_step_timer_ < centipede_step_interval_) return;
    centipede_step_timer_ -= centipede_step_interval_;

    for (int i = 0; i < MAX_SEGMENTS; ++i) {
        if (!segments_[i].active) continue;

        float next_x = segments_[i].x + segments_[i].dir_x;
        int check_x = static_cast<int>(std::round(next_x));
        int cur_y = static_cast<int>(std::round(segments_[i].y));

        bool hit_obstacle = false;

        // Check screen edge
        if (next_x < 0.0f || next_x > 15.0f) {
            hit_obstacle = true;
        } else {
            // Check mushroom collision
            for (int m = 0; m < MAX_MUSHROOMS; ++m) {
                if (mushrooms_[m].active && mushrooms_[m].x == check_x && mushrooms_[m].y == cur_y) {
                    hit_obstacle = true;
                    break;
                }
            }
        }

        if (hit_obstacle) {
            // Drop down one row and reverse horizontal direction
            segments_[i].y += 1.0f;
            if (segments_[i].y >= 15.5f) {
                segments_[i].y = 11.0f; // Loop back up to top of player zone
            }
            segments_[i].dir_x = -segments_[i].dir_x;
        } else {
            segments_[i].x = next_x;
        }
    }
}

void Game043Centipede::CheckCollisions() {
    // 1. Bullets vs Mushrooms
    for (int b = 0; b < MAX_BULLETS; ++b) {
        if (!bullets_[b].active) continue;

        for (int m = 0; m < MAX_MUSHROOMS; ++m) {
            if (!mushrooms_[m].active) continue;

            if (fabsf(bullets_[b].x - mushrooms_[m].x) <= 0.8f &&
                fabsf(bullets_[b].y - mushrooms_[m].y) <= 0.8f) {
                bullets_[b].active = false;
                mushrooms_[m].health--;
                if (mushrooms_[m].health <= 0) {
                    mushrooms_[m].active = false;
                    score_ += 5;
                    if (score_ > high_score_) high_score_ = score_;
                }
                break;
            }
        }
    }

    // 2. Bullets vs Centipede Segments
    for (int b = 0; b < MAX_BULLETS; ++b) {
        if (!bullets_[b].active) continue;

        for (int s = 0; s < MAX_SEGMENTS; ++s) {
            if (!segments_[s].active) continue;

            if (fabsf(bullets_[b].x - segments_[s].x) <= 0.85f &&
                fabsf(bullets_[b].y - segments_[s].y) <= 0.85f) {
                bullets_[b].active = false;
                HitCentipedeSegment(s);
                break;
            }
        }
    }

    // 3. Bullets vs Spider
    if (spider_.active) {
        for (int b = 0; b < MAX_BULLETS; ++b) {
            if (!bullets_[b].active) continue;

            if (fabsf(bullets_[b].x - spider_.x) <= 1.0f &&
                fabsf(bullets_[b].y - spider_.y) <= 1.0f) {
                bullets_[b].active = false;
                spider_.active = false;
                score_ += 300;
                if (score_ > high_score_) high_score_ = score_;
                break;
            }
        }
    }

    // 4. Centipede or Spider vs Player -> Player Death
    for (int s = 0; s < MAX_SEGMENTS; ++s) {
        if (!segments_[s].active) continue;

        if (fabsf(player_x_ - segments_[s].x) <= 0.85f &&
            fabsf(player_y_ - segments_[s].y) <= 0.85f) {
            lives_--;
            state_ = STATE_DEAD;
            state_timer_ = 0.0f;
            return;
        }
    }

    if (spider_.active) {
        if (fabsf(player_x_ - spider_.x) <= 0.9f &&
            fabsf(player_y_ - spider_.y) <= 0.9f) {
            lives_--;
            state_ = STATE_DEAD;
            state_timer_ = 0.0f;
            return;
        }
    }
}

void Game043Centipede::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;
    if (fire_cooldown_ > 0.0f) fire_cooldown_ -= dt;

    if (state_ == STATE_START) {
        if (buttons & (KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_DEAD) {
        if (state_timer_ >= 1.5f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                state_timer_ = 0.0f;
                player_x_ = 7.5f;
                player_y_ = 14.0f;
            }
        }
        return;
    }

    if (state_ == STATE_VICTORY) {
        if (state_timer_ >= 2.5f && (buttons & (KEY_A | KEY_B))) {
            Reset();
        }
        return;
    }

    UpdatePlayer(dt, buttons, prev_buttons);
    UpdateBullets(dt);
    UpdateSpider(dt);
    UpdateCentipede(dt);
    CheckCollisions();
}

void Game043Centipede::Render(uint8_t* fb) {
    // Pitch Black Arcade Space (#000000)
    for (int i = 0; i < 256 * 3; ++i) {
        fb[i] = 0;
    }

    // 1. Draw Mushrooms (Emerald Green or Brown/Purple)
    for (int i = 0; i < MAX_MUSHROOMS; ++i) {
        if (!mushrooms_[i].active) continue;

        int mx = mushrooms_[i].x;
        int my = mushrooms_[i].y;
        if (mx >= 0 && mx < 16 && my >= 0 && my < 16) {
            int idx = (my * 16 + mx) * 3;
            if (mushrooms_[i].health == 2) {
                fb[idx + 0] = 39;  fb[idx + 1] = 174; fb[idx + 2] = 96;  // Fresh Green
            } else {
                fb[idx + 0] = 142; fb[idx + 1] = 68;  fb[idx + 2] = 173; // Damaged Purple
            }
        }
    }

    // 2. Draw Centipede Segments
    for (int i = 0; i < MAX_SEGMENTS; ++i) {
        if (!segments_[i].active) continue;

        int sx = static_cast<int>(std::round(segments_[i].x));
        int sy = static_cast<int>(std::round(segments_[i].y));
        if (sx >= 0 && sx < 16 && sy >= 0 && sy < 16) {
            int idx = (sy * 16 + sx) * 3;
            if (segments_[i].is_head) {
                // Centipede Head: Fiery Scarlet / Orange
                fb[idx + 0] = 231; fb[idx + 1] = 76; fb[idx + 2] = 60;
            } else {
                // Centipede Body: Bright Lime
                fb[idx + 0] = 46; fb[idx + 1] = 204; fb[idx + 2] = 113;
            }
        }
    }

    // 3. Draw Spider
    if (spider_.active) {
        int spx = static_cast<int>(std::round(spider_.x));
        int spy = static_cast<int>(std::round(spider_.y));
        if (spx >= 0 && spx < 16 && spy >= 0 && spy < 16) {
            int idx = (spy * 16 + spx) * 3;
            fb[idx + 0] = 241; fb[idx + 1] = 196; fb[idx + 2] = 15; // Golden Yellow Spider
        }
    }

    // 4. Draw Bullets (Cyan Sparks)
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (!bullets_[i].active) continue;

        int bx = static_cast<int>(std::round(bullets_[i].x));
        int by = static_cast<int>(std::round(bullets_[i].y));
        if (bx >= 0 && bx < 16 && by >= 0 && by < 16) {
            int idx = (by * 16 + bx) * 3;
            fb[idx + 0] = 255; fb[idx + 1] = 255; fb[idx + 2] = 255; // White beam
        }
    }

    // 5. Draw Player Bug Blaster (Cyan #00FFFF)
    int px = static_cast<int>(std::round(player_x_));
    int py = static_cast<int>(std::round(player_y_));
    if (px >= 0 && px < 16 && py >= 0 && py < 16) {
        int idx = (py * 16 + px) * 3;
        fb[idx + 0] = 0; fb[idx + 1] = 255; fb[idx + 2] = 255;
    }
}

} // namespace arcade
