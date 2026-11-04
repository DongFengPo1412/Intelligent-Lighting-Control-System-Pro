// game_065_dots_and_boxes.cpp —— 目标 #065 点格棋 (Dots and Boxes) 核心实现
#include "game_065_dots_and_boxes.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>
#include <stdlib.h>

namespace arcade {

static inline void SetPx065(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

Game065DotsAndBoxes::Game065DotsAndBoxes()
    : state_(STATE_TITLE),
      cur_edge_(0),
      player_boxes_(0),
      ai_boxes_(0),
      player_turn_(true),
      ai_timer_(0.0f),
      score_(0),
      high_score_(0),
      state_timer_(0.0f),
      anim_timer_(0.0f) {
    memset(h_edges_, 0, sizeof(h_edges_));
    memset(v_edges_, 0, sizeof(v_edges_));
    memset(boxes_, 0, sizeof(boxes_));
}

void Game065DotsAndBoxes::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

void Game065DotsAndBoxes::InitBoard() {
    memset(h_edges_, kUnclaimed, sizeof(h_edges_));
    memset(v_edges_, kUnclaimed, sizeof(v_edges_));
    memset(boxes_, kUnclaimed, sizeof(boxes_));
    cur_edge_ = 0;
    player_boxes_ = 0;
    ai_boxes_ = 0;
    player_turn_ = true;
    ai_timer_ = 0.0f;
}

void Game065DotsAndBoxes::Init() {
    Reset();
}

void Game065DotsAndBoxes::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    state_ = STATE_TITLE;
    score_ = 0;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    InitBoard();
}

void Game065DotsAndBoxes::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        state_ = STATE_PLAYING;
        score_ = 0;
        state_timer_ = 0.0f;
        anim_timer_ = 0.0f;
        InitBoard();
    }
}

void Game065DotsAndBoxes::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game065DotsAndBoxes::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

bool Game065DotsAndBoxes::IsEdgeClaimed(int edge_id) const {
    if (edge_id < 0 || edge_id >= kTotalEdges) return true;
    if (edge_id < 20) {
        return h_edges_[edge_id / 4][edge_id % 4] != kUnclaimed;
    }
    int v = edge_id - 20;
    return v_edges_[v / 5][v % 5] != kUnclaimed;
}

void Game065DotsAndBoxes::SetEdgeOwner(int edge_id, uint8_t owner) {
    if (edge_id < 0 || edge_id >= kTotalEdges) return;
    if (edge_id < 20) {
        h_edges_[edge_id / 4][edge_id % 4] = owner;
    } else {
        int v = edge_id - 20;
        v_edges_[v / 5][v % 5] = owner;
    }
}

void Game065DotsAndBoxes::EdgeCenter2x(int edge_id, int& cx2, int& cy2) const {
    if (edge_id < 20) {
        int r = edge_id / 4;
        int c = edge_id % 4;
        cx2 = 7 + c * 6;
        cy2 = 4 + r * 6;
    } else {
        int v = edge_id - 20;
        int r = v / 5;
        int c = v % 5;
        cx2 = 4 + c * 6;
        cy2 = 7 + r * 6;
    }
}

int Game065DotsAndBoxes::BoxEdgeCount(int br, int bc) const {
    int cnt = 0;
    if (h_edges_[br][bc] != kUnclaimed) cnt++;
    if (h_edges_[br + 1][bc] != kUnclaimed) cnt++;
    if (v_edges_[br][bc] != kUnclaimed) cnt++;
    if (v_edges_[br][bc + 1] != kUnclaimed) cnt++;
    return cnt;
}

int Game065DotsAndBoxes::ClaimEdge(int edge_id, uint8_t owner) {
    if (IsEdgeClaimed(edge_id)) return -1;
    SetEdgeOwner(edge_id, owner);

    int completed = 0;
    if (edge_id < 20) {
        int r = edge_id / 4;
        int c = edge_id % 4;
        if (r > 0 && boxes_[r - 1][c] == kUnclaimed && BoxEdgeCount(r - 1, c) == 4) {
            boxes_[r - 1][c] = owner;
            completed++;
        }
        if (r < 4 && boxes_[r][c] == kUnclaimed && BoxEdgeCount(r, c) == 4) {
            boxes_[r][c] = owner;
            completed++;
        }
    } else {
        int v = edge_id - 20;
        int r = v / 5;
        int c = v % 5;
        if (c > 0 && boxes_[r][c - 1] == kUnclaimed && BoxEdgeCount(r, c - 1) == 4) {
            boxes_[r][c - 1] = owner;
            completed++;
        }
        if (c < 4 && boxes_[r][c] == kUnclaimed && BoxEdgeCount(r, c) == 4) {
            boxes_[r][c] = owner;
            completed++;
        }
    }

    if (completed > 0) {
        if (owner == kPlayer) {
            player_boxes_ += completed;
            AddScore((uint32_t)(completed * 50));
        } else {
            ai_boxes_ += completed;
        }
    }
    return completed;
}

