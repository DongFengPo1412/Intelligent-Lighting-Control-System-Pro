#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game060MarbleMadness : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_SHATTERED = 2;
    static constexpr uint8_t STATE_DEAD = 3;
    static constexpr uint8_t STATE_VICTORY = 4;

    Game060MarbleMadness();
    ~Game060MarbleMadness() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Marble Madness (1984)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    float GetTimeRemaining() const { return time_remaining_; }
    float GetMarbleX() const { return marble_x_; }
    float GetMarbleY() const { return marble_y_; }
    float GetMarbleVX() const { return marble_vx_; }
    float GetMarbleVY() const { return marble_vy_; }
    bool IsOnIce() const { return is_on_ice_; }

    void SetMarblePos(float x, float y) { marble_x_ = x; marble_y_ = y; }

private:
    void InitCourse();
    void UpdateMarblePhysics(float dt, uint32_t buttons);
    void UpdateEvilMarble(float dt);
    void CheckTrackHazards();

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;
    float time_remaining_;

    // Marble physics
    float marble_x_;
    float marble_y_;
    float marble_vx_;
    float marble_vy_;
    bool is_on_ice_;

    // Rival Black Evil Marble
    float evil_x_;
    float evil_y_;
    float evil_vx_;
    float evil_vy_;

    // Acid puddle trap
    float acid_x_;
    float acid_y_;

    // Goal zone
    float goal_x_;
    float goal_y_;
};

} // namespace arcade
