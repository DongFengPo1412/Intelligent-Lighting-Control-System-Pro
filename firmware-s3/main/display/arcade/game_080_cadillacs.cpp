#include "game_080_cadillacs.h"
#include <algorithm>
#include <cmath>
#include <cstdlib>

namespace arcade {

Game080Cadillacs::Game080Cadillacs() {
    Reset();
}

void Game080Cadillacs::Init() {
    Reset();
}

void Game080Cadillacs::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    lives_ = 3;
    player_hp_ = 100;
    enemies_defeated_ = 0;
    current_weapon_ = WEAPON_FIST;
    weapon_ammo_ = 0;
    ResetStage();
}

void Game080Cadillacs::ResetStage() {
    px_ = 3.0f;
    py_ = 10.0f;
    facing_ = 1;
    in_air_ = false;
    pvy_ = 0.0f;
    atk_timer_ = 0.0f;

    // Dino
    dino_.active = true;
    dino_.x = 12.0f;
    dino_.y = 10.0f;
    dino_.vx = -1.2f;
    dino_.enraged = false;
    dino_.calm_timer = 0.0f;
    dino_.hp = 4;

    // Enemies
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        enemies_[i].active = true;
        enemies_[i].x = 14.0f + i * 4.0f;
        enemies_[i].y = 8.0f + (i * 2.0f);
        enemies_[i].vx = -2.2f;
        enemies_[i].hp = 2;
    }

    // Bullets & Drops
    for (int i = 0; i < MAX_BULLETS; ++i) bullets_[i].active = false;
    for (int i = 0; i < MAX_DROPS; ++i) drops_[i].active = false;

    // Initial Uzi crate on ground
    drops_[0].active = true;
    drops_[0].x = 7.0f;
    drops_[0].y = 11.0f;
    drops_[0].type = WEAPON_UZI;
    drops_[0].ammo = 15;

    caddy_x_ = -8.0f;
}

void Game080Cadillacs::TriggerCadillacRaid() {
    state_ = STATE_CADILLAC_DRIVE;
    state_timer_ = 0.0f;
    caddy_x_ = -6.0f;
    score_ += 3000;
}

void Game080Cadillacs::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_PLAYER_DEAD || state_ == STATE_VICTORY) {
        if (state_timer_ > 2.5f && (buttons & (BUTTON_A | BUTTON_B))) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_CADILLAC_DRIVE) {
        caddy_x_ += caddy_speed_ * dt;
        px_ = caddy_x_; // Player rides Cadillac

        // Run over enemies & dino
        for (int i = 0; i < MAX_ENEMIES; ++i) {
            if (enemies_[i].active && std::abs(enemies_[i].x - caddy_x_) < 2.5f) {
                enemies_[i].active = false;
                score_ += 500;
                enemies_defeated_++;
            }
        }
        if (dino_.active && std::abs(dino_.x - caddy_x_) < 3.0f) {
            dino_.active = false;
            score_ += 2000;
        }

        if (caddy_x_ > 20.0f) {
            state_ = STATE_VICTORY;
            state_timer_ = 0.0f;
            score_ += 5000;
        }
        return;
    }

    UpdatePlayer(dt, buttons, prev_buttons);
    UpdateEnemies(dt);
    UpdateDino(dt);
    UpdateBullets(dt);
    CheckCollisions();

    if (enemies_defeated_ >= 8 && state_ == STATE_PLAYING) {
        TriggerCadillacRaid();
    }
}

