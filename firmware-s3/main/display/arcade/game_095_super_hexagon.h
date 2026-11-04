// game_095_super_hexagon.h —— 目标 #095 旋转避壁 (Super Hexagon)
// 机制: 脉冲核心与6扇区几何背景 + 向心收缩缺口多边形壁垒 + 双键顺逆时针轨道闪避
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

struct HexWall {
    float radius;
    uint8_t solid_mask; // bit 0..5: 1=实心阻挡扇区, 0=缺口通行扇区
    bool passed;
};

class Game095SuperHexagon : public Cartridge {
public:
    Game095SuperHexagon();
    ~Game095SuperHexagon() override = default;

    uint8_t GetId() const override { return 95; }
    const char* GetName() const override { return "旋转避壁"; }
    const char* GetEnglishName() const override { return "Super Hexagon"; }
    uint16_t GetReleaseYear() const override { return 2012; }
    ControlType GetControlType() const override { return CTRL_TWO_BUTTON; }

    void Init() override;
    void Reset() override;
    void Start() override;
    void Pause() override;
    void Resume() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

    static int AngleToSector(float angle);

private:
    uint32_t NextRand();
    void AddScore(uint32_t pts);
    uint8_t MakeWallMask();
    void SetupArena();

    CartridgeState state_;
    uint32_t score_;
    uint32_t high_score_;
    uint32_t rng_seed_;
    float player_angle_;
    float survival_timer_;
    float state_timer_;
    float anim_timer_;
    uint16_t walls_passed_;
    uint8_t last_gap_;

    static const int kNumWalls = 3;
    HexWall walls_[kNumWalls];
};

} // namespace arcade
