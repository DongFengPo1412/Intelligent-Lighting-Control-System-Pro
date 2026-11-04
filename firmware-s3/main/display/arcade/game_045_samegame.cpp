// game_045_samegame.cpp —— 目标 #045 同色消块 (SameGame) 核心实现
#include "game_045_samegame.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>

namespace arcade {

static inline void SetPx45(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

static inline void GetBlockRGB(uint8_t col, bool hi, uint8_t& r, uint8_t& g, uint8_t& b) {
    switch (col) {
        case 1: r = hi ? 255 : 235; g = hi ? 120 : 55;  b = hi ? 120 : 60;  break; // Red
        case 2: r = hi ? 120 : 45;  g = hi ? 255 : 215; b = hi ? 150 : 95;  break; // Green
        case 3: r = hi ? 130 : 50;  g = hi ? 195 : 140; b = hi ? 255 : 250; break; // Blue
        case 4: r = hi ? 255 : 245; g = hi ? 235 : 195; b = hi ? 120 : 30;  break; // Gold
        default: r = 16; g = 18; b = 28; break;
    }
}

Game045SameGame::Game045SameGame()
    : state_(STATE_TITLE),
      cx_(4),
      cy_(5),
      seed_(0x45198507u),
      score_(0),
      high_score_(0),
      state_timer_(0.0f),
      anim_timer_(0.0f) {
    memset(grid_, 0, sizeof(grid_));
    GenerateBoard();
}

uint32_t Game045SameGame::NextRand() {
    seed_ = seed_ * 1664525u + 1013904223u;
    return (seed_ >> 16) & 0x7FFFu;
}

void Game045SameGame::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

void Game045SameGame::GenerateBoard() {
    for (int r = 0; r < kSize; ++r) {
        for (int c = 0; c < kSize; ++c) {
            grid_[r][c] = (uint8_t)(1u + (NextRand() % 4u));
        }
    }
    if (!HasRemovableGroup()) {
        grid_[kSize - 1][0] = 1;
        grid_[kSize - 1][1] = 1;
    }
}

int Game045SameGame::FloodComponent(int sx, int sy, bool mark[kSize][kSize]) const {
    for (int r = 0; r < kSize; ++r) {
        for (int c = 0; c < kSize; ++c) {
            mark[r][c] = false;
        }
    }
    if (sx < 0 || sx >= kSize || sy < 0 || sy >= kSize) return 0;
    uint8_t target = grid_[sy][sx];
    if (target == 0) return 0;

    int qx[kSize * kSize];
    int qy[kSize * kSize];
    int head = 0, tail = 0;

    qx[tail] = sx;
    qy[tail] = sy;
    tail++;
    mark[sy][sx] = true;

    const int dx[4] = {-1, 1, 0, 0};
    const int dy[4] = {0, 0, -1, 1};

    while (head < tail) {
        int x = qx[head];
        int y = qy[head];
        head++;

        for (int d = 0; d < 4; ++d) {
            int nx = x + dx[d];
            int ny = y + dy[d];
            if (nx >= 0 && nx < kSize && ny >= 0 && ny < kSize) {
                if (!mark[ny][nx] && grid_[ny][nx] == target) {
                    mark[ny][nx] = true;
                    qx[tail] = nx;
                    qy[tail] = ny;
                    tail++;
                }
            }
        }
    }
    return tail;
}

void Game045SameGame::ApplyGravityAndShiftLeft() {
    // 1. Vertical gravity within each column
    for (int c = 0; c < kSize; ++c) {
        int write_r = kSize - 1;
        for (int r = kSize - 1; r >= 0; --r) {
            if (grid_[r][c] != 0) {
                if (write_r != r) {
                    grid_[write_r][c] = grid_[r][c];
                    grid_[r][c] = 0;
                }
                write_r--;
            }
        }
    }

    // 2. Shift whole columns left to close empty column gaps
    int write_c = 0;
    for (int c = 0; c < kSize; ++c) {
        if (grid_[kSize - 1][c] != 0) {
            if (write_c != c) {
                for (int r = 0; r < kSize; ++r) {
                    grid_[r][write_c] = grid_[r][c];
                    grid_[r][c] = 0;
                }
            }
            write_c++;
        }
    }
}

bool Game045SameGame::HasRemovableGroup() const {
    for (int r = 0; r < kSize; ++r) {
        for (int c = 0; c < kSize; ++c) {
            uint8_t v = grid_[r][c];
            if (v == 0) continue;
            if (c + 1 < kSize && grid_[r][c + 1] == v) return true;
            if (r + 1 < kSize && grid_[r + 1][c] == v) return true;
        }
    }
    return false;
}

int Game045SameGame::CountRemaining() const {
    int cnt = 0;
    for (int r = 0; r < kSize; ++r) {
        for (int c = 0; c < kSize; ++c) {
            if (grid_[r][c] != 0) cnt++;
        }
    }
    return cnt;
}

int Game045SameGame::EliminateAt(int cx, int cy) {
    bool mark[kSize][kSize];
    int n = FloodComponent(cx, cy, mark);
    if (n < 2) return 0;

    for (int r = 0; r < kSize; ++r) {
        for (int c = 0; c < kSize; ++c) {
            if (mark[r][c]) grid_[r][c] = 0;
        }
    }

    AddScore((uint32_t)(n * (n - 1) * 5));
    ApplyGravityAndShiftLeft();

    if (!HasRemovableGroup()) {
        int rem = CountRemaining();
        if (rem <= 3) {
            uint32_t clear_bonus = (rem == 0) ? 500u : (uint32_t)((4 - rem) * 100);
            AddScore(clear_bonus);
            state_ = STATE_VICTORY;
            state_timer_ = 0.0f;
        } else {
            state_ = STATE_GAMEOVER;
            state_timer_ = 0.0f;
            if (score_ > high_score_) {
                high_score_ = score_;
                ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
            }
        }
    }
    return n;
}

void Game045SameGame::Init() {
    Reset();
}

void Game045SameGame::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    state_ = STATE_TITLE;
    seed_ = 0x45198507u;
    score_ = 0;
    cx_ = 4;
    cy_ = 5;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    GenerateBoard();
}

void Game045SameGame::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        score_ = 0;
        cx_ = 4;
        cy_ = 5;
        state_timer_ = 0.0f;
        anim_timer_ = 0.0f;
        GenerateBoard();
        state_ = STATE_PLAYING;
    }
}

