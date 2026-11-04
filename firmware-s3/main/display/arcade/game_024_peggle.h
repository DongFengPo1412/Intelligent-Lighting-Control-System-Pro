#pragma once
#include "arcade_b3_helpers.h"
namespace arcade {
class Game024Peggle : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 24; }
    const char *GetName() const override { return "弹珠撞靶"; }
    const char *GetEnglishName() const override { return "Peggle"; }
    ControlType GetControlType() const override { return ControlType(3); }
    CartridgeStatus GetStatus() const override {
        auto s = BatchCartridge::GetStatus();
        s.lives = std::max(0, balls);
        return s;
    }

  private:
    friend struct B3Probe;
    double aim = 0, x = 8, y = 2, vx = 0, vy = 0;
    int mask = 255, balls = 8;
    bool flying = false;
    void Setup() override;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override;
};
} // namespace arcade
