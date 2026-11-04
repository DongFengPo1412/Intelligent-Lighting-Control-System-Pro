#pragma once
#include "arcade_b3_helpers.h"
namespace arcade {
class Game007Downwell : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 7; }
    const char *GetName() const override { return "向下射击"; }
    const char *GetEnglishName() const override { return "Downwell"; }
    ControlType GetControlType() const override { return ControlType(3); }
    CartridgeStatus GetStatus() const override {
        auto s = BatchCartridge::GetStatus();
        s.lives = std::max(0, hp);
        return s;
    }

  private:
    friend struct B3Probe;
    float x = 8, y = 2, vy = 0;
    int ammo = 3, kills = 0, hp = 2;
    bool grounded = false;
    float bx[8]{}, by[8]{};
    bool bullet[8]{}, enemy[3]{};
    void Setup() override;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override;
};
} // namespace arcade
