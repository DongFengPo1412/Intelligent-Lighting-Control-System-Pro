#include "game_118_yiearkungfu.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game118YieArKungFu::Game118YieArKungFu() {
    Reset();
}

void Game118YieArKungFu::Init() {
    Reset();
}

void Game118YieArKungFu::Reset() {
    score_ = 0;
    lives_ = 3;
    round_ = 1;
    InitMatch();
}

void Game118YieArKungFu::InitMatch() {
    state_ = STATE_FIGHTING;
    state_timer_ = 0.0f;
    ai_action_timer_ = 1.0f;

    // Player Oolong
    player_.x = 4.0f;
    player_.y = 13.0f;
    player_.vy = 0.0f;
    player_.hp = 100;
    player_.facing = 1;
    player_.stance = STANCE_IDLE;
    player_.stance_timer = 0.0f;
    player_.hurt_timer = 0.0f;

    // Opponent Master
    opponent_.x = 12.0f;
    opponent_.y = 13.0f;
    opponent_.vy = 0.0f;
    opponent_.hp = 100;
    opponent_.facing = -1;
    opponent_.stance = STANCE_IDLE;
    opponent_.stance_timer = 0.0f;
    opponent_.hurt_timer = 0.0f;

    for (int i = 0; i < MAX_PROJECTILES; ++i) {
        projectiles_[i].active = false;
    }
}

void Game118YieArKungFu::ExecutePlayerAttack(AttackStance stance) {
    if (player_.hurt_timer > 0.0f) return;
    player_.stance = stance;
    if (stance == STANCE_MID_PUNCH) player_.stance_timer = 0.22f;
    else if (stance == STANCE_MID_KICK) player_.stance_timer = 0.25f;
    else if (stance == STANCE_HIGH_JUMP_KICK) player_.stance_timer = 0.35f;
    else if (stance == STANCE_LOW_SWEEP) player_.stance_timer = 0.28f;
}

void Game118YieArKungFu::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_KO_VICTORY) {
        if (state_timer_ > 1.8f) {
            round_++;
            score_ += 1000;
            InitMatch();
        }
        return;
    }

    if (state_ == STATE_PLAYER_DEFEATED) {
        if (state_timer_ > 1.8f) {
            lives_--;
            if (lives_ <= 0) {
                state_ = STATE_GAME_OVER;
            } else {
                InitMatch();
            }
        }
        return;
    }

    UpdatePlayer(dt, buttons, prev_buttons);
    UpdateOpponentAI(dt);
    UpdateProjectiles(dt);
    CheckStrikesAndParries();
}

void Game118YieArKungFu::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    // Hurt recovery
    if (player_.hurt_timer > 0.0f) {
        player_.hurt_timer -= dt;
        player_.stance = STANCE_IDLE;
        return;
    }

    // Stance timer
    if (player_.stance_timer > 0.0f) {
        player_.stance_timer -= dt;
        if (player_.stance_timer <= 0.0f) {
            player_.stance = STANCE_IDLE;
        }
    }

    // Gravity for aerial moves
    if (player_.y < 13.0f || player_.vy < 0.0f) {
        player_.vy += 12.0f * dt;
        player_.y += player_.vy * dt;
        if (player_.y >= 13.0f) {
            player_.y = 13.0f;
            player_.vy = 0.0f;
        }
    }

    // Movement (only if not attacking or crouching)
    float move_spd = 4.5f;
    if (player_.stance == STANCE_IDLE) {
        if (buttons & BTN_LEFT) {
            player_.x -= move_spd * dt;
        }
        if (buttons & BTN_RIGHT) {
            player_.x += move_spd * dt;
        }

        // Jump
        if ((buttons & BTN_UP) && player_.y >= 13.0f) {
            player_.vy = -4.2f;
        }
    }

    // Facing direction
    if (player_.x < opponent_.x) player_.facing = 1;
    else player_.facing = -1;

    // Bounds
    player_.x = std::max(1.5f, std::min(14.5f, player_.x));

    // Attack Inputs
    if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
        ExecutePlayerAttack(STANCE_MID_PUNCH);
    } else if ((buttons & BTN_B) && !(prev_buttons & BTN_B)) {
        if (player_.y < 12.5f || (buttons & BTN_UP)) {
            // High Jump Kick
            if (player_.y >= 13.0f) player_.vy = -4.0f;
            ExecutePlayerAttack(STANCE_HIGH_JUMP_KICK);
        } else if (buttons & BTN_DOWN) {
            // Low Sweeping Leg Kick
            ExecutePlayerAttack(STANCE_LOW_SWEEP);
        } else {
            // Mid Front Kick
            ExecutePlayerAttack(STANCE_MID_KICK);
        }
    }
}

