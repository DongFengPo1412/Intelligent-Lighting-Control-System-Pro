// game_004_doodle_jump.cpp —— 涂鸦跳跃 16 核心实现
#include "game_004_doodle_jump.h"
#include <string.h>
#include <math.h>

namespace arcade {

static inline uint32_t PseudoRand(uint32_t& seed) {
    seed = seed * 1664525u + 1013904223u;
    return seed;
}

static uint32_t g_seed = 0x12345678;

Game004DoodleJump::Game004DoodleJump()
    : state_(STATE_TITLE),
      player_x_(7.0f),
      player_y_(11.0f),
      player_vx_(0.0f),
      player_vy_(0.0f),
      facing_right_(true),
      camera_altitude_(0.0f),
      score_(0),
      high_score_(0),
      state_timer_(0.0f) {
}

void Game004DoodleJump::SpawnPlatform(Platform& p, float min_y, float max_y) {
    uint32_t r = PseudoRand(g_seed);
    p.x = 1.0f + (r % 12); // x 范围 1 ~ 12，留出板宽 3
    p.y = min_y + ((r >> 4) % (int)(max_y - min_y + 1));
    p.broken = false;
    p.vx = 0.0f;

    // 随高度概率提升特殊板
    uint32_t type_roll = (r >> 12) % 100;
    if (camera_altitude_ < 50.0f) {
        if (type_roll < 80) p.type = PLAT_NORMAL;
        else if (type_roll < 95) p.type = PLAT_SPRING;
        else p.type = PLAT_MOVING;
    } else {
        if (type_roll < 45) p.type = PLAT_NORMAL;
        else if (type_roll < 70) p.type = PLAT_MOVING;
        else if (type_roll < 85) p.type = PLAT_SPRING;
        else p.type = PLAT_FRAGILE;
    }

    if (p.type == PLAT_MOVING) {
        p.vx = ((r >> 20) & 1) ? 2.5f : -2.5f;
    }
}

void Game004DoodleJump::Init() {
    Reset();
}

void Game004DoodleJump::Reset() {
    state_ = STATE_PLAYING;
    player_x_ = 7.0f;
    player_y_ = 10.0f;
    player_vx_ = 0.0f;
    player_vy_ = -12.0f; // 开局起跳
    facing_right_ = true;
    camera_altitude_ = 0.0f;
    score_ = 0;
    state_timer_ = 0.0f;

    // 初始化底部起手板
    platforms_[0].x = 6.0f;
    platforms_[0].y = 13.0f;
    platforms_[0].vx = 0.0f;
    platforms_[0].type = PLAT_NORMAL;
    platforms_[0].broken = false;

    // 其余跳板依次阶梯向上排列
    for (int i = 1; i < kMaxPlatforms; ++i) {
        float min_y = 13.0f - (i * 2.5f);
        float max_y = min_y + 1.0f;
        SpawnPlatform(platforms_[i], min_y, max_y);
    }
}

void Game004DoodleJump::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt > 0.05f) dt = 0.05f; // 防大卡顿
    state_timer_ += dt;

    if (state_ == STATE_TITLE) {
        // 标题画面：轻微自动弹跳演示
        player_vy_ += 24.0f * dt;
        player_y_ += player_vy_ * dt;
        if (player_y_ >= 12.0f) {
            player_y_ = 12.0f;
            player_vy_ = -10.0f;
        }
        if (keys_pressed & (KEY_START | KEY_A | KEY_LEFT | KEY_RIGHT)) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_GAMEOVER) {
        if (keys_pressed & (KEY_START | KEY_A | KEY_LEFT | KEY_RIGHT)) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_PLAYING) {
        // 暂停控制
        if (keys_pressed & KEY_START) {
            state_ = STATE_PAUSED;
            return;
        }

        // 左右横移控制
        const float move_accel = 24.0f;
        const float max_vx = 7.0f;
        const float friction = 12.0f;

        if (keys_down & KEY_LEFT) {
            player_vx_ -= move_accel * dt;
            facing_right_ = false;
        } else if (keys_down & KEY_RIGHT) {
            player_vx_ += move_accel * dt;
            facing_right_ = true;
        } else {
            if (player_vx_ > 0.0f) {
                player_vx_ -= friction * dt;
                if (player_vx_ < 0.0f) player_vx_ = 0.0f;
            } else if (player_vx_ < 0.0f) {
                player_vx_ += friction * dt;
                if (player_vx_ > 0.0f) player_vx_ = 0.0f;
            }
        }

        if (player_vx_ > max_vx) player_vx_ = max_vx;
        if (player_vx_ < -max_vx) player_vx_ = -max_vx;

        // 重力加速
        const float gravity = 28.0f;
        player_vy_ += gravity * dt;

        float next_x = player_x_ + player_vx_ * dt;
        float next_y = player_y_ + player_vy_ * dt;

        // 左右无限穿屏
        if (next_x < -1.5f) next_x = 15.5f;
        else if (next_x > 15.5f) next_x = -1.5f;
        player_x_ = next_x;

        // 移动跳板更新
        for (int i = 0; i < kMaxPlatforms; ++i) {
            if (platforms_[i].type == PLAT_MOVING && !platforms_[i].broken) {
                platforms_[i].x += platforms_[i].vx * dt;
                if (platforms_[i].x <= 0.0f) {
                    platforms_[i].x = 0.0f;
                    platforms_[i].vx = -platforms_[i].vx;
                } else if (platforms_[i].x >= 13.0f) {
                    platforms_[i].x = 13.0f;
                    platforms_[i].vx = -platforms_[i].vx;
                }
            }
        }

        // 踏板碰撞判定 (仅在下落阶段 player_vy_ > 0 判定脚底落入)
        if (player_vy_ > 0.0f) {
            float feet_old_y = player_y_ + 2.0f;
            float feet_new_y = next_y + 2.0f;

            for (int i = 0; i < kMaxPlatforms; ++i) {
                if (platforms_[i].broken) continue;

                float plat_top = platforms_[i].y;
                float plat_left = platforms_[i].x - 0.8f;
                float plat_right = platforms_[i].x + 3.0f;

                // 水平重叠检测
                if (player_x_ + 1.8f >= plat_left && player_x_ <= plat_right) {
                    // 纵向穿越踏板平面
                    if (feet_old_y <= plat_top + 0.5f && feet_new_y >= plat_top - 0.2f) {
                        next_y = plat_top - 2.0f;

                        if (platforms_[i].type == PLAT_SPRING) {
                            player_vy_ = -20.5f; // 金色弹簧超高反弹
                        } else if (platforms_[i].type == PLAT_FRAGILE) {
                            platforms_[i].broken = true;
                            player_vy_ = -7.5f;  // 碎板轻微反弹后坠毁
                        } else {
                            player_vy_ = -13.5f; // 普通标准反弹
                        }
                        break;
                    }
                }
            }
        }

        player_y_ = next_y;

        // 摄像机跟随向上滚动 (玩家冲入上半屏 line 7 时发生滚动)
        const float scroll_threshold = 7.0f;
        if (player_y_ < scroll_threshold) {
            float dy = scroll_threshold - player_y_;
            player_y_ = scroll_threshold;
            camera_altitude_ += dy;
            score_ = (uint32_t)(camera_altitude_ * 10.0f);
            if (score_ > high_score_) high_score_ = score_;

            // 所有跳板相对下移
            for (int i = 0; i < kMaxPlatforms; ++i) {
                platforms_[i].y += dy;
                // 若超出屏幕底部，在顶部循环生成新跳板
                if (platforms_[i].y > 16.5f) {
                    SpawnPlatform(platforms_[i], -1.5f, 0.5f);
                }
            }
        }

        // 坠落出屏幕底部即判负
        if (player_y_ > 16.5f) {
            state_ = STATE_GAMEOVER;
            state_timer_ = 0.0f;
        }
    } else if (state_ == STATE_PAUSED) {
        if (keys_pressed & KEY_START) {
            state_ = STATE_PLAYING;
        }
    }
}

