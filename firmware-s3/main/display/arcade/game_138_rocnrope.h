#pragma once

#include <cstdint>
#include "esp_timer.h"

namespace arcade {

// Game #138: 索道探险家 (Roc'n Rope 1983 / Konami)
// 街机历史上第一部融合鱼叉索道搭桥攀登与强光手电眩晕的悬崖探险动作游戏：
// 按键A发射鱼叉射锚空中岩壁搭设斜拉缆绳、沿悬挂索道攀爬登高跨越高崖、
// 按键B强光手电眩晕史前巨兽与穴居人、登顶绝壁朝圣神圣金鸟。

class Game138RocnRope {
public:
    static constexpr uint8_t GAME_ID = 138;
    static constexpr const char* NAME = "索道探险家";
    static constexpr const char* ENGLISH_NAME = "Roc'n Rope";
    static constexpr uint16_t RELEASE_YEAR = 1983;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_FALLEN = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int NUM_LEDGES = 6;
    static constexpr int NUM_ENEMIES = 3;

    struct Ledge {
        float y;
        float x1;
        float x2;
    };

    struct Enemy {
        float x;
        float y;
        float vx;
        float min_x;
        float max_x;
        float stun_timer;
        bool alive;
    };

    Game138RocnRope();
    ~Game138RocnRope() = default;

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
    void LoseLife();
    bool GetCurrentLedge(float px, float py, Ledge& out_ledge);

    uint8_t state_;
    float state_timer_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t level_;

    float px_;
    float py_;
    int8_t facing_;

    bool rope_active_;
    float rope_start_x_;
    float rope_start_y_;
    float rope_end_x_;
    float rope_end_y_;
    bool on_rope_;
    float rope_t_;

    float flashlight_timer_;

    Ledge ledges_[NUM_LEDGES];
    Enemy enemies_[NUM_ENEMIES];
};

} // namespace arcade
