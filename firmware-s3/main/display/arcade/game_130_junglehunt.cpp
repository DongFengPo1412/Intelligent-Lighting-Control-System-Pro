#include "game_130_junglehunt.h"
#include <cmath>
#include <cstdlib>
#include <cstring>

namespace arcade {

Game130JungleHunt::Game130JungleHunt() {
    Init();
}

void Game130JungleHunt::Init() {
    score_ = 0;
    lives_ = 3;
    expedition_round_ = 1;
    stage_ = STAGE_VINES;
    InitStage(stage_);
}

void Game130JungleHunt::Reset() {
    Init();
}

void Game130JungleHunt::InitStage(uint8_t stage) {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    stage_ = stage;
    progress_ = 0.0f;

    px_ = 2.0f;
    py_ = 8.0f;
    pvx_ = 0.0f;
    pvy_ = 0.0f;
    is_jumping_ = false;
    is_ducking_ = false;

    if (stage_ == STAGE_VINES) {
        vine_x_[0] = 5.0f;
        vine_x_[1] = 11.0f;
        vine_angle_[0] = 0.0f;
        vine_angle_[1] = 0.5f;
        current_vine_ = 0;
        in_air_ = false;
    } else if (stage_ == STAGE_RIVER) {
        py_ = 4.0f;
        oxygen_ = 30.0f; // 30 seconds
        is_stabbing_ = false;
        stab_timer_ = 0.0f;

        for (int i = 0; i < 3; ++i) {
            croc_x_[i] = 16.0f + (float)i * 6.0f;
            croc_y_[i] = 5.0f + (float)i * 3.0f;
            croc_vx_[i] = -(2.0f + (float)i * 0.4f + expedition_round_ * 0.2f);
            croc_mouth_open_[i] = (i % 2 == 0);
        }
    } else if (stage_ == STAGE_BOULDERS) {
        py_ = 13.0f;
        for (int i = 0; i < 3; ++i) {
            boulder_x_[i] = 16.0f + (float)i * 7.0f;
            boulder_y_[i] = 13.0f;
            boulder_vx_[i] = -(3.2f + expedition_round_ * 0.3f);
            boulder_is_high_[i] = (i == 1);
        }
    } else if (stage_ == STAGE_RESCUE) {
        px_ = 1.5f;
        py_ = 13.0f;
        native_x_ = 8.0f;
        native_vx_ = 2.2f;
        maiden_y_ = 5.0f;
        maiden_rescued_ = false;
    }
}

void Game130JungleHunt::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & 0x0030) && !(prev_buttons & 0x0030)) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_PLAYER_DYING) {
        if (state_timer_ > 1.3f) {
            lives_--;
            if (lives_ == 0) {
                state_ = STATE_GAME_OVER;
            } else {
                InitStage(stage_);
            }
        }
        return;
    }

    if (state_ == STATE_STAGE_CLEAR) {
        if (state_timer_ > 1.5f) {
            if (stage_ < STAGE_RESCUE) {
                InitStage(stage_ + 1);
            } else {
                expedition_round_++;
                score_ += 2000;
                InitStage(STAGE_VINES);
            }
        }
        return;
    }

    if (stage_ == STAGE_VINES) UpdateVines(dt, buttons, prev_buttons);
    else if (stage_ == STAGE_RIVER) UpdateRiver(dt, buttons, prev_buttons);
    else if (stage_ == STAGE_BOULDERS) UpdateBoulders(dt, buttons, prev_buttons);
    else if (stage_ == STAGE_RESCUE) UpdateRescue(dt, buttons, prev_buttons);
}

