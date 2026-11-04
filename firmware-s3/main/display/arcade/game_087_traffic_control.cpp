// game_087_traffic_control.cpp —— 目标 #087 交通灯管理 核心实现
#include "game_087_traffic_control.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>
#include <math.h>

namespace arcade {

static inline void SetPx87(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

Game087TrafficControl::Game087TrafficControl()
    : state_(STATE_TITLE),
      score_(0),
      high_score_(0),
      state_timer_(0.0f),
      anim_timer_(0.0f),
      phase_(0),
      all_red_timer_(0.0f),
      passed_cars_(0),
      incidents_(0),
      spawn_timer_(0.5f),
      rng_seed_(0x1992087Au),
      crash_flash_timer_(0.0f),
      crash_x_(7),
      crash_y_(7) {
    SetupMatch(STATE_TITLE);
}

void Game087TrafficControl::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

void Game087TrafficControl::CarXY(const TrafficControlCar087& c, float& out_x, float& out_y) const {
    if (c.lane == 0) {
        out_x = 6.0f;
        out_y = c.prog;
    } else if (c.lane == 1) {
        out_x = 9.0f;
        out_y = 15.0f - c.prog;
    } else if (c.lane == 2) {
        out_x = c.prog;
        out_y = 9.0f;
    } else {
        out_x = 15.0f - c.prog;
        out_y = 6.0f;
    }
}

bool Game087TrafficControl::IsAxisGreen(uint8_t axis) const {
    if (all_red_timer_ > 0.0f) return false;
    return (phase_ == axis);
}

void Game087TrafficControl::SetupMatch(CartridgeState new_state) {
    state_ = new_state;
    score_ = 0;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    phase_ = 0;
    all_red_timer_ = 0.0f;
    passed_cars_ = 0;
    incidents_ = 0;
    spawn_timer_ = 0.45f;
    rng_seed_ = 0x1992087Au;
    crash_flash_timer_ = 0.0f;
    crash_x_ = 7;
    crash_y_ = 7;

    for (int i = 0; i < 4; ++i) {
        lane_rage_timer_[i] = 0.0f;
    }
    for (int i = 0; i < kMaxCars; ++i) {
        cars_[i] = {false, 0, 0.0f, 4.8f, 0};
    }

    // Initial pair of approaching cars
    SpawnCar(0);
    SpawnCar(2);
}

void Game087TrafficControl::Init() {
    Reset();
}

void Game087TrafficControl::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    SetupMatch(STATE_TITLE);
}

void Game087TrafficControl::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        SetupMatch(STATE_PLAYING);
    }
}

void Game087TrafficControl::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game087TrafficControl::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

void Game087TrafficControl::SpawnCar(uint8_t lane) {
    for (int i = 0; i < kMaxCars; ++i) {
        if (cars_[i].active && cars_[i].lane == lane && cars_[i].prog < 2.0f) {
            return; // Spawn blocked by backed-up queue
        }
    }
    for (int i = 0; i < kMaxCars; ++i) {
        if (!cars_[i].active) {
            rng_seed_ = rng_seed_ * 1103515245u + 12345u;
            uint8_t cid = (uint8_t)((rng_seed_ >> 16) % 4);
            cars_[i].active = true;
            cars_[i].lane = lane;
            cars_[i].prog = 0.0f;
            cars_[i].speed = 4.6f + (float)((rng_seed_ >> 20) % 3) * 0.35f;
            cars_[i].color_id = cid;
            return;
        }
    }
}

void Game087TrafficControl::RecordIncident(int fx, int fy) {
    crash_x_ = fx;
    crash_y_ = fy;
    crash_flash_timer_ = 0.5f;
    incidents_++;
    if (incidents_ >= 3) {
        state_ = STATE_GAMEOVER;
        state_timer_ = 0.0f;
    }
}

