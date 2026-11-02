#include "game_101_spyhunter.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game101SpyHunter::Game101SpyHunter() {
    Reset();
}

void Game101SpyHunter::Init() {
    Reset();
}

void Game101SpyHunter::Reset() {
    score_ = 0;
    lives_ = 3;
    distance_traveled_ = 0.0f;
    state_ = STATE_DRIVING;
    state_timer_ = 0.0f;
    ResetRoad();
}

void Game101SpyHunter::ResetRoad() {
    px_ = 8.0f;
    py_ = 12.0f;
    speed_ = 10.0f;
    current_weapon_ = WEAPON_NONE;
    weapon_ammo_ = 0;
    fire_cooldown_ = 0.0f;

    road_left_ = 3.0f;
    road_width_ = 10.0f;

    van_.active = false;
    van_.x = 8.0f;
    van_.y = -6.0f;
    van_.speed = 9.0f;
    van_.carrying_weapon = WEAPON_OIL_SLICK;

    for (int i = 0; i < MAX_ENEMIES; ++i) {
        enemies_[i].active = false;
    }
    for (int i = 0; i < MAX_BULLETS; ++i) {
        bullets_[i].active = false;
    }
    for (int i = 0; i < MAX_HAZARDS; ++i) {
        hazards_[i].active = false;
    }

    // Spawn 2 initial rival cars
    enemies_[0].active = true;
    enemies_[0].x = 6.0f;
    enemies_[0].y = 2.0f;
    enemies_[0].speed = 7.0f;
    enemies_[0].type = 0; // Enforcer
    enemies_[0].spinning = false;

    enemies_[1].active = true;
    enemies_[1].x = 10.0f;
    enemies_[1].y = -2.0f;
    enemies_[1].speed = 8.5f;
    enemies_[1].type = 1; // Tire Slasher
    enemies_[1].spinning = false;
}

void Game101SpyHunter::CallWeaponVan() {
    if (!van_.active) {
        van_.active = true;
        van_.x = road_left_ + road_width_ * 0.5f;
        van_.y = -5.0f;
        van_.speed = speed_ * 0.9f;
        van_.carrying_weapon = (distance_traveled_ > 300.0f) ? WEAPON_SMOKE_SCREEN : WEAPON_OIL_SLICK;
    }
}

void Game101SpyHunter::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_CRASHED) {
        if (state_timer_ > 1.8f) {
            lives_--;
            if (lives_ <= 0) {
                state_ = STATE_GAME_OVER;
                state_timer_ = 0.0f;
            } else {
                state_ = (distance_traveled_ >= 500.0f) ? STATE_AMPHIBIOUS_BOATING : STATE_DRIVING;
                state_timer_ = 0.0f;
                px_ = road_left_ + road_width_ * 0.5f;
                py_ = 12.0f;
                speed_ = 9.0f;
            }
        }
        return;
    }

    if (state_ == STATE_WEAPONS_VAN_DOCK) {
        // Docked inside van
        van_.y += (van_.speed - speed_) * dt;
        px_ = van_.x;
        py_ = van_.y + 2.5f;

        if (state_timer_ > 1.4f) {
            // Exit Van with rearmed weapons
            current_weapon_ = van_.carrying_weapon;
            weapon_ammo_ = 3;
            score_ += 500;
            van_.active = false;
            state_ = (distance_traveled_ >= 500.0f) ? STATE_AMPHIBIOUS_BOATING : STATE_DRIVING;
            state_timer_ = 0.0f;
            speed_ = 12.0f;
        }
        return;
    }

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            Reset();
        }
        return;
    }

    // Check transition to Amphibious Boating River
    distance_traveled_ += speed_ * dt;
    score_ += static_cast<int>(speed_ * dt * 2.0f);

    if (state_ == STATE_DRIVING && distance_traveled_ >= 500.0f) {
        state_ = STATE_AMPHIBIOUS_BOATING;
        state_timer_ = 0.0f;
    }

    // Call weapons van periodically if without weapon
    if (current_weapon_ == WEAPON_NONE && !van_.active && static_cast<int>(distance_traveled_) % 180 < 20) {
        CallWeaponVan();
    }

    UpdateCar(dt, buttons, prev_buttons);
    UpdateVan(dt);
    UpdateEnemies(dt);
    UpdateBulletsAndHazards(dt);
    CheckCollisions();
}

