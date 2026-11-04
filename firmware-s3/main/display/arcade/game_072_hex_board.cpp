// game_072_hex_board.cpp —— 目标 #072 Hex连通棋 (Hex Connection, 1985)
#include "game_072_hex_board.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>
#include <math.h>
#include <stdlib.h>

namespace arcade {

static const int kHexNeighbors[6][2] = {
    {-1, 0}, {-1, 1}, {0, -1}, {0, 1}, {1, -1}, {1, 0}
};

// 6 Hex two-bridge patterns: {target_dr, target_dc, c1_dr, c1_dc, c2_dr, c2_dc}
static const int kHexBridges[6][6] = {
    {-1,  2, -1,  1,  0,  1},
    { 1, -2,  0, -1,  1, -1},
    {-2,  1, -1,  0, -1,  1},
    { 2, -1,  1, -1,  1,  0},
    { 1,  1,  0,  1,  1,  0},
    {-1, -1, -1,  0,  0, -1}
};

static inline void SetPixel72(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

Game072HexBoard::Game072HexBoard()
    : state_(STATE_TITLE),
      cursor_r_(3),
      cursor_c_(3),
      turn_player_(true),
      ai_timer_(0.0f),
      moves_count_(0),
      last_ai_r_(-1),
      last_ai_c_(-1),
      score_(0),
      high_score_(0),
      state_timer_(0.0f),
      anim_timer_(0.0f),
      rng_state_(0x72721985u) {
    InitGameData();
}

uint32_t Game072HexBoard::NextRand() {
    rng_state_ = rng_state_ * 1103515245u + 12345u;
    return (rng_state_ >> 16) & 0x7FFFu;
}

void Game072HexBoard::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

void Game072HexBoard::InitGameData() {
    memset(board_, 0, sizeof(board_));
    cursor_r_ = 3;
    cursor_c_ = 3;
    turn_player_ = true;
    ai_timer_ = 0.0f;
    moves_count_ = 0;
    last_ai_r_ = -1;
    last_ai_c_ = -1;
    score_ = 0;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    rng_state_ = 0x72721985u;
}

void Game072HexBoard::Init() {
    Reset();
}

void Game072HexBoard::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    state_ = STATE_TITLE;
    InitGameData();
}

void Game072HexBoard::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        InitGameData();
        state_ = STATE_PLAYING;
    }
}

void Game072HexBoard::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game072HexBoard::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

bool Game072HexBoard::CheckConnectivity(uint8_t who) const {
    bool visited[kBoardSize][kBoardSize];
    memset(visited, 0, sizeof(visited));

    int qr[kBoardSize * kBoardSize];
    int qc[kBoardSize * kBoardSize];
    int head = 0;
    int tail = 0;

    if (who == 1) {
        // Player connects Top (r=0) to Bottom (r=6)
        for (int c = 0; c < kBoardSize; ++c) {
            if (board_[0][c] == 1) {
                visited[0][c] = true;
                qr[tail] = 0;
                qc[tail] = c;
                tail++;
            }
        }
    } else {
        // AI connects Left (c=0) to Right (c=6)
        for (int r = 0; r < kBoardSize; ++r) {
            if (board_[r][0] == 2) {
                visited[r][0] = true;
                qr[tail] = r;
                qc[tail] = 0;
                tail++;
            }
        }
    }

    while (head < tail) {
        int cr = qr[head];
        int cc = qc[head];
        head++;

        if (who == 1 && cr == kBoardSize - 1) return true;
        if (who == 2 && cc == kBoardSize - 1) return true;

        for (int k = 0; k < 6; ++k) {
            int nr = cr + kHexNeighbors[k][0];
            int nc = cc + kHexNeighbors[k][1];
            if (nr >= 0 && nr < kBoardSize && nc >= 0 && nc < kBoardSize) {
                if (!visited[nr][nc] && board_[nr][nc] == who) {
                    visited[nr][nc] = true;
                    qr[tail] = nr;
                    qc[tail] = nc;
                    tail++;
                }
            }
        }
    }
    return false;
}

