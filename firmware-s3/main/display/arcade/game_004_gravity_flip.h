// game_004_gravity_flip.h —— 目标 #004 重力翻转 (VVVVVV Flip)
// 机制: 严禁常规跳跃! 仅在接触地面或天花板时反转重力方向穿梭尖刺回廊
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

struct GravityOrb {
    int x;
    int y;
    bool collected;
};

class Game004GravityFlip : public Cartridge {
public:
    Game004GravityFlip();
    ~Game004GravityFlip() override = default;

    uint8_t GetId() const override { return 4; }
    const char* GetName() const override { return "重力翻转"; }
    const char* GetEnglishName() const override { return "VVVVVV Flip"; }
    uint16_t GetReleaseYear() const override { return 2010; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    void Init() override;
    void Reset() override;
    void Start() override;
    void Pause() override;
    void Resume() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    void LoadStage(int stage_idx);
    void RespawnPlayer();
    void AddScore(uint32_t pts);
    bool IsSolid(int tx, int ty) const;
    bool IsSpike(int tx, int ty) const;

    static const int kNumStages = 3;
    static const int kMaxOrbs = 2;

    CartridgeState state_;
    int stage_idx_;
    uint8_t lives_;
    float player_x_;
    float player_y_;
    float player_vy_;
    int gravity_dir_;
    bool grounded_;
    float drone_x_;
    float drone_y_;
    float drone_vx_;
    float drone_vy_;
    float drone_min_;
    float drone_max_;
    int exit_x_;
    int exit_y_;
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
    float anim_timer_;
    uint8_t grid_[16][16];
    GravityOrb orbs_[kMaxOrbs];
};

} // namespace arcade