void Game101SpyHunter::UpdateCar(float dt, uint32_t buttons, uint32_t prev_buttons) {
    // Steering
    float steer_speed = (state_ == STATE_AMPHIBIOUS_BOATING) ? 8.5f : 10.0f;
    if (buttons & BTN_LEFT) {
        px_ -= steer_speed * dt;
    }
    if (buttons & BTN_RIGHT) {
        px_ += steer_speed * dt;
    }

    // Throttle / Braking
    if (buttons & BTN_UP) {
        speed_ = std::min(18.0f, speed_ + 8.0f * dt);
    } else if (buttons & BTN_DOWN) {
        speed_ = std::max(6.0f, speed_ - 12.0f * dt);
    } else {
        // Natural cruise
        if (speed_ < 10.0f) speed_ += 2.0f * dt;
        if (speed_ > 10.0f) speed_ -= 2.0f * dt;
    }

    // Roadway Curvature
    float curve = std::sin(distance_traveled_ * 0.02f) * 1.5f;
    road_left_ = 3.0f + curve;
    if (road_left_ < 1.0f) road_left_ = 1.0f;
    if (road_left_ > 6.0f) road_left_ = 6.0f;

    // Check Off-road / Bank crash
    if (px_ < road_left_ || px_ > road_left_ + road_width_ - 1.0f) {
        state_ = STATE_CRASHED;
        state_timer_ = 0.0f;
        return;
    }

    // Button A: Fire Dual Machine Guns
    fire_cooldown_ -= dt;
    if ((buttons & BTN_A) && fire_cooldown_ <= 0.0f) {
        fire_cooldown_ = 0.2f;
        for (int i = 0; i < MAX_BULLETS; ++i) {
            if (!bullets_[i].active) {
                bullets_[i].active = true;
                bullets_[i].x = px_;
                bullets_[i].y = py_ - 1.2f;
                bullets_[i].vy = -24.0f;
                break;
            }
        }
    }

    // Button B: Special Weapon / Call Van
    if ((buttons & BTN_B) && !(prev_buttons & BTN_B)) {
        if (current_weapon_ != WEAPON_NONE && weapon_ammo_ > 0) {
            weapon_ammo_--;
            for (int h = 0; h < MAX_HAZARDS; ++h) {
                if (!hazards_[h].active) {
                    hazards_[h].active = true;
                    hazards_[h].x = px_;
                    hazards_[h].y = py_ + 1.2f;
                    break;
                }
            }
            if (weapon_ammo_ <= 0) {
                current_weapon_ = WEAPON_NONE;
            }
        } else if (!van_.active) {
            CallWeaponVan();
        }
    }
}

void Game101SpyHunter::UpdateVan(float dt) {
    if (!van_.active) return;

    // Van moves relative to player car
    float rel_speed = van_.speed - speed_;
    van_.y += rel_speed * dt;

    // Rear dock check
    if (state_ == STATE_DRIVING || state_ == STATE_AMPHIBIOUS_BOATING) {
        float dx = std::abs(px_ - van_.x);
        float dy = py_ - (van_.y + 2.8f);
        if (dx < 1.0f && std::abs(dy) < 0.6f) {
            // Docked!
            state_ = STATE_WEAPONS_VAN_DOCK;
            state_timer_ = 0.0f;
        }
    }

    // Van despawn if fell behind or pulled too far ahead
    if (van_.y > 18.0f || van_.y < -12.0f) {
        van_.active = false;
    }
}

void Game101SpyHunter::UpdateEnemies(float dt) {
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) {
            // Respawn enemy
            enemies_[i].active = true;
            enemies_[i].x = road_left_ + 1.0f + static_cast<float>(i * 3);
            enemies_[i].y = -4.0f;
            enemies_[i].speed = 7.0f + static_cast<float>(i * 1.5f);
            enemies_[i].type = (state_ == STATE_AMPHIBIOUS_BOATING) ? 2 : (i % 2);
            enemies_[i].spinning = false;
            continue;
        }

        if (enemies_[i].spinning) {
            enemies_[i].spin_timer -= dt;
            enemies_[i].x += (i % 2 == 0 ? 3.0f : -3.0f) * dt;
            enemies_[i].y += (enemies_[i].speed - speed_) * dt;
            if (enemies_[i].spin_timer <= 0.0f ||
                enemies_[i].x < road_left_ || enemies_[i].x > road_left_ + road_width_) {
                enemies_[i].active = false;
                score_ += 300;
            }
            continue;
        }

        // Relative vertical movement
        float rel_spd = enemies_[i].speed - speed_;
        enemies_[i].y += rel_spd * dt;

        // Tire Slasher attempts to steer into player
        if (enemies_[i].type == 1) {
            if (enemies_[i].x < px_) enemies_[i].x += 2.0f * dt;
            else if (enemies_[i].x > px_) enemies_[i].x -= 2.0f * dt;
        }

        // Despawn if offscreen
        if (enemies_[i].y > 18.0f || enemies_[i].y < -8.0f) {
            enemies_[i].active = false;
        }
    }
}

