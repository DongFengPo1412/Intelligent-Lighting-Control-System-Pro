// game_075_slalom_ski.h —— 目标 #075 滑雪绕旗 (Alpine Slalom, 1982)
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

struct SlalomGate {
    float y;
    float left_x;
    float right_x;
    bool is_red_left;
    bool judged;
    bool passed;
    bool active;
};

struct SlopeObstacle {
    float x;
    float y;
    uint8_t type; // 0 = pine tree, 1 = mogul bump
    bool active;
};

class Game075SlalomSki : public Cartridge {
public:
    Game075SlalomSki();
    ~Game075SlalomSki() override = default;

    uint8_t GetId() const override { return 75; }
    const char* GetName() const override { return "滑雪绕旗"; }
    const char* GetEnglishName() const override { return "Alpine Slalom"; }
    uint16_t GetReleaseYear() const override { return 1982; }
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
    static const int kMaxGates = 3;
    static const int kMaxObstacles = 4;
    static const int kTargetGates = 20;

    void InitGameData();
    uint32_t NextRand();
    void AddScore(uint32_t pts);
    void SpawnNextGate(int slot, float start_y);
    void SpawnObstacleForGate(float gate_y, float gate_left, float gate_right);

    CartridgeState state_;
    float skier_x_;
    float skier_y_;
    float skier_vx_;
    float downhill_speed_;
    float snow_scroll_;
    SlalomGate gates_[kMaxGates];
    SlopeObstacle obstacles_[kMaxObstacles];
    int gate_seq_;
    int gates_passed_;
    int missed_gates_;
    int combo_;
    uint8_t lives_;
    float time_penalty_s_;
    float invuln_timer_;
    float green_flash_timer_;
    float red_flash_timer_;
    bool finish_active_;
    float finish_banner_y_;
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
    float anim_timer_;
    uint32_t rng_state_;
};

} // namespace arcade
