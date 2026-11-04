#pragma once
#include "arcade_b3_helpers.h"
namespace arcade {
class Game071PegSolitaire : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 71; }
    const char *GetName() const override { return "单人孔明棋"; }
    const char *GetEnglishName() const override { return "Peg Solitaire"; }
    ControlType GetControlType() const override { return ControlType(3); }

  private:
    friend struct B3Probe;
    uint16_t mask = 32766;
    int x = 0, y = 0, dir = 0, moves = 0;
    void Setup() override;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override;
};
} // namespace arcade
