// game_042_puyo_puyo.cpp —— 目标 #042 彩球连锁 (Puyo Puyo) 核心实现
#include "game_042_puyo_puyo.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>

namespace arcade {

static inline void SetPx42(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

static inline void GetPuyoRGB(uint8_t c, uint8_t& r, uint8_t& g, uint8_t& b) {
    switch (c) {
        case 1:  r = 250; g = 45;  b = 55;  break; // Red
        case 2:  r = 40;  g = 230; b = 75;  break; // Green
        case 3:  r = 50;  g = 140; b = 255; break; // Blue
        case 4:  r = 255; g = 220; b = 30;  break; // Yellow
        default: r = 16;  g = 20;  b = 34;  break;
    }
}

Game042PuyoPuyo::Game042PuyoPuyo()
    : state_(STATE_TITLE),
      cur_col_(2),
      cur_row_(1),
      cur_rot_(0),
      main_color_(1),
      sub_color_(2),
      next_main_(3),
      next_sub_(4),
      last_chain_(0),
      max_chain_(0),
      seed_(0x42199101u),
      score_(0),
      high_score_(0),
      drop_timer_(0.0f),
      drop_interval_(0.55f),
      chain_flash_timer_(0.0f),
      state_timer_(0.0f),
      anim_timer_(0.0f) {
    memset(grid_, 0, sizeof(grid_));
}

uint32_t Game042PuyoPuyo::NextRand() {
    seed_ = seed_ * 1664525u + 1013904223u;
    return (seed_ >> 16) & 0x7FFFu;
}

uint8_t Game042PuyoPuyo::RandomColor() {
    return (uint8_t)(1 + (NextRand() % 4));
}

void Game042PuyoPuyo::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

void Game042PuyoPuyo::GetSubOffset(int rot, int& ox, int& oy) const {
    switch (rot & 3) {
        case 0:  ox = 0;  oy = -1; break; // Up
        case 1:  ox = 1;  oy = 0;  break; // Right
        case 2:  ox = 0;  oy = 1;  break; // Down
        default: ox = -1; oy = 0;  break; // Left
    }
}

bool Game042PuyoPuyo::IsCellFree(int c, int r) const {
    if (c < 0 || c >= kCols || r >= kRows) return false;
    if (r < 0) return true;
    return grid_[r][c] == 0;
}

bool Game042PuyoPuyo::CanPlacePair(int c, int r, int rot) const {
    int ox = 0, oy = 0;
    GetSubOffset(rot, ox, oy);
    return IsCellFree(c, r) && IsCellFree(c + ox, r + oy);
}

void Game042PuyoPuyo::SpawnPair() {
    if (grid_[0][2] != 0 || grid_[1][2] != 0) {
        state_ = STATE_GAMEOVER;
        state_timer_ = 0.0f;
        if (score_ > high_score_) {
            high_score_ = score_;
            ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
        }
        return;
    }

    cur_col_ = 2;
    cur_row_ = 1;
    cur_rot_ = 0;
    main_color_ = next_main_;
    sub_color_ = next_sub_;
    next_main_ = RandomColor();
    next_sub_ = RandomColor();
    drop_timer_ = 0.0f;
}

void Game042PuyoPuyo::RotatePair() {
    int nrot = (cur_rot_ + 1) & 3;
    if (CanPlacePair(cur_col_, cur_row_, nrot)) {
        cur_rot_ = nrot;
        return;
    }
    // Wall / neighbor kicks
    if (CanPlacePair(cur_col_ - 1, cur_row_, nrot)) {
        cur_col_ -= 1;
        cur_rot_ = nrot;
        return;
    }
    if (CanPlacePair(cur_col_ + 1, cur_row_, nrot)) {
        cur_col_ += 1;
        cur_rot_ = nrot;
        return;
    }
    if (CanPlacePair(cur_col_, cur_row_ - 1, nrot)) {
        cur_row_ -= 1;
        cur_rot_ = nrot;
        return;
    }
    // 1-wide shaft 180 flip fallback
    int flip_rot = (cur_rot_ + 2) & 3;
    if (CanPlacePair(cur_col_, cur_row_, flip_rot)) {
        cur_rot_ = flip_rot;
    }
}

bool Game042PuyoPuyo::ApplyGravity() {
    bool moved = false;
    for (int c = 0; c < kCols; ++c) {
        int write_r = kRows - 1;
        for (int r = kRows - 1; r >= 0; --r) {
            if (grid_[r][c] != 0) {
                if (write_r != r) {
                    grid_[write_r][c] = grid_[r][c];
                    grid_[r][c] = 0;
                    moved = true;
                }
                write_r--;
            }
        }
    }
    return moved;
}

int Game042PuyoPuyo::PopConnectedGroups() {
    bool visited[kRows][kCols];
    bool to_pop[kRows][kCols];
    memset(visited, 0, sizeof(visited));
    memset(to_pop, 0, sizeof(to_pop));

    int total_popped = 0;
    const int dr[4] = {-1, 1, 0, 0};
    const int dc[4] = {0, 0, -1, 1};

    int qr[kRows * kCols];
    int qc[kRows * kCols];

    for (int r = 0; r < kRows; ++r) {
        for (int c = 0; c < kCols; ++c) {
            uint8_t col = grid_[r][c];
            if (col == 0 || visited[r][c]) continue;

            int head = 0, tail = 0;
            qr[tail] = r;
            qc[tail] = c;
            tail++;
            visited[r][c] = true;

            while (head < tail) {
                int cr = qr[head];
                int cc = qc[head];
                head++;

                for (int d = 0; d < 4; ++d) {
                    int nr = cr + dr[d];
                    int nc = cc + dc[d];
                    if (nr >= 0 && nr < kRows && nc >= 0 && nc < kCols) {
                        if (!visited[nr][nc] && grid_[nr][nc] == col) {
                            visited[nr][nc] = true;
                            qr[tail] = nr;
                            qc[tail] = nc;
                            tail++;
                        }
                    }
                }
            }

            if (tail >= 4) {
                total_popped += tail;
                for (int i = 0; i < tail; ++i) {
                    to_pop[qr[i]][qc[i]] = true;
                }
            }
        }
    }

    if (total_popped > 0) {
        for (int r = 0; r < kRows; ++r) {
            for (int c = 0; c < kCols; ++c) {
                if (to_pop[r][c]) {
                    grid_[r][c] = 0;
                }
            }
        }
    }
    return total_popped;
}

void Game042PuyoPuyo::LockAndResolve() {
    int ox = 0, oy = 0;
    GetSubOffset(cur_rot_, ox, oy);
    int sc = cur_col_ + ox;
    int sr = cur_row_ + oy;

    if (cur_row_ >= 0 && cur_row_ < kRows && cur_col_ >= 0 && cur_col_ < kCols) {
        grid_[cur_row_][cur_col_] = main_color_;
    }
    if (sr >= 0 && sr < kRows && sc >= 0 && sc < kCols) {
        grid_[sr][sc] = sub_color_;
    }

    // Disconnected half splits and settles independently under gravity
    ApplyGravity();

    int chain = 0;
    while (true) {
        int popped = PopConnectedGroups();
        if (popped <= 0) break;
        chain++;
        AddScore((uint32_t)(popped * 10 + chain * 40));
        ApplyGravity();
    }

    last_chain_ = chain;
    if (chain > max_chain_) {
        max_chain_ = chain;
    }
    if (chain > 0) {
        chain_flash_timer_ = 0.45f;
    }

    float target_interval = 0.55f - (float)(score_ / 400) * 0.04f;
    if (target_interval < 0.20f) target_interval = 0.20f;
    drop_interval_ = target_interval;

    SpawnPair();
}

void Game042PuyoPuyo::Init() {
    Reset();
}

void Game042PuyoPuyo::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    state_ = STATE_TITLE;
    memset(grid_, 0, sizeof(grid_));
    seed_ = 0x42199101u;
    score_ = 0;
    last_chain_ = 0;
    max_chain_ = 0;
    drop_timer_ = 0.0f;
    drop_interval_ = 0.55f;
    chain_flash_timer_ = 0.0f;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    next_main_ = RandomColor();
    next_sub_ = RandomColor();
    SpawnPair();
    state_ = STATE_TITLE;
}

void Game042PuyoPuyo::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        memset(grid_, 0, sizeof(grid_));
        score_ = 0;
        last_chain_ = 0;
        max_chain_ = 0;
        drop_timer_ = 0.0f;
        drop_interval_ = 0.55f;
        chain_flash_timer_ = 0.0f;
        state_timer_ = 0.0f;
        anim_timer_ = 0.0f;
        next_main_ = RandomColor();
        next_sub_ = RandomColor();
        state_ = STATE_PLAYING;
        SpawnPair();
    }
}