void Game045SameGame::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game045SameGame::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

void Game045SameGame::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
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

        if (keys_pressed & KEY_LEFT) {
            if (cx_ > 0) cx_--;
        } else if (keys_pressed & KEY_RIGHT) {
            if (cx_ < kSize - 1) cx_++;
        } else if (keys_pressed & KEY_UP) {
            if (cy_ > 0) cy_--;
        } else if (keys_pressed & KEY_DOWN) {
            if (cy_ < kSize - 1) cy_++;
        }

        if (keys_pressed & KEY_A) {
            EliminateAt(cx_, cy_);
        }
    }
}

void Game045SameGame::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            SetPx45(fb_rgb24, x, y, 10, 12, 22);
        }
    }

    // Frame around centered 10x10 board (x = 3..12, y = 3..12)
    for (int y = 2; y <= 13; ++y) {
        SetPx45(fb_rgb24, 2, y, 50, 60, 95);
        SetPx45(fb_rgb24, 13, y, 50, 60, 95);
    }
    for (int x = 2; x <= 13; ++x) {
        SetPx45(fb_rgb24, x, 2, 50, 60, 95);
        SetPx45(fb_rgb24, x, 13, 50, 60, 95);
    }

    bool hover[kSize][kSize];
    int hover_n = FloodComponent(cx_, cy_, hover);

    for (int r = 0; r < kSize; ++r) {
        for (int c = 0; c < kSize; ++c) {
            uint8_t v = grid_[r][c];
            bool hi = (state_ == STATE_PLAYING && hover_n >= 2 && hover[r][c]);
            uint8_t br, bg, bb;
            GetBlockRGB(v, hi, br, bg, bb);
            SetPx45(fb_rgb24, 3 + c, 3 + r, br, bg, bb);
        }
    }

    // Remaining blocks clearance bar at y = 0 (x = 3..12)
    int cleared = 100 - CountRemaining();
    int bar = cleared / 10;
    for (int i = 0; i < 10; ++i) {
        if (i < bar) SetPx45(fb_rgb24, 3 + i, 0, 50, 230, 130);
        else SetPx45(fb_rgb24, 3 + i, 0, 28, 32, 46);
    }

    // Cursor blink
    if (state_ == STATE_PLAYING && (((int)(anim_timer_ * 8.0f) % 2) == 0)) {
        SetPx45(fb_rgb24, 3 + cx_, 3 + cy_, 255, 255, 255);
    }

    if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPx45(fb_rgb24, 6, y, 250, 250, 250);
            SetPx45(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game045SameGame::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = (state_ == STATE_GAMEOVER) ? 0 : 1;
    st.state = (uint8_t)state_;
    st.progress = (uint8_t)(100 - CountRemaining());
    return st;
}

static_assert(sizeof(Game045SameGame) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
