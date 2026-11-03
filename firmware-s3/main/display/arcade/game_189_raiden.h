#pragma once

#include <cstdint>

namespace arcade {

// Game #189: 雷电 (Raiden - 1990 / Seibu Kaihatsu)
// 红蓝双色战术晶石主武切换（红散弹火神炮/蓝集中聚能光束）、
// 追踪导弹拦截与延时热核航弹全屏清场。

class Game189Raiden {
public:
    static constexpr uint8_t GAME_ID = 189;
    static constexpr const char* NAME = "雷电";
    static constexpr const char* ENGLISH_NAME = "Raiden";
    static constexpr uint16_t RELEASE_YEAR = 1990;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_SHIP_DESTROYED = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr uint8_t WEAPON_VULCAN = 0;
    static constexpr uint8_t WEAPON_LASER = 1;

    static constexpr int MAX_BULLETS = 6;
    static constexpr int MAX_ENEMIES = 5;
    static constexpr int MAX_ENEMY_BULLETS = 4;

    struct Bullet {
        float x;
        float y;
        float vx;
        float vy;
        bool is_laser;
        int8_t damage;
        bool active;
    };

    struct Bomb {
        float x;
        float y;
        float fuse;
        float radius;
        bool exploding;
        bool active;
    };

    struct Crystal {
        float x;
        float y;
        float vx;
        float vy;
        uint8_t color; // 0: red, 1: blue
        float swap_timer;
        bool active;
    };

    struct Enemy {
        float x;
        float y;
        float vx;
        float vy;
        uint8_t type; // 0: chopper, 1: tank, 2: boss
        int16_t hp;
        bool alive;
    };

    struct EnemyBullet {
        float x;
        float y;
        float vx;
        float vy;
        bool active;
    };

    Game189Raiden();
    ~Game189Raiden() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetStage() const { return stage_; }

    uint8_t GetWeaponType() const { return weapon_type_; }
    uint8_t GetBombs() const { return bombs_; }
    float GetPx() const { return px_; }
    float GetPy() const { return py_; }

private:
    void InitStage();

    uint8_t state_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t stage_;
    float state_timer_;

    // Fighter
    float px_;
    float py_;
    float speed_;
    uint8_t weapon_type_;
    uint8_t bombs_;

    Bullet bullets_[MAX_BULLETS];
    Bomb mega_bomb_;
    Crystal crystal_;

    Enemy enemies_[MAX_ENEMIES];
    EnemyBullet enemy_bullets_[MAX_ENEMY_BULLETS];
    float enemy_shoot_timer_;
};

} // namespace arcade
