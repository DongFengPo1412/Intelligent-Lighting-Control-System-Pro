// game_028_danmaku.cpp —— 东方蜂群弹幕 1997 核心实现
#include "game_028_danmaku.h"
#include <string.h>
#include <math.h>
#include <stdlib.h>

namespace arcade {

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

Game028Danmaku::Game028Danmaku()
    : state_(STATE_TITLE),
      player_x_(7.5f),
      player_y_(13.5f),
      lives_(3),
      bombs_(2),
      graze_count_(0),
      shoot_timer_(0.0f),
      bomb_flash_timer_(0.0f),
      score_(0),
      high_score_(0),
      state_timer_(0.0f) {
}

void Game028Danmaku::InitBoss() {
    boss_.active = true;
    boss_.x = 7.5f;
    boss_.y = 2.5f;
    boss_.hp = 100;
    boss_.max_hp = 100;
    boss_.pattern_timer = 0.0f;
    boss_.pattern_phase = 0;

    for (int i = 0; i < MAX_BULLETS; ++i) {
        bullets_[i].active = false;
    }

    player_x_ = 7.5f;
    player_y_ = 13.5f;
    lives_ = 3;
    bombs_ = 2;
    graze_count_ = 0;
    shoot_timer_ = 0.0f;
    bomb_flash_timer_ = 0.0f;
}

void Game028Danmaku::Init() {
    Reset();
}

void Game028Danmaku::Reset() {
    state_ = STATE_PLAYING;
    score_ = 0;
    state_timer_ = 0.0f;
    InitBoss();
}

void Game028Danmaku::FirePlayerShot() {
    if (shoot_timer_ > 0.0f) return;
    shoot_timer_ = 0.15f;

    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (!bullets_[i].active) {
            bullets_[i].active = true;
            bullets_[i].x = player_x_;
            bullets_[i].y = player_y_ - 0.5f;
            bullets_[i].vx = 0.0f;
            bullets_[i].vy = -15.0f;
            bullets_[i].is_player = true;
            bullets_[i].grazed = false;
            break;
        }
    }
}

void Game028Danmaku::FireSpiralPattern(float angle_rad) {
    float speed = 4.2f;
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (!bullets_[i].active) {
            bullets_[i].active = true;
            bullets_[i].x = boss_.x;
            bullets_[i].y = boss_.y;
            bullets_[i].vx = speed * cosf(angle_rad);
            bullets_[i].vy = speed * sinf(angle_rad);
            bullets_[i].is_player = false;
            bullets_[i].grazed = false;
            break;
        }
    }
}

void Game028Danmaku::FireRingPattern(int count) {
    float speed = 3.8f;
    float step = (2.0f * (float)M_PI) / (float)count;

    for (int c = 0; c < count; ++c) {
        float rad = (float)c * step;
        for (int i = 0; i < MAX_BULLETS; ++i) {
            if (!bullets_[i].active) {
                bullets_[i].active = true;
                bullets_[i].x = boss_.x;
                bullets_[i].y = boss_.y;
                bullets_[i].vx = speed * cosf(rad);
                bullets_[i].vy = speed * sinf(rad);
                bullets_[i].is_player = false;
                bullets_[i].grazed = false;
                break;
            }
        }
    }
}

void Game028Danmaku::UseBomb() {
    if (bombs_ <= 0) return;
    bombs_--;
    bomb_flash_timer_ = 0.25f;

    // 清屏消灭所有敌方子弹
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (bullets_[i].active && !bullets_[i].is_player) {
            bullets_[i].active = false;
            score_ += 10;
        }
    }

    // 重创 Boss
    boss_.hp -= 25;
    score_ += 500;
    if (score_ > high_score_) high_score_ = score_;

    if (boss_.hp <= 0) {
        boss_.active = false;
        state_ = STATE_VICTORY;
        state_timer_ = 0.0f;
    }
}

