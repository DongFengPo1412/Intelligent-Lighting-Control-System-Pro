// game_026_whack_a_mole.cpp —— 像素打地鼠 1976 核心实现
#include "game_026_whack_a_mole.h"
#include <string.h>
#include <stdlib.h>
#include <math.h>

namespace arcade {

static const int HOLE_X[3] = {3, 8, 13};
static const int HOLE_Y[3] = {3, 8, 13};

Game026WhackAMole::Game026WhackAMole()
    : state_(STATE_TITLE),
      cursor_row_(1),
      cursor_col_(1),
      hammer_anim_timer_(0.0f),
      lives_(3),
      time_remaining_(45.0f),
      spawn_cooldown_(0.0f),
      score_(0),
      high_score_(0),
      state_timer_(0.0f) {
}

void Game026WhackAMole::InitHoles() {
    for (int r = 0; r < 3; ++r) {
        for (int c = 0; c < 3; ++c) {
            int idx = r * 3 + c;
            holes_[idx].cx = HOLE_X[c];
            holes_[idx].cy = HOLE_Y[r];
            holes_[idx].popped = false;
            holes_[idx].type = MOLE_NORMAL;
            holes_[idx].pop_timer = 0.0f;
            holes_[idx].whacked = false;
        }
    }
}

void Game026WhackAMole::Init() {
    Reset();
}

void Game026WhackAMole::Reset() {
    state_ = STATE_PLAYING;
    score_ = 0;
    lives_ = 3;
    time_remaining_ = 45.0f;
    cursor_row_ = 1;
    cursor_col_ = 1;
    hammer_anim_timer_ = 0.0f;
    spawn_cooldown_ = 0.5f;
    state_timer_ = 0.0f;
    InitHoles();
}

void Game026WhackAMole::SpawnMole() {
    // 随机挑选当前空闲的洞穴
    int pick = rand() % TOTAL_HOLES;
    for (int t = 0; t < TOTAL_HOLES; ++t) {
        int idx = (pick + t) % TOTAL_HOLES;
        if (!holes_[idx].popped) {
            holes_[idx].popped = true;
            holes_[idx].whacked = false;
            holes_[idx].pop_timer = 1.0f + ((rand() % 5) / 10.0f); // 1.0s ~ 1.4s

            int roll = rand() % 100;
            if (roll < 65) {
                holes_[idx].type = MOLE_NORMAL;
            } else if (roll < 80) {
                holes_[idx].type = MOLE_GOLDEN;
            } else {
                holes_[idx].type = MOLE_BOMB;
            }
            break;
        }
    }
}

void Game026WhackAMole::StrikeHammer() {
    hammer_anim_timer_ = 0.18f;
    int idx = cursor_row_ * 3 + cursor_col_;

    if (holes_[idx].popped && !holes_[idx].whacked) {
        holes_[idx].whacked = true;

        if (holes_[idx].type == MOLE_NORMAL) {
            score_ += 100;
            if (score_ > high_score_) high_score_ = score_;
        } else if (holes_[idx].type == MOLE_GOLDEN) {
            score_ += 300;
            if (score_ > high_score_) high_score_ = score_;
        } else if (holes_[idx].type == MOLE_BOMB) {
            // 误锤炸弹！引爆扣减生命
            lives_--;
            if (lives_ <= 0) {
                state_ = STATE_GAMEOVER;
                state_timer_ = 0.0f;
            }
        }
    }
}

void Game026WhackAMole::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt > 0.05f) dt = 0.05f;
    state_timer_ += dt;

    if (state_ == STATE_TITLE) {
        if (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        if (state_timer_ > 0.5f && (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT))) {
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

        // 1. 倒计时管理
        time_remaining_ -= dt;
        if (time_remaining_ <= 0.0f) {
            time_remaining_ = 0.0f;
            if (score_ >= 1500) {
                state_ = STATE_VICTORY;
            } else {
                state_ = STATE_GAMEOVER;
            }
            state_timer_ = 0.0f;
            return;
        }

        // 2. 锤击准星移动
        if (keys_pressed & KEY_UP) {
            if (cursor_row_ > 0) cursor_row_--;
        }
        if (keys_pressed & KEY_DOWN) {
            if (cursor_row_ < 2) cursor_row_++;
        }
        if (keys_pressed & KEY_LEFT) {
            if (cursor_col_ > 0) cursor_col_--;
        }
        if (keys_pressed & KEY_RIGHT) {
            if (cursor_col_ < 2) cursor_col_++;
        }

        // 3. 挥锤敲击
        if (hammer_anim_timer_ > 0.0f) hammer_anim_timer_ -= dt;
        if (keys_pressed & (KEY_A | KEY_B)) {
            StrikeHammer();
        }

        // 4. 地鼠探头生成器
        spawn_cooldown_ -= dt;
        if (spawn_cooldown_ <= 0.0f) {
            spawn_cooldown_ = 0.65f + ((rand() % 4) / 10.0f);
            SpawnMole();
        }

        // 5. 更新各洞穴地鼠状态
        for (int i = 0; i < TOTAL_HOLES; ++i) {
            if (!holes_[i].popped) continue;

            holes_[i].pop_timer -= dt;
            if (holes_[i].pop_timer <= 0.0f) {
                holes_[i].popped = false;
                holes_[i].whacked = false;
            }
        }
    }
}

