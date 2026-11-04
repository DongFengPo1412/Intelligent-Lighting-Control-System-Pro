// game_067_quoridor.cpp —— 目标 #067 围墙棋 (Quoridor) 核心实现
#include "game_067_quoridor.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>

namespace arcade {

static const int kQuorDirs[4][2] = {
    {0, -1}, {0, 1}, {-1, 0}, {1, 0} // UP, DOWN, LEFT, RIGHT
};

static inline void SetPx067(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

Game067Quoridor::Game067Quoridor()
    : state_(STATE_TITLE),
      player_c_(3),
      player_r_(6),
      ai_c_(3),
      ai_r_(0),
      player_walls_(kMaxWalls),
      ai_walls_(kMaxWalls),
      mode_(kModeMove),
      aim_dir_(0),
      wall_c_(2),
      wall_r_(2),
      player_turn_(true),
      ai_timer_(0.0f),
      score_(0),
      high_score_(0),
      state_timer_(0.0f),
      anim_timer_(0.0f) {
    memset(h_walls_, 0, sizeof(h_walls_));
    memset(v_walls_, 0, sizeof(v_walls_));
}

void Game067Quoridor::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

void Game067Quoridor::InitBoard() {
    memset(h_walls_, 0, sizeof(h_walls_));
    memset(v_walls_, 0, sizeof(v_walls_));
    player_c_ = 3;
    player_r_ = 6;
    ai_c_ = 3;
    ai_r_ = 0;
    player_walls_ = kMaxWalls;
    ai_walls_ = kMaxWalls;
    mode_ = kModeMove;
    aim_dir_ = 0;
    wall_c_ = 2;
    wall_r_ = 2;
    player_turn_ = true;
    ai_timer_ = 0.0f;
}

void Game067Quoridor::Init() {
    Reset();
}

void Game067Quoridor::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    state_ = STATE_TITLE;
    score_ = 0;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    InitBoard();
}

void Game067Quoridor::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        state_ = STATE_PLAYING;
        score_ = 0;
        state_timer_ = 0.0f;
        anim_timer_ = 0.0f;
        InitBoard();
    }
}

void Game067Quoridor::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game067Quoridor::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

bool Game067Quoridor::IsEdgeBlocked(int c1, int r1, int c2, int r2) const {
    if (c1 == c2) {
        int r_min = (r1 < r2) ? r1 : r2;
        if (r_min < 0 || r_min >= kGrooves) return true;
        if (c1 < kGrooves && h_walls_[r_min][c1]) return true;
        if (c1 > 0 && h_walls_[r_min][c1 - 1]) return true;
        return false;
    }
    if (r1 == r2) {
        int c_min = (c1 < c2) ? c1 : c2;
        if (c_min < 0 || c_min >= kGrooves) return true;
        if (r1 < kGrooves && v_walls_[r1][c_min]) return true;
        if (r1 > 0 && v_walls_[r1 - 1][c_min]) return true;
        return false;
    }
    return true;
}

int Game067Quoridor::ShortestPathLen(int sc, int sr, int goal_row) const {
    if (sr == goal_row) return 0;
    int8_t dist[kCells][kCells];
    memset(dist, -1, sizeof(dist));
    uint8_t qc[kCells * kCells];
    uint8_t qr[kCells * kCells];
    int head = 0, tail = 0;

    dist[sr][sc] = 0;
    qc[tail] = (uint8_t)sc;
    qr[tail] = (uint8_t)sr;
    tail++;

    while (head < tail) {
        int c = qc[head];
        int r = qr[head];
        head++;
        int d = dist[r][c];
        if (r == goal_row) return d;

        for (int i = 0; i < 4; ++i) {
            int nc = c + kQuorDirs[i][0];
            int nr = r + kQuorDirs[i][1];
            if (nc < 0 || nc >= kCells || nr < 0 || nr >= kCells) continue;
            if (dist[nr][nc] >= 0) continue;
            if (IsEdgeBlocked(c, r, nc, nr)) continue;
            dist[nr][nc] = (int8_t)(d + 1);
            if (nr == goal_row) return d + 1;
            qc[tail] = (uint8_t)nc;
            qr[tail] = (uint8_t)nr;
            tail++;
        }
    }
    return -1;
}

