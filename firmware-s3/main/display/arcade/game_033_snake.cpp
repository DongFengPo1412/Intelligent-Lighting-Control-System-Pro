// game_033_snake.cpp —— 经典贪吃蛇 (Classic Snake)
#include "game_033_snake.h"
#include <string.h>
#include <stdlib.h>

namespace arcade {

Game033Snake::Game033Snake()
{
    Init();
}

void Game033Snake::Init()
{
    Reset();
}

void Game033Snake::PlaceFood()
{
    int free_count = 0;
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            bool occ = false;
            for (int i = 0; i < snake_len_; ++i) {
                if (snake_x_[i] == x && snake_y_[i] == y) {
                    occ = true;
                    break;
                }
            }
            if (!occ) free_count++;
        }
    }

    if (free_count == 0) return;

    int choice = rand() % free_count;
    for (int y = 0; y < 16; ++y) {
        for (int x = 0; x < 16; ++x) {
            bool occ = false;
            for (int i = 0; i < snake_len_; ++i) {
                if (snake_x_[i] == x && snake_y_[i] == y) {
                    occ = true;
                    break;
                }
            }
            if (!occ) {
                if (choice == 0) {
                    food_x_ = x;
                    food_y_ = y;
                    return;
                }
                choice--;
            }
        }
    }
}

void Game033Snake::Reset()
{
    memset(snake_x_, 0, sizeof(snake_x_));
    memset(snake_y_, 0, sizeof(snake_y_));

    snake_len_ = 3;
    snake_x_[0] = 5; snake_y_[0] = 7;
    snake_x_[1] = 4; snake_y_[1] = 7;
    snake_x_[2] = 3; snake_y_[2] = 7;

    dir_x_ = 1;
    dir_y_ = 0;
    next_dir_x_ = 1;
    next_dir_y_ = 0;

    score_ = 0;
    state_ = STATE_PLAYING;
    tick_timer_ = 0.0f;
    tick_interval_ = 0.35f;

    PlaceFood();
}

void Game033Snake::Update(float dt, uint16_t keys_down, uint16_t keys_pressed)
{
    if (state_ == STATE_GAMEOVER) {
        if (keys_pressed & (KEY_A | KEY_START)) {
            Reset();
        }
        return;
    }

    if (keys_pressed & KEY_START) {
        state_ = (state_ == STATE_PLAYING) ? STATE_PAUSED : STATE_PLAYING;
        return;
    }

    if (state_ == STATE_PAUSED) return;

    // 输入响应与 180 度防自撞
    if ((keys_pressed & KEY_UP) && dir_y_ != 1) {
        next_dir_x_ = 0; next_dir_y_ = -1;
    } else if ((keys_pressed & KEY_DOWN) && dir_y_ != -1) {
        next_dir_x_ = 0; next_dir_y_ = 1;
    } else if ((keys_pressed & KEY_LEFT) && dir_x_ != 1) {
        next_dir_x_ = -1; next_dir_y_ = 0;
    } else if ((keys_pressed & KEY_RIGHT) && dir_x_ != -1) {
        next_dir_x_ = 1; next_dir_y_ = 0;
    }

    tick_timer_ += dt;
    if (tick_timer_ >= tick_interval_) {
        tick_timer_ -= tick_interval_;
        Step();
    }
}

void Game033Snake::Step()
{
    dir_x_ = next_dir_x_;
    dir_y_ = next_dir_y_;

    int new_hx = (snake_x_[0] + dir_x_ + 16) % 16;
    int new_hy = (snake_y_[0] + dir_y_ + 16) % 16;

    // 自噬检测
    for (int i = 1; i < snake_len_; ++i) {
        if (snake_x_[i] == new_hx && snake_y_[i] == new_hy) {
            state_ = STATE_GAMEOVER;
            return;
        }
    }

    // 移动蛇身
    int tail_x = snake_x_[snake_len_ - 1];
    int tail_y = snake_y_[snake_len_ - 1];

    for (int i = snake_len_ - 1; i > 0; --i) {
        snake_x_[i] = snake_x_[i - 1];
        snake_y_[i] = snake_y_[i - 1];
    }
    snake_x_[0] = new_hx;
    snake_y_[0] = new_hy;

    // 进食检测
    if (new_hx == food_x_ && new_hy == food_y_) {
        score_ += 10;
        if (snake_len_ < kMaxSnakeLen) {
            snake_x_[snake_len_] = tail_x;
            snake_y_[snake_len_] = tail_y;
            snake_len_++;
        }
        // 动态提升难度速度，最低至 0.08s
        tick_interval_ = 0.35f - (snake_len_ - 3) * 0.012f;
        if (tick_interval_ < 0.08f) tick_interval_ = 0.08f;

        PlaceFood();
    }
}

void Game033Snake::Render(uint8_t* fb_rgb24)
{
    memset(fb_rgb24, 0, kFrameBufferSize);

    // 绘制食物：鲜红
    int f_idx = (food_y_ * 16 + food_x_) * 3;
    fb_rgb24[f_idx + 0] = 255;
    fb_rgb24[f_idx + 1] = 20;
    fb_rgb24[f_idx + 2] = 20;

    // 绘制蛇身
    for (int i = 0; i < snake_len_; ++i) {
        int idx = (snake_y_[i] * 16 + snake_x_[i]) * 3;
        if (i == 0) {
            // 蛇头：明亮青柠色
            fb_rgb24[idx + 0] = 30;
            fb_rgb24[idx + 1] = 255;
            fb_rgb24[idx + 2] = 80;
        } else {
            // 蛇身：翠绿色
            fb_rgb24[idx + 0] = 0;
            fb_rgb24[idx + 1] = 180;
            fb_rgb24[idx + 2] = 20;
        }
    }
}

CartridgeStatus Game033Snake::GetStatus() const
{
    CartridgeStatus st;
    st.score = score_;
    st.lives = (state_ == STATE_GAMEOVER) ? 0 : 1;
    st.state = state_;
    st.progress = (snake_len_ * 100) / 64;
    if (st.progress > 100) st.progress = 100;
    return st;
}

} // namespace arcade