void Game065DotsAndBoxes::SnapCursorToUnclaimed() {
    if (!IsEdgeClaimed(cur_edge_)) return;
    int cx2 = 0, cy2 = 0;
    EdgeCenter2x(cur_edge_, cx2, cy2);
    int best_id = -1;
    int best_dist = 999999;
    for (int i = 0; i < kTotalEdges; ++i) {
        if (!IsEdgeClaimed(i)) {
            int jx2 = 0, jy2 = 0;
            EdgeCenter2x(i, jx2, jy2);
            int d = abs(jx2 - cx2) + abs(jy2 - cy2);
            if (d < best_dist) {
                best_dist = d;
                best_id = i;
            }
        }
    }
    if (best_id >= 0) cur_edge_ = best_id;
}

void Game065DotsAndBoxes::MoveCursorDir(int dx, int dy) {
    SnapCursorToUnclaimed();
    int cx2 = 0, cy2 = 0;
    EdgeCenter2x(cur_edge_, cx2, cy2);

    int best_id = -1;
    int best_cost = 999999;
    for (int i = 0; i < kTotalEdges; ++i) {
        if (i == cur_edge_ || IsEdgeClaimed(i)) continue;
        int jx2 = 0, jy2 = 0;
        EdgeCenter2x(i, jx2, jy2);
        int primary = (jx2 - cx2) * dx + (jy2 - cy2) * dy;
        if (primary <= 0) continue;
        int perp = (dx != 0) ? abs(jy2 - cy2) : abs(jx2 - cx2);
        int cost = primary * 5 + perp * 6;
        if (cost < best_cost) {
            best_cost = cost;
            best_id = i;
        }
    }
    if (best_id >= 0) {
        cur_edge_ = best_id;
    }
}

void Game065DotsAndBoxes::ToggleCursorOrientation() {
    SnapCursorToUnclaimed();
    int cx2 = 0, cy2 = 0;
    EdgeCenter2x(cur_edge_, cx2, cy2);
    int start = (cur_edge_ < 20) ? 20 : 0;
    int end = (cur_edge_ < 20) ? 40 : 20;
    int best_id = -1;
    int best_dist = 999999;
    for (int i = start; i < end; ++i) {
        if (!IsEdgeClaimed(i)) {
            int jx2 = 0, jy2 = 0;
            EdgeCenter2x(i, jx2, jy2);
            int d = abs(jx2 - cx2) + abs(jy2 - cy2);
            if (d < best_dist) {
                best_dist = d;
                best_id = i;
            }
        }
    }
    if (best_id >= 0) cur_edge_ = best_id;
}

int Game065DotsAndBoxes::ChooseAiEdge() const {
    int best_edge = -1;
    int best_score = -999999;

    for (int i = 0; i < kTotalEdges; ++i) {
        if (IsEdgeClaimed(i)) continue;

        int completes = 0;
        int gives_third = 0;
        if (i < 20) {
            int r = i / 4;
            int c = i % 4;
            if (r > 0) {
                int ec = BoxEdgeCount(r - 1, c);
                if (ec == 3) completes++;
                else if (ec == 2) gives_third++;
            }
            if (r < 4) {
                int ec = BoxEdgeCount(r, c);
                if (ec == 3) completes++;
                else if (ec == 2) gives_third++;
            }
        } else {
            int v = i - 20;
            int r = v / 5;
            int c = v % 5;
            if (c > 0) {
                int ec = BoxEdgeCount(r, c - 1);
                if (ec == 3) completes++;
                else if (ec == 2) gives_third++;
            }
            if (c < 4) {
                int ec = BoxEdgeCount(r, c);
                if (ec == 3) completes++;
                else if (ec == 2) gives_third++;
            }
        }

        int eval = completes * 1000 - gives_third * 200;
        if (eval > best_score) {
            best_score = eval;
            best_edge = i;
        }
    }
    return best_edge;
}

