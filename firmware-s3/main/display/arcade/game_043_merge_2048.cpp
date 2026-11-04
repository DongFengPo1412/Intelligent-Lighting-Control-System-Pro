// game_043_merge_2048.cpp —— 目标 #043 2048滑块 (Neon 2048) 核心实现
#include "game_043_merge_2048.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>
#include <math.h>

namespace arcade {

static inline void SetPx43(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

static inline void GetTileBaseRGB(uint8_t exp, uint8_t& r, uint8_t& g, uint8_t& b) {
    switch (exp) {
        case 0:  r = 22;  g = 24;  b = 34;  break;
        case 1:  r = 45;  g = 140; b = 220; break; // 2
        case 2:  r = 26;  g = 195; b = 165; break; // 4
        case 3:  r = 46;  g = 215; b = 100; break; // 8
        case 4:  r = 245; g = 205; b = 25;  break; // 16
        case 5:  r = 240; g = 130; b = 30;  break; // 32
        case 6:  r = 235; g = 65;  b = 55;  break; // 64
        case 7:  r = 170; g = 80;  b = 235; break; // 128
        case 8:  r = 255; g = 40;  b = 150; break; // 256
        case 9:  r = 255; g = 215; b = 0;   break; // 512
        case 10: r = 90;  g = 245; b = 235; break; // 1024
        default: r = 255; g = 255; b = 255; break; // 2048
    }
}

static bool MergeLine4(uint8_t line[4], uint32_t& gain) {
    uint8_t nz[4];
    int nz_cnt = 0;
    for (int i = 0; i < 4; ++i) {
        if (line[i] != 0) {
            nz[nz_cnt++] = line[i];
        }
    }

    uint8_t res[4] = {0, 0, 0, 0};
    int out_idx = 0;
    int i = 0;
    while (i < nz_cnt) {
        if (i + 1 < nz_cnt && nz[i] == nz[i + 1]) {
            uint8_t merged = (uint8_t)(nz[i] + 1);
            res[out_idx++] = merged;
            gain += (1u << merged);
            i += 2; // Merge once per pair per move
        } else {
            res[out_idx++] = nz[i];
            i += 1;
        }
    }

    bool changed = false;
    for (int k = 0; k < 4; ++k) {
        if (line[k] != res[k]) changed = true;
        line[k] = res[k];
    }
    return changed;
}

Game043Merge2048::Game043Merge2048()
    : state_(STATE_TITLE),
      max_tile_(1),
      seed_(0x20482014u),
      score_(0),
      high_score_(0),
      state_timer_(0.0f),
      anim_timer_(0.0f) {
    memset(board_, 0, sizeof(board_));
}

uint32_t Game043Merge2048::NextRand() {
    seed_ = seed_ * 1664525u + 1013904223u;
    return (seed_ >> 16) & 0x7FFFu;
}

void Game043Merge2048::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

void Game043Merge2048::RefreshMaxTile() {
    uint8_t m = 0;
    for (int r = 0; r < 4; ++r) {
        for (int c = 0; c < 4; ++c) {
            if (board_[r][c] > m) m = board_[r][c];
        }
    }
    max_tile_ = m;
}

void Game043Merge2048::SpawnRandomTile() {
    int er[16], ec[16];
    int cnt = 0;
    for (int r = 0; r < 4; ++r) {
        for (int c = 0; c < 4; ++c) {
            if (board_[r][c] == 0) {
                er[cnt] = r;
                ec[cnt] = c;
                cnt++;
            }
        }
    }
    if (cnt == 0) return;

    int pick = (int)(NextRand() % (uint32_t)cnt);
    uint8_t exp = (NextRand() % 10u == 0u) ? 2 : 1; // 90% 2, 10% 4
    board_[er[pick]][ec[pick]] = exp;
    RefreshMaxTile();
}

bool Game043Merge2048::CanMove() const {
    for (int r = 0; r < 4; ++r) {
        for (int c = 0; c < 4; ++c) {
            if (board_[r][c] == 0) return true;
            if (c < 3 && board_[r][c] == board_[r][c + 1]) return true;
            if (r < 3 && board_[r][c] == board_[r + 1][c]) return true;
        }
    }
    return false;
}

bool Game043Merge2048::Slide(int dx, int dy) {
    bool moved = false;
    uint32_t gain = 0;

    if (dx != 0) {
        for (int r = 0; r < 4; ++r) {
            uint8_t line[4];
            for (int c = 0; c < 4; ++c) {
                line[c] = (dx < 0) ? board_[r][c] : board_[r][3 - c];
            }
            if (MergeLine4(line, gain)) {
                moved = true;
                for (int c = 0; c < 4; ++c) {
                    if (dx < 0) board_[r][c] = line[c];
                    else board_[r][3 - c] = line[c];
                }
            }
        }
    } else if (dy != 0) {
        for (int c = 0; c < 4; ++c) {
            uint8_t line[4];
            for (int r = 0; r < 4; ++r) {
                line[r] = (dy < 0) ? board_[r][c] : board_[3 - r][c];
            }
            if (MergeLine4(line, gain)) {
                moved = true;
                for (int r = 0; r < 4; ++r) {
                    if (dy < 0) board_[r][c] = line[r];
                    else board_[3 - r][c] = line[r];
                }
            }
        }
    }

    if (gain > 0) {
        AddScore(gain);
    }

    if (moved) {
        RefreshMaxTile();
        if (max_tile_ >= 11) {
            state_ = STATE_VICTORY;
            state_timer_ = 0.0f;
            return true;
        }
        SpawnRandomTile();
        if (max_tile_ >= 11) {
            state_ = STATE_VICTORY;
            state_timer_ = 0.0f;
        } else if (!CanMove()) {
            state_ = STATE_GAMEOVER;
            state_timer_ = 0.0f;
        }
    }
    return moved;
}

void Game043Merge2048::Init() {
    Reset();
}

void Game043Merge2048::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    state_ = STATE_TITLE;
    memset(board_, 0, sizeof(board_));
    seed_ = 0x20482014u;
    score_ = 0;
    max_tile_ = 1;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    SpawnRandomTile();
    SpawnRandomTile();
}

void Game043Merge2048::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        memset(board_, 0, sizeof(board_));
        score_ = 0;
        max_tile_ = 1;
        state_timer_ = 0.0f;
        anim_timer_ = 0.0f;
        SpawnRandomTile();
        SpawnRandomTile();
        state_ = STATE_PLAYING;
    }
}

