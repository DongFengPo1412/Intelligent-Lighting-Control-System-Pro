#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game111LeagueBowling : public Cartridge {
public:
    Game111LeagueBowling();
    ~Game111LeagueBowling() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 111; }
    std::string GetName() const override { return "League Bowling (1990)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_AIMING = 0,
        STATE_POWER_GAUGE = 1,
        STATE_BALL_ROLLING = 2,
        STATE_FRAME_RESULT = 3,
        STATE_GAME_OVER = 4
    };

    struct Pin {
        float x{0.0f};
        float y{0.0f};
        bool standing{true};
        float fall_timer{0.0f};
    };

    static constexpr int NUM_PINS = 10;
    static constexpr int TOTAL_FRAMES = 5;

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetCurrentFrame() const { return current_frame_; }
    int GetCurrentRoll() const { return current_roll_; }
    float GetBowlerX() const { return bowler_x_; }
    float GetBallX() const { return ball_x_; }
    float GetBallY() const { return ball_y_; }
    int GetHookSpin() const { return hook_spin_; } // -1 = Left hook, 0 = Straight, 1 = Right hook
    float GetThrowPower() const { return throw_power_; }
    int GetPinsKnockedDown() const { return pins_knocked_down_; }

    const Pin& GetPin(int i) const { return pins_[i]; }

    void ForceThrow(float power, int hook);

private:
    GameState state_{STATE_AIMING};
    float state_timer_{0.0f};
    int score_{0};
    int current_frame_{1};
    int current_roll_{1};
    int pins_knocked_down_{0};

    // Bowler Stance & Throw
    float bowler_x_{7.5f};
    float gauge_val_{0.0f};
    float gauge_dir_{1.0f};
    float throw_power_{10.0f};
    int hook_spin_{0}; // -1 = Left, 0 = Straight, 1 = Right

    // Bowling Ball
    float ball_x_{7.5f};
    float ball_y_{13.0f};
    float ball_vx_{0.0f};
    float ball_vy_{0.0f};
    bool in_gutter_{false};

    Pin pins_[NUM_PINS];

    void InitFrame();
    void ResetPins();
    void UpdateAimingAndGauge(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateBallRoll(float dt);
    void CheckPinCollisions();
    void ConcludeRoll();
};

} // namespace arcade
