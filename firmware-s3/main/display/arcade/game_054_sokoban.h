// game_054_sokoban.h —— 目标 #054 推箱子 (Sokoban 1982)
// 机制: 单向推移不可拉动 + 空间槽位逻辑归位 + 拓扑死锁与通关判定
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

class Game054Sokoban : public Cartridge {
public:
    Game054Sokoban();
    ~Game054Sokoban() override = default;

    uint8_t GetId() const override { return 54; }
    const char* GetName() const override { return "推箱子"; }
    const char* GetEnglishName() const override { return "Sokoban 1982"; }
    uint16_t GetReleaseYear() const override { return 1982; }
    ControlType GetControlType() const override { return CTRL_DPAD_4WAY; }

    void Init() override;
    void Reset() override;
    void Start() override;
    void Pause() override;
    void Resume() override;
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
    float anim_timer_;

    uint8_t map_[16][16];

    static const int kNumBoxes = 4;
    SokobanBox boxes_[kNumBoxes];
    int boxes_on_goal_;
};

} // namespace arcade

