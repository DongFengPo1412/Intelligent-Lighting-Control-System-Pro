#include "game_129_starcastle.h"
#include <cmath>
#include <cstdlib>
#include <cstring>

namespace arcade {

static constexpr float PI = 3.14159265f;
static constexpr float TWO_PI = 6.2831853f;
static constexpr float CENTER_X = 7.5f;
static constexpr float CENTER_Y = 7.5f;
static constexpr float RING_RADII[3] = {5.4f, 3.8f, 2.4f};

Game129StarCastle::Game129StarCastle() {
    Init();
}

void Game129StarCastle::Init() {
    score_ = 0;
    lives_ = 3;
    level_ = 1;
    InitCastle();
}

void Game129StarCastle::Reset() {
    Init();
}

void Game129StarCastle::InitCastle() {
    state_ = STATE_PLAYING;
    state_timer_ = 0.0f;

    px_ = 7.5f;
    py_ = 14.2f;
    pvx_ = 0.0f;
    pvy_ = 0.0f;
    p_angle_ = -PI * 0.5f; // Facing UP towards castle

    turret_angle_ = 0.0f;
    turret_fire_timer_ = 1.5f;
    blast_.active = false;

    // Rings
    ring_angles_[0] = 0.0f;
    ring_angles_[1] = 0.2f;
    ring_angles_[2] = 0.5f;

    ring_speeds_[0] = 0.8f + level_ * 0.1f;
    ring_speeds_[1] = -(1.1f + level_ * 0.15f);
    ring_speeds_[2] = 1.4f + level_ * 0.2f;

    for (int r = 0; r < NUM_RINGS; ++r) {
        for (int s = 0; s < SEGMENTS_PER_RING; ++s) {
            shield_alive_[r][s] = true;
        }
    }

    for (int i = 0; i < MAX_BULLETS; ++i) {
        bullets_[i].active = false;
    }

    for (int i = 0; i < MAX_SPARKS; ++i) {
        sparks_[i].active = false;
    }
    spark_spawn_timer_ = 1.2f;
}

bool Game129StarCastle::HasDirectLineOfSight(float angle) const {
    while (angle < 0.0f) angle += TWO_PI;
    while (angle >= TWO_PI) angle -= TWO_PI;

    for (int r = 0; r < NUM_RINGS; ++r) {
        float rel_ang = angle - ring_angles_[r];
        while (rel_ang < 0.0f) rel_ang += TWO_PI;
        while (rel_ang >= TWO_PI) rel_ang -= TWO_PI;

        int seg = (int)(rel_ang / (TWO_PI / 8.0f)) % 8;
        if (shield_alive_[r][seg]) {
            return false; // Obstructed by shield ring r
        }
    }
    return true; // Wide open through all 3 rings!
}

void Game129StarCastle::Update(float dt, uint16_t buttons, uint16_t prev_buttons) {
    if (dt <= 0.0f) return;
    if (dt > 0.05f) dt = 0.05f;

    state_timer_ += dt;

    if (state_ == STATE_GAME_OVER) {
        if ((buttons & 0x0030) && !(prev_buttons & 0x0030)) {
            Reset();
        }
        return;
    }

    if (state_ == STATE_PLAYER_EXPLODING) {
        if (state_timer_ > 1.3f) {
            lives_--;
            if (lives_ == 0) {
                state_ = STATE_GAME_OVER;
            } else {
                state_ = STATE_PLAYING;
                px_ = 7.5f;
                py_ = 14.2f;
                pvx_ = 0.0f;
                pvy_ = 0.0f;
                p_angle_ = -PI * 0.5f;
            }
        }
        return;
    }

    if (state_ == STATE_CASTLE_EXPLODING) {
        if (state_timer_ > 1.8f) {
            level_++;
            score_ += 1000;
            InitCastle();
        }
        return;
    }

    // Button A: Fire Torpedo
    if ((buttons & 0x0010) && !(prev_buttons & 0x0010)) {
        for (int i = 0; i < MAX_BULLETS; ++i) {
            if (!bullets_[i].active) {
                bullets_[i].active = true;
                bullets_[i].x = px_;
                bullets_[i].y = py_;
                bullets_[i].vx = std::cos(p_angle_) * 16.0f + pvx_ * 0.5f;
                bullets_[i].vy = std::sin(p_angle_) * 16.0f + pvy_ * 0.5f;
                break;
            }
        }
    }

    // Button B: Retro brake
    if ((buttons & 0x0020) && !(prev_buttons & 0x0020)) {
        pvx_ *= 0.2f;
        pvy_ *= 0.2f;
    }

    UpdateShip(dt, buttons);
    UpdateShields(dt);
    UpdateBullets(dt);
    UpdateSparks(dt);
    UpdateBossTurret(dt);
    CheckCollisions();
}

void Game129StarCastle::UpdateShip(float dt, uint16_t buttons) {
    float turn_speed = 4.5f;
    if (buttons & 0x0004) p_angle_ -= turn_speed * dt; // LEFT
    if (buttons & 0x0008) p_angle_ += turn_speed * dt; // RIGHT

    while (p_angle_ < 0.0f) p_angle_ += TWO_PI;
    while (p_angle_ >= TWO_PI) p_angle_ -= TWO_PI;

    // Thrust
    float thrust = 10.0f;
    if (buttons & 0x0001) { // UP
        pvx_ += std::cos(p_angle_) * thrust * dt;
        pvy_ += std::sin(p_angle_) * thrust * dt;
    }

    // Drag
    pvx_ *= 0.96f;
    pvy_ *= 0.96f;

    px_ += pvx_ * dt;
    py_ += pvy * dt;

    // Wrap
    while (px_ < 0.0f) px_ += 16.0f;
    while (px_ >= 16.0f) px_ -= 16.0f;
    while (py_ < 0.0f) py_ += 16.0f;
    while (py_ >= 16.0f) py_ -= 16.0f;
}

void Game129StarCastle::UpdateShields(float dt) {
    for (int r = 0; r < NUM_RINGS; ++r) {
        ring_angles_[r] += ring_speeds_[r] * dt;
        while (ring_angles_[r] < 0.0f) ring_angles_[r] += TWO_PI;
        while (ring_angles_[r] >= TWO_PI) ring_angles_[r] -= TWO_PI;

        // Check if all segments of outer ring destroyed -> regenerate
        bool any_alive = false;
        for (int s = 0; s < SEGMENTS_PER_RING; ++s) {
            if (shield_alive_[r][s]) {
                any_alive = true;
                break;
            }
        }
        if (!any_alive && r == 0) {
            for (int s = 0; s < SEGMENTS_PER_RING; ++s) {
                shield_alive_[r][s] = true;
            }
        }
    }
}

void Game129StarCastle::UpdateBullets(float dt) {
    for (int i = 0; i < MAX_BULLETS; ++i) {
        if (!bullets_[i].active) continue;
        bullets_[i].x += bullets_[i].vx * dt;
        bullets_[i].y += bullets_[i].vy * dt;

        if (bullets_[i].x < 0.0f || bullets_[i].x >= 16.0f ||
            bullets_[i].y < 0.0f || bullets_[i].y >= 16.0f) {
            bullets_[i].active = false;
        }
    }

    if (blast_.active) {
        blast_.x += blast_.vx * dt;
        blast_.y += blast_.vy * dt;
        if (blast_.x < 0.0f || blast_.x >= 16.0f || blast_.y < 0.0f || blast_.y >= 16.0f) {
            blast_.active = false;
        }
    }
}

void Game129StarCastle::UpdateSparks(float dt) {
    spark_spawn_timer_ -= dt;
    if (spark_spawn_timer_ <= 0.0f) {
        spark_spawn_timer_ = 3.5f - level_ * 0.2f;
        if (spark_spawn_timer_ < 1.5f) spark_spawn_timer_ = 1.5f;

        for (int i = 0; i < MAX_SPARKS; ++i) {
            if (!sparks_[i].active) {
                sparks_[i].active = true;
                sparks_[i].x = CENTER_X;
                sparks_[i].y = CENTER_Y;
                sparks_[i].vx = 0.0f;
                sparks_[i].vy = 0.0f;
                break;
            }
        }
    }

    // Spark homing towards player
    float spark_speed = 3.2f + level_ * 0.25f;
    for (int i = 0; i < MAX_SPARKS; ++i) {
        if (!sparks_[i].active) continue;

        float dx = px_ - sparks_[i].x;
        float dy = py_ - sparks_[i].y;
        float dist = std::sqrt(dx * dx + dy * dy);
        if (dist > 0.1f) {
            sparks_[i].vx = (dx / dist) * spark_speed;
            sparks_[i].vy = (dy / dist) * spark_speed;
        }
        sparks_[i].x += sparks_[i].vx * dt;
        sparks_[i].y += sparks_[i].vy * dt;
    }
}

void Game129StarCastle::UpdateBossTurret(float dt) {
    // Turret aims towards player
    turret_angle_ = std::atan2(py_ - CENTER_Y, px_ - CENTER_X);

    turret_fire_timer_ -= dt;
    if (turret_fire_timer_ <= 0.0f) {
        turret_fire_timer_ = 0.8f;
        // Check if there is an open direct line of sight through the shields
        if (HasDirectLineOfSight(turret_angle_) && !blast_.active) {
            blast_.active = true;
            blast_.x = CENTER_X;
            blast_.y = CENTER_Y;
            float blast_speed = 18.0f;
            blast_.vx = std::cos(turret_angle_) * blast_speed;
            blast_.vy = std::sin(turret_angle_) * blast_speed;
        }
    }
}

void Game129StarCastle::CheckCollisions() {
    // 1. Bullets vs Sparks, Shields, and Castle Core
    for (int b = 0; b < MAX_BULLETS; ++b) {
        if (!bullets_[b].active) continue;

        // vs Sparks
        for (int s = 0; s < MAX_SPARKS; ++s) {
            if (!sparks_[s].active) continue;
            float dx = std::abs(bullets_[b].x - sparks_[s].x);
            float dy = std::abs(bullets_[b].y - sparks_[s].y);
            if (dx < 0.8f && dy < 0.8f) {
                bullets_[b].active = false;
                sparks_[s].active = false;
                score_ += 50;
                break;
            }
        }
        if (!bullets_[b].active) continue;

        // Dist from center
        float cdx = bullets_[b].x - CENTER_X;
        float cdy = bullets_[b].y - CENTER_Y;
        float b_dist = std::sqrt(cdx * cdx + cdy * cdy);
        float b_angle = std::atan2(cdy, cdx);

        // Core Hit!
        if (b_dist < 1.2f) {
            bullets_[b].active = false;
            state_ = STATE_CASTLE_EXPLODING;
            state_timer_ = 0.0f;
            continue;
        }

        // Shield segments
        for (int r = 0; r < NUM_RINGS; ++r) {
            if (std::abs(b_dist - RING_RADII[r]) < 0.55f) {
                float rel_ang = b_angle - ring_angles_[r];
                while (rel_ang < 0.0f) rel_ang += TWO_PI;
                while (rel_ang >= TWO_PI) rel_ang -= TWO_PI;

                int seg = (int)(rel_ang / (TWO_PI / 8.0f)) % 8;
                if (shield_alive_[r][seg]) {
                    shield_alive_[r][seg] = false; // Blast away segment!
                    bullets_[b].active = false;
                    score_ += 20;
                    break;
                }
            }
        }
    }

    // 2. Player vs Sparks & Core Blast
    if (blast_.active) {
        float bdx = std::abs(px_ - blast_.x);
        float bdy = std::abs(py_ - blast_.y);
        if (bdx < 0.85f && bdy < 0.85f) {
            blast_.active = false;
            state_ = STATE_PLAYER_EXPLODING;
            state_timer_ = 0.0f;
        }
    }

    for (int s = 0; s < MAX_SPARKS; ++s) {
        if (!sparks_[s].active) continue;
        float sdx = std::abs(px_ - sparks_[s].x);
        float sdy = std::abs(py_ - sparks_[s].y);
        if (sdx < 0.75f && sdy < 0.75f) {
            sparks_[s].active = false;
            state_ = STATE_PLAYER_EXPLODING;
            state_timer_ = 0.0f;
            break;
        }
    }
}

void Game129StarCastle::Render(uint8_t* fb) {
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

    // 1. Draw 3 concentric shield rings
    uint8_t ring_colors[3][3] = {
        {255, 60, 40},   // Outer red
        {255, 200, 30},  // Middle yellow
        {40, 200, 255}   // Inner cyan
    };

    for (int r = 0; r < NUM_RINGS; ++r) {
        float radius = RING_RADII[r];
        for (int s = 0; s < SEGMENTS_PER_RING; ++s) {
            if (!shield_alive_[r][s]) continue;

            float ang_start = ring_angles_[r] + (float)s * (TWO_PI / 8.0f);
            float ang_mid = ang_start + (TWO_PI / 16.0f);

            int sx = (int)std::round(CENTER_X + radius * std::cos(ang_mid));
            int sy = (int)std::round(CENTER_Y + radius * std::sin(ang_mid));
            set_pixel(sx, sy, ring_colors[r][0], ring_colors[r][1], ring_colors[r][2]);
        }
    }

    // 2. Central Castle Core Turret at (7, 7)-(8, 8)
    if (state_ == STATE_CASTLE_EXPLODING) {
        set_pixel(7, 7, 255, 220, 50);
        set_pixel(8, 7, 255, 80, 20);
        set_pixel(7, 8, 255, 80, 20);
        set_pixel(8, 8, 255, 220, 50);
    } else {
        set_pixel(7, 7, 200, 50, 220); // Castle core purple
        set_pixel(8, 7, 200, 50, 220);
        set_pixel(7, 8, 200, 50, 220);
        set_pixel(8, 8, 255, 255, 255); // Turret muzzle
    }

    // 3. Boss Cannon Blast
    if (blast_.active) {
        int bx = (int)std::round(blast_.x);
        int by = (int)std::round(blast_.y);
        set_pixel(bx, by, 255, 30, 20);
        set_pixel(bx - (int)(blast_.vx * 0.05f), by - (int)(blast_.vy * 0.05f), 255, 220, 40);
    }

    // 4. Sparks
    for (int s = 0; s < MAX_SPARKS; ++s) {
        if (!sparks_[s].active) continue;
        int sx = (int)std::round(sparks_[s].x);
        int sy = (int)std::round(sparks_[s].y);
        bool flash = ((int)(state_timer_ * 12.0f) % 2) == 0;
        set_pixel(sx, sy, flash ? 255 : 200, flash ? 255 : 100, 0);
    }

    // 5. Bullets
    for (int b = 0; b < MAX_BULLETS; ++b) {
        if (!bullets_[b].active) continue;
        int bx = (int)std::round(bullets_[b].x);
        int by = (int)std::round(bullets_[b].y);
        set_pixel(bx, by, 80, 255, 120);
    }

    // 6. Player Starfighter
    int px_s = (int)std::round(px_);
    int py_s = (int)std::round(py_);
    if (state_ == STATE_PLAYING || state_ == STATE_CASTLE_EXPLODING) {
        set_pixel(px_s, py_s, 255, 255, 255);
        int nx = px_s + (int)std::round(std::cos(p_angle_));
        int ny = py_s + (int)std::round(std::sin(p_angle_));
        set_pixel(nx, ny, 0, 220, 255); // Cyan nose
    } else if (state_ == STATE_PLAYER_EXPLODING) {
        set_pixel(px_s, py_s, 255, 200, 50);
        set_pixel(px_s - 1, py_s, 255, 40, 20);
        set_pixel(px_s + 1, py_s, 255, 40, 20);
        set_pixel(px_s, py_s - 1, 255, 40, 20);
        set_pixel(px_s, py_s + 1, 255, 40, 20);
    }

    // 7. Lives
    for (int l = 0; l < lives_ && l < 3; ++l) {
        set_pixel(l * 2, 0, 0, 230, 255);
    }
}

} // namespace arcade
