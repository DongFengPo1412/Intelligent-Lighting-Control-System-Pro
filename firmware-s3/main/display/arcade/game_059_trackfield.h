#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game059TrackField : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_RUNNING = 1;
    static constexpr uint8_t STATE_ANGLE_AIM = 2;
    static constexpr uint8_t STATE_FLIGHT = 3;
    static constexpr uint8_t STATE_FOUL = 4;
    static constexpr uint8_t STATE_RESULT = 5;
    static constexpr uint8_t STATE_DEAD = 6;
    static constexpr uint8_t STATE_VICTORY = 7;

    Game059TrackField();
    ~Game059TrackField() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Track & Field (1983)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    int GetAttempt() const { return attempt_; }
    float GetSpeed() const { return speed_; }
    float GetThrowAngle() const { return throw_angle_; }
    float GetThrowDistance() const { return throw_distance_; }
    float GetBestDistance() const { return best_distance_; }
    float GetAthleteX() const { return athlete_x_; }

    void SetSpeed(float s) { speed_ = s; }
    void TriggerRelease(float angle);

private:
    void InitAttempt();
    void UpdateRunning(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateAiming(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateFlight(float dt);

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;

    int attempt_;               // 1 to 3
    float athlete_x_;
    float athlete_y_;
    float speed_;
    int last_button_pressed_;   // 1 for A, 2 for B

    float throw_angle_;         // 0 to 80 degrees
    bool angle_rising_;

    // Javelin flight physics
    float javelin_x_;
    float javelin_y_;
    float javelin_vx_;
    float javelin_vy_;
    float throw_distance_;
    float best_distance_;
    float qualify_distance_;
};

} // namespace arcade
