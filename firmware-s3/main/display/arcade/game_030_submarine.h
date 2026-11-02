// game_030_submarine.h —— 潜艇鱼雷大战 1979 (Submarine 1979 / Sea Wolf)
// 编号: #030 | 机制: 多吃水层水面舰艇穿行 + 浮力垂直鱼雷前置预判 + 游弋水雷引爆阻截 + 声呐制海权
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

enum ShipType : uint8_t {
    SHIP_PT_BOAT = 0,    // 高速鱼雷艇 (+100分)
    SHIP_DESTROYER = 1,  // 中速驱逐舰 (+200分)
    SHIP_CARRIER = 2,    // 大型航空母舰 (+400分)
};

struct SurfaceShip {
    bool active;
    ShipType type;
    float x;
    float y;
    float vx;
    int hp;
};

struct SubTorpedo {
    bool active;
    float x;
    float y;
    float vy;
};

struct SeaMine {
    bool active;
    float x;
    float y;
    float vx;
};

class Game030Submarine : public Cartridge {
public:
    Game030Submarine();
    ~Game030Submarine() override = default;

    uint8_t GetId() const override { return 30; }
    const char* GetName() const override { return "深海鱼雷战"; }
    const char* GetEnglishName() const override { return "Submarine 1979"; }
    uint16_t GetReleaseYear() const override { return 1979; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    void Init() override;
    void Reset() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    void InitOcean();
    void SpawnShip();
    void SpawnMine();
    void FireTorpedo();
    void UpdateShips(float dt);
    void UpdateTorpedoes(float dt);
    void UpdateMines(float dt);

    CartridgeState state_;

    float player_x_;
    int lives_;
    float reload_timer_;
    int ships_sunk_;

    static constexpr int MAX_SHIPS = 4;
    SurfaceShip ships_[MAX_SHIPS];

    static constexpr int MAX_TORPEDOES = 3;
    SubTorpedo torpedoes_[MAX_TORPEDOES];

    static constexpr int MAX_MINES = 3;
    SeaMine mines_[MAX_MINES];

    float ship_spawn_timer_;
    float mine_spawn_timer_;

    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
};

} // namespace arcade
