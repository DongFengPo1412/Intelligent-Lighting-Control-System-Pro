#pragma once

#include <cstdint>
#include "esp_timer.h"

namespace arcade {

// Game #143: 翻转方块 (Plotting / Flipull 1989 / Taito)
// 街机历史上最经典的横向投掷置换消解与重力沉降益智消除游戏：
// 升降台垂直滑轨对准目标行、按键A水平投掷手牌方块撞击同色消除并置换异色手牌、
// 按键B发射全消彩虹万能弹、重力级联崩落与限时清消达成通关。

class Game143Plotting {
public:
    static constexpr uint8_t GAME_ID = 143;
    static constexpr const char* NAME = "翻转方块";
    static constexpr const char* ENGLISH_NAME = "Plotting";
    static constexpr uint16_t RELEASE_YEAR = 1989;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_NO_MOVES = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr uint8_t COLOR_RED = 1;
    static constexpr uint8_t COLOR_BLUE = 2;
    static constexpr uint8_t COLOR_GREEN = 3;
    static constexpr uint8_t COLOR_YELLOW = 4;

    struct Projectile {
        float x;
        float y;
        uint8_t color;
        bool is_wildcard;
        bool active;
    };

    Game143Plotting();
    ~Game143Plotting() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetLevel() const { return level_; }
    uint16_t GetBlocksCleared() const { return blocks_cleared_; }

private:
    void InitLevel();
    void ApplyGravity();

    uint8_t state_;
    float state_timer_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t level_;

    float time_left_;
    uint16_t blocks_cleared_;
    uint16_t target_blocks_;

    float py_;
    uint8_t hand_block_;
    uint8_t wildcards_left_;

    Projectile projectile_;
    uint8_t board_[16][16];
};

} // namespace arcade

