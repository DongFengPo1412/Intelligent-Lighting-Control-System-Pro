// game_027_asteroids.cpp —— 目标 #027 小行星 (Asteroids) 核心实现
#include "game_027_asteroids.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <math.h>
#include <string.h>

namespace arcade {

static const float kDirDX[8] = {
    0.0f, 0.70710678f, 1.0f, 0.70710678f,
    0.0f, -0.70710678f, -1.0f, -0.70710678f
};
static const float kDirDY[8] = {
    -1.0f, -0.70710678f, 0.0f, 0.70710678f,
    1.0f, 0.70710678f, 0.0f, -0.70710678f
};

static inline float Wrap16(float v) {
    while (v < 0.0f) v += 16.0f;
    while (v >= 16.0f) v -= 16.0f;
    return v;
}

static inline float TorusDist(float x1, float y1, float x2, float y2) {
    float dx = fabsf(x1 - x2);
    if (dx > 8.0f) dx = 16.0f - dx;
    float dy = fabsf(y1 - y2);
    if (dy > 8.0f) dy = 16.0f - dy;
    return sqrtf(dx * dx + dy * dy);
}

static inline void SetPx(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

Game027Asteroids::Game027Asteroids()
    : state_(STATE_TITLE),
      score_(0),
      high_score_(0),
      lives_(3),
      wave_(1),
      ship_x_(8.0f),
      ship_y_(8.0f),
      ship_vx_(0.0f),
      ship_vy_(0.0f),
      ship_dir_(0),
      thrusting_(false),
      rot_timer_(0.0f),
      fire_cooldown_(0.0f),
      invuln_timer_(0.0f),
      asteroids_{},
      bullets_{},
      state_timer_(0.0f),
      anim_timer_(0.0f),
      seed_(0x027A57E1u) {
    SetupNewGame(STATE_TITLE);
}

uint32_t Game027Asteroids::NextRand() {
    seed_ = seed_ * 1103515245u + 12345u;
    return (seed_ >> 16) & 0x7FFFu;
}

void Game027Asteroids::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

void Game027Asteroids::SpawnAsteroid(float x, float y, float vx, float vy, uint8_t size) {
    for (int i = 0; i < kMaxAsteroids; ++i) {
        if (!asteroids_[i].active) {
            asteroids_[i].active = true;
            asteroids_[i].size = size;
            asteroids_[i].x = Wrap16(x);
            asteroids_[i].y = Wrap16(y);
            asteroids_[i].vx = vx;
            asteroids_[i].vy = vy;
            return;
        }
    }
}

void Game027Asteroids::InitWave() {
    for (int i = 0; i < kMaxAsteroids; ++i) asteroids_[i].active = false;
    for (int i = 0; i < kMaxBullets; ++i) bullets_[i].active = false;

    ship_x_ = 8.0f;
    ship_y_ = 8.0f;
    ship_vx_ = 0.0f;
    ship_vy_ = 0.0f;
    ship_dir_ = 0;
    thrusting_ = false;
    invuln_timer_ = 1.0f;

    static const float kSpawnPos[5][2] = {
        {2.0f, 2.0f},
        {13.0f, 2.0f},
        {2.0f, 13.0f},
        {13.0f, 13.0f},
        {8.0f, 1.5f}
    };

    int count = 2 + (int)wave_;
    if (count > 5) count = 5;
    float base_speed = 1.9f + (float)(wave_ - 1) * 0.45f;

    for (int i = 0; i < count; ++i) {
        uint32_t r = NextRand();
        float ang = (float)(i * 1.35f) + (float)(r % 100) * 0.01f + 0.35f;
        SpawnAsteroid(
            kSpawnPos[i][0],
            kSpawnPos[i][1],
            cosf(ang) * base_speed,
            sinf(ang) * base_speed,
            2
        );
    }
}

void Game027Asteroids::SetupNewGame(CartridgeState new_state) {
    state_ = new_state;
    score_ = 0;
    lives_ = 3;
    wave_ = 1;
    rot_timer_ = 0.0f;
    fire_cooldown_ = 0.0f;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    seed_ = 0x027A57E1u;
    InitWave();
}

void Game027Asteroids::Init() {
    Reset();
}

void Game027Asteroids::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    SetupNewGame(STATE_TITLE);
}

void Game027Asteroids::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        SetupNewGame(STATE_PLAYING);
    }
}

