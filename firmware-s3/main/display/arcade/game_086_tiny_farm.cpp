// game_086_tiny_farm.cpp —— 目标 #086 小农场 核心实现
#include "game_086_tiny_farm.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>
#include <math.h>

namespace arcade {

static inline void SetPx86(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

Game086TinyFarm::Game086TinyFarm()
    : state_(STATE_TITLE),
      score_(0),
      high_score_(0),
      state_timer_(0.0f),
      anim_timer_(0.0f),
      season_timer_(60.0f),
      cursor_col_(2),
      cursor_row_(2),
      water_(kMaxWater),
      combo_(0),
      combo_timer_(0.0f),
      move_cooldown_(0.0f) {
    SetupMatch(STATE_TITLE);
}

void Game086TinyFarm::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

void Game086TinyFarm::SetupMatch(CartridgeState new_state) {
    state_ = new_state;
    score_ = 0;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    season_timer_ = 60.0f;
    cursor_col_ = 2;
    cursor_row_ = 2;
    water_ = kMaxWater;
    combo_ = 0;
    combo_timer_ = 0.0f;
    move_cooldown_ = 0.0f;

    for (int r = 0; r < kGridSize; ++r) {
        for (int c = 0; c < kGridSize; ++c) {
            plots_[r][c] = {PLOT_BARREN, false, false, 0.0f};
        }
    }
}

void Game086TinyFarm::Init() {
    Reset();
}

void Game086TinyFarm::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    SetupMatch(STATE_TITLE);
}

void Game086TinyFarm::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        SetupMatch(STATE_PLAYING);
    }
}

void Game086TinyFarm::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game086TinyFarm::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

void Game086TinyFarm::HandleSmartActionA() {
    FarmPlot& p = plots_[cursor_row_][cursor_col_];
    if (p.state == PLOT_BARREN) {
        p.state = PLOT_SEED;
        p.premium = false;
        p.boost_watered = false;
        p.timer = 0.0f;
    } else if (p.state == PLOT_SEED) {
        if (water_ > 0) {
            water_--;
            p.state = PLOT_SPROUT;
            p.timer = 0.0f;
        }
    } else if (p.state == PLOT_SPROUT || p.state == PLOT_GROWING) {
        if (water_ > 0 && !p.boost_watered) {
            water_--;
            p.boost_watered = true;
            p.timer += 1.2f;
        }
    } else if (p.state == PLOT_RIPE) {
        uint32_t base_val = p.premium ? 90u : 50u;
        uint32_t bonus = (combo_timer_ > 0.0f) ? (uint32_t)(combo_ * 10) : 0u;
        AddScore(base_val + bonus);
        if (combo_timer_ > 0.0f) {
            if (combo_ < 5) combo_++;
        } else {
            combo_ = 1;
        }
        combo_timer_ = 4.0f;
        p = {PLOT_BARREN, false, false, 0.0f};
    } else if (p.state == PLOT_WITHERED) {
        p = {PLOT_BARREN, false, false, 0.0f};
    }
}

void Game086TinyFarm::HandleActionB() {
    FarmPlot& p = plots_[cursor_row_][cursor_col_];
    if (p.state == PLOT_BARREN && water_ > 0) {
        // Plant premium fast-high-value seed
        p.state = PLOT_SEED;
        p.premium = true;
        p.boost_watered = false;
        p.timer = 0.0f;
    } else {
        // Refill watering can from corner well
        water_ = kMaxWater;
    }
}

void Game086TinyFarm::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
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

    if (combo_timer_ > 0.0f) {
        combo_timer_ -= dt;
        if (combo_timer_ <= 0.0f) {
            combo_timer_ = 0.0f;
            combo_ = 0;
        }
    }

    if (move_cooldown_ > 0.0f) {
        move_cooldown_ -= dt;
    }
    uint16_t dpad_mask = KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN;
    uint16_t dpad_trig = keys_pressed & dpad_mask;
    if (!dpad_trig && move_cooldown_ <= 0.0f && (keys_down & dpad_mask)) {
        dpad_trig = keys_down & dpad_mask;
        move_cooldown_ = 0.14f;
    } else if (dpad_trig) {
        move_cooldown_ = 0.18f;
    }

    if (dpad_trig & KEY_LEFT) {
        if (cursor_col_ > 0) cursor_col_--;
    } else if (dpad_trig & KEY_RIGHT) {
        if (cursor_col_ < kGridSize - 1) cursor_col_++;
    } else if (dpad_trig & KEY_UP) {
        if (cursor_row_ > 0) cursor_row_--;
    } else if (dpad_trig & KEY_DOWN) {
        if (cursor_row_ < kGridSize - 1) cursor_row_++;
    }

    if (keys_pressed & KEY_A) {
        HandleSmartActionA();
    }
    if (keys_pressed & KEY_B) {
        HandleActionB();
    }

    if (score_ >= kTargetQuota) {
        state_ = STATE_VICTORY;
        state_timer_ = 0.0f;
        return;
    }

    // Update plot growth & withering
    for (int r = 0; r < kGridSize; ++r) {
        for (int c = 0; c < kGridSize; ++c) {
            FarmPlot& p = plots_[r][c];
            if (p.state == PLOT_SPROUT) {
                p.timer += dt;
                float sprout_dur = p.premium ? 1.6f : 2.5f;
                if (p.timer >= sprout_dur) {
                    p.state = PLOT_GROWING;
                    p.timer = 0.0f;
                }
            } else if (p.state == PLOT_GROWING) {
                p.timer += dt;
                float grow_dur = p.premium ? 2.0f : 3.0f;
                if (p.timer >= grow_dur) {
                    p.state = PLOT_RIPE;
                    p.timer = 0.0f;
                }
            } else if (p.state == PLOT_RIPE) {
                p.timer += dt;
                if (p.timer > 10.0f) {
                    p.state = PLOT_WITHERED;
                    p.timer = 0.0f;
                }
            }
        }
    }

    season_timer_ -= dt;
    if (season_timer_ <= 0.0f) {
        season_timer_ = 0.0f;
        if (score_ >= kTargetQuota) {
            state_ = STATE_VICTORY;
        } else {
            state_ = STATE_GAMEOVER;
        }
        state_timer_ = 0.0f;
    }
}

