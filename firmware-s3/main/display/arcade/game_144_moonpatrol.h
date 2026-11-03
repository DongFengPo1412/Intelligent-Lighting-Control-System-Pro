#pragma once

#include <cstdint>
#include "esp_timer.h"

namespace arcade {

// Game #144: 月球巡逻车 (Moon Patrol 1982 / Irem & Williams)
// 街机历史上第一部开创视差多层背景卷轴与双向同步火力月面越野的里程碑神作：
// 三轮月面车高速奔驰与液压避震跳跃跨越环形陨石坑、
// 按键A同步齐射前向碎石激光与垂直防空导弹、按键B大跳避障、猎杀空投飞碟冲刺分段检查站。

class Game144MoonPatrol {
public:
    static constexpr uint8_t GAME_ID = 144;
    static constexpr const char* NAME = "月球巡逻车";
    static constexpr const char* ENGLISH_NAME = "Moon Patrol";
    static constexpr uint16_t RELEASE_YEAR = 1982;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_BUGGY_CRASH = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr float GROUND_Y = 13.0f;
    static constexpr int MAX_LASERS = 2;
    static constexpr int MAX_MISSILES = 2;
    static constexpr int MAX_BOMBS = 3;
    static constexpr int NUM_HAZARDS = 6;
    static constexpr int NUM_UFOS = 2;

    struct Projectile {
        float x;
        float y;
        bool active;
    };

    struct Hazard {
        float x;
        uint8_t type; // 0: crater, 1: boulder, 2: mine
        float width;
        bool alive;
    };

    struct Ufo {
        float x;
        float y;
        float vx;
        float shoot_timer;
        bool alive;
        float respawn_timer;
    };

    struct Bomb {
        float x;
        float y;
        float vy;
        bool active;
    };

    Game144MoonPatrol();
    ~Game144MoonPatrol() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetLevel() const { return level_; }
    float GetDistance() const { return distance_; }
    char GetCheckpoint() const { return checkpoint_letter_; }

private:
    void InitLevel();
    void Crash();

    uint8_t state_;
    float state_timer_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t level_;

    float distance_;
    float target_distance_;
    char checkpoint_letter_;
    float speed_;

    float bx_;
    float by_;
    float bvy_;
    bool is_jumping_;

    Projectile forward_lasers_[MAX_LASERS];
    Projectile upward_missiles_[MAX_MISSILES];
    Hazard hazards_[NUM_HAZARDS];
    Ufo ufos_[NUM_UFOS];
    Bomb bombs_[MAX_BOMBS];
};

} // namespace arcade
