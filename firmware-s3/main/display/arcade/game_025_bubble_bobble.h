// game_025_bubble_bobble.h —— 经典泡泡龙打怪 1986 (Bubble Bobble 1986)
// 编号: #025 | 机制: 吐泡包裹怪物 + 跳跃撞刺戳破秒杀 + 借泡弹跳漂浮 + 气泡升空气流
#pragma once

#include "arcade_cartridge.h"

namespace arcade {

struct BobbleBubble {
    bool active;
    float x;
    float y;
    float vx;
    float vy;
    int trapped_enemy; // -1 表示普通空气泡, >=0 表示被包裹的怪物编号
    float timer;
};

struct BobbleEnemy {
    bool active;
    float x;
    float y;
    float vx;
    float vy;
    bool trapped;
    float move_timer;
};

class Game025BubbleBobble : public Cartridge {
public:
    Game025BubbleBobble();
    ~Game025BubbleBobble() override = default;

    uint8_t GetId() const override { return 25; }
    const char* GetName() const override { return "经典泡泡龙打怪"; }
    const char* GetEnglishName() const override { return "Bubble Bobble 1986"; }
    uint16_t GetReleaseYear() const override { return 1986; }
    ControlType GetControlType() const override { return CTRL_ARCADE_AB; }

    void Init() override;
    void Reset() override;
    void Update(float dt, uint16_t keys_down, uint16_t keys_pressed) override;
    void Render(uint8_t* fb_rgb24) override;
    CartridgeStatus GetStatus() const override;

private:
    void InitLevel();
    void SpitBubble();
    void UpdateBubbles(float dt);
    void UpdateEnemies(float dt);
    bool IsOnPlatform(float x, float y) const;

    CartridgeState state_;

    float player_x_;
    float player_y_;
    float player_vy_;
    int player_dir_; // -1: LEFT, +1: RIGHT
    bool is_jumping_;
    int lives_;
    float spit_cooldown_;

    static constexpr int MAX_BUBBLES = 6;
    BobbleBubble bubbles_[MAX_BUBBLES];

    static constexpr int MAX_ENEMIES = 3;
    BobbleEnemy enemies_[MAX_ENEMIES];

    uint32_t score_;
    uint32_t high_score_;
    float state_timer_;
};

} // namespace arcade
