// game_051_flow_free.cpp —— 目标 #051 同色连线 (Flow Free) 核心实现
#include "game_051_flow_free.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>
#include <math.h>

namespace arcade {

namespace {

struct StageSpec {
    FlowPoint ep[Game051FlowFree::kNumColors][2];
};

// 4 个手工精制 6x6 全覆盖可解关卡 (每关均可 36 格 100% 哈密顿分割连通)
static const StageSpec kStages[Game051FlowFree::kNumStages] = {
    // Stage 0: 嵌套 L 形走廊
    {{
        {{0, 0}, {5, 2}}, // Red
        {{0, 1}, {4, 3}}, // Green
        {{0, 2}, {5, 3}}, // Blue
        {{2, 3}, {5, 5}}, // Yellow
    }},
    // Stage 1: 风车螺旋
    {{
        {{0, 5}, {3, 0}}, // Red
        {{4, 0}, {3, 5}}, // Green
        {{2, 5}, {4, 1}}, // Blue
        {{4, 2}, {2, 4}}, // Yellow
    }},
    // Stage 2: 纵向编织 (Stage 0 转置)
    {{
        {{0, 0}, {2, 5}}, // Red
        {{1, 0}, {3, 4}}, // Green
        {{2, 0}, {3, 5}}, // Blue
        {{3, 2}, {5, 5}}, // Yellow
    }},
    // Stage 3: 镜像风车螺旋
    {{
        {{5, 5}, {2, 0}}, // Red
        {{1, 0}, {2, 5}}, // Green
        {{3, 5}, {1, 1}}, // Blue
        {{1, 2}, {3, 4}}, // Yellow
    }},
};

static const uint8_t kEndpointRGB[4][3] = {
    {255, 75, 65},   // Red
    {60, 235, 110},  // Green
    {70, 180, 255},  // Blue
    {255, 225, 45},  // Yellow
};

static const uint8_t kWireRGB[4][3] = {
    {185, 45, 40},   // Red wire
    {34, 160, 74},   // Green wire
    {38, 118, 195},  // Blue wire
    {190, 155, 20},  // Yellow wire
};

static inline void SetPx(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

} // namespace

Game051FlowFree::Game051FlowFree()
    : state_(STATE_TITLE),
      stage_(0),
      cursor_x_(0),
      cursor_y_(0),
      active_color_(-1),
      drawing_(false),
      moves_(0),
      score_(0),
      high_score_(0),
      state_timer_(0.0f),
      anim_timer_(0.0f) {
    memset(endpoints_, 0, sizeof(endpoints_));
    memset(paths_, 0, sizeof(paths_));
    memset(path_len_, 0, sizeof(path_len_));
    LoadStage(0);
}

void Game051FlowFree::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

void Game051FlowFree::LoadStage(int stage_idx) {
    if (stage_idx < 0 || stage_idx >= kNumStages) stage_idx = 0;
    stage_ = stage_idx;
    for (int c = 0; c < kNumColors; ++c) {
        endpoints_[c][0] = kStages[stage_].ep[c][0];
        endpoints_[c][1] = kStages[stage_].ep[c][1];
        path_len_[c] = 0;
    }
    cursor_x_ = endpoints_[0][0].x;
    cursor_y_ = endpoints_[0][0].y;
    active_color_ = -1;
    drawing_ = false;
}

int Game051FlowFree::EndpointColorAt(int x, int y) const {
    for (int c = 0; c < kNumColors; ++c) {
        if ((endpoints_[c][0].x == x && endpoints_[c][0].y == y) ||
            (endpoints_[c][1].x == x && endpoints_[c][1].y == y)) {
            return c;
        }
    }
    return -1;
}

int Game051FlowFree::WireColorAt(int x, int y, int* out_seg_idx) const {
    for (int c = 0; c < kNumColors; ++c) {
        for (int i = 0; i < path_len_[c]; ++i) {
            if (paths_[c][i].x == x && paths_[c][i].y == y) {
                if (out_seg_idx) *out_seg_idx = i;
                return c;
            }
        }
    }
    return -1;
}

bool Game051FlowFree::IsColorConnected(int color) const {
    if (color < 0 || color >= kNumColors) return false;
    int len = path_len_[color];
    if (len < 2) return false;
    const FlowPoint& p0 = paths_[color][0];
    const FlowPoint& p1 = paths_[color][len - 1];
    const FlowPoint& e0 = endpoints_[color][0];
    const FlowPoint& e1 = endpoints_[color][1];
    return ((p0.x == e0.x && p0.y == e0.y && p1.x == e1.x && p1.y == e1.y) ||
            (p0.x == e1.x && p0.y == e1.y && p1.x == e0.x && p1.y == e0.y));
}

int Game051FlowFree::CountConnectedColors() const {
    int cnt = 0;
    for (int c = 0; c < kNumColors; ++c) {
        if (IsColorConnected(c)) cnt++;
    }
    return cnt;
}

int Game051FlowFree::CountCoveredCells() const {
    bool used[kGridSize][kGridSize];
    memset(used, 0, sizeof(used));
    for (int c = 0; c < kNumColors; ++c) {
        used[endpoints_[c][0].y][endpoints_[c][0].x] = true;
        used[endpoints_[c][1].y][endpoints_[c][1].x] = true;
        for (int i = 0; i < path_len_[c]; ++i) {
            int px = paths_[c][i].x;
            int py = paths_[c][i].y;
            if (px >= 0 && px < kGridSize && py >= 0 && py < kGridSize) {
                used[py][px] = true;
            }
        }
    }
    int total = 0;
    for (int y = 0; y < kGridSize; ++y) {
        for (int x = 0; x < kGridSize; ++x) {
            if (used[y][x]) total++;
        }
    }
    return total;
}

void Game051FlowFree::CheckStageClear() {
    if (CountConnectedColors() == kNumColors) {
        uint32_t bonus = (CountCoveredCells() == kGridCells) ? 100u : 0u;
        AddScore(200u + bonus);
        drawing_ = false;
        active_color_ = -1;
        if (stage_ + 1 < kNumStages) {
            LoadStage(stage_ + 1);
        } else {
            state_ = STATE_VICTORY;
            state_timer_ = 0.0f;
        }
    }
}

void Game051FlowFree::Init() {
    Reset();
}

void Game051FlowFree::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    state_ = STATE_TITLE;
    moves_ = 0;
    score_ = 0;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    LoadStage(0);
}

void Game051FlowFree::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        state_ = STATE_PLAYING;
        moves_ = 0;
        score_ = 0;
        state_timer_ = 0.0f;
        anim_timer_ = 0.0f;
        LoadStage(0);
    }
}

