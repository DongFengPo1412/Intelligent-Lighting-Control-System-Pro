// game_014_orbit_hop.h —— 目标 #014 轨道跃迁 (Orbit Hop)
// 机制: 三层同心环形轨道自动公转 + 单键相邻轨道跃迁切换 + 躲避逆向红雷收集金星
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

struct OrbitStar {
    int orbit;
    float angle;
    bool active;
};

struct OrbitMine {
    int orbit;
    float angle;
    float speed;
    bool active;
};

class Game014OrbitHop : public Cartridge {
public:
    Game014OrbitHop();
    ~Game014OrbitHop() override = default;

    uint8_t GetId() const override { return 14; }
    const char* GetName() const override { return "轨道跃迁"; }
    const char* GetEnglishName() const override { return "Orbit Hop"; }
    uint16_t GetReleaseYear() const override { return 2016; }
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
    void SpawnWave();

    static const int kNumOrbits = 3;
    static const int kMaxStars = 6;
    static const int kMaxMines = 4;
    static const int kTargetWaves = 5;

    CartridgeState state_;
    int orbit_idx_;
    int hop_dir_;
    float player_angle_;
    float hop_flash_timer_;

    OrbitStar stars_[kMaxStars];
    OrbitMine mines_[kMaxMines];
    int stars_remaining_;
    int waves_cleared_;

    uint32_t score_;
    uint32_t high_score_;
    uint32_t rng_seed_;
    float state_timer_;
    float anim_timer_;
};

} // namespace arcade
