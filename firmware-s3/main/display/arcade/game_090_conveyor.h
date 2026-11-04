#pragma once
#include "arcade_b3_helpers.h"
namespace arcade {
class Game090Conveyor : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 90; }
    const char *GetName() const override { return "传送带工厂"; }
    const char *GetEnglishName() const override { return "Conveyor Factory"; }
    ControlType GetControlType() const override { return ControlType(3); }

  private:
    friend struct B3Probe;
    int belt[49]{}, item[4]{}, processed[4]{}, x = 0, y = 0, delivered = 0, waste = 0;
    double clock = 0, spawn = 0;
    void Setup() override;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override;
};
} // namespace arcade
