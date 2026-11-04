#pragma once
#include "arcade_b3_helpers.h"
namespace arcade {
class Game059CutRope : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 59; }
    const char *GetName() const override { return "割绳子"; }
    const char *GetEnglishName() const override { return "Cut the Rope"; }
    ControlType GetControlType() const override { return ControlType(0); }
    CartridgeStatus GetStatus() const override {
        auto s = BatchCartridge::GetStatus();
        s.lives = std::max(0, tries);
        return s;
    }

  private:
    friend struct B3Probe;
    double x = 0, y = 0, vx = 0, vy = 0, theta = 0;
    bool cut = false;
    int tries = 0;
    void Setup() override;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override;
};
} // namespace arcade
