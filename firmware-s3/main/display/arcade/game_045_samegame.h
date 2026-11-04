// game_045_samegame.h —— 目标 #045 同色消块 (SameGame)
// 机制: 10x10 连通同色簇洪泛消除 + 二次方计分 + 列内重力与空列整体左移收拢
#pragma once

#include "arcade_cartridge.h"
#include <stdint.h>

namespace arcade {

class Game045SameGame : public Cartridge {
public:
    static const int kSize = 10;

    Game045SameGame();
    ~Game045SameGame() override = default;

    uint8_t GetId() const override { return 45; }
    const char* GetName() const override { return "同色消块"; }
    const char* GetEnglishName() const override { return "SameGame"; }
    uint16_t GetReleaseYear() const override { return 1985; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    void Init() override;
    void Reset() override;
    void Start() override;
    void Pause() override;
    void Resume() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

    int EliminateAt(int cx, int cy);
    bool HasRemovableGroup() const;
    int CountRemaining() const;

private:
    uint32_t NextRand();
    void GenerateBoard();
    int FloodComponent(int sx, int sy, bool mark[kSize][kSize]) const;
    void ApplyGravityAndShiftLeft();
    void AddScore(uint32_t pts);

    CartridgeState state_;
    uint8_t grid_[kSize][kSize]; // 0: empty, 1..4: colors
    int cx_;
    int cy_;
    uint32_t seed_;
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
    float anim_timer_;
};

} // namespace arcade