void Game027Asteroids::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game027Asteroids::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

void Game027Asteroids::SplitAsteroid(int idx) {
    if (idx < 0 || idx >= kMaxAsteroids || !asteroids_[idx].active) return;

    uint8_t old_size = asteroids_[idx].size;
    float ox = asteroids_[idx].x;
    float oy = asteroids_[idx].y;
    float ovx = asteroids_[idx].vx;
    float ovy = asteroids_[idx].vy;
    asteroids_[idx].active = false;

    if (old_size >= 2) {
        AddScore(50);
        float spd = sqrtf(ovx * ovx + ovy * ovy) * 1.35f;
        if (spd < 2.6f) spd = 2.6f;
        float ang = atan2f(ovy, ovx);
        SpawnAsteroid(ox, oy, cosf(ang + 0.85f) * spd, sinf(ang + 0.85f) * spd, 1);
        SpawnAsteroid(ox, oy, cosf(ang - 0.85f) * spd, sinf(ang - 0.85f) * spd, 1);
    } else {
        AddScore(100);
    }
}

void Game027Asteroids::FireBullet() {
    for (int i = 0; i < kMaxBullets; ++i) {
        if (!bullets_[i].active) {
            float dx = kDirDX[ship_dir_];
            float dy = kDirDY[ship_dir_];
            bullets_[i].active = true;
            bullets_[i].x = Wrap16(ship_x_ + dx * 1.0f);
            bullets_[i].y = Wrap16(ship_y_ + dy * 1.0f);
            bullets_[i].vx = ship_vx_ * 0.35f + dx * 18.0f;
            bullets_[i].vy = ship_vy_ * 0.35f + dy * 18.0f;
            bullets_[i].life = 0.72f;
            fire_cooldown_ = 0.16f;
            return;
        }
    }
}