void Game087TrafficControl::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
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

    if (crash_flash_timer_ > 0.0f) {
        crash_flash_timer_ -= dt;
    }
    if (all_red_timer_ > 0.0f) {
        all_red_timer_ -= dt;
        if (all_red_timer_ < 0.0f) all_red_timer_ = 0.0f;
    }

    // KEY_A toggles N-S Green / E-W Green phase
    if (keys_pressed & KEY_A) {
        phase_ = (uint8_t)(1 - phase_);
        all_red_timer_ = 0.0f;
    }
    // KEY_B toggles temporary All-Red clearance & intersection boost
    if (keys_pressed & KEY_B) {
        if (all_red_timer_ > 0.0f) {
            all_red_timer_ = 0.0f;
        } else {
            all_red_timer_ = 2.0f;
        }
    }

    // Spawn incoming traffic
    spawn_timer_ -= dt;
    if (spawn_timer_ <= 0.0f) {
        rng_seed_ = rng_seed_ * 1103515245u + 12345u;
        uint8_t ln = (uint8_t)((rng_seed_ >> 16) % 4);
        SpawnCar(ln);
        spawn_timer_ = 0.85f;
    }

    // Advance cars & enforce stop-lines + queuing
    for (int i = 0; i < kMaxCars; ++i) {
        if (!cars_[i].active) continue;
        uint8_t axis = (cars_[i].lane < 2) ? 0 : 1;
        bool green = IsAxisGreen(axis);

        float spd = cars_[i].speed;
        if (all_red_timer_ > 0.0f && cars_[i].prog > 5.05f && cars_[i].prog < 10.0f) {
            spd *= 1.45f;
        }

        float next_prog = cars_[i].prog + spd * dt;

        // Stop cleanly behind RED stop line (prog = 5.0) if not yet inside box
        if (!green && cars_[i].prog <= 5.05f) {
            if (next_prog > 5.0f) next_prog = 5.0f;
        }

        // Queue spacing behind nearest car ahead in same lane
        for (int j = 0; j < kMaxCars; ++j) {
            if (i == j || !cars_[j].active || cars_[j].lane != cars_[i].lane) continue;
            if (cars_[j].prog > cars_[i].prog) {
                float max_allowed = cars_[j].prog - 1.6f;
                if (next_prog > max_allowed) {
                    next_prog = max_allowed;
                }
            }
        }

        if (next_prog < cars_[i].prog) {
            next_prog = cars_[i].prog;
        }
        cars_[i].prog = next_prog;

        if (cars_[i].prog >= 15.6f) {
            cars_[i].active = false;
            passed_cars_++;
            AddScore(25);
            if (passed_cars_ >= kTargetCars) {
                AddScore(150);
                state_ = STATE_VICTORY;
                state_timer_ = 0.0f;
                return;
            }
        }
    }

    // Check T-bone collisions between N-S and E-W cars
    for (int i = 0; i < kMaxCars; ++i) {
        if (!cars_[i].active || cars_[i].lane >= 2) continue;
        float x1, y1;
        CarXY(cars_[i], x1, y1);
        for (int j = 0; j < kMaxCars; ++j) {
            if (!cars_[j].active || cars_[j].lane < 2) continue;
            float x2, y2;
            CarXY(cars_[j], x2, y2);
            if (fabsf(x1 - x2) < 0.95f && fabsf(y1 - y2) < 0.95f) {
                cars_[i].active = false;
                cars_[j].active = false;
                RecordIncident((int)roundf((x1 + x2) * 0.5f), (int)roundf((y1 + y2) * 0.5f));
                if (state_ == STATE_GAMEOVER) return;
                break;
            }
        }
    }

    // Check Gridlock Rage (lane backed up to spawn edge on RED for > 3.5s)
    for (uint8_t ln = 0; ln < 4; ++ln) {
        uint8_t axis = (ln < 2) ? 0 : 1;
        bool green = IsAxisGreen(axis);
        int waiting_cnt = 0;
        bool edge_blocked = false;
        int front_idx = -1;
        float front_prog = -1.0f;

        for (int i = 0; i < kMaxCars; ++i) {
            if (!cars_[i].active || cars_[i].lane != ln) continue;
            if (cars_[i].prog <= 5.05f) {
                waiting_cnt++;
                if (cars_[i].prog <= 2.0f) edge_blocked = true;
                if (cars_[i].prog > front_prog) {
                    front_prog = cars_[i].prog;
                    front_idx = i;
                }
            }
        }

        if (!green && waiting_cnt >= 3 && edge_blocked) {
            lane_rage_timer_[ln] += dt;
            if (lane_rage_timer_[ln] > 3.5f) {
                lane_rage_timer_[ln] = 0.0f;
                int fx = 7, fy = 7;
                if (front_idx >= 0) {
                    float cx, cy;
                    CarXY(cars_[front_idx], cx, cy);
                    fx = (int)roundf(cx);
                    fy = (int)roundf(cy);
                    cars_[front_idx].active = false;
                }
                RecordIncident(fx, fy);
                if (state_ == STATE_GAMEOVER) return;
            }
        } else if (green || waiting_cnt < 2) {
            lane_rage_timer_[ln] = 0.0f;
        }
    }
}

