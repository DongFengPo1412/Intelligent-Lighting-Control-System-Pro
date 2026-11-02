// game_011_frogger.cpp —— 像素青蛙过河 1981 核心实现
#include "game_011_frogger.h"
#include <string.h>
#include <math.h>

namespace arcade {

static const int kHomeX[5] = {1, 4, 7, 10, 13};

Game011Frogger::Game011Frogger()
    : state_(STATE_TITLE),
      frog_x_(7.0f),
      frog_y_(14),
      lives_(3),
      score_(0),
      high_score_(0),
      round_timer_(30.0f),
      state_timer_(0.0f),
      homes_occupied_(0) {
    for (int i = 0; i < kNumHomes; ++i) {
        homes_[i] = false;
    }
}

void Game011Frogger::ResetFrogPosition() {
    frog_x_ = 7.0f;
    frog_y_ = 14;
    round_timer_ = 30.0f;
}

void Game011Frogger::SetupLanes() {
    for (int i = 0; i < kTotalLanes; ++i) {
        lanes_[i].num_items = 0;
        lanes_[i].is_river = false;
        lanes_[i].speed = 0.0f;
    }

    // 河流车道 (Row 1..5)
    // Row 1: 快速浮木向右, 宽 3, 2根
    lanes_[1].is_river = true; lanes_[1].speed = 2.8f; lanes_[1].num_items = 2; lanes_[1].item_w = 3.0f;
    lanes_[1].items[0] = {1.0f, 3.0f}; lanes_[1].items[1] = {9.0f, 3.0f};
    lanes_[1].r = 160; lanes_[1].g = 82; lanes_[1].b = 45; // 棕褐

    // Row 2: 漂流水龟向左, 宽 2, 3只
    lanes_[2].is_river = true; lanes_[2].speed = -2.5f; lanes_[2].num_items = 3; lanes_[2].item_w = 2.0f;
    lanes_[2].items[0] = {0.0f, 2.0f}; lanes_[2].items[1] = {6.0f, 2.0f}; lanes_[2].items[2] = {12.0f, 2.0f};
    lanes_[2].r = 230; lanes_[2].g = 126; lanes_[2].b = 34; // 橙龟

    // Row 3: 大浮木向右, 宽 4, 2根
    lanes_[3].is_river = true; lanes_[3].speed = 1.8f; lanes_[3].num_items = 2; lanes_[3].item_w = 4.0f;
    lanes_[3].items[0] = {2.0f, 4.0f}; lanes_[3].items[1] = {10.0f, 4.0f};
    lanes_[3].r = 160; lanes_[3].g = 82; lanes_[3].b = 45;

    // Row 4: 海龟向左, 宽 2, 2只
    lanes_[4].is_river = true; lanes_[4].speed = -3.2f; lanes_[4].num_items = 2; lanes_[4].item_w = 2.0f;
    lanes_[4].items[0] = {3.0f, 2.0f}; lanes_[4].items[1] = {11.0f, 2.0f};
    lanes_[4].r = 230; lanes_[4].g = 126; lanes_[4].b = 34;

    // Row 5: 短浮木向右, 宽 2, 3根
    lanes_[5].is_river = true; lanes_[5].speed = 2.4f; lanes_[5].num_items = 3; lanes_[5].item_w = 2.0f;
    lanes_[5].items[0] = {1.0f, 2.0f}; lanes_[5].items[1] = {7.0f, 2.0f}; lanes_[5].items[2] = {13.0f, 2.0f};
    lanes_[5].r = 160; lanes_[5].g = 82; lanes_[5].b = 45;

    // 公路车道 (Row 7..12)
    // Row 7: 超速红色跑车向左, 宽 1, 2辆
    lanes_[7].is_river = false; lanes_[7].speed = -4.5f; lanes_[7].num_items = 2; lanes_[7].item_w = 1.0f;
    lanes_[7].items[0] = {4.0f, 1.0f}; lanes_[7].items[1] = {12.0f, 1.0f};
    lanes_[7].r = 231; lanes_[7].g = 76; lanes_[7].b = 60; // 猩红跑车

    // Row 8: 双格客车向右, 宽 2, 2辆
    lanes_[8].is_river = false; lanes_[8].speed = 2.2f; lanes_[8].num_items = 2; lanes_[8].item_w = 2.0f;
    lanes_[8].items[0] = {2.0f, 2.0f}; lanes_[8].items[1] = {10.0f, 2.0f};
    lanes_[8].r = 236; lanes_[8].g = 240; lanes_[8].b = 241; // 亮白客车

    // Row 9: 慢速货车向左, 宽 3, 1辆
    lanes_[9].is_river = false; lanes_[9].speed = -1.6f; lanes_[9].num_items = 1; lanes_[9].item_w = 3.0f;
    lanes_[9].items[0] = {6.0f, 3.0f};
    lanes_[9].r = 241; lanes_[9].g = 196; lanes_[9].b = 15; // 明黄大卡

    // Row 10: 穿梭赛车向右, 宽 1, 2辆
    lanes_[10].is_river = false; lanes_[10].speed = 3.8f; lanes_[10].num_items = 2; lanes_[10].item_w = 1.0f;
    lanes_[10].items[0] = {3.0f, 1.0f}; lanes_[10].items[1] = {11.0f, 1.0f};
    lanes_[10].r = 155; lanes_[10].g = 89; lanes_[10].b = 182; // 紫罗兰

    // Row 11: 轿车向左, 宽 2, 2辆
    lanes_[11].is_river = false; lanes_[11].speed = -2.8f; lanes_[11].num_items = 2; lanes_[11].item_w = 2.0f;
    lanes_[11].items[0] = {2.0f, 2.0f}; lanes_[11].items[1] = {9.0f, 2.0f};
    lanes_[11].r = 52; lanes_[11].g = 152; lanes_[11].b = 219; // 宝蓝

    // Row 12: 摩托向右, 宽 1, 3辆
    lanes_[12].is_river = false; lanes_[12].speed = 4.0f; lanes_[12].num_items = 3; lanes_[12].item_w = 1.0f;
    lanes_[12].items[0] = {1.0f, 1.0f}; lanes_[12].items[1] = {7.0f, 1.0f}; lanes_[12].items[2] = {13.0f, 1.0f};
    lanes_[12].r = 230; lanes_[12].g = 126; lanes_[12].b = 34; // 橙黄摩托
}

void Game011Frogger::Init() {
    Reset();
}

void Game011Frogger::Reset() {
    state_ = STATE_PLAYING;
    score_ = 0;
    lives_ = 3;
    state_timer_ = 0.0f;
    homes_occupied_ = 0;
    for (int i = 0; i < kNumHomes; ++i) {
        homes_[i] = false;
    }
    SetupLanes();
    ResetFrogPosition();
}

void Game011Frogger::KillFrog() {
    if (lives_ > 0) lives_--;
    if (lives_ == 0) {
        state_ = STATE_GAMEOVER;
        state_timer_ = 0.0f;
    } else {
        ResetFrogPosition();
    }
}

static bool CheckItemOverlap(float px, float item_x, float item_w) {
    // 考虑环形循环包裹
    float left = item_x;
    float right = item_x + item_w;
    if (px >= left - 0.2f && px <= right - 0.2f) return true;
    if (right > 16.0f) {
        if (px >= 0.0f && px <= (right - 16.0f - 0.2f)) return true;
    }
    if (left < 0.0f) {
        if (px >= (16.0f + left - 0.2f) && px < 16.0f) return true;
    }
    return false;
}

void Game011Frogger::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
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

