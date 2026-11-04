// game_006_bubble_bobble.cpp —— 目标 #006 泡泡捕敌 (Bubble Bobble) 核心实现
#include "game_006_bubble_bobble.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <math.h>
#include <string.h>

namespace arcade {

enum BubblePhase : uint8_t {
    BUB_SHOOT = 0,
    BUB_FLOAT = 1,
};

static inline void SetPx006(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

Game006BubbleBobble::Game006BubbleBobble()
    : state_(STATE_TITLE),
      wave_idx_(0),
      lives_(3),
      player_x_(2.0f),
      player_y_(13.0f),
      player_vy_(0.0f),
      facing_dir_(1),
      on_ground_(true),
      shoot_cooldown_(0.0f),
      invuln_timer_(0.0f),
      score_(0),
      high_score_(0),
      state_timer_(0.0f),
      anim_timer_(0.0f),
      enemies_{},
      bubbles_{},
      fruits_{} {
}

void Game006BubbleBobble::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

bool Game006BubbleBobble::IsPlatformTop(int x, int plat_y) const {
    if (x < 1 || x > 14) return false;
    if (plat_y == 14) return true;
    if (plat_y == 10 && ((x >= 2 && x <= 6) || (x >= 9 && x <= 13))) return true;
    if (plat_y == 6 && (x >= 4 && x <= 11)) return true;
    return false;
}

float Game006BubbleBobble::ResolveLandingY(float x, float old_y, float new_y, bool& landed) const {
    landed = false;
    int ix = (int)roundf(x);
    const int plat_rows[3] = {6, 10, 14};
    for (int i = 0; i < 3; ++i) {
        int py = plat_rows[i];
        float stand_y = (float)(py - 1);
        if (IsPlatformTop(ix, py) && old_y <= stand_y + 0.25f && new_y >= stand_y) {
            landed = true;
            return stand_y;
        }
    }
    if (new_y >= 13.0f) {
        landed = true;
        return 13.0f;
    }
    return new_y;
}

void Game006BubbleBobble::LoadWave(int wave_idx, bool clear_fruits) {
    wave_idx_ = wave_idx;
    for (int i = 0; i < kMaxBubbles; ++i) bubbles_[i].active = false;
    if (clear_fruits) {
        for (int i = 0; i < kMaxFruits; ++i) fruits_[i].active = false;
    }

    if (clear_fruits) {
        player_x_ = 2.0f;
        player_y_ = 13.0f;
        player_vy_ = 0.0f;
        facing_dir_ = 1;
        on_ground_ = true;
    }
    shoot_cooldown_ = 0.0f;
    invuln_timer_ = 0.8f;

    for (int i = 0; i < kMaxEnemies; ++i) enemies_[i].active = false;

    if (wave_idx == 0) {
        enemies_[0] = {6.0f, 13.0f, 2.2f, 0.0f, 2.5f, true, false, false, true};
        enemies_[1] = {10.0f, 9.0f, -2.2f, 0.0f, 1.8f, true, false, false, true};
    } else if (wave_idx == 1) {
        enemies_[0] = {12.0f, 13.0f, -2.6f, 0.0f, 2.0f, true, false, false, true};
        enemies_[1] = {4.0f, 9.0f, 2.5f, 0.0f, 1.5f, true, false, false, true};
        enemies_[2] = {8.0f, 5.0f, -2.5f, 0.0f, 2.2f, true, false, false, true};
    } else {
        enemies_[0] = {12.0f, 13.0f, -3.2f, 0.0f, 1.6f, true, false, false, true};
        enemies_[1] = {11.0f, 9.0f, -3.0f, 0.0f, 1.2f, true, false, false, true};
        enemies_[2] = {6.0f, 5.0f, 3.0f, 0.0f, 1.9f, true, false, false, true};
    }
}

void Game006BubbleBobble::Init() {
    Reset();
}

void Game006BubbleBobble::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    score_ = 0;
    lives_ = 3;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    LoadWave(0, true);
    invuln_timer_ = 0.0f;
    state_ = STATE_TITLE;
}

void Game006BubbleBobble::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        score_ = 0;
        lives_ = 3;
        state_timer_ = 0.0f;
        anim_timer_ = 0.0f;
        LoadWave(0, true);
        invuln_timer_ = 0.0f;
        state_ = STATE_PLAYING;
    }
}

void Game006BubbleBobble::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game006BubbleBobble::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

