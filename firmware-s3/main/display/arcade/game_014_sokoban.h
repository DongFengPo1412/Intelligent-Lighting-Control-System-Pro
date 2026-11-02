// game_014_sokoban.h —— 经典推箱子 1982 (Sokoban 1982)
// 编号: #014 | 机制: 单向推移不可拉动 + 空间槽位逻辑归位 + 拓扑死锁与通关判定
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

enum SokobanTile {
    SOKOBAN_FLOOR = 0,
    SOKOBAN_WALL = 1,
    SOKOBAN_GOAL = 2
};

struct SokobanBox {
    int x;
    int y;
};

class Game014Sokoban : public Cartridge {
public:
    Game014Sokoban();
    ~Game014Sokoban() override = default;

    uint8_t GetId() const override { return 14; }
    const char* GetName() const override { return "经典推箱子"; }
    const char* GetEnglishName() const override { return "Sokoban 1982"; }
    uint16_t GetReleaseYear() const override { return 1982; }
    ControlType GetControlType() const override { return CTRL_DPAD_4WAY; }

    void Init() override;
    void Reset() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    void ResetLevel();
    int FindBoxAt(int x, int y) const;
    bool IsGoal(int x, int y) const;
    void CheckVictory();

    CartridgeState state_;
    int player_x_;
    int player_y_;
    uint32_t moves_;
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;

    // 16x16 静态地图 (0=地面, 1=硬墙, 2=目标槽位)
    uint8_t map_[16][16];

    // 4 个箱子
    static const int kNumBoxes = 4;
    SokobanBox boxes_[kNumBoxes];
    int boxes_on_goal_;
};

} // namespace arcade
