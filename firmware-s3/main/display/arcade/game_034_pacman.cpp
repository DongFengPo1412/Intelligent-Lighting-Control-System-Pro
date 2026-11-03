// game_034_pacman.cpp —— 目标 #034 吃豆人 核心实现
#include "game_034_pacman.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>
#include <math.h>
#include <stdlib.h>

namespace arcade {

static const uint8_t kWallMap[16][16] = {
    {1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1},
    {1,0,0,0,0,0,1,1,1,1,0,0,0,0,0,1},
    {1,0,1,1,0,1,0,0,0,0,1,0,1,1,0,1},
    {1,0,1,1,0,1,0,1,1,0,1,0,1,1,0,1},
    {1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1},
    {1,0,1,1,0,1,1,0,0,1,1,0,1,1,0,1},
    {1,0,0,1,0,1,0,0,0,0,1,0,1,0,0,1},
    {0,0,0,0,0,1,0,0,0,0,1,0,0,0,0,0}, // 左右穿梭隧道 (Row 7)
    {1,0,0,1,0,1,0,0,0,0,1,0,1,0,0,1},
    {1,0,1,1,0,1,1,1,1,1,1,0,1,1,0,1},
    {1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1},
    {1,0,1,1,0,1,1,0,0,1,1,0,1,1,0,1},
    {1,0,0,1,0,0,0,1,1,0,0,0,1,0,0,1},
    {1,1,0,1,0,1,0,0,0,0,1,0,1,0,1,1},
    {1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1},
    {1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1}
};

Game034Pacman::Game034Pacman()
    : state_(STATE_TITLE),
      pac_x_(8.0f),
      pac_y_(10.0f),
      pac_dir_x_(0),
      pac_dir_y_(0),
      desired_dir_x_(0),
      desired_dir_y_(0),
      frightened_timer_(0.0f),
      remaining_dots_(0),
      total_dots_(0),
      lives_(3),
      score_(0),
      high_score_(0),
      state_timer_(0.0f),
      anim_timer_(0.0f) {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
}

bool Game034Pacman::IsWall(int x, int y) const {
    if (y == 7 && (x < 0 || x >= 16)) return false;
    if (x < 0 || x >= 16 || y < 0 || y >= 16) return true;
    return kWallMap[y][x] == 1;
}

void Game034Pacman::ResetPositions() {
    pac_x_ = 8.0f;
    pac_y_ = 10.0f;
    pac_dir_x_ = 0;
    pac_dir_y_ = 0;
    desired_dir_x_ = 0;
    desired_dir_y_ = 0;

    ghosts_[0].x = 7.0f; ghosts_[0].y = 6.0f; ghosts_[0].dir_x = 1; ghosts_[0].dir_y = 0;
    ghosts_[0].state = GHOST_CHASE; ghosts_[0].r = 231; ghosts_[0].g = 76; ghosts_[0].b = 60;
    ghosts_[0].speed = 4.0f;

    ghosts_[1].x = 8.0f; ghosts_[1].y = 7.0f; ghosts_[1].dir_x = -1; ghosts_[1].dir_y = 0;
    ghosts_[1].state = GHOST_CHASE; ghosts_[1].r = 255; ghosts_[1].g = 105; ghosts_[1].b = 180;
    ghosts_[1].speed = 3.8f;

    ghosts_[2].x = 7.0f; ghosts_[2].y = 8.0f; ghosts_[2].dir_x = 0; ghosts_[2].dir_y = 1;
    ghosts_[2].state = GHOST_CHASE; ghosts_[2].r = 0; ghosts_[2].g = 255; ghosts_[2].b = 255;
    ghosts_[2].speed = 3.6f;

    frightened_timer_ = 0.0f;
}

void Game034Pacman::Init() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    Reset();
}

void Game034Pacman::Reset() {
    state_ = STATE_TITLE;
    score_ = 0;
    lives_ = 3;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    remaining_dots_ = 0;

    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (kWallMap[y][x] == 0) {
                if ((x >= 6 && x <= 9 && y >= 6 && y <= 8) || (x == 8 && y == 10)) {
                    grid_[y][x] = 0;
                } else if ((x == 1 && y == 1) || (x == 14 && y == 1) ||
                           (x == 1 && y == 14) || (x == 14 && y == 14)) {
                    grid_[y][x] = 2;
                    remaining_dots_++;
                } else {
                    grid_[y][x] = 1;
                    remaining_dots_++;
                }
            } else {
                grid_[y][x] = 0;
            }
        }
    }
    total_dots_ = remaining_dots_;
    ResetPositions();
}

void Game034Pacman::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        state_ = STATE_PLAYING;
        score_ = 0;
        lives_ = 3;
        state_timer_ = 0.0f;
        anim_timer_ = 0.0f;
        remaining_dots_ = 0;

        for (int y = 0; y < 16; ++y) {
            for (int x = 0; x < 16; ++x) {
                if (kWallMap[y][x] == 0) {
                    if ((x >= 6 && x <= 9 && y >= 6 && y <= 8) || (x == 8 && y == 10)) {
                        grid_[y][x] = 0;
                    } else if ((x == 1 && y == 1) || (x == 14 && y == 1) ||
                               (x == 1 && y == 14) || (x == 14 && y == 14)) {
                        grid_[y][x] = 2;
                        remaining_dots_++;
                    } else {
                        grid_[y][x] = 1;
                        remaining_dots_++;
                    }
                } else {
                    grid_[y][x] = 0;
                }
            }
        }
        total_dots_ = remaining_dots_;
        ResetPositions();
    }
}

