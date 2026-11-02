// game_005_flappy_bird.cpp —— 飞翔小鸟 16 核心实现
#include "game_005_flappy_bird.h"
#include <string.h>
#include <math.h>

namespace arcade {

static inline uint32_t RandSeed(uint32_t& seed) {
    seed = seed * 1103515245u + 12345u;
    return (seed >> 16) & 0x7FFF;
}

static uint32_t g_flappy_seed = 0x87654321;

Game005FlappyBird::Game005FlappyBird()
    : state_(STATE_TITLE),
      bird_x_(3.0f),
      bird_y_(7.0f),
      bird_vy_(0.0f),
      flap_anim_(false),
      flap_timer_(0.0f),
      score_(0),
      high_score_(0),
      ground_scroll_(0.0f),
      state_timer_(0.0f) {
}

void Game005FlappyBird::SpawnPipe(PipeObstacle& pipe, float start_x) {
    uint32_t r = RandSeed(g_flappy_seed);
    pipe.x = start_x;
    // 缝隙高度：前期 5 像素，得分 > 10 后缩至 4 像素增强挑战
    pipe.gap_height = (score_ > 10) ? 4 : 5;
    // 缝隙 Y 轴区间 2 ~ (13 - gap_height)
    int max_top = 13 - pipe.gap_height;
    pipe.gap_y = 2 + (r % (max_top - 2 + 1));
    pipe.scored = false;
}

void Game005FlappyBird::Init() {
    Reset();
}

void Game005FlappyBird::Reset() {
    state_ = STATE_PLAYING;
    bird_x_ = 3.0f;
    bird_y_ = 6.0f;
    bird_vy_ = -6.0f; // 开局向上微扑
    flap_anim_ = false;
    flap_timer_ = 0.0f;
    score_ = 0;
    ground_scroll_ = 0.0f;
    state_timer_ = 0.0f;

    // 两根管道循环轮替，间距 10 像素
    SpawnPipe(pipes_[0], 16.0f);
    SpawnPipe(pipes_[1], 26.0f);
}

void Game005FlappyBird::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt > 0.05f) dt = 0.05f;
    state_timer_ += dt;

    if (state_ == STATE_TITLE) {
        // 标题画面：微弱悬停正弦波
        bird_y_ = 6.5f + sinf(state_timer_ * 4.0f) * 1.5f;
        ground_scroll_ += 4.0f * dt;
        if (ground_scroll_ >= 16.0f) ground_scroll_ -= 16.0f;

        if (keys_pressed & (KEY_START | KEY_A | KEY_UP | KEY_DOWN | KEY_B)) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_GAMEOVER) {
        // 游戏结束坠落倒地
        if (bird_y_ < 13.0f) {
            bird_vy_ += 35.0f * dt;
            bird_y_ += bird_vy_ * dt;
            if (bird_y_ > 13.0f) bird_y_ = 13.0f;
        }
        if (state_timer_ > 0.5f && (keys_pressed & (KEY_START | KEY_A | KEY_UP | KEY_B))) {
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
        // 暂停判定
        if (keys_pressed & KEY_START) {
            state_ = STATE_PAUSED;
            return;
        }

        // 单键拍翅脉冲：任意按键轻点即上升
        const uint16_t tap_mask = KEY_A | KEY_UP | KEY_B | KEY_SELECT | KEY_LEFT | KEY_RIGHT;
        if (keys_pressed & tap_mask) {
            bird_vy_ = -11.0f; // 向上瞬间冲量
            flap_anim_ = true;
            flap_timer_ = 0.15f;
        }

        if (flap_timer_ > 0.0f) {
            flap_timer_ -= dt;
            if (flap_timer_ <= 0.0f) flap_anim_ = false;
        }

        // 恒定重力
        const float gravity = 32.0f;
        bird_vy_ += gravity * dt;
        if (bird_vy_ > 14.0f) bird_vy_ = 14.0f; // 终端速度

        bird_y_ += bird_vy_ * dt;

        // 管道向左卷轴推进
        const float pipe_speed = 5.0f;
        ground_scroll_ += pipe_speed * dt;
        if (ground_scroll_ >= 16.0f) ground_scroll_ -= 16.0f;

        for (int i = 0; i < kMaxPipes; ++i) {
            pipes_[i].x -= pipe_speed * dt;

            // 越过小鸟计分 (小鸟 x 在 3.0，管道宽 2，管道右缘经过 x=3 即算得分)
            if (!pipes_[i].scored && pipes_[i].x + 2.0f < bird_x_) {
                pipes_[i].scored = true;
                score_++;
                if (score_ > high_score_) high_score_ = score_;
            }

            // 移出左边界后在右侧循环重现
            if (pipes_[i].x < -3.0f) {
                // 找到另一根管道的 X，在其后方 10~11 像素处生成
                int other = (i == 0) ? 1 : 0;
                float new_x = pipes_[other].x + 10.5f;
                if (new_x < 16.0f) new_x = 16.0f;
                SpawnPipe(pipes_[i], new_x);
            }
        }

        // 碰撞检测 (小鸟占据 [x, x+1.8] × [y, y+1.8])
        float bx1 = bird_x_;
        float bx2 = bird_x_ + 1.8f;
        float by1 = bird_y_;
        float by2 = bird_y_ + 1.8f;

        // 触碰天花板或触碰地面草坪 (y >= 13.0) 死亡
        if (by1 < 0.0f || by2 >= 13.5f) {
            state_ = STATE_GAMEOVER;
            state_timer_ = 0.0f;
            return;
        }

        // 管道碰撞箱检测 (管道宽 2 像素)
        for (int i = 0; i < kMaxPipes; ++i) {
            float px1 = pipes_[i].x;
            float px2 = pipes_[i].x + 2.0f;

            // 水平重叠
            if (bx2 >= px1 && bx1 <= px2) {
                float gap_top = (float)pipes_[i].gap_y;
                float gap_bottom = gap_top + (float)pipes_[i].gap_height;

                // 若不在安全缝隙范围内，即撞管死亡
                if (by1 < gap_top || by2 > gap_bottom) {
                    state_ = STATE_GAMEOVER;
                    state_timer_ = 0.0f;
                    return;
                }
            }
        }
    }
}

