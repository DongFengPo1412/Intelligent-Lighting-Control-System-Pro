#pragma once

#include <cstdint>

namespace arcade {

// Game #164: 机器人大战2084 (Robotron: 2084 - 1982 / Vid Kidz & Williams)
// 街机历史上双摇杆竞技场全向射击鼻祖与开山丰碑：
// 搜救人类克隆家族（玛米、达迪、麦基）、迎战无敌浩克巨怪推土机碾压、
// 激光全向击退与清屏电磁EMP脉冲歼灭机器狂潮。

class Game164Robotron {
public:
    static constexpr uint8_t GAME_ID = 164;
    static constexpr const char* NAME = "机器人大战2084";
    static constexpr const char* ENGLISH_NAME = "Robotron: 2084";
    static constexpr uint16_t RELEASE_YEAR = 1982;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_WAVE_CLEAR = 1;
    static constexpr uint8_t STATE_PLAYER_DIED = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int NUM_HUMANS = 3;
    static constexpr int NUM_HULKS = 2;
    static constexpr int MAX_GRUNTS = 12;
    static constexpr int MAX_LASERS = 4;

    struct Human {
        float x;
        float y;
        float vx;
        float vy;
        bool alive;
        bool rescued;
    };

    struct Hulk {
        float x;
        float y;
        float vx;
        float vy;
    };

    struct Grunt {
        float x;
        float y;
        float speed;
        bool alive;
    };

    struct Laser {
        float x;
        float y;
        float vx;
        float vy;
        float life;
        bool active;
    };

    Game164Robotron();
    ~Game164Robotron() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetWave() const { return wave_; }
    uint8_t GetEmpCharges() const { return emp_charges_; }

private:
    uint8_t state_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t wave_;
    float state_timer_;

    float px_;
    float py_;
    float facing_dx_;
    float facing_dy_;
    float speed_;
    float fire_cooldown_;
    uint8_t emp_charges_;

    Human humans_[NUM_HUMANS];
    Hulk hulks_[NUM_HULKS];
    Grunt grunts_[MAX_GRUNTS];
    Laser lasers_[MAX_LASERS];
    uint8_t total_grunts_;

    void InitWave();
    void FireLaser();
    void TriggerEmp();
};

} // namespace arcade