void Game034Pacman::Pause() {
    if (state_ == STATE_PLAYING) state_ = STATE_PAUSED;
}

void Game034Pacman::Resume() {
    if (state_ == STATE_PAUSED) state_ = STATE_PLAYING;
}

void Game034Pacman::MoveGhost(PacGhost& g, float dt) {
    float move_step = g.speed * dt;
    if (g.state == GHOST_FRIGHTENED) move_step *= 0.55f;

    int cur_gx = (int)roundf(g.x);
    int cur_gy = (int)roundf(g.y);

    if (fabsf(g.x - (float)cur_gx) < move_step && fabsf(g.y - (float)cur_gy) < move_step) {
        g.x = (float)cur_gx;
        g.y = (float)cur_gy;

        int dirs[4][2] = {{1,0}, {-1,0}, {0,1}, {0,-1}};
        int valid_dirs[4][2];
        int count = 0;

        for (int i = 0; i < 4; ++i) {
            int ndx = dirs[i][0];
            int ndy = dirs[i][1];
            if (ndx == -g.dir_x && ndy == -g.dir_y) continue;
            if (!IsWall(cur_gx + ndx, cur_gy + ndy)) {
                valid_dirs[count][0] = ndx;
                valid_dirs[count][1] = ndy;
                count++;
            }
        }

        if (count > 0) {
            int choice = rand() % count;
            g.dir_x = valid_dirs[choice][0];
            g.dir_y = valid_dirs[choice][1];
        } else {
            g.dir_x = -g.dir_x;
            g.dir_y = -g.dir_y;
        }
    }

    g.x += (float)g.dir_x * move_step;
    g.y += (float)g.dir_y * move_step;

    if (cur_gy == 7) {
        if (g.x < -0.5f) g.x = 15.5f;
        else if (g.x > 15.5f) g.x = -0.5f;
    }
}

void Game034Pacman::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt > 0.05f) dt = 0.05f;
    state_timer_ += dt;
    anim_timer_ += dt;

    if (state_ == STATE_TITLE) {
        if (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)) {
            Start();
        }
        return;
    }

    if (state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        if (state_timer_ > 0.5f && (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT))) {
            Start();
        }
        return;
    }

    if (state_ == STATE_PAUSED) {
        if (keys_pressed & KEY_START) state_ = STATE_PLAYING;
        return;
    }

    if (state_ == STATE_PLAYING) {
        if (keys_pressed & KEY_START) {
            state_ = STATE_PAUSED;
            return;
        }

        if (keys_down & KEY_UP)    { desired_dir_x_ = 0;  desired_dir_y_ = -1; }
        else if (keys_down & KEY_DOWN)  { desired_dir_x_ = 0;  desired_dir_y_ = 1;  }
        else if (keys_down & KEY_LEFT)  { desired_dir_x_ = -1; desired_dir_y_ = 0;  }
        else if (keys_down & KEY_RIGHT) { desired_dir_x_ = 1;  desired_dir_y_ = 0;  }

        float pac_speed = 4.8f;
        float move_step = pac_speed * dt;

        int gx = (int)roundf(pac_x_);
        int gy = (int)roundf(pac_y_);

        if (desired_dir_x_ != pac_dir_x_ || desired_dir_y_ != pac_dir_y_) {
            if (desired_dir_x_ == -pac_dir_x_ && desired_dir_y_ == -pac_dir_y_ && (pac_dir_x_ != 0 || pac_dir_y_ != 0)) {
                pac_dir_x_ = desired_dir_x_;
                pac_dir_y_ = desired_dir_y_;
            } else if (fabsf(pac_x_ - (float)gx) < 0.25f && fabsf(pac_y_ - (float)gy) < 0.25f) {
                if (!IsWall(gx + desired_dir_x_, gy + desired_dir_y_)) {
                    pac_x_ = (float)gx;
                    pac_y_ = (float)gy;
                    pac_dir_x_ = desired_dir_x_;
                    pac_dir_y_ = desired_dir_y_;
                }
            }
        }

        if (!IsWall(gx + pac_dir_x_, gy + pac_dir_y_) ||
            ((pac_dir_x_ > 0 && pac_x_ < (float)gx) || (pac_dir_x_ < 0 && pac_x_ > (float)gx) ||
             (pac_dir_y_ > 0 && pac_y_ < (float)gy) || (pac_dir_y_ < 0 && pac_y_ > (float)gy))) {
            pac_x_ += (float)pac_dir_x_ * move_step;
            pac_y_ += (float)pac_dir_y_ * move_step;
        } else {
            pac_x_ = (float)gx;
            pac_y_ = (float)gy;
        }

        if (gy == 7) {
            if (pac_x_ < -0.5f) pac_x_ = 15.5f;
            else if (pac_x_ > 15.5f) pac_x_ = -0.5f;
        }

        int cur_x = (int)roundf(pac_x_);
        int cur_y = (int)roundf(pac_y_);
        if (cur_x >= 0 && cur_x < 16 && cur_y >= 0 && cur_y < 16) {
            if (grid_[cur_y][cur_x] == 1) {
                grid_[cur_y][cur_x] = 0;
                score_ += 10;
                remaining_dots_--;
            } else if (grid_[cur_y][cur_x] == 2) {
                grid_[cur_y][cur_x] = 0;
                score_ += 50;
                remaining_dots_--;
                frightened_timer_ = 6.0f;
                for (int i = 0; i < kNumGhosts; ++i) {
                    ghosts_[i].state = GHOST_FRIGHTENED;
                }
            }
            if (score_ > high_score_) {
                high_score_ = score_;
                ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
            }
            if (remaining_dots_ <= 0) {
                state_ = STATE_VICTORY;
                state_timer_ = 0.0f;
                return;
            }
        }

        if (frightened_timer_ > 0.0f) {
            frightened_timer_ -= dt;
            if (frightened_timer_ <= 0.0f) {
                for (int i = 0; i < kNumGhosts; ++i) {
                    ghosts_[i].state = GHOST_CHASE;
                }
            }
        }

        for (int i = 0; i < kNumGhosts; ++i) {
            MoveGhost(ghosts_[i], dt);

            if (fabsf(ghosts_[i].x - pac_x_) < 0.8f && fabsf(ghosts_[i].y - pac_y_) < 0.8f) {
                if (ghosts_[i].state == GHOST_FRIGHTENED) {
                    ghosts_[i].x = 7.0f;
                    ghosts_[i].y = 7.0f;
                    ghosts_[i].state = GHOST_CHASE;
                    score_ += 200;
                    if (score_ > high_score_) {
                        high_score_ = score_;
                        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
                    }
                } else if (ghosts_[i].state == GHOST_CHASE) {
                    if (lives_ > 1) {
                        lives_--;
                        ResetPositions();
                    } else {
                        lives_ = 0;
                        state_ = STATE_GAMEOVER;
                        state_timer_ = 0.0f;
                        if (score_ > high_score_) {
                            high_score_ = score_;
                            ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
                        }
                        return;
                    }
                }
            }
        }
    }
}

