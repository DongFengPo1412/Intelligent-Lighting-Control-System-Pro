// game_055_mirror_laser.h —— 目标 #055 镜面激光 (Mirror Laser 1990)
// 机制: 7x7 光学网格实时光线追踪 + / 与 \ 反射镜切换 + 棱镜充能与接收器通关
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

enum LaserCellType : uint8_t {
    LASER_EMPTY = 0,
    LASER_WALL = 1,
    LASER_EMITTER = 2,
    LASER_MIRROR_SLASH = 3,     // '/' : (dx, dy) -> (-dy, -dx)
    LASER_MIRROR_BACKSLASH = 4, // '\' : (dx, dy) -> (dy, dx)
    LASER_CRYSTAL = 5,
    LASER_RECEIVER = 6,
    LASER_BOMB = 7,
};

struct BeamStep {
    int x;
    int y;
};

class Game055MirrorLaser : public Cartridge {
public:
    static const int kGridSize = 7;
    static const int kNumStages = 4;
    static const int kMaxBeamSteps = 64;

    Game055MirrorLaser();
    ~Game055MirrorLaser() override = default;

    uint8_t GetId() const override { return 55; }
    const char* GetName() const override { return "镜面激光"; }
    const char* GetEnglishName() const override { return "Mirror Laser"; }
    uint16_t GetReleaseYear() const override { return 1990; }
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
    void TraceBeam();
    void AddScore(uint32_t pts);

    CartridgeState state_;
    int stage_;
    uint8_t lives_;
    int cursor_x_;
    int cursor_y_;
    int emit_x_;
    int emit_y_;
    int emit_dx_;
    int emit_dy_;
    int total_crystals_;
    int lit_crystals_;
    bool receiver_hit_;
    bool receiver_powered_;
    bool bomb_hit_;
    bool firing_=false;
    float charge_timer_;
    float bomb_timer_;
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
    float anim_timer_;

    uint8_t grid_[kGridSize][kGridSize];
    bool rotatable_[kGridSize][kGridSize];
    bool crystal_lit_[kGridSize][kGridSize];
    BeamStep beam_path_[kMaxBeamSteps];
    int beam_len_;
};

} // namespace arcade
