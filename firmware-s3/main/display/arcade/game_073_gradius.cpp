#include "game_073_gradius.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game073Gradius::Game073Gradius()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(9000),
      lives_(3),
      px_(2.0f),
      py_(8.0f),
      shoot_cooldown_(0.0f),
      missile_cooldown_(0.0f),
      meter_slot_(0),
      has_speed_up_(false),
      has_missile_(false),
      has_double_(false),
      has_laser_(false),
      has_option_(false),
      shield_hp_(0),
      trail_idx_(0),
      enemies_defeated_(0),
      boss_active_(false),
      boss_x_(13.0f),
      boss_y_(8.0f),
      boss_vy_(2.5f),
      boss_barrier_health_(4),
      boss_core_health_(4),
      boss_shoot_cooldown_(1.2f) {
}

void Game073Gradius::Init() {
    Reset();
}

void Game073Gradius::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    lives_ = 3;
    InitStage();
}

void Game073Gradius::InitStage() {
    px_ = 2.0f;
    py_ = 8.0f;
    shoot_cooldown_ = 0.0f;
    missile_cooldown_ = 0.0f;
    meter_slot_ = 0;
    has_speed_up_ = false;
    has_missile_ = false;
    has_double_ = false;
    has_laser_ = false;
    has_option_ = false;
    shield_hp_ = 0;
    trail_idx_ = 0;
    enemies_defeated_ = 0;
    boss_active_ = false;
    boss_x_ = 13.0f;
    boss_y_ = 8.0f;
    boss_vy_ = 2.5f;
    boss_barrier_health_ = 4;
    boss_core_health_ = 4;
    boss_shoot_cooldown_ = 1.2f;

    for (int i = 0; i < TRAIL_SIZE; ++i) {
        trail_[i] = {px_, py_};
    }

    for (int i = 0; i < MAX_SHOTS; ++i) shots_[i].active = false;
    for (int i = 0; i < MAX_MISSILES; ++i) missiles_[i].active = false;
    for (int i = 0; i < MAX_CAPSULES; ++i) capsules_[i].active = false;

    // Formation scout enemies (red type 0 drops capsule)
    enemies_[0] = {16.0f, 4.0f, -3.0f, 0.0f, 0, 1, true};
    enemies_[1] = {18.0f, 7.0f, -3.0f, 0.0f, 0, 1, true};
    enemies_[2] = {20.0f, 10.0f, -3.0f, 0.0f, 0, 1, true};
    enemies_[3] = {15.0f, 13.0f, -2.5f, 0.0f, 1, 1, true};
}

void Game073Gradius::CollectCapsule() {
    meter_slot_ = (meter_slot_ % 6) + 1;
    score_ += 100;
}

void Game073Gradius::ActivatePowerMeter() {
    if (meter_slot_ == 0) return;

    if (meter_slot_ == TIER_SPEED_UP) {
        has_speed_up_ = true;
    } else if (meter_slot_ == TIER_MISSILE) {
        has_missile_ = true;
    } else if (meter_slot_ == TIER_DOUBLE) {
        has_double_ = true;
        has_laser_ = false;
    } else if (meter_slot_ == TIER_LASER) {
        has_laser_ = true;
        has_double_ = false;
    } else if (meter_slot_ == TIER_OPTION) {
        has_option_ = true;
    } else if (meter_slot_ == TIER_SHIELD) {
        shield_hp_ = 2;
    }

    meter_slot_ = 0; // Consumed!
    score_ += 200;
}

