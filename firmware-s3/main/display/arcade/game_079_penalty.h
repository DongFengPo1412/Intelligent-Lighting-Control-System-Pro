#pragma once
#include "arcade_b3_helpers.h"
namespace arcade {
class Game079Penalty : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 79; }
    const char *GetName() const override { return "足球点球"; }
    const char *GetEnglishName() const override { return "Penalty Shootout"; }
    ControlType GetControlType() const override { return ControlType(3); }

  private:
    friend struct B3Probe;
    double aim = 8, power = 0, flight = 0, impact = 8, keeper = 8;
    bool charging = false, flying = false;
    int shots = 0, goals = 0;
    void Setup() override;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override;
};
} // namespace arcade
