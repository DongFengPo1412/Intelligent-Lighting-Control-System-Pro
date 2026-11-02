#include "game_089_snowbros2.h"
#include <cmath>
#include <cstring>
#include <algorithm>

namespace arcade {

Game089SnowBros2::Game089SnowBros2() {
    Init();
}

void Game089SnowBros2::Init() {
    ResetLevel(true);
}

void Game089SnowBros2::Reset() {
    ResetLevel(true);
}

void Game089SnowBros2::ResetLevel(bool hard_reset) {
    if (hard_reset) {
        score_ = 0;
        lives_ = 3;
        stage_ = 1;
        current_element_ = ELEM_SNOW;
    }
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;
    monsters_defeated_ = 0;

    px_ = 2.0f;
    py_ = 13.0f;
    vx_ = 0.0f;
    vy_ = 0.0f;
    facing_ = 1;
    on_ground_ = true;

    for (int i = 0; i < MAX_PROJECTILES; ++i) {
        projectiles_[i].active = false;
    }

    for (int i = 0; i < MAX_MONSTERS; ++i) {
        monsters_[i].active = true;
        monsters_[i].inflate_level = 0;
        monsters_[i].is_kicked = false;
        monsters_[i].kick_vx = 0.0f;
        monsters_[i].kick_vy = 0.0f;
        monsters_[i].respawn_timer = 0.0f;
        monsters_[i].sphere_elem = ELEM_SNOW;

        if (i == 0) {
            monsters_[i].x = 12.0f;
            monsters_[i].y = 13.0f;
            monsters_[i].vx = -1.5f;
        } else if (i == 1) {
            monsters_[i].x = 4.0f;
            monsters_[i].y = 9.0f;
            monsters_[i].vx = 1.2f;
        } else if (i == 2) {
            monsters_[i].x = 11.0f;
            monsters_[i].y = 9.0f;
            monsters_[i].vx = -1.2f;
        } else {
            monsters_[i].x = 8.0f;
            monsters_[i].y = 5.0f;
            monsters_[i].vx = 1.0f;
        }
    }
}

void Game089SnowBros2::Update(float dt, uint32_t buttons, uint32_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_HERO_HIT) {
        if (state_timer_ > 1.8f) {
            lives_--;
            if (lives_ <= 0) {
                state_ = STATE_GAME_OVER;
                state_timer_ = 0.0f;
            } else {
                ResetLevel(false);
            }
        }
        return;
    }

    if (state_ == STATE_STAGE_CLEAR) {
        if (state_timer_ > 2.0f) {
            stage_++;
            ResetLevel(false);
        }
        return;
    }

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & (BTN_A | BTN_B)) && !(prev_buttons & (BTN_A | BTN_B))) {
            ResetLevel(true);
        }
        return;
    }

    // STATE_PLAYING
    UpdatePlayer(dt, buttons, prev_buttons);
    UpdateProjectiles(dt);
    UpdateMonsters(dt);
    CheckCombat();

    if (monsters_defeated_ >= 6) {
        state_ = STATE_STAGE_CLEAR;
        state_timer_ = 0.0f;
        score_ += 1000;
    }
}

