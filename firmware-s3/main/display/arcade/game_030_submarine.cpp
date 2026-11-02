// game_030_submarine.cpp —— 潜艇鱼雷大战 1979 核心实现
#include "game_030_submarine.h"
#include <string.h>
#include <stdlib.h>
#include <math.h>

namespace arcade {

Game030Submarine::Game030Submarine()
    : state_(STATE_TITLE),
      player_x_(7.0f),
      lives_(3),
      reload_timer_(0.0f),
      ships_sunk_(0),
      ship_spawn_timer_(0.0f),
      mine_spawn_timer_(0.0f),
      score_(0),
      high_score_(0),
      state_timer_(0.0f) {
}

void Game030Submarine::SpawnShip() {
    for (int i = 0; i < MAX_SHIPS; ++i) {
        if (!ships_[i].active) {
            ships_[i].active = true;
            bool from_left = (rand() % 2 == 0);
            ships_[i].x = from_left ? -2.0f : 17.0f;

            int roll = rand() % 100;
            if (roll < 45) {
                ships_[i].type = SHIP_PT_BOAT;
                ships_[i].y = 2.0f;
                ships_[i].vx = from_left ? 5.5f : -5.5f;
                ships_[i].hp = 1;
            } else if (roll < 80) {
                ships_[i].type = SHIP_DESTROYER;
                ships_[i].y = 3.5f;
                ships_[i].vx = from_left ? 3.5f : -3.5f;
                ships_[i].hp = 1;
            } else {
                ships_[i].type = SHIP_CARRIER;
                ships_[i].y = 4.5f;
                ships_[i].vx = from_left ? 2.2f : -2.2f;
                ships_[i].hp = 2;
            }
            break;
        }
    }
}

void Game030Submarine::SpawnMine() {
    for (int i = 0; i < MAX_MINES; ++i) {
        if (!mines_[i].active) {
            mines_[i].active = true;
            bool from_left = (rand() % 2 == 0);
            mines_[i].x = from_left ? -1.0f : 16.0f;
            mines_[i].y = 8.0f + (float)(rand() % 3);
            mines_[i].vx = from_left ? 1.5f : -1.5f;
            break;
        }
    }
}

void Game030Submarine::InitOcean() {
    player_x_ = 7.0f;
    lives_ = 3;
    reload_timer_ = 0.0f;
    ships_sunk_ = 0;
    ship_spawn_timer_ = 0.0f;
    mine_spawn_timer_ = 0.0f;

    for (int i = 0; i < MAX_SHIPS; ++i) ships_[i].active = false;
    for (int i = 0; i < MAX_TORPEDOES; ++i) torpedoes_[i].active = false;
    for (int i = 0; i < MAX_MINES; ++i) mines_[i].active = false;

    SpawnShip();
    SpawnMine();
}

void Game030Submarine::Init() {
    Reset();
}

void Game030Submarine::Reset() {
    state_ = STATE_PLAYING;
    score_ = 0;
    state_timer_ = 0.0f;
    InitOcean();
}

void Game030Submarine::FireTorpedo() {
    if (reload_timer_ > 0.0f) return;
    reload_timer_ = 0.35f;

    for (int i = 0; i < MAX_TORPEDOES; ++i) {
        if (!torpedoes_[i].active) {
            torpedoes_[i].active = true;
            torpedoes_[i].x = player_x_ + 0.5f;
            torpedoes_[i].y = 13.0f;
            torpedoes_[i].vy = -10.5f; // 垂直上浮高速冲向海面
            break;
        }
    }
}

void Game030Submarine::UpdateShips(float dt) {
    ship_spawn_timer_ += dt;
    if (ship_spawn_timer_ >= 1.6f) {
        ship_spawn_timer_ = 0.0f;
        SpawnShip();
    }

    for (int i = 0; i < MAX_SHIPS; ++i) {
        if (!ships_[i].active) continue;

        ships_[i].x += ships_[i].vx * dt;

        // 越界销毁
        if ((ships_[i].vx > 0.0f && ships_[i].x > 18.0f) ||
            (ships_[i].vx < 0.0f && ships_[i].x < -3.0f)) {
            ships_[i].active = false;
        }
    }
}

void Game030Submarine::UpdateMines(float dt) {
    mine_spawn_timer_ += dt;
    if (mine_spawn_timer_ >= 3.5f) {
        mine_spawn_timer_ = 0.0f;
        SpawnMine();
    }

    for (int i = 0; i < MAX_MINES; ++i) {
        if (!mines_[i].active) continue;

        mines_[i].x += mines_[i].vx * dt;

        if ((mines_[i].vx > 0.0f && mines_[i].x > 17.0f) ||
            (mines_[i].vx < 0.0f && mines_[i].x < -2.0f)) {
            mines_[i].active = false;
        }
    }
}

void Game030Submarine::UpdateTorpedoes(float dt) {
    for (int i = 0; i < MAX_TORPEDOES; ++i) {
        if (!torpedoes_[i].active) continue;

        torpedoes_[i].y += torpedoes_[i].vy * dt;

        // 浮出海面销毁
        if (torpedoes_[i].y < 0.5f) {
            torpedoes_[i].active = false;
            continue;
        }

        // 1. 撞击游弋水雷
        for (int m = 0; m < MAX_MINES; ++m) {
            if (mines_[m].active) {
                float dist = fabsf(torpedoes_[i].x - mines_[m].x) + fabsf(torpedoes_[i].y - mines_[m].y);
                if (dist <= 1.0f) {
                    torpedoes_[i].active = false;
                    mines_[m].active = false;
                    score_ += 20;
                    if (score_ > high_score_) high_score_ = score_;
                    break;
                }
            }
        }
        if (!torpedoes_[i].active) continue;

        // 2. 命中水面舰艇 (结合吃水深度与前置量预判)
        for (int s = 0; s < MAX_SHIPS; ++s) {
            if (ships_[s].active) {
                float width = (ships_[s].type == SHIP_CARRIER) ? 2.0f : 1.2f;
                float dx = fabsf(torpedoes_[i].x - ships_[s].x);
                float dy = fabsf(torpedoes_[i].y - ships_[s].y);

                if (dx <= width && dy <= 0.9f) {
                    torpedoes_[i].active = false;
                    ships_[s].hp--;

                    if (ships_[s].hp <= 0) {
                        ships_[s].active = false;
                        ships_sunk_++;

                        if (ships_[s].type == SHIP_PT_BOAT) score_ += 100;
                        else if (ships_[s].type == SHIP_DESTROYER) score_ += 200;
                        else score_ += 400;

                        if (score_ > high_score_) high_score_ = score_;

                        if (ships_sunk_ >= 8) {
                            state_ = STATE_VICTORY;
                            state_timer_ = 0.0f;
                            score_ += 1000;
                            if (score_ > high_score_) high_score_ = score_;
                            return;
                        }
                    }
                    break;
                }
            }
        }
    }
}

void Game030Submarine::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt > 0.05f) dt = 0.05f;
    state_timer_ += dt;

    if (state_ == STATE_TITLE) {
        if (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP)) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        if (state_timer_ > 0.5f && (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP))) {
            Reset();
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

        if (reload_timer_ > 0.0f) reload_timer_ -= dt;

        // 1. 潜艇深海潜航 (左右平移)
        float speed = 7.5f;
        if (keys_down & KEY_LEFT) player_x_ -= speed * dt;
        if (keys_down & KEY_RIGHT) player_x_ += speed * dt;

        if (player_x_ < 0.5f) player_x_ = 0.5f;
        if (player_x_ > 14.0f) player_x_ = 14.0f;

        // 2. 发射直航鱼雷
        if (keys_pressed & (KEY_A | KEY_B)) {
            FireTorpedo();
        }

        // 3. 更新舰艇、水雷与鱼雷
        UpdateShips(dt);
        UpdateMines(dt);
        UpdateTorpedoes(dt);
    }
}

