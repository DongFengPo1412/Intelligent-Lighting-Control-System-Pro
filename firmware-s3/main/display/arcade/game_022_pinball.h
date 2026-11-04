// game_022_pinball.h —— 目标 #022 迷你弹珠台 (Mini Pinball)
// 机制: 重力弹珠台 + 发光弹射蘑菇头(+25/+50) + 侧翼弹弓 + 左右独立挡板(A/LEFT 与 B/RIGHT)
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

struct PinballBumper {
    float x;
    float y;
    uint32_t points;
    float flash_timer;
};

class Game022Pinball : public Cartridge {
public:
    Game022Pinball();
    ~Game022Pinball() override = default;

    uint8_t GetId() const override { return 22; }
    const char* GetName() const override { return "迷你弹珠台"; }
    const char* GetEnglishName() const override { return "Mini Pinball"; }
    uint16_t GetReleaseYear() const override { return 1979; }
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
    uint32_t NextRand();
    void AddScore(uint32_t pts);
    void InitBumpers();
    void SpawnBall();

    static const int kNumBumpers = 3;

    CartridgeState state_;
    float ball_x_;
    float ball_y_;
    float ball_vx_;
    float ball_vy_;

    bool left_flipper_up_;
    bool right_flipper_up_;
    float left_swing_timer_;
    float right_swing_timer_;
    float sling_flash_l_;
    float sling_flash_r_;

    PinballBumper bumpers_[kNumBumpers];
    uint8_t balls_left_;

    uint32_t score_;
    uint32_t high_score_;
    uint32_t rng_seed_;
    float state_timer_;
    float anim_timer_;
};

} // namespace arcade