void Game006BubbleBobble::ShootBubble() {
    if (shoot_cooldown_ > 0.0f) return;
    for (int i = 0; i < kMaxBubbles; ++i) {
        if (!bubbles_[i].active) {
            bubbles_[i].active = true;
            float bx = player_x_ + (float)facing_dir_ * 0.8f;
            if (bx < 1.0f) bx = 1.0f;
            if (bx > 14.0f) bx = 14.0f;
            bubbles_[i].x = bx;
            bubbles_[i].y = player_y_;
            bubbles_[i].vx = (float)facing_dir_ * 12.0f;
            bubbles_[i].dist_left = 5.0f;
            bubbles_[i].timer = 4.0f;
            bubbles_[i].trapped_enemy = -1;
            bubbles_[i].phase = BUB_SHOOT;
            shoot_cooldown_ = 0.22f;
            return;
        }
    }
}

void Game006BubbleBobble::SpawnFruit(float x, float y) {
    for (int i = 0; i < kMaxFruits; ++i) {
        if (!fruits_[i].active) {
            fruits_[i].active = true;
            fruits_[i].x = x;
            fruits_[i].y = y;
            fruits_[i].vy = 0.0f;
            fruits_[i].timer = 6.0f;
            fruits_[i].landed = false;
            return;
        }
    }
}

void Game006BubbleBobble::UpdateBubbles(float dt) {
    for (int i = 0; i < kMaxBubbles; ++i) {
        if (!bubbles_[i].active) continue;

        if (bubbles_[i].phase == BUB_SHOOT) {
            float step = bubbles_[i].vx * dt;
            bubbles_[i].x += step;
            bubbles_[i].dist_left -= fabsf(step);
            if (bubbles_[i].x <= 1.0f) {
                bubbles_[i].x = 1.0f;
                bubbles_[i].phase = BUB_FLOAT;
            } else if (bubbles_[i].x >= 14.0f) {
                bubbles_[i].x = 14.0f;
                bubbles_[i].phase = BUB_FLOAT;
            } else if (bubbles_[i].dist_left <= 0.0f) {
                bubbles_[i].phase = BUB_FLOAT;
            }
        } else {
            bubbles_[i].timer -= dt;
            if (bubbles_[i].timer <= 0.0f) {
                if (bubbles_[i].trapped_enemy >= 0) {
                    int e = bubbles_[i].trapped_enemy;
                    if (enemies_[e].active) {
                        enemies_[e].trapped = false;
                        enemies_[e].angry = true;
                        enemies_[e].x = bubbles_[i].x;
                        enemies_[e].y = bubbles_[i].y;
                        enemies_[e].vy = 0.0f;
                        enemies_[e].on_ground = false;
                        enemies_[e].vx = (enemies_[e].vx >= 0.0f) ? 4.4f : -4.4f;
                    }
                }
                bubbles_[i].active = false;
                continue;
            }
            if (bubbles_[i].y > 2.0f) {
                bubbles_[i].y -= 2.2f * dt;
                if (bubbles_[i].y < 2.0f) bubbles_[i].y = 2.0f;
            }
        }

        // Check trapping free enemy
        if (bubbles_[i].trapped_enemy < 0) {
            for (int e = 0; e < kMaxEnemies; ++e) {
                if (enemies_[e].active && !enemies_[e].trapped) {
                    if (fabsf(bubbles_[i].x - enemies_[e].x) <= 1.0f &&
                        fabsf(bubbles_[i].y - enemies_[e].y) <= 1.0f) {
                        bubbles_[i].trapped_enemy = e;
                        bubbles_[i].phase = BUB_FLOAT;
                        bubbles_[i].timer = 4.0f;
                        enemies_[e].trapped = true;
                        AddScore(20);
                        break;
                    }
                }
            }
        }

        if (bubbles_[i].trapped_enemy >= 0) {
            int e = bubbles_[i].trapped_enemy;
            enemies_[e].x = bubbles_[i].x;
            enemies_[e].y = bubbles_[i].y;

            // Player pops trapped bubble on contact!
            if (fabsf(player_x_ - bubbles_[i].x) <= 1.15f &&
                fabsf(player_y_ - bubbles_[i].y) <= 1.15f) {
                enemies_[e].active = false;
                enemies_[e].trapped = false;
                SpawnFruit(bubbles_[i].x, bubbles_[i].y);
                bubbles_[i].active = false;
                AddScore(100);
                continue;
            }
        } else if (bubbles_[i].phase == BUB_FLOAT) {
            // Optional bounce on empty bubble from above
            if (player_vy_ > 0.0f && fabsf(player_x_ - bubbles_[i].x) <= 0.9f &&
                player_y_ < bubbles_[i].y && (bubbles_[i].y - player_y_) <= 1.15f) {
                player_vy_ = -13.5f;
                on_ground_ = false;
                bubbles_[i].active = false;
            }
        }
    }
}