int Game072HexBoard::ComputeShortestCost(uint8_t who) const {
    const int kInf = 999;
    int dist[kBoardSize][kBoardSize];
    for (int r = 0; r < kBoardSize; ++r) {
        for (int c = 0; c < kBoardSize; ++c) {
            dist[r][c] = kInf;
        }
    }

    if (who == 1) {
        for (int c = 0; c < kBoardSize; ++c) {
            if (board_[0][c] == 1) dist[0][c] = 0;
            else if (board_[0][c] == 0) dist[0][c] = 1;
        }
    } else {
        for (int r = 0; r < kBoardSize; ++r) {
            if (board_[r][0] == 2) dist[r][0] = 0;
            else if (board_[r][0] == 0) dist[r][0] = 1;
        }
    }

    for (int iter = 0; iter < 14; ++iter) {
        bool changed = false;
        for (int r = 0; r < kBoardSize; ++r) {
            for (int c = 0; c < kBoardSize; ++c) {
                if (dist[r][c] >= kInf) continue;
                for (int k = 0; k < 6; ++k) {
                    int nr = r + kHexNeighbors[k][0];
                    int nc = c + kHexNeighbors[k][1];
                    if (nr >= 0 && nr < kBoardSize && nc >= 0 && nc < kBoardSize) {
                        uint8_t cell = board_[nr][nc];
                        if (cell != 0 && cell != who) continue;
                        int step_cost = (cell == who) ? 0 : 1;
                        if (dist[r][c] + step_cost < dist[nr][nc]) {
                            dist[nr][nc] = dist[r][c] + step_cost;
                            changed = true;
                        }
                    }
                }
            }
        }
        if (!changed) break;
    }

    int best = kInf;
    if (who == 1) {
        for (int c = 0; c < kBoardSize; ++c) {
            if (dist[kBoardSize - 1][c] < best) best = dist[kBoardSize - 1][c];
        }
    } else {
        for (int r = 0; r < kBoardSize; ++r) {
            if (dist[r][kBoardSize - 1] < best) best = dist[r][kBoardSize - 1];
        }
    }
    return best;
}

