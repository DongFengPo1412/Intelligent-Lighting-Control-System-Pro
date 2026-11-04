#pragma once
#include "arcade_b3_helpers.h"
namespace arcade {
class Game077Bowling : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 77; }
    const char *GetName() const override { return "保龄球"; }
    const char *GetEnglishName() const override { return "Bowling"; }
    ControlType GetControlType() const override { return ControlType(3); }

  private:
    friend struct B3Probe;
    double aim = 0, power = 0, x = 8, y = 14, vx = 0, vy = 0;
    bool charging = false, flying = false;
    int pins = 1023, frame = 0, shot = 0, first = 0, rolls[21]{}, nroll = 0, before = 10;
    void Resolve();
    int Total() const;
    void Setup() override;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override;
};
} // namespace arcade
