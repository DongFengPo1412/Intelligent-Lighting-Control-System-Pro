// game_075_slalom_ski.cpp —— 目标 #075 滑雪绕旗 (Alpine Slalom, 1982)
#include "game_075_slalom_ski.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>
#include <math.h>

namespace arcade {

static inline void SetPixel75(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

Game075SlalomSki::Game075SlalomSki()
    : state_(STATE_TITLE),
      skier_x_(7.5f),
      skier_y_(3.5f),
      skier_vx_(0.0f),
      downhill_speed_(8.5f),
      snow_scroll_(0.0f),
      gate_seq_(0),
      gates_passed_(0),
      missed_gates_(0),
      combo_(0),
      lives_(3),
      time_penalty_s_(0.0f),
      invuln_timer_(0.0f),
      green_flash_timer_(0.0f),
      red_flash_timer_(0.0f),
      finish_active_(false),
      finish_banner_y_(20.0f),
      score_(0),
      high_score_(0),
      state_timer_(0.0f),
      anim_timer_(0.0f),
      rng_state_(0x75751982u) {
    InitGameData();
}

uint32_t Game075SlalomSki::NextRand() {
    rng_state_ = rng_state_ * 1103515245u + 12345u;
    return (rng_state_ >> 16) & 0x7FFFu;
}

void Game075SlalomSki::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

void Game075SlalomSki::SpawnObstacleForGate(float gate_y, float gate_left, float gate_right) {
    int slot = -1;
    for (int i = 0; i < kMaxObstacles; ++i) {
        if (!obstacles_[i].active) {
            slot = i;
            break;
        }
    }
    if (slot < 0) return;

    // Place obstacle midway between gates and strictly outside the slalom corridor
    float obs_x = 2.0f;
    if (gate_left > 6.5f) {
        obs_x = 2.0f + (float)(NextRand() % 3);
    } else {
        obs_x = 11.5f + (float)(NextRand() % 3);
    }
    // Double check outside [gate_left - 1.2, gate_right + 1.2]
    if (obs_x >= gate_left - 1.2f && obs_x <= gate_right + 1.2f) {
        return;
    }

    obstacles_[slot].x = obs_x;
    obstacles_[slot].y = gate_y + 4.5f;
    obstacles_[slot].type = (uint8_t)(NextRand() % 2); // 0 = pine tree, 1 = mogul
    obstacles_[slot].active = true;
}

void Game075SlalomSki::SpawnNextGate(int slot, float start_y) {
    // Alternate slalom left/right rhythmically across slope (width 4.5 px)
    bool left_side = (gate_seq_ % 2 == 0);
    float jitter = (float)(NextRand() % 3) * 0.8f;
    float lx = left_side ? (2.5f + jitter) : (7.4f + jitter);
    float rx = lx + 4.5f;

    gates_[slot].y = start_y;
    gates_[slot].left_x = lx;
    gates_[slot].right_x = rx;
    gates_[slot].is_red_left = left_side;
    gates_[slot].judged = false;
    gates_[slot].passed = false;
    gates_[slot].active = true;

    gate_seq_++;
    SpawnObstacleForGate(start_y, lx, rx);
}

void Game075SlalomSki::InitGameData() {
    skier_x_ = 7.5f;
    skier_y_ = 3.5f;
    skier_vx_ = 0.0f;
    downhill_speed_ = 8.5f;
    snow_scroll_ = 0.0f;
    gate_seq_ = 0;
    gates_passed_ = 0;
    missed_gates_ = 0;
    combo_ = 0;
    lives_ = 3;
    time_penalty_s_ = 0.0f;
    invuln_timer_ = 0.0f;
    green_flash_timer_ = 0.0f;
    red_flash_timer_ = 0.0f;
    finish_active_ = false;
    finish_banner_y_ = 20.0f;
    score_ = 0;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    rng_state_ = 0x75751982u;

    for (int i = 0; i < kMaxObstacles; ++i) {
        obstacles_[i].active = false;
    }
    for (int i = 0; i < kMaxGates; ++i) {
        SpawnNextGate(i, 12.0f + (float)i * 9.5f);
    }
}

void Game075SlalomSki::Init() {
    Reset();
}

void Game075SlalomSki::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    state_ = STATE_TITLE;
    InitGameData();
}

void Game075SlalomSki::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        InitGameData();
        state_ = STATE_PLAYING;
    }
}

