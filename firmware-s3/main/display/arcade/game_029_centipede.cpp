// game_029_centipede.cpp —— 目标 #029 百足蜈蚣 (Centipede) 核心实现
#include "game_029_centipede.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <math.h>
#include <string.h>

namespace arcade {

static inline void SetPx029(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

Game029Centipede::Game029Centipede()
    : state_(STATE_TITLE),
      score_(0),
      high_score_(0),
      lives_(3),
      wave_(1),
      player_x_(8.0f),
      player_y_(14.0f),
      fire_cooldown_(0.0f),
      invuln_timer_(0.0f),
      step_timer_(0.0f),
      step_interval_(0.15f),
      mushrooms_{},
      segments_{},
      bullets_{},
      state_timer_(0.0f),
      anim_timer_(0.0f),
      seed_(0x029CE171u) {
    SetupNewGame(STATE_TITLE);
}

uint32_t Game029Centipede::NextRand() {
    seed_ = seed_ * 1103515245u + 12345u;
    return (seed_ >> 16) & 0x7FFFu;
}

void Game029Centipede::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

int Game029Centipede::CountActiveSegments() const {
    int c = 0;
    for (int i = 0; i < kMaxSegments; ++i) {
        if (segments_[i].active) c++;
    }
    return c;
}

void Game029Centipede::InitMushrooms() {
    memset(mushrooms_, 0, sizeof(mushrooms_));
    static const uint8_t kFixedMushrooms[10][2] = {
        {3, 3}, {11, 3}, {6, 5}, {13, 5}, {2, 7},
        {9, 7}, {5, 9}, {12, 9}, {4, 11}, {10, 11}
    };
    for (int i = 0; i < 10; ++i) {
        mushrooms_[kFixedMushrooms[i][1]][kFixedMushrooms[i][0]] = 2;
    }
    for (int i = 0; i < 3; ++i) {
        int mx = 1 + (int)(NextRand() % 14);
        int my = 3 + (int)(NextRand() % 9);
        mushrooms_[my][mx] = 2;
    }
}

void Game029Centipede::SpawnCentipedeWave() {
    for (int i = 0; i < kMaxBullets; ++i) bullets_[i].active = false;

    int seg_count = (wave_ == 1) ? 7 : 8;
    step_interval_ = 0.15f - (float)(wave_ - 1) * 0.02f;
    if (step_interval_ < 0.09f) step_interval_ = 0.09f;
    step_timer_ = 0.0f;

    for (int i = 0; i < kMaxSegments; ++i) {
        if (i < seg_count) {
            segments_[i].active = true;
            segments_[i].is_head = (i == 0);
            segments_[i].ahead = (i == 0) ? -1 : (int8_t)(i - 1);
            segments_[i].x = (int8_t)(seg_count - i);
            segments_[i].y = 1;
            segments_[i].dir_x = 1;
            segments_[i].dir_y = 1;
        } else {
            segments_[i].active = false;
            segments_[i].is_head = false;
            segments_[i].ahead = -1;
        }
    }
}

void Game029Centipede::SetupNewGame(CartridgeState new_state) {
    state_ = new_state;
    score_ = 0;
    lives_ = 3;
    wave_ = 1;
    player_x_ = 8.0f;
    player_y_ = 14.0f;
    fire_cooldown_ = 0.0f;
    invuln_timer_ = 0.0f;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    seed_ = 0x029CE171u;
    InitMushrooms();
    SpawnCentipedeWave();
}

void Game029Centipede::Init() {
    Reset();
}

void Game029Centipede::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    SetupNewGame(STATE_TITLE);
}

void Game029Centipede::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        SetupNewGame(STATE_PLAYING);
    }
}

void Game029Centipede::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game029Centipede::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

