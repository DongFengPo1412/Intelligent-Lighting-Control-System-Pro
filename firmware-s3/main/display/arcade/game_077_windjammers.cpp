#include "game_077_windjammers.h"
#include <algorithm>
#include <cmath>
#include <cstdlib>

namespace arcade {

Game077Windjammers::Game077Windjammers() {
    Reset();
}

void Game077Windjammers::Init() {
    Reset();
}

void Game077Windjammers::Reset() {
    state_ = STATE_SERVE;
    state_timer_ = 0.0f;
    match_timer_ = 60.0f;
    player_score_ = 0;
    ai_score_ = 0;
    last_scorer_ = 1;
    ResetPoint(1);
}

void Game077Windjammers::ResetPoint(int server) {
    px_ = 3.0f;
    py_ = 7.5f;
    p_dash_timer_ = 0.0f;
    player_charge_ = 0.0f;

    aix_ = 12.0f;
    aiy_ = 7.5f;
    ai_dash_timer_ = 0.0f;
    ai_charge_ = 0.0f;

    disc_.is_super = false;
    disc_.speed = 10.0f;

    if (server == 1) {
        disc_.held_by = 1;
        disc_.x = px_ + 0.8f;
        disc_.y = py_;
        disc_.vx = 0.0f;
        disc_.vy = 0.0f;
        disc_.hold_timer = 1.5f;
    } else {
        disc_.held_by = 2;
        disc_.x = aix_ - 0.8f;
        disc_.y = aiy_;
        disc_.vx = 0.0f;
        disc_.vy = 0.0f;
        disc_.hold_timer = 1.5f;
    }
}

void Game077Windjammers::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_MATCH_OVER) {
        if (state_timer_ > 3.0f && (buttons & (BUTTON_A | BUTTON_B))) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_GOAL) {
        if (state_timer_ > 1.5f) {
            if (player_score_ >= 12 || ai_score_ >= 12 || match_timer_ <= 0.0f) {
                state_ = STATE_MATCH_OVER;
                state_timer_ = 0.0f;
            } else {
                state_ = STATE_SERVE;
                state_timer_ = 0.0f;
                ResetPoint(last_scorer_ == 1 ? 2 : 1);
            }
        }
        return;
    }

    match_timer_ = std::max(0.0f, match_timer_ - dt);
    if (match_timer_ <= 0.0f && state_ == STATE_RALLY) {
        state_ = STATE_MATCH_OVER;
        state_timer_ = 0.0f;
        return;
    }

    UpdatePlayer(dt, buttons, prev_buttons);
    UpdateAI(dt);
    UpdateDisc(dt);
    CheckGoals();
}

