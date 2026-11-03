#pragma once

#include <cstdint>
#include "esp_timer.h"

namespace arcade {

// Game #126: 旋风巡航者 (Gyruss 1983 / Konami)
// 街机历史上最具代表性的360度圆周管状轨道向心射击游戏：
// 外环圆周轨道回旋航行、向心质点火炮齐射、深空中心向外扩散变轨敌机群、行星跃迁倒计时与螺旋机动。

class Game126Gyruss {
public:
    static constexpr uint8_t GAME_ID = 126;
    static constexpr const char* NAME = "旋风巡航者";
    static constexpr const char* ENGLISH_NAME = "Gyruss";
    static constexpr uint16_t RELEASE_YEAR = 1983;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_FLYING = 0;
    static constexpr uint8_t STATE_WARPING = 1;
    static constexpr uint8_t STATE_PLAYER_EXPLODING = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int MAX_ENEMIES = 8;
    static constexpr int MAX_BULLETS = 6;

    struct Enemy {
        float radius; // Distance from center (0.0 to 7.0)
        float angle;  // Radians
        float speed_r;
        float speed_a;
        bool is_asteroid;
        bool active;
    };

    struct Bullet {
        float radius; // Moves from 6.8 towards 0.0
        float angle;
        bool active;
    };

    Game126Gyruss();
    ~Game126Gyruss() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetWarpStage() const { return warp_stage_; }
    int GetRemainingDistance() const { return remaining_dist_; }

private:
    void InitStage();
    void UpdateShip(float dt, uint16_t buttons);
    void UpdateBullets(float dt);
    void UpdateEnemies(float dt);
    void CheckCollisions();
    void SpawnWave();

    uint8_t state_;
    float state_timer_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t warp_stage_; // 0: Neptune, 1: Uranus, 2: Saturn, 3: Jupiter, 4: Mars, 5: Earth
    int remaining_dist_;

    // Player starfighter on outer circle
    float player_angle_; // 0.0 to 2*PI
    float roll_timer_;
    float roll_cooldown_;

    // Bullets
    Bullet bullets_[MAX_BULLETS];

    // Enemies expanding from center outwards
    Enemy enemies_[MAX_ENEMIES];
    float wave_timer_;
};

} // namespace arcade
