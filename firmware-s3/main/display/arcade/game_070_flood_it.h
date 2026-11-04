#pragma once
#include "arcade_b3_helpers.h"
namespace arcade {
class Game070FloodIt : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 70; }
    const char *GetName() const override { return "连通染色"; }
    const char *GetEnglishName() const override { return "Flood-It"; }
    ControlType GetControlType() const override { return ControlType(3); }

  private:
    friend struct B3Probe;
    int board[36]{}, color = 0, selected = 0, moves = 0, count = 0;
    uint64_t flooded = 1;
    void Setup() override;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override;
};
} // namespace arcade
