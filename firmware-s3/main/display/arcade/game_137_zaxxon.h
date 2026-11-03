#pragma once

#include <cstdint>
#include "esp_timer.h"

namespace arcade {

// Game #137: 扎克松立体战机 (Zaxxon 1982 / Sega)
// 街机历史上第一部采用轴测伪3D投影与高度差判定的里程碑太空战机游戏：
// 投射地面阴影指示真实坐标、按键调节飞行海拔高度穿梭城墙狭缝、
// 低空轰炸地面燃油罐补给、规避防空导弹并发射激光击破要塞机器人。

class Game137Zaxxon {
public:
    static constexpr uint8_t GAME_ID = 137;
    static constexpr const char* NAME = "扎克松立体战机";
    static constexpr const char* ENGLISH_NAME = "Zaxxon";
    static constexpr uint16_t RELEASE_YEAR = 1982;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_SHIP_CRASH = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr float MAX_ALTITUDE = 4.0f;
    static constexpr float MIN_ALTITUDE = 0.0f;
    static constexpr int MAX_BULLETS = 2;
    static constexpr int NUM_WALLS = 3;
    static constexpr int NUM_TARGETS = 5;

    struct Bullet {
        float x;
        float y;
        float z;
        bool active;
    };

    struct Wall {
        float y;
        float gate_z;
        bool cleared;
    };

    struct Target {
        float x;
        float y;
        uint8_t type; // 0: fuel, 1: turret
        bool alive;
    };

    struct Missile {
        float x;
        float y;
        bool active;
    };

    Game137Zaxxon();
    ~Game137Zaxxon() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetLevel() const { return level_; }
    float GetFuel() const { return fuel_; }
    float GetAltitude() const { return pz_; }

private:
    void InitLevel();
    void CrashShip();

    uint8_t state_;
    float state_timer_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t level_;
    float fuel_;

    float px_;
    float py_;
    float pz_;
    float distance_traveled_;

    Wall walls_[NUM_WALLS];
    Target targets_[NUM_TARGETS];
    Bullet bullets_[MAX_BULLETS];

    bool boss_active_;
    float boss_y_;
    int8_t boss_hp_;
    Missile boss_missile_;
    bool has_missile_;
};

} // namespace arcade
