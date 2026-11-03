#pragma once

#include <cstdint>

namespace arcade {

// Game #179: 圣铠传说 (Gauntlet - 1985 / Atari Games & Ed Logg)
// 地牢魔物巢穴定点摧毁、钥匙开锁迷宫拓扑、
// 生命流逝捡拾食物续命与全屏魔法药水清场。

class Game179Gauntlet {
public:
    static constexpr uint8_t GAME_ID = 179;
    static constexpr const char* NAME = "圣铠传说";
    static constexpr const char* ENGLISH_NAME = "Gauntlet";
    static constexpr uint16_t RELEASE_YEAR = 1985;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_WARRIOR_DIED = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int MAX_AXES = 2;
    static constexpr int MAX_PICKUPS = 8;
    static constexpr int MAX_GENERATORS = 4;
    static constexpr int MAX_MONSTERS = 8;

    struct Projectile {
        float x;
        float y;
        float vx;
        float vy;
        bool active;
    };

    struct Pickup {
        int8_t x;
        int8_t y;
        uint8_t type; // 0: food, 1: key, 2: potion
        bool active;
    };

    struct Generator {
        int8_t x;
        int8_t y;
        int8_t hp;
        float timer;
    };

    struct Monster {
        float x;
        float y;
        float speed;
        bool alive;
    };

    Game179Gauntlet();
    ~Game179Gauntlet() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    float GetHealth() const { return health_; }
    uint8_t GetStage() const { return stage_; }

    float GetPx() const { return px_; }
    float GetPy() const { return py_; }
    uint8_t GetKeysCount() const { return keys_count_; }
    uint8_t GetPotionsCount() const { return potions_count_; }

private:
    uint8_t state_;
    uint32_t score_;
    float health_;
    uint8_t lives_;
    uint8_t stage_;
    float state_timer_;

    float px_;
    float py_;
    float facing_x_;
    float facing_y_;
    float speed_;

    uint8_t keys_count_;
    uint8_t potions_count_;

    uint8_t grid_[16][16]; // 0: floor, 1: wall, 2: door, 3: exit

    Projectile axes_[MAX_AXES];
    Pickup pickups_[MAX_PICKUPS];
    Generator generators_[MAX_GENERATORS];
    Monster monsters_[MAX_MONSTERS];

    void InitStage();
};

} // namespace arcade

