// game_033_snake.h —— 经典贪吃蛇 (Classic Snake)
// 编号: #033 | 机制: 网格转向、进食生长与自噬/碰墙检测 (支持经典硬边界与可选循环穿墙)
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
    void Start() override;
    void Pause() override;
    void Resume() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

    // 边界规则配置 (默认为传统致命死墙，符合原版街机挑战性；可开启穿墙娱乐模式)
    void SetWrapWalls(bool wrap) { wrap_walls_ = wrap; }
    bool GetWrapWalls() const { return wrap_walls_; }

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
    float anim_timer_;
    uint32_t score_;
    uint32_t high_score_;
    CartridgeState state_;
    bool wrap_walls_ = false; // 默认经典致命死墙
};

} // namespace arcade
