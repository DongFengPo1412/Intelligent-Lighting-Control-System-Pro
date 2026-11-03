#pragma once

#include <cstdint>

namespace arcade {

// Game #163: 异型特警 (Alien Syndrome - 1987 / Sega & Toru Nakayama)
// 街机科幻恐怖俯视角动作射击里程碑神作：
// 潜入异形生物母舰多舱室搜救被困战友蚕茧、拾取墙体武器舱升级高能穿透激光、
// 营救全员后触发全舰紧急自毁撤离倒计时警报、突破虫潮围剿赶赴逃生气闸。

class Game163AlienSyndrome {
public:
    static constexpr uint8_t GAME_ID = 163;
    static constexpr const char* NAME = "异型特警";
    static constexpr const char* ENGLISH_NAME = "Alien Syndrome";
    static constexpr uint16_t RELEASE_YEAR = 1987;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_EVACUATION = 1;
    static constexpr uint8_t STATE_MISSION_CLEAR = 2;
    static constexpr uint8_t STATE_PLAYER_DIED = 3;
    static constexpr uint8_t STATE_GAME_OVER = 4;

    static constexpr int NUM_COMRADES = 4;
    static constexpr int MAX_BULLETS = 6;
    static constexpr int MAX_ALIENS = 5;

    struct Comrade {
        float x;
        float y;
        bool rescued;
    };

    struct Bullet {
        float x;
        float y;
        float vx;
        float vy;
        float life;
        bool is_laser;
        bool active;
    };

    struct Alien {
        int8_t id;
        float x;
        float y;
        float speed;
        bool alive;
    };

    Game163AlienSyndrome();
    ~Game163AlienSyndrome() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetLevel() const { return level_; }
    uint8_t GetComradesRescued() const { return comrades_rescued_; }
    bool IsExitOpen() const { return exit_open_; }
    float GetEvacTimer() const { return evac_timer_; }

private:
    uint8_t state_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t level_;
    float state_timer_;

    float px_;
    float py_;
    float facing_dx_;
    float facing_dy_;
    float speed_;
    bool has_laser_;
    float fire_cooldown_;

    Comrade comrades_[NUM_COMRADES];
    uint8_t comrades_rescued_;

    float evac_timer_;
    bool exit_open_;
    float exit_x_;
    float exit_y_;

    float weapon_pod_x_;
    float weapon_pod_y_;
    bool weapon_pod_collected_;

    Bullet bullets_[MAX_BULLETS];
    Alien aliens_[MAX_ALIENS];
    float alien_spawn_timer_;

    void InitLevel();
    void FireWeapon();
};

} // namespace arcade
