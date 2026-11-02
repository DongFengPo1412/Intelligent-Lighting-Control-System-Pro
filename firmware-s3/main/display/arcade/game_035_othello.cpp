#include "game_035_othello.h"
#include <algorithm>

namespace arcade {

static const int DIRS[8][2] = {
    {-1, -1}, {0, -1}, {1, -1},
    {-1,  0},         {1,  0},
    {-1,  1}, {0,  1}, {1,  1}
};

static const int POS_WEIGHTS[8][8] = {
    { 100, -30,  20,   5,   5,  20, -30, 100 },
    { -30, -50,  -5,  -5,  -5,  -5, -50, -30 },
    {  20,  -5,  15,   3,   3,  15,  -5,  20 },
    {   5,  -5,   3,   3,   3,   3,  -5,   5 },
    {   5,  -5,   3,   3,   3,   3,  -5,   5 },
    {  20,  -5,  15,   3,   3,  15,  -5,  20 },
    { -30, -50,  -5,  -5,  -5,  -5, -50, -30 },
    { 100, -30,  20,   5,   5,  20, -30, 100 }
};

Game035Othello::Game035Othello()
    : state_(STATE_PLAYER_TURN),
      state_timer_(0.0f),
      score_(0),
      high_score_(0),
      cursor_x_(2),
      cursor_y_(3),
      black_count_(2),
      white_count_(2),
      ai_think_timer_(0.0f) {
}

void Game035Othello::Init() {
    Reset();
}

void Game035Othello::Reset() {
    state_ = STATE_PLAYER_TURN;
    state_timer_ = 0.0f;
    score_ = 0;
    cursor_x_ = 2;
    cursor_y_ = 3;
    ai_think_timer_ = 0.0f;
    InitBoard();
}

void Game035Othello::InitBoard() {
    for (int y = 0; y < BOARD_SIZE; ++y) {
        for (int x = 0; x < BOARD_SIZE; ++x) {
            board_[y][x] = PIECE_EMPTY;
        }
    }

    // Classic 4 central pieces
    board_[3][3] = PIECE_WHITE;
    board_[3][4] = PIECE_BLACK;
    board_[4][3] = PIECE_BLACK;
    board_[4][4] = PIECE_WHITE;

    UpdateCounts();
}

void Game035Othello::UpdateCounts() {
    black_count_ = 0;
    white_count_ = 0;
    for (int y = 0; y < BOARD_SIZE; ++y) {
        for (int x = 0; x < BOARD_SIZE; ++x) {
            if (board_[y][x] == PIECE_BLACK) black_count_++;
            else if (board_[y][x] == PIECE_WHITE) white_count_++;
        }
    }
    score_ = black_count_ * 50;
    if (score_ > high_score_) high_score_ = score_;
}

int Game035Othello::CountFlips(int x, int y, Piece color, int dx, int dy) const {
    Piece opp = (color == PIECE_BLACK) ? PIECE_WHITE : PIECE_BLACK;
    int cx = x + dx;
    int cy = y + dy;
    int count = 0;

    while (cx >= 0 && cx < BOARD_SIZE && cy >= 0 && cy < BOARD_SIZE && board_[cy][cx] == opp) {
        count++;
        cx += dx;
        cy += dy;
    }

    if (count > 0 && cx >= 0 && cx < BOARD_SIZE && cy >= 0 && cy < BOARD_SIZE && board_[cy][cx] == color) {
        return count;
    }
    return 0;
}

bool Game035Othello::IsValidMove(int x, int y, Piece color) const {
    if (x < 0 || x >= BOARD_SIZE || y < 0 || y >= BOARD_SIZE) return false;
    if (board_[y][x] != PIECE_EMPTY) return false;

    for (int i = 0; i < 8; ++i) {
        if (CountFlips(x, y, color, DIRS[i][0], DIRS[i][1]) > 0) {
            return true;
        }
    }
    return false;
}

bool Game035Othello::HasAnyValidMove(Piece color) const {
    for (int y = 0; y < BOARD_SIZE; ++y) {
        for (int x = 0; x < BOARD_SIZE; ++x) {
            if (IsValidMove(x, y, color)) return true;
        }
    }
    return false;
}

void Game035Othello::FlipDirection(int x, int y, Piece color, int dx, int dy) {
    Piece opp = (color == PIECE_BLACK) ? PIECE_WHITE : PIECE_BLACK;
    int cx = x + dx;
    int cy = y + dy;

    while (cx >= 0 && cx < BOARD_SIZE && cy >= 0 && cy < BOARD_SIZE && board_[cy][cx] == opp) {
        board_[cy][cx] = color;
        cx += dx;
        cy += dy;
    }
}

bool Game035Othello::PlaceMove(int x, int y, Piece color) {
    if (!IsValidMove(x, y, color)) return false;

    board_[y][x] = color;

    for (int i = 0; i < 8; ++i) {
        if (CountFlips(x, y, color, DIRS[i][0], DIRS[i][1]) > 0) {
            FlipDirection(x, y, color, DIRS[i][0], DIRS[i][1]);
        }
    }

    UpdateCounts();
    return true;
}

void Game035Othello::MakeAIMove() {
    int best_score = -999999;
    int best_x = -1;
    int best_y = -1;

    for (int y = 0; y < BOARD_SIZE; ++y) {
        for (int x = 0; x < BOARD_SIZE; ++x) {
            if (IsValidMove(x, y, PIECE_WHITE)) {
                int total_flips = 0;
                for (int i = 0; i < 8; ++i) {
                    total_flips += CountFlips(x, y, PIECE_WHITE, DIRS[i][0], DIRS[i][1]);
                }
                int eval = POS_WEIGHTS[y][x] + total_flips * 3;
                if (eval > best_score) {
                    best_score = eval;
                    best_x = x;
                    best_y = y;
                }
            }
        }
    }

    if (best_x != -1 && best_y != -1) {
        PlaceMove(best_x, best_y, PIECE_WHITE);
    }
}

void Game035Othello::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_GAMEOVER) {
        if (state_timer_ >= 2.0f && (buttons & (KEY_A | KEY_B))) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_PLAYER_TURN) {
        // Cursor controls
        if ((buttons & KEY_LEFT) && !(prev_buttons & KEY_LEFT)) {
            if (cursor_x_ > 0) cursor_x_--;
        } else if ((buttons & KEY_RIGHT) && !(prev_buttons & KEY_RIGHT)) {
            if (cursor_x_ < BOARD_SIZE - 1) cursor_x_++;
        } else if ((buttons & KEY_UP) && !(prev_buttons & KEY_UP)) {
            if (cursor_y_ > 0) cursor_y_--;
        } else if ((buttons & KEY_DOWN) && !(prev_buttons & KEY_DOWN)) {
            if (cursor_y_ < BOARD_SIZE - 1) cursor_y_++;
        }

        // Place stone
        if ((buttons & KEY_A) && !(prev_buttons & KEY_A)) {
            if (PlaceMove(cursor_x_, cursor_y_, PIECE_BLACK)) {
                // Check next turn
                if (HasAnyValidMove(PIECE_WHITE)) {
                    state_ = STATE_AI_TURN;
                    ai_think_timer_ = 0.5f;
                } else if (!HasAnyValidMove(PIECE_BLACK)) {
                    state_ = STATE_GAMEOVER;
                    state_timer_ = 0.0f;
                    if (black_count_ > white_count_) {
                        score_ += 1000 + (black_count_ - white_count_) * 50;
                        if (score_ > high_score_) high_score_ = score_;
                    }
                }
            }
        }
    } else if (state_ == STATE_AI_TURN) {
        ai_think_timer_ -= dt;
        if (ai_think_timer_ <= 0.0f) {
            MakeAIMove();

            if (HasAnyValidMove(PIECE_BLACK)) {
                state_ = STATE_PLAYER_TURN;
            } else if (!HasAnyValidMove(PIECE_WHITE)) {
                state_ = STATE_GAMEOVER;
                state_timer_ = 0.0f;
                if (black_count_ > white_count_) {
                    score_ += 1000 + (black_count_ - white_count_) * 50;
                    if (score_ > high_score_) high_score_ = score_;
                }
            } else {
                // AI gets consecutive move
                ai_think_timer_ = 0.5f;
            }
        }
    }
}

