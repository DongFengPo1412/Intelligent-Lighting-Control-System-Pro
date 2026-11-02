#include "game_053_wrestling.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game053Wrestling::Game053Wrestling()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(3000),
      player_x_(4.0f),
      player_y_(7.5f),
      player_vx_(0.0f),
      player_vy_(0.0f),
      player_mode_(MODE_NEUTRAL),
      player_stamina_(100),
      player_down_timer_(0.0f),
      opp_x_(11.0f),
      opp_y_(7.5f),
      opp_vx_(0.0f),
      opp_vy_(0.0f),
      opp_mode_(MODE_NEUTRAL),
      opp_stamina_(100),
      opp_down_timer_(0.0f),
      opp_ai_timer_(0.0f),
      grapple_advantage_(0),
      grapple_timer_(0.0f),
      pin_timer_(0.0f),
      referee_count_(0) {
}

void Game053Wrestling::Init() {
    Reset();
}

void Game053Wrestling::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    InitMatch();
}

void Game053Wrestling::InitMatch() {
    player_x_ = 4.0f;
    player_y_ = 7.5f;
    player_vx_ = 0.0f;
    player_vy_ = 0.0f;
    player_mode_ = MODE_NEUTRAL;
    player_stamina_ = 100;
    player_down_timer_ = 0.0f;

    opp_x_ = 11.0f;
    opp_y_ = 7.5f;
    opp_vx_ = 0.0f;
    opp_vy_ = 0.0f;
    opp_mode_ = MODE_NEUTRAL;
    opp_stamina_ = 100;
    opp_down_timer_ = 0.0f;
    opp_ai_timer_ = 0.0f;

    grapple_advantage_ = 0;
    grapple_timer_ = 0.0f;
    pin_timer_ = 0.0f;
    referee_count_ = 0;
}

void Game053Wrestling::TriggerGrappleOverpower() {
    grapple_advantage_ = 3;
}

void Game053Wrestling::TriggerPinAttempt() {
    if (opp_mode_ == MODE_DOWNED) {
        player_mode_ = MODE_PINNING;
        pin_timer_ = 0.0f;
        referee_count_ = 0;
    }
}

void Game053Wrestling::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_DEAD) {
        if (state_timer_ > 2.0f) {
            state_ = STATE_START;
        }
        return;
    }

    if (state_ == STATE_VICTORY) {
        if (state_timer_ > 2.5f) {
            state_ = STATE_PLAYING;
            state_timer_ = 0.0f;
            InitMatch();
        }
        return;
    }

    if (player_mode_ == MODE_GRAPPLE) {
        UpdateGrapple(dt, buttons, prev_buttons);
    } else if (player_mode_ == MODE_PINNING || opp_mode_ == MODE_PINNING) {
        UpdatePinning(dt);
    } else {
        UpdatePlayer(dt, buttons, prev_buttons);
        UpdateOpponent(dt);
    }
}

void Game053Wrestling::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (player_mode_ == MODE_DOWNED) {
        player_down_timer_ -= dt;
        if (player_down_timer_ <= 0.0f) {
            player_mode_ = MODE_NEUTRAL;
        }
        return;
    }

    if (player_mode_ == MODE_ROPE_BOUNCE) {
        player_x_ += player_vx_ * dt;
        player_y_ += player_vy_ * dt;

        // Clothesline collision with opponent
        float dist = std::hypot(player_x_ - opp_x_, player_y_ - opp_y_);
        if (dist < 1.4f && opp_mode_ != MODE_DOWNED) {
            opp_stamina_ -= 30;
            opp_mode_ = MODE_DOWNED;
            opp_down_timer_ = 3.0f;
            score_ += 150;
            player_mode_ = MODE_NEUTRAL;
            player_vx_ = 0.0f;
            player_vy_ = 0.0f;
            return;
        }

        // Return to neutral when speed decays or time expires
        player_down_timer_ += dt;
        if (player_down_timer_ > 0.6f || player_x_ < 2.5f || player_x_ > 12.5f) {
            player_mode_ = MODE_NEUTRAL;
            player_vx_ = 0.0f;
            player_vy_ = 0.0f;
        }
        return;
    }

    // Neutral player movement
    float speed = 5.0f;
    player_vx_ = 0.0f;
    player_vy_ = 0.0f;

    if (buttons & BUTTON_LEFT)  player_vx_ = -speed;
    if (buttons & BUTTON_RIGHT) player_vx_ = speed;
    if (buttons & BUTTON_UP)    player_vy_ = -speed;
    if (buttons & BUTTON_DOWN)  player_vy_ = speed;

    player_x_ += player_vx_ * dt;
    player_y_ += player_vy_ * dt;

    // Ring rope collision and spring bounce!
    if (player_x_ <= 2.5f && player_vx_ < 0.0f) {
        player_x_ = 2.5f;
        player_vx_ = 12.0f; // Rebound to right!
        player_mode_ = MODE_ROPE_BOUNCE;
        player_down_timer_ = 0.0f;
        return;
    } else if (player_x_ >= 12.5f && player_vx_ > 0.0f) {
        player_x_ = 12.5f;
        player_vx_ = -12.0f; // Rebound to left!
        player_mode_ = MODE_ROPE_BOUNCE;
        player_down_timer_ = 0.0f;
        return;
    }

    player_x_ = std::max(2.5f, std::min(12.5f, player_x_));
    player_y_ = std::max(2.5f, std::min(12.5f, player_y_));

    // Distance to opponent
    float dist = std::hypot(player_x_ - opp_x_, player_y_ - opp_y_);

    // Button B: Attempt pin on downed opponent
    if ((buttons & BUTTON_B) && !(prev_buttons & BUTTON_B)) {
        if (opp_mode_ == MODE_DOWNED && dist < 1.8f) {
            player_mode_ = MODE_PINNING;
            pin_timer_ = 0.0f;
            referee_count_ = 0;
            return;
        }
    }

    // Button A: Grapple lock-up or strike
    if ((buttons & BUTTON_A) && !(prev_buttons & BUTTON_A)) {
        if (opp_mode_ == MODE_NEUTRAL && dist < 1.6f) {
            player_mode_ = MODE_GRAPPLE;
            opp_mode_ = MODE_GRAPPLE;
            grapple_advantage_ = 0;
            grapple_timer_ = 0.0f;
        }
    }
}