void Game026WhackAMole::Render(uint8_t* fb_rgb24) {
    // 1. 背景草甸深绿 [20, 50, 25]
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            fb_rgb24[idx + 0] = 20;
            fb_rgb24[idx + 1] = 50;
            fb_rgb24[idx + 2] = 25;
        }
    }

    // 2. 绘制 9 个地洞泥土深黑色 [30, 20, 15] (每个洞穴 2x2 大小)
    for (int r = 0; r < 3; ++r) {
        for (int c = 0; c < 3; ++c) {
            int cx = HOLE_X[c];
            int cy = HOLE_Y[r];
            int idx = r * 3 + c;

            // 绘制地洞基座
            for (int dy = -1; dy <= 0; ++dy) {
                for (int dx = -1; dx <= 0; ++dx) {
                    int px = cx + dx;
                    int py = cy + dy;
                    if (px >= 0 && px < 16 && py >= 0 && py < 16) {
                        int pidx = (py * 16 + px) * 3;
                        fb_rgb24[pidx + 0] = 35; fb_rgb24[pidx + 1] = 25; fb_rgb24[pidx + 2] = 18;
                    }
                }
            }

            // 绘制冒头的地鼠或炸弹
            if (holes_[idx].popped) {
                uint8_t cr, cg, cb;
                if (holes_[idx].whacked) {
                    // 击晕眩光 (纯白)
                    cr = 255; cg = 255; cb = 255;
                } else if (holes_[idx].type == MOLE_NORMAL) {
                    // 普通地鼠褐 [180, 100, 40]
                    cr = 180; cg = 100; cb = 40;
                } else if (holes_[idx].type == MOLE_GOLDEN) {
                    // 黄金地鼠金 [255, 215, 0]
                    cr = 255; cg = 215; cb = 0;
                } else {
                    // 刺球炸弹红 [231, 76, 60]
                    cr = 231; cg = 76;  cb = 60;
                }

                int px = cx - 1;
                int py = cy - 1;
                int pidx = (py * 16 + px) * 3;
                fb_rgb24[pidx + 0] = cr; fb_rgb24[pidx + 1] = cg; fb_rgb24[pidx + 2] = cb;
            }
        }
    }

    // 3. 绘制准星 (青蓝十字瞄准方框 [0, 255, 255])
    int cur_cx = HOLE_X[cursor_col_];
    int cur_cy = HOLE_Y[cursor_row_];

    // 挥锤时亮白红爆炸闪光，平时为青蓝准星
    uint8_t h_r = (hammer_anim_timer_ > 0.0f) ? 255 : 0;
    uint8_t h_g = (hammer_anim_timer_ > 0.0f) ? 255 : 255;
    uint8_t h_b = (hammer_anim_timer_ > 0.0f) ? 50  : 255;

    int p1 = (cur_cy * 16 + cur_cx) * 3;
    fb_rgb24[p1 + 0] = h_r; fb_rgb24[p1 + 1] = h_g; fb_rgb24[p1 + 2] = h_b;

    // 4. 顶部 HUD: 剩余生命与倒计时条 (Row 0)
    for (int i = 0; i < lives_; ++i) {
        int idx = (0 * 16 + i) * 3;
        fb_rgb24[idx + 0] = 231; fb_rgb24[idx + 1] = 76; fb_rgb24[idx + 2] = 60;
    }
    int timer_len = (int)((time_remaining_ / 45.0f) * 10.0f);
    for (int i = 0; i < timer_len; ++i) {
        int idx = (0 * 16 + (15 - i)) * 3;
        fb_rgb24[idx + 0] = 241; fb_rgb24[idx + 1] = 196; fb_rgb24[idx + 2] = 15;
    }

    // 5. 胜负特效
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

CartridgeStatus Game026WhackAMole::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.lives = lives_;
    st.state = (uint8_t)state_;
    // 进度基于得分达成率 (0 ~ 1500 分)
    int prog = (int)((score_ * 100) / 1500);
    if (prog > 100) prog = 100;
    st.progress = (uint8_t)prog;
    return st;
}

} // namespace arcade
