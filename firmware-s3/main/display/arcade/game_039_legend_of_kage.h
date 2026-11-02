#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game039LegendOfKage : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_DEAD = 2;
    static constexpr uint8_t STATE_VICTORY = 3;

    static constexpr int MAX_SHURIKENS = 4;
    static constexpr int MAX_ENEMY_PROJECTILES = 4;
    static constexpr int MAX_ENEMIES = 3;

    struct Projectile {
        float x;
        float y;
        float vx;
        float vy;
        bool active;
    };

    struct Ninja {
        float x;
        float y;
        float vx;
        float vy;
        bool is_red;
        bool active;
        float shoot_timer;
    };

    Game039LegendOfKage();
    ~Game039LegendOfKage() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Legend of Kage (1985)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    int GetLives() const { return lives_; }
    int GetEnemiesDefeated() const { return enemies_defeated_; }

    float GetPlayerX() const { return player_x_; }
    float GetPlayerY() const { return player_y_; }
    bool IsSlashing() const { return slash_timer_ > 0.0f; }

    void SetPlayerPos(float x, float y) { player_x_ = x; player_y_ = y; }
    void ThrowShuriken();
    void SlashSword();

private:
    void InitForest();
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateProjectiles(float dt);
    void UpdateEnemies(float dt);
    void CheckCollisions();

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;
    int lives_;
    int enemies_defeated_;
    int target_kills_;

    float player_x_;
    float player_y_;
    float player_vx_;
    float player_vy_;
    int player_facing_; // -1: Left, 1: Right
    bool is_grounded_;
    float slash_timer_; // 挥刀格挡时间

    Projectile shurikens_[MAX_SHURIKENS];
    Projectile enemy_bullets_[MAX_ENEMY_PROJECTILES];
    Ninja enemies_[MAX_ENEMIES];

    uint8_t tree_map_[16][16]; // 0: Sky, 1: Trunk, 2: Leaf Branch, 3: Ground
};

} // namespace arcade
