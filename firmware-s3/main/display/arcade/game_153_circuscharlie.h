#pragma once

#include <cstdint>

namespace arcade {

// Game #153: 马戏团 (Circus Charlie 1984 / Konami)
// 街机历史上最经典的马戏特技杂技与火圈跳跃传世名作：
// 骑乘驯狮纵马奔腾控速进退、精准起跳跨越地表火盆与移动烈火双环、
// 凌空穿透小火圈夺取悬空金币钱袋、飞跃登顶马戏团终点领奖台。

class Game153CircusCharlie {
public:
    static constexpr uint8_t GAME_ID = 153;
    static constexpr const char* NAME = "马戏团";
    static constexpr const char* ENGLISH_NAME = "Circus Charlie";
    static constexpr uint16_t RELEASE_YEAR = 1984;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_CHARLIE_DOWN = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr float COURSE_LENGTH = 85.0f;
    static constexpr float GROUND_Y = 13.0f;

    static constexpr int MAX_FIRE_POTS = 4;
    static constexpr int MAX_FIRE_HOOPS = 5;

    struct FireHoop {
        float track_pos;
        float speed;
        bool has_money;
        bool money_taken;
    };

    Game153CircusCharlie();
    ~Game153CircusCharlie() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetLevel() const { return level_; }

private:
    void InitLevel();
    void LoseLife();

    uint8_t state_;
    float state_timer_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t level_;

    float track_pos_;
    float y_;
    float vy_;
    bool is_jumping_;

    float fire_pots_[MAX_FIRE_POTS];
    int num_fire_pots_;

    FireHoop fire_hoops_[MAX_FIRE_HOOPS];
    int num_fire_hoops_;
};

} // namespace arcade