void Game006BubbleBobble::UpdateFruits(float dt) {
    for (int i = 0; i < kMaxFruits; ++i) {
        if (!fruits_[i].active) continue;
        fruits_[i].timer -= dt;
        if (fruits_[i].timer <= 0.0f) {
            fruits_[i].active = false;
            continue;
        }
        if (!fruits_[i].landed) {
            float old_y = fruits_[i].y;
            fruits_[i].vy += 24.0f * dt;
            float new_y = fruits_[i].y + fruits_[i].vy * dt;
            bool landed = false;
            fruits_[i].y = ResolveLandingY(fruits_[i].x, old_y, new_y, landed);
            if (landed) {
                fruits_[i].landed = true;
                fruits_[i].vy = 0.0f;
            }
        }
        if (fabsf(player_x_ - fruits_[i].x) <= 1.1f && fabsf(player_y_ - fruits_[i].y) <= 1.1f) {
            fruits_[i].active = false;
            AddScore(150);
        }
    }
}

void Game006BubbleBobble::UpdateEnemies(float dt) {
    int alive_count = 0;
    for (int i = 0; i < kMaxEnemies; ++i) {
        if (!enemies_[i].active) continue;
        alive_count++;
        if (enemies_[i].trapped) continue;

        enemies_[i].x += enemies_[i].vx * dt;
        if (enemies_[i].x <= 1.0f) {
            enemies_[i].x = 1.0f;
            enemies_[i].vx = fabsf(enemies_[i].vx);
        } else if (enemies_[i].x >= 14.0f) {
            enemies_[i].x = 14.0f;
            enemies_[i].vx = -fabsf(enemies_[i].vx);
        }

        if (enemies_[i].on_ground) {
            int support_py = (int)roundf(enemies_[i].y) + 1;
            if (!IsPlatformTop((int)roundf(enemies_[i].x), support_py)) {
                enemies_[i].on_ground = false;
            } else {
                enemies_[i].jump_timer -= dt;
                if (enemies_[i].jump_timer <= 0.0f) {
                    enemies_[i].jump_timer = enemies_[i].angry ? 1.4f : 2.4f;
                    if (player_y_ < enemies_[i].y - 1.5f) {
                        enemies_[i].vy = -15.2f;
                        enemies_[i].on_ground = false;
                    }
                }
            }
        }

        if (!enemies_[i].on_ground) {
            float old_y = enemies_[i].y;
            enemies_[i].vy += 28.0f * dt;
            float new_y = enemies_[i].y + enemies_[i].vy * dt;
            if (enemies_[i].vy >= 0.0f) {
                bool landed = false;
                new_y = ResolveLandingY(enemies_[i].x, old_y, new_y, landed);
                if (landed) {
                    enemies_[i].on_ground = true;
                    enemies_[i].vy = 0.0f;
                }
            }
            enemies_[i].y = new_y;
        }

        if (invuln_timer_ <= 0.0f &&
            fabsf(player_x_ - enemies_[i].x) <= 0.85f &&
            fabsf(player_y_ - enemies_[i].y) <= 0.85f) {
            if (lives_ > 1) {
                lives_--;
                player_x_ = 2.0f;
                player_y_ = 13.0f;
                player_vy_ = 0.0f;
                on_ground_ = true;
                invuln_timer_ = 1.2f;
            } else {
                lives_ = 0;
                state_ = STATE_GAMEOVER;
                state_timer_ = 0.0f;
                return;
            }
        }
    }

    if (alive_count == 0) {
        if (wave_idx_ + 1 < kNumWaves) {
            LoadWave(wave_idx_ + 1, false);
        } else {
            AddScore(300);
            state_ = STATE_VICTORY;
            state_timer_ = 0.0f;
        }
    }
}

