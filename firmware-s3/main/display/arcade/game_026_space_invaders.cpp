// game_026_space_invaders.cpp —— 目标 #026 太空侵略者 核心实现
#include "game_026_space_invaders.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>
#include <math.h>
#include <stdlib.h>

namespace arcade {

Game026SpaceInvaders::Game026SpaceInvaders()
    : state_(STATE_TITLE),
      player_x_(7.0f),
      lives_(3),
      score_(0),
      high_score_(0),
      state_timer_(0.0f),
      anim_timer_(0.0f),
      fleet_x_(1),
      fleet_y_(1),
      fleet_dir_(1),
      fleet_step_timer_(0.0f),
      fleet_step_interval_(0.6f),
      remaining_aliens_(12),
      fleet_anim_frame_(false) {
    for (int i = 0; i < kMaxBullets; ++i) {
        bullets_[i].active = false;
    }
}

void Game026SpaceInvaders::ResetFleet() {
    remaining_aliens_ = kFleetRows * kFleetCols;
    for (int r = 0; r < kFleetRows; ++r) {
        for (int c = 0; c < kFleetCols; ++c) {
            fleet_[r][c].alive = true;
            if (r == 0) {
                fleet_[r][c].r = 255; fleet_[r][c].g = 0; fleet_[r][c].b = 128;
                fleet_[r][c].score_val = 30;
            } else if (r == 1) {
                fleet_[r][c].r = 241; fleet_[r][c].g = 196; fleet_[r][c].b = 15;
                fleet_[r][c].score_val = 20;
            } else {
                fleet_[r][c].r = 0; fleet_[r][c].g = 255; fleet_[r][c].b = 255;
                fleet_[r][c].score_val = 10;
            }
        }
    }
    fleet_x_ = 1;
    fleet_y_ = 1;
    fleet_dir_ = 1;
    fleet_step_timer_ = 0.0f;
    fleet_step_interval_ = 0.6f;
}

void Game026SpaceInvaders::Init() {
    Reset();
}

void Game026SpaceInvaders::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    state_ = STATE_TITLE;
    score_ = 0;
    lives_ = 3;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    player_x_ = 7.0f;

    for (int i = 0; i < kMaxBullets; ++i) {
        bullets_[i].active = false;
    }

    for (int b = 0; b < 3; ++b) {
        for (int r = 0; r < 3; ++r) {
            bunkers_[b][r].hp = 2;
        }
    }

    ResetFleet();
}

void Game026SpaceInvaders::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        state_ = STATE_PLAYING;
        score_ = 0;
        lives_ = 3;
        state_timer_ = 0.0f;
        anim_timer_ = 0.0f;
        player_x_ = 7.0f;
        for (int i = 0; i < kMaxBullets; ++i) bullets_[i].active = false;
        for (int b = 0; b < 3; ++b) {
            for (int r = 0; r < 3; ++r) bunkers_[b][r].hp = 2;
        }
        ResetFleet();
    }
}

void Game026SpaceInvaders::Pause() {
    if (state_ == STATE_PLAYING) state_ = STATE_PAUSED;
}

void Game026SpaceInvaders::Resume() {
    if (state_ == STATE_PAUSED) state_ = STATE_PLAYING;
}

void Game026SpaceInvaders::FirePlayerBullet() {
    for (int i = 0; i < kMaxBullets; ++i) {
        if (!bullets_[i].active) {
            bullets_[i].active = true;
            bullets_[i].x = player_x_;
            bullets_[i].y = 13.0f;
            bullets_[i].vy = -18.0f;
            break;
        }
    }
}

void Game026SpaceInvaders::SpawnAlienBomb() {
    int slot = -1;
    for (int i = 0; i < kMaxBullets; ++i) {
        if (!bullets_[i].active) {
            slot = i;
            break;
        }
    }
    if (slot == -1) return;

    int cols[kFleetCols];
    int count = 0;
    for (int c = 0; c < kFleetCols; ++c) {
        for (int r = kFleetRows - 1; r >= 0; --r) {
            if (fleet_[r][c].alive) {
                cols[count++] = c;
                break;
            }
        }
    }
    if (count == 0) return;

    int col = cols[rand() % count];
    int row = -1;
    for (int r = kFleetRows - 1; r >= 0; --r) {
        if (fleet_[r][col].alive) {
            row = r;
            break;
        }
    }
    if (row != -1) {
        bullets_[slot].active = true;
        bullets_[slot].x = (float)(fleet_x_ + col * 3 + 1);
        bullets_[slot].y = (float)(fleet_y_ + row * 2 + 1);
        bullets_[slot].vy = 9.0f;
    }
}

