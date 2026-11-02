// game_016_neon_2048.h —— 霓虹 2048 (Neon 2048 2014)
// 编号: #016 | 机制: 4x4 网格滑移对撞合并 + 霓虹色阶升维 + 随机落子与死锁判定
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

class Game016Neon2048 : public Cartridge {
public:
    Game016Neon2048();
    ~Game016Neon2048() override = default;

    uint8_t GetId() const override { return 16; }
    const char* GetName() const override { return "霓虹 2048"; }
    const char* GetEnglishName() const override { return "Neon 2048 2014"; }
    uint16_t GetReleaseYear() const override { return 2014; }
    ControlType GetControlType() const override { return CTRL_DPAD_4WAY; }

    void Init() override;
    void Reset() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    void SpawnRandomTile();
    bool Slide(int dx, int dy);
    bool CanMove() const;
    void GetTileColor(uint8_t level, uint8_t& r, uint8_t& g, uint8_t& b) const;

    CartridgeState state_;
    uint8_t board_[4][4]; // 0=空, 1=2, 2=4, 3=8, ... 11=2048
    uint32_t score_;
    uint32_t high_score_;
    uint8_t max_tile_level_;
    float state_timer_;
};

} // namespace arcade
