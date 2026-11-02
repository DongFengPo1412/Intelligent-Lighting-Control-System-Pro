#include "game_078_karatechamp.h"
#include <algorithm>
#include <cmath>
#include <cstdlib>

namespace arcade {

Game078KarateChamp::Game078KarateChamp() {
    Reset();
}

void Game078KarateChamp::Init() {
    Reset();
}

void Game078KarateChamp::Reset() {
    state_ = STATE_FIGHT;
    state_timer_ = 0.0f;
    round_timer_ = 30.0f;
    player_points_ = 0;
    cpu_points_ = 0;
    rounds_won_ = 0;
    dan_level_ = 1;
    score_ = 0;
    ResetRound();
}

void Game078KarateChamp::ResetRound() {
    px_ = 4.0f;
    p_attack_ = ATK_NONE;
    p_atk_timer_ = 0.0f;

    cx_ = 11.0f;
    c_attack_ = ATK_NONE;
    c_atk_timer_ = 0.0f;
    c_ai_think_timer_ = 0.5f;

    round_timer_ = 30.0f;
}

void Game078KarateChamp::StartBonusStage() {
    state_ = STATE_BONUS_STAGE;
    state_timer_ = 0.0f;
    px_ = 5.0f;
    p_attack_ = ATK_NONE;
    p_atk_timer_ = 0.0f;
    bonus_obj_x_ = 15.5f;
    bonus_obj_speed_ = 9.0f;
    bonus_obj_broken_ = false;
}

void Game078KarateChamp::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_GAME_OVER) {
        if (state_timer_ > 2.5f && (buttons & (BUTTON_A | BUTTON_B))) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_POINT_SCORED) {
        if (state_timer_ > 1.4f) {
            if (player_points_ >= 2) {
                state_ = STATE_ROUND_WIN;
                state_timer_ = 0.0f;
                rounds_won_++;
                score_ += 2000;
            } else if (cpu_points_ >= 2) {
                state_ = STATE_GAME_OVER;
                state_timer_ = 0.0f;
            } else {
                state_ = STATE_FIGHT;
                state_timer_ = 0.0f;
                ResetRound();
            }
        }
        return;
    }

    if (state_ == STATE_ROUND_WIN) {
        if (state_timer_ > 1.8f) {
            if (rounds_won_ % 2 == 0) {
                StartBonusStage();
            } else {
                dan_level_++;
                player_points_ = 0;
                cpu_points_ = 0;
                state_ = STATE_FIGHT;
                state_timer_ = 0.0f;
                ResetRound();
            }
        }
        return;
    }

    if (state_ == STATE_BONUS_STAGE) {
        UpdateBonus(dt, buttons, prev_buttons);
        return;
    }

    UpdateFight(dt, buttons, prev_buttons);
}

void Game078KarateChamp::UpdateFight(float dt, uint32_t buttons, uint32_t prev_buttons) {
    round_timer_ = std::max(0.0f, round_timer_ - dt);
    if (round_timer_ <= 0.0f) {
        // Time out: whoever has more points wins, or sudden death draw
        if (player_points_ > cpu_points_) {
            player_points_ = 2;
        } else {
            cpu_points_ = 2;
        }
        state_ = STATE_POINT_SCORED;
        state_timer_ = 0.0f;
        return;
    }

    // 1. Player Attack Timers & Execution
    if (p_atk_timer_ > 0.0f) {
        p_atk_timer_ -= dt;
        if (p_atk_timer_ <= 0.0f) {
            p_attack_ = ATK_NONE;
        }
    } else {
        // Movement
        float move_speed = 4.0f;
        if (buttons & BUTTON_LEFT)  px_ -= move_speed * dt;
        if (buttons & BUTTON_RIGHT) px_ += move_speed * dt;

        // Attack Inputs
        if ((buttons & BUTTON_A) && !(prev_buttons & BUTTON_A)) {
            if (buttons & BUTTON_UP) {
                p_attack_ = ATK_HIGH_KICK;
                p_atk_timer_ = 0.35f;
            } else {
                p_attack_ = ATK_MID_PUNCH;
                p_atk_timer_ = 0.25f;
            }
        } else if ((buttons & BUTTON_B) && !(prev_buttons & BUTTON_B)) {
            if (buttons & BUTTON_DOWN) {
                p_attack_ = ATK_LOW_SWEEP;
                p_atk_timer_ = 0.35f;
            } else {
                p_attack_ = ATK_BLOCK;
                p_atk_timer_ = 0.30f;
            }
        }
    }

    // 2. CPU AI
    if (c_atk_timer_ > 0.0f) {
        c_atk_timer_ -= dt;
        if (c_atk_timer_ <= 0.0f) {
            c_attack_ = ATK_NONE;
        }
    } else {
        c_ai_think_timer_ -= dt;
        float dist = cx_ - px_;

        // Keep karate sparring spacing ~ 2.2 units
        float cpu_speed = 3.6f;
        if (dist > 2.4f) {
            cx_ -= cpu_speed * dt;
        } else if (dist < 1.8f) {
            cx_ += cpu_speed * dt;
        }

        if (c_ai_think_timer_ <= 0.0f) {
            c_ai_think_timer_ = 0.6f + (std::rand() % 40) * 0.01f;
            if (dist < 2.8f) {
                int r = std::rand() % 100;
                if (p_attack_ == ATK_HIGH_KICK || p_attack_ == ATK_MID_PUNCH) {
                    if (r < 45) {
                        c_attack_ = ATK_BLOCK;
                        c_atk_timer_ = 0.35f;
                    }
                } else {
                    if (r < 40) {
                        c_attack_ = ATK_MID_PUNCH;
                        c_atk_timer_ = 0.25f;
                    } else if (r < 75) {
                        c_attack_ = ATK_HIGH_KICK;
                        c_atk_timer_ = 0.35f;
                    } else {
                        c_attack_ = ATK_LOW_SWEEP;
                        c_atk_timer_ = 0.35f;
                    }
                }
            }
        }
    }

    // Spacing constraints
    px_ = std::max(1.0f, std::min(cx_ - 1.4f, px_));
    cx_ = std::max(px_ + 1.4f, std::min(14.5f, cx_));

    CheckHits();
}

