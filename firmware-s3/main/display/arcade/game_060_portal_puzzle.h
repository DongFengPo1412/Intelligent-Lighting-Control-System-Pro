#pragma once
#include "arcade_b3_helpers.h"
namespace arcade {
class Game060PortalPuzzle : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 60; }
    const char *GetName() const override { return "传送门谜题"; }
    const char *GetEnglishName() const override { return "Portal Puzzle"; }
    ControlType GetControlType() const override { return ControlType(3); }

  private:
    friend struct B3Probe;
    int x = 1, y = 6, moves = 0, stage = 0, stage_moves = 0;
    bool gate = false;
    int teleports = 0;
    void Setup() override;
    void LoadStage();
    bool Wall(int, int) const;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override;
};
} // namespace arcade