        // 关卡时间倒计时
        round_timer_ -= dt;
        if (round_timer_ <= 0.0f) {
            KillFrog();
            return;
        }

        // 1. 更新所有车道障碍物位置 (环形循环 0 ~ 16)
        for (int row = 0; row < kTotalLanes; ++row) {
            if (lanes_[row].num_items > 0) {
                for (int i = 0; i < lanes_[row].num_items; ++i) {
                    lanes_[row].items[i].x += lanes_[row].speed * dt;
                    if (lanes_[row].items[i].x >= 16.0f) {
                        lanes_[row].items[i].x -= 16.0f;
                    } else if (lanes_[row].items[i].x < -lanes_[row].item_w) {
                        lanes_[row].items[i].x += 16.0f;
                    }
                }
            }
        }

        // 2. 青蛙离散跳跃输入响应
        if (keys_pressed & KEY_UP) {
            frog_y_--;
            score_ += 10;
            if (score_ > high_score_) high_score_ = score_;
        } else if (keys_pressed & KEY_DOWN) {
            if (frog_y_ < 14) frog_y_++;
        } else if (keys_pressed & KEY_LEFT) {
            frog_x_ -= 1.0f;
            if (frog_x_ < 0.0f) frog_x_ = 0.0f;
        } else if (keys_pressed & KEY_RIGHT) {
            frog_x_ += 1.0f;
            if (frog_x_ > 15.0f) frog_x_ = 15.0f;
        }