void Game034Pacman::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    memset(fb_rgb24, 0, 16 * 16 * 3);

    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            if (kWallMap[y][x] == 1) {
                fb_rgb24[idx + 0] = 33; fb_rgb24[idx + 1] = 66; fb_rgb24[idx + 2] = 180;
            } else if (grid_[y][x] == 1) {
                fb_rgb24[idx + 0] = 255; fb_rgb24[idx + 1] = 184; fb_rgb24[idx + 2] = 151;
            } else if (grid_[y][x] == 2) {
                fb_rgb24[idx + 0] = 255; fb_rgb24[idx + 1] = 255; fb_rgb24[idx + 2] = 255;
            }
        }
    }

    int px = (int)roundf(pac_x_);
    int py = (int)roundf(pac_y_);
    if (px >= 0 && px < 16 && py >= 0 && py < 16) {
        int idx = (py * 16 + px) * 3;
        fb_rgb24[idx + 0] = 255; fb_rgb24[idx + 1] = 255; fb_rgb24[idx + 2] = 0;
    }

    for (int i = 0; i < kNumGhosts; ++i) {
        int gx = (int)roundf(ghosts_[i].x);
        int gy = (int)roundf(ghosts_[i].y);
        if (gx >= 0 && gx < 16 && gy >= 0 && gy < 16) {
            int idx = (gy * 16 + gx) * 3;
            if (ghosts_[i].state == GHOST_FRIGHTENED) {
                fb_rgb24[idx + 0] = 30; fb_rgb24[idx + 1] = 60; fb_rgb24[idx + 2] = 220;
            } else {
                fb_rgb24[idx + 0] = ghosts_[i].r;
                fb_rgb24[idx + 1] = ghosts_[i].g;
                fb_rgb24[idx + 2] = ghosts_[i].b;
            }
        }
    }

    if (state_ == STATE_PAUSED) {
        for (int y = 6; y <= 9; ++y) {
            int idx1 = (y * 16 + 6) * 3;
            int idx2 = (y * 16 + 9) * 3;
            fb_rgb24[idx1 + 0] = fb_rgb24[idx1 + 1] = fb_rgb24[idx1 + 2] = 250;
            fb_rgb24[idx2 + 0] = fb_rgb24[idx2 + 1] = fb_rgb24[idx2 + 2] = 250;
        }
    }
}

CartridgeStatus Game034Pacman::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = lives_;
    st.state = (uint8_t)state_;
    st.progress = total_dots_ > 0 ? (uint8_t)(((total_dots_ - remaining_dots_) * 100) / total_dots_) : 0;
    return st;
}

} // namespace arcade