void Game075SlalomSki::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game075SlalomSki::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

void Game075SlalomSki::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt > 0.05f) dt = 0.05f;

    if (state_ == STATE_PAUSED) {
        if (keys_pressed & KEY_START) {
            state_ = STATE_PLAYING;
        }
        return;
    }

    state_timer_ += dt;
    anim_timer_ += dt;

    if (invuln_timer_ > 0.0f) invuln_timer_ = fmaxf(0.0f, invuln_timer_ - dt);
    if (green_flash_timer_ > 0.0f) green_flash_timer_ = fmaxf(0.0f, green_flash_timer_ - dt);
    if (red_flash_timer_ > 0.0f) red_flash_timer_ = fmaxf(0.0f, red_flash_timer_ - dt);

    if (state_ == STATE_TITLE) {
        snow_scroll_ += 6.0f * dt;
        if (snow_scroll_ >= 16.0f) snow_scroll_ -= 16.0f;
        skier_x_ = 7.5f + sinf(anim_timer_ * 2.5f) * 3.0f;
        if (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP | KEY_DOWN)) {
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

    if (state_ == STATE_PLAYING) {
        if (keys_pressed & KEY_START) {
            state_ = STATE_PAUSED;
            return;
        }

        // 1. Smooth lateral ski carving physics
        const float carve_accel = 28.0f;
        if (keys_down & KEY_LEFT) {
            skier_vx_ -= carve_accel * dt;
        } else if (keys_down & KEY_RIGHT) {
            skier_vx_ += carve_accel * dt;
        } else {
            skier_vx_ *= (1.0f - 4.5f * dt);
        }

        if (skier_vx_ < -9.5f) skier_vx_ = -9.5f;
        if (skier_vx_ > 9.5f) skier_vx_ = 9.5f;

        skier_x_ += skier_vx_ * dt;
        if (skier_x_ < 1.2f) {
            skier_x_ = 1.2f;
            skier_vx_ = 0.0f;
        } else if (skier_x_ > 14.2f) {
            skier_x_ = 14.2f;
            skier_vx_ = 0.0f;
        }

        // 2. Downhill speed boost when skis align with fall-line
        float align = 1.0f - fminf(1.0f, fabsf(skier_vx_) / 8.0f);
        float target_vy = 6.2f + 5.8f * align;
        downhill_speed_ += (target_vy - downhill_speed_) * 4.2f * dt;

        float dy = downhill_speed_ * dt;
        snow_scroll_ += dy;
        if (snow_scroll_ >= 16.0f) snow_scroll_ -= 16.0f;

        // Finish banner scroll & victory check
        if (finish_active_) {
            finish_banner_y_ -= dy;
            if (finish_banner_y_ <= skier_y_) {
                AddScore(200);
                state_ = STATE_VICTORY;
                state_timer_ = 0.0f;
                return;
            }
            return;
        }

        // 3. Scroll slalom gates & judge gate passage
        float max_gate_y = 0.0f;
        for (int i = 0; i < kMaxGates; ++i) {
            if (gates_[i].active && gates_[i].y > max_gate_y) {
                max_gate_y = gates_[i].y;
            }
        }

        for (int i = 0; i < kMaxGates; ++i) {
            if (!gates_[i].active) continue;
            gates_[i].y -= dy;

            if (!gates_[i].judged && gates_[i].y <= skier_y_) {
                gates_[i].judged = true;
                if (skier_x_ >= gates_[i].left_x && skier_x_ <= gates_[i].right_x) {
                    gates_[i].passed = true;
                    combo_++;
                    gates_passed_++;
                    uint32_t mult = (combo_ > 4) ? 4u : (uint32_t)combo_;
                    AddScore(50u * mult);
                    green_flash_timer_ = 0.22f;

                    if (gates_passed_ >= kTargetGates) {
                        finish_active_ = true;
                        finish_banner_y_ = skier_y_ + 4.0f;
                        return;
                    }
                } else {
                    combo_ = 0;
                    missed_gates_++;
                    time_penalty_s_ += 3.0f;
                    downhill_speed_ = 4.5f;
                    red_flash_timer_ = 0.25f;

                    if (missed_gates_ >= 3) {
                        lives_ = 0;
                        state_ = STATE_GAMEOVER;
                        state_timer_ = 0.0f;
                        return;
                    }
                }
            }

            if (gates_[i].y < -1.5f) {
                float next_y = fmaxf(16.5f, max_gate_y + 9.5f);
                max_gate_y = next_y;
                SpawnNextGate(i, next_y);
            }
        }

        // 4. Scroll pine trees & moguls
        for (int i = 0; i < kMaxObstacles; ++i) {
            if (!obstacles_[i].active) continue;
            obstacles_[i].y -= dy;

            if (obstacles_[i].y < -2.0f) {
                obstacles_[i].active = false;
                continue;
            }

            float dx_obs = fabsf(skier_x_ - obstacles_[i].x);
            float dy_obs = fabsf(skier_y_ - obstacles_[i].y);
            if (dx_obs < 0.90f && dy_obs < 0.85f) {
                if (obstacles_[i].type == 0) {
                    // Pine tree crash!
                    obstacles_[i].active = false;
                    if (invuln_timer_ <= 0.0f) {
                        combo_ = 0;
                        red_flash_timer_ = 0.30f;
                        if (lives_ > 1) {
                            lives_--;
                            invuln_timer_ = 0.80f;
                            skier_vx_ = 0.0f;
                            downhill_speed_ = 5.0f;
                        } else {
                            lives_ = 0;
                            state_ = STATE_GAMEOVER;
                            state_timer_ = 0.0f;
                            return;
                        }
                    }
                } else {
                    // Mogul bump: deflect ski edge & damp downhill speed
                    obstacles_[i].active = false;
                    downhill_speed_ *= 0.80f;
                    skier_vx_ += (skier_x_ >= obstacles_[i].x) ? 2.2f : -2.2f;
                }
            }
        }
    }
}

