#pragma once
#include "arcade_b3_helpers.h"
namespace arcade {
class Game100MemoryMatch : public BatchCartridge {
  public:
    uint8_t GetId() const override { return 100; }
    const char *GetName() const override { return "翻牌配对"; }
    const char *GetEnglishName() const override { return "Memory Match"; }
    ControlType GetControlType() const override { return ControlType(3); }

    // Replay control affects subsequent Reset/Start only; normal sessions use fresh entropy.
    void SetReplaySeed(uint32_t seed) {
        replay_seed_ = seed;
        replay_seeded_ = true;
    }
    void UseRandomSeeds() { replay_seeded_ = false; }

  private:
    bool replay_seeded_ = false;
    uint32_t replay_seed_ = 0, last_seed_ = 0;
    friend struct B3Probe;
    int cards[16]{}, x = 0, y = 0, first = -1, second = -1, pairs = 0, turns = 0;
    uint16_t matched = 0;
    double wait = 0;
    void Setup() override;
    void Tick(float, uint16_t, uint16_t) override;
    void Draw(uint8_t *) override;
    int Progress() const override;
};
} // namespace arcade
