#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game044Excitebike : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_CRASH = 2;
    static constexpr uint8_t STATE_OVERHEAT = 3;
    static constexpr uint8_t STATE_VICTORY = 4;

    static constexpr int TRACK_LENGTH = 120; // 120 tiles long track
    static constexpr int NUM_OBSTACLES = 16;

    enum ObstacleType {
        OBS_NONE = 0,
        OBS_SMALL_RAMP = 1,
        OBS_BIG_RAMP = 2,
        OBS_MUD_PUDDLE = 3,
        OBS_COOLING_STRIP = 4,
        OBS_HURDLE = 5
    };

    struct Obstacle {
        float world_x;
        int lane;       // 0..3 (y = 8, 9, 10, 11)
        ObstacleType type;
    };

    Game044Excitebike();
    ~Game044Excitebike() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Excitebike (1984)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    float GetWorldDistance() const { return world_x_; }
    float GetSpeed() const { return speed_; }
    float GetEngineTemp() const { return engine_temp_; }
    float GetPitchAngle() const { return pitch_angle_; }
    bool IsAirborne() const { return is_airborne_; }
    int GetLane() const { return lane_; }

    void SetPlayerPos(float wx, int lane) { world_x_ = wx; lane_ = lane; }
    void TriggerCrash();

private:
    void InitTrack();
    void UpdateBike(float dt, uint32_t buttons, uint32_t prev_buttons);
    void CheckTerrainCollisions();

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;

    float world_x_;
    float speed_;
    int lane_;              // 0..3
    float altitude_;        // Height above ground in air
    float vertical_vy_;     // Airborne vertical speed
    float pitch_angle_;     // -1.0 (nose up/wheelie) to +1.0 (nose dive)
    bool is_airborne_;

    float engine_temp_;     // 0.0 to 100.0 (Overheats at 100)
    float crash_recovery_timer_;

    Obstacle obstacles_[NUM_OBSTACLES];
};

} // namespace arcade
