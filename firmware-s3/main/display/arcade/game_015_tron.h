// game_015_tron.h —— 创战纪光轮摩托 1982 (Tron Light Cycles 1982)
// 编号: #015 | 机制: 极速永久固体光痕堵路 + 90度瞬时折角 + 封闭竞技场智能诱导对决
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

enum TronOwner {
    TRON_NONE = 0,
    TRON_WALL = 1,
    TRON_P1 = 2,
    TRON_P2_AI = 3
};

struct LightCycle {
    int x;
    int y;
    int dir_x;
    int dir_y;
    bool alive;
    uint8_t r, g, b;
};

class Game015Tron : public Cartridge {
public:
    Game015Tron();
    ~Game015Tron() override = default;

    uint8_t GetId() const override { return 15; }
    const char* GetName() const override { return "创战纪光轮摩托"; }
    const char* GetEnglishName() const override { return "Tron Light Cycles 1982"; }
    uint16_t GetReleaseYear() const override { return 1982; }
    ControlType GetControlType() const override { return CTRL_DPAD_4WAY; }

    void Init() override;
    void Reset() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    void ResetRound();
    void StepAI();

    CartridgeState state_;
    uint8_t grid_[16][16]; // 记录光痕归属 (0=空, 1=外墙, 2=P1蓝痕, 3=AI橙红痕)

    LightCycle p1_;
    LightCycle p2_;

    uint8_t p1_wins_;
    uint8_t p2_wins_;
    static const uint8_t kTargetWins = 3;

    float step_timer_;
    float step_interval_; // 0.12s 极速跳步
    float state_timer_;
    uint32_t score_;
    uint32_t high_score_;
};

} // namespace arcade
