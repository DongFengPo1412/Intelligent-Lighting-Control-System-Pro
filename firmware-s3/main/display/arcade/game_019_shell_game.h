// game_019_shell_game.h —— 目标 #019 猜球杯 (Shell Shuffle)
// 机制: 亮珠展示(REVEAL) -> 平滑高速交错洗杯(SHUFFLE) -> 游标选杯开奖(GUESS), 第4关升至4杯
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

enum ShellPhase : uint8_t {
    SHELL_REVEAL  = 0,
    SHELL_SHUFFLE = 1,
    SHELL_GUESS   = 2,
};

class Game019ShellGame : public Cartridge {
public:
    Game019ShellGame();
    ~Game019ShellGame() override = default;

    uint8_t GetId() const override { return 19; }
    const char* GetName() const override { return "猜球杯"; }
    const char* GetEnglishName() const override { return "Shell Shuffle"; }
    uint16_t GetReleaseYear() const override { return 1980; }
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
    float GetSlotX(int slot) const;
    void SetupRound();
    void BeginNextSwap();

    static const int kTotalRounds = 8;

    CartridgeState state_;
    ShellPhase phase_;
    int round_;
    int num_cups_;
    int pearl_slot_;
    int cursor_slot_;
    int chosen_slot_;
    uint8_t lives_;

    float reveal_timer_;
    int swaps_total_;
    int swaps_done_;
    float swap_dur_;
    float swap_t_;
    int swap_a_;
    int swap_b_;

    uint32_t score_;
    uint32_t high_score_;
    uint32_t rng_seed_;
    float state_timer_;
    float anim_timer_;
};

} // namespace arcade
