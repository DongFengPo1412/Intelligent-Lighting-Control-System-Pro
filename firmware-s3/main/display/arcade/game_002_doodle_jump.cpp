// game_002_doodle_jump.cpp —— 目标 #002 涂鸦跳跃 (Doodle Jump) 核心实现
#include "game_002_doodle_jump.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <math.h>
#include <string.h>

namespace arcade {

static inline void SetPx002(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

Game002DoodleJump::Game002DoodleJump()
    : state_(STATE_TITLE),
      player_x_(7.0f),
      player_y_(11.0f),
      player_vx_(0.0f),
      player_vy_(0.0f),
      facing_right_(true),
      max_altitude_(0.0f),
      score_(0),
      high_score_(0),
      state_timer_(0.0f),
      anim_timer_(0.0f),
      rng_seed_(0x20090002u),
      platforms_{} {
}

uint32_t Game002DoodleJump::NextRand() {
    rng_seed_ = rng_seed_ * 1664525u + 1013904223u;
    return (rng_seed_ >> 16) & 0x7FFFu;
}

float Game002DoodleJump::HighestSolidY() const {
    float min_y = 14.0f;
    bool found = false;
    for (int i = 0; i < kMaxPlatforms; ++i) {
        if (!platforms_[i].broken && platforms_[i].type != DOODLE_PLAT_FRAGILE) {
            if (!found || platforms_[i].y < min_y) {
                min_y = platforms_[i].y;
                found = true;
            }
        }
    }
    return min_y;
}

void Game002DoodleJump::SpawnPlatformAbove(DoodlePlatform& p, float ref_solid_y, bool allow_fragile) {
    uint32_t r1 = NextRand();
    uint32_t r2 = NextRand();
    p.x = 1.0f + (float)(r1 % 12u);
    p.broken = false;
    p.vx = 0.0f;

    uint32_t roll = r2 % 100u;
    if (max_altitude_ < 30.0f) {
        if (roll < 75u) p.type = DOODLE_PLAT_NORMAL;
        else if (roll < 90u) p.type = DOODLE_PLAT_SPRING;
        else p.type = DOODLE_PLAT_MOVING;
    } else {
        if (roll < 50u) p.type = DOODLE_PLAT_NORMAL;
        else if (roll < 72u) p.type = DOODLE_PLAT_MOVING;
        else if (roll < 88u || !allow_fragile) p.type = DOODLE_PLAT_SPRING;
        else p.type = DOODLE_PLAT_FRAGILE;
    }

    if (p.type == DOODLE_PLAT_FRAGILE) {
        p.y = ref_solid_y - 1.2f;
    } else {
        float gap = 2.1f + (float)((r1 >> 5) % 7u) * 0.1f;
        p.y = ref_solid_y - gap;
    }

    if (p.type == DOODLE_PLAT_MOVING) {
        p.vx = ((r2 >> 8) & 1u) ? 2.8f : -2.8f;
    }
}

void Game002DoodleJump::InitPlayState() {
    rng_seed_ = 0x20090002u;
    player_x_ = 7.0f;
    player_y_ = 11.0f;
    player_vx_ = 0.0f;
    player_vy_ = -14.5f;
    facing_right_ = true;
    max_altitude_ = 0.0f;
    score_ = 0;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;

    platforms_[0].x = 6.0f;
    platforms_[0].y = 14.0f;
    platforms_[0].vx = 0.0f;
    platforms_[0].type = DOODLE_PLAT_NORMAL;
    platforms_[0].broken = false;

    float ref_y = 14.0f;
    bool prev_fragile = false;
    for (int i = 1; i < kMaxPlatforms; ++i) {
        SpawnPlatformAbove(platforms_[i], ref_y, !prev_fragile);
        if (platforms_[i].type == DOODLE_PLAT_FRAGILE) {
            prev_fragile = true;
        } else {
            prev_fragile = false;
            ref_y = platforms_[i].y;
        }
    }
}

void Game002DoodleJump::Init() {
    Reset();
}

void Game002DoodleJump::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    InitPlayState();
    state_ = STATE_TITLE;
}

void Game002DoodleJump::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        InitPlayState();
        state_ = STATE_PLAYING;
    }
}

