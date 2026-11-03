#pragma once

#include <cstdint>
#include "esp_timer.h"

namespace arcade {

// Game #133: 袋鼠妈妈大冒险 (Kangaroo 1982 / Sun Electronics & Atari)
// 街机历史上第一部融合拳击手套格击与铃铛重置水果的树冠平台攀登动作游戏：
// 拳击手套直拳击昏顽猴与凌空截击飞苹果、跳跃撞响吊钟刷新全树水果、多层树梢爬梯营救小袋鼠。

class Game133Kangaroo {
public:
    static constexpr uint8_t GAME_ID = 133;
    static constexpr const char* NAME = "袋鼠妈妈大冒险";
    static constexpr const char* ENGLISH_NAME = "Kangaroo";
    static constexpr uint16_t RELEASE_YEAR = 1982;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_LEVEL_CLEAR = 1;
    static constexpr uint8_t STATE_MOM_DOWN = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int NUM_MONKEYS = 3;
    static constexpr int MAX_APPLES = 3;
    static constexpr int NUM_FRUITS = 4;

    struct Monkey {
        float x;
        float y;
        float throw_timer;
        bool alive;
    };

    struct Apple {
        float x;
        float y;
        float vy;
        bool active;
    };

    struct Fruit {
        float x;
        float y;
        bool collected;
    };

    Game133Kangaroo();
    ~Game133Kangaroo() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetLevel() const { return level_; }
    bool IsPunching() const { return punch_timer_ > 0.0f; }

private:
    void InitLevel();
    void UpdatePlayer(float dt, uint16_t buttons, uint16_t prev_buttons);
    void UpdateMonkeys(float dt);
    void UpdateApples(float dt);
    void CheckCollisions();
    void RingBell();

    uint8_t state_;
    float state_timer_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t level_;

    // Player Kangaroo
    float px_;
    float py_;
    float pvx_;
    float pvy_;
    int p_facing_; // -1: Left, +1: Right
    bool is_jumping_;
    bool is_ducking_;
    bool on_ladder_;
    float punch_timer_;

    // Bell at (11.0, 3.0)
    bool bell_rung_;
    float bell_ring_anim_;

    // Fruits
    Fruit fruits_[NUM_FRUITS];

    // Monkeys
    Monkey monkeys_[NUM_MONKEYS];

    // Falling apples
    Apple apples_[MAX_APPLES];

    // Joey position at (2.0, 2.0)
};

} // namespace arcade
