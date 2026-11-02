#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game070LunarPool : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_BALLS_MOVING = 2;
    static constexpr uint8_t STATE_DEAD = 3;
    static constexpr uint8_t STATE_VICTORY = 4;

    static constexpr int MAX_BALLS = 5; // 1 Cue ball + 4 Target balls
    static constexpr int MAX_POCKETS = 4;

    struct Ball {
        float x;
        float y;
        float vx;
        float vy;
        bool is_cue;
        int number;      // 0: Cue (white), 1..4: Target colored balls
        bool in_pocket;
    };

    struct Pocket {
        float x;
        float y;
        float radius;
    };

    Game070LunarPool();
    ~Game070LunarPool() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Lunar Pool (1985)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    int GetLives() const { return lives_; }
    float GetAimAngle() const { return aim_angle_; }
    float GetPower() const { return shot_power_; }
    int GetBallsRemaining() const;

    void ShootCueBall(float power);
    void SetAimAngle(float angle) { aim_angle_ = angle; }

private:
    void InitTable();
    void UpdateAiming(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdatePhysics(float dt);
    void CheckPocketCollisions();
    void CheckBallCollisions();

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;
    int lives_;

    // Cue aiming and power
    float aim_angle_;       // In radians
    float shot_power_;
    bool is_charging_power_;
    int combo_multiplier_;
    float friction_;

    Ball balls_[MAX_BALLS];
    Pocket pockets_[MAX_POCKETS];
};

} // namespace arcade
