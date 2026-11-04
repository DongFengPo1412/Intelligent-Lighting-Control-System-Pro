// game_054_sokoban.cpp —— 目标 #054 推箱子 核心实现
#include "game_054_sokoban.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>

namespace arcade {

Game054Sokoban::Game054Sokoban()
    : state_(STATE_TITLE),
      player_x_(7),
      player_y_(8),
      moves_(0),
      score_(0),
      high_score_(0),
      state_timer_(0.0f),
      anim_timer_(0.0f),
      boxes_on_goal_(0) {
}

int Game054Sokoban::FindBoxAt(int x, int y) const {
    for (int i = 0; i < kNumBoxes; ++i) {
        if (boxes_[i].x == x && boxes_[i].y == y) {
            return i;
        }
    }
    return -1;
}

bool Game054Sokoban::IsGoal(int x, int y) const {
    if (x < 0 || x >= 16 || y < 0 || y >= 16) return false;
    return map_[y][x] == SOKOBAN_GOAL;
}

void Game054Sokoban::ResetLevel() {
    memset(map_, SOKOBAN_FLOOR, sizeof(map_));

    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (x < 2 || x > 13 || y < 2 || y > 13) {
                map_[y][x] = SOKOBAN_WALL;
            }
        }
    }

    for (int x = 2; x <= 13; ++x) {
        map_[2][x] = SOKOBAN_WALL;
        map_[13][x] = SOKOBAN_WALL;
    }
    for (int y = 2; y <= 13; ++y) {
        map_[y][2] = SOKOBAN_WALL;
        map_[y][13] = SOKOBAN_WALL;
    }

    map_[5][8] = SOKOBAN_WALL;
    map_[6][8] = SOKOBAN_WALL;
    map_[9][7] = SOKOBAN_WALL;
    map_[10][7] = SOKOBAN_WALL;

    map_[4][4] = SOKOBAN_GOAL;
    map_[4][5] = SOKOBAN_GOAL;
    map_[11][10] = SOKOBAN_GOAL;
    map_[11][11] = SOKOBAN_GOAL;

    boxes_[0] = {5, 6};
    boxes_[1] = {6, 6};
    boxes_[2] = {9, 9};
    boxes_[3] = {10, 9};

    player_x_ = 7;
    player_y_ = 8;
    moves_ = 0;

    CheckVictory();
}

void Game054Sokoban::Init() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    Reset();
}

void Game054Sokoban::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    state_ = STATE_TITLE;
    score_ = 0;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    ResetLevel();
}

void Game054Sokoban::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        state_ = STATE_PLAYING;
        score_ = 0;
        state_timer_ = 0.0f;
        anim_timer_ = 0.0f;
        ResetLevel();
    }
}

void Game054Sokoban::Pause() {
    if (state_ == STATE_PLAYING) state_ = STATE_PAUSED;
}

void Game054Sokoban::Resume() {
    if (state_ == STATE_PAUSED) state_ = STATE_PLAYING;
}

void Game054Sokoban::CheckVictory() {
    int on_goal = 0;
    for (int i = 0; i < kNumBoxes; ++i) {
        if (IsGoal(boxes_[i].x, boxes_[i].y)) {
            on_goal++;
        }
    }
    boxes_on_goal_ = on_goal;

    if (boxes_on_goal_ == kNumBoxes) {
        state_ = STATE_VICTORY;
        state_timer_ = 0.0f;
        int calculated_score = 1000 - ((int)moves_ * 5);
        score_ = calculated_score > 100 ? (uint32_t)calculated_score : 100;
        if (score_ > high_score_) {
            high_score_ = score_;
            ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
        }
    }
}

void Game054Sokoban::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
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

        if (keys_pressed & KEY_SELECT) {
            ResetLevel();
            return;
        }

        int dx = 0, dy = 0;
        if (keys_pressed & KEY_UP) dy = -1;
        else if (keys_pressed & KEY_DOWN) dy = 1;
        else if (keys_pressed & KEY_LEFT) dx = -1;
        else if (keys_pressed & KEY_RIGHT) dx = 1;

        if (dx != 0 || dy != 0) {
            int tx = player_x_ + dx;
            int ty = player_y_ + dy;

            if (map_[ty][tx] != SOKOBAN_WALL) {
                int box_idx = FindBoxAt(tx, ty);
                if (box_idx == -1) {
                    player_x_ = tx;
                    player_y_ = ty;
                    moves_++;
                } else {
                    int behind_x = tx + dx;
                    int behind_y = ty + dy;
                    if (map_[behind_y][behind_x] != SOKOBAN_WALL && FindBoxAt(behind_x, behind_y) == -1) {
                        boxes_[box_idx].x = behind_x;
                        boxes_[box_idx].y = behind_y;
                        player_x_ = tx;
                        player_y_ = ty;
                        moves_++;
                        CheckVictory();
                    }
                }
            }
        }
    }
}

void Game054Sokoban::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    memset(fb_rgb24, 0, 16 * 16 * 3);

    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            if (map_[y][x] == SOKOBAN_WALL) {
                fb_rgb24[idx + 0] = 70; fb_rgb24[idx + 1] = 80; fb_rgb24[idx + 2] = 95;
            } else if (map_[y][x] == SOKOBAN_GOAL) {
                fb_rgb24[idx + 0] = 231; fb_rgb24[idx + 1] = 76; fb_rgb24[idx + 2] = 60;
            } else {
                if (x >= 2 && x <= 13 && y >= 2 && y <= 13) {
                    fb_rgb24[idx + 0] = 25; fb_rgb24[idx + 1] = 25; fb_rgb24[idx + 2] = 28;
                }
            }
        }
    }

    for (int i = 0; i < kNumBoxes; ++i) {
        int bx = boxes_[i].x;
        int by = boxes_[i].y;
        if (bx >= 0 && bx < 16 && by >= 0 && by < 16) {
            int idx = (by * 16 + bx) * 3;
            if (IsGoal(bx, by)) {
                fb_rgb24[idx + 0] = 46; fb_rgb24[idx + 1] = 204; fb_rgb24[idx + 2] = 113;
            } else {
                fb_rgb24[idx + 0] = 241; fb_rgb24[idx + 1] = 196; fb_rgb24[idx + 2] = 15;
            }
        }
    }

    int px = player_x_;
    int py = player_y_;
    if (px >= 0 && px < 16 && py >= 0 && py < 16) {
        int idx = (py * 16 + px) * 3;
        fb_rgb24[idx + 0] = 52; fb_rgb24[idx + 1] = 152; fb_rgb24[idx + 2] = 219;
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

CartridgeStatus Game054Sokoban::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = 1;
    st.state = (uint8_t)state_;
    st.progress = (uint8_t)((boxes_on_goal_ * 100) / kNumBoxes);
    return st;
}

} // namespace arcade

