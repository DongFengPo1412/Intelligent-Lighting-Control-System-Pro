#pragma once

#include <cstdint>

namespace arcade {

// Game #188: 钱币交换机 (Money Puzzle Exchanger - 1997 / Face & Neo Geo MVS)
// 魔法硬币面值合并进位（5枚1分变5分、2枚5分变10分）、双向吸吐硬币重组与防止硬币压线。

class Game188MoneyPuzzleExchanger {
public:
    static constexpr uint8_t GAME_ID = 188;
    static constexpr const char* NAME = "钱币交换机";
    static constexpr const char* ENGLISH_NAME = "Money Puzzle Exchanger";
    static constexpr uint16_t RELEASE_YEAR = 1997;
    static constexpr uint8_t CONTROL_TYPE = 1; // CTRL_ARCADE_AB

    static constexpr uint8_t STATE_PLAYING = 0;
    static constexpr uint8_t STATE_STAGE_CLEAR = 1;
    static constexpr uint8_t STATE_GAME_OVER = 2;

    static constexpr int COLS = 7;
    static constexpr int MAX_ROWS = 14;

    Game188MoneyPuzzleExchanger();
    ~Game188MoneyPuzzleExchanger() = default;

    void Init();
    void Reset();
    void Update(float dt, uint16_t buttons, uint16_t prev_buttons);
    void Render(uint8_t* fb);

    uint8_t GetState() const { return state_; }
    uint32_t GetScore() const { return score_; }
    uint8_t GetStage() const { return stage_; }

    uint8_t GetCursorCol() const { return cursor_col_; }
    uint16_t GetHeldDenom() const { return held_denom_; }
    uint8_t GetHeldCount() const { return held_count_; }
    int GetColHeight(int col) const {
        return (col >= 0 && col < COLS) ? col_len_[col] : 0;
    }

private:
    void InitStage();
    void PushCeilingRow();
    bool ResolveExchanges();

    uint8_t state_;
    uint32_t score_;
    uint8_t stage_;
    float state_timer_;

    // Grid: grid_[col][row]
    uint16_t grid_[COLS][MAX_ROWS];
    uint8_t col_len_[COLS];

    uint8_t cursor_col_;
    float cursor_cooldown_;

    uint16_t held_denom_;
    uint8_t held_count_;

    float drop_timer_;
    float max_drop_timer_;
};

} // namespace arcade