void Game051FlowFree::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game051FlowFree::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

void Game051FlowFree::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
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

        if (keys_pressed & KEY_SELECT) {
            LoadStage(stage_);
            return;
        }

        if (keys_pressed & KEY_B) {
            if (drawing_ && active_color_ >= 0) {
                path_len_[active_color_] = 0;
                drawing_ = false;
                active_color_ = -1;
            } else {
                int seg = -1;
                int wc = WireColorAt(cursor_x_, cursor_y_, &seg);
                int ec = EndpointColorAt(cursor_x_, cursor_y_);
                int target_c = (wc >= 0) ? wc : ec;
                if (target_c >= 0 && path_len_[target_c] > 0) {
                    path_len_[target_c] = 0;
                } else {
                    LoadStage(stage_);
                }
            }
            return;
        }

        if (keys_pressed & KEY_A) {
            if (drawing_) {
                drawing_ = false;
                active_color_ = -1;
            } else {
                int ec = EndpointColorAt(cursor_x_, cursor_y_);
                int seg = -1;
                int wc = WireColorAt(cursor_x_, cursor_y_, &seg);
                if (ec >= 0) {
                    paths_[ec][0] = {cursor_x_, cursor_y_};
                    path_len_[ec] = 1;
                    active_color_ = ec;
                    drawing_ = true;
                } else if (wc >= 0 && seg >= 0) {
                    path_len_[wc] = seg + 1;
                    active_color_ = wc;
                    drawing_ = true;
                }
            }
            return;
        }

        int dx = 0;
        int dy = 0;
        if (keys_pressed & KEY_UP) dy = -1;
        else if (keys_pressed & KEY_DOWN) dy = 1;
        else if (keys_pressed & KEY_LEFT) dx = -1;
        else if (keys_pressed & KEY_RIGHT) dx = 1;

        if (dx != 0 || dy != 0) {
            int nx = cursor_x_ + dx;
            int ny = cursor_y_ + dy;
            if (nx < 0 || nx >= kGridSize || ny < 0 || ny >= kGridSize) {
                return;
            }

            if (!drawing_ || active_color_ < 0) {
                cursor_x_ = nx;
                cursor_y_ = ny;
                return;
            }

            int c = active_color_;
            int ep_c = EndpointColorAt(nx, ny);
            // 不能覆盖其他颜色的端点
            if (ep_c >= 0 && ep_c != c) {
                return;
            }

            // 检查是否回退到自身导线上
            int own_idx = -1;
            for (int i = 0; i < path_len_[c]; ++i) {
                if (paths_[c][i].x == nx && paths_[c][i].y == ny) {
                    own_idx = i;
                    break;
                }
            }
            if (own_idx >= 0) {
                path_len_[c] = own_idx + 1;
                cursor_x_ = nx;
                cursor_y_ = ny;
                moves_++;
                return;
            }

            // 若当前导线已连到终点，则不允许继续越过终点延伸
            if (IsColorConnected(c)) {
                drawing_ = false;
                active_color_ = -1;
                return;
            }

            // 若踩到其他颜色的已有导线，截断/清除该异色导线
            int other_seg = -1;
            int other_c = WireColorAt(nx, ny, &other_seg);
            if (other_c >= 0 && other_c != c) {
                path_len_[other_c] = 0;
            }

            if (path_len_[c] < kGridCells) {
                paths_[c][path_len_[c]] = {nx, ny};
                path_len_[c]++;
                cursor_x_ = nx;
                cursor_y_ = ny;
                moves_++;

                if (IsColorConnected(c)) {
                    drawing_ = false;
                    active_color_ = -1;
                    CheckStageClear();
                }
            }
        }
    }
}