void Game080Cadillacs::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    float move_speed = 5.0f;

    // Whirlwind Kick (A + B)
    if ((buttons & BUTTON_A) && (buttons & BUTTON_B) &&
        (!(prev_buttons & BUTTON_A) || !(prev_buttons & BUTTON_B))) {
        if (player_hp_ > 15) {
            player_hp_ -= 10;
            atk_timer_ = 0.35f;
            // Clears nearby enemies
            for (int i = 0; i < MAX_ENEMIES; ++i) {
                if (enemies_[i].active && std::abs(enemies_[i].x - px_) < 2.8f && std::abs(enemies_[i].y - py_) < 2.0f) {
                    enemies_[i].hp -= 2;
                    if (enemies_[i].hp <= 0) {
                        enemies_[i].active = false;
                        enemies_[i].respawn_timer = 2.0f;
                        enemies_defeated_++;
                        score_ += 300;
                    }
                }
            }
            if (dino_.active && std::abs(dino_.x - px_) < 3.0f && std::abs(dino_.y - py_) < 2.0f) {
                dino_.enraged = false; // Calmed by whirlwind!
            }
            return;
        }
    }

    // Jump Physics
    if (in_air_) {
        pvy_ += 22.0f * dt;
        py_ += pvy_ * dt;
        if (py_ >= 10.0f) {
            py_ = 10.0f;
            pvy_ = 0.0f;
            in_air_ = false;
        }
    } else {
        if (buttons & BUTTON_LEFT)  { px_ -= move_speed * dt; facing_ = -1; }
        if (buttons & BUTTON_RIGHT) { px_ += move_speed * dt; facing_ = 1; }
        if (buttons & BUTTON_UP)    py_ -= (move_speed * 0.7f) * dt;
        if (buttons & BUTTON_DOWN)  py_ += (move_speed * 0.7f) * dt;

        px_ = std::max(1.0f, std::min(14.5f, px_));
        py_ = std::max(7.0f, std::min(13.5f, py_));

        if ((buttons & BUTTON_B) && !(prev_buttons & BUTTON_B)) {
            in_air_ = true;
            pvy_ = -8.5f;
        }
    }

    if (atk_timer_ > 0.0f) {
        atk_timer_ -= dt;
    }

    // Fire or Punch (Button A)
    if ((buttons & BUTTON_A) && !(prev_buttons & BUTTON_A)) {
        atk_timer_ = 0.22f;
        if (current_weapon_ != WEAPON_FIST && weapon_ammo_ > 0) {
            FireWeapon();
        } else {
            // Check pickup weapon drop
            bool picked = false;
            for (int i = 0; i < MAX_DROPS; ++i) {
                if (drops_[i].active && std::abs(drops_[i].x - px_) < 1.6f && std::abs(drops_[i].y - py_) < 1.6f) {
                    current_weapon_ = drops_[i].type;
                    weapon_ammo_ = drops_[i].ammo;
                    drops_[i].active = false;
                    picked = true;
                    score_ += 200;
                    break;
                }
            }

            // Punch melee attack
            if (!picked) {
                // Strike enemies
                for (int i = 0; i < MAX_ENEMIES; ++i) {
                    if (enemies_[i].active && std::abs(enemies_[i].x - px_) < 2.0f && std::abs(enemies_[i].y - py_) < 1.4f) {
                        enemies_[i].hp--;
                        if (enemies_[i].hp <= 0) {
                            enemies_[i].active = false;
                            enemies_[i].respawn_timer = 2.0f;
                            enemies_defeated_++;
                            score_ += 300;
                            // Chance to drop Bazooka
                            if (std::rand() % 3 == 0 && !drops_[1].active) {
                                drops_[1].active = true;
                                drops_[1].x = enemies_[i].x;
                                drops_[1].y = enemies_[i].y;
                                drops_[1].type = WEAPON_BAZOOKA;
                                drops_[1].ammo = 4;
                            }
                        }
                    }
                }
                // Strike Dino
                if (dino_.active && std::abs(dino_.x - px_) < 2.2f && std::abs(dino_.y - py_) < 1.5f) {
                    if (!dino_.enraged) {
                        dino_.enraged = true; // Turn red and frenzy!
                        dino_.vx = facing_ * 3.5f;
                    } else {
                        dino_.hp--;
                        if (dino_.hp <= 1) {
                            dino_.enraged = false; // Calmed down!
                            dino_.hp = 4;
                            score_ += 1000;
                        }
                    }
                }
            }
        }
    }
}

void Game080Cadillacs::FireWeapon() {
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (!bullets_[i].active) {
            bullets_[i].active = true;
            bullets_[i].x = px_ + (facing_ * 1.0f);
            bullets_[i].y = py_;
            bullets_[i].vx = (facing_ * 20.0f);
            bullets_[i].is_bazooka = (current_weapon_ == WEAPON_BAZOOKA);
            weapon_ammo_--;
            if (weapon_ammo_ <= 0) {
                current_weapon_ = WEAPON_FIST;
            }
            break;
        }
    }
}

