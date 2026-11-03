#pragma once

#include <cstdint>

namespace arcade {

// Game #182: 魔法水滴 (Magical Drop - 1995 / Data East)
// 小丑底线穿梭同色多球瞬吸入腹、向上弹射列置换重组、
// 三连消除与磁力级联连锁爆破。

class Game182MagicalDrop {
public:
    static constexpr uint8_t GAME_ID = 182;
    static constexpr const char* NAME = "魔法水滴";
    static constexpr const char* ENGLISH_NAME = "Magical Drop";
    static constexpr uint16_t RELEASE_YEAR = 1995;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_FLOOR_CRUSHED = 2;
    static constexpr uint8_t STATE_GAME_OVER = 3;

    static constexpr uint8_t COLOR_NONE = 0;
    static constexpr uint8_t COLOR_RED = 1;
    static constexpr uint8_t COLOR_BLUE = 2;
    static constexpr uint8_t COLOR_GREEN = 3;
    static constexpr uint8_t COLOR_YELLOW = 4;

    Game182MagicalDrop();
    ~Game182MagicalDrop() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetLives() const { return lives_; }
    uint8_t GetStage() const { return stage_; }

    int8_t GetCol() const { return col_; }
    uint8_t GetHeldColor() const { return held_color_; }
    uint8_t GetHeldCount() const { return held_count_; }
    uint16_t GetBubblesCleared() const { return bubbles_cleared_; }

private:
    uint8_t state_;
    uint32_t score_;
    uint8_t lives_;
    uint8_t stage_;
    float state_timer_;

    int8_t col_;
    uint8_t held_color_;
    uint8_t held_count_;

    uint8_t grid_[16][16];
    float drop_timer_;
    uint16_t cleared_target_;
    uint16_t bubbles_cleared_;

    void InitStage();
    void PullBubbles(int x);
    void FlingBubbles(int x);
    void CheckColumnMatches(int x);
    void DropCeilingRow();
};

} // namespace arcade

