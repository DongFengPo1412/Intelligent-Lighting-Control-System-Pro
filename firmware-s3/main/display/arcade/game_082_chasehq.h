#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game082ChaseHQ : public Cartridge {
public:
    Game082ChaseHQ();
    ~Game082ChaseHQ() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 82; }
    std::string GetName() const override { return "Chase H.Q. (1988)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_APPROACH = 0, // Catching up with suspect
        STATE_PURSUIT = 1,  // Ramming criminal car
        STATE_ARRESTED = 2, // Victory
        STATE_TIME_UP = 3   // Failed
    };

    struct TrafficCar {
        float x{0.0f};
        float y{0.0f}; // 0 = far, 14 = near
        float speed{5.0f};
        bool active{false};
    };

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    float GetTimeRemaining() const { return time_remaining_; }
    int GetTurbosLeft() const { return turbos_left_; }
    float GetSuspectDamage() const { return suspect_damage_; }
    float GetPlayerX() const { return px_; }
    float GetSuspectX() const { return sx_; }
    bool IsTurboActive() const { return turbo_timer_ > 0.0f; }

private:
    void ResetMission();
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateTraffic(float dt);
    void UpdateSuspect(float dt);
    void CheckRamming();

    GameState state_{STATE_APPROACH};
    float state_timer_{0.0f};
    float time_remaining_{45.0f};
    int score_{0};
    int high_score_{20000};
    int turbos_left_{3};
    float turbo_timer_{0.0f};

    // Police Cruiser (Porsche 928)
    float px_{7.5f};
    float py_{13.0f};
    float p_speed_{10.0f}; // normal ~10, turbo ~18

    // Distance to suspect (starts 100.0m -> 0.0m triggers PURSUIT)
    float distance_to_suspect_{100.0f};

    // Suspect Criminal Vehicle
    float sx_{7.5f};
    float sy_{6.0f};
    float s_speed_{9.0f};
    float suspect_damage_{0.0f}; // 0% to 100%
    float s_swerve_timer_{0.0f};

    static constexpr int MAX_TRAFFIC = 3;
    TrafficCar traffic_[MAX_TRAFFIC];

    float road_scroll_{0.0f};
};

} // namespace arcade
