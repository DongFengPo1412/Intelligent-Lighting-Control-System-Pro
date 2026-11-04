// game_062_reversi.cpp —— 目标 #062 黑白棋 (Reversi) 核心实现
#include "game_062_reversi.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>

namespace arcade {

static const int kRevDirs[8][2] = {
    {-1, -1}, {0, -1}, {1, -1},
    {-1,  0},          {1,  0},
    {-1,  1}, {0,  1}, {1,  1}
};

static const int kPosWeights[8][8] = {
    { 100, -30,  20,   6,   6,  20, -30, 100 },
    { -30, -50,  -6,  -4,  -4,  -6, -50, -30 },
    {  20,  -6,  15,   4,   4,  15,  -6,  20 },
    {   6,  -4,   4,   2,   2,   4,  -4,   6 },
    {   6,  -4,   4,   2,   2,   4,  -4,   6 },
    {  20,  -6,  15,   4,   4,  15,  -6,  20 },
    { -30, -50,  -6,  -4,  -4,  -6, -50, -30 },
    { 100, -30,  20,   6,   6,  20, -30, 100 }
};

static inline void SetPx062(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

Game062Reversi::Game062Reversi()
    : state_(STATE_TITLE),
      cursor_x_(2),
      cursor_y_(3),
      player_turn_(true),
      ai_timer_(0.0f),
      player_count_(2),
      ai_count_(2),
      score_(0),
      high_score_(0),
      state_timer_(0.0f),
      anim_timer_(0.0f) {
    memset(board_, 0, sizeof(board_));
}

void Game062Reversi::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

void Game062Reversi::UpdateDiscCounts() {
    int p = 0;
    int a = 0;
    for (int y = 0; y < kBoardSize; ++y) {
        for (int x = 0; x < kBoardSize; ++x) {
            if (board_[y][x] == kPlayer) p++;
            else if (board_[y][x] == kAi) a++;
        }
    }
    player_count_ = p;
    ai_count_ = a;
}

void Game062Reversi::InitBoard() {
    memset(board_, kEmpty, sizeof(board_));
    board_[3][3] = kAi;
    board_[3][4] = kPlayer;
    board_[4][3] = kPlayer;
    board_[4][4] = kAi;
    cursor_x_ = 2;
    cursor_y_ = 3;
    player_turn_ = true;
    ai_timer_ = 0.0f;
    UpdateDiscCounts();
}

void Game062Reversi::Init() {
    Reset();
}

void Game062Reversi::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    state_ = STATE_TITLE;
    score_ = 0;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    InitBoard();
}

void Game062Reversi::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        state_ = STATE_PLAYING;
        score_ = 0;
        state_timer_ = 0.0f;
        anim_timer_ = 0.0f;
        InitBoard();
    }
}

void Game062Reversi::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game062Reversi::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

int Game062Reversi::CountFlipsDir(int x, int y, uint8_t side, int dx, int dy) const {
    uint8_t opp = (side == kPlayer) ? kAi : kPlayer;
    int cx = x + dx;
    int cy = y + dy;
    int count = 0;
    while (cx >= 0 && cx < kBoardSize && cy >= 0 && cy < kBoardSize && board_[cy][cx] == opp) {
        count++;
        cx += dx;
        cy += dy;
    }
    if (count > 0 && cx >= 0 && cx < kBoardSize && cy >= 0 && cy < kBoardSize && board_[cy][cx] == side) {
        return count;
    }
    return 0;
}

int Game062Reversi::TotalFlips(int x, int y, uint8_t side) const {
    if (x < 0 || x >= kBoardSize || y < 0 || y >= kBoardSize) return 0;
    if (board_[y][x] != kEmpty) return 0;
    int total = 0;
    for (int i = 0; i < 8; ++i) {
        total += CountFlipsDir(x, y, side, kRevDirs[i][0], kRevDirs[i][1]);
    }
    return total;
}

bool Game062Reversi::IsValidMove(int x, int y, uint8_t side) const {
    return TotalFlips(x, y, side) > 0;
}

bool Game062Reversi::HasValidMove(uint8_t side) const {
    for (int y = 0; y < kBoardSize; ++y) {
        for (int x = 0; x < kBoardSize; ++x) {
            if (IsValidMove(x, y, side)) return true;
        }
    }
    return false;
}

int Game062Reversi::PlaceDisc(int x, int y, uint8_t side) {
    int total = TotalFlips(x, y, side);
    if (total <= 0) return 0;

    uint8_t opp = (side == kPlayer) ? kAi : kPlayer;
    board_[y][x] = side;
    for (int i = 0; i < 8; ++i) {
        int dx = kRevDirs[i][0];
        int dy = kRevDirs[i][1];
        if (CountFlipsDir(x, y, side, dx, dy) > 0) {
            int cx = x + dx;
            int cy = y + dy;
            while (cx >= 0 && cx < kBoardSize && cy >= 0 && cy < kBoardSize && board_[cy][cx] == opp) {
                board_[cy][cx] = side;
                cx += dx;
                cy += dy;
            }
        }
    }
    UpdateDiscCounts();
    return total;
}