void Game072HexBoard::ChooseAIMove(int& out_r, int& out_c) {
    out_r = -1;
    out_c = -1;

    // 1. Immediate win check for AI
    for (int r = 0; r < kBoardSize; ++r) {
        for (int c = 0; c < kBoardSize; ++c) {
            if (board_[r][c] == 0) {
                board_[r][c] = 2;
                bool win = CheckConnectivity(2);
                board_[r][c] = 0;
                if (win) {
                    out_r = r;
                    out_c = c;
                    return;
                }
            }
        }
    }

    // 2. Immediate block check against Player win
    for (int r = 0; r < kBoardSize; ++r) {
        for (int c = 0; c < kBoardSize; ++c) {
            if (board_[r][c] == 0) {
                board_[r][c] = 1;
                bool pwin = CheckConnectivity(1);
                board_[r][c] = 0;
                if (pwin) {
                    out_r = r;
                    out_c = c;
                    return;
                }
            }
        }
    }

    int base_ai_cost = ComputeShortestCost(2);
    int base_pl_cost = ComputeShortestCost(1);

    int best_score = -999999;
    for (int r = 0; r < kBoardSize; ++r) {
        for (int c = 0; c < kBoardSize; ++c) {
            if (board_[r][c] != 0) continue;

            board_[r][c] = 2;
            int new_ai_cost = ComputeShortestCost(2);
            int new_pl_cost = ComputeShortestCost(1);
            board_[r][c] = 0;

            int val = (base_ai_cost - new_ai_cost) * 32 + (new_pl_cost - base_pl_cost) * 26;

            // Bridge defense & bridge building heuristic
            for (int b = 0; b < 6; ++b) {
                // Check if (r, c) saves a threatened AI two-bridge
                for (int r1 = 0; r1 < kBoardSize; ++r1) {
                    for (int c1 = 0; c1 < kBoardSize; ++c1) {
                        if (board_[r1][c1] != 2) continue;
                        int r2 = r1 + kHexBridges[b][0];
                        int c2 = c1 + kHexBridges[b][1];
                        if (r2 < 0 || r2 >= kBoardSize || c2 < 0 || c2 >= kBoardSize) continue;
                        if (board_[r2][c2] != 2) continue;

                        int m1r = r1 + kHexBridges[b][2];
                        int m1c = c1 + kHexBridges[b][3];
                        int m2r = r1 + kHexBridges[b][4];
                        int m2c = c1 + kHexBridges[b][5];
                        if (m1r == r && m1c == c && board_[m2r][m2c] == 1) val += 42;
                        if (m2r == r && m2c == c && board_[m1r][m1c] == 1) val += 42;
                    }
                }

                // Check if placing at (r, c) forms a clean two-bridge with an existing AI stone
                int br = r + kHexBridges[b][0];
                int bc = c + kHexBridges[b][1];
                int m1r = r + kHexBridges[b][2];
                int m1c = c + kHexBridges[b][3];
                int m2r = r + kHexBridges[b][4];
                int m2c = c + kHexBridges[b][5];
                if (br >= 0 && br < kBoardSize && bc >= 0 && bc < kBoardSize) {
                    if (board_[br][bc] == 2 && board_[m1r][m1c] == 0 && board_[m2r][m2c] == 0) {
                        val += 10;
                    }
                }
            }

            // Center control + deterministic jitter
            int center_bias = 6 - abs(r - 3) - abs(c - 3);
            val += center_bias * 2 + (int)(NextRand() % 4);

            if (val > best_score) {
                best_score = val;
                out_r = r;
                out_c = c;
            }
        }
    }
}

void Game072HexBoard::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    (void)keys_down;
    if (dt > 0.05f) dt = 0.05f;

    if (state_ == STATE_PAUSED) {
        if (keys_pressed & KEY_START) {
            state_ = STATE_PLAYING;
        }
        return;
    }

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

    if (state_ == STATE_PLAYING) {
        if (keys_pressed & KEY_START) {
            state_ = STATE_PAUSED;
            return;
        }

        if (turn_player_) {
            if (keys_pressed & KEY_LEFT) {
                if (cursor_c_ > 0) cursor_c_--;
            }
            if (keys_pressed & KEY_RIGHT) {
                if (cursor_c_ < kBoardSize - 1) cursor_c_++;
            }
            if (keys_pressed & KEY_UP) {
                if (cursor_r_ > 0) cursor_r_--;
            }
            if (keys_pressed & KEY_DOWN) {
                if (cursor_r_ < kBoardSize - 1) cursor_r_++;
            }

            if ((keys_pressed & KEY_A) && board_[cursor_r_][cursor_c_] == 0) {
                board_[cursor_r_][cursor_c_] = 1;
                moves_count_++;
                AddScore(15);

                if (CheckConnectivity(1)) {
                    AddScore(400);
                    state_ = STATE_VICTORY;
                    state_timer_ = 0.0f;
                    return;
                }

                turn_player_ = false;
                ai_timer_ = 0.20f;
            }
        } else {
            ai_timer_ -= dt;
            if (ai_timer_ <= 0.0f) {
                int ar = -1;
                int ac = -1;
                ChooseAIMove(ar, ac);
                if (ar >= 0 && ac >= 0 && board_[ar][ac] == 0) {
                    board_[ar][ac] = 2;
                    last_ai_r_ = ar;
                    last_ai_c_ = ac;
                    moves_count_++;
                    if (CheckConnectivity(2)) {
                        state_ = STATE_GAMEOVER;
                        state_timer_ = 0.0f;
                        return;
                    }
                }
                turn_player_ = true;
            }
        }
    }
}

