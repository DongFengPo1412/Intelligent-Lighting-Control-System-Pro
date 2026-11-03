#pragma once

#include <cstdint>
#include "esp_timer.h"

namespace arcade {

// Game #134: 动物园管理员 (Zoo Keeper 1982 / Taito)
// 街机历史上最经典的外环修墙筑牢与跳跃避兽益智动作游戏：
// 外环跑道环绕兽笼、按键A涂砌砖墙封堵缺口、按键B跳跃闪避逃窜猛兽、获取捕捉网回捕狮猴。

class Game134ZooKeeper {
public:
    static constexpr uint8_t GAME_ID = 134;
    static constexpr const char* NAME = "动物园管理员";
    static constexpr const char* ENGLISH_NAME = "Zoo Keeper";
    static constexpr uint16_t RELEASE_YEAR = 1982;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_LEVEL_CLEAR = 1;
    static constexpr uint8_t STATE_CAUGHT = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int NUM_ANIMALS = 4;
    static constexpr int WALL_MIN = 2;
    static constexpr int WALL_MAX = 13;

    struct Animal {
        float x;
        float y;
        float vx;
        float vy;
        uint8_t type;     // 0: Lion, 1: Gorilla
        bool escaped;
        float track_pos;
        float track_dir;
    };

    Game134ZooKeeper();
    ~Game134ZooKeeper() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetLevel() const { return level_; }

private:
    void InitLevel();
    void InitWalls();
    void TrackPosToXY(float pos, float& x, float& y);
    void GetAdjacentWallCoord(float px, float py, int& wx, int& wy);

    uint8_t state_;
    float state_timer_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t level_;
    float time_left_;

    float track_pos_;
    float px_;
    float py_;
    bool is_jumping_;
    float jump_timer_;
    float net_timer_;

    bool walls_[16][16];
    Animal animals_[NUM_ANIMALS];

    bool net_spawned_;
    float net_pos_;
    float net_respawn_timer_;
};

} // namespace arcade
