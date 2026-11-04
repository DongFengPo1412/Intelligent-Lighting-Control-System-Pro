// game_003_celeste_dash.h —— 目标 #003 空中冲刺 (Celeste Dash)
// 机制: 精密平台跳跃 + 8方向零重力空中冲刺 + 落地/水晶充能 + 多房间攀登
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

struct CelesteTrail {
    float x;
    float y;
    float timer;
    bool pink;
    bool active;
};

class Game003CelesteDash : public Cartridge {
public:
    Game003CelesteDash();
    ~Game003CelesteDash() override = default;

    uint8_t GetId() const override { return 3; }
    const char* GetName() const override { return "空中冲刺"; }
    const char* GetEnglishName() const override { return "Celeste Dash"; }
    uint16_t GetReleaseYear() const override { return 2018; }
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
    void LoadRoom(int room_idx);
    void RespawnInRoom();
    void AddScore(uint32_t pts);
    void SpawnTrail(bool pink);
    bool IsSolidTile(int tx, int ty) const;
    bool IsSpikeTile(int tx, int ty) const;

    static const int kNumRooms = 3;
    static const int kMaxTrail = 6;

    CartridgeState state_;
    int room_idx_;
    uint8_t lives_;
    float player_x_;
    float player_y_;
    float player_vx_;
    float player_vy_;
    int facing_x_;
    bool on_ground_;
    float coyote_timer_;
    bool dash_ready_;
    float dash_timer_;
    float dash_vx_;
    float dash_vy_;
    float trail_spawn_acc_;
    int crystal_x_;
    int crystal_y_;
    bool crystal_present_;
    float crystal_cooldown_;
    bool crystal_scored_;
    int goal_x_;
    int goal_y_;
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
    float anim_timer_;
    uint8_t grid_[16][16];
    CelesteTrail trails_[kMaxTrail];
};

} // namespace arcade