void Game118YieArKungFu::UpdateOpponentAI(float dt) {
    if (opponent_.hurt_timer > 0.0f) {
        opponent_.hurt_timer -= dt;
        opponent_.stance = STANCE_IDLE;
        return;
    }

    if (opponent_.stance_timer > 0.0f) {
        opponent_.stance_timer -= dt;
        if (opponent_.stance_timer <= 0.0f) {
            opponent_.stance = STANCE_IDLE;
        }
    }

    // Facing direction
    if (opponent_.x < player_.x) opponent_.facing = 1;
    else opponent_.facing = -1;

    // Distance tracking
    float dx = player_.x - opponent_.x;
    float dist = std::abs(dx);

    ai_action_timer_ -= dt;
    if (ai_action_timer_ <= 0.0f) {
        ai_action_timer_ = 1.0f + static_cast<float>(rand() % 8) * 0.1f;

        if (dist > 4.5f) {
            // Throw ninja star projectile towards player!
            for (int i = 0; i < MAX_PROJECTILES; ++i) {
                if (!projectiles_[i].active) {
                    projectiles_[i].x = opponent_.x + static_cast<float>(opponent_.facing) * 0.8f;
                    projectiles_[i].y = 12.0f;
                    projectiles_[i].vx = static_cast<float>(opponent_.facing) * 7.5f;
                    projectiles_[i].active = true;
                    break;
                }
            }
        } else if (dist <= 2.2f) {
            // Strike at player!
            opponent_.stance = (rand() % 2 == 0) ? STANCE_MID_PUNCH : STANCE_MID_KICK;
            opponent_.stance_timer = 0.25f;
        }
    }

    // Movement
    if (opponent_.stance == STANCE_IDLE) {
        float step = 2.8f * dt;
        if (dist > 2.0f) {
            opponent_.x += static_cast<float>(opponent_.facing) * step;
        } else if (dist < 1.4f) {
            opponent_.x -= static_cast<float>(opponent_.facing) * step;
        }
    }

    opponent_.x = std::max(1.5f, std::min(14.5f, opponent_.x));
}

void Game118YieArKungFu::UpdateProjectiles(float dt) {
    for (int i = 0; i < MAX_PROJECTILES; ++i) {
        if (!projectiles_[i].active) continue;
        projectiles_[i].x += projectiles_[i].vx * dt;
        if (projectiles_[i].x < 0.5f || projectiles_[i].x > 15.5f) {
            projectiles_[i].active = false;
        }
    }
}

void Game118YieArKungFu::CheckStrikesAndParries() {
    // 1. Player parry against projectile
    if (player_.stance != STANCE_IDLE) {
        for (int i = 0; i < MAX_PROJECTILES; ++i) {
            if (!projectiles_[i].active) continue;
            float dx = std::abs(player_.x - projectiles_[i].x);
            float dy = std::abs(player_.y - projectiles_[i].y);
            if (dx < 1.4f && dy < 1.6f) {
                // Deflected!
                projectiles_[i].active = false;
                score_ += 100; // Parry bonus!
            }
        }
    }

    // 2. Projectile hit player
    for (int i = 0; i < MAX_PROJECTILES; ++i) {
        if (!projectiles_[i].active) continue;
        float dx = std::abs(player_.x - projectiles_[i].x);
        float dy = std::abs(player_.y - projectiles_[i].y);
        if (dx < 0.8f && dy < 1.2f) {
            // Low sweep ducks under projectile at y=12.0
            if (player_.stance == STANCE_LOW_SWEEP) {
                continue; // Ducked!
            }
            projectiles_[i].active = false;
            player_.hp -= 15;
            player_.hurt_timer = 0.3f;
            player_.x -= static_cast<float>(player_.facing) * 0.8f;
            if (player_.hp <= 0) {
                player_.hp = 0;
                state_ = STATE_PLAYER_DEFEATED;
                state_timer_ = 0.0f;
            }
        }
    }

    // 3. Player strike opponent
    if (player_.stance != STANCE_IDLE && opponent_.hurt_timer <= 0.0f) {
        float reach = 1.6f;
        int damage = 10;
        if (player_.stance == STANCE_MID_KICK) { reach = 2.0f; damage = 15; }
        else if (player_.stance == STANCE_HIGH_JUMP_KICK) { reach = 2.4f; damage = 25; }
        else if (player_.stance == STANCE_LOW_SWEEP) { reach = 1.8f; damage = 18; }

        float target_x = player_.x + static_cast<float>(player_.facing) * reach;
        if (std::abs(target_x - opponent_.x) < 1.2f && std::abs(player_.y - opponent_.y) < 1.8f) {
            // Direct Hit!
            opponent_.hp -= damage;
            opponent_.hurt_timer = 0.28f;
            opponent_.x += static_cast<float>(player_.facing) * 1.2f;
            score_ += damage * 10;

            if (opponent_.hp <= 0) {
                opponent_.hp = 0;
                state_ = STATE_KO_VICTORY;
                state_timer_ = 0.0f;
            }
        }
    }

    // 4. Opponent strike player
    if (opponent_.stance != STANCE_IDLE && player_.hurt_timer <= 0.0f) {
        float reach = 1.8f;
        float target_x = opponent_.x + static_cast<float>(opponent_.facing) * reach;
        if (std::abs(target_x - player_.x) < 1.1f && std::abs(opponent_.y - player_.y) < 1.6f) {
            // Low sweep ducks under mid punches
            if (player_.stance == STANCE_LOW_SWEEP && opponent_.stance == STANCE_MID_PUNCH) {
                // Evaded!
            } else {
                player_.hp -= 12;
                player_.hurt_timer = 0.28f;
                player_.x += static_cast<float>(opponent_.facing) * 1.0f;
                if (player_.hp <= 0) {
                    player_.hp = 0;
                    state_ = STATE_PLAYER_DEFEATED;
                    state_timer_ = 0.0f;
                }
            }
        }
    }
}

