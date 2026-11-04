#pragma once
#include "arcade_b3_helpers.h"
namespace arcade {
class Game082Artillery : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 82; }
    const char *GetName() const override { return "坦克抛物线对轰"; }
    const char *GetEnglishName() const override { return "Artillery"; }
    ControlType GetControlType() const override { return ControlType(3); }
    CartridgeStatus GetStatus() const override {
        auto s = BatchCartridge::GetStatus();
        s.lives = std::max(0, hp);
        return s;
    }

  private:
    friend struct B3Probe;
    double angle = .8, power = 8, x = 2, y = 10, vx = 0, vy = 0;
    int terrain[16]{}, hp = 3, enemy_hp = 3, owner = 0, shots = 0;
    bool flying = false;
    void Setup() override;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override;
};
} // namespace arcade
