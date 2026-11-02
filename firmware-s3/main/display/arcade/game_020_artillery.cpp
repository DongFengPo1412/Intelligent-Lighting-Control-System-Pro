// game_020_artillery.cpp —— 像素百战天虫 1980 核心实现
#include "game_020_artillery.h"
#include <string.h>
#include <math.h>
#include <stdlib.h>

namespace arcade {

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

Game020Artillery::Game020Artillery()
    : state_(STATE_TITLE),
      wind_(0.0f),
      charging_power_(false),
      turn_player_(true),
      turn_timer_(0.0f),
      score_(0),
      high_score_(0),
      state_timer_(0.0f) {
    shell_.active = false;
}

void Game020Artillery::GenerateTerrain() {
    // 随机起伏山脉 (中央隆起山头，两侧平缓)
    for (int x = 0; x < 16; ++x) {
        float normalized = (float)x / 15.0f;
        // 中间隆起
        float hill = sinf(normalized * (float)M_PI) * 4.0f;
        int h = 13 - (int)roundf(hill) + (rand() % 2);
        if (h < 8) h = 8;
        if (h > 14) h = 14;
        terrain_[x] = (uint8_t)h;
    }

    // 随机侧风 (-2.0 ~ +2.0)
    wind_ = ((rand() % 41) - 20) / 10.0f;

    // 放置双方坦克
    player_.x = 2;
    player_.y = terrain_[2] - 1;
    player_.hp = 3;
    player_.angle_deg = 45.0f;
    player_.power = 50.0f;

    enemy_.x = 13;
    enemy_.y = terrain_[13] - 1;
    enemy_.hp = 3;
    enemy_.angle_deg = 45.0f;
    enemy_.power = 50.0f;

    turn_player_ = true;
    turn_timer_ = 0.0f;
    charging_power_ = false;
    shell_.active = false;
}

void Game020Artillery::Init() {
    Reset();
}

void Game020Artillery::Reset() {
    state_ = STATE_PLAYING;
    score_ = 0;
    state_timer_ = 0.0f;
    GenerateTerrain();
}

void Game020Artillery::FireShell(bool from_player) {
    shell_.active = true;
    shell_.is_player = from_player;

    if (from_player) {
        shell_.x = (float)player_.x;
        shell_.y = (float)player_.y - 0.5f;

        float rad = player_.angle_deg * (float)M_PI / 180.0f;
        float speed = (player_.power / 100.0f) * 16.5f;
        shell_.vx = speed * cosf(rad); // 向右飞
        shell_.vy = -speed * sinf(rad);// 向上升
    } else {
        shell_.x = (float)enemy_.x;
        shell_.y = (float)enemy_.y - 0.5f;

        float rad = enemy_.angle_deg * (float)M_PI / 180.0f;
        float speed = (enemy_.power / 100.0f) * 16.5f;
        shell_.vx = -speed * cosf(rad);// 向左飞
        shell_.vy = -speed * sinf(rad);
    }
}

void Game020Artillery::Explode(float ex, float ey, bool from_player) {
    shell_.active = false;
    int gx = (int)roundf(ex);

    // 炸碎弹坑 (地形凹陷加深 1~2 格)
    if (gx >= 0 && gx < 16) {
        if (terrain_[gx] < 15) terrain_[gx]++;
        if (gx > 0 && terrain_[gx - 1] < 15) terrain_[gx - 1]++;
        if (gx < 15 && terrain_[gx + 1] < 15) terrain_[gx + 1]++;
    }

    // 坦克受损检测
    if (from_player) {
        float dist = fabsf(ex - (float)enemy_.x) + fabsf(ey - (float)enemy_.y);
        if (dist <= 1.8f) { // 命中或近距离爆风
            enemy_.hp--;
            score_ += 150;
            if (score_ > high_score_) high_score_ = score_;

            if (enemy_.hp <= 0) {
                state_ = STATE_VICTORY;
                state_timer_ = 0.0f;
                return;
            }
        }
        // 轮换回合给 AI
        turn_player_ = false;
        turn_timer_ = 0.0f;
    } else {
        float dist = fabsf(ex - (float)player_.x) + fabsf(ey - (float)player_.y);
        if (dist <= 1.8f) {
            player_.hp--;
            if (player_.hp <= 0) {
                state_ = STATE_GAMEOVER;
                state_timer_ = 0.0f;
                return;
            }
        }
        // 轮换回合给玩家，并变换风力
        turn_player_ = true;
        turn_timer_ = 0.0f;
        wind_ = ((rand() % 41) - 20) / 10.0f;
    }

    // 确保坦克由于地形凹陷而下沉落稳
    player_.y = terrain_[player_.x] - 1;
    enemy_.y = terrain_[enemy_.x] - 1;
}

void Game020Artillery::AIShoot() {
    // AI 弹道反算预估
    float dx = (float)(enemy_.x - player_.x); // 约 11 格
    enemy_.angle_deg = 45.0f + (float)(rand() % 15 - 7);

    // 考虑侧风影响修正蓄力
    float estimated_power = 62.0f + (wind_ * 4.0f) + (float)(rand() % 11 - 5);
    if (estimated_power < 30.0f) estimated_power = 30.0f;
    if (estimated_power > 95.0f) estimated_power = 95.0f;
    enemy_.power = estimated_power;

    FireShell(false);
}

void Game020Artillery::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
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

