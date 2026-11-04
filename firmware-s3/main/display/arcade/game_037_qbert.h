#pragma once
#include "arcade_b3_helpers.h"
namespace arcade {
class Game037Qbert : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 37; }
    const char *GetName() const override { return "染色跳格"; }
    const char *GetEnglishName() const override { return "Qbert"; }
    ControlType GetControlType() const override { return ControlType(2); }
    CartridgeStatus GetStatus() const override {
        auto s = BatchCartridge::GetStatus();
        s.lives = std::max(0, hp);
        return s;
    }

  private:
    friend struct B3Probe;
    int row = 0, col = 0, er = 4, ec = 2, hp = 2, mask = 1;
    float hop = 0, chase = -8;
    void Setup() override;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override;
};
} // namespace arcade
