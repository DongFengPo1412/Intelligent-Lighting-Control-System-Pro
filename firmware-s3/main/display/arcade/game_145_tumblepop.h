#pragma once

#include <cstdint>
#include "esp_timer.h"

namespace arcade {

// Game #145: 吸尘器大冒险 (Tumblepop 1991 / Data East)
// 街机历史上最著名的人气吸入式平台动作消除游戏：
// 按键A吸尘器强力抽吸幽灵怪兽打包收纳进背包、
// 按键B喷射巨型滚动怪兽肉球横向穿梭墙壁反弹、如保龄球般连锁碾碎全图小怪。

class Game145Tumblepop {
public:
    static constexpr uint8_t GAME_ID = 145;
    static constexpr const char* NAME = "吸尘器大冒险";
    static constexpr const char* ENGLISH_NAME = "Tumblepop";
    static constexpr uint16_t RELEASE_YEAR = 1991;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_PLAYER_DOWN = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int NUM_ENEMIES = 4;
    static constexpr int MAX_PACK = 4;

    struct Enemy {
        float x;
        float y;
        float vx;
        uint8_t type;
        bool being_sucked;
        bool alive;
    };

    struct RollingBall {
        float x;
        float y;
        float vx;
        int8_t bounces;
        uint8_t power;
        bool active;
    };

    Game145Tumblepop();
    ~Game145Tumblepop() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetLevel() const { return level_; }
    uint8_t GetPackCount() const { return monsters_in_pack_; }

private:
    void InitLevel();
    void LoseLife();

    uint8_t state_;
    float state_timer_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t level_;

    float px_;
    float py_;
    float pvy_;
    int8_t facing_;
    bool is_jumping_;

    bool is_vacuuming_;
    uint8_t monsters_in_pack_;

    RollingBall rolling_ball_;
    Enemy enemies_[NUM_ENEMIES];
};

} // namespace arcade