void Game042PuyoPuyo::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game042PuyoPuyo::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

void Game042PuyoPuyo::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt > 0.05f) dt = 0.05f;
    state_timer_ += dt;
    anim_timer_ += dt;
    if (chain_flash_timer_ > 0.0f) {
        chain_flash_timer_ -= dt;
        if (chain_flash_timer_ < 0.0f) chain_flash_timer_ = 0.0f;
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

        if (keys_pressed & KEY_LEFT) {
            if (CanPlacePair(cur_col_ - 1, cur_row_, cur_rot_)) {
                cur_col_ -= 1;
            }
        } else if (keys_pressed & KEY_RIGHT) {
            if (CanPlacePair(cur_col_ + 1, cur_row_, cur_rot_)) {
                cur_col_ += 1;
            }
        }

        if (keys_pressed & (KEY_A | KEY_UP)) {
            RotatePair();
        }

        // Fast/hard drop on KEY_B
        if (keys_pressed & KEY_B) {
            while (CanPlacePair(cur_col_, cur_row_ + 1, cur_rot_)) {
                cur_row_ += 1;
            }
            AddScore(2);
            LockAndResolve();
            return;
        }

        // Soft drop step on KEY_DOWN press + accelerated gravity while held
        if (keys_pressed & KEY_DOWN) {
            if (CanPlacePair(cur_col_, cur_row_ + 1, cur_rot_)) {
                cur_row_ += 1;
                drop_timer_ = 0.0f;
            } else {
                LockAndResolve();
                return;
            }
        }

        float eff_interval = (keys_down & KEY_DOWN) ? 0.07f : drop_interval_;
        drop_timer_ += dt;
        if (drop_timer_ >= eff_interval) {
            drop_timer_ -= eff_interval;
            if (CanPlacePair(cur_col_, cur_row_ + 1, cur_rot_)) {
                cur_row_ += 1;
            } else {
                LockAndResolve();
            }
        }
    }
}

