#include "game_057_wonderboy.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game057WonderBoy::Game057WonderBoy()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(3000),
      lives_(3),
      player_x_(2.0f),
      player_y_(13.0f),
      player_vx_(0.0f),
      player_vy_(0.0f),
      player_facing_(1),
      is_jumping_(false),
      vitality_(14),
      vitality_timer_(0.0f),
      has_skateboard_(false),
      has_fairy_(false),
      fairy_timer_(0.0f),
      stage_progress_(0.0f),
      scroll_speed_(6.0f) {
}

void Game057WonderBoy::Init() {
    Reset();
}

void Game057WonderBoy::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    lives_ = 3;
    InitStage();
}

void Game057WonderBoy::InitStage() {
    player_x_ = 2.0f;
    player_y_ = 13.0f;
    player_vx_ = 0.0f;
    player_vy_ = 0.0f;
    player_facing_ = 1;
    is_jumping_ = false;
    vitality_ = 14;
    vitality_timer_ = 0.0f;
    has_skateboard_ = false;
    has_fairy_ = false;
    fairy_timer_ = 0.0f;
    stage_progress_ = 0.0f;

    for (int i = 0; i < MAX_AXES; ++i) axes_[i].active = false;

    // Monsters drifting left with terrain
    monsters_[0] = {12.0f, 13.0f, -2.0f, 0, 1, true};  // Snail
    monsters_[1] = {18.0f, 13.0f, -2.5f, 1, 1, true};  // Octopus
    monsters_[2] = {26.0f, 13.0f, -3.0f, 2, 1, true};  // Rolling boulder
    monsters_[3] = {34.0f, 13.0f, -2.0f, 0, 1, true};

    // Fruits & Eggs
    fruits_[0] = {8.0f, 12.0f, 0, true};   // Banana
    fruits_[1] = {15.0f, 12.0f, 2, true};  // Skateboard Egg!
    fruits_[2] = {22.0f, 12.0f, 1, true};  // Apple
}

void Game057WonderBoy::ThrowAxe() {
    for (int i = 0; i < MAX_AXES; ++i) {
        if (!axes_[i].active) {
            axes_[i].active = true;
            axes_[i].x = player_x_ + (player_facing_ > 0 ? 1.0f : -1.0f);
            axes_[i].y = player_y_ - 0.5f;
            axes_[i].vx = player_facing_ * 10.0f;
            axes_[i].vy = -7.0f; // High parabolic arc
            break;
        }
    }
}

void Game057WonderBoy::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_DEAD) {
        if (state_timer_ > 1.5f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                state_timer_ = 0.0f;
                InitStage();
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

    // Vitality depletion timer
    vitality_timer_ += dt;
    if (vitality_timer_ >= 1.2f) {
        vitality_timer_ = 0.0f;
        vitality_--;
        if (vitality_ <= 0) {
            vitality_ = 0;
            lives_--;
            state_ = STATE_DEAD;
            state_timer_ = 0.0f;
            return;
        }
    }

    // Fairy invincibility timer
    if (has_fairy_) {
        fairy_timer_ -= dt;
        if (fairy_timer_ <= 0.0f) {
            has_fairy_ = false;
        }
    }

    UpdatePlayer(dt, buttons, prev_buttons);
    UpdateAxes(dt);
    UpdateMonsters(dt);
    CheckCollisions();

    // Check Stage Victory
    if (stage_progress_ >= 50.0f) {
        state_ = STATE_VICTORY;
        state_timer_ = 0.0f;
        score_ += 1500 + vitality_ * 50;
        if (score_ > high_score_) high_score_ = score_;
    }
}

void Game057WonderBoy::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    float move_speed = has_skateboard_ ? 9.0f : 6.0f;

    if (has_skateboard_) {
        // Skateboard moves forward with forward momentum
        player_vx_ = move_speed;
        player_facing_ = 1;
        if (buttons & BUTTON_LEFT)  player_vx_ = move_speed * 0.4f; // braking drag
        if (buttons & BUTTON_RIGHT) player_vx_ = move_speed * 1.3f; // turbo glide
    } else {
        player_vx_ = 0.0f;
        if (buttons & BUTTON_LEFT)  { player_vx_ = -move_speed; player_facing_ = -1; }
        if (buttons & BUTTON_RIGHT) { player_vx_ = move_speed;  player_facing_ = 1; }
    }

    player_x_ += player_vx_ * dt;

    // Jump physics
    if (is_jumping_) {
        player_y_ += player_vy_ * dt;
        player_vy_ += 35.0f * dt; // Gravity
        if (player_y_ >= 13.0f) {
            player_y_ = 13.0f;
            player_vy_ = 0.0f;
            is_jumping_ = false;
        }
    } else {
        if ((buttons & BUTTON_B) && !(prev_buttons & BUTTON_B)) {
            is_jumping_ = true;
            player_vy_ = has_skateboard_ ? -13.0f : -11.0f;
        }
    }

    // Attack: Throw Stone Axe
    if ((buttons & BUTTON_A) && !(prev_buttons & BUTTON_A)) {
        ThrowAxe();
    }

    // Keep player on screen, advance stage progress
    if (player_x_ > 8.0f) {
        float overflow = player_x_ - 8.0f;
        player_x_ = 8.0f;
        stage_progress_ += overflow * 1.5f;
    }
    if (player_x_ < 1.0f) player_x_ = 1.0f;

    score_ += static_cast<int>(player_vx_ * dt * 2.0f);
}