void Game053Wrestling::UpdateOpponent(float dt) {
    if (opp_mode_ == MODE_DOWNED) {
        opp_down_timer_ -= dt;
        if (opp_down_timer_ <= 0.0f) {
            opp_mode_ = MODE_NEUTRAL;
        }
        return;
    }

    if (opp_mode_ == MODE_ROPE_BOUNCE) {
        opp_x_ += opp_vx_ * dt;
        opp_y_ += opp_vy_ * dt;

        float dist = std::hypot(opp_x_ - player_x_, opp_y_ - player_y_);
        if (dist < 1.4f && player_mode_ != MODE_DOWNED) {
            player_stamina_ -= 30;
            player_mode_ = MODE_DOWNED;
            player_down_timer_ = 3.0f;
            opp_mode_ = MODE_NEUTRAL;
            opp_vx_ = 0.0f;
            opp_vy_ = 0.0f;
            return;
        }

        opp_down_timer_ += dt;
        if (opp_down_timer_ > 0.6f || opp_x_ < 2.5f || opp_x_ > 12.5f) {
            opp_mode_ = MODE_NEUTRAL;
            opp_vx_ = 0.0f;
            opp_vy_ = 0.0f;
        }
        return;
    }

    // Opponent AI Movement
    opp_ai_timer_ += dt;
    float dx = player_x_ - opp_x_;
    float dy = player_y_ - opp_y_;
    float dist = std::hypot(dx, dy);

    if (dist > 0.5f) {
        opp_x_ += (dx / dist) * 3.5f * dt;
        opp_y_ += (dy / dist) * 3.5f * dt;
    }

    // If player is downed, AI moves in to pin!
    if (player_mode_ == MODE_DOWNED && dist < 1.5f) {
        opp_mode_ = MODE_PINNING;
        pin_timer_ = 0.0f;
        referee_count_ = 0;
    }

    opp_x_ = std::max(2.5f, std::min(12.5f, opp_x_));
    opp_y_ = std::max(2.5f, std::min(12.5f, opp_y_));
}

void Game053Wrestling::UpdateGrapple(float dt, uint32_t buttons, uint32_t prev_buttons) {
    grapple_timer_ += dt;

    // Player mash A button to build grapple advantage
    if ((buttons & BUTTON_A) && !(prev_buttons & BUTTON_A)) {
        grapple_advantage_++;
    }

    // Opponent resistance pushes back
    if (grapple_timer_ >= 0.25f) {
        grapple_timer_ = 0.0f;
        grapple_advantage_--;
    }

    // Player wins grapple: executes Bodyslam!
    if (grapple_advantage_ >= 3) {
        opp_stamina_ -= 25;
        opp_mode_ = MODE_DOWNED;
        opp_down_timer_ = 3.0f;
        player_mode_ = MODE_NEUTRAL;
        score_ += 100;
        grapple_advantage_ = 0;
    } else if (grapple_advantage_ <= -3) {
        // Opponent wins grapple: suplexes player!
        player_stamina_ -= 25;
        player_mode_ = MODE_DOWNED;
        player_down_timer_ = 3.0f;
        opp_mode_ = MODE_NEUTRAL;
        grapple_advantage_ = 0;
    }
}

