#include "game_109_spaceharrier.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game109SpaceHarrier::Game109SpaceHarrier() {
    Reset();
}

void Game109SpaceHarrier::Init() {
    Reset();
}

void Game109SpaceHarrier::Reset() {
    score_ = 0;
    lives_ = 3;
    stage_ = 1;
    InitStage();
}

void Game109SpaceHarrier::InitStage() {
    state_ = STATE_FLYING;
    state_timer_ = 0.0f;
    horizon_scroll_ = 0.0f;
    enemies_defeated_ = 0;

    hero_x_ = 8.0f;
    hero_y_ = 11.0f;
    shot_cooldown_ = 0.0f;
    roll_timer_ = 0.0f;

    for (int i = 0; i < MAX_SHOTS; ++i) {
        shots_[i].active = false;
    }

    // Spawn initial oncoming entities
    for (int i = 0; i < MAX_ENTITIES; ++i) {
        entities_[i].active = true;
        entities_[i].x = 4.0f + static_cast<float>((i * 3) % 9);
        entities_[i].y = 5.0f + static_cast<float>(i % 3);
        entities_[i].z = 6.0f + static_cast<float>(i * 2.0f);
        entities_[i].type = (i % 2 == 0) ? 0 : 1; // 0 = Drone, 1 = Tree Pillar
        entities_[i].hp = 1;
    }
}

void Game109SpaceHarrier::SpawnDragonBoss() {
    state_ = STATE_BOSS_DRAGON;
    state_timer_ = 0.0f;
    dragon_x_ = 8.0f;
    dragon_y_ = 6.0f;
    dragon_z_ = 6.0f;
    dragon_hp_ = 8;
    dragon_angle_ = 0.0f;

    for (int i = 0; i < MAX_ENTITIES; ++i) {
        entities_[i].active = false;
    }
}

void Game109SpaceHarrier::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;
    horizon_scroll_ += 12.0f * dt;

    if (state_ == STATE_HERO_HIT) {
        if (state_timer_ > 1.8f) {
            lives_--;
            if (lives_ <= 0) {
                state_ = STATE_GAME_OVER;
                state_timer_ = 0.0f;
            } else {
                state_ = STATE_FLYING;
                state_timer_ = 0.0f;
                hero_x_ = 8.0f;
                hero_y_ = 11.0f;
            }
        }
        return;
    }

    if (state_ == STATE_STAGE_CLEAR) {
        if (state_timer_ > 2.5f) {
            stage_++;
            InitStage();
        }
        return;
    }

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            Reset();
        }
        return;
    }

    UpdateHero(dt, buttons, prev_buttons);
    UpdateShots(dt);

    if (state_ == STATE_BOSS_DRAGON) {
        UpdateDragonBoss(dt);
    } else {
        UpdateEntities(dt);
        if (enemies_defeated_ >= 6) {
            SpawnDragonBoss();
        }
    }

    CheckCollisions();
}

void Game109SpaceHarrier::UpdateHero(float dt, uint32_t buttons, uint32_t prev_buttons) {
    float spd = (roll_timer_ > 0.0f) ? 14.0f : 9.0f;
    if (buttons & BTN_LEFT)  hero_x_ = std::max(2.0f, hero_x_ - spd * dt);
    if (buttons & BTN_RIGHT) hero_x_ = std::min(13.0f, hero_x_ + spd * dt);
    if (buttons & BTN_UP)    hero_y_ = std::max(4.0f, hero_y_ - spd * dt);
    if (buttons & BTN_DOWN)  hero_y_ = std::min(13.0f, hero_y_ + spd * dt);

    // Button B: Rapid Dodge Roll
    if ((buttons & BTN_B) && !(prev_buttons & BTN_B)) {
        roll_timer_ = 0.35f;
    }
    if (roll_timer_ > 0.0f) roll_timer_ -= dt;

    // Button A: Rapid Plasma Cannon
    shot_cooldown_ -= dt;
    if ((buttons & BTN_A) && shot_cooldown_ <= 0.0f) {
        shot_cooldown_ = 0.2f;
        for (int i = 0; i < MAX_SHOTS; ++i) {
            if (!shots_[i].active) {
                shots_[i].active = true;
                shots_[i].x = hero_x_;
                shots_[i].y = hero_y_ - 0.5f;
                shots_[i].z = 0.5f;
                break;
            }
        }
    }
}

