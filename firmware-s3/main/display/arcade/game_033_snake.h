// game_033_snake.h —— 经典贪吃蛇 (Classic Snake)
// 编号: #033 | 机制: 网格转向、进食生长与自噬检测
#pragma once

#include "arcade_cartridge.h"
#include <stdint.h>
#include <stdbool.h>

namespace arcade {

class Game033Snake : public Cartridge {
public:
    Game033Snake();
    ~Game033Snake() override = default;

    uint8_t GetId() const override { return 33; }
    const char* GetName() const override { return "经典贪吃蛇"; }
    const char* GetEnglishName() const override { return "Classic Snake"; }
    uint16_t GetReleaseYear() const override { return 1976; }
    ControlType GetControlType() const override { return CTRL_DPAD_4WAY; }

    void Init() override;
    void Reset() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    void PlaceFood();
    void Step();

    static const int kMaxSnakeLen = 256;
    int snake_x_[kMaxSnakeLen];
    int snake_y_[kMaxSnakeLen];
    int snake_len_;
    int dir_x_;
    int dir_y_;
    int next_dir_x_;
    int next_dir_y_;
    int food_x_;
    int food_y_;

    float tick_timer_;
    float tick_interval_;
    uint32_t score_;
    CartridgeState state_;
};

} // namespace arcade
