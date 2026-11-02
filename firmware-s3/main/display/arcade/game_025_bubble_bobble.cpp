// game_025_bubble_bobble.cpp —— 经典泡泡龙打怪 1986 核心实现
#include "game_025_bubble_bobble.h"
#include <string.h>
#include <stdlib.h>
#include <math.h>

namespace arcade {

Game025BubbleBobble::Game025BubbleBobble()
    : state_(STATE_TITLE),
      player_x_(2.0f),
      player_y_(13.0f),
      player_vy_(0.0f),
      player_dir_(1),
      is_jumping_(false),
      lives_(3),
      spit_cooldown_(0.0f),
      score_(0),
      high_score_(0),
      state_timer_(0.0f) {
}

bool Game025BubbleBobble::IsOnPlatform(float x, float y) const {
    int px = (int)roundf(x);
    int py = (int)roundf(y);

    // 落地高度判定 (层 0=13, 层 1=9, 层 2=5)
    if (py == 13) return true; // 底层全通
    if (py == 9 && ((px >= 2 && px <= 6) || (px >= 9 && px <= 13))) return true; // 中层左右横梁
    if (py == 5 && (px >= 4 && px <= 11)) return true; // 顶层横梁
    return false;
}

void Game025BubbleBobble::InitLevel() {
    player_x_ = 2.0f;
    player_y_ = 13.0f;
    player_vy_ = 0.0f;
    player_dir_ = 1;
    is_jumping_ = false;
    spit_cooldown_ = 0.0f;

    for (int i = 0; i < MAX_BUBBLES; ++i) {
        bubbles_[i].active = false;
    }

    // 3 只机械发条怪
    enemies_[0].active = true;
    enemies_[0].x = 12.0f;
    enemies_[0].y = 13.0f;
    enemies_[0].vx = -3.0f;
    enemies_[0].trapped = false;
    enemies_[0].move_timer = 0.0f;

    enemies_[1].active = true;
    enemies_[1].x = 4.0f;
    enemies_[1].y = 9.0f;
    enemies_[1].vx = 2.5f;
    enemies_[1].trapped = false;
    enemies_[1].move_timer = 0.0f;

    enemies_[2].active = true;
    enemies_[2].x = 10.0f;
    enemies_[2].y = 5.0f;
    enemies_[2].vx = -2.5f;
    enemies_[2].trapped = false;
    enemies_[2].move_timer = 0.0f;
}

void Game025BubbleBobble::Init() {
    Reset();
}

void Game025BubbleBobble::Reset() {
    state_ = STATE_PLAYING;
    score_ = 0;
    lives_ = 3;
    state_timer_ = 0.0f;
    InitLevel();
}

void Game025BubbleBobble::SpitBubble() {
    if (spit_cooldown_ > 0.0f) return;
    spit_cooldown_ = 0.28f;

    for (int i = 0; i < MAX_BUBBLES; ++i) {
        if (!bubbles_[i].active) {
            bubbles_[i].active = true;
            bubbles_[i].x = player_x_ + (float)player_dir_ * 1.0f;
            bubbles_[i].y = player_y_;
            bubbles_[i].vx = (float)player_dir_ * 6.5f;
            bubbles_[i].vy = 0.0f;
            bubbles_[i].trapped_enemy = -1;
            bubbles_[i].timer = 7.0f;
            break;
        }
    }
}

void Game025BubbleBobble::UpdateBubbles(float dt) {
    for (int i = 0; i < MAX_BUBBLES; ++i) {
        if (!bubbles_[i].active) continue;

        bubbles_[i].timer -= dt;
        if (bubbles_[i].timer <= 0.0f) {
            // 气泡自然超时破裂
            if (bubbles_[i].trapped_enemy >= 0) {
                int e = bubbles_[i].trapped_enemy;
                enemies_[e].trapped = false;
                enemies_[e].x = bubbles_[i].x;
                enemies_[e].y = bubbles_[i].y;
            }
            bubbles_[i].active = false;
            continue;
        }

        // 水平减速并上升气流
        if (fabsf(bubbles_[i].vx) > 0.2f) {
            bubbles_[i].x += bubbles_[i].vx * dt;
            bubbles_[i].vx *= 0.80f;
        } else {
            bubbles_[i].vx = 0.0f;
            bubbles_[i].vy = -1.8f; // 向上漂浮
            bubbles_[i].y += bubbles_[i].vy * dt;

            // 飘到天花板停留
            if (bubbles_[i].y < 1.0f) {
                bubbles_[i].y = 1.0f;
                bubbles_[i].vy = 0.0f;
            }
        }

        // 若包裹怪物，同步怪物坐标
        if (bubbles_[i].trapped_enemy >= 0) {
            int e = bubbles_[i].trapped_enemy;
            enemies_[e].x = bubbles_[i].x;
            enemies_[e].y = bubbles_[i].y;
        } else {
            // 检测包裹附近的游荡怪物
            for (int e = 0; e < MAX_ENEMIES; ++e) {
                if (enemies_[e].active && !enemies_[e].trapped) {
                    float dist = fabsf(bubbles_[i].x - enemies_[e].x) + fabsf(bubbles_[i].y - enemies_[e].y);
                    if (dist <= 0.85f) {
                        bubbles_[i].trapped_enemy = e;
                        enemies_[e].trapped = true;
                        score_ += 50;
                        if (score_ > high_score_) high_score_ = score_;
                        break;
                    }
                }
            }
        }

        // 玩家触碰与踩踏检测
        float p_dist = fabsf(player_x_ - bubbles_[i].x) + fabsf(player_y_ - bubbles_[i].y);
        if (p_dist <= 1.0f) {
            if (bubbles_[i].trapped_enemy >= 0) {
                // 玩家撞破包裹怪物的气泡！将其斩杀引爆！
                int e = bubbles_[i].trapped_enemy;
                enemies_[e].active = false;
                bubbles_[i].active = false;
                score_ += 300;
                if (score_ > high_score_) high_score_ = score_;
            } else if (player_vy_ > 0.0f && player_y_ < bubbles_[i].y) {
                // 踏在空气泡上借力反弹跳跃！
                player_vy_ = -6.2f;
                is_jumping_ = true;
                score_ += 20;
                if (score_ > high_score_) high_score_ = score_;
            }
        }
    }
}

void Game025BubbleBobble::UpdateEnemies(float dt) {
    bool any_active = false;

    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;
        any_active = true;

        if (enemies_[i].trapped) continue; // 被困气泡中不自主巡逻

        // 沿平台游弋巡逻
        enemies_[i].x += enemies_[i].vx * dt;

        // 左右墙壁或横梁边缘反弹
        if (enemies_[i].x <= 0.5f) {
            enemies_[i].x = 0.5f;
            enemies_[i].vx = -enemies_[i].vx;
        } else if (enemies_[i].x >= 14.5f) {
            enemies_[i].x = 14.5f;
            enemies_[i].vx = -enemies_[i].vx;
        }

        // 接触玩家致命判定
        float dist = fabsf(player_x_ - enemies_[i].x) + fabsf(player_y_ - enemies_[i].y);
        if (dist <= 0.8f) {
            lives_--;
            if (lives_ <= 0) {
                state_ = STATE_GAMEOVER;
                state_timer_ = 0.0f;
                return;
            } else {
                player_x_ = 2.0f;
                player_y_ = 13.0f;
                return;
            }
        }
    }

