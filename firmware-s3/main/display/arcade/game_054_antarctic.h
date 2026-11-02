#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game054Antarctic : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_DEAD = 2;
    static constexpr uint8_t STATE_VICTORY = 3;

    static constexpr int MAX_CREVASSES = 3;
    static constexpr int MAX_SEALS = 2;
    static constexpr int MAX_FISH = 2;

    struct Crevasse {
        float z;        // Distance down road (0 to 100)
        float lane;     // -0.8 to +0.8
        bool active;
    };

    struct Seal {
        float z;
        float lane;
        bool popped_up;
        bool active;
    };

    struct Fish {
        float z;
        float lane;
        bool active;
    };

    Game054Antarctic();
    ~Game054Antarctic() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Antarctic Adventure (1983)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }

    float GetSpeed() const { return speed_; }
    float GetDistanceRemaining() const { return distance_remaining_; }
    float GetTimeRemaining() const { return time_remaining_; }
    bool IsJumping() const { return is_jumping_; }
    bool IsStunned() const { return trip_stun_timer_ > 0.0f; }
    float GetLane() const { return penguin_lane_; }

    void SetDistanceRemaining(float d) { distance_remaining_ = d; }
    void TriggerJump();

private:
    void InitStage();
    void UpdatePenguin(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateHazards(float dt);
    void CheckCollisions();

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;

    float penguin_lane_;    // -1.0 (left) to +1.0 (right)
    float speed_;           // Current skating speed
    bool is_jumping_;
    float jump_timer_;
    float trip_stun_timer_; // Stun delay when tripping on obstacle

    float distance_remaining_;
    float time_remaining_;
    int fish_collected_;

    Crevasse crevasses_[MAX_CREVASSES];
    Seal seals_[MAX_SEALS];
    Fish fishes_[MAX_FISH];
};

} // namespace arcade
