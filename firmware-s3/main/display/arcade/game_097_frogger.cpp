// game_097_frogger.cpp —— 目标 #097 青蛙过河 核心实现
#include "game_097_frogger.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>
#include <math.h>

namespace arcade {

static const int kHomeX[5] = {1, 4, 7, 10, 13};

Game097Frogger::Game097Frogger()
    : state_(STATE_TITLE),
      frog_x_(7.0f),
      frog_y_(14),
      best_row_(14),
      lives_(3),
      score_(0),
      high_score_(0),
      round_timer_(30.0f),
      state_timer_(0.0f),
      anim_timer_(0.0f),
      homes_occupied_(0) {
    for (int i = 0; i < kNumHomes; ++i) {
        homes_[i] = false;
    }
}

void Game097Frogger::ResetFrogPosition() {
    frog_x_ = 7.0f;
    frog_y_ = 14;
    best_row_ = 14;
    round_timer_ = 30.0f;
}

void Game097Frogger::SetupLanes() {
    for (int i = 0; i < kTotalLanes; ++i) {
        lanes_[i].num_items = 0;
        lanes_[i].is_river = false;
        lanes_[i].speed = 0.0f;
    }

    lanes_[1].is_river = true; lanes_[1].speed = 2.8f; lanes_[1].num_items = 2; lanes_[1].item_w = 3.0f;
    lanes_[1].items[0] = {1.0f, 3.0f}; lanes_[1].items[1] = {9.0f, 3.0f};
    lanes_[1].r = 160; lanes_[1].g = 82; lanes_[1].b = 45;

    lanes_[2].is_river = true; lanes_[2].speed = -2.5f; lanes_[2].num_items = 3; lanes_[2].item_w = 2.0f;
    lanes_[2].items[0] = {0.0f, 2.0f}; lanes_[2].items[1] = {6.0f, 2.0f}; lanes_[2].items[2] = {12.0f, 2.0f};
    lanes_[2].r = 230; lanes_[2].g = 126; lanes_[2].b = 34;

    lanes_[3].is_river = true; lanes_[3].speed = 1.8f; lanes_[3].num_items = 2; lanes_[3].item_w = 4.0f;
    lanes_[3].items[0] = {2.0f, 4.0f}; lanes_[3].items[1] = {10.0f, 4.0f};
    lanes_[3].r = 160; lanes_[3].g = 82; lanes_[3].b = 45;

    lanes_[4].is_river = true; lanes_[4].speed = -3.2f; lanes_[4].num_items = 2; lanes_[4].item_w = 2.0f;
    lanes_[4].items[0] = {3.0f, 2.0f}; lanes_[4].items[1] = {11.0f, 2.0f};
    lanes_[4].r = 230; lanes_[4].g = 126; lanes_[4].b = 34;

    lanes_[5].is_river = true; lanes_[5].speed = 2.4f; lanes_[5].num_items = 3; lanes_[5].item_w = 2.0f;
    lanes_[5].items[0] = {1.0f, 2.0f}; lanes_[5].items[1] = {7.0f, 2.0f}; lanes_[5].items[2] = {13.0f, 2.0f};
    lanes_[5].r = 160; lanes_[5].g = 82; lanes_[5].b = 45;

    lanes_[7].is_river = false; lanes_[7].speed = -4.5f; lanes_[7].num_items = 2; lanes_[7].item_w = 1.0f;
    lanes_[7].items[0] = {4.0f, 1.0f}; lanes_[7].items[1] = {12.0f, 1.0f};
    lanes_[7].r = 231; lanes_[7].g = 76; lanes_[7].b = 60;

    lanes_[8].is_river = false; lanes_[8].speed = 2.2f; lanes_[8].num_items = 2; lanes_[8].item_w = 2.0f;
    lanes_[8].items[0] = {2.0f, 2.0f}; lanes_[8].items[1] = {10.0f, 2.0f};
    lanes_[8].r = 236; lanes_[8].g = 240; lanes_[8].b = 241;

    lanes_[9].is_river = false; lanes_[9].speed = -1.6f; lanes_[9].num_items = 1; lanes_[9].item_w = 3.0f;
    lanes_[9].items[0] = {6.0f, 3.0f};
    lanes_[9].r = 241; lanes_[9].g = 196; lanes_[9].b = 15;

    lanes_[10].is_river = false; lanes_[10].speed = 3.8f; lanes_[10].num_items = 2; lanes_[10].item_w = 1.0f;
    lanes_[10].items[0] = {3.0f, 1.0f}; lanes_[10].items[1] = {11.0f, 1.0f};
    lanes_[10].r = 155; lanes_[10].g = 89; lanes_[10].b = 182;

    lanes_[11].is_river = false; lanes_[11].speed = -2.8f; lanes_[11].num_items = 2; lanes_[11].item_w = 2.0f;
    lanes_[11].items[0] = {2.0f, 2.0f}; lanes_[11].items[1] = {9.0f, 2.0f};
    lanes_[11].r = 52; lanes_[11].g = 152; lanes_[11].b = 219;

    lanes_[12].is_river = false; lanes_[12].speed = 4.0f; lanes_[12].num_items = 3; lanes_[12].item_w = 1.0f;
    lanes_[12].items[0] = {1.0f, 1.0f}; lanes_[12].items[1] = {7.0f, 1.0f}; lanes_[12].items[2] = {13.0f, 1.0f};
    lanes_[12].r = 230; lanes_[12].g = 126; lanes_[12].b = 34;
}

void Game097Frogger::Init() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    Reset();
}