void Game062Reversi::FinishGame() {
    UpdateDiscCounts();
    if (player_count_ > ai_count_) {
        AddScore(200u + (uint32_t)(player_count_ - ai_count_) * 10u);
        state_ = STATE_VICTORY;
    } else {
        state_ = STATE_GAMEOVER;
    }
    state_timer_ = 0.0f;
}

void Game062Reversi::ResolveNextTurn(uint8_t preferred_next) {
    uint8_t other = (preferred_next == kPlayer) ? kAi : kPlayer;
    if (HasValidMove(preferred_next)) {
        player_turn_ = (preferred_next == kPlayer);
        if (!player_turn_) {
            ai_timer_ = 0.22f;
        }
    } else if (HasValidMove(other)) {
        player_turn_ = (other == kPlayer);
        if (!player_turn_) {
            ai_timer_ = 0.22f;
        }
    } else {
        FinishGame();
    }
}

void Game062Reversi::MakeAiMove() {
    int best_eval = -999999;
    int best_x = -1;
    int best_y = -1;

    for (int y = 0; y < kBoardSize; ++y) {
        for (int x = 0; x < kBoardSize; ++x) {
            int flips = TotalFlips(x, y, kAi);
            if (flips > 0) {
                int eval = kPosWeights[y][x] + flips * 3;
                if (eval > best_eval) {
                    best_eval = eval;
                    best_x = x;
                    best_y = y;
                }
            }
        }
    }

    if (best_x >= 0 && best_y >= 0) {
        PlaceDisc(best_x, best_y, kAi);
    }
}

void Game062Reversi::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
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

            if (keys_pressed & KEY_A) {
                int flipped = PlaceDisc(cursor_x_, cursor_y_, kPlayer);
                if (flipped > 0) {
                    AddScore((uint32_t)(flipped * 10));
                    ResolveNextTurn(kAi);
                }
            }
        } else {
            ai_timer_ -= dt;
            if (ai_timer_ <= 0.0f) {
                MakeAiMove();
                ResolveNextTurn(kPlayer);
            }
        }
    }
}

void Game062Reversi::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    for (int cy = 0; cy < kBoardSize; ++cy) {
        for (int cx = 0; cx < kBoardSize; ++cx) {
            int px = cx * 2;
            int py = cy * 2;
            bool even = ((cx + cy) % 2 == 0);
            uint8_t br = even ? 14 : 20;
            uint8_t bg = even ? 58 : 74;
            uint8_t bb = even ? 28 : 36;

            uint8_t p = board_[cy][cx];
            if (p == kPlayer) {
                SetPx062(fb_rgb24, px,     py,     110, 250, 255);
                SetPx062(fb_rgb24, px + 1, py,       0, 210, 245);
                SetPx062(fb_rgb24, px,     py + 1,   0, 210, 245);
                SetPx062(fb_rgb24, px + 1, py + 1,   0, 165, 210);
            } else if (p == kAi) {
                SetPx062(fb_rgb24, px,     py,     255, 215,  80);
                SetPx062(fb_rgb24, px + 1, py,     255, 150,  20);
                SetPx062(fb_rgb24, px,     py + 1, 255, 150,  20);
                SetPx062(fb_rgb24, px + 1, py + 1, 210, 100,  10);
            } else {
                SetPx062(fb_rgb24, px,     py,     br, bg, bb);
                SetPx062(fb_rgb24, px + 1, py,     br, bg, bb);
                SetPx062(fb_rgb24, px,     py + 1, br, bg, bb);
                SetPx062(fb_rgb24, px + 1, py + 1, br, bg, bb);

                if (state_ == STATE_PLAYING && player_turn_ && IsValidMove(cx, cy, kPlayer)) {
                    SetPx062(fb_rgb24, px, py, 55, 165, 110);
                }
            }
        }
    }

    if (state_ == STATE_PLAYING && player_turn_) {
        bool blink = (((int)(anim_timer_ * 6.0f)) % 2 == 0);
        if (blink) {
            int px = cursor_x_ * 2;
            int py = cursor_y_ * 2;
            SetPx062(fb_rgb24, px,     py,     255, 240, 60);
            SetPx062(fb_rgb24, px + 1, py + 1, 255, 240, 60);
        }
    }

    if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPx062(fb_rgb24, 6, y, 250, 250, 250);
            SetPx062(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game062Reversi::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = (state_ == STATE_GAMEOVER) ? 0 : 1;
    st.state = (uint8_t)state_;
    int total = player_count_ + ai_count_;
    st.progress = (uint8_t)((total * 100) / 64);
    return st;
}

static_assert(sizeof(Game062Reversi) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
