// game_018_red_green_light.h —— 目标 #018 红灯绿灯 (Red Light Green)
// 机制: 顶部绿/黄闪烁/红信号灯与监察木偶 + 按住A/UP冲刺松开急刹 + 红灯移动激光淘汰
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

enum TrafficSignalPhase : uint8_t {
    SIGNAL_GREEN  = 0,
    SIGNAL_YELLOW = 1,
    SIGNAL_RED    = 2,
};

class Game018RedGreenLight : public Cartridge {
public:
    Game018RedGreenLight();
    ~Game018RedGreenLight() override = default;

    uint8_t GetId() const override { return 18; }
    const char* GetName() const override { return "红灯绿灯"; }
    const char* GetEnglishName() const override { return "Red Light Green"; }
    uint16_t GetReleaseYear() const override { return 2021; }
    ControlType GetControlType() const override { return CTRL_TAP_SINGLE; }

    void Init() override;
    void Reset() override;
    void Start() override;
    void Pause() override;
    void Resume() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    uint32_t NextRand();
    void AddScore(uint32_t pts);
    void StartRound(int round_num);
    float NextGreenDuration();
    float NextRedDuration();

    static const int kTotalRounds = 3;

    CartridgeState state_;
    TrafficSignalPhase signal_;
    float signal_timer_;
    float red_elapsed_;
    float player_x_;
    float player_y_;
    int round_;
    float round_timer_;
    bool laser_eliminated_;

    uint32_t score_;
    uint32_t high_score_;
    uint32_t rng_seed_;
    float state_timer_;
    float anim_timer_;
};

} // namespace arcade