void Game004DoodleJump::DrawDoodler(uint8_t* fb, int px, int py, bool facing_right) {
    // 角色 2x2 主体 + 视线与鞋子点缀
    for (int dy = 0; dy < 2; ++dy) {
        for (int dx = 0; dx < 2; ++dx) {
            int x = px + dx;
            int y = py + dy;
            if (x >= 0 && x < 16 && y >= 0 && y < 16) {
                int idx = (y * 16 + x) * 3;
                if (dy == 0) {
                    // 头部 (明亮草绿色)
                    fb[idx + 0] = 46;
                    fb[idx + 1] = 204;
                    fb[idx + 2] = 113;
                    // 眼睛高光
                    if ((facing_right && dx == 1) || (!facing_right && dx == 0)) {
                        fb[idx + 0] = 255;
                        fb[idx + 1] = 255;
                        fb[idx + 2] = 255;
                    }
                } else {
                    // 下半身/小靴子 (活力橙)
                    fb[idx + 0] = 230;
                    fb[idx + 1] = 126;
                    fb[idx + 2] = 34;
                }
            }
        }
    }
}

void Game004DoodleJump::Render(uint8_t* fb_rgb24) {
    // 1. 深邃复古午夜蓝背景
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            fb_rgb24[idx + 0] = 10;
            fb_rgb24[idx + 1] = 14;
            fb_rgb24[idx + 2] = 24;
        }
    }

    // 2. 绘制高度星空微光 (随高度缓缓飘动)
    int star_offset = ((int)camera_altitude_) % 16;
    for (int i = 0; i < 4; ++i) {
        int sx = (i * 5 + 3) % 16;
        int sy = (i * 7 + star_offset) % 16;
        int idx = (sy * 16 + sx) * 3;
        fb_rgb24[idx + 0] = 30;
        fb_rgb24[idx + 1] = 45;
        fb_rgb24[idx + 2] = 70;
    }

    // 3. 绘制跳板
    for (int i = 0; i < kMaxPlatforms; ++i) {
        if (platforms_[i].broken) continue;

        int py = (int)roundf(platforms_[i].y);
        int px = (int)roundf(platforms_[i].x);

        if (py >= 0 && py < 16) {
            uint8_t r = 39, g = 174, b = 96; // 普通绿板
            if (platforms_[i].type == PLAT_MOVING) {
                r = 0; g = 210; b = 211;     // 青色移动板
            } else if (platforms_[i].type == PLAT_SPRING) {
                r = 241; g = 196; b = 15;    // 金色弹簧板
            } else if (platforms_[i].type == PLAT_FRAGILE) {
                r = 211; g = 84; b = 0;      // 棕色碎裂板
            }

            for (int dx = 0; dx < 3; ++dx) {
                int x = px + dx;
                if (x >= 0 && x < 16) {
                    int idx = (py * 16 + x) * 3;
                    fb_rgb24[idx + 0] = r;
                    fb_rgb24[idx + 1] = g;
                    fb_rgb24[idx + 2] = b;
                    // 弹簧板中间点白点表示弹簧
                    if (platforms_[i].type == PLAT_SPRING && dx == 1) {
                        fb_rgb24[idx + 0] = 255;
                        fb_rgb24[idx + 1] = 255;
                        fb_rgb24[idx + 2] = 255;
                    }
                }
            }
        }
    }

    // 4. 绘制主角小涂鸦
    int px = (int)roundf(player_x_);
    int py = (int)roundf(player_y_);
    DrawDoodler(fb_rgb24, px, py, facing_right_);

    // 5. 游戏结束或暂停特效
    if (state_ == STATE_GAMEOVER) {
        // 底部红光示警
        for (int x = 0; x < 16; ++x) {
            int idx = (15 * 16 + x) * 3;
            fb_rgb24[idx + 0] = 231;
            fb_rgb24[idx + 1] = 76;
            fb_rgb24[idx + 2] = 60;
        }
    } else if (state_ == STATE_PAUSED) {
        // 屏幕中心暂停双竖杠
        for (int y = 6; y <= 9; ++y) {
            int idx1 = (y * 16 + 6) * 3;
            int idx2 = (y * 16 + 9) * 3;
            fb_rgb24[idx1 + 0] = fb_rgb24[idx1 + 1] = fb_rgb24[idx1 + 2] = 240;
            fb_rgb24[idx2 + 0] = fb_rgb24[idx2 + 1] = fb_rgb24[idx2 + 2] = 240;
        }
    }
}

CartridgeStatus Game004DoodleJump::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.lives = (state_ == STATE_GAMEOVER) ? 0 : 1;
    st.state = (uint8_t)state_;
    st.progress = (uint8_t)(camera_altitude_ > 255.0f ? 255 : camera_altitude_);
    return st;
}

} // namespace arcade