void Game101SpyHunter::UpdateBulletsAndHazards(float dt) {
    // Bullets
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (!bullets_[i].active) continue;
        bullets_[i].y += bullets_[i].vy * dt;
        if (bullets_[i].y < -2.0f) {
            bullets_[i].active = false;
        }
    }

    // Hazards (Oil Slick drift relative to player)
    for (int h = 0; h < MAX_HAZARDS; ++h) {
        if (!hazards_[h].active) continue;
        hazards_[h].y -= speed_ * dt;
        if (hazards_[h].y > 18.0f) {
            hazards_[h].active = false;
        }
    }
}

void Game101SpyHunter::CheckCollisions() {
    // 1. Bullets vs Enemies
    for (int b = 0; b < MAX_BULLETS; ++b) {
        if (!bullets_[b].active) continue;
        for (int e = 0; e < MAX_ENEMIES; ++e) {
            if (!enemies_[e].active || enemies_[e].spinning) continue;
            float dx = std::abs(bullets_[b].x - enemies_[e].x);
            float dy = std::abs(bullets_[b].y - enemies_[e].y);
            if (dx < 1.2f && dy < 1.4f) {
                bullets_[b].active = false;
                if (enemies_[e].type == 0) {
                    // Bulletproof Enforcer deflects bullets!
                    score_ += 50;
                } else {
                    // Tire Slasher or Torpedo Boat destroyed
                    enemies_[e].active = false;
                    score_ += 200;
                }
                break;
            }
        }
    }

    // 2. Oil Hazards vs Enemies
    for (int h = 0; h < MAX_HAZARDS; ++h) {
        if (!hazards_[h].active) continue;
        for (int e = 0; e < MAX_ENEMIES; ++e) {
            if (!enemies_[e].active || enemies_[e].spinning) continue;
            float dx = std::abs(hazards_[h].x - enemies_[e].x);
            float dy = std::abs(hazards_[h].y - enemies_[e].y);
            if (dx < 1.3f && dy < 1.3f) {
                enemies_[e].spinning = true;
                enemies_[e].spin_timer = 1.0f;
                score_ += 150;
            }
        }
    }

    // 3. Enemy vs Player Car
    for (int e = 0; e < MAX_ENEMIES; ++e) {
        if (!enemies_[e].active || enemies_[e].spinning) continue;
        float dx = std::abs(px_ - enemies_[e].x);
        float dy = std::abs(py_ - enemies_[e].y);
        if (dx < 1.1f && dy < 1.3f) {
            if (enemies_[e].type == 1) {
                // Tire Slasher shreds tires! Immediate crash
                state_ = STATE_CRASHED;
                state_timer_ = 0.0f;
                return;
            } else {
                // Enforcer side collision: bumps player sideways
                if (px_ < enemies_[e].x) px_ -= 0.8f;
                else px_ += 0.8f;
            }
        }
    }
}

