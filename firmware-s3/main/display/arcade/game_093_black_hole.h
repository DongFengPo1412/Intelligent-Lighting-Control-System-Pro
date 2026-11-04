// game_093_black_hole.h —— 目标 #093 黑洞吞噬 (Hole.io)
// 机制: 城市街区四向游走黑洞 + 三阶体积阈值判定(阻挡推挤 vs 引力吞噬) + 半径成长扩张清图
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

struct CityProp {
    bool alive;
    uint8_t tier;     // 1: 1x1 树木/路锥, 2: 2x2 汽车/货箱, 3: 3x3 摩天大楼
    uint8_t size;
    float x;
    float y;
    float req_radius; // 吞噬所需最小黑洞半径 (1.0 / 1.8 / 2.6)
};

class Game093BlackHole : public Cartridge {
public:
    Game093BlackHole();
    ~Game093BlackHole() override = default;

    uint8_t GetId() const override { return 93; }
    const char* GetName() const override { return "黑洞吞噬"; }
    const char* GetEnglishName() const override { return "Hole.io"; }
    uint16_t GetReleaseYear() const override { return 2018; }
    ControlType GetControlType() const override { return CTRL_DPAD_4WAY; }

    void Init() override;
    void Reset() override;
    void Start() override;
    void Pause() override;
    void Resume() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    void AddScore(uint32_t pts);
    void SetupCity();

    CartridgeState state_;
    uint32_t score_;
    uint32_t high_score_;
    float hole_x_;
    float hole_y_;
    float hole_radius_;
    float time_left_;
    float swallow_pulse_;
    float state_timer_;
    float anim_timer_;
    uint8_t remaining_props_;

    static const int kTotalProps = 20;
    CityProp props_[kTotalProps];
};

} // namespace arcade