void Game028Danmaku::UpdateBoss(float dt) {
    if (!boss_.active) return;

    // Boss 水平正弦巡弋
    boss_.x = 7.5f + sinf(state_timer_ * 2.0f) * 3.5f;

    boss_.pattern_timer += dt;

    // 阶段 0: 几何螺旋弹幕
    if (boss_.pattern_phase == 0) {
        static float spiral_angle = 0.0f;
        if (boss_.pattern_timer >= 0.12f) {
            boss_.pattern_timer = 0.0f;
            FireSpiralPattern(spiral_angle);
            FireSpiralPattern(spiral_angle + (float)M_PI); // 双螺旋
            spiral_angle += 0.45f;
        }
        if (state_timer_ >= 12.0f && boss_.pattern_phase == 0) {
            boss_.pattern_phase = 1;
        }
    } else {
        // 阶段 1: 同心环爆震弹幕
        if (boss_.pattern_timer >= 1.4f) {
            boss_.pattern_timer = 0.0f;
            FireRingPattern(8);
        }
    }
}

void Game028Danmaku::UpdateBullets(float dt) {
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (!bullets_[i].active) continue;

        bullets_[i].x += bullets_[i].vx * dt;
        bullets_[i].y += bullets_[i].vy * dt;

        // 出界销毁
        if (bullets_[i].x < -1.0f || bullets_[i].x > 17.0f ||
            bullets_[i].y < -1.0f || bullets_[i].y > 17.0f) {
            bullets_[i].active = false;
            continue;
        }

        if (bullets_[i].is_player) {
            // 命中 Boss 判定
            if (boss_.active) {
                float dist = fabsf(bullets_[i].x - boss_.x) + fabsf(bullets_[i].y - boss_.y);
                if (dist <= 1.4f) {
                    bullets_[i].active = false;
                    boss_.hp--;
                    score_ += 15;
                    if (score_ > high_score_) high_score_ = score_;

                    if (boss_.hp <= 0) {
                        boss_.active = false;
                        state_ = STATE_VICTORY;
                        state_timer_ = 0.0f;
                        score_ += 2000;
                        if (score_ > high_score_) high_score_ = score_;
                        return;
                    }
                }
            }
        } else {
            // 敌方子弹对玩家判定
            float dist = fabsf(bullets_[i].x - player_x_) + fabsf(bullets_[i].y - player_y_);

            // 1. 致命命中判定 (严格 1 像素核心 Hitbox，dist <= 0.65f)
            if (dist <= 0.65f) {
                bullets_[i].active = false;
                lives_--;
                if (lives_ <= 0) {
                    state_ = STATE_GAMEOVER;
                    state_timer_ = 0.0f;
                    return;
                } else {
                    // 扣命后原地清弹提供短暂无敌
                    for (int b = 0; b < MAX_BULLETS; ++b) {
                        if (!bullets_[b].is_player) bullets_[b].active = false;
                    }
                    player_x_ = 7.5f;
                    player_y_ = 13.5f;
                    return;
                }
            }
            // 2. 擦弹 (Graze) 判定 (0.65f < dist <= 1.4f)
            else if (dist <= 1.4f && !bullets_[i].grazed) {
                bullets_[i].grazed = true;
                graze_count_++;
                score_ += 20;
                if (score_ > high_score_) high_score_ = score_;
            }
        }
    }
}

void Game028Danmaku::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
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

        if (shoot_timer_ > 0.0f) shoot_timer_ -= dt;
        if (bomb_flash_timer_ > 0.0f) bomb_flash_timer_ -= dt;

        // 1. 玩家高精度微操平移 (八向灵动位移)
        float speed = 7.2f;
        if (keys_down & KEY_LEFT) player_x_ -= speed * dt;
        if (keys_down & KEY_RIGHT) player_x_ += speed * dt;
        if (keys_down & KEY_UP) player_y_ -= speed * dt;
        if (keys_down & KEY_DOWN) player_y_ += speed * dt;

        if (player_x_ < 0.5f) player_x_ = 0.5f;
        if (player_x_ > 14.5f) player_x_ = 14.5f;
        if (player_y_ < 4.0f) player_y_ = 4.0f; // 战机活动于中下半区
        if (player_y_ > 14.5f) player_y_ = 14.5f;

        // 2. 射击与炸弹控制
        if (keys_down & KEY_A) {
            FirePlayerShot();
        }
        if (keys_pressed & KEY_B) {
            UseBomb();
        }

        // 3. 更新 Boss 与弹幕
        UpdateBoss(dt);
        UpdateBullets(dt);
    }
}