void Game130JungleHunt::UpdateVines(float dt, uint16_t buttons, uint16_t prev_buttons) {
    // Sway vines
    float sway_speed = 3.5f + expedition_round_ * 0.2f;
    vine_angle_[0] = std::sin(state_timer_ * sway_speed) * 0.7f;
    vine_angle_[1] = std::sin(state_timer_ * sway_speed + 1.6f) * 0.7f;

    if (!in_air_) {
        // Holding current vine
        float v_len = 7.0f;
        px_ = vine_x_[current_vine_] + std::sin(vine_angle_[current_vine_]) * v_len;
        py_ = 2.0f + std::cos(vine_angle_[current_vine_]) * v_len;

        // Button A: Leap off vine!
        if ((buttons & 0x0010) && !(prev_buttons & 0x0010)) {
            in_air_ = true;
            pvx_ = std::cos(vine_angle_[current_vine_]) * 7.5f;
            pvy_ = -std::sin(vine_angle_[current_vine_]) * 7.5f - 2.0f;
        }
    } else {
        // Flying between vines
        pvy_ += 12.0f * dt; // Gravity
        px_ += pvx_ * dt;
        py_ += pvy_ * dt;

        // Check catch next vine
        int next_vine = 1 - current_vine_;
        float v_tip_x = vine_x_[next_vine] + std::sin(vine_angle_[next_vine]) * 7.0f;
        float v_tip_y = 2.0f + std::cos(vine_angle_[next_vine]) * 7.0f;

        float dist = std::sqrt((px_ - v_tip_x) * (px_ - v_tip_x) + (py_ - v_tip_y) * (py_ - v_tip_y));
        if (dist < 1.4f && pvy_ > -1.0f) {
            in_air_ = false;
            current_vine_ = next_vine;
            progress_ += 25.0f;
            score_ += 100;

            if (progress_ >= 100.0f) {
                state_ = STATE_STAGE_CLEAR;
                state_timer_ = 0.0f;
            }
        }

        // Fall into jungle pit
        if (py_ >= 15.0f) {
            state_ = STATE_PLAYER_DYING;
            state_timer_ = 0.0f;
        }
    }
}

void Game130JungleHunt::UpdateRiver(float dt, uint16_t buttons, uint16_t prev_buttons) {
    // Oxygen depletion
    oxygen_ -= dt;
    if (py_ <= 2.5f) {
        oxygen_ = 30.0f; // Surfaced for air
    }
    if (oxygen_ <= 0.0f) {
        state_ = STATE_PLAYER_DYING;
        state_timer_ = 0.0f;
        return;
    }

    // Swim controls
    float swim_speed = 4.5f;
    if (buttons & 0x0001) py_ -= swim_speed * dt; // UP
    if (buttons & 0x0002) py_ += swim_speed * dt; // DOWN
    if (buttons & 0x0004) px_ -= swim_speed * dt; // LEFT
    if (buttons & 0x0008) {                       // RIGHT
        px_ += swim_speed * dt;
        progress_ += 5.0f * dt;
    }

    if (px_ < 1.0f) px_ = 1.0f;
    if (px_ > 14.5f) {
        px_ = 2.0f;
        progress_ += 35.0f;
    }
    if (py_ < 2.0f) py_ = 2.0f;
    if (py_ > 14.0f) py_ = 14.0f;

    // Knife stab (Button A)
    if (stab_timer_ > 0.0f) stab_timer_ -= dt;
    if ((buttons & 0x0010) && !(prev_buttons & 0x0010)) {
        if (stab_timer_ <= 0.0f) {
            is_stabbing_ = true;
            stab_timer_ = 0.4f;
        }
    }
    if (stab_timer_ <= 0.0f) is_stabbing_ = false;

    // Crocodiles
    for (int i = 0; i < 3; ++i) {
        croc_x_[i] += croc_vx_[i] * dt;
        if (croc_x_[i] < -2.0f) {
            croc_x_[i] = 17.5f;
            croc_mouth_open_[i] = (rand() % 2 == 0);
        }

        // Collision
        float dx = std::abs(px_ - croc_x_[i]);
        float dy = std::abs(py_ - croc_y_[i]);
        if (dx < 1.2f && dy < 0.9f) {
            if (is_stabbing_ && !croc_mouth_open_[i]) {
                // Slay crocodile!
                croc_x_[i] = -5.0f;
                score_ += 200;
            } else {
                // Bitten by crocodile!
                state_ = STATE_PLAYER_DYING;
                state_timer_ = 0.0f;
                break;
            }
        }
    }

    if (progress_ >= 100.0f) {
        state_ = STATE_STAGE_CLEAR;
        state_timer_ = 0.0f;
    }
}

