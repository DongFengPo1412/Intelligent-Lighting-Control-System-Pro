// game_019_shell_game.cpp —— 目标 #019 猜球杯 (Shell Shuffle) 核心实现
#include "game_019_shell_game.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>
#include <math.h>

namespace arcade {

static const float kPi = 3.1415926f;

static inline void SetPixel19(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

Game019ShellGame::Game019ShellGame()
    : state_(STATE_TITLE),
      phase_(SHELL_REVEAL),
      round_(1),
      num_cups_(3),
      pearl_slot_(1),
      cursor_slot_(1),
      chosen_slot_(-1),
      lives_(3),
      reveal_timer_(0.90f),
      swaps_total_(4),
      swaps_done_(0),
      swap_dur_(0.40f),
      swap_t_(0.0f),
      swap_a_(0),
      swap_b_(1),
      score_(0),
      high_score_(0),
      rng_seed_(0x19198001u),
      state_timer_(0.0f),
      anim_timer_(0.0f) {
}

uint32_t Game019ShellGame::NextRand() {
    rng_seed_ = rng_seed_ * 1103515245u + 12345u;
    return (rng_seed_ >> 16) & 0x7FFFu;
}

void Game019ShellGame::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

float Game019ShellGame::GetSlotX(int slot) const {
    if (num_cups_ == 4) {
        static const float kSlot4[4] = {1.0f, 5.0f, 9.0f, 13.0f};
        if (slot < 0) slot = 0;
        if (slot > 3) slot = 3;
        return kSlot4[slot];
    } else {
        static const float kSlot3[3] = {1.0f, 6.0f, 11.0f};
        if (slot < 0) slot = 0;
        if (slot > 2) slot = 2;
        return kSlot3[slot];
    }
}

void Game019ShellGame::BeginNextSwap() {
    swap_a_ = (int)(NextRand() % num_cups_);
    swap_b_ = (swap_a_ + 1 + (int)(NextRand() % (num_cups_ - 1))) % num_cups_;
    swap_t_ = 0.0f;
}

void Game019ShellGame::SetupRound() {
    num_cups_ = (round_ >= 4) ? 4 : 3;
    pearl_slot_ = (int)(NextRand() % num_cups_);
    cursor_slot_ = num_cups_ / 2;
    chosen_slot_ = -1;
    phase_ = SHELL_REVEAL;
    reveal_timer_ = 0.90f;
    swaps_total_ = 4 + ((round_ - 1) * 8) / 7;
    if (swaps_total_ > 12) swaps_total_ = 12;
    swaps_done_ = 0;
    swap_dur_ = 0.40f - (float)(round_ - 1) * 0.032f;
    if (swap_dur_ < 0.16f) swap_dur_ = 0.16f;
    swap_t_ = 0.0f;
    swap_a_ = 0;
    swap_b_ = 1;
}

void Game019ShellGame::Init() {
    Reset();
}

void Game019ShellGame::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    state_ = STATE_TITLE;
    round_ = 1;
    lives_ = 3;
    score_ = 0;
    rng_seed_ = 0x19198001u;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    SetupRound();
}

void Game019ShellGame::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        state_ = STATE_PLAYING;
        round_ = 1;
        lives_ = 3;
        score_ = 0;
        rng_seed_ = 0x19198001u;
        state_timer_ = 0.0f;
        anim_timer_ = 0.0f;
        SetupRound();
    }
}

void Game019ShellGame::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game019ShellGame::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

void Game019ShellGame::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt < 0.0f) dt = 0.0f;
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
        if (state_timer_ > 0.5f && (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT))) {
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

        if (phase_ == SHELL_REVEAL) {
            reveal_timer_ -= dt;
            if (reveal_timer_ <= 0.0f) {
                reveal_timer_ = 0.0f;
                phase_ = SHELL_SHUFFLE;
                swaps_done_ = 0;
                BeginNextSwap();
            }
            return;
        }

        if (phase_ == SHELL_SHUFFLE) {
            swap_t_ += dt / swap_dur_;
            while (swap_t_ >= 1.0f && phase_ == SHELL_SHUFFLE) {
                if (pearl_slot_ == swap_a_) {
                    pearl_slot_ = swap_b_;
                } else if (pearl_slot_ == swap_b_) {
                    pearl_slot_ = swap_a_;
                }
                swaps_done_++;
                if (swaps_done_ >= swaps_total_) {
                    phase_ = SHELL_GUESS;
                    cursor_slot_ = num_cups_ / 2;
                    swap_t_ = 0.0f;
                } else {
                    float over = swap_t_ - 1.0f;
                    BeginNextSwap();
                    swap_t_ = over;
                }
            }
            return;
        }

        if (phase_ == SHELL_GUESS) {
            if (keys_pressed & KEY_LEFT) {
                if (cursor_slot_ > 0) cursor_slot_--;
            }
            if (keys_pressed & KEY_RIGHT) {
                if (cursor_slot_ < num_cups_ - 1) cursor_slot_++;
            }
            if (keys_pressed & (KEY_A | KEY_B)) {
                chosen_slot_ = cursor_slot_;
                if (chosen_slot_ == pearl_slot_) {
                    AddScore(100u * (uint32_t)round_);
                    if (round_ >= kTotalRounds) {
                        state_ = STATE_VICTORY;
                        state_timer_ = 0.0f;
                        return;
                    }
                    round_++;
                    SetupRound();
                } else {
                    if (lives_ > 1) {
                        lives_--;
                        SetupRound();
                    } else {
                        lives_ = 0;
                        state_ = STATE_GAMEOVER;
                        state_timer_ = 0.0f;
                        return;
                    }
                }
            }
        }
    }
}