void Game002DoodleJump::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game002DoodleJump::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

void Game002DoodleJump::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt > 0.05f) dt = 0.05f;
    state_timer_ += dt;
    anim_timer_ += dt;

    if (state_ == STATE_TITLE) {
        player_vy_ += 28.0f * dt;
        player_y_ += player_vy_ * dt;
        if (player_y_ >= 12.0f) {
            player_y_ = 12.0f;
            player_vy_ = -11.5f;
        }
        if (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP)) {
            Start();
        }
        return;
    }

    if (state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        if (state_timer_ > 0.5f && (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT))) {
            Start();
        }
        return;
    }

    if (state_ == STATE_PAUSED) {
        if (keys_pressed & KEY_START) {
            state_ = STATE_PLAYING;
        }
        return;
    }

    if (state_ == STATE_PLAYING) {
        if (keys_pressed & KEY_START) {
            state_ = STATE_PAUSED;
            return;
        }

        const float accel = 30.0f;
        const float max_vx = 8.5f;
        const float friction = 16.0f;

        if (keys_down & KEY_LEFT) {
            player_vx_ -= accel * dt;
            facing_right_ = false;
        } else if (keys_down & KEY_RIGHT) {
            player_vx_ += accel * dt;
            facing_right_ = true;
        } else {
            if (player_vx_ > 0.0f) {
                player_vx_ -= friction * dt;
                if (player_vx_ < 0.0f) player_vx_ = 0.0f;
            } else if (player_vx_ < 0.0f) {
                player_vx_ += friction * dt;
                if (player_vx_ > 0.0f) player_vx_ = 0.0f;
            }
        }

        if (player_vx_ > max_vx) player_vx_ = max_vx;
        if (player_vx_ < -max_vx) player_vx_ = -max_vx;

        const float gravity = 28.0f;
        player_vy_ += gravity * dt;
        if (player_vy_ > 16.0f) player_vy_ = 16.0f;

        float next_x = player_x_ + player_vx_ * dt;
        while (next_x < 0.0f) next_x += 16.0f;
        while (next_x >= 16.0f) next_x -= 16.0f;
        player_x_ = next_x;

        float old_y = player_y_;
        float next_y = player_y_ + player_vy_ * dt;

        for (int i = 0; i < kMaxPlatforms; ++i) {
            if (platforms_[i].type == DOODLE_PLAT_MOVING && !platforms_[i].broken) {
                platforms_[i].x += platforms_[i].vx * dt;
                if (platforms_[i].x <= 0.0f) {
                    platforms_[i].x = 0.0f;
                    platforms_[i].vx = -platforms_[i].vx;
                } else if (platforms_[i].x >= 13.0f) {
                    platforms_[i].x = 13.0f;
                    platforms_[i].vx = -platforms_[i].vx;
                }
            }
        }

        if (player_vy_ > 0.0f) {
            float feet_old = old_y + 2.0f;
            float feet_new = next_y + 2.0f;

            for (int i = 0; i < kMaxPlatforms; ++i) {
                if (platforms_[i].broken) continue;

                float plat_top = platforms_[i].y;
                float plat_left = platforms_[i].x - 0.6f;
                float plat_right = platforms_[i].x + 2.8f;

                bool horiz_hit = false;
                for (int shift = -16; shift <= 16; shift += 16) {
                    float sx = player_x_ + (float)shift;
                    if (sx + 1.8f >= plat_left && sx <= plat_right) {
                        horiz_hit = true;
                        break;
                    }
                }

                if (horiz_hit && feet_old <= plat_top + 0.55f && feet_new >= plat_top - 0.2f) {
                    next_y = plat_top - 2.0f;
                    if (platforms_[i].type == DOODLE_PLAT_SPRING) {
                        player_vy_ = -21.0f;
                    } else if (platforms_[i].type == DOODLE_PLAT_FRAGILE) {
                        platforms_[i].broken = true;
                        player_vy_ = -6.0f;
                    } else {
                        player_vy_ = -14.5f;
                    }
                    break;
                }
            }
        }

        player_y_ = next_y;

        const float scroll_line = 6.5f;
        if (player_y_ < scroll_line) {
            float dy = scroll_line - player_y_;
            player_y_ = scroll_line;
            max_altitude_ += dy;
            uint32_t new_score = (uint32_t)(max_altitude_ * 10.0f);
            if (new_score > score_) {
                score_ = new_score;
                if (score_ > high_score_) {
                    high_score_ = score_;
                    ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
                }
            }

            for (int i = 0; i < kMaxPlatforms; ++i) {
                platforms_[i].y += dy;
            }
            for (int i = 0; i < kMaxPlatforms; ++i) {
                if (platforms_[i].y >= 16.0f) {
                    float top_solid = HighestSolidY();
                    SpawnPlatformAbove(platforms_[i], top_solid, true);
                }
            }
        }

        if (player_y_ >= 16.0f) {
            state_ = STATE_GAMEOVER;
            state_timer_ = 0.0f;
            if (score_ > high_score_) {
                high_score_ = score_;
                ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
            }
        }
    }
}