void Game101SpyHunter::Render(uint8_t* fb) {
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

    bool is_water = (state_ == STATE_AMPHIBIOUS_BOATING);

    // Terrain & Roadway
    for (int y = 0; y < 16; ++y) {
        int r_left = static_cast<int>(std::round(road_left_));
        int r_right = static_cast<int>(std::round(road_left_ + road_width_));

        for (int x = 0; x < 16; ++x) {
            if (x < r_left || x >= r_right) {
                // Shoulder: Grass or riverbank
                if (is_water) {
                    set_pixel(x, y, 40, 80, 30); // Dark moss bank
                } else {
                    set_pixel(x, y, 30, 100, 20); // Green grass
                }
            } else {
                // Road or River
                if (is_water) {
                    uint8_t wave = ((y + static_cast<int>(distance_traveled_ * 0.5f)) % 4 == 0) ? 60 : 30;
                    set_pixel(x, y, 10, wave, 140);
                } else {
                    set_pixel(x, y, 50, 50, 55); // Asphalt
                    // Road Center Dashed Line
                    if (x == r_left + static_cast<int>(road_width_ * 0.5f)) {
                        if ((y + static_cast<int>(distance_traveled_ * 0.5f)) % 4 < 2) {
                            set_pixel(x, y, 220, 220, 200);
                        }
                    }
                }
            }
        }
    }

    // Oil Hazards
    for (int h = 0; h < MAX_HAZARDS; ++h) {
        if (!hazards_[h].active) continue;
        int hx = static_cast<int>(std::round(hazards_[h].x));
        int hy = static_cast<int>(std::round(hazards_[h].y));
        set_pixel(hx, hy, 20, 20, 20);
        set_pixel(hx + 1, hy, 40, 30, 10);
    }

    // Weapons Van
    if (van_.active) {
        int vx = static_cast<int>(std::round(van_.x));
        int vy = static_cast<int>(std::round(van_.y));
        // Large red/white van body
        set_pixel(vx, vy, 220, 40, 30);
        set_pixel(vx + 1, vy, 220, 40, 30);
        set_pixel(vx, vy + 1, 240, 240, 240);
        set_pixel(vx + 1, vy + 1, 240, 240, 240);
        set_pixel(vx, vy + 2, 220, 40, 30);
        set_pixel(vx + 1, vy + 2, 220, 40, 30);
        // Yellow flashing beacon on top
        set_pixel(vx, vy - 1, 255, 200, 0);
    }

    // Bullets
    for (int b = 0; b < MAX_BULLETS; ++b) {
        if (!bullets_[b].active) continue;
        int bx = static_cast<int>(std::round(bullets_[b].x));
        int by = static_cast<int>(std::round(bullets_[b].y));
        set_pixel(bx, by, 255, 255, 120);
    }

    // Enemies
    for (int e = 0; e < MAX_ENEMIES; ++e) {
        if (!enemies_[e].active) continue;
        int ex = static_cast<int>(std::round(enemies_[e].x));
        int ey = static_cast<int>(std::round(enemies_[e].y));

        if (enemies_[e].spinning) {
            set_pixel(ex, ey, 255, 120, 0);
            set_pixel(ex + 1, ey, 255, 60, 0);
        } else if (enemies_[e].type == 0) {
            // Blue Bulletproof Enforcer
            set_pixel(ex, ey, 40, 60, 200);
            set_pixel(ex, ey - 1, 30, 40, 150);
            set_pixel(ex, ey + 1, 20, 30, 100);
        } else if (enemies_[e].type == 1) {
            // Orange Tire Slasher with spikes
            set_pixel(ex, ey, 240, 100, 20);
            set_pixel(ex - 1, ey, 255, 255, 255);
            set_pixel(ex + 1, ey, 255, 255, 255);
        } else {
            // Torpedo Boat
            set_pixel(ex, ey, 180, 40, 180);
            set_pixel(ex, ey - 1, 220, 80, 220);
        }
    }

    // Player Vehicle (White G-6155 Interceptor Car or Turbo Speedboat)
    int px_i = static_cast<int>(std::round(px_));
    int py_i = static_cast<int>(std::round(py_));

    if (state_ == STATE_CRASHED) {
        set_pixel(px_i, py_i, 255, 60, 20);
        set_pixel(px_i - 1, py_i, 255, 180, 0);
        set_pixel(px_i + 1, py_i, 255, 180, 0);
        set_pixel(px_i, py_i - 1, 255, 220, 0);
    } else {
        if (is_water) {
            // Speedboat mode
            set_pixel(px_i, py_i, 250, 250, 255);
            set_pixel(px_i, py_i - 1, 40, 180, 255); // Streamlined bow
            set_pixel(px_i - 1, py_i + 1, 200, 240, 255); // Port wake spray
            set_pixel(px_i + 1, py_i + 1, 200, 240, 255); // Starboard wake
        } else {
            // Sports car mode
            set_pixel(px_i, py_i, 240, 240, 250);     // Roof
            set_pixel(px_i, py_i - 1, 255, 255, 255); // Hood
            set_pixel(px_i, py_i + 1, 220, 20, 20);   // Tail lights
            set_pixel(px_i - 1, py_i, 40, 40, 40);    // Left tire
            set_pixel(px_i + 1, py_i, 40, 40, 40);    // Right tire
        }
    }

    // HUD: Ammo indicator on bottom left
    if (weapon_ammo_ > 0) {
        for (int a = 0; a < weapon_ammo_; ++a) {
            set_pixel(a, 15, 255, 200, 0);
        }
    }
    // Lives on top left
    for (int l = 0; l < std::min(lives_, 3); ++l) {
        set_pixel(l, 0, 255, 255, 255);
    }
}

} // namespace arcade
