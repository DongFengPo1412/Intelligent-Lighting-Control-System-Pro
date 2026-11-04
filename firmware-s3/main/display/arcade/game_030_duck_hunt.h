// game_030_duck_hunt.h —— 目标 #030 打鸭子 (Duck Hunt, 1984)
// 机制: 草丛起飞折线振翅野鸭 + 准星移动 + 每只3发霰弹与4.5s逃逸倒计时 + 轮次配额(4/6晋级)
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

enum DuckFlightState030 : uint8_t {
    DUCK_FLYING = 0,
    DUCK_STUNNED = 1,
    DUCK_FALLING = 2,
    DUCK_ESCAPING = 3,
};

class Game030DuckHunt : public Cartridge {
public:
    static const int kDucksPerRound = 6;
    static const int kRoundQuota = 4;
    static const int kTotalRounds = 3;

    Game030DuckHunt();
    ~Game030DuckHunt() override = default;

    uint8_t GetId() const override { return 30; }
    const char* GetName() const override { return "打鸭子"; }
    const char* GetEnglishName() const override { return "Duck Hunt"; }
    uint16_t GetReleaseYear() const override { return 1984; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    void Init() override;
    void Reset() override;
    void Start() override;
    void Pause() override;
    void Resume() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    uint32_t NextRand();
    void AddScore(uint32_t pts);
    void SetupNewGame(CartridgeState new_state);
    void StartRound();
    void SpawnDuck();
    void FinishCurrentDuck(bool was_hit);
    bool PullTrigger();

    CartridgeState state_;
    uint32_t score_;
    uint32_t high_score_;
    uint8_t round_;
    uint8_t duck_index_;
    uint8_t round_hits_;
    uint8_t round_misses_;
    uint8_t shells_;
    uint8_t duck_results_[kDucksPerRound]; // 0=待出, 1=命中, 2=逃脱

    DuckFlightState030 duck_state_;
    float duck_x_;
    float duck_y_;
    float duck_vx_;
    float duck_vy_;
    float escape_timer_;
    float phase_timer_;
    float weave_timer_;

    float reticle_x_;
    float reticle_y_;
    float muzzle_flash_;

    float state_timer_;
    float anim_timer_;
    uint32_t seed_;
};

} // namespace arcade
