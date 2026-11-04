#pragma once
#include "arcade_b3_helpers.h"
namespace arcade {
class Game068Mastermind : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 68; }
    const char *GetName() const override { return "颜色密码"; }
    const char *GetEnglishName() const override { return "Mastermind"; }
    ControlType GetControlType() const override { return ControlType(3); }

  private:
    friend struct B3Probe;
    int secret[4]{}, guess[4]{}, slot = 0, tries = 0, exact = 0, near = 0;
    void Setup() override;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override;
};
} // namespace arcade