void Game077Windjammers::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    float speed = 6.0f;

    if (p_dash_timer_ > 0.0f) {
        p_dash_timer_ -= dt;
        px_ += p_dash_vx_ * 14.0f * dt;
        py_ += p_dash_vy_ * 14.0f * dt;
    } else {
        float move_x = 0.0f;
        float move_y = 0.0f;
        if (buttons & BUTTON_LEFT)  move_x -= 1.0f;
        if (buttons & BUTTON_RIGHT) move_x += 1.0f;
        if (buttons & BUTTON_UP)    move_y -= 1.0f;
        if (buttons & BUTTON_DOWN)  move_y += 1.0f;

        px_ += move_x * speed * dt;
        py_ += move_y * speed * dt;

        // Slide / Dash intercept (Button B when not holding disc)
        if (disc_.held_by != 1 && (buttons & BUTTON_B) && !(prev_buttons & BUTTON_B)) {
            p_dash_vx_ = (move_x != 0.0f || move_y != 0.0f) ? move_x : 1.0f;
            p_dash_vy_ = move_y;
            p_dash_timer_ = 0.22f;
        }
    }

    // Left court boundary
    px_ = std::max(1.0f, std::min(7.0f, px_));
    py_ = std::max(1.0f, std::min(14.0f, py_));

    // Player holding disc
    if (disc_.held_by == 1) {
        disc_.x = px_ + 0.8f;
        disc_.y = py_;
        disc_.hold_timer -= dt;

        // Charge meter builds if held
        player_charge_ = std::min(1.0f, player_charge_ + dt * 1.5f);

        bool throw_btn = (buttons & BUTTON_A) && !(prev_buttons & BUTTON_A);
        bool lob_btn = (buttons & BUTTON_B) && !(prev_buttons & BUTTON_B);

        if (throw_btn || disc_.hold_timer <= 0.0f) {
            disc_.held_by = 0;
            state_ = STATE_RALLY;
            float base_spd = (player_charge_ >= 0.95f) ? 16.0f : 11.0f;
            disc_.is_super = (player_charge_ >= 0.95f);

            float throw_vy = 0.0f;
            if (buttons & BUTTON_UP)   throw_vy = -6.5f;
            if (buttons & BUTTON_DOWN) throw_vy = 6.5f;

            disc_.vx = base_spd;
            disc_.vy = throw_vy;
            player_charge_ = 0.0f;
        } else if (lob_btn) {
            // Lob Shot: slow arcing shot
            disc_.held_by = 0;
            state_ = STATE_RALLY;
            disc_.is_super = false;
            disc_.vx = 7.0f;
            disc_.vy = (buttons & BUTTON_UP) ? -3.0f : ((buttons & BUTTON_DOWN) ? 3.0f : 0.0f);
            player_charge_ = 0.0f;
        }
    } else {
        // Intercept check
        float dx = disc_.x - px_;
        float dy = disc_.y - py_;
        float dist = std::sqrt(dx * dx + dy * dy);
        if (dist < 1.1f && disc_.held_by == 0 && disc_.vx < 0.0f) {
            disc_.held_by = 1;
            disc_.hold_timer = 0.9f;
            disc_.vx = 0.0f;
            disc_.vy = 0.0f;
            player_charge_ = (p_dash_timer_ > 0.0f) ? 0.6f : 0.0f;
        }
    }
}

void Game077Windjammers::UpdateAI(float dt) {
    float ai_speed = 5.2f;

    // AI Court positioning
    if (disc_.held_by == 2) {
        disc_.x = aix_ - 0.8f;
        disc_.y = aiy_;
        disc_.hold_timer -= dt;
        ai_charge_ = std::min(1.0f, ai_charge_ + dt * 1.4f);

        if (disc_.hold_timer <= 0.3f) {
            disc_.held_by = 0;
            state_ = STATE_RALLY;
            bool do_super = (ai_charge_ >= 0.9f);
            disc_.is_super = do_super;
            disc_.vx = do_super ? -15.0f : -10.5f;

            // Target player weak spot
            if (py_ < 7.5f) {
                disc_.vy = 5.5f; // curve down
            } else {
                disc_.vy = -5.5f; // curve up
            }
            ai_charge_ = 0.0f;
        }
    } else {
        // Track disc y
        float target_y = disc_.y;
        if (target_y > aiy_ + 0.3f) aiy_ += ai_speed * dt;
        else if (target_y < aiy_ - 0.3f) aiy_ -= ai_speed * dt;

        // Keep defense baseline around x = 12.0
        float target_x = (disc_.vx > 0.0f && disc_.x > 10.0f) ? disc_.x : 12.5f;
        if (target_x > aix_ + 0.3f) aix_ += ai_speed * dt;
        else if (target_x < aix_ - 0.3f) aix_ -= ai_speed * dt;

        aix_ = std::max(8.5f, std::min(14.5f, aix_));
        aiy_ = std::max(1.0f, std::min(14.0f, aiy_));

        // AI Intercept
        float dx = disc_.x - aix_;
        float dy = disc_.y - aiy_;
        float dist = std::sqrt(dx * dx + dy * dy);
        if (dist < 1.1f && disc_.held_by == 0 && disc_.vx > 0.0f) {
            disc_.held_by = 2;
            disc_.hold_timer = 0.8f;
            disc_.vx = 0.0f;
            disc_.vy = 0.0f;
            ai_charge_ = 0.2f;
        }
    }
}

