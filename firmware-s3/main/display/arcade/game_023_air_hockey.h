#pragma once
#include "arcade_b3_helpers.h"
namespace arcade {
class Game023AirHockey : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 23; }
    const char *GetName() const override { return "空气曲棍球"; }
    const char *GetEnglishName() const override { return "Air Hockey"; }
    ControlType GetControlType() const override { return ControlType(3); }
    CartridgeStatus GetStatus() const override {
        auto s = BatchCartridge::GetStatus();
        s.lives = std::max(0, 3 - against);
        return s;
    }

  private:
    friend struct B3Probe;
    float paddle_x = 8, paddle_y = 13, ax = 8, x = 8, y = 8, vx = 1, vy = 3, cooldown = 0;
    int goals = 0, against = 0;
    void Setup() override;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override;
};
} // namespace arcade
