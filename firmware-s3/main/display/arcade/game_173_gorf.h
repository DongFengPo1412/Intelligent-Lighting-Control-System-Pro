#pragma once

#include <cstdint>

namespace arcade {

// Game #173: 高尔夫太空战 (Gorf - 1981 / Bally Midway & Dave Nutting)
// 三阶段连环战役推进：激光护航突围、空间漩涡弹射、
// 母舰力场凿孔穿刺核心反应堆爆破。

class Game173Gorf {
public:
    static constexpr uint8_t GAME_ID = 173;
    static constexpr const char* NAME = "高尔夫太空战";
    static constexpr const char* ENGLISH_NAME = "Gorf";
    static constexpr uint16_t RELEASE_YEAR = 1981;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_PHASE_TRANSITION = 1;
    static constexpr uint8_t STATE_FLAGSHIP_EXPLODING = 2;
    static constexpr uint8_t STATE_PLAYER_DIED = 3;
    static constexpr uint8_t STATE_GAME_OVER = 4;

    static constexpr uint8_t PHASE_LASER_ATTACK = 0;
    static constexpr uint8_t PHASE_SPACE_WARP = 1;
    static constexpr uint8_t PHASE_FLAGSHIP_CORE = 2;

    static constexpr int NUM_ESCORTS = 4;
    static constexpr int NUM_WARP_SHIPS = 6;
    static constexpr int MAX_BOMBS = 3;

    struct Escort {
        float x;
        float y;
        float vx;
        bool alive;
        float laser_timer;
        float firing_beam;
    };

    struct WarpShip {
        float angle;
        float radius;
        float speed;
        bool alive;
    };

    struct Bomb {
        float x;
        float y;
        bool active;
    };

    Game173Gorf();
    ~Game173Gorf() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetCycle() const { return cycle_; }
    uint8_t GetPhase() const { return phase_; }

    float GetPx() const { return px_; }
    float GetPy() const { return py_; }
    uint8_t GetShieldBits() const { return shield_bits_; }

private:
    uint8_t state_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t cycle_;
    uint8_t phase_;
    float state_timer_;

    float px_;
    float py_;
    bool laser_active_;
    float lx_;
    float ly_;

    Escort escorts_[NUM_ESCORTS];
    WarpShip warp_ships_[NUM_WARP_SHIPS];
    Bomb bombs_[MAX_BOMBS];

    uint8_t shield_bits_;
    int8_t flagship_core_hp_;
    float flagship_x_;
    float flagship_dir_;

    void InitPhase();
    void CheckLaserHit();
    void UpdateLaserAttack(float dt);
    void UpdateSpaceWarp(float dt);
    void UpdateFlagship(float dt);
    void KillPlayer();
};

} // namespace arcade
