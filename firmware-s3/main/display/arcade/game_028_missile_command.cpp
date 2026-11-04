// game_028_missile_command.cpp —— 目标 #028 导弹指挥官 (Missile Command) 核心实现
#include "game_028_missile_command.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <math.h>
#include <string.h>

namespace arcade {

static const int kCityX[Game028MissileCommand::kNumCities] = {2, 5, 10, 13};
static const int kSiloX[3] = {0, 8, 15};

static inline void SetPx028(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

Game028MissileCommand::Game028MissileCommand()
    : state_(STATE_TITLE),
      score_(0),
      high_score_(0),
      wave_(1),
      ammo_(15),
      spawn_remaining_(8),
      cross_x_(7.5f),
      cross_y_(7.0f),
      fire_cooldown_(0.0f),
      spawn_timer_(0.5f),
      city_alive_{true, true, true, true},
      enemies_{},
      counters_{},
      blasts_{},
      state_timer_(0.0f),
      anim_timer_(0.0f),
      seed_(0x028C0DE1u) {
    SetupNewGame(STATE_TITLE);
}

uint32_t Game028MissileCommand::NextRand() {
    seed_ = seed_ * 1103515245u + 12345u;
    return (seed_ >> 16) & 0x7FFFu;
}

void Game028MissileCommand::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

uint8_t Game028MissileCommand::CountCities() const {
    uint8_t c = 0;
    for (int i = 0; i < kNumCities; ++i) {
        if (city_alive_[i]) c++;
    }
    return c;
}

void Game028MissileCommand::InitWave() {
    ammo_ = 16;
    spawn_remaining_ = (uint8_t)(6 + wave_ * 2);
    spawn_timer_ = 0.35f;
    for (int i = 0; i < kMaxEnemyMissiles; ++i) enemies_[i].active = false;
    for (int i = 0; i < kMaxCounterMissiles; ++i) counters_[i].active = false;
    for (int i = 0; i < kMaxBlasts; ++i) blasts_[i].active = false;
}

void Game028MissileCommand::SetupNewGame(CartridgeState new_state) {
    state_ = new_state;
    score_ = 0;
    wave_ = 1;
    cross_x_ = 7.5f;
    cross_y_ = 7.0f;
    fire_cooldown_ = 0.0f;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    seed_ = 0x028C0DE1u;
    for (int i = 0; i < kNumCities; ++i) city_alive_[i] = true;
    InitWave();
}

void Game028MissileCommand::Init() {
    Reset();
}

void Game028MissileCommand::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    SetupNewGame(STATE_TITLE);
}

void Game028MissileCommand::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        SetupNewGame(STATE_PLAYING);
    }
}

void Game028MissileCommand::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game028MissileCommand::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

void Game028MissileCommand::SpawnEnemyMissile() {
    if (spawn_remaining_ == 0) return;

    for (int i = 0; i < kMaxEnemyMissiles; ++i) {
        if (!enemies_[i].active) {
            int alive_targets[kNumCities];
            int n_alive = 0;
            for (int c = 0; c < kNumCities; ++c) {
                if (city_alive_[c]) alive_targets[n_alive++] = kCityX[c];
            }

            float sx = 1.0f + (float)(NextRand() % 14);
            float tx = (n_alive > 0)
                           ? (float)alive_targets[NextRand() % n_alive]
                           : (float)kSiloX[NextRand() % 3];

            float speed = 2.1f + (float)(wave_ - 1) * 0.45f;
            float dx = tx - sx;
            float dy = 15.0f;
            float dist = sqrtf(dx * dx + dy * dy);
            if (dist < 0.1f) dist = 0.1f;

            enemies_[i].active = true;
            enemies_[i].start_x = sx;
            enemies_[i].x = sx;
            enemies_[i].y = 0.0f;
            enemies_[i].target_x = tx;
            enemies_[i].vx = (dx / dist) * speed;
            enemies_[i].vy = (dy / dist) * speed;
            spawn_remaining_--;
            return;
        }
    }
}

