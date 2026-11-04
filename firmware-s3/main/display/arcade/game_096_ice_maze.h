#pragma once
#include "arcade_b3_helpers.h"
namespace arcade {
class Game096IceMaze : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 96; }
    const char *GetName() const override { return "冰面滑行迷宫"; }
    const char *GetEnglishName() const override { return "Ice Maze"; }
    ControlType GetControlType() const override { return ControlType(2); }

  private:
    friend struct B3Probe;
    int x = 1, y = 5, dx = 0, dy = 0, moves = 0;
    double clock = 0;
    bool sliding = false;
    bool Wall(int, int) const;
    void Setup() override;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override;
};
} // namespace arcade