void Game005FlappyBird::DrawBird(uint8_t* fb, int bx, int by, bool flap_up) {
    // 2x2 亮黄色小鸟 + 白眼黑瞳 + 红色鸟喙
    for (int dy = 0; dy < 2; ++dy) {
        for (int dx = 0; dx < 2; ++dx) {
            int x = bx + dx;
            int y = by + dy;
            if (x >= 0 && x < 16 && y >= 0 && y < 16) {
                int idx = (y * 16 + x) * 3;
                if (dy == 0) {
                    if (dx == 0) {
                        // 头部羽毛 (亮黄)
                        fb[idx + 0] = 241; fb[idx + 1] = 196; fb[idx + 2] = 15;
                    } else {
                        // 眼睛高光白点
                        fb[idx + 0] = 255; fb[idx + 1] = 255; fb[idx + 2] = 255;
                    }
                } else {
                    if (dx == 0) {
                        // 翅膀 (拍打时略浅色)
                        if (flap_up) {
                            fb[idx + 0] = 243; fb[idx + 1] = 156; fb[idx + 2] = 18;
                        } else {
                            fb[idx + 0] = 230; fb[idx + 1] = 126; fb[idx + 2] = 34;
                        }
                    } else {
                        // 红色鸟嘴
                        fb[idx + 0] = 231; fb[idx + 1] = 76; fb[idx + 2] = 60;
                    }
                }
            }
        }
    }
}

