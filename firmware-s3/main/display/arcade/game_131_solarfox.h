#pragma once

#include <cstdint>
#include "esp_timer.h"

namespace arcade {

// Game #131: 太阳能战机 (Solar Fox 1981 / Bally Midway)
// 街机历史上最具速度感的矩阵能量网格扫掠与外围哨兵狙击对决：
// 矩阵太阳能晶胞高速巡航收割、外围四方巡逻哨兵向心齐射火球、双速巡航超频冲刺与能量护盾。

class Game131SolarFox {
public:
    static constexpr uint8_t GAME_ID = 131;
    static constexpr const char* NAME = "太阳能战机";
    static constexpr const char* ENGLISH_NAME = "Solar Fox";
    static constexpr uint16_t RELEASE_YEAR = 1981;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_FLYING = 0;
    static constexpr uint8_t STATE_SHIP_EXPLODING = 1;
    static constexpr uint8_t STATE_QUADRANT_CLEAR = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int MATRIX_W = 10;
    static constexpr int MATRIX_H = 10;
    static constexpr int MAX_FIREBALLS = 4;
    static constexpr int NUM_SENTINELS = 4; // 0: Top, 1: Bottom, 2: Left, 3: Right

    struct Sentinel {
        float pos; // Position along perimeter (2.0 to 13.0)
        float speed;
        float fire_cooldown;
    };

    struct Fireball {
        float x;
        float y;
        float vx;
        float vy;
        bool active;
    };

    Game131SolarFox();
    ~Game131SolarFox() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetQuadrant() const { return quadrant_; }
    int GetRemainingCells() const { return remaining_cells_; }
    bool IsShieldActive() const { return shield_timer_ > 0.0f; }

private:
    void InitQuadrant();
    void UpdateShip(float dt, uint16_t buttons);
    void UpdateSentinels(float dt);
    void UpdateFireballs(float dt);
    void CheckCollisions();

    uint8_t state_;
    float state_timer_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t quadrant_;
    int remaining_cells_;

    // Player starfighter
    float px_;
    float py_;
    int dir_x_;
    int dir_y_;
    int next_dir_x_;
    int next_dir_y_;
    bool is_hyperspeed_;
    float shield_timer_;
    float shield_cooldown_;

    // Energy cells matrix (10x10 located in range x in [3, 12], y in [3, 12])
    bool cells_[MATRIX_H][MATRIX_W];

    // Perimeter sentinels
    Sentinel sentinels_[NUM_SENTINELS];

    // Fireballs
    Fireball fireballs_[MAX_FIREBALLS];
};

} // namespace arcade
