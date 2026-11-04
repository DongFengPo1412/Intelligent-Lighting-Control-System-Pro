// game_074_highway_racer.cpp —— 目标 #074 变道赛车 核心实现
#include "game_074_highway_racer.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>
#include <math.h>
#include <stdlib.h>

namespace arcade {

static const float kLaneCenters[3] = {3.5f, 7.0f, 10.5f};

Game074HighwayRacer::Game074HighwayRacer()
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
      anim_timer_(0.0f),
      spawn_timer_(0.0f),
      crash_anim_timer_(0.0f) {
    for (int i = 0; i < kMaxTraffic; ++i) {
        traffic_[i].active = false;
    }
}

void Game074HighwayRacer::ResetPlayerCar() {
    car_x_ = 7.0f;
    speed_ = 16.0f;
    crash_anim_timer_ = 0.0f;

    for (int i = 0; i < kMaxTraffic; ++i) {
        if (traffic_[i].active && traffic_[i].y > 8.0f) {
            traffic_[i].active = false;
        }
    }
}

void Game074HighwayRacer::Init() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    Reset();
}

void Game074HighwayRacer::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    state_ = STATE_TITLE;
    score_ = 0;
    lives_ = 3;
    distance_m_ = 0.0f;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    spawn_timer_ = 0.0f;
    road_scroll_y_ = 0.0f;

    for (int i = 0; i < kMaxTraffic; ++i) {
        traffic_[i].active = false;
    }

    ResetPlayerCar();
}

void Game074HighwayRacer::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        state_ = STATE_PLAYING;
        score_ = 0;
        lives_ = 3;
        distance_m_ = 0.0f;
        state_timer_ = 0.0f;
        anim_timer_ = 0.0f;
        spawn_timer_ = 0.0f;
        road_scroll_y_ = 0.0f;
        for (int i = 0; i < kMaxTraffic; ++i) traffic_[i].active = false;
        ResetPlayerCar();
    }
}

void Game074HighwayRacer::Pause() {
    if (state_ == STATE_PLAYING) state_ = STATE_PAUSED;
}

void Game074HighwayRacer::Resume() {
    if (state_ == STATE_PAUSED) state_ = STATE_PLAYING;
}

void Game074HighwayRacer::CrashCar() {
    if (lives_ > 1) {
        lives_--;
        ResetPlayerCar();
    } else {
        lives_ = 0;
        state_ = STATE_GAMEOVER;
        state_timer_ = 0.0f;
        if (score_ > high_score_) {
            high_score_ = score_;
            ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
        }
    }
}

void Game074HighwayRacer::SpawnTraffic() {
    int slot = -1;
    for (int i = 0; i < kMaxTraffic; ++i) {
        if (!traffic_[i].active) {
            slot = i;
            break;
        }
    }
    if (slot == -1) return;

    int chosen_lane = rand() % 3;
    for (int i = 0; i < kMaxTraffic; ++i) {
        if (traffic_[i].active && traffic_[i].y < 2.0f && traffic_[i].lane == chosen_lane) {
            return;
        }
    }

    int type = rand() % 3;
    traffic_[slot].active = true;
    traffic_[slot].lane = chosen_lane;
    traffic_[slot].x = kLaneCenters[chosen_lane];
    traffic_[slot].y = -3.0f;

    if (type == 0) {
        traffic_[slot].width = 2;
        traffic_[slot].height = 3;
        traffic_[slot].speed = 6.0f;
        traffic_[slot].r = 241; traffic_[slot].g = 196; traffic_[slot].b = 15;
    } else if (type == 1) {
        traffic_[slot].width = 2;
        traffic_[slot].height = 2;
        traffic_[slot].speed = 9.0f;
        traffic_[slot].r = 52; traffic_[slot].g = 152; traffic_[slot].b = 219;
    } else {
        traffic_[slot].width = 2;
        traffic_[slot].height = 2;
        traffic_[slot].speed = 12.0f;
        traffic_[slot].r = 236; traffic_[slot].g = 240; traffic_[slot].b = 241;
    }
}

void Game074HighwayRacer::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt > 0.05f) dt = 0.05f;
    state_timer_ += dt;
    anim_timer_ += dt;

    if (state_ == STATE_TITLE) {
        if (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN)) {
            Start();
        }
        return;
    }

    if (state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        if (state_timer_ > 0.5f && (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN))) {
            Start();
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

        const float steer_speed = 9.0f;
        if (keys_down & KEY_LEFT) car_x_ -= steer_speed * dt;
        else if (keys_down & KEY_RIGHT) car_x_ += steer_speed * dt;

        if (keys_down & (KEY_UP | KEY_A)) {
            speed_ += 10.0f * dt;
            if (speed_ > 28.0f) speed_ = 28.0f;
        } else if (keys_down & (KEY_DOWN | KEY_B)) {
            speed_ -= 12.0f * dt;
            if (speed_ < 10.0f) speed_ = 10.0f;
        } else {
            if (speed_ > 18.0f) speed_ -= 4.0f * dt;
            else if (speed_ < 18.0f) speed_ += 4.0f * dt;
        }

        if (car_x_ < 2.2f || car_x_ > 11.8f) {
            CrashCar();
            return;
        }

        road_scroll_y_ += speed_ * dt;
        if (road_scroll_y_ >= 4.0f) road_scroll_y_ -= 4.0f;

        distance_m_ += speed_ * dt * 2.5f;
        score_ = (uint32_t)distance_m_;
        if (score_ > high_score_) {
            high_score_ = score_;
            ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
        }

        if (distance_m_ >= target_distance_) {
            state_ = STATE_VICTORY;
            state_timer_ = 0.0f;
            return;
        }

        spawn_timer_ += dt;
        if (spawn_timer_ >= 1.2f) {
            spawn_timer_ = 0.0f;
            SpawnTraffic();
        }

        for (int i = 0; i < kMaxTraffic; ++i) {
            if (traffic_[i].active) {
                float rel_speed = speed_ - traffic_[i].speed;
                traffic_[i].y += rel_speed * dt;

                if (traffic_[i].y > 17.0f) {
                    traffic_[i].active = false;
                }

                float px1 = car_x_;
                float px2 = car_x_ + 1.8f;
                float py1 = 12.0f;
                float py2 = 14.5f;

                float tx1 = traffic_[i].x;
                float tx2 = traffic_[i].x + (float)traffic_[i].width - 0.2f;
                float ty1 = traffic_[i].y;
                float ty2 = traffic_[i].y + (float)traffic_[i].height;

                if (px2 >= tx1 && px1 <= tx2 && py2 >= ty1 && py1 <= ty2) {
                    CrashCar();
                    return;
                }
            }
        }
    }
}

