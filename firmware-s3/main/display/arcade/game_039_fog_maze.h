#pragma once
#include "arcade_b3_helpers.h"
namespace arcade {
class Game039FogMaze : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 39; }
    const char *GetName() const override { return "迷雾探索迷宫"; }
    const char *GetEnglishName() const override { return "Fog Maze"; }
    ControlType GetControlType() const override { return ControlType(2); }

  private:
    friend struct B3Probe;
    int x = 1, y = 1, moves = 0, explored = 1;
    uint8_t grid[16][16]{}, seen[16][16]{}, visited[16][16]{};
    uint32_t layout_hash = 0;
    void Setup() override;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override;
};
} // namespace arcade
