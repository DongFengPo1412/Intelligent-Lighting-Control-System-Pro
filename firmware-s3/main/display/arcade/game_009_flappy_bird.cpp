// game_009_flappy_bird.cpp —— 目标 #009 飞翔小鸟 16 核心实现
#include "game_009_flappy_bird.h"
#include "arcade_result_screen.h"
#include "arcade_score_store.h"
#include <string.h>
#include <math.h>

namespace arcade {

static inline uint32_t RandSeed(uint32_t& seed) {
    seed = seed * 1103515245u + 12345u;
    return (seed >> 16) & 0x7FFF;
}

static uint32_t g_flappy_seed = 0x87654321;

Game009FlappyBird::Game009FlappyBird()
    : state_(STATE_TITLE),
      bird_x_(3.0f),
      bird_y_(7.0f),
      bird_vy_(0.0f),
      flap_anim_(false),
      flap_timer_(0.0f),
      score_(0),
      high_score_(0),
      ground_scroll_(0.0f),
      state_timer_(0.0f),
      anim_timer_(0.0f) {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
}

void Game009FlappyBird::SpawnPipe(PipeObstacle& pipe, float start_x) {
    uint32_t r = RandSeed(g_flappy_seed);
    pipe.x = start_x;
    pipe.gap_height = (score_ > 10) ? 4 : 5;
    int max_top = 13 - pipe.gap_height;
    pipe.gap_y = 2 + (r % (max_top - 2 + 1));
    pipe.scored = false;
}

void Game009FlappyBird::Init() {
    high_score_ = ArcadeScoreStore::LoadHighScore(GetId());
    Reset();
}

void Game009FlappyBird::Reset() {
    state_ = STATE_TITLE;
    bird_x_ = 3.0f;
    bird_y_ = 6.0f;
    bird_vy_ = 0.0f;
    flap_anim_ = false;
    flap_timer_ = 0.0f;
    score_ = 0;
    ground_scroll_ = 0.0f;
    state_timer_ = 0.0f;
    anim_timer_ = 0.0f;

    SpawnPipe(pipes_[0], 16.0f);
    SpawnPipe(pipes_[1], 26.0f);
}

void Game009FlappyBird::Start() {
    if (state_ == STATE_TITLE || state_ == STATE_GAMEOVER) {
        state_ = STATE_PLAYING;
        bird_x_ = 3.0f;
        bird_y_ = 6.0f;
        bird_vy_ = 0.0f;
        score_ = 0;
        state_timer_ = 0.0f;
        anim_timer_ = 0.0f;
        SpawnPipe(pipes_[0], 16.0f);
        SpawnPipe(pipes_[1], 26.0f);
    }
}

void Game009FlappyBird::Pause() {
    if (state_ == STATE_PLAYING) {
        state_ = STATE_PAUSED;
    }
}

void Game009FlappyBird::Resume() {
    if (state_ == STATE_PAUSED) {
        state_ = STATE_PLAYING;
    }
}

void Game009FlappyBird::Update(float dt, uint16_t keys_down, uint16_t keys_pressed) {
    if (dt > 0.05f) dt = 0.05f;
    state_timer_ += dt;
    anim_timer_ += dt;

    if (state_ == STATE_TITLE) {
        bird_y_ = 6.5f + sinf(state_timer_ * 4.0f) * 1.5f;
        ground_scroll_ += 4.0f * dt;
        if (ground_scroll_ >= 16.0f) ground_scroll_ -= 16.0f;

        if (keys_pressed & (KEY_START | KEY_A | KEY_UP | KEY_DOWN | KEY_B)) {
            Start();
        }
        return;
    }

    if (state_ == STATE_GAMEOVER) {
        if (bird_y_ < 13.0f) {
            bird_vy_ += 35.0f * dt;
            bird_y_ += bird_vy_ * dt;
            if (bird_y_ > 13.0f) bird_y_ = 13.0f;
        }
        if (state_timer_ > 0.5f && (keys_pressed & (KEY_START | KEY_A | KEY_UP | KEY_B))) {
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

        const uint16_t tap_mask = KEY_A | KEY_UP | KEY_B | KEY_SELECT | KEY_LEFT | KEY_RIGHT;
        if (keys_pressed & tap_mask) {
            bird_vy_ = -11.0f;
            flap_anim_ = true;
            flap_timer_ = 0.15f;
        }

        if (flap_timer_ > 0.0f) {
            flap_timer_ -= dt;
            if (flap_timer_ <= 0.0f) flap_anim_ = false;
        }

        const float gravity = 32.0f;
        bird_vy_ += gravity * dt;
        if (bird_vy_ > 14.0f) bird_vy_ = 14.0f;

        bird_y_ += bird_vy_ * dt;

        const float pipe_speed = 5.0f;
        ground_scroll_ += pipe_speed * dt;
        if (ground_scroll_ >= 16.0f) ground_scroll_ -= 16.0f;

        for (int i = 0; i < kMaxPipes; ++i) {
            pipes_[i].x -= pipe_speed * dt;

            if (!pipes_[i].scored && pipes_[i].x + 2.0f < bird_x_) {
                pipes_[i].scored = true;
                score_++;
                if (score_ > high_score_) {
                    high_score_ = score_;
                    ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
                }
            }

            if (pipes_[i].x < -3.0f) {
                int other = (i == 0) ? 1 : 0;
                float new_x = pipes_[other].x + 10.5f;
                if (new_x < 16.0f) new_x = 16.0f;
                SpawnPipe(pipes_[i], new_x);
            }
        }

        float bx1 = bird_x_;
        float bx2 = bird_x_ + 1.8f;
        float by1 = bird_y_;
        float by2 = bird_y_ + 1.8f;

        if (by1 < 0.0f || by2 >= 13.5f) {
            state_ = STATE_GAMEOVER;
            state_timer_ = 0.0f;
            if (score_ > high_score_) {
                high_score_ = score_;
                ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
            }
            return;
        }

        for (int i = 0; i < kMaxPipes; ++i) {
            float px1 = pipes_[i].x;
            float px2 = pipes_[i].x + 2.0f;

            if (bx2 >= px1 && bx1 <= px2) {
                float gap_top = (float)pipes_[i].gap_y;
                float gap_bottom = gap_top + (float)pipes_[i].gap_height;

                if (by1 < gap_top || by2 > gap_bottom) {
                    state_ = STATE_GAMEOVER;
                    state_timer_ = 0.0f;
                    if (score_ > high_score_) {
                        high_score_ = score_;
                        ArcadeScoreStore::SaveHighScore(GetId(), high_score_);
                    }
                    return;
                }
            }
        }
    }
}

void Game009FlappyBird::DrawBird(uint8_t* fb, int bx, int by, bool flap_up) {
    for (int dy = 0; dy < 2; ++dy) {
        for (int dx = 0; dx < 2; ++dx) {
            int x = bx + dx;
            int y = by + dy;
            if (x >= 0 && x < 16 && y >= 0 && y < 16) {
                int idx = (y * 16 + x) * 3;
                if (dy == 0) {
                    if (dx == 0) {
                        fb[idx + 0] = 241; fb[idx + 1] = 196; fb[idx + 2] = 15;
                    } else {
                        fb[idx + 0] = 255; fb[idx + 1] = 255; fb[idx + 2] = 255;
                    }
                } else {
                    if (dx == 0) {
                        if (flap_up) {
                            fb[idx + 0] = 243; fb[idx + 1] = 156; fb[idx + 2] = 18;
                        } else {
                            fb[idx + 0] = 230; fb[idx + 1] = 126; fb[idx + 2] = 34;
                        }
                    } else {
                        fb[idx + 0] = 231; fb[idx + 1] = 76; fb[idx + 2] = 60;
                    }
                }
            }
        }
    }
}

void Game009FlappyBird::Render(uint8_t* fb_rgb24) {
    if (state_ == STATE_GAMEOVER && state_timer_ > 0.8f) {
        ArcadeResultScreen::RenderResult(fb_rgb24, false, score_, high_score_, anim_timer_);
        return;
    }

    for (int y = 0; y < 14; ++y) {
        for (int x = 0; x < 16; ++x) {
            int idx = (y * 16 + x) * 3;
            fb_rgb24[idx + 0] = 52;
            fb_rgb24[idx + 1] = 152 + (y * 3);
            fb_rgb24[idx + 2] = 219;
        }
    }

    for (int x = 0; x < 16; ++x) {
        int idx14 = (14 * 16 + x) * 3;
        int idx15 = (15 * 16 + x) * 3;
        fb_rgb24[idx14 + 0] = 46; fb_rgb24[idx14 + 1] = 204; fb_rgb24[idx14 + 2] = 113;
        fb_rgb24[idx15 + 0] = 211; fb_rgb24[idx15 + 1] = 84; fb_rgb24[idx15 + 2] = 0;
    }

    for (int i = 0; i < kMaxPipes; ++i) {
        int px = (int)roundf(pipes_[i].x);
        int gap_y = pipes_[i].gap_y;
        int gap_h = pipes_[i].gap_height;

        for (int dx = 0; dx < 2; ++dx) {
            int x = px + dx;
            if (x >= 0 && x < 16) {
                for (int y = 0; y < gap_y; ++y) {
                    int idx = (y * 16 + x) * 3;
                    if (y == gap_y - 1) {
                        fb_rgb24[idx + 0] = 39; fb_rgb24[idx + 1] = 174; fb_rgb24[idx + 2] = 96;
                    } else {
                        if (dx == 0) {
                            fb_rgb24[idx + 0] = 46; fb_rgb24[idx + 1] = 204; fb_rgb24[idx + 2] = 113;
                        } else {
                            fb_rgb24[idx + 0] = 34; fb_rgb24[idx + 1] = 153; fb_rgb24[idx + 2] = 84;
                        }
                    }
                }

                for (int y = gap_y + gap_h; y < 14; ++y) {
                    int idx = (y * 16 + x) * 3;
                    if (y == gap_y + gap_h) {
                        fb_rgb24[idx + 0] = 39; fb_rgb24[idx + 1] = 174; fb_rgb24[idx + 2] = 96;
                    } else {
                        if (dx == 0) {
                            fb_rgb24[idx + 0] = 46; fb_rgb24[idx + 1] = 204; fb_rgb24[idx + 2] = 113;
                        } else {
                            fb_rgb24[idx + 0] = 34; fb_rgb24[idx + 1] = 153; fb_rgb24[idx + 2] = 84;
                        }
                    }
                }
            }
        }
    }

    int bx = (int)roundf(bird_x_);
    int by = (int)roundf(bird_y_);
    DrawBird(fb_rgb24, bx, by, flap_anim_);

    if (state_ == STATE_GAMEOVER) {
        for (int x = 0; x < 16; ++x) {
            int idx = (0 * 16 + x) * 3;
            fb_rgb24[idx + 0] = 231; fb_rgb24[idx + 1] = 76; fb_rgb24[idx + 2] = 60;
        }
    } else if (state_ == STATE_PAUSED) {
        for (int y = 5; y <= 8; ++y) {
            int idx1 = (y * 16 + 6) * 3;
            int idx2 = (y * 16 + 9) * 3;
            fb_rgb24[idx1 + 0] = fb_rgb24[idx1 + 1] = fb_rgb24[idx1 + 2] = 250;
            fb_rgb24[idx2 + 0] = fb_rgb24[idx2 + 1] = fb_rgb24[idx2 + 2] = 250;
        }
    }
}

CartridgeStatus Game009FlappyBird::GetStatus() const {
    CartridgeStatus st;
    st.score = score_;
    st.high_score = high_score_;
    st.lives = (state_ == STATE_GAMEOVER) ? 0 : 1;
    st.state = (uint8_t)state_;
    st.progress = (uint8_t)(score_ > 255 ? 255 : score_);
    return st;
}

} // namespace arcade
