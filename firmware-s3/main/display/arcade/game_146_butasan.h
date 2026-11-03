#pragma once

#include <cstdint>
#include "esp_timer.h"

namespace arcade {

// Game #146: 碰碰小猪 (Butasan 1987 / Jaleco)
// 街机历史上最经典的数字引信炸弹搬运投掷与滑行飞踢对战动作游戏：
// 竞技场散落多秒倒计时炸弹、按键A双手举起炸弹并定向抛投、
// 按键B滑铲飞踢地面炸弹产生直线滑行冲击、连锁爆风清屏歼灭敌方小猪。

class Game146Butasan {
public:
    static constexpr uint8_t GAME_ID = 146;
    static constexpr const char* NAME = "碰碰小猪";
    static constexpr const char* ENGLISH_NAME = "Butasan";
    static constexpr uint16_t RELEASE_YEAR = 1987;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_PIG_BLASTED = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr int MAX_BOMBS = 6;
    static constexpr int MAX_EXPLOSIONS = 15;
    static constexpr int NUM_ENEMIES = 3;

    struct Bomb {
        float x;
        float y;
        float fuse;
        uint8_t state; // 0: ground, 1: held, 2: flying, 3: sliding
        float vx;
        float vy;
        bool active;
    };

    struct Explosion {
        int8_t x;
        int8_t y;
        float timer;
    };

    struct Enemy {
        float x;
        float y;
        float vx;
        float vy;
        bool alive;
    };

    Game146Butasan();
    ~Game146Butasan() = default;

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
    void ExplodeBomb(float bx, float by);
    void LoseLife();

    uint8_t state_;
    float state_timer_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t level_;

    float px_;
    float py_;
    float facing_x_;
    float facing_y_;
    int8_t held_bomb_idx_;

    Bomb bombs_[MAX_BOMBS];
    Explosion explosions_[MAX_EXPLOSIONS];
    Enemy enemies_[NUM_ENEMIES];
};

} // namespace arcade
