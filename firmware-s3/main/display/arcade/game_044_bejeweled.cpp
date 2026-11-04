// game_044_bejeweled.cpp —— 目标 #044 宝石迷阵 (Bejeweled) 核心实现
#include "game_044_bejeweled.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>
#include <stdlib.h>
#include <math.h>

namespace arcade {

static inline void SetPx44(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

static inline void GetJewelRGB(uint8_t gem, bool spec, uint8_t& r, uint8_t& g, uint8_t& b) {
    switch (gem) {
        case 1: // Ruby Red
            r = spec ? 255 : 235; g = spec ? 145 : 40;  b = spec ? 155 : 60;  break;
        case 2: // Emerald Green
            r = spec ? 145 : 35;  g = spec ? 255 : 215; b = spec ? 170 : 85;  break;
        case 3: // Sapphire Blue
            r = spec ? 150 : 45;  g = spec ? 210 : 130; b = spec ? 255 : 250; break;
        case 4: // Topaz Gold
            r = spec ? 255 : 245; g = spec ? 245 : 200; b = spec ? 150 : 25;  break;
        case 5: // Amethyst Purple
            r = spec ? 235 : 185; g = spec ? 160 : 60;  b = spec ? 255 : 240; break;
        default:
            r = 20; g = 22; b = 34; break;
    }
}

Game044Bejeweled::Game044Bejeweled()
    : state_(STATE_TITLE),
      cx_(2),
      cy_(2),
      sel_x_(-1),
      sel_y_(-1),
      last_chain_(0),
      seed_(0x44200109u),
      score_(0),
      high_score_(0),
      time_left_(60.0f),
      invalid_flash_(0.0f),
      state_timer_(0.0f),
      anim_timer_(0.0f) {
    memset(board_, 0, sizeof(board_));
    GeneratePlayableBoard();
}

uint32_t Game044Bejeweled::NextRand() {
    seed_ = seed_ * 1664525u + 1013904223u;
    return (seed_ >> 16) & 0x7FFFu;
}

uint8_t Game044Bejeweled::RandomGem() {
    return (uint8_t)(1 + (NextRand() % 5u));
}

void Game044Bejeweled::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

int Game044Bejeweled::FindMatches(bool mark[kSize][kSize]) const {
    for (int r = 0; r < kSize; ++r) {
        for (int c = 0; c < kSize; ++c) {
            mark[r][c] = false;
        }
    }

    // Horizontal runs >= 3
    for (int r = 0; r < kSize; ++r) {
        int c = 0;
        while (c < kSize) {
            uint8_t g = board_[r][c];
            if (g == 0) { c++; continue; }
            int end = c + 1;
            while (end < kSize && board_[r][end] == g) end++;
            if (end - c >= 3) {
                for (int k = c; k < end; ++k) mark[r][k] = true;
            }
            c = end;
        }
    }

    // Vertical runs >= 3
    for (int c = 0; c < kSize; ++c) {
        int r = 0;
        while (r < kSize) {
            uint8_t g = board_[r][c];
            if (g == 0) { r++; continue; }
            int end = r + 1;
            while (end < kSize && board_[end][c] == g) end++;
            if (end - r >= 3) {
                for (int k = r; k < end; ++k) mark[k][c] = true;
            }
            r = end;
        }
    }

    int cnt = 0;
    for (int r = 0; r < kSize; ++r) {
        for (int c = 0; c < kSize; ++c) {
            if (mark[r][c]) cnt++;
        }
    }
    return cnt;
}

bool Game044Bejeweled::HasValidMove() {
    bool mark[kSize][kSize];
    for (int r = 0; r < kSize; ++r) {
        for (int c = 0; c < kSize; ++c) {
            if (c + 1 < kSize) {
                uint8_t t = board_[r][c];
                board_[r][c] = board_[r][c + 1];
                board_[r][c + 1] = t;
                int m = FindMatches(mark);
                board_[r][c + 1] = board_[r][c];
                board_[r][c] = t;
                if (m > 0) return true;
            }
            if (r + 1 < kSize) {
                uint8_t t = board_[r][c];
                board_[r][c] = board_[r + 1][c];
                board_[r + 1][c] = t;
                int m = FindMatches(mark);
                board_[r + 1][c] = board_[r][c];
                board_[r][c] = t;
                if (m > 0) return true;
            }
        }
    }
    return false;
}

void Game044Bejeweled::GeneratePlayableBoard() {
    for (int attempt = 0; attempt < 32; ++attempt) {
        for (int r = 0; r < kSize; ++r) {
            for (int c = 0; c < kSize; ++c) {
                uint8_t g = RandomGem();
                int guard = 0;
                while (guard < 16 &&
                       ((c >= 2 && board_[r][c - 1] == g && board_[r][c - 2] == g) ||
                        (r >= 2 && board_[r - 1][c] == g && board_[r - 2][c] == g))) {
                    g = (uint8_t)((g % 5u) + 1u);
                    guard++;
                }
                board_[r][c] = g;
            }
        }
        if (HasValidMove()) return;
    }
    // Guaranteed fallback pattern with a valid move and zero pre-existing matches
    board_[0][0] = 1; board_[0][1] = 1; board_[0][2] = 2;
    board_[1][2] = 1;
}

void Game044Bejeweled::ApplyGravityAndRefill() {
    for (int c = 0; c < kSize; ++c) {
        int write_r = kSize - 1;
        for (int r = kSize - 1; r >= 0; --r) {
            if (board_[r][c] != 0) {
                board_[write_r][c] = board_[r][c];
                if (write_r != r) board_[r][c] = 0;
                write_r--;
            }
        }
        for (int r = write_r; r >= 0; --r) {
            board_[r][c] = RandomGem();
        }
    }
}

bool Game044Bejeweled::TrySwap(int x1, int y1, int x2, int y2) {
    if (x1 < 0 || x1 >= kSize || y1 < 0 || y1 >= kSize) return false;
    if (x2 < 0 || x2 >= kSize || y2 < 0 || y2 >= kSize) return false;
    if (abs(x1 - x2) + abs(y1 - y2) != 1) return false;

    uint8_t tmp = board_[y1][x1];
    board_[y1][x1] = board_[y2][x2];
    board_[y2][x2] = tmp;

    bool mark[kSize][kSize];
    int matched = FindMatches(mark);
    if (matched == 0) {
        // Invalid Bejeweled swap -> revert immediately
        board_[y2][x2] = board_[y1][x1];
        board_[y1][x1] = tmp;
        invalid_flash_ = 0.25f;
        return false;
    }

    int chain = 0;
    while (matched > 0 && chain < 24) {
        chain++;
        for (int r = 0; r < kSize; ++r) {
            for (int c = 0; c < kSize; ++c) {
                if (mark[r][c]) board_[r][c] = 0;
            }
        }
        AddScore((uint32_t)(matched * 10 * chain));
        time_left_ += 1.5f;
        if (time_left_ > 60.0f) time_left_ = 60.0f;

        ApplyGravityAndRefill();
        matched = FindMatches(mark);
    }

    last_chain_ = chain;

    if (score_ >= kTargetScore) {
        state_ = STATE_VICTORY;
        state_timer_ = 0.0f;
        return true;
    }

    if (!HasValidMove()) {
        GeneratePlayableBoard();
    }
    return true;
}

void Game044Bejeweled::Init() {
    Reset();
}

void Game044Bejeweled::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    state_ = STATE_TITLE;
    seed_ = 0x44200109u;
    score_ = 0;
    cx_ = 2;
    cy_ = 2;
    sel_x_ = -1;
    sel_y_ = -1;
    last_chain_ = 0;
    time_left_ = 60.0f;
    invalid_flash_ = 0.0f;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    GeneratePlayableBoard();
}

void Game044Bejeweled::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        score_ = 0;
        cx_ = 2;
        cy_ = 2;
        sel_x_ = -1;
        sel_y_ = -1;
        last_chain_ = 0;
        time_left_ = 60.0f;
        invalid_flash_ = 0.0f;
        state_timer_ = 0.0f;
        anim_timer_ = 0.0f;
        GeneratePlayableBoard();
        state_ = STATE_PLAYING;
    }
}

