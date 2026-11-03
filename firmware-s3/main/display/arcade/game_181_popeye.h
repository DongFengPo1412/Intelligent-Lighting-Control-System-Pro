#pragma once

#include <cstdint>

namespace arcade {

// Game #181: 大力水手 (Popeye - 1982 / Nintendo)
// 楼层回廊穿梭接取奥莉薇爱心、拳击菠菜罐头狂暴轰飞布鲁托、
// 抛投悬桶砸头与避让海巫毒瓶。

class Game181Popeye {
public:
    static constexpr uint8_t GAME_ID = 181;
    static constexpr const char* NAME = "大力水手";
    static constexpr const char* ENGLISH_NAME = "Popeye";
    static constexpr uint16_t RELEASE_YEAR = 1982;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_POPEYE_DEFEATED = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int MAX_HEARTS = 4;

    struct Heart {
        float x;
        float y;
        float vx;
        float vy;
        bool on_floor;
        float floor_timer;
        bool active;
    };

    Game181Popeye();
    ~Game181Popeye() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetStage() const { return stage_; }

    float GetPx() const { return px_; }
    float GetPy() const { return py_; }
    bool IsSpinachActive() const { return spinach_timer_ > 0.0f; }
    uint8_t GetHeartsCollected() const { return hearts_collected_; }

private:
    uint8_t state_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t stage_;
    float state_timer_;

    float px_;
    float py_;
    float speed_;
    float spinach_timer_;
    bool spinach_available_;
    float spinach_x_;
    float spinach_y_;

    float bx_;
    float by_;
    float bluto_stun_;
    float bluto_speed_;

    float olive_x_;
    float olive_y_;
    float drop_timer_;
    uint8_t hearts_collected_;
    uint8_t target_hearts_;

    Heart hearts_[MAX_HEARTS];

    void InitStage();
};

} // namespace arcade
