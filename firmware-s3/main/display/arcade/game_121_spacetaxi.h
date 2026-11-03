#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game121SpaceTaxi : public Cartridge {
public:
    Game121SpaceTaxi();
    ~Game121SpaceTaxi() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 121; }
    std::string GetName() const override { return "Space Taxi (1984)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_FLYING = 0,
        STATE_BOARDING = 1,
        STATE_FARE_PAID = 2,
        STATE_CRASHED = 3,
        STATE_GAME_OVER = 4
    };

    struct Pad {
        int id{1};
        int x_start{0};
        int x_end{0};
        int y{0};
    };

    struct Passenger {
        int current_pad{1};
        int target_pad{2};
        bool in_taxi{false};
        bool delivered{false};
    };

    static constexpr int NUM_PADS = 4;

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetLives() const { return lives_; }
    float GetFuel() const { return fuel_; }
    float GetTaxiX() const { return px_; }
    float GetTaxiY() const { return py_; }
    bool IsGearDeployed() const { return gear_deployed_; }
    int GetPassengerCurrentPad() const { return passenger_.current_pad; }
    int GetPassengerTargetPad() const { return passenger_.target_pad; }
    bool IsPassengerInTaxi() const { return passenger_.in_taxi; }

    void ToggleGear();
    void SetPositionAndVelocity(float x, float y, float vx, float vy);

private:
    GameState state_{STATE_FLYING};
    float state_timer_{0.0f};
    int score_{0};
    int lives_{3};
    float fuel_{100.0f};
    int fares_completed_{0};

    // Taxi Physics
    float px_{2.5f};
    float py_{12.0f};
    float vx_{0.0f};
    float vy_{0.0f};
    bool gear_deployed_{true};
    bool thrust_up_{false};
    bool thrust_left_{false};
    bool thrust_right_{false};

    Pad pads_[NUM_PADS];
    Passenger passenger_;

    void InitLevel();
    void InitPads();
    void SpawnPassenger();
    void UpdatePhysics(float dt, uint32_t buttons, uint32_t prev_buttons);
    void CheckPadLanding();
};

} // namespace arcade
