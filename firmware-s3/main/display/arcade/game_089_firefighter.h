#pragma once
#include "arcade_b3_helpers.h"
namespace arcade {
class Game089Firefighter : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 89; }
    const char *GetName() const override { return "消防灭火"; }
    const char *GetEnglishName() const override { return "Firefighter"; }
    ControlType GetControlType() const override { return ControlType(3); }

  private:
    friend struct B3Probe;
    int fire[64]{}, x = 1, y = 6, face = 0, water = 8, burned = 0, extinguished = 0;
    double spread = 0;
    void Setup() override;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override;
};
} // namespace arcade