void Game027Asteroids::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
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
        for (int i = 0; i < kMaxAsteroids; ++i) {
            if (asteroids_[i].active) {
                asteroids_[i].x = Wrap16(asteroids_[i].x + asteroids_[i].vx * dt * 0.6f);
                asteroids_[i].y = Wrap16(asteroids_[i].y + asteroids_[i].vy * dt * 0.6f);
            }
        }
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

        if (rot_timer_ > 0.0f) rot_timer_ -= dt;
        if (fire_cooldown_ > 0.0f) fire_cooldown_ -= dt;
        if (invuln_timer_ > 0.0f) invuln_timer_ -= dt;

        // 8方向飞船旋转 (支持点按与长按步进)
        if (keys_pressed & KEY_LEFT) {
            ship_dir_ = (uint8_t)((ship_dir_ + 7) & 7);
            rot_timer_ = 0.14f;
        } else if (keys_pressed & KEY_RIGHT) {
            ship_dir_ = (uint8_t)((ship_dir_ + 1) & 7);
            rot_timer_ = 0.14f;
        } else if ((keys_down & KEY_LEFT) && rot_timer_ <= 0.0f) {
            ship_dir_ = (uint8_t)((ship_dir_ + 7) & 7);
            rot_timer_ = 0.14f;
        } else if ((keys_down & KEY_RIGHT) && rot_timer_ <= 0.0f) {
            ship_dir_ = (uint8_t)((ship_dir_ + 1) & 7);
            rot_timer_ = 0.14f;
        }

        // 牛顿惯性推进: KEY_A 或 KEY_UP
        thrusting_ = (keys_down & (KEY_A | KEY_UP)) != 0;
        if (thrusting_) {
            const float accel = 14.0f;
            ship_vx_ += kDirDX[ship_dir_] * accel * dt;
            ship_vy_ += kDirDY[ship_dir_] * accel * dt;
            float spd = sqrtf(ship_vx_ * ship_vx_ + ship_vy_ * ship_vy_);
            if (spd > 9.0f) {
                ship_vx_ = (ship_vx_ / spd) * 9.0f;
                ship_vy_ = (ship_vy_ / spd) * 9.0f;
            }
        }

        // 微弱太空阻尼维持长惯性滑行
        ship_vx_ *= (1.0f - 0.35f * dt);
        ship_vy_ *= (1.0f - 0.35f * dt);

        ship_x_ = Wrap16(ship_x_ + ship_vx_ * dt);
        ship_y_ = Wrap16(ship_y_ + ship_vy_ * dt);

        // 射击: KEY_B 主射击 (若用 KEY_UP 推进也兼容 KEY_A 射击)
        bool want_shoot = (keys_pressed & KEY_B) != 0 ||
                          ((keys_down & KEY_B) != 0 && fire_cooldown_ <= 0.0f) ||
                          ((keys_down & KEY_UP) != 0 && (keys_pressed & KEY_A) != 0);
        if (want_shoot && fire_cooldown_ <= 0.0f) {
            FireBullet();
        }

        // 更新子弹
        for (int i = 0; i < kMaxBullets; ++i) {
            if (!bullets_[i].active) continue;
            bullets_[i].life -= dt;
            if (bullets_[i].life <= 0.0f) {
                bullets_[i].active = false;
                continue;
            }
            bullets_[i].x = Wrap16(bullets_[i].x + bullets_[i].vx * dt);
            bullets_[i].y = Wrap16(bullets_[i].y + bullets_[i].vy * dt);
        }

        // 更新陨石
        for (int i = 0; i < kMaxAsteroids; ++i) {
            if (!asteroids_[i].active) continue;
            asteroids_[i].x = Wrap16(asteroids_[i].x + asteroids_[i].vx * dt);
            asteroids_[i].y = Wrap16(asteroids_[i].y + asteroids_[i].vy * dt);
        }

        // 子弹击中陨石
        for (int b = 0; b < kMaxBullets; ++b) {
            if (!bullets_[b].active) continue;
            for (int a = 0; a < kMaxAsteroids; ++a) {
                if (!asteroids_[a].active) continue;
                float hit_r = (asteroids_[a].size >= 2) ? 1.35f : 0.85f;
                float cx = (asteroids_[a].size >= 2) ? Wrap16(asteroids_[a].x + 0.5f) : asteroids_[a].x;
                float cy = (asteroids_[a].size >= 2) ? Wrap16(asteroids_[a].y + 0.5f) : asteroids_[a].y;
                if (TorusDist(bullets_[b].x, bullets_[b].y, cx, cy) <= hit_r) {
                    bullets_[b].active = false;
                    SplitAsteroid(a);
                    break;
                }
            }
        }

        // 飞船碰撞陨石
        if (invuln_timer_ <= 0.0f) {
            for (int a = 0; a < kMaxAsteroids; ++a) {
                if (!asteroids_[a].active) continue;
                float hit_r = (asteroids_[a].size >= 2) ? 1.25f : 0.75f;
                float cx = (asteroids_[a].size >= 2) ? Wrap16(asteroids_[a].x + 0.5f) : asteroids_[a].x;
                float cy = (asteroids_[a].size >= 2) ? Wrap16(asteroids_[a].y + 0.5f) : asteroids_[a].y;
                if (TorusDist(ship_x_, ship_y_, cx, cy) <= hit_r) {
                    SplitAsteroid(a);
                    if (lives_ > 1) {
                        lives_--;
                        ship_x_ = 8.0f;
                        ship_y_ = 8.0f;
                        ship_vx_ = 0.0f;
                        ship_vy_ = 0.0f;
                        invuln_timer_ = 1.5f;
                    } else {
                        lives_ = 0;
                        state_ = STATE_GAMEOVER;
                        state_timer_ = 0.0f;
                        return;
                    }
                    break;
                }
            }
        }

        // 检查波次清空
        bool any_left = false;
        for (int a = 0; a < kMaxAsteroids; ++a) {
            if (asteroids_[a].active) {
                any_left = true;
                break;
            }
        }
        if (!any_left) {
            AddScore(200);
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

void Game027Asteroids::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    // 深邃星空背景
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            SetPx(fb_rgb24, x, y, 4, 6, 14);
        }
    }
    SetPx(fb_rgb24, 3, 5, 25, 30, 55);
    SetPx(fb_rgb24, 12, 3, 30, 35, 60);
    SetPx(fb_rgb24, 5, 12, 25, 30, 55);
    SetPx(fb_rgb24, 11, 10, 30, 35, 60);

    // 绘制陨石
    for (int a = 0; a < kMaxAsteroids; ++a) {
        if (!asteroids_[a].active) continue;
        if (asteroids_[a].size >= 2) {
            int ax = ((int)floorf(asteroids_[a].x)) & 15;
            int ay = ((int)floorf(asteroids_[a].y)) & 15;
            SetPx(fb_rgb24, ax, ay, 185, 175, 160);
            SetPx(fb_rgb24, (ax + 1) & 15, ay, 145, 135, 125);
            SetPx(fb_rgb24, ax, (ay + 1) & 15, 130, 120, 110);
            SetPx(fb_rgb24, (ax + 1) & 15, (ay + 1) & 15, 165, 155, 140);
        } else {
            int ax = ((int)roundf(asteroids_[a].x)) & 15;
            int ay = ((int)roundf(asteroids_[a].y)) & 15;
            SetPx(fb_rgb24, ax, ay, 225, 210, 180);
        }
    }

    // 绘制子弹
    for (int b = 0; b < kMaxBullets; ++b) {
        if (!bullets_[b].active) continue;
        int bx = ((int)roundf(bullets_[b].x)) & 15;
        int by = ((int)roundf(bullets_[b].y)) & 15;
        SetPx(fb_rgb24, bx, by, 255, 240, 80);
    }

    // 绘制飞船 (船体 + 8向机头指示 + 尾焰)
    bool blink_hide = (invuln_timer_ > 0.0f) && (((int)(anim_timer_ * 12.0f) & 1) == 1);
    if (!blink_hide && state_ != STATE_GAMEOVER) {
        int sx = ((int)roundf(ship_x_)) & 15;
        int sy = ((int)roundf(ship_y_)) & 15;
        int nx = ((int)roundf(ship_x_ + kDirDX[ship_dir_])) & 15;
        int ny = ((int)roundf(ship_y_ + kDirDY[ship_dir_])) & 15;

        if (thrusting_) {
            int tx = ((int)roundf(ship_x_ - kDirDX[ship_dir_])) & 15;
            int ty = ((int)roundf(ship_y_ - kDirDY[ship_dir_])) & 15;
            SetPx(fb_rgb24, tx, ty, 255, 120, 20);
        }
        SetPx(fb_rgb24, sx, sy, 52, 172, 255);
        SetPx(fb_rgb24, nx, ny, 255, 255, 255);
    }

    // 顶部生命与波次 HUD
    for (int i = 0; i < (int)lives_ && i < 3; ++i) {
        SetPx(fb_rgb24, i * 2, 0, 0, 230, 255);
    }
    for (int w = 0; w < (int)wave_ && w < 3; ++w) {
        SetPx(fb_rgb24, 15 - w * 2, 0, 255, 215, 0);
    }

    if (state_ == STATE_GAMEOVER) {
        for (int x = 0; x < 16; ++x) SetPx(fb_rgb24, x, 0, 231, 76, 60);
    } else if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPx(fb_rgb24, 6, y, 250, 250, 250);
            SetPx(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game027Asteroids::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = lives_;
    st.state = (uint8_t)state_;
    st.progress = (uint8_t)((state_ == STATE_VICTORY) ? 100 : ((wave_ - 1) * 33));
    return st;
}

static_assert(sizeof(Game027Asteroids) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