    if (!any_active) {
        state_ = STATE_VICTORY;
        state_timer_ = 0.0f;
        score_ += 1000;
        if (score_ > high_score_) high_score_ = score_;
    }
}

void Game025BubbleBobble::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
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

        if (spit_cooldown_ > 0.0f) spit_cooldown_ -= dt;

        // 1. 吐泡泡 (A 键)
        if (keys_pressed & KEY_A) {
            SpitBubble();
        }

        // 2. 左右横移
        float speed = 6.0f;
        if (keys_down & KEY_LEFT) {
            player_x_ -= speed * dt;
            player_dir_ = -1;
        }
        if (keys_down & KEY_RIGHT) {
            player_x_ += speed * dt;
            player_dir_ = 1;
        }
        if (player_x_ < 0.0f) player_x_ = 0.0f;
        if (player_x_ > 15.0f) player_x_ = 15.0f;

        // 3. 跳跃控制 (B 键)
        if (!is_jumping_ && (keys_pressed & (KEY_B | KEY_UP))) {
            is_jumping_ = true;
            player_vy_ = -6.8f;
        }

        if (is_jumping_) {
            player_vy_ += 14.0f * dt; // 重力加速度
            player_y_ += player_vy_ * dt;

            // 落地判定 (只当下落 vy > 0 时踩在横梁上站稳)
            if (player_vy_ > 0.0f && IsOnPlatform(player_x_, player_y_)) {
                player_y_ = roundf(player_y_);
                player_vy_ = 0.0f;
                is_jumping_ = false;
            }
        } else {
            // 如果踩出平台边缘，受重力下落
            if (!IsOnPlatform(player_x_, player_y_)) {
                is_jumping_ = true;
                player_vy_ = 2.0f;
            }
        }

        // 确保不会掉穿底层
        if (player_y_ > 13.0f) {
            player_y_ = 13.0f;
            player_vy_ = 0.0f;
            is_jumping_ = false;
        }

        // 4. 更新气泡与怪物
        UpdateBubbles(dt);
        UpdateEnemies(dt);
    }
}