void Game002DoodleJump::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            SetPx002(fb_rgb24, x, y, 10, 14, 26);
        }
    }

    int star_off = ((int)max_altitude_) & 15;
    for (int i = 0; i < 4; ++i) {
        int sx = (i * 5 + 2) & 15;
        int sy = (i * 7 + star_off) & 15;
        SetPx002(fb_rgb24, sx, sy, 32, 48, 76);
    }

    for (int i = 0; i < kMaxPlatforms; ++i) {
        if (platforms_[i].broken) continue;
        int py = (int)roundf(platforms_[i].y);
        int px = (int)roundf(platforms_[i].x);
        if (py >= 0 && py < 16) {
            uint8_t r = 39, g = 174, b = 96;
            if (platforms_[i].type == DOODLE_PLAT_MOVING) {
                r = 0; g = 210; b = 211;
            } else if (platforms_[i].type == DOODLE_PLAT_SPRING) {
                r = 241; g = 196; b = 15;
            } else if (platforms_[i].type == DOODLE_PLAT_FRAGILE) {
                r = 211; g = 84; b = 0;
            }
            for (int dx = 0; dx < 3; ++dx) {
                if (platforms_[i].type == DOODLE_PLAT_SPRING && dx == 1) {
                    SetPx002(fb_rgb24, px + dx, py, 255, 255, 255);
                } else {
                    SetPx002(fb_rgb24, px + dx, py, r, g, b);
                }
            }
        }
    }

    int px = ((int)roundf(player_x_)) & 15;
    int py = (int)roundf(player_y_);
    for (int dy = 0; dy < 2; ++dy) {
        for (int dx = 0; dx < 2; ++dx) {
            int wx = (px + dx) & 15;
            int wy = py + dy;
            if (dy == 0) {
                if ((facing_right_ && dx == 1) || (!facing_right_ && dx == 0)) {
                    SetPx002(fb_rgb24, wx, wy, 255, 255, 255);
                } else {
                    SetPx002(fb_rgb24, wx, wy, 46, 204, 113);
                }
            } else {
                SetPx002(fb_rgb24, wx, wy, 230, 126, 34);
            }
        }
    }

    if (state_ == STATE_GAMEOVER) {
        for (int x = 0; x < 16; ++x) {
            SetPx002(fb_rgb24, x, 15, 231, 76, 60);
        }
    } else if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPx002(fb_rgb24, 6, y, 250, 250, 250);
            SetPx002(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game002DoodleJump::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = (state_ == STATE_GAMEOVER) ? 0 : 1;
    st.state = (uint8_t)state_;
    st.progress = (uint8_t)(max_altitude_ > 100.0f ? 100 : (int)max_altitude_);
    return st;
}

static_assert(sizeof(Game002DoodleJump) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
