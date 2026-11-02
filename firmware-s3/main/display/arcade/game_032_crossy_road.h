#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game032CrossyRoad : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_DEAD = 2;

    static constexpr int NUM_LANES = 24;
    static constexpr int MAX_OBSTACLES = 32;

    enum LaneType : uint8_t {
        LANE_GRASS = 0,
        LANE_ROAD = 1,
        LANE_RIVER = 2,
        LANE_RAIL = 3,
    };

    struct Lane {
        LaneType type;
        int world_y; // 绝对垂直世界坐标
        float speed; // 负数向左，正数向右
        float spawn_timer;
        float spawn_interval;
        float train_timer; // 仅用于铁路：倒计时触发火车
        bool train_warning;
        bool train_passing;
        float train_x;
    };

    struct Obstacle {
        bool active;
        int lane_idx;
        float x;
        float length;
        bool is_log; // true: 浮木(安全平台), false: 汽车(致命障碍)
    };

    Game032CrossyRoad();
    ~Game032CrossyRoad() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Crossy Road (2014)"; }
    uint8_t GetControlScheme() const override { return CTRL_DPAD_4WAY; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    int GetMaxDistance() const { return max_distance_; }
    float GetIdleTimer() const { return idle_timer_; }

    float GetPlayerX() const { return player_x_; }
    int GetPlayerWorldY() const { return player_world_y_; }

    void SetPlayerPos(float x, int wy) { player_x_ = x; player_world_y_ = wy; }
    void SetState(uint8_t s) { state_ = s; }
    void TriggerEagleStrike();

private:
    void InitWorld();
    void GenerateLane(int lane_idx, int world_y);
    void UpdateLanesAndObstacles(float dt);
    void CheckEagle(float dt);
    void CheckCollisions();

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;
    int max_distance_;

    float player_x_;
    int player_world_y_; // 世界坐标：越大越往上
    int camera_world_y_; // 摄像机底部对应的世界坐标
    float idle_timer_;   // 停留超时老鹰计时
    bool eagle_striking_;
    float eagle_y_;      // 老鹰垂直俯冲位置

    Lane lanes_[NUM_LANES];
    Obstacle obstacles_[MAX_OBSTACLES];
};

} // namespace arcade
