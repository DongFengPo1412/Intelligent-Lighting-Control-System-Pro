#pragma once

#include <cstdint>

namespace arcade {

// Game #187: 侵略者归来 (Return of the Invaders - 1985 / Taito & UPL)
// 外星侵略者细胞分裂增殖、弧形回旋光镖双程贯通、引力光束母舰核爆与集束能量反攻。

class Game187ReturnOfTheInvaders {
public:
    static constexpr uint8_t GAME_ID = 187;
    static constexpr const char* NAME = "侵略者归来";
    static constexpr const char* ENGLISH_NAME = "Return of the Invaders";
    static constexpr uint16_t RELEASE_YEAR = 1985;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_SHIP_DESTROYED = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int MAX_LASERS = 3;
    static constexpr int MAX_ALIENS = 16;
    static constexpr int MAX_BOMBS = 4;

    struct Laser {
        float x;
        float y;
        float vy;
        bool active;
    };

    struct Boomerang {
        float x;
        float y;
        float vx;
        float vy;
        uint8_t state; // 0: ascending, 1: returning
        bool active;
    };

    struct Alien {
        float x;
        float y;
        float vx;
        float vy;
        uint8_t type; // 0: normal, 1: splitter, 2: mini
        int8_t hp;
        bool alive;
    };

    struct Bomb {
        float x;
        float y;
        float vy;
        bool active;
    };

    Game187ReturnOfTheInvaders();
    ~Game187ReturnOfTheInvaders() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetStage() const { return stage_; }

    float GetPx() const { return px_; }
    bool IsBoomerangActive() const { return boomerang_.active; }
    bool IsUfoActive() const { return ufo_active_; }

private:
    void InitStage();
    void SplitAlien(float x, float y);

    uint8_t state_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t stage_;
    float state_timer_;

    // Player Ship
    float px_;
    float py_;
    float speed_;

    // Weapons
    Laser lasers_[MAX_LASERS];
    Boomerang boomerang_;

    // Aliens
    Alien aliens_[MAX_ALIENS];
    float alien_dir_;
    float bomb_timer_;
    Bomb bombs_[MAX_BOMBS];

    // Mothership UFO
    float ufo_x_;
    bool ufo_active_;
    float ufo_timer_;
};

} // namespace arcade

