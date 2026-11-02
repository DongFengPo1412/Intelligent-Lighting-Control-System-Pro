#pragma once

#include "cartridge.h"
#include <cstdint>
#include <string>

namespace arcade {

class Game102Columns : public Cartridge {
public:
    Game102Columns();
    ~Game102Columns() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    uint32_t GetId() const override { return 102; }
    std::string GetName() const override { return "Columns (1990)"; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    enum GameState {
        STATE_FALLING = 0,
        STATE_FLASHING_MATCH = 1,
        STATE_COLLAPSING = 2,
        STATE_GAME_OVER = 3
    };

    static constexpr int BOARD_COLS = 6;
    static constexpr int BOARD_ROWS = 13;
    static constexpr int NUM_GEM_TYPES = 5;

    GameState GetState() const { return state_; }
    int GetScore() const { return score_; }
    int GetLevel() const { return level_; }
    int GetChains() const { return chain_count_; }
    int GetCurCol() const { return cur_col_; }
    float GetCurY() const { return cur_y_; }
    uint8_t GetBoardAt(int c, int r) const {
        if (c >= 0 && c < BOARD_COLS && r >= 0 && r < BOARD_ROWS) {
            return board_[r][c];
        }
        return 0;
    }
    uint8_t GetCurGem(int i) const { return (i >= 0 && i < 3) ? cur_gems_[i] : 0; }

    void CycleCurrentColumn();
    void ForcePlaceColumn(int col, int base_row, uint8_t g0, uint8_t g1, uint8_t g2);

private:
    GameState state_{STATE_FALLING};
    float state_timer_{0.0f};
    int score_{0};
    int level_{1};
    int matches_cleared_{0};
    int chain_count_{0};

    // Board representation (0 = empty, 1..5 = gem type)
    uint8_t board_[BOARD_ROWS][BOARD_COLS];
    bool matched_mask_[BOARD_ROWS][BOARD_COLS];

    // Current falling column (3 gems: 0=top, 1=mid, 2=bot)
    uint8_t cur_gems_[3];
    int cur_col_{2};
    float cur_y_{0.0f}; // Continuous row position
    float fall_speed_{1.5f};
    float move_cooldown_{0.0f};

    void SpawnNewColumn();
    bool CheckPlacementCollision(int col, int row_bot) const;
    void LockCurrentColumn();
    bool FindMatches();
    void ClearMatches();
    bool ApplyGravityCollapse();
};

} // namespace arcade
