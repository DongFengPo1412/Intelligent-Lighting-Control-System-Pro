#pragma once
#include "arcade_b3_helpers.h"
namespace arcade {
class Game046Suika : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 46; }
    const char *GetName() const override { return "合成大西瓜"; }
    const char *GetEnglishName() const override { return "Suika"; }
    ControlType GetControlType() const override { return ControlType(3); }

  private:
    friend struct B3Probe;
    double aim = 8, bx[16]{}, by[16]{}, vx[16]{}, vy[16]{}, cooldown = 0, overflow = 0;
    int level[16]{}, best = 0, drops = 0, active_count = 0;
    void Setup() override;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override;
};
} // namespace arcade
