// game_064_checkers.cpp —— 目标 #064 西洋跳棋 (Checkers) 核心实现
#include "game_064_checkers.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>
#include <stdlib.h>

namespace arcade {

static inline void SetPx064(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

Game064Checkers::Game064Checkers()
    : state_(STATE_TITLE),
      cursor_x_(1),
      cursor_y_(5),
      selected_x_(-1),
      selected_y_(-1),
      in_chain_jump_(false),
      player_turn_(true),
      ai_timer_(0.0f),
      quiet_turns_(0),
      score_(0),
      high_score_(0),
      state_timer_(0.0f),
      anim_timer_(0.0f) {
    memset(board_, 0, sizeof(board_));
}

void Game064Checkers::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

void Game064Checkers::InitBoard() {
    memset(board_, kEmpty, sizeof(board_));
    for (int y = 0; y < kBoardSize; ++y) {
        for (int x = 0; x < kBoardSize; ++x) {
            if ((x + y) % 2 == 1) {
                if (y <= 2) {
                    board_[y][x] = kAiMan;
                } else if (y >= 5) {
                    board_[y][x] = kPMan;
                }
            }
        }
    }
    cursor_x_ = 1;
    cursor_y_ = 5;
    selected_x_ = -1;
    selected_y_ = -1;
    in_chain_jump_ = false;
    player_turn_ = true;
    ai_timer_ = 0.0f;
    quiet_turns_ = 0;
}

void Game064Checkers::Init() {
    Reset();
}

void Game064Checkers::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    state_ = STATE_TITLE;
    score_ = 0;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    InitBoard();
}

void Game064Checkers::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        state_ = STATE_PLAYING;
        score_ = 0;
        state_timer_ = 0.0f;
        anim_timer_ = 0.0f;
        InitBoard();
    }
}

void Game064Checkers::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game064Checkers::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

bool Game064Checkers::CanDirY(uint8_t p, int dy) const {
    if (p == kPMan) return dy == -1;
    if (p == kAiMan) return dy == 1;
    if (p == kPKing || p == kAiKing) return (dy == -1 || dy == 1);
    return false;
}

bool Game064Checkers::IsValidMove(int sx, int sy, int tx, int ty, bool jump_only) const {
    if (sx < 0 || sx >= kBoardSize || sy < 0 || sy >= kBoardSize) return false;
    if (tx < 0 || tx >= kBoardSize || ty < 0 || ty >= kBoardSize) return false;
    if (board_[ty][tx] != kEmpty) return false;

    uint8_t p = board_[sy][sx];
    if (p == kEmpty) return false;
    bool p_side = IsPlayerPiece(p);

    int dx = tx - sx;
    int dy = ty - sy;
    if (!jump_only && abs(dx) == 1 && abs(dy) == 1) {
        return CanDirY(p, dy);
    }
    if (abs(dx) == 2 && abs(dy) == 2) {
        int step_y = dy / 2;
        if (!CanDirY(p, step_y)) return false;
        int mx = (sx + tx) / 2;
        int my = (sy + ty) / 2;
        uint8_t mid = board_[my][mx];
        if (p_side && IsAiPiece(mid)) return true;
        if (!p_side && IsPlayerPiece(mid)) return true;
    }
    return false;
}

bool Game064Checkers::HasMoveFrom(int sx, int sy, bool jump_only) const {
    for (int dy = -2; dy <= 2; ++dy) {
        if (dy == 0) continue;
        for (int dx = -2; dx <= 2; ++dx) {
            if (abs(dx) != abs(dy)) continue;
            if (IsValidMove(sx, sy, sx + dx, sy + dy, jump_only)) {
                return true;
            }
        }
    }
    return false;
}

bool Game064Checkers::SideHasAnyMove(bool for_player) const {
    for (int y = 0; y < kBoardSize; ++y) {
        for (int x = 0; x < kBoardSize; ++x) {
            uint8_t p = board_[y][x];
            if ((for_player && IsPlayerPiece(p)) || (!for_player && IsAiPiece(p))) {
                if (HasMoveFrom(x, y, false)) return true;
            }
        }
    }
    return false;
}

int Game064Checkers::CountPieces(bool for_player) const {
    int cnt = 0;
    for (int y = 0; y < kBoardSize; ++y) {
        for (int x = 0; x < kBoardSize; ++x) {
            uint8_t p = board_[y][x];
            if ((for_player && IsPlayerPiece(p)) || (!for_player && IsAiPiece(p))) {
                cnt++;
            }
        }
    }
    return cnt;
}

bool Game064Checkers::WouldBeCapturableAt(int tx, int ty, int from_x, int from_y) const {
    for (int dy = -1; dy <= 1; dy += 2) {
        for (int dx = -1; dx <= 1; dx += 2) {
            int ax = tx + dx;
            int ay = ty + dy;
            int lx = tx - dx;
            int ly = ty - dy;
            if (ax < 0 || ax >= kBoardSize || ay < 0 || ay >= kBoardSize) continue;
            if (lx < 0 || lx >= kBoardSize || ly < 0 || ly >= kBoardSize) continue;
            bool landing_empty = (board_[ly][lx] == kEmpty) || (lx == from_x && ly == from_y);
            if (!landing_empty) continue;
            uint8_t opp = board_[ay][ax];
            if (IsPlayerPiece(opp) && CanDirY(opp, ly - ty)) {
                return true;
            }
        }
    }
    return false;
}