void Game072HexBoard::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    // Deep midnight background
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            SetPixel72(fb_rgb24, x, y, 10, 12, 20);
        }
    }

    // Colored Hex connection borders around 7x7 parallelogram (px = 1 + c + r, py = 4 + r)
    // Player Red/Gold Top (y=3) & Bottom (y=11) borders
    for (int c = 0; c < kBoardSize; ++c) {
        SetPixel72(fb_rgb24, 1 + c, 3, 220, 55, 35);
        SetPixel72(fb_rgb24, 1 + c + 6, 11, 220, 55, 35);
    }
    // AI Blue/Cyan Left & Right borders
    for (int r = 0; r < kBoardSize; ++r) {
        SetPixel72(fb_rgb24, r, 4 + r, 35, 130, 235);
        SetPixel72(fb_rgb24, 8 + r, 4 + r, 35, 130, 235);
    }

    // Render 49 hex cells
    for (int r = 0; r < kBoardSize; ++r) {
        for (int c = 0; c < kBoardSize; ++c) {
            int px = 1 + c + r;
            int py = 4 + r;
            uint8_t cell = board_[r][c];
            if (cell == 0) {
                uint8_t shade = ((r + c) % 2 == 0) ? 46 : 36;
                SetPixel72(fb_rgb24, px, py, shade, shade + 6, shade + 18);
            } else if (cell == 1) {
                // Player stone: Red/Gold
                SetPixel72(fb_rgb24, px, py, 255, 120, 25);
            } else {
                // AI stone: Cyan/Blue
                if (r == last_ai_r_ && c == last_ai_c_) {
                    SetPixel72(fb_rgb24, px, py, 110, 235, 255);
                } else {
                    SetPixel72(fb_rgb24, px, py, 30, 185, 250);
                }
            }
        }
    }

    // Blinking cursor on Player's turn
    if (state_ == STATE_PLAYING && turn_player_) {
        bool blink_on = (fmodf(anim_timer_, 0.4f) < 0.24f);
        if (blink_on) {
            int cx = 1 + cursor_c_ + cursor_r_;
            int cy = 4 + cursor_r_;
            if (board_[cursor_r_][cursor_c_] == 0) {
                SetPixel72(fb_rgb24, cx, cy, 255, 240, 120);
            } else {
                SetPixel72(fb_rgb24, cx, cy, 255, 255, 255);
            }
        }
    } else if (state_ == STATE_TITLE) {
        // Title preview stones forming mini hex bridge
        SetPixel72(fb_rgb24, 1 + 3 + 2, 4 + 2, 255, 130, 30);
        SetPixel72(fb_rgb24, 1 + 3 + 4, 4 + 4, 255, 130, 30);
        SetPixel72(fb_rgb24, 1 + 2 + 3, 4 + 3, 40, 195, 255);
        SetPixel72(fb_rgb24, 1 + 4 + 3, 4 + 3, 40, 195, 255);
    }

    // Top HUD turn indicator (y=0)
    if (turn_player_) {
        SetPixel72(fb_rgb24, 1, 0, 255, 130, 30);
        SetPixel72(fb_rgb24, 2, 0, 255, 180, 40);
    } else {
        SetPixel72(fb_rgb24, 13, 0, 40, 195, 255);
        SetPixel72(fb_rgb24, 14, 0, 40, 195, 255);
    }

    if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPixel72(fb_rgb24, 6, y, 250, 250, 250);
            SetPixel72(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game072HexBoard::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = (state_ == STATE_GAMEOVER) ? 0 : 1;
    st.state = (uint8_t)state_;
    int cost = ComputeShortestCost(1);
    int prog = (cost >= 7) ? 0 : ((7 - cost) * 100) / 7;
    if (state_ == STATE_VICTORY) prog = 100;
    st.progress = (uint8_t)prog;
    return st;
}

static_assert(sizeof(Game072HexBoard) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
