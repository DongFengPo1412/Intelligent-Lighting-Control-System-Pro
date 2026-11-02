#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>
#include <vector>

namespace arcade {

class Game083PuyoPuyo : public Cartridge {
public:
    Game083PuyoPuyo();
    ~Game083PuyoPuyo() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 83; }
    std::string GetName() const override { return "Puyo Puyo (1991)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_PLAYING = 0,
        STATE_CHAIN_RESOLVE = 1,
        STATE_GAME_OVER = 2
    };

    enum PuyoColor {
        PUYO_EMPTY = 0,
        PUYO_RED = 1,
        PUYO_GREEN = 2,
        PUYO_BLUE = 3,
        PUYO_YELLOW = 4,
        PUYO_GARBAGE = 5 // Ojama grey puyo
    };

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetChainCount() const { return max_chain_; }
    int GetCurrentChain() const { return current_chain_; }
    PuyoColor GetCell(int col, int row) const;
    int GetCurrentCol() const { return cur_col_; }

private:
    void SpawnPair();
    void DropPair();
    void RotatePair(int dir); // +1 cw, -1 ccw
    bool ApplyGravity();
    bool CheckMatches();
    void ClearBoard();

    GameState state_{STATE_PLAYING};
    float state_timer_{0.0f};
    float drop_timer_{0.0f};
    float drop_interval_{0.8f};

    int score_{0};
    int current_chain_{0};
    int max_chain_{0};

    // Matrix playing field: 6 columns x 14 rows (well width x=3..8 or x=4..9)
    static constexpr int COLS = 6;
    static constexpr int ROWS = 13;
    PuyoColor grid_[ROWS][COLS];

    // Current falling pair (main pivot + orbiting partner)
    int cur_col_{2};
    float cur_row_{0.0f};
    PuyoColor puyo_main_{PUYO_RED};
    PuyoColor puyo_sub_{PUYO_GREEN};
    int sub_offset_x_{0}; // 0 = above, 1 = right, 0 = below, -1 = left
    int sub_offset_y_{-1};
};

} // namespace arcade