void Game089SnowBros2::UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons) {
    // Switch elemental elf: Down + Button B (or Down + Button A)
    if ((buttons & BTN_DOWN) && (buttons & BTN_B) && !(prev_buttons & BTN_B)) {
        current_element_ = static_cast<ElementType>((static_cast<int>(current_element_) + 1) % 4);
        return;
    }

    // Horizontal Movement
    float speed = 6.0f;
    if (buttons & BTN_LEFT) {
        px_ -= speed * dt;
        facing_ = -1;
    }
    if (buttons & BTN_RIGHT) {
        px_ += speed * dt;
        facing_ = 1;
    }

    // Jump
    if ((buttons & BTN_UP) && !(prev_buttons & BTN_UP)) {
        if (on_ground_) {
            vy_ = -6.2f;
            on_ground_ = false;
        }
    }

    // Gravity
    if (!on_ground_) {
        vy_ += 15.0f * dt;
        py_ += vy_ * dt;
    }

    // Ground & Platform collisions
    if (py_ >= 13.0f) {
        py_ = 13.0f;
        vy_ = 0.0f;
        on_ground_ = true;
    } else {
        // Platform checks when descending (vy_ >= 0)
        on_ground_ = false;
        if (vy_ >= 0.0f) {
            // Mid platforms (y=9.0f)
            if (py_ >= 8.8f && py_ <= 9.3f) {
                if ((px_ >= 1.5f && px_ <= 7.0f) || (px_ >= 8.5f && px_ <= 14.0f)) {
                    py_ = 9.0f;
                    vy_ = 0.0f;
                    on_ground_ = true;
                }
            }
            // Top platform (y=5.0f)
            else if (py_ >= 4.8f && py_ <= 5.3f) {
                if (px_ >= 3.5f && px_ <= 12.0f) {
                    py_ = 5.0f;
                    vy_ = 0.0f;
                    on_ground_ = true;
                }
            }
        }
    }

    px_ = std::clamp(px_, 0.5f, 15.0f);

    // Shoot Elemental Burst (Button A)
    if ((buttons & BTN_A) && !(prev_buttons & BTN_A)) {
        for (int i = 0; i < MAX_PROJECTILES; ++i) {
            if (!projectiles_[i].active) {
                projectiles_[i].active = true;
                projectiles_[i].x = px_ + facing_ * 0.8f;
                projectiles_[i].y = py_ - 0.5f;
                projectiles_[i].vx = facing_ * 9.5f;
                projectiles_[i].elem = current_element_;
                break;
            }
        }
    }

    // Kick Ball (Button B)
    if ((buttons & BTN_B) && !(prev_buttons & BTN_B) && !(buttons & BTN_DOWN)) {
        for (int i = 0; i < MAX_MONSTERS; ++i) {
            Monster& m = monsters_[i];
            if (m.active && m.inflate_level >= 3 && !m.is_kicked) {
                float dx = std::fabs(px_ - m.x);
                float dy = std::fabs(py_ - m.y);
                if (dx < 1.6f && dy < 1.4f) {
                    m.is_kicked = true;
                    m.kick_vx = (float)facing_ * 10.0f;
                    m.kick_vy = (m.sphere_elem == ELEM_WIND) ? -4.0f : 0.0f;
                    score_ += 50;
                    break;
                }
            }
        }
    }
}

void Game089SnowBros2::UpdateProjectiles(float dt) {
    for (int i = 0; i < MAX_PROJECTILES; ++i) {
        Projectile& p = projectiles_[i];
        if (!p.active) continue;

        p.x += p.vx * dt;
        if (p.x < -1.0f || p.x > 17.0f) {
            p.active = false;
        }
    }
}

void Game089SnowBros2::UpdateMonsters(float dt) {
    for (int i = 0; i < MAX_MONSTERS; ++i) {
        Monster& m = monsters_[i];
        if (!m.active) {
            if (m.respawn_timer > 0.0f) {
                m.respawn_timer -= dt;
            } else {
                m.active = true;
                m.inflate_level = 0;
                m.is_kicked = false;
                m.x = 2.0f + (float)(rand() % 12);
                m.y = (rand() % 2 == 0) ? 9.0f : 13.0f;
                m.vx = (rand() % 2 == 0) ? 1.5f : -1.5f;
            }
            continue;
        }

        if (m.is_kicked) {
            // Rolling / Ricocheting ball
            m.x += m.kick_vx * dt;
            m.y += m.kick_vy * dt;

            // Bounce on left/right walls
            if (m.x <= 0.8f) {
                m.x = 0.8f;
                m.kick_vx = -m.kick_vx;
            } else if (m.x >= 14.8f) {
                m.x = 14.8f;
                m.kick_vx = -m.kick_vx;
            }

            // Wind elf ball bounces vertically
            if (m.sphere_elem == ELEM_WIND) {
                m.kick_vy += 9.8f * dt;
                if (m.y >= 13.0f) {
                    m.y = 13.0f;
                    m.kick_vy = -4.0f;
                }
            } else {
                // Ground level rolling
                if (m.y < 13.0f) m.y += 6.0f * dt;
                if (m.y >= 13.0f) m.y = 13.0f;
            }

            // After moving for a while, ball pops
            m.respawn_timer += dt;
            if (m.respawn_timer >= 2.5f) {
                m.active = false;
                m.is_kicked = false;
                m.respawn_timer = 2.0f;
                score_ += 300; // Fruit pop bonus
                monsters_defeated_++;
            }
            continue;
        }

        // If partially inflated, slowly deflates
        if (m.inflate_level > 0 && m.inflate_level < 3) {
            m.respawn_timer += dt;
            if (m.respawn_timer >= 3.0f) {
                m.inflate_level--;
                m.respawn_timer = 0.0f;
            }
            continue;
        }

        if (m.inflate_level >= 3) {
            // Trapped in ball, cannot walk
            continue;
        }

        // Normal patrolling monster
        m.x += m.vx * dt;
        if (m.x <= 1.0f) {
            m.x = 1.0f;
            m.vx = std::fabs(m.vx);
        } else if (m.x >= 14.5f) {
            m.x = 14.5f;
            m.vx = -std::fabs(m.vx);
        }
    }
}

