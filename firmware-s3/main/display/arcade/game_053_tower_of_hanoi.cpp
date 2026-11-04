// game_053_tower_of_hanoi.cpp —— 目标 #053 汉诺塔 (Tower of Hanoi) 核心实现
#include "game_053_tower_of_hanoi.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>

namespace arcade {

namespace {

static const int kPegX[Game053TowerOfHanoi::kNumPegs] = {2, 7, 12};

// 盘片尺寸 1..5 彩虹配色: 红 / 橙 / 绿 / 蓝 / 紫
static const uint8_t kDiskRGB[6][3] = {
    {0, 0, 0},
    {255, 65, 60},   // Size 1: Red
    {255, 160, 25},  // Size 2: Orange
    {50, 225, 95},   // Size 3: Green
    {55, 175, 255},  // Size 4: Blue
    {195, 85, 255},  // Size 5: Violet
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

Game053TowerOfHanoi::Game053TowerOfHanoi()
    : state_(STATE_TITLE),
      stage_(0),
      num_disks_(4),
      cursor_peg_(0),
      held_disk_(0),
      held_from_peg_(-1),
      moves_(0),
      score_(0),
      high_score_(0),
      error_timer_(0.0f),
      state_timer_(0.0f),
      anim_timer_(0.0f) {
    memset(pegs_, 0, sizeof(pegs_));
    memset(peg_count_, 0, sizeof(peg_count_));
    LoadStage(0);
}

void Game053TowerOfHanoi::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

void Game053TowerOfHanoi::LoadStage(int stage_idx) {
    if (stage_idx < 0 || stage_idx >= kNumStages) stage_idx = 0;
    stage_ = stage_idx;
    num_disks_ = (stage_ == 0) ? 4 : 5;
    memset(pegs_, 0, sizeof(pegs_));
    memset(peg_count_, 0, sizeof(peg_count_));

    for (int i = 0; i < num_disks_; ++i) {
        pegs_[0][i] = num_disks_ - i; // 底部最大，顶部最小 (1)
    }
    peg_count_[0] = num_disks_;
    peg_count_[1] = 0;
    peg_count_[2] = 0;

    cursor_peg_ = 0;
    held_disk_ = 0;
    held_from_peg_ = -1;
    moves_ = 0;
    error_timer_ = 0.0f;
}

void Game053TowerOfHanoi::Init() {
    Reset();
}

void Game053TowerOfHanoi::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    state_ = STATE_TITLE;
    score_ = 0;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    LoadStage(0);
}

void Game053TowerOfHanoi::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        state_ = STATE_PLAYING;
        score_ = 0;
        state_timer_ = 0.0f;
        anim_timer_ = 0.0f;
        LoadStage(0);
    }
}

void Game053TowerOfHanoi::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game053TowerOfHanoi::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

void Game053TowerOfHanoi::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
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

        if (error_timer_ > 0.0f) {
            error_timer_ -= dt;
            if (error_timer_ < 0.0f) error_timer_ = 0.0f;
        }

        if (keys_pressed & KEY_SELECT) {
            LoadStage(stage_);
            return;
        }

        if (keys_pressed & KEY_LEFT) {
            if (cursor_peg_ > 0) cursor_peg_--;
        } else if (keys_pressed & KEY_RIGHT) {
            if (cursor_peg_ < kNumPegs - 1) cursor_peg_++;
        }

        if (held_disk_ == 0) {
            if (keys_pressed & KEY_A) {
                if (peg_count_[cursor_peg_] > 0) {
                    peg_count_[cursor_peg_]--;
                    held_disk_ = pegs_[cursor_peg_][peg_count_[cursor_peg_]];
                    pegs_[cursor_peg_][peg_count_[cursor_peg_]] = 0;
                    held_from_peg_ = cursor_peg_;
                }
            }
        } else {
            if (keys_pressed & (KEY_A | KEY_B)) {
                int top_cnt = peg_count_[cursor_peg_];
                bool can_drop = (top_cnt == 0) || (held_disk_ < pegs_[cursor_peg_][top_cnt - 1]);
                if (!can_drop) {
                    error_timer_ = 0.30f;
                } else {
                    pegs_[cursor_peg_][top_cnt] = held_disk_;
                    peg_count_[cursor_peg_]++;
                    if (cursor_peg_ != held_from_peg_) {
                        moves_++;
                    }
                    held_disk_ = 0;
                    held_from_peg_ = -1;

                    if (peg_count_[2] == num_disks_) {
                        int optimal = (1 << num_disks_) - 1;
                        int extra = ((int)moves_ > optimal) ? ((int)moves_ - optimal) : 0;
                        int stage_pts = 500 - extra * 5;
                        if (stage_pts < 100) stage_pts = 100;
                        AddScore((uint32_t)stage_pts);

                        if (stage_ + 1 < kNumStages) {
                            LoadStage(stage_ + 1);
                        } else {
                            state_ = STATE_VICTORY;
                            state_timer_ = 0.0f;
                        }
                    }
                }
            }
        }
    }
}

