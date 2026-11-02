#include "game_040_dodgeball.h"
#include <cmath>
#include <cstdlib>
#include <algorithm>

namespace arcade {

Game040Dodgeball::Game040Dodgeball()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(0),
      charge_timer_(0.0f),
      catch_window_timer_(0.0f) {
}

void Game040Dodgeball::Init() {
    Reset();
}

void Game040Dodgeball::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    charge_timer_ = 0.0f;
    catch_window_timer_ = 0.0f;

    player_ = {4.0f, 8.0f, 3, true};
    enemy_ = {11.0f, 8.0f, 3, true};

    // Ball starts at center line, slightly towards player
    ball_ = {5.0f, 8.0f, 0.0f, 0.0f, 1, false}; // Player starts with possession
}

void Game040Dodgeball::ThrowBall(bool is_super) {
    if (ball_.state != 1) return;

    float speed = is_super ? 18.0f : 10.5f;
    float dx = enemy_.x - player_.x;
    float dy = enemy_.y - player_.y;
    float dist = sqrtf(dx * dx + dy * dy);
    if (dist < 0.1f) dist = 0.1f;

    ball_.state = 3; // Thrown by Player
    ball_.x = player_.x + 0.8f;
    ball_.y = player_.y;
    ball_.vx = (dx / dist) * speed;
    ball_.vy = (dy / dist) * speed;
    ball_.is_super = is_super;
}

bool Game040Dodgeball::TryCatchBall() {
    if (ball_.state == 4) { // Thrown by Enemy
        float dist = fabsf(player_.x - ball_.x) + fabsf(player_.y - ball_.y);
        if (dist <= 1.45f) {
            // Caught out of mid-air!
            ball_.state = 1; // Held by Player
            ball_.vx = 0.0f;
            ball_.vy = 0.0f;
            ball_.is_super = false;
            score_ += 100; // Catch bonus
            if (score_ > high_score_) high_score_ = score_;
            return true;
        }
    }
    return false;
}

void Game040Dodgeball::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    const float speed = 5.5f;

    // Movement constrained to left half of court [1.5, 7.0] x [3.5, 13.5]
    if (buttons & KEY_LEFT)  player_.x = std::max(1.5f, player_.x - speed * dt);
    if (buttons & KEY_RIGHT) player_.x = std::min(7.0f, player_.x + speed * dt);
    if (buttons & KEY_UP)    player_.y = std::max(3.5f, player_.y - speed * dt);
    if (buttons & KEY_DOWN)  player_.y = std::min(13.5f, player_.y + speed * dt);

    // Ball pickup if ball is free on player's half
    if (ball_.state == 0 && ball_.x <= 7.2f) {
        float dist = fabsf(player_.x - ball_.x) + fabsf(player_.y - ball_.y);
        if (dist <= 1.0f) {
            ball_.state = 1;
            ball_.vx = 0.0f;
            ball_.vy = 0.0f;
        }
    }

    // Ball holding position
    if (ball_.state == 1) {
        ball_.x = player_.x + 0.6f;
        ball_.y = player_.y;

        // Super Shot Charging
        if (buttons & KEY_A) {
            charge_timer_ += dt;
        } else if (prev_buttons & KEY_A) {
            // Release throw
            bool is_super = (charge_timer_ >= 0.5f);
            ThrowBall(is_super);
            charge_timer_ = 0.0f;
        }
    } else {
        charge_timer_ = 0.0f;
    }

    // Catch button (KEY_B)
    if ((buttons & KEY_B) && !(prev_buttons & KEY_B)) {
        TryCatchBall();
    }
}

