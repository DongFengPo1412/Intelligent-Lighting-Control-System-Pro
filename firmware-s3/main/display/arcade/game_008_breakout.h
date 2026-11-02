// game_008_breakout.h —— 经典打砖块 1976 (Breakout 1976)
// 编号: #008 | 机制: 移动挡板反弹折射 + 上方阵列砖块敲击碎裂 + 生命损耗 + 清屏通关
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

struct Brick {
    uint8_t hp;       // 剩余生命 (0 为已击碎)
    uint8_t r, g, b;  // 砖块颜色
};

class Game008Breakout : public Cartridge {
public:
    Game008Breakout();
    ~Game008Breakout() override = default;

    uint8_t GetId() const override { return 8; }
    const char* GetName() const override { return "经典打砖块"; }
    const char* GetEnglishName() const override { return "Breakout 1976"; }
    uint16_t GetReleaseYear() const override { return 1976; }
    ControlType GetControlType() const override { return CTRL_TWO_BUTTON; }

    void Init() override;
    void Reset() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    void ResetBallAndPaddle();

    CartridgeState state_;
    float paddle_x_;        // 底部挡板左侧 X (0 ~ 12)
    float paddle_w_;        // 挡板宽度 (4 像素)

    float ball_x_;          // 小球 X
    float ball_y_;          // 小球 Y
    float ball_vx_;         // 小球 X 速度
    float ball_vy_;         // 小球 Y 速度
    bool ball_stuck_;       // 发球前小球吸附在挡板上

    static const int kRows = 4;
    static const int kCols = 8;
    Brick bricks_[kRows][kCols]; // 4 排，每排 8 块 (每块占 2x1 像素)
    int remaining_bricks_;

    uint8_t lives_;         // 剩余生命 (初始 3)
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
};

} // namespace arcade
