#include "game_069_qbert.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game069Qbert::Game069Qbert()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(7000),
      lives_(3),
      player_row_(0),
      player_col_(0),
      jump_anim_timer_(0.0f),
      jump_offset_x_(0.0f),
      jump_offset_y_(0.0f),
      cubes_flipped_(0),
      disc_left_active_(true),
      disc_right_active_(true),
      freeze_timer_(0.0f),
      enemy_spawn_timer_(2.5f) {
}

void Game069Qbert::Init() {
    Reset();
}

void Game069Qbert::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    lives_ = 3;
    InitStage();
}

void Game069Qbert::InitStage() {
    player_row_ = 0;
    player_col_ = 0;
    jump_anim_timer_ = 0.0f;
    jump_offset_x_ = 0.0f;
    jump_offset_y_ = 0.0f;

    for (int i = 0; i < TOTAL_CUBES; ++i) {
        cube_flipped_[i] = false;
    }
    // Starting cube (0, 0) flipped
    cube_flipped_[0] = true;
    cubes_flipped_ = 1;

    disc_left_active_ = true;
    disc_right_active_ = true;
    freeze_timer_ = 0.0f;
    enemy_spawn_timer_ = 1.5f;

    // Coily starts dormant and drops in after delay
    coily_.row = 0;
    coily_.col = 0;
    coily_.is_hatched = false;
    coily_.jump_timer = 1.0f;
    coily_.active = false;

    for (int i = 0; i < MAX_BALLS; ++i) {
        balls_[i].active = false;
    }
}

int Game069Qbert::GetCubeIndex(int r, int c) const {
    if (r < 0 || r >= NUM_ROWS || c < 0 || c > r) return -1;
    // Row 0 has 1, Row 1 has 2, ...
    int start_idx = (r * (r + 1)) / 2;
    return start_idx + c;
}

void Game069Qbert::Jump(int drow, int dcol) {
    if (jump_anim_timer_ > 0.0f) return;

    int nr = player_row_ + drow;
    int nc = player_col_ + dcol;

    // Check escape discs
    if (nr == 2 && nc == -1 && disc_left_active_) {
        // Leaps on left spinning disc!
        disc_left_active_ = false;
        player_row_ = 0;
        player_col_ = 0;
        score_ += 500;
        // Tricked Coily falls off!
        if (coily_.active && coily_.is_hatched) {
            coily_.active = false;
            score_ += 500;
        }
        return;
    }
    if (nr == 2 && nc == 3 && disc_right_active_) {
        // Leaps on right spinning disc!
        disc_right_active_ = false;
        player_row_ = 0;
        player_col_ = 0;
        score_ += 500;
        if (coily_.active && coily_.is_hatched) {
            coily_.active = false;
            score_ += 500;
        }
        return;
    }

    // Check leap into the abyss
    int idx = GetCubeIndex(nr, nc);
    if (idx == -1) {
        // Fell off pyramid!
        lives_--;
        state_ = STATE_DEAD;
        state_timer_ = 0.0f;
        return;
    }

    // Successful jump on cube
    player_row_ = nr;
    player_col_ = nc;
    jump_anim_timer_ = 0.18f;

    if (!cube_flipped_[idx]) {
        cube_flipped_[idx] = true;
        cubes_flipped_++;
        score_ += 25;

        if (cubes_flipped_ >= TOTAL_CUBES) {
            state_ = STATE_VICTORY;
            state_timer_ = 0.0f;
            score_ += 3500;
            if (score_ > high_score_) high_score_ = score_;
            return;
        }
    }
}

