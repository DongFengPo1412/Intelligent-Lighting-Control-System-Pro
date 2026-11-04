#pragma once
#include "arcade_b3_helpers.h"
namespace arcade {
class Game078Baseball : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 78; }
    const char *GetName() const override { return "棒球击打"; }
    const char *GetEnglishName() const override { return "Baseball"; }
    ControlType GetControlType() const override { return ControlType(0); }

  private:
    friend struct B3Probe;
    double ball_y = 1, wait = .5;
    int pitches = 0, runs = 0, strikes = 0;
    bool active = false;
    void Setup() override;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override;
};
} // namespace arcade