void Game028Danmaku::Render(uint8_t* fb_rgb24) {
    memset(fb_rgb24, 0, 16 * 16 * 3);

    // 1. 炸弹清屏全屏闪白特效
    if (bomb_flash_timer_ > 0.0f) {
        for (int i = 0; i < 16 * 16 * 3; ++i) {
            fb_rgb24[i] = 180;
        }
    }

    // 2. 绘制 Boss (猩红机械战舰核心 [231, 76, 60] 带双翼紫晶 [155, 89, 182])
    if (boss_.active) {
        int bx = (int)roundf(boss_.x);
        int by = (int)roundf(boss_.y);
        if (bx >= 0 && bx < 16 && by >= 0 && by < 16) {
            int bidx = (by * 16 + bx) * 3;
            fb_rgb24[bidx + 0] = 231; fb_rgb24[bidx + 1] = 76; fb_rgb24[bidx + 2] = 60;
            if (bx > 0) {
                int lidx = (by * 16 + (bx - 1)) * 3;
                fb_rgb24[lidx + 0] = 155; fb_rgb24[lidx + 1] = 89; fb_rgb24[lidx + 2] = 182;
            }
            if (bx < 15) {
                int ridx = (by * 16 + (bx + 1)) * 3;
                fb_rgb24[ridx + 0] = 155; fb_rgb24[ridx + 1] = 89; fb_rgb24[ridx + 2] = 182;
            }
        }
    }

    // 3. 绘制弹幕粒子 (高密等离子红粉光流 [255, 105, 180], 玩家光子蓝白 [255, 255, 255])
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (!bullets_[i].active) continue;

        int bx = (int)roundf(bullets_[i].x);
        int by = (int)roundf(bullets_[i].y);
        if (bx >= 0 && bx < 16 && by >= 0 && by < 16) {
            int idx = (by * 16 + bx) * 3;
            if (bullets_[i].is_player) {
                fb_rgb24[idx + 0] = 255; fb_rgb24[idx + 1] = 255; fb_rgb24[idx + 2] = 255;
            } else {
                fb_rgb24[idx + 0] = 255; fb_rgb24[idx + 1] = 40;  fb_rgb24[idx + 2] = 120; // 艳粉诱爆弹
            }
        }
    }

    // 4. 绘制玩家战机 (两侧青翼 [0, 200, 255], 核心红点 1 像素判定点 [255, 50, 50])
    if (lives_ > 0) {
        int px = (int)roundf(player_x_);
        int py = (int)roundf(player_y_);

        if (px >= 0 && px < 16 && py >= 0 && py < 16) {
            // 机翼
            if (px > 0) {
                int lidx = (py * 16 + (px - 1)) * 3;
                fb_rgb24[lidx + 0] = 0; fb_rgb24[lidx + 1] = 200; fb_rgb24[lidx + 2] = 255;
            }
            if (px < 15) {
                int ridx = (py * 16 + (px + 1)) * 3;
                fb_rgb24[ridx + 0] = 0; fb_rgb24[ridx + 1] = 200; fb_rgb24[ridx + 2] = 255;
            }
            // 核心判定点
            int cidx = (py * 16 + px) * 3;
            fb_rgb24[cidx + 0] = 255; fb_rgb24[cidx + 1] = 50; fb_rgb24[cidx + 2] = 50;
        }
    }

    // 5. 顶部 HUD: 生命指示 (白点) 与 Bomb 储备 (绿点) 与 Boss 血条 (暗红点)
    for (int i = 0; i < lives_; ++i) {
        int idx = (0 * 16 + i) * 3;
        fb_rgb24[idx + 0] = 255; fb_rgb24[idx + 1] = 255; fb_rgb24[idx + 2] = 255;
    }
    for (int i = 0; i < bombs_; ++i) {
        int idx = (0 * 16 + (i + 4)) * 3;
        fb_rgb24[idx + 0] = 46; fb_rgb24[idx + 1] = 204; fb_rgb24[idx + 2] = 113;
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

CartridgeStatus Game028Danmaku::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.lives = lives_;
    st.state = (uint8_t)state_;
    // 进度基于 Boss 剩余血量
    int prog = ((boss_.max_hp - boss_.hp) * 100) / boss_.max_hp;
    if (prog < 0) prog = 0;
    if (prog > 100) prog = 100;
    st.progress = (uint8_t)prog;
    return st;
}

} // namespace arcade