void Game069Qbert::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_DEAD) {
        if (state_timer_ > 1.8f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                state_timer_ = 0.0f;
                player_row_ = 0;
                player_col_ = 0;
                coily_.row = 0;
                coily_.col = 0;
                coily_.is_hatched = false;
                coily_.jump_timer = 1.0f;
                coily_.active = true;
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

    if (jump_anim_timer_ > 0.0f) jump_anim_timer_ -= dt;

    if (freeze_timer_ > 0.0f) {
        freeze_timer_ -= dt;
    } else {
        UpdateEnemies(dt);
    }

    UpdatePlayer(dt, buttons, prev_buttons);
    CheckCollisions();
}

void Game069Qbert::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (jump_anim_timer_ > 0.0f) return;

    // Diagonal jumping mapped to 4-way D-Pad
    if ((buttons & BUTTON_UP) && !(prev_buttons & BUTTON_UP)) {
        Jump(-1, -1); // Up-Left
    } else if ((buttons & BUTTON_RIGHT) && !(prev_buttons & BUTTON_RIGHT)) {
        Jump(-1, 0);  // Up-Right
    } else if ((buttons & BUTTON_LEFT) && !(prev_buttons & BUTTON_LEFT)) {
        Jump(1, 0);   // Down-Left
    } else if ((buttons & BUTTON_DOWN) && !(prev_buttons & BUTTON_DOWN)) {
        Jump(1, 1);   // Down-Right
    }
}

void Game069Qbert::UpdateEnemies(float dt) {
    // Coily jump logic
    if (coily_.active) {
        coily_.jump_timer -= dt;
        if (coily_.jump_timer <= 0.0f) {
            coily_.jump_timer = 0.85f;

            if (!coily_.is_hatched) {
                // Purple egg rolls downward
                int dc = (rand() % 2); // 0 or 1
                coily_.row++;
                coily_.col += dc;
                if (coily_.row >= 4) {
                    coily_.is_hatched = true; // Hatches at bottom into snake!
                }
            } else {
                // Snake chases Q*bert
                int dr = 0, dc = 0;
                if (coily_.row < player_row_) {
                    dr = 1;
                    dc = (coily_.col <= player_col_) ? 1 : 0;
                } else if (coily_.row > player_row_) {
                    dr = -1;
                    dc = (coily_.col > player_col_) ? -1 : 0;
                } else {
                    // Same row: move towards col
                    if (coily_.col < player_col_) { dr = 1; dc = 1; }
                    else { dr = -1; dc = -1; }
                }

                int nr = coily_.row + dr;
                int nc = coily_.col + dc;
                if (GetCubeIndex(nr, nc) != -1) {
                    coily_.row = nr;
                    coily_.col = nc;
                }
            }
        }
    } else {
        // Respawn Coily after delay
        enemy_spawn_timer_ -= dt;
        if (enemy_spawn_timer_ <= 0.0f) {
            enemy_spawn_timer_ = 3.0f;
            coily_.active = true;
            coily_.row = 0;
            coily_.col = 0;
            coily_.is_hatched = false;
            coily_.jump_timer = 1.0f;
        }
    }

    // Falling balls
    for (int i = 0; i < MAX_BALLS; ++i) {
        if (!balls_[i].active) continue;
        balls_[i].jump_timer -= dt;
        if (balls_[i].jump_timer <= 0.0f) {
            balls_[i].jump_timer = 0.75f;
            balls_[i].row++;
            balls_[i].col += (rand() % 2);
            if (balls_[i].row >= NUM_ROWS) {
                balls_[i].active = false;
            }
        }
    }

    // Spawn green or red ball periodically
    if (!balls_[0].active && !balls_[1].active && (rand() % 50 == 0)) {
        balls_[0].active = true;
        balls_[0].row = 1;
        balls_[0].col = rand() % 2;
        balls_[0].jump_timer = 0.8f;
        balls_[0].is_green = (rand() % 3 == 0); // 1 in 3 chance for green freeze ball
    }
}

void Game069Qbert::CheckCollisions() {
    // 1. Coily collision
    if (coily_.active && coily_.row == player_row_ && coily_.col == player_col_) {
        lives_--;
        state_ = STATE_DEAD;
        state_timer_ = 0.0f;
        return;
    }

    // 2. Balls collision
    for (int i = 0; i < MAX_BALLS; ++i) {
        if (!balls_[i].active) continue;
        if (balls_[i].row == player_row_ && balls_[i].col == player_col_) {
            balls_[i].active = false;
            if (balls_[i].is_green) {
                // Freezes time!
                freeze_timer_ = 4.0f;
                score_ += 100;
            } else {
                // Red lethal ball
                lives_--;
                state_ = STATE_DEAD;
                state_timer_ = 0.0f;
                return;
            }
        }
    }
}

