#pragma once
#include "arcade_b3_helpers.h"
namespace arcade {
class Game025MarbleMaze : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 25; }
    const char *GetName() const override { return "滚珠平衡迷宫"; }
    const char *GetEnglishName() const override { return "Marble Maze"; }
    ControlType GetControlType() const override { return ControlType(3); }

  private:
    friend struct B3Probe;
    float x = 2, y = 2, vx = 0, vy = 0;
    uint8_t grid[16][16]{};
    void Setup() override;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override;
};
} // namespace arcade
