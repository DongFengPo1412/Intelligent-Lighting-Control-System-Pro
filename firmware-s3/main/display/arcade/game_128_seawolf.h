#pragma once

#include <cstdint>
#include "esp_timer.h"

namespace arcade {

// Game #128: 潜艇潜望镜猎杀 (Sea Wolf 1976 / Midway)
// 街机历史上第一人称潜望镜鱼雷猎杀模拟鼻祖：
// 潜望镜准星全景扫视、多层深度不同航速战舰编队、水面漂雷阻挡弹道、四联装鱼雷管序列齐射与限时猎杀。

class Game128SeaWolf {
public:
    static constexpr uint8_t GAME_ID = 128;
    static constexpr const char* NAME = "潜艇潜望镜猎杀";
    static constexpr const char* ENGLISH_NAME = "Sea Wolf";
    static constexpr uint16_t RELEASE_YEAR = 1976;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_HUNTING = 0;
    static constexpr uint8_t STATE_PATROL_CLEAR = 1;
    static constexpr uint8_t STATE_GAME_OVER = 2;

    static constexpr int NUM_DEPTH_LANES = 3; // Lane 0: y=2.0 (Fast PT boat), Lane 1: y=4.5 (Destroyer), Lane 2: y=7.0 (Cargo)
    static constexpr int MAX_SHIPS = 4;
    static constexpr int MAX_MINES = 3;
    static constexpr int MAX_TORPEDOES = 4;

    struct Ship {
        float x;
        float y;
        float vx;
        uint8_t type; // 0: Fast PT boat (500pts), 1: Destroyer (200pts), 2: Cargo (100pts)
        bool active;
    };

    struct SeaMine {
        float x;
        float y;
        float vx;
        bool active;
    };

    struct Torpedo {
        float x;
        float y;
        float vy;
        bool active;
    };

    Game128SeaWolf();
    ~Game128SeaWolf() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    float GetTimeRemaining() const { return time_remaining_; }
    uint8_t GetPatrolRound() const { return patrol_round_; }
    int GetAvailableTubes() const;

private:
    void InitPatrol();
    void UpdatePeriscope(float dt, uint16_t buttons);
    void UpdateTorpedoes(float dt);
    void UpdateShips(float dt);
    void UpdateMines(float dt);
    void CheckCollisions();
    void SpawnShip();

    uint8_t state_;
    float state_timer_;
    uint32_t score_;
    float time_remaining_;
    uint8_t patrol_round_;
    uint8_t ships_sunk_;

    // Periscope crosshair
    float periscope_x_;

    // 4 Torpedo tubes
    Torpedo torpedoes_[MAX_TORPEDOES];
    float tube_reload_timers_[MAX_TORPEDOES];

    // Naval targets
    Ship ships_[MAX_SHIPS];
    float ship_spawn_timer_;

    // Sea mines at y=9.0
    SeaMine mines_[MAX_MINES];
};

} // namespace arcade