void Game078KarateChamp::CheckHits() {
    float dist = cx_ - px_;

    // Player attack connecting
    if (p_atk_timer_ > 0.1f && dist <= 2.2f) {
        if (p_attack_ == ATK_MID_PUNCH) {
            if (c_attack_ != ATK_BLOCK) {
                // Waza-ari (技有 = 1 point)
                player_points_ += 1;
                score_ += 500;
                last_scorer_ = 1;
                judge_call_ = "WAZA-ARI";
                state_ = STATE_POINT_SCORED;
                state_timer_ = 0.0f;
                return;
            }
        } else if (p_attack_ == ATK_HIGH_KICK) {
            if (c_attack_ != ATK_BLOCK && c_attack_ != ATK_LOW_SWEEP) {
                // Ippon (一本 = 2 points)
                player_points_ += 2;
                score_ += 1000;
                last_scorer_ = 1;
                judge_call_ = "IPPON";
                state_ = STATE_POINT_SCORED;
                state_timer_ = 0.0f;
                return;
            }
        } else if (p_attack_ == ATK_LOW_SWEEP) {
            if (c_attack_ != ATK_HIGH_KICK) {
                // Low Sweep Ippon (一本 = 2 points)
                player_points_ += 2;
                score_ += 1000;
                last_scorer_ = 1;
                judge_call_ = "IPPON";
                state_ = STATE_POINT_SCORED;
                state_timer_ = 0.0f;
                return;
            }
        }
    }

    // CPU attack connecting
    if (c_atk_timer_ > 0.1f && dist <= 2.2f) {
        if (c_attack_ == ATK_MID_PUNCH) {
            if (p_attack_ != ATK_BLOCK) {
                cpu_points_ += 1;
                last_scorer_ = 2;
                judge_call_ = "WAZA-ARI";
                state_ = STATE_POINT_SCORED;
                state_timer_ = 0.0f;
                return;
            }
        } else if (c_attack_ == ATK_HIGH_KICK) {
            if (p_attack_ != ATK_BLOCK && p_attack_ != ATK_LOW_SWEEP) {
                cpu_points_ += 2;
                last_scorer_ = 2;
                judge_call_ = "IPPON";
                state_ = STATE_POINT_SCORED;
                state_timer_ = 0.0f;
                return;
            }
        } else if (c_attack_ == ATK_LOW_SWEEP) {
            if (p_attack_ != ATK_HIGH_KICK) {
                cpu_points_ += 2;
                last_scorer_ = 2;
                judge_call_ = "IPPON";
                state_ = STATE_POINT_SCORED;
                state_timer_ = 0.0f;
                return;
            }
        }
    }
}

void Game078KarateChamp::UpdateBonus(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (!bonus_obj_broken_) {
        bonus_obj_x_ -= bonus_obj_speed_ * dt;

        // Player strike input
        if ((buttons & (BUTTON_A | BUTTON_B)) && !(prev_buttons & (BUTTON_A | BUTTON_B))) {
            p_attack_ = ATK_MID_PUNCH;
            p_atk_timer_ = 0.25f;

            if (std::abs(bonus_obj_x_ - px_) < 1.6f) {
                bonus_obj_broken_ = true;
                score_ += 1500;
            }
        }

        if (bonus_obj_x_ < 0.0f) {
            // Object passed untouched
            state_ = STATE_FIGHT;
            state_timer_ = 0.0f;
            player_points_ = 0;
            cpu_points_ = 0;
            dan_level_++;
            ResetRound();
        }
    } else {
        if (state_timer_ > 1.5f) {
            state_ = STATE_FIGHT;
            state_timer_ = 0.0f;
            player_points_ = 0;
            cpu_points_ = 0;
            dan_level_++;
            ResetRound();
        }
    }
}

