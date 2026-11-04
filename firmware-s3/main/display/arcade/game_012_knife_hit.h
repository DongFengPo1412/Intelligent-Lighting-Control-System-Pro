#pragma once
#include "arcade_b3_helpers.h"
namespace arcade {
class Game012KnifeHit : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 12; }
    const char *GetName() const override { return "旋盘投刀"; }
    const char *GetEnglishName() const override { return "Knife Hit"; }
    ControlType GetControlType() const override { return ControlType(0); }

  private:
    friend struct B3Probe;
    float theta = 0, knife_y = 14, angles[16]{};
    int count = 2, hits = 0;
    bool flying = false;
    void Setup() override;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override;
};
} // namespace arcade
