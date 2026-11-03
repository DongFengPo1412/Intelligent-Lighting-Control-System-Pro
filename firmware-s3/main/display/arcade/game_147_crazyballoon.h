#pragma once

#include <cstdint>
#include <cmath>

namespace arcade {

// Game #147: 疯狂气球 (Crazy Balloon 1980 / Taito)
// 街机历史上首款谐振摆动物理穿梭与尖刺迷宫避险经典：
// 悬臂小车支撑浮空摆动气球无休止左右摆荡、按键A开启阻尼减摆进行缝隙微操、
// 按键B喷气突进逆转摆向、抗衡风道横向推挤偏航穿行通关。

class Game147CrazyBalloon {
public:
    static constexpr uint8_t GAME_ID = 147;
    static constexpr const char* NAME = "疯狂气球";
    static constexpr const char* ENGLISH_NAME = "Crazy Balloon";
    static constexpr uint16_t RELEASE_YEAR = 1980;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_BALLOON_POPPED = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int MAX_HAZARDS = 4;
    static constexpr int MAX_PARTICLES = 8;

    struct Hazard {
        float x;
        float y;
        float vx;
        float vy;
        float min_val;
        float max_val;
        bool horizontal;
    };

    struct Particle {
        float x;
        float y;
        float vx;
        float vy;
        float life;
    };

    Game147CrazyBalloon();
    ~Game147CrazyBalloon() = default;

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
    void PopBalloon();
    bool IsSpikeWall(int x, int y) const;

    uint8_t state_;
    float state_timer_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t level_;

    float cx_;
    float cy_;
    float swing_angle_;
    float swing_speed_;
    float swing_amp_;
    float arm_length_;

    float bx_;
    float by_;

    float gx_;
    float gy_;

    Hazard hazards_[MAX_HAZARDS];
    int num_hazards_;
    Particle particles_[MAX_PARTICLES];
    int num_particles_;
};

} // namespace arcade