void Game130JungleHunt::UpdateBoulders(float dt, uint16_t buttons, uint16_t prev_buttons) {
    // Jump / Duck
    is_ducking_ = (buttons & 0x0002) != 0; // DOWN

    if ((buttons & 0x0010) && !(prev_buttons & 0x0010)) { // Button A: Jump
        if (!is_jumping_) {
            is_jumping_ = true;
            pvy_ = -8.5f;
        }
    }

    if (is_jumping_) {
        pvy_ += 18.0f * dt;
        py_ += pvy_ * dt;
        if (py_ >= 13.0f) {
            py_ = 13.0f;
            pvy_ = 0.0f;
            is_jumping_ = false;
        }
    }

    // Run right up slope
    if (buttons & 0x0008) {
        px_ += 4.0f * dt;
        progress_ += 8.0f * dt;
    }
    if (buttons & 0x0004) px_ -= 4.0f * dt;

    if (px_ < 1.5f) px_ = 1.5f;
    if (px_ > 14.0f) {
        px_ = 2.0f;
        progress_ += 35.0f;
    }

    // Boulders
    for (int i = 0; i < 3; ++i) {
        boulder_x_[i] += boulder_vx_[i] * dt;
        if (boulder_x_[i] < -2.0f) {
            boulder_x_[i] = 17.5f;
            boulder_is_high_[i] = (rand() % 2 == 0);
        }

        float b_y = boulder_is_high_[i] ? 10.5f : 13.0f;
        float dx = std::abs(px_ - boulder_x_[i]);
        float dy = std::abs(py_ - b_y);

        if (dx < 0.9f) {
            if (boulder_is_high_[i]) {
                // High bouncing boulder hits if player is standing or jumping
                if (!is_ducking_) {
                    state_ = STATE_PLAYER_DYING;
                    state_timer_ = 0.0f;
                    break;
                }
            } else {
                // Low rolling boulder hits unless jumping
                if (dy < 0.8f) {
                    state_ = STATE_PLAYER_DYING;
                    state_timer_ = 0.0f;
                    break;
                }
            }
        }
    }

    if (progress_ >= 100.0f) {
        state_ = STATE_STAGE_CLEAR;
        state_timer_ = 0.0f;
    }
}

void Game130JungleHunt::UpdateRescue(float dt, uint16_t buttons, uint16_t prev_buttons) {
    // Native patrol
    native_x_ += native_vx_ * dt;
    if (native_x_ < 6.0f) { native_x_ = 6.0f; native_vx_ = -native_vx_; }
    if (native_x_ > 11.0f) { native_x_ = 11.0f; native_vx_ = -native_vx_; }

    // Jump
    if ((buttons & 0x0010) && !(prev_buttons & 0x0010)) {
        if (!is_jumping_) {
            is_jumping_ = true;
            pvy_ = -9.0f;
            pvx_ = 4.5f;
        }
    }

    if (is_jumping_) {
        pvy_ += 16.0f * dt;
        px_ += pvx_ * dt;
        py_ += pvy_ * dt;
        if (py_ >= 13.0f) {
            py_ = 13.0f;
            pvx_ = 0.0f;
            pvy_ = 0.0f;
            is_jumping_ = false;
        }
    }

    if (buttons & 0x0004) px_ -= 3.5f * dt;
    if (buttons & 0x0008) px_ += 3.5f * dt;
    if (px_ < 1.0f) px_ = 1.0f;

    // Hit by native spear
    if (std::abs(px_ - native_x_) < 0.85f && py_ >= 12.0f) {
        state_ = STATE_PLAYER_DYING;
        state_timer_ = 0.0f;
        return;
    }

    // Grab rope & rescue maiden at x >= 12.5, y <= 8.0
    if (px_ >= 12.0f && py_ <= 8.5f && is_jumping_) {
        maiden_rescued_ = true;
        state_ = STATE_STAGE_CLEAR;
        state_timer_ = 0.0f;
    }
}