void Game109SpaceHarrier::UpdateShots(float dt) {
    for (int i = 0; i < MAX_SHOTS; ++i) {
        if (!shots_[i].active) continue;
        shots_[i].z += 16.0f * dt; // Flies deep into screen
        if (shots_[i].z > 10.0f) {
            shots_[i].active = false;
        }
    }
}

void Game109SpaceHarrier::UpdateEntities(float dt) {
    float approach_spd = 5.0f;
    for (int i = 0; i < MAX_ENTITIES; ++i) {
        if (!entities_[i].active) {
            entities_[i].active = true;
            entities_[i].x = 3.0f + static_cast<float>((i * 4 + enemies_defeated_) % 10);
            entities_[i].y = 4.0f + static_cast<float>((i * 2) % 6);
            entities_[i].z = 10.0f;
            entities_[i].type = (i % 2 == 0) ? 0 : 1;
            entities_[i].hp = 1;
            continue;
        }

        entities_[i].z -= approach_spd * dt;

        // Passed screen camera
        if (entities_[i].z <= 0.0f) {
            entities_[i].active = false;
            score_ += 50;
        }
    }
}

void Game109SpaceHarrier::UpdateDragonBoss(float dt) {
    dragon_angle_ += 2.5f * dt;
    dragon_x_ = 8.0f + std::cos(dragon_angle_) * 3.5f;
    dragon_y_ = 6.0f + std::sin(dragon_angle_ * 1.5f) * 2.0f;
    dragon_z_ = 5.5f + std::sin(dragon_angle_) * 1.5f;
}

void Game109SpaceHarrier::CheckCollisions() {
    // 1. Plasma Shots vs Oncoming Flying Drones / Enemies
    for (int s = 0; s < MAX_SHOTS; ++s) {
        if (!shots_[s].active) continue;

        if (state_ == STATE_BOSS_DRAGON) {
            float dx = std::abs(shots_[s].x - dragon_x_);
            float dy = std::abs(shots_[s].y - dragon_y_);
            float dz = std::abs(shots_[s].z - dragon_z_);
            if (dx < 1.6f && dy < 1.6f && dz < 1.6f) {
                shots_[s].active = false;
                dragon_hp_--;
                score_ += 300;
                if (dragon_hp_ <= 0) {
                    state_ = STATE_STAGE_CLEAR;
                    state_timer_ = 0.0f;
                    score_ += 5000;
                }
            }
        } else {
            for (int e = 0; e < MAX_ENTITIES; ++e) {
                if (!entities_[e].active || entities_[e].type == 1) continue; // Trees cannot be shot
                float dx = std::abs(shots_[s].x - entities_[e].x);
                float dy = std::abs(shots_[s].y - entities_[e].y);
                float dz = std::abs(shots_[s].z - entities_[e].z);
                if (dx < 1.4f && dy < 1.4f && dz < 1.6f) {
                    shots_[s].active = false;
                    entities_[e].active = false;
                    score_ += 150;
                    enemies_defeated_++;
                    break;
                }
            }
        }
    }

    // 2. Oncoming Entities vs Harrier Hero (z <= 1.2 close collision)
    if (state_ == STATE_FLYING && roll_timer_ <= 0.0f) {
        for (int e = 0; e < MAX_ENTITIES; ++e) {
            if (!entities_[e].active) continue;
            if (entities_[e].z <= 1.2f && entities_[e].z >= 0.0f) {
                float dx = std::abs(hero_x_ - entities_[e].x);
                float dy = std::abs(hero_y_ - entities_[e].y);
                if (dx < 1.2f && dy < 1.2f) {
                    state_ = STATE_HERO_HIT;
                    state_timer_ = 0.0f;
                    return;
                }
            }
        }
    }

    // Boss vs Hero
    if (state_ == STATE_BOSS_DRAGON && roll_timer_ <= 0.0f) {
        if (dragon_z_ <= 2.0f) {
            if (std::abs(hero_x_ - dragon_x_) < 1.4f && std::abs(hero_y_ - dragon_y_) < 1.4f) {
                state_ = STATE_HERO_HIT;
                state_timer_ = 0.0f;
            }
        }
    }
}

