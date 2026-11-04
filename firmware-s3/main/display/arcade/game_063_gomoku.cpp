// game_063_gomoku.cpp —— 目标 #063 五子棋 (Gomoku) 核心实现
#include "game_063_gomoku.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>
#include <stdlib.h>

namespace arcade {

static const int kGomokuAxes[4][2] = {
    {1, 0}, {0, 1}, {1, 1}, {1, -1}
};

static inline void SetPx063(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

Game063Gomoku::Game063Gomoku()
    : state_(STATE_TITLE),
      cursor_x_(7),
      cursor_y_(7),
      last_x_(-1),
      last_y_(-1),
      moves_count_(0),
      player_turn_(true),
      ai_timer_(0.0f),
      score_(0),
      high_score_(0),
      state_timer_(0.0f),
      anim_timer_(0.0f) {
    memset(board_, 0, sizeof(board_));
}

void Game063Gomoku::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

void Game063Gomoku::InitBoard() {
    memset(board_, kEmpty, sizeof(board_));
    cursor_x_ = 7;
    cursor_y_ = 7;
    last_x_ = -1;
    last_y_ = -1;
    moves_count_ = 0;
    player_turn_ = true;
    ai_timer_ = 0.0f;
}

void Game063Gomoku::Init() {
    Reset();
}

void Game063Gomoku::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    state_ = STATE_TITLE;
    score_ = 0;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    InitBoard();
}

void Game063Gomoku::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        state_ = STATE_PLAYING;
        score_ = 0;
        state_timer_ = 0.0f;
        anim_timer_ = 0.0f;
        InitBoard();
    }
}

void Game063Gomoku::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game063Gomoku::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

bool Game063Gomoku::CheckWinAt(int x, int y, uint8_t side) const {
    if (x < 0 || x >= kGridSize || y < 0 || y >= kGridSize) return false;
    if (board_[y][x] != side) return false;

    for (int a = 0; a < 4; ++a) {
        int dx = kGomokuAxes[a][0];
        int dy = kGomokuAxes[a][1];
        int cnt = 1;

        int cx = x + dx;
        int cy = y + dy;
        while (cx >= 0 && cx < kGridSize && cy >= 0 && cy < kGridSize && board_[cy][cx] == side) {
            cnt++;
            cx += dx;
            cy += dy;
        }

        cx = x - dx;
        cy = y - dy;
        while (cx >= 0 && cx < kGridSize && cy >= 0 && cy < kGridSize && board_[cy][cx] == side) {
            cnt++;
            cx -= dx;
            cy -= dy;
        }

        if (cnt >= 5) return true;
    }
    return false;
}

int Game063Gomoku::EvaluatePointForSide(int x, int y, uint8_t side) const {
    int total = 0;
    for (int a = 0; a < 4; ++a) {
        int dx = kGomokuAxes[a][0];
        int dy = kGomokuAxes[a][1];
        int run = 1;
        int open_ends = 0;

        int cx = x + dx;
        int cy = y + dy;
        while (cx >= 0 && cx < kGridSize && cy >= 0 && cy < kGridSize && board_[cy][cx] == side) {
            run++;
            cx += dx;
            cy += dy;
        }
        if (cx >= 0 && cx < kGridSize && cy >= 0 && cy < kGridSize && board_[cy][cx] == kEmpty) {
            open_ends++;
        }

        cx = x - dx;
        cy = y - dy;
        while (cx >= 0 && cx < kGridSize && cy >= 0 && cy < kGridSize && board_[cy][cx] == side) {
            run++;
            cx -= dx;
            cy -= dy;
        }
        if (cx >= 0 && cx < kGridSize && cy >= 0 && cy < kGridSize && board_[cy][cx] == kEmpty) {
            open_ends++;
        }

        if (run >= 5) {
            total += 100000;
        } else if (run == 4) {
            if (open_ends == 2) total += 15000;
            else if (open_ends == 1) total += 3500;
        } else if (run == 3) {
            if (open_ends == 2) total += 2500;
            else if (open_ends == 1) total += 300;
        } else if (run == 2) {
            if (open_ends == 2) total += 160;
            else if (open_ends == 1) total += 25;
        }
    }
    return total;
}