void Game035Othello::Render(uint8_t* fb) {
    // 1. Board Background: Dark Green Felt (#1B5E20)
    for (int cy = 0; cy < BOARD_SIZE; ++cy) {
        for (int cx = 0; cx < BOARD_SIZE; ++cx) {
            int px0 = cx * 2;
            int py0 = cy * 2;

            Piece p = board_[cy][cx];
            uint8_t r = 27, g = 94, b = 32; // Default green felt

            if (p == PIECE_BLACK) {
                // Obsidian Black
                r = 20; g = 25; b = 30;
            } else if (p == PIECE_WHITE) {
                // Pure White
                r = 245; g = 245; b = 245;
            }

            for (int dy = 0; dy < 2; ++dy) {
                for (int dx = 0; dx < 2; ++dx) {
                    int idx = ((py0 + dy) * 16 + (px0 + dx)) * 3;
                    fb[idx + 0] = r;
                    fb[idx + 1] = g;
                    fb[idx + 2] = b;
                }
            }

            // Valid move indicator for player
            if (state_ == STATE_PLAYER_TURN && p == PIECE_EMPTY && IsValidMove(cx, cy, PIECE_BLACK)) {
                int hint_idx = ((py0) * 16 + px0) * 3;
                fb[hint_idx + 0] = 50; fb[hint_idx + 1] = 160; fb[hint_idx + 2] = 60; // Subtle dot
            }
        }
    }

    // 2. Cursor Highlight (Blinking Gold #F1C40F on current cell)
    if (state_ == STATE_PLAYER_TURN) {
        bool blink = (static_cast<int>(state_timer_ * 6.0f) % 2 == 0);
        if (blink) {
            int cur_px = cursor_x_ * 2;
            int cur_py = cursor_y_ * 2;
            for (int dy = 0; dy < 2; ++dy) {
                for (int dx = 0; dx < 2; ++dx) {
                    int idx = ((cur_py + dy) * 16 + (cur_px + dx)) * 3;
                    fb[idx + 0] = 241; fb[idx + 1] = 196; fb[idx + 2] = 15;
                }
            }
        }
    }
}

} // namespace arcade
