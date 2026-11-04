#pragma once
#include "arcade_b3_helpers.h"
namespace arcade {
class Game008JumpKing : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 8; }
    const char *GetName() const override { return "蓄力跳跃"; }
    const char *GetEnglishName() const override { return "Jump King"; }
    ControlType GetControlType() const override { return ControlType(3); }

  private:
    friend struct B3Probe;
    float x = 3.5f, y = 46, vx = 0, vy = 0, charge = 0;
    int facing = 1;
    bool grounded = true, charging = false;
    void Setup() override;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override;
};
} // namespace arcade