        // 3. 终点判定 (Row 0: 五个洞穴)
        if (frog_y_ == 0) {
            bool entered_home = false;
            for (int h = 0; h < kNumHomes; ++h) {
                if (fabsf(frog_x_ - (float)kHomeX[h]) < 0.75f) {
                    if (!homes_[h]) {
                        homes_[h] = true;
                        homes_occupied_++;
                        score_ += 200 + (uint32_t)(round_timer_ * 10);
                        if (score_ > high_score_) high_score_ = score_;
                        entered_home = true;

                        if (homes_occupied_ >= kNumHomes) {
                            state_ = STATE_VICTORY;
                            state_timer_ = 0.0f;
                            return;
                        } else {
                            ResetFrogPosition();
                            return;
                        }
                    } else {
                        // 洞穴已被占
                        KillFrog();
                        return;
                    }
                }
            }
            if (!entered_home) {
                // 撞击灌木草丛
                KillFrog();
                return;
            }
        }

        // 4. 河流区域判定 (Row 1..5)
        if (frog_y_ >= 1 && frog_y_ <= 5) {
            Lane& rlane = lanes_[frog_y_];
            bool on_floating_item = false;
            for (int i = 0; i < rlane.num_items; ++i) {
                if (CheckItemOverlap(frog_x_, rlane.items[i].x, rlane.items[i].width)) {
                    on_floating_item = true;
                    break;
                }
            }

            if (on_floating_item) {
                // 随浮木漂移
                frog_x_ += rlane.speed * dt;
                if (frog_x_ < -0.2f || frog_x_ >= 15.8f) {
                    // 被漂出屏幕边界溺亡
                    KillFrog();
                    return;
                }
            } else {
                // 跌入水中溺亡
                KillFrog();
                return;
            }
        }

        // 5. 公路区域碰撞检测 (Row 7..12)
        if (frog_y_ >= 7 && frog_y_ <= 12) {
            Lane& hlane = lanes_[frog_y_];
            for (int i = 0; i < hlane.num_items; ++i) {
                if (CheckItemOverlap(frog_x_, hlane.items[i].x, hlane.items[i].width)) {
                    // 被车撞击碾压
                    KillFrog();
                    return;
                }
            }
        }
    }
}