bool Game067Quoridor::CanPlaceWall(int wc, int wr, bool horiz) {
    if (wc < 0 || wc >= kGrooves || wr < 0 || wr >= kGrooves) return false;

    if (horiz) {
        if (h_walls_[wr][wc]) return false;
        if (wc > 0 && h_walls_[wr][wc - 1]) return false;
        if (wc + 1 < kGrooves && h_walls_[wr][wc + 1]) return false;
        if (v_walls_[wr][wc]) return false;

        h_walls_[wr][wc] = true;
        int pd = ShortestPathLen(player_c_, player_r_, 0);
        int ad = ShortestPathLen(ai_c_, ai_r_, kCells - 1);
        h_walls_[wr][wc] = false;
        return (pd >= 0 && ad >= 0);
    } else {
        if (v_walls_[wr][wc]) return false;
        if (wr > 0 && v_walls_[wr - 1][wc]) return false;
        if (wr + 1 < kGrooves && v_walls_[wr + 1][wc]) return false;
        if (h_walls_[wr][wc]) return false;

        v_walls_[wr][wc] = true;
        int pd = ShortestPathLen(player_c_, player_r_, 0);
        int ad = ShortestPathLen(ai_c_, ai_r_, kCells - 1);
        v_walls_[wr][wc] = false;
        return (pd >= 0 && ad >= 0);
    }
}

bool Game067Quoridor::ComputePawnStep(int sc, int sr, int oc, int orow, int dir, int& out_c, int& out_r) const {
    if (dir < 0 || dir >= 4) return false;
    int dc = kQuorDirs[dir][0];
    int dr = kQuorDirs[dir][1];
    int nc = sc + dc;
    int nr = sr + dr;
    if (nc < 0 || nc >= kCells || nr < 0 || nr >= kCells) return false;
    if (IsEdgeBlocked(sc, sr, nc, nr)) return false;

    if (nc == oc && nr == orow) {
        int jc = nc + dc;
        int jr = nr + dr;
        if (jc >= 0 && jc < kCells && jr >= 0 && jr < kCells && !IsEdgeBlocked(nc, nr, jc, jr)) {
            out_c = jc;
            out_r = jr;
            return true;
        }
        // Diagonal jump around blocked opponent pawn
        int p1c = nc - dr, p1r = nr + dc;
        if (p1c >= 0 && p1c < kCells && p1r >= 0 && p1r < kCells && !IsEdgeBlocked(nc, nr, p1c, p1r)) {
            out_c = p1c;
            out_r = p1r;
            return true;
        }
        int p2c = nc + dr, p2r = nr - dc;
        if (p2c >= 0 && p2c < kCells && p2r >= 0 && p2r < kCells && !IsEdgeBlocked(nc, nr, p2c, p2r)) {
            out_c = p2c;
            out_r = p2r;
            return true;
        }
        return false;
    }

    out_c = nc;
    out_r = nr;
    return true;
}

