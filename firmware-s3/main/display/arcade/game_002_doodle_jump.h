// game_002_doodle_jump.h —— 目标 #002 涂鸦跳跃 (Doodle Jump)
// 机制: 踩板自动弹跳上升 + 左右穿屏移动 + 镜头单向上移计分
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

enum DoodlePlatType : uint8_t {
    DOODLE_PLAT_NORMAL  = 0,
    DOODLE_PLAT_MOVING  = 1,
    DOODLE_PLAT_SPRING  = 2,
    DOODLE_PLAT_FRAGILE = 3,
};

struct DoodlePlatform {
    float x;
    float y;
    float vx;
    uint8_t type;
    bool broken;
};

class Game002DoodleJump : public Cartridge {
public:
    Game002DoodleJump();
    ~Game002DoodleJump() override = default;

    uint8_t GetId() const override { return 2; }
    const char* GetName() const override { return "涂鸦跳跃"; }
    const char* GetEnglishName() const override { return "Doodle Jump"; }
    uint16_t GetReleaseYear() const override { return 2009; }
    ControlType GetControlType() const override { return CTRL_TWO_BUTTON; }

    void Init() override;
    void Reset() override;
    void Start() override;
    void Pause() override;
    void Resume() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    uint32_t NextRand();
    float HighestSolidY() const;
    void SpawnPlatformAbove(DoodlePlatform& p, float ref_solid_y, bool allow_fragile);
    void InitPlayState();

    static const int kMaxPlatforms = 7;

    CartridgeState state_;
    float player_x_;
    float player_y_;
    float player_vx_;
    float player_vy_;
    bool facing_right_;
    float max_altitude_;
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
    float anim_timer_;
    uint32_t rng_seed_;
    DoodlePlatform platforms_[kMaxPlatforms];
};

} // namespace arcade