        // 1. 炮弹飞行物理 (重力与风力驱动)
        if (shell_.active) {
            shell_.vx += wind_ * 2.5f * dt;
            shell_.vy += 11.5f * dt; // 重力下坠加速度
            shell_.x += shell_.vx * dt;
            shell_.y += shell_.vy * dt;

            // 出界判定
            if (shell_.x < -1.0f || shell_.x > 16.5f || shell_.y > 15.5f) {
                shell_.active = false;
                if (shell_.is_player) {
                    turn_player_ = false;
                    turn_timer_ = 0.0f;
                } else {
                    turn_player_ = true;
                    turn_timer_ = 0.0f;
                    wind_ = ((rand() % 41) - 20) / 10.0f;
                }
                return;
            }

            // 撞地检测
            int check_gx = (int)roundf(shell_.x);
            if (check_gx >= 0 && check_gx < 16) {
                if (shell_.y >= (float)terrain_[check_gx]) {
                    Explode(shell_.x, shell_.y, shell_.is_player);
                    return;
                }
            }
            return;
        }

        // 2. 玩家回合操作
        if (turn_player_) {
            // 仰角微调
            if (keys_down & KEY_LEFT) {
                player_.angle_deg -= 35.0f * dt;
                if (player_.angle_deg < 15.0f) player_.angle_deg = 15.0f;
            } else if (keys_down & KEY_RIGHT) {
                player_.angle_deg += 35.0f * dt;
                if (player_.angle_deg > 75.0f) player_.angle_deg = 75.0f;
            }

            // 蓄力控制: 按住 A 充能，松开发射
            if (keys_down & KEY_A) {
                charging_power_ = true;
                player_.power += 60.0f * dt;
                if (player_.power > 100.0f) player_.power = 20.0f; // 循环过载
            } else if (charging_power_) {
                charging_power_ = false;
                FireShell(true);
            }
        } else {
            // 3. AI 回合等待与发射
            turn_timer_ += dt;
            if (turn_timer_ >= 0.8f) {
                turn_timer_ = 0.0f;
                AIShoot();
            }
        }
    }
}

void Game020Artillery::Render(uint8_t* fb_rgb24) {
    memset(fb_rgb24, 0, 16 * 16 * 3);

    // 1. 绘制山脉地形 (泥土深褐 + 草甸嫩绿表层)
    for (int x = 0; x < 16; ++x) {
        int surface_y = terrain_[x];
        for (int y = surface_y; y < 16; ++y) {
            int idx = (y * 16 + x) * 3;
            if (y == surface_y) {
                fb_rgb24[idx + 0] = 39;  fb_rgb24[idx + 1] = 174; fb_rgb24[idx + 2] = 96;  // 草甸绿
            } else {
                fb_rgb24[idx + 0] = 120; fb_rgb24[idx + 1] = 66;  fb_rgb24[idx + 2] = 18;  // 泥土褐
            }
        }
    }

    // 2. 绘制玩家坦克 (青蓝光辉 [0, 255, 255])
    if (player_.hp > 0) {
        int idx = (player_.y * 16 + player_.x) * 3;
        fb_rgb24[idx + 0] = 0; fb_rgb24[idx + 1] = 255; fb_rgb24[idx + 2] = 255;
    }

    // 3. 绘制敌方坦克 (猩红战车 [231, 76, 60])
    if (enemy_.hp > 0) {
        int idx = (enemy_.y * 16 + enemy_.x) * 3;
        fb_rgb24[idx + 0] = 231; fb_rgb24[idx + 1] = 76; fb_rgb24[idx + 2] = 60;
    }

    // 4. 绘制飞行中炮弹 (耀眼白金 [255, 255, 200])
    if (shell_.active) {
        int sx = (int)roundf(shell_.x);
        int sy = (int)roundf(shell_.y);
        if (sx >= 0 && sx < 16 && sy >= 0 && sy < 16) {
            int idx = (sy * 16 + sx) * 3;
            fb_rgb24[idx + 0] = 255; fb_rgb24[idx + 1] = 255; fb_rgb24[idx + 2] = 220;
        }
    }

    // 5. 顶部 HUD: 双方生命 (左侧P1蓝心，右侧AI红心) 与风向标
    for (int i = 0; i < player_.hp; ++i) {
        int idx = (0 * 16 + (i + 1)) * 3;
        fb_rgb24[idx + 0] = 0; fb_rgb24[idx + 1] = 255; fb_rgb24[idx + 2] = 255;
    }
    for (int i = 0; i < enemy_.hp; ++i) {
        int idx = (0 * 16 + (14 - i)) * 3;
        fb_rgb24[idx + 0] = 231; fb_rgb24[idx + 1] = 76; fb_rgb24[idx + 2] = 60;
    }
    // 中央风向点 (x=7~8)
    int wind_center = (wind_ > 0.3f) ? 8 : (wind_ < -0.3f) ? 7 : 7;
    int idx_wind = (0 * 16 + wind_center) * 3;
    fb_rgb24[idx_wind + 0] = 241; fb_rgb24[idx_wind + 1] = 196; fb_rgb24[idx_wind + 2] = 15;

    // 6. 特效渲染
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

CartridgeStatus Game020Artillery::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.lives = player_.hp;
    st.state = (uint8_t)state_;
    st.progress = (uint8_t)(((3 - enemy_.hp) * 100) / 3);
    return st;
}

} // namespace arcade