void Game078KarateChamp::Render(uint8_t* fb) {
    auto set_pixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // 1. Dojo Wooden / Tatami Wall Backdrop
    for (int y = 0; y < 13; ++y) {
        for (int x = 0; x < 16; ++x) {
            set_pixel(x, y, 40, 25, 20); // Warm traditional dojo interior
        }
    }

    // 2. Dojo Tatami Floor (y = 13..15)
    for (int y = 13; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            set_pixel(x, y, 160, 140, 80);
        }
    }

    // 3. Referee in the middle background (x = 7, 8; y = 9..12)
    set_pixel(7, 10, 220, 180, 140); // Ref face
    set_pixel(7, 11, 20, 20, 20);    // Black Ref suit
    set_pixel(8, 11, 20, 20, 20);
    set_pixel(7, 12, 40, 40, 40);
    set_pixel(8, 12, 40, 40, 40);

    // Referee flags on point scored
    if (state_ == STATE_POINT_SCORED) {
        if (last_scorer_ == 1) {
            set_pixel(6, 9, 255, 255, 255); // White flag raised on left
        } else {
            set_pixel(9, 9, 255, 20, 20);   // Red flag raised on right
        }
    }

    // 4. Player (White Karate Gi)
    int px = static_cast<int>(std::round(px_));
    set_pixel(px, 10, 240, 180, 140); // Head
    set_pixel(px, 9, 20, 20, 20);     // Black hair / headband

    if (p_attack_ == ATK_HIGH_KICK) {
        set_pixel(px, 11, 250, 250, 250);
        set_pixel(px + 1, 10, 250, 250, 250); // High leg raised
        set_pixel(px, 12, 240, 240, 240);
    } else if (p_attack_ == ATK_MID_PUNCH) {
        set_pixel(px, 11, 250, 250, 250);
        set_pixel(px + 1, 11, 240, 180, 140); // Punch fist forward
        set_pixel(px, 12, 240, 240, 240);
    } else if (p_attack_ == ATK_LOW_SWEEP) {
        set_pixel(px, 12, 250, 250, 250);
        set_pixel(px + 1, 12, 250, 250, 250); // Sweeping low
    } else if (p_attack_ == ATK_BLOCK) {
        set_pixel(px, 11, 250, 250, 250);
        set_pixel(px - 1, 11, 240, 180, 140); // Defensive arms crossed
        set_pixel(px, 12, 240, 240, 240);
    } else {
        set_pixel(px, 11, 250, 250, 250); // Stance body
        set_pixel(px, 12, 240, 240, 240); // Legs
    }

    // 5. CPU (Red Karate Gi)
    int cx = static_cast<int>(std::round(cx_));
    set_pixel(cx, 10, 240, 180, 140); // Head
    set_pixel(cx, 9, 20, 20, 20);     // Hair

    if (c_attack_ == ATK_HIGH_KICK) {
        set_pixel(cx, 11, 220, 30, 30);
        set_pixel(cx - 1, 10, 220, 30, 30); // High kick toward player
        set_pixel(cx, 12, 200, 20, 20);
    } else if (c_attack_ == ATK_MID_PUNCH) {
        set_pixel(cx, 11, 220, 30, 30);
        set_pixel(cx - 1, 11, 240, 180, 140); // Punch toward player
        set_pixel(cx, 12, 200, 20, 20);
    } else if (c_attack_ == ATK_LOW_SWEEP) {
        set_pixel(cx, 12, 220, 30, 30);
        set_pixel(cx - 1, 12, 220, 30, 30);
    } else if (c_attack_ == ATK_BLOCK) {
        set_pixel(cx, 11, 220, 30, 30);
        set_pixel(cx + 1, 11, 240, 180, 140);
        set_pixel(cx, 12, 200, 20, 20);
    } else {
        set_pixel(cx, 11, 220, 30, 30);
        set_pixel(cx, 12, 200, 20, 20);
    }

    // 6. Bonus Stage Flying Object
    if (state_ == STATE_BONUS_STAGE) {
        int ox = static_cast<int>(std::round(bonus_obj_x_));
        if (!bonus_obj_broken_) {
            set_pixel(ox, 11, 180, 100, 40); // Flying terracotta vase / board
            set_pixel(ox, 10, 220, 120, 50);
        } else {
            set_pixel(ox - 1, 11, 255, 200, 0); // Shatter particles
            set_pixel(ox + 1, 10, 255, 120, 0);
        }
    }

    // 7. Score / Point HUD on top row
    // Player white flags (2 max)
    for (int i = 0; i < player_points_; ++i) {
        set_pixel(i * 2 + 1, 0, 255, 255, 255);
    }
    // CPU red flags (2 max)
    for (int i = 0; i < cpu_points_; ++i) {
        set_pixel(14 - i * 2, 0, 255, 30, 30);
    }
    // Dan belt indicator at middle
    set_pixel(7, 0, 20, 20, 20);
    set_pixel(8, 0, 200, 160, 20);
}

} // namespace arcade
