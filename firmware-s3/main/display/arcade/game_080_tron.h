#pragma once
#include "arcade_b3_helpers.h"
namespace arcade {
class Game080Tron : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 80; }
    const char *GetName() const override { return "光线摩托"; }
    const char *GetEnglishName() const override { return "Tron Light Cycles"; }
    ControlType GetControlType() const override { return ControlType(2); }

  private:
    friend struct B3Probe;
    uint8_t board[256]{};
    int x = 3, y = 12, dir = 0, ex = 12, ey = 3, edir = 2, steps = 0;
    double clock = 0;
    uint32_t board_hash = 0;
    void Setup() override;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override;
};
} // namespace arcade