void Game130JungleHunt::Render(uint8_t* fb) {
    if (!fb) return;
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    if (stage_ == STAGE_VINES) {
        // Jungle Canopy Green
        for (int x = 0; x < 16; ++x) set_pixel(x, 1, 30, 120, 40);
        // Vines
        for (int v = 0; v < 2; ++v) {
            int vx = (int)std::round(vine_x_[v] + std::sin(vine_angle_[v]) * 7.0f);
            int vy = (int)std::round(2.0f + std::cos(vine_angle_[v]) * 7.0f);
            set_pixel((int)vine_x_[v], 2, 60, 160, 40);
            set_pixel(vx, vy, 120, 220, 60);
        }
        // Pit at bottom
        for (int x = 0; x < 16; ++x) set_pixel(x, 15, 15, 40, 20);
    } else if (stage_ == STAGE_RIVER) {
        // Water blue
        for (int y = 2; y < 15; ++y) {
            for (int x = 0; x < 16; ++x) set_pixel(x, y, 10, 40, 140);
        }
        // Crocodiles
        for (int c = 0; c < 3; ++c) {
            int cx = (int)std::round(croc_x_[c]);
            int cy = (int)std::round(croc_y_[c]);
            set_pixel(cx, cy, 40, 160, 60);
            set_pixel(cx - 1, cy, 30, 120, 40);
            if (croc_mouth_open_[c]) set_pixel(cx + 1, cy, 255, 60, 40);
        }
        // Oxygen meter on top row 0
        int ox_pips = (int)(oxygen_ / 2.0f);
        for (int o = 0; o < ox_pips && o < 16; ++o) {
            set_pixel(o, 0, 0, 220, 255);
        }
    } else if (stage_ == STAGE_BOULDERS) {
        // Slope terrain
        for (int x = 0; x < 16; ++x) {
            set_pixel(x, 14, 140, 90, 40);
            set_pixel(x, 15, 100, 60, 30);
        }
        // Boulders
        for (int b = 0; b < 3; ++b) {
            int bx = (int)std::round(boulder_x_[b]);
            int by = (int)std::round(boulder_is_high_[b] ? 10.5f : 13.0f);
            set_pixel(bx, by, 180, 160, 140);
        }
    } else if (stage_ == STAGE_RESCUE) {
        // Ground & Cauldron
        for (int x = 0; x < 16; ++x) set_pixel(x, 14, 100, 60, 30);
        set_pixel(13, 13, 255, 60, 20); // Cauldron flame
        set_pixel(13, 12, 60, 60, 60);
        // Maiden
        set_pixel(13, (int)std::round(maiden_y_), 255, 200, 220); // Pink dress
        // Native
        int nx = (int)std::round(native_x_);
        set_pixel(nx, 13, 200, 120, 40);
        set_pixel(nx - 1, 13, 255, 255, 255); // Spear tip
    }

    // Player Explorer
    int px_s = (int)std::round(px_);
    int py_s = (int)std::round(py_);
    if (state_ == STATE_PLAYING || state_ == STATE_STAGE_CLEAR) {
        set_pixel(px_s, py_s, 240, 210, 160); // Explorer skin
        set_pixel(px_s, py_s - 1, 255, 220, 40); // Safari pith helmet
        if (stage_ == STAGE_RIVER && is_stabbing_) {
            set_pixel(px_s + 1, py_s, 255, 255, 255); // Knife
        }
    } else if (state_ == STATE_PLAYER_DYING) {
        set_pixel(px_s, py_s, 255, 60, 40);
        set_pixel(px_s - 1, py_s, 255, 200, 0);
    }

    // Lives
    for (int l = 0; l < lives_ && l < 3; ++l) {
        set_pixel(l * 2, 0, 255, 220, 40);
    }
}

} // namespace arcade
