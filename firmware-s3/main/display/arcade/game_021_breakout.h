// game_021_breakout.h —— 目标 #021 经典打砖块 (Breakout 1976)
// 机制: 移动挡板反弹折射 + 上方阵列砖块敲击碎裂 + 生命损耗 + 清屏通关
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

struct BreakoutBrick {
    uint8_t hp;       // 剩余生命 (0 为已击碎)
    uint8_t r, g, b;  // 砖块颜色
};

class Game021Breakout : public Cartridge {
public:
    Game021Breakout();
    ~Game021Breakout() override = default;

    uint8_t GetId() const override { return 21; }
    const char* GetName() const override { return "经典打砖块"; }
    const char* GetEnglishName() const override { return "Breakout 1976"; }
    uint16_t GetReleaseYear() const override { return 1976; }
    ControlType GetControlType() const override { return CTRL_TWO_BUTTON; }

    void Init() override;
    void Reset() override;
    void Start() override;
    void Pause() override;
    void Resume() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    void ResetBallAndPaddle();

    CartridgeState state_;
    float paddle_x_;
    float paddle_w_;

    float ball_x_;
    float ball_y_;
    float ball_vx_;
    float ball_vy_;
    bool ball_stuck_;

    static const int kRows = 4;
    static const int kCols = 8;
    BreakoutBrick bricks_[kRows][kCols];
    int remaining_bricks_;

    uint8_t lives_;
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
    float anim_timer_;
};

} // namespace arcade