void Game065DotsAndBoxes::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
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
            SnapCursorToUnclaimed();
            if (keys_pressed & KEY_LEFT) MoveCursorDir(-1, 0);
            else if (keys_pressed & KEY_RIGHT) MoveCursorDir(1, 0);
            else if (keys_pressed & KEY_UP) MoveCursorDir(0, -1);
            else if (keys_pressed & KEY_DOWN) MoveCursorDir(0, 1);

            if (keys_pressed & KEY_B) {
                ToggleCursorOrientation();
            }

            if (keys_pressed & KEY_A) {
                int made = ClaimEdge(cur_edge_, kPlayer);
                if (made >= 0) {
                    if (player_boxes_ + ai_boxes_ >= 16) {
                        if (player_boxes_ > ai_boxes_) {
                            AddScore(200);
                            state_ = STATE_VICTORY;
                        } else {
                            state_ = STATE_GAMEOVER;
                        }
                        state_timer_ = 0.0f;
                        return;
                    }
                    SnapCursorToUnclaimed();
                    if (made == 0) {
                        player_turn_ = false;
                        ai_timer_ = 0.20f;
                    }
                }
            }
        } else {
            ai_timer_ -= dt;
            if (ai_timer_ <= 0.0f) {
                int ai_e = ChooseAiEdge();
                if (ai_e >= 0) {
                    int made = ClaimEdge(ai_e, kAi);
                    if (player_boxes_ + ai_boxes_ >= 16) {
                        if (player_boxes_ > ai_boxes_) {
                            AddScore(200);
                            state_ = STATE_VICTORY;
                        } else {
                            state_ = STATE_GAMEOVER;
                        }
                        state_timer_ = 0.0f;
                        return;
                    }
                    SnapCursorToUnclaimed();
                    if (made > 0) {
                        ai_timer_ = 0.18f;
                    } else {
                        player_turn_ = true;
                    }
                } else {
                    player_turn_ = true;
                }
            }
        }
    }
}

void Game065DotsAndBoxes::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            SetPx065(fb_rgb24, x, y, 12, 14, 24);
        }
    }

    for (int r = 0; r < 4; ++r) {
        for (int c = 0; c < 4; ++c) {
            uint8_t b = boxes_[r][c];
            if (b != kUnclaimed) {
                uint8_t cr = (b == kPlayer) ? 0 : 165;
                uint8_t cg = (b == kPlayer) ? 130 : 35;
                uint8_t cb = (b == kPlayer) ? 170 : 48;
                int x0 = 3 + c * 3;
                int y0 = 3 + r * 3;
                for (int dy = 0; dy < 2; ++dy) {
                    for (int dx = 0; dx < 2; ++dx) {
                        SetPx065(fb_rgb24, x0 + dx, y0 + dy, cr, cg, cb);
                    }
                }
            }
        }
    }

    for (int r = 0; r < 5; ++r) {
        for (int c = 0; c < 4; ++c) {
            uint8_t owner = h_edges_[r][c];
            uint8_t cr = 28, cg = 32, cb = 46;
            if (owner == kPlayer) { cr = 0; cg = 215; cb = 255; }
            else if (owner == kAi) { cr = 255; cg = 75; cb = 75; }
            int x0 = 3 + c * 3;
            int y0 = 2 + r * 3;
            SetPx065(fb_rgb24, x0,     y0, cr, cg, cb);
            SetPx065(fb_rgb24, x0 + 1, y0, cr, cg, cb);
        }
    }

    for (int r = 0; r < 4; ++r) {
        for (int c = 0; c < 5; ++c) {
            uint8_t owner = v_edges_[r][c];
            uint8_t cr = 28, cg = 32, cb = 46;
            if (owner == kPlayer) { cr = 0; cg = 215; cb = 255; }
            else if (owner == kAi) { cr = 255; cg = 75; cb = 75; }
            int x0 = 2 + c * 3;
            int y0 = 3 + r * 3;
            SetPx065(fb_rgb24, x0, y0,     cr, cg, cb);
            SetPx065(fb_rgb24, x0, y0 + 1, cr, cg, cb);
        }
    }

    if (state_ == STATE_PLAYING && player_turn_ && !IsEdgeClaimed(cur_edge_)) {
        bool blink = (((int)(anim_timer_ * 6.0f)) % 2 == 0);
        uint8_t cr = blink ? 255 : 140;
        uint8_t cg = blink ? 235 : 130;
        uint8_t cb = blink ?  35 :  25;
        if (cur_edge_ < 20) {
            int r = cur_edge_ / 4;
            int c = cur_edge_ % 4;
            int x0 = 3 + c * 3;
            int y0 = 2 + r * 3;
            SetPx065(fb_rgb24, x0,     y0, cr, cg, cb);
            SetPx065(fb_rgb24, x0 + 1, y0, cr, cg, cb);
        } else {
            int v = cur_edge_ - 20;
            int r = v / 5;
            int c = v % 5;
            int x0 = 2 + c * 3;
            int y0 = 3 + r * 3;
            SetPx065(fb_rgb24, x0, y0,     cr, cg, cb);
            SetPx065(fb_rgb24, x0, y0 + 1, cr, cg, cb);
        }
    }

    for (int gy = 0; gy < 5; ++gy) {
        for (int gx = 0; gx < 5; ++gx) {
            SetPx065(fb_rgb24, 2 + gx * 3, 2 + gy * 3, 235, 240, 250);
        }
    }

    if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPx065(fb_rgb24, 6, y, 250, 250, 250);
            SetPx065(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game065DotsAndBoxes::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = (state_ == STATE_GAMEOVER) ? 0 : 1;
    st.state = (uint8_t)state_;
    st.progress = (uint8_t)(((player_boxes_ + ai_boxes_) * 100) / 16);
    return st;
}

static_assert(sizeof(Game065DotsAndBoxes) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
