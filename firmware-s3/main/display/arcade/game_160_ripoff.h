#pragma once

#include <cstdint>

namespace arcade {

// Game #160: 碰碰抢夺 / 燃料守卫 (Rip Off 1979 / Cinematronics & Tim Skelly)
// 街机历史上第一款协作守卫与敌机盗窃拖拽资源神作：
// 守卫中央基地4组高能燃料罐、拦截并击溃四向入侵企图挂索拖走燃料的太空海盗战车、
// 磁力抓钩收回散落燃料罐、抵御海盗掠夺狂潮。

class Game160RipOff {
public:
    static constexpr uint8_t GAME_ID = 160;
    static constexpr const char* NAME = "碰碰抢夺";
    static constexpr const char* ENGLISH_NAME = "Rip Off";
    static constexpr uint16_t RELEASE_YEAR = 1979;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_WAVE_CLEAR = 1;
    static constexpr uint8_t STATE_GAME_OVER = 2;

    static constexpr int NUM_CANISTERS = 4;
    static constexpr int MAX_BULLETS = 3;
    static constexpr int MAX_PIRATES = 2;
    static constexpr int MAX_EXPLOSIONS = 4;

    struct Canister {
        float x;
        float y;
        float home_x;
        float home_y;
        uint8_t status; // 0: at_base, 1: towed, 2: dropped, 3: stolen
        int8_t carrier_id;
    };

    struct Bullet {
        float x;
        float y;
        float vx;
        float vy;
        float life;
        bool active;
    };

    struct Pirate {
        int8_t id;
        float x;
        float y;
        float speed;
        int8_t towing_canister;
        bool alive;
    };

    struct Explosion {
        float x;
        float y;
        float timer;
        bool active;
    };

    Game160RipOff();
    ~Game160RipOff() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetWave() const { return wave_; }
    uint8_t GetRemainingFuel() const;

private:
    uint8_t state_;
    uint32_t score_;
    uint8_t wave_;

    float player_x_;
    float player_y_;
    float player_vx_;
    float player_vy_;
    float facing_dx_;
    float facing_dy_;
    bool player_alive_;
    float respawn_timer_;
    float fire_cooldown_;

    Canister canisters_[NUM_CANISTERS];
    Bullet bullets_[MAX_BULLETS];
    Pirate pirates_[MAX_PIRATES];
    Explosion explosions_[MAX_EXPLOSIONS];

    uint8_t pirates_killed_in_wave_;
    uint8_t pirates_needed_for_wave_;
    float spawn_timer_;
    int8_t next_pirate_id_;

    void FireBullet();
    void MagnetRecoverCanisters();
    void SpawnPirate();
    void AddExplosion(float x, float y, float duration);
};

} // namespace arcade