void Game040Dodgeball::UpdateAI(float dt) {
    const float speed = 4.8f;

    // AI movement constrained to right half [8.0, 13.5] x [3.5, 13.5]
    if (ball_.state == 2) {
        // AI holds ball: align Y with player and throw
        float dy = player_.y - enemy_.y;
        if (fabsf(dy) > 0.5f) {
            enemy_.y += (dy > 0 ? 1.0f : -1.0f) * speed * dt;
        }

        ball_.x = enemy_.x - 0.6f;
        ball_.y = enemy_.y;

        // Throw after holding for 0.6s
        if (state_timer_ >= 0.6f) {
            state_timer_ = 0.0f;
            float b_speed = 10.5f;
            float dx = player_.x - enemy_.x;
            float bdy = player_.y - enemy_.y;
            float dist = sqrtf(dx * dx + bdy * bdy);
            if (dist < 0.1f) dist = 0.1f;

            ball_.state = 4; // Thrown by Enemy
            ball_.x = enemy_.x - 0.8f;
            ball_.y = enemy_.y;
            ball_.vx = (dx / dist) * b_speed;
            ball_.vy = (bdy / dist) * b_speed;
            ball_.is_super = (rand() % 3 == 0); // 33% chance super shot
        }
    } else if (ball_.state == 0 && ball_.x >= 7.5f) {
        // Chase ball on enemy half
        float dx = ball_.x - enemy_.x;
        float dy = ball_.y - enemy_.y;
        float dist = sqrtf(dx * dx + dy * dy);
        if (dist > 0.3f) {
            enemy_.x += (dx / dist) * speed * dt;
            enemy_.y += (dy / dist) * speed * dt;
        } else {
            // Pick up ball
            ball_.state = 2;
            ball_.vx = 0.0f;
            ball_.vy = 0.0f;
            state_timer_ = 0.0f;
        }
    } else {
        // Dodge incoming ball by moving perpendicular
        if (ball_.state == 3) {
            if (fabsf(enemy_.y - ball_.y) < 1.2f) {
                float dodge_dir = (enemy_.y < 8.0f) ? 1.0f : -1.0f;
                enemy_.y += dodge_dir * speed * dt;
            }
        }
    }

    // Clamp
    enemy_.x = std::max(8.0f, std::min(13.5f, enemy_.x));
    enemy_.y = std::max(3.5f, std::min(13.5f, enemy_.y));
}

void Game040Dodgeball::UpdateBall(float dt) {
    if (ball_.state == 3 || ball_.state == 4) {
        ball_.x += ball_.vx * dt;
        ball_.y += ball_.vy * dt;

        // Top / Bottom wall bounce
        if (ball_.y <= 3.0f) {
            ball_.y = 3.0f;
            ball_.vy = -ball_.vy;
        } else if (ball_.y >= 14.0f) {
            ball_.y = 14.0f;
            ball_.vy = -ball_.vy;
        }

        // Out of bounds on left / right ends: drops to ground
        if (ball_.x < 1.0f || ball_.x > 14.5f) {
            ball_.state = 0; // Free on ground
            ball_.vx = 0.0f;
            ball_.vy = 0.0f;
            ball_.is_super = false;
        }
    }
}

void Game040Dodgeball::CheckBallHits() {
    // 1. Ball thrown by Player hits Enemy
    if (ball_.state == 3) {
        float dist = fabsf(enemy_.x - ball_.x) + fabsf(enemy_.y - ball_.y);
        if (dist <= 1.0f) {
            int dmg = ball_.is_super ? 2 : 1;
            enemy_.hp -= dmg;
            score_ += dmg * 150;
            if (score_ > high_score_) high_score_ = score_;

            // Ball rebounds and drops
            ball_.state = 0;
            ball_.vx = 0.0f;
            ball_.vy = 0.0f;
            ball_.is_super = false;

            if (enemy_.hp <= 0) {
                state_ = STATE_VICTORY;
                state_timer_ = 0.0f;
                score_ += 1000;
                if (score_ > high_score_) high_score_ = score_;
            }
        }
    }
    // 2. Ball thrown by Enemy hits Player
    else if (ball_.state == 4) {
        float dist = fabsf(player_.x - ball_.x) + fabsf(player_.y - ball_.y);
        if (dist <= 0.95f) {
            int dmg = ball_.is_super ? 2 : 1;
            player_.hp -= dmg;

            ball_.state = 0;
            ball_.vx = 0.0f;
            ball_.vy = 0.0f;
            ball_.is_super = false;

            if (player_.hp <= 0) {
                state_ = STATE_DEAD;
                state_timer_ = 0.0f;
            }
        }
    }
}

