#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game037SprintRacer : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_RACING = 1;
    static constexpr uint8_t STATE_VICTORY = 2;
    static constexpr uint8_t STATE_TIMEOUT = 3;

    static constexpr int NUM_CHECKPOINTS = 4;
    static constexpr int MAX_LAPS = 3;
    static constexpr int MAX_OIL_SLICKS = 3;

    struct OilSlick {
        float x;
        float y;
        bool active;
    };

    struct Car {
        float x;
        float y;
        float angle; // 弧度 [0, 2*PI)
        float speed;
        int next_checkpoint;
        int laps;
        float spin_timer;
    };

    Game037SprintRacer();
    ~Game037SprintRacer() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Sprint 2 (1976)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    int GetPlayerLaps() const { return player_.laps; }
    int GetAILaps() const { return ai_.laps; }
    float GetRaceTime() const { return race_time_; }

    float GetPlayerX() const { return player_.x; }
    float GetPlayerY() const { return player_.y; }
    float GetPlayerSpeed() const { return player_.speed; }

    void SetPlayerPos(float x, float y, float angle) {
        player_.x = x; player_.y = y; player_.angle = angle;
    }
    void SetPlayerLaps(int laps) { player_.laps = laps; }

private:
    void InitTrack();
    bool IsOnTrack(float x, float y) const;
    void UpdatePlayer(float dt, uint32_t buttons);
    void UpdateAI(float dt);
    void CheckCheckpoints(Car& car, bool is_player);
    void CheckOilCollisions(Car& car);

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;
    float race_time_;
    float time_limit_;

    Car player_;
    Car ai_;

    OilSlick oil_slicks_[MAX_OIL_SLICKS];
    uint8_t track_map_[16][16]; // 0: Track asphalt, 1: Wall/Infield barrier
};

} // namespace arcade
