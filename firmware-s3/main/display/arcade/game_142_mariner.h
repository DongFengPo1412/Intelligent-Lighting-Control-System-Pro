#pragma once

#include <cstdint>
#include "esp_timer.h"

namespace arcade {

// Game #142: 深海潜航者 (Mariner 1981 / Amenip)
// 街机历史上第一部具备双向水下/水面火控与深海海沟勘探的潜艇横版射击游戏：
// 平移推进与中性浮力潜浮、按键A前向重型鱼雷猎杀深海潜艇、
// 按键B垂直防空深水导弹轰击水面驱逐舰、捕获海底热泉氧气泡与打捞沉船黄金。

class Game142Mariner {
public:
    static constexpr uint8_t GAME_ID = 142;
    static constexpr const char* NAME = "深海潜航者";
    static constexpr const char* ENGLISH_NAME = "Mariner";
    static constexpr uint16_t RELEASE_YEAR = 1981;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_SUB_CRASH = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int MAX_TORPEDOES = 2;
    static constexpr int MAX_MISSILES = 2;
    static constexpr int MAX_DEPTH_CHARGES = 3;
    static constexpr int NUM_ENEMIES = 3;
    static constexpr int NUM_BUBBLES = 2;

    struct Projectile {
        float x;
        float y;
        bool active;
    };

    struct DepthCharge {
        float x;
        float y;
        float vy;
        bool active;
    };

    struct Enemy {
        float x;
        float y;
        float vx;
        uint8_t type; // 0: destroyer, 1: sub
        float shoot_timer;
        bool alive;
    };

    struct Bubble {
        float x;
        float y;
        float vy;
        bool alive;
    };

    struct Treasure {
        float x;
        float y;
        bool collected;
    };

    Game142Mariner();
    ~Game142Mariner() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetLevel() const { return level_; }
    float GetOxygen() const { return oxygen_; }

private:
    void InitLevel();
    void Crash();

    uint8_t state_;
    float state_timer_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t level_;
    float oxygen_;

    float px_;
    float py_;

    Projectile torpedoes_[MAX_TORPEDOES];
    Projectile vertical_missiles_[MAX_MISSILES];
    DepthCharge depth_charges_[MAX_DEPTH_CHARGES];
    Enemy enemies_[NUM_ENEMIES];
    Bubble bubbles_[NUM_BUBBLES];
    Treasure treasure_;

    float seabed_[16];
};

} // namespace arcade
