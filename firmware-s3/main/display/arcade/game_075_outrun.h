#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game075OutRun : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_CRASH = 2;
    static constexpr uint8_t STATE_VICTORY = 3;

    static constexpr int MAX_CARS = 3;
    static constexpr int MAX_SCENERY = 4;

    struct TrafficCar {
        float x;           // -1.0 (left curb) to +1.0 (right curb)
        float distance;    // Ahead of player
        float speed;
        int color_type;    // 0: Blue sedan, 1: Yellow truck
        bool active;
    };

    struct Scenery {
        float x;
        float distance;
        int type;          // 0: Palm tree, 1: Billboard
        bool active;
    };

    Game075OutRun();
    ~Game075OutRun() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Out Run (1986)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    float GetCarX() const { return car_x_; }
    float GetCarSpeed() const { return car_speed_; }
    float GetTimeRemaining() const { return time_remaining_; }
    int GetStage() const { return current_stage_; }
    int GetRadioStation() const { return radio_station_; }
    bool IsAtFork() const { return is_at_fork_; }

    void CycleRadio();
    void ShiftGear();

private:
    void InitStage();
    void UpdateDriving(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateRoad(float dt);
    void UpdateTraffic(float dt);
    void CheckCollisions();

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;

    // Red Ferrari Testarossa state
    float car_x_;           // -1.0 to +1.0 (0 = center)
    float car_speed_;       // Current speed (0.0 to 180.0 km/h)
    bool high_gear_;
    int radio_station_;     // 0: Magical Sound Shower, 1: Passing Breeze, 2: Splash Wave

    // Road & Curve physics
    float road_curve_;      // Dynamic road curving (-1.0 to 1.0)
    float stage_distance_;  // Progress in current stage
    float stage_length_;    // Total distance to checkpoint/fork
    int current_stage_;     // 1 to 3
    float time_remaining_;
    bool is_at_fork_;

    TrafficCar traffic_[MAX_CARS];
    Scenery scenery_[MAX_SCENERY];
};

} // namespace arcade
