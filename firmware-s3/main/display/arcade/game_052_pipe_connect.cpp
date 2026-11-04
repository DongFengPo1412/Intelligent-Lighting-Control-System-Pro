// game_052_pipe_connect.cpp —— 目标 #052 管道旋转接水 (Pipe Connect) 核心实现
#include "game_052_pipe_connect.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>

namespace arcade {

namespace {

static const int kDX[4] = {0, 1, 0, -1};
static const int kDY[4] = {-1, 0, 1, 0};

// 初始关卡管件掩码 (每个关卡 (0,0) 为水源固定口, (4,4) 为排水口固定口)
// Stage 0: S弯折管路 (直管+弯头)
// 正确解: (0,0)=2 -> (1,0)=10 -> (2,0)=12 -> (2,1)=5 -> (2,2)=3 -> (3,2)=10 -> (4,2)=12 -> (4,3)=5 -> (4,4)=1
static const uint8_t kStageInit[Game052PipeConnect::kNumStages][5][5] = {
    {
        { 2,  5,  3, 10,  6},
        { 5,  6,  5, 12,  5},
        { 3, 10,  9, 10,  6},
        { 5,  9,  6,  5,  5},
        { 3, 10,  9, 10,  1},
    },
    // Stage 1: 十字立交桥环路 (含 CROSS=15 全端口闭合回路)
    // 正确解: (0,0)=4 -> (0,1)=5 -> (0,2)=3 -> (1,2)=10 -> (2,2)=15 -> (3,2)=9 -> (3,1)=12 -> (2,1)=6 -> (2,2)=15 -> (2,3)=3 -> (3,3)=10 -> (4,3)=12 -> (4,4)=1
    {
        { 4, 10,  6, 12,  6},
        {10,  3,  3,  9,  5},
        { 9, 10, 15,  6,  5},
        { 5,  6,  9,  5,  6},
        { 3, 10, 12, 10,  1},
    },
    // Stage 2: 三通双支路汇流 (含两个 TEE 分流与合流)
    // 正确解: (0,0)=2 -> (1,0)=14 -> 上路 (2,0)=10 -> (3,0)=12 -> (3,1)=5 -> (3,2)=5 -> (3,3)=11
    //                         -> 下路 (1,1)=5 -> (1,2)=5 -> (1,3)=3 -> (2,3)=10 -> (3,3)=11 -> (4,3)=12 -> (4,4)=1
    {
        { 2,  7,  5,  6, 12},
        { 6, 10,  6,  5,  5},
        { 5,  5, 10, 10,  5},
        { 3,  9, 10, 14,  6},
        { 3, 10,  9, 10,  1},
    },
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

uint8_t Game052PipeConnect::RotateMaskCW(uint8_t mask) {
    return (uint8_t)(((mask << 1) & 0x0Fu) | ((mask >> 3) & 0x01u));
}

Game052PipeConnect::Game052PipeConnect()
    : state_(STATE_TITLE),
      stage_(0),
      cursor_x_(1),
      cursor_y_(0),
      flow_active_(false),
      prep_countdown_(15.0f),
      flow_timer_(0.0f),
      flow_interval_(0.22f),
      score_(0),
      high_score_(0),
      state_timer_(0.0f),
      anim_timer_(0.0f) {
    memset(masks_, 0, sizeof(masks_));
    memset(fixed_, 0, sizeof(fixed_));
    memset(wet_preview_, 0, sizeof(wet_preview_));
    memset(flowing_, 0, sizeof(flowing_));
    LoadStage(0);
}

void Game052PipeConnect::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

void Game052PipeConnect::LoadStage(int stage_idx) {
    if (stage_idx < 0 || stage_idx >= kNumStages) stage_idx = 0;
    stage_ = stage_idx;
    for (int y = 0; y < kGridSize; ++y) {
        for (int x = 0; x < kGridSize; ++x) {
            masks_[y][x] = kStageInit[stage_][y][x];
            fixed_[y][x] = false;
            flowing_[y][x] = false;
        }
    }
    fixed_[0][0] = true;
    fixed_[4][4] = true;
    cursor_x_ = 1;
    cursor_y_ = 0;
    flow_active_ = false;
    prep_countdown_ = 15.0f;
    flow_timer_ = 0.0f;
    flow_interval_ = 0.22f;
    RecomputeWetPreview();
}

void Game052PipeConnect::RecomputeWetPreview() {
    memset(wet_preview_, 0, sizeof(wet_preview_));
    int qx[25];
    int qy[25];
    int head = 0;
    int tail = 0;
    wet_preview_[0][0] = true;
    qx[tail] = 0;
    qy[tail] = 0;
    tail++;

    while (head < tail) {
        int cx = qx[head];
        int cy = qy[head];
        head++;
        uint8_t m = masks_[cy][cx];
        for (int d = 0; d < 4; ++d) {
            if ((m & (1u << d)) == 0) continue;
            int nx = cx + kDX[d];
            int ny = cy + kDY[d];
            if (nx < 0 || nx >= kGridSize || ny < 0 || ny >= kGridSize) continue;
            int opp = (d + 2) & 3;
            if ((masks_[ny][nx] & (1u << opp)) != 0 && !wet_preview_[ny][nx]) {
                wet_preview_[ny][nx] = true;
                qx[tail] = nx;
                qy[tail] = ny;
                tail++;
            }
        }
    }
}

void Game052PipeConnect::StepWaterFlow() {
    bool next_flowing[kGridSize][kGridSize];
    memcpy(next_flowing, flowing_, sizeof(flowing_));
    bool leak = false;
    int newly_wet = 0;

    for (int y = 0; y < kGridSize; ++y) {
        for (int x = 0; x < kGridSize; ++x) {
            if (!flowing_[y][x]) continue;
            uint8_t m = masks_[y][x];
            for (int d = 0; d < 4; ++d) {
                if ((m & (1u << d)) == 0) continue;
                int nx = x + kDX[d];
                int ny = y + kDY[d];
                if (nx < 0 || nx >= kGridSize || ny < 0 || ny >= kGridSize) {
                    leak = true;
                    continue;
                }
                int opp = (d + 2) & 3;
                if ((masks_[ny][nx] & (1u << opp)) == 0) {
                    leak = true;
                    continue;
                }
                if (!next_flowing[ny][nx]) {
                    next_flowing[ny][nx] = true;
                    newly_wet++;
                }
            }
        }
    }

    memcpy(flowing_, next_flowing, sizeof(flowing_));

    if (leak) {
        state_ = STATE_GAMEOVER;
        state_timer_ = 0.0f;
        return;
    }

    if (flowing_[4][4]) {
        // 验证终点自身无悬空漏口后通关本关
        AddScore(200u);
        if (stage_ + 1 < kNumStages) {
            LoadStage(stage_ + 1);
        } else {
            state_ = STATE_VICTORY;
            state_timer_ = 0.0f;
        }
        return;
    }

    if (newly_wet == 0) {
        // 死循环未到达排水口
        state_ = STATE_GAMEOVER;
        state_timer_ = 0.0f;
    }
}

void Game052PipeConnect::Init() {
    Reset();
}

void Game052PipeConnect::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    state_ = STATE_TITLE;
    score_ = 0;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    LoadStage(0);
}

void Game052PipeConnect::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        state_ = STATE_PLAYING;
        score_ = 0;
        state_timer_ = 0.0f;
        anim_timer_ = 0.0f;
        LoadStage(0);
    }
}

