#pragma once

#include <cstdint>
#include "esp_timer.h"

namespace arcade {

// Game #125: 碰碰车大乱斗 (Bumping Buggies 1981 / Sanritsu & Sega)
// 街机历史上经典的游乐场碰碰车冲撞竞技：
// 弹性碰撞动量转移、油渍漂移失控打滑、高压电网围栏边缘处决、蓄力猛撞与手刹甩尾。

class Game125BumpingBuggies {
public:
    static constexpr uint8_t GAME_ID = 125;
    static constexpr const char* NAME = "碰碰车大乱斗";
    static constexpr const char* ENGLISH_NAME = "Bumping Buggies";
    static constexpr uint16_t RELEASE_YEAR = 1981;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_PLAYER_CRASHED = 1;
    static constexpr uint8_t STATE_ROUND_CLEAR = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int MAX_OPPONENTS = 3;
    static constexpr int MAX_OIL_SLICKS = 3;

    struct Buggy {
        float x;
        float y;
        float vx;
        float vy;
        float angle; // radians
        float spin_timer;
        bool is_ramming;
        bool active;
    };

    struct OilSlick {
        float x;
        float y;
        bool active;
    };

    Game125BumpingBuggies();
    ~Game125BumpingBuggies() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetRound() const { return round_; }
    int GetActiveOpponents() const;

private:
    void InitRound();
    void UpdatePlayer(float dt, uint16_t buttons, uint16_t prev_buttons);
    void UpdateOpponents(float dt);
    void HandleBuggyCollision(Buggy& a, Buggy& b);
    void CheckWallAndHazardCollisions();

    uint8_t state_;
    float state_timer_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t round_;

    // Player Buggy
    Buggy player_;
    float ram_cooldown_;
    float drift_timer_;

    // Opponent Buggies
    Buggy opponents_[MAX_OPPONENTS];

    // Oil slicks
    OilSlick slicks_[MAX_OIL_SLICKS];
};

} // namespace arcade
