#pragma once
#include "arcade_b3_helpers.h"
namespace arcade {
class Game061ConnectFour : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 61; }
    const char *GetName() const override { return "四子棋"; }
    const char *GetEnglishName() const override { return "Connect Four"; }
    ControlType GetControlType() const override { return ControlType(3); }

  private:
    friend struct B3Probe;
    int board[42]{}, column = 3, turns = 0;
    int Drop(int, int);
    bool Won(int) const;
    int Choose() const;
    void Setup() override;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override;
};
} // namespace arcade
