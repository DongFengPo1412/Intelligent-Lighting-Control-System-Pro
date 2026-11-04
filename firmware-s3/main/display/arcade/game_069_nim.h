#pragma once
#include "arcade_b3_helpers.h"
namespace arcade {
class Game069Nim : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 69; }
    const char *GetName() const override { return "取石子"; }
    const char *GetEnglishName() const override { return "Nim"; }
    ControlType GetControlType() const override { return ControlType(3); }

  private:
    friend struct B3Probe;
    int piles[3]{}, pile = 0, take = 1, turns = 0, human_wins = 0, ai_wins = 0, round = 0;
    double thinking = 0;
    void LoadRound();
    void EndRound(bool);
    void Setup() override;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override;
};
} // namespace arcade