void Game089SnowBros2::CheckCombat() {
    // 1. Projectiles vs Monsters
    for (int p_idx = 0; p_idx < MAX_PROJECTILES; ++p_idx) {
        Projectile& p = projectiles_[p_idx];
        if (!p.active) continue;

        for (int m_idx = 0; m_idx < MAX_MONSTERS; ++m_idx) {
            Monster& m = monsters_[m_idx];
            if (!m.active || m.is_kicked) continue;

            float dx = std::fabs(p.x - m.x);
            float dy = std::fabs(p.y - m.y);

            if (dx < 1.2f && dy < 1.2f) {
                p.active = false;
                m.inflate_level = std::min(3, m.inflate_level + 1);
                m.sphere_elem = p.elem;
                m.respawn_timer = 0.0f; // reset deflation timer
                score_ += 20;

                // Lightning chains shock to adjacent monsters
                if (p.elem == ELEM_LIGHTNING && m.inflate_level >= 2) {
                    for (int o = 0; o < MAX_MONSTERS; ++o) {
                        if (o != m_idx && monsters_[o].active && !monsters_[o].is_kicked) {
                            if (std::fabs(m.x - monsters_[o].x) < 3.0f && std::fabs(m.y - monsters_[o].y) < 1.5f) {
                                monsters_[o].inflate_level = std::min(3, monsters_[o].inflate_level + 1);
                                monsters_[o].sphere_elem = ELEM_LIGHTNING;
                                score_ += 10;
                            }
                        }
                    }
                }
                break;
            }
        }
    }

    // 2. Kicked Ball vs other monsters
    for (int k = 0; k < MAX_MONSTERS; ++k) {
        Monster& km = monsters_[k];
        if (!km.active || !km.is_kicked) continue;

        for (int o = 0; o < MAX_MONSTERS; ++o) {
            if (o == k) continue;
            Monster& om = monsters_[o];
            if (!om.active) continue;

            float dx = std::fabs(km.x - om.x);
            float dy = std::fabs(km.y - om.y);

            if (dx < 1.3f && dy < 1.3f) {
                // Squashed by rolling ball!
                om.active = false;
                om.respawn_timer = 2.5f;
                score_ += 200;
                monsters_defeated_++;
            }
        }
    }

    // 3. Monsters vs Hero
    for (int i = 0; i < MAX_MONSTERS; ++i) {
        Monster& m = monsters_[i];
        if (!m.active) continue;

        // If trapped in ball or kicked, harmless to hero
        if (m.inflate_level >= 3 || m.is_kicked) continue;

        float dx = std::fabs(px_ - m.x);
        float dy = std::fabs(py_ - m.y);

        if (dx < 1.0f && dy < 1.0f) {
            // Hero hit!
            state_ = STATE_HERO_HIT;
            state_timer_ = 0.0f;
            break;
        }
    }
}

