// game_015_simon_memory.h —— 目标 #015 闪灯记忆 (Simon Says)
// 机制: 四象限彩色序列记忆回放 + 玩家按四轨按键逐拍复现
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

enum SimonPhase : uint8_t {
    SIMON_SHOW_ON = 0,
    SIMON_SHOW_GAP = 1,
    SIMON_INPUT = 2,
    SIMON_ROUND_PAUSE = 3,
};

class Game015SimonMemory : public Cartridge {
public:
    Game015SimonMemory();
    ~Game015SimonMemory() override = default;

    uint8_t GetId() const override { return 15; }
    const char* GetName() const override { return "闪灯记忆"; }
    const char* GetEnglishName() const override { return "Simon Says"; }
    uint16_t GetReleaseYear() const override { return 1978; }
    ControlType GetControlType() const override { return CTRL_MULTI_TRACK; }

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

    static const int kMaxSequence = 15;

    CartridgeState state_;
    SimonPhase phase_;
    uint8_t sequence_[kMaxSequence];
    int seq_len_;
    int show_idx_;
    int input_idx_;
    int lit_pad_;
    float phase_timer_;
    float input_flash_timer_;

    uint32_t score_;
    uint32_t high_score_;
    uint32_t rng_seed_;
    float state_timer_;
    float anim_timer_;
};

} // namespace arcade
