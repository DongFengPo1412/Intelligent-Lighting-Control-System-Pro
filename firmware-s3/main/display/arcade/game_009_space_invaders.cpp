// game_009_space_invaders.cpp —— 太空侵略者 1978 核心实现
#include "game_009_space_invaders.h"
#include <string.h>
#include <math.h>
#include <stdlib.h>

namespace arcade {

Game009SpaceInvaders::Game009SpaceInvaders()
    : state_(STATE_TITLE),
      player_x_(7.0f),
      lives_(3),
      score_(0),
      high_score_(0),
      state_timer_(0.0f),
      fleet_x_(1),
      fleet_y_(1),
      fleet_dir_(1),
      march_timer_(0.0f),
      march_interval_(0.6f),
      remaining_aliens_(12),
      bomb_drop_timer_(0.0f) {
    player_bullet_.active = false;
    for (int i = 0; i < kMaxAlienBombs; ++i) {
        alien_bombs_[i].active = false;
    }
}

void Game009SpaceInvaders::ResetFleet() {
    remaining_aliens_ = kFleetRows * kFleetCols;
    for (int r = 0; r < kFleetRows; ++r) {
        for (int c = 0; c < kFleetCols; ++c) {
            fleet_[r][c].alive = true;
            if (r == 0) {
                fleet_[r][c].r = 255; fleet_[r][c].g = 0;   fleet_[r][c].b = 128; // 紫红 30分
                fleet_[r][c].score_val = 30;
            } else if (r == 1) {
                fleet_[r][c].r = 241; fleet_[r][c].g = 196; fleet_[r][c].b = 15;  // 亮黄 20分
                fleet_[r][c].score_val = 20;
            } else {
                fleet_[r][c].r = 0;   fleet_[r][c].g = 255; fleet_[r][c].b = 255; // 青蓝 10分
                fleet_[r][c].score_val = 10;
            }
        }
    }
    fleet_x_ = 1;
    fleet_y_ = 1;
    fleet_dir_ = 1;
    march_timer_ = 0.0f;
    march_interval_ = 0.6f;
}

void Game009SpaceInvaders::Init() {
    Reset();
}

void Game009SpaceInvaders::Reset() {
    state_ = STATE_PLAYING;
    score_ = 0;
    lives_ = 3;
    state_timer_ = 0.0f;
    player_x_ = 7.0f;

    player_bullet_.active = false;
    for (int i = 0; i < kMaxAlienBombs; ++i) {
        alien_bombs_[i].active = false;
    }

    // 初始化掩体: 3座，每座2x2 (位于 y=11..12, x=2..3, 7..8, 12..13)
    for (int b = 0; b < kNumBunkers; ++b) {
        for (int r = 0; r < 2; ++r) {
            for (int c = 0; c < 2; ++c) {
                bunkers_[b][r][c].hp = 2; // 满耐久 2
            }
        }
    }

    ResetFleet();
}

void Game009SpaceInvaders::FirePlayerBullet() {
    if (!player_bullet_.active) {
        player_bullet_.active = true;
        player_bullet_.x = player_x_;
        player_bullet_.y = 12.0f;
        player_bullet_.vy = -18.0f;
    }
}

void Game009SpaceInvaders::SpawnAlienBomb() {
    // 寻找空闲炸弹槽位
    int slot = -1;
    for (int i = 0; i < kMaxAlienBombs; ++i) {
        if (!alien_bombs_[i].active) {
            slot = i;
            break;
        }
    }
    if (slot == -1) return;

    // 随机选择一列存活的外星人投掷炸弹
    int candidates[kFleetCols];
    int cand_count = 0;
    for (int c = 0; c < kFleetCols; ++c) {
        for (int r = kFleetRows - 1; r >= 0; --r) {
            if (fleet_[r][c].alive) {
                candidates[cand_count++] = c;
                break;
            }
        }
    }
    if (cand_count == 0) return;

    int chosen_col = candidates[rand() % cand_count];
    int chosen_row = -1;
    for (int r = kFleetRows - 1; r >= 0; --r) {
        if (fleet_[r][chosen_col].alive) {
            chosen_row = r;
            break;
        }
    }

    if (chosen_row != -1) {
        alien_bombs_[slot].active = true;
        alien_bombs_[slot].x = (float)(fleet_x_ + chosen_col * 2);
        alien_bombs_[slot].y = (float)(fleet_y_ + chosen_row * 2 + 1);
        alien_bombs_[slot].vy = 8.0f;
    }
}

void Game009SpaceInvaders::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt > 0.05f) dt = 0.05f;
    state_timer_ += dt;

    if (state_ == STATE_TITLE) {
        if (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP)) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        if (state_timer_ > 0.5f && (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT))) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_PAUSED) {
        if (keys_pressed & KEY_START) {
            state_ = STATE_PLAYING;
        }
        return;
    }

    if (state_ == STATE_PLAYING) {
        if (keys_pressed & KEY_START) {
            state_ = STATE_PAUSED;
            return;
        }

        // 1. 玩家移动控制
        const float player_speed = 10.0f;
        if (keys_down & KEY_LEFT) {
            player_x_ -= player_speed * dt;
        } else if (keys_down & KEY_RIGHT) {
            player_x_ += player_speed * dt;
        }
        if (player_x_ < 1.0f) player_x_ = 1.0f;
        if (player_x_ > 14.0f) player_x_ = 14.0f;

        // 2. 玩家开火
        if (keys_pressed & (KEY_A | KEY_B | KEY_UP)) {
            FirePlayerBullet();
        }

        // 3. 玩家子弹推进与碰撞
        if (player_bullet_.active) {
            player_bullet_.y += player_bullet_.vy * dt;
            int bx = (int)roundf(player_bullet_.x);
            int by = (int)roundf(player_bullet_.y);

            // 出顶界
            if (player_bullet_.y <= 0.0f) {
                player_bullet_.active = false;
            } else {
                // (a) 检查击中掩体
                bool hit_bunker = false;
                for (int b = 0; b < kNumBunkers && !hit_bunker; ++b) {
                    int bx_origin = (b == 0) ? 2 : (b == 1) ? 7 : 12;
                    if (bx >= bx_origin && bx < bx_origin + 2 && by >= 11 && by <= 12) {
                        int br = by - 11;
                        int bc = bx - bx_origin;
                        if (bunkers_[b][br][bc].hp > 0) {
                            bunkers_[b][br][bc].hp--;
                            player_bullet_.active = false;
                            hit_bunker = true;
                        }
                    }
                }

                // (b) 检查击中外星侵略者
                if (player_bullet_.active) {
                    for (int r = 0; r < kFleetRows; ++r) {
                        for (int c = 0; c < kFleetCols; ++c) {
                            if (fleet_[r][c].alive) {
                                int ax = fleet_x_ + c * 2;
                                int ay = fleet_y_ + r * 2;
                                if (fabsf(player_bullet_.x - (float)ax) < 0.9f &&
                                    fabsf(player_bullet_.y - (float)ay) < 0.9f) {
                                    fleet_[r][c].alive = false;
                                    remaining_aliens_--;
                                    score_ += fleet_[r][c].score_val;
                                    if (score_ > high_score_) high_score_ = score_;
                                    player_bullet_.active = false;

                                    // 加快步进速度
                                    march_interval_ = 0.12f + (0.48f * remaining_aliens_) / 12.0f;

                                    if (remaining_aliens_ <= 0) {
                                        state_ = STATE_VICTORY;
                                        state_timer_ = 0.0f;
                                        return;
                                    }
                                    goto bullet_done;
                                }
                            }
                        }
                    }
                }
            }
        }
bullet_done:

        // 4. 外星舰队行军节拍
        march_timer_ += dt;
        if (march_timer_ >= march_interval_) {
            march_timer_ = 0.0f;

            // 计算当前存活边界
            int min_c = kFleetCols, max_c = -1, max_r = -1;
            for (int r = 0; r < kFleetRows; ++r) {
                for (int c = 0; c < kFleetCols; ++c) {
                    if (fleet_[r][c].alive) {
                        if (c < min_c) min_c = c;
                        if (c > max_c) max_c = c;
                        if (r > max_r) max_r = r;
                    }
                }
            }

            if (max_c != -1) {
                int next_edge_right = fleet_x_ + max_c * 2 + fleet_dir_;
                int next_edge_left = fleet_x_ + min_c * 2 + fleet_dir_;

                if (fleet_dir_ > 0 && next_edge_right >= 16) {
                    fleet_y_ += 1; // 下压
                    fleet_dir_ = -1;
                } else if (fleet_dir_ < 0 && next_edge_left < 0) {
                    fleet_y_ += 1; // 下压
                    fleet_dir_ = 1;
                } else {
                    fleet_x_ += fleet_dir_;
                }

                // 入侵触底检测 (若压到 y=13 玩家基准线，防守溃败)
                if (fleet_y_ + max_r * 2 >= 13) {
                    state_ = STATE_GAMEOVER;
                    state_timer_ = 0.0f;
                    return;
                }
            }
        }

        // 5. 敌机随机投放炸弹
        bomb_drop_timer_ += dt;
        if (bomb_drop_timer_ >= 1.2f) {
            bomb_drop_timer_ = 0.0f;
            SpawnAlienBomb();
        }

        // 6. 敌机炸弹下落与判定
        for (int i = 0; i < kMaxAlienBombs; ++i) {
            if (alien_bombs_[i].active) {
                alien_bombs_[i].y += alien_bombs_[i].vy * dt;
                int bx = (int)roundf(alien_bombs_[i].x);
                int by = (int)roundf(alien_bombs_[i].y);

                // (a) 检查炸毁掩体
                bool hit_bunker = false;
                for (int b = 0; b < kNumBunkers && !hit_bunker; ++b) {
                    int bx_origin = (b == 0) ? 2 : (b == 1) ? 7 : 12;
                    if (bx >= bx_origin && bx < bx_origin + 2 && by >= 11 && by <= 12) {
                        int br = by - 11;
                        int bc = bx - bx_origin;
                        if (bunkers_[b][br][bc].hp > 0) {
                            bunkers_[b][br][bc].hp--;
                            alien_bombs_[i].active = false;
                            hit_bunker = true;
                        }
                    }
                }

                // (b) 检查击中玩家
                if (alien_bombs_[i].active && by >= 13 && by <= 14) {
                    if (fabsf(alien_bombs_[i].x - player_x_) <= 1.2f) {
                        alien_bombs_[i].active = false;
                        if (lives_ > 0) lives_--;
                        if (lives_ == 0) {
                            state_ = STATE_GAMEOVER;
                            state_timer_ = 0.0f;
                            return;
                        }
                    }
                }

                // (c) 出底界
                if (alien_bombs_[i].y >= 16.0f) {
                    alien_bombs_[i].active = false;
                }
            }
        }
    }
}

