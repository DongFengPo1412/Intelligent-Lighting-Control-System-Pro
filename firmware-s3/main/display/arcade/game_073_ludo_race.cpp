// game_073_ludo_race.cpp —— 目标 #073 飞行棋 (Ludo Race, 1986)
#include "game_073_ludo_race.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>
#include <math.h>

namespace arcade {

static const int kOuterLoop[24][2] = {
    {4, 10}, {4, 9}, {4, 8}, {4, 7}, {4, 6}, {4, 5},
    {5, 4},  {6, 4}, {7, 4}, {8, 4}, {9, 4}, {10, 4},
    {11, 5}, {11, 6}, {11, 7}, {11, 8}, {11, 9}, {11, 10},
    {10, 11}, {9, 11}, {8, 11}, {7, 11}, {6, 11}, {5, 11}
};

static const int kPlayerHomeStretch[3][2] = {{5, 10}, {6, 9}, {6, 8}};
static const int kAIHomeStretch[3][2] = {{10, 5}, {9, 6}, {9, 7}};

static inline void SetPixel73(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

Game073LudoRace::Game073LudoRace()
    : state_(STATE_TITLE),
      phase_(LUDO_WAIT_ROLL),
      dice_(6),
      anim_die_(1),
      selected_token_(0),
      phase_timer_(0.0f),
      capture_flash_timer_(0.0f),
      score_(0),
      high_score_(0),
      state_timer_(0.0f),
      anim_timer_(0.0f),
      rng_state_(0x73731986u) {
    InitGameData();
}

uint32_t Game073LudoRace::NextRand() {
    rng_state_ = rng_state_ * 1103515245u + 12345u;
    return (rng_state_ >> 16) & 0x7FFFu;
}

void Game073LudoRace::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

void Game073LudoRace::InitGameData() {
    phase_ = LUDO_WAIT_ROLL;
    p_step_[0] = -1;
    p_step_[1] = -1;
    ai_step_[0] = -1;
    ai_step_[1] = -1;
    dice_ = 6;
    anim_die_ = 1;
    selected_token_ = 0;
    phase_timer_ = 0.0f;
    capture_flash_timer_ = 0.0f;
    score_ = 0;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    rng_state_ = 0x73731986u;
}

void Game073LudoRace::Init() {
    Reset();
}

void Game073LudoRace::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    state_ = STATE_TITLE;
    InitGameData();
}

void Game073LudoRace::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        InitGameData();
        state_ = STATE_PLAYING;
    }
}

void Game073LudoRace::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game073LudoRace::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

bool Game073LudoRace::CanMoveToken(int step, int die_val) const {
    if (step == -1) {
        return die_val >= 5;
    }
    return step >= 0 && step < 27;
}

void Game073LudoRace::ApplyMove(bool is_player, int tok_idx) {
    int* my_steps = is_player ? p_step_ : ai_step_;
    int* opp_steps = is_player ? ai_step_ : p_step_;

    int cur = my_steps[tok_idx];
    int nxt = cur;
    if (cur == -1) {
        nxt = 0;
        if (is_player) AddScore(15);
    } else {
        nxt = cur + dice_;
        if (nxt > 27) nxt = 27;
        if (is_player) {
            AddScore((nxt == 27) ? 60 : 10);
        }
    }
    my_steps[tok_idx] = nxt;

    // Authentic Ludo outer-track capture: landing on opponent's LONE outer-track token knocks it back!
    if (nxt >= 0 && nxt <= 23) {
        int my_outer = is_player ? nxt : ((12 + nxt) % 24);
        int opp_at_cell = 0;
        int victim_idx = -1;
        for (int j = 0; j < 2; ++j) {
            if (opp_steps[j] >= 0 && opp_steps[j] <= 23) {
                int opp_outer = is_player ? ((12 + opp_steps[j]) % 24) : opp_steps[j];
                if (opp_outer == my_outer) {
                    opp_at_cell++;
                    victim_idx = j;
                }
            }
        }
        if (opp_at_cell == 1 && victim_idx >= 0) {
            opp_steps[victim_idx] = -1;
            capture_flash_timer_ = 0.35f;
            if (is_player) {
                AddScore(80);
            }
        }
    }

    // Check victory / game over
    if (p_step_[0] == 27 && p_step_[1] == 27) {
        AddScore(400);
        state_ = STATE_VICTORY;
        state_timer_ = 0.0f;
        return;
    }
    if (ai_step_[0] == 27 && ai_step_[1] == 27) {
        state_ = STATE_GAMEOVER;
        state_timer_ = 0.0f;
        return;
    }

    // Bonus roll on 6!
    if (is_player) {
        if (dice_ == 6) {
            phase_ = LUDO_WAIT_ROLL;
        } else {
            phase_ = LUDO_AI_THINK;
            phase_timer_ = 0.22f;
        }
    } else {
        if (dice_ == 6) {
            phase_ = LUDO_AI_THINK;
            phase_timer_ = 0.22f;
        } else {
            phase_ = LUDO_WAIT_ROLL;
        }
    }
}