void Game097Frogger::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    state_ = STATE_TITLE;
    score_ = 0;
    lives_ = 3;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    homes_occupied_ = 0;
    for (int i = 0; i < kNumHomes; ++i) {
        homes_[i] = false;
    }
    SetupLanes();
    ResetFrogPosition();
}

void Game097Frogger::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        state_ = STATE_PLAYING;
        score_ = 0;
        lives_ = 3;
        state_timer_ = 0.0f;
        anim_timer_ = 0.0f;
        homes_occupied_ = 0;
        for (int i = 0; i < kNumHomes; ++i) homes_[i] = false;
        SetupLanes();
        ResetFrogPosition();
    }
}

void Game097Frogger::Pause() {
    if (state_ == STATE_PLAYING) state_ = STATE_PAUSED;
}

void Game097Frogger::Resume() {
    if (state_ == STATE_PAUSED) state_ = STATE_PLAYING;
}

void Game097Frogger::KillFrog() {
    if (lives_ > 1) {
        lives_--;
        ResetFrogPosition();
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

void Game097Frogger::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt > 0.05f) dt = 0.05f;
    state_timer_ += dt;
    anim_timer_ += dt;

    if (state_ == STATE_TITLE) {
        if (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)) {
            Start();
        }
        return;
    }

    if (state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        if (state_timer_ > 0.5f && (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT))) {
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

        round_timer_ -= dt;
        if (round_timer_ <= 0.0f) {
            KillFrog();
            return;
        }

        if (keys_pressed & KEY_UP) {
            if (frog_y_ > 0) {
                frog_y_--;
                if (frog_y_ < best_row_) {
                    best_row_ = frog_y_;
                    score_ += 10;
                    if (score_ > high_score_) {
                        high_score_ = score_;
                        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
                    }
                }
            }
        } else if (keys_pressed & KEY_DOWN) {
            if (frog_y_ < 14) frog_y_++;
        } else if (keys_pressed & KEY_LEFT) {
            if (frog_x_ > 0.5f) frog_x_ -= 1.0f;
        } else if (keys_pressed & KEY_RIGHT) {
            if (frog_x_ < 14.5f) frog_x_ += 1.0f;
        }

        for (int y = 0; y < kTotalLanes; ++y) {
            if (lanes_[y].num_items > 0) {
                float spd = lanes_[y].speed;
                for (int i = 0; i < lanes_[y].num_items; ++i) {
                    lanes_[y].items[i].x += spd * dt;
                    if (spd > 0 && lanes_[y].items[i].x > 16.0f) {
                        lanes_[y].items[i].x -= (16.0f + lanes_[y].items[i].width + 2.0f);
                    } else if (spd < 0 && (lanes_[y].items[i].x + lanes_[y].items[i].width) < 0.0f) {
                        lanes_[y].items[i].x += (16.0f + lanes_[y].items[i].width + 2.0f);
                    }
                }
            }
        }

        if (frog_y_ >= 1 && frog_y_ <= 5) {
            FrogLane& lane = lanes_[frog_y_];
            bool on_log = false;
            for (int i = 0; i < lane.num_items; ++i) {
                float lx1 = lane.items[i].x;
                float lx2 = lx1 + lane.items[i].width;
                if (frog_x_ >= lx1 - 0.4f && frog_x_ <= lx2 - 0.6f) {
                    on_log = true;
                    break;
                }
            }
            if (on_log) {
                frog_x_ += lane.speed * dt;
                if (frog_x_ < 0.0f || frog_x_ > 15.0f) {
                    KillFrog();
                    return;
                }
            } else {
                KillFrog();
                return;
            }
        }

        if (frog_y_ >= 7 && frog_y_ <= 12) {
            FrogLane& lane = lanes_[frog_y_];
            for (int i = 0; i < lane.num_items; ++i) {
                float cx1 = lane.items[i].x;
                float cx2 = cx1 + lane.items[i].width;
                if (frog_x_ >= cx1 - 0.6f && frog_x_ <= cx2 - 0.4f) {
                    KillFrog();
                    return;
                }
            }
        }

        if (frog_y_ == 0) {
            int home_idx = -1;
            for (int i = 0; i < kNumHomes; ++i) {
                if (fabsf(frog_x_ - (float)kHomeX[i]) < 0.8f) {
                    home_idx = i;
                    break;
                }
            }

            if (home_idx >= 0 && !homes_[home_idx]) {
                homes_[home_idx] = true;
                homes_occupied_++;
                score_ += 200 + (uint32_t)round_timer_ * 10;
                if (score_ > high_score_) {
                    high_score_ = score_;
                    ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
                }

                if (homes_occupied_ >= kNumHomes) {
                    state_ = STATE_VICTORY;
                    state_timer_ = 0.0f;
                    return;
                } else {
                    ResetFrogPosition();
                }
            } else {
                KillFrog();
                return;
            }
        }
    }
}