void Game029Centipede::StepCentipede() {
    int8_t old_x[kMaxSegments];
    int8_t old_y[kMaxSegments];
    int8_t old_dx[kMaxSegments];
    int8_t old_dy[kMaxSegments];

    for (int i = 0; i < kMaxSegments; ++i) {
        old_x[i] = segments_[i].x;
        old_y[i] = segments_[i].y;
        old_dx[i] = segments_[i].dir_x;
        old_dy[i] = segments_[i].dir_y;
    }

    for (int i = 0; i < kMaxSegments; ++i) {
        if (!segments_[i].active) continue;

        int leader = segments_[i].ahead;
        if (segments_[i].is_head || leader < 0 || !segments_[leader].active) {
            segments_[i].is_head = true;
            segments_[i].ahead = -1;

            int nx = (int)segments_[i].x + (int)segments_[i].dir_x;
            int cy = (int)segments_[i].y;
            bool blocked = (nx < 0 || nx > 15) || (cy >= 0 && cy < 16 && mushrooms_[cy][nx] > 0);

            if (blocked) {
                int ny = cy + (int)segments_[i].dir_y;
                if (ny > 15) {
                    segments_[i].dir_y = -1;
                    ny = 14;
                } else if (ny < 12 && segments_[i].dir_y < 0) {
                    segments_[i].dir_y = 1;
                    ny = 13;
                }
                segments_[i].y = (int8_t)ny;
                segments_[i].dir_x = (int8_t)(-segments_[i].dir_x);
            } else {
                segments_[i].x = (int8_t)nx;
            }
        } else {
            segments_[i].x = old_x[leader];
            segments_[i].y = old_y[leader];
            segments_[i].dir_x = old_dx[leader];
            segments_[i].dir_y = old_dy[leader];
        }
    }
}

void Game029Centipede::HitSegment(int idx) {
    if (idx < 0 || idx >= kMaxSegments || !segments_[idx].active) return;

    int sx = (int)segments_[idx].x;
    int sy = (int)segments_[idx].y;
    bool was_head = segments_[idx].is_head;
    segments_[idx].active = false;

    // 击中节所在格长出蘑菇
    if (sx >= 0 && sx < 16 && sy >= 0 && sy < 16) {
        mushrooms_[sy][sx] = 2;
    }

    // 后继节自动分裂为独立蜈蚣链的新头部
    for (int j = 0; j < kMaxSegments; ++j) {
        if (segments_[j].active && segments_[j].ahead == idx) {
            segments_[j].ahead = -1;
            segments_[j].is_head = true;
        }
    }

    AddScore(was_head ? 100u : 25u);

    if (CountActiveSegments() == 0) {
        AddScore(200);
        if (wave_ >= 3) {
            state_ = STATE_VICTORY;
            state_timer_ = 0.0f;
        } else {
            wave_++;
            SpawnCentipedeWave();
        }
    }
}

void Game029Centipede::FireBolt() {
    if (fire_cooldown_ > 0.0f) return;
    for (int i = 0; i < kMaxBullets; ++i) {
        if (!bullets_[i].active) {
            bullets_[i].active = true;
            bullets_[i].x = player_x_;
            bullets_[i].y = player_y_ - 0.6f;
            fire_cooldown_ = 0.14f;
            return;
        }
    }
}