void Game025BubbleBobble::Render(uint8_t* fb_rgb24) {
    memset(fb_rgb24, 0, 16 * 16 * 3);

    // 1. 绘制平台横梁 (嫩草绿 [46, 204, 113])
    // 底层 (y=14)
    for (int x = 0; x < 16; ++x) {
        int idx = (14 * 16 + x) * 3;
        fb_rgb24[idx + 0] = 46; fb_rgb24[idx + 1] = 204; fb_rgb24[idx + 2] = 113;
    }
    // 中层左右横梁 (y=10)
    for (int x = 2; x <= 6; ++x) {
        int idx = (10 * 16 + x) * 3;
        fb_rgb24[idx + 0] = 46; fb_rgb24[idx + 1] = 204; fb_rgb24[idx + 2] = 113;
    }
    for (int x = 9; x <= 13; ++x) {
        int idx = (10 * 16 + x) * 3;
        fb_rgb24[idx + 0] = 46; fb_rgb24[idx + 1] = 204; fb_rgb24[idx + 2] = 113;
    }
    // 顶层横梁 (y=6)
    for (int x = 4; x <= 11; ++x) {
        int idx = (6 * 16 + x) * 3;
        fb_rgb24[idx + 0] = 46; fb_rgb24[idx + 1] = 204; fb_rgb24[idx + 2] = 113;
    }

    // 2. 绘制漂浮气泡 (青晶幽光 [52, 152, 219], 包裹怪物时金黄闪烁 [241, 196, 15])
    for (int i = 0; i < MAX_BUBBLES; ++i) {
        if (!bubbles_[i].active) continue;
        int bx = (int)roundf(bubbles_[i].x);
        int by = (int)roundf(bubbles_[i].y);
        if (bx >= 0 && bx < 16 && by >= 0 && by < 16) {
            int idx = (by * 16 + bx) * 3;
            if (bubbles_[i].trapped_enemy >= 0) {
                fb_rgb24[idx + 0] = 241; fb_rgb24[idx + 1] = 196; fb_rgb24[idx + 2] = 15;
            } else {
                fb_rgb24[idx + 0] = 52;  fb_rgb24[idx + 1] = 152; fb_rgb24[idx + 2] = 219;
            }
        }
    }

    // 3. 绘制游弋怪物 (深红机械发条怪 [231, 76, 60])
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;
        int ex = (int)roundf(enemies_[i].x);
        int ey = (int)roundf(enemies_[i].y);
        if (ex >= 0 && ex < 16 && ey >= 0 && ey < 16) {
            int idx = (ey * 16 + ex) * 3;
            if (!enemies_[i].trapped) {
                fb_rgb24[idx + 0] = 231; fb_rgb24[idx + 1] = 76; fb_rgb24[idx + 2] = 60;
            }
        }
    }

    // 4. 绘制小恐龙巴比 (翠绿身姿带纯白背鳍 [255, 255, 255])
    if (lives_ > 0) {
        int px = (int)roundf(player_x_);
        int py = (int)roundf(player_y_);
        if (px >= 0 && px < 16 && py >= 0 && py < 16) {
            int idx = (py * 16 + px) * 3;
            fb_rgb24[idx + 0] = 255; fb_rgb24[idx + 1] = 255; fb_rgb24[idx + 2] = 255;
        }
    }

    // 5. 顶部生命显示
    for (int i = 0; i < lives_; ++i) {
        int idx = (0 * 16 + i) * 3;
        fb_rgb24[idx + 0] = 255; fb_rgb24[idx + 1] = 255; fb_rgb24[idx + 2] = 255;
    }

    // 6. 胜负特效
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

CartridgeStatus Game025BubbleBobble::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.lives = lives_;
    st.state = (uint8_t)state_;

    int alive = 0;
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (enemies_[i].active) alive++;
    }
    st.progress = (uint8_t)(((MAX_ENEMIES - alive) * 100) / MAX_ENEMIES);
    return st;
}

} // namespace arcade
