// game_027_asteroids.h —— 目标 #027 小行星 (Asteroids, 1979)
// 机制: 8方向旋转 + 牛顿惯性推进(环绕宇宙0..15) + 大陨石(2x2)击碎分裂为2颗小陨石(1x1)
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

struct AsteroidRock027 {
    bool active;
    uint8_t size; // 2 = 大陨石(2x2), 1 = 小陨石(1x1)
    float x;
    float y;
    float vx;
    float vy;
};

struct SpaceBullet027 {
    bool active;
    float x;
    float y;
    float vx;
    float vy;
    float life;
};

class Game027Asteroids : public Cartridge {
public:
    Game027Asteroids();
    ~Game027Asteroids() override = default;

    uint8_t GetId() const override { return 27; }
    const char* GetName() const override { return "小行星"; }
    const char* GetEnglishName() const override { return "Asteroids"; }
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
    static const int kMaxAsteroids = 16;
    static const int kMaxBullets = 4;

    uint32_t NextRand();
    void AddScore(uint32_t pts);
    void SetupNewGame(CartridgeState new_state);
    void InitWave();
    void SpawnAsteroid(float x, float y, float vx, float vy, uint8_t size);
    void SplitAsteroid(int idx);
    void FireBullet();

    CartridgeState state_;
    uint32_t score_;
    uint32_t high_score_;
    uint8_t lives_;
    uint8_t wave_;

    float ship_x_;
    float ship_y_;
    float ship_vx_;
    float ship_vy_;
    uint8_t ship_dir_; // 0..7 (0=上, 顺时针每45度一档)
    bool thrusting_;
    float rot_timer_;
    float fire_cooldown_;
    float invuln_timer_;

    AsteroidRock027 asteroids_[kMaxAsteroids];
    SpaceBullet027 bullets_[kMaxBullets];

    float state_timer_;
    float anim_timer_;
    uint32_t seed_;
};

} // namespace arcade
