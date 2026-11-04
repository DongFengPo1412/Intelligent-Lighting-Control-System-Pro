// game_031_robotron.cpp —— 目标 #031 双向射击 (Robotron 2084) 核心实现
#include "game_031_robotron.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <math.h>
#include <string.h>

namespace arcade {

static const float kAimDX031[8] = {
    0.0f, 0.70710678f, 1.0f, 0.70710678f,
    0.0f, -0.70710678f, -1.0f, -0.70710678f
};
static const float kAimDY031[8] = {
    -1.0f, -0.70710678f, 0.0f, 0.70710678f,
    1.0f, 0.70710678f, 0.0f, -0.70710678f
};

static inline void SetPx031(uint8_t* fb, int x, int y, uint8_t r, uint8_t g, uint8_t b) {
    if (x >= 0 && x < 16 && y >= 0 && y < 16) {
        int idx = (y * 16 + x) * 3;
        fb[idx + 0] = r;
        fb[idx + 1] = g;
        fb[idx + 2] = b;
    }
}

static uint8_t VecToDir8(int ix, int iy) {
    if (ix == 0 && iy < 0) return 0;
    if (ix > 0 && iy < 0)  return 1;
    if (ix > 0 && iy == 0) return 2;
    if (ix > 0 && iy > 0)  return 3;
    if (ix == 0 && iy > 0) return 4;
    if (ix < 0 && iy > 0)  return 5;
    if (ix < 0 && iy == 0) return 6;
    if (ix < 0 && iy < 0)  return 7;
    return 0;
}

Game031Robotron::Game031Robotron()
    : state_(STATE_TITLE),
      score_(0),
      high_score_(0),
      lives_(3),
      wave_(1),
      px_(7.5f),
      py_(7.5f),
      aim_dir_(2),
      aim_locked_(false),
      fire_cooldown_(0.0f),
      invuln_timer_(0.0f),
      robots_{},
      humans_{},
      lasers_{},
      state_timer_(0.0f),
      anim_timer_(0.0f),
      seed_(0x0312084Au) {
    SetupNewGame(STATE_TITLE);
}

uint32_t Game031Robotron::NextRand() {
    seed_ = seed_ * 1103515245u + 12345u;
    return (seed_ >> 16) & 0x7FFFu;
}

void Game031Robotron::AddScore(uint32_t pts) {
    score_ += pts;
    if (score_ > high_score_) {
        high_score_ = score_;
        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
    }
}

int Game031Robotron::CountActiveRobots() const {
    int c = 0;
    for (int i = 0; i < kMaxRobots; ++i) {
        if (robots_[i].active) c++;
    }
    return c;
}

void Game031Robotron::InitWave() {
    px_ = 7.5f;
    py_ = 7.5f;
    invuln_timer_ = 1.0f;
    for (int i = 0; i < kMaxLasers; ++i) lasers_[i].active = false;

    static const float kHumanInit[kMaxHumans][4] = {
        {3.5f, 4.0f, 1.1f, 0.8f},
        {11.5f, 4.0f, -1.0f, 0.9f},
        {7.5f, 12.0f, 0.9f, -1.0f}
    };
    for (int h = 0; h < kMaxHumans; ++h) {
        humans_[h].active = true;
        humans_[h].x = kHumanInit[h][0];
        humans_[h].y = kHumanInit[h][1];
        humans_[h].vx = kHumanInit[h][2];
        humans_[h].vy = kHumanInit[h][3];
    }

    int count = 6 + (int)wave_ * 2;
    if (count > kMaxRobots) count = kMaxRobots;
    float base_spd = 1.85f + (float)(wave_ - 1) * 0.35f;

    static const float kPerim[12][2] = {
        {1.2f, 1.2f}, {13.8f, 1.2f}, {1.2f, 13.8f}, {13.8f, 13.8f},
        {7.5f, 1.2f}, {7.5f, 13.8f}, {1.2f, 7.5f}, {13.8f, 7.5f},
        {4.0f, 1.2f}, {11.0f, 1.2f}, {4.0f, 13.8f}, {11.0f, 13.8f}
    };
    for (int i = 0; i < kMaxRobots; ++i) {
        if (i < count) {
            uint32_t r = NextRand();
            robots_[i].active = true;
            robots_[i].x = kPerim[i][0];
            robots_[i].y = kPerim[i][1];
            robots_[i].speed = base_spd + (float)(r % 4) * 0.1f;
        } else {
            robots_[i].active = false;
        }
    }
}

void Game031Robotron::SetupNewGame(CartridgeState new_state) {
    state_ = new_state;
    score_ = 0;
    lives_ = 3;
    wave_ = 1;
    aim_dir_ = 2;
    aim_locked_ = false;
    fire_cooldown_ = 0.0f;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;
    seed_ = 0x0312084Au;
    InitWave();
}

void Game031Robotron::Init() {
    Reset();
}

void Game031Robotron::Reset() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    SetupNewGame(STATE_TITLE);
}