void Game109SpaceHarrier::Render(uint8_t* fb) {
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

    // Surreal Sky (Horizon at y=8)
    for (int y = 0; y < 8; ++y) {
        for (int x = 0; x < 16; ++x) {
            // Gradient Fantasy Sky: Cyan to Violet
            uint8_t sr = 40 + y * 15;
            uint8_t sg = 10 + y * 8;
            uint8_t sb = 120 + y * 12;
            set_pixel(x, y, sr, sg, sb);
        }
    }

    // Checkered Rolling Horizon Ground (y = 8 to 15)
    int scroll_row = static_cast<int>(horizon_scroll_) % 4;
    for (int y = 8; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            int check_pat = ((x / 2) + (y - 8 + scroll_row)) % 2;
            if (check_pat == 0) {
                set_pixel(x, y, 40, 180, 50); // Neon Green
            } else {
                set_pixel(x, y, 220, 200, 30); // Bright Yellow
            }
        }
    }

    // Scaled Oncoming Entities
    for (int i = 0; i < MAX_ENTITIES; ++i) {
        if (!entities_[i].active) continue;
        int ex = static_cast<int>(std::round(entities_[i].x));
        int ey = static_cast<int>(std::round(entities_[i].y));

        if (entities_[i].z > 6.0f) {
            // Distant small 1-pixel dot
            if (entities_[i].type == 1) set_pixel(ex, ey, 180, 80, 40); // Tree trunk
            else set_pixel(ex, ey, 255, 60, 60); // Drone
        } else {
            // Scaled up 3x3 sprite
            if (entities_[i].type == 1) {
                // Giant surreal tree / column
                set_pixel(ex, ey, 60, 160, 40);
                set_pixel(ex - 1, ey, 40, 120, 30);
                set_pixel(ex + 1, ey, 40, 120, 30);
                set_pixel(ex, ey - 1, 80, 200, 50); // Foliage crown
                set_pixel(ex, ey + 1, 140, 80, 30); // Trunk
            } else {
                // Flying One-eyed Mammoth Drone
                set_pixel(ex, ey, 255, 40, 40);
                set_pixel(ex - 1, ey, 200, 30, 80);
                set_pixel(ex + 1, ey, 200, 30, 80);
                set_pixel(ex, ey - 1, 255, 255, 255); // Eye
            }
        }
    }

    // Boss Uriah (Chinese Dragon)
    if (state_ == STATE_BOSS_DRAGON) {
        int dx = static_cast<int>(std::round(dragon_x_));
        int dy = static_cast<int>(std::round(dragon_y_));
        // Serpentine dragon segments
        set_pixel(dx, dy, 255, 200, 0);       // Head
        set_pixel(dx - 1, dy, 255, 60, 20);   // Whisker/horn
        set_pixel(dx + 1, dy, 255, 255, 255); // Glow eye
        set_pixel(dx, dy + 1, 240, 140, 0);   // Body segment
        set_pixel(dx - 1, dy + 1, 220, 100, 0);
        set_pixel(dx - 2, dy + 1, 200, 60, 0); // Tail
    }

    // Plasma Shots in flight
    for (int s = 0; s < MAX_SHOTS; ++s) {
        if (!shots_[s].active) continue;
        int sx = static_cast<int>(std::round(shots_[s].x));
        int sy = static_cast<int>(std::round(shots_[s].y));
        set_pixel(sx, sy, 0, 240, 255); // Glowing cyan plasma
    }

    // Harrier Hero at (hero_x, hero_y)
    int hx = static_cast<int>(std::round(hero_x_));
    int hy = static_cast<int>(std::round(hero_y_));

    if (state_ == STATE_HERO_HIT) {
        set_pixel(hx, hy, 255, 60, 30);
        set_pixel(hx - 1, hy, 255, 180, 0);
        set_pixel(hx + 1, hy, 255, 180, 0);
    } else {
        if (roll_timer_ > 0.0f) {
            // Turbo roll spin
            set_pixel(hx, hy, 255, 220, 0);
            set_pixel(hx - 1, hy, 40, 120, 255);
            set_pixel(hx + 1, hy, 40, 120, 255);
        } else {
            // Hero running/flying with big rocket cannon
            set_pixel(hx, hy, 240, 240, 250);     // Red/white suit
            set_pixel(hx, hy - 1, 255, 200, 140); // Blonde hair / head
            set_pixel(hx, hy + 1, 40, 60, 180);   // Boots
            set_pixel(hx + 1, hy, 160, 160, 180); // Under-arm rocket cannon
            set_pixel(hx - 1, hy, 220, 40, 30);   // Red shoulder
        }
    }

    // Lives on top left
    for (int l = 0; l < std::min(lives_, 3); ++l) {
        set_pixel(l * 2, 0, 255, 200, 0);
    }
}

} // namespace arcade
