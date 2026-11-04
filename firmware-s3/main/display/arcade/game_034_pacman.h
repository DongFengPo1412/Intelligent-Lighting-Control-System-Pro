// game_034_pacman.h —— 目标 #034 吃豆人 (Pac-Man 1980)
// 机制: 迷宫全豆漫游吞食 + 左右穿梭隧道 + 四向巡逻幽灵 + 大能量豆反噬逃跑态
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

enum PacGhostState {
    GHOST_CHASE = 0,
    GHOST_FRIGHTENED = 1,
    GHOST_EATEN = 2
};

struct PacGhost {
    float x;
    float y;
    int dir_x;
    int dir_y;
    PacGhostState state;
    uint8_t r, g, b;
    float speed;
};

class Game034Pacman : public Cartridge {
public:
    Game034Pacman();
    ~Game034Pacman() override = default;

    uint8_t GetId() const override { return 34; }
    const char* GetName() const override { return "吃豆人"; }
    const char* GetEnglishName() const override { return "Pac-Man 1980"; }
    uint16_t GetReleaseYear() const override { return 1980; }
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
    void ResetPositions();
    bool IsWall(int x, int y) const;
    void MoveGhost(PacGhost& g, float dt);

    CartridgeState state_;
    float pac_x_;
    float pac_y_;
    int pac_dir_x_;
    int pac_dir_y_;
    int desired_dir_x_;
    int desired_dir_y_;

    static const int kNumGhosts = 3;
    PacGhost ghosts_[kNumGhosts];
    float frightened_timer_;

    uint8_t grid_[16][16];
    int remaining_dots_;
    int total_dots_;

    uint8_t lives_;
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
    float anim_timer_;
};

} // namespace arcade