void Game042PuyoPuyo::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    // Background
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            SetPx42(fb_rgb24, x, y, 12, 14, 24);
        }
    }

    // 6x12 Well borders: interior x = 2..7, y = 3..14
    for (int y = 2; y <= 15; ++y) {
        SetPx42(fb_rgb24, 1, y, 75, 85, 130);
        SetPx42(fb_rgb24, 8, y, 75, 85, 130);
    }
    for (int x = 1; x <= 8; ++x) {
        SetPx42(fb_rgb24, x, 15, 75, 85, 130);
    }
    // Spawn X marker at (2 + 2, 3)
    SetPx42(fb_rgb24, 4, 3, 55, 25, 35);

    // Settled puyos
    for (int r = 0; r < kRows; ++r) {
        for (int c = 0; c < kCols; ++c) {
            if (grid_[r][c] != 0) {
                uint8_t pr, pg, pb;
                GetPuyoRGB(grid_[r][c], pr, pg, pb);
                SetPx42(fb_rgb24, 2 + c, 3 + r, pr, pg, pb);
            }
        }
    }

    // Active falling pair
    if (state_ == STATE_PLAYING || state_ == STATE_TITLE || state_ == STATE_PAUSED) {
        int ox = 0, oy = 0;
        GetSubOffset(cur_rot_, ox, oy);
        int sc = cur_col_ + ox;
        int sr = cur_row_ + oy;

        uint8_t mr, mg, mb, sr_c, sg_c, sb_c;
        GetPuyoRGB(main_color_, mr, mg, mb);
        GetPuyoRGB(sub_color_, sr_c, sg_c, sb_c);

        if (cur_row_ >= 0 && cur_row_ < kRows) {
            SetPx42(fb_rgb24, 2 + cur_col_, 3 + cur_row_, mr, mg, mb);
        }
        if (sr >= 0 && sr < kRows && sc >= 0 && sc < kCols) {
            SetPx42(fb_rgb24, 2 + sc, 3 + sr, sr_c, sg_c, sb_c);
        }
    }

    // Next-pair preview frame on right (x = 10..14, y = 3..8)
    for (int x = 10; x <= 14; ++x) {
        SetPx42(fb_rgb24, x, 3, 45, 55, 85);
        SetPx42(fb_rgb24, x, 8, 45, 55, 85);
    }
    for (int y = 3; y <= 8; ++y) {
        SetPx42(fb_rgb24, 10, y, 45, 55, 85);
        SetPx42(fb_rgb24, 14, y, 45, 55, 85);
    }
    {
        uint8_t nmr, nmg, nmb, nsr, nsg, nsb;
        GetPuyoRGB(next_sub_, nsr, nsg, nsb);
        GetPuyoRGB(next_main_, nmr, nmg, nmb);
        SetPx42(fb_rgb24, 12, 5, nsr, nsg, nsb);
        SetPx42(fb_rgb24, 12, 6, nmr, nmg, nmb);
    }

    // Chain indicator bars on right lower area (x = 11..13, y = 10..14)
    int display_chain = (chain_flash_timer_ > 0.0f) ? last_chain_ : max_chain_;
    if (display_chain > 5) display_chain = 5;
    for (int i = 0; i < display_chain; ++i) {
        uint8_t cr = (chain_flash_timer_ > 0.0f) ? 255 : 180;
        uint8_t cg = (chain_flash_timer_ > 0.0f) ? 215 : 140;
        SetPx42(fb_rgb24, 11, 14 - i, cr, cg, 25);
        SetPx42(fb_rgb24, 12, 14 - i, cr, cg, 25);
    }

    // Score bar at y = 0
    int dots = (int)(score_ / 80);
    if (dots > 16) dots = 16;
    for (int x = 0; x < dots; ++x) {
        SetPx42(fb_rgb24, x, 0, 40, 210, 255);
    }

    if (state_ == STATE_GAMEOVER) {
        for (int x = 0; x < 16; ++x) {
            SetPx42(fb_rgb24, x, 0, 235, 50, 50);
        }
    } else if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPx42(fb_rgb24, 6, y, 250, 250, 250);
            SetPx42(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game042PuyoPuyo::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = (state_ == STATE_GAMEOVER) ? 0 : 1;
    st.state = (uint8_t)state_;
    uint32_t prog = score_ / 10;
    st.progress = (uint8_t)(prog > 100 ? 100 : prog);
    return st;
}

static_assert(sizeof(Game042PuyoPuyo) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
