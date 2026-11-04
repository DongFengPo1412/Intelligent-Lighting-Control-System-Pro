#pragma once
#include "arcade_b3_helpers.h"
namespace arcade {
class Game049LightsOut : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 49; }
    const char *GetName() const override { return "灭灯"; }
    const char *GetEnglishName() const override { return "Lights Out"; }
    ControlType GetControlType() const override { return ControlType(3); }

  private:
    friend struct B3Probe;
    uint32_t mask = 0;
    int x = 2, y = 2, moves = 0;
    void Setup() override;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override;
};
} // namespace arcade