void Game089SnowBros2::Render(uint8_t* fb) {
    std::memset(fb, 0, 16 * 16 * 3);

    auto set_pixel = [&](int x, int y, uint8_t r, uint8_t g, uint8_t b) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            int idx = (y * 16 + x) * 3;
            fb[idx] = r;
            fb[idx + 1] = g;
            fb[idx + 2] = b;
        }
    };

    // Render Platforms
    // Ground (y=14 and 15)
    for (int x = 0; x < 16; ++x) {
        set_pixel(x, 14, 50, 120, 180);
        set_pixel(x, 15, 30, 70, 120);
    }

    // Mid platforms (y=10)
    for (int x = 2; x <= 6; ++x) {
        set_pixel(x, 10, 80, 140, 200);
    }
    for (int x = 9; x <= 13; ++x) {
        set_pixel(x, 10, 80, 140, 200);
    }

    // Top platform (y=6)
    for (int x = 4; x <= 11; ++x) {
        set_pixel(x, 6, 100, 160, 220);
    }

    // Render Projectiles
    for (int i = 0; i < MAX_PROJECTILES; ++i) {
        const Projectile& p = projectiles_[i];
        if (!p.active) continue;

        int px = (int)std::round(p.x);
        int py = (int)std::round(p.y);

        if (p.elem == ELEM_SNOW) {
            set_pixel(px, py, 230, 240, 255); // Ice white
        } else if (p.elem == ELEM_WATER) {
            set_pixel(px, py, 40, 150, 255);  // Water blue
        } else if (p.elem == ELEM_LIGHTNING) {
            set_pixel(px, py, 255, 240, 40);  // Thunder yellow
        } else {
            set_pixel(px, py, 50, 255, 120);  // Cyclone green
        }
    }

    // Render Monsters
    for (int i = 0; i < MAX_MONSTERS; ++i) {
        const Monster& m = monsters_[i];
        if (!m.active) continue;

        int mx = (int)std::round(m.x);
        int my = (int)std::round(m.y);

        if (m.is_kicked || m.inflate_level >= 3) {
            // Giant rolling/trapped elemental sphere (2x2)
            uint8_t cr = 240, cg = 240, cb = 255;
            if (m.sphere_elem == ELEM_WATER) { cr = 30; cg = 120; cb = 240; }
            else if (m.sphere_elem == ELEM_LIGHTNING) { cr = 255; cg = 220; cb = 20; }
            else if (m.sphere_elem == ELEM_WIND) { cr = 40; cg = 240; cb = 100; }

            set_pixel(mx, my - 1, cr, cg, cb);
            set_pixel(mx + 1, my - 1, cr, cg, cb);
            set_pixel(mx, my, cr, cg, cb);
            set_pixel(mx + 1, my, cr, cg, cb);
        } else if (m.inflate_level > 0) {
            // Partially inflated monster
            set_pixel(mx, my, 220, 100, 140);
            set_pixel(mx, my - 1, 240, 180, 180);
        } else {
            // Normal red imp monster
            set_pixel(mx, my, 220, 40, 40);
            set_pixel(mx, my - 1, 255, 100, 60);
        }
    }

    // Render Hero Elf
    int hx = (int)std::round(px_);
    int hy = (int)std::round(py_);

    if (state_ == STATE_HERO_HIT) {
        set_pixel(hx, hy, 255, 50, 50);
        set_pixel(hx, hy - 1, 255, 255, 0);
    } else {
        // Body color depends on chosen elf element:
        // Snow (Nick): White/Blue
        // Water (Roy): Cyan/Blue
        // Lightning (Ching): Yellow
        // Wind (Shin-Shin): Green
        uint8_t r = 240, g = 240, b = 255;
        if (current_element_ == ELEM_WATER) { r = 40; g = 180; b = 255; }
        else if (current_element_ == ELEM_LIGHTNING) { r = 255; g = 220; b = 40; }
        else if (current_element_ == ELEM_WIND) { r = 50; g = 230; b = 100; }

        set_pixel(hx, hy, r, g, b);
        set_pixel(hx, hy - 1, 250, 200, 160); // face
        set_pixel(hx + facing_, hy - 1, r, g, b); // hat tip
    }

    // HUD: Lives on top-left, current element orb on top-right
    for (int l = 0; l < lives_ && l < 3; ++l) {
        set_pixel(l, 0, 255, 100, 150);
    }

    // Active Element Icon
    uint8_t er = 255, eg = 255, eb = 255;
    if (current_element_ == ELEM_WATER) { er = 0; eg = 150; eb = 255; }
    else if (current_element_ == ELEM_LIGHTNING) { er = 255; eg = 240; eb = 0; }
    else if (current_element_ == ELEM_WIND) { er = 0; eg = 255; eb = 100; }
    set_pixel(15, 0, er, eg, eb);
}

} // namespace arcade
