#pragma once

#include <cstdint>
#include "esp_timer.h"

namespace arcade {

// Game #124: 狂欢节射击场 (Carnival 1980 / Sega)
// 街机历史上最具代表性的游乐园旋转打靶游戏：
// 有限弹药库存管控、三层双向对开旋转靶标传送带、俯冲偷吃子弹的野鸭、转轮弹药补给与飞行奖励。

class Game124Carnival {
public:
    static constexpr uint8_t GAME_ID = 124;
    static constexpr const char* NAME = "狂欢节射击场";
    static constexpr const char* ENGLISH_NAME = "Carnival";
    static constexpr uint16_t RELEASE_YEAR = 1980;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_DUCK_ATTACK = 1;
    static constexpr uint8_t STATE_ROUND_CLEAR = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int NUM_ROWS = 3;
    static constexpr int TARGETS_PER_ROW = 6;
    static constexpr int MAX_BULLETS = 3;

    struct TargetItem {
        float x;
        uint8_t type; // 0: Rabbit (10pts), 1: Duck (20pts/dives), 2: Owl (30pts), 3: Extra Ammo (+5)
        bool alive;
    };

    struct DivingDuck {
        float x;
        float y;
        float vx;
        float vy;
        bool active;
    };

    struct Bullet {
        float x;
        float y;
        bool active;
    };

    Game124Carnival();
    ~Game124Carnival() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    int16_t GetAmmo() const { return ammo_; }
    uint8_t GetRound() const { return round_; }
    int GetRemainingTargets() const;

private:
    void InitRound();
    void UpdateGun(float dt, uint16_t buttons);
    void UpdateBullets(float dt);
    void UpdateCarousels(float dt);
    void UpdateDivingDucks(float dt);
    void CheckCollisions();
    void TriggerDivingDuck();

    uint8_t state_;
    float state_timer_;
    uint32_t score_;
    int16_t ammo_;
    uint8_t round_;

    // Gun position
    float gun_x_;

    // Bullets
    Bullet bullets_[MAX_BULLETS];

    // 3 carousel rows:
    // Row 0: y=3.0, moving left
    // Row 1: y=5.0, moving right
    // Row 2: y=7.0, moving left
    TargetItem rows_[NUM_ROWS][TARGETS_PER_ROW];
    float row_offsets_[NUM_ROWS];
    float row_speeds_[NUM_ROWS];

    // Diving duck threat
    DivingDuck diving_duck_;
    float duck_dive_timer_;

    // Top bonus wheel (pipe target at row y=1.0)
    float bonus_wheel_x_;
    bool bonus_wheel_alive_;
};

} // namespace arcade