void Game063Gomoku::MakeAiMove() {
    int best_score = -1;
    int best_x = -1;
    int best_y = -1;

    for (int y = 0; y < kGridSize; ++y) {
        for (int x = 0; x < kGridSize; ++x) {
            if (board_[y][x] != kEmpty) continue;
            int atk = EvaluatePointForSide(x, y, kAi);
            int def = EvaluatePointForSide(x, y, kPlayer);
            int center_bonus = 14 - (abs(x - 7) + abs(y - 7));
            int val = atk * 10 + def * 9 + center_bonus;
            if (val > best_score) {
                best_score = val;
                best_x = x;
                best_y = y;
            }
        }
    }

    if (best_x >= 0 && best_y >= 0) {
        board_[best_y][best_x] = kAi;
        last_x_ = best_x;
        last_y_ = best_y;
        moves_count_++;
        if (CheckWinAt(best_x, best_y, kAi) || moves_count_ >= kGridSize * kGridSize) {
            state_ = STATE_GAMEOVER;
            state_timer_ = 0.0f;
            return;
        }
    }
    player_turn_ = true;
}

void Game063Gomoku::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    (void)keys_down;
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
        if (state_timer_ > 0.5f && (keys_pressed & (KEY_START | KEY_A | KEY_B))) {
            Start();
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

        if (player_turn_) {
            if (keys_pressed & KEY_LEFT) {
                if (cursor_x_ > 0) cursor_x_--;
            } else if (keys_pressed & KEY_RIGHT) {
                if (cursor_x_ < kGridSize - 1) cursor_x_++;
            }
            if (keys_pressed & KEY_UP) {
                if (cursor_y_ > 0) cursor_y_--;
            } else if (keys_pressed & KEY_DOWN) {
                if (cursor_y_ < kGridSize - 1) cursor_y_++;
            }

            if (keys_pressed & KEY_A) {
                if (board_[cursor_y_][cursor_x_] == kEmpty) {
                    board_[cursor_y_][cursor_x_] = kPlayer;
                    last_x_ = cursor_x_;
                    last_y_ = cursor_y_;
                    moves_count_++;
                    AddScore(10);

                    if (CheckWinAt(cursor_x_, cursor_y_, kPlayer)) {
                        AddScore(500);
                        state_ = STATE_VICTORY;
                        state_timer_ = 0.0f;
                        return;
                    }
                    if (moves_count_ >= kGridSize * kGridSize) {
                        state_ = STATE_GAMEOVER;
                        state_timer_ = 0.0f;
                        return;
                    }
                    player_turn_ = false;
                    ai_timer_ = 0.16f;
                }
            }
        } else {
            ai_timer_ -= dt;
            if (ai_timer_ <= 0.0f) {
                MakeAiMove();
            }
        }
    }
}

void Game063Gomoku::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (x < kGridSize && y < kGridSize) {
                bool is_star = ((x == 3 || x == 11) && (y == 3 || y == 11)) || (x == 7 && y == 7);
                if (is_star) {
                    SetPx063(fb_rgb24, x, y, 78, 54, 24);
                } else if ((x + y) % 2 == 0) {
                    SetPx063(fb_rgb24, x, y, 52, 35, 16);
                } else {
                    SetPx063(fb_rgb24, x, y, 42, 28, 12);
                }
            } else {
                SetPx063(fb_rgb24, x, y, 22, 14, 8);
            }
        }
    }

    if (player_turn_) {
        SetPx063(fb_rgb24, 15, 0, 0, 220, 255);
    } else {
        SetPx063(fb_rgb24, 15, 0, 255, 70, 35);
    }

    for (int y = 0; y < kGridSize; ++y) {
        for (int x = 0; x < kGridSize; ++x) {
            uint8_t v = board_[y][x];
            if (v == kPlayer) {
                if (x == last_x_ && y == last_y_) {
                    SetPx063(fb_rgb24, x, y, 255, 255, 255);
                } else {
                    SetPx063(fb_rgb24, x, y, 100, 240, 255);
                }
            } else if (v == kAi) {
                if (x == last_x_ && y == last_y_) {
                    SetPx063(fb_rgb24, x, y, 255, 155, 45);
                } else {
                    SetPx063(fb_rgb24, x, y, 245, 55, 35);
                }
            }
        }
    }

    if (state_ == STATE_PLAYING && player_turn_) {
        bool blink = (((int)(anim_timer_ * 6.0f)) % 2 == 0);
        if (blink) {
            SetPx063(fb_rgb24, cursor_x_, cursor_y_, 255, 235, 40);
        }
    }

    if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPx063(fb_rgb24, 6, y, 250, 250, 250);
            SetPx063(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game063Gomoku::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = (state_ == STATE_GAMEOVER) ? 0 : 1;
    st.state = (uint8_t)state_;
    int prog = (moves_count_ * 100) / 40;
    st.progress = (uint8_t)(prog > 100 ? 100 : prog);
    return st;
}

static_assert(sizeof(Game063Gomoku) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