void Game086TinyFarm::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    // Warm meadow paths background
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            SetPx86(fb_rgb24, x, y, 28, 48, 22);
        }
    }
    for (int x = 0; x < 16; ++x) {
        SetPx86(fb_rgb24, x, 0, 12, 14, 18);
        SetPx86(fb_rgb24, x, 1, 20, 34, 18);
    }

    // Corner Water Well at (15, 1) and (0, 1)
    SetPx86(fb_rgb24, 15, 1, 30, 175, 255);
    SetPx86(fb_rgb24, 0, 1, 30, 175, 255);

    // 5x5 farm plots (2x2 px each across x=1..14, y=2..15)
    bool gold_blink = (((int)(anim_timer_ * 6.0f)) % 2) == 0;
    for (int r = 0; r < kGridSize; ++r) {
        for (int c = 0; c < kGridSize; ++c) {
            int px = 1 + c * 3;
            int py = 2 + r * 3;
            const FarmPlot& p = plots_[r][c];
            for (int dy = 0; dy < 2; ++dy) {
                for (int dx = 0; dx < 2; ++dx) {
                    uint8_t cr = 75, cg = 48, cb = 26;
                    if (p.state == PLOT_SEED) {
                        if (dx == 0 && dy == 0) {
                            if (p.premium) { cr = 255; cg = 140; cb = 210; }
                            else { cr = 225; cg = 190; cb = 65; }
                        } else {
                            cr = 85; cg = 55; cb = 30;
                        }
                    } else if (p.state == PLOT_SPROUT) {
                        cr = 35; cg = 205; cb = 165;
                    } else if (p.state == PLOT_GROWING) {
                        cr = 45; cg = 215; cb = 65;
                    } else if (p.state == PLOT_RIPE) {
                        if (gold_blink) {
                            cr = 255; cg = p.premium ? 175 : 215; cb = 25;
                        } else {
                            cr = 255; cg = 240; cb = 110;
                        }
                    } else if (p.state == PLOT_WITHERED) {
                        cr = 95; cg = 95; cb = 100;
                    }
                    SetPx86(fb_rgb24, px + dx, py + dy, cr, cg, cb);
                }
            }
        }
    }

    // Farmer cursor around active 2x2 plot
    if (state_ == STATE_PLAYING || state_ == STATE_TITLE) {
        int cx = 1 + cursor_col_ * 3;
        int cy = 2 + cursor_row_ * 3;
        if ((((int)(anim_timer_ * 7.0f)) % 2) == 0) {
            SetPx86(fb_rgb24, cx, cy, 255, 255, 255);
            SetPx86(fb_rgb24, cx + 1, cy + 1, 255, 255, 255);
        }
    }

    // Row 0 HUD: Season timer (0..7) & Water meter (9..14)
    int time_pips = (int)ceilf((season_timer_ / 60.0f) * 8.0f);
    if (time_pips < 0) time_pips = 0;
    if (time_pips > 8) time_pips = 8;
    for (int i = 0; i < 8; ++i) {
        if (i < time_pips) {
            SetPx86(fb_rgb24, i, 0, 245, 175, 35);
        } else {
            SetPx86(fb_rgb24, i, 0, 45, 30, 12);
        }
    }
    for (int w = 0; w < kMaxWater; ++w) {
        if (w < water_) {
            SetPx86(fb_rgb24, 9 + w, 0, 35, 195, 255);
        } else {
            SetPx86(fb_rgb24, 9 + w, 0, 15, 40, 60);
        }
    }

    if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPx86(fb_rgb24, 6, y, 250, 250, 250);
            SetPx86(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game086TinyFarm::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = (state_ == STATE_GAMEOVER) ? 0 : 1;
    st.state = (uint8_t)state_;
    uint32_t prog = (score_ * 100u) / kTargetQuota;
    st.progress = (uint8_t)(prog > 100u ? 100u : prog);
    return st;
}

static_assert(sizeof(Game086TinyFarm) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