void Game051FlowFree::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    // 深蓝边框背景 + 6x6 棋盘底纹
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (x >= 2 && x <= 13 && y >= 2 && y <= 13) {
                int gx = (x - 2) / 2;
                int gy = (y - 2) / 2;
                uint8_t base = ((gx + gy) & 1) ? 24 : 18;
                SetPx(fb_rgb24, x, y, base, base + 4, base + 10);
            } else {
                SetPx(fb_rgb24, x, y, 10, 14, 24);
            }
        }
    }

    // 顶部关卡进度指示灯 (y=0)
    for (int s = 0; s < kNumStages; ++s) {
        int px = 4 + s * 2 + (s >= 2 ? 1 : 0);
        if (s < stage_) {
            SetPx(fb_rgb24, px, 0, 46, 215, 100);
        } else if (s == stage_) {
            SetPx(fb_rgb24, px, 0, 255, 215, 40);
        } else {
            SetPx(fb_rgb24, px, 0, 45, 55, 70);
        }
    }

    // 绘制已铺设导线 (2x2 格)
    for (int c = 0; c < kNumColors; ++c) {
        for (int i = 0; i < path_len_[c]; ++i) {
            int px = 2 + paths_[c][i].x * 2;
            int py = 2 + paths_[c][i].y * 2;
            for (int dy = 0; dy < 2; ++dy) {
                for (int dx = 0; dx < 2; ++dx) {
                    SetPx(fb_rgb24, px + dx, py + dy, kWireRGB[c][0], kWireRGB[c][1], kWireRGB[c][2]);
                }
            }
        }
    }

    // 绘制 4 对彩色端点 (带高光圆点感)
    for (int c = 0; c < kNumColors; ++c) {
        for (int k = 0; k < 2; ++k) {
            int px = 2 + endpoints_[c][k].x * 2;
            int py = 2 + endpoints_[c][k].y * 2;
            for (int dy = 0; dy < 2; ++dy) {
                for (int dx = 0; dx < 2; ++dx) {
                    uint8_t r = kEndpointRGB[c][0];
                    uint8_t g = kEndpointRGB[c][1];
                    uint8_t b = kEndpointRGB[c][2];
                    if (dx == 0 && dy == 0) {
                        r = (r + 255) >> 1;
                        g = (g + 255) >> 1;
                        b = (b + 255) >> 1;
                    }
                    SetPx(fb_rgb24, px + dx, py + dy, r, g, b);
                }
            }
        }
        // 底部颜色配对完成状态灯 (y=15)
        int bx = 4 + c * 2 + (c >= 2 ? 1 : 0);
        if (IsColorConnected(c)) {
            SetPx(fb_rgb24, bx, 15, kEndpointRGB[c][0], kEndpointRGB[c][1], kEndpointRGB[c][2]);
        } else {
            SetPx(fb_rgb24, bx, 15, kWireRGB[c][0] / 3, kWireRGB[c][1] / 3, kWireRGB[c][2] / 3);
        }
    }

    // 光标闪烁渲染
    if (state_ == STATE_PLAYING || state_ == STATE_TITLE) {
        bool blink = ((int)(anim_timer_ * 6.0f) % 2) == 0;
        int cpx = 2 + cursor_x_ * 2;
        int cpy = 2 + cursor_y_ * 2;
        if (drawing_ && active_color_ >= 0) {
            SetPx(fb_rgb24, cpx, cpy, 255, 255, 255);
            SetPx(fb_rgb24, cpx + 1, cpy + 1, 255, 255, 255);
        } else if (blink) {
            SetPx(fb_rgb24, cpx + 1, cpy, 255, 255, 255);
            SetPx(fb_rgb24, cpx, cpy + 1, 255, 255, 255);
        }
    }

    if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPx(fb_rgb24, 6, y, 250, 250, 250);
            SetPx(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game051FlowFree::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = 1;
    st.state = (uint8_t)state_;
    int prog = stage_ * 25 + (CountConnectedColors() * 25) / kNumColors;
    if (state_ == STATE_VICTORY) prog = 100;
    st.progress = (uint8_t)(prog > 100 ? 100 : prog);
    return st;
}

static_assert(sizeof(Game051FlowFree) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
