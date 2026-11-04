// game_084_node_conquest.cpp —— 目标 #084 节点征服 核心实现
#include "game_084_node_conquest.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>
#include <math.h>

namespace arcade {

static const int kNodeCoords[7][2] = {
    {1, 2},   // 0: Player Cyan
    {7, 1},   // 1: Neutral
    {2, 8},   // 2: Neutral
    {7, 7},   // 3: Center Hub
    {12, 6},  // 4: Neutral
    {6, 13},  // 5: Neutral
    {13, 12}, // 6: AI Red
};

static inline void SetPx84(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

Game084NodeConquest::Game084NodeConquest()
    : state_(STATE_TITLE),
      score_(0),
      high_score_(0),
      state_timer_(0.0f),
      anim_timer_(0.0f),
      cursor_node_(0),
      selected_node_(-1),
      ai_timer_(2.8f) {
    SetupMatch(STATE_TITLE);
}

void Game084NodeConquest::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

void Game084NodeConquest::SetupMatch(CartridgeState new_state) {
    state_ = new_state;
    score_ = 0;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    cursor_node_ = 0;
    selected_node_ = -1;
    ai_timer_ = 2.8f;

    const float init_troops[kNumNodes] = {20.0f, 6.0f, 6.0f, 10.0f, 6.0f, 6.0f, 16.0f};
    const uint8_t init_owners[kNumNodes] = {
        NODE_PLAYER, NODE_NEUTRAL, NODE_NEUTRAL, NODE_NEUTRAL,
        NODE_NEUTRAL, NODE_NEUTRAL, NODE_AI
    };

    for (int i = 0; i < kNumNodes; ++i) {
        nodes_[i].x = kNodeCoords[i][0];
        nodes_[i].y = kNodeCoords[i][1];
        nodes_[i].owner = init_owners[i];
        nodes_[i].troops = init_troops[i];
    }

    for (int i = 0; i < kMaxFleets; ++i) {
        fleets_[i] = {false, NODE_NEUTRAL, 0, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f};
    }
}

void Game084NodeConquest::Init() {
    Reset();
}

void Game084NodeConquest::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    SetupMatch(STATE_TITLE);
}

void Game084NodeConquest::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        SetupMatch(STATE_PLAYING);
    }
}

void Game084NodeConquest::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game084NodeConquest::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

void Game084NodeConquest::MoveCursorDir(int dx, int dy) {
    float cx = (float)nodes_[cursor_node_].x + 0.5f;
    float cy = (float)nodes_[cursor_node_].y + 0.5f;
    int best_idx = -1;
    float best_metric = 1e9f;

    for (int i = 0; i < kNumNodes; ++i) {
        if (i == cursor_node_) continue;
        float vx = ((float)nodes_[i].x + 0.5f) - cx;
        float vy = ((float)nodes_[i].y + 0.5f) - cy;
        float proj = vx * (float)dx + vy * (float)dy;
        if (proj > 0.5f) {
            float perp = fabsf(vx * (float)dy - vy * (float)dx);
            float metric = proj + perp * 1.6f;
            if (metric < best_metric) {
                best_metric = metric;
                best_idx = i;
            }
        }
    }

    if (best_idx >= 0) {
        cursor_node_ = best_idx;
    } else {
        if (dx > 0 || dy > 0) {
            cursor_node_ = (cursor_node_ + 1) % kNumNodes;
        } else {
            cursor_node_ = (cursor_node_ + kNumNodes - 1) % kNumNodes;
        }
    }
}

void Game084NodeConquest::DispatchFleet(int src_idx, int dst_idx) {
    if (src_idx < 0 || src_idx >= kNumNodes || dst_idx < 0 || dst_idx >= kNumNodes) return;
    if (src_idx == dst_idx) return;
    int send = (int)(nodes_[src_idx].troops * 0.5f);
    if (send < 1) return;

    for (int f = 0; f < kMaxFleets; ++f) {
        if (!fleets_[f].active) {
            nodes_[src_idx].troops -= (float)send;
            float sx = (float)nodes_[src_idx].x + 0.5f;
            float sy = (float)nodes_[src_idx].y + 0.5f;
            float tx = (float)nodes_[dst_idx].x + 0.5f;
            float ty = (float)nodes_[dst_idx].y + 0.5f;
            float dx = tx - sx;
            float dy = ty - sy;
            float dist = sqrtf(dx * dx + dy * dy);
            if (dist < 0.01f) dist = 1.0f;
            const float speed = 6.5f;
            fleets_[f].active = true;
            fleets_[f].owner = nodes_[src_idx].owner;
            fleets_[f].target_node = dst_idx;
            fleets_[f].troops = (float)send;
            fleets_[f].x = sx;
            fleets_[f].y = sy;
            fleets_[f].vx = (dx / dist) * speed;
            fleets_[f].vy = (dy / dist) * speed;
            return;
        }
    }
}

