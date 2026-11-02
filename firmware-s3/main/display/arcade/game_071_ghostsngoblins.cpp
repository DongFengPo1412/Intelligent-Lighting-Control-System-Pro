#include "game_071_ghostsngoblins.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game071GhostsNGoblins::Game071GhostsNGoblins()
    : state_(STATE_START),
      state_timer_(0.0f),
      score_(0),
      high_score_(7500),
      lives_(3),
      px_(2.0f),
      py_(14.0f),
      pvy_(0.0f),
      on_ground_(true),
      is_ducking_(false),
      facing_(1),
      armor_stage_(ARMOR_STEEL),
      weapon_type_(WEAPON_LANCE),
      throw_cooldown_(0.0f),
      enemies_defeated_(0),
      armor_drop_active_(false),
      armor_drop_x_(0.0f),
      armor_drop_y_(0.0f) {
}

void Game071GhostsNGoblins::Init() {
    Reset();
}

void Game071GhostsNGoblins::Reset() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    score_ = 0;
    lives_ = 3;
    InitStage();
}

void Game071GhostsNGoblins::InitStage() {
    px_ = 2.0f;
    py_ = 14.0f;
    pvy_ = 0.0f;
    on_ground_ = true;
    is_ducking_ = false;
    facing_ = 1;
    armor_stage_ = ARMOR_STEEL;
    weapon_type_ = WEAPON_LANCE;
    throw_cooldown_ = 0.0f;
    enemies_defeated_ = 0;
    armor_drop_active_ = false;

    for (int i = 0; i < MAX_WEAPONS; ++i) weapons_[i].active = false;
    for (int i = 0; i < MAX_FLAMES; ++i) flames_[i].active = false;

    // Ground zombies and Red Arremer
    enemies_[0] = {14.0f, 14.0f, -2.0f, 0.0f, 0, 1, true}; // Zombie 1
    enemies_[1] = {10.0f, 14.0f, -1.8f, 0.0f, 0, 1, true}; // Zombie 2
    enemies_[2] = {6.0f, 14.0f, -2.2f, 0.0f, 0, 1, true};  // Zombie 3
    enemies_[3] = {8.0f, 5.0f, -2.5f, 1.5f, 1, 2, true};   // Red Arremer demon
}

void Game071GhostsNGoblins::ThrowWeapon() {
    if (throw_cooldown_ > 0.0f) return;

    for (int i = 0; i < MAX_WEAPONS; ++i) {
        if (!weapons_[i].active) {
            weapons_[i].active = true;
            weapons_[i].x = px_ + facing_ * 0.8f;
            weapons_[i].y = is_ducking_ ? py_ + 0.5f : py_ - 0.5f;
            weapons_[i].type = weapon_type_;

            if (weapon_type_ == WEAPON_LANCE) {
                weapons_[i].vx = facing_ * 14.0f;
                weapons_[i].vy = 0.0f;
            } else {
                // Torch: lobbed fire flask
                weapons_[i].vx = facing_ * 8.0f;
                weapons_[i].vy = -7.0f;
            }
            break;
        }
    }

    throw_cooldown_ = 0.25f;
}

void Game071GhostsNGoblins::Jump() {
    if (on_ground_ && !is_ducking_) {
        pvy_ = -8.8f;
        on_ground_ = false;
    }
}