void Game080Cadillacs::UpdateEnemies(float dt) {
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) {
            if (enemies_[i].respawn_timer > 0.0f) {
                enemies_[i].respawn_timer -= dt;
                if (enemies_[i].respawn_timer <= 0.0f && enemies_defeated_ + i < 8) {
                    enemies_[i].active = true;
                    enemies_[i].x = 15.5f;
                    enemies_[i].y = 8.0f + (std::rand() % 5);
                    enemies_[i].hp = 2;
                }
            }
            continue;
        }

        // Enemy moves toward player
        if (enemies_[i].x > px_ + 1.2f) {
            enemies_[i].x -= 2.5f * dt;
        } else if (enemies_[i].x < px_ - 1.2f) {
            enemies_[i].x += 2.5f * dt;
        }

        if (enemies_[i].y > py_ + 0.4f) {
            enemies_[i].y -= 1.5f * dt;
        } else if (enemies_[i].y < py_ - 0.4f) {
            enemies_[i].y += 1.5f * dt;
        }
    }
}

void Game080Cadillacs::UpdateDino(float dt) {
    if (!dino_.active) return;

    if (dino_.enraged) {
        // Enraged: charges across screen violently
        dino_.x += dino_.vx * dt;
        if (dino_.x < 1.0f) {
            dino_.x = 1.0f;
            dino_.vx = 4.0f;
        } else if (dino_.x > 14.5f) {
            dino_.x = 14.5f;
            dino_.vx = -4.0f;
        }

        // Tramples enemies in path
        for (int i = 0; i < MAX_ENEMIES; ++i) {
            if (enemies_[i].active && std::abs(enemies_[i].x - dino_.x) < 2.0f && std::abs(enemies_[i].y - dino_.y) < 1.5f) {
                enemies_[i].active = false;
                enemies_defeated_++;
                score_ += 400;
            }
        }
    } else {
        // Calm patrol
        dino_.x += dino_.vx * dt;
        if (dino_.x < 6.0f) {
            dino_.vx = 1.0f;
        } else if (dino_.x > 14.0f) {
            dino_.vx = -1.0f;
        }
    }
}

void Game080Cadillacs::UpdateBullets(float dt) {
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (!bullets_[i].active) continue;

        bullets_[i].x += bullets_[i].vx * dt;
        if (bullets_[i].x < 0.0f || bullets_[i].x > 15.5f) {
            bullets_[i].active = false;
        }
    }
}

void Game080Cadillacs::CheckCollisions() {
    // 1. Bullets vs Enemies & Dino
    for (int b = 0; b < MAX_BULLETS; ++b) {
        if (!bullets_[b].active) continue;

        for (int e = 0; e < MAX_ENEMIES; ++e) {
            if (!enemies_[e].active) continue;
            if (std::abs(bullets_[b].x - enemies_[e].x) < 1.5f && std::abs(bullets_[b].y - enemies_[e].y) < 1.4f) {
                bullets_[b].active = false;
                int dmg = bullets_[b].is_bazooka ? 3 : 1;
                enemies_[e].hp -= dmg;
                if (enemies_[e].hp <= 0) {
                    enemies_[e].active = false;
                    enemies_defeated_++;
                    score_ += 350;
                }
                break;
            }
        }

        if (bullets_[b].active && dino_.active) {
            if (std::abs(bullets_[b].x - dino_.x) < 1.8f && std::abs(bullets_[b].y - dino_.y) < 1.6f) {
                bullets_[b].active = false;
                dino_.enraged = true;
                score_ += 100;
            }
        }
    }

    // 2. Enemy attacks Player
    for (int e = 0; e < MAX_ENEMIES; ++e) {
        if (!enemies_[e].active) continue;
        if (std::abs(enemies_[e].x - px_) < 1.2f && std::abs(enemies_[e].y - py_) < 1.0f) {
            player_hp_ -= 1; // Chip damage
            if (player_hp_ <= 0) {
                lives_--;
                if (lives_ > 0) {
                    player_hp_ = 100;
                    px_ = 3.0f;
                    py_ = 10.0f;
                } else {
                    state_ = STATE_PLAYER_DEAD;
                    state_timer_ = 0.0f;
                }
                return;
            }
        }
    }

    // 3. Enraged Dino tramples Player
    if (dino_.active && dino_.enraged) {
        if (std::abs(dino_.x - px_) < 1.6f && std::abs(dino_.y - py_) < 1.2f) {
            player_hp_ -= 2; // Heavy stampede damage
            if (player_hp_ <= 0) {
                lives_--;
                if (lives_ > 0) {
                    player_hp_ = 100;
                    px_ = 3.0f;
                    py_ = 10.0f;
                } else {
                    state_ = STATE_PLAYER_DEAD;
                    state_timer_ = 0.0f;
                }
                return;
            }
        }
    }
}

