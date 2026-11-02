// game_010_pacman.h —— 像素吃豆人 1980 (Pac-Man 1980)
// 编号: #010 | 机制: 迷宫全豆漫游吞食 + 左右穿梭隧道 + 四向巡逻幽灵 + 大能量豆反噬逃跑态
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

enum GhostState {
    GHOST_CHASE = 0,
    GHOST_FRIGHTENED = 1,
    GHOST_EATEN = 2
};

struct Ghost {
    float x;
    float y;
    int dir_x; // -1, 0, 1
    int dir_y; // -1, 0, 1
    GhostState state;
    uint8_t r, g, b;
    float speed;
};

class Game010Pacman : public Cartridge {
public:
    Game010Pacman();
    ~Game010Pacman() override = default;

    uint8_t GetId() const override { return 10; }
    const char* GetName() const override { return "像素吃豆人"; }
    const char* GetEnglishName() const override { return "Pac-Man 1980"; }
    uint16_t GetReleaseYear() const override { return 1980; }
    ControlType GetControlType() const override { return CTRL_DPAD_4WAY; }

    void Init() override;
    void Reset() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    void ResetPositions();
    bool IsWall(int x, int y) const;
    void MoveGhost(Ghost& g, float dt);

    CartridgeState state_;
    float pac_x_;
    float pac_y_;
    int pac_dir_x_;
    int pac_dir_y_;
    int desired_dir_x_;
    int desired_dir_y_;

    static const int kNumGhosts = 3;
    Ghost ghosts_[kNumGhosts];
    float frightened_timer_;

    // 16x16 迷宫豆子状态: 0=空, 1=普通豆, 2=大力丸能量豆
    uint8_t grid_[16][16];
    int remaining_dots_;

    uint8_t lives_;
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
};

} // namespace arcade
