#include "game_032_crossy_road.h"
#include <cmath>
#include <cstdlib>
#include <algorithm>

namespace arcade {

Game032CrossyRoad::Game032CrossyRoad()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(0),
      max_distance_(0),
      player_x_(7.0f),
      player_world_y_(0),
      camera_world_y_(0),
      idle_timer_(0.0f),
      eagle_striking_(false),
      eagle_y_(0.0f) {
}

void Game032CrossyRoad::Init() {
    Reset();
}

void Game032CrossyRoad::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    max_distance_ = 0;
    player_x_ = 7.0f;
    player_world_y_ = 0;
    camera_world_y_ = 0;
    idle_timer_ = 0.0f;
    eagle_striking_ = false;
    eagle_y_ = 0.0f;

    for (int i = 0; i < MAX_OBSTACLES; ++i) {
        obstacles_[i].active = false;
    }

    InitWorld();
}

void Game032CrossyRoad::GenerateLane(int lane_idx, int world_y) {
    Lane& l = lanes_[lane_idx];
    l.world_y = world_y;
    l.spawn_timer = 0.0f;
    l.train_warning = false;
    l.train_passing = false;
    l.train_timer = 0.0f;
    l.train_x = -10.0f;

    if (world_y <= 2) {
        // Safe starting grass
        l.type = LANE_GRASS;
        l.speed = 0.0f;
        l.spawn_interval = 999.0f;
        return;
    }

    // Procedural generation pattern
    int pattern = (world_y % 10);
    if (pattern == 3 || pattern == 7) {
        // Rail track
        l.type = LANE_RAIL;
        l.speed = 22.0f;
        l.spawn_interval = 999.0f;
        l.train_timer = 2.0f + static_cast<float>(rand() % 30) / 10.0f;
    } else if (pattern == 4 || pattern == 5 || pattern == 8) {
        // River with logs
        l.type = LANE_RIVER;
        bool to_right = (world_y % 2 == 0);
        l.speed = (to_right ? 1.0f : -1.0f) * (2.2f + static_cast<float>(rand() % 15) / 10.0f);
        l.spawn_interval = 2.2f;
    } else if (pattern == 0 || pattern == 9) {
        // Safe rest grass
        l.type = LANE_GRASS;
        l.speed = 0.0f;
        l.spawn_interval = 999.0f;
    } else {
        // Road with cars
        l.type = LANE_ROAD;
        bool to_right = (world_y % 2 == 0);
        l.speed = (to_right ? 1.0f : -1.0f) * (3.5f + static_cast<float>(rand() % 25) / 10.0f);
        l.spawn_interval = 1.8f;
    }
}

void Game032CrossyRoad::InitWorld() {
    for (int i = 0; i < NUM_LANES; ++i) {
        GenerateLane(i, i);
    }
}

void Game032CrossyRoad::TriggerEagleStrike() {
    eagle_striking_ = true;
    eagle_y_ = 0.0f;
}