int Game073LudoRace::ChooseAIToken() const {
    int best_tok = -1;
    int best_val = -9999;

    for (int t = 0; t < 2; ++t) {
        int cur = ai_step_[t];
        if (!CanMoveToken(cur, dice_)) continue;

        int nxt = (cur == -1) ? 0 : (cur + dice_ > 27 ? 27 : cur + dice_);
        int val = nxt * 3;

        // Priority 1: Capture lone player token
        if (nxt >= 0 && nxt <= 23) {
            int ai_outer = (12 + nxt) % 24;
            int pl_count = 0;
            for (int j = 0; j < 2; ++j) {
                if (p_step_[j] == ai_outer) pl_count++;
            }
            if (pl_count == 1) val += 500;
        }
        // Priority 2: Reach goal
        if (nxt == 27) val += 300;
        // Priority 3: Launch out of hangar
        if (cur == -1) val += 140;
        // Priority 4: Enter safe home stretch
        if (cur < 24 && nxt >= 24) val += 90;

        if (val > best_val) {
            best_val = val;
            best_tok = t;
        }
    }
    return best_tok;
}

void Game073LudoRace::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
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
    if (capture_flash_timer_ > 0.0f) {
        capture_flash_timer_ -= dt;
        if (capture_flash_timer_ < 0.0f) capture_flash_timer_ = 0.0f;
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

    if (state_ == STATE_PLAYING) {
        if (keys_pressed & KEY_START) {
            state_ = STATE_PAUSED;
            return;
        }

        if (phase_ == LUDO_WAIT_ROLL) {
            if (keys_pressed & KEY_A) {
                dice_ = 1 + (int)(NextRand() % 6);
                anim_die_ = 1 + (int)(NextRand() % 6);
                phase_ = LUDO_ROLL_ANIM;
                phase_timer_ = 0.16f;
            }
        } else if (phase_ == LUDO_ROLL_ANIM) {
            phase_timer_ -= dt;
            anim_die_ = 1 + ((int)(anim_timer_ * 30.0f) % 6);
            if (phase_timer_ <= 0.0f) {
                bool m0 = CanMoveToken(p_step_[0], dice_);
                bool m1 = CanMoveToken(p_step_[1], dice_);
                if (!m0 && !m1) {
                    phase_ = LUDO_PASS_DELAY;
                    phase_timer_ = 0.22f;
                } else {
                    selected_token_ = m0 ? 0 : 1;
                    phase_ = LUDO_SELECT_TOKEN;
                }
            }
        } else if (phase_ == LUDO_SELECT_TOKEN) {
            bool m0 = CanMoveToken(p_step_[0], dice_);
            bool m1 = CanMoveToken(p_step_[1], dice_);
            if (m0 && m1 && (keys_pressed & (KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN | KEY_B))) {
                selected_token_ = 1 - selected_token_;
            } else if (m0 && !m1) {
                selected_token_ = 0;
            } else if (!m0 && m1) {
                selected_token_ = 1;
            }

            if (keys_pressed & KEY_A) {
                if (CanMoveToken(p_step_[selected_token_], dice_)) {
                    ApplyMove(true, selected_token_);
                }
            }
        } else if (phase_ == LUDO_PASS_DELAY) {
            phase_timer_ -= dt;
            if (phase_timer_ <= 0.0f) {
                phase_ = LUDO_AI_THINK;
                phase_timer_ = 0.22f;
            }
        } else if (phase_ == LUDO_AI_THINK) {
            phase_timer_ -= dt;
            if (phase_timer_ <= 0.0f) {
                dice_ = 1 + (int)(NextRand() % 6);
                phase_ = LUDO_AI_MOVE;
                phase_timer_ = 0.18f;
            }
        } else if (phase_ == LUDO_AI_MOVE) {
            phase_timer_ -= dt;
            if (phase_timer_ <= 0.0f) {
                int tok = ChooseAIToken();
                if (tok >= 0) {
                    ApplyMove(false, tok);
                } else {
                    if (dice_ == 6) {
                        phase_ = LUDO_AI_THINK;
                        phase_timer_ = 0.22f;
                    } else {
                        phase_ = LUDO_WAIT_ROLL;
                    }
                }
            }
        }
    }
}