void Game073Gradius::Shoot() {
    if (shoot_cooldown_ > 0.0f) return;

    // 1. Main cannon / Laser
    for (int i = 0; i < MAX_SHOTS; ++i) {
        if (!shots_[i].active) {
            shots_[i].active = true;
            shots_[i].x = px_ + 1.2f;
            shots_[i].y = py_;
            shots_[i].vx = 16.0f;
            shots_[i].vy = 0.0f;
            shots_[i].is_laser = has_laser_;
            break;
        }
    }

    // 2. Double 45-degree upward shot
    if (has_double_) {
        for (int i = 0; i < MAX_SHOTS; ++i) {
            if (!shots_[i].active) {
                shots_[i].active = true;
                shots_[i].x = px_ + 0.8f;
                shots_[i].y = py_ - 0.8f;
                shots_[i].vx = 12.0f;
                shots_[i].vy = -12.0f;
                shots_[i].is_laser = false;
                break;
            }
        }
    }

    // 3. Option shot
    if (has_option_) {
        int opt_idx = (trail_idx_ + TRAIL_SIZE / 2) % TRAIL_SIZE;
        for (int i = 0; i < MAX_SHOTS; ++i) {
            if (!shots_[i].active) {
                shots_[i].active = true;
                shots_[i].x = trail_[opt_idx].x + 1.0f;
                shots_[i].y = trail_[opt_idx].y;
                shots_[i].vx = 16.0f;
                shots_[i].vy = 0.0f;
                shots_[i].is_laser = has_laser_;
                break;
            }
        }
    }

    // 4. Missile drop
    if (has_missile_ && missile_cooldown_ <= 0.0f) {
        for (int i = 0; i < MAX_MISSILES; ++i) {
            if (!missiles_[i].active) {
                missiles_[i].active = true;
                missiles_[i].x = px_;
                missiles_[i].y = py_ + 0.6f;
                missiles_[i].vx = 7.0f;
                missiles_[i].vy = 6.0f;
                missile_cooldown_ = 0.5f;
                break;
            }
        }
    }

    shoot_cooldown_ = 0.22f;
}

void Game073Gradius::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_DEAD) {
        if (state_timer_ > 1.8f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                state_timer_ = 0.0f;
                px_ = 2.0f;
                py_ = 8.0f;
                shield_hp_ = 0;
            } else {
                state_ = STATE_START;
            }
        }
        return;
    }

    if (state_ == STATE_VICTORY) {
        if (state_timer_ > 2.5f) {
            state_ = STATE_PLAYING;
            state_timer_ = 0.0f;
            InitStage();
        }
        return;
    }

    if (shoot_cooldown_ > 0.0f) shoot_cooldown_ -= dt;
    if (missile_cooldown_ > 0.0f) missile_cooldown_ -= dt;

    UpdatePlayer(dt, buttons, prev_buttons);
    UpdateProjectiles(dt);

    if (boss_active_) {
        UpdateBoss(dt);
    } else {
        UpdateEnemies(dt);
        if (enemies_defeated_ >= 6) {
            boss_active_ = true;
            boss_x_ = 13.0f;
            boss_y_ = 8.0f;
            for (int i = 0; i < MAX_ENEMIES; ++i) enemies_[i].active = false;
        }
    }

    CheckCollisions();
}

void Game073Gradius::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    float speed = has_speed_up_ ? 8.5f : 5.5f;

    if (buttons & BUTTON_LEFT)  px_ -= speed * dt;
    if (buttons & BUTTON_RIGHT) px_ += speed * dt;
    if (buttons & BUTTON_UP)    py_ -= speed * dt;
    if (buttons & BUTTON_DOWN)  py_ += speed * dt;

    px_ = std::max(1.0f, std::min(14.5f, px_));
    py_ = std::max(2.0f, std::min(13.5f, py_));

    // Record trail node for Option
    trail_[trail_idx_] = {px_, py_};
    trail_idx_ = (trail_idx_ + 1) % TRAIL_SIZE;

    // Button A: Shoot
    if ((buttons & BUTTON_A) && !(prev_buttons & BUTTON_A)) {
        Shoot();
    }

    // Button B: Activate Power Meter
    if ((buttons & BUTTON_B) && !(prev_buttons & BUTTON_B)) {
        ActivatePowerMeter();
    }
}

