// game_012_highway_racer.cpp —— 极速变道赛车 1982 核心实现
#include "game_012_highway_racer.h"
#include <string.h>
#include <math.h>
#include <stdlib.h>

namespace arcade {

static const float kLaneCenters[3] = {3.5f, 7.0f, 10.5f};

Game012HighwayRacer::Game012HighwayRacer()
    : state_(STATE_TITLE),
      car_x_(7.0f),
      speed_(18.0f),
      road_scroll_y_(0.0f),
      distance_m_(0.0f),
      target_distance_(1000.0f),
      lives_(3),
      score_(0),
      high_score_(0),
      state_timer_(0.0f),
      spawn_timer_(0.0f),
      crash_anim_timer_(0.0f) {
    for (int i = 0; i < kMaxTraffic; ++i) {
        traffic_[i].active = false;
    }
}

void Game012HighwayRacer::ResetPlayerCar() {
    car_x_ = 7.0f;
    speed_ = 16.0f;
    crash_anim_timer_ = 0.0f;

    // 清空靠近玩家的交通车
    for (int i = 0; i < kMaxTraffic; ++i) {
        if (traffic_[i].active && traffic_[i].y > 8.0f) {
            traffic_[i].active = false;
        }
    }
}

void Game012HighwayRacer::Init() {
    Reset();
}

void Game012HighwayRacer::Reset() {
    state_ = STATE_PLAYING;
    score_ = 0;
    lives_ = 3;
    distance_m_ = 0.0f;
    state_timer_ = 0.0f;
    spawn_timer_ = 0.0f;
    road_scroll_y_ = 0.0f;

    for (int i = 0; i < kMaxTraffic; ++i) {
        traffic_[i].active = false;
    }

    ResetPlayerCar();
}

void Game012HighwayRacer::CrashCar() {
    if (lives_ > 0) lives_--;
    if (lives_ == 0) {
        state_ = STATE_GAMEOVER;
        state_timer_ = 0.0f;
    } else {
        ResetPlayerCar();
    }
}

void Game012HighwayRacer::SpawnTraffic() {
    int slot = -1;
    for (int i = 0; i < kMaxTraffic; ++i) {
        if (!traffic_[i].active) {
            slot = i;
            break;
        }
    }
    if (slot == -1) return;

    // 随机选择车道，避免三车道在顶部完全并排堵死
    int chosen_lane = rand() % 3;
    for (int i = 0; i < kMaxTraffic; ++i) {
        if (traffic_[i].active && traffic_[i].y < 2.0f && traffic_[i].lane == chosen_lane) {
            return; // 该车道入口已被占
        }
    }

    int type = rand() % 3;
    traffic_[slot].active = true;
    traffic_[slot].lane = chosen_lane;
    traffic_[slot].x = kLaneCenters[chosen_lane];
    traffic_[slot].y = -3.0f;

    if (type == 0) {
        // 慢速卡车 (黄, 长3)
        traffic_[slot].width = 2;
        traffic_[slot].height = 3;
        traffic_[slot].speed = 6.0f;
        traffic_[slot].r = 241; traffic_[slot].g = 196; traffic_[slot].b = 15;
    } else if (type == 1) {
        // 中速轿车 (蓝, 长2)
        traffic_[slot].width = 2;
        traffic_[slot].height = 2;
        traffic_[slot].speed = 9.0f;
        traffic_[slot].r = 52; traffic_[slot].g = 152; traffic_[slot].b = 219;
    } else {
        // 极速快车 (白, 长2)
        traffic_[slot].width = 2;
        traffic_[slot].height = 2;
        traffic_[slot].speed = 12.0f;
        traffic_[slot].r = 236; traffic_[slot].g = 240; traffic_[slot].b = 241;
    }
}

void Game012HighwayRacer::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt > 0.05f) dt = 0.05f;
    state_timer_ += dt;

    if (state_ == STATE_TITLE) {
        if (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN)) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        if (state_timer_ > 0.5f && (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN))) {
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

        // 1. 速度控制 (油门与刹车)
        const float accel_rate = 14.0f;
        const float brake_rate = 22.0f;
        if (keys_down & (KEY_UP | KEY_A)) {
            speed_ += accel_rate * dt;
            if (speed_ > 28.0f) speed_ = 28.0f; // 极速
        } else if (keys_down & (KEY_DOWN | KEY_B)) {
            speed_ -= brake_rate * dt;
            if (speed_ < 8.0f) speed_ = 8.0f;   // 慢速
        } else {
            // 自然阻力回归巡航速度 18.0
            if (speed_ < 18.0f) {
                speed_ += 4.0f * dt;
                if (speed_ > 18.0f) speed_ = 18.0f;
            } else if (speed_ > 18.0f) {
                speed_ -= 4.0f * dt;
                if (speed_ < 18.0f) speed_ = 18.0f;
            }
        }

        // 2. 转向变道控制
        const float steer_speed = 10.0f;
        if (keys_down & KEY_LEFT) {
            car_x_ -= steer_speed * dt;
        } else if (keys_down & KEY_RIGHT) {
            car_x_ += steer_speed * dt;
        }

        // 3. 碰撞护栏路肩检测 (x < 2.4 或 x > 11.6)
        if (car_x_ < 2.4f || car_x_ > 11.6f) {
            CrashCar();
            return;
        }

        // 4. 里程积累与道路标线滚动
        distance_m_ += speed_ * 2.5f * dt;
        road_scroll_y_ += speed_ * dt;
        if (road_scroll_y_ >= 4.0f) {
            road_scroll_y_ -= 4.0f;
        }

        // 通关里程判定 (到达 1000m)
        if (distance_m_ >= target_distance_) {
            state_ = STATE_VICTORY;
            state_timer_ = 0.0f;
            score_ += 500;
            if (score_ > high_score_) high_score_ = score_;
            return;
        }

        // 5. 敌车生成周期
        spawn_timer_ += dt;
        if (spawn_timer_ >= 1.4f) {
            spawn_timer_ = 0.0f;
            SpawnTraffic();
        }

        // 6. 敌车相对物理位移与碰撞检测
        for (int i = 0; i < kMaxTraffic; ++i) {
            if (traffic_[i].active) {
                float rel_speed = speed_ - traffic_[i].speed;
                traffic_[i].y += rel_speed * dt;

                // 超车判定
                if (traffic_[i].y > 15.5f) {
                    traffic_[i].active = false;
                    score_ += 50; // 超车奖励
                    if (score_ > high_score_) high_score_ = score_;
                } else if (traffic_[i].y < -4.0f) {
                    // 若玩家刹太猛，被敌车反超拉开距离
                    traffic_[i].active = false;
                } else {
                    // 追尾碰撞检测: 玩家车位于 y=13..14
                    float car_top = 13.0f;
                    float car_bottom = 14.8f;
                    float t_top = traffic_[i].y;
                    float t_bottom = traffic_[i].y + traffic_[i].height;

                    if (t_bottom >= car_top && t_top <= car_bottom) {
                        if (fabsf(car_x_ - traffic_[i].x) < 1.5f) {
                            CrashCar();
                            return;
                        }
                    }
                }
            }
        }
    }
}

