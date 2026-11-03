#pragma once

#include <cstdint>

namespace arcade {

// Game #184: 战场之狼 (Commando - 1985 / Capcom & Tokuro Fujiwara)
// 八向冲锋枪倾泻射击、高弧度抛投破片手榴弹轰炸掩体、
// 营救战俘与强攻敌军要塞铁闸。

class Game184Commando {
public:
    static constexpr uint8_t GAME_ID = 184;
    static constexpr const char* NAME = "战场之狼";
    static constexpr const char* ENGLISH_NAME = "Commando";
    static constexpr uint16_t RELEASE_YEAR = 1985;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_JOE_KILLED = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int MAX_BULLETS = 4;
    static constexpr int MAX_GRENADES = 2;
    static constexpr int MAX_ENEMIES = 4;
    static constexpr int MAX_POWS = 2;

    struct Bullet {
        float x;
        float y;
        float vx;
        float vy;
        bool active;
    };

    struct Grenade {
        float x;
        float y;
        float tx;
        float ty;
        float timer;
        bool active;
    };

    struct Enemy {
        float x;
        float y;
        float vx;
        float vy;
        uint8_t type; // 0: infantry, 1: bunker, 2: officer
        int8_t hp;
        bool alive;
    };

    struct POW {
        float x;
        float y;
        bool rescued;
        bool active;
    };

    Game184Commando();
    ~Game184Commando() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetStage() const { return stage_; }

    float GetPx() const { return px_; }
    float GetPy() const { return py_; }
    uint8_t GetGrenades() const { return grenades_; }
    float GetDistance() const { return distance_; }

private:
    uint8_t state_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t stage_;
    float state_timer_;

    float px_;
    float py_;
    float facing_x_;
    float facing_y_;
    float speed_;
    uint8_t grenades_;

    float distance_;
    float target_distance_;
    bool gate_breached_;

    Bullet bullets_[MAX_BULLETS];
    Grenade grenades_[MAX_GRENADES];
    Enemy enemies_[MAX_ENEMIES];
    POW pows_[MAX_POWS];

    void InitStage();
    void SpawnWave();
};

} // namespace arcade

