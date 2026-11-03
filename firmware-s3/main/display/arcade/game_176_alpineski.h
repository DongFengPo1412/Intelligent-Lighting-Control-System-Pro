#pragma once

#include <cstdint>

namespace arcade {

// Game #176: 高山滑雪 (Alpine Ski - 1982 / Taito)
// 高山雪道极速俯冲、红蓝旗门回转穿梭加分、
// 飞跃跳台腾空跨越树丛巨石与限时冲线。

class Game176AlpineSki {
public:
    static constexpr uint8_t GAME_ID = 176;
    static constexpr const char* NAME = "高山滑雪";
    static constexpr const char* ENGLISH_NAME = "Alpine Ski";
    static constexpr uint16_t RELEASE_YEAR = 1982;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_WIPEOUT = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int MAX_ELEMENTS = 40;

    enum ElementType : uint8_t {
        ELEM_GATE = 0,
        ELEM_TREE = 1,
        ELEM_ROCK = 2,
        ELEM_RAMP = 3,
    };

    struct TrackElement {
        float y;
        ElementType type;
        float x;
        float x2;
        bool cleared;
        bool active;
    };

    Game176AlpineSki();
    ~Game176AlpineSki() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetStage() const { return stage_; }

    float GetPx() const { return px_; }
    float GetTimeLeft() const { return time_left_; }
    float GetDistance() const { return distance_; }
    bool IsInAir() const { return in_air_; }

private:
    uint8_t state_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t stage_;
    float state_timer_;

    float px_;
    float py_;
    float steer_speed_;
    float base_speed_;
    float speed_;
    bool in_air_;
    float jump_timer_;

    float time_left_;
    float distance_;
    float target_distance_;

    TrackElement elements_[MAX_ELEMENTS];

    void InitStage();
    void SpawnTrack();
    void Wipeout();
};

} // namespace arcade