void Game067Quoridor::MakeAiTurn() {
    int p_dist = ShortestPathLen(player_c_, player_r_, 0);
    int a_dist = ShortestPathLen(ai_c_, ai_r_, kCells - 1);

    if (ai_walls_ > 0 && p_dist <= a_dist && p_dist <= 4) {
        int best_gain = 0;
        int best_wc = -1, best_wr = -1;
        bool best_h = true;

        for (int h = 0; h < 2; ++h) {
            bool horiz = (h == 0);
            for (int wr = 0; wr < kGrooves; ++wr) {
                for (int wc = 0; wc < kGrooves; ++wc) {
                    if (!CanPlaceWall(wc, wr, horiz)) continue;
                    if (horiz) h_walls_[wr][wc] = true;
                    else v_walls_[wr][wc] = true;

                    int np = ShortestPathLen(player_c_, player_r_, 0);
                    int na = ShortestPathLen(ai_c_, ai_r_, kCells - 1);

                    if (horiz) h_walls_[wr][wc] = false;
                    else v_walls_[wr][wc] = false;

                    int gain = (np - p_dist) - (na - a_dist);
                    if (gain > best_gain) {
                        best_gain = gain;
                        best_wc = wc;
                        best_wr = wr;
                        best_h = horiz;
                    }
                }
            }
        }

        int min_gain = (p_dist <= 2) ? 1 : 2;
        if (best_wc >= 0 && best_gain >= min_gain) {
            if (best_h) h_walls_[best_wr][best_wc] = true;
            else v_walls_[best_wr][best_wc] = true;
            ai_walls_--;
            player_turn_ = true;
            return;
        }
    }

    int best_dir = -1;
    int best_len = 999999;
    for (int d = 0; d < 4; ++d) {
        int nc = 0, nr = 0;
        if (ComputePawnStep(ai_c_, ai_r_, player_c_, player_r_, d, nc, nr)) {
            int rem = ShortestPathLen(nc, nr, kCells - 1);
            if (rem >= 0 && rem < best_len) {
                best_len = rem;
                best_dir = d;
            }
        }
    }

    if (best_dir >= 0) {
        int nc = 0, nr = 0;
        if (ComputePawnStep(ai_c_, ai_r_, player_c_, player_r_, best_dir, nc, nr)) {
            ai_c_ = nc;
            ai_r_ = nr;
            if (ai_r_ == kCells - 1) {
                state_ = STATE_GAMEOVER;
                state_timer_ = 0.0f;
                return;
            }
        }
    }
    player_turn_ = true;
}