void Game057WonderBoy::UpdateAxes(float dt) {
    for (int i = 0; i < MAX_AXES; ++i) {
        if (!axes_[i].active) continue;
        axes_[i].x += axes_[i].vx * dt;
        axes_[i].y += axes_[i].vy * dt;
        axes_[i].vy += 22.0f * dt; // Gravity

        if (axes_[i].x < 0.0f || axes_[i].x > 16.0f || axes_[i].y > 15.0f) {
            axes_[i].active = false;
        }
    }
}

void Game057WonderBoy::UpdateMonsters(float dt) {
    float scroll_eff = (has_skateboard_ ? 9.0f : 5.0f) * dt;

    for (int i = 0; i < MAX_MONSTERS; ++i) {
        if (!monsters_[i].active) continue;
        monsters_[i].x += (monsters_[i].vx * dt) - scroll_eff * 0.4f;

        if (monsters_[i].x < -2.0f) {
            monsters_[i].x = 18.0f + (i * 6.0f);
            monsters_[i].health = 1;
        }
    }

    for (int i = 0; i < MAX_FRUITS; ++i) {
        if (!fruits_[i].active) continue;
        fruits_[i].x -= scroll_eff * 0.6f;
        if (fruits_[i].x < -2.0f) {
            fruits_[i].x = 16.0f + (i * 10.0f);
        }
    }
}

void Game057WonderBoy::CheckCollisions() {
    // Stone axe hitting monsters
    for (int a = 0; a < MAX_AXES; ++a) {
        if (!axes_[a].active) continue;
        for (int m = 0; m < MAX_MONSTERS; ++m) {
            if (!monsters_[m].active) continue;
            if (std::abs(axes_[a].x - monsters_[m].x) < 1.2f &&
                std::abs(axes_[a].y - monsters_[m].y) < 1.2f) {
                axes_[a].active = false;
                monsters_[m].health--;
                if (monsters_[m].health <= 0) {
                    monsters_[m].active = false;
                    score_ += 100;
                }
                break;
            }
        }
    }

    // Player collecting fruits or skateboard egg
    for (int f = 0; f < MAX_FRUITS; ++f) {
        if (!fruits_[f].active) continue;
        if (std::abs(player_x_ - fruits_[f].x) < 1.1f &&
            std::abs(player_y_ - fruits_[f].y) < 1.2f) {
            fruits_[f].active = false;
            if (fruits_[f].type == 2) {
                // Skateboard egg!
                has_skateboard_ = true;
                score_ += 300;
            } else {
                // Fruit: restores vitality +3
                vitality_ = std::min(16, vitality_ + 3);
                score_ += 100;
            }
        }
    }

    // Player colliding with monsters
    for (int m = 0; m < MAX_MONSTERS; ++m) {
        if (!monsters_[m].active) continue;
        if (std::abs(player_x_ - monsters_[m].x) < 0.9f &&
            std::abs(player_y_ - monsters_[m].y) < 0.9f) {
            if (has_fairy_) {
                // Fairy kills monster
                monsters_[m].active = false;
                score_ += 200;
            } else if (has_skateboard_) {
                // Skateboard absorbs crash!
                has_skateboard_ = false;
                monsters_[m].active = false;
            } else {
                // Direct death
                lives_--;
                state_ = STATE_DEAD;
                state_timer_ = 0.0f;
                return;
            }
        }
    }
}

