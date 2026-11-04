#pragma once
#include "arcade_b3_helpers.h"
namespace arcade {
class Game013PendulumToss : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 13; }
    const char *GetName() const override { return "摆锤投球"; }
    const char *GetEnglishName() const override { return "Pendulum Toss"; }
    ControlType GetControlType() const override { return ControlType(0); }
    CartridgeStatus GetStatus() const override {
        auto s = BatchCartridge::GetStatus();
        s.lives = std::max(0, balls);
        return s;
    }

  private:
    friend struct B3Probe;
    float x = 8, y = 6, vx = 0, vy = 0, phase = 0;
    bool flying = false;
    int hits = 0, balls = 5;
    void Setup() override;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override;
};
} // namespace arcade
