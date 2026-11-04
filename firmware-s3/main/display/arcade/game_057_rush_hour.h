#pragma once
#include "arcade_batch_cartridge.h"
namespace arcade {
class Game057RushHour : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 57; }
    const char *GetName() const override { return "堵车"; }
    const char *GetEnglishName() const override { return "Rush Hour"; }

  private:
    friend struct B2MechanismProbe; // deterministic host collision fixtures
    int cars_[7][4]{};
    int selected_ = 0, moves_ = 0;
    bool Occupied(int, int, int) const;
    void Setup() override;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override { return cars_[0][0] * 25; }
};
} // namespace arcade