void Game057WonderBoy::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    // Sky & Tropical Beach Background (Cyan sky, Sandy ground)
    for (int y = 0; y < 14; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = 40;
            fb[idx + 1] = 160 + y * 5;
            fb[idx + 2] = 240; // Tropical cyan sky
        }
    }

    // Ground platform (Grass top y=14, Dirt y=15)
    for (int x = 0; x < 16; ++x) {
        int idx_g = (14 * 16 + x) * 3;
        fb[idx_g] = 50;
        fb[idx_g + 1] = 200;
        fb[idx_g + 2] = 40; // Green grass

        int idx_d = (15 * 16 + x) * 3;
        fb[idx_d] = 140;
        fb[idx_d + 1] = 80;
        fb[idx_d + 2] = 30; // Brown soil
    }

    // Render Fruits (Bananas = Yellow, Apples = Red, Egg = White)
    for (int f = 0; f < MAX_FRUITS; ++f) {
        if (!fruits_[f].active) continue;
        int fx = static_cast<int>(std::round(fruits_[f].x));
        int fy = static_cast<int>(std::round(fruits_[f].y));
        if (fx >= 0 && fx < 16 && fy >= 0 && fy < 16) {
            int idx = (fy * 16 + fx) * 3;
            if (fruits_[f].type == 0) {
                fb[idx] = 255;
                fb[idx + 1] = 230;
                fb[idx + 2] = 0; // Yellow banana
            } else if (fruits_[f].type == 1) {
                fb[idx] = 255;
                fb[idx + 1] = 30;
                fb[idx + 2] = 30; // Red apple
            } else {
                fb[idx] = 255;
                fb[idx + 1] = 255;
                fb[idx + 2] = 255; // White egg
            }
        }
    }

    // Render Monsters (Snails / Octopuses)
    for (int m = 0; m < MAX_MONSTERS; ++m) {
        if (!monsters_[m].active) continue;
        int mx = static_cast<int>(std::round(monsters_[m].x));
        int my = static_cast<int>(std::round(monsters_[m].y));
        if (mx >= 0 && mx < 16 && my >= 0 && my < 16) {
            int idx = (my * 16 + mx) * 3;
            if (monsters_[m].type == 0) {
                fb[idx] = 160;
                fb[idx + 1] = 60;
                fb[idx + 2] = 180; // Purple snail
            } else if (monsters_[m].type == 1) {
                fb[idx] = 255;
                fb[idx + 1] = 80;
                fb[idx + 2] = 0; // Orange octopus
            } else {
                fb[idx] = 120;
                fb[idx + 1] = 120;
                fb[idx + 2] = 120; // Grey boulder
            }
        }
    }

    // Render Stone Axes
    for (int a = 0; a < MAX_AXES; ++a) {
        if (!axes_[a].active) continue;
        int ax = static_cast<int>(std::round(axes_[a].x));
        int ay = static_cast<int>(std::round(axes_[a].y));
        if (ax >= 0 && ax < 16 && ay >= 0 && ay < 16) {
            int idx = (ay * 16 + ax) * 3;
            fb[idx] = 240;
            fb[idx + 1] = 240;
            fb[idx + 2] = 240; // Silver stone axe
        }
    }

    // Render Player (Tom-Tom: Grass skirt & cap)
    int px = static_cast<int>(std::round(player_x_));
    int py = static_cast<int>(std::round(player_y_));
    if (px >= 0 && px < 16 && py >= 0 && py < 16) {
        int idx = (py * 16 + px) * 3;
        fb[idx] = 255;
        fb[idx + 1] = 180;
        fb[idx + 2] = 120; // Skin tone

        // Skateboard beneath feet
        if (has_skateboard_) {
            if (py < 15) {
                int s_idx = ((py + 1) * 16 + px) * 3;
                fb[s_idx] = 255;
                fb[s_idx + 1] = 50;
                fb[s_idx + 2] = 50; // Red skateboard
            }
        }

        // Fairy hovering over head
        if (has_fairy_) {
            if (py > 0) {
                int f_idx = ((py - 1) * 16 + px) * 3;
                fb[f_idx] = 0;
                fb[f_idx + 1] = 255;
                fb[f_idx + 2] = 255; // Cyan angel
            }
        }
    }

    // Top HUD: Vitality Bar (0 to 16 pixels)
    for (int v = 0; v < vitality_ && v < 16; ++v) {
        int idx = v * 3;
        if (vitality_ <= 4) {
            fb[idx] = 255;
            fb[idx + 1] = 0;
            fb[idx + 2] = 0; // Low vitality alert RED
        } else {
            fb[idx] = 0;
            fb[idx + 1] = 255;
            fb[idx + 2] = 0; // Healthy GREEN
        }
    }
}

} // namespace arcade