void Game097Frogger::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    memset(fb_rgb24, 0, 16 * 16 * 3);

    for (int x = 0; x < 16; ++x) {
        int idx = x * 3;
        fb_rgb24[idx + 0] = 34; fb_rgb24[idx + 1] = 139; fb_rgb24[idx + 2] = 34;
    }
    for (int i = 0; i < kNumHomes; ++i) {
        int x = kHomeX[i];
        int idx = x * 3;
        if (homes_[i]) {
            fb_rgb24[idx + 0] = 46; fb_rgb24[idx + 1] = 204; fb_rgb24[idx + 2] = 113;
        } else {
            fb_rgb24[idx + 0] = 20; fb_rgb24[idx + 1] = 40; fb_rgb24[idx + 2] = 80;
        }
    }

    for (int y = 1; y <= 5; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            fb_rgb24[idx + 0] = 15; fb_rgb24[idx + 1] = 45; fb_rgb24[idx + 2] = 135;
        }
    }

    for (int x = 0; x < 16; ++x) {
        int idx6 = (6 * 16 + x) * 3;
        int idx13 = (13 * 16 + x) * 3;
        int idx14 = (14 * 16 + x) * 3;
        fb_rgb24[idx6 + 0] = 46; fb_rgb24[idx6 + 1] = 139; fb_rgb24[idx6 + 2] = 87;
        fb_rgb24[idx13 + 0] = 46; fb_rgb24[idx13 + 1] = 139; fb_rgb24[idx13 + 2] = 87;
        fb_rgb24[idx14 + 0] = 34; fb_rgb24[idx14 + 1] = 139; fb_rgb24[idx14 + 2] = 34;
    }

    for (int y = 7; y <= 12; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            fb_rgb24[idx + 0] = 25; fb_rgb24[idx + 1] = 25; fb_rgb24[idx + 2] = 28;
        }
    }

    for (int y = 1; y <= 12; ++y) {
        if (lanes_[y].num_items > 0) {
            for (int i = 0; i < lanes_[y].num_items; ++i) {
                int x1 = (int)roundf(lanes_[y].items[i].x);
                int x2 = (int)roundf(lanes_[y].items[i].x + lanes_[y].items[i].width);
                for (int x = x1; x < x2; ++x) {
                    if (x >= 0 && x < 16) {
                        int idx = (y * 16 + x) * 3;
                        fb_rgb24[idx + 0] = lanes_[y].r;
                        fb_rgb24[idx + 1] = lanes_[y].g;
                        fb_rgb24[idx + 2] = lanes_[y].b;
                    }
                }
            }
        }
    }

    int fx = (int)roundf(frog_x_);
    int fy = frog_y_;
    if (fx >= 0 && fx < 16 && fy >= 0 && fy < 16) {
        int idx = (fy * 16 + fx) * 3;
        fb_rgb24[idx + 0] = 50; fb_rgb24[idx + 1] = 255; fb_rgb24[idx + 2] = 50;
    }

    for (int i = 0; i < lives_ && i < 3; ++i) {
        int idx = (15 * 16 + i * 2) * 3;
        fb_rgb24[idx + 0] = 46; fb_rgb24[idx + 1] = 204; fb_rgb24[idx + 2] = 113;
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

CartridgeStatus Game097Frogger::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = lives_;
    st.state = (uint8_t)state_;
    st.progress = (uint8_t)((homes_occupied_ * 100) / kNumHomes);
    return st;
}

} // namespace arcade