void Game084NodeConquest::UpdateAI(float dt) {
    ai_timer_ -= dt;
    if (ai_timer_ > 0.0f) return;
    ai_timer_ = 2.8f;

    int best_src = -1;
    float max_troops = 13.0f;
    for (int i = 0; i < kNumNodes; ++i) {
        if (nodes_[i].owner == NODE_AI && nodes_[i].troops > max_troops) {
            max_troops = nodes_[i].troops;
            best_src = i;
        }
    }
    if (best_src < 0) return;

    int best_dst = -1;
    float best_cost = 1e9f;
    for (int j = 0; j < kNumNodes; ++j) {
        if (nodes_[j].owner == NODE_AI) continue;
        float dx = (float)(nodes_[j].x - nodes_[best_src].x);
        float dy = (float)(nodes_[j].y - nodes_[best_src].y);
        float dist = sqrtf(dx * dx + dy * dy);
        float cost = nodes_[j].troops * 1.2f + dist * 0.8f;
        if (cost < best_cost) {
            best_cost = cost;
            best_dst = j;
        }
    }
    if (best_dst >= 0) {
        DispatchFleet(best_src, best_dst);
    }
}

void Game084NodeConquest::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
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

    if (keys_pressed & KEY_START) {
        state_ = STATE_PAUSED;
        return;
    }

    if (selected_node_ >= 0 && nodes_[selected_node_].owner != NODE_PLAYER) {
        selected_node_ = -1;
    }

    // D-pad navigation among nodes
    if (keys_pressed & KEY_LEFT) MoveCursorDir(-1, 0);
    else if (keys_pressed & KEY_RIGHT) MoveCursorDir(1, 0);
    else if (keys_pressed & KEY_UP) MoveCursorDir(0, -1);
    else if (keys_pressed & KEY_DOWN) MoveCursorDir(0, 1);

    // KEY_A: select owned source node, or dispatch 50% to target node
    if (keys_pressed & KEY_A) {
        if (selected_node_ < 0) {
            if (nodes_[cursor_node_].owner == NODE_PLAYER) {
                selected_node_ = cursor_node_;
            }
        } else {
            if (cursor_node_ == selected_node_) {
                selected_node_ = -1;
            } else {
                if (nodes_[selected_node_].owner == NODE_PLAYER) {
                    DispatchFleet(selected_node_, cursor_node_);
                }
                selected_node_ = -1;
            }
        }
    }

    // KEY_B: cancel selection if on selected node, else dispatch 50% from all owned nodes to cursor_node_
    if (keys_pressed & KEY_B) {
        if (selected_node_ >= 0 && cursor_node_ == selected_node_) {
            selected_node_ = -1;
        } else {
            for (int i = 0; i < kNumNodes; ++i) {
                if (nodes_[i].owner == NODE_PLAYER && i != cursor_node_) {
                    DispatchFleet(i, cursor_node_);
                }
            }
            selected_node_ = -1;
        }
    }

    // Troop generation (+1.5/s on owned nodes, cap 50)
    for (int i = 0; i < kNumNodes; ++i) {
        if (nodes_[i].owner == NODE_PLAYER || nodes_[i].owner == NODE_AI) {
            nodes_[i].troops += 1.5f * dt;
            if (nodes_[i].troops > 50.0f) {
                nodes_[i].troops = 50.0f;
            }
        }
    }

    // AI decisions
    UpdateAI(dt);

    // Fleet movement and arrival resolution
    for (int f = 0; f < kMaxFleets; ++f) {
        if (!fleets_[f].active) continue;
        fleets_[f].x += fleets_[f].vx * dt;
        fleets_[f].y += fleets_[f].vy * dt;

        int dst = fleets_[f].target_node;
        float tx = (float)nodes_[dst].x + 0.5f;
        float ty = (float)nodes_[dst].y + 0.5f;
        float dx = tx - fleets_[f].x;
        float dy = ty - fleets_[f].y;
        if (dx * dx + dy * dy <= 0.45f * 0.45f) {
            fleets_[f].active = false;
            if (nodes_[dst].owner == fleets_[f].owner) {
                nodes_[dst].troops += fleets_[f].troops;
                if (nodes_[dst].troops > 50.0f) nodes_[dst].troops = 50.0f;
            } else {
                nodes_[dst].troops -= fleets_[f].troops;
                if (nodes_[dst].troops < 0.0f) {
                    nodes_[dst].owner = fleets_[f].owner;
                    nodes_[dst].troops = -nodes_[dst].troops;
                    if (nodes_[dst].troops > 50.0f) nodes_[dst].troops = 50.0f;
                    if (fleets_[f].owner == NODE_PLAYER) {
                        AddScore(50);
                    }
                }
            }
        }
    }

    // Victory / Gameover check
    int player_nodes = 0;
    int ai_nodes = 0;
    for (int i = 0; i < kNumNodes; ++i) {
        if (nodes_[i].owner == NODE_PLAYER) player_nodes++;
        else if (nodes_[i].owner == NODE_AI) ai_nodes++;
    }

    if (ai_nodes == 0) {
        AddScore(500);
        state_ = STATE_VICTORY;
        state_timer_ = 0.0f;
        return;
    }
    if (player_nodes == 0) {
        state_ = STATE_GAMEOVER;
        state_timer_ = 0.0f;
        return;
    }
}