void Game087TrafficControl::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    // Urban grass / sidewalks & 4-way asphalt intersection (x=6..9, y=6..9)
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            bool v_road = (x >= 6 && x <= 9);
            bool h_road = (y >= 6 && y <= 9);
            if (v_road || h_road) {
                SetPx87(fb_rgb24, x, y, 30, 32, 38);
                if (v_road && !h_road && (y % 3 == 1)) {
                    SetPx87(fb_rgb24, 7, y, 75, 75, 55);
                } else if (h_road && !v_road && (x % 3 == 1)) {
                    SetPx87(fb_rgb24, x, 7, 75, 75, 55);
                }
            } else {
                SetPx87(fb_rgb24, x, y, 20, 42, 26);
            }
        }
    }

    // Intersection corner Traffic Signals: (5,5) & (10,10) = N-S; (10,5) & (5,10) = E-W
    bool ns_green = IsAxisGreen(0);
    bool ew_green = IsAxisGreen(1);

    uint8_t nsr = ns_green ? 30 : 255;
    uint8_t nsg = ns_green ? 245 : 35;
    uint8_t nsb = ns_green ? 70 : 35;
    SetPx87(fb_rgb24, 5, 5, nsr, nsg, nsb);
    SetPx87(fb_rgb24, 10, 10, nsr, nsg, nsb);

    uint8_t ewr = ew_green ? 30 : 255;
    uint8_t ewg = ew_green ? 245 : 35;
    uint8_t ewb = ew_green ? 70 : 35;
    SetPx87(fb_rgb24, 10, 5, ewr, ewg, ewb);
    SetPx87(fb_rgb24, 5, 10, ewr, ewg, ewb);

    // Cars
    static const uint8_t kCarPalette[4][3] = {
        {60, 200, 255},
        {255, 205, 45},
        {195, 110, 255},
        {240, 245, 250},
    };
    for (int i = 0; i < kMaxCars; ++i) {
        if (!cars_[i].active) continue;
        float cx, cy;
        CarXY(cars_[i], cx, cy);
        int ix = (int)roundf(cx);
        int iy = (int)roundf(cy);
        const uint8_t* col = kCarPalette[cars_[i].color_id & 3];
        SetPx87(fb_rgb24, ix, iy, col[0], col[1], col[2]);
    }

    // Crash / Gridlock explosion flash
    if (crash_flash_timer_ > 0.0f) {
        for (int dy = -1; dy <= 1; ++dy) {
            for (int dx = -1; dx <= 1; ++dx) {
                SetPx87(fb_rgb24, crash_x_ + dx, crash_y_ + dy, 255, 95, 20);
            }
        }
        SetPx87(fb_rgb24, crash_x_, crash_y_, 255, 240, 80);
    }

    // HUD top-left (x=0..4, y=0): Remaining Lives (3 - incidents) & top-right (x=11..15, y=0): Progress
    int lives_rem = 3 - (int)incidents_;
    for (int i = 0; i < 3; ++i) {
        if (i < lives_rem) SetPx87(fb_rgb24, i, 0, 45, 230, 95);
        else SetPx87(fb_rgb24, i, 0, 90, 25, 25);
    }
    int prog_pips = (passed_cars_ * 5) / kTargetCars;
    for (int p = 0; p < 5; ++p) {
        if (p < prog_pips) SetPx87(fb_rgb24, 11 + p, 0, 255, 215, 40);
        else SetPx87(fb_rgb24, 11 + p, 0, 45, 40, 15);
    }

    if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPx87(fb_rgb24, 6, y, 250, 250, 250);
            SetPx87(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game087TrafficControl::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = (uint8_t)(incidents_ >= 3 ? 0 : (3 - incidents_));
    st.state = (uint8_t)state_;
    st.progress = (uint8_t)((passed_cars_ * 100) / kTargetCars);
    if (st.progress > 100) st.progress = 100;
    return st;
}

static_assert(sizeof(Game087TrafficControl) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