void Game044Bejeweled::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game044Bejeweled::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

void Game044Bejeweled::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    (void)keys_down;
    if (dt > 0.05f) dt = 0.05f;
    state_timer_ += dt;
    anim_timer_ += dt;
    if (invalid_flash_ > 0.0f) {
        invalid_flash_ -= dt;
        if (invalid_flash_ < 0.0f) invalid_flash_ = 0.0f;
    }

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

        time_left_ -= dt;
        if (time_left_ <= 0.0f) {
            time_left_ = 0.0f;
            state_ = STATE_GAMEOVER;
            state_timer_ = 0.0f;
            if (score_ > high_score_) {
                high_score_ = score_;
                ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
            }
            return;
        }

        if (keys_pressed & KEY_B) {
            sel_x_ = -1;
            sel_y_ = -1;
        }

        int dx = 0, dy = 0;
        if (keys_pressed & KEY_LEFT) dx = -1;
        else if (keys_pressed & KEY_RIGHT) dx = 1;
        else if (keys_pressed & KEY_UP) dy = -1;
        else if (keys_pressed & KEY_DOWN) dy = 1;

        if (dx != 0 || dy != 0) {
            if (sel_x_ >= 0 && sel_y_ >= 0) {
                int nx = sel_x_ + dx;
                int ny = sel_y_ + dy;
                if (nx >= 0 && nx < kSize && ny >= 0 && ny < kSize) {
                    int sx = sel_x_;
                    int sy = sel_y_;
                    cx_ = nx;
                    cy_ = ny;
                    sel_x_ = -1;
                    sel_y_ = -1;
                    TrySwap(sx, sy, nx, ny);
                    return;
                }
            } else {
                int nx = cx_ + dx;
                int ny = cy_ + dy;
                if (nx >= 0 && nx < kSize) cx_ = nx;
                if (ny >= 0 && ny < kSize) cy_ = ny;
            }
        }

        if (keys_pressed & KEY_A) {
            if (sel_x_ < 0) {
                sel_x_ = cx_;
                sel_y_ = cy_;
            } else if (abs(cx_ - sel_x_) + abs(cy_ - sel_y_) == 1) {
                int sx = sel_x_;
                int sy = sel_y_;
                sel_x_ = -1;
                sel_y_ = -1;
                TrySwap(sx, sy, cx_, cy_);
            } else {
                sel_x_ = -1;
                sel_y_ = -1;
            }
        }
    }
}