void Game011Frogger::Render(uint8_t* fb_rgb24) {
    // 1. 底色与背景环境绘制
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            if (y == 0) {
                // 顶部灌木丛林
                fb_rgb24[idx + 0] = 19; fb_rgb24[idx + 1] = 15; fb_rgb24[idx + 2] = 64;
            } else if (y >= 1 && y <= 5) {
                // 幽蓝深河水
                fb_rgb24[idx + 0] = 21; fb_rgb24[idx + 1] = 67; fb_rgb24[idx + 2] = 96;
            } else if (y == 6) {
                // 中央安全草坪
                fb_rgb24[idx + 0] = 39; fb_rgb24[idx + 1] = 174; fb_rgb24[idx + 2] = 96;
            } else if (y >= 7 && y <= 12) {
                // 黑色柏油公路
                fb_rgb24[idx + 0] = 28; fb_rgb24[idx + 1] = 40;  fb_rgb24[idx + 2] = 51;
            } else if (y >= 13 && y <= 14) {
                // 起跳安全站台 (青蓝)
                fb_rgb24[idx + 0] = 46; fb_rgb24[idx + 1] = 134; fb_rgb24[idx + 2] = 193;
            } else {
                // 底部状态栏
                fb_rgb24[idx + 0] = 0;  fb_rgb24[idx + 1] = 0;   fb_rgb24[idx + 2] = 0;
            }
        }
    }

    // 2. 绘制顶部 5 个荷叶洞穴
    for (int h = 0; h < kNumHomes; ++h) {
        int hx = kHomeX[h];
        int idx = (0 * 16 + hx) * 3;
        if (homes_[h]) {
            // 已进驻: 亮绿常驻青蛙
            fb_rgb24[idx + 0] = 46; fb_rgb24[idx + 1] = 204; fb_rgb24[idx + 2] = 113;
        } else {
            // 空荷叶洞穴: 暗海蓝光
            fb_rgb24[idx + 0] = 0;  fb_rgb24[idx + 1] = 210; fb_rgb24[idx + 2] = 211;
        }
    }

    // 3. 绘制车道障碍物 (浮木/汽车)
    for (int y = 1; y <= 12; ++y) {
        if (lanes_[y].num_items > 0) {
            for (int i = 0; i < lanes_[y].num_items; ++i) {
                float ix = lanes_[y].items[i].x;
                float iw = lanes_[y].items[i].width;
                for (int x = 0; x < 16; ++x) {
                    if (CheckItemOverlap((float)x, ix, iw)) {
                        int idx = (y * 16 + x) * 3;
                        fb_rgb24[idx + 0] = lanes_[y].r;
                        fb_rgb24[idx + 1] = lanes_[y].g;
                        fb_rgb24[idx + 2] = lanes_[y].b;
                    }
                }
            }
        }
    }

    // 4. 绘制主角青蛙 (耀眼翠绿)
    int fx = (int)roundf(frog_x_);
    int fy = frog_y_;
    if (fx >= 0 && fx < 16 && fy >= 0 && fy < 16) {
        int idx = (fy * 16 + fx) * 3;
        fb_rgb24[idx + 0] = 46;
        fb_rgb24[idx + 1] = 204;
        fb_rgb24[idx + 2] = 113;
    }

    // 5. 底部状态栏显示 (Row 15: 左侧剩余生命，右侧倒计时时间条)
    for (int i = 0; i < lives_; ++i) {
        int idx = (15 * 16 + (i * 2)) * 3;
        fb_rgb24[idx + 0] = 231; fb_rgb24[idx + 1] = 76; fb_rgb24[idx + 2] = 60; // 剩余生命红心
    }
    int timer_bars = (int)((round_timer_ / 30.0f) * 6.0f);
    for (int i = 0; i < timer_bars; ++i) {
        int idx = (15 * 16 + (10 + i)) * 3;
        fb_rgb24[idx + 0] = 241; fb_rgb24[idx + 1] = 196; fb_rgb24[idx + 2] = 15; // 计时条明黄
    }

    // 6. 胜败特效
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

CartridgeStatus Game011Frogger::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.lives = lives_;
    st.state = (uint8_t)state_;
    st.progress = (uint8_t)((homes_occupied_ * 100) / kNumHomes);
    return st;
}

} // namespace arcade