void Game053TowerOfHanoi::DrawDisk(uint8_t* fb, int cx, int y, int disk_size, bool highlight_err) const {
    if (disk_size < 1 || disk_size > kMaxDisks) return;
    uint8_t r = highlight_err ? 255 : kDiskRGB[disk_size][0];
    uint8_t g = highlight_err ? 35  : kDiskRGB[disk_size][1];
    uint8_t b = highlight_err ? 35  : kDiskRGB[disk_size][2];

    if (disk_size == 1) {
        SetPx(fb, cx, y, r, g, b);
    } else if (disk_size == 2) {
        SetPx(fb, cx - 1, y, r / 2, g / 2, b / 2);
        SetPx(fb, cx, y, r, g, b);
        SetPx(fb, cx + 1, y, r / 2, g / 2, b / 2);
    } else if (disk_size == 3) {
        for (int dx = -1; dx <= 1; ++dx) {
            SetPx(fb, cx + dx, y, r, g, b);
        }
    } else if (disk_size == 4) {
        SetPx(fb, cx - 2, y, r / 2, g / 2, b / 2);
        for (int dx = -1; dx <= 1; ++dx) {
            SetPx(fb, cx + dx, y, r, g, b);
        }
        SetPx(fb, cx + 2, y, r / 2, g / 2, b / 2);
    } else {
        for (int dx = -2; dx <= 2; ++dx) {
            SetPx(fb, cx + dx, y, r, g, b);
        }
    }
}

void Game053TowerOfHanoi::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    // 夜空渐变底色
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            SetPx(fb_rgb24, x, y, 12, 16 + y, 30 + y);
        }
    }

    // 违例放置红光警示条
    if (error_timer_ > 0.0f) {
        for (int x = 0; x < 16; ++x) {
            SetPx(fb_rgb24, x, 0, 245, 30, 30);
        }
    } else {
        // 右上角关卡指示点 (x=15)
        SetPx(fb_rgb24, 15, 0, (stage_ >= 1) ? 46 : 255, 215, 60);
        SetPx(fb_rgb24, 15, 1, (stage_ >= 1) ? 255 : 50, (stage_ >= 1) ? 215 : 55, 65);
    }

    // 底座木台 (y=14..15)
    for (int x = 0; x < 15; ++x) {
        SetPx(fb_rgb24, x, 14, 155, 105, 55);
        SetPx(fb_rgb24, x, 15, 110, 72, 36);
    }

    // 三根立柱 (x=2, 7, 12; y=6..13), 目标柱 Peg 2 微泛金光
    for (int p = 0; p < kNumPegs; ++p) {
        int px = kPegX[p];
        for (int y = 6; y <= 13; ++y) {
            if (p == 2) {
                SetPx(fb_rgb24, px, y, 175, 155, 90);
            } else {
                SetPx(fb_rgb24, px, y, 110, 120, 138);
            }
        }
    }

    // 各柱已堆叠盘片 (y=13 向上堆叠)
    for (int p = 0; p < kNumPegs; ++p) {
        int cx = kPegX[p];
        for (int i = 0; i < peg_count_[p]; ++i) {
            int y = 13 - i;
            DrawDisk(fb_rgb24, cx, y, pegs_[p][i], false);
        }
    }

    // 顶部选择器光标 (y=0..1) 与悬空抓取盘片 (y=2)
    int sel_x = kPegX[cursor_peg_];
    bool err_flash = (error_timer_ > 0.0f);
    SetPx(fb_rgb24, sel_x, 0, 255, 245, 180);
    SetPx(fb_rgb24, sel_x - 1, 0, 180, 175, 120);
    SetPx(fb_rgb24, sel_x + 1, 0, 180, 175, 120);
    SetPx(fb_rgb24, sel_x, 1, 255, 255, 255);

    if (held_disk_ > 0) {
        DrawDisk(fb_rgb24, sel_x, 2, held_disk_, err_flash);
    }

    if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPx(fb_rgb24, 6, y, 250, 250, 250);
            SetPx(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game053TowerOfHanoi::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = 1;
    st.state = (uint8_t)state_;
    int prog = stage_ * 50 + (peg_count_[2] * 50) / num_disks_;
    if (state_ == STATE_VICTORY) prog = 100;
    st.progress = (uint8_t)(prog > 100 ? 100 : prog);
    return st;
}

static_assert(sizeof(Game053TowerOfHanoi) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
