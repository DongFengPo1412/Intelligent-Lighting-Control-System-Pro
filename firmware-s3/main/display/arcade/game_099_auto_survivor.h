#pragma once
#include "arcade_b3_helpers.h"
namespace arcade {
class Game099AutoSurvivor : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 99; }
    const char *GetName() const override { return "自动攻击生存"; }
    const char *GetEnglishName() const override { return "Auto Attack Survivor"; }
    ControlType GetControlType() const override { return ControlType(3); }
    CartridgeStatus GetStatus() const override {
        auto s = BatchCartridge::GetStatus();
        s.lives = std::max(0, hp);
        return s;
    }

  private:
    friend struct B3Probe;
    double x = 8, y = 8, ex[12]{}, ey[12]{}, spawn = 0, attack = 0, invul = 0;
    int ehp[12]{}, hp = 5, kills = 0, damage = 1, upgrades = 0, rate_bonus = 0;
    uint32_t seed = 0x99ab;
    void Setup() override;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override;
};
} // namespace arcade
