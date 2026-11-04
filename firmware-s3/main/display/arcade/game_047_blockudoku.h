#pragma once
#include "arcade_b3_helpers.h"
namespace arcade {
class Game047Blockudoku : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 47; }
    const char *GetName() const override { return "自由方块消除"; }
    const char *GetEnglishName() const override { return "Blockudoku"; }
    ControlType GetControlType() const override { return ControlType(3); }

  private:
    friend struct B3Probe;
    uint64_t board = 0;
    int x = 0, y = 0, selected = 0, rack = 7, placed = 0, cleared = 0;
    void Setup() override;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override;
};
} // namespace arcade
