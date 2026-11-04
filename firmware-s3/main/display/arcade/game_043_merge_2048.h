// game_043_merge_2048.h —— 目标 #043 2048滑块 (Neon 2048)
// 机制: 4x4 网格滑移对撞单次合并 + 霓虹色阶与点位编码 + 随机落子与死锁判定
#pragma once

#include "arcade_cartridge.h"
#include <stdint.h>

namespace arcade {

class Game043Merge2048 : public Cartridge {
public:
    Game043Merge2048();
    ~Game043Merge2048() override = default;

    uint8_t GetId() const override { return 43; }
    const char* GetName() const override { return "2048滑块"; }
    const char* GetEnglishName() const override { return "Neon 2048"; }
    uint16_t GetReleaseYear() const override { return 2014; }
    ControlType GetControlType() const override { return CTRL_DPAD_4WAY; }

    void Init() override;
    void Reset() override;
    void Start() override;
    void Pause() override;
    void Resume() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

    bool Slide(int dx, int dy);
    bool CanMove() const;

private:
    uint32_t NextRand();
    void SpawnRandomTile();
    void RefreshMaxTile();
    void AddScore(uint32_t pts);

    CartridgeState state_;
    uint8_t board_[4][4];
    uint8_t max_tile_;
    uint32_t seed_;
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
    float anim_timer_;
};

} // namespace arcade