void Game053Wrestling::UpdatePinning(float dt) {
    pin_timer_ += dt;

    // Referee counts every 0.8 seconds
    if (pin_timer_ >= 0.8f) {
        pin_timer_ = 0.0f;
        referee_count_++;

        if (player_mode_ == MODE_PINNING) {
            // Check if opponent kicks out
            if (referee_count_ < 3 && opp_stamina_ > 30) {
                // Kick out!
                opp_mode_ = MODE_NEUTRAL;
                player_mode_ = MODE_NEUTRAL;
                referee_count_ = 0;
                return;
            }

            if (referee_count_ >= 3) {
                // 3-COUNT! VICTORY!
                state_ = STATE_VICTORY;
                state_timer_ = 0.0f;
                score_ += 1000;
                if (score_ > high_score_) high_score_ = score_;
            }
        } else if (opp_mode_ == MODE_PINNING) {
            // Check if player kicks out
            if (referee_count_ < 3 && player_stamina_ > 30) {
                player_mode_ = MODE_NEUTRAL;
                opp_mode_ = MODE_NEUTRAL;
                referee_count_ = 0;
                return;
            }

            if (referee_count_ >= 3) {
                // 3-COUNT! Defeat!
                state_ = STATE_DEAD;
                state_timer_ = 0.0f;
            }
        }
    }
}

void Game053Wrestling::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    // Canvas ring (Blue canvas / Red perimeter ropes)
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            if (x >= 2 && x <= 13 && y >= 2 && y <= 13) {
                // Ring mat (Light Blue canvas)
                fb[idx] = 20;
                fb[idx + 1] = 40;
                fb[idx + 2] = 80;

                // Ring ropes (Red boundary border)
                if (x == 2 || x == 13 || y == 2 || y == 13) {
                    fb[idx] = 200;
                    fb[idx + 1] = 30;
                    fb[idx + 2] = 30;
                }

                // Turnbuckle ring posts (White corner turnbuckles)
                if ((x == 2 || x == 13) && (y == 2 || y == 13)) {
                    fb[idx] = 255;
                    fb[idx + 1] = 255;
                    fb[idx + 2] = 255;
                }
            } else {
                // Crowd arena floor
                fb[idx] = 10;
                fb[idx + 1] = 10;
                fb[idx + 2] = 15;
            }
        }
    }

    // Render Opponent (Red trunks wrestler)
    int ox = static_cast<int>(std::round(opp_x_));
    int oy = static_cast<int>(std::round(opp_y_));
    if (ox >= 0 && ox < 16 && oy >= 0 && oy < 16) {
        int idx = (oy * 16 + ox) * 3;
        if (opp_mode_ == MODE_DOWNED) {
            fb[idx] = 180;
            fb[idx + 1] = 20;
            fb[idx + 2] = 20; // Flattened red
        } else {
            fb[idx] = 255;
            fb[idx + 1] = 50;
            fb[idx + 2] = 50; // Active red
        }
    }

    // Render Player (Gold trunks wrestler)
    int px = static_cast<int>(std::round(player_x_));
    int py = static_cast<int>(std::round(player_y_));
    if (px >= 0 && px < 16 && py >= 0 && py < 16) {
        int idx = (py * 16 + px) * 3;
        if (player_mode_ == MODE_DOWNED) {
            fb[idx] = 180;
            fb[idx + 1] = 160;
            fb[idx + 2] = 20;
        } else {
            fb[idx] = 255;
            fb[idx + 1] = 220;
            fb[idx + 2] = 30; // Gold
        }

        // Grapple indicator
        if (player_mode_ == MODE_GRAPPLE) {
            int g_idx = (py * 16 + px) * 3;
            fb[g_idx] = 255;
            fb[g_idx + 1] = 255;
            fb[g_idx + 2] = 255; // White lock-up spark
        }
    }

    // Referee 1-2-3 count display on top bar
    if (player_mode_ == MODE_PINNING || opp_mode_ == MODE_PINNING) {
        for (int c = 0; c < referee_count_ && c < 3; ++c) {
            int idx = (0 * 16 + 7 + c) * 3;
            fb[idx] = 255;
            fb[idx + 1] = 255;
            fb[idx + 2] = 0; // Yellow count pips
        }
    }

    // Stamina bars on row 15 (bottom)
    int p_bars = (player_stamina_ * 5) / 100;
    for (int i = 0; i < p_bars && i < 5; ++i) {
        int idx = (15 * 16 + i) * 3;
        fb[idx] = 0;
        fb[idx + 1] = 255;
        fb[idx + 2] = 0;
    }

    int o_bars = (opp_stamina_ * 5) / 100;
    for (int i = 0; i < o_bars && i < 5; ++i) {
        int idx = (15 * 16 + (15 - i)) * 3;
        fb[idx] = 255;
        fb[idx + 1] = 0;
        fb[idx + 2] = 0;
    }
}

} // namespace arcade
