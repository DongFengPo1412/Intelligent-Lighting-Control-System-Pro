// game_006_bubble_bobble.h —— 目标 #006 泡泡捕敌 (Bubble Bobble)
// 机制: 平台跳跃 + 水平吐泡裹敌上浮 + 触碰戳破击杀掉水果 (严禁做成消除类泡泡龙!)
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

struct BobbleEnemy {
    float x;
    float y;
    float vx;
    float vy;
    float jump_timer;
    bool on_ground;
    bool trapped;
    bool angry;
    bool active;
};

struct BobbleShot {
    float x;
    float y;
    float vx;
    float dist_left;
    float timer;
    int trapped_enemy;
    uint8_t phase;
    bool active;
};

struct BobbleFruit {
    float x;
    float y;
    float vy;
    float timer;
    bool landed;
    bool active;
};

class Game006BubbleBobble : public Cartridge {
public:
    Game006BubbleBobble();
    ~Game006BubbleBobble() override = default;

    uint8_t GetId() const override { return 6; }
    const char* GetName() const override { return "泡泡捕敌"; }
    const char* GetEnglishName() const override { return "Bubble Bobble"; }
    uint16_t GetReleaseYear() const override { return 1986; }
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
    void LoadWave(int wave_idx, bool clear_fruits);
    void AddScore(uint32_t pts);
    bool IsPlatformTop(int x, int plat_y) const;
    float ResolveLandingY(float x, float old_y, float new_y, bool& landed) const;
    void ShootBubble();
    void SpawnFruit(float x, float y);
    void UpdateBubbles(float dt);
    void UpdateFruits(float dt);
    void UpdateEnemies(float dt);

    static const int kNumWaves = 3;
    static const int kMaxEnemies = 3;
    static const int kMaxBubbles = 5;
    static const int kMaxFruits = 3;

    CartridgeState state_;
    int wave_idx_;
    uint8_t lives_;
    float player_x_;
    float player_y_;
    float player_vy_;
    int facing_dir_;
    bool on_ground_;
    float shoot_cooldown_;
    float invuln_timer_;
    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
    float anim_timer_;
    BobbleEnemy enemies_[kMaxEnemies];
    BobbleShot bubbles_[kMaxBubbles];
    BobbleFruit fruits_[kMaxFruits];
};

} // namespace arcade