void Game075SlalomSki::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    int scroll_i = (int)floorf(snow_scroll_);
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (x == 0 || x == 15) {
                // Alpine pine border
                bool dark = (((y + scroll_i) % 3) == 0);
                SetPixel75(fb_rgb24, x, y, 15, dark ? 75 : 105, 35);
            } else {
                // Crisp ice-blue / white snow texture
                bool sparkle = (((x * 5 + y + scroll_i) % 7) == 0);
                uint8_t r = sparkle ? 185 : 215;
                uint8_t g = sparkle ? 225 : 235;
                uint8_t b = 252;
                if (green_flash_timer_ > 0.0f && y == 1) {
                    r = 46; g = 230; b = 110;
                } else if (red_flash_timer_ > 0.0f && y == 1) {
                    r = 240; g = 60; b = 60;
                }
                SetPixel75(fb_rgb24, x, y, r, g, b);
            }
        }
    }

    // Obstacles (pine trees & moguls)
    for (int i = 0; i < kMaxObstacles; ++i) {
        if (!obstacles_[i].active) continue;
        int ox = (int)roundf(obstacles_[i].x);
        int oy = (int)roundf(obstacles_[i].y);
        if (obstacles_[i].type == 0) {
            SetPixel75(fb_rgb24, ox, oy - 1, 20, 145, 45);
            SetPixel75(fb_rgb24, ox, oy, 15, 110, 35);
            SetPixel75(fb_rgb24, ox, oy + 1, 110, 65, 25);
        } else {
            SetPixel75(fb_rgb24, ox, oy, 130, 175, 225);
            SetPixel75(fb_rgb24, ox + 1, oy, 150, 195, 240);
        }
    }

    // Paired Red/Blue slalom flag gates
    for (int i = 0; i < kMaxGates; ++i) {
        if (!gates_[i].active) continue;
        int gy = (int)roundf(gates_[i].y);
        int lx = (int)roundf(gates_[i].left_x);
        int rx = (int)roundf(gates_[i].right_x);

        // Faint snow line between gate poles so opening is unmistakable
        for (int gx = lx + 1; gx < rx; ++gx) {
            if (gates_[i].passed) {
                SetPixel75(fb_rgb24, gx, gy, 100, 240, 140);
            } else {
                SetPixel75(fb_rgb24, gx, gy, 175, 210, 245);
            }
        }

        if (gates_[i].is_red_left) {
            SetPixel75(fb_rgb24, lx, gy, 245, 35, 35);
            SetPixel75(fb_rgb24, lx, gy - 1, 255, 80, 60);
            SetPixel75(fb_rgb24, rx, gy, 30, 90, 250);
            SetPixel75(fb_rgb24, rx, gy - 1, 70, 140, 255);
        } else {
            SetPixel75(fb_rgb24, lx, gy, 30, 90, 250);
            SetPixel75(fb_rgb24, lx, gy - 1, 70, 140, 255);
            SetPixel75(fb_rgb24, rx, gy, 245, 35, 35);
            SetPixel75(fb_rgb24, rx, gy - 1, 255, 80, 60);
        }
    }

    // Checkered Finish Banner
    if (finish_active_) {
        int fy = (int)roundf(finish_banner_y_);
        for (int x = 1; x <= 14; ++x) {
            if ((x % 2) == 0) {
                SetPixel75(fb_rgb24, x, fy, 255, 45, 45);
            } else {
                SetPixel75(fb_rgb24, x, fy, 255, 215, 0);
            }
        }
    }

    // Skier + carved ski tracks behind
    int sx = (int)roundf(skier_x_);
    int sy = (int)roundf(skier_y_);
    int lean = (skier_vx_ < -2.0f) ? -1 : ((skier_vx_ > 2.0f) ? 1 : 0);
    SetPixel75(fb_rgb24, sx - lean, sy - 2, 165, 200, 235);
    SetPixel75(fb_rgb24, sx, sy - 1, 255, 210, 40); // Helmet/goggles
    if (invuln_timer_ <= 0.0f || fmodf(anim_timer_, 0.16f) < 0.08f) {
        SetPixel75(fb_rgb24, sx, sy, 235, 45, 35);  // Red racing suit
        SetPixel75(fb_rgb24, sx + lean, sy + 1, 40, 120, 220); // Skis angled in carve direction
    }

    // Top HUD (y=0): lives on left (cyan/green), missed gates warning on right (red)
    for (int x = 0; x < 16; ++x) {
        SetPixel75(fb_rgb24, x, 0, 15, 25, 40);
    }
    for (int l = 0; l < (int)lives_ && l < 3; ++l) {
        SetPixel75(fb_rgb24, 1 + l * 2, 0, 46, 220, 113);
    }
    for (int m = 0; m < missed_gates_ && m < 3; ++m) {
        SetPixel75(fb_rgb24, 14 - m * 2, 0, 245, 50, 50);
    }

    if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPixel75(fb_rgb24, 6, y, 250, 250, 250);
            SetPixel75(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game075SlalomSki::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = lives_;
    st.state = (uint8_t)state_;
    int prog = (gates_passed_ * 100) / kTargetGates;
    if (prog > 100) prog = 100;
    st.progress = (uint8_t)prog;
    return st;
}

static_assert(sizeof(Game075SlalomSki) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
