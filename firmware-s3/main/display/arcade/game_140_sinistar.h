#pragma once

#include <cstdint>
#include "esp_timer.h"

namespace arcade {

// Game #140: 巨脸毁灭者 (Sinistar 1983 / Williams Electronics)
// 街机历史上最震撼的星际采矿萃取晶石与反击狂暴机械巨脸的传奇射击游戏：
// 自由惯性漂移星域、轰击小行星开采能量晶石合成为西尼追踪炸弹、
// 拦截偷运晶石组装魔头的工蜂战机、发射西尼炸弹引爆巨型咆哮魔头“西尼星君”。

class Game140Sinistar {
public:
    static constexpr uint8_t GAME_ID = 140;
    static constexpr const char* NAME = "巨脸毁灭者";
    static constexpr const char* ENGLISH_NAME = "Sinistar";
    static constexpr uint16_t RELEASE_YEAR = 1983;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_SHIP_DEVOURED = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int MAX_BULLETS = 3;
    static constexpr int MAX_BOMBS = 2;
    static constexpr int MAX_CRYSTALS = 5;
    static constexpr int NUM_ASTEROIDS = 4;
    static constexpr int NUM_WORKERS = 2;

    struct Bullet {
        float x;
        float y;
        float vx;
        float vy;
        bool active;
    };

    struct Asteroid {
        float x;
        float y;
        int8_t hp;
    };

    struct Crystal {
        float x;
        float y;
        bool active;
    };

    struct Worker {
        float x;
        float y;
        float vx;
        float vy;
        bool has_crystal;
        bool alive;
        float respawn_timer;
    };

    Game140Sinistar();
    ~Game140Sinistar() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetLevel() const { return level_; }
    uint8_t GetSinibombs() const { return sinibombs_; }
    bool IsSinistarAlive() const { return sinistar_alive_; }

private:
    void InitLevel();

    uint8_t state_;
    float state_timer_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t level_;

    float px_;
    float py_;
    float vx_;
    float vy_;
    float angle_;
    uint8_t sinibombs_;

    Bullet bullets_[MAX_BULLETS];
    Bullet active_bombs_[MAX_BOMBS];
    Asteroid asteroids_[NUM_ASTEROIDS];
    Crystal crystals_[MAX_CRYSTALS];
    Worker workers_[NUM_WORKERS];

    bool sinistar_alive_;
    uint8_t sinistar_pieces_;
    int8_t sinistar_hp_;
    float sinistar_x_;
    float sinistar_y_;
};

} // namespace arcade