void Game084NodeConquest::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    // Deep space tactical backdrop
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            uint8_t bg_b = (uint8_t)(16 + ((x * 5 + y * 3) % 10));
            SetPx84(fb_rgb24, x, y, 6, 10, bg_b);
        }
    }

    // Green halo around selected source node
    if (selected_node_ >= 0 && selected_node_ < kNumNodes) {
        int sx = nodes_[selected_node_].x;
        int sy = nodes_[selected_node_].y;
        for (int dy = -1; dy <= 2; ++dy) {
            for (int dx = -1; dx <= 2; ++dx) {
                if (dx == -1 || dx == 2 || dy == -1 || dy == 2) {
                    SetPx84(fb_rgb24, sx + dx, sy + dy, 40, 235, 90);
                }
            }
        }
    }

    // White/Gold cursor brackets around cursor_node_
    if (state_ == STATE_PLAYING || state_ == STATE_TITLE) {
        int cx = nodes_[cursor_node_].x;
        int cy = nodes_[cursor_node_].y;
        bool blink = (((int)(anim_timer_ * 6.0f)) % 2) == 0;
        if (blink) {
            SetPx84(fb_rgb24, cx - 1, cy - 1, 255, 230, 80);
            SetPx84(fb_rgb24, cx + 2, cy - 1, 255, 230, 80);
            SetPx84(fb_rgb24, cx - 1, cy + 2, 255, 230, 80);
            SetPx84(fb_rgb24, cx + 2, cy + 2, 255, 230, 80);
        }
    }

    // Render 7 2x2 nodes with brightness pulsing by troop count (1..50)
    for (int i = 0; i < kNumNodes; ++i) {
        float ratio = nodes_[i].troops / 50.0f;
        if (ratio < 0.0f) ratio = 0.0f;
        if (ratio > 1.0f) ratio = 1.0f;
        float pulse = 0.85f + 0.15f * sinf(anim_timer_ * (2.5f + ratio * 5.0f));
        float scale = (0.45f + 0.55f * ratio) * pulse;

        uint8_t nr = 140, ng = 145, nb = 155;
        if (nodes_[i].owner == NODE_PLAYER) {
            nr = 20; ng = 225; nb = 255;
        } else if (nodes_[i].owner == NODE_AI) {
            nr = 255; ng = 55; nb = 55;
        }

        uint8_t fr = (uint8_t)fminf(255.0f, (float)nr * scale);
        uint8_t fg = (uint8_t)fminf(255.0f, (float)ng * scale);
        uint8_t fb_c = (uint8_t)fminf(255.0f, (float)nb * scale);

        for (int dy = 0; dy < 2; ++dy) {
            for (int dx = 0; dx < 2; ++dx) {
                SetPx84(fb_rgb24, nodes_[i].x + dx, nodes_[i].y + dy, fr, fg, fb_c);
            }
        }
    }

    // Render flying fleets
    for (int f = 0; f < kMaxFleets; ++f) {
        if (!fleets_[f].active) continue;
        int fx = (int)roundf(fleets_[f].x);
        int fy = (int)roundf(fleets_[f].y);
        if (fleets_[f].owner == NODE_PLAYER) {
            SetPx84(fb_rgb24, fx, fy, 120, 250, 255);
        } else {
            SetPx84(fb_rgb24, fx, fy, 255, 130, 90);
        }
    }

    // Row 0 HUD: Player vs AI node balance bar
    int p_cnt = 0, a_cnt = 0;
    for (int i = 0; i < kNumNodes; ++i) {
        if (nodes_[i].owner == NODE_PLAYER) p_cnt++;
        else if (nodes_[i].owner == NODE_AI) a_cnt++;
    }
    for (int k = 0; k < p_cnt && k < 7; ++k) {
        SetPx84(fb_rgb24, k, 0, 0, 220, 255);
    }
    for (int k = 0; k < a_cnt && k < 7; ++k) {
        SetPx84(fb_rgb24, 15 - k, 0, 245, 50, 50);
    }

    if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPx84(fb_rgb24, 6, y, 250, 250, 250);
            SetPx84(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game084NodeConquest::GetStatus() const {
    int p_cnt = 0;
    for (int i = 0; i < kNumNodes; ++i) {
        if (nodes_[i].owner == NODE_PLAYER) p_cnt++;
    }
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = (uint8_t)p_cnt;
    st.state = (uint8_t)state_;
    st.progress = (uint8_t)((p_cnt * 100) / kNumNodes);
    return st;
}

static_assert(sizeof(Game084NodeConquest) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