void Game069Qbert::Render(uint8_t* fb) {
    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // 1. Black void arcade background
    for (int i = 0; i < 16 * 16 * 3; ++i) {
        fb[i] = 0;
    }

    // 2. Isometric Pyramid Cubes
    for (int r = 0; r < NUM_ROWS; ++r) {
        for (int c = 0; c <= r; ++c) {
            int idx = GetCubeIndex(r, c);
            bool flipped = cube_flipped_[idx];

            int cx = 7 - r * 1 + c * 3;
            int cy = 3 + r * 2;

            uint8_t top_r = flipped ? 255 : 20;
            uint8_t top_g = flipped ? 220 : 60;
            uint8_t top_b = flipped ? 20  : 200;

            // Top face of cube (2x1)
            set_pixel(cx, cy, top_r, top_g, top_b);
            set_pixel(cx + 1, cy, top_r, top_g, top_b);

            // Left shaded side
            set_pixel(cx, cy + 1, top_r / 2, top_g / 2, top_b / 2);

            // Right dark shaded side
            set_pixel(cx + 1, cy + 1, top_r / 4, top_g / 4, top_b / 4);
        }
    }

    // 3. Escape Discs
    if (disc_left_active_) {
        // Floating near row 2, left side
        set_pixel(2, 7, 255, 100, 255);
        set_pixel(3, 7, 255, 100, 255);
    }
    if (disc_right_active_) {
        // Floating near row 2, right side
        set_pixel(13, 7, 255, 100, 255);
        set_pixel(14, 7, 255, 100, 255);
    }

    // 4. Falling Balls
    for (int i = 0; i < MAX_BALLS; ++i) {
        if (!balls_[i].active) continue;
        int bx = 7 - balls_[i].row * 1 + balls_[i].col * 3;
        int by = 3 + balls_[i].row * 2 - 1;
        if (balls_[i].is_green) {
            set_pixel(bx, by, 50, 255, 50); // Green freeze ball
        } else {
            set_pixel(bx, by, 255, 40, 40); // Red lethal ball
        }
    }

    // 5. Coily the Snake
    if (coily_.active) {
        int sx = 7 - coily_.row * 1 + coily_.col * 3;
        int sy = 3 + coily_.row * 2 - 1;
        if (!coily_.is_hatched) {
            // Purple bouncing egg
            set_pixel(sx, sy, 200, 40, 220);
        } else {
            // Purple coiled snake with red fangs
            set_pixel(sx, sy, 180, 20, 220);
            set_pixel(sx, sy - 1, 255, 30, 30);
        }
    }

    // 6. Q*bert (Orange round snout character with big eyes)
    if (state_ != STATE_DEAD) {
        int qx = 7 - player_row_ * 1 + player_col_ * 3;
        int qy = 3 + player_row_ * 2 - 1;

        set_pixel(qx, qy, 255, 140, 20);       // Orange body
        set_pixel(qx + 1, qy, 255, 100, 0);   // Snout
        set_pixel(qx, qy - 1, 255, 255, 255); // White eyes
    } else {
        // Flashing comic curse bubble "@!#?@!"
        int qx = 7 - player_row_ * 1 + player_col_ * 3;
        int qy = 3 + player_row_ * 2 - 1;
        set_pixel(qx, qy, 255, 255, 0);
        set_pixel(qx + 1, qy - 1, 255, 0, 0);
    }

    // 7. Freeze aura HUD
    if (freeze_timer_ > 0.0f) {
        set_pixel(0, 0, 0, 255, 255);
        set_pixel(15, 0, 0, 255, 255);
    }
}

} // namespace arcade