void Game064Checkers::EndPlayerTurn() {
    selected_x_ = -1;
    selected_y_ = -1;
    in_chain_jump_ = false;

    if (CountPieces(false) == 0 || !SideHasAnyMove(false)) {
        AddScore(300);
        state_ = STATE_VICTORY;
        state_timer_ = 0.0f;
        return;
    }
    if (quiet_turns_ >= 80) {
        if (CountPieces(true) > CountPieces(false)) {
            AddScore(200);
            state_ = STATE_VICTORY;
        } else {
            state_ = STATE_GAMEOVER;
        }
        state_timer_ = 0.0f;
        return;
    }

    player_turn_ = false;
    ai_timer_ = 0.22f;
}

void Game064Checkers::MakeAiTurn() {
    int best_eval = -999999;
    int best_sx = -1, best_sy = -1, best_tx = -1, best_ty = -1;

    for (int sy = 0; sy < kBoardSize; ++sy) {
        for (int sx = 0; sx < kBoardSize; ++sx) {
            uint8_t p = board_[sy][sx];
            if (!IsAiPiece(p)) continue;

            for (int dy = -2; dy <= 2; ++dy) {
                if (dy == 0) continue;
                for (int dx = -2; dx <= 2; ++dx) {
                    if (abs(dx) != abs(dy)) continue;
                    int tx = sx + dx;
                    int ty = sy + dy;
                    if (!IsValidMove(sx, sy, tx, ty, false)) continue;

                    int eval = 0;
                    if (abs(dx) == 2) {
                        eval += 120;
                    } else {
                        if (p == kAiMan && dy > 0) eval += 8 + ty * 2;
                        if (sy == 0 && p == kAiMan) eval -= 6;
                    }
                    if (p == kAiMan && ty == kBoardSize - 1) {
                        eval += 40;
                    }
                    if (WouldBeCapturableAt(tx, ty, sx, sy)) {
                        eval -= 35;
                    }
                    if (tx >= 2 && tx <= 5) {
                        eval += 3;
                    }

                    if (eval > best_eval) {
                        best_eval = eval;
                        best_sx = sx;
                        best_sy = sy;
                        best_tx = tx;
                        best_ty = ty;
                    }
                }
            }
        }
    }

    if (best_sx >= 0) {
        int sx = best_sx, sy = best_sy, tx = best_tx, ty = best_ty;
        uint8_t p = board_[sy][sx];
        board_[sy][sx] = kEmpty;
        bool jumped = (abs(tx - sx) == 2);
        if (jumped) {
            board_[(sy + ty) / 2][(sx + tx) / 2] = kEmpty;
            quiet_turns_ = 0;
        } else {
            quiet_turns_++;
        }
        bool promoted = false;
        if (p == kAiMan && ty == kBoardSize - 1) {
            p = kAiKing;
            promoted = true;
        }
        board_[ty][tx] = p;

        while (jumped && !promoted && HasMoveFrom(tx, ty, true)) {
            int next_tx = -1, next_ty = -1;
            for (int dy = -2; dy <= 2; dy += 4) {
                for (int dx = -2; dx <= 2; dx += 4) {
                    if (IsValidMove(tx, ty, tx + dx, ty + dy, true)) {
                        next_tx = tx + dx;
                        next_ty = ty + dy;
                        break;
                    }
                }
                if (next_tx >= 0) break;
            }
            if (next_tx < 0) break;
            board_[ty][tx] = kEmpty;
            board_[(ty + next_ty) / 2][(tx + next_tx) / 2] = kEmpty;
            tx = next_tx;
            ty = next_ty;
            if (p == kAiMan && ty == kBoardSize - 1) {
                p = kAiKing;
                promoted = true;
            }
            board_[ty][tx] = p;
        }
    }

    if (CountPieces(true) == 0 || !SideHasAnyMove(true)) {
        state_ = STATE_GAMEOVER;
        state_timer_ = 0.0f;
        return;
    }
    if (quiet_turns_ >= 80) {
        if (CountPieces(true) > CountPieces(false)) {
            AddScore(200);
            state_ = STATE_VICTORY;
        } else {
            state_ = STATE_GAMEOVER;
        }
        state_timer_ = 0.0f;
        return;
    }
    player_turn_ = true;
}

