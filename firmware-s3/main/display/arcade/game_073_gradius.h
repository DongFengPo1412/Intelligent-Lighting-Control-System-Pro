#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game073Gradius : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_DEAD = 2;
    static constexpr uint8_t STATE_VICTORY = 3;

    // Power Meter Tiers (0: none, 1..6)
    static constexpr uint8_t TIER_SPEED_UP = 1;
    static constexpr uint8_t TIER_MISSILE  = 2;
    static constexpr uint8_t TIER_DOUBLE   = 3;
    static constexpr uint8_t TIER_LASER    = 4;
    static constexpr uint8_t TIER_OPTION   = 5;
    static constexpr uint8_t TIER_SHIELD   = 6;

    static constexpr int MAX_SHOTS = 4;
    static constexpr int MAX_MISSILES = 2;
    static constexpr int MAX_CAPSULES = 3;
    static constexpr int MAX_ENEMIES = 4;
    static constexpr int TRAIL_SIZE = 12;

    struct Projectile {
        float x;
        float y;
        float vx;
        float vy;
        bool is_laser;
        bool active;
    };

    struct Capsule {
        float x;
        float y;
        bool active;
    };

    struct Enemy {
        float x;
        float y;
        float vx;
        float vy;
        int type;       // 0: Red formation scout (drops capsule), 1: Turret
        int health;
        bool active;
    };

    struct PositionNode {
        float x;
        float y;
    };

    Game073Gradius();
    ~Game073Gradius() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "Gradius (1985)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    int GetLives() const { return lives_; }
    float GetPlayerX() const { return px_; }
    float GetPlayerY() const { return py_; }
    uint8_t GetMeterSlot() const { return meter_slot_; }
    bool HasSpeedUp() const { return has_speed_up_; }
    bool HasMissile() const { return has_missile_; }
    bool HasDouble() const { return has_double_; }
    bool HasLaser() const { return has_laser_; }
    bool HasOption() const { return has_option_; }
    bool HasShield() const { return shield_hp_ > 0; }
    bool IsBossActive() const { return boss_active_; }
    int GetBossHealth() const { return boss_core_health_; }

    void Shoot();
    void ActivatePowerMeter();
    void CollectCapsule();

private:
    void InitStage();
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateProjectiles(float dt);
    void UpdateEnemies(float dt);
    void UpdateBoss(float dt);
    void CheckCollisions();

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;
    int lives_;

    // Vic Viper state
    float px_;
    float py_;
    float shoot_cooldown_;
    float missile_cooldown_;

    // Power meter slot (0 = none, 1..6)
    uint8_t meter_slot_;
    bool has_speed_up_;
    bool has_missile_;
    bool has_double_;
    bool has_laser_;
    bool has_option_;
    int shield_hp_;

    // Option follower trail
    PositionNode trail_[TRAIL_SIZE];
    int trail_idx_;

    int enemies_defeated_;

    // Big Core Boss
    bool boss_active_;
    float boss_x_;
    float boss_y_;
    float boss_vy_;
    int boss_barrier_health_;
    int boss_core_health_;
    float boss_shoot_cooldown_;

    Projectile shots_[MAX_SHOTS];
    Projectile missiles_[MAX_MISSILES];
    Capsule capsules_[MAX_CAPSULES];
    Enemy enemies_[MAX_ENEMIES];
};

} // namespace arcade
