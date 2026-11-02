// game_004_doodle_jump.h —— 涂鸦跳跃 16 (Doodle Jump 16)
// 编号: #004 | 机制: 接触自动弹跳 + 左右穿屏 + 纵向无限滚动
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

enum PlatformType : uint8_t {
    PLAT_NORMAL  = 0, // 绿色普通跳板 (弹力 1.0x)
    PLAT_MOVING  = 1, // 青色横移跳板 (水平巡逻)
    PLAT_SPRING  = 2, // 金色弹簧跳板 (弹力 1.6x 超级跳)
    PLAT_FRAGILE = 3, // 棕色破碎跳板 (踩后断裂塌陷)
};

struct Platform {
    float x;
    float y;
    float vx;
    PlatformType type;
    bool broken;
};

class Game004DoodleJump : public Cartridge {
public:
    Game004DoodleJump();
    ~Game004DoodleJump() override = default;

    uint8_t GetId() const override { return 4; }
    const char* GetName() const override { return "涂鸦跳跃"; }
    const char* GetEnglishName() const override { return "Doodle Jump 16"; }
    uint16_t GetReleaseYear() const override { return 2009; }
    ControlType GetControlType() const override { return CTRL_TWO_BUTTON; }

    void Init() override;
    void Reset() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    void SpawnPlatform(Platform& p, float min_y, float max_y);
    void DrawDoodler(uint8_t* fb, int px, int py, bool facing_right);

    CartridgeState state_;
    float player_x_;
    float player_y_;
    float player_vx_;
    float player_vy_;
    bool facing_right_;

    static const int kMaxPlatforms = 6;
    Platform platforms_[kMaxPlatforms];

    float camera_altitude_;
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
};

} // namespace arcade
