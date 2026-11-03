#pragma once

#include <cstdint>

namespace arcade {

// Game #180: 小丑跷跷板 (Clowns / Circus - 1977 / Exidy & Midway)
// 底座跷跷板接球抛投、双杂技小丑交替重力重力弹射、
// 高空气球阵列逐层引爆清屏。

class Game180Clowns {
public:
    static constexpr uint8_t GAME_ID = 180;
    static constexpr const char* NAME = "小丑跷跷板";
    static constexpr const char* ENGLISH_NAME = "Clowns";
    static constexpr uint16_t RELEASE_YEAR = 1977;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_ACROBAT_SPLAT = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    Game180Clowns();
    ~Game180Clowns() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetStage() const { return stage_; }

    float GetSx() const { return sx_; }
    float GetAx() const { return ax_; }
    float GetAy() const { return ay_; }
    int8_t GetSeesawTilt() const { return seesaw_tilt_; }
    uint16_t GetBalloonsLeft() const { return balloons_left_; }

private:
    uint8_t state_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t stage_;
    float state_timer_;

    float sx_;
    int8_t seesaw_tilt_; // -1: left down, 1: right down
    float seesaw_speed_;

    float ax_;
    float ay_;
    float avx_;
    float avy_;
    float gravity_;

    uint8_t balloon_mask_[32]; // 256 bits for 16x16 balloons
    uint16_t balloons_left_;

    void InitStage();
    bool IsBalloon(int x, int y) const;
    void RemoveBalloon(int x, int y);
};

} // namespace arcade
