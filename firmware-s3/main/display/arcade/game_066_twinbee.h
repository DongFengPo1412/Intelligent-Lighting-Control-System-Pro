#pragma once

#include "cartridge.h"
#include <cstdint>

namespace arcade {

class Game066TwinBee : public Cartridge {
public:
    static constexpr uint8_t STATE_START = 0;
    static constexpr uint8_t STATE_PLAYING = 1;
    static constexpr uint8_t STATE_DEAD = 2;
    static constexpr uint8_t STATE_VICTORY = 3;

    // Bell Color Types
    static constexpr uint8_t BELL_YELLOW = 0; // Bonus Points
    static constexpr uint8_t BELL_WHITE  = 1; // Speed & Twin Gun
    static constexpr uint8_t BELL_BLUE   = 2; // Energy Shield
    static constexpr uint8_t BELL_RED    = 3; // Shadow Option Clone

    static constexpr int MAX_SHOTS = 4;
    static constexpr int MAX_BOMBS = 2;
    static constexpr int MAX_ENEMIES = 4;
    static constexpr int MAX_GROUND_TARGETS = 3;
    static constexpr int MAX_BELLS = 2;

    struct Projectile {
        float x;
        float y;
        float vx;
        float vy;
        bool active;
    };

    struct Bell {
        float x;
        float y;
        float vy;
        int hit_count;
        uint8_t color_type;
        bool active;
    };

    struct Enemy {
        float x;
        float y;
        float vx;
        float vy;
        int type;       // 0: Flying Strawberry, 1: Saucer
        int health;
        bool active;
    };

    struct GroundTarget {
        float x;
        float y;
        int type;       // 0: Ground Fruit, 1: Turret Gun
        bool active;
    };

    Game066TwinBee();
    ~Game066TwinBee() override = default;

    void Init() override;
    void Update(float dt, uint32_t buttons, uint32_t prev_buttons) override;
    void Render(uint8_t* fb) override;
    void Reset() override;

    const char* GetName() const override { return "TwinBee (1985)"; }
    uint8_t GetControlScheme() const override { return CTRL_ARCADE_AB; }

    uint8_t GetState() const { return state_; }
    int32_t GetScore() const { return score_; }
    int32_t GetHighScore() const { return high_score_; }
    int GetLives() const { return lives_; }
    float GetPlayerX() const { return px_; }
    float GetPlayerY() const { return py_; }
    bool HasShield() const { return has_shield_; }
    bool HasTwinGun() const { return has_twin_gun_; }
    bool HasOptionClone() const { return has_option_clone_; }
    bool HasArms() const { return has_arms_; }
    int GetEnemiesDefeated() const { return enemies_defeated_; }

    void ShootAir();
    void DropGroundBomb();
    void SpawnBell(float x, float y);

private:
    void InitStage();
    void UpdatePlayer(float dt, uint32_t buttons, uint32_t prev_buttons);
    void UpdateProjectiles(float dt);
    void UpdateBells(float dt);
    void UpdateEnemies(float dt);
    void UpdateAmbulance(float dt);
    void CheckCollisions();

    uint8_t state_;
    float state_timer_;
    int32_t score_;
    int32_t high_score_;
    int lives_;

    // TwinBee ship state
    float px_;
    float py_;
    float shoot_cooldown_;
    float bomb_cooldown_;
    bool has_twin_gun_;
    bool has_shield_;
    bool has_option_clone_;
    bool has_arms_;

    // Ambulance angel (appears when arms are lost)
    bool ambulance_active_;
    float amb_x_;
    float amb_y_;

    int enemies_defeated_;
    float cloud_timer_;

    Projectile shots_[MAX_SHOTS];
    Projectile bombs_[MAX_BOMBS];
    Bell bells_[MAX_BELLS];
    Enemy enemies_[MAX_ENEMIES];
    GroundTarget ground_targets_[MAX_GROUND_TARGETS];
};

} // namespace arcade