void Game073Gradius::UpdateProjectiles(float dt) {
    for (int i = 0; i < MAX_SHOTS; ++i) {
        if (!shots_[i].active) continue;
        shots_[i].x += shots_[i].vx * dt;
        shots_[i].y += shots_[i].vy * dt;
        if (shots_[i].x > 15.5f || shots_[i].y < 1.0f || shots_[i].y > 14.5f) {
            shots_[i].active = false;
        }
    }

    for (int i = 0; i < MAX_MISSILES; ++i) {
        if (!missiles_[i].active) continue;
        missiles_[i].x += missiles_[i].vx * dt;
        missiles_[i].y += missiles_[i].vy * dt;
        if (missiles_[i].x > 15.5f || missiles_[i].y > 14.0f) {
            missiles_[i].active = false;
        }
    }

    // Capsules drift left
    for (int i = 0; i < MAX_CAPSULES; ++i) {
        if (!capsules_[i].active) continue;
        capsules_[i].x -= 2.0f * dt;
        if (capsules_[i].x < 0.0f) capsules_[i].active = false;
    }
}

void Game073Gradius::UpdateEnemies(float dt) {
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;

        enemies_[i].x += enemies_[i].vx * dt;
        enemies_[i].y += std::sin(state_timer_ * 4.0f + i) * 2.0f * dt;

        if (enemies_[i].x < -1.5f) {
            enemies_[i].x = 17.0f + (i * 3.0f);
            enemies_[i].health = 1;
        }
    }
}

void Game073Gradius::UpdateBoss(float dt) {
    boss_y_ += boss_vy_ * dt;
    if (boss_y_ < 4.5f) {
        boss_y_ = 4.5f;
        boss_vy_ = std::abs(boss_vy_);
    } else if (boss_y_ > 10.5f) {
        boss_y_ = 10.5f;
        boss_vy_ = -std::abs(boss_vy_);
    }

    boss_shoot_cooldown_ -= dt;
    if (boss_shoot_cooldown_ <= 0.0f) {
        boss_shoot_cooldown_ = 1.3f;
        // Boss fires dual blue laser beams
        for (int dy = -1; dy <= 1; dy += 2) {
            for (int i = 0; i < MAX_SHOTS; ++i) {
                if (!shots_[i].active) {
                    shots_[i].active = true;
                    shots_[i].x = boss_x_ - 1.5f;
                    shots_[i].y = boss_y_ + dy * 1.5f;
                    shots_[i].vx = -12.0f;
                    shots_[i].vy = 0.0f;
                    shots_[i].is_laser = true;
                    break;
                }
            }
        }
    }
}

