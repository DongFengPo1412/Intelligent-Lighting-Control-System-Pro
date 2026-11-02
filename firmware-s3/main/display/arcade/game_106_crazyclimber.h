#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game106CrazyClimber : public Cartridge {
public:
    Game106CrazyClimber();
    ~Game106CrazyClimber() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 106; }
    std::string GetName() const override { return "Crazy Climber (1980)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_CLIMBING = 0,
        STATE_SLIPPED_ONE_HAND = 1,
        STATE_FALL_OFF = 2,
        STATE_ROOFTOP_CLEAR = 3,
        STATE_GAME_OVER = 4
    };

    struct Window {
        bool is_open{true};
        float toggle_timer{2.0f};
        bool has_hazard{false}; // Flowerpot dropper
    };

    struct FallingHazard {
        float x{0.0f};
        float y{0.0f};
        float vy{7.0f};
        bool is_condor_egg{false};
        bool active{false};
    };

    static constexpr int NUM_WINDOW_COLS = 4; // Columns at x=3, 6, 9, 12
    static constexpr int NUM_WINDOW_ROWS = 6;
    static constexpr int MAX_HAZARDS = 3;

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetLives() const { return lives_; }
    int GetAltitude() const { return altitude_; }
    int GetCurrentCol() const { return climber_col_; }
    float GetPlayerY() const { return climber_y_; }
    bool GetLeftHandGrip() const { return left_hand_grip_; }
    bool GetRightHandGrip() const { return right_hand_grip_; }

    const FallingHazard& GetHazard(int i) const { return hazards_[i]; }

private:
    GameState state_{STATE_CLIMBING};
    float state_timer_{0.0f};
    int score_{0};
    int lives_{3};
    int altitude_{0}; // 0 to 100 meters to reach rooftop

    // Climber
    int climber_col_{1}; // 0..3 (cols at x=3, 6, 9, 12)
    float climber_y_{13.0f};
    bool left_hand_grip_{true};
    bool right_hand_grip_{true};
    float slip_recovery_timer_{0.0f};
    int last_pull_hand_{0}; // 1 = Left (A), 2 = Right (B)

    // Condor
    float condor_x_{2.0f};
    float condor_vx_{3.0f};
    float condor_egg_timer_{1.5f};

    Window windows_[NUM_WINDOW_ROWS][NUM_WINDOW_COLS];
    FallingHazard hazards_[MAX_HAZARDS];

    void InitBuilding();
    void UpdateClimber(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateWindows(float dt);
    void UpdateCondorAndHazards(float dt);
    void CheckCollisions();
};

} // namespace arcade
