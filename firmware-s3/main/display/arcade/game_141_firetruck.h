#pragma once

#include <cstdint>
#include "esp_timer.h"

namespace arcade {

// Game #141: 消防云梯车 (Fire Truck 1978 / Atari)
// 街机历史上第一部铰接式长轴消防挂车物理转向与急速出警模拟驾驶游戏：
// 车头牵引转向、后桥舵手铰链尾部摆荡惯性模拟、按键A/B联动后舵纠偏防甩尾擦碰、
// 穿越窄道油渍急弯赶赴火场救援。

class Game141FireTruck {
public:
    static constexpr uint8_t GAME_ID = 141;
    static constexpr const char* NAME = "消防云梯车";
    static constexpr const char* ENGLISH_NAME = "Fire Truck";
    static constexpr uint16_t RELEASE_YEAR = 1978;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_CRASH = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int NUM_OBSTACLES = 4;

    struct Obstacle {
        float x;
        float y;
        uint8_t type; // 0: car, 1: oil
        bool alive;
    };

    Game141FireTruck();
    ~Game141FireTruck() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetLevel() const { return level_; }
    float GetDistance() const { return distance_; }
    float GetHitchAngle() const { return hitch_angle_; }

private:
    void InitLevel();
    void InitRoad();
    void Crash();

    uint8_t state_;
    float state_timer_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t level_;

    float time_left_;
    float distance_;
    float target_distance_;
    float speed_;

    float cx_;
    float cy_;
    float cab_vx_;

    float tx_;
    float ty_;
    float hitch_angle_;

    float road_center_[16];
    float road_width_;

    Obstacle obstacles_[NUM_OBSTACLES];
};

} // namespace arcade

