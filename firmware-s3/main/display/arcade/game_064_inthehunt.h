#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game064InTheHunt : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_DEAD = 2;
    static constexpr uint8_t STATE_VICTORY = 3;

    static constexpr int MAX_TORPEDOES = 4;
    static constexpr int MAX_MISSILES = 3;
    static constexpr int MAX_DEPTH_CHARGES = 3;
    static constexpr int MAX_ENEMIES = 4;

    struct Projectile {
        float x;
        float y;
        float vx;
        float vy;
        bool is_player;
        bool active;
    };

    struct Enemy {
        float x;
        float y;
        float vx;
        int type;       // 0: Surface Gunboat, 1: Enemy Sub, 2: Sea Mine
        int health;
        bool active;
        float shoot_cooldown;
    };

    Game064InTheHunt();
    ~Game064InTheHunt() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "In The Hunt (1993)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    int GetLives() const { return lives_; }
    float GetSubX() const { return sub_x_; }
    float GetSubY() const { return sub_y_; }
    bool IsBossActive() const { return boss_active_; }
    int GetBossHealth() const { return boss_health_; }

    void FireTorpedoes();
    void DropDepthCharge();

private:
    void InitStage();
    void UpdateSubmarine(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateProjectiles(float dt);
    void UpdateEnemies(float dt);
    void UpdateBoss(float dt);
    void CheckCollisions();

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;
    int lives_;

    // Granvia submarine state
    float sub_x_;
    float sub_y_;
    int sub_facing_;
    float shoot_cooldown_;

    float scroll_x_;
    int enemies_defeated_;

    // Boss Mecha Kraken
    bool boss_active_;
    float boss_x_;
    float boss_y_;
    float boss_vy_;
    int boss_health_;
    float boss_shoot_cooldown_;

    Projectile torpedoes_[MAX_TORPEDOES];
    Projectile missiles_[MAX_MISSILES];
    Projectile depth_charges_[MAX_DEPTH_CHARGES];
    Enemy enemies_[MAX_ENEMIES];
};

} // namespace arcade