void Game029Centipede::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
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
        step_timer_ += dt;
        if (step_timer_ >= 0.22f) {
            step_timer_ -= 0.22f;
            StepCentipede();
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

        if (fire_cooldown_ > 0.0f) fire_cooldown_ -= dt;
        if (invuln_timer_ > 0.0f) invuln_timer_ -= dt;

        // 底部3行移动 (y: 13..15)
        const float speed = 10.0f;
        float nx = player_x_;
        float ny = player_y_;
        if (keys_down & KEY_LEFT)  nx -= speed * dt;
        if (keys_down & KEY_RIGHT) nx += speed * dt;
        if (keys_down & KEY_UP)    ny -= speed * dt;
        if (keys_down & KEY_DOWN)  ny += speed * dt;

        if (nx < 0.0f) nx = 0.0f;
        if (nx > 15.0f) nx = 15.0f;
        if (ny < 13.0f) ny = 13.0f;
        if (ny > 15.0f) ny = 15.0f;

        int gx = (int)roundf(nx);
        int gy = (int)roundf(ny);
        if (mushrooms_[gy][gx] == 0) {
            player_x_ = nx;
            player_y_ = ny;
        }

        if ((keys_pressed & (KEY_A | KEY_B)) || (keys_down & (KEY_A | KEY_B))) {
            FireBolt();
        }

        // 更新子弹并判定碰撞
        const float bolt_speed = 24.0f;
        for (int b = 0; b < kMaxBullets; ++b) {
            if (!bullets_[b].active) continue;
            bullets_[b].y -= bolt_speed * dt;
            if (bullets_[b].y < 0.0f) {
                bullets_[b].active = false;
                continue;
            }

            // 优先检测是否击中蜈蚣节
            bool hit = false;
            for (int s = 0; s < kMaxSegments; ++s) {
                if (!segments_[s].active) continue;
                if (fabsf(bullets_[b].x - (float)segments_[s].x) <= 0.65f &&
                    fabsf(bullets_[b].y - (float)segments_[s].y) <= 0.65f) {
                    bullets_[b].active = false;
                    HitSegment(s);
                    hit = true;
                    break;
                }
            }
            if (hit || state_ != STATE_PLAYING) {
                if (state_ != STATE_PLAYING) return;
                continue;
            }

            // 检测是否击中蘑菇
            int bx = (int)roundf(bullets_[b].x);
            int by = (int)roundf(bullets_[b].y);
            if (bx >= 0 && bx < 16 && by >= 0 && by < 16 && mushrooms_[by][bx] > 0) {
                bullets_[b].active = false;
                mushrooms_[by][bx]--;
                if (mushrooms_[by][bx] == 0) {
                    AddScore(5);
                }
            }
        }

        // 推进蜈蚣网格步进
        step_timer_ += dt;
        while (step_timer_ >= step_interval_) {
            step_timer_ -= step_interval_;
            StepCentipede();
        }

        // 蜈蚣触碰玩家判定
        if (invuln_timer_ <= 0.0f) {
            for (int s = 0; s < kMaxSegments; ++s) {
                if (!segments_[s].active) continue;
                if (fabsf(player_x_ - (float)segments_[s].x) <= 0.75f &&
                    fabsf(player_y_ - (float)segments_[s].y) <= 0.75f) {
                    if (lives_ > 1) {
                        lives_--;
                        player_x_ = 8.0f;
                        player_y_ = 15.0f;
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
    }
}

void Game029Centipede::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    // 森林暗夜底色
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            SetPx029(fb_rgb24, x, y, 4, 8, 6);
        }
    }

    // 绘制蘑菇
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (mushrooms_[y][x] == 2) {
                SetPx029(fb_rgb24, x, y, 210, 60, 180);
            } else if (mushrooms_[y][x] == 1) {
                SetPx029(fb_rgb24, x, y, 120, 45, 110);
            }
        }
    }

    // 绘制蜈蚣节 (头部亮绯红橙, 身体翠绿)
    for (int s = kMaxSegments - 1; s >= 0; --s) {
        if (!segments_[s].active) continue;
        if (segments_[s].is_head) {
            SetPx029(fb_rgb24, segments_[s].x, segments_[s].y, 255, 85, 45);
        } else {
            SetPx029(fb_rgb24, segments_[s].x, segments_[s].y, 46, 215, 105);
        }
    }

    // 绘制子弹
    for (int b = 0; b < kMaxBullets; ++b) {
        if (!bullets_[b].active) continue;
        SetPx029(fb_rgb24, (int)roundf(bullets_[b].x), (int)roundf(bullets_[b].y), 255, 255, 120);
    }

    // 绘制底部射手
    bool blink_hide = (invuln_timer_ > 0.0f) && (((int)(anim_timer_ * 12.0f) & 1) == 1);
    if (!blink_hide && state_ != STATE_GAMEOVER) {
        SetPx029(fb_rgb24, (int)roundf(player_x_), (int)roundf(player_y_), 0, 240, 255);
    }

    // 顶部生命与波次 HUD (y=0)
    for (int i = 0; i < (int)lives_ && i < 3; ++i) {
        SetPx029(fb_rgb24, i * 2, 0, 0, 240, 255);
    }
    for (int w = 0; w < (int)wave_ && w < 3; ++w) {
        SetPx029(fb_rgb24, 15 - w * 2, 0, 255, 215, 0);
    }

    if (state_ == STATE_GAMEOVER) {
        for (int x = 0; x < 16; ++x) SetPx029(fb_rgb24, x, 0, 231, 76, 60);
    } else if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPx029(fb_rgb24, 6, y, 250, 250, 250);
            SetPx029(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game029Centipede::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = lives_;
    st.state = (uint8_t)state_;
    st.progress = (uint8_t)((state_ == STATE_VICTORY) ? 100 : ((wave_ - 1) * 33));
    return st;
}

static_assert(sizeof(Game029Centipede) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