void Game052PipeConnect::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game052PipeConnect::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

void Game052PipeConnect::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
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
            if (cursor_x_ > 0) cursor_x_--;
        } else if (keys_pressed & KEY_RIGHT) {
            if (cursor_x_ < kGridSize - 1) cursor_x_++;
        } else if (keys_pressed & KEY_UP) {
            if (cursor_y_ > 0) cursor_y_--;
        } else if (keys_pressed & KEY_DOWN) {
            if (cursor_y_ < kGridSize - 1) cursor_y_++;
        }

        // KEY_A 顺时针旋转未进水且非固定的管件
        if (keys_pressed & KEY_A) {
            if (!fixed_[cursor_y_][cursor_x_] && !flowing_[cursor_y_][cursor_x_]) {
                masks_[cursor_y_][cursor_x_] = RotateMaskCW(masks_[cursor_y_][cursor_x_]);
                RecomputeWetPreview();
            }
        }

        // KEY_B 立即高速放水
        if (keys_pressed & KEY_B) {
            if (!flow_active_) {
                flow_active_ = true;
                prep_countdown_ = 0.0f;
                flowing_[0][0] = true;
                flow_timer_ = 0.0f;
            }
            flow_interval_ = 0.06f;
        }

        if (!flow_active_) {
            prep_countdown_ -= dt;
            if (prep_countdown_ <= 0.0f) {
                prep_countdown_ = 0.0f;
                flow_active_ = true;
                flowing_[0][0] = true;
                flow_timer_ = 0.0f;
            }
        } else {
            flow_timer_ += dt;
            while (flow_timer_ >= flow_interval_ && state_ == STATE_PLAYING && flow_active_) {
                flow_timer_ -= flow_interval_;
                StepWaterFlow();
            }
        }
    }
}

