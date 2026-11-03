#pragma once

#include <cstdint>

namespace arcade {

// Game #190: 破坏大奖赛 (Demolition Derby - 1984 / Bally Midway)
// 泥地封闭竞技场战车物理冲撞、倒车重击护甲保全水箱、
// 定点侧翼T-Bone毁灭撞击与残骸生存淘汰。

class Game190DemolitionDerby {
public:
    static constexpr uint8_t GAME_ID = 190;
    static constexpr const char* NAME = "破坏大奖赛";
    static constexpr const char* ENGLISH_NAME = "Demolition Derby";
    static constexpr uint16_t RELEASE_YEAR = 1984;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_CAR_WRECKED = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int MAX_RIVALS = 3;

    struct Rival {
        float x;
        float y;
        float angle;
        float vx;
        float vy;
        float speed;
        float hp;
        bool alive;
        uint8_t r;
        uint8_t g;
        uint8_t b;
    };

    Game190DemolitionDerby();
    ~Game190DemolitionDerby() = default;

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
    float GetHp() const { return hp_; }
    float GetSpeed() const { return speed_; }

private:
    void InitStage();

    uint8_t state_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t stage_;
    float state_timer_;

    // Player Car
    float px_;
    float py_;
    float angle_;
    float vx_;
    float vy_;
    float speed_;
    float hp_;

    Rival rivals_[MAX_RIVALS];
};

} // namespace arcade
