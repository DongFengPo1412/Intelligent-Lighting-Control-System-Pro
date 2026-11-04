#pragma once
#include "arcade_b3_helpers.h"
namespace arcade {
class Game011DinoRunner : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 11; }
    const char *GetName() const override { return "恐龙跑酷"; }
    const char *GetEnglishName() const override { return "Dino Runner"; }
    ControlType GetControlType() const override { return ControlType(0); }

  private:
    friend struct B3Probe;
    float y = 12, vy = 0, distance = 0, ob[3]{};
    int cleared = 0;
    void Setup() override;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override;
};
} // namespace arcade