void Game012HighwayRacer::Render(uint8_t* fb_rgb24) {
    // 1. 道路底色 (纯黑沥青路面: x=2..12, 墨绿草坪路肩: x=0..1 与 x=13..15)
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            if (x < 2 || x > 12) {
                // 两侧草坪
                fb_rgb24[idx + 0] = 39; fb_rgb24[idx + 1] = 174; fb_rgb24[idx + 2] = 96;
            } else {
                // 黑色柏油公路
                fb_rgb24[idx + 0] = 33; fb_rgb24[idx + 1] = 33; fb_rgb24[idx + 2] = 33;
            }
        }
    }

    // 2. 护栏红白斑马线 (x=1 与 x=13 沿路滚动)
    int scroll_step = (int)road_scroll_y_;
    for (int y = 0; y < 16; ++y) {
        bool red = ((y + scroll_step) % 4 < 2);
        uint8_t cr = red ? 231 : 255;
        uint8_t cg = red ? 76  : 255;
        uint8_t cb = red ? 60  : 255;

        int idx_left = (y * 16 + 1) * 3;
        int idx_right = (y * 16 + 13) * 3;
        fb_rgb24[idx_left + 0] = cr; fb_rgb24[idx_left + 1] = cg; fb_rgb24[idx_left + 2] = cb;
        fb_rgb24[idx_right + 0] = cr; fb_rgb24[idx_right + 1] = cg; fb_rgb24[idx_right + 2] = cb;
    }

    // 3. 动态分道虚线 (x=5 与 x=9, 明黄虚线)
    for (int y = 0; y < 16; ++y) {
        if ((y + scroll_step) % 4 < 2) {
            int idx1 = (y * 16 + 5) * 3;
            int idx2 = (y * 16 + 9) * 3;
            fb_rgb24[idx1 + 0] = 241; fb_rgb24[idx1 + 1] = 196; fb_rgb24[idx1 + 2] = 15;
            fb_rgb24[idx2 + 0] = 241; fb_rgb24[idx2 + 1] = 196; fb_rgb24[idx2 + 2] = 15;
        }
    }

    // 4. 绘制敌车
    for (int i = 0; i < kMaxTraffic; ++i) {
        if (traffic_[i].active) {
            int tx = (int)roundf(traffic_[i].x);
            int ty_start = (int)roundf(traffic_[i].y);
            int ty_end = ty_start + traffic_[i].height;

            for (int y = ty_start; y < ty_end; ++y) {
                if (y >= 0 && y < 16) {
                    for (int dx = -1; dx <= 0; ++dx) {
                        int x = tx + dx;
                        if (x >= 0 && x < 16) {
                            int idx = (y * 16 + x) * 3;
                            fb_rgb24[idx + 0] = traffic_[i].r;
                            fb_rgb24[idx + 1] = traffic_[i].g;
                            fb_rgb24[idx + 2] = traffic_[i].b;
                        }
                    }
                }
            }
        }
    }

    // 5. 绘制玩家赛车 (y=13..14, 红色跑车 + 青蓝座舱)
    int px = (int)roundf(car_x_);
    // 车身头部 (y=13)
    if (px >= 0 && px < 16) {
        int idx = (13 * 16 + px) * 3;
        fb_rgb24[idx + 0] = 0; fb_rgb24[idx + 1] = 255; fb_rgb24[idx + 2] = 255; // 驾驶舱
    }
    // 车身底座与双轮 (y=14)
    for (int dx = -1; dx <= 1; ++dx) {
        int x = px + dx;
        if (x >= 0 && x < 16) {
            int idx = (14 * 16 + x) * 3;
            fb_rgb24[idx + 0] = 231; fb_rgb24[idx + 1] = 76; fb_rgb24[idx + 2] = 60; // 猩红跑车
        }
    }

    // 6. 顶部 HUD (y=0: 左侧生命红心，右侧速度指示)
    for (int i = 0; i < lives_; ++i) {
        int idx = (0 * 16 + i) * 3;
        fb_rgb24[idx + 0] = 231; fb_rgb24[idx + 1] = 76; fb_rgb24[idx + 2] = 60;
    }
    int speed_dots = (int)((speed_ - 8.0f) / 4.0f) + 1;
    for (int i = 0; i < speed_dots && i < 6; ++i) {
        int idx = (0 * 16 + (15 - i)) * 3;
        fb_rgb24[idx + 0] = 46; fb_rgb24[idx + 1] = 204; fb_rgb24[idx + 2] = 113; // 绿色速度指示
    }

    // 7. 特效渲染
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

CartridgeStatus Game012HighwayRacer::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.lives = lives_;
    st.state = (uint8_t)state_;
    st.progress = (uint8_t)fminf(100.0f, (distance_m_ * 100.0f) / target_distance_);
    return st;
}

} // namespace arcade