void Game006BubbleBobble::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt > 0.05f) dt = 0.05f;
    state_timer_ += dt;
    anim_timer_ += dt;

    if (state_ == STATE_TITLE) {
        if (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_LEFT | KEY_RIGHT | KEY_UP)) {
            Start();
        }
        return;
    }

    if (state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        if (state_timer_ > 0.5f && (keys_pressed & (KEY_START | KEY_A | KEY_B))) {
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

        if (shoot_cooldown_ > 0.0f) shoot_cooldown_ -= dt;
        if (invuln_timer_ > 0.0f) invuln_timer_ -= dt;

        // Horizontal movement
        const float move_speed = 6.8f;
        if (keys_down & KEY_LEFT) {
            player_x_ -= move_speed * dt;
            facing_dir_ = -1;
        } else if (keys_down & KEY_RIGHT) {
            player_x_ += move_speed * dt;
            facing_dir_ = 1;
        }
        if (player_x_ < 1.0f) player_x_ = 1.0f;
        if (player_x_ > 14.0f) player_x_ = 14.0f;

        // KEY_A (or KEY_UP): Jump (passes through platforms from below!)
        if (on_ground_ && (keys_pressed & (KEY_A | KEY_UP))) {
            player_vy_ = -15.8f;
            on_ground_ = false;
        }

        // KEY_B: Shoot bubble horizontally
        if (keys_pressed & KEY_B) {
            ShootBubble();
        }

        if (on_ground_) {
            int support_py = (int)roundf(player_y_) + 1;
            if (!IsPlatformTop((int)roundf(player_x_), support_py)) {
                on_ground_ = false;
                player_vy_ = 0.0f;
            }
        }

        if (!on_ground_) {
            float old_y = player_y_;
            player_vy_ += 28.0f * dt;
            if (player_vy_ > 14.0f) player_vy_ = 14.0f;
            float new_y = player_y_ + player_vy_ * dt;
            if (new_y < 1.0f) {
                new_y = 1.0f;
                player_vy_ = 0.0f;
            }
            if (player_vy_ >= 0.0f) {
                bool landed = false;
                new_y = ResolveLandingY(player_x_, old_y, new_y, landed);
                if (landed) {
                    on_ground_ = true;
                    player_vy_ = 0.0f;
                }
            }
            player_y_ = new_y;
        }

        UpdateBubbles(dt);
        UpdateFruits(dt);
        UpdateEnemies(dt);
    }
}

void Game006BubbleBobble::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (x == 0 || x == 15) {
                SetPx006(fb_rgb24, x, y, 95, 50, 130);
            } else {
                SetPx006(fb_rgb24, x, y, 12, 10, 24);
            }
        }
    }

    // Platforms
    for (int x = 1; x <= 14; ++x) {
        SetPx006(fb_rgb24, x, 14, 155, 89, 182);
        SetPx006(fb_rgb24, x, 15, 85, 45, 110);
        if (IsPlatformTop(x, 10)) SetPx006(fb_rgb24, x, 10, 155, 89, 182);
        if (IsPlatformTop(x, 6))  SetPx006(fb_rgb24, x, 6, 155, 89, 182);
    }

    // Fruit bonuses
    for (int i = 0; i < kMaxFruits; ++i) {
        if (fruits_[i].active) {
            SetPx006(fb_rgb24, (int)roundf(fruits_[i].x), (int)roundf(fruits_[i].y), 255, 165, 20);
        }
    }

    // Free enemies
    for (int i = 0; i < kMaxEnemies; ++i) {
        if (enemies_[i].active && !enemies_[i].trapped) {
            int ex = (int)roundf(enemies_[i].x);
            int ey = (int)roundf(enemies_[i].y);
            if (enemies_[i].angry) {
                SetPx006(fb_rgb24, ex, ey, 255, 40, 40);
            } else {
                SetPx006(fb_rgb24, ex, ey, 231, 95, 65);
            }
        }
    }

    // Bubbles (cyan when empty, bright gold-green when enemy is trapped inside)
    for (int i = 0; i < kMaxBubbles; ++i) {
        if (!bubbles_[i].active) continue;
        int bx = (int)roundf(bubbles_[i].x);
        int by = (int)roundf(bubbles_[i].y);
        if (bubbles_[i].trapped_enemy >= 0) {
            SetPx006(fb_rgb24, bx, by, 245, 220, 45);
        } else {
            SetPx006(fb_rgb24, bx, by, 70, 225, 255);
        }
    }

    // Player Bub (bright green dragon)
    if (lives_ > 0 && (invuln_timer_ <= 0.0f || (((int)(anim_timer_ * 16.0f)) & 1) == 0)) {
        SetPx006(fb_rgb24, (int)roundf(player_x_), (int)roundf(player_y_), 46, 240, 115);
    }

    // Lives HUD at y=0, x=1..3
    for (int i = 0; i < (int)lives_ && i < 3; ++i) {
        SetPx006(fb_rgb24, 1 + i, 0, 46, 240, 115);
    }

    if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPx006(fb_rgb24, 6, y, 250, 250, 250);
            SetPx006(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game006BubbleBobble::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = lives_;
    st.state = (uint8_t)state_;
    if (state_ == STATE_VICTORY) {
        st.progress = 100;
    } else {
        st.progress = (uint8_t)((wave_idx_ * 100) / kNumWaves);
    }
    return st;
}

static_assert(sizeof(Game006BubbleBobble) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