void Game073LudoRace::GetTokenPixel(bool is_player, int tok_idx, int& out_x, int& out_y) const {
    int step = is_player ? p_step_[tok_idx] : ai_step_[tok_idx];
    if (step == -1) {
        if (is_player) {
            out_x = (tok_idx == 0) ? 1 : 2;
            out_y = (tok_idx == 0) ? 13 : 14;
        } else {
            out_x = (tok_idx == 0) ? 13 : 14;
            out_y = (tok_idx == 0) ? 1 : 2;
        }
    } else if (step <= 23) {
        int outer = is_player ? step : ((12 + step) % 24);
        out_x = kOuterLoop[outer][0];
        out_y = kOuterLoop[outer][1];
    } else if (step <= 26) {
        int h = step - 24;
        if (is_player) {
            out_x = kPlayerHomeStretch[h][0];
            out_y = kPlayerHomeStretch[h][1];
        } else {
            out_x = kAIHomeStretch[h][0];
            out_y = kAIHomeStretch[h][1];
        }
    } else {
        if (is_player) {
            out_x = (tok_idx == 0) ? 7 : 8;
            out_y = 8;
        } else {
            out_x = (tok_idx == 0) ? 8 : 7;
            out_y = 7;
        }
    }
}

void Game073LudoRace::DrawDie3x3(uint8_t* fb, int val, bool is_player_turn) const {
    uint8_t bg_r = is_player_turn ? 20 : 45;
    uint8_t bg_g = is_player_turn ? 45 : 20;
    uint8_t bg_b = is_player_turn ? 55 : 25;
    for (int y = 0; y <= 2; ++y) {
        for (int x = 0; x <= 2; ++x) {
            SetPixel73(fb, x, y, bg_r, bg_g, bg_b);
        }
    }

    uint8_t pr = 255, pg = 235, pb = 120;
    if (val == 6) {
        pr = 255; pg = 190; pb = 0;
    }

    if (val == 1 || val == 3 || val == 5) {
        SetPixel73(fb, 1, 1, pr, pg, pb);
    }
    if (val >= 2) {
        SetPixel73(fb, 0, 0, pr, pg, pb);
        SetPixel73(fb, 2, 2, pr, pg, pb);
    }
    if (val >= 4) {
        SetPixel73(fb, 2, 0, pr, pg, pb);
        SetPixel73(fb, 0, 2, pr, pg, pb);
    }
    if (val == 6) {
        SetPixel73(fb, 0, 1, pr, pg, pb);
        SetPixel73(fb, 2, 1, pr, pg, pb);
    }
}