void Game043Merge2048::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game043Merge2048::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

void Game043Merge2048::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
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
            Slide(-1, 0);
        } else if (keys_pressed & KEY_RIGHT) {
            Slide(1, 0);
        } else if (keys_pressed & KEY_UP) {
            Slide(0, -1);
        } else if (keys_pressed & KEY_DOWN) {
            Slide(0, 1);
        }
    }
}

void Game043Merge2048::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    // 1px dark grid background across 16x16
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            SetPx43(fb_rgb24, x, y, 10, 12, 18);
        }
    }

    // 4x4 tiles, each 3x3 px at (c*4, r*4), gap at 3, 7, 11, 15
    for (int r = 0; r < 4; ++r) {
        int y0 = r * 4;
        for (int c = 0; c < 4; ++c) {
            int x0 = c * 4;
            uint8_t exp = board_[r][c];
            uint8_t br, bg, bb;
            GetTileBaseRGB(exp, br, bg, bb);

            for (int dy = 0; dy < 3; ++dy) {
                for (int dx = 0; dx < 3; ++dx) {
                    SetPx43(fb_rgb24, x0 + dx, y0 + dy, br, bg, bb);
                }
            }

            // Inner dot/corner encoding for exponents 1..11
            if (exp == 2) {
                SetPx43(fb_rgb24, x0 + 1, y0 + 1, 210, 255, 245);
            } else if (exp == 3) {
                SetPx43(fb_rgb24, x0 + 0, y0 + 0, 220, 255, 220);
            } else if (exp == 4) {
                SetPx43(fb_rgb24, x0 + 0, y0 + 0, 255, 255, 220);
                SetPx43(fb_rgb24, x0 + 1, y0 + 1, 255, 255, 220);
            } else if (exp == 5) {
                SetPx43(fb_rgb24, x0 + 0, y0 + 0, 255, 240, 200);
                SetPx43(fb_rgb24, x0 + 2, y0 + 2, 255, 240, 200);
            } else if (exp == 6) {
                SetPx43(fb_rgb24, x0 + 1, y0 + 1, 255, 255, 255);
            } else if (exp == 7) {
                SetPx43(fb_rgb24, x0 + 0, y0 + 1, 245, 215, 255);
                SetPx43(fb_rgb24, x0 + 1, y0 + 1, 245, 215, 255);
                SetPx43(fb_rgb24, x0 + 2, y0 + 1, 245, 215, 255);
            } else if (exp == 8) {
                SetPx43(fb_rgb24, x0 + 1, y0 + 0, 255, 225, 245);
                SetPx43(fb_rgb24, x0 + 1, y0 + 1, 255, 225, 245);
                SetPx43(fb_rgb24, x0 + 1, y0 + 2, 255, 225, 245);
            } else if (exp == 9) {
                SetPx43(fb_rgb24, x0 + 1, y0 + 0, 255, 255, 255);
                SetPx43(fb_rgb24, x0 + 0, y0 + 1, 255, 255, 255);
                SetPx43(fb_rgb24, x0 + 1, y0 + 1, 255, 255, 255);
                SetPx43(fb_rgb24, x0 + 2, y0 + 1, 255, 255, 255);
                SetPx43(fb_rgb24, x0 + 1, y0 + 2, 255, 255, 255);
            } else if (exp == 10) {
                SetPx43(fb_rgb24, x0 + 0, y0 + 0, 255, 255, 255);
                SetPx43(fb_rgb24, x0 + 2, y0 + 0, 255, 255, 255);
                SetPx43(fb_rgb24, x0 + 0, y0 + 2, 255, 255, 255);
                SetPx43(fb_rgb24, x0 + 2, y0 + 2, 255, 255, 255);
            } else if (exp >= 11) {
                uint8_t g = (uint8_t)(180 + 75.0f * (0.5f + 0.5f * sinf(anim_timer_ * 8.0f)));
                SetPx43(fb_rgb24, x0 + 1, y0 + 1, 255, g, 20);
            }
        }
    }

    if (state_ == STATE_VICTORY) {
        for (int x = 0; x < 16; ++x) {
            SetPx43(fb_rgb24, x, 15, 46, 215, 100);
        }
    } else if (state_ == STATE_GAMEOVER) {
        for (int x = 0; x < 16; ++x) {
            SetPx43(fb_rgb24, x, 15, 235, 50, 50);
        }
    } else if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPx43(fb_rgb24, 6, y, 250, 250, 250);
            SetPx43(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game043Merge2048::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = (state_ == STATE_GAMEOVER) ? 0 : 1;
    st.state = (uint8_t)state_;
    uint32_t prog = (max_tile_ * 100u) / 11u;
    st.progress = (uint8_t)(prog > 100u ? 100u : prog);
    return st;
}

static_assert(sizeof(Game043Merge2048) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