void Game044Bejeweled::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            SetPx44(fb_rgb24, x, y, 12, 14, 24);
        }
    }

    // Blitz timer bar at y = 0 (x = 1..14)
    int t_px = (int)((time_left_ / 60.0f) * 14.0f + 0.5f);
    if (t_px < 0) t_px = 0;
    if (t_px > 14) t_px = 14;
    for (int i = 0; i < 14; ++i) {
        if (i < t_px) {
            if (time_left_ > 20.0f) SetPx44(fb_rgb24, 1 + i, 0, 45, 220, 110);
            else SetPx44(fb_rgb24, 1 + i, 0, 245, 70, 55);
        } else {
            SetPx44(fb_rgb24, 1 + i, 0, 30, 32, 46);
        }
    }

    // Score progress bar toward 500 at y = 1 (x = 1..14)
    int s_px = (int)((score_ * 14u) / kTargetScore);
    if (s_px > 14) s_px = 14;
    for (int i = 0; i < 14; ++i) {
        if (i < s_px) SetPx44(fb_rgb24, 1 + i, 1, 255, 210, 40);
        else SetPx44(fb_rgb24, 1 + i, 1, 24, 28, 42);
    }

    // Subtle board frame around x = 2..13, y = 3..14
    for (int y = 2; y <= 15; ++y) {
        SetPx44(fb_rgb24, 1, y, 42, 48, 72);
        SetPx44(fb_rgb24, 14, y, 42, 48, 72);
    }
    for (int x = 1; x <= 14; ++x) {
        SetPx44(fb_rgb24, x, 2, 42, 48, 72);
        SetPx44(fb_rgb24, x, 15, 42, 48, 72);
    }

    // 6x6 gems, each 2x2 px at (2 + c*2, 3 + r*2)
    for (int r = 0; r < kSize; ++r) {
        int py = 3 + r * 2;
        for (int c = 0; c < kSize; ++c) {
            int px = 2 + c * 2;
            uint8_t gem = board_[r][c];
            for (int dy = 0; dy < 2; ++dy) {
                for (int dx = 0; dx < 2; ++dx) {
                    uint8_t jr, jg, jb;
                    GetJewelRGB(gem, (dx == 0 && dy == 0), jr, jg, jb);
                    SetPx44(fb_rgb24, px + dx, py + dy, jr, jg, jb);
                }
            }
        }
    }

    // Selected gem blinking white corners
    bool blink = ((int)(anim_timer_ * 8.0f) % 2) == 0;
    if (sel_x_ >= 0 && sel_y_ >= 0) {
        int sx = 2 + sel_x_ * 2;
        int sy = 3 + sel_y_ * 2;
        uint8_t br = blink ? 255 : 200;
        SetPx44(fb_rgb24, sx, sy, br, br, br);
        SetPx44(fb_rgb24, sx + 1, sy, br, br, br);
        SetPx44(fb_rgb24, sx, sy + 1, br, br, br);
        SetPx44(fb_rgb24, sx + 1, sy + 1, br, br, br);
    } else if (state_ == STATE_PLAYING) {
        int kx = 2 + cx_ * 2;
        int ky = 3 + cy_ * 2;
        if (invalid_flash_ > 0.0f) {
            SetPx44(fb_rgb24, kx + 1, ky + 1, 255, 30, 30);
            SetPx44(fb_rgb24, kx, ky + 1, 255, 30, 30);
        } else if (blink) {
            SetPx44(fb_rgb24, kx + 1, ky + 1, 255, 255, 255);
        }
    }

    if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPx44(fb_rgb24, 6, y, 250, 250, 250);
            SetPx44(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game044Bejeweled::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = (state_ == STATE_GAMEOVER) ? 0 : 1;
    st.state = (uint8_t)state_;
    uint32_t prog = (score_ * 100u) / kTargetScore;
    st.progress = (uint8_t)(prog > 100u ? 100u : prog);
    return st;
}

static_assert(sizeof(Game044Bejeweled) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