void Game073Gradius::CheckCollisions() {
    // 1. Player shots hit enemies & Boss
    for (int s = 0; s < MAX_SHOTS; ++s) {
        if (!shots_[s].active || shots_[s].vx < 0.0f) continue; // Only player shots

        if (boss_active_) {
            // Hit Big Core barrier or Core
            if (std::abs(shots_[s].x - (boss_x_ - 1.0f)) < 1.4f &&
                std::abs(shots_[s].y - boss_y_) < 2.0f) {
                shots_[s].active = false;
                if (boss_barrier_health_ > 0) {
                    boss_barrier_health_--;
                    score_ += 50;
                } else {
                    // Penetrating hit directly into blue Core!
                    boss_core_health_--;
                    score_ += 200;
                    if (boss_core_health_ <= 0) {
                        boss_active_ = false;
                        state_ = STATE_VICTORY;
                        state_timer_ = 0.0f;
                        score_ += 3500;
                        if (score_ > high_score_) high_score_ = score_;
                        return;
                    }
                }
            }
        } else {
            for (int e = 0; e < MAX_ENEMIES; ++e) {
                if (!enemies_[e].active) continue;
                if (std::abs(shots_[s].x - enemies_[e].x) < 1.2f &&
                    std::abs(shots_[s].y - enemies_[e].y) < 1.2f) {
                    if (!shots_[s].is_laser) shots_[s].active = false; // Laser penetrates!
                    enemies_[e].health--;
                    if (enemies_[e].health <= 0) {
                        enemies_[e].active = false;
                        enemies_defeated_++;
                        score_ += 150;

                        // Red scouts drop capsule
                        if (enemies_[e].type == 0) {
                            for (int c = 0; c < MAX_CAPSULES; ++c) {
                                if (!capsules_[c].active) {
                                    capsules_[c].active = true;
                                    capsules_[c].x = enemies_[e].x;
                                    capsules_[c].y = enemies_[e].y;
                                    break;
                                }
                            }
                        }

                        if (enemies_defeated_ >= 6) {
                            boss_active_ = true;
                            boss_x_ = 13.0f;
                            boss_y_ = 8.0f;
                            for (int k = 0; k < MAX_ENEMIES; ++k) enemies_[k].active = false;
                        }
                    }
                    break;
                }
            }
        }
    }

    // 2. Missiles hit enemies
    for (int m = 0; m < MAX_MISSILES; ++m) {
        if (!missiles_[m].active) continue;
        for (int e = 0; e < MAX_ENEMIES; ++e) {
            if (!enemies_[e].active) continue;
            if (std::abs(missiles_[m].x - enemies_[e].x) < 1.2f &&
                std::abs(missiles_[m].y - enemies_[e].y) < 1.2f) {
                missiles_[m].active = false;
                enemies_[e].active = false;
                enemies_defeated_++;
                score_ += 200;
                break;
            }
        }
    }

    // 3. Player collects Capsule
    for (int c = 0; c < MAX_CAPSULES; ++c) {
        if (!capsules_[c].active) continue;
        if (std::abs(px_ - capsules_[c].x) < 1.3f &&
            std::abs(py_ - capsules_[c].y) < 1.3f) {
            capsules_[c].active = false;
            CollectCapsule();
            break;
        }
    }

    // 4. Enemy / Boss shots hit Vic Viper
    for (int s = 0; s < MAX_SHOTS; ++s) {
        if (!shots_[s].active || shots_[s].vx > 0.0f) continue; // Enemy shot
        if (std::abs(px_ - shots_[s].x) < 1.0f && std::abs(py_ - shots_[s].y) < 1.0f) {
            shots_[s].active = false;
            if (shield_hp_ > 0) {
                shield_hp_--;
            } else {
                lives_--;
                state_ = STATE_DEAD;
                state_timer_ = 0.0f;
                return;
            }
        }
    }

    // Direct collision
    for (int e = 0; e < MAX_ENEMIES; ++e) {
        if (!enemies_[e].active) continue;
        if (std::abs(px_ - enemies_[e].x) < 1.0f && std::abs(py_ - enemies_[e].y) < 1.0f) {
            if (shield_hp_ > 0) {
                shield_hp_--;
                enemies_[e].active = false;
            } else {
                lives_--;
                state_ = STATE_DEAD;
                state_timer_ = 0.0f;
                return;
            }
        }
    }
}

