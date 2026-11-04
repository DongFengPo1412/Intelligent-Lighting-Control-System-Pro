#pragma once
#include "arcade_batch_cartridge.h"
namespace arcade {
class Game098LunarLander : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 98; }
    const char *GetName() const override { return "月球着陆"; }
    const char *GetEnglishName() const override { return "Lunar Lander"; }

  private:
    friend struct B2MechanismProbe; // deterministic host collision fixtures
    float x_ = 4, y_ = 2, vx_ = 0, vy_ = 0, angle_ = 0, fuel_ = 35;
    bool thrusting_ = false;
    void Setup() override;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override {
        return int(std::max(0.f, std::min(100.f, (y_ - 2) / 11 * 100)));
    }
};
} // namespace arcade
