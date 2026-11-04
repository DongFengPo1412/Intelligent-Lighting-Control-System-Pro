#pragma once
#include "arcade_b3_helpers.h"
namespace arcade {
class Game036DigDug : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 36; }
    const char *GetName() const override { return "地下充气战"; }
    const char *GetEnglishName() const override { return "Dig Dug"; }
    ControlType GetControlType() const override { return ControlType(3); }
    CartridgeStatus GetStatus() const override {
        auto s = BatchCartridge::GetStatus();
        s.lives = std::max(0, hp);
        return s;
    }

  private:
    friend struct B3Probe;
    int x = 7, y = 7, face = 0, hp = 2, kills = 0, ex[3]{}, ey[3]{};
    float inflate[3]{}, enemy_clock = 0;
    bool enemy[3]{};
    uint8_t dirt[16][16]{};
    void Setup() override;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override;
};
} // namespace arcade
