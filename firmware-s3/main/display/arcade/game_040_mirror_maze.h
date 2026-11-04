// game_040_mirror_maze.h —— 目标 #040 镜像双人迷宫 (Mirror Twins)
// 机制: 左右对称双生角色同步反向移动 + 不对称墙壁卡位对齐 + 陷阱躲避与双终点同时抵达
#pragma once

#include "arcade_cartridge.h"
#include <stdint.h>

namespace arcade {

class Game040MirrorMaze : public Cartridge {
public:
    Game040MirrorMaze();
    ~Game040MirrorMaze() override = default;

    uint8_t GetId() const override { return 40; }
    const char* GetName() const override { return "镜像双人迷宫"; }
    const char* GetEnglishName() const override { return "Mirror Twins"; }
    uint16_t GetReleaseYear() const override { return 2012; }
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
    static const int kTotalLevels = 4;

    void LoadLevel(int lvl);
    void StepMove(int dx, int dy);
    void AddScore(uint32_t pts);

    CartridgeState state_;
    uint8_t map_[16][16]; // 0: floor, 1: wall, 2: hazard pit, 3: goal_a, 4: goal_b
    int level_;
    int ax_;
    int ay_;
    int bx_;
    int by_;
    int goal_ax_;
    int goal_ay_;
    int goal_bx_;
    int goal_by_;
    int moves_;
    uint8_t lives_;
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
    float anim_timer_;
};

} // namespace arcade
