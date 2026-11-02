// game_019_puzzle_bobble.h —— 像素泡泡龙 1994 (Puzzle Bobble 1994)
// 编号: #019 | 机制: 仰角旋转发射 + 侧壁反弹吸附 + 三连同色拓扑消除 + 浮空孤岛脱落
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

enum BubbleColor {
    BUBBLE_NONE = 0,
    BUBBLE_RED = 1,
    BUBBLE_BLUE = 2,
    BUBBLE_GREEN = 3,
    BUBBLE_YELLOW = 4
};

struct FlyingBubble {
    bool active;
    float x;
    float y;
    float vx;
    float vy;
    uint8_t color;
};

class Game019PuzzleBobble : public Cartridge {
public:
    Game019PuzzleBobble();
    ~Game019PuzzleBobble() override = default;

    uint8_t GetId() const override { return 19; }
    const char* GetName() const override { return "像素泡泡龙"; }
    const char* GetEnglishName() const override { return "Puzzle Bobble 1994"; }
    uint16_t GetReleaseYear() const override { return 1994; }
    ControlType GetControlType() const override { return CTRL_TWO_BUTTON; }

    void Init() override;
    void Reset() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    void ResetLevel();
    void FireBubble();
    void SnapAndResolve(float fx, float fy, uint8_t color);
    void RemoveFloatingIslands();
    void CheckCeilingDrop();
    int CountRemainingBubbles() const;

    CartridgeState state_;
    uint8_t grid_[16][16]; // 泡泡网格 (y: 0 ~ 13)

    float angle_deg_;      // 瞄准角度 (-60° ~ +60°, 0°为正上方)
    uint8_t current_color_;// 当前待发射泡泡颜色
    uint8_t next_color_;   // 下一颗预备泡泡
    FlyingBubble flying_;  // 飞行中泡泡

    uint32_t shots_fired_;
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
};

} // namespace arcade