void Game074HighwayRacer::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    memset(fb_rgb24, 0, 16 * 16 * 3);

    for (int y = 0; y < 16; ++y) {
        int idx_l0 = (y * 16 + 0) * 3;
        int idx_l1 = (y * 16 + 1) * 3;
        int idx_r0 = (y * 16 + 14) * 3;
        int idx_r1 = (y * 16 + 15) * 3;
        fb_rgb24[idx_l0 + 0] = 34; fb_rgb24[idx_l0 + 1] = 139; fb_rgb24[idx_l0 + 2] = 34;
        fb_rgb24[idx_l1 + 0] = 34; fb_rgb24[idx_l1 + 1] = 139; fb_rgb24[idx_l1 + 2] = 34;
        fb_rgb24[idx_r0 + 0] = 34; fb_rgb24[idx_r0 + 1] = 139; fb_rgb24[idx_r0 + 2] = 34;
        fb_rgb24[idx_r1 + 0] = 34; fb_rgb24[idx_r1 + 1] = 139; fb_rgb24[idx_r1 + 2] = 34;

        for (int x = 2; x <= 13; ++x) {
            int idx = (y * 16 + x) * 3;
            fb_rgb24[idx + 0] = 35; fb_rgb24[idx + 1] = 35; fb_rgb24[idx + 2] = 38;
        }
    }

    int scroll_offset = (int)roundf(road_scroll_y_);
    for (int y = 0; y < 16; ++y) {
        if (((y + scroll_offset) % 4) < 2) {
            int idx1 = (y * 16 + 5) * 3;
            int idx2 = (y * 16 + 9) * 3;
            fb_rgb24[idx1 + 0] = fb_rgb24[idx1 + 1] = fb_rgb24[idx1 + 2] = 220;
            fb_rgb24[idx2 + 0] = fb_rgb24[idx2 + 1] = fb_rgb24[idx2 + 2] = 220;
        }
    }

    for (int i = 0; i < kMaxTraffic; ++i) {
        if (traffic_[i].active) {
            int tx = (int)roundf(traffic_[i].x);
            int ty = (int)roundf(traffic_[i].y);
            for (int dy = 0; dy < traffic_[i].height; ++dy) {
                for (int dx = 0; dx < traffic_[i].width; ++dx) {
                    int x = tx + dx;
                    int y = ty + dy;
                    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
                        int idx = (y * 16 + x) * 3;
                        fb_rgb24[idx + 0] = traffic_[i].r;
                        fb_rgb24[idx + 1] = traffic_[i].g;
                        fb_rgb24[idx + 2] = traffic_[i].b;
                    }
                }
            }
        }
    }

    int cx = (int)roundf(car_x_);
    for (int dy = 0; dy < 3; ++dy) {
        for (int dx = 0; dx < 2; ++dx) {
            int x = cx + dx;
            int y = 12 + dy;
            if (x >= 0 && x < 16 && y < 16) {
                int idx = (y * 16 + x) * 3;
                if (dy == 0) {
                    fb_rgb24[idx + 0] = 231; fb_rgb24[idx + 1] = 76; fb_rgb24[idx + 2] = 60;
                } else if (dy == 1) {
                    fb_rgb24[idx + 0] = 52; fb_rgb24[idx + 1] = 152; fb_rgb24[idx + 2] = 219;
                } else {
                    fb_rgb24[idx + 0] = 231; fb_rgb24[idx + 1] = 76; fb_rgb24[idx + 2] = 60;
                }
            }
        }
    }

    for (int i = 0; i < lives_ && i < 3; ++i) {
        int idx = (0 * 16 + i * 2) * 3;
        fb_rgb24[idx + 0] = 231; fb_rgb24[idx + 1] = 76; fb_rgb24[idx + 2] = 60;
    }

    if (state_ == STATE_PAUSED) {
        for (int y = 6; y <= 9; ++y) {
            int idx1 = (y * 16 + 6) * 3;
            int idx2 = (y * 16 + 9) * 3;
            fb_rgb24[idx1 + 0] = fb_rgb24[idx1 + 1] = fb_rgb24[idx1 + 2] = 250;
            fb_rgb24[idx2 + 0] = fb_rgb24[idx2 + 1] = fb_rgb24[idx2 + 2] = 250;
        }
    }
}

CartridgeStatus Game074HighwayRacer::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = lives_;
    st.state = (uint8_t)state_;
    st.progress = (uint8_t)((distance_m_ * 100) / target_distance_);
    if (st.progress > 100) st.progress = 100;
    return st;
}

} // namespace arcade