void Game067Quoridor::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
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
            if (keys_pressed & KEY_B) {
                if (player_walls_ > 0) {
                    mode_ = (mode_ + 1) % 3;
                } else {
                    mode_ = kModeMove;
                }
            }

            if (mode_ == kModeMove) {
                if (keys_pressed & KEY_UP) aim_dir_ = 0;
                else if (keys_pressed & KEY_DOWN) aim_dir_ = 1;
                else if (keys_pressed & KEY_LEFT) aim_dir_ = 2;
                else if (keys_pressed & KEY_RIGHT) aim_dir_ = 3;

                if (keys_pressed & KEY_A) {
                    int nc = 0, nr = 0;
                    if (ComputePawnStep(player_c_, player_r_, ai_c_, ai_r_, aim_dir_, nc, nr)) {
                        player_c_ = nc;
                        player_r_ = nr;
                        AddScore(10);
                        if (player_r_ == 0) {
                            AddScore(400);
                            state_ = STATE_VICTORY;
                            state_timer_ = 0.0f;
                            return;
                        }
                        player_turn_ = false;
                        ai_timer_ = 0.20f;
                    }
                }
            } else {
                if (keys_pressed & KEY_LEFT) {
                    if (wall_c_ > 0) wall_c_--;
                } else if (keys_pressed & KEY_RIGHT) {
                    if (wall_c_ < kGrooves - 1) wall_c_++;
                }
                if (keys_pressed & KEY_UP) {
                    if (wall_r_ > 0) wall_r_--;
                } else if (keys_pressed & KEY_DOWN) {
                    if (wall_r_ < kGrooves - 1) wall_r_++;
                }

                if (keys_pressed & KEY_A) {
                    bool horiz = (mode_ == kModeWallH);
                    if (player_walls_ > 0 && CanPlaceWall(wall_c_, wall_r_, horiz)) {
                        if (horiz) h_walls_[wall_r_][wall_c_] = true;
                        else v_walls_[wall_r_][wall_c_] = true;
                        player_walls_--;
                        mode_ = kModeMove;
                        player_turn_ = false;
                        ai_timer_ = 0.20f;
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

void Game067Quoridor::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            SetPx067(fb_rgb24, x, y, 12, 12, 18);
        }
    }

    // Goal row borders
    for (int x = 1; x <= 13; ++x) {
        SetPx067(fb_rgb24, x, 0,  0,  75, 95);
        SetPx067(fb_rgb24, x, 14, 95, 25, 25);
    }

    // 7x7 pawn lattice squares
    for (int r = 0; r < kCells; ++r) {
        for (int c = 0; c < kCells; ++c) {
            SetPx067(fb_rgb24, 1 + c * 2, 1 + r * 2, 42, 36, 32);
        }
    }

    // Placed horizontal & vertical walls
    for (int wr = 0; wr < kGrooves; ++wr) {
        for (int wc = 0; wc < kGrooves; ++wc) {
            if (h_walls_[wr][wc]) {
                int y = 2 + wr * 2;
                int x0 = 1 + wc * 2;
                for (int dx = 0; dx < 3; ++dx) {
                    SetPx067(fb_rgb24, x0 + dx, y, 235, 170, 45);
                }
            }
            if (v_walls_[wr][wc]) {
                int x = 2 + wc * 2;
                int y0 = 1 + wr * 2;
                for (int dy = 0; dy < 3; ++dy) {
                    SetPx067(fb_rgb24, x, y0 + dy, 235, 170, 45);
                }
            }
        }
    }

    // Active turn preview (pawn step target OR wall ghost)
    if (state_ == STATE_PLAYING && player_turn_) {
        bool blink = (((int)(anim_timer_ * 6.0f)) % 2 == 0);
        if (mode_ == kModeMove) {
            int tc = 0, tr = 0;
            if (blink && ComputePawnStep(player_c_, player_r_, ai_c_, ai_r_, aim_dir_, tc, tr)) {
                SetPx067(fb_rgb24, 1 + tc * 2, 1 + tr * 2, 60, 230, 120);
            }
        } else {
            bool horiz = (mode_ == kModeWallH);
            bool ok = CanPlaceWall(wall_c_, wall_r_, horiz);
            if (blink) {
                uint8_t cr = ok ? 90 : 240;
                uint8_t cg = ok ? 250 : 45;
                uint8_t cb = ok ? 110 : 45;
                if (horiz) {
                    int y = 2 + wall_r_ * 2;
                    int x0 = 1 + wall_c_ * 2;
                    for (int dx = 0; dx < 3; ++dx) SetPx067(fb_rgb24, x0 + dx, y, cr, cg, cb);
                } else {
                    int x = 2 + wall_c_ * 2;
                    int y0 = 1 + wall_r_ * 2;
                    for (int dy = 0; dy < 3; ++dy) SetPx067(fb_rgb24, x, y0 + dy, cr, cg, cb);
                }
            }
        }
    }

    // Pawns
    SetPx067(fb_rgb24, 1 + player_c_ * 2, 1 + player_r_ * 2, 0, 235, 255);
    SetPx067(fb_rgb24, 1 + ai_c_ * 2,     1 + ai_r_ * 2,     255, 65, 55);

    // Row 15: wall stock indicators + mode indicator
    for (int i = 0; i < player_walls_; ++i) {
        SetPx067(fb_rgb24, 1 + i, 15, 0, 200, 235);
    }
    for (int i = 0; i < ai_walls_; ++i) {
        SetPx067(fb_rgb24, 14 - i, 15, 235, 80, 65);
    }
    if (mode_ == kModeMove) {
        SetPx067(fb_rgb24, 7, 15, 0, 235, 255);
    } else {
        SetPx067(fb_rgb24, 7, 15, 255, 215, 30);
        SetPx067(fb_rgb24, 8, 15, 255, 215, 30);
    }

    if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPx067(fb_rgb24, 6, y, 250, 250, 250);
            SetPx067(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game067Quoridor::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = (state_ == STATE_GAMEOVER) ? 0 : 1;
    st.state = (uint8_t)state_;
    st.progress = (uint8_t)(((6 - player_r_) * 100) / 6);
    return st;
}

static_assert(sizeof(Game067Quoridor) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
