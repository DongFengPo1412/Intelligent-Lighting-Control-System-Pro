#pragma once
#include "arcade_b3_helpers.h"
namespace arcade {
class Game050MiniSudoku : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 50; }
    const char *GetName() const override { return "四色迷你数独"; }
    const char *GetEnglishName() const override { return "Mini Sudoku"; }
    ControlType GetControlType() const override { return ControlType(3); }
    CartridgeStatus GetStatus() const override {
        auto s = BatchCartridge::GetStatus();
        s.lives = std::max(0, attempts);
        return s;
    }

  private:
    friend struct B3Probe;
    int board[16]{}, x = 0, y = 0, attempts = 2, edits = 0;
    uint16_t fixed = 0;
    float conflict = 0;
    void Setup() override;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override;
};
} // namespace arcade
