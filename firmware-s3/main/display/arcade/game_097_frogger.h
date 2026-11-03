// game_097_frogger.h —— 目标 #097 青蛙过河 (Frogger 1981)
// 机制: 垂直多车道公路闪避 + 水流浮木动态附着漂移 + 五穴安全进驻清屏
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

struct FrogLaneObstacle {
    float x;
    float width;
};

struct FrogLane {
    float speed;
    int num_items;
    float item_w;
    FrogLaneObstacle items[3];
    bool is_river;
    uint8_t r, g, b;
};

class Game097Frogger : public Cartridge {
public:
    Game097Frogger();
    ~Game097Frogger() override = default;

    uint8_t GetId() const override { return 97; }
    const char* GetName() const override { return "青蛙过河"; }
    const char* GetEnglishName() const override { return "Frogger 1981"; }
    uint16_t GetReleaseYear() const override { return 1981; }
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
    void ResetFrogPosition();
    void SetupLanes();
    void KillFrog();

    CartridgeState state_;
    float frog_x_;
    int frog_y_;
    uint8_t lives_;
    uint32_t score_;
    uint32_t high_score_;
    float round_timer_;
    float state_timer_;
    float anim_timer_;

    static const int kNumHomes = 5;
    bool homes_[kNumHomes];
    int homes_occupied_;

    static const int kTotalLanes = 16;
    FrogLane lanes_[kTotalLanes];
};

} // namespace arcade
