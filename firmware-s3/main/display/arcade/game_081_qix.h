#pragma once
#include "arcade_batch_cartridge.h"
namespace arcade {
class Game081Qix : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 81; }
    const char *GetName() const override { return "Qix圈地"; }
    const char *GetEnglishName() const override { return "Qix"; }

  private:
    friend struct B2MechanismProbe; // deterministic host collision fixtures
    uint8_t grid_[16][16]{};
    int x_ = 1, y_ = 8, ex_ = 10, ey_ = 8, vx_ = -1, vy_ = 1, claimed_ = 0;
    bool armed_ = false, drawing_ = false;
    float enemy_clock_ = 0;
    void Capture();
    void Setup() override;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override { return claimed_ * 100 / 144; }
};
} // namespace arcade