void Game080Cadillacs::Render(uint8_t* fb) {
    auto set_pixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // 1. Jungle Ruin Skyline (y: 0..6)
    for (int y = 0; y < 7; ++y) {
        for (int x = 0; x < 16; ++x) {
            set_pixel(x, y, 20, 45, 25);
        }
    }

    // 2. Highway / Dirt Terrain (y: 7..14)
    for (int y = 7; y < 15; ++y) {
        for (int x = 0; x < 16; ++x) {
            set_pixel(x, y, 70, 60, 45);
        }
    }

    // 3. Cadillac Raid Car
    if (state_ == STATE_CADILLAC_DRIVE) {
        int cx = static_cast<int>(std::round(caddy_x_));
        int cy = 10;
        // 1953 Cadillac Convertible (Yellow & Crimson Red)
        for (int dx = -2; dx <= 2; ++dx) {
            set_pixel(cx + dx, cy, 255, 40, 40);
            set_pixel(cx + dx, cy - 1, 255, 220, 0);
        }
        set_pixel(cx + 3, cy, 255, 255, 200); // Headlights
    }

    // 4. Weapon Drops on ground
    for (int i = 0; i < MAX_DROPS; ++i) {
        if (!drops_[i].active) continue;
        int dx = static_cast<int>(std::round(drops_[i].x));
        int dy = static_cast<int>(std::round(drops_[i].y));
        if (drops_[i].type == WEAPON_UZI) {
            set_pixel(dx, dy, 50, 150, 255); // Blue Uzi
        } else {
            set_pixel(dx, dy, 255, 120, 0);   // Orange Bazooka
        }
    }

    // 5. Dinosaur (Green calm, Red enraged)
    if (dino_.active) {
        int dx = static_cast<int>(std::round(dino_.x));
        int dy = static_cast<int>(std::round(dino_.y));
        if (dino_.enraged) {
            set_pixel(dx, dy, 255, 30, 30);
            set_pixel(dx, dy - 1, 255, 80, 0);
            set_pixel(dx + 1, dy, 255, 180, 0);
        } else {
            set_pixel(dx, dy, 30, 200, 50);
            set_pixel(dx, dy - 1, 60, 240, 80);
            set_pixel(dx + 1, dy, 20, 160, 40);
        }
    }

    // 6. Enemies (Purple / Black punk thugs)
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;
        int ex = static_cast<int>(std::round(enemies_[i].x));
        int ey = static_cast<int>(std::round(enemies_[i].y));
        set_pixel(ex, ey, 180, 40, 200);
        set_pixel(ex, ey - 1, 240, 180, 140);
    }

    // 7. Bullets
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (!bullets_[i].active) continue;
        int bx = static_cast<int>(std::round(bullets_[i].x));
        int by = static_cast<int>(std::round(bullets_[i].y));
        if (bullets_[i].is_bazooka) {
            set_pixel(bx, by, 255, 200, 0);
            set_pixel(bx - 1, by, 255, 80, 0);
        } else {
            set_pixel(bx, by, 255, 255, 100);
        }
    }

    // 8. Player (Mustapha Cairo in Yellow hat & Blue jeans)
    if (state_ != STATE_CADILLAC_DRIVE) {
        int px = static_cast<int>(std::round(px_));
        int py = static_cast<int>(std::round(py_));
        set_pixel(px, py, 40, 100, 220);     // Blue pants
        set_pixel(px, py - 1, 255, 240, 200); // Shirt
        set_pixel(px, py - 2, 255, 220, 0);   // Yellow Fedora hat
        if (atk_timer_ > 0.0f) {
            set_pixel(px + facing_, py - 1, 255, 200, 50); // Fist or muzzle flash
        }
    }

    // 9. HUD (y = 15)
    // Health bar (green to red)
    int hp_bars = std::max(0, std::min(8, player_hp_ / 12));
    for (int b = 0; b < hp_bars; ++b) {
        set_pixel(b, 15, 50, 220, 50);
    }
    // Ammo or weapon indicator
    if (current_weapon_ != WEAPON_FIST) {
        for (int a = 0; a < std::min(6, weapon_ammo_); ++a) {
            set_pixel(15 - a, 15, 255, 200, 0);
        }
    }
}

} // namespace arcade
