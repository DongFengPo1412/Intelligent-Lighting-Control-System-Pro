#pragma once
#include "arcade_b3_helpers.h"
namespace arcade {
class Game032Defender : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 32; }
    const char *GetName() const override { return "横向防卫"; }
    const char *GetEnglishName() const override { return "Defender"; }
    ControlType GetControlType() const override { return ControlType(3); }
    CartridgeStatus GetStatus() const override {
        auto s = BatchCartridge::GetStatus();
        s.lives = std::max(0, hp);
        return s;
    }

  private:
    friend struct B3Probe;
    float x = 8, y = 6;
    int facing = 1, hp = 2, kills = 0;
    float ex[4]{}, ey[4]{}, bx[8]{}, by[8]{}, bv[8]{}, life[8]{}, shot = 0;
    bool enemy[4]{}, carrying[4]{}, human[4]{}, bullet[8]{};
    void Setup() override;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override;
};
} // namespace arcade