void Game118YieArKungFu::Render(uint8_t* fb) {
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

    // 1. Health Bars on Top Row (y = 0)
    // Player HP (Green/Cyan, x = 0..6)
    int p_bars = static_cast<int>((player_.hp / 100.0f) * 7.0f);
    for (int i = 0; i < p_bars; ++i) {
        set_pixel(i, 0, 40, 220, 80);
    }
    // Opponent HP (Crimson/Yellow, x = 9..15)
    int o_bars = static_cast<int>((opponent_.hp / 100.0f) * 7.0f);
    for (int i = 0; i < o_bars; ++i) {
        set_pixel(15 - i, 0, 255, 40, 30);
    }

    // 2. Dojo Floor (y = 14..15) & Temple Pillars
    for (int x = 0; x < 16; ++x) {
        set_pixel(x, 14, 180, 100, 40); // Hardwood mat
        set_pixel(x, 15, 120, 60, 20);
    }
    set_pixel(1, 13, 200, 40, 30);  // Left red pagoda pillar
    set_pixel(14, 13, 200, 40, 30); // Right red pagoda pillar

    // 3. Projectiles (Shurikens)
    for (int i = 0; i < MAX_PROJECTILES; ++i) {
        if (!projectiles_[i].active) continue;
        int sx = static_cast<int>(std::round(projectiles_[i].x));
        int sy = static_cast<int>(std::round(projectiles_[i].y));
        set_pixel(sx, sy, 0, 255, 255); // Cyan spinning star
    }

    // 4. Opponent Master
    int ox = static_cast<int>(std::round(opponent_.x));
    int oy = static_cast<int>(std::round(opponent_.y));

    if (opponent_.hurt_timer > 0.0f) {
        // Recoil flash
        set_pixel(ox, oy, 255, 255, 255);
        set_pixel(ox, oy - 1, 255, 80, 40);
    } else {
        // Crimson martial arts robe
        set_pixel(ox, oy, 220, 40, 30);
        set_pixel(ox, oy - 1, 255, 200, 140); // Head
        set_pixel(ox, oy + 1, 40, 40, 50);    // Boots
        if (opponent_.stance != STANCE_IDLE) {
            set_pixel(ox + opponent_.facing, oy, 255, 200, 40); // Attack strike
        }
    }

    // 5. Player Oolong
    int px = static_cast<int>(std::round(player_.x));
    int py = static_cast<int>(std::round(player_.y));

    if (player_.hurt_timer > 0.0f) {
        set_pixel(px, py, 255, 255, 255);
        set_pixel(px, py - 1, 255, 60, 40);
    } else if (player_.stance == STANCE_LOW_SWEEP) {
        // Low crouching kick along ground
        set_pixel(px, py, 255, 255, 255);
        set_pixel(px + player_.facing, py, 40, 100, 240);
        set_pixel(px + player_.facing * 2, py, 255, 200, 140);
    } else if (player_.stance == STANCE_HIGH_JUMP_KICK) {
        // Aerial flying kick
        set_pixel(px, py, 255, 255, 255);
        set_pixel(px, py - 1, 255, 200, 140);
        set_pixel(px + player_.facing, py, 40, 100, 240);
    } else {
        // Standing stance / Punch / Kick
        set_pixel(px, py, 255, 255, 255); // White Gi
        set_pixel(px, py - 1, 255, 200, 140); // Head
        set_pixel(px, py + 1, 40, 100, 240);  // Blue trousers

        if (player_.stance == STANCE_MID_PUNCH) {
            set_pixel(px + player_.facing, py, 255, 200, 140); // Extended fist
        } else if (player_.stance == STANCE_MID_KICK) {
            set_pixel(px + player_.facing, py, 40, 100, 240);  // Extended foot
        }
    }
}

} // namespace arcade