void Game071GhostsNGoblins::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    state_timer_ += dt;

    if (state_ == STATE_DEAD) {
        if (state_timer_ > 1.8f) {
            if (lives_ > 0) {
                state_ = STATE_PLAYING;
                state_timer_ = 0.0f;
                InitStage();
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

    if (throw_cooldown_ > 0.0f) throw_cooldown_ -= dt;

    UpdatePlayer(dt, buttons, prev_buttons);
    UpdateWeapons(dt);
    UpdateEnemies(dt);
    CheckCollisions();
}

void Game071GhostsNGoblins::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    is_ducking_ = (buttons & BUTTON_DOWN) && on_ground_;

    float speed = is_ducking_ ? 0.0f : 5.0f;

    if (!is_ducking_) {
        if (buttons & BUTTON_LEFT)  { px_ -= speed * dt; facing_ = -1; }
        if (buttons & BUTTON_RIGHT) { px_ += speed * dt; facing_ = 1; }
    }

    px_ = std::max(0.5f, std::min(15.0f, px_));

    // Gravity
    pvy_ += 26.0f * dt;
    py_ += pvy_ * dt;

    on_ground_ = false;
    if (pvy_ >= 0.0f) {
        if (py_ >= 14.0f) {
            py_ = 14.0f;
            pvy_ = 0.0f;
            on_ground_ = true;
        } else if (py_ >= 9.0f && py_ <= 9.6f && px_ >= 3.8f && px_ <= 11.2f) {
            py_ = 9.0f;
            pvy_ = 0.0f;
            on_ground_ = true;
        }
    }

    // Button A: Jump
    if ((buttons & BUTTON_A) && !(prev_buttons & BUTTON_A)) {
        Jump();
    }

    // Button B: Throw
    if ((buttons & BUTTON_B) && !(prev_buttons & BUTTON_B)) {
        ThrowWeapon();
    }
}

void Game071GhostsNGoblins::UpdateWeapons(float dt) {
    for (int i = 0; i < MAX_WEAPONS; ++i) {
        if (!weapons_[i].active) continue;

        weapons_[i].x += weapons_[i].vx * dt;
        if (weapons_[i].type == WEAPON_TORCH) {
            weapons_[i].vy += 22.0f * dt; // Gravity on torch
            weapons_[i].y += weapons_[i].vy * dt;

            // Hits ground: bursts into flame!
            if (weapons_[i].y >= 14.0f) {
                weapons_[i].active = false;
                for (int f = 0; f < MAX_FLAMES; ++f) {
                    if (!flames_[f].active) {
                        flames_[f].active = true;
                        flames_[f].x = weapons_[i].x;
                        flames_[f].y = 14.0f;
                        flames_[f].duration = 1.8f;
                        break;
                    }
                }
            }
        }

        if (weapons_[i].x < 0.0f || weapons_[i].x > 15.5f || weapons_[i].y < 0.0f) {
            weapons_[i].active = false;
        }
    }

    // Update flames
    for (int f = 0; f < MAX_FLAMES; ++f) {
        if (!flames_[f].active) continue;
        flames_[f].duration -= dt;
        if (flames_[f].duration <= 0.0f) {
            flames_[f].active = false;
        }
    }
}

void Game071GhostsNGoblins::UpdateEnemies(float dt) {
    for (int i = 0; i < MAX_ENEMIES; ++i) {
        if (!enemies_[i].active) continue;

        if (enemies_[i].type == 0) {
            // Zombie: straight shambling walk
            enemies_[i].x += enemies_[i].vx * dt;
            if (enemies_[i].x < -1.0f) {
                enemies_[i].x = 16.5f;
            } else if (enemies_[i].x > 17.0f) {
                enemies_[i].x = -0.5f;
            }
        } else {
            // Red Arremer: swoop in sinusoidal arc
            enemies_[i].x += enemies_[i].vx * dt;
            enemies_[i].y += std::sin(state_timer_ * 5.0f) * 3.5f * dt;

            if (enemies_[i].x < 1.0f) {
                enemies_[i].x = 1.0f;
                enemies_[i].vx = std::abs(enemies_[i].vx);
            } else if (enemies_[i].x >= 14.0f) {
                enemies_[i].x = 14.0f;
                enemies_[i].vx = -std::abs(enemies_[i].vx);
            }
        }
    }
}

void Game071GhostsNGoblins::CheckCollisions() {
    // 1. Weapons hit enemies
    for (int w = 0; w < MAX_WEAPONS; ++w) {
        if (!weapons_[w].active) continue;
        for (int e = 0; e < MAX_ENEMIES; ++e) {
            if (!enemies_[e].active) continue;
            if (std::abs(weapons_[w].x - enemies_[e].x) < 1.2f &&
                std::abs(weapons_[w].y - enemies_[e].y) < 1.2f) {
                weapons_[w].active = false;
                enemies_[e].health--;
                if (enemies_[e].health <= 0) {
                    enemies_[e].active = false;
                    enemies_defeated_++;
                    score_ += (enemies_[e].type == 1) ? 500 : 150;

                    // Chance to drop Armor Jar if in boxers
                    if (armor_stage_ == ARMOR_BOXERS && !armor_drop_active_) {
                        armor_drop_active_ = true;
                        armor_drop_x_ = enemies_[e].x;
                        armor_drop_y_ = 14.0f;
                    }

                    if (enemies_defeated_ >= 8) {
                        state_ = STATE_VICTORY;
                        state_timer_ = 0.0f;
                        score_ += 3000;
                        if (score_ > high_score_) high_score_ = score_;
                        return;
                    }
                }
                break;
            }
        }
    }

    // 2. Ground flames burn enemies
    for (int f = 0; f < MAX_FLAMES; ++f) {
        if (!flames_[f].active) continue;
        for (int e = 0; e < MAX_ENEMIES; ++e) {
            if (!enemies_[e].active) continue;
            if (std::abs(flames_[f].x - enemies_[e].x) < 1.2f &&
                std::abs(flames_[f].y - enemies_[e].y) < 1.2f) {
                enemies_[e].active = false;
                enemies_defeated_++;
                score_ += 200;
                if (enemies_defeated_ >= 8) {
                    state_ = STATE_VICTORY;
                    state_timer_ = 0.0f;
                    score_ += 3000;
                    if (score_ > high_score_) high_score_ = score_;
                    return;
                }
            }
        }
    }

    // 3. Player collects armor jar
    if (armor_drop_active_) {
        if (std::abs(px_ - armor_drop_x_) < 1.2f && std::abs(py_ - armor_drop_y_) < 1.2f) {
            armor_drop_active_ = false;
            armor_stage_ = ARMOR_STEEL; // Restored steel armor!
            score_ += 500;
        }
    }

    // 4. Enemy hits Arthur (Two-stage damage system!)
    for (int e = 0; e < MAX_ENEMIES; ++e) {
        if (!enemies_[e].active) continue;
        if (std::abs(px_ - enemies_[e].x) < 0.9f &&
            std::abs(py_ - enemies_[e].y) < 0.9f) {
            if (armor_stage_ == ARMOR_STEEL) {
                // Armor shatters into pieces!
                armor_stage_ = ARMOR_BOXERS;
                // Knocks back slightly
                px_ -= facing_ * 1.5f;
                pvy_ = -4.0f;
            } else {
                // Fatal skeleton death in boxers!
                lives_--;
                state_ = STATE_DEAD;
                state_timer_ = 0.0f;
                return;
            }
            break;
        }
    }
}

void Game071GhostsNGoblins::Render(uint8_t* fb) {
    auto set_pixel = [fb](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // 1. Spooky Haunted Forest / Cemetery Night
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            set_pixel(x, y, 5, 10, 25);
        }
    }

    // Blood Moon
    set_pixel(13, 2, 220, 50, 40);
    set_pixel(14, 2, 220, 50, 40);

    // 2. Cemetery Ground and Platform
    for (int x = 0; x < 16; ++x) {
        set_pixel(x, 15, 30, 60, 25); // Earth / grass
    }
    // Ledge platform
    for (int x = 4; x <= 11; ++x) {
        set_pixel(x, 10, 70, 70, 80);
    }

    // Tombstones on ground
    set_pixel(3, 14, 120, 120, 130);
    set_pixel(8, 14, 120, 120, 130);

    // 3. Armor Jar item
    if (armor_drop_active_) {
        int ax = int(std::round(armor_drop_x_));
        int ay = int(std::round(armor_drop_y_));
        set_pixel(ax, ay, 200, 200, 220);     // Silver jar
        set_pixel(ax, ay - 1, 255, 215, 0);   // Gold knight crest
    }

    // 4. Ground Flames
    for (int f = 0; f < MAX_FLAMES; ++f) {
        if (!flames_[f].active) continue;
        int fx = int(std::round(flames_[f].x));
        int fy = int(std::round(flames_[f].y));
        set_pixel(fx, fy, 255, 100, 20);
        set_pixel(fx, fy - 1, 255, 220, 40);
    }

    // 5. Enemies
    for (int e = 0; e < MAX_ENEMIES; ++e) {
        if (!enemies_[e].active) continue;
        int ex = int(std::round(enemies_[e].x));
        int ey = int(std::round(enemies_[e].y));

        if (enemies_[e].type == 0) {
            // Zombie: greyish green rotting corpse
            set_pixel(ex, ey, 70, 130, 80);
            set_pixel(ex, ey - 1, 100, 160, 110);
            set_pixel(ex, ey - 2, 220, 220, 200); // Shaggy hair
        } else {
            // Red Arremer Demon: crimson wings and horns
            set_pixel(ex, ey, 220, 20, 20);
            set_pixel(ex - 1, ey, 160, 10, 10); // Left wing
            set_pixel(ex + 1, ey, 160, 10, 10); // Right wing
            set_pixel(ex, ey - 1, 255, 60, 60); // Glowing eyes
        }
    }

    // 6. Projectiles
    for (int w = 0; w < MAX_WEAPONS; ++w) {
        if (!weapons_[w].active) continue;
        int wx = int(std::round(weapons_[w].x));
        int wy = int(std::round(weapons_[w].y));
        if (weapons_[w].type == WEAPON_LANCE) {
            set_pixel(wx, wy, 220, 220, 240); // Silver lance
        } else {
            set_pixel(wx, wy, 255, 120, 0);   // Fire flask
        }
    }

    // 7. Arthur
    if (state_ != STATE_DEAD) {
        int px = int(std::round(px_));
        int py = int(std::round(py_));

        if (armor_stage_ == ARMOR_STEEL) {
            // Full Shining Knight Steel Armor
            set_pixel(px, py, 190, 200, 210);       // Cuirass
            set_pixel(px, py - 1, 220, 230, 240);   // Visor helmet
            set_pixel(px + facing_, py - 1, 255, 50, 50); // Red helmet plume
        } else {
            // Boxer Shorts (White with red polka dots / bare skin)
            set_pixel(px, py, 255, 255, 255);       // Boxers
            set_pixel(px, py - 1, 230, 170, 130);   // Bare chest
            set_pixel(px, py - 2, 160, 90, 40);     // Brown beard/hair
        }
    } else {
        // Skeleton bones pile
        int px = int(std::round(px_));
        int py = int(std::round(py_));
        set_pixel(px - 1, py, 220, 220, 220);
        set_pixel(px,     py, 255, 255, 255); // Skull
        set_pixel(px + 1, py, 220, 220, 220);
    }
}

} // namespace arcade
