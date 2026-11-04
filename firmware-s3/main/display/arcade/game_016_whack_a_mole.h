// game_016_whack_a_mole.h —— 目标 #016 打地鼠 (Whack-A-Mole)
// 机制: 3x3 地洞网格 + 方向键锤子准星移动 + A键挥锤敲击普通地鼠/避开红紫刺雷地鼠
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

enum WhackMoleKind : uint8_t {
    WHACK_MOLE_NORMAL = 0,
    WHACK_MOLE_BOMB   = 1,
};

struct WhackHoleSlot {
    bool popped;
    bool whacked;
    WhackMoleKind kind;
    float pop_timer;
};

class Game016WhackAMole : public Cartridge {
public:
    Game016WhackAMole();
    ~Game016WhackAMole() override = default;

    uint8_t GetId() const override { return 16; }
    const char* GetName() const override { return "打地鼠"; }
    const char* GetEnglishName() const override { return "Whack-A-Mole"; }
    uint16_t GetReleaseYear() const override { return 1976; }
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
    void InitHoles();
    void SpawnMole(bool force_normal);
    void StrikeHammer();

    static const int kTotalHoles = 9;
    static const uint32_t kTargetScore = 100;

    CartridgeState state_;
    WhackHoleSlot holes_[kTotalHoles];
    int cursor_row_;
    int cursor_col_;
    float hammer_timer_;
    uint8_t lives_;
    float time_remaining_;
    float spawn_cooldown_;
    int spawn_count_;

    uint32_t score_;
    uint32_t high_score_;
    uint32_t rng_seed_;
    float state_timer_;
    float anim_timer_;
};

} // namespace arcade