void Game026SpaceInvaders::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt > 0.05f) dt = 0.05f;
    state_timer_ += dt;
    anim_timer_ += dt;

    if (state_ == STATE_TITLE) {
        fleet_step_timer_ += dt;
        if (fleet_step_timer_ >= 0.5f) {
            fleet_step_timer_ = 0.0f;
            fleet_x_ += fleet_dir_;
            if (fleet_x_ <= 0 || fleet_x_ >= 4) {
                fleet_dir_ = -fleet_dir_;
            }
        }
        if (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP)) {
            Start();
        }
        return;
    }

    if (state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        if (state_timer_ > 0.5f && (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT))) {
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

        const float speed = 11.0f;
        if (keys_down & KEY_LEFT) player_x_ -= speed * dt;
        else if (keys_down & KEY_RIGHT) player_x_ += speed * dt;
        if (player_x_ < 1.0f) player_x_ = 1.0f;
        if (player_x_ > 14.0f) player_x_ = 14.0f;

        if (keys_pressed & (KEY_A | KEY_B | KEY_UP)) {
            FirePlayerBullet();
        }

        fleet_step_timer_ += dt;
        if (fleet_step_timer_ >= fleet_step_interval_) {
            fleet_step_timer_ = 0.0f;
            fleet_anim_frame_ = !fleet_anim_frame_;

            bool reach_wall = false;
            for (int c = 0; c < kFleetCols; ++c) {
                for (int r = 0; r < kFleetRows; ++r) {
                    if (fleet_[r][c].alive) {
                        int ax = fleet_x_ + c * 3;
                        if ((fleet_dir_ > 0 && ax >= 12) || (fleet_dir_ < 0 && ax <= 0)) {
                            reach_wall = true;
                            break;
                        }
                    }
                }
                if (reach_wall) break;
            }

            if (reach_wall) {
                fleet_dir_ = -fleet_dir_;
                fleet_y_++;
                if (fleet_y_ >= 10) {
                    state_ = STATE_GAMEOVER;
                    state_timer_ = 0.0f;
                    if (score_ > high_score_) {
                        high_score_ = score_;
                        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
                    }
                    return;
                }
            } else {
                fleet_x_ += fleet_dir_;
            }

            if ((rand() % 100) < 45) {
                SpawnAlienBomb();
            }
        }

        for (int i = 0; i < kMaxBullets; ++i) {
            if (bullets_[i].active) {
                bullets_[i].y += bullets_[i].vy * dt;

                if (bullets_[i].vy < 0.0f) {
                    for (int r = 0; r < kFleetRows; ++r) {
                        for (int c = 0; c < kFleetCols; ++c) {
                            if (fleet_[r][c].alive) {
                                int ax = fleet_x_ + c * 3;
                                int ay = fleet_y_ + r * 2;
                                if (fabsf(bullets_[i].x - (float)ax) < 1.2f &&
                                    fabsf(bullets_[i].y - (float)ay) < 1.0f) {
                                    fleet_[r][c].alive = false;
                                    bullets_[i].active = false;
                                    remaining_aliens_--;
                                    score_ += fleet_[r][c].score_val;
                                    if (score_ > high_score_) {
                                        high_score_ = score_;
                                        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
                                    }

                                    fleet_step_interval_ = 0.15f + (float)remaining_aliens_ * 0.035f;

                                    if (remaining_aliens_ <= 0) {
                                        state_ = STATE_VICTORY;
                                        state_timer_ = 0.0f;
                                        return;
                                    }
                                    break;
                                }
                            }
                        }
                        if (!bullets_[i].active) break;
                    }
                } else {
                    if (fabsf(bullets_[i].x - player_x_) < 1.4f && bullets_[i].y >= 13.5f) {
                        bullets_[i].active = false;
                        if (lives_ > 1) {
                            lives_--;
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

                if (bullets_[i].y < 0.0f || bullets_[i].y > 15.5f) {
                    bullets_[i].active = false;
                }
            }
        }
    }
}

void Game026SpaceInvaders::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    memset(fb_rgb24, 0, 16 * 16 * 3);

    for (int r = 0; r < kFleetRows; ++r) {
        for (int c = 0; c < kFleetCols; ++c) {
            if (fleet_[r][c].alive) {
                int ax = fleet_x_ + c * 3;
                int ay = fleet_y_ + r * 2;
                if (ay >= 0 && ay < 16) {
                    for (int dx = 0; dx < 2; ++dx) {
                        int x = ax + dx;
                        if (x >= 0 && x < 16) {
                            int idx = (ay * 16 + x) * 3;
                            fb_rgb24[idx + 0] = fleet_[r][c].r;
                            fb_rgb24[idx + 1] = fleet_[r][c].g;
                            fb_rgb24[idx + 2] = fleet_[r][c].b;
                        }
                    }
                }
            }
        }
    }

    int px = (int)roundf(player_x_);
    if (px >= 1 && px < 15) {
        int idx_top = (14 * 16 + px) * 3;
        fb_rgb24[idx_top + 0] = 46; fb_rgb24[idx_top + 1] = 204; fb_rgb24[idx_top + 2] = 113;

        for (int dx = -1; dx <= 1; ++dx) {
            int idx = (15 * 16 + (px + dx)) * 3;
            fb_rgb24[idx + 0] = 39; fb_rgb24[idx + 1] = 174; fb_rgb24[idx + 2] = 96;
        }
    }

    for (int i = 0; i < kMaxBullets; ++i) {
        if (bullets_[i].active) {
            int bx = (int)roundf(bullets_[i].x);
            int by = (int)roundf(bullets_[i].y);
            if (bx >= 0 && bx < 16 && by >= 0 && by < 16) {
                int idx = (by * 16 + bx) * 3;
                if (bullets_[i].vy < 0.0f) {
                    fb_rgb24[idx + 0] = 255; fb_rgb24[idx + 1] = 255; fb_rgb24[idx + 2] = 255;
                } else {
                    fb_rgb24[idx + 0] = 231; fb_rgb24[idx + 1] = 76; fb_rgb24[idx + 2] = 60;
                }
            }
        }
    }

    for (int i = 0; i < lives_ && i < 3; ++i) {
        int idx = (0 * 16 + i * 2) * 3;
        fb_rgb24[idx + 0] = 46; fb_rgb24[idx + 1] = 204; fb_rgb24[idx + 2] = 113;
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

CartridgeStatus Game026SpaceInvaders::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = lives_;
    st.state = (uint8_t)state_;
    st.progress = (uint8_t)(((12 - remaining_aliens_) * 100) / 12);
    return st;
}

} // namespace arcade