void Game040Dodgeball::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_START) {
        if (buttons & (KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_DEAD || state_ == STATE_VICTORY) {
        if (state_timer_ >= 2.0f && (buttons & (KEY_A | KEY_B))) {
            Reset();
        }
        return;
    }

    UpdatePlayer(dt, buttons, prev_buttons);
    UpdateAI(dt);
    UpdateBall(dt);
    CheckBallHits();
}

void Game040Dodgeball::Render(uint8_t* fb) {
    // 1. Court Floor: Polished Hardwood Parquet (#D35400 / #E67E22)
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            if (y >= 3 && y <= 14 && x >= 1 && x <= 14) {
                fb[idx + 0] = 211; fb[idx + 1] = 84; fb[idx + 2] = 0; // Hardwood Orange
            } else {
                fb[idx + 0] = 30; fb[idx + 1] = 30; fb[idx + 2] = 30; // Outer court dark
            }
        }
    }

    // Center dividing line (White dots at x=7 and x=8, y=3..14)
    for (int y = 3; y <= 14; ++y) {
        int idx = (y * 16 + 7) * 3;
        fb[idx + 0] = 245; fb[idx + 1] = 245; fb[idx + 2] = 245;
    }

    // 2. HUD: Player HP (Left blue dots) and Enemy HP (Right red dots) on Row 0
    for (int h = 0; h < player_.hp && h < 3; ++h) {
        int idx = (0 * 16 + (h + 1)) * 3;
        fb[idx + 0] = 52; fb[idx + 1] = 152; fb[idx + 2] = 219;
    }
    for (int h = 0; h < enemy_.hp && h < 3; ++h) {
        int idx = (0 * 16 + (14 - h)) * 3;
        fb[idx + 0] = 231; fb[idx + 1] = 76; fb[idx + 2] = 60;
    }

    // 3. Enemy Captain (Crimson Gi #E74C3C)
    if (enemy_.hp > 0) {
        int ex = static_cast<int>(std::round(enemy_.x));
        int ey = static_cast<int>(std::round(enemy_.y));
        if (ex >= 0 && ex < 16 && ey >= 0 && ey < 16) {
            int idx = (ey * 16 + ex) * 3;
            fb[idx + 0] = 231; fb[idx + 1] = 76; fb[idx + 2] = 60;
        }
    }

    // 4. Player Captain (Nekketsu Blue Gi #3498DB with White Headband)
    if (player_.hp > 0) {
        int px = static_cast<int>(std::round(player_.x));
        int py = static_cast<int>(std::round(player_.y));
        if (px >= 0 && px < 16 && py >= 0 && py < 16) {
            int idx = (py * 16 + px) * 3;
            if (charge_timer_ >= 0.5f) {
                // Flashing Super Charge Aura
                fb[idx + 0] = 255; fb[idx + 1] = 255; fb[idx + 2] = 255;
            } else {
                fb[idx + 0] = 52; fb[idx + 1] = 152; fb[idx + 2] = 219;
            }
        }
    }

    // 5. The Dodgeball (Glowing White or Fiery Red/Gold if Super Shot)
    int bx = static_cast<int>(std::round(ball_.x));
    int by = static_cast<int>(std::round(ball_.y));
    if (bx >= 0 && bx < 16 && by >= 0 && by < 16) {
        int idx = (by * 16 + bx) * 3;
        if (ball_.is_super) {
            // Blinking supersonic killer ball
            fb[idx + 0] = 255; fb[idx + 1] = 215; fb[idx + 2] = 0; // Gold
        } else {
            fb[idx + 0] = 255; fb[idx + 1] = 255; fb[idx + 2] = 255; // Crisp White Ball
        }
    }
}

} // namespace arcade
