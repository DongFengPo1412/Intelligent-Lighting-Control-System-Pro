#pragma once
#include "arcade_b3_helpers.h"
namespace arcade {
class Game048TripleTown : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 48; }
    const char *GetName() const override { return "三合镇"; }
    const char *GetEnglishName() const override { return "Triple Town"; }
    ControlType GetControlType() const override { return ControlType(3); }

  private:
    friend struct B3Probe;
    int board[25]{}, x = 0, y = 0, moves = 0, best = 0;
    uint32_t board_hash = 0;
    void Setup() override;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override;
};
} // namespace arcade
