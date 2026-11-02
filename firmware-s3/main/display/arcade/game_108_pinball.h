#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game108Pinball : public Cartridge {
public:
    Game108Pinball();
    ~Game108Pinball() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 108; }
    std::string GetName() const override { return "Pinball (1984)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_PLUNGER_READY = 0,
        STATE_BALL_IN_PLAY = 1,
        STATE_BALL_DRAINED = 2,
        STATE_GAME_OVER = 3
    };

    struct Bumper {
        float x{0.0f};
        float y{0.0f};
        float flash_timer{0.0f};
    };

    struct Rollover {
        int x{0};
        int y{0};
        bool lit{false};
    };

    static constexpr int NUM_BUMPERS = 3;
    static constexpr int NUM_ROLLOVERS = 3;

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetBallsLeft() const { return balls_left_; }
    int GetMultiplier() const { return multiplier_; }
    float GetBallX() const { return ball_x_; }
    float GetBallY() const { return ball_y_; }
    bool IsLeftFlipperUp() const { return left_flipper_up_; }
    bool IsRightFlipperUp() const { return right_flipper_up_; }

    const Bumper& GetBumper(int i) const { return bumpers_[i]; }
    const Rollover& GetRollover(int i) const { return rollovers_[i]; }

    void LaunchBall(float power);

private:
    GameState state_{STATE_PLUNGER_READY};
    float state_timer_{0.0f};
    int score_{0};
    int balls_left_{3};
    int multiplier_{1};

    // Plunger
    float plunger_charge_{0.0f};

    // Silver Ball Physics
    float ball_x_{14.5f}; // In shooter lane
    float ball_y_{14.0f};
    float ball_vx_{0.0f};
    float ball_vy_{0.0f};

    // Flippers: Left (x=5..7, y=14), Right (x=8..10, y=14)
    bool left_flipper_up_{false};
    bool right_flipper_up_{false};

    Bumper bumpers_[NUM_BUMPERS];
    Rollover rollovers_[NUM_ROLLOVERS];

    void InitTable();
    void ResetBallToPlunger();
    void UpdateFlippersAndPlunger(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateBallPhysics(float dt);
    void CheckBumperCollisions();
    void CheckFlipperCollisions();
    void CheckRollovers();
};

} // namespace arcade