void Game005FlappyBird::Render(uint8_t* fb_rgb24) {
    // 1. 经典 NES 晴空蓝背景
    for (int y = 0; y < 14; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            // 垂直微渐变天蓝色
            fb_rgb24[idx + 0] = 52;
            fb_rgb24[idx + 1] = 152 + (y * 3);
            fb_rgb24[idx + 2] = 219;
        }
    }

    // 2. 底部地面草地层 (y = 14, 15)
    for (int x = 0; x < 16; ++x) {
        int idx14 = (14 * 16 + x) * 3;
        int idx15 = (15 * 16 + x) * 3;
        // y=14 绿色草坪顶沿
        fb_rgb24[idx14 + 0] = 46; fb_rgb24[idx14 + 1] = 204; fb_rgb24[idx14 + 2] = 113;
        // y=15 泥土暖褐色
        fb_rgb24[idx15 + 0] = 211; fb_rgb24[idx15 + 1] = 84; fb_rgb24[idx15 + 2] = 0;
    }

    // 3. 绘制上下对称的翡翠绿管道柱
    for (int i = 0; i < kMaxPipes; ++i) {
        int px = (int)roundf(pipes_[i].x);
        int gap_y = pipes_[i].gap_y;
        int gap_h = pipes_[i].gap_height;

        // 管道占据 2 像素宽 (px, px+1)
        for (int dx = 0; dx < 2; ++dx) {
            int x = px + dx;
            if (x >= 0 && x < 16) {
                // 上半截管道 (从 y=0 到 gap_y-1)
                for (int y = 0; y < gap_y; ++y) {
                    int idx = (y * 16 + x) * 3;
                    if (y == gap_y - 1) {
                        // 管道口凸沿高光
                        fb_rgb24[idx + 0] = 39; fb_rgb24[idx + 1] = 174; fb_rgb24[idx + 2] = 96;
                    } else {
                        // 管道身 (左浅右深增加立体感)
                        if (dx == 0) {
                            fb_rgb24[idx + 0] = 46; fb_rgb24[idx + 1] = 204; fb_rgb24[idx + 2] = 113;
                        } else {
                            fb_rgb24[idx + 0] = 34; fb_rgb24[idx + 1] = 153; fb_rgb24[idx + 2] = 84;
                        }
                    }
                }

                // 下半截管道 (从 gap_y + gap_h 到 y=13)
                for (int y = gap_y + gap_h; y < 14; ++y) {
                    int idx = (y * 16 + x) * 3;
                    if (y == gap_y + gap_h) {
                        // 管道口凸沿高光
                        fb_rgb24[idx + 0] = 39; fb_rgb24[idx + 1] = 174; fb_rgb24[idx + 2] = 96;
                    } else {
                        if (dx == 0) {
                            fb_rgb24[idx + 0] = 46; fb_rgb24[idx + 1] = 204; fb_rgb24[idx + 2] = 113;
                        } else {
                            fb_rgb24[idx + 0] = 34; fb_rgb24[idx + 1] = 153; fb_rgb24[idx + 2] = 84;
                        }
                    }
                }
            }
        }
    }

    // 4. 绘制主角小鸟
    int bx = (int)roundf(bird_x_);
    int by = (int)roundf(bird_y_);
    DrawBird(fb_rgb24, bx, by, flap_anim_);

    // 5. 死亡闪红或暂停提示
    if (state_ == STATE_GAMEOVER) {
        // 顶部警示红边
        for (int x = 0; x < 16; ++x) {
            int idx = (0 * 16 + x) * 3;
            fb_rgb24[idx + 0] = 231; fb_rgb24[idx + 1] = 76; fb_rgb24[idx + 2] = 60;
        }
    } else if (state_ == STATE_PAUSED) {
        // 暂停两条白线
        for (int y = 5; y <= 8; ++y) {
            int idx1 = (y * 16 + 6) * 3;
            int idx2 = (y * 16 + 9) * 3;
            fb_rgb24[idx1 + 0] = fb_rgb24[idx1 + 1] = fb_rgb24[idx1 + 2] = 250;
            fb_rgb24[idx2 + 0] = fb_rgb24[idx2 + 1] = fb_rgb24[idx2 + 2] = 250;
        }
    }
}

CartridgeStatus Game005FlappyBird::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.lives = (state_ == STATE_GAMEOVER) ? 0 : 1;
    st.state = (uint8_t)state_;
    st.progress = (uint8_t)(score_ > 255 ? 255 : score_);
    return st;
}

} // namespace arcade
