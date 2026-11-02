#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game045SidePocket : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_AIMING = 1;
    static constexpr uint8_t STATE_CHARGING = 2;
    static constexpr uint8_t STATE_ROLLING = 3;
    static constexpr uint8_t STATE_SCRATCH = 4;
    static constexpr uint8_t STATE_VICTORY = 5;

    static constexpr int NUM_OBJECT_BALLS = 5;
    static constexpr int TOTAL_BALLS = 6; // 1 Cue ball + 5 Object balls

    struct Ball {
        float x;
        float y;
        float vx;
        float vy;
        bool active;
        bool is_cue;
        uint8_t r, g, b;
    };

    Game045SidePocket();
    ~Game045SidePocket() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Side Pocket (1986)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    float GetAimAngle() const { return aim_angle_; }
    float GetChargePower() const { return charge_power_; }
    int GetRemainingBalls() const;

    float GetCueBallX() const { return balls_[0].x; }
    float GetCueBallY() const { return balls_[0].y; }
    void StrikeCueBall(float angle_rad, float power);

private:
    void InitTable();
    void UpdateAiming(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdatePhysics(float dt);
    void CheckPocketCollisions();
    void CheckBallBallCollisions();
    void CheckCushionCollisions();
    bool AreBallsMoving() const;

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;
    int balls_potted_;

    float aim_angle_;       // Radians 0 to 2*PI
    float charge_power_;    // 0.0 to 1.0
    float charge_dir_;      // +1 or -1 oscillation

    Ball balls_[TOTAL_BALLS];
};

} // namespace arcade