void Game009SpaceInvaders::Render(uint8_t* fb_rgb24) {
    memset(fb_rgb24, 0, 16 * 16 * 3);

    // 1. 顶部生命显示 (y=0, 绿色点阵)
    for (int i = 0; i < lives_; ++i) {
        int idx = (0 * 16 + (i * 2)) * 3;
        fb_rgb24[idx + 0] = 46; fb_rgb24[idx + 1] = 204; fb_rgb24[idx + 2] = 113;
    }

    // 2. 绘制外星舰队
    for (int r = 0; r < kFleetRows; ++r) {
        for (int c = 0; c < kFleetCols; ++c) {
            if (fleet_[r][c].alive) {
                int ax = fleet_x_ + c * 2;
                int ay = fleet_y_ + r * 2;
                if (ax >= 0 && ax < 16 && ay >= 0 && ay < 16) {
                    int idx = (ay * 16 + ax) * 3;
                    fb_rgb24[idx + 0] = fleet_[r][c].r;
                    fb_rgb24[idx + 1] = fleet_[r][c].g;
                    fb_rgb24[idx + 2] = fleet_[r][c].b;
                }
            }
        }
    }

    // 3. 绘制掩体 (y=11..12)
    for (int b = 0; b < kNumBunkers; ++b) {
        int bx_origin = (b == 0) ? 2 : (b == 1) ? 7 : 12;
        for (int r = 0; r < 2; ++r) {
            int y = 11 + r;
            for (int c = 0; c < 2; ++c) {
                int x = bx_origin + c;
                if (bunkers_[b][r][c].hp > 0) {
                    int idx = (y * 16 + x) * 3;
                    if (bunkers_[b][r][c].hp == 2) {
                        fb_rgb24[idx + 0] = 46; fb_rgb24[idx + 1] = 204; fb_rgb24[idx + 2] = 113; // 鲜绿
                    } else {
                        fb_rgb24[idx + 0] = 30; fb_rgb24[idx + 1] = 132; fb_rgb24[idx + 2] = 73;  // 暗损绿
                    }
                }
            }
        }
    }

    // 4. 绘制敌机炸弹
    for (int i = 0; i < kMaxAlienBombs; ++i) {
        if (alien_bombs_[i].active) {
            int bx = (int)roundf(alien_bombs_[i].x);
            int by = (int)roundf(alien_bombs_[i].y);
            if (bx >= 0 && bx < 16 && by >= 0 && by < 16) {
                int idx = (by * 16 + bx) * 3;
                fb_rgb24[idx + 0] = 231; fb_rgb24[idx + 1] = 76; fb_rgb24[idx + 2] = 60; // 危险红
            }
        }
    }

    // 5. 绘制玩家炮台 (基座 y=14 宽3，炮管 y=13 宽1)
    int px = (int)roundf(player_x_);
    // 炮管
    if (px >= 0 && px < 16) {
        int idx = (13 * 16 + px) * 3;
        fb_rgb24[idx + 0] = 255; fb_rgb24[idx + 1] = 255; fb_rgb24[idx + 2] = 255;
    }
    // 底座
    for (int dx = -1; dx <= 1; ++dx) {
        int x = px + dx;
        if (x >= 0 && x < 16) {
            int idx = (14 * 16 + x) * 3;
            fb_rgb24[idx + 0] = 46; fb_rgb24[idx + 1] = 204; fb_rgb24[idx + 2] = 113;
        }
    }

    // 6. 绘制玩家激光子弹
    if (player_bullet_.active) {
        int bx = (int)roundf(player_bullet_.x);
        int by = (int)roundf(player_bullet_.y);
        if (bx >= 0 && bx < 16 && by >= 0 && by < 16) {
            int idx = (by * 16 + bx) * 3;
            fb_rgb24[idx + 0] = fb_rgb24[idx + 1] = fb_rgb24[idx + 2] = 255; // 激光白
        }
    }

    // 7. 特效渲染
    if (state_ == STATE_VICTORY) {
        for (int x = 0; x < 16; ++x) {
            int idx = (15 * 16 + x) * 3;
            fb_rgb24[idx + 0] = 52; fb_rgb24[idx + 1] = 152; fb_rgb24[idx + 2] = 219;
        }
    } else if (state_ == STATE_GAMEOVER) {
        for (int x = 0; x < 16; ++x) {
            int idx = (15 * 16 + x) * 3;
            fb_rgb24[idx + 0] = 231; fb_rgb24[idx + 1] = 76; fb_rgb24[idx + 2] = 60;
        }
    }
}

CartridgeStatus Game009SpaceInvaders::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.lives = lives_;
    st.state = (uint8_t)state_;
    st.progress = (uint8_t)(((kFleetRows * kFleetCols - remaining_aliens_) * 100) / (kFleetRows * kFleetCols));
    return st;
}

} // namespace arcade
