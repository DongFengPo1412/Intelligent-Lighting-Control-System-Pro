#pragma once
#include "arcade_b3_helpers.h"
namespace arcade {
class Game091WireMaze : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 91; }
    const char *GetName() const override { return "电线迷宫"; }
    const char *GetEnglishName() const override { return "Wire Maze"; }
    ControlType GetControlType() const override { return ControlType(2); }

  private:
    friend struct B3Probe;
    bool wire[256]{};
    int x = 2, y = 13, steps = 0;
    void Setup() override;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override;
};
} // namespace arcade
