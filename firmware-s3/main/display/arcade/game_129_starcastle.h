#pragma once

#include <cstdint>
#include "esp_timer.h"

namespace arcade {

// Game #129: 星际要塞 (Star Castle 1980 / Cinematronics)
// 街机历史上最具传奇色彩的多层同心回转护盾穿透射击游戏：
// 三层对向旋转同心护盾环、环隙对齐致命主炮直射、精准穿透射击爆破核心、拦截追踪电火花地雷。

class Game129StarCastle {
public:
    static constexpr uint8_t GAME_ID = 129;
    static constexpr const char* NAME = "星际要塞";
    static constexpr const char* ENGLISH_NAME = "Star Castle";
    static constexpr uint16_t RELEASE_YEAR = 1980;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_CASTLE_EXPLODING = 1;
    static constexpr uint8_t STATE_PLAYER_EXPLODING = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int NUM_RINGS = 3;       // 0: Outer (R=5.2), 1: Middle (R=3.8), 2: Inner (R=2.4)
    static constexpr int SEGMENTS_PER_RING = 8;
    static constexpr int MAX_BULLETS = 4;
    static constexpr int MAX_SPARKS = 3;

    struct SparkMine {
        float x;
        float y;
        float vx;
        float vy;
        bool active;
    };

    struct Bullet {
        float x;
        float y;
        float vx;
        float vy;
        bool active;
    };

    struct CannonBlast {
        float x;
        float y;
        float vx;
        float vy;
        bool active;
    };

    Game129StarCastle();
    ~Game129StarCastle() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetLevel() const { return level_; }
    bool IsShieldSegmentAlive(int ring, int seg) const { return shield_alive_[ring][seg]; }

private:
    void InitCastle();
    void UpdateShip(float dt, uint16_t buttons);
    void UpdateShields(float dt);
    void UpdateBullets(float dt);
    void UpdateSparks(float dt);
    void UpdateBossTurret(float dt);
    void CheckCollisions();
    bool HasDirectLineOfSight(float angle) const;

    uint8_t state_;
    float state_timer_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t level_;

    // Player ship
    float px_;
    float py_;
    float pvx_;
    float pvy_;
    float p_angle_; // radians

    // Boss Core Cannon at (7.5, 7.5)
    float turret_angle_;
    float turret_fire_timer_;
    CannonBlast blast_;

    // 3 concentric shield rings
    bool shield_alive_[NUM_RINGS][SEGMENTS_PER_RING];
    float ring_angles_[NUM_RINGS];
    float ring_speeds_[NUM_RINGS];

    // Sparks & bullets
    SparkMine sparks_[MAX_SPARKS];
    float spark_spawn_timer_;
    Bullet bullets_[MAX_BULLETS];
};

} // namespace arcade