void Game030Submarine::Render(uint8_t* fb_rgb24) {
    memset(fb_rgb24, 0, 16 * 16 * 3);

    // 1. 湛蓝深海渐变背景
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            if (y == 0) {
                fb_rgb24[idx + 0] = 52;  fb_rgb24[idx + 1] = 152; fb_rgb24[idx + 2] = 219; // 海平线天空蓝
            } else if (y <= 5) {
                fb_rgb24[idx + 0] = 41;  fb_rgb24[idx + 1] = 128; fb_rgb24[idx + 2] = 185; // 浅海波纹蓝
            } else if (y <= 11) {
                fb_rgb24[idx + 0] = 21;  fb_rgb24[idx + 1] = 67;  fb_rgb24[idx + 2] = 96;  // 中层大洋深蓝
            } else {
                fb_rgb24[idx + 0] = 11;  fb_rgb24[idx + 1] = 22;  fb_rgb24[idx + 2] = 44;  // 深渊幽暗黑蓝
            }
        }
    }

    // 2. 绘制水面舰艇
    for (int i = 0; i < MAX_SHIPS; ++i) {
        if (!ships_[i].active) continue;

        int sx = (int)roundf(ships_[i].x);
        int sy = (int)roundf(ships_[i].y);

        if (sy >= 0 && sy < 16) {
            uint8_t cr, cg, cb;
            if (ships_[i].type == SHIP_PT_BOAT) {
                cr = 241; cg = 196; cb = 15;  // 鱼雷艇金黄
            } else if (ships_[i].type == SHIP_DESTROYER) {
                cr = 189; cg = 195; cb = 199; // 驱逐舰钢灰
            } else {
                cr = 231; cg = 76;  cb = 60;  // 航母猩红
            }

            int w = (ships_[i].type == SHIP_CARRIER) ? 2 : 1;
            for (int dx = 0; dx < w; ++dx) {
                int px = sx + dx;
                if (px >= 0 && px < 16) {
                    int idx = (sy * 16 + px) * 3;
                    fb_rgb24[idx + 0] = cr; fb_rgb24[idx + 1] = cg; fb_rgb24[idx + 2] = cb;
                }
            }
        }
    }

    // 3. 绘制游弋水雷 (暗红刺球带黑心 [231, 76, 60])
    for (int i = 0; i < MAX_MINES; ++i) {
        if (!mines_[i].active) continue;

        int mx = (int)roundf(mines_[i].x);
        int my = (int)roundf(mines_[i].y);
        if (mx >= 0 && mx < 16 && my >= 0 && my < 16) {
            int idx = (my * 16 + mx) * 3;
            fb_rgb24[idx + 0] = 231; fb_rgb24[idx + 1] = 76; fb_rgb24[idx + 2] = 60;
        }
    }

    // 4. 绘制上浮鱼雷 (耀眼纯白航迹 [255, 255, 255])
    for (int i = 0; i < MAX_TORPEDOES; ++i) {
        if (!torpedoes_[i].active) continue;

        int tx = (int)roundf(torpedoes_[i].x);
        int ty = (int)roundf(torpedoes_[i].y);
        if (tx >= 0 && tx < 16 && ty >= 0 && ty < 16) {
            int idx = (ty * 16 + tx) * 3;
            fb_rgb24[idx + 0] = 255; fb_rgb24[idx + 1] = 255; fb_rgb24[idx + 2] = 255;
        }
    }

    // 5. 绘制核潜艇 (潜艇两格长，亮绿声呐流光 [46, 204, 113])
    if (lives_ > 0) {
        int px1 = (int)roundf(player_x_);
        int px2 = px1 + 1;
        int py = 14;

        if (px1 >= 0 && px1 < 16) {
            int idx1 = (py * 16 + px1) * 3;
            fb_rgb24[idx1 + 0] = 46; fb_rgb24[idx1 + 1] = 204; fb_rgb24[idx1 + 2] = 113;
        }
        if (px2 >= 0 && px2 < 16) {
            int idx2 = (py * 16 + px2) * 3;
            fb_rgb24[idx2 + 0] = 0; fb_rgb24[idx2 + 1] = 255; fb_rgb24[idx2 + 2] = 255; // 艇首声呐舱
        }
    }

    // 6. 顶部 HUD: 击沉战果点数 (金黄微粒) 与潜艇耐久 (绿点)
    for (int i = 0; i < lives_; ++i) {
        int idx = (0 * 16 + i) * 3;
        fb_rgb24[idx + 0] = 46; fb_rgb24[idx + 1] = 204; fb_rgb24[idx + 2] = 113;
    }
    for (int i = 0; i < ships_sunk_; ++i) {
        int idx = (0 * 16 + (15 - i)) * 3;
        fb_rgb24[idx + 0] = 241; fb_rgb24[idx + 1] = 196; fb_rgb24[idx + 2] = 15;
    }

    // 7. 胜负特效
    if (state_ == STATE_VICTORY) {
        for (int x = 0; x < 16; ++x) {
            int idx = (15 * 16 + x) * 3;
            fb_rgb24[idx + 0] = 46; fb_rgb24[idx + 1] = 204; fb_rgb24[idx + 2] = 113;
        }
    } else if (state_ == STATE_GAMEOVER) {
        for (int x = 0; x < 16; ++x) {
            int idx = (15 * 16 + x) * 3;
            fb_rgb24[idx + 0] = 231; fb_rgb24[idx + 1] = 76; fb_rgb24[idx + 2] = 60;
        }
    }
}

CartridgeStatus Game030Submarine::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.lives = lives_;
    st.state = (uint8_t)state_;
    int prog = (ships_sunk_ * 100) / 8;
    if (prog > 100) prog = 100;
    st.progress = (uint8_t)prog;
    return st;
}

} // namespace arcade