void Game019ShellGame::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    // 绿绒魔术赌桌背景
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (y >= 11) {
                SetPixel19(fb_rgb24, x, y, 22, 62, 42);
            } else {
                SetPixel19(fb_rgb24, x, y, 12, 22, 32);
            }
        }
    }

    int cup_w = (num_cups_ == 4) ? 2 : 3;

    // 亮珠揭晓期或结算期绘制金珍珠
    bool show_pearl = (state_ == STATE_TITLE) ||
                      (state_ == STATE_PLAYING && phase_ == SHELL_REVEAL) ||
                      (state_ == STATE_GAMEOVER) ||
                      (state_ == STATE_VICTORY);
    if (show_pearl) {
        int px = (int)roundf(GetSlotX(pearl_slot_)) + (cup_w / 2);
        SetPixel19(fb_rgb24, px, 10, 255, 225, 40);
    }

    // 绘制各个杯子
    for (int s = 0; s < num_cups_; ++s) {
        float fx = GetSlotX(s);
        float fy = 8.0f;

        if (state_ == STATE_TITLE && s == pearl_slot_) {
            fy = 5.0f + sinf(anim_timer_ * 4.0f) * 1.0f;
        } else if (state_ == STATE_PLAYING && phase_ == SHELL_REVEAL && s == pearl_slot_) {
            fy = 5.0f;
        } else if (state_ == STATE_PLAYING && phase_ == SHELL_SHUFFLE) {
            if (s == swap_a_) {
                float xa = GetSlotX(swap_a_);
                float xb = GetSlotX(swap_b_);
                fx = xa + (xb - xa) * swap_t_;
                fy = 8.0f - sinf(swap_t_ * kPi) * 2.0f;
            } else if (s == swap_b_) {
                float xa = GetSlotX(swap_a_);
                float xb = GetSlotX(swap_b_);
                fx = xb + (xa - xb) * swap_t_;
                fy = 8.0f + sinf(swap_t_ * kPi) * 2.0f;
            }
        } else if ((state_ == STATE_VICTORY || state_ == STATE_GAMEOVER) && (s == chosen_slot_ || s == pearl_slot_)) {
            fy = 5.0f;
        }

        int ix = (int)roundf(fx);
        int iy = (int)roundf(fy);
        for (int dy = 0; dy < 3; ++dy) {
            for (int dx = 0; dx < cup_w; ++dx) {
                uint8_t cr = (dy == 0) ? 245 : 210;
                uint8_t cg = (dy == 0) ? 130 : 65;
                uint8_t cb = (dy == 0) ? 45 : 40;
                SetPixel19(fb_rgb24, ix + dx, iy + dy, cr, cg, cb);
            }
        }
    }

    // 选杯游标箭头 (GUESS 阶段)
    if (state_ == STATE_PLAYING && phase_ == SHELL_GUESS) {
        int cx = (int)roundf(GetSlotX(cursor_slot_)) + (cup_w / 2);
        SetPixel19(fb_rgb24, cx, 13, 0, 245, 255);
        SetPixel19(fb_rgb24, cx - 1, 14, 0, 200, 240);
        SetPixel19(fb_rgb24, cx, 14, 255, 255, 255);
        SetPixel19(fb_rgb24, cx + 1, 14, 0, 200, 240);
    }

    // 顶部 HUD: 左侧红心生命, 右侧关卡点
    for (int i = 0; i < (int)lives_ && i < 3; ++i) {
        SetPixel19(fb_rgb24, i * 2, 0, 235, 65, 55);
    }
    for (int r = 0; r < round_ && r < kTotalRounds; ++r) {
        SetPixel19(fb_rgb24, 15 - r, 0, 255, 215, 35);
    }

    if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPixel19(fb_rgb24, 6, y, 250, 250, 250);
            SetPixel19(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game019ShellGame::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = lives_;
    st.state = (uint8_t)state_;
    int cleared = (state_ == STATE_VICTORY) ? kTotalRounds : (round_ - 1);
    st.progress = (uint8_t)((cleared * 100) / kTotalRounds);
    return st;
}

static_assert(sizeof(Game019ShellGame) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