void Game077Windjammers::UpdateDisc(float dt) {
    if (disc_.held_by != 0) return;

    disc_.x += disc_.vx * dt;
    disc_.y += disc_.vy * dt;

    // Top / Bottom wall rebounds
    if (disc_.y <= 0.5f) {
        disc_.y = 0.5f;
        disc_.vy = std::abs(disc_.vy);
    } else if (disc_.y >= 14.5f) {
        disc_.y = 14.5f;
        disc_.vy = -std::abs(disc_.vy);
    }
}

void Game077Windjammers::CheckGoals() {
    if (disc_.held_by != 0) return;

    // Left Goal Check (AI Scores on Player)
    if (disc_.x <= 0.0f) {
        int pts = (disc_.y >= 5.0f && disc_.y <= 10.0f) ? 5 : 3;
        ai_score_ += pts;
        last_scorer_ = 2;
        state_ = STATE_GOAL;
        state_timer_ = 0.0f;
    }
    // Right Goal Check (Player Scores on AI)
    else if (disc_.x >= 15.0f) {
        int pts = (disc_.y >= 5.0f && disc_.y <= 10.0f) ? 5 : 3;
        player_score_ += pts;
        last_scorer_ = 1;
        state_ = STATE_GOAL;
        state_timer_ = 0.0f;
    }
}

void Game077Windjammers::Render(uint8_t* fb) {
    auto set_pixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // 1. Court Sand / Blue Turf
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            set_pixel(x, y, 10, 30, 60);
        }
    }

    // 2. Goal lines (Left = x:0, Right = x:15)
    for (int y = 0; y < 16; ++y) {
        if (y >= 5 && y <= 10) {
            set_pixel(0, y, 255, 30, 30);  // 5pts Red Zone
            set_pixel(15, y, 255, 30, 30);
        } else {
            set_pixel(0, y, 255, 220, 0);  // 3pts Yellow Zone
            set_pixel(15, y, 255, 220, 0);
        }
    }

    // 3. Center Net (x=7, x=8 dashed)
    for (int y = 0; y < 16; y += 2) {
        set_pixel(7, y, 200, 200, 220);
        set_pixel(8, y, 200, 200, 220);
    }

    // 4. Player (Left Blue Athlete)
    int px = static_cast<int>(std::round(px_));
    int py = static_cast<int>(std::round(py_));
    if (p_dash_timer_ > 0.0f) {
        set_pixel(px, py, 100, 200, 255);
        set_pixel(px - 1, py, 40, 100, 200);
    } else {
        set_pixel(px, py, 30, 140, 255);
        set_pixel(px, py - 1, 255, 200, 140);
        if (player_charge_ >= 0.9f) {
            set_pixel(px, py + 1, 255, 180, 0); // Charge Aura
        }
    }

    // 5. AI (Right Red Athlete)
    int ax = static_cast<int>(std::round(aix_));
    int ay = static_cast<int>(std::round(aiy_));
    set_pixel(ax, ay, 255, 50, 60);
    set_pixel(ax, ay - 1, 255, 200, 140);
    if (ai_charge_ >= 0.9f) {
        set_pixel(ax, ay + 1, 255, 100, 0);
    }

    // 6. Flying Disc
    int dx = static_cast<int>(std::round(disc_.x));
    int dy = static_cast<int>(std::round(disc_.y));
    if (disc_.is_super) {
        set_pixel(dx, dy, 255, 255, 255);
        set_pixel(dx - 1, dy, 255, 120, 0);
        set_pixel(dx + 1, dy, 255, 200, 0);
    } else {
        set_pixel(dx, dy, 255, 255, 80);
    }

    // 7. Score HUD on top (y=0)
    int p_bars = std::min(7, player_score_);
    for (int i = 0; i < p_bars; ++i) {
        set_pixel(i, 0, 50, 180, 255);
    }
    int a_bars = std::min(7, ai_score_);
    for (int i = 0; i < a_bars; ++i) {
        set_pixel(15 - i, 0, 255, 60, 60);
    }
}

} // namespace arcade
