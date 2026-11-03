#pragma once

#include <cstdint>
#include "esp_timer.h"

namespace arcade {

// Game #135: 疯狂小蜜蜂 (Pleiads 1981 / Tehkan)
// 街机历史上第一部具备三阶段递进战役与战舰泊机跑道的传奇射击游戏：
// 阶段一雷达屏障对垒、阶段二不死飞鸟俯冲截击、阶段三母舰核心轰破与航空跑道精准迫降。
// 按键A双联激光炮，按键B能量防护盾（每局限次）。

class Game135Pleiads {
public:
    static constexpr uint8_t GAME_ID = 135;
    static constexpr const char* NAME = "疯狂小蜜蜂";
    static constexpr const char* ENGLISH_NAME = "Pleiads";
    static constexpr uint16_t RELEASE_YEAR = 1981;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_SHIP_HIT = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr uint8_t PHASE_RADAR = 0;
    static constexpr uint8_t PHASE_BIRDS = 1;
    static constexpr uint8_t PHASE_LANDING = 2;

    static constexpr int MAX_BULLETS = 2;
    static constexpr int MAX_ENEMY_BULLETS = 4;
    static constexpr int NUM_ENEMIES = 4;
    static constexpr int NUM_BARRIERS = 4;

    struct Bullet {
        float x;
        float y;
        bool active;
    };

    struct Enemy {
        float x;
        float y;
        float vx;
        float base_x;
        float swoop_timer;
        bool alive;
        float shoot_timer;
    };

    struct Barrier {
        float x;
        float y;
        uint8_t hp;
    };

    Game135Pleiads();
    ~Game135Pleiads() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint8_t GetPhase() const { return phase_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetLevel() const { return level_; }

private:
    void InitLevel();
    void InitPhase0();
    void InitPhase1();
    void InitPhase2();
    void LoseLife();

    uint8_t state_;
    float state_timer_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t level_;

    uint8_t phase_;
    float px_;
    float py_;
    uint8_t shields_left_;
    bool shield_active_;
    float shield_timer_;

    Bullet bullets_[MAX_BULLETS];
    Bullet enemy_bullets_[MAX_ENEMY_BULLETS];
    Enemy enemies_[NUM_ENEMIES];
    Barrier barriers_[NUM_BARRIERS];

    int8_t mothership_hp_;
    float mothership_x_;
    float mothership_dir_;
    bool mothership_destroyed_;
};

} // namespace arcade
