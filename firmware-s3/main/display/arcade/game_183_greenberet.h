#pragma once

#include <cstdint>

namespace arcade {

// Game #183: 绿色兵团 (Green Beret / Rush'n Attack - 1985 / Konami)
// 特种兵近身快刀突刺、击杀红衣军官缴获火箭筒、
// 卧倒伏地闪避流弹与摧毁导弹发射井。

class Game183GreenBeret {
public:
    static constexpr uint8_t GAME_ID = 183;
    static constexpr const char* NAME = "绿色兵团";
    static constexpr const char* ENGLISH_NAME = "Green Beret";
    static constexpr uint16_t RELEASE_YEAR = 1985;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_SOLDIER_KILLED = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int MAX_ENEMIES = 4;
    static constexpr int MAX_PARATROOPERS = 2;
    static constexpr int MAX_ROCKETS = 2;

    struct Enemy {
        float x;
        float y;
        float vx;
        bool is_officer;
        bool alive;
    };

    struct Paratrooper {
        float x;
        float y;
        float vy;
        bool alive;
    };

    struct Rocket {
        float x;
        float y;
        float vx;
        bool active;
    };

    Game183GreenBeret();
    ~Game183GreenBeret() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetStage() const { return stage_; }

    float GetPx() const { return px_; }
    float GetDistance() const { return distance_; }
    uint8_t GetRpgAmmo() const { return rpg_ammo_; }
    bool IsProne() const { return is_prone_; }
    int8_t GetSiloHp() const { return silo_hp_; }

private:
    uint8_t state_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t stage_;
    float state_timer_;

    float px_;
    float py_;
    int8_t facing_;
    float speed_;
    bool is_prone_;
    float knife_timer_;
    uint8_t rpg_ammo_;

    float distance_;
    float target_distance_;
    int8_t silo_hp_;

    Enemy enemies_[MAX_ENEMIES];
    Paratrooper paratroopers_[MAX_PARATROOPERS];
    Rocket rockets_[MAX_ROCKETS];

    void InitStage();
    void SpawnEnemyWave();
};

} // namespace arcade
