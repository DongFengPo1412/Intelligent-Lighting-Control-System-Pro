#pragma once

#include <cstdint>

namespace arcade {

// Game #177: 深水炸弹 (Depthcharge - 1977 / Gremlin & Sega)
// 水面驱逐舰左右巡航、左右双舷深水炸弹抛投下沉爆破、
// 三层潜深潜艇伏击与规避上浮鱼雷水雷。

class Game177Depthcharge {
public:
    static constexpr uint8_t GAME_ID = 177;
    static constexpr const char* NAME = "深水炸弹";
    static constexpr const char* ENGLISH_NAME = "Depthcharge";
    static constexpr uint16_t RELEASE_YEAR = 1977;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_SHIP_SUNK = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int NUM_SUBS = 3;
    static constexpr int MAX_CHARGES = 4;
    static constexpr int MAX_TORPEDOES = 4;

    struct Submarine {
        int8_t id;
        float x;
        float y;
        float vx;
        uint8_t tier;
        bool alive;
        float reload;
    };

    struct DepthCharge {
        float x;
        float y;
        float vy;
        bool active;
    };

    struct Torpedo {
        float x;
        float y;
        float vy;
        bool active;
    };

    Game177Depthcharge();
    ~Game177Depthcharge() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetStage() const { return stage_; }

    float GetPx() const { return px_; }
    uint8_t GetSubsAlive() const;

private:
    uint8_t state_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t stage_;
    float state_timer_;

    float px_;
    float py_;
    float speed_;

    Submarine subs_[NUM_SUBS];
    DepthCharge charges_[MAX_CHARGES];
    Torpedo torpedoes_[MAX_TORPEDOES];

    void InitStage();
    void CheckStageClear();
};

} // namespace arcade
