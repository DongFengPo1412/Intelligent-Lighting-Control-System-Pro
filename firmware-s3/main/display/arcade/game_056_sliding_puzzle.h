#pragma once
#include "arcade_b3_helpers.h"
namespace arcade {
class Game056SlidingPuzzle : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 56; }
    const char *GetName() const override { return "数字华容道"; }
    const char *GetEnglishName() const override { return "Sliding Puzzle"; }
    ControlType GetControlType() const override { return ControlType(2); }

  private:
    friend struct B3Probe;
    int board[9]{}, blank = 8, moves = 0;
    void Setup() override;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override;
};
} // namespace arcade
