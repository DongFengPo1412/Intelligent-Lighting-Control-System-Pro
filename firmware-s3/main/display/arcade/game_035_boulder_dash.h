#pragma once
#include "arcade_batch_cartridge.h"
namespace arcade {
class Game035BoulderDash : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 35; }
    const char *GetName() const override { return "落石夺宝"; }
    const char *GetEnglishName() const override { return "Boulder Dash"; }
    ControlType GetControlType() const override { return CTRL_DPAD_4WAY; }

  private:
    friend struct B2MechanismProbe; // deterministic host collision fixtures
    uint8_t grid_[16][16]{};
    int x_ = 2, y_ = 2, gems_ = 0;
    float fall_ = 0;
    void Setup() override;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override { return gems_ * 100 / 8; }
};
} // namespace arcade
