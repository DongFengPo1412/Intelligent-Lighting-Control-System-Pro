#pragma once

#include <cstdint>
#include "esp_timer.h"

namespace arcade {

// Game #123: 碰碰激光车 (Targ 1980 / Exidy)
// 街机历史上开创性的网格街道追逐射击游戏：
// 9x9街区交叉路口高速机动、定向激光炮击破走私车、狂暴变身Spectar黄色突击领航车、氮气紧急加速冲刺。

class Game123Targ {
public:
    static constexpr uint8_t GAME_ID = 123;
    static constexpr const char* NAME = "碰碰激光车";
    static constexpr const char* ENGLISH_NAME = "Targ";
    static constexpr uint16_t RELEASE_YEAR = 1980;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_DYING = 1;
    static constexpr uint8_t STATE_SECTOR_CLEAR = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int MAX_ENEMIES = 5;

    struct EnemyCar {
        float x;
        float y;
        int dir_x;
        int dir_y;
        bool is_spectar;
        bool active;
    };

    struct LaserBeam {
        float x;
        float y;
        int dir_x;
        int dir_y;
        bool active;
    };

    Game123Targ();
    ~Game123Targ() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetEnemiesRemaining() const { return enemies_remaining_; }
    uint8_t GetSector() const { return sector_; }

private:
    void InitSector();
    void UpdatePlayer(float dt, uint16_t buttons);
    void UpdateLaser(float dt);
    void UpdateEnemies(float dt);
    void CheckCollisions();
    void SpawnEnemy();
    bool IsIntersection(float x, float y, float tol = 0.25f);

    uint8_t state_;
    float state_timer_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t sector_;
    uint8_t enemies_remaining_;

    // Player car
    float px_;
    float py_;
    int p_dir_x_;
    int p_dir_y_;
    int next_dir_x_;
    int next_dir_y_;
    float turbo_timer_;
    float turbo_cooldown_;

    // Laser
    LaserBeam laser_;

    // Enemies
    EnemyCar enemies_[MAX_ENEMIES];
    float spawn_timer_;
};

} // namespace arcade