void Game031Robotron::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) {
        SetupNewGame(STATE_PLAYING);
    }
}

void Game031Robotron::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game031Robotron::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

void Game031Robotron::FireLaser() {
    if (fire_cooldown_ > 0.0f) return;
    for (int i = 0; i < kMaxLasers; ++i) {
        if (!lasers_[i].active) {
            float dx = kAimDX031[aim_dir_];
            float dy = kAimDY031[aim_dir_];
            lasers_[i].active = true;
            lasers_[i].x = px_ + dx * 0.6f;
            lasers_[i].y = py_ + dy * 0.6f;
            lasers_[i].vx = dx * 18.0f;
            lasers_[i].vy = dy * 18.0f;
            lasers_[i].life = 0.85f;
            fire_cooldown_ = 0.14f;
            return;
        }
    }
}

void Game031Robotron::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
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
        aim_dir_ = (uint8_t)(((int)(anim_timer_ * 4.0f)) & 7);
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

        // KEY_B: 首次按下锁定当前瞄准向, 再次按下顺时针循环切换8向瞄准; KEY_SELECT 解锁跟随移动
        if (keys_pressed & KEY_B) {
            if (!aim_locked_) {
                aim_locked_ = true;
            } else {
                aim_dir_ = (uint8_t)((aim_dir_ + 1) & 7);
            }
        }
        if (keys_pressed & KEY_SELECT) {
            aim_locked_ = false;
        }

        // 8向自由走位
        int move_ix = 0;
        int move_iy = 0;
        if (keys_down & KEY_LEFT)  move_ix -= 1;
        if (keys_down & KEY_RIGHT) move_ix += 1;
        if (keys_down & KEY_UP)    move_iy -= 1;
        if (keys_down & KEY_DOWN)  move_iy += 1;

        if (move_ix != 0 || move_iy != 0) {
            if (!aim_locked_) {
                aim_dir_ = VecToDir8(move_ix, move_iy);
            }
            float len = sqrtf((float)(move_ix * move_ix + move_iy * move_iy));
            const float move_speed = 6.2f;
            px_ += ((float)move_ix / len) * move_speed * dt;
            py_ += ((float)move_iy / len) * move_speed * dt;
            if (px_ < 1.0f) px_ = 1.0f;
            if (px_ > 14.0f) px_ = 14.0f;
            if (py_ < 1.0f) py_ = 1.0f;
            if (py_ > 14.0f) py_ = 14.0f;
        }

        if ((keys_pressed & KEY_A) || (keys_down & KEY_A)) {
            FireLaser();
        }

        // 幸存者漫步与营救 (+100)
        for (int h = 0; h < kMaxHumans; ++h) {
            if (!humans_[h].active) continue;
            humans_[h].x += humans_[h].vx * dt;
            humans_[h].y += humans_[h].vy * dt;
            if (humans_[h].x <= 1.2f || humans_[h].x >= 13.8f) humans_[h].vx = -humans_[h].vx;
            if (humans_[h].y <= 1.2f || humans_[h].y >= 13.8f) humans_[h].vy = -humans_[h].vy;

            float dx = humans_[h].x - px_;
            float dy = humans_[h].y - py_;
            if (sqrtf(dx * dx + dy * dy) <= 0.95f) {
                humans_[h].active = false;
                AddScore(100);
            }
        }

        // 激光更新与击毁机器人
        for (int l = 0; l < kMaxLasers; ++l) {
            if (!lasers_[l].active) continue;
            lasers_[l].x += lasers_[l].vx * dt;
            lasers_[l].y += lasers_[l].vy * dt;
            lasers_[l].life -= dt;

            if (lasers_[l].life <= 0.0f ||
                lasers_[l].x < 0.5f || lasers_[l].x > 14.5f ||
                lasers_[l].y < 0.5f || lasers_[l].y > 14.5f) {
                lasers_[l].active = false;
                continue;
            }

            for (int r = 0; r < kMaxRobots; ++r) {
                if (!robots_[r].active) continue;
                float dx = robots_[r].x - lasers_[l].x;
                float dy = robots_[r].y - lasers_[l].y;
                if (sqrtf(dx * dx + dy * dy) <= 0.85f) {
                    robots_[r].active = false;
                    lasers_[l].active = false;
                    AddScore(50);
                    break;
                }
            }
        }

        // 机器人追击与玩家触碰判定
        for (int r = 0; r < kMaxRobots; ++r) {
            if (!robots_[r].active) continue;
            float dx = px_ - robots_[r].x;
            float dy = py_ - robots_[r].y;
            float dist = sqrtf(dx * dx + dy * dy);
            if (dist > 0.05f) {
                robots_[r].x += (dx / dist) * robots_[r].speed * dt;
                robots_[r].y += (dy / dist) * robots_[r].speed * dt;
            }

            if (invuln_timer_ <= 0.0f && dist <= 0.72f) {
                if (lives_ > 1) {
                    lives_--;
                    px_ = 7.5f;
                    py_ = 7.5f;
                    invuln_timer_ = 1.4f;
                    // 击退近身机器人防止重生秒杀
                    for (int k = 0; k < kMaxRobots; ++k) {
                        if (!robots_[k].active) continue;
                        float kdx = robots_[k].x - 7.5f;
                        float kdy = robots_[k].y - 7.5f;
                        float kd = sqrtf(kdx * kdx + kdy * kdy);
                        if (kd < 4.0f) {
                            if (kd < 0.1f) { kdx = 1.0f; kdy = 0.0f; kd = 1.0f; }
                            robots_[k].x = 7.5f + (kdx / kd) * 5.0f;
                            robots_[k].y = 7.5f + (kdy / kd) * 5.0f;
                            if (robots_[k].x < 1.2f) robots_[k].x = 1.2f;
                            if (robots_[k].x > 13.8f) robots_[k].x = 13.8f;
                            if (robots_[k].y < 1.2f) robots_[k].y = 1.2f;
                            if (robots_[k].y > 13.8f) robots_[k].y = 13.8f;
                        }
                    }
                } else {
                    lives_ = 0;
                    state_ = STATE_GAMEOVER;
                    state_timer_ = 0.0f;
                    return;
                }
                break;
            }
        }

        // 全灭清波晋级
        if (CountActiveRobots() == 0) {
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

void Game031Robotron::Render(uint8_t* fb_rgb24) {
    if ((state_ == STATE_GAMEOVER || state_ == STATE_VICTORY) && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, state_ == STATE_VICTORY, score_, high_score_, anim_timer_);
        return;
    }

    // 赛博黑底 + 霓虹边界墙
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            if (x == 0 || x == 15 || y == 0 || y == 15) {
                SetPx031(fb_rgb24, x, y, 90, 20, 175);
            } else {
                SetPx031(fb_rgb24, x, y, 5, 5, 12);
            }
        }
    }

    // 幸存人类 (亮青绿)
    for (int h = 0; h < kMaxHumans; ++h) {
        if (humans_[h].active) {
            SetPx031(fb_rgb24, (int)roundf(humans_[h].x), (int)roundf(humans_[h].y), 46, 235, 150);
        }
    }

    // 敌方机器人群 (猩红闪烁)
    for (int r = 0; r < kMaxRobots; ++r) {
        if (robots_[r].active) {
            SetPx031(fb_rgb24, (int)roundf(robots_[r].x), (int)roundf(robots_[r].y), 245, 50, 45);
        }
    }

    // 激光束
    for (int l = 0; l < kMaxLasers; ++l) {
        if (lasers_[l].active) {
            SetPx031(fb_rgb24, (int)roundf(lasers_[l].x), (int)roundf(lasers_[l].y), 255, 245, 80);
        }
    }

    // 玩家与瞄准星指示
    bool blink_hide = (invuln_timer_ > 0.0f) && (((int)(anim_timer_ * 12.0f) & 1) == 1);
    if (!blink_hide && state_ != STATE_GAMEOVER) {
        int ix = (int)roundf(px_);
        int iy = (int)roundf(py_);
        int ax = (int)roundf(px_ + kAimDX031[aim_dir_]);
        int ay = (int)roundf(py_ + kAimDY031[aim_dir_]);
        if (aim_locked_) {
            SetPx031(fb_rgb24, ax, ay, 255, 165, 0);  // 锁定态橙金准星
        } else {
            SetPx031(fb_rgb24, ax, ay, 0, 200, 255);  // 自由态亮青准星
        }
        SetPx031(fb_rgb24, ix, iy, 255, 255, 255);
    }

    // 顶部边框嵌合 HUD: 生命与波次
    for (int i = 0; i < (int)lives_ && i < 3; ++i) {
        SetPx031(fb_rgb24, 1 + i * 2, 0, 0, 240, 255);
    }
    for (int w = 0; w < (int)wave_ && w < 3; ++w) {
        SetPx031(fb_rgb24, 14 - w * 2, 0, 255, 215, 0);
    }

    if (state_ == STATE_GAMEOVER) {
        for (int x = 0; x < 16; ++x) SetPx031(fb_rgb24, x, 0, 231, 76, 60);
    } else if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            SetPx031(fb_rgb24, 6, y, 250, 250, 250);
            SetPx031(fb_rgb24, 9, y, 250, 250, 250);
        }
    }
}

CartridgeStatus Game031Robotron::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = lives_;
    st.state = (uint8_t)state_;
    st.progress = (uint8_t)((state_ == STATE_VICTORY) ? 100 : ((wave_ - 1) * 33));
    return st;
}

static_assert(sizeof(Game031Robotron) <= 8192, "Cartridge must fit in arena");

} // namespace arcade