void Game032CrossyRoad::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_START) {
        if (buttons & (KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_DEAD) {
        if (state_timer_ >= 1.5f && (buttons & (KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT))) {
            Reset();
        }
        return;
    }

    // 1. Player Hopping Input
    if ((buttons & KEY_UP) && !(prev_buttons & KEY_UP)) {
        player_world_y_++;
        idle_timer_ = 0.0f; // Reset eagle swoop!
        if (player_world_y_ > max_distance_) {
            max_distance_ = player_world_y_;
            score_ = max_distance_ * 10;
            if (score_ > high_score_) high_score_ = score_;
        }
    } else if ((buttons & KEY_DOWN) && !(prev_buttons & KEY_DOWN)) {
        if (player_world_y_ > camera_world_y_) {
            player_world_y_--;
        }
    } else if ((buttons & KEY_LEFT) && !(prev_buttons & KEY_LEFT)) {
        player_x_ = std::max(0.0f, player_x_ - 1.0f);
    } else if ((buttons & KEY_RIGHT) && !(prev_buttons & KEY_RIGHT)) {
        player_x_ = std::min(15.0f, player_x_ + 1.0f);
    }

    // Camera follow player smoothly
    int target_cam_y = player_world_y_ - 8;
    if (target_cam_y > camera_world_y_) {
        camera_world_y_ = target_cam_y;
    }

    // Re-cycle lanes ahead of camera
    for (int i = 0; i < NUM_LANES; ++i) {
        if (lanes_[i].world_y < camera_world_y_) {
            // Find max world_y currently active
            int highest_y = camera_world_y_;
            for (int j = 0; j < NUM_LANES; ++j) {
                if (lanes_[j].world_y > highest_y) highest_y = lanes_[j].world_y;
            }
            GenerateLane(i, highest_y + 1);
        }
    }

    UpdateLanesAndObstacles(dt);
    CheckEagle(dt);
    CheckCollisions();
}

void Game032CrossyRoad::UpdateLanesAndObstacles(float dt) {
    // 1. Update Lane Spawners
    for (int i = 0; i < NUM_LANES; ++i) {
        Lane& l = lanes_[i];

        if (l.type == LANE_ROAD || l.type == LANE_RIVER) {
            l.spawn_timer += dt;
            if (l.spawn_timer >= l.spawn_interval) {
                l.spawn_timer = 0.0f;

                // Spawn obstacle
                for (int ob = 0; ob < MAX_OBSTACLES; ++ob) {
                    if (!obstacles_[ob].active) {
                        obstacles_[ob].active = true;
                        obstacles_[ob].lane_idx = i;
                        obstacles_[ob].is_log = (l.type == LANE_RIVER);
                        obstacles_[ob].length = (l.type == LANE_RIVER) ? 3.5f : 2.2f;
                        obstacles_[ob].x = (l.speed > 0.0f) ? -3.0f : 18.0f;
                        break;
                    }
                }
            }
        } else if (l.type == LANE_RAIL) {
            if (!l.train_warning && !l.train_passing) {
                l.train_timer -= dt;
                if (l.train_timer <= 0.0f) {
                    l.train_warning = true;
                    l.train_timer = 0.8f; // Warning duration
                }
            } else if (l.train_warning) {
                l.train_timer -= dt;
                if (l.train_timer <= 0.0f) {
                    l.train_warning = false;
                    l.train_passing = true;
                    l.train_x = -8.0f; // Zoom in from left
                }
            } else if (l.train_passing) {
                l.train_x += l.speed * dt;
                if (l.train_x > 24.0f) {
                    l.train_passing = false;
                    l.train_timer = 3.5f + static_cast<float>(rand() % 30) / 10.0f;
                }
            }
        }
    }

    // 2. Update Obstacle Movements
    for (int ob = 0; ob < MAX_OBSTACLES; ++ob) {
        if (!obstacles_[ob].active) continue;

        int l_idx = obstacles_[ob].lane_idx;
        Lane& l = lanes_[l_idx];

        obstacles_[ob].x += l.speed * dt;

        // Cull out of bounds
        if ((l.speed > 0.0f && obstacles_[ob].x > 20.0f) ||
            (l.speed < 0.0f && obstacles_[ob].x < -5.0f)) {
            obstacles_[ob].active = false;
        }
    }
}

void Game032CrossyRoad::CheckEagle(float dt) {
    idle_timer_ += dt;

    if (!eagle_striking_ && idle_timer_ >= 3.5f) {
        TriggerEagleStrike();
    }

    if (eagle_striking_) {
        eagle_y_ += 28.0f * dt; // High speed downward dive!
        int player_screen_y = 15 - (player_world_y_ - camera_world_y_);
        if (eagle_y_ >= static_cast<float>(player_screen_y)) {
            // Eagle snatches player!
            state_ = STATE_DEAD;
            state_timer_ = 0.0f;
            eagle_striking_ = false;
        }
    }
}

void Game032CrossyRoad::CheckCollisions() {
    if (state_ != STATE_PLAYING) return;

    // Find current lane
    Lane* cur_lane = nullptr;
    int cur_lane_idx = -1;
    for (int i = 0; i < NUM_LANES; ++i) {
        if (lanes_[i].world_y == player_world_y_) {
            cur_lane = &lanes_[i];
            cur_lane_idx = i;
            break;
        }
    }

    if (!cur_lane) return;

    // 1. Road Car collision
    if (cur_lane->type == LANE_ROAD) {
        for (int ob = 0; ob < MAX_OBSTACLES; ++ob) {
            if (obstacles_[ob].active && obstacles_[ob].lane_idx == cur_lane_idx) {
                float ox = obstacles_[ob].x;
                float o_len = obstacles_[ob].length;
                if (player_x_ >= ox - 0.4f && player_x_ <= ox + o_len + 0.4f) {
                    // Splat by car!
                    state_ = STATE_DEAD;
                    state_timer_ = 0.0f;
                    return;
                }
            }
        }
    }

    // 2. River & Log physics
    if (cur_lane->type == LANE_RIVER) {
        bool on_log = false;
        for (int ob = 0; ob < MAX_OBSTACLES; ++ob) {
            if (obstacles_[ob].active && obstacles_[ob].lane_idx == cur_lane_idx) {
                float ox = obstacles_[ob].x;
                float o_len = obstacles_[ob].length;
                if (player_x_ >= ox - 0.3f && player_x_ <= ox + o_len + 0.3f) {
                    on_log = true;
                    // Drift with log
                    player_x_ += cur_lane->speed * (1.0f / 30.0f);
                    break;
                }
            }
        }

        if (!on_log || player_x_ < 0.0f || player_x_ > 15.0f) {
            // Drown in water!
            state_ = STATE_DEAD;
            state_timer_ = 0.0f;
            return;
        }
    }

    // 3. Train collision
    if (cur_lane->type == LANE_RAIL && cur_lane->train_passing) {
        if (player_x_ >= cur_lane->train_x - 0.5f && player_x_ <= cur_lane->train_x + 8.0f) {
            // Smashed by express train!
            state_ = STATE_DEAD;
            state_timer_ = 0.0f;
            return;
        }
    }
}

void Game032CrossyRoad::Render(uint8_t* fb) {
    // 1. Render all 16 rows from bottom to top
    for (int screen_y = 0; screen_y < 16; ++screen_y) {
        int world_y = camera_world_y_ + (15 - screen_y);

        Lane* l = nullptr;
        int l_idx = -1;
        for (int i = 0; i < NUM_LANES; ++i) {
            if (lanes_[i].world_y == world_y) {
                l = &lanes_[i];
                l_idx = i;
                break;
            }
        }

        // Default background grass
        uint8_t bg_r = 39, bg_g = 174, bg_b = 96;
        if (l) {
            if (l->type == LANE_ROAD) {
                bg_r = 44; bg_g = 62; bg_b = 80; // Dark asphalt
            } else if (l->type == LANE_RIVER) {
                bg_r = 41; bg_g = 128; bg_b = 185; // Blue River
            } else if (l->type == LANE_RAIL) {
                bg_r = 90; bg_g = 95; bg_b = 100; // Grey track
            }
        }

        for (int x = 0; x < 16; ++x) {
            int idx = (screen_y * 16 + x) * 3;
            fb[idx + 0] = bg_r;
            fb[idx + 1] = bg_g;
            fb[idx + 2] = bg_b;
        }

        if (!l) continue;

        // Render Rail warning light or Train
        if (l->type == LANE_RAIL) {
            if (l->train_warning) {
                // Red flashing light on left and right borders
                bool blink = (static_cast<int>(state_timer_ * 10.0f) % 2 == 0);
                if (blink) {
                    fb[(screen_y * 16 + 0) * 3 + 0] = 255;
                    fb[(screen_y * 16 + 0) * 3 + 1] = 0;
                    fb[(screen_y * 16 + 0) * 3 + 2] = 0;

                    fb[(screen_y * 16 + 15) * 3 + 0] = 255;
                    fb[(screen_y * 16 + 15) * 3 + 1] = 0;
                    fb[(screen_y * 16 + 15) * 3 + 2] = 0;
                }
            } else if (l->train_passing) {
                int tx_start = static_cast<int>(l->train_x);
                for (int tx = tx_start; tx < tx_start + 7; ++tx) {
                    if (tx >= 0 && tx < 16) {
                        int idx = (screen_y * 16 + tx) * 3;
                        fb[idx + 0] = 231; fb[idx + 1] = 76; fb[idx + 2] = 60; // Crimson Train
                    }
                }
            }
        }

        // Render Obstacles (Cars / Logs) on this lane
        for (int ob = 0; ob < MAX_OBSTACLES; ++ob) {
            if (obstacles_[ob].active && obstacles_[ob].lane_idx == l_idx) {
                int ox_start = static_cast<int>(obstacles_[ob].x);
                int ox_end = ox_start + static_cast<int>(obstacles_[ob].length);

                for (int x = ox_start; x < ox_end; ++x) {
                    if (x >= 0 && x < 16) {
                        int idx = (screen_y * 16 + x) * 3;
                        if (obstacles_[ob].is_log) {
                            // Wood brown log
                            fb[idx + 0] = 160; fb[idx + 1] = 82; fb[idx + 2] = 45;
                        } else {
                            // Bright vehicle (Yellow/Amber)
                            fb[idx + 0] = 241; fb[idx + 1] = 196; fb[idx + 2] = 15;
                        }
                    }
                }
            }
        }
    }

    // 2. Render Player (Crossy Chicken: White Body with Red Comb)
    int player_screen_y = 15 - (player_world_y_ - camera_world_y_);
    int px = static_cast<int>(std::round(player_x_));

    if (player_screen_y >= 0 && player_screen_y < 16 && px >= 0 && px < 16) {
        int idx = (player_screen_y * 16 + px) * 3;
        if (state_ == STATE_DEAD) {
            // Flattened splat red
            fb[idx + 0] = 231; fb[idx + 1] = 76; fb[idx + 2] = 60;
        } else {
            // White Chicken
            fb[idx + 0] = 250; fb[idx + 1] = 250; fb[idx + 2] = 250;
            // Red Comb on top pixel if available
            if (player_screen_y > 0) {
                int comb_idx = ((player_screen_y - 1) * 16 + px) * 3;
                fb[comb_idx + 0] = 231; fb[comb_idx + 1] = 76; fb[comb_idx + 2] = 60;
            }
        }
    }

    // 3. Render Diving Eagle
    if (eagle_striking_) {
        int ey = static_cast<int>(eagle_y_);
        if (ey >= 0 && ey < 16 && px >= 0 && px < 16) {
            int e_idx = (ey * 16 + px) * 3;
            fb[e_idx + 0] = 80; fb[e_idx + 1] = 40; fb[e_idx + 2] = 20; // Dark Eagle
        }
    }
}

} // namespace arcade