void Game064Checkers::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
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
                if (cursor_x_ < kBoardSize - 1) cursor_x_++;
            }
            if (keys_pressed & KEY_UP) {
                if (cursor_y_ > 0) cursor_y_--;
            } else if (keys_pressed & KEY_DOWN) {
                if (cursor_y_ < kBoardSize - 1) cursor_y_++;
            }

            if (keys_pressed & KEY_B) {
                if (in_chain_jump_) {
                    EndPlayerTurn();
                } else {
                    selected_x_ = -1;
                    selected_y_ = -1;
                }
                return;
            }

            if (keys_pressed & KEY_A) {
                if (selected_x_ >= 0 && IsValidMove(selected_x_, selected_y_, cursor_x_, cursor_y_, in_chain_jump_)) {
                    int sx = selected_x_;
                    int sy = selected_y_;
                    int tx = cursor_x_;
                    int ty = cursor_y_;
                    uint8_t p = board_[sy][sx];
                    board_[sy][sx] = kEmpty;

                    bool jumped = (abs(tx - sx) == 2);
                    if (jumped) {
                        board_[(sy + ty) / 2][(sx + tx) / 2] = kEmpty;
                        AddScore(50);
                        quiet_turns_ = 0;
                    } else {
                        quiet_turns_++;
                    }

                    bool promoted = false;
                    if (p == kPMan && ty == 0) {
                        p = kPKing;
                        promoted = true;
                    }
                    board_[ty][tx] = p;

                    if (CountPieces(false) == 0) {
                        AddScore(300);
                        state_ = STATE_VICTORY;
                        state_timer_ = 0.0f;
                        return;
                    }

                    if (jumped && !promoted && HasMoveFrom(tx, ty, true)) {
                        selected_x_ = tx;
                        selected_y_ = ty;
                        in_chain_jump_ = true;
                    } else {
                        EndPlayerTurn();
                    }
                } else if (!in_chain_jump_) {
                    uint8_t clicked = board_[cursor_y_][cursor_x_];
                    if (IsPlayerPiece(clicked) && HasMoveFrom(cursor_x_, cursor_y_, false)) {
                        selected_x_ = cursor_x_;
                        selected_y_ = cursor_y_;
                    }
                }
            }
        } else {
            ai_timer_ -= dt;
            if (ai_timer_ <= 0.0f) {
                MakeAiTurn();
            }
        }
    }
}

void Game064Checkers::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    for (int cy = 0; cy < kBoardSize; ++cy) {
        for (int cx = 0; cx < kBoardSize; ++cx) {
            int px = cx * 2;
            int py = cy * 2;
            bool dark = ((cx + cy) % 2 == 1);
            uint8_t br = dark ? 24 : 64;
            uint8_t bg = dark ? 20 : 52;
            uint8_t bb = dark ? 18 : 38;

            uint8_t p = board_[cy][cx];
            if (p == kEmpty) {
                SetPx064(fb_rgb24, px,     py,     br, bg, bb);
                SetPx064(fb_rgb24, px + 1, py,     br, bg, bb);
                SetPx064(fb_rgb24, px,     py + 1, br, bg, bb);
                SetPx064(fb_rgb24, px + 1, py + 1, br, bg, bb);

                if (state_ == STATE_PLAYING && player_turn_ && selected_x_ >= 0 &&
                    IsValidMove(selected_x_, selected_y_, cx, cy, in_chain_jump_)) {
                    SetPx064(fb_rgb24, px,     py,     46, 210, 115);
                    SetPx064(fb_rgb24, px + 1, py + 1, 46, 210, 115);
                }
            } else if (IsPlayerPiece(p)) {
                SetPx064(fb_rgb24, px,     py,     80, 245, 255);
                SetPx064(fb_rgb24, px + 1, py,      0, 205, 240);
                SetPx064(fb_rgb24, px,     py + 1,  0, 205, 240);
                SetPx064(fb_rgb24, px + 1, py + 1,  0, 160, 205);
                if (p == kPKing) {
                    SetPx064(fb_rgb24, px + 1, py, 255, 220, 20);
                }
            } else {
                SetPx064(fb_rgb24, px,     py,     255, 110, 100);
                SetPx064(fb_rgb24, px + 1, py,     230,  45,  45);
                SetPx064(fb_rgb24, px,     py + 1, 230,  45,  45);
                SetPx064(fb_rgb24, px + 1, py + 1, 180,  25,  25);
                if (p == kAiKing) {
                    SetPx064(fb_rgb24, px + 1, py, 255, 220, 20);
                }
            }

            if (cx == selected_x_ && cy == selected_y_) {
                SetPx064(fb_rgb24, px, py, 130, 255, 140);
            }
        }
    }

    if (state_ == STATE_PLAYING && player_turn_) {
        bool blink = (((int)(anim_timer_ * 6.0f)) % 2 == 0);
        if (blink) {
            int px = cursor_x_ * 2;
            int py = cursor_y_ * 2;
            SetPx064(fb_rgb24, px,     py,     255, 240, 50);
            SetPx064(fb_rgb24, px + 1, py + 1, 255, 240, 50);
        }
    }

    if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPx064(fb_rgb24, 6, y, 250, 250, 250);
            SetPx064(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game064Checkers::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = (state_ == STATE_GAMEOVER) ? 0 : 1;
    st.state = (uint8_t)state_;
    int ai_left = CountPieces(false);
    int captured = 12 - ai_left;
    if (captured < 0) captured = 0;
    st.progress = (uint8_t)((captured * 100) / 12);
    return st;
}

static_assert(sizeof(Game064Checkers) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
