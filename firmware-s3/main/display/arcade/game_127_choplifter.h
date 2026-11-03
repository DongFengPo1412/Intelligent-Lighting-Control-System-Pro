#pragma once

#include <cstdint>
#include "esp_timer.h"

namespace arcade {

// Game #127: 救难直升机 (Choplifter 1982 / Broderbund & Sega Arcade)
// 街机历史上最具传奇色彩的敌后人质营救飞行战斗模拟：
// 三向姿态切换(左/中俯视投弹/右)、轰碎敌军集中营牢房、平稳着陆登机撤离、规避高炮与防空喷气机、基地安全卸载。

class Game127Choplifter {
public:
    static constexpr uint8_t GAME_ID = 127;
    static constexpr const char* NAME = "救难直升机";
    static constexpr const char* ENGLISH_NAME = "Choplifter";
    static constexpr uint16_t RELEASE_YEAR = 1982;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_FLYING = 0;
    static constexpr uint8_t STATE_CHOPPER_DOWN = 1;
    static constexpr uint8_t STATE_MISSION_CLEAR = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr uint8_t FACING_LEFT = 0;
    static constexpr uint8_t FACING_FORWARD = 1; // Drops bombs downwards
    static constexpr uint8_t FACING_RIGHT = 2;

    static constexpr int MAX_HOSTAGES = 16;
    static constexpr int MAX_ONBOARD = 8;
    static constexpr int MAX_BULLETS = 4;
    static constexpr int MAX_ENEMY_JETS = 2;

    struct Hostage {
        float x;
        float y;
        uint8_t state; // 0: In Barracks, 1: Running, 2: Onboard, 3: Rescued, 4: KIA
    };

    struct Bullet {
        float x;
        float y;
        float vx;
        float vy;
        bool is_bomb;
        bool active;
    };

    struct EnemyJet {
        float x;
        float y;
        float vx;
        bool active;
    };

    Game127Choplifter();
    ~Game127Choplifter() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetOnboardCount() const { return onboard_count_; }
    uint8_t GetRescuedCount() const { return rescued_count_; }
    uint8_t GetFacing() const { return facing_; }

private:
    void InitMission();
    void UpdateChopper(float dt, uint16_t buttons, uint16_t prev_buttons);
    void UpdateHostages(float dt);
    void UpdateBullets(float dt);
    void UpdateEnemies(float dt);
    void CheckCollisions();

    uint8_t state_;
    float state_timer_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t mission_;

    // Helicopter
    float hx_;
    float hy_;
    float hvx_;
    float hvy_;
    uint8_t facing_;
    bool is_landed_;
    uint8_t onboard_count_;
    uint8_t rescued_count_;
    uint8_t kia_count_;

    // Barracks at x=10.0, y=13.0
    bool barracks_broken_;
    float barracks_hp_;

    // Hostages
    Hostage hostages_[MAX_HOSTAGES];

    // Weapons
    Bullet bullets_[MAX_BULLETS];

    // Enemy Jets
    EnemyJet jets_[MAX_ENEMY_JETS];
    float jet_spawn_timer_;

    // Enemy Ground Tank
    float tank_x_;
    float tank_vx_;
    bool tank_alive_;
};

} // namespace arcade
