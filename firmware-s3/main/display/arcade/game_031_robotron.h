// game_031_robotron.h —— 目标 #031 双向射击 (Robotron 2084, 1982)
// 机制: 2D竞技场机器人潮围攻 + 人质营救(+100) + 移动与射击方向独立解耦(KEY_B锁定/轮换瞄准向, 边退边射)
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

struct RobotGrunt031 {
    bool active;
    float x;
    float y;
    float speed;
};

struct HumanSurvivor031 {
    bool active;
    float x;
    float y;
    float vx;
    float vy;
};

struct ArenaLaser031 {
    bool active;
    float x;
    float y;
    float vx;
    float vy;
    float life;
};

class Game031Robotron : public Cartridge {
public:
    static const int kMaxRobots = 12;
    static const int kMaxHumans = 3;
    static const int kMaxLasers = 6;

    Game031Robotron();
    ~Game031Robotron() override = default;

    uint8_t GetId() const override { return 31; }
    const char* GetName() const override { return "双向射击"; }
    const char* GetEnglishName() const override { return "Robotron 2084"; }
    uint16_t GetReleaseYear() const override { return 1982; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

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
    void SetupNewGame(CartridgeState new_state);
    void InitWave();
    void FireLaser();
    int CountActiveRobots() const;

    CartridgeState state_;
    uint32_t score_;
    uint32_t high_score_;
    uint8_t lives_;
    uint8_t wave_;

    float px_;
    float py_;
    uint8_t aim_dir_;   // 0..7 (8向瞄准: 0=上, 2=右, 4=下, 6=左)
    bool aim_locked_;   // KEY_B 锁定瞄准/循环切换角度, 实现移动与射击解耦
    float fire_cooldown_;
    float invuln_timer_;

    RobotGrunt031 robots_[kMaxRobots];
    HumanSurvivor031 humans_[kMaxHumans];
    ArenaLaser031 lasers_[kMaxLasers];

    float state_timer_;
    float anim_timer_;
    uint32_t seed_;
};

} // namespace arcade