void Game073Gradius::Render(uint8_t* fb) {
    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // 1. Starfield Space Background
    for (int i = 0; i < 16 * 16 * 3; ++i) fb[i] = 0;

    // Distant scrolling stars
    for (int i = 0; i < 6; ++i) {
        int sx = (int(state_timer_ * 6.0f + i * 5) % 16);
        int sy = 2 + (i * 2);
        set_pixel(15 - sx, sy, 100, 120, 160);
    }

    // 2. Power Meter HUD (y=0)
    // 6 slots: Speed, Missile, Double, Laser, Option, Shield
    for (int slot = 1; slot <= 6; ++slot) {
        int hx = 2 + (slot - 1) * 2;
        if (meter_slot_ == slot) {
            // Highlighted active slot (Blinking yellow/cyan)
            bool blink = (int(state_timer_ * 12.0f) % 2 == 0);
            set_pixel(hx, 0, blink ? 255 : 40, blink ? 220 : 220, blink ? 30 : 255);
        } else {
            // Dormant slot
            set_pixel(hx, 0, 50, 60, 80);
        }
    }

    // 3. Capsules (Orange glowing pod)
    for (int c = 0; c < MAX_CAPSULES; ++c) {
        if (!capsules_[c].active) continue;
        int cx = int(std::round(capsules_[c].x));
        int cy = int(std::round(capsules_[c].y));
        set_pixel(cx, cy, 255, 120, 20);
        set_pixel(cx, cy - 1, 255, 220, 50);
    }

    // 4. Enemies
    for (int e = 0; e < MAX_ENEMIES; ++e) {
        if (!enemies_[e].active) continue;
        int ex = int(std::round(enemies_[e].x));
        int ey = int(std::round(enemies_[e].y));
        if (enemies_[e].type == 0) {
            // Red scout: crimson fighter
            set_pixel(ex, ey, 240, 30, 30);
            set_pixel(ex + 1, ey, 255, 100, 30);
        } else {
            // Turret: grey/yellow
            set_pixel(ex, ey, 140, 140, 160);
            set_pixel(ex - 1, ey, 255, 200, 40);
        }
    }

    // 5. Big Core Boss
    if (boss_active_) {
        int bx = int(std::round(boss_x_));
        int by = int(std::round(boss_y_));

        // Upper and lower hulls
        for (int dx = -1; dx <= 1; ++dx) {
            set_pixel(bx + dx, by - 2, 160, 160, 180);
            set_pixel(bx + dx, by + 2, 160, 160, 180);
        }

        // Barrier shield in front of core
        if (boss_barrier_health_ > 0) {
            set_pixel(bx - 1, by, 60, 180, 255);      // Cyan energy barrier
            set_pixel(bx - 1, by - 1, 60, 180, 255);
            set_pixel(bx - 1, by + 1, 60, 180, 255);
        }

        // Central vulnerable core
        uint8_t cr = (boss_barrier_health_ <= 0) ? 255 : 40;
        uint8_t cg = (boss_barrier_health_ <= 0) ? 30 : 100;
        uint8_t cb = (boss_barrier_health_ <= 0) ? 30 : 255;
        set_pixel(bx, by, cr, cg, cb);
    }

    // 6. Projectiles
    for (int s = 0; s < MAX_SHOTS; ++s) {
        if (!shots_[s].active) continue;
        int sx = int(std::round(shots_[s].x));
        int sy = int(std::round(shots_[s].y));
        if (shots_[s].is_laser) {
            set_pixel(sx, sy, 50, 240, 255); // Cyan laser beam
            set_pixel(sx - 1, sy, 50, 200, 255);
        } else {
            set_pixel(sx, sy, 255, 240, 100);
        }
    }

    for (int m = 0; m < MAX_MISSILES; ++m) {
        if (!missiles_[m].active) continue;
        set_pixel(int(std::round(missiles_[m].x)), int(std::round(missiles_[m].y)), 255, 120, 0);
    }

    // 7. Option Follower
    if (has_option_) {
        int opt_idx = (trail_idx_ + TRAIL_SIZE / 2) % TRAIL_SIZE;
        int ox = int(std::round(trail_[opt_idx].x));
        int oy = int(std::round(trail_[opt_idx].y));
        set_pixel(ox, oy, 255, 140, 20); // Glowing orange energy sphere
    }

    // 8. Vic Viper Ship
    if (state_ != STATE_DEAD) {
        int vx = int(std::round(px_));
        int vy = int(std::round(py_));

        // Shield at nose
        if (shield_hp_ > 0) {
            set_pixel(vx + 2, vy, 100, 200, 255);
            set_pixel(vx + 2, vy - 1, 100, 200, 255);
            set_pixel(vx + 2, vy + 1, 100, 200, 255);
        }

        // Vic Viper fuselage (white/blue needle craft)
        set_pixel(vx, vy, 240, 240, 255);       // Hull
        set_pixel(vx + 1, vy, 40, 100, 240);    // Cockpit
        set_pixel(vx - 1, vy - 1, 220, 30, 30); // Wing tip upper
        set_pixel(vx - 1, vy + 1, 220, 30, 30); // Wing tip lower
        set_pixel(vx - 1, vy, 255, 160, 40);    // Ion thruster flame
    } else {
        int vx = int(std::round(px_));
        int vy = int(std::round(py_));
        for (int dy = -1; dy <= 1; ++dy) {
            for (int dx = -1; dx <= 1; ++dx) {
                set_pixel(vx + dx, vy + dy, 255, 120, 30);
            }
        }
    }
}

} // namespace arcade
