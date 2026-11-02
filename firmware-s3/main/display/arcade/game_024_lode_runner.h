// game_024_lode_runner.h —— 淘金者 1983 (Lode Runner 1983)
// 编号: #024 | 机制: 左右掘坑陷阱 + 活埋警卫再生 + 踏头过坑 + 收集全金显现逃生天梯
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

enum LodeTile : uint8_t {
    LODE_AIR = 0,
    LODE_BRICK = 1,       // 可挖掘砖块
    LODE_SOLID = 2,       // 不可破坏基岩
    LODE_LADDER = 3,      // 爬梯
    LODE_BAR = 4,         // 悬挂横杆/滑索
    LODE_HOLE = 5,        // 被挖开的砖坑 (计时填埋)
};

struct LodeHole {
    bool active;
    int x;
    int y;
    float timer;
};

struct LodeGuard {
    bool active;
    float x;
    float y;
    float move_timer;
    bool trapped;
    float trap_timer;
};

struct LodeGold {
    bool collected;
    int x;
    int y;
};

class Game024LodeRunner : public Cartridge {
public:
    Game024LodeRunner();
    ~Game024LodeRunner() override = default;

    uint8_t GetId() const override { return 24; }
    const char* GetName() const override { return "淘金者"; }
    const char* GetEnglishName() const override { return "Lode Runner 1983"; }
    uint16_t GetReleaseYear() const override { return 1983; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    void Init() override;
    void Reset() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    void InitLevel();
    void DigHole(int dx);
    void UpdateHoles(float dt);
    void UpdateGuards(float dt);
    bool CanWalk(int x, int y) const;
    bool CanFall(int x, int y) const;

    CartridgeState state_;
    uint8_t grid_[16][16];

    float player_x_;
    float player_y_;
    int player_dir_;
    int lives_;
    float move_timer_;

    static constexpr int MAX_HOLES = 4;
    LodeHole holes_[MAX_HOLES];

    static constexpr int MAX_GUARDS = 2;
    LodeGuard guards_[MAX_GUARDS];

    static constexpr int TOTAL_GOLDS = 3;
    LodeGold golds_[TOTAL_GOLDS];

    bool escape_ladder_revealed_;
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
};

} // namespace arcade