void Game073LudoRace::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    // Dark velvet board background (flashes warm amber briefly on capture!)
    uint8_t bg_r = (capture_flash_timer_ > 0.0f) ? 55 : 10;
    uint8_t bg_g = (capture_flash_timer_ > 0.0f) ? 25 : 14;
    uint8_t bg_b = (capture_flash_timer_ > 0.0f) ? 10 : 22;
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            SetPixel73(fb_rgb24, x, y, bg_r, bg_g, bg_b);
        }
    }

    // Hangar pads: Player Cyan (bottom-left 1..2, 13..14), AI Red (top-right 13..14, 1..2)
    for (int dy = 0; dy < 2; ++dy) {
        for (int dx = 0; dx < 2; ++dx) {
            SetPixel73(fb_rgb24, 1 + dx, 13 + dy, 12, 60, 80);
            SetPixel73(fb_rgb24, 13 + dx, 1 + dy, 80, 20, 25);
        }
    }

    // 24-step outer loop
    for (int i = 0; i < 24; ++i) {
        int tx = kOuterLoop[i][0];
        int ty = kOuterLoop[i][1];
        if (i == 0) {
            SetPixel73(fb_rgb24, tx, ty, 20, 100, 125); // Player launch pad
        } else if (i == 12) {
            SetPixel73(fb_rgb24, tx, ty, 125, 35, 35);  // AI launch pad
        } else {
            uint8_t v = (i % 2 == 0) ? 55 : 42;
            SetPixel73(fb_rgb24, tx, ty, v, v + 4, v + 12);
        }
    }

    // Colored 3-step home stretches
    for (int h = 0; h < 3; ++h) {
        SetPixel73(fb_rgb24, kPlayerHomeStretch[h][0], kPlayerHomeStretch[h][1], 18, 95, 120);
        SetPixel73(fb_rgb24, kAIHomeStretch[h][0], kAIHomeStretch[h][1], 120, 30, 35);
    }

    // Center goal shrine (7..8, 7..8)
    for (int y = 7; y <= 8; ++y) {
        for (int x = 7; x <= 8; ++x) {
            SetPixel73(fb_rgb24, x, y, 110, 90, 20);
        }
    }

    // Die in top-left corner (0..2, 0..2)
    bool p_turn = (phase_ == LUDO_WAIT_ROLL || phase_ == LUDO_ROLL_ANIM || phase_ == LUDO_SELECT_TOKEN);
    int shown_die = (phase_ == LUDO_ROLL_ANIM) ? anim_die_ : dice_;
    DrawDie3x3(fb_rgb24, shown_die, p_turn);

    // Draw AI Red tokens
    for (int t = 0; t < 2; ++t) {
        int tx = 0, ty = 0;
        GetTokenPixel(false, t, tx, ty);
        if (ai_step_[t] == 27) {
            SetPixel73(fb_rgb24, tx, ty, 255, 95, 50);
        } else {
            SetPixel73(fb_rgb24, tx, ty, 240, 50, 50);
        }
    }

    // Draw Player Cyan tokens (blinking selected movable token!)
    bool blink_bright = (fmodf(anim_timer_, 0.36f) < 0.20f);
    for (int t = 0; t < 2; ++t) {
        int tx = 0, ty = 0;
        GetTokenPixel(true, t, tx, ty);
        if (state_ == STATE_PLAYING && phase_ == LUDO_SELECT_TOKEN && t == selected_token_) {
            if (blink_bright) {
                SetPixel73(fb_rgb24, tx, ty, 255, 255, 255);
            } else {
                SetPixel73(fb_rgb24, tx, ty, 0, 230, 255);
            }
        } else if (p_step_[t] == 27) {
            SetPixel73(fb_rgb24, tx, ty, 120, 255, 210);
        } else {
            SetPixel73(fb_rgb24, tx, ty, 0, 215, 255);
        }
    }

    if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPixel73(fb_rgb24, 6, y, 250, 250, 250);
            SetPixel73(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game073LudoRace::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = (state_ == STATE_GAMEOVER) ? 0 : 1;
    st.state = (uint8_t)state_;
    int p0 = (p_step_[0] < 0) ? 0 : (p_step_[0] + 1);
    int p1 = (p_step_[1] < 0) ? 0 : (p_step_[1] + 1);
    int prog = ((p0 + p1) * 100) / 56;
    if (prog > 100) prog = 100;
    st.progress = (uint8_t)prog;
    return st;
}

static_assert(sizeof(Game073LudoRace) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