void Game052PipeConnect::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    // 工业深灰底色
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            SetPx(fb_rgb24, x, y, 16, 20, 28);
        }
    }

    // 顶部 y=0 倒计时水压条 (0..14)
    int bar_len = (int)((prep_countdown_ / 15.0f) * 15.0f + 0.5f);
    for (int x = 0; x < 15; ++x) {
        if (flow_active_) {
            SetPx(fb_rgb24, x, 0, 0, 220, 255);
        } else if (x < bar_len) {
            SetPx(fb_rgb24, x, 0, 245, 180, 25);
        } else {
            SetPx(fb_rgb24, x, 0, 35, 40, 50);
        }
    }

    // 右侧 x=15 关卡进度灯
    for (int s = 0; s < kNumStages; ++s) {
        int py = 3 + s * 4;
        if (s < stage_) {
            SetPx(fb_rgb24, 15, py, 46, 215, 100);
        } else if (s == stage_) {
            SetPx(fb_rgb24, 15, py, 255, 215, 35);
        } else {
            SetPx(fb_rgb24, 15, py, 50, 55, 68);
        }
    }

    // 绘制 5x5 管件 (每格 3x3 像素: x=gx*3, y=1+gy*3)
    for (int gy = 0; gy < kGridSize; ++gy) {
        for (int gx = 0; gx < kGridSize; ++gx) {
            int px0 = gx * 3;
            int py0 = 1 + gy * 3;
            uint8_t m = masks_[gy][gx];
            if (m == 0) continue;

            uint8_t r = 115, g = 126, b = 138;
            if (flowing_[gy][gx]) {
                r = 90; g = 255; b = 255;
            } else if (wet_preview_[gy][gx]) {
                r = 0; g = 195; b = 245;
            }
            if (gx == 0 && gy == 0) {
                r = 35; g = 235; b = 140; // 水源绿青色
            } else if (gx == 4 && gy == 4) {
                if (flowing_[4][4] || wet_preview_[4][4]) {
                    r = 80; g = 255; b = 160;
                } else {
                    r = 245; g = 165, b = 25; // 排水口琥珀金
                }
            }

            // 中心节点 + 四个方向臂 (3x3 清晰呈现 | - L T +)
            SetPx(fb_rgb24, px0 + 1, py0 + 1, r, g, b);
            if (m & kPortUp)    SetPx(fb_rgb24, px0 + 1, py0 + 0, r, g, b);
            if (m & kPortRight) SetPx(fb_rgb24, px0 + 2, py0 + 1, r, g, b);
            if (m & kPortDown)  SetPx(fb_rgb24, px0 + 1, py0 + 2, r, g, b);
            if (m & kPortLeft)  SetPx(fb_rgb24, px0 + 0, py0 + 1, r, g, b);
        }
    }

    // 游标四角高亮 (在 3x3 格的四角闪烁，不遮挡中心十字管路!)
    if (state_ == STATE_PLAYING || state_ == STATE_TITLE) {
        bool blink = ((int)(anim_timer_ * 6.0f) % 2) == 0;
        if (blink) {
            int cx0 = cursor_x_ * 3;
            int cy0 = 1 + cursor_y_ * 3;
            SetPx(fb_rgb24, cx0, cy0, 255, 255, 100);
            SetPx(fb_rgb24, cx0 + 2, cy0, 255, 255, 100);
            SetPx(fb_rgb24, cx0, cy0 + 2, 255, 255, 100);
            SetPx(fb_rgb24, cx0 + 2, cy0 + 2, 255, 255, 100);
        }
    }

    if (state_ == STATE_GAMEOVER) {
        for (int x = 0; x < 16; ++x) {
            SetPx(fb_rgb24, x, 0, 240, 50, 45);
        }
    } else if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPx(fb_rgb24, 6, y, 250, 250, 250);
            SetPx(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game052PipeConnect::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = (state_ == STATE_GAMEOVER) ? 0 : 1;
    st.state = (uint8_t)state_;
    int prog = stage_ * 33 + (wet_preview_[4][4] ? 20 : 0);
    if (state_ == STATE_VICTORY) prog = 100;
    st.progress = (uint8_t)(prog > 100 ? 100 : prog);
    return st;
}

static_assert(sizeof(Game052PipeConnect) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