bool Game028MissileCommand::FireCounterMissile() {
    if (ammo_ == 0 || fire_cooldown_ > 0.0f) return false;

    for (int i = 0; i < kMaxCounterMissiles; ++i) {
        if (!counters_[i].active) {
            int best_silo = kSiloX[1];
            float best_d = 999.0f;
            for (int s = 0; s < 3; ++s) {
                float d = fabsf(cross_x_ - (float)kSiloX[s]);
                if (d < best_d) {
                    best_d = d;
                    best_silo = kSiloX[s];
                }
            }

            float sx = (float)best_silo;
            float sy = 14.5f;
            float dx = cross_x_ - sx;
            float dy = cross_y_ - sy;
            float dist = sqrtf(dx * dx + dy * dy);
            if (dist < 0.1f) dist = 0.1f;

            const float speed = 22.0f;
            counters_[i].active = true;
            counters_[i].x = sx;
            counters_[i].y = sy;
            counters_[i].target_x = cross_x_;
            counters_[i].target_y = cross_y_;
            counters_[i].vx = (dx / dist) * speed;
            counters_[i].vy = (dy / dist) * speed;

            ammo_--;
            fire_cooldown_ = 0.12f;
            return true;
        }
    }
    return false;
}

void Game028MissileCommand::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt < 0.0f) dt = 0.0f;
    if (dt > 0.05f) dt = 0.05f;

    if (state_ == STATE_PAUSED) {
        if (keys_pressed & KEY_START) {
            state_ = STATE_PLAYING;
        }
        return;
    }

    state_timer_ += dt;
    anim_timer_ += dt;

    if (state_ == STATE_TITLE) {
        cross_x_ = 7.5f + sinf(anim_timer_ * 2.5f) * 4.0f;
        cross_y_ = 6.5f + cosf(anim_timer_ * 1.8f) * 2.5f;
        if (keys_pressed & (KEY_START | KEY_A | KEY_B | KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)) {
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

    if (state_ == STATE_PLAYING) {
        if (keys_pressed & KEY_START) {
            state_ = STATE_PAUSED;
            return;
        }

        if (fire_cooldown_ > 0.0f) fire_cooldown_ -= dt;

        // 移动瞄准准星
        const float aim_speed = 12.0f;
        if (keys_down & KEY_LEFT)  cross_x_ -= aim_speed * dt;
        if (keys_down & KEY_RIGHT) cross_x_ += aim_speed * dt;
        if (keys_down & KEY_UP)    cross_y_ -= aim_speed * dt;
        if (keys_down & KEY_DOWN)  cross_y_ += aim_speed * dt;

        if (cross_x_ < 1.0f) cross_x_ = 1.0f;
        if (cross_x_ > 14.0f) cross_x_ = 14.0f;
        if (cross_y_ < 1.0f) cross_y_ = 1.0f;
        if (cross_y_ > 13.0f) cross_y_ = 13.0f;

        if (keys_pressed & (KEY_A | KEY_B)) {
            FireCounterMissile();
        }

        // 刷出敌方弹道导弹
        if (spawn_remaining_ > 0) {
            spawn_timer_ -= dt;
            if (spawn_timer_ <= 0.0f) {
                float interval = 1.05f - (float)(wave_ - 1) * 0.15f;
                if (interval < 0.55f) interval = 0.55f;
                spawn_timer_ = interval;
                SpawnEnemyMissile();
            }
        }

        // 更新拦截弹
        for (int i = 0; i < kMaxCounterMissiles; ++i) {
            if (!counters_[i].active) continue;
            counters_[i].x += counters_[i].vx * dt;
            counters_[i].y += counters_[i].vy * dt;

            float dx = counters_[i].target_x - counters_[i].x;
            float dy = counters_[i].target_y - counters_[i].y;
            float dist = sqrtf(dx * dx + dy * dy);

            if (dist <= 0.85f || counters_[i].y <= counters_[i].target_y) {
                float bx = counters_[i].target_x;
                float by = counters_[i].target_y;
                counters_[i].active = false;

                for (int k = 0; k < kMaxBlasts; ++k) {
                    if (!blasts_[k].active) {
                        blasts_[k].active = true;
                        blasts_[k].expanding = true;
                        blasts_[k].x = bx;
                        blasts_[k].y = by;
                        blasts_[k].radius = 0.4f;
                        blasts_[k].max_radius = 2.5f;
                        break;
                    }
                }
            }
        }

        // 更新圆形冲击波 (先扩散至 ~2.5 px 再收缩消失)
        for (int k = 0; k < kMaxBlasts; ++k) {
            if (!blasts_[k].active) continue;

            if (blasts_[k].expanding) {
                blasts_[k].radius += 6.2f * dt;
                if (blasts_[k].radius >= blasts_[k].max_radius) {
                    blasts_[k].radius = blasts_[k].max_radius;
                    blasts_[k].expanding = false;
                }
            } else {
                blasts_[k].radius -= 4.2f * dt;
                if (blasts_[k].radius <= 0.0f) {
                    blasts_[k].active = false;
                    continue;
                }
            }

            for (int m = 0; m < kMaxEnemyMissiles; ++m) {
                if (!enemies_[m].active) continue;
                float dx = enemies_[m].x - blasts_[k].x;
                float dy = enemies_[m].y - blasts_[k].y;
                if (sqrtf(dx * dx + dy * dy) <= blasts_[k].radius + 0.35f) {
                    enemies_[m].active = false;
                    AddScore(100);
                }
            }
        }

        // 更新来袭导弹与城市命中判定
        for (int m = 0; m < kMaxEnemyMissiles; ++m) {
            if (!enemies_[m].active) continue;
            enemies_[m].x += enemies_[m].vx * dt;
            enemies_[m].y += enemies_[m].vy * dt;

            // 二次检测爆炸圈拦截(防止高速穿越)
            bool intercepted = false;
            for (int k = 0; k < kMaxBlasts; ++k) {
                if (!blasts_[k].active) continue;
                float dx = enemies_[m].x - blasts_[k].x;
                float dy = enemies_[m].y - blasts_[k].y;
                if (sqrtf(dx * dx + dy * dy) <= blasts_[k].radius + 0.35f) {
                    enemies_[m].active = false;
                    AddScore(100);
                    intercepted = true;
                    break;
                }
            }
            if (intercepted) continue;

            if (enemies_[m].y >= 15.0f) {
                enemies_[m].active = false;
                for (int c = 0; c < kNumCities; ++c) {
                    if (city_alive_[c] && fabsf(enemies_[m].x - (float)kCityX[c]) <= 0.95f) {
                        city_alive_[c] = false;
                        break;
                    }
                }
                if (CountCities() == 0) {
                    state_ = STATE_GAMEOVER;
                    state_timer_ = 0.0f;
                    return;
                }
            }
        }

        // 波次结算
        if (spawn_remaining_ == 0) {
            bool any_enemy = false;
            for (int m = 0; m < kMaxEnemyMissiles; ++m) {
                if (enemies_[m].active) {
                    any_enemy = true;
                    break;
                }
            }
            if (!any_enemy) {
                AddScore((uint32_t)CountCities() * 100u + (uint32_t)ammo_ * 10u);
                if (wave_ >= 3) {
                    state_ = STATE_VICTORY;
                    state_timer_ = 0.0f;
                } else {
                    wave_++;
                    InitWave();
                }
            }
        }
    }
}

void Game028MissileCommand::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    // 夜空底色
    for (int y = 0; y < 15; ++y) {
        for (int x = 0; x < 16; ++x) {
            SetPx028(fb_rgb24, x, y, 5, 8, 18);
        }
    }
    // 地面层 y=15
    for (int x = 0; x < 16; ++x) {
        SetPx028(fb_rgb24, x, 15, 140, 95, 40);
    }

    // 发射井
    for (int s = 0; s < 3; ++s) {
        int sx = kSiloX[s];
        SetPx028(fb_rgb24, sx, 15, 60, 150, 230);
        if (ammo_ > 0) {
            SetPx028(fb_rgb24, sx, 14, 210, 235, 255);
        }
    }

    // 4座城市 (y=15 穹顶亮青绿)
    for (int c = 0; c < kNumCities; ++c) {
        if (city_alive_[c]) {
            SetPx028(fb_rgb24, kCityX[c], 15, 46, 224, 150);
            SetPx028(fb_rgb24, kCityX[c], 14, 30, 170, 210);
        } else {
            SetPx028(fb_rgb24, kCityX[c], 15, 65, 45, 35);
        }
    }

    // 来袭弹道尾迹与弹头
    for (int m = 0; m < kMaxEnemyMissiles; ++m) {
        if (!enemies_[m].active) continue;
        for (int step = 1; step <= 3; ++step) {
            int tx = (int)roundf(enemies_[m].x - enemies_[m].vx * 0.12f * (float)step);
            int ty = (int)roundf(enemies_[m].y - enemies_[m].vy * 0.12f * (float)step);
            SetPx028(fb_rgb24, tx, ty, 120, 30, 30);
        }
        int mx = (int)roundf(enemies_[m].x);
        int my = (int)roundf(enemies_[m].y);
        SetPx028(fb_rgb24, mx, my, 255, 65, 55);
    }

    // 玩家拦截弹
    for (int i = 0; i < kMaxCounterMissiles; ++i) {
        if (!counters_[i].active) continue;
        int ix = (int)roundf(counters_[i].x);
        int iy = (int)roundf(counters_[i].y);
        SetPx028(fb_rgb24, ix, iy, 255, 255, 255);
    }

    // 圆形冲击波爆炸圈
    for (int k = 0; k < kMaxBlasts; ++k) {
        if (!blasts_[k].active) continue;
        int cx = (int)roundf(blasts_[k].x);
        int cy = (int)roundf(blasts_[k].y);
        float r2 = blasts_[k].radius * blasts_[k].radius;
        int ir = (int)ceilf(blasts_[k].radius);
        for (int dy = -ir; dy <= ir; ++dy) {
            for (int dx = -ir; dx <= ir; ++dx) {
                float d2 = (float)(dx * dx + dy * dy);
                if (d2 <= r2) {
                    bool core = (d2 <= r2 * 0.35f);
                    SetPx028(fb_rgb24, cx + dx, cy + dy,
                             255, core ? 245 : 175, core ? 180 : 25);
                }
            }
        }
    }

    // 瞄准十字准星
    int hx = (int)roundf(cross_x_);
    int hy = (int)roundf(cross_y_);
    SetPx028(fb_rgb24, hx - 1, hy, 46, 204, 113);
    SetPx028(fb_rgb24, hx + 1, hy, 46, 204, 113);
    SetPx028(fb_rgb24, hx, hy - 1, 46, 204, 113);
    SetPx028(fb_rgb24, hx, hy + 1, 46, 204, 113);
    SetPx028(fb_rgb24, hx, hy, 220, 255, 220);

    if (state_ == STATE_GAMEOVER) {
        for (int x = 0; x < 16; ++x) SetPx028(fb_rgb24, x, 0, 231, 76, 60);
    } else if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPx028(fb_rgb24, 6, y, 250, 250, 250);
            SetPx028(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game028MissileCommand::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = CountCities();
    st.state = (uint8_t)state_;
    st.progress = (uint8_t)((state_ == STATE_VICTORY) ? 100 : ((wave_ - 1) * 33));
    return st;
}

static_assert(sizeof(Game028MissileCommand) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
